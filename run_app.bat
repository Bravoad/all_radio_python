@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

if not exist "main.py" (
    echo Не найден файл main.py рядом с этим батником.
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import PyQt6, pyradios, vlc" >nul 2>nul
if errorlevel 1 (
    echo Не удалось найти нужные зависимости.
    echo.
    echo Если проект еще не настроен, выполни:
    echo python -m venv .venv
    echo .venv\Scripts\activate
    echo pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" main.py
if errorlevel 1 (
    echo.
    echo Программа завершилась с ошибкой.
    echo.
    pause
    exit /b %errorlevel%
)
