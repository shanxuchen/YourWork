@echo off
REM ========================================
REM   YourWork Startup Script (Windows)
REM ========================================

echo.
echo ========================================
echo   YourWork Dev Server
echo ========================================
echo.
echo [Starting] Launching service...
echo [Access]   http://localhost:8001
echo [Docs]     http://localhost:8001/docs
echo.
echo Press Ctrl+C to stop service
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.12+
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if database exists
if not exist "data\yourwork.db" (
    echo [INFO] Initializing database...
    python init_db.py
    if errorlevel 1 (
        echo [ERROR] Database initialization failed
        pause
        exit /b 1
    )
)

REM Start server
echo.
echo [INFO] Service starting...
python main.py
