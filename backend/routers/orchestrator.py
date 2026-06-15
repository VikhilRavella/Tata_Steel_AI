from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from backend.database import get_db
from backend.models import User, AuditLog
from backend.routers.auth import get_current_active_user
router = APIRouter()

class OrchestrateRequest(BaseModel):
    message: str

@router.post('/chat')
async def orchestrate_chat(request: OrchestrateRequest, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    msg = request.message.lower()
    emergency_keywords = ['fire', 'explosion', 'spark', 'short circuit', 'gas leak', 'injury', 'smoke', 'emergency', 'danger', 'hazard', 'accident']
    if any((k in msg for k in emergency_keywords)):
        log = AuditLog(user_id=current_user.id, action='orchestrator_emergency', details=json.dumps({'message': request.message}))
        db.add(log)
        db.commit()
        return {'agent': 'field', 'response': '🚨 STOP WORK. Supervisor alerted.', 'routed_to': '/api/alerts/emergency'}
    inventory_keywords = ['spare part', 'stock', 'warehouse', 'aisle', 'bin', 'bolt size', 'part number', 'inventory', 'how many', 'available', 'm14']
    if any((k in msg for k in inventory_keywords)):
        return {'agent': 'inventory', 'response': 'Routing to Inventory Database...', 'routed_to': '/api/inventory/search'}
    field_keywords = ['repair', 'fix', 'broken', 'fault', 'vibrat', 'noise', 'overheat', 'bolt', 'bearing', 'motor', 'machine', 'equipment', 'how to', 'steps', 'procedure', 'loto', 'ppe', 'safety']
    if any((k in msg for k in field_keywords)):
        return {'agent': 'field', 'response': 'Routing to Field Agent...', 'routed_to': '/api/agent/chat'}
    eng_keywords = ['architecture', 'design', 'code', 'implement', 'develop', 'build', 'system', 'database', 'api', 'requirement', 'plan']
    if any((k in msg for k in eng_keywords)):
        return {'agent': 'engineering', 'response': 'Routing to Engineering Agent...', 'routed_to': '/api/engineering/chat'}
    return {'agent': 'sandbox', 'response': 'Routing to Sandbox Agent...', 'routed_to': '/api/sandbox/chat'}