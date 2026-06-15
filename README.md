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

## 🏗️ Complete System Architecture

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef users fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef backend fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef intel fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef models fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef data fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    %% Users Layer
    subgraph "👥 Presentation Layer (Users)"
        E(Engineer Portal):::users
        S(Supervisor Portal):::users
        M(Manager Portal):::users
    end

    %% Backend Layer
    subgraph "⚙️ FastAPI Backend"
        API("<b>Core Services:</b><br/>Authentication Service<br/>Notification Service<br/>Workflow Engine<br/>Approval Engine<br/>Audit Logging<br/>Report Generation<br/>Inventory Management<br/>Work Order Management"):::backend
    end

    %% Intelligence Layer
    subgraph "🧠 Maintenance Intelligence Layer"
        INTEL("<b>Agentic Modules:</b><br/>Sandbox Agent<br/>Engineering Agent<br/>Document Intelligence<br/>Vision Diagnostics<br/>Inventory Intelligence<br/>Root Cause Analysis<br/>Risk Assessment Engine<br/>Recommendation Engine<br/>Workflow Intelligence"):::intel
    end

    %% AI Models Layer
    subgraph "🤖 AI Models Layer"
        AI("Mistral (Engineering Reasoning)<br/>Qwen2.5VL (Vision Analysis)<br/>BAAI/bge-small-en-v1.5 (Document Embeddings)"):::models
    end

    %% Data Layer
    subgraph "💾 Data Layer"
        SQL("<b>SQLite Database</b><br/>Users, Inventory, Requests, Work Orders, Notifications, Audit Logs, Maintenance History, Maintenance Outcomes, Supervisor Directory"):::data
        CHROMA("<b>ChromaDB</b><br/>PDF Embeddings, SOP Embeddings, Maintenance Manuals, Engineering Knowledge Base"):::data
        FILE("<b>File Storage</b><br/>Uploaded PDFs, Equipment Images, Generated Reports, Profile Images"):::data
    end

    %% Connections
    E --> API
    S --> API
    M --> API
    
    API --> INTEL
    INTEL --> AI
    INTEL --> SQL
    INTEL --> CHROMA
    INTEL --> FILE
```

---

## ⚙️ Engineering Agent Workflow

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef router fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef branch fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef process fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef agent fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef output fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    Q(Engineer Query):::input --> ID(Intent Detection):::router
    ID --> DR(Decision Router):::router

    subgraph "🔀 Intelligent Routing"
        DR --> DOC(1. Document Intelligence / RAG):::branch
        DR --> VIS(2. Vision Diagnostics):::branch
        DR --> INV(3. Inventory Intelligence):::branch
        DR --> RISK(4. Risk Assessment Engine):::branch
    end

    subgraph "📚 Document Intelligence Flow"
        DOC --> PU[PDF Upload]:::process --> TE[Text Extraction]:::process --> CH[Chunking]:::process --> BAAI[BAAI/bge-small-en-v1.5]:::process --> DB[ChromaDB Retrieval]:::process --> RK[Relevant Knowledge Chunks]:::process
    end

    subgraph "👁️ Vision Diagnostics Flow"
        VIS --> EI[Equipment Image]:::process --> QW[Qwen2.5VL]:::process --> OD[Object Detection]:::process --> DD[Defect Detection]:::process --> CD[Crack Detection]:::process --> CRD[Corrosion Detection]:::process --> WD[Wear Detection]:::process
    end

    subgraph "📦 Inventory Intelligence Flow"
        INV --> IS[Inventory Search]:::process --> SV[Stock Verification]:::process --> PA[Part Availability Check]:::process --> IR[Inventory Request Generation]:::process
    end

    subgraph "⚠️ Risk Assessment Flow"
        RISK --> EC[Equipment Condition]:::process --> RCA[Root Cause Analysis]:::process --> FP[Failure Prediction]:::process --> RC["Risk Classification:<br/>LOW | MEDIUM | HIGH | CRITICAL"]:::process
    end

    RK --> EA((Engineering Agent)):::agent
    WD --> EA
    IR --> EA
    RC --> EA

    subgraph "🧠 Central Engineering Agent"
        EA --> Tasks("<b>Core Processing:</b><br/>• Maintenance Reasoning<br/>• Engineering Analysis<br/>• Root Cause Analysis<br/>• Recommendation Generation<br/>• Safety Compliance Check<br/>• Workflow Automation"):::agent
    end

    subgraph "📤 Output Layer"
        Tasks --> OUT("<b>Generated Deliverables:</b><br/>• Engineering Report<br/>• Maintenance Report<br/>• Work Order<br/>• Inventory Request<br/>• Risk Assessment Report<br/>• Safety Inspection Report<br/>• Notifications<br/>• Escalation Alerts"):::output
    end
```

