from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import User, Session as DbSession, Equipment, Document, Alert
from backend.routers.auth import RoleChecker, get_current_active_user
router = APIRouter()
allow_supervisor_manager = RoleChecker(['supervisor', 'manager', 'engineer'])
from datetime import datetime, date

@router.get('/metrics')
def get_metrics(db: Session=Depends(get_db), current_user: User=Depends(allow_supervisor_manager)):
    if (current_user.role or '').lower() != 'supervisor':
        total_engineers = db.query(User).filter(User.role.ilike('engineer')).count()
        active_engineers = db.query(User).filter(User.role.ilike('engineer'), User.is_active == True).count()
        return {'engineers_on_shift': f'{active_engineers} / {total_engineers}', 'active_escalations': db.query(DbSession).filter(DbSession.status == 'escalated').count(), 'safety_waivers': db.query(DbSession).filter(DbSession.cross_domain_flag == True).count(), 'resolved_today': db.query(DbSession).filter(DbSession.status == 'resolved').count()}
    total_assigned = db.query(User).filter(User.supervisor_id == current_user.id).count()
    active_assigned = db.query(User).filter(User.supervisor_id == current_user.id, User.is_active == True).count()
    active_escalations = db.query(DbSession).join(User, DbSession.primary_engineer_id == User.id).filter(User.supervisor_id == current_user.id, DbSession.status == 'escalated').count()
    today = date.today()
    safety_waivers = db.query(DbSession).join(User, DbSession.primary_engineer_id == User.id).filter(User.supervisor_id == current_user.id, DbSession.cross_domain_flag == True).count()
    resolved_today = db.query(DbSession).join(User, DbSession.primary_engineer_id == User.id).filter(User.supervisor_id == current_user.id, DbSession.status == 'resolved').count()
    return {'engineers_on_shift': f'{active_assigned} / {total_assigned}', 'active_escalations': active_escalations, 'safety_waivers': safety_waivers, 'resolved_today': resolved_today}

@router.get('/escalations')
def get_escalations(db: Session=Depends(get_db), current_user: User=Depends(allow_supervisor_manager)):
    query = db.query(DbSession, User).join(User, DbSession.primary_engineer_id == User.id).filter(DbSession.status == 'escalated')
    if (current_user.role or '').lower() == 'supervisor':
        query = query.filter(User.supervisor_id == current_user.id)
    escalations = query.all()
    result = []
    for sess, user in escalations:
        elapsed = 'Unknown'
        if sess.started_at:
            delta = datetime.datetime.utcnow() - sess.started_at
            hours = delta.total_seconds() // 3600
            minutes = delta.total_seconds() % 3600 // 60
            elapsed = f'{int(hours)}h {int(minutes)}m'
        result.append({'session_id': sess.id, 'engineer_name': user.name, 'equipment': sess.task_domain or 'Unknown Equipment', 'time_elapsed': elapsed, 'priority': 'High Priority', 'ai_root_cause': 'System automatically triggered escalation for supervisor review.', 'mttr_estimated': 'Pending Review', 'personnel_needed': 'TBD'})
    return result
from backend.models import Message
from fastapi import HTTPException

@router.get('/escalations/{session_id}')
def get_escalation_detail(session_id: str, db: Session=Depends(get_db), current_user: User=Depends(allow_supervisor_manager)):
    sess = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail='Session not found')
    engineer = db.query(User).filter(User.id == sess.primary_engineer_id).first()
    if (current_user.role or '').lower() == 'supervisor' and engineer.supervisor_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized to view this escalation')
    elapsed = 'Unknown'
    if sess.started_at:
        delta = datetime.utcnow() - sess.started_at
        hours = delta.total_seconds() // 3600
        minutes = delta.total_seconds() % 3600 // 60
        elapsed = f'{int(hours)}h {int(minutes)}m'
    last_ai_msg = db.query(Message).filter(Message.session_id == session_id, Message.sender == 'ai').order_by(Message.created_at.desc()).first()
    ai_summary = 'AI root cause analysis pending or not available.'
    if last_ai_msg:
        ai_summary = last_ai_msg.content
    return {'session_id': sess.id, 'equipment_name': sess.task_domain or 'Unknown Equipment', 'engineer_name': engineer.name if engineer else 'Unknown', 'specialization': engineer.specialization if engineer else 'General', 'time_elapsed': elapsed, 'ai_summary': ai_summary, 'mttr_estimate': 'Pending Review'}
from backend.models import Alert, Equipment
from sqlalchemy import func

@router.get('/health/predictive-flags')
def get_predictive_flags(sector: str='All Sectors', db: Session=Depends(get_db), current_user: User=Depends(allow_supervisor_manager)):
    query = db.query(Alert, Equipment).join(Equipment, Alert.equipment_id == Equipment.id)
    query = query.filter((Alert.alert_type == 'predictive') | (Alert.severity == 'critical'))
    if sector and sector != 'All Sectors':
        query = query.filter(Equipment.block == sector)
    alerts = query.all()
    result = []
    for alert, eq in alerts:
        confidence = '92%' if alert.severity == 'critical' else '85%'
        result.append({'asset_name': eq.equipment_name, 'anomaly_detected': alert.message, 'confidence_score': confidence, 'equipment_id': eq.id})
    return result

