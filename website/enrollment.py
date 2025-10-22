from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import conn

enrollment = Blueprint('enrollment', __name__)

@enrollment.route('/enrollment/<student_id>')
def enrollment_page(student_id):
    cursor = conn.cursor(dictionary=True)
    # Lấy tất cả lớp học
    cursor.callproc('GetAllCourseClasses')
    course_class = []
    for result in cursor.stored_results():
        course_class = result.fetchall()
    cursor.close()

    # Lấy các lớp mà sinh viên đã đăng ký
    cursor = conn.cursor(dictionary=True)
    cursor.callproc('GetRegisteredCourses', (student_id,))
    registered_class = []
    for result in cursor.stored_results():
        registered_class = result.fetchall()
    cursor.close()

    return render_template("enrollment.html",
                           student_id=student_id,
                           registered_class=registered_class,
                           course_class=course_class)


@enrollment.route('/enrollment/<student_id>/register', methods=['POST'])
def register_courses(student_id):
    conn.ping(reconnect=True)
    selected = request.form.getlist('selected_courses')

    cursor = conn.cursor(dictionary=True)

    replaced = 0
    added = 0

    try:
        # Lấy course_id và tên môn của lớp đang chọn
        for cc_id in selected:
            cursor.callproc('GetCourseInfoByClassId', (cc_id,))
            for result in cursor.stored_results():
                new_course = result.fetchone()
            if not new_course:
                continue

            course_id = new_course['course_id']
            course_name = new_course['course_name']

            # 🔹 Kiểm tra xem sinh viên đã có lớp nào cùng course_id chưa
            cursor.callproc('CheckDuplicateEnrollment', (student_id, course_id))

            # Lấy kết quả từ stored procedure
            old_enrollment = None
            for result in cursor.stored_results():
                old_enrollment = result.fetchone()
            # 🔹 Nếu đã có lớp cũ -> xóa lớp cũ trước
            if old_enrollment:
                cursor.callproc('RemoveOldEnrollment', (student_id, old_enrollment['course_class_id']))
                replaced += 1

            # 🔹 Thêm lớp mới
            cursor.callproc('AddNewEnrollment', (student_id, cc_id))
            added += 1

        conn.commit()

        # 🔹 Hiển thị thông báo kết quả
        if added > 0:
            flash(f"✅ Đăng ký thành công {added} lớp học!", "success")
        if replaced > 0:
            flash(f"⚠️ Đã thay thế {replaced} lớp trùng môn bằng lớp mới.", "error")

    except Exception as e:
        conn.rollback()
        flash(f"⚠️ Lỗi trong quá trình đăng ký: {e}", "error")

    finally:
        cursor.close()

    return redirect(url_for('enrollment.enrollment_page', student_id=student_id))


@enrollment.route('/enrollment/<student_id>/cancel', methods=['POST'])
def canceled_course(student_id):
    conn.ping(reconnect=True)
    selected_cancel = request.form.getlist('selected_cancel_courses')

    cursor = conn.cursor()
    try:
        for cc_id in selected_cancel:
            cursor.callproc('CancelEnrollment', (student_id, cc_id))
        conn.commit()
        flash("✅ Huỷ đăng ký thành công!", "cancel_success")

    except Exception as e:
        conn.rollback()
        flash(f"⚠️ Lỗi khi huỷ đăng ký: {e}", "cancel_error")

    finally:
        cursor.close()

    return redirect(url_for('enrollment.enrollment_page', student_id=student_id))