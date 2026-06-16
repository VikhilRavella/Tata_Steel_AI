from sqlalchemy.future import select
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from backend.database import get_db
from backend.models import Session as DbSession, User, Equipment, Message
from backend.services.ai_service import generate_response_stream
from backend.services.vision_service import analyze_equipment_image
import asyncio
from backend.services.document_service import search_documents
from backend.routers.auth import get_current_active_user
from backend.services.audit_service import log_action
from backend.services.memory_service import extract_and_update_memory
from backend.database import SessionLocal
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str
    image_base64: Optional[str] = None

class BoltAnalysisRequest(BaseModel):
    base64_image: str
    bolt_spec: str = 'M14'

class EquipmentAnalysisRequest(BaseModel):
    base64_image: str
    equipment_id: str = ''
    equipment_type: str = 'motor'

class LotoComplianceRequest(BaseModel):
    base64_image: str

@router.post('/chat')
async def chat_with_agent(request: ChatRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    context_data = {}
    engineer = db.query(User).filter(User.id == session.primary_engineer_id).first()
    equipment = db.query(Equipment).filter(Equipment.id == session.equipment_id).first()
    context_data = {'active_worker_name': engineer.name if engineer else 'Unknown', 'active_worker_role': engineer.role if engineer else 'Unknown', 'device_owner_name': engineer.name if engineer else 'Unknown', 'is_assisted_session': str(session.assisting_engineer_id is not None), 'equipment_name': equipment.equipment_name if equipment else 'Unknown', 'equipment_id': equipment.equipment_id_code if equipment else 'Unknown', 'block': equipment.block if equipment else 'Unknown', 'floor': equipment.floor if equipment else 'Unknown', 'safety_verified': str(session.safety_verified), 'loto_confirmed': str(session.loto_confirmed), 'current_phase': 'Phase 3' if session.loto_confirmed else 'Phase 1', 'cross_domain_flag': 'True' if engineer and engineer.role == 'junior' else 'False'}
    if not session.safety_verified and 'safety' not in request.message.lower():

        def block_stream():
            token_data = json.dumps({'token': '[ALERT] Safety verification incomplete. Please complete LOTO and PPE checks before proceeding.\n'})
            yield f'data: {token_data}\n\n'
            yield 'data: [DONE]\n\n'
        return StreamingResponse(block_stream(), media_type='text/event-stream')
    context_docs = search_documents(request.message, current_user.role, current_user.department)
    context_text = '\n'.join(context_docs)
    user_msg = Message(session_id=session.id, sender='user', content=request.message)
    db.add(user_msg)
    db.commit()
    if request.image_base64:
        vision_json_str = await asyncio.to_thread(analyze_equipment_image, request.image_base64, request.message)
        try:
            v_data = json.loads(vision_json_str)
            image_analysis = f"Equipment: {v_data.get('equipment_type', 'Unknown')}\n"
            image_analysis += f"Defects: {', '.join(v_data.get('detected_defects', []))}\n"
            image_analysis += f"Risk Level: {v_data.get('risk_level', 'Unknown')}\n"
            image_analysis += f"Root Cause: {v_data.get('root_cause', 'Unknown')}\n"
            image_analysis += f"Recommendations: {', '.join(v_data.get('recommendations', []))}\n"
            image_analysis += f"Safety Notes: {', '.join(v_data.get('safety_notes', []))}"
        except Exception:
            image_analysis = vision_json_str
            
        request.message = f'{request.message}\nImage Analysis: {image_analysis}'
        
        # Trigger Vision Analysis Completed email for chat image upload
        try:
            from backend.services.email_service import send_notification_sync
            email_body = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <h2>Vision Analysis Results Available</h2>
                <p>Hello {current_user.name},</p>
                <p>Your chat image vision analysis has completed successfully.</p>
                <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                    {image_analysis}
                </div>
            </div>
            """
            send_notification_sync(
                user_id=current_user.id,
                notification_type="Vision Analysis Completed",
                message="Your chat image vision analysis is complete.",
                to_email=current_user.email,
                subject="Vision Analysis Results Available",
                email_body=email_body
            )
        except Exception as ne:
            logger.error(f"Failed to trigger Vision Completed notification for chat image: {ne}")
            
    log_action(db, current_user.id, 'agent_chat_request', 'session', session.id)

    async def stream_with_memory():
        llm_response_text = ''
        async for chunk in generate_response_stream(request.message, context_data, context_text):
            if chunk.startswith('data: '):
                data_str = chunk[6:].strip()
                if data_str and data_str != '[DONE]':
                    try:
                        data = json.loads(data_str)
                        if 'token' in data:
                            llm_response_text += data['token']
                    except:
                        pass
            yield chunk
        if llm_response_text:
            bg_db = SessionLocal()
            try:
                await extract_and_update_memory(user_id=current_user.id, session_id=request.session_id, user_message=request.message, agent_message=llm_response_text, db=bg_db)
            except Exception as mem_err:
                logger.warning(f'Memory extraction failed: {mem_err}')
            finally:
                bg_db.close()
    return StreamingResponse(stream_with_memory(), media_type='text/event-stream')
