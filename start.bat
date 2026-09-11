@echo off
echo ================================================
echo   Hebrew RAG System - Startup Script
echo ================================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Creating virtual environment with Python 3.13...
    "C:\Users\sit327\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Make sure Python 3.13 is installed.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
echo [2/3] Installing dependencies...
pip install -r backend\requirements.txt -q --no-warn-script-location

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/3] Starting Hebrew RAG API server...
echo.
echo   API: http://localhost:8000
echo   UI:  http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo.
echo   To index the book, click 'טעינת ספר' in the UI.
echo   Or run: python backend\ingest.py
echo.
echo Press Ctrl+C to stop the server.
echo ================================================

cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
