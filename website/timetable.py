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
     # Gọi stored procedure
    cursor.callproc('get_timetable_by_week', [student_id, week])

    # Lấy dữ liệu trả về
    rows = []
    for result in cursor.stored_results():
        rows = result.fetchall()

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