---

## 📚 Document Intelligence (RAG) Workflow
**Retrieval-Augmented Generation for Engineering Knowledge**

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef process fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef embed fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef db fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef agent fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef output fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    %% Document Ingestion
    subgraph "📄 Document Ingestion"
        PU("<b>Manager Uploads PDF</b><br/>• SOP Manuals<br/>• Equipment Manuals<br/>• Maintenance Procedures<br/>• Safety Documents"):::input
        DA[Document Approval]:::process
        PS[PDF Storage]:::process
        PU --> DA --> PS
    end

    %% Document Processing
    subgraph "⚙️ Document Processing"
        PS --> PE[PDF Extraction]:::process
        PE --> TC[Text Cleaning]:::process
        TC --> CH("<b>Chunking</b><br/>Chunk Size = 800<br/>Chunk Overlap = 100"):::process
        CH --> MG("<b>Metadata Generation</b><br/>Document Name<br/>Page Number<br/>Section Title"):::process
    end

    %% Embedding Generation
    subgraph "🧠 Embedding Generation"
        MG --> TXC[Text Chunks]:::process
        TXC --> BAAI["<b>BAAI/bge-small-en-v1.5</b><br/>Embedding Model"]:::embed
        BAAI --> DIM[384-Dimensional Vectors]:::embed
        DIM --> VG[Vector Generation]:::embed
    end

    %% Vector Storage
    subgraph "💾 Vector Storage"
        VG --> VDB("<b>ChromaDB</b><br/>Stores:<br/>• SOP Chunks<br/>• Manual Chunks<br/>• Maintenance Procedures<br/>• Safety Guidelines<br/>• Technical Knowledge"):::db
    end

    %% Query Workflow
    subgraph "🔍 Query Workflow"
        EQ("<b>Engineer Question</b><br/>• Summarize this PDF<br/>• What maintenance procedures are described?<br/>• What safety precautions are mentioned?<br/>• Explain bearing maintenance SOP"):::input
        QE[Question Embedding]:::process
        Q_BAAI["<b>BAAI/bge-small-en-v1.5</b>"]:::embed
        SS[Semantic Search]:::process
        TRC[Top Relevant Chunks Retrieved]:::process

        EQ --> QE --> Q_BAAI --> SS
        VDB -.->|Vector Comparison| SS
        SS --> TRC
    end

    %% Answer Generation
    subgraph "🤖 Answer Generation"
        TRC --> EA((Engineering Agent)):::agent
        EA --> MIS[Mistral]:::agent
        MIS --> GR("<b>Grounded Engineering Response</b>"):::agent
        GR --> SC("<b>Source Citations</b><br/>Document Name<br/>Page Number<br/>Section Reference"):::agent
    end

    %% Final Outputs
    subgraph "📤 Final Outputs"
        SC --> FO("<b>Outputs:</b><br/>• PDF Summary<br/>• SOP Explanation<br/>• Maintenance Procedures<br/>• Safety Guidelines<br/>• Engineering Reports<br/>• Technical Recommendations"):::output
    end
