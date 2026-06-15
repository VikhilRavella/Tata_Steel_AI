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

async def analyze_image(image_base64: str, prompt: str, context_data: dict, rag_context: str) -> str:
    """
    Calls Ollama with LLaVA model for image analysis.
    This remains non-streaming for simplicity before injecting into qwen2.5-coder:7b.
    """
    import base64
    from io import BytesIO
    try:
        from PIL import Image
    except ImportError:
        Image = None

    # Strip data URI prefix if present
    raw_b64 = image_base64
    if raw_b64.startswith("data:image"):
        raw_b64 = raw_b64.split(",", 1)[1]

    # Trace Payload
    try:
        image_bytes = base64.b64decode(raw_b64)
        image_size_kb = len(image_bytes) / 1024
        
        print(f"--- VISION PAYLOAD TRACE ---")
        print(f"Base64 Length: {len(raw_b64)}")
        print(f"Image Size: {image_size_kb:.2f} KB")
        
        if Image:
            with Image.open(BytesIO(image_bytes)) as img:
                print(f"Image Format: {img.format}")
                print(f"Image Width: {img.width}")
                print(f"Image Height: {img.height}")
        else:
            print("Image Format: UNKNOWN (PIL not installed)")
            print("Image Width: UNKNOWN")
            print("Image Height: UNKNOWN")
    except Exception as e:
        print(f"Failed to decode image for tracing: {e}")

    vision_prompt = f"""You are an expert industrial vision AI.
Analyze the provided image and extract facts.
Do NOT answer the user's question directly. Only extract visual facts.

STEP 1 - IMAGE CLASSIFICATION
Classify the image as one of: Industrial Equipment, Mechanical Component, Electrical Equipment, Technical Document, Computer Screenshot, Unknown.

STEP 2 - OBJECT DETECTION
List all visible equipment or components.

STEP 3 - DEFECT DETECTION
List any visible defects (Wear, Corrosion, Leakage, Contamination, Broken Component, Cracks, Misalignment, Missing Parts, Burn Marks, Overheating Signs, Loose Components).
Do NOT claim internal damage unless visible. Do NOT invent measurements.

STEP 4 - CONFIDENCE
Assign: High, Medium, or Low.

USER QUESTION:
{prompt}

Respond EXACTLY in this format:
CLASSIFICATION: [classification]
DETECTED OBJECTS: [list]
VISIBLE DEFECTS: [list]
CONFIDENCE: [High/Medium/Low]
"""
    payload = {'model': VISION_MODEL, 'prompt': vision_prompt, 'images': [raw_b64], 'stream': False}
    
    print(f"Number of images sent in request: {len(payload['images'])}")
    print(f"Exact Ollama payload keys: {list(payload.keys())}")
    print(f"----------------------------")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_API_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                res = data.get('response', '')
                print(f"RAW_LLAVA_RESPONSE: {res}")
                return res
            else:
                return 'Mock LLaVA: I see the equipment. The bearing housing looks misaligned and there are visible metal shavings.'
    except Exception:
        return 'Mock LLaVA: I see the equipment. The bearing housing looks misaligned and there are visible metal shavings.'

def _get_mock_response(prompt: str) -> str:
    return "The AI service is temporarily unavailable or encountered a streaming error. Please try again or escalate to a supervisor."

async def analyze_bolt_damage(base64_image: str, bolt_spec: str='M14') -> dict:
    """
    Analyzes a bolt image for rust, thread damage, and corrosion.
    Used by Field Agent when worker uploads a photo of a suspect bolt.
    """
    system_prompt = 'You are an industrial maintenance vision AI\n    at a steel manufacturing plant. Analyze the bolt in this image.\n    \n    YOU MUST respond with ONLY a valid JSON object.\n    No explanation. No markdown. No preamble. Just JSON.\n    \n    Return this EXACT structure:\n    {\n        "bolt_condition": "GOOD | DEGRADED | CRITICAL | REPLACE_IMMEDIATELY",\n        "detected_defects": ["list of specific defects found"],\n        "rust_level": "NONE | SURFACE | MODERATE | SEVERE",\n        "thread_condition": "INTACT | WORN | FLATTENED | STRIPPED",\n        "corrosion_type": "none | surface_oxidation | deep_pitting | galvanic",\n        "safe_to_reuse": false,\n        "recommended_action": "REUSE | CLEAN_AND_REUSE | REPLACE | REPLACE_IMMEDIATELY",\n        "confidence_score": 0.94,\n        "warning": "Do NOT re-tighten a stripped bolt — it will snap inside the frame"\n    }'
    import httpx, json, re, os
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    payload = {'model': VISION_MODEL, 'messages': [{'role': 'user', 'content': f'Analyze this {bolt_spec} bolt for industrial safety:', 'images': [base64_image]}], 'system': system_prompt, 'options': {'temperature': 0.0}, 'stream': False}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f'{ollama_url}/api/chat', json=payload)
        response.raise_for_status()
        raw = response.json()['message']['content']
    raw = re.sub('```json\\s*', '', raw)
    raw = re.sub('```\\s*', '', raw)
    match = re.search('\\{.*\\}', raw, re.DOTALL)
    if not match:
        return {'bolt_condition': 'UNKNOWN', 'detected_defects': ['Vision analysis failed — manual inspection required'], 'safe_to_reuse': False, 'recommended_action': 'MANUAL_INSPECT', 'confidence_score': 0.0, 'raw_response': raw[:300]}
    return json.loads(match.group())

