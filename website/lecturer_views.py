# =========================================================================================
# Module: lecturer_views.py
# Mô tả: Các route liên quan đến chức năng giảng viên (Refactored - Tab-based)
# Bao gồm: Dashboard, quản lý lớp học, nhập điểm, xem thời khóa biểu
# =========================================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .models import conn
from .chatbot_helper import extract_entity_context, get_session_context, call_openai_chat, get_fallback_reply
import unicodedata
from datetime import datetime, timedelta, date

lecturer_views = Blueprint('lecturer_views', __name__)
cursor = conn.cursor(dictionary=True)
# ==================== Timetable Helper Functions ====================

def _parse_schedule_row(row):
	"""Parse dữ liệu lịch học: (class_day, start_time, end_time, room) -> (ui_day, start_str, end_str, room)"""
	cd, st, et = row.get('class_day'), row.get('start_time'), row.get('end_time')
	if not all([cd, st, et]):
		return None, None, None, None
	
	try:
		ui_day = int(cd) + 1  # DB: 1-7 -> UI: 2-8
		st_s = st.strftime('%H:%M') if hasattr(st, 'strftime') else str(st)[:5]
		et_s = et.strftime('%H:%M') if hasattr(et, 'strftime') else str(et)[:5]
		return ui_day, st_s, et_s, row.get('class_room', 'Phòng chưa rõ')
	except:
		return None, None, None, None


def _build_timetable_blocks(classes, week_start, week_end):
	"""Xây dựng timetable blocks với vị trí tuyệt đối (top%, height%)"""
	blocks = []
	base = datetime.strptime('07:00', '%H:%M')
	window_min = 720  # 12 tiếng
	
	for cls in classes:
		dow, s_str, e_str, room = _parse_schedule_row(cls)
		if not all([dow, s_str, e_str]):
			continue
		
		try:
			s_dt = datetime.strptime(s_str[:5], '%H:%M')
			e_dt = datetime.strptime(e_str[:5], '%H:%M')
			start_min = max(0, (s_dt - base).total_seconds() / 60)
			dur = (e_dt - s_dt).total_seconds() / 60
			
			if dur > 0:
				blocks.append({
					'id': cls['course_class_id'],
					'title': f"{cls['course_class_id']} — {cls['course_name']}",
					'day': int(dow),
					'top_pct': min(100, (start_min / window_min) * 100),
					'height_pct': max(3, min(100, (dur / window_min) * 100)),
					'room': room,
					'time': f"{s_dt:%H:%M}-{e_dt:%H:%M}"
				})
		except:
			continue
	
	return blocks


def _get_week_range(week_param=None):
	"""Tính tuần: (week_start, week_end, prev_week_iso, next_week_iso)"""
	try:
		week_start = datetime.fromisoformat(week_param).date() if week_param else date.today()
	except:
		week_start = date.today()
	
	week_start = week_start - timedelta(days=week_start.weekday())
	return (week_start, 
	        week_start + timedelta(days=6),
	        (week_start - timedelta(days=7)).isoformat(),
	        (week_start + timedelta(days=7)).isoformat())

# ==================== End Timetable Helpers ====================

def _strip_vi(text):
	"""Bỏ dấu tiếng Việt: 'Nguyễn' -> 'nguyen'"""
	return ''.join(c for c in unicodedata.normalize('NFD', text or '') 
	               if unicodedata.category(c) != 'Mn').lower().strip()


