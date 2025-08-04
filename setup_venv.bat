@echo off

echo Checking for Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found. Please install Python and make sure it's in your PATH.
    pause
    exit /b 1
)

if exist kb_env (
    echo Virtual environment 'kb_env' already exists.
) else (
    echo Creating virtual environment 'kb_env'...
    py -m venv kb_env
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment and installing requirements...
call .\kb_env\Scripts\activate.bat

pip install -r .\env\requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install requirements from env/requirements.txt.
    pause
    exit /b 1
)

echo.
echo ==================================================================
echo  Setup complete! Running the main script...
echo ==================================================================
echo.

py .\main\chatbot\main.py

echo.
echo ==================================================================
echo  Script execution finished.
echo ==================================================================
echo.
pause
