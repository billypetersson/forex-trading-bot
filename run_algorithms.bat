@echo off
echo ===============================================
echo    Forex Trading Bot - Algorithm Selector
echo ===============================================
echo.
echo Available Algorithms:
echo 1. Momentum - Best for volatile markets
echo 2. Trend Following - Best for trending markets
echo 3. Mean Reversion - Best for ranging markets
echo 4. Hybrid - Adaptive (Recommended)
echo.
set /p choice="Select algorithm (1-4): "

if "%choice%"=="1" set algo=momentum
if "%choice%"=="2" set algo=trend
if "%choice%"=="3" set algo=mean_reversion
if "%choice%"=="4" set algo=hybrid

if "%algo%"=="" (
    echo Invalid choice!
    pause
    exit /b 1
)

echo.
echo Starting bot with %algo% algorithm...
echo.

REM Check if virtual environment exists
if exist "venv" (
    call venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)

REM Run the bot with selected algorithm
python forex_bot.py --algorithm %algo%

pause
