import sqlite3
import urllib.request
import urllib.parse
import http.cookiejar
from PIL import Image
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')

print('=== 1. Checking Database Records ===')
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()

# Check Users
c.execute("SELECT id, username, role, status FROM users")
users = c.fetchall()
print(f'Total users in DB: {len(users)}')
for u in users:
    print(f' - ID={u[0]}, Username={u[1]}, Role={u[2]}, Status={u[3]}')

usernames = [u[1] for u in users]
assert 'Betatester101' in usernames, 'Betatester101 not found!'
assert 'god' in usernames, 'god not found!'
assert 'KoldP' in usernames, 'KoldP not found!'
assert 'admin' in usernames, 'admin not found!'

# Ensure no old test users remain
for old in ['member1', 'op1', 'operator1', 'test001', 'cha', 'airi', '31', '32']:
    assert old not in usernames, f'Old user {old} should have been cleared!'

# Ensure member count is 0
c.execute("SELECT COUNT(*) FROM users WHERE role='member'")
member_count = c.fetchone()[0]
assert member_count == 0, f'Expected 0 members, found {member_count}'
print('[PASS] Members completely cleared (0 members).')

# Ensure operator count is 1
c.execute("SELECT COUNT(*) FROM users WHERE role='operator'")
operator_count = c.fetchone()[0]
assert operator_count == 1, f'Expected 1 operator, found {operator_count}'
print('[PASS] Exactly 1 operator (Betatester101).')

# Check tables: orders, transactions, user_ammo
c.execute("SELECT COUNT(*) FROM orders")
assert c.fetchone()[0] == 0, 'Orders not empty'
c.execute("SELECT COUNT(*) FROM transactions")
assert c.fetchone()[0] == 0, 'Transactions not empty'
c.execute("SELECT COUNT(*) FROM user_ammo")
assert c.fetchone()[0] == 0, 'user_ammo not empty'
print('[PASS] orders, transactions, user_ammo all clean (0 records).')

# Check club_inventory
c.execute("SELECT ammo_type, quantity FROM club_inventory")
inv = dict(c.fetchall())
print('Inventory:', inv)
for k in ['.177', '.22 LR (CCI)', '.22 LR (RWS)', 'เป้าปืนยาว', 'เป้าปืนสั้น']:
    assert inv.get(k) == 1000, f'Inventory for {k} is {inv.get(k)} (expected 1000)'
print('[PASS] Club inventory restored to 1,000 units each.')

conn.close()

print('\n=== 2. Checking Default Gray Avatar ===')
for path in ['static/default_avatar.png', 'static/profiles/default_avatar.png']:
    im = Image.open(path)
    assert im.size == (512, 512), f'Wrong size {im.size}'
    assert im.mode == 'RGBA', f'Wrong mode {im.mode}'
    arr = np.array(im)
    # Check that colors are neutral gray
    # Solid circle pixels
    opaque = arr[arr[:, :, 3] > 200][:, :3]
    # In neutral gray, R, G, B channels are close to each other
    diff = np.abs(opaque[:, 0].astype(int) - opaque[:, 1].astype(int)) + np.abs(opaque[:, 1].astype(int) - opaque[:, 2].astype(int))
    max_channel_diff = diff.max()
    assert max_channel_diff < 40, f'Avatar is not neutral gray, channel diff={max_channel_diff}'
    print(f'[PASS] {path} is 512x512 RGBA neutral gray avatar (max channel diff: {max_channel_diff}).')

print('\n=== 3. Testing Authentication via Live HTTP Server ===')
# Test Betatester101 login with Test888
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 3a. Bad password
login_data_bad = urllib.parse.urlencode({'username': 'Betatester101', 'password': 'WrongPassword'}).encode('utf-8')
req_bad = urllib.request.Request('http://127.0.0.1:5000/login', data=login_data_bad, headers={'X-Requested-With': 'XMLHttpRequest'})
res_bad = opener.open(req_bad)
bad_body = res_bad.read().decode('utf-8')
assert 'success":false' in bad_body or 'success": false' in bad_body, f'Bad login succeeded: {bad_body}'
print('[PASS] Betatester101 rejected with wrong password.')

# 3b. Correct password Test888
login_data_good = urllib.parse.urlencode({'username': 'Betatester101', 'password': 'Test888'}).encode('utf-8')
req_good = urllib.request.Request('http://127.0.0.1:5000/login', data=login_data_good, headers={'X-Requested-With': 'XMLHttpRequest'})
res_good = opener.open(req_good)
good_body = res_good.read().decode('utf-8')
assert 'success":true' in good_body or 'success": true' in good_body, f'Good login failed: {good_body}'
assert '/operator' in good_body, f'Redirect URL missing: {good_body}'
print('[PASS] Betatester101 logged in successfully and redirected to /operator.')

# 3c. Test God account KoldP with 1987
login_data_god = urllib.parse.urlencode({'username': 'KoldP', 'password': '1987'}).encode('utf-8')
req_god = urllib.request.Request('http://127.0.0.1:5000/login', data=login_data_god, headers={'X-Requested-With': 'XMLHttpRequest'})
res_god = opener.open(req_god)
god_body = res_god.read().decode('utf-8')
assert 'success":true' in god_body or 'success": true' in god_body, f'God login failed: {god_body}'
assert '/god' in god_body, f'God redirect URL missing: {god_body}'
print('[PASS] God Admin (KoldP) preserved and logged in successfully to /god.')

print('\n>>> ALL DATABASE RESET & BETATESTER101 VERIFICATIONS PASSED 100%! <<<')
