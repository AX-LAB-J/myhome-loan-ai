@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
echo Same Wi-Fi access: http://YOUR_PC_LAN_IP:8501
echo Stop the existing local server before running this file.
if not exist "side\Scripts\python.exe" (
  echo Run setup.cmd first.
  exit /b 1
)
"side\Scripts\python.exe" -m scripts.check
if errorlevel 1 exit /b 1
"side\Scripts\python.exe" -m uvicorn housing_app.api:app --host 0.0.0.0 --port 8501
