from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from backend.models import AuditLog
import json

def log_action(db: Session, user_id: int, action: str, entity_type: str=None, entity_id: str=None, details: dict=None, ip_address: str=None):
    """
    Creates an immutable audit log entry for the specified action.
    """
    log_entry = AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details=json.dumps(details) if details else None, ip_address=ip_address)
    db.add(log_entry)
    db.commit()