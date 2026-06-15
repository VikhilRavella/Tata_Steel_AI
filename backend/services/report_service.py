import asyncio
from sqlalchemy.orm import Session
import backend.models as models
from backend.services.ollama_service import generate_completion_sync

def generate_report(session_id: str, title: str, report_type: str, user_id: int, db: Session) -> models.EngineeringReport:
    # 1. Load chat history
    messages = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at.asc()).all()
    chat_log = "\n".join([f"{m.sender}: {m.content}" for m in messages])
    
    # 2. Load memory context
    memory_items = db.query(models.Memory).filter(models.Memory.user_id == user_id).all()
    memory_log = "\n".join([f"- {m.key}: {m.value}" for m in memory_items])
    
    # 3. Load requirement profile
    profile = db.query(models.RequirementProfile).filter(models.RequirementProfile.session_id == session_id).first()
    profile_log = f"Goal: {profile.business_goal}\nConstraints: {profile.constraints}" if profile else "No profile found."
    
    # 4. Extract Vision findings
    vision_findings = [m.image_analysis for m in messages if m.image_analysis]
    vision_log = "\n".join(vision_findings) if vision_findings else "No images analyzed."
    
    # Compile prompt to LLM to summarize into a report
    prompt = f"""
You are the Lead Engineer generating a formal {report_type} report.
Based on the following data, generate a comprehensive Markdown report.
Ensure it contains exactly these sections:
## Executive Summary
## Problem Statement
## Root Cause Analysis
## Safety Findings
## Inventory & Vision Findings
## Recommendations
## Work Orders Generated

DATA CONTEXT:
[REQUIREMENT PROFILE]
{profile_log}

[MEMORY]
{memory_log}

[VISION ANALYSIS]
{vision_log}

[CHAT HISTORY]
{chat_log[-3000:]}

Generate the Markdown report now:
"""
    report_content = generate_completion_sync(prompt, model="qwen2.5-coder:7b")
    
    db_report = models.EngineeringReport(
        session_id=session_id,
        title=title,
        report_type=report_type,
        report_content=report_content,
        generated_by=user_id
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    try:
        from backend.services.email_service import notify_engineering_report_generated
        notify_engineering_report_generated(db, db_report.id)
    except Exception as e:
        pass
        
    return db_report
