@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist "side\Scripts\python.exe" (
  echo Run setup.cmd first.
  exit /b 1
)
"side\Scripts\python.exe" -m scripts.check
if errorlevel 1 exit /b 1
"side\Scripts\python.exe" -m uvicorn housing_app.api:app --host 127.0.0.1 --port 8501
