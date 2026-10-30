import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username, password, role, status FROM users")
users = c.fetchall()

test_passwords = ['123', '1234', '123456', 'admin', 'password', 'god', '1987', 'op1', 'operator', 'member1', 'operator1', 'root']

print("=== CHECKING ALL USERS PASSWORD MATCHES ===")
for uid, u, p, r, s in users:
    matched = None
    if p.startswith(('scrypt:', 'pbkdf2:')):
        for test_p in test_passwords:
            if check_password_hash(p, test_p):
                matched = test_p
                break
    else:
        matched = f"Plaintext: {p}"
    print(f"[{uid}] User: '{u}' (role: {r}) -> Match: {matched}")

conn.close()