```

---

## 👁️ Vision Diagnostics Workflow
**AI-Powered Equipment Inspection & Defect Detection**

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef ai fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef detect fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef assess fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef risk fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef action fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    %% Image Input
    subgraph "📷 Image Input"
        EI("<b>Engineer Uploads Equipment Image</b><br/>• Bearing<br/>• Motor<br/>• Gearbox<br/>• Pump<br/>• Conveyor<br/>• Shaft"):::input
        IV[Image Validation]:::detect
        IP[Image Processing]:::detect
        EI --> IV --> IP
    end

    %% Vision AI Analysis
    subgraph "🧠 Vision AI Analysis"
        IP --> EQ[Equipment Image]:::input
        EQ --> QW["<b>Qwen2.5VL</b><br/>Vision Foundation Model"]:::ai
        QW --> OD("<b>Object Detection</b><br/>Identify:<br/>• Bearings<br/>• Motors<br/>• Gearboxes<br/>• Pumps<br/>• Shafts<br/>• Belts<br/>• Couplings"):::detect
    end

    %% Defect Detection
    subgraph "🔍 Defect Detection"
        OD --> VI[Visual Inspection]:::detect
        VI --> CD[Crack Detection]:::detect
        VI --> COR[Corrosion Detection]:::detect
        VI --> WD[Wear Detection]:::detect
        VI --> LD[Leak Detection]:::detect
        VI --> MD[Misalignment Detection]:::detect
        VI --> SD[Surface Damage Detection]:::detect
    end

    %% Condition Assessment
    subgraph "📊 Condition Assessment"
        CD & COR & WD & LD & MD & SD --> EHE[Equipment Health Evaluation]:::assess
        EHE --> CC("<b>Condition Classification:</b><br/>Excellent | Good | Fair | Poor | Critical"):::assess
    end

    %% Risk Assessment Engine
    subgraph "⚠️ Risk Assessment Engine"
        CC --> DD[Detected Defects]:::risk
        DD --> RCA[Root Cause Analysis]:::risk
        RCA --> FP[Failure Prediction]:::risk
        FP --> SA[Severity Assessment]:::risk
        SA --> RC("<b>Risk Classification:</b><br/>LOW | MEDIUM | HIGH | CRITICAL"):::risk
    end

    %% Recommendation Engine
    subgraph "💡 Recommendation Engine"
        RC --> AMA[AI Maintenance Advisor]:::action
        AMA --> GEN("<b>Generate:</b><br/>• Maintenance Recommendation<br/>• Inspection Report<br/>• Defect Report<br/>• Root Cause Analysis<br/>• Risk Assessment Report<br/>• Corrective Action Plan"):::action
    end

    %% Workflow Automation
    subgraph "⚡ Workflow Automation"
        GEN -->|If HIGH or CRITICAL| ALERT[Safety Alert]:::risk
        ALERT --> SN[Supervisor Notification]:::action
        SN --> IC[Inventory Check]:::action
        IC --> WOG[Work Order Generation]:::action
        WOG --> ME[Maintenance Escalation]:::action
    end

    %% Final Output
    subgraph "🖥️ Final Output"
        ME --> DASH("<b>Engineer Dashboard Displays:</b><br/>• Defect Summary<br/>• Risk Level<br/>• Root Cause<br/>• Recommended Action<br/>• Maintenance Plan<br/>• Safety Alerts"):::input
    end
```

---

## 📦 Inventory & Approval Workflow
**Automated Spare Part Request and Approval Process**

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef db fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef decision fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef action fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef alert fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef monitor fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    %% Engineer Initiates Request
    subgraph "👷 Engineer Initiates Request"
        EF[Equipment Failure Detected]:::input
        EF --> EAR[Engineering Agent Recommendation]:::input
        EAR --> IS[Inventory Search]:::input
        IS --> PAC[Part Availability Check]:::input
        PAC --> CIR("<b>Create Inventory Request</b><br/>Examples:<br/>• Bearing<br/>• Motor<br/>• Coupling<br/>• Gear<br/>• Pump Seal"):::input
    end

    %% Inventory System
    subgraph "📦 Inventory System"
        CIR --> IDB("<b>Inventory Database Checks:</b><br/>• Part Availability<br/>• Stock Quantity<br/>• Reorder Level<br/>• Warehouse Location"):::db
        IDB --> SA{"<b>Stock Available?</b>"}:::decision
    end

    %% IF STOCK AVAILABLE
    subgraph "✅ IF STOCK AVAILABLE"
        SA -->|YES| RS[Request Submitted]:::action
        RS --> SR[Supervisor Review]:::action
        SR --> APP{"<b>Approve or Reject?</b>"}:::decision
    end

    %% IF APPROVED
    subgraph "✔️ IF APPROVED"
        APP -->|Approve| IA[Inventory Allocation]:::action
        IA --> SU[Stock Updated]:::action
        SU --> PR[Part Reserved]:::action
        PR --> EN1[Engineer Notification]:::action
        EN1 --> WOE[Work Order Execution]:::action
    end

    %% IF REJECTED
    subgraph "❌ IF REJECTED"
        APP -->|Reject| RR[Request Returned]:::alert
        RR --> EN2[Engineer Notification]:::alert
        EN2 --> AR[Alternative Recommendation]:::alert
    end

    %% IF STOCK NOT AVAILABLE
    subgraph "⚠️ IF STOCK NOT AVAILABLE"
        SA -->|NO| LIA[Low Inventory Alert]:::alert
        LIA --> SN[Supervisor Notification]:::alert
        SN --> MN[Manager Notification]:::alert
        MN --> REQ[Reorder Request]:::alert
        REQ --> PP[Procurement Process]:::alert
    end

    %% Final Output
    subgraph "🏁 Final Output"
        WOE --> II[Inventory Issued]:::monitor
        II --> MA[Maintenance Activity]:::monitor
        MA --> WOC[Work Order Completion]:::monitor
        WOC --> MHU[Maintenance History Updated]:::monitor
    end

    %% Manager Monitoring
    subgraph "📊 Manager Monitoring"
        MD("<b>Manager Dashboard Displays:</b><br/>• Pending Requests<br/>• Approved Requests<br/>• Rejected Requests<br/>• Inventory Status<br/>• Low Stock Alerts<br/>• Critical Inventory Items"):::monitor
    end

    %% Notification Center
    subgraph "🔔 Notification Center"
        NC("<b>Send Notifications To:</b><br/>• Engineer | Supervisor | Manager<br/><br/><b>Types:</b><br/>Created | Approved | Rejected | Updated | Alerts"):::db
    end

    %% Audit Logging
    subgraph "📝 Audit Logging"
        AL("<b>Record:</b><br/>• Request ID<br/>• User<br/>• Part Name<br/>• Quantity<br/>• Approval Status<br/>• Timestamp"):::db
    end

    %% Floating connections for visual completeness
    RS -.-> NC
    APP -.-> AL
    LIA -.-> MD
