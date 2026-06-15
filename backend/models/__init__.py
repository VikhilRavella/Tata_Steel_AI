import datetime
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from backend.database import Base

import datetime
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=False) # 'ENGINEER' | 'SUPERVISOR' | 'MANAGER'
    specialization = Column(String) 
    certifications = Column(Text) # JSON array
    department = Column(String)
    supervisor_id = Column(Integer, ForeignKey("users.id"))
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    skills = Column(Text, nullable=True)
    profile_image = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    supervisor = relationship("User", remote_side=[id])

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    email_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class MaintenanceOutcome(Base):
    __tablename__ = "maintenance_outcomes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=False)
    engineer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    root_cause = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)
    outcome_status = Column(String, nullable=False)
    risk_level = Column(String, nullable=True)
    priority_level = Column(String, nullable=True)
    downtime_avoided = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ShiftRoster(Base):
    __tablename__ = "shift_roster"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_date = Column(DateTime, nullable=False)
    shift_type = Column(String, nullable=False) # 'Morning', 'Evening', 'Night'
    is_present = Column(Boolean, default=False)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    primary_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assisting_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    device_owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    task_domain = Column(String)
    worker_domain = Column(String)
    cross_domain_flag = Column(Boolean, default=False)
    safety_verified = Column(Boolean, default=False)
    loto_confirmed = Column(Boolean, default=False)
    risk_assessment_done = Column(Boolean, default=False)
    work_permit_number = Column(String)
    digital_signature = Column(String)
    block = Column(String)
    floor = Column(String)
    status = Column(String, default='active')
    escalated_to = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime)
    handover_note = Column(Text)
    session_summary = Column(Text)
    mttr_estimate_hours = Column(Float, nullable=True)
    waiver_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default='text')
    source_citations = Column(Text) # JSON array
    step_number = Column(Integer)
    step_confirmed = Column(Boolean, default=False)
    step_confirmed_at = Column(DateTime)
    image_path = Column(String)
    image_analysis = Column(Text) # JSON from LLaVA
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SessionContext(Base):
    __tablename__ = "session_context"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    context_key = Column(String, nullable=False)
    context_value = Column(Text, nullable=False)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)
    source = Column(String)

class SafetyChecklist(Base):
    __tablename__ = "safety_checklist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    item_name = Column(String, nullable=False)
    required = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    verification_method = Column(String)
    image_path = Column(String)
    verified_at = Column(DateTime)
    notes = Column(Text)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    department = Column(String)
    document_category = Column(String)
    assigned_roles = Column(Text) # JSON array
    stamp_verified = Column(Boolean, default=False)
    stamp_check_results = Column(Text) # JSON array
    processing_status = Column(String, default='pending')
    chroma_collection = Column(String)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_name = Column(String, nullable=False)
    equipment_id_code = Column(String, unique=True)
    category = Column(String)
    block = Column(String)
    floor = Column(String)
    line = Column(String)
    serial_number = Column(String)
    manufacturer = Column(String)
    installation_date = Column(DateTime)
    last_maintenance_date = Column(DateTime)
    health_status = Column(String, default='normal')
    health_score = Column(Integer, default=100)
    notes = Column(Text)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    alert_type = Column(String)
    severity = Column(String)
    message = Column(Text, nullable=False)
    error_code = Column(String)
    sensor_value = Column(String)
    threshold_value = Column(String)
    triggered_by = Column(String)
    status = Column(String, default='active')
    assigned_to = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, ForeignKey("sessions.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime)
    confidence_score = Column(Float, nullable=True)
    ai_diagnosis_summary = Column(Text, nullable=True)

class SparePart(Base):
    __tablename__ = "spare_parts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_name = Column(String, nullable=False)
    part_number = Column(String, unique=True)
    equipment_category = Column(String)
    bin_location = Column(String)
    quantity_in_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=2)
    unit_cost = Column(Float)
    procurement_lead_days = Column(Integer)
    supplier_name = Column(String)
    last_updated = Column(DateTime)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    related_session_id = Column(String)
    related_equipment_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(String)
    details = Column(Text) # JSON
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# DEPRECATED: This model is superseded by UserRating.
# Do not use Feedback for new code. Use models.UserRating instead.
# Kept for backward compatibility with existing database rows only.
class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)
    feedback_type = Column(String)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InstructionAcknowledgment(Base):
    __tablename__ = "instruction_acknowledgments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instruction_summary = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    signature = Column(String)
    clarification_requested = Column(Boolean, default=False)
    image_proof_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# class SandboxSession(Base):
