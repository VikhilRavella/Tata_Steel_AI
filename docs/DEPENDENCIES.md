# Project Dependencies

- **Python Version:** 3.10+
- **FastAPI:** Core backend web framework
- **Transformers:** Vision ecosystem (`qwen-vl-utils`, `accelerate`)
- **Torch:** PyTorch backend for hardware acceleration
- **ChromaDB:** Local vector embedding storage
- **SQLite:** Relational database (`SQLAlchemy`)
- **Pillow:** Image processing and compression
- **Sentence Transformers:** Text chunk embedding
- **Ollama:** Primary conversational inference daemon

## Installation Commands

Ensure Ollama is installed natively on your system first, and then pull the required models:
```bash
ollama run qwen2.5-coder:7b
ollama run mistral
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```
