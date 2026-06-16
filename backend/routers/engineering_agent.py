from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from backend.database import get_db
import backend.models as models
from backend.routers.auth import get_current_active_user
from backend.services.ollama_service import generate_completion_stream, generate_completion_sync
from backend.services.requirement_discovery import process_requirements
from backend.services.memory_service import extract_and_update_memory, get_global_context
from backend.services.document_service import process_document, search_documents
from backend.services.vision_service import analyze_equipment_image
import asyncio
from backend.services.report_service import generate_report
from fastapi import UploadFile, File
from typing import Optional
import os

router = APIRouter()
@router.get('/history/list')
def list_engineering_sessions(db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    from backend.models import EngineeringSession, EngineeringMessage
    query = db.query(EngineeringSession)
    if current_user.role.upper() == 'ENGINEER':
        query = query.filter(EngineeringSession.user_id == current_user.id)
    elif current_user.role.upper() == 'SUPERVISOR':
        engineers = db.query(models.User).filter(models.User.supervisor_id == current_user.id).all()
        eng_ids = [e.id for e in engineers] + [current_user.id]
        query = query.filter(EngineeringSession.user_id.in_(eng_ids))
    sessions = query.order_by(EngineeringSession.created_at.desc()).all()
    result = []
    for s in sessions:
        msg_count = db.query(EngineeringMessage).filter(EngineeringMessage.session_id == s.session_id).count()
        last_msg = db.query(EngineeringMessage).filter(EngineeringMessage.session_id == s.session_id).order_by(EngineeringMessage.created_at.desc()).first()
        preview = last_msg.content[:50] + "..." if last_msg and last_msg.content else ""
        result.append({
            "session_id": s.session_id,
            "title": s.title or "Engineering Session",
            "status": s.status,
            "started_at": s.created_at.isoformat() if s.created_at else None,
            "message_count": msg_count,
            "last_message_preview": preview
        })
    return result

import uuid
from backend.models import EngineeringSession

@router.post('/session')
def create_engineering_session(db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    session_id = str(uuid.uuid4())
    eng_session = EngineeringSession(session_id=session_id, user_id=current_user.id, status='active')
    db.add(eng_session)
    db.commit()
    return {'status': 'success', 'session_id': session_id}



@router.delete("/session/{session_id}")
def delete_engineering_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    from sqlalchemy import select, delete
    session = db.query(models.EngineeringSession).filter(models.EngineeringSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if current_user.role.upper() == 'ENGINEER' and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role.upper() == 'SUPERVISOR' and session.user_id != current_user.id:
        user_of_session = db.query(models.User).filter(models.User.id == session.user_id).first()
        if not user_of_session or user_of_session.supervisor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    db.execute(delete(models.EngineeringMessage).where(models.EngineeringMessage.session_id == session_id))
    db.execute(delete(models.EngineeringMemory).where(models.EngineeringMemory.session_id == session_id))
    db.execute(delete(models.AgentFeedback).where(models.AgentFeedback.session_id == session_id))
    db.execute(delete(models.EscalationHistory).where(models.EscalationHistory.engineering_session_id == session_id))
    try:
        db.execute(delete(models.EngineeringFile).where(models.EngineeringFile.session_id == session_id))
    except Exception:
        pass
    try:
        db.execute(delete(models.EngineeringReport).where(models.EngineeringReport.session_id == session_id))
    except Exception:
        pass
    try:
        db.execute(delete(models.RequirementProfile).where(models.RequirementProfile.session_id == session_id))
    except Exception:
        pass
        
    db.delete(session)
    db.commit()
    return {"status": "success"}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: str = 'qwen2.5-coder:7b'
    image_base64: Optional[str] = None
    document_id: Optional[int] = None

def is_casual_message(message: str) -> bool:
    message = message.lower().strip()
    casual_words = ['hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon', 'how are you', 'thanks', 'thank you', 'ok', 'okay', 'bye', 'goodbye', 'yes', 'no', 'sure', 'great', 'nice', 'cool', 'got it', 'understood']
    return len(message.split()) <= 4 or any((message.startswith(w) for w in casual_words)) or message in casual_words

@router.get('/context/{session_id}')
def get_project_context(session_id: str, db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    memories = db.query(models.EngineeringMemory).filter(models.EngineeringMemory.session_id == session_id).order_by(models.EngineeringMemory.created_at.desc()).all()
    return {'status': 'success', 'memories': [{'type': m.memory_type, 'content': m.memory_value, 'score': 1.0} for m in memories]}

from fastapi import Form
@router.post('/upload')
async def upload_engineering_document(
    file: UploadFile = File(...),
    session_id: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    STORAGE_DIR = 'backend/storage/documents'
    os.makedirs(STORAGE_DIR, exist_ok=True)
    file_path = os.path.join(STORAGE_DIR, file.filename)
    with open(file_path, 'wb') as buffer:
        buffer.write(await file.read())
    try:
        is_verified = await process_document(file_path, file.filename, current_user, db)
        if not is_verified:
            raise HTTPException(status_code=403, detail="Document rejected by security scan.")
            
        if session_id:
            eng_file = models.EngineeringFile(
                session_id=session_id,
                user_id=current_user.id,
                file_name=file.filename,
                file_type="pdf" if file.filename.lower().endswith(".pdf") else "document",
                file_path=file_path
            )
            db.add(eng_file)
            db.commit()
            
        return {"status": "success", "message": "Document processed and stored for Engineering RAG."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/requirements/{session_id}')
def get_requirements(session_id: str, db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    profile = db.query(models.RequirementProfile).filter(models.RequirementProfile.session_id == session_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail='Requirement profile not found')
    return {'status': 'success', 'profile': {'project_name': profile.project_name, 'problem_statement': profile.problem_statement, 'business_goal': profile.business_goal, 'expected_outcome': profile.expected_outcome, 'tech_stack': profile.tech_stack, 'constraints': profile.constraints, 'timeline': profile.timeline, 'profile_status': profile.status}}

@router.get('/history/chat/{session_id}')
def get_engineering_chat_history(session_id: str, db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    session = db.query(models.EngineeringSession).filter(models.EngineeringSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if current_user.role.upper() == 'ENGINEER' and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    messages = db.query(models.EngineeringMessage).filter(models.EngineeringMessage.session_id == session_id).all()
    try:
        files = db.query(models.EngineeringFile).filter(models.EngineeringFile.session_id == session_id).all()
    except Exception:
        files = []
    try:
        reports = db.query(models.EngineeringReport).filter(models.EngineeringReport.session_id == session_id).all()
    except Exception:
        reports = []
    try:
        reqs = db.query(models.RequirementProfile).filter(models.RequirementProfile.session_id == session_id).all()
    except Exception:
        reqs = []
    try:
        memories = db.query(models.EngineeringMemory).filter(models.EngineeringMemory.session_id == session_id).all()
    except Exception:
        memories = []
        
    timeline = []
    for m in messages:
        timeline.append({
            "type": "message", 
            "sender": m.sender, 
            "content": m.content, 
            "message_type": m.message_type,
            "detected_language": m.detected_language,
            "timestamp": m.created_at.isoformat() if m.created_at else "1970-01-01T00:00:00"
        })
    for f in files:
        timeline.append({"type": "file", "file_name": f.file_name, "file_type": f.file_type, "file_path": f.file_path, "timestamp": f.uploaded_at.isoformat() if f.uploaded_at else "1970-01-01T00:00:00"})
    for r in reports:
        timeline.append({"type": "report", "title": r.title, "report_type": r.report_type, "content": r.report_content, "timestamp": r.created_at.isoformat() if r.created_at else "1970-01-01T00:00:00"})
    for req in reqs:
        timeline.append({"type": "requirement", "project_name": req.project_name, "status": req.status, "timestamp": req.created_at.isoformat() if req.created_at else "1970-01-01T00:00:00"})
    # Do not append memory to the user-facing chat timeline to prevent backend logs from rendering.
    # for mem in memories:
    #     timeline.append({"type": "memory", ...})
        
    # Check if this session was escalated from sandbox
    try:
        from backend.models import EscalationHistory
        escalation = db.query(EscalationHistory).filter(EscalationHistory.engineering_session_id == session_id).first()
        if escalation:
            timeline.append({
                "type": "system", 
                "sender": "system", 
                "content": "Escalated from Sandbox", 
                "timestamp": escalation.escalated_at.isoformat() if escalation.escalated_at else "1970-01-01T00:00:00"
            })
    except Exception:
        pass
        
    timeline.sort(key=lambda x: x["timestamp"])
    return timeline

@router.post('/chat')
async def engineering_chat(request: ChatRequest, background_tasks: BackgroundTasks, db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    import time
    start_time = time.time()
    
    # 5. Skip Gemini Normalization if Intent == PDF
    temp_has_image = bool(request.image_base64)
    temp_has_doc = bool(request.document_id)
    
    # Skip Gemini Normalization if Intent == PDF (defined by having a document attached and no image)
    is_pdf_intent = temp_has_doc and not temp_has_image
            
    if not is_pdf_intent:
        from backend.services.text_normalization_service import normalize_user_text
        request.message = await normalize_user_text(request.message)
    
    session = db.query(models.EngineeringSession).filter(models.EngineeringSession.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Engineering session not found")

    user_msg = models.EngineeringMessage(session_id=request.session_id, sender="user", content=request.message)
    db.add(user_msg)
    db.commit()

    msg_lower = request.message.lower().strip()
    has_image = bool(request.image_base64)
    has_doc = bool(request.document_id)
    
    # ---------------------------------------------------------
    # 1. INTENT CLASSIFICATION
    # ---------------------------------------------------------
    intent = "UNKNOWN_INTENT"
    selected_module = "GENERAL_CHAT"
    
    casual_words = ['hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon', 'how are you', 'thanks', 'thank you', 'ok', 'okay', 'bye', 'goodbye', 'yes', 'no', 'sure', 'great', 'nice', 'cool', 'got it', 'understood', 'who am i', 'help', 'what can you do', 'show profile']
    vision_keywords = ['image', 'photo', 'picture', 'snapshot', 'inspect', 'defect', 'fault', 'damage', 'visual', 'crack', 'corrosion', 'wear', 'rust', 'misalignment', 'leak', 'thermal']
    pdf_keywords = ['hazards', 'warnings', 'ppe', 'procedure', 'maintenance', 'manual', 'equipment', 'parts', 'inspection', 'safety', 'loto', 'lockout', 'tagout', 'document', 'pdf', 'sop', 'guide', 'datasheet', 'specification', 'report', 'drawing']
    inventory_keywords = ['inventory', 'stock', 'spare', 'part', 'bearing', 'filter', 'gasket', 'seal', 'valve', 'motor', 'pump', 'gear', 'coupling', 'belt', 'chain', 'sensor', 'warehouse', 'bin', 'rack', 'supplier', 'vendor', 'material', 'bom']
    vision_inventory_keywords = ['suggest spare', 'replacement part', 'required part', 'replace', 'availability', 'create request', 'spare recommendation', 'spare part']
    wo_keywords = ['work order', 'task', 'job card', 'schedule', 'service request', 'work request', 'planned maintenance', 'corrective maintenance', 'preventive', 'breakdown', 'pending work']
    supervisor_keywords = ['supervisor', 'manager', 'lead', 'reporting manager', 'approval', 'escalation', 'who is my']
    rca_keywords = ['root cause', 'rca', 'why did this fail', 'investigate', 'failure analysis', 'diagnose', 'troubleshoot']
    report_keywords = ['report', 'summary report', 'audit report', 'incident report', 'weekly report', 'daily report']
    safety_keywords = ['safety', 'hazard', 'risk', 'incident', 'near miss', 'unsafe', 'permit', 'hot work', 'confined space', 'electrical safety', 'leak', 'crack']
    memory_keywords = ['remember', 'memory', 'previous chat', 'last discussion', 'earlier conversation', 'history', 'recall', 'stored', 'project goal', 'preference']
    profile_keywords = ['my profile', 'my role', 'my department']

    if has_image:
        if any(k in msg_lower for k in vision_inventory_keywords):
            intent = "VISION_INVENTORY"
        else:
            intent = "VISION"
    elif has_doc and any(k in msg_lower for k in pdf_keywords):
        intent = "PDF"
    elif any(k in msg_lower for k in supervisor_keywords):
        intent = "SUPERVISOR"
    elif any(k in msg_lower for k in report_keywords):
        intent = "REPORT"
    elif any(k in msg_lower for k in rca_keywords):
        intent = "RCA"
    elif any(k in msg_lower for k in safety_keywords):
        intent = "SAFETY"
    elif any(k in msg_lower for k in wo_keywords):
        intent = "WORK_ORDER"
    elif any(k in msg_lower for k in inventory_keywords):
        intent = "INVENTORY"
    elif any(k in msg_lower for k in profile_keywords):
        intent = "PROFILE"
    elif any(k in msg_lower for k in memory_keywords):
        intent = "MEMORY"
    elif any(k in msg_lower for k in pdf_keywords):
        intent = "PDF" if has_doc else "GENERAL_CHAT"
    elif len(msg_lower.split()) <= 4 or any(msg_lower.startswith(w) for w in casual_words) or msg_lower in casual_words:
        intent = "GENERAL_CHAT"
    else:
        intent = "GENERAL_CHAT" # Fallback

    # ---------------------------------------------------------
    # 2. MODEL ROUTING
    # ---------------------------------------------------------
    if intent in ["PDF"]:
        selected_model = "mistral:latest"
    elif intent in ["VISION", "VISION_INVENTORY"]:
        selected_model = "qwen2.5vl:latest"
    else:
        selected_model = "qwen2.5-coder:7b"

    # Load Conversational History
    try:
        recent_msgs = db.query(models.EngineeringMessage).filter(models.EngineeringMessage.session_id == request.session_id).order_by(models.EngineeringMessage.created_at.desc()).limit(6).all()
        recent_msgs.reverse()
        chat_history_str = "\n".join([f"{m.sender}: {m.content}" for m in recent_msgs if m.sender != "system"])
    except Exception:
        chat_history_str = "No recent history."

    # ---------------------------------------------------------
    # 3. MODULE LOADING (CONTEXT ISOLATION)
    # ---------------------------------------------------------
    resources_loaded = []
    
    # --- ENHANCED AGENT CONTEXT ---
    enhanced_context = f"--- LOGGED-IN ENGINEER PROFILE ---\nName: {current_user.name}\nRole: {current_user.role}\nDepartment: {current_user.department}\nEmail: {current_user.email}\n\n"
    
    # Assigned Assets
    eqs = []
    if current_user.supervisor_id:
        supervisor = db.query(models.User).filter(models.User.id == current_user.supervisor_id).first()
        if supervisor:
            eqs = db.query(models.EquipmentMaster).filter(
                (models.EquipmentMaster.assigned_supervisor == supervisor.employee_id) |
                (models.EquipmentMaster.assigned_supervisor == str(supervisor.id))
            ).limit(5).all()
    enhanced_context += "Assigned Assets:\n" + ("\n".join([f"- {e.equipment_name} ({e.status})" for e in eqs]) if eqs else "None") + "\n\n"
    
    # Active Work Orders
    wos = db.query(models.WorkOrder).filter(models.WorkOrder.assigned_to == current_user.id, models.WorkOrder.status != "Completed").limit(3).all()
    enhanced_context += "Active Work Orders:\n" + ("\n".join([f"- WO #{w.id}: {w.title} ({w.priority})" for w in wos]) if wos else "None") + "\n\n"
    
    # Recent Risk Alerts
    try:
        alerts = db.query(models.NotificationLog).filter(models.NotificationLog.user_id == current_user.id, models.NotificationLog.notification_type == "Critical Risk Alert").order_by(models.NotificationLog.timestamp.desc()).limit(3).all()
        enhanced_context += "Recent Risk Alerts:\n" + ("\n".join([f"- {a.timestamp.strftime('%Y-%m-%d %H:%M')}: {a.message}" for a in alerts]) if alerts else "None") + "\n\n"
    except Exception:
        enhanced_context += "Recent Risk Alerts: None\n\n"
        
    # Recent Maintenance Outcomes
    try:
        outcomes = db.query(models.MaintenanceOutcome).filter(models.MaintenanceOutcome.engineer_id == current_user.id).order_by(models.MaintenanceOutcome.timestamp.desc()).limit(3).all()
        enhanced_context += "Recent Maintenance Outcomes:\n" + ("\n".join([f"- Asset {o.asset_id}: {o.outcome_status} (Risk: {o.risk_level})" for o in outcomes]) if outcomes else "None") + "\n\n"
    except Exception:
        enhanced_context += "Recent Maintenance Outcomes: None\n\n"

    # Recent Requests (Inventory/Parts requests)
    try:
        reqs = db.query(models.InventoryTransaction).filter(
            models.InventoryTransaction.requested_by == current_user.id,
            models.InventoryTransaction.transaction_type.in_(['PENDING', 'APPROVED', 'REJECTED'])
        ).order_by(models.InventoryTransaction.timestamp.desc()).limit(5).all()
        enhanced_context += "Recent Requests:\n" + ("\n".join([f"- Request for {r.quantity}x {r.part_name} ({r.transaction_type})" for r in reqs]) if reqs else "None") + "\n\n"
    except Exception:
        enhanced_context += "Recent Requests: None\n\n"

    # Maintenance History
    try:
        mhs = db.query(models.MaintenanceHistory).filter(models.MaintenanceHistory.performed_by == current_user.id).order_by(models.MaintenanceHistory.maintenance_date.desc()).limit(5).all()
        enhanced_context += "Maintenance History:\n" + ("\n".join([f"- {m.maintenance_date.strftime('%Y-%m-%d')}: {m.description} ({m.status})" for m in mhs]) if mhs else "None") + "\n\n"
    except Exception:
        enhanced_context += "Maintenance History: None\n\n"

    context_text = enhanced_context
    rag_length = 0

    if intent == "VISION":
        selected_module = "VISION MODULE"
        resources_loaded.append("Vision Analysis Only")
        try:
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
                
            context_text += f"\nVISION ANALYSIS:\n{image_analysis}\n\nWARNING: If there are safety risks (leaks, cracks, exposed wiring), emphasize them immediately.\nDO NOT automatically create inventory requests for purely visual analysis.\n"
            
            # Trigger Vision Analysis Completed email
            try:
                from backend.services.email_service import send_notification_sync, notify_safety_escalation
                email_body = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <h2>Vision Analysis Results Available</h2>
                    <p>Hello {current_user.name},</p>
                    <p>Your engineering agent image analysis has completed successfully.</p>
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                        {image_analysis}
                    </div>
                </div>
                """
                send_notification_sync(
                    user_id=current_user.id,
                    notification_type="Vision Analysis Completed",
                    message="Your agent image vision analysis is complete.",
                    to_email=current_user.email,
                    subject="Vision Analysis Results Available",
                    email_body=email_body
                )
                
                # Auto-evaluate Risk Level
                analysis_upper = image_analysis.upper()
                auto_risk = None
                if "CRITICAL" in analysis_upper and ("RISK" in analysis_upper or "DEFECT" in analysis_upper or "OVERHEATING" in analysis_upper or "CRACK" in analysis_upper):
                    auto_risk = "CRITICAL"
                elif "HIGH" in analysis_upper and ("RISK" in analysis_upper or "DEFECT" in analysis_upper or "OVERHEATING" in analysis_upper):
                    auto_risk = "HIGH"
                
                if auto_risk:
                    temp_db = SessionLocal()
                    try:
                        notify_safety_escalation(
                            db=temp_db,
                            asset_name="Detected Equipment (Vision)",
                            asset_id="Unknown",
                            location="Plant Floor",
                            risk_level=auto_risk,
                            issue_description="Automated Vision Detection found high/critical defect.",
                            root_cause="Visual Defect",
                            recommended_action="Immediate manual inspection required.",
                            priority_level="Urgent",
                            reporter_id=current_user.id
                        )
                        context_text += f"\n[SYSTEM ACTION: {auto_risk} RISK ESCALATION TRIGGERED AUTOMATICALLY]\n"
                    finally:
                        temp_db.close()
                        
            except Exception as ne:
                pass
        except Exception as e:
            return StreamingResponse((f"data: {json.dumps({'token': 'Image analysis unavailable.'})}\n\ndata: [DONE]\n\n" for _ in range(1)), media_type='text/event-stream')

    elif intent == "VISION_INVENTORY":
        selected_module = "VISION + INVENTORY MODULE"
        resources_loaded.append("Vision Analysis")
        resources_loaded.append("InventoryMaster")
        try:
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
                
            context_text += f"\nVISION ANALYSIS RESULTS:\n{image_analysis}\n"
            
            # Trigger Vision Analysis Completed email
            try:
                from backend.services.email_service import send_notification_sync, notify_safety_escalation
                email_body = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                    <h2>Vision Analysis Results Available</h2>
                    <p>Hello {current_user.name},</p>
                    <p>Your engineering agent vision and inventory analysis has completed successfully.</p>
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin-top: 15px; white-space: pre-wrap;">
                        {image_analysis}
                    </div>
                </div>
                """
                send_notification_sync(
                    user_id=current_user.id,
                    notification_type="Vision Analysis Completed",
                    message="Your agent vision and inventory image analysis is complete.",
                    to_email=current_user.email,
                    subject="Vision Analysis Results Available",
                    email_body=email_body
                )
                
                # Auto-evaluate Risk Level
                analysis_upper = image_analysis.upper()
                auto_risk = None
                if "CRITICAL" in analysis_upper and ("RISK" in analysis_upper or "DEFECT" in analysis_upper or "OVERHEATING" in analysis_upper or "CRACK" in analysis_upper):
                    auto_risk = "CRITICAL"
                elif "HIGH" in analysis_upper and ("RISK" in analysis_upper or "DEFECT" in analysis_upper or "OVERHEATING" in analysis_upper):
                    auto_risk = "HIGH"
                
                if auto_risk:
                    temp_db = SessionLocal()
                    try:
                        notify_safety_escalation(
                            db=temp_db,
                            asset_name="Detected Equipment (Vision+Inventory)",
                            asset_id="Unknown",
                            location="Plant Floor",
                            risk_level=auto_risk,
                            issue_description="Automated Vision Detection found high/critical defect.",
                            root_cause="Visual Defect",
                            recommended_action="Immediate manual inspection required.",
                            priority_level="Urgent",
                            reporter_id=current_user.id
                        )
                        context_text += f"\n[SYSTEM ACTION: {auto_risk} RISK ESCALATION TRIGGERED AUTOMATICALLY]\n"
                    finally:
                        temp_db.close()
                        
            except Exception as ne:
                pass
            
            # Cross-reference with Inventory
            parts = db.query(models.InventoryMaster).all()
            found_vision_parts = []
            analysis_lower = image_analysis.lower()
            
            for p in parts:
                p_name = p.part_name.lower() if p.part_name else ""
                p_num = p.part_number.lower() if p.part_number else ""
                if (p_name and p_name in analysis_lower) or (p_num and p_num in analysis_lower):
                    found_vision_parts.append(p)
            
            if found_vision_parts:
                context_text += "\n--- INVENTORY AVAILABILITY FOR DETECTED COMPONENTS ---\n"
                for p in found_vision_parts:
                    context_text += f"Part: {p.part_name} ({p.part_number}), Stock: {p.stock_qty}, Location: WH-{p.warehouse}\n"
                context_text += "\nAGENT INSTRUCTION: Explicitly ask the engineer if they would like to create a spare part request for these components. Do NOT use the [INVENTORY_REQUEST_TRIGGER] yet, wait for their 'YES' confirmation.\n"
            else:
                context_text += "\n--- INVENTORY AVAILABILITY ---\nRequired replacement part not found in inventory. Supervisor escalation recommended.\n"
                
        except Exception as e:
            context_text += "\nVision analysis failed or inventory lookup unavailable.\n"

    elif intent == "PDF":
        selected_module = "PDF MODULE"
        resources_loaded.append("Selected Document")
        resources_loaded.append("RAG Search")

    elif intent == "INVENTORY":
        selected_module = "INVENTORY MODULE"
        resources_loaded.append("InventoryMaster")
        resources_loaded.append("InventoryTransaction")
        try:
            parts = db.query(models.InventoryMaster).all()
            found_parts = []
            for p in parts:
                p_name = p.part_name.lower() if p.part_name else ""
                p_num = p.part_number.lower() if p.part_number else ""
                matched = False
                if p_name and p_name in msg_lower: matched = True
                if p_num and p_num in msg_lower: matched = True
                if not matched:
                    for k in ['bearing', 'pump', 'filter', 'seal', 'bolt', 'valve']:
                        if k in msg_lower and k in p_name:
                            matched = True
                            break
                if matched:
                    found_parts.append(f"Part: {p.part_name} ({p.part_number})\nStock: {p.stock_qty}\nLocation: Whs {p.warehouse}, Rack {p.rack}, Bin {p.bin}\nSupplier: {p.supplier}")
            if found_parts:
                context_text += "\nINVENTORY AVAILABILITY:\n" + "\n\n".join(found_parts) + "\n"
        except Exception:
            return StreamingResponse((f"data: {json.dumps({'token': 'Inventory lookup unavailable.'})}\n\ndata: [DONE]\n\n" for _ in range(1)), media_type='text/event-stream')

    elif intent == "WORK_ORDER":
        selected_module = "WORK ORDER MODULE"
        resources_loaded.append("Work Orders")
        resources_loaded.append("Equipment")
        my_wos = db.query(models.WorkOrder).filter(models.WorkOrder.assigned_to == current_user.id, models.WorkOrder.status.in_(['OPEN', 'PENDING', 'IN_PROGRESS', 'Open', 'pending'])).all()
        if my_wos:
            context_text += "ACTIVE WORK ORDERS:\n"
            for wo in my_wos:
                context_text += f"- [WO-{wo.id}] {wo.title} (Equipment: {wo.equipment_id}, Status: {wo.status}, Priority: {wo.priority})\n"
        recent_wos = db.query(models.WorkOrder).order_by(models.WorkOrder.created_at.desc()).limit(3).all()
        if recent_wos:
            context_text += "\nRECENT WORK ORDERS:\n"
            for wo in recent_wos:
                context_text += f"- [WO-{wo.id}] {wo.title}\n"
        my_eqs = db.query(models.EquipmentMaster).limit(5).all()
        if my_eqs:
            context_text += "\nASSIGNED EQUIPMENT:\n"
            for eq in my_eqs:
                context_text += f"- [{eq.equipment_id}] {eq.equipment_name} (Status: {eq.status})\n"

    elif intent == "PROFILE":
        selected_module = "PROFILE MODULE"
        resources_loaded.append("User Profile")
        context_text += f"LOGGED-IN ENGINEER PROFILE:\nName: {current_user.name}\nDepartment: {current_user.department}\nRole: {current_user.role}\n\n"

    elif intent == "SUPERVISOR":
        selected_module = "PROFILE MODULE"
        resources_loaded.append("User Profile")
        resources_loaded.append("Supervisor")
        context_text += f"LOGGED-IN ENGINEER PROFILE:\nName: {current_user.name}\nDepartment: {current_user.department}\nRole: {current_user.role}\n\n"
        supervisor = db.query(models.User).filter(models.User.id == current_user.supervisor_id).first()
        if supervisor:
            context_text += f"ASSIGNED SUPERVISOR:\nName: {supervisor.name}\nEmail: {supervisor.email or 'N/A'}\nDepartment: {supervisor.department or 'N/A'}\n\n"

    elif intent == "SAFETY":
        selected_module = "SAFETY MODULE"
        resources_loaded.append("Safety SOP")
        if has_doc:
            resources_loaded.append("PDF RAG")

    elif intent == "RCA":
        selected_module = "RCA MODULE"
        resources_loaded.append("Equipment History")
        resources_loaded.append("Failure Data")
        resources_loaded.append("Maintenance Records")
        eqs = db.query(models.EquipmentMaster).all()
        for eq in eqs:
            if eq.equipment_name.lower() in msg_lower or eq.equipment_id.lower() in msg_lower:
                context_text += f"\nEQUIPMENT MENTIONED: {eq.equipment_id} - {eq.equipment_name}\n"
                maint_hist = db.query(models.MaintenanceHistory).filter(models.MaintenanceHistory.equipment_id == eq.equipment_id).order_by(models.MaintenanceHistory.maintenance_date.desc()).limit(10).all()
                if maint_hist:
                    context_text += "RECENT MAINTENANCE HISTORY:\n"
                    for mh in maint_hist:
                        context_text += f"- Status: {mh.status} - {mh.description}\n"
                break

    elif intent == "REPORT":
        selected_module = "REPORT MODULE"
        resources_loaded.append("Relevant Module Context Only")
        context_text += f"LOGGED-IN ENGINEER PROFILE:\nName: {current_user.name}\nRole: {current_user.role}\n"
        if has_doc:
            resources_loaded.append("PDF Context")

    elif intent == "MEMORY":
        selected_module = "MEMORY MODULE"
        resources_loaded.append("Memory Service")
        global_context = get_global_context(request.session_id, db)
        context_text += f"{global_context}\n"
        context_text += "Use the Shared Memory to seamlessly continue previous discussions.\n"

    else:
        # GENERAL_CHAT
        selected_module = "GENERAL_CHAT"
        resources_loaded.append("User Profile")
        context_text += f"LOGGED-IN ENGINEER PROFILE:\nName: {current_user.name}\nRole: {current_user.role}\n"

    user_id = current_user.id

    async def intercepted_stream():
        nonlocal context_text
        full_agent_response = ""
        pdf_pages = "N/A"
        retrieved_chunks_count = 0
        compressed_context_length = 0
        selected_mode = "N/A"
        
        try:
            # Check if PDF RAG context needs to be built
            if has_doc and intent in ["PDF", "SAFETY", "REPORT"]:
                import os
                import fitz
                from backend.services.document_service import get_all_document_chunks, search_documents_v3, parse_page_number
                from backend.services.rag_service import compress_qa_context, generate_hierarchical_summary
                
                # Stage 1: Reading document...
                yield f"data: {json.dumps({'status': '📄 Reading document...'})}\n\n"
                
                doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.id == request.document_id).first()
                if doc and os.path.exists(doc.file_path):
                    if doc.file_path.endswith('.pdf'):
                        try:
                            pdf_doc = fitz.open(doc.file_path)
                            pdf_pages = len(pdf_doc)
                            pdf_doc.close()
                        except Exception as e:
                            print(f"Error reading PDF page count: {e}")
                    
                    # Stage 2: Retrieving relevant sections...
                    yield f"data: {json.dumps({'status': '📚 Retrieving relevant sections...'})}\n\n"
                    
                    query_lower = request.message.lower()
                    
                    # Determine selected_mode from 7 V4 modes:
                    is_summary_query = any(k in query_lower for k in ["summarize", "summary", "overview", "executive summary"])
                    is_page_search = parse_page_number(request.message) is not None or any(k in query_lower for k in ["page ", "p.", "pg", "section", "heading", "cite", "citation"])
                    is_safety_search = any(k in query_lower for k in ["safety", "hazard", "warning", "caution", "ppe", "lockout", "tagout", "loto", "risk", "incident"])
                    is_maintenance_search = any(k in query_lower for k in ["maintenance", "procedure", "spare part", "equipment", "inspection", "sop", "guide", "datasheet", "repair", "install", "troubleshoot"])
                    is_table_search = any(k in query_lower for k in ["table", "chart", "graph", "figure", "data sheet"])
                    is_insights_search = any(k in query_lower for k in ["insight", "analysis", "deep dive", "recommendations", "patterns"])
                    
                    if is_summary_query:
                        selected_mode = "DOCUMENT_SUMMARY"
                    elif is_page_search:
                        selected_mode = "PAGE_SEARCH"
                    elif is_safety_search:
                        selected_mode = "SAFETY_SEARCH"
                    elif is_maintenance_search:
                        selected_mode = "MAINTENANCE_SEARCH"
                    elif is_table_search:
                        selected_mode = "TABLE_SEARCH"
                    elif is_insights_search:
                        selected_mode = "DOCUMENT_INSIGHTS"
                    else:
                        selected_mode = "QUESTION_ANSWERING"
                        
                    # Rule override for pages > 100
                    if isinstance(pdf_pages, int) and pdf_pages > 100 and selected_mode not in ["PAGE_SEARCH", "SAFETY_SEARCH", "MAINTENANCE_SEARCH", "TABLE_SEARCH"]:
                        selected_mode = "DOCUMENT_SUMMARY"
                        
                    retrieved_pages_list = []
                    
                    if selected_mode == "DOCUMENT_SUMMARY":
                        from backend.services.document_service import get_all_document_chunks_with_metadata
                        raw_chunks = await get_all_document_chunks_with_metadata(request.document_id, file_path=doc.file_path)
                        # Fallback to direct reading if Chroma has no chunks
                        if not raw_chunks:
                            from backend.services.document_service import PYMUPDF_AVAILABLE
                            if doc.file_path.endswith('.pdf') and PYMUPDF_AVAILABLE:
                                try:
                                    pdf_doc = fitz.open(doc.file_path)
                                    for page_idx, page in enumerate(pdf_doc):
                                        page_text = page.get_text()
                                        if page_text.strip():
                                            raw_chunks.append({
                                                "text": page_text,
                                                "page_number": page_idx + 1,
                                                "section_name": "General Section",
                                                "heading": "Technical Content"
                                            })
                                    pdf_doc.close()
                                except:
                                    pass
                        retrieved_chunks_count = len(raw_chunks)
                        retrieved_pages_list = sorted(list(set([c.get('page_number', 1) for c in raw_chunks if isinstance(c, dict) and 'page_number' in c])))
                        
                        # Stage 3: Compressing context...
                        yield f"data: {json.dumps({'status': '🧠 Compressing context...'})}\n\n"
                        compressed_rag = await generate_hierarchical_summary(raw_chunks)
                        
                    elif selected_mode == "PAGE_SEARCH":
                        # Stage 2.5: Searching pages...
                        yield f"data: {json.dumps({'status': 'Searching Document Knowledge Base...'})}\n\n"
                        
                        chunks_with_metadata = await search_documents_v3(
                            request.message, 
                            current_user.role, 
                            current_user.department, 
                            top_k=4, 
                            company_doc_id=request.document_id,
                            file_path=doc.file_path
                        )
                        retrieved_chunks_count = len(chunks_with_metadata)
                        retrieved_pages_list = list(set([c['page_number'] for c in chunks_with_metadata if 'page_number' in c]))
                        
                        # Stage 3: Compressing context...
                        yield f"data: {json.dumps({'status': 'Retrieving Relevant Chunks...'})}\n\n"
                        
                        formatted_chunks = []
                        for c in chunks_with_metadata:
                            formatted_chunks.append(f"Source: Page {c.get('page_number')}\nSection: {c.get('section_name')}\nHeading: {c.get('heading')}\nContent: {c.get('text')}")
                        compressed_rag = "\n\n".join(formatted_chunks)
                        
                    else:
                        # SAFETY_SEARCH, MAINTENANCE_SEARCH, TABLE_SEARCH, DOCUMENT_INSIGHTS, QUESTION_ANSWERING
                        query_for_search = request.message
                        if selected_mode == "SAFETY_SEARCH":
                            query_for_search = request.message + " PPE, safety precaution, hazard warning, LOTO lockout tagout, safety guide, safety instructions, PPE requirement, warning sign, caution, lock-out tag-out procedure"
                        elif selected_mode == "MAINTENANCE_SEARCH":
                            query_for_search = request.message + " maintenance procedure, spare parts, equipment inspection, troubleshooting, repair, calibration, tool list, spare part list, installation, corrective maintenance, preventive maintenance, repair instructions"
                        elif selected_mode == "TABLE_SEARCH":
                            query_for_search = request.message + " table, chart, data sheet, technical specification, parameter, dimension, values"
                        elif selected_mode == "DOCUMENT_INSIGHTS":
                            query_for_search = request.message + " conclusion, recommendation, analysis, critical finding, overall condition"
                            
                        chunks_with_metadata = await search_documents_v3(
                            query_for_search, 
                            current_user.role, 
                            current_user.department, 
                            top_k=4, 
                            company_doc_id=request.document_id,
                            file_path=doc.file_path
                        )
                        retrieved_chunks_count = len(chunks_with_metadata)
                        retrieved_pages_list = list(set([c['page_number'] for c in chunks_with_metadata if 'page_number' in c]))
                        
                        # Stage 3: Compressing context...
                        yield f"data: {json.dumps({'status': 'Retrieving Relevant Chunks...'})}\n\n"
                        
                        formatted_chunks = []
                        for c in chunks_with_metadata:
                            formatted_chunks.append(f"Source: Page {c.get('page_number')}\nSection: {c.get('section_name')}\nHeading: {c.get('heading')}\nContent: {c.get('text')}")
                            
                        pages_val = pdf_pages if isinstance(pdf_pages, int) else 1
                        if pages_val <= 20:
                            compressed_rag = "\n\n".join(formatted_chunks)
                        else:
                            compressed_rag = await compress_qa_context(formatted_chunks, request.message)
                    
                    # Stream Failure Protection: Enforce strict 5000 character limit
                    compressed_rag = compressed_rag[:5000]
                    compressed_context_length = len(compressed_rag)
                    
                    if intent == "PDF":
                        context_text += f"\n\n--- VERIFIED COMPANY DOCUMENT CONTEXT ({doc.filename}) ---\n" + compressed_rag
                    elif intent == "SAFETY":
                        context_text += f"\n\n--- SAFETY SOP FROM {doc.filename} ---\n" + compressed_rag
                    elif intent == "REPORT":
                        context_text += f"\n--- REPORT CONTEXT FROM {doc.filename} ---\n" + compressed_rag
                    
                    try:
                        audit_log = models.AuditLog(
                            user_id=current_user.id, action="use_company_document", entity_type="CompanyDocument", entity_id=doc.id,
                            details=json.dumps({"filename": doc.filename, "session_id": request.session_id, "message": "Document used as context for AI via RAG"})
                        )
                        db.add(audit_log)
                        db.commit()
                    except Exception as ae:
                        print(f"Warning: Audit log error: {ae}")
                else:
                    yield f"data: {json.dumps({'status': '⚠️ Document not found'})}\n\n"
                    
            # Performance Logging
            print(f"--- PDF V4 PERFORMANCE LOG ---")
            print(f"Total Pages: {pdf_pages}")
            print(f"Selected Mode: {selected_mode}")
            print(f"Retrieved Chunks: {retrieved_chunks_count}")
            print(f"Context Length: {compressed_context_length}/5000")
            print(f"------------------------------")
            
            # Stage 4: Generating response...
            yield f"data: {json.dumps({'status': 'Generating Engineering Response...'})}\n\n"
        except Exception as ex:
            import traceback
            trace_str = traceback.format_exc()
            err_msg = f"RAG context assembly failed: {str(ex)}\n\n{trace_str}"
            yield f"data: {json.dumps({'token': err_msg})}\n\ndata: [DONE]\n\n"
            return

        # Build Prompt
        if intent == "VISION":
            system_prompt = f"""YOU ARE A VISION ANALYSIS ASSISTANT.
Analyze the image and respond directly. Do not generate any system triggers like [WORK_ORDER_TRIGGER] or [REPORT_TRIGGER].

RULES FOR VISION ANALYSIS:
1. Do not invent placeholder values (e.g. Asset #12345, Demo Asset). If data does not exist, state "Asset information not available."
2. If uncertain, use low-confidence phrasing (e.g., "Possible Crack Detected", "Confidence: Medium") instead of absolute statements like "Crack Detected".
3. Use the following professional format if applicable:
   Asset Information
   Risk Assessment
   Detected Issues
   Recommended Actions
   Safety Considerations
   Next Steps

--- VISION ANALYSIS ---
{context_text}

USER QUERY:
{request.message}"""
        else:
            system_prompt = f"""YOU ARE THE DYNAMIC ENGINEERING RESPONSE COMPOSER.
Your goal is to answer the user's request using the available context.
You have detected the user's primary intent as: {intent}.

--- RECENT CHAT HISTORY ---
{chat_history_str}

RULES FOR RESPONSE COMPOSITION:
1. DO NOT simply output raw context. Interpret it.
2. Generate natural language responses. Act as an expert Industrial Engineer, Maintenance Specialist, Safety Specialist, or Technical Documentation Analyst depending on the query.
3. Provide executive summaries, engineering insights, maintenance recommendations, safety observations, and operational guidance naturally.
4. MUST NOT HALLUCINATE. Do not invent facts about inventory or work orders. If you cannot find requested database records, just say so politely.
5. NEVER use placeholders or fake data. Do not use: #12345, #26, #9, Asset #12345, Location Not Specified, Unknown Asset, Sample Asset, Demo Asset.
6. Use Real Data: If actual asset information exists, display: Asset Name, Asset ID, Plant, Department, Engineer, Work Order ID, Inventory Request ID.
7. If Data Does Not Exist: Display "Asset information not available.", "Location information not available.", "Work order will be generated after approval." Do not generate fake IDs.
8. Report Formatting: Avoid "Report #9", "Report #10", "Work Order #26" unless the value actually exists in the database.
9. RAG Response Rule: If information is not found in the uploaded PDF, return: "Information not found in the uploaded document." You may optionally add: "Based on general engineering practices..." but clearly separate PDF knowledge from generated recommendations.
10. Root Cause Analysis: If confidence is low, display "Possible Causes" instead of "Confirmed Root Cause".
11. Response Format: Structure your final response using these headings:
    Asset Information
    Risk Assessment
    Detected Issues
    Recommended Actions
    Safety Considerations
    Next Steps

EXAMPLES OF DYNAMIC STRUCTURE:
- If user asks "What component is visible?": Provide Component, Visible Defects, Confidence.
- If user asks "Create a work order": Provide Title, Description, Priority, Tasks. AND append [WORK_ORDER_TRIGGER:{{"title": "...", "description": "...", "priority": "High"}}] at the end.
- If user asks "Generate report": Provide Findings, Conclusions, Recommendations. AND append [REPORT_TRIGGER:{{"title": "...", "report_type": "Root Cause Analysis"}}] at the end.
- If user asks to request a part: Provide details and append [INVENTORY_REQUEST_TRIGGER:{{"part_name": "...", "quantity": 1, "equipment_id": "..."}}]
- If user asks to approve issue: Append [INVENTORY_APPROVAL_TRIGGER:{{"transaction_id": "..."}}]
- If user asks to return part: Append [INVENTORY_RETURN_TRIGGER:{{"part_name": "...", "quantity": 1}}]
- If you detect a CRITICAL or HIGH safety/maintenance risk, append [SAFETY_ALERT_TRIGGER:{{"asset_name":"...", "asset_id":"...", "location":"...", "risk_level":"CRITICAL", "issue_description":"...", "root_cause":"...", "recommended_action":"...", "priority_level":"Urgent"}}]

--- AVAILABLE CONTEXT ---
{context_text}

USER QUERY:
{request.message}
"""
        prompt_length = len(system_prompt)

        try:
            async for chunk in generate_completion_stream(system_prompt, model=selected_model):
                if '[DONE]' in chunk:
                    break
                try:
                    if chunk.startswith('data: '):
                        data = json.loads(chunk[6:])
                        if 'token' in data:
                            full_agent_response += data['token']
                except:
                    pass
                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'token': f'Model generation failed: {str(e)}'})}\n\ndata: [DONE]\n\n"
            return

        # TRIGGERS
        from backend.database import SessionLocal
        bg_db = SessionLocal()
        final_content = full_agent_response
        system_additions = ""
        created_wo_id = None
        created_rep_id = None
        try:
            import re
            match_wo = re.search(r'\[WORK_ORDER_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_wo:
                try:
                    wo_data = json.loads(match_wo.group(1))
                    db_wo = models.WorkOrder(
                        title=wo_data.get('title', 'Generated Work Order'), 
                        description=wo_data.get('description', ''), 
                        priority=wo_data.get('priority', 'Medium'), 
                        status='Open', 
                        assigned_to=user_id,
                        created_by=user_id
                    )
                    bg_db.add(db_wo)
                    bg_db.flush()
                    created_wo_id = db_wo.id
                    final_content = final_content.replace(match_wo.group(0), '').strip()
                    sys_msg = f'\n\n[System: Work Order #{db_wo.id} has been created]'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    final_content = final_content.replace(match_wo.group(0), '').strip()
                    sys_msg = f'\n\n[System Error: Failed to create Work Order - {str(e)}]'
                    final_content += sys_msg
                    system_additions += sys_msg
            
            match_rep = re.search(r'\[REPORT_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_rep:
                try:
                    rep_data = json.loads(match_rep.group(1))
                    db_rep = models.EngineeringReport(
                        session_id=request.session_id, 
                        title=rep_data.get('title', 'Generated Report'), 
                        report_type=rep_data.get('report_type', 'Engineering Analysis'), 
                        report_content=final_content.replace(match_rep.group(0), '').strip(), 
                        generated_by=user_id
                    )
                    bg_db.add(db_rep)
                    bg_db.flush()
                    created_rep_id = db_rep.id
                    final_content = final_content.replace(match_rep.group(0), '').strip()
                    sys_msg = f'\n\n[System: Report #{db_rep.id} has been generated]'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    pass

            match_inv_req = re.search(r'\[INVENTORY_REQUEST_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_inv_req:
                try:
                    from backend.services.inventory_service import request_part
                    req_data = json.loads(match_inv_req.group(1))
                    svc_msg = request_part(bg_db, user_id, req_data.get('part_name', ''), req_data.get('quantity', 1), req_data.get('equipment_id', ''))
                    final_content = final_content.replace(match_inv_req.group(0), '').strip()
                    sys_msg = f'\n\n✅ **System Action:** {svc_msg}'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    pass

            match_inv_app = re.search(r'\[INVENTORY_APPROVAL_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_inv_app:
                try:
                    from backend.services.inventory_service import approve_issue
                    app_data = json.loads(match_inv_app.group(1))
                    svc_msg = approve_issue(bg_db, user_id, app_data.get('transaction_id', ''))
                    final_content = final_content.replace(match_inv_app.group(0), '').strip()
                    sys_msg = f'\n\n✅ **System Action:** {svc_msg}'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    pass

            match_inv_ret = re.search(r'\[INVENTORY_RETURN_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_inv_ret:
                try:
                    from backend.services.inventory_service import approve_return
                    ret_data = json.loads(match_inv_ret.group(1))
                    svc_msg = approve_return(bg_db, user_id, ret_data.get('part_name', ''), ret_data.get('quantity', 1))
                    final_content = final_content.replace(match_inv_ret.group(0), '').strip()
                    sys_msg = f'\n\n✅ **System Action:** {svc_msg}'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    pass

            match_safety = re.search(r'\[SAFETY_ALERT_TRIGGER:\s*(\{.*?\})\s*\]', final_content, re.IGNORECASE)
            if match_safety:
                try:
                    from backend.services.email_service import notify_safety_escalation
                    safety_data = json.loads(match_safety.group(1))
                    notify_safety_escalation(
                        db=bg_db,
                        asset_name=safety_data.get('asset_name', 'Unknown Asset'),
                        asset_id=safety_data.get('asset_id', 'N/A'),
                        location=safety_data.get('location', 'N/A'),
                        risk_level=safety_data.get('risk_level', 'HIGH'),
                        issue_description=safety_data.get('issue_description', 'No details provided'),
                        root_cause=safety_data.get('root_cause', 'Under Investigation'),
                        recommended_action=safety_data.get('recommended_action', 'Inspect immediately'),
                        priority_level=safety_data.get('priority_level', 'Urgent'),
                        reporter_id=user_id
                    )
                    final_content = final_content.replace(match_safety.group(0), '').strip()
                    r_lvl = safety_data.get('risk_level', 'HIGH')
                    sys_msg = f'\n\n🚨 **System Action:** {r_lvl} RISK ESCALATION generated and stakeholders notified.'
                    final_content += sys_msg
                    system_additions += sys_msg
                except Exception as e:
                    pass
            
            yield f"data: {json.dumps({'status': '✅ Response ready'})}\n\n"
            
            if system_additions:
                yield f"data: {json.dumps({'token': system_additions})}\n\n"
            
            # Send metadata payload
            end_time = time.time()
            response_time = round(end_time - start_time, 2)
            # Make sure retrieved_chunks_count and retrieved_pages_list are defined
            chunk_cnt = retrieved_chunks_count if 'retrieved_chunks_count' in locals() else 0
            page_list = retrieved_pages_list if 'retrieved_pages_list' in locals() else []
            
            yield f"data: {json.dumps({'metadata': {'response_time': response_time, 'retrieved_chunks': chunk_cnt, 'source_pages': page_list}})}\n\n"
            yield 'data: [DONE]\n\n'
            
            agent_msg = models.EngineeringMessage(session_id=request.session_id, sender="assistant", content=final_content)
            bg_db.add(agent_msg)
            
            msg_count = bg_db.query(models.EngineeringMessage).filter(models.EngineeringMessage.session_id == request.session_id).count()
            if msg_count == 2:
                session = bg_db.query(models.EngineeringSession).filter(models.EngineeringSession.session_id == request.session_id).first()
                if session and not session.title:
                    clean_msg = re.sub(r'[^a-zA-Z0-9\s]', '', request.message)
                    words = clean_msg.split()
                    title = ' '.join([w.capitalize() for w in words[:10]])
                    if len(title) > 50:
                         title = title[:47] + '...'
                    if not title.strip():
                         title = 'Engineering Session'
                    session.title = title
            bg_db.commit()

            # Trigger email notifications post-commit so background threads can read the records
            if created_wo_id:
                try:
                    from backend.services.email_service import notify_work_order_generated
                    notify_work_order_generated(bg_db, created_wo_id)
                except Exception as ne:
                    logger.error(f"Failed to trigger work order generated notification from agent: {ne}")

            if created_rep_id:
                try:
                    from backend.services.email_service import notify_engineering_report_generated
                    notify_engineering_report_generated(bg_db, created_rep_id)
                except Exception as ne:
                    logger.error(f"Failed to trigger report ready notification from agent: {ne}")
            bg_db.commit()

            # Fault Tolerant Memory (Non-Blocking)
            import asyncio
            async def background_memory_extract():
                try:
                    mem_db = SessionLocal()
                    await extract_and_update_memory(user_id=user_id, session_id=request.session_id, user_message=request.message, agent_message=final_content, db=mem_db)
                    mem_db.close()
                except Exception as memory_error:
                    print(f"Warning: Memory extraction failed - {str(memory_error)}")
            
            asyncio.create_task(background_memory_extract())
            
            end_time = time.time()
            response_time = end_time - start_time
            print("\n--- MODEL PERFORMANCE LOGGING ---")
            print(f"Detected Intent: {intent}")
            print(f"Selected Module: {selected_module}")
            print(f"Selected Model: {selected_model}")
            print(f"Prompt Length: {prompt_length}")
            print(f"Response Time: {response_time:.4f} seconds")
            print("---------------------------------\n")
            
        except Exception as e:
            import traceback
            print("Failed inside intercepted_stream:", e)
            traceback.print_exc()
        finally:
            bg_db.close()

    return StreamingResponse(intercepted_stream(), media_type='text/event-stream')
