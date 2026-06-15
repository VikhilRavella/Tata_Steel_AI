from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import uuid
import json
from backend.database import get_db
from backend.models import Session as DbSession, Message, SafetyChecklist, User
from backend.schemas import SessionCreate, SessionResponse, SessionAssistCreate
from backend.services.safety_service import verify_safety_checklist
from backend.routers.auth import get_current_active_user
from backend.services.audit_service import log_action
router = APIRouter()

@router.post('/', response_model=SessionResponse)
def create_session(session_in: SessionCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    cross_domain = False
    if session_in.task_domain and current_user.specialization:
        if session_in.task_domain.lower() not in current_user.specialization.lower():
            cross_domain = True
    new_session = DbSession(id=str(uuid.uuid4()), status='active', equipment_id=session_in.equipment_id, primary_engineer_id=current_user.id, task_domain=session_in.task_domain, cross_domain_flag=cross_domain)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    log_action(db, current_user.id, 'session_start', 'session', new_session.id, {'task_domain': session_in.task_domain, 'cross_domain': cross_domain})
    return new_session

@router.post('/assist', response_model=SessionResponse)
def create_assisted_session(session_in: SessionAssistCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    target_user = db.query(User).filter(User.employee_id == session_in.target_employee_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail='Target Employee ID not found.')
    cross_domain = False
    if session_in.task_domain and target_user.specialization:
        if session_in.task_domain.lower() not in target_user.specialization.lower():
            cross_domain = True
    new_session = DbSession(id=str(uuid.uuid4()), status='active', equipment_id=session_in.equipment_id, primary_engineer_id=target_user.id, assisting_engineer_id=current_user.id, device_owner_id=current_user.id, task_domain=session_in.task_domain, cross_domain_flag=cross_domain)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    log_action(db, current_user.id, 'assisted_session_start', 'session', new_session.id, {'target_user_id': target_user.id, 'task_domain': session_in.task_domain})
    return new_session

@router.get('/{session_id}', response_model=SessionResponse)
def get_session(session_id: str, db: Session=Depends(get_db)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    return session

class SafetySubmitRequest(BaseModel):
    worker_name: str
    ppe_verified: bool
    loto_applied: bool
    signature: str

@router.post('/{session_id}/safety')
def submit_safety(session_id: str, req: SafetySubmitRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    log_user_id = session.primary_engineer_id
    record = verify_safety_checklist(db=db, session_id=session_id, worker_name=req.worker_name, ppe_verified=req.ppe_verified, loto_applied=req.loto_applied, signature=req.signature, user_id=log_user_id)
    session.safety_verified = True
    session.loto_confirmed = req.loto_applied
    db.commit()
    log_action(db, log_user_id, 'safety_verified', 'session', session_id)
    return {'status': 'success', 'message': 'Safety verification recorded'}

@router.post('/{session_id}/escalate')
def escalate_session(session_id: str, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    session.status = 'escalated'
    db.commit()
    log_action(db, current_user.id, 'session_escalated', 'session', session_id)
    return {'status': 'success', 'message': 'Session escalated to supervisor.'}

@router.post('/{session_id}/resolve')
def resolve_session(session_id: str, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    session.status = 'resolved'
    session.handover_note = 'Auto-generated handover: Task completed successfully.'
    db.commit()
    log_action(db, current_user.id, 'session_resolved', 'session', session_id)
    return {'status': 'success', 'message': 'Session resolved.'}
from backend.schemas import InstructionAcknowledgeRequest
from backend.models import InstructionAcknowledgment

@router.post('/{session_id}/acknowledge')
def acknowledge_instruction(session_id: str, req: InstructionAcknowledgeRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    ack = InstructionAcknowledgment(session_id=session_id, user_id=current_user.id, instruction_summary=req.instruction_summary, acknowledged=req.status.lower() == 'yes', clarification_requested=req.status.lower() == 'no', signature=req.signature)
    db.add(ack)
    db.commit()
    action_name = 'instruction_acknowledged' if ack.acknowledged else 'instruction_clarification_requested'
    log_action(db, current_user.id, action_name, 'instruction_acknowledgment', str(ack.id), {'summary': req.instruction_summary, 'status': req.status})
    return {'status': 'success', 'message': f'Instruction acknowledgment recorded: {req.status}'}

@router.get('/history/list')
def get_session_history(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    query = db.query(DbSession)
    if current_user.role == 'engineer':
        query = query.filter((DbSession.primary_engineer_id == current_user.id) | (DbSession.assisting_engineer_id == current_user.id))
    elif current_user.role == 'supervisor':
        team_member_ids = [u.id for u in db.query(User).filter(User.supervisor_id == current_user.id).all()]
        team_member_ids.append(current_user.id)
        query = query.filter(DbSession.primary_engineer_id.in_(team_member_ids))
    elif current_user.role == 'manager':
        pass
    sessions = query.order_by(DbSession.started_at.desc()).all()
    result = []
    for s in sessions:
        primary = db.query(User).filter(User.id == s.primary_engineer_id).first()
        result.append({'session_id': s.id, 'status': s.status, 'task_domain': s.task_domain, 'started_at': s.started_at, 'primary_engineer': primary.name if primary else 'Unknown', 'equipment_id': s.equipment_id})
    return result

@router.get('/recent/list')
def get_recent_sessions(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    query = db.query(DbSession)
    if current_user.role == 'engineer':
        query = query.filter((DbSession.primary_engineer_id == current_user.id) | (DbSession.assisting_engineer_id == current_user.id))
    elif current_user.role == 'supervisor':
        team_member_ids = [u.id for u in db.query(User).filter(User.supervisor_id == current_user.id).all()]
        team_member_ids.append(current_user.id)
        query = query.filter(DbSession.primary_engineer_id.in_(team_member_ids))
    elif current_user.role == 'manager':
        pass
    sessions = query.order_by(DbSession.started_at.desc()).limit(3).all()
    result = []
    for s in sessions:
        primary = db.query(User).filter(User.id == s.primary_engineer_id).first()
        result.append({'session_id': s.id, 'status': s.status, 'task_domain': s.task_domain, 'started_at': s.started_at, 'primary_engineer': primary.name if primary else 'Unknown', 'equipment_id': s.equipment_id})
    return result

@router.put('/{session_id}/approve-waiver')
def approve_cross_domain_waiver(session_id: str, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can approve waivers.')
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail='Session not found')
    sess.cross_domain_flag = True
    db.commit()
    log_action(db, current_user.id, 'waiver_approved', 'session', session_id)
    return {'status': 'success', 'message': 'Waiver approved.'}

class ReassignRequest(BaseModel):
    new_engineer_id: int

@router.put('/{session_id}/reassign')
def reassign_session(session_id: str, req: ReassignRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can reassign sessions.')
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail='Session not found')
    sess.primary_engineer_id = req.new_engineer_id
    sess.status = 'active'
    db.commit()
    log_action(db, current_user.id, 'session_reassigned', 'session', session_id, {'new_engineer_id': req.new_engineer_id})
    return {'status': 'success', 'message': 'Session reassigned successfully.'}

@router.delete('/{session_id}')
def delete_session(session_id: str, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    from sqlalchemy import delete
    from backend.models import Message, EngineeringMemory, SafetyChecklist, InstructionAcknowledgment, RequirementProfile, SessionContext, Alert, Feedback, AgentTransfer
    db.execute(delete(Message).where(Message.session_id == session_id))
    db.execute(delete(EngineeringMemory).where(EngineeringMemory.session_id == session_id))
    db.execute(delete(SafetyChecklist).where(SafetyChecklist.session_id == session_id))
    db.execute(delete(InstructionAcknowledgment).where(InstructionAcknowledgment.session_id == session_id))
    db.execute(delete(RequirementProfile).where(RequirementProfile.session_id == session_id))
    db.execute(delete(SessionContext).where(SessionContext.session_id == session_id))
    db.execute(delete(Alert).where(Alert.session_id == session_id))
    db.execute(delete(Feedback).where(Feedback.session_id == session_id))
    db.execute(delete(AgentTransfer).where(AgentTransfer.engineer_session_id == session_id))
    db.delete(session)
    db.commit()
    log_action(db, current_user.id, 'session_deleted', 'session', session_id)
    return {'status': 'success', 'message': 'Session and its messages deleted safely.'}