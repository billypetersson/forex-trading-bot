@echo off
echo Starting Forex Trading Bot...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if config.json exists
if not exist "config.json" (
    echo Error: config.json not found!
    echo Please copy config_template.json to config.json and update with your credentials
    pause
    exit /b 1
)

REM Install requirements if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Run the bot
echo.
echo Starting bot... Press Ctrl+C to stop
echo.
python forex_bot.py

pause
