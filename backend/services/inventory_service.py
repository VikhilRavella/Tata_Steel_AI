import datetime
import logging
from sqlalchemy.orm import Session
from backend.models import InventoryMaster, InventoryTransaction, AuditLog, Alert, Notification, User
from backend.services.email_service import send_notification_sync, format_email_body

logger = logging.getLogger("inventory_service")

def request_part(db: Session, user_id: int, part_identifier: str, quantity: int, equipment_id: str) -> str:
    """Engineer requests a part, creating a pending transaction."""
    import re
    
    part = None
    # 1. Try to extract part number pattern (e.g. PART-078)
    part_num_match = re.search(r'(PART-\d+)', part_identifier, re.IGNORECASE)
    if part_num_match:
        extracted_num = part_num_match.group(1).upper()
        part = db.query(InventoryMaster).filter(InventoryMaster.part_number == extracted_num).first()
        
    # 2. Try exact match on part_number
    if not part:
        part = db.query(InventoryMaster).filter(InventoryMaster.part_number == part_identifier).first()
    
    # 3. Try to clean out the PART-XXX string and search part_name
    if not part:
        clean_identifier = re.sub(r'\(?PART-\d+\)?', '', part_identifier, flags=re.IGNORECASE).strip()
        if clean_identifier:
            part = db.query(InventoryMaster).filter(InventoryMaster.part_name.ilike(f"%{clean_identifier}%")).first()
            
    # 4. Final fallback to raw ilike
    if not part:
        part = db.query(InventoryMaster).filter(InventoryMaster.part_name.ilike(f"%{part_identifier}%")).first()
        
    if not part:
        raise ValueError(f"Part '{part_identifier}' not found in inventory.")
    
    # Create transaction
    txn = InventoryTransaction(
        part_number=part.part_number,
        part_name=part.part_name,
        equipment_id=equipment_id,
        requested_by=user_id,
        quantity=quantity,
        transaction_type='PENDING'
    )
    db.add(txn)
    
    # Audit log
    audit = AuditLog(
        user_id=user_id,
        action="REQUEST_PART",
        entity_type="INVENTORY",
        entity_id=part.part_number,
        details=f'{{"quantity": {quantity}, "equipment_id": "{equipment_id}"}}'
    )
    db.add(audit)
    
    db.commit()
    db.refresh(txn)

    # 1. Inventory Request Created Email Notification to Engineer
    try:
        engineer = db.query(User).filter(User.id == user_id).first()
        if engineer and engineer.email:
            timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            details = {
                "Request ID": txn.transaction_id,
                "Part Name": part.part_name,
                "Quantity": str(quantity),
                "Status": "PENDING"
            }
            email_body = format_email_body(
                name=engineer.name,
                message="Your inventory request has been successfully submitted and is currently pending supervisor approval.",
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=user_id,
                notification_type="Inventory Request Submitted",
                message=f"Your request for {quantity}x {part.part_name} has been submitted.",
                to_email=engineer.email,
                subject="Inventory Request Submitted",
                email_body=email_body
            )
    except Exception as e:
        logger.error(f"Failed to send inventory request submitted email: {e}")

    return f"Request created for {quantity}x {part.part_name} (Transaction ID: {txn.transaction_id}). Pending supervisor approval."

def approve_issue(db: Session, supervisor_id: int, transaction_id: str) -> str:
    """Supervisor approves a pending request."""
    txn = db.query(InventoryTransaction).filter(InventoryTransaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found.")
    if txn.transaction_type != 'PENDING':
        raise ValueError(f"Transaction is already {txn.transaction_type}.")
    
    part = db.query(InventoryMaster).filter(InventoryMaster.part_number == txn.part_number).first()
    if not part:
        raise ValueError("Part not found.")
    
    if part.stock_qty < txn.quantity:
        # Insufficient stock: keep PENDING, create notification and alert
        notif = Notification(
            recipient_id=txn.requested_by,
            title="Part Request Delayed",
            body=f"Your request for {txn.quantity}x {txn.part_name} is delayed due to insufficient stock.",
            type="inventory_alert"
        )
        db.add(notif)
        
        alert = Alert(
            alert_type="LOW_STOCK",
            severity="High",
            message=f"Insufficient stock to approve request {txn.transaction_id} for {txn.part_name}. Requested: {txn.quantity}, Available: {part.stock_qty}",
            status='active'
        )
        db.add(alert)
        db.commit()
        raise ValueError(f"Insufficient stock. Available: {part.stock_qty}, Requested: {txn.quantity}.")
    
    # Update inventory
    part.stock_qty -= txn.quantity
    
    # Update transaction
    txn.transaction_type = 'APPROVED'
    txn.approved_by = supervisor_id
    txn.timestamp = datetime.datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=supervisor_id,
        action="APPROVE_ISSUE",
        entity_type="INVENTORY_TRANSACTION",
        entity_id=txn.transaction_id,
        details=f"Approved request for {txn.quantity} of {txn.part_number}"
    )
    db.add(audit)
    db.commit()

    # Determine approver role and send email to engineer
    try:
        engineer = db.query(User).filter(User.id == txn.requested_by).first()
        approver = db.query(User).filter(User.id == supervisor_id).first()
        approver_role = (approver.role or "supervisor").lower() if approver else "supervisor"
        
        if approver_role == "manager":
            subject = "Request Approved By Manager"
            notification_type = "Request Approved By Manager"
            lead_text = f"Your inventory request has been approved by Manager {approver.name if approver else ''}."
            details = {
                "Request ID": txn.transaction_id,
                "Manager Name": approver.name if approver else "Manager",
                "Status": "APPROVED"
            }
        else:
            subject = "Request Approved By Supervisor"
            notification_type = "Request Approved By Supervisor"
            lead_text = f"Your inventory request has been approved by Supervisor {approver.name if approver else ''}."
            details = {
                "Request ID": txn.transaction_id,
                "Supervisor Name": approver.name if approver else "Supervisor",
                "Status": "APPROVED"
            }

        if engineer and engineer.email:
            timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            email_body = format_email_body(
                name=engineer.name,
                message=f"{lead_text} The parts have been issued and stock has been deducted.",
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=txn.requested_by,
                notification_type=notification_type,
                message=f"Your request for {txn.quantity}x {txn.part_name} was approved.",
                to_email=engineer.email,
                subject=subject,
                email_body=email_body
            )
    except Exception as e:
        logger.error(f"Failed to send request approved email: {e}")
    
    # Check low stock
    if part.stock_qty <= part.minimum_stock:
        from backend.models import SupervisorDirectory
        sup = db.query(SupervisorDirectory).first()
        sup_contact = f"Contact: {sup.name} ({sup.phone})" if sup else "No supervisor mapped"
        alert = Alert(
            alert_type="LOW_STOCK",
            severity="High",
            message=f"LOW STOCK ALERT\nPart Number: {part.part_number}\nCurrent Stock: {part.stock_qty}\nMinimum Stock: {part.minimum_stock}\nWarehouse: {part.warehouse}\nSupervisor {sup_contact}",
            status='active'
        )
        db.add(alert)
        db.commit()
    
    return f"Approved issue of {txn.quantity}x {part.part_name}. Remaining stock: {part.stock_qty}."

