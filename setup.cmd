@echo off
setlocal
cd /d "%~dp0"
if exist "side\Scripts\python.exe" goto install
py -3.12 -m venv side
if errorlevel 1 (
  echo Python 3.12 is required. Install it, then run setup.cmd again.
  exit /b 1
)
:install
set "REQ=requirements.txt"
if /I "%~1"=="dev" set "REQ=requirements-dev.txt"
"side\Scripts\python.exe" -m pip install --require-hashes -r "%REQ%"
if errorlevel 1 exit /b 1
"side\Scripts\python.exe" -m pip check
exit /b %errorlevel%
