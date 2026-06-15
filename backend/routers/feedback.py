from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import get_db
import backend.models as models
from backend.routers.auth import get_current_active_user
router = APIRouter()

class RatingRequest(BaseModel):
    session_id: str
    message_id: int
    satisfaction_score: int
    response_quality_score: int
    retrieval_quality_score: int
    agent_type: str

@router.post('/rate')
def submit_rating(request: RatingRequest, db: Session=Depends(get_db), current_user: models.User=Depends(get_current_active_user)):
    rating = models.UserRating(session_id=request.session_id, message_id=request.message_id, satisfaction_score=request.satisfaction_score, response_quality_score=request.response_quality_score, retrieval_quality_score=request.retrieval_quality_score, agent_type=request.agent_type)
    db.add(rating)
    db.commit()
    return {'status': 'success', 'message': 'Rating submitted successfully'}