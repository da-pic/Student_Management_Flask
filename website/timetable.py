from flask import Blueprint, render_template, request
from datetime import date, timedelta
from .models import conn

timetable = Blueprint('timetable', __name__)

@timetable.route('/timetable/<student_id>')
def timetable_page(student_id):
    # Lấy tuần hiện tại từ query string, mặc định = 1
    week = int(request.args.get('week', 1))

    # Ngày bắt đầu học kỳ (ví dụ: 24/02/2025)
    start_semester = date(2025, 2, 24)
    start_of_week = start_semester + timedelta(weeks=week - 1)
    end_of_week = start_of_week + timedelta(days=6)

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            c.course_name AS subject_name,
            cc.class_day,
            cc.start_time,
            cc.end_time,
            cc.class_room,
            cc.week_start,
            cc.week_end,
            l.lecturer_name AS teacher
        FROM Enrollment e
        JOIN Course_Class cc ON e.course_class_id = cc.course_class_id
        JOIN Course c ON cc.course_id = c.course_id
        JOIN Lecturer l ON cc.lecturer_id = l.lecturer_id
        WHERE e.student_id = %s
          AND %s BETWEEN cc.week_start AND cc.week_end       
        ORDER BY cc.class_day, cc.start_time
    """, (student_id, week))

    rows = cursor.fetchall()
    cursor.close()

    timetable_data = [
    {
        "day": r["class_day"],
        "start": r["start_time"].seconds // 3600 if r["start_time"] else None,
        "end": r["end_time"].seconds // 3600 if r["end_time"] else None,
        "name": r["subject_name"],
        "room": r["class_room"],
        "teacher": r["teacher"]
    }
    for r in rows
]

    return render_template(
        "timetable.html",
        timetable_data=timetable_data,
        week=week,
        start_of_week=start_of_week,
        end_of_week=end_of_week,
        student_id=student_id
    )
