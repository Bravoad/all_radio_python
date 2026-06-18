@echo off
chcp 65001 >nul
call .venv\Scripts\activate
pyinstaller --noconfirm --windowed --name AllRadioPython main.py
pause
