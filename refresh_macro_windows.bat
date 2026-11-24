@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run setup_windows.bat to install the project.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\refresh_macro_snapshot.py
if errorlevel 1 (
  echo Macro refresh failed. Previous successful snapshot was preserved.
  exit /b 1
)
echo Macro snapshot updated.
