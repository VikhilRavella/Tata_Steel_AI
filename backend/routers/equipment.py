from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import EquipmentMaster, AuditLog, User
from typing import List, Optional
import csv
import io
import datetime

router = APIRouter(prefix="/equipment", tags=["Equipment"])

@router.post("/upload")
async def upload_equipment_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Must be a CSV file")
    
    contents = await file.read()
    decoded = contents.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    updated = 0
    inserted = 0
    
    for row in reader:
        eq_id = row.get('equipment_id')
        if not eq_id:
            continue
            
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == eq_id).first()
        if eq:
            for key, value in row.items():
                if hasattr(eq, key) and value:
                    setattr(eq, key, value)
            updated += 1
        else:
            new_eq = EquipmentMaster(**{k: v for k, v in row.items() if hasattr(EquipmentMaster, k) and v})
            db.add(new_eq)
            inserted += 1
            
    db.commit()
    return {"message": "Upload successful", "inserted": inserted, "updated": updated}

@router.get("/search")
def search_equipment(equipment_name: Optional[str] = None, equipment_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(EquipmentMaster)
    if equipment_name:
        query = query.filter(EquipmentMaster.equipment_name.ilike(f"%{equipment_name}%"))
    if equipment_id:
        query = query.filter(EquipmentMaster.equipment_id.ilike(f"%{equipment_id}%"))
    return query.all()
