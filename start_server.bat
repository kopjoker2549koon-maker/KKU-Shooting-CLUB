@echo off
title KKU Shooting Club - Production Server (Khon Kaen University)
color 0B
echo ==================================================================
echo   KKU SHOOTING CLUB - STARTING PRODUCTION SERVER...
echo   ชมรมกีฬายิงปืน มหาวิทยาลัยขอนแก่น
echo ==================================================================
echo.

py run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] เซิร์ฟเวอร์หยุดทำงานด้วยรหัสข้อผิดพลาด %ERRORLEVEL%
    pause
)
