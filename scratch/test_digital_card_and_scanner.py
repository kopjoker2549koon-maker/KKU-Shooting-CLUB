import os
import sys
import sqlite3
import json

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from werkzeug.security import generate_password_hash

client = app.test_client()

print("==================================================")
print("TEST: DIGITAL MEMBER CARD, PWA, AND RANGE SCANNER")
print("==================================================")

# 1. Test PWA Endpoints
print("\n--- 1. Testing PWA Manifest & Service Worker ---")
r_manifest = client.get('/manifest.json')
assert r_manifest.status_code == 200, f"Expected 200, got {r_manifest.status_code}"
manifest_data = json.loads(r_manifest.data.decode('utf-8'))
assert manifest_data.get('short_name') == 'KKU Shoot'
assert manifest_data.get('display') == 'standalone'
assert len(manifest_data.get('icons', [])) >= 2
print("[PASS] PWA manifest.json is valid and properly configured.")

r_sw = client.get('/sw.js')
assert r_sw.status_code == 200, f"Expected 200, got {r_sw.status_code}"
assert b'kku-shooting-club' in r_sw.data
print("[PASS] Service Worker /sw.js is accessible.")

# Check icons exist
assert os.path.exists('static/icons/icon-192.png'), "Missing icon-192.png"
assert os.path.exists('static/icons/icon-512.png'), "Missing icon-512.png"
assert os.path.exists('static/icons/apple-touch-icon.png'), "Missing apple-touch-icon.png"
assert os.path.exists('static/qrcode.min.js'), "Missing local qrcode.min.js"
assert os.path.exists('static/html5-qrcode.min.js'), "Missing local html5-qrcode.min.js"
print("[PASS] All PWA app icons and offline scanner libraries verified in static/.")

# 2. Test Digital Membership Card for Member
print("\n--- 2. Testing Digital Membership Card (/member/card) ---")
# Setup member1
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("""
    UPDATE users 
    SET password = ?, status = 'approved', prefix = 'นาย', first_name = 'สมชาย', last_name = 'รักชาติ', student_id = '653040111-2', faculty = 'วิทยาลัยการคอมพิวเตอร์', academic_year = '3', kku_mail = 'member1@kkumail.com'
    WHERE username = 'member1'
""", (generate_password_hash('123'),))

# Ensure member1 has some ammo in user_ammo
c.execute("INSERT OR REPLACE INTO user_ammo (user_id, ammo_type, quantity) VALUES (9, '.22 LR (RWS)', 150)")
c.execute("INSERT OR REPLACE INTO user_ammo (user_id, ammo_type, quantity) VALUES (9, 'เป้าปืนยาว', 10)")
conn.commit()
conn.close()

# Login as member1
login_res = client.post('/', data={'username': 'member1', 'password': '123', 'role': 'member'}, follow_redirects=True)
assert login_res.status_code == 200

# Access /member/card
r_card = client.get('/member/card')
assert r_card.status_code == 200
card_html = r_card.data.decode('utf-8')
assert 'บัตรสมาชิกดิจิทัล' in card_html
assert 'สมชาย' in card_html and 'รักชาติ' in card_html
assert '653040111-2' in card_html
assert 'KKU-SC-0009' in card_html or 'KKU-SC:' in card_html
assert 'cardQrContainer' in card_html
assert 'fullscreenQrOverlay' in card_html
assert '.22 LR (RWS)' in card_html
print("[PASS] /member/card rendered successfully with member details, scannable QR container, and wallet balance.")

# Access /member to ensure link to card is present
r_member = client.get('/member')
assert r_member.status_code == 200
member_html = r_member.data.decode('utf-8')
assert '/member/card' in member_html
assert 'บัตรสมาชิกดิจิทัล' in member_html
print("[PASS] /member dashboard contains direct link to Digital Membership Card in navbar and drawer.")

# 3. Test Operator Range Scanner & Counter API
print("\n--- 3. Testing Operator Range Scanner API (/api/member_lookup) ---")
client.get('/logout')

# Unauthenticated access to API should be blocked
r_unauth = client.get('/api/member_lookup?query=member1')
assert r_unauth.status_code == 403
print("[PASS] Unauthenticated access to /api/member_lookup correctly blocked (403).")

# Login as Operator op1
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("UPDATE users SET password = ?, status = 'approved' WHERE username = 'op1'", (generate_password_hash('123'),))
conn.commit()
conn.close()

r_op_login = client.post('/', data={'username': 'op1', 'password': '123', 'role': 'operator'}, follow_redirects=True)
assert r_op_login.status_code == 200

