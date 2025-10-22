from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import conn

auth = Blueprint('auth', __name__)
cursor = conn.cursor(dictionary=True)


def student_auth(username, password):
    cursor.callproc('AuthenticateStudent', (username, password))
    result = None
    for r in cursor.stored_results():
        result = r.fetchone()
    return result


def lecturer_auth(username, password):
    cursor.callproc('AuthenticateLecturer', (username, password))
    result = None
    for r in cursor.stored_results():
        result = r.fetchone()
    return result

def admin_auth(username, password):
    cursor.callproc('AuthenticateAdmin', (username, password))
    for result in cursor.stored_results():
        return result.fetchone()
    
@auth.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('ID')
        password = request.form.get('password')

        # Kiểm tra admin
        admin_account = admin_auth(username, password)
        if admin_account:
           session.clear()
           session['role'] = 'admin'
           session['user_id'] = admin_account['password']
           return redirect(url_for('admin_views.admin'))
        

        # Kiểm tra sinh viên
        student_account = student_auth(username, password)
        if student_account:
            session.clear()
            session['role'] = 'student'
            session['user_id'] = student_account['student_id']
            return redirect(url_for('views.home', student_id = student_account['student_id']))

        # Kiểm tra giảng viên
        lecturer_account = lecturer_auth(username, password)
        if lecturer_account:
            session.clear()
            session['role'] = 'lecturer'
            session['user_id'] = lecturer_account['lecturer_id']
            return redirect(url_for('lecturer_views.lecturer_home', lecturer_id=lecturer_account['lecturer_id']))

        # Sai thông tin
        flash("Sai ID hoặc Password! Vui lòng thử lại!")

    return render_template('login.html')


@auth.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Lấy mật khẩu hiện tại từ DB
        cursor.callproc('get_student_password', (session['user_id'],))
        for result in cursor.stored_results():
            user = result.fetchone()

        if not user:
            flash('Không tìm thấy tài khoản.', 'danger')
            return redirect(url_for('auth.change_password'))

        if user['password'] != current_password:
            flash('Mật khẩu hiện tại không đúng.', 'danger')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('Mật khẩu mới và xác nhận không khớp.', 'warning')
            return redirect(url_for('auth.change_password'))

        # Cập nhật mật khẩu mới
        cursor.callproc('ChangeStudentPassword', (session['user_id'], new_password))
        conn.commit()

        flash('Đổi mật khẩu thành công!', 'success')
        return redirect(url_for('auth.login',))

    return render_template('change_password.html')

@auth.route('/logout')
def logout():
    session.clear()
    flash("Đăng xuất thành công.")
    return redirect(url_for('auth.login'))