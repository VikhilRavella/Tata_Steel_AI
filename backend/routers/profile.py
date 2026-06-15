import os
import json
import base64
import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from backend.routers.auth import get_current_active_user
from backend.services.email_service import send_notification
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("profile_router")
router = APIRouter(prefix="/profile", tags=["Profile"])

class ProfileUpdatePayload(BaseModel):
    full_name: str
    email: str
    phone_number: str

@router.get("")
def get_profile(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Dynamically resolve plant and supervisor name from supervisor
    plant = "N/A"
    supervisor_name = "N/A"
    if current_user.supervisor_id:
        supervisor = db.query(models.User).filter(models.User.id == current_user.supervisor_id).first()
        if supervisor:
            supervisor_name = supervisor.name
            sup_dir = db.query(models.SupervisorDirectory).filter(models.SupervisorDirectory.employee_id == supervisor.employee_id).first()
            if sup_dir:
                plant = sup_dir.plant or "N/A"
                
    return {
        "id": current_user.id,
        "username": current_user.employee_id,
        "employee_id": current_user.employee_id,
        "full_name": current_user.name,
        "email": current_user.email or "",
        "phone_number": current_user.phone or "",
        "role": current_user.role,
        "department": current_user.department or "N/A",
        "plant": plant,
        "supervisor_name": supervisor_name,
        "is_active": current_user.is_active
    }

@router.put("/update")
async def update_profile(
    payload: ProfileUpdatePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Validation for email and phone number
    import re
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not re.match(r"^\+?[0-9\s\-()]{7,20}$", payload.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    # Old values for audit logging
    old_values = {
        "full_name": current_user.name,
        "email": current_user.email,
        "phone_number": current_user.phone
    }
    
    # Update fields
    current_user.name = payload.full_name
    current_user.email = payload.email
    current_user.phone = payload.phone_number
    
    db.commit()
    
    new_values = {
        "full_name": current_user.name,
        "email": current_user.email,
        "phone_number": current_user.phone
    }
    
    # Log action
    details_dict = {
        "old_values": old_values,
        "new_values": new_values
    }
    db.add(models.AuditLog(
        user_id=current_user.id,
        action="PROFILE_UPDATED",
        entity_type="User",
        entity_id=str(current_user.id),
        details=json.dumps(details_dict),
        ip_address="127.0.0.1"
    ))
    db.commit()
    
    # Send email notification asynchronously using the stable email service
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
    
    await send_notification(
        user_id=current_user.id,
        notification_type="Profile Updated",
        message="Your profile information has been updated successfully.",
        to_email=current_user.email,
        subject="Profile Updated Successfully",
        email_body=email_body
    )
    
    return {"status": "success", "message": "Profile updated successfully"}

# Include GET /api/notifications here to match frontend URLs exactly
notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notification_router.get("")
def get_user_notifications(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Fetch notifications for current user
    notifs = db.query(models.Notification).filter(models.Notification.recipient_id == current_user.id).order_by(models.Notification.created_at.desc()).all()
    unread_count = db.query(models.Notification).filter(models.Notification.recipient_id == current_user.id, models.Notification.is_read == False).count()
    
    formatted = []
    for n in notifs:
        formatted.append({
            "id": n.id,
            "type": n.type or "Alert",
            "message": n.body,
            "timestamp": n.created_at.isoformat() if n.created_at else "",
            "is_read": n.is_read
        })
        
    return {
        "unread_count": unread_count,
        "notifications": formatted
    }

@notification_router.put("/{id}/read")
@notification_router.patch("/{id}/read")
def mark_notification_as_read(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    notif = db.query(models.Notification).filter(models.Notification.id == id, models.Notification.recipient_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "success"}

@notification_router.put("/read-all")
@notification_router.patch("/read-all")
@notification_router.post("/read-all")
def mark_all_notifications_as_read(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    notifs = db.query(models.Notification).filter(models.Notification.recipient_id == current_user.id, models.Notification.is_read == False).all()
    for n in notifs:
        n.is_read = True
    db.commit()
    return {"status": "success", "count": len(notifs)}