@router.get('/health/aggregates')
def get_health_aggregates(sector: str='All Sectors', db: Session=Depends(get_db), current_user: User=Depends(allow_supervisor_manager)):
    query = db.query(Equipment.category, func.avg(Equipment.health_score).label('avg_health'), func.count(Equipment.id).label('total_assets'))
    if sector and sector != 'All Sectors':
        query = query.filter(Equipment.block == sector)
    aggregates = query.group_by(Equipment.category).all()
    result = []
    for agg in aggregates:
        cat = agg.category or 'Uncategorized'
        avg_health = int(agg.avg_health) if agg.avg_health else 100
        alert_query = db.query(Alert).join(Equipment, Alert.equipment_id == Equipment.id).filter(Equipment.category == agg.category, Alert.status == 'active')
        if sector and sector != 'All Sectors':
            alert_query = alert_query.filter(Equipment.block == sector)
        active_alerts = alert_query.count()
        if avg_health > 80:
            note = 'All systems operating within normal parameters.'
        elif avg_health > 50:
            note = f'Requires attention. {active_alerts} minor alerts active.'
        else:
            note = f'Critical failure detected. {active_alerts} active alerts.'
        result.append({'category': cat, 'avg_health': avg_health, 'active_alerts': active_alerts, 'critical_notes': note})
    return result

from backend.models import EquipmentMaster, InventoryMaster, WorkOrder, MaintenanceHistory, AuditLog, InventoryTransaction, SupervisorDirectory

@router.get('/engineers')
def get_engineers(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    if (current_user.role or '').lower() == 'supervisor':
        engineers = db.query(User).filter(User.role.ilike('engineer'), User.supervisor_id == current_user.id).all()
    else:
        engineers = db.query(User).filter(User.role.ilike('engineer')).all()
    res = []
    for eng in engineers:
        # Assigned equipment count (using assigned_supervisor from EquipmentMaster)
        # Actually engineers might be assigned via work orders or directly. If the supervisor owns the equipment, they oversee it.
        # Let's count open work orders
        open_wos = db.query(WorkOrder).filter(WorkOrder.assigned_to == eng.id, WorkOrder.status == 'Open').count()
        res.append({
            "id": eng.id,
            "employee_id": eng.employee_id,
            "name": eng.name,
            "department": eng.department,
            "phone": eng.phone or "N/A",
            "status": "Active" if eng.is_active else "Inactive",
            "open_work_orders": open_wos
        })
    return res

@router.get('/equipment')
def get_equipment(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    if (current_user.role or '').lower() == 'supervisor':
        sup_dir = db.query(SupervisorDirectory).filter(SupervisorDirectory.employee_id == current_user.employee_id).first()
        if sup_dir:
            eqs = db.query(EquipmentMaster).filter(
                (EquipmentMaster.assigned_supervisor == sup_dir.supervisor_id) | 
                (EquipmentMaster.assigned_supervisor == current_user.employee_id) |
                (EquipmentMaster.assigned_supervisor == str(current_user.id))
            ).all()
        else:
            eqs = db.query(EquipmentMaster).filter(
                (EquipmentMaster.assigned_supervisor == current_user.employee_id) |
                (EquipmentMaster.assigned_supervisor == str(current_user.id))
            ).all()
    else:
        eqs = db.query(EquipmentMaster).all()
    
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
            "last_maintenance": last_maint.maintenance_date.strftime('%Y-%m-%d') if last_maint else "Never"
        })
    return res

@router.get('/work-orders')
def get_work_orders(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    wos = db.query(WorkOrder).all()
    res = []
    
    is_sup = (current_user.role or '').lower() == 'supervisor'
    sup_dir = None
    if is_sup:
        sup_dir = db.query(SupervisorDirectory).filter(SupervisorDirectory.employee_id == current_user.employee_id).first()
        
    for w in wos:
        eng = db.query(User).filter(User.id == w.assigned_to).first()
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == w.equipment_id).first()
        
        if is_sup:
            can_see = False
            # Condition 1: Supervisor created it
            if w.created_by == current_user.id:
                can_see = True
            # Condition 2: Assigned to one of their engineers
            elif eng and eng.supervisor_id == current_user.id:
                can_see = True
            # Condition 3: Equipment belongs to supervisor
            elif eq and sup_dir and eq.assigned_supervisor == sup_dir.supervisor_id:
                can_see = True
                
            if not can_see:
                continue
                
        res.append({
            "id": w.id,
            "title": w.title,
            "equipment_name": eq.equipment_name if eq else "N/A",
            "priority": w.priority,
            "status": w.status,
            "assigned_to": eng.name if eng else "Unassigned",
            "created_at": w.created_at
        })
    return res

