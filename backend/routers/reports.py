from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
import backend.models as models
from backend.routers.auth import get_current_active_user
from backend.services.report_service import generate_report

router = APIRouter()

class ReportGenerateRequest(BaseModel):
    session_id: str
    title: str
    report_type: str = "Root Cause Analysis"

class ReportResponse(BaseModel):
    id: int
    session_id: str
    title: str
    report_type: str
    report_content: str
    generated_by: int
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("/generate", response_model=ReportResponse)
def api_generate_report(req: ReportGenerateRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Note: generate_report is currently sync
    try:
        db_report = generate_report(req.session_id, req.title, req.report_type, current_user.id, db)
        return db_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_rep = db.query(models.EngineeringReport).filter(models.EngineeringReport.id == report_id).first()
    if not db_rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return db_rep

@router.get("/session/{session_id}", response_model=List[ReportResponse])
def get_session_reports(session_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    return db.query(models.EngineeringReport).filter(models.EngineeringReport.session_id == session_id).order_by(models.EngineeringReport.created_at.desc()).all()
