from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.routers.auth import get_current_active_user
from backend.models import InventoryMaster, InventoryTransaction, PartRequest, AuditLog, Alert, User
from pydantic import BaseModel
from typing import List, Optional
import csv
import io
import datetime
import uuid

router = APIRouter(prefix="/inventory", tags=["Inventory"])

class PartRequestCreate(BaseModel):
    requested_by: int
    equipment_id: Optional[str] = None
    part_number: str
    quantity: int
    reason: Optional[str] = None
    priority: str = "Medium"

class PartRequestApprove(BaseModel):
    transaction_id: str
    approved_by: int
    action: str = "approve"  # "approve" or "reject"
    rejection_reason: Optional[str] = None

class InventoryIssue(BaseModel):
    part_number: str
    quantity: int
    equipment_id: Optional[str] = None
    requested_by: int
    approved_by: int

class InventoryReturn(BaseModel):
    part_number: str
    quantity: int
    returned_by: int
    approved_by: int

@router.post("/upload")
async def upload_inventory_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Must be a CSV file")
    
    contents = await file.read()
    decoded = contents.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    updated = 0
    inserted = 0
    
    for row in reader:
        part_no = row.get('part_number')
        if not part_no:
            continue
            
        part = db.query(InventoryMaster).filter(InventoryMaster.part_number == part_no).first()
        if part:
            for key, value in row.items():
                if hasattr(part, key) and value:
                    if key in ['stock_qty', 'minimum_stock'] and value:
                        setattr(part, key, int(value))
                    else:
                        setattr(part, key, value)
            updated += 1
        else:
            data = {k: v for k, v in row.items() if hasattr(InventoryMaster, k) and v}
            if 'stock_qty' in data: data['stock_qty'] = int(data['stock_qty'])
            if 'minimum_stock' in data: data['minimum_stock'] = int(data['minimum_stock'])
            new_part = InventoryMaster(**data)
            db.add(new_part)
            inserted += 1
            
    db.commit()
    return {"message": "Upload successful", "inserted": inserted, "updated": updated}

from sqlalchemy import or_

@router.get("/search")
def search_inventory(q: Optional[str] = None, part_name: Optional[str] = None, part_number: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(InventoryMaster)
    if q:
        query = query.filter(or_(InventoryMaster.part_name.ilike(f"%{q}%"), InventoryMaster.part_number.ilike(f"%{q}%")))
    else:
        if part_name:
            query = query.filter(InventoryMaster.part_name.ilike(f"%{part_name}%"))
        if part_number:
            query = query.filter(InventoryMaster.part_number.ilike(f"%{part_number}%"))
    return query.all()

@router.post("/part-request/create")
def create_part_request(req: PartRequestCreate, db: Session = Depends(get_db)):
    from backend.services.inventory_service import request_part
    try:
        msg = request_part(db, req.requested_by, req.part_number, req.quantity, "")
        # Return success with a dummy object matching the old PartRequest schema superficially if needed,
        # but the UI expects 'request_id' probably. We will just return what the UI expects but mapped from the transaction.
        from backend.models import InventoryTransaction
        # Get the newly created transaction
        txn = db.query(InventoryTransaction).filter(
            InventoryTransaction.requested_by == req.requested_by,
            InventoryTransaction.part_number == req.part_number
        ).order_by(InventoryTransaction.timestamp.desc()).first()
        return {
            "request_id": txn.transaction_id,  # Mapping transaction_id to request_id for legacy UI compatibility
            "part_number": txn.part_number,
            "quantity": txn.quantity,
            "requested_by": txn.requested_by,
            "status": txn.transaction_type,
            "message": msg
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/part-request/approve")
def approve_part_request(req: PartRequestApprove, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    from backend.services.inventory_service import approve_issue, reject_issue
    try:
        user_id = current_user.id
        if req.action.lower() == "reject":
            msg = reject_issue(db, user_id, req.transaction_id, req.rejection_reason)
        else:
            msg = approve_issue(db, user_id, req.transaction_id)
            
        from backend.models import InventoryTransaction
        txn = db.query(InventoryTransaction).filter(InventoryTransaction.transaction_id == req.transaction_id).first()
        return {"transaction_id": txn.transaction_id, "status": txn.transaction_type, "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/issue")
def issue_inventory(req: InventoryIssue, db: Session = Depends(get_db)):
    part = db.query(InventoryMaster).filter(InventoryMaster.part_number == req.part_number).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    if part.stock_qty < req.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
        
    part.stock_qty -= req.quantity
    
    txn = InventoryTransaction(
        transaction_id=str(uuid.uuid4()),
        part_number=req.part_number,
        part_name=part.part_name,
        equipment_id=req.equipment_id,
        requested_by=req.requested_by,
        approved_by=req.approved_by,
        quantity=req.quantity,
        transaction_type="ISSUE"
    )
    db.add(txn)
    
    audit = AuditLog(
        user_id=req.approved_by,
        action="ISSUE_INVENTORY",
        entity_type="INVENTORY",
        entity_id=part.part_number,
        details=f"Issued {req.quantity} of {part.part_number}"
    )
    db.add(audit)
    
    if part.stock_qty <= part.minimum_stock:
        alert = Alert(
            alert_type="LOW_STOCK",
            severity="High",
            message=f"LOW STOCK: {part.part_name} has {part.stock_qty} left.",
            status="active"
        )
        db.add(alert)
        
    db.commit()
    return {"message": "Issued successfully", "transaction_id": txn.transaction_id, "remaining_stock": part.stock_qty}

@router.post("/return")
def return_inventory(req: InventoryReturn, db: Session = Depends(get_db)):
    part = db.query(InventoryMaster).filter(InventoryMaster.part_number == req.part_number).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    part.stock_qty += req.quantity
    
    txn = InventoryTransaction(
        transaction_id=str(uuid.uuid4()),
        part_number=req.part_number,
        part_name=part.part_name,
        requested_by=req.returned_by,
        approved_by=req.approved_by,
        quantity=req.quantity,
        transaction_type="RETURN"
    )
    db.add(txn)
    
    audit = AuditLog(
        user_id=req.approved_by,
        action="RETURN_INVENTORY",
        entity_type="INVENTORY",
        entity_id=part.part_number,
        details=f"Returned {req.quantity} of {part.part_number}"
    )
    db.add(audit)
    db.commit()
    return {"message": "Returned successfully", "transaction_id": txn.transaction_id, "new_stock": part.stock_qty}

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()