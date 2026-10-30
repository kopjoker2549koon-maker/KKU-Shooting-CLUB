import os
import sys
import urllib.request
from PIL import Image
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

print('=== 1. Checking Image Properties ===')
img_path = 'static/leon_board.png'
assert os.path.exists(img_path), 'Target image does not exist'
im = Image.open(img_path)
assert im.size == (1080, 596), f'Unexpected dimensions: {im.size}'
assert im.mode == 'RGBA', f'Unexpected mode: {im.mode}'
print(f' Dimensions: {im.size}, Mode: {im.mode}')

print('=== 2. Checking Alpha Channel & Cutout Quality ===')
arr = np.array(im)
alpha = arr[:, :, 3]
assert np.sum(alpha == 0) > 400000, 'Transparent background missing'
assert np.sum(alpha == 255) > 80000, 'Solid foreground subject missing'
assert np.sum((alpha > 0) & (alpha < 255)) > 2000, 'Feathered edge missing'
print(f' Alpha: {np.sum(alpha==0)} transparent, {np.sum(alpha==255)} solid, {np.sum((alpha>0)&(alpha<255))} feathered edges')

print('=== 3. Checking Backup Preservation ===')
assert os.path.exists('static/leon_board_backup.png'), 'Backup original not found'
print(' Backup static/leon_board_backup.png verified.')

print('=== 4. Checking Live Server HTTP Status ===')
res = urllib.request.urlopen('http://127.0.0.1:5000/static/leon_board.png?v=2')
assert res.status == 200, f'Bad HTTP status: {res.status}'
content = res.read()
assert len(content) == os.path.getsize(img_path), 'Served image size mismatch'
print(f' HTTP 200 OK, served {len(content)} bytes')

print('=== 5. Checking Login Page HTML Integration ===')
login_res = urllib.request.urlopen('http://127.0.0.1:5000/login')
assert login_res.status == 200
html = login_res.read().decode('utf-8')
assert 'id="charOperator"' in html, '#charOperator not found'
assert 'leon_board.png?v=2' in html, 'leon_board.png?v=2 not found'
assert 'switchRole(\'operator\')' in html or 'switchRole("operator")' in html, 'switchRole(operator) not found'
print(' Login template correctly integrates the new character.')

print('\n All 5 verification checks passed successfully!')
