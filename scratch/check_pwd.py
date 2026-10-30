import sqlite3
import werkzeug.security

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username, password, role FROM users WHERE role='god'")
for uid, u, p, r in c.fetchall():
    print(f"User: {u}, Role: {r}")
    for candidate in ['123', 'god', '1987', 'admin']:
        if werkzeug.security.check_password_hash(p, candidate):
            print(f"  -> Match found! Password is '{candidate}'")
conn.close()
