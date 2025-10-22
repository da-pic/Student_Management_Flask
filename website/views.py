from flask import render_template, Blueprint, request, url_for, session
from .models import conn
from decimal import Decimal


views = Blueprint('views', __name__)

@views.route('/home/<student_id>')
def home(student_id):
    cursor = conn.cursor(dictionary=True)
    # Lấy thông tin sinh viên
    cursor.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        return "Không tìm thấy sinh viên", 404

    # Xác định tab hiện tại
    active_tab = request.args.get("tab", "hoso")

    # Nếu tab = lop-hanh-chinh => lấy danh sách lớp hành chính
    students = []
    if active_tab == "lop-hanh-chinh":
        cursor.execute("SELECT * FROM Student WHERE administrative_class = %s", (student['administrative_class'],))
        students = cursor.fetchall()

    # Nếu tab = hoc-tap => lấy kết quả học tập
    scores = []
    if active_tab == "hoc-tap":
        cursor.execute("""
            SELECT 
                c.course_name,
                c.course_id,
                sc.attendance_scr,
                sc.midterm_scr,
                sc.finalterm_scr
            FROM Score sc
            JOIN Course_class cc ON sc.course_class_id = cc.course_class_id
            JOIN Course c ON c.course_id = cc.course_id
            WHERE sc.student_id = %s
        """, (student_id,))
        scores = cursor.fetchall()
        for s in scores:
            attend = s['attendance_scr']
            mid = s['midterm_scr']
            final = s['finalterm_scr']

            for row in scores:
                row['final_grade'] = (
                (row['attendance_scr'] or 0) * 0.1 +
                (row['midterm_scr'] or 0) * 0.2 +
                (row['finalterm_scr'] or 0) * 0.7
            )
        conn.commit()

    # Lay thong tin cac lop tin chi cua sinh vien.
    course_class = []
    if active_tab == "lop-tin-chi":
        cursor.execute("""
            SELECT c.course_name, cc.course_class_id, L.lecturer_name, c.volume
            FROM Enrollment enr
            JOIN Course_Class cc ON enr.course_class_id = cc.course_class_id
            JOIN Lecturer L ON L.lecturer_id = cc.lecturer_id
            JOIN Course c ON c.course_id = cc.course_id
            WHERE enr.student_id = %s 
        """, (student_id,))
        course_class = cursor.fetchall()
    cursor.close()


    academy_cards = []
    if active_tab == "hoso":
        academy_cards = [
            {"id": 0, "title": "Khai giảng học kỳ mới", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=0)},
            {"id": 1, "title": "Thông báo học bổng", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=1)},
            {"id": 2, "title": "Bảo trì hệ thống", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=2)},
            {"id": 3, "title": "Câu lạc bộ AI", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=3)},
            {"id": 4, "title": "Hội thảo nghiên cứu", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=4)},
            {"id": 5, "title": "Tuyển sinh trợ giảng", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=5)},
            {"id": 6, "title": "Sự kiện thể thao", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=6)},
            {"id": 7, "title": "Khóa học kỹ năng mềm", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=7)},
            {"id": 8, "title": "Cuộc thi sáng tạo", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=8)},
            {"id": 9, "title": "Ngày hội việc làm", "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "link": url_for("views.academy_detail", card_id=9)}
        ]


    return render_template(
        "home.html",
        student=student,
        active_tab=active_tab,
        students=students,
        scores=scores,
        course_class=course_class,
        academy_cards=academy_cards
    )

@views.route("/home/class_details/<course_class_id>")
def class_details(course_class_id):
    cursor = conn.cursor(dictionary=True)

    # Thông tin lớp học + môn + giảng viên
    cursor.execute("""
        SELECT cc.course_class_id, c.volume, c.course_id, c.course_name, 
               l.lecturer_id, l.lecturer_name, l.lecturer_contact, l.lecturer_email
        FROM Course_Class cc
        JOIN Course c ON cc.course_id = c.course_id
        JOIN Lecturer l ON cc.lecturer_id = l.lecturer_id
        WHERE cc.course_class_id = %s
    """, (course_class_id,))
    course_class = cursor.fetchone()

    if not course_class:
        cursor.close()
        return "Không tìm thấy lớp học", 404

    # Danh sách sinh viên trong lớp (nếu có)
    cursor.execute("""
        SELECT s.student_id, s.administrative_class, s.student_name, s.student_gender,
               s.student_bd, s.student_address, s.student_contact, s.student_email, s.CPA
        FROM Enrollment e
        JOIN Student s ON e.student_id = s.student_id
        WHERE e.course_class_id = %s
        ORDER BY s.student_name
    """, (course_class_id,))
    students = cursor.fetchall()
    student_count = len(students)
    cursor.close()
    return render_template('class_details.html', course_class=course_class, students=students, student_count=student_count)



