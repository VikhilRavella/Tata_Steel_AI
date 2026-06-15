from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserCreateByManager(BaseModel):
    employee_id: str
    name: str
    password: str
    department: str
    role: str # "supervisor" or "engineer"
    specialization: Optional[str] = None

class UserCreateBySupervisor(BaseModel):
    employee_id: str
    name: str
    password: str
    department: str
    role: str = "engineer"
    specialization: Optional[str] = None

class UserBase(BaseModel):
    employee_id: str
    name: str
    role: str
    specialization: Optional[str] = None
    department: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    employee_id: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    employee_id: str

class EquipmentBase(BaseModel):
    equipment_name: str
    equipment_id_code: str
    category: Optional[str] = None
    block: Optional[str] = None
    floor: Optional[str] = None
    health_status: str

class EquipmentResponse(EquipmentBase):
    id: int
    health_score: int
    model_config = ConfigDict(from_attributes=True)

class SessionCreate(BaseModel):
    equipment_id: int
    task_domain: Optional[str] = None

class SessionAssistCreate(BaseModel):
    target_employee_id: str
    equipment_id: int
    task_domain: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    primary_engineer_id: int
    status: str
    equipment_id: Optional[int] = None
    started_at: datetime
    loto_confirmed: bool
    safety_verified: bool
    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str
    sender_type: str = "user"

class MessageResponse(BaseModel):
    id: int
    session_id: str
    sender: str
    content: str
    message_type: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: int
    equipment_id: Optional[int] = None
    message: str
    severity: Optional[str] = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class InstructionAcknowledgeRequest(BaseModel):
    instruction_summary: str
    status: str # "yes" or "no"
    signature: Optional[str] = None

# ==========================================
# AGENT SCHEMAS
# ==========================================

class SandboxSessionBase(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = "Active"

class SandboxSessionCreate(SandboxSessionBase):
    pass

class SandboxSessionResponse(SandboxSessionBase):
    session_id: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SandboxMessageBase(BaseModel):
    sender: str
    content: str

class SandboxMessageCreate(SandboxMessageBase):
    session_id: str

class SandboxMessageResponse(SandboxMessageBase):
    id: int
    session_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EngineeringSessionBase(BaseModel):
    equipment_id: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = "Active"

class EngineeringSessionCreate(EngineeringSessionBase):
    pass

class EngineeringSessionResponse(EngineeringSessionBase):
    session_id: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EngineeringMessageBase(BaseModel):
    sender: str
    content: str

class EngineeringMessageCreate(EngineeringMessageBase):
    session_id: str

class EngineeringMessageResponse(EngineeringMessageBase):
    id: int
    session_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EscalationRequest(BaseModel):
    sandbox_session_id: str

class EscalationResponse(BaseModel):
    id: int
    sandbox_session_id: str
    engineering_session_id: str
    escalated_by: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class AgentFeedbackCreate(BaseModel):
    agent_type: str
    session_id: str
    rating: int
    feedback: Optional[str] = None

class AgentFeedbackResponse(AgentFeedbackCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ContinuousLearningCreate(BaseModel):
    equipment_id: str
    issue_description: str
    recommendation: str
    actual_resolution: Optional[str] = None
    supervisor_feedback: Optional[str] = None
    outcome_score: Optional[float] = None

class ContinuousLearningResponse(ContinuousLearningCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
