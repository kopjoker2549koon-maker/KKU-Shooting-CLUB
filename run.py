import os
import sys
import socket
from datetime import datetime

# Windows terminal UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import app, init_db

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

if __name__ == '__main__':
    print("==================================================================")
    print("  KKU SHOOTING CLUB - PRODUCTION SERVER (มข. เผยแพร่ใช้งานจริง)")
    print("  ชมรมกีฬายิงปืน มหาวิทยาลัยขอนแก่น (Official Release)")
    print("==================================================================")
    
    # 1. Initialize & migrate database
    init_db()
    
    # 2. Network & Server configuration
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    local_ip = get_local_ip()
    
    print(f"\n[INFO] Starting Production WSGI Server (Waitress)...")
    print(f"[*] Local Access      : http://localhost:{port}")
    print(f"[*] Campus / WiFi URL : http://{local_ip}:{port}")
    print(f"[*] Concurrency Mode  : Multi-threaded (8 Worker Threads)")
    print(f"[*] Database Engine   : SQLite Enterprise WAL Concurrency Mode")
    print(f"[*] Digital QR Scanner: Active & PWA Ready")
    print("------------------------------------------------------------------")
    print("  กด [Ctrl + C] ในหน้าต่างนี้เพื่อหยุดการทำงานของเซิร์ฟเวอร์")
    print("==================================================================\n")
    
    try:
        import waitress
        waitress.serve(app, host=host, port=port, threads=8)
    except ImportError:
        print("[WARN] Waitress not found, falling back to standard server.")
        app.run(host=host, port=port, debug=False)
