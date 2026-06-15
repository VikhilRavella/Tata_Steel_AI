from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import bcrypt
from backend.database import get_db
from backend.models import User
from backend.schemas import LoginRequest, Token, UserResponse, UserCreate, UserCreateByManager, UserCreateBySupervisor
from fastapi.security import OAuth2PasswordBearer
router = APIRouter()
SECRET_KEY = 'hackathon_super_secret_key'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 480
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/auth/login')

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials', headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id: str = payload.get('sub')
        if employee_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user

class RoleChecker:

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User=Depends(get_current_active_user)):
        user_role_upper = user.role.upper() if user.role else ''
        allowed_roles_upper = [r.upper() for r in self.allowed_roles]
        if user_role_upper not in allowed_roles_upper:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Operation not permitted')
        return user

@router.post('/manager/create-supervisor', response_model=UserResponse)
def manager_create_supervisor(user_in: UserCreateByManager, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if current_user.role != 'manager':
        raise HTTPException(status_code=403, detail='Only Managers can create Supervisors or Engineers.')
    db_user = db.query(User).filter(User.employee_id == user_in.employee_id).first()
    if db_user:
        raise HTTPException(status_code=400, detail='Employee ID already registered')
    hashed_password = get_password_hash(user_in.password)
    new_user = User(employee_id=user_in.employee_id, name=user_in.name, role=user_in.role, department=user_in.department, specialization=user_in.specialization, password_hash=hashed_password, is_active=True)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post('/supervisor/create-engineer', response_model=UserResponse)
def supervisor_create_engineer(user_in: UserCreateBySupervisor, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only Supervisors can create Engineers using this endpoint.')
    db_user = db.query(User).filter(User.employee_id == user_in.employee_id).first()
    if db_user:
        raise HTTPException(status_code=400, detail='Employee ID already registered')
    hashed_password = get_password_hash(user_in.password)
    new_user = User(employee_id=user_in.employee_id, name=user_in.name, role='engineer', department=user_in.department, specialization=user_in.specialization, supervisor_id=current_user.id, password_hash=hashed_password, is_active=True)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get('/demo-users')
def get_demo_users():
    return {
        "manager": {
            "employee_id": "MGR001",
            "role": "manager"
        },
        "supervisor": {
            "employee_id": "SUP001",
            "role": "supervisor"
        },
        "engineer": {
            "employee_id": "ENG001",
            "role": "engineer"
        }
    }

@router.post('/login', response_model=Token)
def login(request: LoginRequest, db: Session=Depends(get_db)):
    print(f'Login attempt for: {request.employee_id}')
    user = db.query(User).filter(User.employee_id == request.employee_id).first()
    print(f'User found: {user is not None}')
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect employee ID or password', headers={'WWW-Authenticate': 'Bearer'})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account deactivated')
    import json
    from backend.models import AuditLog
    new_log = AuditLog(user_id=user.id, action='login', details=json.dumps({'message': f'User {user.name} logged in successfully', 'role': user.role}))
    db.add(new_log)
    db.commit()

    # Send Account Login Notification
    if user.email:
        try:
            from backend.services.email_service import send_notification_sync, format_email_body
            timestamp_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            details = {
                "Employee ID": user.employee_id,
                "Name": user.name,
                "Role": user.role.upper() if user.role else "N/A",
                "IP Address": "127.0.0.1"
            }
            email_body = format_email_body(
                name=user.name,
                message="A new login was detected for your account.",
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=user.id,
                notification_type="Account Login Detected",
                message=f"Account login detected for {user.name} ({user.employee_id}).",
                to_email=user.email,
                subject="Account Login Detected",
                email_body=email_body
            )
        except Exception as e:
            print(f"Failed to send account login notification: {e}")

    access_token = create_access_token(data={'sub': user.employee_id, 'role': user.role})
    return {'access_token': access_token, 'token_type': 'bearer', 'role': user.role, 'name': user.name, 'employee_id': user.employee_id}

@router.post('/register', response_model=UserResponse)
def register(user_in: UserCreate, db: Session=Depends(get_db)):
    existing_user = db.query(User).filter(User.employee_id == user_in.employee_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Employee ID already registered')
    hashed_password = get_password_hash(user_in.password)
    new_user = User(name=user_in.name, employee_id=user_in.employee_id, role=user_in.role, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user