import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in c.fetchall()]
print('Tables in DB:', tables)

for t in tables:
    c.execute(f"PRAGMA table_info({t});")
    cols = [r[1] for r in c.fetchall()]
    c.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = c.fetchone()[0]
    print(f"Table '{t}' ({cnt} rows): cols={cols}")

print('\nExisting users:')
c.execute("SELECT id, username, role, first_name, last_name, profile_pic FROM users")
for u in c.fetchall():
    print(u)

conn.close()
