import os
import sys
import sqlite3
import io
from PIL import Image

# Set utf-8 output encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from werkzeug.security import generate_password_hash

client = app.test_client()

print("==================================================")
print("TEST: IMAGE CROPPING SYSTEM INTEGRATION")
print("==================================================")

# 1. Verify Static Files
print("\n--- 1. Verifying Cropper Static Assets ---")
assert os.path.exists('static/cropper.min.js'), "Missing cropper.min.js"
assert os.path.exists('static/cropper.min.css'), "Missing cropper.min.css"
assert os.path.exists('static/image_cropper_helper.js'), "Missing image_cropper_helper.js"

r_js = client.get('/static/cropper.min.js')
assert r_js.status_code == 200
r_css = client.get('/static/cropper.min.css')
assert r_css.status_code == 200
r_helper = client.get('/static/image_cropper_helper.js')
assert r_helper.status_code == 200
assert b'handleImageSelectForCrop' in r_helper.data
print("[PASS] Cropper.js, CSS, and Image Cropper Helper verified and accessible via HTTP.")

# 2. Verify Template Inclusions
print("\n--- 2. Verifying Templates Integration ---")

# Member Register
r_reg = client.get('/register')
reg_html = r_reg.data.decode('utf-8')
assert 'cropper.min.css' in reg_html, "register.html missing cropper CSS"
assert 'cropper.min.js' in reg_html, "register.html missing cropper JS"
assert 'image_cropper_helper.js' in reg_html, "register.html missing helper JS"
assert 'handleImageSelectForCrop' in reg_html, "register.html missing handleImageSelectForCrop call"
print("[PASS] Member Registration (register.html) successfully wired with interactive image cropper.")

# Operator Register
r_op_reg = client.get('/register_operator')
op_reg_html = r_op_reg.data.decode('utf-8')
assert 'cropper.min.css' in op_reg_html, "register_operator.html missing cropper CSS"
assert 'cropper.min.js' in op_reg_html, "register_operator.html missing cropper JS"
assert 'image_cropper_helper.js' in op_reg_html, "register_operator.html missing helper JS"
assert 'handleImageSelectForCrop' in op_reg_html, "register_operator.html missing handleImageSelectForCrop call"
print("[PASS] Operator Registration (register_operator.html) successfully wired with interactive image cropper.")

# Member Dashboard (Slips + Avatar update)
login_res = client.post('/', data={'username': 'member1', 'password': '123', 'role': 'member'}, follow_redirects=True)
assert login_res.status_code == 200

r_member = client.get('/member')
member_html = r_member.data.decode('utf-8')
assert 'cropper.min.css' in member_html, "member.html missing cropper CSS"
assert 'cropper.min.js' in member_html, "member.html missing cropper JS"
assert 'image_cropper_helper.js' in member_html, "member.html missing helper JS"
assert 'handleImageSelectForCrop' in member_html, "member.html missing handleImageSelectForCrop call"
assert 'updateAvatarForm' in member_html, "member.html missing updateAvatarForm"
print("[PASS] Member Dashboard (member.html) wired with slip cropper and profile avatar update cropper.")

# 3. Test Profile Photo Upload / Update Backend Route
print("\n--- 3. Testing Backend Profile Photo Update (update_profile_pic) ---")
# Create a dummy cropped image in memory (e.g. 200x200 square)
img_byte_arr = io.BytesIO()
img = Image.new('RGB', (200, 200), color=(37, 99, 235))
img.save(img_byte_arr, format='JPEG')
img_byte_arr.seek(0)

# Submit update_profile_pic
r_update = client.post('/member', data={
    'action': 'update_profile_pic',
    'profile_image': (img_byte_arr, 'my_cropped_avatar.jpg')
}, content_type='multipart/form-data', follow_redirects=True)

assert r_update.status_code == 200

# Check DB for updated profile pic
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT profile_pic FROM users WHERE username='member1'")
new_pic = c.fetchone()[0]
conn.close()

assert new_pic != 'default_avatar.png'
assert new_pic.startswith('member1_')
assert os.path.exists(os.path.join('static', 'profiles', new_pic)), f"File not found on disk: {new_pic}"
print(f"[PASS] Profile picture successfully updated and saved on disk: static/profiles/{new_pic}")

# 4. Test Registration with Cropped Photo
print("\n--- 4. Testing Member Registration with Cropped Photo ---")
test_user = 'crop_tester_01'
test_email = 'crop_tester_01@kkumail.com'

# Clean up if existed
conn = sqlite3.connect('shooting_club.db')
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.commit()
conn.close()

reg_img_bytes = io.BytesIO()
reg_img = Image.new('RGB', (300, 300), color=(245, 158, 11))
reg_img.save(reg_img_bytes, format='JPEG')
reg_img_bytes.seek(0)

r_new_reg = client.post('/register', data={
    'username': test_user,
    'password': 'Password123',
    'confirm_password': 'Password123',
    'prefix': 'นาย',
    'first_name': 'ทดสอบ',
    'last_name': 'ครอปรูป',
    'faculty': 'วิศวกรรมศาสตร์',
    'academic_year': '2',
    'kku_mail': test_email,
    'student_id': '653040888-8',
    'phone': '0812345678',
    'profile_image': (reg_img_bytes, 'avatar_cropped.jpg')
}, content_type='multipart/form-data', follow_redirects=True)

assert r_new_reg.status_code == 200

# Verify in DB
conn = sqlite3.connect('shooting_club.db')
c = conn.cursor()
c.execute("SELECT profile_pic FROM users WHERE username=?", (test_user,))
saved_pic = c.fetchone()[0]
conn.close()

assert saved_pic.startswith(f"{test_user}_")
assert os.path.exists(os.path.join('static', 'profiles', saved_pic))
print(f"[PASS] New member registered with cropped photo saved at static/profiles/{saved_pic}")

# Clean up test user & file
conn = sqlite3.connect('shooting_club.db')
conn.execute("DELETE FROM users WHERE username=?", (test_user,))
conn.commit()
conn.close()
if os.path.exists(os.path.join('static', 'profiles', saved_pic)):
    os.remove(os.path.join('static', 'profiles', saved_pic))

print("\n==================================================")
print(">>> ALL TESTS PASSED! IMAGE CROPPING FULLY VERIFIED! <<<")
print("==================================================")
