"""
FastAPI Router for Text Correction endpoint.
POST /api/text-correction
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TextCorrectionRequest(BaseModel):
    text: str


class TextCorrectionResponse(BaseModel):
    original: str
    corrected: str


@router.post("/text-correction", response_model=TextCorrectionResponse)
def text_correction(request: TextCorrectionRequest):
    """
    Correct grammar and spelling using the local T5 model.
    No Gemini API calls are made.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    from backend.services.text_correction_service import correct_text, get_model_status

    status = get_model_status()
    if not status["loaded"]:
        raise HTTPException(
            status_code=503,
            detail=f"Text correction model is not loaded. Error: {status['error']}"
        )

    corrected = correct_text(request.text)

    return TextCorrectionResponse(original=request.text, corrected=corrected)


@router.get("/text-correction/status")
def text_correction_status():
    """Check if the text correction model is loaded and ready."""
    from backend.services.text_correction_service import get_model_status
    return get_model_status()
