# =========================================================================================
# Module: chatbot_helper.py
# Mô tả: Helper functions cho chatbot API
# =========================================================================================

from flask import current_app, session, jsonify
from .models import conn
import os
import re


def extract_entity_context(user_msg):
	"""
	Trích xuất context từ mã giảng viên (L####) hoặc sinh viên (S####) trong câu hỏi
	
	Args:
		user_msg: Câu hỏi của người dùng
	
	Returns:
		list: Danh sách chuỗi context
	"""
	extra_context = []
	
	try:
		# Tìm mã giảng viên (L####)
		m = re.search(r"\bL\d{1,5}\b", user_msg, flags=re.IGNORECASE)
		if m:
			lid = m.group(0).upper()
			try:
				cur_e = conn.cursor(dictionary=True)
				
				# Lấy thông tin giảng viên
				cur_e.execute(
					"SELECT lecturer_id, lecturer_name, lecturer_contact, lecturer_email, lecturer_faculty "
					"FROM Lecturer WHERE lecturer_id=%s", 
					(lid,)
				)
				L = cur_e.fetchone()
				if L:
					extra_context.append(f"Lecturer: {L.get('lecturer_name')} (ID {L.get('lecturer_id')})")
					if L.get('lecturer_faculty'):
						extra_context.append(f"Faculty: {L.get('lecturer_faculty')}")
					
					# Lấy danh sách môn học
					cur_e.execute(
						"SELECT cc.course_class_id, c.course_name "
						"FROM course_class cc JOIN course c ON cc.course_id=c.course_id "
						"WHERE cc.lecturer_id=%s", 
						(lid,)
					)
					rows = cur_e.fetchall()
					if rows:
						courses = ", ".join([f"{r['course_class_id']}={r['course_name']}" for r in rows])
						extra_context.append(f"Courses: {courses}")
						
						# Lấy lịch học chi tiết
						try:
							cur_e.execute(
								"SELECT course_class_id, class_day, start_time, end_time, class_room "
								"FROM course_class WHERE lecturer_id=%s", 
								(lid,)
							)
							sched = cur_e.fetchall()
							if sched:
								for s in sched:
									# Chuyển class_day (1..7) thành label (Thứ 2..CN)
									dow = s.get('class_day')
									if dow:
										dd = int(dow)
										dow_label = 'CN' if dd == 7 else f"Thứ {dd+1}"
									else:
										dow_label = 'Khác'
									
									# Format thời gian
									st = s.get('start_time')
									et = s.get('end_time')
									st_s = st.strftime('%H:%M') if hasattr(st, 'strftime') else (str(st)[:5] if st else '')
									et_s = et.strftime('%H:%M') if hasattr(et, 'strftime') else (str(et)[:5] if et else '')
									
									extra_context.append(
										f"Lớp {s.get('course_class_id')}: {dow_label} {st_s}-{et_s} "
										f"tại {s.get('class_room') or 'Phòng chưa rõ'}"
									)
						except Exception:
							pass
				
				cur_e.close()
				conn.close()
			except Exception:
				current_app.logger.exception('Failed to fetch lecturer by id in quick-extract')
		else:
			# Tìm mã sinh viên (S####)
			m2 = re.search(r"\bS\d{1,5}\b", user_msg, flags=re.IGNORECASE)
			if m2:
				sid = m2.group(0).upper()
				try:
					cur_e = conn.cursor(dictionary=True)
					cur_e.execute(
						"SELECT student_id, student_name, administrative_class, student_email "
						"FROM Student WHERE student_id=%s", 
						(sid,)
					)
					S = cur_e.fetchone()
					if S:
						extra_context.append(f"Student: {S.get('student_name')} (ID {S.get('student_id')})")
						if S.get('administrative_class'):
							extra_context.append(f"Class: {S.get('administrative_class')}")
					cur_e.close()
					conn.close()
				except Exception:
					current_app.logger.exception('Failed to fetch student by id in quick-extract')
	except Exception:
		current_app.logger.exception('Error in entity extraction')
	
	return extra_context


def get_session_context():
	"""
	Lấy context từ session user hiện tại
	
	Returns:
		list: Danh sách chuỗi context
	"""
	context_parts = []
	
	try:
		uid = session.get('user_id')
		role = session.get('role')
		
		if uid and role:
			cur_ctx = conn.cursor(dictionary=True)
			
			if role == 'lecturer':
				# Lấy thông tin giảng viên
				cur_ctx.execute(
					"SELECT lecturer_id, lecturer_name, lecturer_contact, lecturer_email, lecturer_faculty "
					"FROM Lecturer WHERE lecturer_id=%s", 
					(uid,)
				)
				L = cur_ctx.fetchone()
				if L:
					context_parts.append(f"Lecturer: {L.get('lecturer_name')} (ID {L.get('lecturer_id')})")
					if L.get('lecturer_faculty'):
						context_parts.append(f"Faculty: {L.get('lecturer_faculty')}")
					if L.get('lecturer_contact'):
						context_parts.append(f"Contact: {L.get('lecturer_contact')}")
				
				# Lấy danh sách môn học
				cur_ctx.execute(
					"SELECT cc.course_class_id, c.course_name "
					"FROM course_class cc JOIN course c ON cc.course_id=c.course_id "
					"WHERE cc.lecturer_id=%s", 
					(uid,)
				)
				rows = cur_ctx.fetchall()
				if rows:
					courses = ", ".join([f"{r['course_class_id']}={r['course_name']}" for r in rows])
					context_parts.append(f"Courses: {courses}")
			
			elif role == 'student':
				# Lấy thông tin sinh viên
				cur_ctx.execute(
					"SELECT student_id, student_name, administrative_class, student_email "
					"FROM Student WHERE student_id=%s", 
					(uid,)
				)
				S = cur_ctx.fetchone()
				if S:
					context_parts.append(f"Student: {S.get('student_name')} (ID {S.get('student_id')})")
					if S.get('administrative_class'):
						context_parts.append(f"Class: {S.get('administrative_class')}")
					if S.get('student_email'):
						context_parts.append(f"Email: {S.get('student_email')}")
			
			cur_ctx.close()
			conn.close()
	except Exception:
		current_app.logger.exception('Failed to gather context from DB')
	
	return context_parts


