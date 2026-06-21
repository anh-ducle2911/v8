@echo off
echo =========================================
echo   HPL AI Dispatching ^& Routing Engine v3
echo   Hoa Phat Logistics - Control Tower
echo =========================================

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo Chua cai Python 3. Tai tai https://python.org
  pause
  exit /b 1
)

if not exist venv (
  echo Dang tao moi truong Python...
  python -m venv venv
)

call venv\Scripts\activate.bat

echo Dang cai thu vien...
pip install -q -r requirements.txt

echo.
echo San sang! Mo trinh duyet tai: http://localhost:8000
echo (Ctrl+C de dung)
echo.

python app.py
pause
