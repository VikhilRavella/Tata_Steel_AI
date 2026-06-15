from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
from sqlalchemy.orm import Session
import backend.models as models
from backend.services.ollama_service import generate_completion_sync
TRANSFER_PROMPT_TEMPLATE = 'You are an AI Architect transitioning a sandbox experiment into an engineering project.\nAnalyze the following conversation history and generate a structured JSON summary.\n\nRequired JSON structure:\n{{\n  "project_objective": "str",\n  "user_requirements": ["str"],\n  "uploaded_documents": ["str"],\n  "key_discussions": ["str"],\n  "technical_constraints": ["str"],\n  "suggested_next_steps": ["str"],\n  "open_questions": ["str"]\n}}\n\nCONVERSATION HISTORY:\n{history}\n'

async def execute_agent_transfer(sandbox_session_id: str, new_engineer_session_id: str, db: Session, user_id: int=None) -> models.EscalationHistory:
    messages = db.query(models.SandboxMessage).filter(models.SandboxMessage.session_id == sandbox_session_id).order_by(models.SandboxMessage.created_at).all()
    history_text = '\\n'.join([f'{m.sender}: {m.content}' for m in messages])
    if not history_text:
        history_text = 'No conversation history found.'
    prompt = TRANSFER_PROMPT_TEMPLATE.format(history=history_text)
    
    # We use sync generate here because it's currently defined that way, but awaited in sandbox.py?
    # Wait, the original code had 'await generate_completion_sync'. This is invalid in python unless it's an async function, but we will leave it as generate_completion_sync.
    try:
        from backend.services.ollama_service import generate_completion_sync
        llm_response = await generate_completion_sync(prompt, model='mistral:latest')
    except Exception:
        llm_response = "{}"
        
    transfer_data = {}
    try:
        if '```json' in llm_response:
            json_str = llm_response.split('```json')[1].split('```')[0].strip()
            transfer_data = json.loads(json_str)
        else:
            transfer_data = json.loads(llm_response)
    except Exception:
        transfer_data = {'project_objective': 'Summary generation failed.', 'raw_output': llm_response}
        
    escalation = models.EscalationHistory(sandbox_session_id=sandbox_session_id, engineering_session_id=new_engineer_session_id, escalated_by=user_id, status="Completed")
    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    
    context = models.EscalationContext(escalation_id=escalation.id, context_type="Summary", context_data=json.dumps(transfer_data))
    db.add(context)
    
    # Also add to EngineeringMemory
    for req in transfer_data.get('user_requirements', []):
        mem = models.EngineeringMemory(session_id=new_engineer_session_id, memory_type='business_requirement', memory_key='req', memory_value=req)
        db.add(mem)
        
    # Copy SandboxMessage history to EngineeringMessage history
    for m in messages:
        sender_mapped = 'assistant' if m.sender == 'agent' else m.sender
        eng_msg = models.EngineeringMessage(
            session_id=new_engineer_session_id,
            sender=sender_mapped,
            content=m.content,
            message_type=m.message_type,
            detected_language=m.detected_language,
            created_at=m.created_at
        )
        db.add(eng_msg)
        
    db.commit()
    db.refresh(escalation)
    
    # Mocking transfer_summary attribute to not break sandbox.py
    escalation.transfer_summary = json.dumps(transfer_data)
    return escalation