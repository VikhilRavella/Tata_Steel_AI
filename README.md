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

## ✨ Platform Features & Capabilities

The Maintenance Wizard is a comprehensive, production-ready Agentic AI platform built with a wide array of advanced features specifically tailored for industrial environments:

### 🤖 1. Specialized Agentic AI
*   **Engineering Assistant**: A conversational AI agent that can diagnose equipment failures, recommend repair strategies, and summarize complex manuals.
*   **Computer Vision Diagnostics**: Engineers can upload images of broken machinery or parts, and the AI agent uses Vision Models to analyze the visual data and suggest repair steps.
*   **Automated Workflows**: The AI dynamically detects intents during a chat session to automatically trigger workflows, such as generating maintenance work orders and inventory requests without manual form entry.

### 📚 2. Advanced RAG Pipeline (Retrieval-Augmented Generation)
*   **PDF Knowledge Ingestion**: Managers can upload massive PDF technical manuals and Standard Operating Procedures (SOPs).
*   **Vector Database Integration**: Uploaded documents are automatically chunked, embedded using `BAAI/bge-small-en-v1.5`, and stored in a local ChromaDB instance for ultra-fast semantic search.
*   **Source Citations & Metadata**: The AI accurately cites exact page numbers and document names when providing technical advice, ensuring perfect traceability.

### 👥 3. Role-Based Access Control (RBAC) & Portals
*   **Manager Portal**: Full administrative oversight, including PDF document library management, user auditing, and system-wide analytics.
*   **Supervisor Dashboard**: Live tracking of shift metrics, plant health, active escalations, open maintenance requests, and team management.
*   **Engineer Portal**: Focuses purely on execution—featuring the active AI Sandbox, assigned work orders, equipment lists, and safety compliance tools.

### ⚙️ 4. Intelligent Orchestration & Escalations
*   **Dynamic Escalation Matrix**: Automatically tracks overdue maintenance requests, critical equipment downtime, and triggers live escalations to Shift Supervisors.
*   **Inventory Tracking**: Live tracking of warehouse parts with automated "Low Stock" warnings integrated into the Supervisor reports.
*   **Safety Compliance Tracker**: Manages safety waivers and tracks maintenance operations to ensure factory compliance protocols are strictly met.

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

---

## 📥 Step 6: Loading Demo Data (For Judges)

To fully explore the platform's capabilities, we have provided an `EXAMPLE/` folder inside this repository containing sample CSV databases and a PDF manual. 

Please log into the **Manager Portal** (`manager` / `password`) and use the sidebar menu to upload the following CSV files from the `EXAMPLE/` folder to populate the system:

1. **Engineer Management**: Upload `users.csv`
2. **Supervisor Management**: Upload `supervisor_directory (1).csv`
   * *Inside Supervisor Management (Mapping)*: Upload `engineer_supervisor_mapping (1).csv`
3. **Equipment Registry**: Upload `equipment (1).csv`
   * *Inside Equipment Registry (Mapping)*: Upload `supervisor_equipment_mapping (1).csv`
4. **Equipment BOM**: Upload `equipment_parts.csv`
5. **Inventory**: Upload `inventory (1).csv`
6. **Work Orders**: Upload `work_orders.csv`
7. **Maintenance History**: Upload `maintenance_history.csv`
8. **Document Library**: Upload the provided PDF manual `t999_user_manual.pdf` to test the AI RAG functionality.
