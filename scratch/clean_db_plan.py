import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()

c.execute('SELECT * FROM club_inventory')
print('Inventory:', c.fetchall())

c.execute("SELECT id, username, role, password FROM users WHERE role IN ('god', 'admin')")
gods = c.fetchall()
print('\nGod users to preserve:')
for g in gods:
    print(f'ID={g[0]}, username={g[1]}, role={g[2]}, hash={g[3][:25]}...')

c.execute("SELECT id, username, role FROM users WHERE role NOT IN ('god', 'admin')")
to_delete = c.fetchall()
print(f'\nUsers to delete ({len(to_delete)} users):')
for u in to_delete:
    print(f'ID={u[0]}, username={u[1]}, role={u[2]}')

conn.close()

print('\nProfiles directory files:', os.listdir('static/profiles'))
print('Slips directory count:', len(os.listdir('static/slips')))
