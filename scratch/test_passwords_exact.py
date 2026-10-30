import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT username, password, role FROM users")
for u, p, r in c.fetchall():
    for test in ['admin123', 'god123', 'op123', '123', '1234', '1987', 'test1', '1']:
        if p.startswith(('scrypt:', 'pbkdf2:')):
            if check_password_hash(p, test):
                print(f"User: {u:12} | Role: {r:10} | Password MATCH: '{test}'")
                break
        elif p == test:
            print(f"User: {u:12} | Role: {r:10} | Plaintext MATCH: '{test}'")
            break
    else:
        print(f"User: {u:12} | Role: {r:10} | NO MATCH! (Stored: {p[:15]}...)")
conn.close()
