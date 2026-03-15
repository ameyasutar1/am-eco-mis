@echo off
cd /d "C:\Users\Admin\Desktop\Codes"

start "ASRS Backend" "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" "c:\Users\Admin\Desktop\Codes\main.py"

timeout /t 2 /nobreak >nul

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8000/"
