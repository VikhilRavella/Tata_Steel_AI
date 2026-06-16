# System Architecture

## Complete System Architecture
- **Frontend:** React / Next.js
- **Backend:** FastAPI (Python)
- **Relational Database:** SQLite (SQLAlchemy)
- **Vector Database:** ChromaDB
- **Agentic Engine:** Ollama (`qwen2.5-coder:7b`, `mistral`)
- **Vision Engine:** Hugging Face Transformers (`Qwen/Qwen2-VL` architecture implementation)
- **Embedding Engine:** Hugging Face Sentence Transformers (`BAAI/bge-small-en-v1.5`)

## Engineering Agent Workflow
Engineer Query → Intent Router → Module Selector (RAG / Vision / Chat) → Ollama (`qwen2.5-coder:7b`) → Streamed Response

## PDF RAG Workflow
Manager PDF Upload → Text Extraction → Chunking (Size 800, Overlap 100) → `BAAI/bge-small-en-v1.5` → ChromaDB Vectorization → Semantic Retrieval → Engineering Agent Context

## Vision Analysis Workflow
Equipment Image Upload → Base64 Encode → Hugging Face `Qwen3-VL` → JSON Defect Detection → Engineering Agent Context → Conversational Maintenance Recommendation

## Inventory Workflow
Engineer Query / Vision Result → LLM Trigger Generation `[INVENTORY_REQUEST]` → Inventory Service API → Database Deduction/Allocation → Supervisor Approval Portal

## End-to-End Workflow
1. **Manager Portal:** Ingests raw SOPs and Parts data.
2. **Supervisor Portal:** Manages team workloads and approvals.
3. **Engineer Portal:** AI-driven diagnostic sessions and conversational database operations.

## Database Relationships
- `User` ↔ `EngineeringSession` (1:N)
- `EngineeringSession` ↔ `EngineeringMessage` (1:N)
- `EngineeringSession` ↔ `EngineeringReport` (1:N)
- `Equipment` ↔ `WorkOrder` (1:N)
- `Equipment` ↔ `MaintenanceHistory` (1:N)
- `InventoryMaster` ↔ `InventoryTransaction` (1:N)
