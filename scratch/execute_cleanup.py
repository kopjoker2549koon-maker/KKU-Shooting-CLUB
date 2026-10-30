import sqlite3
import os
import glob
from werkzeug.security import generate_password_hash
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

print('=== 1. Connecting to SQLite Database ===')
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()

# Get IDs of God Admin users
c.execute("SELECT id, username, role FROM users WHERE role IN ('god', 'admin')")
god_users = c.fetchall()
god_ids = [u[0] for u in god_users]
print(f'Preserved God Admins ({len(god_users)} accounts):')
for u in god_users:
    print(f' - ID={u[0]}, Username={u[1]}, Role={u[2]}')

# Delete non-god users (members and old operators)
c.execute("DELETE FROM users WHERE role NOT IN ('god', 'admin')")
deleted_users_count = c.rowcount
print(f'Deleted {deleted_users_count} member & operator users from `users`.')

# Delete non-god user ammo
c.execute(f"DELETE FROM user_ammo WHERE user_id NOT IN ({','.join(map(str, god_ids))})")
print(f'Cleared `user_ammo` ({c.rowcount} rows).')

# Delete orders (all were test orders)
c.execute("DELETE FROM orders")
print(f'Cleared `orders` ({c.rowcount} rows).')

# Delete transactions
c.execute("DELETE FROM transactions")
print(f'Cleared `transactions` ({c.rowcount} rows).')

# Delete otp_codes
c.execute("DELETE FROM otp_codes")
print(f'Cleared `otp_codes` ({c.rowcount} rows).')

# Reset club_inventory to 1,000 for each item
inventory_defaults = [
    ('.177', 1000),
    ('.22 LR (CCI)', 1000),
    ('.22 LR (RWS)', 1000),
    ('เป้าปืนยาว', 1000),
    ('เป้าปืนสั้น', 1000)
]
for item, qty in inventory_defaults:
    c.execute("INSERT OR REPLACE INTO club_inventory (ammo_type, quantity) VALUES (?, ?)", (item, qty))
print('Reset `club_inventory` to 1,000 units each.')

# Create the requested Operator: Betatester101 / Test888
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
hashed_pw = generate_password_hash('Test888')

c.execute("""
    INSERT INTO users (
        username, password, role, status, 
        prefix, first_name, last_name, 
        position, kku_mail, profile_pic, created_at
    ) VALUES (
        'Betatester101', ?, 'operator', 'approved',
        'นาย', 'เบต้า', 'เทสเตอร์',
        'กรรมการชมรม', 'betatester101@kkumail.com', 'default_avatar.png', ?
    )
""", (hashed_pw, now))
new_op_id = c.lastrowid
print(f'Successfully created Committee account: Betatester101 (ID={new_op_id}, Role=operator, Status=approved)')

conn.commit()
conn.close()

# Clean uploaded profile pictures except default_avatar.png
print('\n=== 2. Cleaning Uploaded Files ===')
profiles_dir = 'static/profiles'
cleaned_profiles = 0
for f in os.listdir(profiles_dir):
    if f != 'default_avatar.png':
        os.remove(os.path.join(profiles_dir, f))
        cleaned_profiles += 1
print(f'Removed {cleaned_profiles} old profile uploads from static/profiles.')

# Clean uploaded slips
slips_dir = 'static/slips'
cleaned_slips = 0
for f in os.listdir(slips_dir):
    os.remove(os.path.join(slips_dir, f))
    cleaned_slips += 1
print(f'Removed {cleaned_slips} old payment slips from static/slips.')

print('\n=== 3. Verification of Final State ===')
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT id, username, role, status, profile_pic FROM users")
for u in c.fetchall():
    print(f'User: ID={u[0]}, Username={u[1]}, Role={u[2]}, Status={u[3]}, Avatar={u[4]}')

conn.close()
print('\nCleanup and Account Creation completed successfully!')
