from sqlalchemy.future import select
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from backend.database import get_db
from backend.models import Session as DbSession, User, Equipment, Message
from backend.services.ai_service import generate_response_stream, analyze_image, analyze_bolt_damage, analyze_equipment_damage, verify_loto_compliance
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
        image_analysis = await analyze_image(request.image_base64, request.message, context_data, context_text)
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

@router.post('/analyze/bolt')
async def analyze_bolt(request: BoltAnalysisRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    result = await analyze_bolt_damage(request.base64_image, request.bolt_spec)
    
    # Trigger Vision Analysis Completed email
    try:
        import json
        result_str = json.dumps(result, indent=2)
        email_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2>Vision Analysis Results Available</h2>
            <p>Hello {current_user.name},</p>
            <p>Your vision analysis request for bolt {request.bolt_spec} has completed successfully.</p>
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                {result_str}
            </div>
        </div>
        """
        from backend.services.email_service import send_notification_sync
        send_notification_sync(
            user_id=current_user.id,
            notification_type="Vision Analysis Completed",
            message=f"Vision analysis results available for bolt {request.bolt_spec}",
            to_email=current_user.email,
            subject="Vision Analysis Results Available",
            email_body=email_body
        )
        
        # Trigger Critical Risk Alert if condition is critical
        if result.get("bolt_condition") in ["CRITICAL", "HIGH", "REPLACE_IMMEDIATELY"]:
            from backend.services.email_service import notify_safety_escalation
            defects = ", ".join(result.get("detected_defects", [])) or "Corrosion or thread wear"
            recom = result.get("recommended_action") or "Replace bolt immediately"
            notify_safety_escalation(
                db=db,
                asset_name=f"Bolt ({request.bolt_spec})",
                asset_id=request.bolt_spec,
                location="Plant Floor",
                risk_level=result.get("bolt_condition", "HIGH"),
                issue_description=defects,
                root_cause=defects,
                recommended_action=recom,
                priority_level="Urgent",
                reporter_id=current_user.id
            )
    except Exception as e:
        logger.error(f"Failed to trigger notifications in bolt analysis: {e}")
        
    return result

@router.post('/analyze/equipment')
async def analyze_equipment(request: EquipmentAnalysisRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    result = await analyze_equipment_damage(request.base64_image, request.equipment_id, request.equipment_type)
    
    # Trigger Vision Analysis Completed email
    try:
        import json
        result_str = json.dumps(result, indent=2)
        email_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2>Vision Analysis Results Available</h2>
            <p>Hello {current_user.name},</p>
            <p>Your vision analysis request for equipment {request.equipment_id or 'Unknown'} has completed successfully.</p>
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                {result_str}
            </div>
        </div>
        """
        from backend.services.email_service import send_notification_sync
        send_notification_sync(
            user_id=current_user.id,
            notification_type="Vision Analysis Completed",
            message=f"Vision analysis results available for equipment {request.equipment_id}",
            to_email=current_user.email,
            subject="Vision Analysis Results Available",
            email_body=email_body
        )
        
        # Trigger Critical Risk Alert if condition is critical
        if result.get("overall_condition") in ["CRITICAL", "HIGH", "FAILURE"]:
            from backend.services.email_service import notify_safety_escalation
            issues = result.get("detected_issues", [])
            issue_desc = ", ".join([f"{i.get('issue_type')} at {i.get('location')}" for i in issues]) or "Structural anomaly"
            recom = result.get("recommended_action") or "Schedule immediate maintenance"
            notify_safety_escalation(
                db=db,
                asset_name=request.equipment_type or "Unknown Equipment",
                asset_id=request.equipment_id or "N/A",
                location="Plant Floor",
                risk_level=result.get("overall_condition", "HIGH"),
                issue_description=issue_desc,
                root_cause=issue_desc,
                recommended_action=recom,
                priority_level="Urgent",
                reporter_id=current_user.id
            )
    except Exception as e:
        logger.error(f"Failed to trigger notifications in equipment analysis: {e}")
        
    return result

@router.post('/analyze/loto')
async def analyze_loto(request: LotoComplianceRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    result = await verify_loto_compliance(request.base64_image)
    if result.get('verdict') == 'REJECTED':
        log_action(db, current_user.id, 'loto_rejected', 'safety', None, details={'reason': result.get('reason')})
        
    # Trigger Vision Analysis Completed email
    try:
        import json
        result_str = json.dumps(result, indent=2)
        email_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2>Vision Analysis Results Available</h2>
            <p>Hello {current_user.name},</p>
            <p>Your LOTO safety compliance vision analysis has completed successfully.</p>
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                {result_str}
            </div>
        </div>
        """
        from backend.services.email_service import send_notification_sync
        send_notification_sync(
            user_id=current_user.id,
            notification_type="Vision Analysis Completed",
            message="LOTO safety compliance vision analysis completed.",
            to_email=current_user.email,
            subject="Vision Analysis Results Available",
            email_body=email_body
        )
    except Exception as e:
        logger.error(f"Failed to trigger notification in LOTO analysis: {e}")
        
    return result