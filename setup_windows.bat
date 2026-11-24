@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo Checking for Python 3.11 or newer...
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.13 3.12 3.11) do (
        if not defined PYTHON_CMD (
            py -%%V -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_CMD=py -%%V"
        )
    )
)
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)
if not defined PYTHON_CMD (
    echo ERROR: Install Python 3.11, 3.12, or 3.13 from python.org and try again.
    pause
    exit /b 1
)
echo Using !PYTHON_CMD!
if not exist ".venv\Scripts\python.exe" (
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 goto :venv_failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo WARNING: Package installation succeeded, but the test suite failed.
    pause
    exit /b 1
)
echo.
echo Setup and tests completed successfully.
echo To run locally: double-click run_windows.bat
 echo To share on trusted home Wi-Fi: double-click run_windows_LAN.bat
pause
exit /b 0
:venv_failed
echo ERROR: Could not create the Python environment.
pause
exit /b 1
:install_failed
echo ERROR: Dependency installation failed. Review messages above.
pause
exit /b 1
