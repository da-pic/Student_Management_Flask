from flask import render_template, Blueprint, request, redirect, url_for, session
from .models import conn


admin_proposal = Blueprint('admin_proposal', __name__)
cursor = conn.cursor(dictionary=True)

@admin_proposal.route('/proposal', methods=['GET'])
def show_proposal():
    cursor.execute('''
        SELECT * FROM proposed_scr
        WHERE _status='Pending';
    ''')
    proposals = cursor.fetchall()
    return render_template('admin_proposal.html', proposals=proposals)


@admin_proposal.route('/approve/<proposal_id>', methods=['POST'])
def approve_proposal(proposal_id):
    cursor.execute("SET @is_admin = TRUE")
    proposal = []
    cursor.execute('SELECT * FROM proposed_scr WHERE proposal_id = %s', (proposal_id,))
    proposal = cursor.fetchone()
    cursor.execute('''
        UPDATE Score
        SET attendance_scr = %s, midterm_scr = %s, finalterm_scr = %s
        WHERE student_id = %s AND course_class_id = %s''',
        (proposal['proposed_attendance_scr'], proposal['proposed_midterm_scr'], proposal['proposed_finalterm_scr'], 
        proposal['student_id'], proposal['course_class_id'])
    )
    cursor.execute("UPDATE proposed_scr SET _status='Approved' WHERE proposal_id = %s",
                   (proposal_id,))
    cursor.execute("SET @is_admin = FALSE")
    conn.commit()
    return redirect(url_for('admin_proposal.show_proposal'))

@admin_proposal.route('/deny/<proposal_id>', methods=['POST'])
def deny_proposal(proposal_id):
    cursor.execute("UPDATE proposed_scr SET _status='Denied' WHERE proposal_id = %s",
                   (proposal_id,))
    conn.commit()
    return redirect(url_for('admin_proposal.show_proposal'))
