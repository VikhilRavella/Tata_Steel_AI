from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from backend.models import SafetyChecklist, Session as DbSession, Notification

async def verify_safety_checklist(db: AsyncSession, session_id: str, worker_name: str, ppe_verified: bool, loto_applied: bool, signature: str, user_id: int):
    """
    Records a completed safety verification step and notifies supervisors.
    """
    if ppe_verified:
        ppe_record = SafetyChecklist(session_id=session_id, item_name='PPE Check', verified=True, verification_method='image_detection')
        db.add(ppe_record)
    if loto_applied:
        loto_record = SafetyChecklist(session_id=session_id, item_name='LOTO', verified=True, verification_method='manual_confirm', notes=signature)
        db.add(loto_record)
    db_session = (db.execute(select(DbSession).where(DbSession.id == session_id))).scalars().first()
    if db_session:
        db_session.loto_confirmed = loto_applied
        db_session.safety_verified = True
        db_session.digital_signature = signature
    notification = Notification(recipient_id=1, title='Safety Verified', body=f'Safety verified for session {session_id} by {worker_name}', type='safety_alert')
    db.add(notification)
    db.commit()
    return True