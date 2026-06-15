from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Document
from backend.services.document_service import process_document
from backend.routers.auth import get_current_active_user
from backend.services.audit_service import log_action
import os
import json
router = APIRouter()
STORAGE_DIR = 'backend/storage/documents'
os.makedirs(STORAGE_DIR, exist_ok=True)

@router.post('/upload')
async def upload_document(file: UploadFile=File(...), db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if not file.filename.endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail='Only PDF and DOCX files are allowed.')
    file_path = os.path.join(STORAGE_DIR, file.filename)
    with open(file_path, 'wb') as buffer:
        buffer.write(await file.read())
    try:
        is_verified = process_document(file_path, file.filename, current_user, db)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        log_action(db, current_user.id, 'doc_upload_failed', 'document', file.filename, {'error': str(e)})
        raise HTTPException(status_code=500, detail=f'Processing failed: {str(e)}')
    if not is_verified:
        if os.path.exists(file_path):
            os.remove(file_path)
        log_action(db, current_user.id, 'doc_upload_rejected', 'document', file.filename, {'reason': 'Missing security stamp'})
        raise HTTPException(status_code=403, detail='Document rejected: Invalid security stamp.')
    log_action(db, current_user.id, 'doc_upload_success', 'document', file.filename)
    return {'status': 'success', 'message': 'Document uploaded, chunked, and stored successfully.'}

@router.get('/')
def get_documents(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    all_docs = (db.execute(select(Document))).scalars().order_by(Document.uploaded_at.desc()).all()
    if current_user.role == 'manager':
        filtered_docs = all_docs
    elif current_user.role == 'supervisor':
        filtered_docs = all_docs
    else:
        filtered_docs = []
        for doc in all_docs:
            if doc.uploaded_by == current_user.id:
                filtered_docs.append(doc)
                continue
            if doc.assigned_roles:
                try:
                    roles = json.loads(doc.assigned_roles)
                    spec = current_user.specialization.lower() if current_user.specialization else ''
                    if 'all' in roles or 'engineer' in roles or spec in roles:
                        filtered_docs.append(doc)
                except:
                    pass
    result = []
    for d in filtered_docs:
        uploader = db.query(User).filter(User.id == d.uploaded_by).first()
        result.append({'id': d.id, 'filename': d.original_filename, 'category': d.document_category, 'uploaded_by_name': uploader.name if uploader else 'Unknown', 'uploaded_at': d.uploaded_at, 'assigned_roles': d.assigned_roles})
    return result

@router.get('/team')
def get_team_documents(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can access team documents.')
    all_docs = (db.execute(select(Document))).scalars().order_by(Document.uploaded_at.desc()).all()
    filtered_docs = []
    managed_users = db.query(User).filter(User.supervisor_id == current_user.id).all()
    managed_roles = set([u.role for u in managed_users] + [u.specialization.lower() for u in managed_users if u.specialization])
    managed_roles.add('engineer')
    for doc in all_docs:
        if doc.uploaded_by == current_user.id:
            filtered_docs.append(doc)
            continue
        if doc.assigned_roles:
            try:
                roles = json.loads(doc.assigned_roles)
                if 'all' in roles or any((r in managed_roles for r in roles)):
                    filtered_docs.append(doc)
            except:
                pass
    result = []
    for d in filtered_docs:
        uploader = db.query(User).filter(User.id == d.uploaded_by).first()
        result.append({'id': d.id, 'document_name': d.original_filename, 'filename': d.original_filename, 'category': d.document_category, 'uploaded_by_name': uploader.name if uploader else 'Unknown', 'uploaded_at': d.uploaded_at, 'assigned_roles': d.assigned_roles})
    return result