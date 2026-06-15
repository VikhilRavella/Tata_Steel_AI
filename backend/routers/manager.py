from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
import bcrypt
from backend.database import get_db
from backend.models import User
from backend.routers.auth import RoleChecker, get_current_active_user
router = APIRouter()
allow_manager = RoleChecker(['manager'])
from backend.services.audit_service import log_action
from sqlalchemy.orm import aliased
from backend.models import AuditLog

@router.get('/audit')
def get_audit_logs(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    SupervisorAlias = aliased(User)
    logs = db.query(AuditLog.created_at, AuditLog.action, AuditLog.details, User.name.label('employee_name'), User.employee_id.label('employee_id'), User.role.label('role'), SupervisorAlias.name.label('supervisor_name')).join(User, AuditLog.user_id == User.id).outerjoin(SupervisorAlias, User.supervisor_id == SupervisorAlias.id).order_by(AuditLog.created_at.desc()).all()
    result = []
    for log in logs:
        result.append({'timestamp': log.created_at, 'action': log.action, 'employee_name': log.employee_name, 'employee_id': log.employee_id, 'role': log.role, 'supervisor_name': log.supervisor_name or 'N/A', 'details': log.details or ''})
    return result

class UserRoleUpdate(BaseModel):
    role: str

class UserCreateAdmin(BaseModel):
    employee_id: str
    name: str
    password: str
    role: str
    department: str
    specialization: str = None
    supervisor_id: Optional[int] = None

class UserUpdateAdmin(BaseModel):
    name: str
    role: str
    department: str
    specialization: str = None
    supervisor_id: Optional[int] = None
    password: Optional[str] = None

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

@router.get('/users')
def get_users(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    users = db.query(User).all()
    return [{'id': u.id, 'employee_id': u.employee_id, 'name': u.name, 'role': u.role, 'department': u.department} for u in users]

@router.get('/supervisors/list')
def get_supervisors_list(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    supervisors = db.query(User).filter(User.role == 'supervisor', User.is_active == True).all()
    return [{'id': s.id, 'name': s.name} for s in supervisors]

@router.post('/users')
def create_user(user_in: UserCreateAdmin, db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    existing_user = db.query(User).filter(User.employee_id == user_in.employee_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Employee ID already exists')
    if user_in.role == 'engineer':
        if not user_in.supervisor_id:
            raise HTTPException(status_code=400, detail='Supervisor must be assigned for Engineers.')
        supervisor = db.query(User).filter(User.id == user_in.supervisor_id, User.role == 'supervisor', User.is_active == True).first()
        if not supervisor:
            raise HTTPException(status_code=400, detail='Invalid or inactive Supervisor assigned.')
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(employee_id=user_in.employee_id, name=user_in.name, password_hash=hashed_pw, role=user_in.role, department=user_in.department, specialization=user_in.specialization, supervisor_id=user_in.supervisor_id if user_in.role == 'engineer' else None, is_active=True)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_action(db, current_user.id, 'create_user', 'User', str(new_user.id), {'details': f'Manager {current_user.name} created new {new_user.role} account for {new_user.employee_id}'})
    return {'id': new_user.id, 'employee_id': new_user.employee_id, 'name': new_user.name, 'role': new_user.role, 'department': new_user.department, 'specialization': new_user.specialization, 'supervisor_id': new_user.supervisor_id}

@router.put('/users/{user_id}/role')
def update_user_role(user_id: int, req: UserRoleUpdate, db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.role = req.role
    db.commit()
    return {'status': 'success', 'new_role': user.role}

@router.put('/users/{user_id}/toggle-status')
def toggle_user_status(user_id: int, db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.is_active = not user.is_active
    db.commit()
    return {'status': 'success', 'is_active': user.is_active}

@router.get('/users/manager-view')
def get_users_manager_view(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    from sqlalchemy import func
    from backend.models import Session as DbSession, SafetyChecklist, Message
    try:
        users = db.query(User).all()
    except Exception as e:
        print(f'Error querying users: {e}')
        users = []
    result = {'managers': [], 'supervisors': [], 'engineers': []}
    for u in users:
        try:
            base_data = {'id': u.id, 'employee_id': u.employee_id, 'name': u.name, 'role': u.role, 'department': u.department, 'specialization': u.specialization, 'is_active': u.is_active}
            role_upper = u.role.upper() if u.role else ''
            if role_upper == 'MANAGER':
                result['managers'].append(base_data)
            elif role_upper == 'SUPERVISOR':
                result['supervisors'].append(base_data)
            elif role_upper == 'ENGINEER':
                base_data['supervisor_name'] = u.supervisor.name if getattr(u, 'supervisor', None) else 'Unassigned'
                spec = u.specialization
                if not spec:
                    last_session = (db.execute(select(DbSession).where(DbSession.primary_engineer_id == u.id))).scalars().order_by(DbSession.started_at.desc()).first()
                    if last_session and last_session.task_domain:
                        spec = f'Recent: {last_session.task_domain}'
                    else:
                        spec = 'General Maintenance'
                base_data['specialization'] = spec
                sessions = db.query(DbSession).filter(DbSession.primary_engineer_id == u.id).all()
                session_ids = [s.id for s in sessions]
                if not session_ids:
                    base_data['safety_compliance'] = 'No Data'
                else:
                    total_checks = db.query(SafetyChecklist).filter(SafetyChecklist.session_id.in_(session_ids)).count()
                    if total_checks == 0:
                        base_data['safety_compliance'] = 'No Data'
                    else:
                        verified_checks = db.query(SafetyChecklist).filter(SafetyChecklist.session_id.in_(session_ids), SafetyChecklist.verified == True).count()
                        pct = int(verified_checks / total_checks * 100)
                        if pct >= 80:
                            base_data['safety_compliance'] = f'{pct}% Compliant'
                        else:
                            base_data['safety_compliance'] = f'Warning ({pct}%)'
                total_sessions = len(session_ids)
                if session_ids:
                    total_messages = db.query(Message).filter(Message.session_id.in_(session_ids), Message.sender == 'user').count()
                else:
                    total_messages = 0
                base_data['ai_agent_usage'] = f'{total_sessions} Sessions / {total_messages} Msgs'
                result['engineers'].append(base_data)
        except Exception as item_err:
            print(f'Error parsing manager-view user item: {item_err}')
            continue
    return result

@router.get('/users/{user_id}')
def get_user_by_id(user_id: int, db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return {'id': user.id, 'employee_id': user.employee_id, 'name': user.name, 'role': user.role, 'department': user.department, 'specialization': user.specialization, 'supervisor_id': user.supervisor_id, 'is_active': user.is_active}

@router.put('/users/{user_id}')
def update_user_profile(user_id: int, req: UserUpdateAdmin, db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    if req.role == 'engineer':
        if not req.supervisor_id:
            raise HTTPException(status_code=400, detail='Supervisor must be assigned for Engineers.')
        supervisor = db.query(User).filter(User.id == req.supervisor_id, User.role == 'supervisor', User.is_active == True).first()
        if not supervisor:
            raise HTTPException(status_code=400, detail='Invalid or inactive Supervisor assigned.')
    user.name = req.name
    user.role = req.role
    user.department = req.department
    user.specialization = req.specialization
    user.supervisor_id = req.supervisor_id if req.role == 'engineer' else None
    if req.password and req.password.strip():
        user.password_hash = get_password_hash(req.password)
    db.commit()
    db.refresh(user)
    log_action(db, current_user.id, 'update_user', 'User', str(user.id), {'details': f'Manager {current_user.name} updated profile for {user.employee_id}'})
    return {'id': user.id, 'employee_id': user.employee_id, 'name': user.name, 'role': user.role, 'department': user.department, 'specialization': user.specialization, 'supervisor_id': user.supervisor_id}
from backend.models import Equipment, Alert

@router.get('/health/blocks')
def get_macro_health_blocks(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    aggregates = db.query(Equipment.block, func.avg(Equipment.health_score).label('avg_health')).group_by(Equipment.block).all()
    result = []
    for agg in aggregates:
        block_name = agg.block or 'Unassigned Block'
        avg_health = int(agg.avg_health) if agg.avg_health else 100
        alerts = db.query(Alert).join(Equipment, Alert.equipment_id == Equipment.id).filter(Equipment.block == agg.block, Alert.status == 'active', Alert.severity == 'critical').all()
        status = 'Healthy'
        status_summary = 'All primary cooling systems and conveyors operating nominally.'
        if len(alerts) > 0:
            status = 'Critical Alerts'
            eq = db.query(Equipment).filter(Equipment.id == alerts[0].equipment_id).first()
            if eq:
                status_summary = f'{eq.equipment_name} offline or in critical state. {alerts[0].message}'
            else:
                status_summary = f'Critical alerts active.'
        result.append({'block_name': block_name, 'avg_health_score': avg_health, 'status': status, 'status_summary': status_summary})
    return result
from backend.models import Session as DbSession
import datetime

@router.get('/kpis')
def get_plant_kpis(db: Session=Depends(get_db), current_user: User=Depends(allow_manager)):
    oee_result = db.query(func.avg(Equipment.health_score)).scalar()
    oee = round(oee_result, 1) if oee_result else 100.0
    resolved_sessions = db.query(DbSession).filter(DbSession.status == 'resolved', DbSession.ended_at != None).all()
    if resolved_sessions:
        total_seconds = 0
        for s in resolved_sessions:
            diff = s.ended_at - s.started_at
            total_seconds += diff.total_seconds()
        avg_hours = total_seconds / len(resolved_sessions) / 3600
        mttr = round(avg_hours, 1)
    else:
        mttr = 0.0
    active_issues = db.query(Alert).filter(Alert.status == 'active').count()
    audits_due = db.query(DbSession).filter((DbSession.status == 'escalated') | (DbSession.cross_domain_flag == True) & (DbSession.waiver_approved_by == None)).count()
    aggregates = db.query(Equipment.block, func.avg(Equipment.health_score).label('avg_health')).group_by(Equipment.block).all()
    departments = []
    for agg in aggregates:
        block_name = agg.block or 'Unassigned'
        alerts_count = db.query(Alert).join(Equipment, Alert.equipment_id == Equipment.id).filter(Equipment.block == agg.block, Alert.status == 'active').count()
        status = 'Healthy'
        if alerts_count > 0 or (agg.avg_health and agg.avg_health < 80):
            status = 'Attention'
        departments.append({'name': block_name, 'status': status})
    return {'top_kpis': {'oee': f'{oee}%', 'mttr': f'{mttr} hrs', 'active_issues': active_issues, 'audits_due': audits_due}, 'departments': departments}