import os
import sys
import sqlite3

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, get_db

client = app.test_client()

print("==================================================")
print("TEST: INLINE FORM CORRECTION & FIELD RETENTION")
print("==================================================")

# Pre-clean test accounts
conn = get_db()
c = conn.cursor()
c.execute("DELETE FROM users WHERE username IN ('test_inline_ok_01', 'test_inline_op_01')")
conn.commit()
conn.close()

# --- 1. Testing Login Form ---
print("\n--- 1. Testing Login Form ---")

# 1.1 Wrong password via standard POST: username must be retained in HTML
r_login_post = client.post('/login', data={'username': 'member1', 'password': 'wrongpassword_999'}, follow_redirects=True)
html_login = r_login_post.data.decode('utf-8')
assert 'member1' in html_login, "Username was NOT retained in login HTML!"
assert 'รหัสผ่านไม่ถูกต้อง' in html_login
print("[PASS] Standard POST login failure preserves entered username in HTML.")

# 1.2 Wrong password via AJAX: JSON returned with field='password'
r_login_ajax = client.post('/login', data={'username': 'member1', 'password': 'wrongpassword_999'}, headers={'X-Requested-With': 'XMLHttpRequest'})
assert r_login_ajax.status_code == 200
data = r_login_ajax.get_json()
assert data['success'] is False
assert data['field'] == 'password'
assert 'รหัสผ่านไม่ถูกต้อง' in data['message']
print(f"[PASS] AJAX login failure returned targeted error: field='{data['field']}', message='{data['message']}'")

# 1.3 Non-existent user via AJAX: field='username'
r_user_ajax = client.post('/login', data={'username': 'non_existing_user_99', 'password': '123'}, headers={'X-Requested-With': 'XMLHttpRequest'})
data_user = r_user_ajax.get_json()
assert data_user['success'] is False
assert data_user['field'] == 'username'
print(f"[PASS] Non-existent user login returned field='{data_user['field']}' for inline correction.")

# 1.4 Valid login via AJAX: success=True, redirect provided
r_valid_ajax = client.post('/login', data={'username': 'member1', 'password': '123'}, headers={'X-Requested-With': 'XMLHttpRequest'})
data_valid = r_valid_ajax.get_json()
assert data_valid['success'] is True
assert data_valid['redirect'] == '/member'
print(f"[PASS] Valid login via AJAX returned redirect: '{data_valid['redirect']}'")

# --- 2. Testing Member Registration Form ---
print("\n--- 2. Testing Member Registration Form ---")

sample_member = {
    'username': 'test_inline_mem_01',
    'password': 'password123',
    'prefix': 'นาย',
    'first_name': 'สมหมาย',
    'last_name': 'ใจดี',
    'faculty': 'วิศวกรรมศาสตร์',
    'academic_year': '3',
    'kku_mail': 'sommai.j@gmail.com', # Invalid: not @kkumail.com
    'student_id': '6530409991',       # Invalid: missing dash
    'phone': '0891112233'
}

# 2.1 Missing dash in student_id via standard POST: form_data retained in HTML
r_reg_dash = client.post('/register', data=sample_member)
html_reg_dash = r_reg_dash.data.decode('utf-8')
assert 'test_inline_mem_01' in html_reg_dash
assert 'สมหมาย' in html_reg_dash
assert 'ใจดี' in html_reg_dash
assert 'วิศวกรรมศาสตร์' in html_reg_dash
assert '0891112233' in html_reg_dash
assert 'กรุณากรอกรหัสนักศึกษาให้อยู่ในรูปแบบที่มีขีด' in html_reg_dash
print("[PASS] Registration failure with missing dash retains all form inputs without losing data.")

# 2.2 Missing dash via AJAX: field='student_id'
r_reg_ajax_dash = client.post('/register', data=sample_member, headers={'X-Requested-With': 'XMLHttpRequest'})
data_dash = r_reg_ajax_dash.get_json()
assert data_dash['success'] is False
assert data_dash['field'] == 'student_id'
print(f"[PASS] AJAX registration missing dash returned field='{data_dash['field']}'")

