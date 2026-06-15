# Tata Steel Industrial AI Platform - Complete Setup Guide

Welcome to the **Maintenance Wizard** Industrial AI Platform! 
Follow these exact steps to run the application from scratch on a brand new machine.

---

## 📁 Project Folder Structure

Understanding how the application is organized:

```text
Tata_Steel_AI/
│
├── backend/            # Core backend infrastructure. Contains the FastAPI server, database models, 
│                       # API routers (for Auth, Engineering, Manager, Supervisor), service layers 
│                       # (RAG, Ollama AI, Vector Storage), and file storage systems.
│
├── frontend/           # The vanilla HTML, CSS, and JS web interfaces for all user roles. 
│                       # Contains separate portals for Engineers, Shift Supervisors, and Managers.
│
├── docs/               # Comprehensive system documentation, including architecture diagrams, 
│                       # API route maps, database schemas, and final acceptance/audit reports.
│
├── scratch/            # Temporary experimental scripts, test files, and notification checkers 
│                       # used during active development and debugging.
│
├── start_app.py        # The unified startup orchestrator script.
├── requirements.txt    # Python dependency lockfile.
└── docker-compose.yml  # Docker configuration for containerized deployment.
```

---

## 🛠️ Step 1: Install Python
This project requires **Python 3.10 or higher**.

1. Download and install Python from the official website: [python.org/downloads](https://www.python.org/downloads/)
2. **Important for Windows:** During installation, make sure to check the box that says **"Add Python to PATH"**.
3. Open your terminal or command prompt.

---

## 📦 Step 2: Create and Activate a Virtual Environment
You must create an isolated environment (`venv`) to prevent package conflicts.

1. Navigate to the root project folder:
   ```bash
   cd path/to/Tata_Steel_AI
   ```

2. **Create the virtual environment:**
   ```bash
   python -m venv env
   ```

3. **Activate the environment:**
   - **Windows:**
     ```bash
     env\Scripts\activate
     ```
   - **Mac/Linux:**
     ```bash
     source env/bin/activate
     ```

---

## ⚙️ Step 3: Install Required Dependencies
Once your environment is active, install all the locked production dependencies.

1. Ensure your terminal is inside the root folder and your environment is activated (`(env)` should appear in your prompt).
2. Install the packages using pip:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🧠 Step 4: Install Ollama (AI Engine)
Because this platform uses completely private, locally-hosted AI models, you need to install Ollama to serve them.

1. **Install Ollama**: Download it from [ollama.com/download](https://ollama.com/download) and install it.
2. **Start Ollama** (if it isn't running automatically in your background/taskbar):
   ```bash
   ollama serve
   ```
*(Note: You do not need to manually download the AI models! The startup script in Step 5 will automatically verify and pull the required models for you.)*

---

## 🚀 Step 5: Start the Application!
Everything is now installed and configured. You can boot up both the **Frontend** and the **Backend** concurrently using our built-in orchestration script.

1. Ensure you are in the root directory and your virtual environment is activated.
2. Run the start script:
   ```bash
   python start_app.py
   ```

**The script will automatically:**
1. Connect to Ollama and pull all required AI models (`mistral`, `qwen2.5-coder`, etc.) if they aren't already installed.
2. Start the FastAPI Backend on `http://localhost:8000`
3. Start the Web Frontend on `http://localhost:3000`
4. Automatically open your default web browser directly to the Login portal!

To safely stop the servers, simply press `Ctrl+C` in your terminal. Good luck with the Hackathon!
