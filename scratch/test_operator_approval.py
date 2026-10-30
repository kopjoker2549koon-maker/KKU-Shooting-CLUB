import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
from app import app, get_db

def run_tests():
    print("==================================================")
    print("STARTING TEST: Committee First-Time Registration & God Approval")
    print("==================================================")
    client = app.test_client()

    # 1. Test GET /register_operator
    res = client.get('/register_operator')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode('utf-8')
    assert 'ลงทะเบียนกรรมการครั้งแรก' in html, "Page title missing in register_operator.html"
    assert 'position' in html, "Position field missing"
    assert 'student_id' in html, "Student ID field missing"
    print("[PASS] 1. GET /register_operator returned 200 OK with correct form fields")

    # Clean up any leftover test accounts
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username IN ('test_op_somchai', 'test_op_reject')")
    conn.commit()
    conn.close()

    # 2. Test Invalid Student ID (no hyphen)
    res = client.post('/register_operator', data={
        'username': 'test_op_somchai',
        'password': 'password123',
        'confirm_password': 'password123',
        'position': 'ฝ่ายพัสดุ',
        'prefix': 'นาย',
        'first_name': 'สมชาย',
        'last_name': 'ใจดี',
        'student_id': '6630509999', # no hyphen!
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 3',
        'kku_mail': 'somchai@kkumail.com',
        'phone': '0891234567'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รหัสนักศึกษาให้อยู่ในรูปแบบที่มีขีด' in html, "Hyphen validation failed to trigger"
    print("[PASS] 2. Student ID hyphen validation properly triggered")

    # 3. Test Password Mismatch
    res = client.post('/register_operator', data={
        'username': 'test_op_somchai',
        'password': 'password123',
        'confirm_password': 'different_password',
        'position': 'ฝ่ายพัสดุ',
        'prefix': 'นาย',
        'first_name': 'สมชาย',
        'last_name': 'ใจดี',
        'student_id': '663050999-1',
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 3',
        'kku_mail': 'somchai@kkumail.com',
        'phone': '0891234567'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน' in html, "Password mismatch validation failed"
    print("[PASS] 3. Password mismatch validation properly triggered")

    # 4. Test Valid Registration
    res = client.post('/register_operator', data={
        'username': 'test_op_somchai',
        'password': 'op_password123',
        'confirm_password': 'op_password123',
        'position': 'ฝ่ายพัสดุ',
        'prefix': 'นาย',
        'first_name': 'สมชาย',
        'last_name': 'ใจดี',
        'student_id': '663050999-1',
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 3',
        'kku_mail': 'somchai@kkumail.com',
        'phone': '0891234567'
    }, follow_redirects=True)
    assert res.status_code == 200, f"Expected 200 after redirect, got {res.status_code}"
    html = res.data.decode('utf-8')
    assert 'ส่งคำขอลงทะเบียนกรรมการเรียบร้อยแล้ว' in html, "Success flash message missing"
    print("[PASS] 4. Valid operator registration submitted and redirected with success alert")

    # Verify status in database is 'pending'
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, role, status, position FROM users WHERE username='test_op_somchai'")
    user = c.fetchone()
    conn.close()
    assert user is not None, "User record not found in database"
    assert user['role'] == 'operator', f"Expected role 'operator', got {user['role']}"
    assert user['status'] == 'pending', f"Expected status 'pending', got {user['status']}"
    assert user['position'] == 'ฝ่ายพัสดุ', f"Expected position match, got {user['position']}"
    test_user_id = user['id']
    print(f"[PASS] 5. Database record confirmed: ID #{test_user_id}, status='pending', role='operator'")

    # 5. Attempt login with pending operator credentials -> Must be blocked!
    res = client.post('/', data={
        'username': 'test_op_somchai',
        'password': 'op_password123',
        'role': 'operator'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รอการอนุมัติจากผู้ดูแลระบบ' in html, "Pending user was not blocked at login!"
    with client.session_transaction() as sess:
        assert 'user_id' not in sess, "Pending user should not have an active session!"
    print("[PASS] 6. Pending operator login is correctly BLOCKED with approval warning")

    # 6. Login as God Admin and check pending queue in /god
    client.post('/', data={
        'username': 'KoldP',
        'password': '1987',
        'role': 'god',
        'secret_god_mode': 'activated'
    }, follow_redirects=True)

    res = client.get('/god')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'คำขอลงทะเบียนกรรมการใหม่' in html or 'PENDING OPERATOR' in html, "Pending section missing from god.html"
    assert 'test_op_somchai' in html, "Pending operator username missing in god queue"
    assert 'ฝ่ายพัสดุ' in html, "Pending operator position missing in god queue"
    assert '663050999-1' in html, "Pending operator student ID missing in god queue"
    print("[PASS] 7. God admin sees pending operator in queue with all submitted details")

    # 7. God approves operator
    res = client.post('/god', data={
        'action': 'approve_operator',
        'user_id': test_user_id
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'อนุมัติสิทธิ์กรรมการเรียบร้อยแล้ว' in html, "Approval success message missing"
    
    # Verify in DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT status FROM users WHERE id=?", (test_user_id,))
    row = c.fetchone()
    conn.close()
    assert row['status'] == 'approved', f"Expected status 'approved', got {row['status']}"
    print(f"[PASS] 8. God Admin approved operator ID #{test_user_id}. DB status is now 'approved'")

    # Logout god
    client.get('/logout')

    # 8. Login as newly approved operator -> Must SUCCEED!
    res = client.post('/', data={
        'username': 'test_op_somchai',
        'password': 'op_password123',
        'role': 'operator'
    }, follow_redirects=True)
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'ระบบจัดการคลังและอนุมัติสลิป' in html, "Approved operator did not land on operator dashboard"
    assert 'test_op_somchai' in html or 'สมชาย' in html, "Operator name not rendered on dashboard"
    print("[PASS] 9. Approved operator logged in successfully and accessed Operator Dashboard!")

    # 9. Test Reject Flow
    client.get('/logout')
    # Register another operator to test reject
    client.post('/register_operator', data={
        'username': 'test_op_reject',
        'password': 'password123',
        'confirm_password': 'password123',
        'position': 'กรรมการทั่วไป',
        'prefix': 'นาย',
        'first_name': 'ทดสอบ',
        'last_name': 'ปฏิเสธ',
        'student_id': '663050888-8',
        'faculty': 'ศึกษาศาสตร์',
        'academic_year': 'ปี 2',
        'kku_mail': 'reject@kkumail.com',
        'phone': '0811111111'
    }, follow_redirects=True)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username='test_op_reject'")
    rej_user = c.fetchone()
    conn.close()
    assert rej_user is not None
    rej_id = rej_user['id']

    # Login god
    client.post('/', data={
        'username': 'KoldP',
        'password': '1987',
        'role': 'god',
        'secret_god_mode': 'activated'
    })
    # God rejects
    res = client.post('/god', data={
        'action': 'reject_operator',
        'user_id': rej_id
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'ปฏิเสธและลบคำขอลงทะเบียนกรรมการเรียบร้อยแล้ว' in html
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (rej_id,))
    assert c.fetchone() is None, "Rejected user was not removed"
    conn.close()
    print("[PASS] 10. Reject flow successfully verified (request removed cleanly)")

    # Clean up test operator
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username='test_op_somchai'")
    conn.commit()
    conn.close()

    print("==================================================")
    print("ALL 10 TESTS PASSED SUCCESSFULLY! WORKFLOW VERIFIED.")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
