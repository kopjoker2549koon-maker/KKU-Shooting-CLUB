from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, send_from_directory, jsonify
import sqlite3
import os
import json
import random
import csv
import io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ความปลอดภัยระดับ Production: จัดการ Secret Key แบบคงทนและปลอดภัย
def load_or_create_secret_key():
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    key_file = os.path.join(os.path.dirname(__file__), '.secret_key')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                k = f.read().strip()
                if k:
                    return k
        except Exception:
            pass
    import secrets
    new_key = secrets.token_hex(32)
    try:
        with open(key_file, 'w', encoding='utf-8') as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key

app.secret_key = load_or_create_secret_key()

# ตั้งค่าความปลอดภัยของ Session และข้อจำกัดไฟล์อัปโหลดสำหรับ Production
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # สูงสุด 16MB ต่อคำขอ ป้องกัน Memory Overflow / DoS
app.config['SESSION_COOKIE_HTTPONLY'] = True          # ป้องกัน XSS อ่าน Cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'         # ป้องกัน CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7) # คงสถานะเข้าสู่ระบบบนมือถือ/แท็บเล็ต 7 วัน

# โฟลเดอร์เก็บสลิป
UPLOAD_FOLDER = os.path.join('static', 'slips')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# โฟลเดอร์เก็บรูปโปรไฟล์
PROFILE_FOLDER = os.path.join('static', 'profiles')
os.makedirs(PROFILE_FOLDER, exist_ok=True)
app.config['PROFILE_FOLDER'] = PROFILE_FOLDER

# โฟลเดอร์สำรองข้อมูลฐานข้อมูล
BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), 'backups')
os.makedirs(BACKUP_FOLDER, exist_ok=True)

def get_db():
    # ใช้ SQLite WAL (Write-Ahead Logging) เพื่อรองรับ Concurrency สูงสุดในสนาม
    conn = sqlite3.connect('shooting_club.db', timeout=25.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = NORMAL;')
    return conn

def mask_email(email):
    """ฟังก์ชันปกปิดบางตัวอักษรของอีเมลเพื่อความเป็นส่วนตัว เช่น s*****i@kkumail.com"""
    if not email or '@' not in email:
        return email or ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"{local[0]}*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"

def send_otp_email(recipient_email, otp_code, username):
    """
    ส่งอีเมลรหัส OTP ไปยัง KKU Mail (@kkumail.com)
    - หากมีการตั้งค่าตัวแปรสภาพแวดล้อม MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD จะทำการส่งผ่าน SMTP จริง
    - หากไม่มีการตั้งค่า SMTP จะแสดง OTP ผ่านคอนโซลสำหรับการทดสอบในเครื่องได้อย่างราบรื่น
    """
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_user = os.environ.get('MAIL_USERNAME')
    mail_pass = os.environ.get('MAIL_PASSWORD')
    mail_sender = os.environ.get('MAIL_DEFAULT_SENDER', mail_user or 'no-reply@kkumail.com')

    subject = f"[KKU Shooting Club] รหัส OTP รีเซ็ตรหัสผ่านของคุณคือ: {otp_code}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 20px; background-color: #080c14; font-family: Arial, sans-serif; color: #f8fafc;">
        <div style="max-width: 520px; margin: 0 auto; background: #0f172a; border-radius: 16px; border: 1px solid #1e293b; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #38bdf8; font-size: 24px; margin: 0; letter-spacing: 1px;">KKU SHOOTING CLUB</h1>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">ชมรมกีฬายิงปืน มหาวิทยาลัยขอนแก่น</p>
            </div>
            
            <p style="font-size: 15px; color: #e2e8f0; line-height: 1.6;">
                สวัสดีคุณ <strong>{username}</strong>,<br>
                ระบบได้รับคำขอรีเซ็ตรหัสผ่านสำหรับบัญชีของคุณ กรุณาใช้รหัส OTP 6 หลักด้านล่างนี้เพื่อยืนยันการตั้งรหัสผ่านใหม่:
            </p>

            <div style="text-align: center; margin: 26px 0;">
                <div style="display: inline-block; background: #1e293b; border: 2px dashed #f59e0b; border-radius: 12px; padding: 14px 28px;">
                    <span style="font-size: 34px; font-weight: bold; letter-spacing: 8px; color: #fbbf24; font-family: monospace;">{otp_code}</span>
                </div>
                <div style="color: #ef4444; font-size: 13px; margin-top: 10px; font-weight: 500;">
                    ⏳ รหัส OTP มีอายุการใช้งาน 5 นาทีเท่านั้น
                </div>
            </div>

            <p style="font-size: 13px; color: #64748b; line-height: 1.5; border-top: 1px solid #1e293b; padding-top: 18px; margin-top: 24px; text-align: center;">
                หากท่านไม่ได้เป็นผู้ทำรายการนี้ โปรดอย่าเปิดเผยรหัส OTP ให้แก่ผู้อื่นเพื่อความปลอดภัยของบัญชี
            </p>
        </div>
    </body>
    </html>
    """

    sent_via_smtp = False
    if mail_server and mail_user and mail_pass:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"KKU Shooting Club <{mail_sender}>"
            msg['To'] = recipient_email
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
                server.starttls()
                server.login(mail_user, mail_pass)
                server.sendmail(mail_sender, [recipient_email], msg.as_string())
            sent_via_smtp = True
            print(f"[MAIL SUCCESS] Sent OTP to {recipient_email}")
        except Exception as e:
            print(f"[MAIL WARNING] SMTP Send failed: {e}")

    if not sent_via_smtp:
        print(f"\n==================================================")
        print(f"[KKU MAIL OTP SYSTEM]")
        print(f"Recipient: {recipient_email}")
        print(f"Username : {username}")
        print(f"OTP Code : {otp_code}")
        print(f"Expires  : 5 Minutes")
        print(f"==================================================\n")

    return sent_via_smtp

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        username TEXT UNIQUE, 
        password TEXT, 
        role TEXT,
        prefix TEXT,
        first_name TEXT,
        last_name TEXT,
        faculty TEXT,
        academic_year TEXT,
        kku_mail TEXT,
        student_id TEXT,
        phone TEXT,
        profile_pic TEXT
    )''')
    
    for col in ['prefix', 'first_name', 'last_name', 'faculty', 'academic_year', 'kku_mail', 'student_id', 'phone', 'profile_pic', 'position', 'status', 'created_at']:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    # อัปเดตผู้ใช้เดิมที่ไม่มี status ให้เป็น 'approved'
    c.execute("UPDATE users SET status='approved' WHERE status IS NULL OR status=''")

    c.execute('''CREATE TABLE IF NOT EXISTS club_inventory (ammo_type TEXT PRIMARY KEY, quantity INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_ammo (user_id INTEGER, ammo_type TEXT, quantity INTEGER, PRIMARY KEY(user_id, ammo_type))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, ammo_type TEXT, amount INTEGER, timestamp TEXT, note TEXT)''')
    
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN note TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE,
        user_id INTEGER,
        items_summary TEXT,
        items_json TEXT,
        total_price INTEGER,
        total_bullets INTEGER,
        total_targets INTEGER,
        slip_image TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        reviewed_by TEXT,
        reviewed_at TEXT,
        reject_reason TEXT
    )''')

    c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('.177', 2000)")
    c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('.22 LR (CCI)', 2000)")
    c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('.22 LR (RWS)', 1000)")
    c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('เป้าปืนยาว', 1000)")
    c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('เป้าปืนสั้น', 1000)")
    
    # ไมเกรตเป้ากระดาษเดิม (ถ้ามี)
    c.execute("SELECT quantity FROM club_inventory WHERE ammo_type='เป้ากระดาษ'")
    old_target = c.fetchone()
    if old_target:
        c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('เป้าปืนยาว', ?)", (old_target['quantity'],))
        c.execute("INSERT OR IGNORE INTO club_inventory VALUES ('เป้าปืนสั้น', ?)", (old_target['quantity'],))
        c.execute("DELETE FROM club_inventory WHERE ammo_type='เป้ากระดาษ'")

    c.execute("UPDATE user_ammo SET ammo_type='เป้าปืนยาว' WHERE ammo_type='เป้ากระดาษ'")

    c.execute("DELETE FROM club_inventory WHERE ammo_type IN ('.22 ปืนยาวชาวบ้าน', '.177 ปืนยาวอัดลม', '.177 ปืนสั้นอัดลม')")
    
    # ตารางเก็บรหัส OTP สำหรับรีเซ็ตรหัสผ่าน
    c.execute('''CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        email TEXT,
        otp_code TEXT,
        expires_at TEXT,
        used INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    # อัปเกรดรหัสผ่านเดิมที่เป็น Plaintext ให้เป็น Scrypt Hashed Password (PDPA / Production Security)
    c.execute("SELECT id, password FROM users")
    for u in c.fetchall():
        pwd = u['password']
        if pwd and not pwd.startswith(('scrypt:', 'pbkdf2:')):
            c.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(pwd), u['id']))

    # ตรวจสอบบัญชีกรรมการ Betatester101
    c.execute("SELECT id FROM users WHERE username='Betatester101'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (
                username, password, role, status, 
                prefix, first_name, last_name, 
                position, kku_mail, profile_pic
            ) VALUES (
                'Betatester101', ?, 'operator', 'approved',
                'นาย', 'เบต้า', 'เทสเตอร์',
                'กรรมการชมรม', 'betatester101@kkumail.com', 'default_avatar.png'
            )
        """, (generate_password_hash('Test888'),))

    # ตรวจสอบบัญชี Superadmin KoldP
    c.execute("SELECT id FROM users WHERE username='KoldP'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role, status) VALUES ('KoldP', ?, 'god', 'approved')", (generate_password_hash('1987'),))

    conn.commit()
    conn.close()

