from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import conn

auth = Blueprint('auth', __name__)
cursor = conn.cursor(dictionary=True)


def student_auth(username, password):
    query = '''
        SELECT student_id, student_email 
        FROM student 
        WHERE student_email = %s AND student_id = %s;
    '''
    cursor.execute(query, (username, password))
    return cursor.fetchone()


def lecturer_auth(username, password):
    query = '''
        SELECT lecturer_id, lecturer_email
        FROM lecturer
        WHERE lecturer_email = %s AND lecturer_id = %s;
    '''
    cursor.execute(query, (username, password))
    return cursor.fetchone()

def admin_auth(username, password):
    query = '''
        SELECT admin_id, admin_password
        FROM admin
        WHERE admin_id = %s AND admin_password = %s;
    '''
    cursor.execute(query, (username, password))
    return cursor.fetchone()

@auth.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('email')
        password = request.form.get('ID')

        # Kiểm tra admin
        #admin_account = admin_auth(username, password)
        #if admin_account:
           # session.clear()
           # session['role'] = 'admin'
           # session['user_id'] = 'admin'
           # return redirect(url_for('views.admin'))

        # Kiểm tra sinh viên
        student_account = student_auth(username, password)
        if student_account:
            session.clear()
            session['role'] = 'student'
            session['user_id'] = student_account['student_id']
            session['email'] = student_account['student_email']
            return redirect(url_for('views.home', student_id = student_account['student_id']))

        # Kiểm tra giảng viên
        lecturer_account = lecturer_auth(username, password)
        if lecturer_account:
            session.clear()
            session['role'] = 'lecturer'
            session['user_id'] = lecturer_account['lecturer_id']
            session['email'] = lecturer_account['lecturer_email']
            return redirect(url_for('views.lecturer_home'))

        # Sai thông tin
        flash("Sai ID hoặc Email, vui lòng thử lại!")

    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash("Đăng xuất thành công.")
    return redirect(url_for('auth.login'))
