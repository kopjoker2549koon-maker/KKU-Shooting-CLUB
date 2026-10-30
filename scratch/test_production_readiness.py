import os
import sys
import sqlite3

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, get_db

client = app.test_client()

print("==================================================================")
print("TEST: PRODUCTION READINESS & PUBLISH AUDIT")
print("==================================================================")

# 1. Verify Secret Key & Security Config
print("\n--- 1. Security & Configuration Audit ---")
assert app.secret_key and len(app.secret_key) >= 16, "Insecure secret key!"
assert os.path.exists('.secret_key'), "Persistent .secret_key file missing!"
assert app.config.get('MAX_CONTENT_LENGTH') == 16 * 1024 * 1024, "MAX_CONTENT_LENGTH not set!"
assert app.config.get('SESSION_COOKIE_HTTPONLY') is True, "SESSION_COOKIE_HTTPONLY not enabled!"
assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax', "SESSION_COOKIE_SAMESITE not Lax!"
print("[PASS] Secret key persistent, session cookies secured, upload limits enforced.")

# 2. Verify Database WAL Concurrency Mode
print("\n--- 2. Database Engine & Concurrency Audit ---")
conn = get_db()
c = conn.cursor()
c.execute("PRAGMA journal_mode;")
journal_mode = c.fetchone()[0]
assert journal_mode.lower() == 'wal', f"Expected WAL mode, got: {journal_mode}"
c.execute("PRAGMA foreign_keys;")
fk = c.fetchone()[0]
assert fk == 1, "Foreign keys not enforced!"
conn.close()
print(f"[PASS] SQLite WAL mode confirmed: '{journal_mode.upper()}' (High concurrency read/write ready).")

# 3. Verify Custom 404 & 500 Templates
print("\n--- 3. Custom Error Pages Audit ---")
r_404 = client.get('/non_existent_page_12345')
assert r_404.status_code == 404
assert b'404' in r_404.data
assert 'ไม่พบหน้าที่ท่านต้องการ' in r_404.data.decode('utf-8')
print("[PASS] Custom 404 page rendered beautifully with club branding.")

assert os.path.exists('templates/500.html')
with open('templates/500.html', 'r', encoding='utf-8') as f:
    h500 = f.read()
    assert 'ระบบเกิดข้อผิดพลาดชั่วคราว' in h500
print("[PASS] Custom 500 error template verified.")

# 4. Verify God Admin Database Backup API
print("\n--- 4. Database Online Backup Snapshot Audit ---")
# Unauthorized access blocked
r_unauth = client.get('/god/backup_db')
assert r_unauth.status_code == 302, "Unauthenticated backup must be redirected!"

# God admin authorized backup
with client.session_transaction() as sess:
    sess['user_id'] = 5
    sess['username'] = 'KoldP'
    sess['role'] = 'god'

r_backup = client.get('/god/backup_db')
assert r_backup.status_code == 200, f"Expected 200, got: {r_backup.status_code}"
assert r_backup.headers.get('Content-Disposition', '').startswith('attachment;')
assert len(r_backup.data) > 1000, "Backup file is empty!"
print(f"[PASS] Online SQLite backup snapshot succeeded! Size: {len(r_backup.data)} bytes.")

# 5. Verify Gun Safety Agreement in Registration Templates
print("\n--- 5. Gun Safety Agreement & Rules Audit ---")
r_reg = client.get('/register')
assert 'กฎความปลอดภัย 4 ประการแห่งการใช้อาวุธปืน' in r_reg.data.decode('utf-8')
assert 'safetyCheck' in r_reg.data.decode('utf-8')
print("[PASS] Member Registration includes Gun Safety Agreement checkbox.")

r_op_reg = client.get('/register_operator')
assert 'ข้อตกลงและหน้าที่รับผิดชอบความปลอดภัยของกรรมการสนาม' in r_op_reg.data.decode('utf-8')
assert 'opSafetyCheck' in r_op_reg.data.decode('utf-8')
print("[PASS] Operator Registration includes Staff Safety Duties acknowledgment.")

# 6. Verify Production Server Scripts
print("\n--- 6. Production Launcher & Documentation Audit ---")
assert os.path.exists('run.py'), "Missing run.py!"
assert os.path.exists('start_server.bat'), "Missing start_server.bat!"
assert os.path.exists('requirements.txt'), "Missing requirements.txt!"
assert os.path.exists('README.md'), "Missing README.md!"

import waitress
import importlib.metadata
waitress_ver = importlib.metadata.version('waitress')
assert hasattr(waitress, 'serve'), "Waitress WSGI serve ready."
print(f"[PASS] Waitress version {waitress_ver} verified. run.py and start_server.bat ready.")

# 7. Verify PWA & Offline Range Assets
print("\n--- 7. PWA & Offline Range Assets Audit ---")
assert os.path.exists('static/manifest.json')
assert os.path.exists('static/sw.js')
with open('static/sw.js', 'r', encoding='utf-8') as f:
    sw_code = f.read()
    assert 'cropper.min.js' in sw_code
    assert 'html5-qrcode.min.js' in sw_code
    assert 'qrcode.min.js' in sw_code
print("[PASS] Service Worker caches all critical range and cropper offline libraries.")

print("\n==================================================================")
print(">>> ALL 7 PRODUCTION READINESS AUDIT CHECKS PASSED 100%! <<<")
print("==================================================================")
