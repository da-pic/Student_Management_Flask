from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import conn

auth = Blueprint('auth', __name__)
cursor = conn.cursor(dictionary=True)




def student_auth(username, password):
    student_query = '''
            SELECT student_id, student_email 
            FROM student 
            WHERE student_email = %s AND student_id = %s;
        '''
    cursor.execute(student_query, (username, password))
    return cursor.fetchone()
    
def lecturer_auth(username, password):
    lecturer_query = '''
        SELECT lecturer_id, lecturer_email
        FROM Lecturer
        WHERE lecturer_email = %s AND lecturer_id = %s;
    '''
    cursor.execute(lecturer_query, (username, password))
    return cursor.fetchone()


@auth.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('email')
        password = request.form.get('ID')

        student_account = student_auth(username, password)
        lecturer_account = lecturer_auth(username, password)

        # Admin page.
        if username == "admin" and password == "taolaadmin":
            return redirect(url_for('views.admin'))
        
        # Student page.
        elif student_account:
            student_id = student_account["student_id"]
            return redirect(url_for('views.home', student_id=student_id))
        
        # Lecturer Page.
        elif lecturer_account:
            pass
        else:
            flash("Sai ID hoặc Email, vui lòng thử lại!")

    return render_template('login.html')