def reject_issue(db: Session, supervisor_id: int, transaction_id: str, rejection_reason: str = "") -> str:
    """Supervisor rejects a pending request."""
    txn = db.query(InventoryTransaction).filter(InventoryTransaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found.")
    if txn.transaction_type != 'PENDING':
        raise ValueError(f"Transaction is already {txn.transaction_type}.")
    
    txn.transaction_type = 'REJECTED'
    txn.approved_by = supervisor_id
    txn.timestamp = datetime.datetime.utcnow()
    txn.rejection_reason = rejection_reason
    
    audit = AuditLog(
        user_id=supervisor_id,
        action="REJECT_ISSUE",
        entity_type="INVENTORY_TRANSACTION",
        entity_id=txn.transaction_id,
        details=f"Rejected request for {txn.quantity} of {txn.part_number}"
    )
    db.add(audit)
    db.commit()

    # Determine rejecter role and send email to engineer
    try:
        engineer = db.query(User).filter(User.id == txn.requested_by).first()
        approver = db.query(User).filter(User.id == supervisor_id).first()
        approver_role = (approver.role or "supervisor").lower() if approver else "supervisor"
        
        if approver_role == "manager":
            subject = "Request Rejected By Manager"
            notification_type = "Request Rejected By Manager"
            lead_text = f"Your inventory request has been rejected by Manager {approver.name if approver else ''}."
            details = {
                "Request ID": txn.transaction_id,
                "Rejection Reason": rejection_reason or "No reason provided"
            }
        else:
            subject = "Request Rejected By Supervisor"
            notification_type = "Request Rejected By Supervisor"
            lead_text = f"Your inventory request has been rejected by Supervisor {approver.name if approver else ''}."
            details = {
                "Request ID": txn.transaction_id,
                "Rejection Reason": rejection_reason or "No reason provided"
            }

        if engineer and engineer.email:
            timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            email_body = format_email_body(
                name=engineer.name,
                message=lead_text,
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=txn.requested_by,
                notification_type=notification_type,
                message=f"Your request for {txn.quantity}x {txn.part_name} was rejected. Reason: {rejection_reason or 'No reason'}",
                to_email=engineer.email,
                subject=subject,
                email_body=email_body
            )
    except Exception as e:
        logger.error(f"Failed to send request rejected email: {e}")
        
    return f"Rejected request for {txn.quantity}x {txn.part_name}."

def approve_return(db: Session, supervisor_id: int, part_identifier: str, quantity: int) -> str:
    """Supervisor approves a return."""
    part = db.query(InventoryMaster).filter(InventoryMaster.part_number == part_identifier).first()
    if not part:
        part = db.query(InventoryMaster).filter(InventoryMaster.part_name.ilike(f"%{part_identifier}%")).first()
        
    if not part:
        raise ValueError(f"Part '{part_identifier}' not found.")
    
    part.stock_qty += quantity
    
    txn = InventoryTransaction(
        part_number=part.part_number,
        part_name=part.part_name,
        requested_by=supervisor_id,
        approved_by=supervisor_id,
        quantity=quantity,
        transaction_type='RETURN'
    )
    db.add(txn)
    
    audit = AuditLog(
        user_id=supervisor_id,
        action="RETURN_PART",
        entity_type="INVENTORY",
        entity_id=part.part_number,
        details=f'{{"quantity": {quantity}}}'
    )
    db.add(audit)
    
    db.commit()
    return f"Returned {quantity}x {part.part_name} to inventory. New stock: {part.stock_qty}."


