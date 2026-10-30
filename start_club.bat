@echo off
title KKU Shooting Club - Production Server (Official Release)
echo ========================================================
echo   KKU SHOOTING CLUB MANAGEMENT SYSTEM (มข. เผยแพร่จริง)
echo   กำลังเริ่มต้นเซิร์ฟเวอร์แบบ Production (Waitress Multi-threaded)...
echo ========================================================

:: รอให้ Production Server บูตเสร็จสมบูรณ์ก่อนเปิด Browser อัตโนมัติ
start "" /b cmd /c "ping 127.0.0.1 -n 3 >nul && start http://127.0.0.1:5000"

:: รัน Production WSGI Server (Waitress Multi-threaded + SQLite WAL Mode)
py run.py
pause
