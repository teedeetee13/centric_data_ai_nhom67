@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Tim Python 3.12: uu tien trinh khoi chay "py -3.12", sau do moi den "python" tren PATH
set "PY="
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY (
    python -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1 && set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    if not defined PY (
        echo Can Python 3.12. Tai tai https://www.python.org/downloads/release/python-3120/ va tich "Add Python to PATH".
        pause
        exit /b 1
    )
    echo Dang tao moi truong ao .venv ...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Tao moi truong ao that bai. Kiem tra lai Python 3.12.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import streamlit,sklearn,pandas,openpyxl,plotly; assert sklearn.__version__ == '1.9.1'" >nul 2>&1
if errorlevel 1 (
    echo Dang cai thu vien. Lan dau can ket noi Internet, mat vai phut.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Cai thu vien chua thanh cong. Kiem tra Internet va Python 3.12.
        pause
        exit /b 1
    )
)

echo Mo trinh duyet tai http://127.0.0.1:8501 . Dong cua so nay de tat ung dung.
".venv\Scripts\python.exe" run_mvp.py
pause