@lecturer_views.route('/lecturer/home/<lecturer_id>')
def lecturer_home(lecturer_id):
	"""
	Trang chủ giảng viên với tab-based navigation
	Tabs: home, courses, input, timetable
	"""

	# Lấy thông tin giảng viên
	cursor.execute("SELECT * FROM Lecturer WHERE lecturer_id = %s", (lecturer_id,))
	lecturer = cursor.fetchone()
	if not lecturer:
		return "Không tìm thấy giảng viên", 404

	# Xác định tab hiện tại
	active_tab = request.args.get("tab", "home")

	# === TAB: HOME (Dashboard) ===
	classes = []
	courses = []
	timetable_blocks = []
	if active_tab == "home":
		# Lấy danh sách lớp học với lịch học
		cursor.execute("""
			SELECT cc.course_class_id, c.course_name, cc.class_day, cc.start_time, 
			       cc.end_time, cc.class_room, cc.semester, cc.academic_year
			FROM course_class cc
			JOIN course c ON cc.course_id = c.course_id
			WHERE cc.lecturer_id = %s
			ORDER BY cc.class_day, cc.start_time
		""", (lecturer_id,))
		classes = cursor.fetchall()

		# Xây dựng timetable blocks
		week_start, week_end, _, _ = _get_week_range()
		timetable_blocks = _build_timetable_blocks(classes, week_start, week_end)

		# Lấy danh sách môn học
		cursor.execute("""
			SELECT DISTINCT c.course_name
			FROM course c
			JOIN course_class cc ON c.course_id = cc.course_id
			WHERE cc.lecturer_id = %s
		""", (lecturer_id,))
		courses = cursor.fetchall()

	# === TAB: COURSES (Môn phụ trách) ===
	courses_dict = {}
	if active_tab == "courses":
		cursor.execute("""
			SELECT c.course_id, c.course_name, cc.course_class_id
			FROM course_class AS cc
			JOIN course AS c ON cc.course_id = c.course_id
			WHERE cc.lecturer_id = %s
			ORDER BY c.course_name
		""", (lecturer_id,))
		results = cursor.fetchall()
		
		# Nhóm các lớp theo tên môn học
		for row in results:
			course_name = row['course_name']
			if course_name not in courses_dict:
				courses_dict[course_name] = []
			courses_dict[course_name].append(row['course_class_id'])

	# === TAB: INPUT (Nhập điểm) ===
	input_classes = []
	if active_tab == "input":
		cursor.execute("""
			SELECT cc.course_class_id, c.course_name
			FROM course_class cc
			JOIN course c ON cc.course_id = c.course_id
			WHERE cc.lecturer_id = %s
		""", (lecturer_id,))
		input_classes = cursor.fetchall()

	# === TAB: TIMETABLE (Thời khóa biểu) ===
	week_meta = {}
	week_options = []
	if active_tab == "timetable":
		week_start, week_end, prev_week, next_week = _get_week_range(request.args.get('week'))

		# Lấy lịch học
		cursor.execute("""
			SELECT cc.course_class_id, c.course_name, cc.class_day, cc.start_time, 
			       cc.end_time, cc.class_room, cc.semester, cc.academic_year
			FROM course_class cc
			JOIN course c ON cc.course_id = c.course_id
			WHERE cc.lecturer_id = %s
			ORDER BY cc.class_day, cc.start_time
		""", (lecturer_id,))
		classes = cursor.fetchall()
		timetable_blocks = _build_timetable_blocks(classes, week_start, week_end)

		# Tạo dropdown tuần (26 tuần: -12 đến +12)
		week_options = [
			{'iso': (week_start + timedelta(weeks=off)).isoformat(),
			 'label': f"Tuần {(week_start + timedelta(weeks=off)).isocalendar()[1]} [{(week_start + timedelta(weeks=off)).strftime('%d/%m')} - {(week_start + timedelta(weeks=off, days=6)).strftime('%d/%m')}]",
			 'selected': off == 0}
			for off in range(-12, 13)
		]

		week_meta = {
			'start': week_start.strftime('%d/%m/%Y'),
			'end': week_end.strftime('%d/%m/%Y'),
			'prev': prev_week,
			'next': next_week,
			'iso_start': week_start.isoformat()
		}


	return render_template(
		'lecturer.html',
		lecturer=lecturer,
		active_tab=active_tab,
		classes=classes,
		courses=courses,
		courses_dict=courses_dict,
		input_classes=input_classes,
		timetable_blocks=timetable_blocks,
		week_meta=week_meta,
		week_options=week_options
	)