```

---

## 🔄 End-to-End Industrial AI Maintenance Workflow
**Complete Maintenance Lifecycle Powered by AI**

```mermaid
graph TD
    %% Styling Colors (Steel Gray & Blue Theme)
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef process fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef agent fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef ai fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef action fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef output fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    %% STAGE 1 - KNOWLEDGE INITIALIZATION
    subgraph "📊 STAGE 1: KNOWLEDGE INITIALIZATION"
        MP[Manager Portal]:::input
        UCSV("<b>Upload CSV Data</b><br/>• Users | Supervisors | Equipment<br/>• Inventory | Work Orders | Maintenance History"):::process
        DP[Database Population]:::process
        UTM("<b>Upload Technical Manuals</b><br/>• SOPs | User Manuals | Safety Procedures"):::process
        DA[Document Approval]:::process
        RAG[RAG Knowledge Base Creation]:::action

        MP --> UCSV --> DP
        DP --> UTM --> DA --> RAG
    end

    %% STAGE 2 - ENGINEER OPERATIONS
    subgraph "👷 STAGE 2: ENGINEER OPERATIONS"
        EL[Engineer Login]:::input
        ED[Engineer Dashboard]:::process
        SE[Select Equipment]:::process
        ID("<b>Issue Detected</b><br/>Examples:<br/>• Bearing Noise<br/>• Motor Overheating<br/>• Gearbox Vibration<br/>• Pump Leakage"):::process

        EL --> ED --> SE --> ID
    end

    %% STAGE 3 - ENGINEERING AGENT
    subgraph "🤖 STAGE 3: ENGINEERING AGENT"
        EQ[Engineer Query]:::input
        IND[Intent Detection]:::agent
        DROUT("<b>Decision Router</b><br/>Selects:<br/>• Document Intelligence<br/>• Vision Diagnostics<br/>• Inventory Intelligence<br/>• Risk Assessment"):::agent

        EQ --> IND --> DROUT
    end

    %% STAGE 4 - DOCUMENT INTELLIGENCE
    subgraph "📚 STAGE 4: DOCUMENT INTELLIGENCE"
        EUP[Engineer Uploads PDF]:::input
        SS[Semantic Search]:::ai
        CDR[ChromaDB Retrieval]:::ai
        EKR[Engineering Knowledge Retrieval]:::ai

        EUP --> SS --> CDR --> EKR
    end

    %% STAGE 5 - VISION DIAGNOSTICS
    subgraph "👁️ STAGE 5: VISION DIAGNOSTICS"
        EUI[Engineer Uploads Equipment Image]:::input
        QVA[Qwen2.5VL Analysis]:::ai
        VDEF("<b>Defect Detection</b><br/>• Crack | Corrosion | Wear | Leakage | Misalignment"):::ai

        EUI --> QVA --> VDEF
    end

    %% STAGE 6 - AI MAINTENANCE INTELLIGENCE
    subgraph "🧠 STAGE 6: AI MAINTENANCE INTELLIGENCE"
        EAC("<b>Engineering Agent Combines:</b><br/>• RAG Results<br/>• Vision Results<br/>• Equipment History<br/>• Maintenance Records"):::agent
        RCA[Root Cause Analysis]:::ai
        RA("<b>Risk Assessment</b><br/>LOW | MEDIUM | HIGH | CRITICAL"):::ai
        MREC[Maintenance Recommendation]:::ai

        EAC --> RCA --> RA --> MREC
    end

    %% STAGE 7 - AUTOMATED WORKFLOW
    subgraph "⚡ STAGE 7: AUTOMATED WORKFLOW"
        EAG("<b>Engineering Agent Generates:</b><br/>• Engineering Report<br/>• Maintenance Report<br/>• Risk Assessment Report<br/>• Work Order<br/>• Inventory Request"):::action
    end

    %% STAGE 8 - INVENTORY PROCESS
    subgraph "📦 STAGE 8: INVENTORY PROCESS"
        IR[Inventory Request]:::process
        IAC[Inventory Availability Check]:::process
        SA{"Stock Available?<br/>YES / NO"}:::process

        IR --> IAC --> SA
    end

    %% STAGE 9 - SUPERVISOR APPROVAL
    subgraph "✅ STAGE 9: SUPERVISOR APPROVAL"
        SD[Supervisor Dashboard]:::input
        RR[Review Request]:::process
        AR[Approve / Reject]:::action
        NS[Notification Sent]:::action

        SD --> RR --> AR --> NS
    end

    %% STAGE 10 - MANAGER MONITORING
    subgraph "📈 STAGE 10: MANAGER MONITORING"
        MMD("<b>Manager Dashboard Displays:</b><br/>• Plant Health | Open Work Orders<br/>• Critical Risks | Inventory Status<br/>• Safety Alerts | Escalations"):::output
    end

    %% STAGE 11 - MAINTENANCE EXECUTION
    subgraph "🔧 STAGE 11: MAINTENANCE EXECUTION"
        EWO[Engineer Executes Work Order]:::action
        ER[Equipment Repaired]:::action
        MOR[Maintenance Outcome Recorded]:::action
        MHU[Maintenance History Updated]:::action

        EWO --> ER --> MOR --> MHU
    end

    %% STAGE 12 - CONTINUOUS LEARNING
    subgraph "🔄 STAGE 12: CONTINUOUS LEARNING"
        OD[Outcome Data]:::ai
        AL[Audit Logs]:::ai
        KR[Knowledge Repository]:::ai
        FMI[Future Maintenance Intelligence]:::ai

        OD --> AL --> KR --> FMI
    end

    %% FINAL BUSINESS OUTCOMES
    subgraph "🏆 FINAL BUSINESS OUTCOMES"
        FBO("<b>Outcomes:</b><br/>• Reduced Downtime<br/>• Faster Fault Diagnosis<br/>• Improved Safety<br/>• Better Inventory Visibility<br/>• Knowledge Preservation<br/>• Workflow Automation<br/>• Increased Operational Efficiency"):::output
    end

    %% Core Connections between Stages
    RAG -.->|System Ready| EL
    ID --> EQ
    DROUT --> EUP
    DROUT --> EUI
    EKR --> EAC
    VDEF --> EAC
    MREC --> EAG
    EAG --> IR
    SA -->|Route| SD
    NS --> MMD
    NS --> EWO
    MHU --> OD
    FMI --> FBO
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