#     __tablename__ = "sandbox_sessions"
#     id = Column(String, primary_key=True, default=generate_uuid)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     selected_model = Column(String, default="mistral")
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     is_escalated = Column(Boolean, default=False)


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    category = Column(String)
    chunk_count = Column(Integer)
    embedding_status = Column(String) # pending, complete, failed
    file_size = Column(Integer)

# class AgentMemory(Base):
#     __tablename__ = "agent_memory"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
#     session_id = Column(String, ForeignKey("sessions.id"))
#     memory_type = Column(String) # project_goal, project_constraint, architecture_decision, completed_task, pending_task, user_preference, technical_requirement, business_requirement
#     content = Column(Text)
#     importance_score = Column(Integer, default=1)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class RequirementProfile(Base):
    __tablename__ = "requirement_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    project_name = Column(String)
    problem_statement = Column(Text)
    business_goal = Column(Text)
    expected_outcome = Column(Text)
    tech_stack = Column(Text)
    constraints = Column(Text)
    timeline = Column(String)
    status = Column(String, default="gathering") # gathering, complete
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# class AgentTransfer(Base):
#     __tablename__ = "agent_transfers"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     sandbox_session_id = Column(String, ForeignKey("sandbox_sessions.id"))
#     engineer_session_id = Column(String, ForeignKey("sessions.id"))
#     transfer_summary = Column(Text) # JSON: Project Objective, User Requirements, Uploaded Documents, Key Discussions, Constraints, Next Steps, Open Questions, Satisfaction Score
# 
# class UserRating(Base):
#     __tablename__ = "user_ratings"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     session_id = Column(String)
#     message_id = Column(Integer, ForeignKey("messages.id"))
#     satisfaction_score = Column(Integer)
#     response_quality_score = Column(Integer)
#     retrieval_quality_score = Column(Integer)
#     agent_type = Column(String) # sandbox, engineering
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority = Column(String, default="Medium")  # Low, Medium, High, Critical
    status = Column(String, default="Open")      # Open, In Progress, Blocked, Completed
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    related_alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class EngineeringReport(Base):
    __tablename__ = "engineering_reports"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    title = Column(String, nullable=False)
    report_type = Column(String, default="Root Cause Analysis")
    report_content = Column(String, nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InventoryMaster(Base):
    __tablename__ = "inventory_master"
    part_number = Column(String, primary_key=True)
    part_name = Column(String, nullable=False)
    part_category = Column(String)
    stock_qty = Column(Integer, default=0)
    minimum_stock = Column(Integer, default=0)
    warehouse = Column(String)
    block = Column(String)
    rack = Column(String)
    bin = Column(String)
    supplier = Column(String)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    transaction_id = Column(String, primary_key=True, default=generate_uuid)
    part_number = Column(String, ForeignKey("inventory_master.part_number"), nullable=False)
    part_name = Column(String, nullable=False)
    equipment_id = Column(String)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    transaction_type = Column(String, nullable=False) # ISSUE, RETURN, ADJUSTMENT, PENDING, APPROVED, REJECTED
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

class EquipmentMaster(Base):
    __tablename__ = "equipment_master"
    equipment_id = Column(String, primary_key=True)
    equipment_name = Column(String, nullable=False)
    equipment_type = Column(String)
    location = Column(String)
    plant = Column(String)
    block = Column(String)
    area = Column(String)
    status = Column(String, default='active')
    criticality = Column(String)
    manufacturer = Column(String)
    model_number = Column(String)
    install_date = Column(DateTime)
    assigned_supervisor = Column(String, ForeignKey("supervisor_directory.supervisor_id"), nullable=True)

class PartRequest(Base):
    __tablename__ = "part_requests"
    request_id = Column(String, primary_key=True, default=generate_uuid)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=True)
    part_number = Column(String, ForeignKey("inventory_master.part_number"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text)
    priority = Column(String, default="Medium")
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED, ISSUED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
class SupervisorDirectory(Base):
    __tablename__ = "supervisor_directory"
    supervisor_id = Column(String, primary_key=True, default=generate_uuid)
    employee_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    department = Column(String)
    plant = Column(String)
    block = Column(String)
    status = Column(String, default="active")

class EquipmentParts(Base):
    __tablename__ = "equipment_parts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=False)
    part_number = Column(String, ForeignKey("inventory_master.part_number"), nullable=False)
    quantity_required = Column(Integer, default=1)
    critical_part = Column(Boolean, default=False)

class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=False)
    maintenance_date = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="Completed")

