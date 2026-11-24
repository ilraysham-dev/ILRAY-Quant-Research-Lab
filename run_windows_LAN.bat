@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing Python environment. Run setup_windows.bat first.
  pause
  exit /b 1
)
echo WARNING: This dashboard has NO LOGIN. Only run on trusted, private home networks.
echo Keep your router port forwarding DISABLED and allow only Private network access.
echo Windows PC: http://localhost:8501
 echo Mac on same trusted Wi-Fi: http://YOUR-WINDOWS-IP:8501
 echo Find your PC's IPv4 address using ipconfig in a separate Command Prompt.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
if errorlevel 1 echo ERROR: Dashboard failed to start. Review messages above.
pause
