from flask import render_template, Blueprint, request
from .models import conn
views = Blueprint('views', __name__)

@views.route('/home/<student_id>')
def home(student_id):
    tab = request.args.get("tab", "hoso")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    administrative_students = []
    if tab == "lop-hanh-chinh":
        cursor.execute("select * from student where administrative_class = %s", (student['administrative_class'],))
        administrative_students = cursor.fetchall()
        print(">>> Lớp hành chính của SV:", student['administrative_class'])
        print(">>> Danh sách cùng lớp:", administrative_students)
    return render_template("home.html", student=student, students=administrative_students, active_tab=tab)