# ==========================================
# AGENT ARCHITECTURE
# ==========================================

class SandboxSession(Base):
    __tablename__ = "sandbox_sessions"
    session_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class SandboxMessage(Base):
    __tablename__ = "sandbox_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sandbox_sessions.session_id"), nullable=False)
    sender = Column(String, nullable=False) # 'user' or 'agent'
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text") # 'text' or 'voice'
    detected_language = Column(String, nullable=True) # e.g., 'te', 'hi', 'en'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SandboxMemory(Base):
    __tablename__ = "sandbox_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sandbox_sessions.session_id"), nullable=False)
    memory_type = Column(String, nullable=False) # e.g., Requirements, Architecture
    memory_key = Column(String, nullable=False)
    memory_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class EngineeringSession(Base):
    __tablename__ = "engineering_sessions"
    session_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=True)
    title = Column(String, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class EngineeringFile(Base):
    __tablename__ = "engineering_files"
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("engineering_sessions.session_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class EngineeringMessage(Base):
    __tablename__ = "engineering_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("engineering_sessions.session_id"), nullable=False)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text") # 'text' or 'voice'
    detected_language = Column(String, nullable=True) # e.g., 'te', 'hi', 'en'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class EngineeringMemory(Base):
    __tablename__ = "engineering_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("engineering_sessions.session_id"), nullable=False)
    memory_type = Column(String, nullable=False) # e.g., Defect, RootCause
    memory_key = Column(String, nullable=False)
    memory_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class EscalationHistory(Base):
    __tablename__ = "escalation_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sandbox_session_id = Column(String, ForeignKey("sandbox_sessions.session_id"), nullable=False)
    engineering_session_id = Column(String, ForeignKey("engineering_sessions.session_id"), nullable=False)
    escalated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    escalated_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Pending")

class EscalationContext(Base):
    __tablename__ = "escalation_context"
    id = Column(Integer, primary_key=True, autoincrement=True)
    escalation_id = Column(Integer, ForeignKey("escalation_history.id"), nullable=False)
    context_type = Column(String, nullable=False)
    context_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AgentFeedback(Base):
    __tablename__ = "agent_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_type = Column(String, nullable=False) # 'Sandbox' or 'Engineering'
    session_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False) # 1 to 5
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ContinuousLearning(Base):
    __tablename__ = "continuous_learning"
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String, ForeignKey("equipment_master.equipment_id"), nullable=False)
    issue_description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    actual_resolution = Column(Text, nullable=True)
    supervisor_feedback = Column(Text, nullable=True)
    outcome_score = Column(Float, nullable=True) # E.g., 0.0 to 1.0
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CompanyDocument(Base):
    __tablename__ = 'company_documents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default='Pending') # Pending, Approved, Rejected
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
