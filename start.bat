@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo      Douyin Live AI Assistant
echo ========================================

:: Step 0: Set Ollama model path
set OLLAMA_MODELS=E:\ollama\models

:: Step 1: Check & start Ollama
echo [1/4] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Starting Ollama...
    start /B "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 8 /nobreak >nul
) else (
    echo   OK
)

:: Step 2: Check model
echo [2/4] Checking model...
curl -s http://localhost:11434/api/tags | find "qwen2.5:3b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Pulling qwen2.5:3b...
    "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" pull qwen2.5:3b
) else (
    echo   OK
)

:: Step 3: Activate venv
echo [3/4] Loading Python...
call venv\Scripts\activate.bat

:: Step 4: Run
echo [4/4] Starting AI assistant...
echo.
echo   Press Ctrl+C to stop
echo.
python pipeline.py

pause
