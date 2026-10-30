import sys
import os
import sqlite3

# Set utf-8 output encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=== Running Verification Test: Password Hashing & Executive Back-Office Dashboard ===")

# 1. Inspect DB directly to verify password hashes
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username, password, role, status FROM users")
users = c.fetchall()
conn.close()

print(f"\n1. Direct Database Inspection (Found {len(users)} users):")
all_hashed = True
for uid, u, p, r, s in users:
    is_hash = p.startswith('scrypt:') or p.startswith('pbkdf2:')
    status_str = "HASHED" if is_hash else "PLAINTEXT (FAIL!)"
    print(f"  - [{uid}] {u:15} | Role: {r:10} | Status: {s:10} | Password: {p[:20]}... -> {status_str}")
    if not is_hash:
        all_hashed = False

assert all_hashed, "Found unhashed plaintext password in database!"
print(">>> Check 1 Passed: 100% of user passwords in database are cryptographically hashed.")

# 2. Test Flask app using test_client
from app import app
client = app.test_client()

print("\n2. Testing Authentication with Hashed Passwords:")
# Test login with god admin (KoldP / 1987)
res = client.post('/', data={'username': 'KoldP', 'password': '1987', 'role': 'god'}, follow_redirects=True)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert b'GOD' in res.data or b'Executive' in res.data or b'Control Center' in res.data or b'god' in res.data.lower()
print("  - Logged in as 'KoldP' (God Admin) successfully using hashed password verification.")

# 3. Test Accessing /god Dashboard
print("\n3. Testing Executive Dashboard (/god):")
res = client.get('/god')
assert res.status_code == 200
html = res.data.decode('utf-8')

# Verify KPI Stat Cards
assert 'สมาชิกชมรมทั้งหมด' in html, "Missing member count KPI"
assert 'ยอดรายรับสะสม' in html, "Missing revenue KPI"
assert 'ยอดคงเหลือพัสดุและกระสุนในคลังกลาง' in html, "Missing inventory section"
assert '/god/export_members' in html, "Missing member export button"
assert 'ทำเนียบคณะกรรมการและเจ้าหน้าที่คลัง' in html, "Missing operator management section"
assert 'ทำเนียบสมาชิกและกระเป๋ากระสุน' in html, "Missing member database section"
print("  - Executive Dashboard (/god) rendered with all KPI cards, stock status, committee roster, and member database.")

# 4. Test Export Members to CSV / Excel
print("\n4. Testing Member CSV/Excel Export (/god/export_members):")
export_res = client.get('/god/export_members')
assert export_res.status_code == 200
assert export_res.headers['Content-Type'].startswith('text/csv')
csv_content = export_res.data
assert csv_content.startswith(b'\xef\xbb\xbf'), "Missing UTF-8 BOM for Microsoft Excel Thai compatibility"
csv_text = csv_content.decode('utf-8')
print("  - CSV Header preview:")
print("   ", csv_text.splitlines()[0])
assert 'ชื่อผู้ใช้' in csv_text and 'รหัสนักศึกษา' in csv_text and 'KKU Mail' in csv_text
print("  - Exported CSV includes UTF-8 BOM and correct column headers for university reporting.")

# 5. Test Operator Registration with Hashing and God Approval
print("\n5. Testing New Operator Registration & God Approval:")
test_op_user = 'test_eval_op'
test_op_email = 'test_eval_op@kkumail.com'
test_op_pass = 'Secr3t#Pass'

# Clean up if existed
conn = sqlite3.connect('shooting_club.db')
conn.execute("DELETE FROM users WHERE username=?", (test_op_user,))
conn.commit()
conn.close()

# Register operator
reg_res = client.post('/register_operator', data={
    'username': test_op_user,
    'password': test_op_pass,
    'confirm_password': test_op_pass,
    'name': 'นายผู้ประเมิน ทดสอบ',
    'student_id': '653040999-9',
    'kku_mail': test_op_email,
    'phone': '0899999999',
    'position': 'ฝ่ายเทคโนโลยี',
    'faculty': 'วิทยาลัยการคอมพิวเตอร์'
}, follow_redirects=True)
assert reg_res.status_code == 200

# Check DB has hashed password and pending status
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, password, status, position FROM users WHERE username=?", (test_op_user,))
op_row = c.fetchone()
conn.close()

assert op_row is not None
op_id, op_pwd_hash, op_status, op_pos = op_row
assert op_pwd_hash.startswith('scrypt:'), "Operator password was not hashed with scrypt"
assert op_status == 'pending', f"Operator status should be pending, got {op_status}"
assert op_pos == 'ฝ่ายเทคโนโลยี'
print(f"  - Operator registered with pending status, position 'ฝ่ายเทคโนโลยี', and hashed password: {op_pwd_hash[:25]}...")

# God approves operator
approve_res = client.post('/god', data={
    'action': 'approve_operator',
    'user_id': op_id
}, follow_redirects=True)
assert approve_res.status_code == 200

# Verify status is approved
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT status FROM users WHERE id=?", (op_id,))
new_status = c.fetchone()[0]
conn.close()
assert new_status == 'approved'
print(f"  - God approved operator id={op_id}. Status updated to: {new_status}.")

# Log out and test login as approved operator
client.get('/logout')
op_login_res = client.post('/', data={'username': test_op_user, 'password': test_op_pass, 'role': 'operator'}, follow_redirects=True)
assert op_login_res.status_code == 200
assert b'Operator' in op_login_res.data or b'\xe0\xb8\x81\xe0\xb8\xa3\xe0\xb8\xa3\xe0\xb8\xa1\xe0\xb8\x81\xe0\xb8\xb2\xe0\xb8\xa3' in op_login_res.data
print("  - Operator successfully logged into Operator Console using hashed password.")

# Clean up test operator
conn = sqlite3.connect('shooting_club.db')
conn.execute("DELETE FROM users WHERE username=?", (test_op_user,))
conn.commit()
conn.close()

print("\n=======================================================")
print(">>> ALL TESTS PASSED! PASSWORD HASHING & GOD DASHBOARD FULLY VERIFIED! <<<")
print("=======================================================")
