import sqlite3
import werkzeug.security

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username, password, role FROM users")
passwords_to_test = ['123', '1234', '123456', '12345678', 'admin', 'password', 'god', '1987', 'root', 'op1', 'member1', 'operator1', 'test001', 'cha', 'airi', '31', '32']
for uid, u, p, r in c.fetchall():
    matched = None
    for pwd in passwords_to_test:
        if werkzeug.security.check_password_hash(p, pwd):
            matched = pwd
            break
    print(f"[{uid}] {u:15} ({r:10}) -> password: {matched if matched else 'UNKNOWN'}")
conn.close()
