from flask import render_template, Blueprint, request
from .models import conn
views = Blueprint('views', __name__)

@views.route('/home/<student_id>')
def home(student_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    
    if not student:
        return "Không tìm thấy sinh viên", 404

    return render_template("home.html", student=student)