## 🔓 Step 6: Quick-Access Login Cards (No Typing Required)
To make testing as seamless as possible for the judges, we have built a rapid-access login page. You do not need to manually type any usernames or passwords. 
1. When you arrive at the `http://localhost:3000` login page, simply click on one of the three **Role Cards** (Manager, Supervisor, or Engineer).
2. The system will automatically inject the secure credentials and instantly log you into that specific dashboard!

---

## 📥 Step 7: Complete User Flow & Demo Data Initialization

To fully evaluate the platform, judges must follow this exact sequence to populate the databases, map the user roles, and verify the AI training documents.

### Phase A: Manager Data Mapping (Database Initialization)
1. Click the **Plant Manager** login card.
2. You will be greeted by the **Manager Dashboard Overview** showing live plant metrics.
3. Using the left sidebar menu, you must upload the provided sample `.csv` files from the `EXAMPLE/` folder to populate the company database. **Please upload them in this exact order to ensure relationships map correctly:**
   * **Engineer Management** $\rightarrow$ Upload `users.csv`
   * **Supervisor Management** $\rightarrow$ Upload `supervisor_directory (1).csv`
   * **Supervisor Management** $\rightarrow$ Upload `engineer_supervisor_mapping (1).csv`
   * **Equipment Registry** $\rightarrow$ Upload `equipment (1).csv`
   * **Equipment Registry** $\rightarrow$ Upload `supervisor_equipment_mapping (1).csv`
   * **Equipment BOM** $\rightarrow$ Upload `equipment_parts.csv`
   * **Inventory** $\rightarrow$ Upload `inventory (1).csv`
   * **Work Orders** $\rightarrow$ Upload `work_orders.csv`
   * **Maintenance History** $\rightarrow$ Upload `maintenance_history.csv`