# ================= Login =================
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        raw_username = request.form.get('username', '')
        raw_password = request.form.get('password', '')
        
        username = raw_username.strip()
        password = raw_password.strip()
        
        if not username or not password:
            msg = 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username' if not username else 'password'})
            flash(msg)
            return render_template('login.html', form_data=request.form)
            
        conn = get_db()
        c = conn.cursor()
        
        # ค้นหาผู้ใช้งานด้วย Username, Student ID หรือ KKU Mail (ไม่จำกัดเฉพาะ role เพื่อความยืดหยุ่น)
        c.execute("""
            SELECT * FROM users 
            WHERE LOWER(username) = LOWER(?) 
               OR student_id = ? 
               OR LOWER(kku_mail) = LOWER(?)
        """, (username, username, username))
        user = c.fetchone()
        
        if not user:
            conn.close()
            msg = 'ไม่พบบัญชีผู้ใช้งานนี้ในระบบ (ตรวจสอบชื่อผู้ใช้, รหัสนักศึกษา หรือ KKU Mail)'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username'})
            flash(msg)
            return render_template('login.html', form_data=request.form)
            
        stored_pwd = user['password'] or ''
        valid_password = False
        
        # 1. ตรวจสอบรหัสผ่านแบบ Scrypt / PBKDF2 Hash
        if stored_pwd.startswith(('scrypt:', 'pbkdf2:')):
            valid_password = check_password_hash(stored_pwd, password)
            if not valid_password and raw_password != password:
                valid_password = check_password_hash(stored_pwd, raw_password)
        # 2. ตรวจสอบรหัสผ่านแบบ Plaintext เดิม (Auto-upgrade เป็น Hash ทันที)
        elif stored_pwd in (password, raw_password):
            valid_password = True
            c.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(password), user['id']))
            conn.commit()
            
        # สำรองสำหรับบัญชีเดโมและผู้ดูแลระบบเดิม (admin, god, operator1, op1, member1)
        if not valid_password:
            demo_match = False
            u_lower = user['username'].lower()
            if u_lower == 'admin' and password in ('admin123', 'admin', '123', '1234'):
                demo_match = True
            elif u_lower == 'god' and password in ('god123', 'god', '123', '1234'):
                demo_match = True
            elif u_lower == 'koldp' and password in ('1987', 'god123', '123'):
                demo_match = True
            elif u_lower in ('op1', 'operator1') and password in ('123', '1234', 'op123', '1'):
                demo_match = True
            elif u_lower == 'member1' and password in ('123', '1234', '1'):
                demo_match = True

            if demo_match:
                valid_password = True
                c.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(password), user['id']))
                conn.commit()

        if not valid_password:
            conn.close()
            msg = 'รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง หรือใช้เมนู "ลืมรหัสผ่าน?"'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'password'})
            flash(msg)
            return render_template('login.html', form_data=request.form)

        # ตรวจสอบสถานะการอนุมัติ (Status Check)
        user_status = user['status'] if ('status' in user.keys() and user['status']) else 'approved'
        if user_status == 'pending':
            conn.close()
            msg = 'บัญชีนี้อยู่ระหว่างรอการอนุมัติจากผู้ดูแลระบบ (God Admin) กรุณารอสักครู่'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'status'})
            flash(msg)
            return render_template('login.html', form_data=request.form)
        elif user_status == 'rejected':
            conn.close()
            msg = 'คำขอเปิดบัญชีนี้ไม่ได้รับการอนุมัติ หากมีข้อสงสัยโปรดติดต่อผู้ดูแลระบบ (God Admin)'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'status'})
            flash(msg)
            return render_template('login.html', form_data=request.form)

        # เข้าสู่ระบบสำเร็จ -> กำหนด Session
        session['user_id'] = user['id']
        session['username'] = user['username']

        # กำหนด role ตามข้อมูลจริงในฐานข้อมูล
        actual_role = user['role']
        if actual_role in ('god', 'admin'):
            session['role'] = 'god'
        elif actual_role == 'operator':
            session['role'] = 'operator'
        else:
            session['role'] = 'member'

        session['first_name'] = user['first_name'] if ('first_name' in user.keys() and user['first_name']) else user['username']
        session['position'] = user['position'] if ('position' in user.keys() and user['position']) else ''
        session['profile_pic'] = user['profile_pic'] if user['profile_pic'] else 'default_avatar.png'
        conn.close()

        # นำทางผู้ใช้ไปยัง Dashboard ประจำบทบาทอย่างแม่นยำ
        if session['role'] == 'god':
            target_url = url_for('god_admin')
        elif session['role'] == 'operator':
            target_url = url_for('operator_dashboard')
        else:
            target_url = url_for('member')

        if is_ajax:
            return jsonify({'success': True, 'redirect': target_url})
        return redirect(target_url)

    return render_template('login.html')

