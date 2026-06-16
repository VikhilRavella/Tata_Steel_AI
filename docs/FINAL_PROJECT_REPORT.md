# Final Project Report

## Executive Summary
This application is an end-to-end Industrial AI Maintenance Assistant designed to connect field engineers with powerful vision diagnostics, document intelligence (RAG), and a full-featured inventory and supervisor approval workflow.

## Problem Statement
Plant engineers traditionally face disconnected SOP documents, manual reporting workflows, and disjointed inventory requests that slow down critical maintenance timelines.

## Solution Overview
A unified portal utilizing localized AI models to deliver autonomous vision inspections, immediate safety document retrieval, and natural language database interactions.

## Features
- Agentic Chat via Engineering Agent
- Vision Equipment Diagnostics
- PDF Knowledge Base RAG
- Autonomous Inventory & Work Order Generation
- Hierarchical Portals (Engineer, Supervisor, Manager)

## AI Models Used
- `qwen2.5-coder:7b` (Primary Logic / Ollama)
- `mistral:latest` (Background RAG / Ollama)
- `Qwen3-VL-8B-Instruct` (Vision / Hugging Face)
- `BAAI/bge-small-en-v1.5` (Embeddings / Sentence Transformers)

## PDF RAG Pipeline
Ingests heavy engineering manuals, automatically chunks text, and embeds them into ChromaDB for highly contextual safety and troubleshooting retrieval.

## Vision Analysis
Detects physical defects, assesses risk levels, and recommends root causes natively via Hugging Face Transformers.

## Inventory Workflow
Fully integrated with the text-agent to autonomously parse engineer intent and generate database requests without manual form entry.

## Testing Results
System boots correctly within memory limits. Text LLM was rolled back to ensure perfect stability for demonstration.

## API Audit
All endpoints passing. Legacy vision REST routes cleanly removed.

## UI Audit
User interface streamlined and verified for Demo flow.

## Performance Results
Stable inference and retrieval times with graceful hardware fallbacks.

## Demo Readiness
100% Ready.

## Final Acceptance
Approved for hackathon submission.