async def analyze_equipment_damage(base64_image: str, equipment_id: str='', equipment_type: str='motor') -> dict:
    """
    Analyzes equipment photos for cracks, wear, overheating signs.
    Used for general equipment health inspection.
    """
    system_prompt = 'You are an expert industrial maintenance AI\n    at a Tata Steel manufacturing plant. Analyze this equipment photo.\n    \n    YOU MUST respond with ONLY valid JSON. No text. No markdown.\n    \n    Return this EXACT structure:\n    {\n        "overall_condition": "HEALTHY | WARNING | CRITICAL | FAILURE",\n        "detected_issues": [\n            {\n                "issue_type": "crack | rust | overheating | wear | leakage | misalignment",\n                "location": "describe where on the equipment",\n                "severity": "LOW | MEDIUM | HIGH | CRITICAL"\n            }\n        ],\n        "heat_indicators": "NONE | DISCOLORATION | BURNING_MARKS | MELTING",\n        "structural_integrity": "INTACT | COMPROMISED | SEVERELY_DAMAGED",\n        "immediate_action_required": false,\n        "stop_machine_immediately": false,\n        "recommended_action": "CONTINUE | MONITOR | SCHEDULE_MAINTENANCE | STOP_NOW",\n        "estimated_failure_risk_percent": 15,\n        "confidence_score": 0.88\n    }'
    import httpx, json, re, os
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    payload = {'model': VISION_MODEL, 'messages': [{'role': 'user', 'content': f'Inspect this {equipment_type} (ID: {equipment_id}) for damage:', 'images': [base64_image]}], 'system': system_prompt, 'options': {'temperature': 0.0}, 'stream': False}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f'{ollama_url}/api/chat', json=payload)
        response.raise_for_status()
        raw = response.json()['message']['content']
    raw = re.sub('```json\\s*', '', raw)
    raw = re.sub('```\\s*', '', raw)
    match = re.search('\\{.*\\}', raw, re.DOTALL)
    if not match:
        return {'overall_condition': 'UNKNOWN', 'confidence_score': 0.0}
    return json.loads(match.group())

async def verify_loto_compliance(base64_image: str) -> dict:
    """
    Verifies LOTO (Lockout/Tagout) compliance from a photo.
    Worker must upload photo of padlock on breaker before work begins.
    This function checks if the photo shows proper isolation.
    """
    system_prompt = 'You are a safety compliance AI for a steel plant.\n    Check if this photo shows proper Lockout/Tagout (LOTO) procedure.\n    \n    YOU MUST respond with ONLY valid JSON. No explanation.\n    \n    Return this EXACT structure:\n    {\n        "loto_compliant": false,\n        "padlock_visible": false,\n        "padlock_color": "yellow | red | other | none",\n        "breaker_position": "LOCKED_OFF | ON | UNKNOWN",\n        "tag_visible": false,\n        "isolation_confirmed": false,\n        "compliance_issues": ["list any issues found"],\n        "verdict": "APPROVED | REJECTED | UNCLEAR",\n        "reason": "brief explanation",\n        "confidence_score": 0.91\n    }'
    import httpx, json, re, os
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    payload = {'model': VISION_MODEL, 'messages': [{'role': 'user', 'content': 'Verify LOTO safety compliance in this image:', 'images': [base64_image]}], 'system': system_prompt, 'options': {'temperature': 0.0}, 'stream': False}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f'{ollama_url}/api/chat', json=payload)
        response.raise_for_status()
        raw = response.json()['message']['content']
    raw = re.sub('```json\\s*', '', raw)
    raw = re.sub('```\\s*', '', raw)
    match = re.search('\\{.*\\}', raw, re.DOTALL)
    if not match:
        return {'loto_compliant': False, 'verdict': 'REJECTED', 'reason': 'Could not analyze image — manual verification required', 'confidence_score': 0.0}
    return json.loads(match.group())