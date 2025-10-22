from flask import Blueprint, render_template, request, redirect, url_for
from .models import conn

admin_views = Blueprint('admin_views', __name__)

@admin_views.route("/admin")
def admin():
    active_tab = request.args.get("tab", "danh-sach-sinh-vien")
    cursor = conn.cursor(dictionary=True)
    administrative_classes = []
    lecturers = []
    proposals = []
    if active_tab == 'danh-sach-sinh-vien':
        cursor.callproc("GetAdministrativeClassList")
        for result in cursor.stored_results():
            administrative_classes = result.fetchall()

    if active_tab == 'danh-sach-giang-vien':
        cursor.execute('''
            SELECT * FROM Lecturer
        ''')
        lecturers = cursor.fetchall()

    
    return render_template(
        "admin.html", 
        administrative_classes=administrative_classes, 
        active_tab=active_tab,
        lecturers=lecturers
    )

@admin_views.route("/admin/<administrative_class>")
def manage_students(administrative_class):
    cursor = conn.cursor(dictionary=True)   
    cursor.execute("SELECT * FROM Student WHERE administrative_class = %s", (administrative_class,))
    students = cursor.fetchall()
    cursor.close()
    return render_template("manage_students.html", students=students, administrative_class=administrative_class)

@admin_views.route("/admin/add-student/<administrative_class>", methods=["POST"])
def add_student(administrative_class):
    data = request.form
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Student (student_id, administrative_class, student_name, student_gender, student_bd, student_email, student_contact, password)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["student_id"],
            administrative_class,
            data["student_name"],
            data.get("student_gender"),
            data.get("student_bd"),
            data.get("student_email"),
            data.get("student_contact"),
            "123456"
        ))
    conn.commit()
    cursor.close()
    return redirect(url_for("admin_views.manage_students", administrative_class=administrative_class))

@admin_views.route("/admin/update-student/<student_id>", methods=["POST"])
def update_student(student_id):
    data = request.form
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Student
        SET student_name=%s, student_gender=%s, student_bd=%s, student_email=%s,
            student_contact=%s, student_address=%s
        WHERE student_id=%s
        """, (
            data.get("student_name"),
            data.get("student_gender"),
            data.get("student_bd"),
            data.get("student_email"),
            data.get("student_contact"),
            data.get("student_address"),
            student_id
        ))
    conn.commit()
    cursor.close()
    return redirect(request.referrer)

@admin_views.route("/admin/delete-student/<student_id>", methods=["POST"])
def delete_student(student_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Student WHERE student_id = %s", (student_id,))
    conn.commit()
    cursor.close()
    return redirect(request.referrer)

# Thêm giảng viên
@admin_views.route('/add-lecturer', methods=['POST'])
def add_lecturer():
    lecturer_id = request.form['lecturer_id']
    name = request.form['lecturer_name']
    email = request.form['lecturer_email']
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lecturer (lecturer_id, lecturer_name, lecturer_email, password) VALUES (%s, %s, %s, %s)",
        (lecturer_id, name, email, "123")
    )
    conn.commit()
    return redirect(url_for('admin_views.admin', tab='danh-sach-giang-vien'))

# Sua thong tin Giang Vien
@admin_views.route('/admin/edit_lecturer/<lecturer_id>', methods=['POST'])
def edit_lecturer(lecturer_id):
    lecturer_name = request.form.get('lecturer_name')
    lecturer_email = request.form.get('lecturer_email')

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Lecturer
        SET lecturer_name = %s, lecturer_email = %s
        WHERE lecturer_id = %s
    """, (lecturer_name, lecturer_email, lecturer_id))
    conn.commit()
    cursor.close()

    return redirect(url_for('admin_views.admin', tab='danh-sach-giang-vien'))

# Xóa giảng viên
@admin_views.route('/delete-lecturer/<lecturer_id>', methods=['POST'])
def delete_lecturer(lecturer_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lecturer WHERE lecturer_id=%s", (lecturer_id,))
    conn.commit()
    return redirect(url_for('admin_views.admin', tab='danh-sach-giang-vien'))