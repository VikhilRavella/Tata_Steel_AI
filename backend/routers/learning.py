from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from backend.database import get_db
import backend.models as models
import backend.schemas as schemas

router = APIRouter(prefix="/api/learning", tags=["Learning"])

@router.post("/feedback", response_model=schemas.AgentFeedbackResponse)
def submit_agent_feedback(
    feedback: schemas.AgentFeedbackCreate,
    db: Session = Depends(get_db)
):
    new_feedback = models.AgentFeedback(
        agent_type=feedback.agent_type,
        session_id=feedback.session_id,
        rating=feedback.rating,
        feedback=feedback.feedback,
        created_at=datetime.utcnow()
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return new_feedback

@router.get("/history", response_model=List[schemas.ContinuousLearningResponse])
def get_continuous_learning_history(
    db: Session = Depends(get_db)
):
    learning_records = db.query(models.ContinuousLearning).order_by(models.ContinuousLearning.created_at.desc()).all()
    return learning_records

@router.post("/capture", response_model=schemas.ContinuousLearningResponse)
def capture_continuous_learning(
    learning: schemas.ContinuousLearningCreate,
    db: Session = Depends(get_db)
):
    new_learning = models.ContinuousLearning(
        equipment_id=learning.equipment_id,
        issue_description=learning.issue_description,
        recommendation=learning.recommendation,
        actual_resolution=learning.actual_resolution,
        supervisor_feedback=learning.supervisor_feedback,
        outcome_score=learning.outcome_score,
        created_at=datetime.utcnow()
    )
    db.add(new_learning)
    db.commit()
    db.refresh(new_learning)
    return new_learning
