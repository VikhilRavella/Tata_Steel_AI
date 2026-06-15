# AI Model Setup Guide

This project leverages local, privacy-first AI models running entirely on-premises using Ollama.

## 1. Installation Steps
To run the models, you must first install Ollama on your machine.
1. Navigate to: [https://ollama.com/download](https://ollama.com/download)
2. Download and install the application for your operating system.
3. Keep Ollama running in the background.

## 2. Required Models & Startup Commands
Open your terminal and run the following commands one by one to pull the required models:

```bash
ollama pull mistral:latest
ollama pull qwen2.5vl:latest
ollama pull qwen2.5-coder:7b
ollama pull BAAI/bge-small-en-v1.5
```

Verify that the models are installed successfully by running:
```bash
ollama list
```
Finally, ensure the inference server is running:
```bash
ollama serve
```

## 3. Model Responsibilities

### `qwen2.5-coder:7b`
- **Agent**: Engineering Agent
- **Purpose**: Deep Engineering Analysis, Root Cause Analysis, PDF RAG Generation, Complex Industrial Reasoning.
- **Input**: Text & Document Context
- **Output**: Structured Text & Markdown (Moderate Response Time: 3-5s)

### `qwen2.5vl:latest`
- **Agent**: Vision Service Engine
- **Purpose**: Visual Diagnostics, Defect Detection, Equipment Inspection, Structural Fault Analysis.
- **Input**: Image (Base64) & Text Prompt
- **Output**: Descriptive Text & JSON (Moderate Response Time: 4-6s)

### `mistral:latest`
- **Agent**: Sandbox Agent & Intent Decision Router
- **Purpose**: Fast Chat Responses, Work Order Automation, Inventory Queries, Supervisor Queries.
- **Input**: Conversational Text
- **Output**: Conversational Text & JSON (Fast Response Time: 1-2s)

### `BAAI/bge-small-en-v1.5`
- **Agent**: Document Intelligence & ChromaDB
- **Purpose**: Vector Embeddings for SOPs, Technical Manuals, and RAG Knowledge Retrieval.
- **Input**: Text Chunks
- **Output**: 384-Dimensional Vectors (Instant Response Time: <1s)

## 4. Troubleshooting
- **Model not found error**: Ensure you ran `ollama pull <model_name>` before launching the app.
- **Connection Refused**: Verify that Ollama is actively running in your system tray or run `ollama serve` in a dedicated terminal.
- **OOM (Out of Memory)**: If using a low RAM machine, the startup orchestrator (`start_app.py`) will automatically optimize model context limits.
