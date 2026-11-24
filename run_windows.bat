@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing Python environment. Run setup_windows.bat first.
  pause
  exit /b 1
)
echo Launching Quant Lab on THIS COMPUTER ONLY at http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 echo ERROR: Dashboard failed to start. Review messages above.
pause
