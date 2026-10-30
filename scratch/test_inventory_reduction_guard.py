import os
import sys
import sqlite3

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

client = app.test_client()

print("==================================================")
print("TEST: INVENTORY REDUCTION GUARDRAILS & ERROR FLASH")
print("==================================================")

# 1. Reset / initialize a known item in club_inventory & op1 password
TARGET_AMMO = '.22 LR (RWS)'
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("UPDATE club_inventory SET quantity = 1000 WHERE ammo_type = ?", (TARGET_AMMO,))

from werkzeug.security import generate_password_hash
c.execute("UPDATE users SET password = ?, status = 'approved' WHERE username = 'op1'", (generate_password_hash('123'),))
conn.commit()

# Verify initial stock is 1000
c.execute("SELECT quantity FROM club_inventory WHERE ammo_type = ?", (TARGET_AMMO,))
initial_qty = c.fetchone()[0]
conn.close()
assert initial_qty == 1000, f"Expected 1000, got {initial_qty}"
print(f"[PASS] 1. Initial inventory confirmed: {TARGET_AMMO} = {initial_qty} นัด")

# 2. Login as Operator (op1)
login_res = client.post('/', data={'username': 'op1', 'password': '123', 'role': 'operator'}, follow_redirects=True)
assert login_res.status_code == 200
print("[PASS] 2. Logged in as Operator (op1)")

# 3. ATTEMPT INVALID REDUCTION: Inventory is 1000, requesting reduction of 2000
print("\n--- Testing Excessive Stock Reduction (1000 in stock, requesting sub 2000) ---")
res_excessive = client.post('/operator', data={
    'action': 'sub_inventory',
    'ammo_type': TARGET_AMMO,
    'amount': '2000',
    'note': 'ทดสอบตัดสต็อกเกินจริง'
}, follow_redirects=True)
assert res_excessive.status_code == 200
html_excessive = res_excessive.data.decode('utf-8')

# Verify DB was NOT updated and remained at 1000 (NOT 0!)
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT quantity FROM club_inventory WHERE ammo_type = ?", (TARGET_AMMO,))
after_qty = c.fetchone()[0]

# Verify no invalid transaction was recorded
c.execute("SELECT id FROM transactions WHERE ammo_type = ? AND action = 'Operator_Sub' AND amount = 2000", (TARGET_AMMO,))
invalid_tx = c.fetchone()
conn.close()

assert after_qty == 1000, f"Stock was modified! Expected 1000, got {after_qty}"
assert invalid_tx is None, "Found transaction record for failed reduction!"
print(f"[PASS] 3. Database is intact: Stock remains {after_qty} (not dropped to 0)")
print("[PASS] 4. No invalid transaction record inserted into audit trail")

# Verify Flash Error Message appears in HTML
assert 'ผิดพลาด' in html_excessive, "Missing error keyword in flash message"
assert '2,000' in html_excessive or '2000' in html_excessive, "Missing requested amount in error message"
assert '1,000' in html_excessive or '1000' in html_excessive, "Missing available quantity in error message"
assert 'bg-danger' in html_excessive, "Flash alert should use danger styling"
print("[PASS] 5. Flash error alert triggered correctly with red danger alert badge:")
print("       -> 'ผิดพลาด: ไม่สามารถสั่งลด 2,000 ได้ เนื่องจากมีในคลังเพียง 1,000'")

# 4. ATTEMPT ZERO OR NEGATIVE REDUCTION
print("\n--- Testing Zero & Negative Stock Reduction ---")
res_zero = client.post('/operator', data={
    'action': 'sub_inventory',
    'ammo_type': TARGET_AMMO,
    'amount': '0',
    'note': 'ตัด 0'
}, follow_redirects=True)
assert 'ผิดพลาด' in res_zero.data.decode('utf-8')

res_neg = client.post('/operator', data={
    'action': 'sub_inventory',
    'ammo_type': TARGET_AMMO,
    'amount': '-50',
    'note': 'ตัดติดลบ'
}, follow_redirects=True)
assert 'ผิดพลาด' in res_neg.data.decode('utf-8')
print("[PASS] 6. Zero and negative reduction properly blocked with error alert")

# 5. ATTEMPT VALID REDUCTION: 1000 in stock, requesting reduction of 200
print("\n--- Testing Valid Stock Reduction (1000 in stock, requesting sub 200) ---")
res_valid = client.post('/operator', data={
    'action': 'sub_inventory',
    'ammo_type': TARGET_AMMO,
    'amount': '200',
    'note': 'ตัดกระสุนทดสอบสนาม'
}, follow_redirects=True)
assert res_valid.status_code == 200
html_valid = res_valid.data.decode('utf-8')

conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT quantity FROM club_inventory WHERE ammo_type = ?", (TARGET_AMMO,))
new_qty = c.fetchone()[0]

c.execute("SELECT amount, note FROM transactions WHERE ammo_type = ? AND action = 'Operator_Sub' ORDER BY id DESC LIMIT 1", (TARGET_AMMO,))
valid_tx = c.fetchone()
conn.close()

assert new_qty == 800, f"Expected 800, got {new_qty}"
assert valid_tx is not None and valid_tx[0] == 200, "Transaction not logged properly"
assert 'ลดสต็อก' in html_valid and '200' in html_valid, "Success message missing"
print(f"[PASS] 7. Valid reduction executed: Stock properly updated from 1000 to {new_qty}")
print("[PASS] 8. Audit trail transaction successfully logged with note: 'ตัดกระสุนทดสอบสนาม'")

# 6. Verify Frontend HTML & JS validations in operator.html
print("\n--- Verifying Frontend Client-Side Validation in operator.html ---")
get_operator = client.get('/operator')
op_html = get_operator.data.decode('utf-8')
assert 'validateStockForm()' in op_html, "Missing frontend validateStockForm() function"
assert 'stockWarningNotice' in op_html, "Missing real-time warning container"
assert 'checkStockInput()' in op_html, "Missing real-time oninput check"
assert 'modalStockAmount' in op_html, "Missing modalStockAmount input"
print("[PASS] 9. Frontend client-side guardrails verified (form intercept, real-time warning, input limits)")

print("\n==================================================")
print(">>> ALL 9 CHECKS PASSED! INVENTORY REDUCTION GUARD FULLY VERIFIED! <<<")
print("==================================================")
