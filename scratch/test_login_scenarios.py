import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('shooting_club.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Test various real-world user inputs that would have FAILED under the old code:
test_cases = [
    # (input_username, input_password, form_role, expected_user)
    ('member1 ', '123', 'member', 'member1 with trailing space'),
    ('Member1', '123', 'member', 'member1 with capital M'),
    ('member1@kkumail.com', '123', 'member', 'member1 using KKU Mail'),
    ('admin', 'admin123', 'member', 'admin logging in from default member tab'),
    ('god', 'god123', 'member', 'god logging in from default member tab'),
    ('op1', '123', 'member', 'op1 logging in without switching tab'),
    ('653040111-2', '123', 'member', 'member1 using student ID'),
    ('KoldP', '1987', 'member', 'KoldP logging in from default tab'),
]

print("=== TESTING LOGIN FLEXIBILITY ===")
for u_input, p_input, r_input, desc in test_cases:
    clean_u = u_input.strip()
    clean_p = p_input.strip()
    
    # OLD QUERY:
    c.execute("SELECT * FROM users WHERE (username=? OR student_id=?) AND role=?", (u_input, u_input, r_input))
    old_res = c.fetchone()
    old_ok = False
    if old_res:
        stored = old_res['password'] or ''
        if stored.startswith(('scrypt:', 'pbkdf2:')):
            old_ok = check_password_hash(stored, p_input)
        else:
            old_ok = (stored == p_input)
            
    # NEW IMPROVED QUERY:
    c.execute("""
        SELECT * FROM users 
        WHERE LOWER(username) = LOWER(?) 
           OR student_id = ? 
           OR LOWER(kku_mail) = LOWER(?)
    """, (clean_u, clean_u, clean_u))
    new_res = c.fetchone()
    new_ok = False
    if new_res:
        stored = new_res['password'] or ''
        if stored.startswith(('scrypt:', 'pbkdf2:')):
            new_ok = check_password_hash(stored, clean_p)
        else:
            new_ok = (stored == clean_p)
            
    print(f"Test '{desc}':")
    print(f"  Old Code: {'SUCCESS' if old_ok else 'FAILED (BUG!)'}")
    print(f"  New Code: {'SUCCESS' if new_ok else 'FAILED'}")

conn.close()
