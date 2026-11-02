@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: Project virtual environment was not found.
    echo Expected: .venv\Scripts\python.exe
    echo.
    echo Create it first with: python -m venv .venv
    pause
    exit /b 1
)

echo Starting BTC Compounding Machine dashboard...
echo Press Ctrl+C in this window to stop the server.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

endlocal
