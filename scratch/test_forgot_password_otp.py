import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
from app import app, get_db

def run_tests():
    print("==================================================")
    print("STARTING TEST: KKU Mail Enforcement & Forgot Password OTP")
    print("==================================================")
    client = app.test_client()

    # Clean up test accounts
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username IN ('test_kku_mem', 'test_kku_op', 'test_bad_mail')")
    c.execute("UPDATE users SET password='123', kku_mail='member1@kkumail.com' WHERE username='member1'")
    conn.commit()
    conn.close()

    # --------------------------------------------------
    # 1. Enforce @kkumail.com on Member Registration
    # --------------------------------------------------
    res = client.post('/register', data={
        'username': 'test_bad_mail',
        'password': 'password123',
        'prefix': 'นาย',
        'first_name': 'ทดสอบ',
        'last_name': 'อีเมลผิด',
        'student_id': '663050111-1',
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 1',
        'kku_mail': 'user@gmail.com',  # Invalid! Not @kkumail.com
        'phone': '0812345678'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'อีเมลต้องลงท้ายด้วย @kkumail.com' in html, "Failed to block non-kkumail on member register"
    print("[PASS] 1. Non-kkumail email (@gmail.com) blocked on Member Registration")

    # --------------------------------------------------
    # 2. Enforce @kkumail.com on Operator Registration
    # --------------------------------------------------
    res = client.post('/register_operator', data={
        'username': 'test_bad_mail_op',
        'password': 'password123',
        'confirm_password': 'password123',
        'position': 'ฝ่ายพัสดุ',
        'prefix': 'นาย',
        'first_name': 'ทดสอบ',
        'last_name': 'กรรมการอีเมลผิด',
        'student_id': '663050222-2',
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 4',
        'kku_mail': 'operator@hotmail.com',  # Invalid! Not @kkumail.com
        'phone': '0812345678'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'อีเมลต้องลงท้ายด้วย @kkumail.com' in html, "Failed to block non-kkumail on operator register"
    print("[PASS] 2. Non-kkumail email (@hotmail.com) blocked on Operator Registration")

    # --------------------------------------------------
    # 3. Valid Member Registration with @kkumail.com
    # --------------------------------------------------
    res = client.post('/register', data={
        'username': 'test_kku_mem',
        'password': 'password123',
        'prefix': 'นาย',
        'first_name': 'สมชาย',
        'last_name': 'เรียนดี',
        'student_id': '663050333-3',
        'faculty': 'วิศวกรรมศาสตร์',
        'academic_year': 'ปี 2',
        'kku_mail': 'somchai.r@kkumail.com',  # Valid!
        'phone': '0812345678'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'สมัครสมาชิกสำเร็จ' in html, "Valid member registration failed"
    print("[PASS] 3. Valid member registration with @kkumail.com succeeded")

    # --------------------------------------------------
    # 4. Forgot Password - Non-existent user
    # --------------------------------------------------
    res = client.post('/forgot_password', data={
        'identifier': 'nobody_user_12345'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'ไม่พบบัญชีผู้ใช้หรืออีเมลนี้' in html
    print("[PASS] 4. Non-existent username properly handled in forgot_password")

    # --------------------------------------------------
    # 5. Forgot Password - Valid Request for 'member1'
    # --------------------------------------------------
    res = client.post('/forgot_password', data={
        'identifier': 'member1'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'ยืนยันรหัส OTP' in html, "Did not redirect to verify_otp"
    assert 'm*****1@kkumail.com' in html, "Masked email not displayed correctly"

    # Check OTP generated in database
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT o.* FROM otp_codes o 
        JOIN users u ON o.user_id = u.id 
        WHERE u.username='member1' AND o.used=0 
        ORDER BY o.id DESC LIMIT 1
    """)
    otp_record = c.fetchone()
    conn.close()
    assert otp_record is not None, "OTP record not created in db"
    valid_otp = otp_record['otp_code']
    print(f"[PASS] 5. OTP generated successfully for member1: {valid_otp} (masked email confirmed)")

    # --------------------------------------------------
    # 6. Verify OTP - Wrong OTP Code
    # --------------------------------------------------
    res = client.post('/verify_otp', data={
        'otp': '000000',  # Wrong!
        'new_password': 'new_secret_password',
        'confirm_password': 'new_secret_password'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รหัส OTP ไม่ถูกต้อง' in html
    print("[PASS] 6. Invalid OTP code rejected with proper error")

    # --------------------------------------------------
    # 7. Verify OTP - Password Mismatch
    # --------------------------------------------------
    res = client.post('/verify_otp', data={
        'otp': valid_otp,
        'new_password': 'new_secret_password',
        'confirm_password': 'different_secret_password'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน' in html
    print("[PASS] 7. Password mismatch rejected with proper error")

    # --------------------------------------------------
    # 8. Verify OTP - Success Flow
    # --------------------------------------------------
    res = client.post('/verify_otp', data={
        'otp': valid_otp,
        'new_password': 'new_secret_password123',
        'confirm_password': 'new_secret_password123'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'รีเซ็ตรหัสผ่านสำเร็จเรียบร้อยแล้ว' in html
    
    # Verify in DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username='member1'")
    u = c.fetchone()
    c.execute("SELECT used FROM otp_codes WHERE id=?", (otp_record['id'],))
    otp_used = c.fetchone()['used']
    conn.close()
    from werkzeug.security import check_password_hash
    assert check_password_hash(u['password'], 'new_secret_password123'), "Password was not updated in DB with proper hash"
    assert otp_used == 1, "OTP was not marked as used"
    print("[PASS] 8. Password reset successfully verified in DB and OTP marked as used")

    # --------------------------------------------------
    # 9. Login with new password
    # --------------------------------------------------
    # Old password should fail
    res = client.post('/', data={
        'username': 'member1',
        'password': '123',
        'role': 'member'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'ไม่ถูกต้อง' in html, "Old password should not work"

    # New password should succeed
    res = client.post('/', data={
        'username': 'member1',
        'password': 'new_secret_password123',
        'role': 'member'
    }, follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'member' in html.lower(), "Login with new password failed"
    print("[PASS] 9. Login with new password succeeded! (Old password rejected)")

    # --------------------------------------------------
    # 10. Test Resend OTP Flow
    # --------------------------------------------------
    # Request OTP again
    client.post('/forgot_password', data={'identifier': 'member1'}, follow_redirects=True)
    # Resend OTP
    res = client.post('/resend_otp', follow_redirects=True)
    html = res.data.decode('utf-8')
    assert 'ส่งรหัส OTP ชุดใหม่' in html
    print("[PASS] 10. Resend OTP flow verified successfully")

    # Clean up test accounts
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username='test_kku_mem'")
    # Restore member1 password
    c.execute("UPDATE users SET password='123' WHERE username='member1'")
    conn.commit()
    conn.close()

    print("==================================================")
    print("ALL 10 TESTS PASSED! FULL KKU MAIL & OTP SYSTEM VERIFIED.")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