def call_openai_chat(user_msg, context_parts, extra_context):
	"""
	Gọi OpenAI API để trả lời câu hỏi
	
	Args:
		user_msg: Câu hỏi của người dùng
		context_parts: Context từ session
		extra_context: Context trích xuất từ câu hỏi
	
	Returns:
		str: Câu trả lời từ OpenAI hoặc None nếu lỗi
	"""
	openai_key = os.environ.get('OPENAI_API_KEY')
	if not openai_key:
		return None
	
	try:
		import importlib
		openai = importlib.import_module('openai')
		openai.api_key = openai_key
		
		# System prompt
		system_prompt = (
			"You are an assistant for a university management system. "
			"Answer in Vietnamese. Use only the information provided in the Context. "
			"Do not invent facts. If the answer is not in Context, say 'Mình không có dữ liệu về việc này.' "
			"Keep answers concise and, when appropriate, cite the source label from Context."
		)
		
		# Few-shot examples
		few_shots = [
			("Giảng viên L001 dạy môn gì?", "L001 — Cơ sở dữ liệu; CC002 — Lập trình Python."),
			("Làm sao để xem bảng điểm?", "Bạn có thể vào mục 'Quản lý điểm' và chọn 'Nhập điểm' hoặc vào trang hồ sơ sinh viên để xem kết quả.")
		]
		
		# Xây dựng messages
		messages = [{"role": "system", "content": system_prompt}]
		for q, a in few_shots:
			messages.append({"role": "user", "content": q})
			messages.append({"role": "assistant", "content": a})
		
		# Kết hợp context
		combined_ctx = []
		if context_parts:
			combined_ctx.extend(context_parts)
		if extra_context:
			combined_ctx.extend(extra_context)
		ctx_text = "\n".join(combined_ctx) if combined_ctx else ""
		
		# User prompt
		user_prompt = (
			f"Context:\n{ctx_text or '(No context available)'}\n\n"
			f"Question: {user_msg}\n\n"
			"Instructions: Use only Context, answer in Vietnamese. "
			"If not in Context say 'Mình không có dữ liệu về việc này.' Keep it concise."
		)
		messages.append({"role": "user", "content": user_prompt})
		
		current_app.logger.debug(f'OpenAI ctx length: {len(ctx_text)}; extra_context_len={len(extra_context)}')
		
		# Gọi OpenAI API
		resp = openai.ChatCompletion.create(
			model='gpt-3.5-turbo',
			messages=messages,
			max_tokens=300,
			temperature=0.1,
		)
		
		return resp.choices[0].message.content.strip()
	except Exception:
		current_app.logger.exception('OpenAI call failed')
		return None


def get_fallback_reply(user_msg, extra_context):
	"""
	Trả lời fallback đơn giản dựa trên từ khóa (khi không có OpenAI)
	
	Args:
		user_msg: Câu hỏi của người dùng
		extra_context: Context trích xuất được
	
	Returns:
		str: Câu trả lời fallback
	"""
	# Nếu có extra_context, trả về luôn
	if extra_context:
		return 'Thông tin tìm thấy: ' + '; '.join(extra_context)
	
	u = user_msg.lower()
	
	# Câu hỏi về giảng viên
	if any(g in u for g in ['giảng viên', 'giang vien', 'giangvien']):
		if session.get('lecturer_id'):
			lid = session.get('lecturer_id')
			try:
				curx = conn.cursor()
				curx.execute("SELECT lecturer_name FROM Lecturer WHERE lecturer_id=%s", (lid,))
				rowx = curx.fetchone()
				curx.close()
				conn.close()
				if rowx:
					return f"Giảng viên hiện tại: {rowx[0]} (ID {lid})"
			except Exception:
				current_app.logger.exception('fallback lecturer lookup failed')
		return 'Bạn đang hỏi về giảng viên nào? Vui lòng cung cấp mã giảng viên (ví dụ: L001) hoặc tên để mình tra giúp.'
	
	# Chào hỏi
	if any(g in u for g in ['xin chào', 'hello', 'chào', 'hi']):
		return 'Chào bạn! Mình có thể giúp gì cho bạn về hệ thống quản lý sinh viên?'
	
	# Câu hỏi về điểm
	if 'điểm' in u or 'score' in u or 'điểm số' in u:
		return 'Bạn muốn xem hay nhập điểm? Vui lòng cho biết mã lớp hoặc mã sinh viên.'
	
	# Câu hỏi về hồ sơ
	if 'hồ sơ' in u or 'profile' in u:
		return 'Để vào hồ sơ giảng viên, bạn có thể dùng mục Hồ sơ (QLGV) ở sidebar.'
	
	# Trả lời mặc định
	return "Xin lỗi, mình chưa hiểu rõ. Hãy thử hỏi lại hoặc mô tả rõ hơn."