# Tata Steel AI Hackathon - Final Interview Prep Guide

Congratulations on making it to the Top 40! The interview panel will want to see that you deeply understand the architecture, the problem it solves, and why you made specific technical choices.

## 1. The Core Problem Statement
*How you should explain it to the judges:*
"Currently, field engineers waste hours manually searching through heavy safety manuals (SOPs), typing up routine maintenance reports, and dealing with a disconnected inventory system. My solution unifies this entire process. It gives the engineer an AI assistant on the factory floor that can instantly diagnose physical equipment via images, pull exact safety guidelines from manuals, and autonomously generate work orders and inventory requests for supervisor approval."

---

## 2. The End-to-End Architecture (How It Works)
When the judges ask "walk us through the architecture," explain these three distinct layers:

### A. The Document Intelligence (PDF RAG) Layer
* **What it does:** Allows engineers to instantly search safety documents and SOPs.
* **How it works:** When a manager uploads a PDF, the backend extracts the text, splits it into chunks of 800 characters, and converts those chunks into mathematical vectors using the **Hugging Face BAAI/bge-small-en-v1.5** model. These vectors are stored in a local **ChromaDB**. When an engineer asks a question, the system searches ChromaDB for the closest matching chunks and feeds them to the LLM.

### B. The Multimodal Vision Layer
* **What it does:** Analyzes photos of broken equipment (like a cracked bearing or leaking pump).
* **How it works:** The engineer uploads an image via the chat interface. The backend intercepts this image and passes it to the **Hugging Face Qwen3-VL-8B-Instruct** vision model. This model analyzes the image, identifies the equipment type, detects specific defects (like corrosion or cracks), and outputs a structured JSON report. The Engineering Agent translates this JSON into a readable markdown report and risk assessment for the engineer.

### C. The Conversational & Business Logic Layer
* **What it does:** Orchestrates the chat, connects to the SQLite database, and handles Inventory/Work Orders.
* **How it works:** The central brain of the chat is powered by **qwen2.5-coder:7b** running on **Ollama**. As the engineer chats, the LLM determines their "Intent". If the engineer says "I need a replacement motor", the LLM generates a hidden system trigger (`[INVENTORY_REQUEST]`). The FastAPI backend intercepts this trigger, automatically queries the `SQLite` inventory database, deducts the stock, and logs an approval request for the Supervisor portal.

---

## 3. Why Did You Choose These Technologies?
Judges always ask *why* you chose a specific tech stack. Here are your answers:

* **Why Ollama & Local Models?**
  "Data privacy is critical for Tata Steel. Sending proprietary plant schematics or equipment data to OpenAI/Cloud providers is a massive security risk. By running Ollama and Hugging Face models completely locally on the edge hardware, we ensure 100% data security and zero latency dependency on internet connection."

* **Why Qwen3-VL for Vision?**
  "Industrial equipment analysis requires highly capable multimodal reasoning. Qwen3-VL is currently state-of-the-art for open-source visual language tasks, allowing the system to not just classify an image, but read gauges, spot micro-fractures, and output structured JSON."

* **Why FastAPI & SQLite?**
  "FastAPI provides incredibly fast, asynchronous REST endpoints which are required for streaming Server-Sent Events (SSE) back to the chat UI smoothly. SQLite was chosen for this prototype for rapid development and zero-config deployment, but the SQLAlchemy ORM makes it trivial to swap to PostgreSQL for enterprise scale."

* **Why BAAI/bge-small for Embeddings?**
  "It ranks near the top of the Massive Text Embedding Benchmark (MTEB) for open-source models while having a tiny memory footprint. It’s highly efficient for vectorizing dense engineering manuals."

---

## 4. Key Workflows to Emphasize

**1. The Supervisor Approval Loop:**
Emphasize that the AI doesn't just do whatever it wants. It has "Human-in-the-Loop" constraints. When the AI requests a spare part from the warehouse, it doesn't immediately dispatch it; it queues it in the Supervisor Portal for human approval. This proves you thought about enterprise safety and accountability.

**2. Memory & Hardware Constraints:**
Mention that you built "Lazy Loading" and "CPU Fallbacks". Explain that you knew industrial edge servers might not have massive GPUs, so you engineered the system to check VRAM availability and fallback to system RAM/CPU processing if needed so the application never crashes. This shows senior-level engineering maturity.

---

## 5. Potential Interview Questions & Answers

**Q: What happens if the LLM hallucinates an answer about safety?**
*A: "I implemented Strict Contextual Grounding in the system prompt. The agent is strictly instructed to only answer based on the retrieved ChromaDB context. If the answer isn't in the SOP, it refuses to guess and tells the engineer to escalate to a supervisor. Industrial safety is non-negotiable."*

**Q: How do you handle large PDF manuals?**
*A: "Heavy manuals are processed asynchronously. They are chunked with a 100-character overlap to ensure context isn't lost between pages, and stored efficiently in the vector database."*

**Q: How would you scale this for all Tata Steel plants globally?**
*A: "I would migrate the SQLite database to a distributed PostgreSQL cluster. The FastAPI backend is completely stateless, meaning it can be containerized using Docker and deployed on Kubernetes. The local LLMs could be hosted on dedicated internal GPU inference servers (like vLLM or Triton) accessible via private endpoints by the different plants."*
