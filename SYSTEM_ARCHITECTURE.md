# Tata Steel Industrial AI Platform - System Architecture

This document provides a comprehensive overview of the Enterprise Architecture for the Maintenance Wizard platform. 

## 1. Complete System Architecture
```mermaid
graph TD
    classDef users fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef backend fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef intel fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef models fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef data fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    subgraph "👥 Presentation Layer (Users)"
        E(Engineer Portal):::users
        S(Supervisor Portal):::users
        M(Manager Portal):::users
    end

    subgraph "⚙️ FastAPI Backend"
        API("<b>Core Services:</b><br/>Authentication | Notifications | Workflows<br/>Approval Engine | Audit Logging<br/>Reports | Inventory | Work Orders"):::backend
    end

    subgraph "🧠 Maintenance Intelligence Layer"
        INTEL("<b>Agentic Modules:</b><br/>Sandbox Agent | Engineering Agent<br/>Document Intelligence | Vision Diagnostics<br/>Inventory & Workflow Intelligence"):::intel
    end

    subgraph "🤖 AI Models Layer"
        AI("Mistral (Reasoning & Chat)<br/>Qwen2.5VL (Vision)<br/>Qwen2.5-Coder (Engineering)<br/>BAAI/bge-small-en-v1.5 (Embeddings)"):::models
    end

    subgraph "💾 Data Layer"
        SQL("<b>SQLite Database</b><br/>Users, Work Orders, Maintenance History"):::data
        CHROMA("<b>ChromaDB</b><br/>PDF Vectors, Knowledge Base"):::data
        FILE("<b>File Storage</b><br/>Uploaded PDFs, Imagery"):::data
    end

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

## 2. Engineering Agent Workflow
```mermaid
graph TD
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef router fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef branch fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef agent fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef output fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    Q(Engineer Query):::input --> ID(Intent Detection):::router
    ID --> DR(Decision Router):::router

    DR --> DOC(Document Intelligence / RAG):::branch
    DR --> VIS(Vision Diagnostics):::branch
    DR --> INV(Inventory Intelligence):::branch
    DR --> RISK(Risk Assessment):::branch

    DOC --> EA((Engineering Agent)):::agent
    VIS --> EA
    INV --> EA
    RISK --> EA

    EA --> OUT("<b>Deliverables:</b><br/>Reports, Work Orders, Notifications"):::output
```

---

## 3. Document Intelligence (RAG) Workflow
```mermaid
graph TD
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef embed fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef db fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef output fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    PU(Manager Uploads PDF):::input --> PS[PDF Storage]:::embed
    PS --> PE[PDF Extraction & Chunking]:::embed
    PE --> BAAI[BAAI/bge-small-en Embedding]:::embed
    BAAI --> VDB[(ChromaDB Vector Store)]:::db

    EQ(Engineer Question):::input --> QE[Question Embedding]:::embed
    QE --> SS[Semantic Search]:::embed
    VDB -.->|Vector Comparison| SS
    SS --> TRC[Retrieved Knowledge]:::embed
    TRC --> OUT[Grounded Response + Source Citations]:::output
```

---

## 4. Vision Diagnostics Workflow
```mermaid
graph TD
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef ai fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef risk fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    EI(Engineer Uploads Image):::input --> QW[Qwen2.5VL Vision Analysis]:::ai
    QW --> OD[Object Detection & Defect Inspection]:::ai
    OD --> EHE[Equipment Condition Assessment]:::ai
    EHE --> RA[Risk Assessment]:::risk
    RA --> REC[AI Maintenance Advisor]:::ai
    REC --> DASH(Engineer Dashboard Deliverables):::input
```

---

## 5. Inventory & Approval Workflow
```mermaid
graph TD
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef db fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef action fill:#312e81,stroke:#c084fc,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef alert fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    CIR(Create Inventory Request):::input --> IDB[Inventory Database Check]:::db
    IDB --> SA{Stock Available?}:::db
    
    SA -->|YES| RS[Request Submitted]:::action
    RS --> SR[Supervisor Review]:::action
    SR --> APP{Approve/Reject?}:::db
    
    APP -->|Approve| IA[Inventory Allocated & Issued]:::action
    APP -->|Reject| RR[Request Returned]:::alert
    
    SA -->|NO| LIA[Low Inventory Alert]:::alert
    LIA --> MN[Manager Procurement Process]:::alert
```

---

## 6. End-to-End Industrial AI Maintenance Workflow
```mermaid
graph TD
    classDef input fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef process fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef action fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff,rx:5px,ry:5px;

    MP[Manager Initialization]:::input --> EL[Engineer Operations]:::process
    EL --> EA[Engineering Agent AI]:::process
    EA --> AI[RAG / Vision / Routing]:::process
    AI --> WK[Automated Workflows]:::action
    WK --> INV[Inventory Processing]:::process
    INV --> SUP[Supervisor Approvals]:::action
    SUP --> EXEC[Maintenance Execution]:::action
    EXEC --> LOG[Audit & Continuous Learning]:::process
```

---

## 7. Database Relationships
The platform uses SQLite for relational persistence mapping the physical factory environment.

- **Users**: (Plant Managers, Shift Supervisors, Maintenance Engineers)
- **Equipment Registry**: Core machines linked to Supervisors and assigned to Engineers.
- **Inventory/BOM**: Spare parts mapped to their respective compatible equipment.
- **Work Orders**: Connects Engineers to specific Equipment, documenting the repair process and inventory consumed.
- **Maintenance History**: Long-term audit trail of completed Work Orders used for MTBF (Mean Time Between Failures) analytics.