@views.route("/academy/<int:card_id>")
def academy_detail(card_id):
    cards = [
        {
            "id": 0,
            "title": "Khai giảng học kỳ mới",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Học kỳ II năm học 2025-2026 sẽ chính thức bắt đầu vào ngày 5/11/2025.",
            "details": "Sinh viên cần hoàn tất đăng ký tín chỉ trước ngày 30/10/2025. Buổi lễ khai giảng diễn ra tại hội trường lớn."
        },
        {
            "id": 1,
            "title": "Thông báo học bổng",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Sinh viên có CPA từ 3.2 trở lên đủ điều kiện xét học bổng.",
            "details": "Bao gồm học bổng khuyến học, doanh nghiệp tài trợ và nghiên cứu khoa học. Hạn chót: 10/11/2025."
        },
        {
            "id": 2,
            "title": "Lịch bảo trì hệ thống",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Cổng thông tin sinh viên sẽ bảo trì từ 00:00-02:00 ngày 25/10/2025.",
            "details": "Trong thời gian này không thể đăng ký tín chỉ hoặc xem điểm. Vui lòng hoàn thành thao tác trước thời điểm này."
        },
        {
            "id": 3,
            "title": "Câu lạc bộ AI",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "CLB AI chính thức ra mắt cho sinh viên yêu thích công nghệ.",
            "details": "Tổ chức workshop, chia sẻ kiến thức về Machine Learning, Deep Learning. Đăng ký tại văn phòng Đoàn trường."
        },
        {
            "id": 4,
            "title": "Hội thảo nghiên cứu",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Hội thảo nghiên cứu khoa học 2025 Cơ hội giao lưu học thuật.",
            "details": "Giảng viên và sinh viên trình bày các đề tài mới trong lĩnh vực AI và Data Science."
        },
        {
            "id": 5,
            "title": "Tuyển sinh trợ giảng",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Khoa CNTT thông báo tuyển trợ giảng cho học kỳ mới.",
            "details": "Ứng viên cần đạt CPA từ 3.0 trở lên, nộp hồ sơ trước 28/10/2025 tại văn phòng khoa."
        },
        {
            "id": 6,
            "title": "Sự kiện thể thao",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Giải thể thao sinh viên toàn trường 2025 khởi tranh!",
            "details": "Bao gồm bóng đá, cầu lông, bóng bàn. Đăng ký tại phòng Công tác sinh viên."
        },
        {
            "id": 7,
            "title": "Khóa học kỹ năng mềm",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Mở lớp kỹ năng giao tiếp và làm việc nhóm miễn phí.",
            "details": "Khai giảng ngày 10/11/2025. Sinh viên đăng ký qua website hoặc tại phòng đào tạo."
        },
        {
            "id": 8,
            "title": "Cuộc thi sáng tạo",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Cuộc thi sáng tạo dành cho sinh viên toàn quốc.",
            "details": "Chủ đề: 'Công nghệ vì cộng đồng'. Giải thưởng lên đến 50 triệu đồng."
        },
        {
            "id": 9,
            "title": "Ngày hội việc làm",
            "image": "https://dean1665.vn/uploads/school/buu-chinh-vien-thong_1.jpg",
            "content": "Ngày hội việc làm 2025 quy tụ hơn 30 doanh nghiệp.",
            "details": "Tổ chức tại sảnh lớn ngày 15/11/2025. Mang theo CV để phỏng vấn trực tiếp."
        }
    ]
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        return "Không tìm thấy thông tin học viện", 404

    return render_template("academy_detail.html", card=card, student_id=session['user_id'])


