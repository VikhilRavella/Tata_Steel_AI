from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
import csv
import io
import datetime
import uuid

from backend.database import get_db
from backend.models import (
    User, SupervisorDirectory, EquipmentMaster, InventoryMaster, 
    EquipmentParts, WorkOrder, MaintenanceHistory, AuditLog, InventoryTransaction
)
from backend.routers.auth import RoleChecker, get_current_active_user
import bcrypt

router = APIRouter(prefix="/manager_portal", tags=["Manager Portal"])
allow_manager = RoleChecker(['manager'])

def create_audit(db, current_user, action, entity_type, entity_id, details):
    audit = AuditLog(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    db.add(audit)
    db.commit()

@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    return {
        "engineers": db.query(User).filter(User.role == 'ENGINEER').count(),
        "supervisors": db.query(SupervisorDirectory).count(),
        "equipment": db.query(EquipmentMaster).count(),
        "inventory": db.query(InventoryMaster).count(),
        "running_equipment": db.query(EquipmentMaster).filter(EquipmentMaster.status == 'active').count(),
        "maintenance_equipment": db.query(EquipmentMaster).filter(EquipmentMaster.status == 'maintenance').count(),
        "open_work_orders": db.query(WorkOrder).filter(WorkOrder.status == 'Open').count(),
        "low_stock": db.query(InventoryMaster).filter(InventoryMaster.stock_qty <= InventoryMaster.minimum_stock).count()
    }

# --- ENGINEERS ---
@router.get("/engineers")
def get_engineers(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    engineers = db.query(User).filter(func.upper(User.role) == 'ENGINEER').all()
    res = []
    for eng in engineers:
        sup_name = "Unassigned"
        if eng.supervisor_id:
            sup = db.query(User).filter(User.id == eng.supervisor_id).first()
            if sup: sup_name = sup.name
        res.append({
            "id": eng.id, "employee_id": eng.employee_id, "name": eng.name,
            "department": eng.department, "role": eng.role,
            "assigned_supervisor": sup_name, "phone": eng.phone,
            "email": eng.email, "status": "Active" if eng.is_active else "Inactive"
        })
    return res

@router.post("/engineers/upload")
async def upload_engineers(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    for raw_row in reader:
        try:
            # Normalize keys to lowercase and strip whitespace
            row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items() if k is not None}
            
            # Force role to be uppercase if provided
            if 'role' in row and row['role']:
                row['role'] = row['role'].upper()
            
            emp_id = row.get('employee_id')
            if not emp_id:
                stats["failed"] += 1
                stats["errors"].append(f"Row missing 'employee_id': {row}")
                continue
                
            user = db.query(User).filter(User.employee_id == emp_id).first()
            if user:
                for k, v in row.items():
                    if hasattr(user, k) and v and k != 'password_hash': setattr(user, k, v)
                stats["updated"] += 1
            else:
                data = {k: v for k, v in row.items() if hasattr(User, k) and v}
                if 'password_hash' not in data: data['password_hash'] = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                new_user = User(**data)
                db.add(new_user)
                stats["inserted"] += 1
                
            # If role is SUPERVISOR, keep SupervisorDirectory in sync
            if row.get('role') == 'SUPERVISOR':
                sup = db.query(SupervisorDirectory).filter(SupervisorDirectory.employee_id == emp_id).first()
                if sup:
                    sup.name = row.get('name', sup.name)
                    sup.department = row.get('department', sup.department)
                    sup.email = row.get('email', sup.email)
                    sup.phone = row.get('phone', sup.phone)
                else:
                    new_sup = SupervisorDirectory(
                        employee_id=emp_id,
                        name=row.get('name', 'Unknown'),
                        department=row.get('department', 'Unknown'),
                        email=row.get('email', ''),
                        phone=row.get('phone', ''),
                        plant='JSR-01',
                        block='Primary',
                        status='Active'
                    )
                    db.add(new_sup)
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Row error: {str(e)}")
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "ENGINEERS", "users.csv", f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    return stats

@router.delete("/engineers/{id}")
def delete_engineer(id: int, db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    eng = db.query(User).filter(User.id == id).first()
    if not eng: raise HTTPException(status_code=404)
    # Safely clear work orders
    wos = db.query(WorkOrder).filter(WorkOrder.assigned_to == id).all()
    for wo in wos: wo.assigned_to = None
    db.delete(eng)
    db.commit()
    create_audit(db, current_user, "DELETE", "ENGINEER", str(id), f"Deleted engineer {eng.name}. Cleared {len(wos)} work orders.")
    return {"message": "Success"}

# --- SUPERVISORS ---
@router.get("/supervisors")
def get_supervisors(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    sups = db.query(SupervisorDirectory).all()
    res = []
    for sup in sups:
        user_sup = db.query(User).filter(User.employee_id == sup.employee_id).first()
        eng_count = db.query(User).filter(User.supervisor_id == user_sup.id).count() if user_sup else 0
        eq_count = db.query(EquipmentMaster).filter(EquipmentMaster.assigned_supervisor == sup.supervisor_id).count()
        res.append({
            "supervisor_id": sup.supervisor_id, "name": sup.name, "department": sup.department,
            "plant": sup.plant, "block": sup.block, "phone": sup.phone, "email": sup.email,
            "status": sup.status, "assigned_engineers": eng_count, "assigned_equipment": eq_count
        })
    return res

@router.post("/supervisors/upload")
async def upload_supervisors(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    for raw_row in reader:
        try:
            row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items() if k is not None}
            row['role'] = 'SUPERVISOR'
            
            emp_id = row.get('employee_id')
            if not emp_id:
                stats["failed"] += 1
                stats["errors"].append(f"Row missing 'employee_id': {row}")
                continue
                
            user = db.query(User).filter(User.employee_id == emp_id).first()
            if user:
                for k, v in row.items():
                    if hasattr(user, k) and v and k != 'password_hash': setattr(user, k, v)
                stats["updated"] += 1
            else:
                data = {k: v for k, v in row.items() if hasattr(User, k) and v}
                if 'password_hash' not in data: data['password_hash'] = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                new_user = User(**data)
                db.add(new_user)
                stats["inserted"] += 1
                
            sup = db.query(SupervisorDirectory).filter(SupervisorDirectory.employee_id == emp_id).first()
            if sup:
                sup.name = row.get('name', sup.name)
                sup.department = row.get('department', sup.department)
                sup.email = row.get('email', sup.email)
                sup.phone = row.get('phone', sup.phone)
            else:
                new_sup = SupervisorDirectory(
                    employee_id=emp_id,
                    name=row.get('name', 'Unknown'),
                    department=row.get('department', 'Unknown'),
                    email=row.get('email', ''),
                    phone=row.get('phone', ''),
                    plant='JSR-01',
                    block='Primary',
                    status='Active'
                )
                db.add(new_sup)
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Row error: {str(e)}")
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "SUPERVISORS", "supervisor_directory.csv", f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    return stats

@router.post("/supervisors/mapping/upload")
async def upload_supervisor_mapping(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    
    for raw_row in reader:
        try:
            row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items() if k is not None}
            sup_id = row.get('supervisor_id') or row.get('supervisor_employee_id') or row.get('supe_id')
            if not sup_id:
                stats["failed"] += 1
                stats["errors"].append(f"Missing supervisor_id in row: {row}")
                continue
                
            # Check if this is an Equipment Mapping
            eq_id = row.get('equipment_id') or row.get('eq_id')
            if eq_id:
                # Process Equipment Mapping
                eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == eq_id).first()
                sup_dir = db.query(SupervisorDirectory).filter((SupervisorDirectory.supervisor_id == sup_id) | (SupervisorDirectory.employee_id == sup_id)).first()
                
                if not eq or not sup_dir:
                    stats["failed"] += 1
                    stats["errors"].append(f"Invalid equipment_id {eq_id} or supervisor_id {sup_id}")
                    continue
                    
                eq.assigned_supervisor = sup_dir.supervisor_id
                stats["updated"] += 1
            else:
                # Process Engineer Mapping
                eng_id = row.get('engineer_user_id') or row.get('engineer_employee_id') or row.get('engineer_id') or row.get('empid')
                if not eng_id:
                    stats["failed"] += 1
                    stats["errors"].append(f"Missing eng_id or equipment_id in row: {row}")
                    continue
                
                eng = db.query(User).filter(User.employee_id == eng_id).first()
                sup = db.query(User).filter(User.employee_id == sup_id).first()
                if not eng or not sup:
                    stats["failed"] += 1
                    stats["errors"].append(f"User not found for {eng_id} or {sup_id}")
                    continue
                    
                eng.supervisor_id = sup.id
                stats["updated"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "SUPERVISOR_MAPPING", "supervisor_mapping.csv", f"Mappings updated: {stats['updated']}")
    return stats

@router.put("/supervisors/{id}")
async def update_supervisor(id: str, req: Request, db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    data = await req.json()
    sup = db.query(SupervisorDirectory).filter(SupervisorDirectory.supervisor_id == id).first()
    if not sup: raise HTTPException(status_code=404, detail="Supervisor not found")
    
    for field in ['name', 'department', 'plant', 'block', 'phone', 'email', 'status']:
        if field in data:
            setattr(sup, field, data[field])
            
    user = db.query(User).filter(User.employee_id == sup.employee_id).first()
    if user:
        if 'name' in data: user.name = data['name']
        if 'department' in data: user.department = data['department']
        if 'phone' in data: user.phone = data['phone']
        if 'email' in data: user.email = data['email']
        
    db.commit()
    create_audit(db, current_user, "UPDATE", "SUPERVISOR", id, f"Updated supervisor {sup.name}")
    return {"status": "success"}

@router.delete("/supervisors/{id}")
def delete_supervisor(id: str, db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    sup = db.query(SupervisorDirectory).filter(SupervisorDirectory.supervisor_id == id).first()
    if not sup: raise HTTPException(status_code=404)
    # Safely clear engineer mappings
    user_sup = db.query(User).filter(User.employee_id == sup.employee_id).first()
    if user_sup:
        engs = db.query(User).filter(User.supervisor_id == user_sup.id).all()
        for e in engs: e.supervisor_id = None
    # Safely clear equipment mappings
    eqs = db.query(EquipmentMaster).filter(EquipmentMaster.assigned_supervisor == id).all()
    for eq in eqs: eq.assigned_supervisor = None
    db.delete(sup)
    db.commit()
    create_audit(db, current_user, "DELETE", "SUPERVISOR", id, f"Deleted supervisor {sup.name}. Cleared mappings.")
    return {"message": "Success"}

# --- EQUIPMENT REGISTRY ---
@router.get("/equipment")
def get_equipment(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    eqs = db.query(EquipmentMaster).all()
    res = []
    for eq in eqs:
        sup_name = "Unassigned"
        if eq.assigned_supervisor:
            sup = db.query(SupervisorDirectory).filter(SupervisorDirectory.supervisor_id == eq.assigned_supervisor).first()
            if sup: sup_name = sup.name
        res.append({
            "equipment_id": eq.equipment_id, "equipment_name": eq.equipment_name,
            "equipment_type": eq.equipment_type, "location": eq.location, "plant": eq.plant, "block": eq.block,
            "area": eq.area, "status": eq.status, "criticality": eq.criticality,
            "manufacturer": eq.manufacturer, "model_number": eq.model_number,
            "assigned_supervisor": sup_name
        })
    return res

@router.post("/equipment/upload")
async def upload_equipment(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    
    for raw_row in reader:
        try:
            row = {str(k).strip().lower().replace(' ', '_'): str(v).strip() for k, v in raw_row.items() if k is not None}
            
            # Alias mapping
            if 'name' in row and 'equipment_name' not in row: row['equipment_name'] = row['name']
            if 'type' in row and 'equipment_type' not in row: row['equipment_type'] = row['type']
            if 'model' in row and 'model_number' not in row: row['model_number'] = row['model']
            if 'date' in row and 'install_date' not in row: row['install_date'] = row['date']
            
            eq_id = row.get('equipment_id') or row.get('id') or row.get('eq_id')
            if not eq_id:
                stats["failed"] += 1
                stats["errors"].append(f"Missing equipment_id in row: {row}")
                continue

            if 'install_date' in row and row['install_date']:
                import dateutil.parser
                try: row['install_date'] = dateutil.parser.parse(row['install_date'])
                except: pass
                
            # Process Supervisor mapping
            sup_val = row.get('supervisor') or row.get('assigned_supervisor')
            if sup_val:
                sup_dir = db.query(SupervisorDirectory).filter(
                    (SupervisorDirectory.name.ilike(sup_val)) |
                    (SupervisorDirectory.employee_id.ilike(sup_val))
                ).first()
                if sup_dir:
                    row['assigned_supervisor'] = sup_dir.supervisor_id
                else:
                    # Look up in users table as fallback
                    u = db.query(User).filter(User.name.ilike(sup_val)).first()
                    if u: row['assigned_supervisor'] = u.employee_id
                    else: row['assigned_supervisor'] = sup_val
            
            eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == eq_id).first()
            if eq:
                for k, v in row.items():
                    if hasattr(eq, k) and v: setattr(eq, k, v)
                stats["updated"] += 1
            else:
                data = {k: v for k, v in row.items() if hasattr(EquipmentMaster, k) and v}
                if 'equipment_id' not in data: data['equipment_id'] = eq_id
                new_eq = EquipmentMaster(**data)
                db.add(new_eq)
                stats["inserted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "EQUIPMENT", "equipment.csv", f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    return stats

@router.delete("/equipment/{id}")
def delete_equipment(id: str, db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == id).first()
    if not eq: raise HTTPException(status_code=404)
    # Clear parts mapping
    parts = db.query(EquipmentParts).filter(EquipmentParts.equipment_id == id).all()
    for p in parts: db.delete(p)
    db.delete(eq)
    db.commit()
    create_audit(db, current_user, "DELETE", "EQUIPMENT", id, f"Deleted equipment {eq.equipment_name}.")
    return {"message": "Success"}

# --- INVENTORY MANAGEMENT ---
@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    return db.query(InventoryMaster).all()

@router.post("/inventory/upload")
async def upload_inventory(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    
    for raw_row in reader:
        try:
            row = {str(k).strip().lower().replace(' ', '_'): str(v).strip() for k, v in raw_row.items() if k is not None}
            
            # Alias mapping
            if 'part_no' in row and 'part_number' not in row: row['part_number'] = row['part_no']
            if 'name' in row and 'part_name' not in row: row['part_name'] = row['name']
            if 'category' in row and 'part_category' not in row: row['part_category'] = row['category']
            if 'stock_qty' in row and 'stock_quantity' not in row: row['stock_quantity'] = row['stock_qty']
            if 'qty' in row and 'stock_quantity' not in row: row['stock_quantity'] = row['qty']
            if 'min_stock' in row and 'minimum_stock' not in row: row['minimum_stock'] = row['min_stock']
            if 'min' in row and 'minimum_stock' not in row: row['minimum_stock'] = row['min']
            
            part_no = row.get('part_number')
            if not part_no:
                stats["failed"] += 1
                stats["errors"].append(f"Missing part_number in row: {row}")
                continue

            if 'last_updated' in row and row['last_updated']:
                import dateutil.parser
                try: row['last_updated'] = dateutil.parser.parse(row['last_updated'])
                except: pass
                
            part = db.query(InventoryMaster).filter(InventoryMaster.part_number == part_no).first()
            if part:
                for k, v in row.items():
                    if hasattr(part, k) and v:
                        if k in ['stock_qty', 'stock_quantity', 'minimum_stock']: 
                            actual_k = 'stock_qty' if k == 'stock_quantity' else k
                            setattr(part, actual_k, int(v))
                        else: setattr(part, k, v)
                stats["updated"] += 1
            else:
                data = {k: v for k, v in row.items() if hasattr(InventoryMaster, k) and v}
                if 'part_number' not in data: data['part_number'] = part_no
                if 'stock_quantity' in row: data['stock_qty'] = int(row['stock_quantity'])
                elif 'stock_qty' in data: data['stock_qty'] = int(data['stock_qty'])
                if 'minimum_stock' in data: data['minimum_stock'] = int(data['minimum_stock'])
                new_part = InventoryMaster(**data)
                db.add(new_part)
                stats["inserted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "INVENTORY", "inventory.csv", f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    return stats

@router.delete("/inventory/{id}")
def delete_inventory(id: str, db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    part = db.query(InventoryMaster).filter(InventoryMaster.part_number == id).first()
    if not part: raise HTTPException(status_code=404)
    # Clear parts mapping
    eps = db.query(EquipmentParts).filter(EquipmentParts.part_number == id).all()
    for ep in eps: db.delete(ep)
    db.delete(part)
    db.commit()
    create_audit(db, current_user, "DELETE", "INVENTORY", id, f"Deleted part {part.part_name}.")
    return {"message": "Success"}

# --- EQUIPMENT PART MAPPING ---
@router.get("/equipment-parts")
def get_equipment_parts(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    mappings = db.query(EquipmentParts).all()
    res = []
    for m in mappings:
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == m.equipment_id).first()
        part = db.query(InventoryMaster).filter(InventoryMaster.part_number == m.part_number).first()
        res.append({
            "id": m.id, "equipment_id": m.equipment_id, 
            "equipment_name": eq.equipment_name if eq else "Unknown",
            "part_number": m.part_number, 
            "part_name": part.part_name if part else "Unknown",
            "quantity_required": m.quantity_required, "critical_part": m.critical_part
        })
    return res

@router.post("/equipment-parts/upload")
async def upload_equipment_parts(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()
    
    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}
    if len(lines) == 1:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["File contains only 1 line. Either there is no data, or newlines are missing/corrupted."]}
        
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    
    for raw_row in reader:
        try:
            row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items() if k is not None}
            eq_id = row.get('equipment_id')
            part_no = row.get('part_number')
            
            if not eq_id or not part_no:
                stats["failed"] += 1
                stats["errors"].append(f"Missing equipment_id or part_number in row: {row}")
                continue
            
            # Validation Rule: No Orphans
            if not db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == eq_id).first():
                stats["failed"] += 1
                stats["errors"].append(f"Invalid equipment_id {eq_id}")
                continue
            if not db.query(InventoryMaster).filter(InventoryMaster.part_number == part_no).first():
                # Auto-create dummy inventory item to satisfy foreign key constraint
                dummy_part = InventoryMaster(part_number=part_no, part_name="Unknown Part (Auto-created)")
                db.add(dummy_part)
                db.commit()
                
            ep = db.query(EquipmentParts).filter(EquipmentParts.equipment_id == eq_id, EquipmentParts.part_number == part_no).first()
            if ep:
                if 'quantity_required' in row: ep.quantity_required = int(row['quantity_required'])
                if 'critical_part' in row: ep.critical_part = str(row['critical_part']).lower() in ['true', '1', 'yes', 'y']
                stats["updated"] += 1
            else:
                qty = int(row.get('quantity_required', 1))
                crit = str(row.get('critical_part', 'false')).lower() in ['true', '1', 'yes', 'y']
                new_ep = EquipmentParts(equipment_id=eq_id, part_number=part_no, quantity_required=qty, critical_part=crit)
                db.add(new_ep)
                stats["inserted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "EQUIPMENT_PARTS", "equipment_parts.csv", f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    return stats

# --- MAINTENANCE HISTORY ---
@router.get("/maintenance-history")
def get_maintenance_history(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    histories = db.query(MaintenanceHistory).all()
    res = []
    for h in histories:
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == h.equipment_id).first()
        user = db.query(User).filter(User.id == h.performed_by).first() if h.performed_by else None
        res.append({
            "id": h.id, "equipment_id": h.equipment_id, "equipment_name": eq.equipment_name if eq else "Unknown",
            "maintenance_date": h.maintenance_date, "description": h.description,
            "performed_by": user.name if user else "Unknown", "status": h.status
        })
    return res

@router.post("/maintenance-history/upload")
async def upload_maintenance_history(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()

    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}

    delimiter = '\t' if '\t' in lines[0] else ','
    import csv
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    for raw_row in reader:
        try:
            row = {str(k).strip().lower().replace(' ', '_'): str(v).strip() for k, v in raw_row.items() if k is not None}
            
            eq_id = row.get('equipment_id') or row.get('eq_id')
            if not eq_id: continue
            if not db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == eq_id).first():
                stats["failed"] += 1
                stats["errors"].append(f"Invalid equipment_id {eq_id}")
                continue

            # Alias mapping
            if 'date' in row and 'maintenance_date' not in row: row['maintenance_date'] = row['date']
            if 'completion_date' in row and 'maintenance_date' not in row: row['maintenance_date'] = row['completion_date']
            if 'performed_by' not in row:
                row['performed_by'] = row.get('engineer_user_id') or row.get('supervisor_id')
                
            # Compile description from findings and action_taken if present
            desc_parts = []
            if 'findings' in row and row['findings']: desc_parts.append(f"Findings: {row['findings']}")
            if 'action_taken' in row and row['action_taken']: desc_parts.append(f"Action: {row['action_taken']}")
            if 'description' in row and row['description']: desc_parts.insert(0, row['description'])
            if desc_parts: row['description'] = ' | '.join(desc_parts)

            if 'maintenance_date' in row and row['maintenance_date']:
                import dateutil.parser
                try: row['maintenance_date'] = dateutil.parser.parse(row['maintenance_date'])
                except: pass

            data = {k: v for k, v in row.items() if hasattr(MaintenanceHistory, k) and v}
            if 'equipment_id' not in data: data['equipment_id'] = eq_id
            
            if 'performed_by' in row and row['performed_by']:
                u = db.query(User).filter(User.employee_id == row['performed_by']).first()
                if u: data['performed_by'] = u.id
                else: data.pop('performed_by', None)

            new_mh = MaintenanceHistory(**data)
            db.add(new_mh)
            stats["inserted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "MAINTENANCE_HISTORY", "maintenance_history.csv", f"Inserted: {stats['inserted']}")
    return stats

@router.post("/work-orders/upload")
async def upload_work_orders(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    contents = await file.read()
    contents_str = contents.decode('utf-8-sig')
    lines = contents_str.splitlines()

    if not lines:
        return {"inserted": 0, "updated": 0, "failed": 0, "errors": ["Uploaded file is completely empty."]}

    delimiter = '\t' if '\t' in lines[0] else ','
    import csv
    reader = csv.DictReader(lines, delimiter=delimiter)
    stats = {"inserted": 0, "updated": 0, "failed": 0, "errors": []}
    for raw_row in reader:
        try:
            row = {str(k).strip().lower().replace(' ', '_'): str(v).strip() for k, v in raw_row.items() if k is not None}
            
            # Map aliases
            title = row.get('title') or row.get('work_order_id') or 'Imported Work Order'
            desc = row.get('description') or 'Imported from CSV'
            
            if 'created_at' in row and row['created_at']:
                import dateutil.parser
                try: row['created_at'] = dateutil.parser.parse(row['created_at'])
                except: pass
                
            data = {k: v for k, v in row.items() if hasattr(WorkOrder, k) and v}
            data['title'] = title
            data['description'] = desc
            if 'equipment_id' not in data and 'eq_id' in row: data['equipment_id'] = row['eq_id']
            
            # Map assigned_to / created_by
            assigned_emp = row.get('assigned_to') or row.get('assigned_engineer_id')
            if assigned_emp:
                u = db.query(User).filter(User.employee_id == assigned_emp).first()
                if u: data['assigned_to'] = u.id
                
            created_emp = row.get('created_by') or row.get('supervisor_id')
            if created_emp:
                u = db.query(User).filter(User.employee_id == created_emp).first()
                if u: data['created_by'] = u.id
                else: data['created_by'] = current_user.id
            else:
                data['created_by'] = current_user.id

            new_wo = WorkOrder(**data)
            db.add(new_wo)
            stats["inserted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(str(e))
    db.commit()
    create_audit(db, current_user, "UPLOAD_CSV", "WORK_ORDERS", "work_orders.csv", f"Inserted: {stats['inserted']}")
    return stats

# --- WORK ORDERS ---
@router.get("/work-orders")
def get_work_orders(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    wos = db.query(WorkOrder).all()
    res = []
    for w in wos:
        eng = db.query(User).filter(User.id == w.assigned_to).first() if w.assigned_to else None
        creator = db.query(User).filter(User.id == w.created_by).first() if w.created_by else None
        eq = db.query(EquipmentMaster).filter(EquipmentMaster.equipment_id == w.equipment_id).first() if w.equipment_id else None
        res.append({
            "id": w.id, "title": w.title, "description": w.description,
            "equipment_name": eq.equipment_name if eq else "N/A",
            "priority": w.priority, "status": w.status,
            "assigned_to": eng.name if eng else "Unassigned",
            "created_by": creator.name if creator else "System",
            "created_at": w.created_at, "completed_at": w.completed_at
        })
    return res

# --- AUDIT LOGS ---
@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(allow_manager)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(1000).all()
    res = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        res.append({
            "id": log.id, "timestamp": log.created_at, "user": user.name if user else "System",
            "action": log.action, "entity_type": log.entity_type,
            "entity_id": log.entity_id, "details": log.details
        })
    return res
