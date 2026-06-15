from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime

from backend.database import get_db
from backend.models import User, CompanyDocument
from backend.routers.auth import get_current_active_user
from backend.services.document_service import embed_company_document, remove_company_document_embeddings

router = APIRouter(
    tags=["company-documents"]
)

# Upload directory
UPLOAD_DIR = "backend/storage/company_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def ensure_manager(current_user: User = Depends(get_current_active_user)):
    if (current_user.role or '').lower() != 'manager':
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user

# 1. Manager: Upload Document
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_manager)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    file_path = os.path.join(UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc = CompanyDocument(
        filename=file.filename,
        file_path=file_path,
        uploaded_by=current_user.id,
        status="Pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Generate RAG Embeddings in Background/Async
    await embed_company_document(file_path, file.filename, doc.id)
    
    return {"id": doc.id, "filename": doc.filename, "status": doc.status}

# 2. Manager: Get all documents
@router.get("")
def get_all_documents(db: Session = Depends(get_db), current_user: User = Depends(ensure_manager)):
    docs = db.query(CompanyDocument).order_by(CompanyDocument.upload_date.desc()).all()
    res = []
    for d in docs:
        uploader = db.query(User).filter(User.id == d.uploaded_by).first()
        res.append({
            "id": d.id,
            "filename": d.filename,
            "upload_date": d.upload_date.isoformat() if d.upload_date else None,
            "uploader": uploader.name if uploader else "Unknown",
            "status": d.status
        })
    return res

# 3. Manager: Update Status
@router.put("/{doc_id}/status")
def update_document_status(
    doc_id: int, 
    status: str = Form(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(ensure_manager)
):
    if status not in ["Pending", "Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    doc = db.query(CompanyDocument).filter(CompanyDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc.status = status
    db.commit()
    return {"id": doc.id, "status": doc.status}

# 4. Manager: Delete Document
@router.delete("/{doc_id}")
async def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(ensure_manager)):
    doc = db.query(CompanyDocument).filter(CompanyDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        
    db.delete(doc)
    db.commit()
    
    # Remove RAG Embeddings
    await remove_company_document_embeddings(doc_id)
    
    return {"detail": "Document deleted"}

# 4b. Manager: Replace Document
@router.put("/replace/{doc_id}")
async def replace_document(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_manager)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    doc = db.query(CompanyDocument).filter(CompanyDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        
    # Remove old embeddings
    await remove_company_document_embeddings(doc_id)
    
    file_path = os.path.join(UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc.filename = file.filename
    doc.file_path = file_path
    doc.status = "Pending"
    doc.uploaded_by = current_user.id
    db.commit()
    
    # Generate new embeddings
    await embed_company_document(file_path, file.filename, doc.id)
    
    return {"id": doc.id, "filename": doc.filename, "status": doc.status}

# 5. Any Authenticated Employee: Get Approved Documents
@router.get("/approved")
def get_approved_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    docs = db.query(CompanyDocument).filter(CompanyDocument.status == "Approved").order_by(CompanyDocument.upload_date.desc()).all()
    return [{"id": d.id, "filename": d.filename, "upload_date": d.upload_date.isoformat() if d.upload_date else None, "file_path": d.file_path} for d in docs]