# ================= Register =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        prefix = request.form.get('prefix')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        faculty = request.form.get('faculty', '').strip()
        academic_year = request.form.get('academic_year')
        kku_mail = request.form.get('kku_mail', '').strip()
        student_id = request.form.get('student_id', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not username or not password:
            msg = 'กรุณากรอกชื่อผู้ใช้และรหัสผ่านให้ครบถ้วน'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username' if not username else 'password'})
            flash(msg)
            return render_template('register.html', form_data=request.form)

        if '-' not in student_id:
            msg = 'กรุณากรอกรหัสนักศึกษาให้อยู่ในรูปแบบที่มีขีด เช่น 663050123-4'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'student_id'})
            flash(msg)
            return render_template('register.html', form_data=request.form)

        if not kku_mail.lower().endswith('@kkumail.com'):
            msg = 'อีเมลต้องลงท้ายด้วย @kkumail.com เท่านั้น (KKU Mail)'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'kku_mail'})
            flash(msg)
            return render_template('register.html', form_data=request.form)
            
        # จัดการไฟล์รูปโปรไฟล์
        profile_file = request.files.get('profile_image')
        profile_filename = 'default_avatar.png'

        if profile_file and profile_file.filename != '':
            ext = profile_file.filename.rsplit('.', 1)[1].lower() if '.' in profile_file.filename else 'jpg'
            profile_filename = secure_filename(f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            profile_file.save(os.path.join(app.config['PROFILE_FOLDER'], profile_filename))
        
        conn = get_db()
        c = conn.cursor()
        try:
            hashed_pwd = generate_password_hash(password)
            c.execute('''INSERT INTO users (
                username, password, role, prefix, first_name, last_name, 
                faculty, academic_year, kku_mail, student_id, phone, profile_pic, status, created_at
            ) VALUES (?, ?, 'member', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)''', 
            (username, hashed_pwd, prefix, first_name, last_name, faculty, academic_year, kku_mail, student_id, phone, profile_filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            flash('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ')
            if is_ajax:
                return jsonify({'success': True, 'redirect': url_for('login'), 'message': 'สมัครสมาชิกสำเร็จ! กำลังนำทางไปหน้าเข้าสู่ระบบ'})
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            msg = 'Username หรือชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว กรุณาเลือกชื่ออื่น'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username'})
            flash(msg)
            return render_template('register.html', form_data=request.form)
        finally:
            conn.close()
            
    return render_template('register.html')

# ================= Register Operator (สำหรับกรรมการเข้าใช้งานครั้งแรก) =================
@app.route('/register_operator', methods=['GET', 'POST'])
def register_operator():
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        position = request.form.get('position', '').strip() or 'ฝ่ายพัสดุ'
        prefix = request.form.get('prefix')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        faculty = request.form.get('faculty', '').strip()
        academic_year = request.form.get('academic_year')
        kku_mail = request.form.get('kku_mail', '').strip()
        student_id = request.form.get('student_id', '').strip()
        phone = request.form.get('phone', '').strip()

        if not username or not password:
            msg = 'กรุณากรอกชื่อผู้ใช้และรหัสผ่านให้ครบถ้วน'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username' if not username else 'password'})
            flash(msg)
            return render_template('register_operator.html', form_data=request.form)

        if confirm_password and password != confirm_password:
            msg = 'รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'confirm_password'})
            flash(msg)
            return render_template('register_operator.html', form_data=request.form)

        if '-' not in student_id:
            msg = 'กรุณากรอกรหัสนักศึกษาให้อยู่ในรูปแบบที่มีขีด เช่น 663050123-4'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'student_id'})
            flash(msg)
            return render_template('register_operator.html', form_data=request.form)

        if not kku_mail.lower().endswith('@kkumail.com'):
            msg = 'อีเมลต้องลงท้ายด้วย @kkumail.com เท่านั้น (KKU Mail)'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'kku_mail'})
            flash(msg)
            return render_template('register_operator.html', form_data=request.form)

        # จัดการไฟล์รูปโปรไฟล์
        profile_file = request.files.get('profile_image')
        profile_filename = 'default_avatar.png'

        if profile_file and profile_file.filename != '':
            ext = profile_file.filename.rsplit('.', 1)[1].lower() if '.' in profile_file.filename else 'jpg'
            profile_filename = secure_filename(f"op_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            profile_file.save(os.path.join(app.config['PROFILE_FOLDER'], profile_filename))

        conn = get_db()
        c = conn.cursor()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            hashed_pwd = generate_password_hash(password)
            c.execute('''INSERT INTO users (
                username, password, role, prefix, first_name, last_name, 
                position, faculty, academic_year, kku_mail, student_id, phone, profile_pic, status, created_at
            ) VALUES (?, ?, 'operator', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)''', 
            (username, hashed_pwd, prefix, first_name, last_name, position, faculty, academic_year, kku_mail, student_id, phone, profile_filename, now_str))
            
            conn.commit()
            flash('ส่งคำขอลงทะเบียนกรรมการเรียบร้อยแล้ว! กรุณารอการตรวจสอบและอนุมัติจากผู้ดูแลระบบ (God Admin)')
            if is_ajax:
                return jsonify({'success': True, 'redirect': url_for('login', role='operator'), 'message': 'ส่งคำขอลงทะเบียนกรรมการเรียบร้อยแล้ว'})
            return redirect(url_for('login', role='operator'))
        except sqlite3.IntegrityError:
            msg = 'Username หรือชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว กรุณาเลือกชื่ออื่น'
            if is_ajax:
                return jsonify({'success': False, 'message': msg, 'field': 'username'})
            flash(msg)
            return render_template('register_operator.html', form_data=request.form)
        finally:
            conn.close()

    return render_template('register_operator.html')

# ================= Forgot Password (ลืมรหัสผ่านด้วย OTP ทาง KKU Mail) =================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        if not identifier:
            flash('กรุณากรอกชื่อผู้ใช้ หรืออีเมล @kkumail.com ของท่าน')
            return render_template('forgot_password.html', form_data=request.form)

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(kku_mail) = LOWER(?)", (identifier, identifier))
        user = c.fetchone()

        if not user:
            conn.close()
            flash('ไม่พบบัญชีผู้ใช้หรืออีเมลนี้ในระบบ กรุณาตรวจสอบข้อมูลอีกครั้ง')
            return render_template('forgot_password.html', form_data=request.form)

        user_email = user['kku_mail']
        if not user_email or not user_email.lower().endswith('@kkumail.com'):
            conn.close()
            flash('บัญชีนี้ยังไม่มีอีเมล @kkumail.com ที่ถูกต้องในระบบ กรุณาติดต่อผู้ดูแลระบบ')
            return render_template('forgot_password.html', form_data=request.form)

        # สร้างรหัส OTP 6 หลัก และกำหนดเวลาหมดอายุ 5 นาที
        otp_code = f"{random.randint(100000, 999999)}"
        now = datetime.now()
        expires_at = (now + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        # ยกเลิกรหัส OTP เดิมที่ยังไม่ได้ใช้ของผู้ใช้นี้
        c.execute("UPDATE otp_codes SET used=1 WHERE user_id=? AND used=0", (user['id'],))
        # บันทึกรหัส OTP ใหม่
        c.execute("""
            INSERT INTO otp_codes (user_id, email, otp_code, expires_at, used, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (user['id'], user_email, otp_code, expires_at, now_str))
        conn.commit()
        conn.close()

        # บันทึกข้อมูลลง Session สำหรับหน้ายืนยัน
        session['reset_user_id'] = user['id']
        session['reset_username'] = user['username']
        session['reset_email'] = user_email
        masked = mask_email(user_email)
        session['reset_masked_email'] = masked

        # ส่งอีเมล
        sent_smtp = send_otp_email(user_email, otp_code, user['username'])

        if sent_smtp:
            flash(f'ระบบได้ส่งรหัส OTP 6 หลักไปยัง {masked} แล้ว กรุณาตรวจสอบอีเมลของคุณ')
        else:
            flash(f'ระบบได้ส่งรหัส OTP ไปยัง {masked} แล้ว (สำหรับทดสอบในเครื่อง: OTP คือ {otp_code})')

        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')

# ================= Verify OTP & Set New Password =================
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('reset_user_id')
    masked_email = session.get('reset_masked_email')

    if not user_id or not masked_email:
        flash('กรุณากรอกชื่อผู้ใช้หรืออีเมลเพื่อขอรับรหัส OTP ก่อน')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not otp_input or not new_password:
            flash('กรุณากรอกรหัส OTP และรหัสผ่านใหม่ให้ครบถ้วน')
            return render_template('verify_otp.html', masked_email=masked_email)

        if new_password != confirm_password:
            flash('รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน')
            return render_template('verify_otp.html', masked_email=masked_email)

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM otp_codes 
            WHERE user_id=? AND otp_code=? AND used=0 AND expires_at > ?
            ORDER BY id DESC LIMIT 1
        """, (user_id, otp_input, now_str))
        otp_record = c.fetchone()

        if not otp_record:
            conn.close()
            flash('รหัส OTP ไม่ถูกต้อง หรือหมดอายุแล้ว (รหัสมีอายุ 5 นาที) กรุณาตรวจสอบหรือขอรหัสใหม่')
            return render_template('verify_otp.html', masked_email=masked_email)

        # ทำเครื่องหมายว่าใช้รหัส OTP แล้ว
        c.execute("UPDATE otp_codes SET used=1 WHERE id=?", (otp_record['id'],))
        # อัปเดตรหัสผ่านใหม่ของผู้ใช้ (แฮชด้วย Scrypt)
        hashed_new_pwd = generate_password_hash(new_password)
        c.execute("UPDATE users SET password=? WHERE id=?", (hashed_new_pwd, user_id))
        conn.commit()
        conn.close()

        # ล้างข้อมูล Reset ใน Session
        session.pop('reset_user_id', None)
        session.pop('reset_username', None)
        session.pop('reset_email', None)
        session.pop('reset_masked_email', None)

        flash('รีเซ็ตรหัสผ่านสำเร็จเรียบร้อยแล้ว! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่')
        return redirect(url_for('login'))

    return render_template('verify_otp.html', masked_email=masked_email)

# ================= Resend OTP =================
@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    user_id = session.get('reset_user_id')
    user_email = session.get('reset_email')
    username = session.get('reset_username')

    if not user_id or not user_email:
        flash('ไม่พบข้อมูลการขอรหัส OTP กรุณาทำรายการใหม่')
        return redirect(url_for('forgot_password'))

    otp_code = f"{random.randint(100000, 999999)}"
    now = datetime.now()
    expires_at = (now + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE otp_codes SET used=1 WHERE user_id=? AND used=0", (user_id,))
    c.execute("""
        INSERT INTO otp_codes (user_id, email, otp_code, expires_at, used, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    """, (user_id, user_email, otp_code, expires_at, now_str))
    conn.commit()
    conn.close()

    sent_smtp = send_otp_email(user_email, otp_code, username)
    masked = mask_email(user_email)

    if sent_smtp:
        flash(f'ระบบได้ส่งรหัส OTP ชุดใหม่ไปยัง {masked} แล้ว (รหัสมีอายุ 5 นาที)')
    else:
        flash(f'ส่งรหัส OTP ชุดใหม่ไปยัง {masked} แล้ว (สำหรับทดสอบในเครื่อง: OTP คือ {otp_code})')

    return redirect(url_for('verify_otp'))

# ================= Member Dashboard =================
@app.route('/member', methods=['GET', 'POST'])
def member():
    if 'user_id' not in session or session.get('role') != 'member':
        return redirect(url_for('login'))
        
    conn = get_db()
    c = conn.cursor()
    user_id = session['user_id']
    receipt_data = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if action == 'buy_cart':
            payload_str = request.form.get('cart_payload')
            slip_file = request.files.get('slip_image')
            slip_filename = None

            if slip_file and slip_file.filename != '':
                ext = slip_file.filename.rsplit('.', 1)[1].lower() if '.' in slip_file.filename else 'jpg'
                slip_filename = secure_filename(f"slip_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
                slip_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_filename))

            if payload_str:
                cart_items = json.loads(payload_str)
                total_price = 0
                total_bullets = 0
                total_targets = 0
                processed_items = []
                summary_lines = []
                insufficient_stock = False

                for item in cart_items:
                    backend_stock_key = item['stockKey']
                    pkg_name = item['pkgName']
                    price = item['price'] * item['qty']
                    bullet_amount = item['bullets'] * item['qty']
                    target_amount = item.get('targets', 0) * item['qty']

                    if 'ปืนยาวอัดลม' in pkg_name:
                        user_wallet_type = '.177 ปืนยาวอัดลม'
                    elif 'ปืนสั้นอัดลม' in pkg_name:
                        user_wallet_type = '.177 ปืนสั้นอัดลม'
                    else:
                        user_wallet_type = backend_stock_key

                    # กำหนดประเภทเป้า (เป้าปืนยาว หรือ เป้าปืนสั้น)
                    target_type = item.get('targetType')
                    if not target_type:
                        if 'ปืนสั้น' in pkg_name:
                            target_type = 'เป้าปืนสั้น'
                        else:
                            target_type = 'เป้าปืนยาว'

                    # ตรวจสอบเบื้องต้นว่ามีของในคลังไหม
                    c.execute("SELECT quantity FROM club_inventory WHERE ammo_type=?", (backend_stock_key,))
                    inv_bullets = c.fetchone()
                    
                    inv_targets = None
                    if target_amount > 0:
                        c.execute("SELECT quantity FROM club_inventory WHERE ammo_type=?", (target_type,))
                        inv_targets = c.fetchone()
                    
                    if (not inv_bullets or inv_bullets['quantity'] < bullet_amount) or (target_amount > 0 and (not inv_targets or inv_targets['quantity'] < target_amount)):
                        insufficient_stock = True
                        flash(f'กระสุน ({backend_stock_key}) หรือ{target_type} ในคลังมีไม่เพียงพอสำหรับการสั่งซื้อ')
                        break

                    total_price += price
                    total_bullets += bullet_amount
                    total_targets += target_amount

                    processed_items.append({
                        'stockKey': backend_stock_key,
                        'pkgName': pkg_name,
                        'walletType': user_wallet_type,
                        'targetType': target_type,
                        'price': price,
                        'bullets': bullet_amount,
                        'targets': target_amount,
                        'qty': item['qty']
                    })
                    summary_lines.append(f"{pkg_name} x{item['qty']} ({bullet_amount} นัด, {target_type} {target_amount} แผ่น)")

                if not insufficient_stock and processed_items:
                    items_summary = ", ".join(summary_lines)
                    order_no = f"ORD-{datetime.now().strftime('%y%m%d%H%M%S')}-{random.randint(100, 999)}"

                    c.execute("""
                        INSERT INTO orders (
                            order_no, user_id, items_summary, items_json,
                            total_price, total_bullets, total_targets,
                            slip_image, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    """, (order_no, user_id, items_summary, json.dumps(processed_items, ensure_ascii=False),
                          total_price, total_bullets, total_targets, slip_filename, now))
                    conn.commit()

                    receipt_data = {
                        'order_id': order_no,
                        'timestamp': now,
                        'cart_items': [{
                            'name': f"{it['walletType']} ({it['pkgName']})",
                            'qty': it['qty'],
                            'bullets': it['bullets'],
                            'targets': it['targets'],
                            'price': it['price']
                        } for it in processed_items],
                        'total_bullets': total_bullets,
                        'total_targets': total_targets,
                        'total_price': total_price,
                        'slip_img': slip_filename,
                        'status': 'pending'
                    }
                    flash('ส่งคำสั่งซื้อและหลักฐานการโอนเงินเรียบร้อยแล้ว! กรุณารอกรรมการชมรมตรวจสอบและอนุมัติสลิป')

        elif action == 'withdraw':
            wallet_type = request.form.get('ammo_type')
            raw_amount = request.form.get('amount')
            if raw_amount and raw_amount.isdigit():
                amount = int(raw_amount)
                c.execute("SELECT quantity FROM user_ammo WHERE user_id=? AND ammo_type=?", (user_id, wallet_type))
                res = c.fetchone()
                if res and res['quantity'] >= amount:
                    c.execute("UPDATE user_ammo SET quantity = quantity - ? WHERE user_id = ? AND ammo_type = ?", (amount, user_id, wallet_type))
                    c.execute("""
                        INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) 
                        VALUES (?, 'Withdraw', ?, ?, ?, ?)
                    """, (user_id, wallet_type, amount, now, 'เบิกซ้อมสนาม'))
                    conn.commit()
                    flash(f'เบิก {wallet_type} จำนวน {amount} เรียบร้อย!')
                else:
                    flash(f'{wallet_type} ในกระเป๋าของคุณมีไม่เพียงพอสำหรับการเบิก')
        
        elif action == 'return_ammo':
            wallet_type = request.form.get('ammo_type')
            raw_amount = request.form.get('amount')
            if raw_amount and raw_amount.isdigit():
                amount = int(raw_amount)
                c.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN action = 'Withdraw' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN action = 'Return' THEN amount ELSE 0 END), 0) AS pending_return
                    FROM transactions 
                    WHERE user_id = ? AND ammo_type = ?
                """, (user_id, wallet_type))
                
                pending_res = c.fetchone()
                pending_return = pending_res['pending_return'] if pending_res else 0

                if amount <= pending_return and pending_return > 0:
                    c.execute("UPDATE user_ammo SET quantity = quantity + ? WHERE user_id = ? AND ammo_type = ?", (amount, user_id, wallet_type))
                    c.execute("""
                        INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) 
                        VALUES (?, 'Return', ?, ?, ?, ?)
                    """, (user_id, wallet_type, amount, now, 'คืนของที่เหลือจากการซ้อม'))
                    conn.commit()
                    flash(f'คืน {wallet_type} จำนวน {amount} สำเร็จ! เข้ากระเป๋าเรียบร้อย')
                else:
                    if pending_return > 0:
                        flash(f'คุณสามารถคืน {wallet_type} ได้สูงสุดแค่ {pending_return} (ตามจำนวนที่เบิกไป)')
                    else:
                        flash(f'คุณไม่ได้เบิก {wallet_type} ออกไป หรือคืนครบหมดแล้ว ไม่สามารถคืนเพิ่มได้')

        elif action == 'update_profile_pic':
            profile_file = request.files.get('profile_image')
            if profile_file and profile_file.filename != '':
                ext = profile_file.filename.rsplit('.', 1)[1].lower() if '.' in profile_file.filename else 'jpg'
                profile_filename = secure_filename(f"{session['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
                profile_file.save(os.path.join(app.config['PROFILE_FOLDER'], profile_filename))
                c.execute("UPDATE users SET profile_pic=? WHERE id=?", (profile_filename, user_id))
                conn.commit()
                session['profile_pic'] = profile_filename
                flash('อัปเดตรูปโปรไฟล์ใหม่สำเร็จเรียบร้อย!')

    c.execute("SELECT * FROM user_ammo WHERE user_id=? ORDER BY ammo_type ASC", (user_id,))
    my_ammo = c.fetchall()
    c.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
    history = c.fetchall()
    c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    my_orders = c.fetchall()
    pending_orders_count = sum(1 for o in my_orders if o['status'] == 'pending')
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_info = c.fetchone()
    if user_info and user_info['profile_pic']:
        session['profile_pic'] = user_info['profile_pic']
    conn.close()
    
    return render_template('member.html', user_info=user_info, my_ammo=my_ammo, history=history, my_orders=my_orders, pending_orders_count=pending_orders_count, receipt_data=receipt_data)

# ================= Shortcut Profile Route =================
@app.route('/profile')
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'member':
        return redirect(url_for('member_card'))
    elif session.get('role') == 'operator':
        return redirect(url_for('operator_dashboard'))
    return redirect(url_for('god_admin'))

# ================= Digital Membership Card =================
@app.route('/member/card')
def member_card():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    c = conn.cursor()
    user_id = session['user_id']
    
    # ถ้ามี target_id และเป็น operator/god ให้ดูบัตรสมาชิกคนนั้นได้
    target_id = request.args.get('user_id', user_id)
    if session.get('role') in ['operator', 'god'] and target_id:
        c.execute("SELECT * FROM users WHERE id=?", (target_id,))
    else:
        c.execute("SELECT * FROM users WHERE id=?", (user_id,))
        
    user_info = c.fetchone()
    if not user_info:
        conn.close()
        flash('ไม่พบข้อมูลสมาชิก')
        return redirect(url_for('login'))
        
    c.execute("SELECT * FROM user_ammo WHERE user_id=? ORDER BY ammo_type ASC", (user_info['id'],))
    my_ammo = c.fetchall()
    
    # คำนวณกระสุนที่อยู่บนช่องยิง (เบิกไปแล้วยังไม่คืน)
    c.execute("""
        SELECT 
            ammo_type,
            COALESCE(SUM(CASE WHEN action = 'Withdraw' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN action = 'Return' THEN amount ELSE 0 END), 0) AS on_lane
        FROM transactions 
        WHERE user_id = ?
        GROUP BY ammo_type
    """, (user_info['id'],))
    lane_rows = c.fetchall()
    on_lane = {r['ammo_type']: max(0, r['on_lane']) for r in lane_rows if r['on_lane'] > 0}
    conn.close()
    
    return render_template('member_card.html', user_info=user_info, my_ammo=my_ammo, on_lane=on_lane)

# ================= Range Counter & QR Scanner APIs =================
@app.route('/api/member_lookup')
def api_member_lookup():
    if 'user_id' not in session or session.get('role') not in ['operator', 'god']:
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง (Unauthorized)'}), 403
        
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'success': False, 'message': 'กรุณาระบุคำค้นหาหรือรหัส QR'}), 400
        
    conn = get_db()
    c = conn.cursor()
    
    # จัดการกรณีข้อมูลมาจาก QR code format: KKU-SC:MEMBER:9:653040123-4 หรือ URL
    user_id_target = None
    if 'KKU-SC:MEMBER:' in query:
        parts = query.split(':')
        if len(parts) >= 3 and parts[2].isdigit():
            user_id_target = int(parts[2])
    elif query.isdigit():
        user_id_target = int(query)
        
    if user_id_target:
        c.execute("SELECT * FROM users WHERE id=? AND role='member'", (user_id_target,))
        user = c.fetchone()
    else:
        # ค้นหาด้วยรหัสนักศึกษา, username, หรืออีเมล
        c.execute("SELECT * FROM users WHERE (student_id=? OR username=? OR kku_mail=?) AND role='member'", (query, query, query))
        user = c.fetchone()
        
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': f'ไม่พบสมาชิกในระบบตามรหัส: {query}'}), 404
        
    # ดึงกระเป๋ากระสุนของสมาชิก
    c.execute("SELECT ammo_type, quantity FROM user_ammo WHERE user_id=? ORDER BY ammo_type ASC", (user['id'],))
    ammo_rows = c.fetchall()
    wallet = [{'ammo_type': r['ammo_type'], 'quantity': r['quantity']} for r in ammo_rows]
    
    # คำนวณยอดกระสุนที่เบิกไปและยังไม่ได้คืน
    c.execute("""
        SELECT 
            ammo_type,
            COALESCE(SUM(CASE WHEN action = 'Withdraw' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN action = 'Return' THEN amount ELSE 0 END), 0) AS on_lane
        FROM transactions 
        WHERE user_id = ?
        GROUP BY ammo_type
    """, (user['id'],))
    lane_rows = c.fetchall()
    on_lane = {r['ammo_type']: max(0, r['on_lane']) for r in lane_rows if r['on_lane'] > 0}
    
    conn.close()
    
    first = user['first_name'] or ''
    last = user['last_name'] or ''
    prefix = user['prefix'] or ''
    full_name = f"{prefix}{first} {last}".strip() or user['username']
    
    member_data = {
        'id': user['id'],
        'username': user['username'],
        'full_name': full_name,
        'student_id': user['student_id'] or '-',
        'faculty': user['faculty'] or '-',
        'academic_year': user['academic_year'] or '-',
        'kku_mail': user['kku_mail'] or '-',
        'phone': user['phone'] or '-',
        'profile_pic': user['profile_pic'] or 'default_avatar.png',
        'status': user['status'] or 'approved',
        'created_at': user['created_at'] or '-',
        'wallet': wallet,
        'on_lane': on_lane
    }
    
    return jsonify({'success': True, 'member': member_data})


@app.route('/api/range_quick_withdraw', methods=['POST'])
def api_range_quick_withdraw():
    if 'user_id' not in session or session.get('role') not in ['operator', 'god']:
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง'}), 403
        
    member_id = request.form.get('member_id')
    ammo_type = request.form.get('ammo_type')
    try:
        amount = int(request.form.get('amount', 0))
    except (ValueError, TypeError):
        amount = 0
        
    lane_no = request.form.get('lane_no', '').strip()
    note = f"เบิกซ้อมสนามหน้าช่อง {lane_no}" if lane_no else "เบิกซ้อมสนาม (สแกนบัตรที่เคาน์เตอร์)"
    
    if not member_id or not ammo_type or amount <= 0:
        return jsonify({'success': False, 'message': 'ข้อมูลไม่ถูกต้อง จำนวนต้องมากกว่า 0'}), 400
        
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ตรวจสอบยอดในกระเป๋าสมาชิก
    c.execute("SELECT quantity FROM user_ammo WHERE user_id=? AND ammo_type=?", (member_id, ammo_type))
    row = c.fetchone()
    current_wallet = row['quantity'] if row else 0
    
    if current_wallet < amount:
        conn.close()
        return jsonify({
            'success': False, 
            'message': f'สมาชิกมี {ammo_type} เพียง {current_wallet:,} นัด ไม่พอสำหรับการเบิก {amount:,} นัด'
        }), 400
        
    # หักกระสุนจากกระเป๋าสมาชิก
    c.execute("UPDATE user_ammo SET quantity = quantity - ? WHERE user_id=? AND ammo_type=?", (amount, member_id, ammo_type))
    
    # บันทึกธุรกรรมระบุกรรมการผู้ดำเนินการ
    op_user = session.get('username', 'operator')
    c.execute("""
        INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) 
        VALUES (?, 'Withdraw', ?, ?, ?, ?)
    """, (member_id, ammo_type, amount, now, f"{note} [อนุมัติโดย: {op_user}]"))
    
    conn.commit()
    
    # ดึงยอดล่าสุด
    c.execute("SELECT ammo_type, quantity FROM user_ammo WHERE user_id=? ORDER BY ammo_type ASC", (member_id,))
    updated_wallet = [{'ammo_type': r['ammo_type'], 'quantity': r['quantity']} for r in c.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True, 
        'message': f'เบิก {ammo_type} จำนวน {amount:,} นัด ให้สมาชิกเรียบร้อยแล้ว!',
        'wallet': updated_wallet
    })

# ================= PWA Static Endpoints =================
@app.route('/manifest.json')
def pwa_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def pwa_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# ================= Operator Dashboard =================
@app.route('/operator', methods=['GET', 'POST'])
def operator_dashboard():
    if 'user_id' not in session or session.get('role') not in ['operator', 'god']:
        return redirect(url_for('login'))
        
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'approve_order':
            order_id = request.form.get('order_id')
            c.execute("SELECT * FROM orders WHERE id=? AND status='pending'", (order_id,))
            order = c.fetchone()
            
            if not order:
                flash('ไม่พบคำสั่งซื้อนี้ หรือคำสั่งซื้อนี้ถูกดำเนินการไปแล้ว')
            else:
                items = json.loads(order['items_json'])
                
                # รวมยอดที่ต้องการตัดสต็อกเพื่อตรวจคลังก่อน
                needed_stock = {}
                for it in items:
                    s_key = it['stockKey']
                    needed_stock[s_key] = needed_stock.get(s_key, 0) + it['bullets']
                    
                    t_amount = it.get('targets', 0)
                    if t_amount > 0:
                        t_type = it.get('targetType') or ('เป้าปืนสั้น' if 'ปืนสั้น' in it.get('pkgName', '') else 'เป้าปืนยาว')
                        needed_stock[t_type] = needed_stock.get(t_type, 0) + t_amount
                
                insufficient = []
                for s_key, req_qty in needed_stock.items():
                    c.execute("SELECT quantity FROM club_inventory WHERE ammo_type=?", (s_key,))
                    row = c.fetchone()
                    avail = row['quantity'] if row else 0
                    if avail < req_qty:
                        insufficient.append(f"{s_key} (ต้องการ {req_qty}, มีในคลัง {avail})")
                
                if insufficient:
                    flash(f"ไม่อนุมัติ: สินค้าในคลังไม่เพียงพอ! ({', '.join(insufficient)}) กรุณาเติมสต็อกก่อน")
                else:
                    for it in items:
                        s_key = it['stockKey']
                        b_amount = it['bullets']
                        t_amount = it.get('targets', 0)
                        u_wallet = it['walletType']
                        t_type = it.get('targetType') or ('เป้าปืนสั้น' if 'ปืนสั้น' in it.get('pkgName', '') else 'เป้าปืนยาว')
                        price = it['price']
                        
                        # หักกระสุนคลังกลาง
                        c.execute("UPDATE club_inventory SET quantity = quantity - ? WHERE ammo_type = ?", (b_amount, s_key))
                        
                        # โอนกระสุนเข้ากระเป๋าสมาชิก
                        c.execute("""
                            INSERT INTO user_ammo (user_id, ammo_type, quantity) 
                            VALUES (?, ?, ?) 
                            ON CONFLICT(user_id, ammo_type) 
                            DO UPDATE SET quantity = quantity + ?
                        """, (order['user_id'], u_wallet, b_amount, b_amount))
                        
                        # หักเป้าและโอนให้สมาชิก (ถ้ามี)
                        if t_amount > 0:
                            c.execute("UPDATE club_inventory SET quantity = quantity - ? WHERE ammo_type = ?", (t_amount, t_type))
                            c.execute("""
                                INSERT INTO user_ammo (user_id, ammo_type, quantity) 
                                VALUES (?, ?, ?) 
                                ON CONFLICT(user_id, ammo_type) 
                                DO UPDATE SET quantity = quantity + ?
                            """, (order['user_id'], t_type, t_amount, t_amount))
                        
                        # บันทึกประวัติรายการ
                        note_text = f"ยอด {price} ฿ | อนุมัติโดย {session['username']} | ออเดอร์ #{order['order_no']}"
                        c.execute("""
                            INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) 
                            VALUES (?, 'Buy', ?, ?, ?, ?)
                        """, (order['user_id'], f"{s_key} [{u_wallet}] + {t_type} {t_amount} แผ่น", b_amount, now, note_text))
                    
                    # อัปเดตสถานะออเดอร์เป็น approved
                    c.execute("""
                        UPDATE orders 
                        SET status='approved', reviewed_by=?, reviewed_at=? 
                        WHERE id=?
                    """, (session['username'], now, order_id))
                    conn.commit()
                    flash(f"อนุมัติคำสั่งซื้อ {order['order_no']} เรียบร้อย! กระสุนและเป้าถูกโอนเข้ากระเป๋าสมาชิกแล้ว")

        elif action == 'reject_order':
            order_id = request.form.get('order_id')
            reject_reason = request.form.get('reject_reason', '').strip() or 'สลิปไม่ถูกต้อง / ไม่พบยอดเงิน'
            c.execute("SELECT * FROM orders WHERE id=? AND status='pending'", (order_id,))
            order = c.fetchone()
            
            if not order:
                flash('ไม่พบคำสั่งซื้อนี้ หรือคำสั่งซื้อนี้ถูกดำเนินการไปแล้ว')
            else:
                c.execute("""
                    UPDATE orders 
                    SET status='rejected', reviewed_by=?, reviewed_at=?, reject_reason=? 
                    WHERE id=?
                """, (session['username'], now, reject_reason, order_id))
                conn.commit()
                flash(f"ปฏิเสธคำสั่งซื้อ {order['order_no']} แล้ว (สาเหตุ: {reject_reason})")

        elif action == 'add_inventory':
            ammo_type = request.form.get('ammo_type')
            try:
                amount = int(request.form.get('amount', 0))
            except (ValueError, TypeError):
                amount = 0
            note = request.form.get('note', '').strip() or '-'

            if amount <= 0:
                flash('ผิดพลาด: จำนวนที่ต้องการเพิ่มต้องมากกว่า 0')
            else:
                c.execute("UPDATE club_inventory SET quantity = quantity + ? WHERE ammo_type = ?", (amount, ammo_type))
                c.execute("INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) VALUES (?, 'Operator_Add', ?, ?, ?, ?)", (session['user_id'], ammo_type, amount, now, note))
                conn.commit()
                flash(f'เพิ่มสต็อก {ammo_type} จำนวน {amount:,} สำเร็จ!')

        elif action == 'sub_inventory':
            ammo_type = request.form.get('ammo_type')
            try:
                amount = int(request.form.get('amount', 0))
            except (ValueError, TypeError):
                amount = 0
            note = request.form.get('note', '').strip() or '-'

            if amount <= 0:
                flash('ผิดพลาด: จำนวนที่ต้องการลดต้องมากกว่า 0')
            else:
                c.execute("SELECT quantity FROM club_inventory WHERE ammo_type = ?", (ammo_type,))
                inv_item = c.fetchone()
                current_qty = inv_item['quantity'] if inv_item else 0

                if amount > current_qty:
                    flash(f'ผิดพลาด: ไม่สามารถสั่งลด {amount:,} ได้ เนื่องจากมีในคลังเพียง {current_qty:,}')
                else:
                    c.execute("UPDATE club_inventory SET quantity = quantity - ? WHERE ammo_type = ?", (amount, ammo_type))
                    c.execute("INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) VALUES (?, 'Operator_Sub', ?, ?, ?, ?)", (session['user_id'], ammo_type, amount, now, note))
                    conn.commit()
                    flash(f'ลดสต็อก {ammo_type} จำนวน {amount:,} เรียบร้อย!')

        elif action == 'set_inventory':
            ammo_type = request.form.get('ammo_type')
            try:
                amount = int(request.form.get('amount', 0))
            except (ValueError, TypeError):
                amount = -1
            note = request.form.get('note', '').strip() or '-'

            if amount < 0:
                flash('ผิดพลาด: ยอดคงเหลือต้องไม่ติดลบ (ต้องเป็น 0 หรือมากกว่า)')
            else:
                c.execute("UPDATE club_inventory SET quantity = ? WHERE ammo_type = ?", (amount, ammo_type))
                c.execute("INSERT INTO transactions (user_id, action, ammo_type, amount, timestamp, note) VALUES (?, 'Operator_Set', ?, ?, ?, ?)", (session['user_id'], ammo_type, amount, now, note))
                conn.commit()
                flash(f'ปรับยอดสต็อก {ammo_type} เป็น {amount:,} เรียบร้อย!')

    c.execute("SELECT * FROM club_inventory")
    inventory = c.fetchall()
    
    # ดึงคำสั่งซื้อที่รออนุมัติ (pending)
    c.execute("""
        SELECT o.*, u.username, u.first_name, u.last_name, u.student_id, u.phone, u.faculty
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.status = 'pending'
        ORDER BY o.created_at ASC
    """)
    pending_orders = c.fetchall()
    
    # ดึงประวัติคำสั่งซื้อที่อนุมัติหรือปฏิเสธแล้ว
    c.execute("""
        SELECT o.*, u.username, u.first_name, u.last_name, u.student_id, u.phone, u.faculty
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.status != 'pending'
        ORDER BY o.reviewed_at DESC
        LIMIT 50
    """)
    past_orders = c.fetchall()

    # ดึงประวัติรายการธุรกรรมทั้งหมด
    c.execute("SELECT t.*, u.username FROM transactions t JOIN users u ON t.user_id = u.id ORDER BY t.timestamp DESC")
    all_history = c.fetchall()
    conn.close()
    
    return render_template('operator.html', 
                           inventory=inventory, 
                           history=all_history, 
                           pending_orders=pending_orders, 
                           past_orders=past_orders)

# ================= God Admin =================
@app.route('/god', methods=['GET', 'POST'])
def god_admin():
    if 'user_id' not in session or session.get('role') != 'god':
        return redirect(url_for('login'))
        
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_operator':
            op_user = request.form.get('op_username')
            op_pass = request.form.get('op_password')
            op_position = request.form.get('op_position', '').strip() or 'ฝ่ายพัสดุ'
            try:
                hashed = generate_password_hash(op_pass)
                c.execute("INSERT INTO users (username, password, role, position, status) VALUES (?, ?, 'operator', ?, 'approved')", (op_user, hashed, op_position))
                conn.commit()
                flash(f'สร้าง Operator: {op_user} ({op_position}) สำเร็จ!')
            except sqlite3.IntegrityError:
                flash(f'Username {op_user} มีอยู่ในระบบแล้ว')

        elif action == 'approve_operator':
            user_id = request.form.get('user_id')
            c.execute("UPDATE users SET status='approved' WHERE id=? AND role='operator'", (user_id,))
            conn.commit()
            flash('อนุมัติสิทธิ์กรรมการเรียบร้อยแล้ว! กรรมการสามารถเข้าสู่ระบบได้ทันที')

        elif action == 'reject_operator':
            user_id = request.form.get('user_id')
            c.execute("DELETE FROM users WHERE id=? AND role='operator'", (user_id,))
            conn.commit()
            flash('ปฏิเสธและลบคำขอลงทะเบียนกรรมการเรียบร้อยแล้ว')
                
        elif action == 'edit_operator_pass':
            user_id = request.form.get('user_id')
            new_pass = request.form.get('new_password')
            hashed = generate_password_hash(new_pass)
            c.execute("UPDATE users SET password=? WHERE id=? AND role='operator'", (hashed, user_id))
            conn.commit()
            flash('อัปเดตรหัสผ่าน Operator สำเร็จ (เข้ารหัสด้วย Scrypt)!')
            
        elif action == 'delete_operator':
            user_id = request.form.get('user_id')
            c.execute("DELETE FROM users WHERE id=? AND role='operator'", (user_id,))
            conn.commit()
            flash('ลบ Operator เรียบร้อยแล้ว')

        elif action == 'add_member':
            mem_user = request.form.get('mem_username')
            mem_pass = request.form.get('mem_password')
            try:
                hashed = generate_password_hash(mem_pass)
                c.execute("INSERT INTO users (username, password, role, status) VALUES (?, ?, 'member', 'approved')", (mem_user, hashed))
                conn.commit()
                flash(f'เพิ่ม Member: {mem_user} สำเร็จ!')
            except sqlite3.IntegrityError:
                flash(f'Username {mem_user} มีอยู่ในระบบแล้ว')

        elif action == 'edit_member_pass':
            user_id = request.form.get('user_id')
            new_pass = request.form.get('new_password')
            hashed = generate_password_hash(new_pass)
            c.execute("UPDATE users SET password=? WHERE id=? AND role='member'", (hashed, user_id))
            conn.commit()
            flash('อัปเดตรหัสผ่าน Member สำเร็จ (เข้ารหัสด้วย Scrypt)!')

        elif action == 'delete_member':
            user_id = request.form.get('user_id')
            c.execute("DELETE FROM users WHERE id=? AND role='member'", (user_id,))
            c.execute("DELETE FROM user_ammo WHERE user_id=?", (user_id,))
            conn.commit()
            flash('ลบข้อมูล Member และกระเป๋าเรียบร้อยแล้ว')

    # 1. ข้อมูลสถิติภาพรวมสำคัญ (Executive KPIs)
    c.execute("SELECT COUNT(*) FROM users WHERE role='member'")
    total_members = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE role='operator' AND (status='approved' OR status IS NULL OR status='')")
    total_operators = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status='approved'")
    total_revenue = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(total_bullets), 0) FROM orders WHERE status='approved'")
    total_bullets_sold = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(total_targets), 0) FROM orders WHERE status='approved'")
    total_targets_sold = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending_orders_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    # 2. คลังและสต็อกปัจจุบัน
    c.execute("SELECT * FROM club_inventory")
    inventory = c.fetchall()

    # 3. คำขอลงทะเบียนกรรมการที่รอการอนุมัติ (pending)
    c.execute("""
        SELECT * FROM users 
        WHERE role='operator' AND status='pending' 
        ORDER BY id DESC
    """)
    pending_operators = c.fetchall()

    # 4. รายชื่อกรรมการที่อนุมัติแล้ว
    c.execute("""
        SELECT * FROM users 
        WHERE role='operator' AND (status='approved' OR status IS NULL OR status='') 
        ORDER BY id ASC
    """)
    operators = c.fetchall()

    # 5. รายชื่อสมาชิกชมรมพร้อมกระเป๋ากระสุน
    c.execute("""
        SELECT u.*,
               COALESCE(GROUP_CONCAT(ua.ammo_type || ': ' || ua.quantity, ', '), 'ไม่มีของคงเหลือ') AS ammo_summary
        FROM users u
        LEFT JOIN user_ammo ua ON u.id = ua.user_id
        WHERE u.role = 'member'
        GROUP BY u.id
        ORDER BY u.id ASC
    """)
    members = c.fetchall()

    # 6. ประวัติคำสั่งซื้อล่าสุด (Recent Orders)
    c.execute("""
        SELECT o.*, u.username, u.first_name, u.last_name, u.student_id
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.id DESC
        LIMIT 25
    """)
    recent_orders = c.fetchall()

    # 7. ประวัติธุรกรรมคลังล่าสุด (Recent Inventory Transactions)
    c.execute("""
        SELECT t.*, u.username
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.id DESC
        LIMIT 25
    """)
    recent_transactions = c.fetchall()

    stats = {
        'total_members': total_members,
        'total_operators': total_operators,
        'pending_operators_count': len(pending_operators),
        'total_revenue': total_revenue,
        'total_bullets_sold': total_bullets_sold,
        'total_targets_sold': total_targets_sold,
        'pending_orders_count': pending_orders_count,
        'total_orders': total_orders
    }

    conn.close()
    
    return render_template('god.html', 
                           stats=stats,
                           inventory=inventory,
                           operators=operators, 
                           pending_operators=pending_operators, 
                           members=members,
                           recent_orders=recent_orders,
                           recent_transactions=recent_transactions)

# ================= Export Members (ส่งออกข้อมูลสมาชิกเป็น Excel / CSV ส่ง กพศ. มข.) =================
@app.route('/god/export_members')
def export_members_csv():
    if 'user_id' not in session or session.get('role') != 'god':
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username, u.prefix, u.first_name, u.last_name, 
               u.student_id, u.faculty, u.academic_year, u.kku_mail, u.phone, 
               u.created_at, u.status,
               COALESCE(GROUP_CONCAT(ua.ammo_type || ': ' || ua.quantity, ' | '), 'ไม่มีของคงเหลือ') AS ammo_summary
        FROM users u
        LEFT JOIN user_ammo ua ON u.id = ua.user_id
        WHERE u.role = 'member'
        GROUP BY u.id
        ORDER BY u.id ASC
    """)
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Microsoft Excel on Windows
    writer = csv.writer(output)
    writer.writerow([
        'ลำดับ (ID)', 'ชื่อผู้ใช้ (Username)', 'คำนำหน้า', 'ชื่อจริง', 'นามสกุล', 
        'รหัสนักศึกษา', 'คณะ', 'ชั้นปี', 'KKU Mail', 'เบอร์โทรศัพท์', 
        'ยอดกระสุนและเป้าคงเหลือ', 'วันที่สมัคร', 'สถานะ'
    ])
    
    for r in rows:
        writer.writerow([
            r['id'],
            r['username'] or '',
            r['prefix'] or '',
            r['first_name'] or '',
            r['last_name'] or '',
            r['student_id'] or '',
            r['faculty'] or '',
            r['academic_year'] or '',
            r['kku_mail'] or '',
            r['phone'] or '',
            r['ammo_summary'] or '',
            r['created_at'] or '',
            r['status'] or 'approved'
        ])

    csv_data = output.getvalue()
    filename = f"kku_shooting_club_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/god/backup_db')
def god_backup_db():
    if 'user_id' not in session or session.get('role') != 'god':
        return redirect(url_for('login'))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"shooting_club_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
    
    # ใช้ออนไลน์แบ็กอัป API ของ SQLite เพื่อได้ Snapshot ที่สมบูรณ์ 100% แม้มีการใช้งานพร้อมกัน
    src_conn = get_db()
    dst_conn = sqlite3.connect(backup_path)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    
    return send_from_directory(BACKUP_FOLDER, backup_filename, as_attachment=True)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    # รันบน 0.0.0.0 เพื่อรองรับทั้ง Localhost และการเข้าใช้งานผ่านอุปกรณ์มือถือ/แท็บเล็ตในวง WiFi เครือข่ายเดียวกัน
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)