### Phase B: Document Verification Flow (RAG Knowledge Base)
The Engineering AI Agent operates on strict compliance. It will **NOT** read or reference any uploaded manual unless it has been explicitly approved by a Manager.
1. While still logged in as the **Manager**, navigate to the **Document Library** via the sidebar.
2. Upload the provided PDF manual: `EXAMPLE/t999_user_manual.pdf`.
3. Once uploaded, the document will appear in the library table with a status of **"Pending"**.
4. **Crucial Step:** You must click the dropdown menu next to the document and change its status to **"Approved"**. 
5. The moment it is approved, the backend automatically chunks and vectorizes the PDF into the local ChromaDB database, making it instantly available to the AI.

---

## 👷 Step 8: Exploring the Engineer Portal & Daily Execution

The Engineer Portal is the operational heart of the platform. This is where maintenance workers manage their assigned machinery, check active work orders, and interact with the AI.

### 1. Accessing the Workspace
1. Click **Logout** from the Manager portal, and click the **Engineer** login card on the home screen.
2. You will land on the **Engineer Workspace Overview** dashboard to instantly view your assigned KPI metrics (Assigned Equipment, Open Work Orders, Pending Requests).

### 2. Managing Daily Operations
Use the left sidebar menu to navigate the execution workflows:
* **My Equipment**: View a list of all heavy machinery currently assigned to your profile based on the data the Manager mapped earlier.
* **Work Orders**: View all your assigned, active maintenance tasks.
* **Inventory & Parts**: Browse the factory's live database of spare parts (valves, bearings).
* **Maintenance History**: Review a comprehensive log of all past repairs performed on your assigned equipment.

---

## 🧠 Step 9: Testing the Intelligent Engineering Agent (AI Sandbox)

The most powerful feature of the Engineer Portal is the multimodal AI assistant built to help troubleshoot mechanical failures on the factory floor. 

### 1. Testing the RAG Pipeline (PDF Knowledge Retrieval)
1. Click on **Engineering Agent** in the left sidebar.
2. Because the Manager approved the document in Phase B, you can now test the AI. Ask it a technical question: *"What is the standard operating procedure for the T999 machine?"* 
3. The AI will instantly search the approved manuals and provide a highly accurate, summarized response complete with specific source citations. *(If the manager had rejected the document, the AI would have safely stated it does not have the knowledge).*

### 2. Testing Computer Vision Diagnostics
The agent can also "see" physical damage and diagnose it using Vision AI models.
1. Click the **Attachment (Paperclip) icon** next to the chat bar.
2. Select and upload the provided sample image: `EXAMPLE/test_equipment_defect.jpeg`.
3. Type a prompt alongside the image, such as: *"Analyze this visual defect and tell me exactly how to repair it."*
4. The Vision AI will process the image, identify the structural fault, and output a step-by-step repair strategy.
<br><img src="EXAMPLE/test_equipment_defect.jpeg" width="300" alt="Defect Example">

### 3. Testing Automated Workflow Triggers
1. In the chat, type an intent-driven command like: *"I need to order 5 replacement bearings for the main conveyor."*
2. The AI will seamlessly intercept the intent and automatically generate an **Inventory Request ticket** in the background, without requiring you to manually fill out any forms!

---

## 📊 Step 10: Supervisor Monitoring
1. Log out and click the **Shift Supervisor** login card.
2. Navigate the left sidebar to view the results of the data you mapped in Phase A. You will see real-time Plant Health summaries, low Inventory Alerts, and dynamic Work Order Escalations generated automatically for your specific shift!
