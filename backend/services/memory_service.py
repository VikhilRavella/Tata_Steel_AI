from sqlalchemy.future import select
from sqlalchemy.orm import Session
import json
import datetime
from sqlalchemy.orm import Session
import backend.models as models
from backend.services.ollama_service import generate_completion_sync
MEMORY_EXTRACTION_PROMPT = 'Analyze the following interaction between a user and an AI Agent.\nExtract any new, important project context, user preferences, requirements, or terminology corrections.\n\nINTERACTION:\nUser: {user_message}\nAgent: {agent_message}\n\nCATEGORIES:\n- user_preference (User communication style, formatting preferences)\n- project_goal (High level project objectives)\n- project_constraint (Limitations, tech stack, constraints)\n- architecture_decision (Database, API, technical decisions)\n- technical_requirement (Specific functional/non-functional requirements)\n- spelling_correction (If the user misspelled a domain term and you understood it, e.g. "emgcy dispatch" -> "emergency dispatch")\n- terminology (Domain-specific terminology to remember)\n\nRespond STRICTLY with valid JSON representing a list of extracted memories. For spelling_correction, include the "incorrect" and "correct" fields in the content. For others, just put the fact in content.\n\nExample:\n[\n  {{\n    "memory_type": "project_goal",\n    "content": "Build an Industrial Maintenance platform.",\n    "importance_score": 5\n  }},\n  {{\n    "memory_type": "spelling_correction",\n    "content": "{{"incorrect": "emgcy", "correct": "emergency"}}",\n    "importance_score": 3\n  }}\n]\n\nIf nothing new or important was discussed, return an empty list: []\n'

async def extract_and_update_memory(user_id: int, session_id: str, user_message: str, agent_message: str, db: Session):
    prompt = MEMORY_EXTRACTION_PROMPT.format(user_message=user_message, agent_message=agent_message)
    try:
        import inspect
        from backend.services.ollama_service import generate_completion_sync
        if inspect.iscoroutinefunction(generate_completion_sync):
            llm_response = await generate_completion_sync(prompt, model='qwen2.5-coder:7b')
        else:
            llm_response = generate_completion_sync(prompt, model='qwen2.5-coder:7b')
            if inspect.iscoroutine(llm_response):
                llm_response = await llm_response
    except Exception as e:
        print(f'Failed to run generate_completion_sync: {e}')
        return

    try:
        if '```json' in llm_response:
            json_str = llm_response.split('```json')[1].split('```')[0].strip()
            memories = json.loads(json_str)
        else:
            memories = json.loads(llm_response)
        for mem in memories:
            mem_type = mem.get('memory_type', 'General')
            mem_val = mem.get('content', '')
            mem_key = mem.get('memory_key', 'Extracted')
            if mem_val:
                existing = db.query(models.EngineeringMemory).filter(
                    models.EngineeringMemory.session_id == session_id, 
                    models.EngineeringMemory.memory_type == mem_type, 
                    models.EngineeringMemory.memory_value == mem_val
                ).first()
                if not existing:
                    new_mem = models.EngineeringMemory(
                        session_id=session_id, 
                        memory_type=mem_type, 
                        memory_key=mem_key,
                        memory_value=mem_val
                    )
                    db.add(new_mem)
        db.commit()
    except Exception as e:
        print(f'Memory extraction failed or returned invalid JSON: {e}')

def get_global_context(session_id: str, db: Session) -> str:
    memories = db.query(models.EngineeringMemory).filter(models.EngineeringMemory.session_id == session_id).limit(10).all()
    if not memories:
        return 'No previous project context found.'
    context_str = '=== SHARED PROJECT MEMORY ===\n'
    for m in memories:
        context_str += f'- [{m.memory_type}] {m.memory_value}\n'
    return context_str + '\n===============================\n'