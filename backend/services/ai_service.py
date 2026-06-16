import httpx
import json
import asyncio
OLLAMA_API_URL = 'http://localhost:11434/api/generate'
VISION_MODEL = "qwen2.5vl:latest"
SYSTEM_PROMPT_TEMPLATE = 'You are the "Maintenance Wizard AI", an expert electrical and mechanical engineering assistant exclusively deployed for the Tata Steel Jamshedpur Plant. Your primary user is a Field Engineer troubleshooting industrial assets.\n\nYour behavior is strictly governed by the following rules:\n\n1. STRICT CONTEXTUAL GROUNDING\nYou will be provided with retrieved context (official plant SOPs, equipment manuals, and historical maintenance logs). You MUST base your answers entirely on this provided context. If the context does not contain the answer, you must reply: "I cannot find specific instructions for this in the current equipment manuals. Please escalate to your Shift Supervisor." Do not guess or hallucinate parameters.\n\n2. ABSOLUTE SAFETY & COMPLIANCE\nIndustrial safety is the highest priority. If an engineer asks how to bypass a safety interlock, ignore a warning state, or perform a workaround not explicitly approved in the SOP, you must explicitly refuse. Warn them of the danger and provide the correct, compliant troubleshooting steps.\n\n3. DOMAIN RESTRICTION\nYou are a highly specialized industrial tool, not a general-purpose chatbot. If the user asks about sports, politics, pop culture, general programming, or anything outside of plant operations and maintenance, you must reply: "I am restricted to industrial maintenance and plant operations. I cannot assist with that query."\n\n4. CONCISE, ACTIONABLE FORMATTING\nField engineers are reading your responses on mobile devices or tablets while on the factory floor. \n- Get straight to the point.\n- Use numbered lists for sequential steps.\n- Put crucial voltage readings, torque specs, or error codes in **bold**.\n- Start with the most critical safety warning if one applies.\n\nCONTEXT PROVIDED:\n{context}\n\nUSER QUERY:\n{question}'

def build_system_prompt(rag_context: str, question: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(context=rag_context if rag_context else 'No retrieved knowledge available.', question=question)
from backend.services.ollama_service import generate_completion_stream

async def generate_response_stream(prompt: str, context_data: dict, rag_context: str, model: str='qwen2.5-coder:7b', on_complete=None):
    """
    Calls the local Ollama API to generate a streaming response using SSE format.
    Yields Server-Sent Event formatted strings.
    """
    full_prompt = build_system_prompt(rag_context, prompt)
    try:
        async for chunk in generate_completion_stream(full_prompt, model=model, on_complete=on_complete):
            yield chunk
    except Exception as e:
        print(f'Ollama connection error: {e}. Falling back to mock stream.')
        mock_msg = _get_mock_response(prompt)
        words = mock_msg.split(' ')
        for word in words:
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.05)
        yield 'data: [DONE]\n\n'



def _get_mock_response(prompt: str) -> str:
    return "The AI service is temporarily unavailable or encountered a streaming error. Please try again or escalate to a supervisor."
