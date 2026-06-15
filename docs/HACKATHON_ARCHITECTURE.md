# Hackathon Architecture

The Tata Steel Industrial Maintenance Platform is built using a modern, multi-agent AI architecture.

## Tech Stack
- **Frontend**: Vanilla HTML/JS/CSS (No frameworks, for rapid prototyping). Custom RBAC implemented via JS checking JWT tokens.
- **Backend**: FastAPI (Python 3)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/LLM**: Local Ollama running `mistral:latest`
- **Vector DB**: ChromaDB for Retrieval-Augmented Generation (RAG)
- **Deployment**: Docker Compose with Nginx reverse proxy

## AI Agent Ecosystem

### 1. Engineering Agent
- **Purpose**: Formal maintenance sessions.
- **Features**: Highly structured prompting, intent detection (Industrial vs Software), adaptive requirement collection, and persistent memory extraction.

### 2. Sandbox Agent
- **Purpose**: Informal experimentation.
- **Features**: Loose prompting, document upload for local context, and capability to escalate to a formal Engineering Session.

### 3. Service Agents (Specialized)
- **Document Agent**: Processes PDFs, chunks them, and embeds them into ChromaDB.
- **Safety Agent**: Evaluates task domains and equipment to generate safety checklists (e.g., LOTO).
- **Audit Agent**: Tracks user actions silently in the background for compliance.

## Multi-Agent Communication
Agents communicate via the `transfer_service.py` which passes context (JSON summaries) between agent types, and `memory_service.py` which continuously extracts key facts from conversations into a structured database to prevent redundant questioning.
# Engineering Agent Architecture

This document details the enhanced architecture of the Engineering Agent, featuring the newly integrated **Risk Assessment Engine** within the Maintenance Intelligence Layer.

## 1. Maintenance Intelligence Architecture

The following architectural diagram illustrates the components of the Maintenance Intelligence Layer.

```mermaid
graph TD
    classDef layerFill fill:#0f172a,stroke:#334155,stroke-width:2px,color:#f8fafc;
    classDef component fill:#1e293b,stroke:#0033A0,stroke-width:2px,color:#cbd5e1,rx:5px,ry:5px;
    classDef newComponent fill:#0033A0,stroke:#60a5fa,stroke-width:3px,color:#ffffff,rx:8px,ry:8px,font-weight:bold;
    
    subgraph MIL[Maintenance Intelligence Layer]
        DI[Document Intelligence]:::component
        ERE[Evidence Retrieval Engine]:::component
        II[Inventory Intelligence]:::component
        VD[Visual Diagnostics]:::component
        RCA[Root Cause Analysis]:::component
        RAE[Risk Assessment Engine]:::newComponent
        RE[Recommendation Engine]:::component
        WI[Workflow Intelligence]:::component
        
        DI --> ERE
        VD --> RCA
        RCA --> RAE
        ERE --> RAE
        II --> RAE
        RAE --> RE
        RE --> WI
    end
    
    class MIL layerFill;
```

## 2. Risk Assessment Workflow

The workflow diagram below demonstrates the pipeline from vision diagnostics through risk assessment to the final engineering report. It includes the inputs, processing stages, and outputs of the new Risk Assessment Engine.

```mermaid
flowchart TD
    %% Tata Steel Enterprise Theme
    classDef processNode fill:#1e293b,stroke:#0033A0,stroke-width:2px,color:#f1f5f9,rx:4px;
    classDef highlightNode fill:#0033A0,stroke:#93c5fd,stroke-width:3px,color:#ffffff,rx:8px,font-weight:bold;
    classDef inputNode fill:#334155,stroke:#475569,stroke-width:1px,color:#cbd5e1;
    classDef processSub fill:#0f172a,stroke:#3b82f6,stroke-width:1px,color:#93c5fd,stroke-dasharray: 5 5;
    classDef outputNode fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5;
    classDef reportNode fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fef2f2;
    classDef container fill:#020617,stroke:#1e293b,stroke-width:2px,color:#94a3b8;

    subgraph Pipeline [Core Engineering Pipeline]
        VDiag[Vision Diagnostics]:::processNode
        RootCause[Root Cause Analysis]:::processNode
        RiskEngine[Risk Assessment Engine]:::highlightNode
        RecEngine[Recommendation Engine]:::processNode
        EngReport[Engineering Report]:::processNode
        
        VDiag -->|Identifies Defects| RootCause
        RootCause -->|Determines Origin| RiskEngine
        RiskEngine -->|Provides Risk Context| RecEngine
        RecEngine -->|Generates Actions| EngReport
    end

    subgraph RiskInputs [Engine Inputs]
        I1(Vision Analysis Results):::inputNode
        I2(Root Cause Analysis Results):::inputNode
        I3(Inventory Availability):::inputNode
        I4(Maintenance History):::inputNode
        I5(SOP Evidence):::inputNode
        I6(Equipment Condition):::inputNode
    end

    subgraph RiskProcessing [Risk Assessment Processing]
        P1[Calculate Risk Level<br/>Low / Medium / High / Critical]:::processSub
        P2[Assess Operational Impact]:::processSub
        P3[Assess Maintenance Priority]:::processSub
        P4[Evaluate Spare Availability Impact]:::processSub
        P5[Generate Maintenance Urgency Score]:::processSub
    end

    subgraph RiskOutputs [Engine Outputs]
        O1(Risk Assessment Report):::outputNode
        O2(Priority Classification):::outputNode
        O3(Maintenance Recommendation):::outputNode
        O4(Action Timeline):::outputNode
        O5(Engineering Decision Support):::outputNode
    end

    %% Connect Inputs to Engine
    I1 -.-> RiskEngine
    I2 -.-> RiskEngine
    I3 -.-> RiskEngine
    I4 -.-> RiskEngine
    I5 -.-> RiskEngine
    I6 -.-> RiskEngine

    %% Connect Engine to Processing Internal
    RiskEngine === P1
    P1 === P2
    P2 === P3
    P3 === P4
    P4 === P5

    %% Connect Processing to Outputs
    P5 === O1
    P5 === O2
    P5 === O3
    P5 === O4
    P5 === O5

    class Pipeline,RiskInputs,RiskOutputs container;
```

## 3. Sample Output Evaluation

> [!WARNING]
> **Asset**: Conveyor Motor CM-101  
> **Detected Issue**: Bearing Wear  
> **Root Cause**: Lubrication Failure  
> **Risk Level**: High  
> **Operational Impact**: Potential downtime within 72 hours  
> **Maintenance Priority**: P1 Critical  
> **Recommended Action**: Immediate inspection and bearing replacement

## Maintenance Outcome Learning Repository

The Maintenance Outcome Repository provides a traceable knowledge base of all completed maintenance work. This is not autonomous retraining, but rather a structured evidence retrieval system.

### Workflow

```mermaid
graph TD
    A[Completed Work Order] -->|Marked as Complete| B[Maintenance Outcome Record]
    B --> C[(Maintenance Outcomes Database)]
    C -->|Evidence Retrieval Engine| D[Engineering Agent Context]
    D --> E[Future Recommendations]
    
    style A fill:#eff6ff,stroke:#3b82f6
    style B fill:#f8fafc,stroke:#94a3b8
    style C fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style D fill:#f0fdf4,stroke:#166534
    style E fill:#fefce8,stroke:#a16207
```

### Purpose
When an Engineer completes a Work Order, the final root cause, taken action, risk level, and downtime avoided are securely logged into the `maintenance_outcomes` table. Future queries to the Engineering Agent related to the same asset or issue will retrieve these outcomes as contextual evidence, significantly speeding up future diagnostics.
