@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\refresh_market_snapshot.py --out-dir local_data
if errorlevel 1 echo Price update failed. Check internet access and provider status.
pause
