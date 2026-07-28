@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo IS529N launcher: .venv\Scripts\python.exe was not found.
    echo Create a Windows virtual environment and install requirements-desktop.txt first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m desktop.app %*
if errorlevel 1 pause
