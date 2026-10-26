@echo off
setlocal enabledelayedexpansion
title Adore Model on ngrok

:: 1. Determine ML service directory
set "ML_DIR=c:\fyp saqlain\adore\ml_service"
if exist "%~dp0app\main.py" set "ML_DIR=%~dp0"
if exist "%~dp0ml_service\app\main.py" set "ML_DIR=%~dp0ml_service"

if not exist "%ML_DIR%" (
    echo [ERROR] ML Service directory not found at: %ML_DIR%
    pause
    exit /b 1
)

:: 2. Find Python environment
set "PYTHON_EXE="
if exist "%ML_DIR%\.venv_m48\Scripts\python.exe" (
    set "PYTHON_EXE=%ML_DIR%\.venv_m48\Scripts\python.exe"
) else if exist "%ML_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ML_DIR%\.venv\Scripts\python.exe"
) else (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] Python environment not found in %ML_DIR%!
    pause
    exit /b 1
)

:: 3. Find ngrok executable
set "NGROK_EXE="
if exist "C:\Program Files\ngrok\ngrok.exe" (
    set "NGROK_EXE=C:\Program Files\ngrok\ngrok.exe"
) else if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" (
    set "NGROK_EXE=%LOCALAPPDATA%\ngrok\ngrok.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\ngrok\ngrok.exe" (
    set "NGROK_EXE=%USERPROFILE%\AppData\Local\Programs\ngrok\ngrok.exe"
) else (
    for /f "tokens=*" %%i in ('where ngrok 2^>nul') do (
        if not defined NGROK_EXE set "NGROK_EXE=%%i"
    )
)

if not defined NGROK_EXE (
    echo [ERROR] ngrok was not found on your system!
    echo Please install ngrok or add ngrok.exe to your PATH.
    pause
    exit /b 1
)

echo ========================================================
echo   Adore ML Model + ngrok Launcher
echo ========================================================
echo ML Directory : %ML_DIR%
echo Python Path  : %PYTHON_EXE%
echo ngrok Path   : %NGROK_EXE%
echo ========================================================
echo.

echo Starting Adore clothing model on http://127.0.0.1:8000 ...
start "Adore Model Server" /D "%ML_DIR%" cmd /k "chcp 65001 >nul & \"%PYTHON_EXE%\" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for model server to initialize...
ping 127.0.0.1 -n 7 >nul

echo.
echo Opening ngrok tunnel on port 8000...
echo Your public ngrok URL will appear below.
echo Keep both this window and the model window open!
echo.
"%NGROK_EXE%" http 8000
