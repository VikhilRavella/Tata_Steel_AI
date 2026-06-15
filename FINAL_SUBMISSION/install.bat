@echo off
setlocal enabledelayedexpansion

set LOG_FILE=setup.log
echo Starting Tata Steel Industrial AI Platform Installation... > %LOG_FILE%
echo =========================================================
echo Tata Steel Industrial AI Platform - One-Click Installer
echo =========================================================

:: 1. Check Python
echo [+] Checking Python installation...
python --version >> %LOG_FILE% 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python is not installed or not in PATH. Please install Python 3.10+.
    echo [!] Python is not installed or not in PATH. >> %LOG_FILE%
    exit /b 1
)

:: 2. Create Virtual Environment
echo [+] Setting up virtual environment (venv)...
if not exist "env" (
    python -m venv env >> %LOG_FILE% 2>&1
)

:: 3. Activate Virtual Environment & Install Requirements
echo [+] Installing Python dependencies (this may take a minute)...
call env\Scripts\activate
pip install -r requirements.txt >> %LOG_FILE% 2>&1

:: 4. Check Ollama
echo [+] Checking Ollama installation...
ollama --version >> %LOG_FILE% 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Ollama not found. Downloading and installing automatically...
    powershell -Command "irm https://ollama.com/install.ps1 | iex"
    
    :: Wait a few seconds for the service to start after install
    timeout /t 5 /nobreak >nul
    
    :: Re-check if it was installed successfully
    ollama --version >> %LOG_FILE% 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [!] Automated installation failed. Please manually install Ollama from https://ollama.com/download
        exit /b 1
    )
    echo [+] Ollama installed successfully!
) else (
    echo [+] Ollama is already installed.
)

:: 5. Download Models
echo [+] Verifying and pulling required AI models...
for %%M in (mistral:latest qwen2.5vl:latest qwen2.5-coder:7b) do (
    echo     - Checking %%M...
    ollama list | findstr "%%M" >nul
    if !ERRORLEVEL! neq 0 (
        echo     - Pulling %%M (This will take time depending on your internet speed)...
        ollama pull %%M >> %LOG_FILE% 2>&1
    ) else (
        echo     - %%M already installed. Skipping.
    )
)

:: 6. Create Required Directories
echo [+] Creating required storage directories...
if not exist "backend\storage\chroma_db" mkdir backend\storage\chroma_db
if not exist "backend\storage\company_documents" mkdir backend\storage\company_documents

echo.
echo =========================================================
echo Installation Complete
echo.
echo Backend:
echo http://localhost:8000
echo.
echo Frontend:
echo http://localhost:3000
echo =========================================================
echo.
echo To start the platform, run: START_PLATFORM.bat
echo.
pause
