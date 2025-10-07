from flask import render_template, Blueprint, request
from .models import conn
from decimal import Decimal


views = Blueprint('views', __name__)

@views.route('/home/<student_id>')
def home(student_id):
    cursor = conn.cursor(dictionary=True)
    # Lấy thông tin sinh viên
    cursor.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        return "Không tìm thấy sinh viên", 404

    # Xác định tab hiện tại
    active_tab = request.args.get("tab", "hoso")

    # Nếu tab = lop-hanh-chinh => lấy danh sách lớp hành chính
    students = []
    if active_tab == "lop-hanh-chinh":
        cursor.execute("SELECT * FROM Student WHERE administrative_class = %s", (student['administrative_class'],))
        students = cursor.fetchall()

    # Nếu tab = hoc-tap => lấy kết quả học tập
    scores = []
    if active_tab == "hoc-tap":
        cursor.execute("""
            SELECT 
                c.course_name,
                c.course_id,
                sc.attendane_scr,
                sc.midterm_scr,
                sc.finalterm_scr,
                sc.final_grade
            FROM Score sc
            JOIN Course c ON sc.course_id = c.course_id
            WHERE sc.student_id = %s
        """, (student_id,))
        scores = cursor.fetchall()
        for s in scores:
            attend = s['attendane_scr']
            mid = s['midterm_scr']
            final = s['finalterm_scr']

            if attend is not None and mid is not None and final is not None:
                total = round(float(attend) * 0.1 + float(mid) * 0.3 + float(final) * 0.6, 2)

                # Nếu điểm tổng kết chưa có hoặc cần cập nhật
                if s['final_grade'] != total:
                    cursor.execute("""
                        UPDATE Score
                        SET final_grade = %s
                        WHERE student_id = %s AND course_id = %s
                    """, (total, student_id, s['course_id']))
        conn.commit()

    # Lay thong tin cac lop tin chi cua sinh vien.
    course_class = []
    if active_tab == "lop-tin-chi":
        cursor.execute("""
            SELECT c.course_name, cc.course_class_id, L.lecturer_name, c.volume
            FROM Enrollment enr
            JOIN Course_Class cc ON enr.course_class_id = cc.course_class_id
            JOIN Lecturer L ON L.lecturer_id = cc.lecturer_id
            JOIN Course c ON c.course_id = cc.course_id
            WHERE enr.student_id = %s 
        """, (student_id,))
        course_class = cursor.fetchall()
    cursor.close()

    return render_template(
        "home.html",
        student=student,
        active_tab=active_tab,
        students=students,
        scores=scores,
        course_class=course_class
    )


@views.route("/admin")
def admin():
    active_tab = request.args.get("tab", "danh-sach-sinh-vien")
    cursor = conn.cursor(dictionary=True)
    administrative_classes = []
    if active_tab == 'danh-sach-sinh-vien':
        cursor.execute('''
            SELECT administrative_class, COUNT(student_id) AS student_count
            FROM Student
            GROUP BY administrative_class;
        ''')
        administrative_classes = cursor.fetchall()
    return render_template("admin.html", administrative_classes=administrative_classes, active_tab=active_tab)

@views.route("/admin/<administrative_class>")
def manage_student(administrative_class):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
                   
    """)