from pydantic import BaseModel
class AssignEngineerRequest(BaseModel):
    engineer_id: int

@router.post('/work-orders/{wo_id}/assign')
def assign_work_order(wo_id: int, req: AssignEngineerRequest, db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
        
    engineer = db.query(User).filter(User.id == req.engineer_id).first()
    if not engineer:
        raise HTTPException(status_code=404, detail="Engineer not found")
        
    wo.assigned_to = engineer.id
    
    # Audit log
    import json
    from datetime import datetime
    new_log = AuditLog(
        user_id=current_user.id,
        action='assign_work_order',
        entity_type='WorkOrder',
        entity_id=str(wo.id),
        details=json.dumps({"message": f"Assigned Work Order {wo.id} to Engineer {engineer.name}"}),
        created_at=datetime.utcnow()
    )
    db.add(new_log)
    db.commit()
    
    # Trigger notification
    try:
        from backend.services.email_service import notify_work_order_generated
        notify_work_order_generated(db, wo.id)
    except Exception as e:
        pass
        
    return {"status": "success", "message": "Engineer assigned successfully"}

@router.get('/maintenance-requests')
def get_maintenance_requests(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    mhs = db.query(MaintenanceHistory).all()
    res = []
    for mh in mhs:
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == mh.equipment_id).first()
        eng = db.query(User).filter(User.id == mh.performed_by).first()
        
        if (current_user.role or '').lower() == 'supervisor':
            # Check if equipment belongs to supervisor
            if not eq or (eq.assigned_supervisor != current_user.employee_id and eq.assigned_supervisor != str(current_user.id)):
                continue

        res.append({
            "id": mh.id,
            "equipment_name": eq.equipment_name if eq else mh.equipment_id,
            "date": mh.maintenance_date,
            "description": mh.description,
            "engineer": eng.name if eng else "Unknown",
            "status": mh.status
        })
    return res

@router.get('/inventory-requests')
def get_inventory_requests(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    reqs = db.query(InventoryTransaction).filter(InventoryTransaction.transaction_type == 'PENDING').all()
    res = []
    import datetime
    for r in reqs:
        eng = db.query(User).filter(User.id == r.requested_by).first()
        if (current_user.role or '').lower() == 'supervisor':
            if not eng or eng.supervisor_id != current_user.id:
                continue
        time_waiting = "0 mins"
        if r.timestamp:
            delta = datetime.datetime.utcnow() - r.timestamp
            time_waiting = f"{int(delta.total_seconds() // 60)} mins"
            
        res.append({
            "id": r.transaction_id,
            "engineer": eng.name if eng else "Unknown",
            "equipment": r.equipment_id or "N/A",
            "part": r.part_name,
            "quantity": r.quantity,
            "request_time": r.timestamp.strftime('%Y-%m-%d %H:%M:%S') if r.timestamp else "N/A",
            "status": r.transaction_type,
            "time_waiting": time_waiting
        })
    return res

@router.get('/inventory-status')
def get_inventory_status(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    invs = db.query(InventoryMaster).all()
    res = []
    for inv in invs:
        res.append({
            "part_number": inv.part_number,
            "part_name": inv.part_name,
            "stock_qty": inv.stock_qty,
            "minimum_stock": inv.minimum_stock,
            "warehouse": inv.warehouse,
            "rack": inv.rack,
            "bin": inv.bin,
            "supplier": inv.supplier or "N/A"
        })
    return res

@router.get('/audit-logs')
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    res = []
    for l in logs:
        user = db.query(User).filter(User.id == l.user_id).first()
        # Filter for only the supervisor's team's actions (engineers assigned to them)
        if (current_user.role or '').lower() == 'supervisor':
            if not user or user.supervisor_id != current_user.id:
                continue
        res.append({
            "id": l.id,
            "timestamp": l.created_at,
            "user": user.name if user else f"User {l.user_id}",
            "action": l.action,
            "entity": l.entity_type,
            "details": l.details
        })
    return res

@router.get('/profile')
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(allow_supervisor_manager)):
    profile_data = {
        "name": current_user.name,
        "employee_id": current_user.employee_id,
        "email": current_user.email,
        "phone": current_user.phone,
        "department": current_user.department,
        "role": current_user.role,
        "plant": "N/A",
        "block": "N/A"
    }
    
    sup_dir = db.query(SupervisorDirectory).filter(SupervisorDirectory.employee_id == current_user.employee_id).first()
    if sup_dir:
        profile_data["name"] = sup_dir.name or profile_data["name"]
        profile_data["department"] = sup_dir.department or profile_data["department"]
        profile_data["email"] = sup_dir.email or profile_data["email"]
        profile_data["phone"] = sup_dir.phone or profile_data["phone"]
        profile_data["plant"] = sup_dir.plant or profile_data["plant"]
        profile_data["block"] = sup_dir.block or profile_data["block"]
        
    return profile_data
