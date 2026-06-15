from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from backend.database import get_db
from backend.models import User, NotificationLog
from backend.routers.auth import get_current_active_user

router = APIRouter()

@router.get("/")
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    logs = db.query(NotificationLog).filter(NotificationLog.user_id == current_user.id).order_by(NotificationLog.timestamp.desc()).limit(50).all()
    unread_count = db.query(NotificationLog).filter(NotificationLog.user_id == current_user.id, NotificationLog.is_read == False).count()
    
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "type": log.notification_type,
            "message": log.message,
            "is_read": log.is_read,
            "timestamp": log.timestamp.isoformat()
        })
    return {"unread_count": unread_count, "notifications": result}

@router.put("/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    log = db.query(NotificationLog).filter(NotificationLog.id == notification_id, NotificationLog.user_id == current_user.id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    log.is_read = True
    db.commit()
    return {"status": "success"}
