@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
    if errorlevel 1 (
        echo Ban demo nay da kiem tra voi Python 3.12. Hay cai Python 3.12 va them vao PATH.
        pause
        exit /b 1
    )
    python -m venv .venv
    if errorlevel 1 (
        echo Can cai Python 3.12 va bat tuy chon Add Python to PATH.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -c "import streamlit,sklearn,pandas,openpyxl,plotly; assert sklearn.__version__ == '1.9.1'" >nul 2>&1
if errorlevel 1 (
    echo Dang cai thu vien. Lan dau can ket noi Internet.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Cai thu vien chua thanh cong. Kiem tra Internet va Python 3.12.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" run_mvp.py
pause
