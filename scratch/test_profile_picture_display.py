import os
import sys
import hashlib
import sqlite3

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, get_db

client = app.test_client()

print("==================================================================")
print("TEST: PROFILE PICTURE DISPLAY & AVATAR INDEPENDENCE AUDIT")
print("==================================================================")

# 1. Verify that default_avatar.png is completely decoupled from God Admin (wesker.png)
print("\n--- 1. Cryptographic Decoupling of Default Avatar ---")
h_default = hashlib.md5(open('static/profiles/default_avatar.png', 'rb').read()).hexdigest()
h_god = hashlib.md5(open('static/wesker.png', 'rb').read()).hexdigest()

assert h_default != h_god, "CRITICAL ERROR: default_avatar.png is still identical to God Admin (wesker.png)!"
print(f"[PASS] default_avatar.png ({h_default[:10]}...) is NOT God Admin wesker ({h_god[:10]}...).")

# 2. Verify Member Dashboard Avatar Rendering
print("\n--- 2. Member Dashboard (/member) Profile Picture ---")
# Login as test member or Betatester101
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username FROM users WHERE role='member' LIMIT 1")
test_u = c.fetchone()
if not test_u:
    c.execute("INSERT INTO users (username, password, role, status, profile_pic) VALUES ('temp_test_mem', 'hash', 'member', 'approved', 'default_avatar.png')")
    test_uid = c.lastrowid
    test_uname = 'temp_test_mem'
    conn.commit()
else:
    test_uid, test_uname = test_u[0], test_u[1]
conn.close()

with client.session_transaction() as sess:
    sess['user_id'] = test_uid
    sess['username'] = test_uname
    sess['role'] = 'member'

r_mem = client.get('/member')
assert r_mem.status_code == 200
html_mem = r_mem.data.decode('utf-8')
assert 'drawerAvatarImg' in html_mem
assert 'user-profile-nav' in html_mem
assert 'member1' in html_mem
print("[PASS] Member Dashboard displays user profile avatar in navbar and drawer.")

# 3. Verify Digital Membership Card (/member/card) Avatar Rendering
print("\n--- 3. Digital Membership Card (/member/card) ---")
r_card = client.get('/member/card')
assert r_card.status_code == 200
html_card = r_card.data.decode('utf-8')
assert 'avatar-img' in html_card
assert 'avatar-status-badge' in html_card
assert 'NO. KKU-SC-0009' in html_card
print("[PASS] Digital Membership Card correctly displays member photo and fallback.")

# 4. Verify Shortcut /profile Route
print("\n--- 4. Shortcut /profile Route ---")
r_prof = client.get('/profile', follow_redirects=False)
assert r_prof.status_code == 302
assert r_prof.headers['Location'].endswith('/member/card')
print(f"[PASS] /profile cleanly redirects to '{r_prof.headers['Location']}'")

# 5. Verify Operator Range Member Lookup API (/api/member_lookup)
print("\n--- 5. Operator Scanner Member Lookup API ---")
with client.session_transaction() as sess:
    sess['user_id'] = 7
    sess['username'] = 'op1'
    sess['role'] = 'operator'

r_lookup = client.get('/api/member_lookup?query=member1')
assert r_lookup.status_code == 200
m_data = r_lookup.get_json()['member']
assert m_data['username'] == 'member1'
assert m_data['profile_pic'] != 'wesker.png'
print(f"[PASS] Lookup returned member profile_pic: '{m_data['profile_pic']}'")

# 6. Verify God Admin Member Roster Avatar Display
print("\n--- 6. God Admin Members Table Avatar Column ---")
with client.session_transaction() as sess:
    sess['user_id'] = 5
    sess['username'] = 'KoldP'
    sess['role'] = 'god'

r_god = client.get('/god')
assert r_god.status_code == 200
html_god = r_god.data.decode('utf-8')
assert 'profiles/' in html_god
print("[PASS] God Admin member table displays individual member avatar thumbnails.")

print("\n==================================================================")
print(">>> ALL 6 PROFILE PICTURE CHECKS PASSED 100%! BUG RESOLVED! <<<")
print("==================================================================")
