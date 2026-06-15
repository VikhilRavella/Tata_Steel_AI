#!/bin/bash

LOG_FILE="setup.log"
echo "Starting Tata Steel Industrial AI Platform Installation..." > $LOG_FILE

echo "========================================================="
echo "Tata Steel Industrial AI Platform - One-Click Installer"
echo "========================================================="

# 1. Check Python
echo "[+] Checking Python installation..." | tee -a $LOG_FILE
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 is not installed or not in PATH." | tee -a $LOG_FILE
    exit 1
fi

# 2. Create Virtual Environment
echo "[+] Setting up virtual environment..." | tee -a $LOG_FILE
if [ ! -d "env" ]; then
    python3 -m venv env >> $LOG_FILE 2>&1
fi

# 3. Activate & Install
echo "[+] Installing Python dependencies (this may take a minute)..." | tee -a $LOG_FILE
source env/bin/activate
pip install -r requirements.txt >> $LOG_FILE 2>&1

# 4. Check/Install Ollama
echo "[+] Checking Ollama installation..." | tee -a $LOG_FILE
if ! command -v ollama &> /dev/null; then
    echo "[+] Ollama not found. Installing Ollama..." | tee -a $LOG_FILE
    curl -fsSL https://ollama.com/install.sh | sh >> $LOG_FILE 2>&1
fi

# Start Ollama in background if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "[+] Starting Ollama service in background..." | tee -a $LOG_FILE
    ollama serve > ollama.log 2>&1 &
    sleep 3
fi

# 5. Download Models
echo "[+] Verifying and pulling required AI models..." | tee -a $LOG_FILE
MODELS=("mistral:latest" "qwen2.5vl:latest" "qwen2.5-coder:7b")
for MODEL in "${MODELS[@]}"; do
    if ! ollama list | grep -q "$MODEL"; then
        echo "    - Pulling $MODEL (This will take time depending on internet speed)..." | tee -a $LOG_FILE
        ollama pull $MODEL >> $LOG_FILE 2>&1
    else
        echo "    - $MODEL already installed. Skipping." | tee -a $LOG_FILE
    fi
done

# 6. Create Required Directories
echo "[+] Creating required storage directories..." | tee -a $LOG_FILE
mkdir -p backend/storage/chroma_db
mkdir -p backend/storage/company_documents

echo ""
echo "========================================================="
echo "Installation Complete"
echo ""
echo "Backend:"
echo "http://localhost:8000"
echo ""
echo "Frontend:"
echo "http://localhost:3000"
echo "========================================================="
echo ""
echo "To start the platform, run: ./START_PLATFORM.sh"
echo ""
