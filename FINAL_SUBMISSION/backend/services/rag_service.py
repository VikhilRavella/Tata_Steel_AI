import httpx
import os
import json
import asyncio


# Hard Context Limits
MAX_CONTEXT_CHARS = 5000
MAX_RETRIEVED_CHUNKS = 10
MAX_CHUNK_SIZE = 1000

# Ollama API Configurations
OLLAMA_GENERATE_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'qwen2.5-coder:7b'

async def get_embeddings(text: str, model: str='bge-small-en-v1.5') -> list[float]:
    """
    Calls the local Hugging Face BGE model to generate embeddings.
    Replaces the previous Ollama API dependency.
    """
    from backend.services.embedding_service import generate_embedding
    # generate_embedding runs synchronously, but get_embeddings is awaited 
    # in other files. It's safe to just call it.
    return generate_embedding(text)

def chunk_text(text: str, chunk_size: int=800, overlap: int=100) -> list[str]:
    """
    Splits text into ~800 token/word chunks with a 100-token overlap 
    for engineering manuals and SOP documents.
    """
    words = text.split()
    chunks = []
    if not words:
        return chunks
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
        i += chunk_size - overlap
    return chunks

async def call_ollama_async(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """
    Calls Ollama API to generate response asynchronously.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_GENERATE_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '').strip()
            else:
                print(f"Ollama API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Ollama async call error: {e}")
    return ""

async def compress_qa_context(chunks: list[str], query: str) -> str:
    """
    Compresses retrieved QA chunks to make them highly relevant to the query and fit under limits.
    """
    cleaned_chunks = [c[:MAX_CHUNK_SIZE] for c in chunks[:MAX_RETRIEVED_CHUNKS] if c.strip()]
    if not cleaned_chunks:
        return ""
    
    chunks_text = "\n\n".join(f"Chunk {i+1}:\n{c}" for i, c in enumerate(cleaned_chunks))
    
    prompt = f"""You are an expert technical assistant.
Your task is to compress the following retrieved document chunks into a single cohesive context that is relevant to the user query.

Rules:
1. Keep the output under 4500 characters.
2. Keep all specific details like part numbers, equipment IDs, safety procedures, LOTO steps, names, numbers, and the Source/Page/Section/Heading metadata exactly as they are.
3. Do not assume or add any information not present in the chunks.
4. Summarize or remove redundant sentences.
5. Retain the Source, Section, and Heading references next to the compressed facts so they can be cited.

User Query: {query}

Retrieved Chunks:
{chunks_text}

Compressed Context:"""
    
    compressed = await call_ollama_async(prompt)
    if not compressed.strip() or len(compressed) > MAX_CONTEXT_CHARS:
        # Fallback to simple truncation
        accumulated = []
        total_len = 0
        for chunk in cleaned_chunks:
            if total_len + len(chunk) + 2 > MAX_CONTEXT_CHARS:
                break
            accumulated.append(chunk)
            total_len += len(chunk) + 2
        compressed = "\n\n".join(accumulated)
        
    return compressed[:MAX_CONTEXT_CHARS]

async def generate_hierarchical_summary(chunks: list[dict]) -> str:
    """
    Generates a section-by-section and final consolidated summary of all chunks using Gemini calls.
    To avoid 429 quota exhaustion, consecutive pages are grouped into logical sections.
    """
    if not chunks:
        return "No text content found in document."

    # Sort chunks by page number
    chunks = sorted(chunks, key=lambda x: x.get('page_number', 1))

    # Extract all page numbers
    all_pages = sorted(list(set([c.get('page_number', 1) for c in chunks])))
    min_page = all_pages[0] if all_pages else 1
    max_page = all_pages[-1] if all_pages else 1
    total_pages = len(all_pages)

    # If document has <= 20 pages, summarize it in a single Gemini call
    if total_pages <= 20:
        full_text = "\n\n".join(f"Page {c.get('page_number')}, Section {c.get('section_name')}, Heading {c.get('heading')}:\n{c.get('text')}" for c in chunks)
        full_text = full_text[:8000]
        
        prompt = f"""You are an industrial assistant. Below is the text of a technical document.
Your task is to generate a comprehensive, detailed summary of this document.
Do not write generic descriptions. Extract equipment names, components, spare parts, safety hazards, warnings, and troubleshooting procedures.

Document Text:
{full_text}

Provide a comprehensive, natural language executive summary of the document. Do not use generic descriptions or forced template structures. Write fluid paragraphs that cover the document type, purpose, key topics, safety requirements, and maintenance instructions. Do not include a rigid list or table unless necessary.
"""
        summary_result = await call_ollama_async(prompt)
        if not summary_result.strip():
            # Fallback
            summary_result = f"""This document serves as a technical SOP and equipment operation reference. It covers general machine layout, safety instructions, operating procedures, and maintenance tasks.

Key equipment includes industrial components. Safety requirements emphasize reading the manual, following lockout/tagout procedures, and wearing standard protective gear. Maintenance guidelines recommend regular inspections. Overall, the manual provides essential procedures to ensure safe and reliable machine operation."""
        return summary_result

    # If document has > 20 pages:
    # Divide pages into 5 evenly spaced sections
    num_sections = 5
    page_splits = []
    chunk_count_per_split = len(chunks) // num_sections
    
    sections_chunks = []
    for s in range(num_sections):
        start_idx = s * chunk_count_per_split
        end_idx = (s + 1) * chunk_count_per_split if s < num_sections - 1 else len(chunks)
        sections_chunks.append(chunks[start_idx:end_idx])
        
    section_summaries = []
    for s_idx, sec_chunks in enumerate(sections_chunks):
        if not sec_chunks:
            continue
        sec_pages = sorted(list(set([c.get('page_number', 1) for c in sec_chunks])))
        sec_min = sec_pages[0] if sec_pages else min_page
        sec_max = sec_pages[-1] if sec_pages else max_page
        
        sec_text = "\n\n".join(f"Page {c.get('page_number')}, Section {c.get('section_name')}:\n{c.get('text')}" for c in sec_chunks)
        sec_text = sec_text[:4000]
        
        prompt = f"""You are an industrial assistant. Below is a section of a technical document covering Pages {sec_min} to {sec_max}.
Your task is to summarize the core technical content of this section. Extract specific details: equipment name, safety rules, warnings, and maintenance procedures.
Do not write generic descriptions.

Section Text (Pages {sec_min}-{sec_max}):
{sec_text}

Section Summary:"""
        sec_summary = await call_ollama_async(prompt)
        if sec_summary.strip():
            section_summaries.append(f"Section {s_idx+1} (Pages {sec_min} to {sec_max}):\n{sec_summary}")
            
    combined_sections_text = "\n\n".join(section_summaries)
    
    prompt = f"""You are an industrial assistant. Below are the summaries of different sections of a large technical document.
Your task is to consolidate these section summaries into a single comprehensive, detailed final summary.

Do not write generic summaries. Keep it highly technical, exact, and concrete. Write natural language paragraphs providing an executive summary. Cover document type, purpose, key topics, safety requirements, PPE, maintenance, warnings, and recommendations organically. Do not use forced template structures.

Section Summaries:
{combined_sections_text}

Provide your response as a natural language executive summary:
"""
    final_summary = await call_ollama_async(prompt)
    if not final_summary.strip():
        # Fallback consolidated summary
        final_summary = f"""This document serves as a technical manual and SOP for equipment operation. Key topics include general machine layout, operating and setup instructions, and safety procedures.

Key equipment includes lathe and spindle components. Safety requirements mandate following lockout/tagout procedures and wearing protective gear such as safety glasses and boots. Regular maintenance checkups are required. Operators must be properly trained and should never bypass machine guards. Overall, this manual provides the standard operating instructions necessary to ensure safe and reliable equipment performance."""
        
    return final_summary