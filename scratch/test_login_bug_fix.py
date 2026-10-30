import os
import sys
import sqlite3

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

client = app.test_client()

print("==================================================")
print("TEST: COMPREHENSIVE LOGIN BUG FIX VERIFICATION")
print("==================================================")

cases = [
    # Username, Password, Role sent from form, Expected Redirect / Access
    ("member1", "123", "member", "/member"),
    ("member1 ", "123", "member", "/member"),
    ("Member1", "123", "member", "/member"),
    ("member1", "123 ", "member", "/member"),
    ("member1@kkumail.com", "123", "member", "/member"),
    ("653040111-2", "123", "member", "/member"),
    ("member1", "1234", "member", "/member"),  # Demo hint
    ("op1", "123", "operator", "/operator"),
    ("op1", "1", "operator", "/operator"),      # Demo hint
    ("op1", "123", "member", "/operator"),      # Logged in from member tab -> auto routes to /operator!
    ("admin", "admin123", "member", "/god"),    # Admin from default tab -> auto routes to /god!
    ("admin", "123", "member", "/god"),        # Admin with 123 -> auto routes to /god!
    ("god", "123", "god", "/god"),
    ("god", "god123", "member", "/god"),
    ("KoldP", "1987", "god", "/god"),
    ("KoldP", "1987", "member", "/god"),       # KoldP from default member tab
]

all_passed = True
for idx, (u, p, r, expected_loc) in enumerate(cases, 1):
    client.get('/logout')
    res = client.post('/', data={'username': u, 'password': p, 'role': r}, follow_redirects=False)
    loc = res.headers.get('Location', '')
    ok = (res.status_code == 302 and loc == expected_loc)
    print(f"[{'PASS' if ok else 'FAIL'}] {idx:2d}. User '{u}' | Pwd '{p}' | Role '{r}' -> Status {res.status_code}, Redirect to: '{loc}' (Expected: '{expected_loc}')")
    if not ok:
        all_passed = False

# Test invalid password
print("\n--- Testing Invalid Password ---")
client.get('/logout')
res_bad_pwd = client.post('/', data={'username': 'member1', 'password': 'completely_wrong_password_999', 'role': 'member'}, follow_redirects=True)
bad_html = res_bad_pwd.data.decode('utf-8')
assert 'รหัสผ่านไม่ถูกต้อง' in bad_html
print("[PASS] Invalid password correctly shows: 'รหัสผ่านไม่ถูกต้อง'")

# Test non-existent user
print("\n--- Testing Non-existent User ---")
client.get('/logout')
res_no_user = client.post('/', data={'username': 'user_does_not_exist_at_all_999', 'password': 'any', 'role': 'member'}, follow_redirects=True)
no_user_html = res_no_user.data.decode('utf-8')
assert 'ไม่พบบัญชีผู้ใช้งานนี้ในระบบ' in no_user_html
print("[PASS] Non-existent user correctly shows: 'ไม่พบบัญชีผู้ใช้งานนี้ในระบบ'")

assert all_passed, "Some login test cases failed!"
print("\n==================================================")
print(">>> ALL 16 LOGIN SCENARIOS PASSED 100%! BUG RESOLVED! <<<")
print("==================================================")
