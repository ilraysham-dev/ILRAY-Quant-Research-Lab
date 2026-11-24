@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Python environment missing. Run setup_windows.bat first.
  pause
  exit /b 1
)
echo Running Python unit tests...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
  echo WARNING: Unit tests failed. Review errors above.
  pause
  exit /b 1
)
echo.
echo Checking all dashboard pages using synthetic data...
".venv\Scripts\python.exe" scripts\self_check.py --live
if errorlevel 1 (
  echo WARNING: At least one check failed. Open SELF_CHECK_RESULTS.json.
  pause
  exit /b 1
)
echo.
echo All available tests passed. Open SELF_CHECK_RESULTS.json for details.
pause