# 2.3 Invalid email via AJAX: field='kku_mail'
sample_member['student_id'] = '653040999-1' # Fixed dash
r_reg_ajax_mail = client.post('/register', data=sample_member, headers={'X-Requested-With': 'XMLHttpRequest'})
data_mail = r_reg_ajax_mail.get_json()
assert data_mail['success'] is False
assert data_mail['field'] == 'kku_mail'
print(f"[PASS] AJAX registration invalid email returned field='{data_mail['field']}'")

# 2.4 Duplicate username via AJAX: field='username'
sample_member['kku_mail'] = 'sommai.j@kkumail.com' # Fixed mail
sample_member['username'] = 'member1'             # Already exists!
r_reg_ajax_dup = client.post('/register', data=sample_member, headers={'X-Requested-With': 'XMLHttpRequest'})
data_dup = r_reg_ajax_dup.get_json()
assert data_dup['success'] is False
assert data_dup['field'] == 'username'
print(f"[PASS] AJAX registration duplicate username returned field='{data_dup['field']}'")

# 2.5 Valid registration via AJAX: success=True, redirect='/login'
sample_member['username'] = 'test_inline_ok_01'
r_reg_ok = client.post('/register', data=sample_member, headers={'X-Requested-With': 'XMLHttpRequest'})
data_ok = r_reg_ok.get_json()
assert data_ok['success'] is True
assert data_ok['redirect'] == '/login'
print(f"[PASS] Valid registration via AJAX succeeded with redirect: '{data_ok['redirect']}'")

# --- 3. Testing Operator Registration Form ---
print("\n--- 3. Testing Operator Registration Form ---")

sample_op = {
    'username': 'test_inline_op_01',
    'password': 'password123',
    'confirm_password': 'mismatch_password_999',
    'position': 'ฝ่ายพัสดุ',
    'prefix': 'นาย',
    'first_name': 'ธีระ',
    'last_name': 'มั่นคง',
    'faculty': 'วิทยาลัยการคอมพิวเตอร์',
    'academic_year': 'ปี 4',
    'kku_mail': 'teera.m@kkumail.com',
    'student_id': '653040888-2',
    'phone': '0894445566'
}

# 3.1 Password mismatch via AJAX: field='confirm_password'
r_op_mismatch = client.post('/register_operator', data=sample_op, headers={'X-Requested-With': 'XMLHttpRequest'})
data_op_mis = r_op_mismatch.get_json()
assert data_op_mis['success'] is False
assert data_op_mis['field'] == 'confirm_password'
print(f"[PASS] AJAX operator registration password mismatch returned field='{data_op_mis['field']}'")

# 3.2 Password mismatch via standard POST: all fields retained in HTML
r_op_post = client.post('/register_operator', data=sample_op)
html_op = r_op_post.data.decode('utf-8')
assert 'test_inline_op_01' in html_op
assert 'ธีระ' in html_op
assert 'มั่นคง' in html_op
assert 'วิทยาลัยการคอมพิวเตอร์' in html_op
assert '0894445566' in html_op
assert 'รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน' in html_op
print("[PASS] Operator registration failure retains all input values in HTML.")

# 3.3 Valid operator registration via AJAX
sample_op['confirm_password'] = 'password123'
r_op_ok = client.post('/register_operator', data=sample_op, headers={'X-Requested-With': 'XMLHttpRequest'})
data_op_ok = r_op_ok.get_json()
assert data_op_ok['success'] is True
assert '/login' in data_op_ok['redirect']
print(f"[PASS] Valid operator registration succeeded with redirect: '{data_op_ok['redirect']}'")

# --- 4. Testing Forgot Password Identifier Retention ---
print("\n--- 4. Testing Forgot Password Form ---")
r_forgot = client.post('/forgot_password', data={'identifier': 'unknown_student_99@kkumail.com'})
html_forgot = r_forgot.data.decode('utf-8')
assert r_forgot.status_code == 200
assert 'unknown_student_99@kkumail.com' in html_forgot
print("[PASS] Forgot password failure preserves entered identifier in input field.")

# Clean up test accounts
conn = get_db()
c = conn.cursor()
c.execute("DELETE FROM users WHERE username IN ('test_inline_ok_01', 'test_inline_op_01')")
conn.commit()
conn.close()

print("\n==================================================")
print(">>> ALL TESTS PASSED! INLINE CORRECTION VERIFIED! <<<")
print("==================================================")