@lecturer_views.route('/lecturer/input/<lecturer_id>/<course_class_id>', methods=['GET', 'POST'])
def lecturer_input_scores(lecturer_id, course_class_id):
	"""Trang nhập điểm cho lớp học"""
	if request.method == 'POST':
		count = int(request.form.get('count', 0))
		try:
			update_sql = """
				UPDATE Score
				SET attendance_scr = %s,
					midterm_scr = %s,
					finalterm_scr = %s
				WHERE student_id = %s AND course_class_id = %s
			"""

			def to_val(v):
				if v in (None, ''):
					return None
				try:
					return float(v)
				except:
					return None

			for i in range(count):
				sid = request.form.get(f'student_id_{i}')
				att_v = to_val(request.form.get(f'attendance_scr_{i}'))
				mid_v = to_val(request.form.get(f'midterm_scr_{i}'))
				fin_v = to_val(request.form.get(f'finalterm_scr_{i}'))
				params = (att_v, mid_v, fin_v, sid, course_class_id)
				cursor.execute("SET @lecturer_id=%s", (lecturer_id,))
				cursor.execute("SET @is_admin=FALSE")
				cursor.execute(update_sql, params)
			
			conn.commit()
			flash('Cập nhật điểm thành công!')
		except Exception as e:
			return f"Lỗi khi lưu điểm: {e}", 500

		return redirect(url_for('lecturer_views.lecturer_input_scores', lecturer_id=lecturer_id, course_class_id=course_class_id))

	# GET: load thông tin
	cursor.execute("SELECT * FROM Lecturer WHERE lecturer_id = %s", (lecturer_id,))
	lecturer = cursor.fetchone()
	if not lecturer:
		return "Không tìm thấy giảng viên", 404

	cursor.execute("""
		SELECT cc.course_class_id, c.course_name
		FROM course_class cc
		JOIN course c ON cc.course_id = c.course_id
		WHERE cc.course_class_id = %s
	""", (course_class_id,))
	class_info = cursor.fetchone()

	cursor.execute("""
		SELECT s.student_id, s.student_name, sc.attendance_scr, sc.midterm_scr, sc.finalterm_scr
		FROM enrollment e
		JOIN student s ON e.student_id = s.student_id
		LEFT JOIN Score sc ON sc.student_id = s.student_id AND sc.course_class_id = %s
		WHERE e.course_class_id = %s
		ORDER BY s.student_name
	""", (course_class_id, course_class_id))
	students = cursor.fetchall()

	return render_template(
		'lecturer.html', 
		active_tab='input_scores', 
		lecturer=lecturer, 
		class_info=class_info, 
		students=students
	)



@lecturer_views.route('/lecturer/class/<course_class_id>')
def lecturer_class_detail(course_class_id):
	"""Chi tiết lớp học và danh sách sinh viên"""

	cursor.execute("""
		SELECT cc.course_class_id, c.course_id, c.course_name,
		       l.lecturer_id, l.lecturer_name
		FROM course_class cc
		JOIN course c ON cc.course_id = c.course_id
		JOIN lecturer l ON cc.lecturer_id = l.lecturer_id
		WHERE cc.course_class_id = %s
	""", (course_class_id,))
	class_info = cursor.fetchone()
	if not class_info:
		return "Không tìm thấy lớp học", 404

	cursor.execute("""
		SELECT s.student_id, s.student_name, s.administrative_class,
		       s.student_bd AS dob, s.student_address, s.student_email
		FROM enrollment e
		JOIN student s ON s.student_id = e.student_id
		WHERE e.course_class_id = %s
	""", (course_class_id,))
	students = cursor.fetchall() or []

	# Sắp xếp theo tên (bỏ dấu tiếng Việt)
	for sv in students:
		parts = (sv.get("student_name") or "").strip().split()
		sv["_k"] = (_strip_vi(parts[-1] if parts else ""), 
		            _strip_vi(" ".join(parts[:-1]) if len(parts) > 1 else ""))
	
	students.sort(key=lambda x: (*x["_k"], x["student_id"]))
	for sv in students:
		sv.pop("_k", None)

	lecturer = None
	lid = class_info.get('lecturer_id')
	if lid:
		cursor.execute("SELECT * FROM Lecturer WHERE lecturer_id = %s", (lid,))
		lecturer = cursor.fetchone()

	return render_template(
		'lecturer.html', 
		active_tab='class_detail', 
		class_info=class_info, 
		students=students, 
		lecturer=lecturer
	)


@lecturer_views.route('/chat/api', methods=['POST'])
def chat_api():
	"""API chatbot hỗ trợ trả lời câu hỏi"""
	try:
		data = request.get_json(force=True) or {}
	except Exception:
		data = {}
	
	user_msg = (data.get('message') or '').strip()
	if not user_msg:
		return jsonify({'reply': 'Bạn chưa nhập gì cả. Hãy gửi câu hỏi nhé.'})
	
	extra_context = extract_entity_context(user_msg)
	context_parts = get_session_context()
	openai_reply = call_openai_chat(user_msg, context_parts, extra_context)
	
	if openai_reply:
		return jsonify({'reply': openai_reply})
	
	from .chatbot_helper import get_fallback_reply
	fallback_reply = get_fallback_reply(user_msg, extra_context)
	return jsonify({'reply': fallback_reply})