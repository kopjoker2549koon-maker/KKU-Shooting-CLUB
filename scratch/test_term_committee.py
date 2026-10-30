import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

print('=== 1. Checking /login page ===')
res_login = urllib.request.urlopen('http://127.0.0.1:5000/login')
assert res_login.status == 200
html_login = res_login.read().decode('utf-8')
assert '<span>กรรมการ</span>' in html_login, 'Role tab <span>กรรมการ</span> not found in login'
assert 'alt="กรรมการ"' in html_login, 'Character alt="กรรมการ" not found in login'
assert 'เข้าสู่ระบบกรรมการ' in html_login, 'submit button text เข้าสู่ระบบกรรมการ not found in login'
assert 'เจ้าหน้าที่' not in html_login, 'Unexpected เจ้าหน้าที่ still present in login.html'
print('[PASS] Login page renders "กรรมการ" cleanly with zero "เจ้าหน้าที่" occurrences.')

print('=== 2. Checking /register_operator page ===')
res_reg = urllib.request.urlopen('http://127.0.0.1:5000/register_operator')
assert res_reg.status == 200
html_reg = res_reg.read().decode('utf-8')
assert 'คณะกรรมการชมรม' in html_reg, 'Badge คณะกรรมการชมรม not found in register_operator'
assert 'เข้าสู่ระบบกรรมการ' in html_reg, 'Link เข้าสู่ระบบกรรมการ not found in register_operator'
assert 'ข้อตกลงและหน้าที่รับผิดชอบความปลอดภัยของกรรมการสนาม' in html_reg, 'Safety agreement title not updated'
assert 'เจ้าหน้าที่' not in html_reg, 'Unexpected เจ้าหน้าที่ still present in register_operator.html'
print('[PASS] Register operator page renders "กรรมการ" cleanly with zero "เจ้าหน้าที่" occurrences.')

print('=== 3. Checking Static Files & Templates ===')
for filename in ['templates/login.html', 'templates/register_operator.html', 'templates/god.html', 'templates/member.html', 'templates/member_card.html', 'templates/operator.html', 'app.py']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'เจ้าหน้าที่' not in content, f'Found เจ้าหน้าที่ in {filename}'
    print(f'[PASS] {filename} verified (zero "เจ้าหน้าที่" occurrences)')

print('\n>>> ALL COMMITTEE (กรรมการ) TERMINOLOGY CHECKS PASSED 100%! <<<')
