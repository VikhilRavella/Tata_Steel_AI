from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from backend.database import get_db
from backend.models import Alert, User, Equipment
from backend.services.websocket_manager import ws_manager
from backend.services.audit_service import log_action
from backend.routers.auth import get_current_active_user
logger = logging.getLogger(__name__)
router = APIRouter()

class EmergencyPayload(BaseModel):
    session_id: int
    equipment_id: str
    fault_type: str
    description: str
    location: str
    reported_by_user_id: int

class AcknowledgePayload(BaseModel):
    assigned_to: int

class ResolvePayload(BaseModel):
    resolution_notes: Optional[str] = None

@router.websocket('/ws/{user_id}/{role}')
async def websocket_endpoint(ws: WebSocket, user_id: int, role: str):
    await ws_manager.connect(ws, user_id, role)
    try:
        await ws.send_json({'event': 'CONNECTED', 'message': f'Alert channel active for user {user_id}', 'role': role})
        while True:
            data = await ws.receive_text()
            if data == 'ping':
                await ws.send_text('pong')
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f'WS error user {user_id}: {e}')
        await ws_manager.disconnect(user_id)

@router.post('/emergency')
async def trigger_emergency(payload: EmergencyPayload, db: Session=Depends(get_db)):
    alert = {'event': 'EMERGENCY', 'equipment_id': payload.equipment_id, 'fault_type': payload.fault_type, 'description': payload.description, 'location': payload.location, 'severity': 'CRITICAL', 'timestamp': datetime.utcnow().isoformat(), 'action_required': 'Respond immediately'}
    sent_count = await ws_manager.broadcast_to_role('supervisor', alert)
    eq_id = None
    asset_name = payload.equipment_id
    if payload.equipment_id.isdigit():
        eq_id = int(payload.equipment_id)
        eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
        if eq:
            asset_name = f"{eq.equipment_name} ({eq.equipment_id_code})"
    else:
        eq = db.query(Equipment).filter(Equipment.equipment_id_code == payload.equipment_id).first()
        if eq:
            eq_id = eq.id
            asset_name = f"{eq.equipment_name} ({eq.equipment_id_code})"
            
    new_alert = Alert(equipment_id=eq_id, alert_type=payload.fault_type, message=payload.description, severity='critical', status='open', session_id=str(payload.session_id))
    db.add(new_alert)
    db.commit()
    log_action(db, user_id=payload.reported_by_user_id, action='EMERGENCY_TRIGGERED', entity_type='equipment', entity_id=str(eq_id) if eq_id else None, details={'fault_type': payload.fault_type, 'location': payload.location})
    
    # Trigger Critical Risk Alert email notification
    try:
        from backend.services.email_service import notify_safety_escalation
        notify_safety_escalation(
            db=db,
            asset_name=asset_name,
            asset_id=payload.equipment_id,
            location=payload.location,
            risk_level="CRITICAL",
            issue_description=payload.description,
            root_cause=payload.fault_type,
            recommended_action=payload.description,
            priority_level="Urgent",
            reporter_id=payload.reported_by_user_id
        )
    except Exception as e:
        logger.error(f"Failed to trigger critical risk email notification: {e}")
        
    return {'status': 'dispatched', 'supervisors_alerted': sent_count, 'alert_id': new_alert.id}

@router.get('/active')
async def get_active_alerts(current_user: User=Depends(get_current_active_user), db: AsyncSession=Depends(get_db)):
    alerts = (db.execute(select(Alert).where(Alert.status == 'open'))).scalars().order_by(Alert.created_at.desc()).limit(50).all()
    return {'alerts': [{'id': a.id, 'equipment_id': a.equipment_id, 'fault_type': a.alert_type, 'message': a.message, 'severity': a.severity, 'created_at': a.created_at.isoformat() if a.created_at else None} for a in alerts]}

@router.patch('/{alert_id}/acknowledge')
async def acknowledge_alert(
    alert_id: int, 
    payload: AcknowledgePayload, 
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = "acknowledged"
    alert.assigned_to = payload.assigned_to
    db.commit()
    db.refresh(alert)
    
    return {
        "id": alert.id,
        "status": alert.status,
        "assigned_to": alert.assigned_to
    }

@router.patch('/{alert_id}/resolve')
async def resolve_alert(
    alert_id: int, 
    payload: ResolvePayload, 
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    
    if payload.resolution_notes:
        alert.message += f"\n\nResolution Notes: {payload.resolution_notes}"
        
    db.commit()
    db.refresh(alert)
    
    return {
        "id": alert.id,
        "status": alert.status,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
    }