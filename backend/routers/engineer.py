from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Notification
import backend.models as models
from backend.routers.auth import get_current_active_user
router = APIRouter()

@router.get('/notifications')
def get_notifications(unread_only: bool=True, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    query = db.query(Notification).filter(Notification.recipient_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).all()
    if notifications:
        for n in notifications:
            n.is_read = True
        db.commit()
    return {'count': len(notifications), 'notifications': [{'id': n.id, 'title': n.title, 'message': n.body, 'type': n.type, 'created_at': n.created_at} for n in notifications]}

@router.patch('/notifications/{id}/read')
def mark_notification_read(id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    notification = db.query(Notification).filter(Notification.id == id, Notification.recipient_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail='Notification not found')
    notification.is_read = True
    db.commit()
    return {'status': 'success', 'message': 'Notification marked as read'}

from backend.models import EquipmentMaster, WorkOrder, MaintenanceHistory, InventoryTransaction, PartRequest

@router.get('/profile')
def get_profile(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    supervisor = db.query(User).filter(User.id == current_user.supervisor_id).first()
    return {
        "id": current_user.id,
        "name": current_user.name,
        "employee_id": current_user.employee_id,
        "email": current_user.email or "",
        "phone": current_user.phone or "",
        "department": current_user.department or "N/A",
        "supervisor": supervisor.name if supervisor else "N/A",
        "plant": supervisor.plant if (supervisor and hasattr(supervisor, 'plant')) else "N/A",
        "role": current_user.role
    }

from pydantic import BaseModel
class ProfileUpdate(BaseModel):
    name: str
    email: str
    phone: str

@router.put('/profile')
async def update_profile(profile: ProfileUpdate, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    import json
    import datetime
    import re
    
    # Validation for email and phone number
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", profile.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not re.match(r"^\+?[0-9\s\-()]{7,20}$", profile.phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
        
    # Old values for audit logging
    old_values = {
        "full_name": current_user.name,
        "email": current_user.email,
        "phone_number": current_user.phone
    }
    
    current_user.name = profile.name
    current_user.email = profile.email
    current_user.phone = profile.phone
    db.commit()
    
    new_values = {
        "full_name": current_user.name,
        "email": current_user.email,
        "phone_number": current_user.phone
    }
    
    # Audit log
    details_dict = {
        "old_values": old_values,
        "new_values": new_values
    }
    from backend.models import AuditLog
    db.add(AuditLog(
        user_id=current_user.id,
        action="PROFILE_UPDATED",
        entity_type="User",
        entity_id=str(current_user.id),
        details=json.dumps(details_dict),
        ip_address="127.0.0.1"
    ))
    db.commit()
    
    # Send email notification and log
    timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    email_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; color: #333;">
        <p>Hello {current_user.name},</p>
        <p>Your profile information has been updated successfully.</p>
        <p><strong>Updated Details:</strong></p>
        <p>Name: {current_user.name}</p>
        <p>Email: {current_user.email}</p>
        <p>Phone Number: {current_user.phone}</p>
        <p>Updated At: {timestamp_str}</p>
        <p>Industrial AI Maintenance Platform</p>
    </div>
    """
    
    from backend.services.email_service import send_notification
    await send_notification(
        user_id=current_user.id,
        notification_type="Profile Updated",
        message="Your profile information has been updated successfully.",
        to_email=current_user.email,
        subject="Profile Updated Successfully",
        email_body=email_body
    )
    return {"status": "success", "message": "Profile updated successfully"}

@router.get('/equipment')
def get_my_equipment(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    # Since there is no assigned_engineer, we return equipment assigned to their supervisor
    if not current_user.supervisor_id:
        return []
    supervisor = db.query(User).filter(User.id == current_user.supervisor_id).first()
    if not supervisor:
        return []
    
    eqs = db.query(EquipmentMaster).filter(
        (EquipmentMaster.assigned_supervisor == supervisor.employee_id) | 
        (EquipmentMaster.assigned_supervisor == str(supervisor.id))
    ).all()
    
    res = []
    for eq in eqs:
        last_maint = db.query(MaintenanceHistory).filter(MaintenanceHistory.equipment_id == eq.equipment_id).order_by(MaintenanceHistory.maintenance_date.desc()).first()
        res.append({
            "equipment_id": eq.equipment_id,
            "equipment_name": eq.equipment_name,
            "equipment_type": eq.equipment_type,
            "plant": eq.plant,
            "block": eq.block,
            "status": eq.status,
            "criticality": eq.criticality,
            "assigned_supervisor": supervisor.name,
            "last_maintenance": last_maint.maintenance_date.strftime('%Y-%m-%d') if last_maint else "Never"
        })
    return res

@router.get('/work-orders')
def get_my_work_orders(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    wos = db.query(WorkOrder).filter(WorkOrder.assigned_to == current_user.id).all()
    res = []
    for w in wos:
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == w.equipment_id).first()
        assigner = db.query(User).filter(User.id == w.created_by).first()
        res.append({
            "id": w.id,
            "title": w.title,
            "equipment_name": eq.equipment_name if eq else "N/A",
            "priority": w.priority,
            "status": w.status,
            "assigned_by": assigner.name if assigner else "System",
            "created_at": w.created_at
        })
    return res

@router.get('/maintenance')
def get_my_maintenance(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    mhs = db.query(MaintenanceHistory).filter(MaintenanceHistory.performed_by == current_user.id).all()
    res = []
    for mh in mhs:
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == mh.equipment_id).first()
        res.append({
            "id": mh.id,
            "equipment_name": eq.equipment_name if eq else mh.equipment_id,
            "date": mh.maintenance_date,
            "description": mh.description,
            "performed_by": current_user.name,
            "status": mh.status
        })
    return res

@router.get('/inventory-requests')
def get_my_inventory_requests(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    reqs = db.query(InventoryTransaction).filter(
        InventoryTransaction.requested_by == current_user.id,
        InventoryTransaction.transaction_type.in_(['PENDING', 'APPROVED', 'REJECTED'])
    ).all()
    res = []
    for r in reqs:
        # Get approver name if approved_by exists
        approver_name = "N/A"
        if r.approved_by:
            approver = db.query(models.User).filter(models.User.id == r.approved_by).first()
            if approver:
                approver_name = approver.name
                
        res.append({
            "transaction_id": r.transaction_id,
            "part_number": r.part_number,
            "part_name": r.part_name,
            "quantity": r.quantity,
            "status": r.transaction_type,
            "timestamp": r.timestamp,
            "approved_at": r.approved_at,
            "approved_by": approver_name,
            "rejection_reason": r.rejection_reason
        })
    return res

@router.get('/dashboard-metrics')
def get_dashboard_metrics(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    open_wo = db.query(WorkOrder).filter(WorkOrder.assigned_to == current_user.id, WorkOrder.status != "Completed").count()
    completed_wo = db.query(WorkOrder).filter(WorkOrder.assigned_to == current_user.id, WorkOrder.status == "Completed").count()
    pending_req = db.query(InventoryTransaction).filter(InventoryTransaction.requested_by == current_user.id, InventoryTransaction.transaction_type == "PENDING").count()
    recent_maint = db.query(MaintenanceHistory).filter(MaintenanceHistory.performed_by == current_user.id).count()
    
    return {
        "assigned_equipment": len(get_my_equipment(db, current_user)),
        "open_work_orders": open_wo,
        "completed_work_orders": completed_wo,
        "pending_requests": pending_req,
        "recent_maintenance": recent_maint,
        "inventory_requests": pending_req,
        "safety_alerts": 0,
        "equipment_health_summary": "98%"
    }