# Lookup by username
r_lookup_user = client.get('/api/member_lookup?query=member1')
assert r_lookup_user.status_code == 200
data_user = json.loads(r_lookup_user.data.decode('utf-8'))
assert data_user['success'] is True
assert data_user['member']['username'] == 'member1'
assert data_user['member']['student_id'] == '653040111-2'
assert len(data_user['member']['wallet']) >= 1
print("[PASS] Lookup by username 'member1' returned full profile and ammo wallet.")

# Lookup by QR code format (KKU-SC:MEMBER:9:653040111-2)
r_lookup_qr = client.get('/api/member_lookup?query=KKU-SC:MEMBER:9:653040111-2')
assert r_lookup_qr.status_code == 200
data_qr = json.loads(r_lookup_qr.data.decode('utf-8'))
assert data_qr['success'] is True
assert data_qr['member']['id'] == 9
print("[PASS] Lookup by scannable QR Code payload returned member successfully.")

# Lookup by student ID
r_lookup_std = client.get('/api/member_lookup?query=653040111-2')
assert r_lookup_std.status_code == 200
data_std = json.loads(r_lookup_std.data.decode('utf-8'))
assert data_std['success'] is True
print("[PASS] Lookup by student ID '653040111-2' returned member successfully.")

# Lookup non-existent member
r_lookup_none = client.get('/api/member_lookup?query=not_a_member_999')
assert r_lookup_none.status_code == 404
print("[PASS] Non-existent member query returns 404 cleanly.")

# 4. Test Quick Range Withdraw Counter API (/api/range_quick_withdraw)
print("\n--- 4. Testing Quick Range Ammo Withdraw API ---")
# Check starting balance for member1 (id=9)
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT quantity FROM user_ammo WHERE user_id = 9 AND ammo_type = '.22 LR (RWS)'")
bal_before = c.fetchone()[0]
conn.close()

# Withdraw valid amount (e.g. 50 rounds)
r_withdraw = client.post('/api/range_quick_withdraw', data={
    'member_id': '9',
    'ammo_type': '.22 LR (RWS)',
    'amount': '50',
    'lane_no': 'ช่องยิงที่ 4'
})
assert r_withdraw.status_code == 200
w_data = json.loads(r_withdraw.data.decode('utf-8'))
assert w_data['success'] is True
assert 'เรียบร้อย' in w_data['message']

# Verify DB balance deducted by 50
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT quantity FROM user_ammo WHERE user_id = 9 AND ammo_type = '.22 LR (RWS)'")
bal_after = c.fetchone()[0]
assert bal_after == bal_before - 50, f"Expected {bal_before - 50}, got {bal_after}"

# Verify transaction logged
c.execute("SELECT action, amount, note FROM transactions WHERE user_id = 9 ORDER BY id DESC LIMIT 1")
tx = c.fetchone()
conn.close()
assert tx[0] == 'Withdraw'
assert tx[1] == 50
assert 'ช่องยิงที่ 4' in tx[2]
print(f"[PASS] Range quick withdraw succeeded: balance deducted from {bal_before} to {bal_after}, transaction logged with lane info.")

# Test excessive withdraw (attempting to withdraw 500 when only 100 remains)
r_withdraw_fail = client.post('/api/range_quick_withdraw', data={
    'member_id': '9',
    'ammo_type': '.22 LR (RWS)',
    'amount': '500',
    'lane_no': 'ช่องยิงที่ 1'
})
assert r_withdraw_fail.status_code == 400
w_fail_data = json.loads(r_withdraw_fail.data.decode('utf-8'))
assert w_fail_data['success'] is False
assert 'ไม่พอสำหรับการเบิก' in w_fail_data['message']
print("[PASS] Excessive range withdraw correctly rejected with error message.")

# 5. Check Operator Interface UI elements
print("\n--- 5. Verifying Operator Interface & Scanner Controls ---")
r_op_page = client.get('/operator')
assert r_op_page.status_code == 200
op_page_html = r_op_page.data.decode('utf-8')
assert 'rangeScannerModal' in op_page_html
assert 'html5-qrcode.min.js' in op_page_html
assert 'openRangeScannerModal' in op_page_html
assert 'btnModeCamera' in op_page_html
assert 'manualSearchInput' in op_page_html
assert 'submitQuickRangeWithdraw' in op_page_html
print("[PASS] Operator Console includes Range Scanner modal, camera viewfinder, manual barcode search, and dispense panel.")

print("\n==================================================")
print(">>> ALL TESTS PASSED! DIGITAL CARD, PWA, AND RANGE SCANNER VERIFIED! <<<")
print("==================================================")
