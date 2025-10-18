from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import conn

enrollment = Blueprint('enrollment', __name__)

@enrollment.route('/enrollment/<student_id>')
def enrollment_page(student_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            c.course_id,
            c.course_name,
            c.volume,
            cc.course_class_id,
            l.lecturer_name
        FROM course_class cc
        JOIN course c ON cc.course_id = c.course_id
        JOIN lecturer l ON cc.lecturer_id = l.lecturer_id
    """)
    course_class = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            c.course_id,
            c.course_name,
            c.volume,
            cc.course_class_id,
            l.lecturer_name
        FROM enrollment e
        JOIN course_class cc ON e.course_class_id = cc.course_class_id
        JOIN course c ON cc.course_id = c.course_id
        JOIN lecturer l ON cc.lecturer_id = l.lecturer_id
        WHERE e.student_id = %s
    """, (student_id,))
    registered_class = cursor.fetchall()
    cursor.close()

    return render_template("enrollment.html", student_id=student_id, registered_class=registered_class, course_class=course_class)


@enrollment.route('/enrollment/<student_id>/register', methods=['POST'])
def register_courses(student_id):
    conn.ping(reconnect=True)  # đảm bảo kết nối MySQL còn sống
    selected = request.form.getlist('selected_courses')

    has_error = False
    cursor = conn.cursor()

    try:
        for cc_id in selected:
            cursor.execute("""
                INSERT INTO enrollment (student_id, course_class_id)
                VALUES (%s, %s)
            """, (student_id, cc_id))
        conn.commit()
        flash("✅ Đăng ký thành công!", "success")

    except Exception as e:
        conn.rollback()
        has_error = True
        flash(f"⚠️ bạn đã đăng ký lớp học này!", "error")

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
            cursor.execute("""
                DELETE FROM enrollment
                WHERE student_id = %s AND course_class_id = %s
            """, (student_id, cc_id))
        conn.commit()
        flash("✅ Huỷ đăng ký thành công!", "cancel_success")

    except Exception as e:
        conn.rollback()
        flash(f"⚠️ Lỗi khi huỷ đăng ký: {e}", "cancel_error")

    finally:
        cursor.close()

    return redirect(url_for('enrollment.enrollment_page', student_id=student_id))
