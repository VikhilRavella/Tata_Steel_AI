from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
import backend.models as models
from backend.routers.auth import get_current_active_user

router = APIRouter()

class WorkOrderCreate(BaseModel):
    title: str
    description: str
    priority: str = "Medium"
    assigned_to: Optional[int] = None
    related_alert_id: Optional[int] = None

class WorkOrderUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[int] = None

class MaintenanceOutcomeCreate(BaseModel):
    root_cause: str
    recommendation: str
    action_taken: str
    outcome_status: str
    risk_level: str
    priority_level: str
    downtime_avoided: str
    feedback: Optional[str] = None

class WorkOrderResponse(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[int]
    created_by: int
    related_alert_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.post("", response_model=WorkOrderResponse)
def create_work_order(work_order: WorkOrderCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_wo = models.WorkOrder(
        title=work_order.title,
        description=work_order.description,
        priority=work_order.priority,
        assigned_to=work_order.assigned_to,
        created_by=current_user.id,
        related_alert_id=work_order.related_alert_id
    )
    db.add(db_wo)
    db.commit()
    db.refresh(db_wo)
    
    # Trigger notification if engineer is assigned immediately
    if db_wo.assigned_to:
        from backend.services.email_service import notify_work_order_generated
        notify_work_order_generated(db, db_wo.id)
        
    return db_wo

@router.get("", response_model=List[WorkOrderResponse])
def get_work_orders(status: Optional[str] = None, assigned_to: Optional[int] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    query = db.query(models.WorkOrder)
    if status:
        query = query.filter(models.WorkOrder.status == status)
    if assigned_to is not None:
        query = query.filter(models.WorkOrder.assigned_to == assigned_to)
    return query.all()

@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(work_order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == work_order_id).first()
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return db_wo

@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order(work_order_id: int, work_order: WorkOrderUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == work_order_id).first()
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    status_changed_to_completed = False
    assigned_to_changed = False
    
    if work_order.status is not None:
        if work_order.status == "Completed" and db_wo.status != "Completed":
            status_changed_to_completed = True
        db_wo.status = work_order.status
        if work_order.status == "Completed" and not db_wo.completed_at:
            db_wo.completed_at = datetime.utcnow()
            
    if work_order.assigned_to is not None:
        if db_wo.assigned_to != work_order.assigned_to:
            assigned_to_changed = True
        db_wo.assigned_to = work_order.assigned_to
        
    db.commit()
    db.refresh(db_wo)
    
    from backend.services.email_service import notify_work_order_generated, notify_maintenance_completed
    
    if assigned_to_changed and db_wo.assigned_to:
        notify_work_order_generated(db, db_wo.id)
        
    if status_changed_to_completed:
        notify_maintenance_completed(db, db_wo.id)
        
    return db_wo

@router.post("/{work_order_id}/outcome")
def log_work_order_outcome(
    work_order_id: int, 
    outcome: MaintenanceOutcomeCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_active_user)
):
    db_wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == work_order_id).first()
    if not db_wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    status_changed_to_completed = False
    if db_wo.status != "Completed":
        db_wo.status = "Completed"
        db_wo.completed_at = datetime.utcnow()
        status_changed_to_completed = True
        
    # Log the outcome
    db_outcome = models.MaintenanceOutcome(
        asset_id=db_wo.equipment_id or "Unknown",
        engineer_id=current_user.id,
        root_cause=outcome.root_cause,
        recommendation=outcome.recommendation,
        action_taken=outcome.action_taken,
        outcome_status=outcome.outcome_status,
        risk_level=outcome.risk_level,
        priority_level=outcome.priority_level,
        downtime_avoided=outcome.downtime_avoided,
        feedback=outcome.feedback
    )
    db.add(db_outcome)
    db.commit()
    
    # Audit log
    details_dict = {
        "work_order_id": work_order_id,
        "asset_id": db_wo.equipment_id,
        "outcome_status": outcome.outcome_status,
        "risk_level": outcome.risk_level
    }
    from backend.services.audit_service import log_action
    log_action(
        db=db,
        user_id=current_user.id,
        action="MAINTENANCE_OUTCOME_LOGGED",
        entity_type="WorkOrder",
        entity_id=str(work_order_id),
        details=details_dict
    )
    
    if status_changed_to_completed:
        from backend.services.email_service import notify_maintenance_completed
        notify_maintenance_completed(db, db_wo.id)
        
    return {"status": "success", "message": "Maintenance outcome logged successfully and work order completed"}
