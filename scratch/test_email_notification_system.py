import os
import sys
import sqlite3
import datetime
import time

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
import backend.models as models
from backend.services.email_service import (
    notify_work_order_generated,
    notify_maintenance_completed,
    notify_engineering_report_generated,
    notify_critical_risk_alert,
    send_notification_sync
)
from backend.services.inventory_service import (
    request_part,
    approve_issue,
    reject_issue
)

DB_PATH = r"C:\Users\ravel\Downloads\Tata_Steel_AI-main\Tata_Steel_AI-main\backend\maintenance.db"

def setup_test_users():
    """Setup users with test email addresses in the target database"""
    print("[+] Seeding users table with test emails for E2E notifications...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Enable test emails for all users to verify Gmail SMTP
    test_email = "ravellavikhil2004@gmail.com"
    
    # 1. Update ENG001
    c.execute("UPDATE users SET email=? WHERE employee_id='ENG001'", (test_email,))
    # 2. Update SUP001
    c.execute("UPDATE users SET email=? WHERE employee_id='SUP001'", (test_email,))
    # 3. Update MGR001
    c.execute("UPDATE users SET email=? WHERE employee_id='MGR001'", (test_email,))
    
    conn.commit()
    conn.close()
    print("[+] Test users successfully configured.")

def test_email_system():
    setup_test_users()
    db = SessionLocal()
    
    # Retrieve user records
    eng = db.query(models.User).filter(models.User.employee_id == 'ENG001').first()
    sup = db.query(models.User).filter(models.User.employee_id == 'SUP001').first()
    mgr = db.query(models.User).filter(models.User.employee_id == 'MGR001').first()
    
    # Ensure supervisor relationship is set
    eng.supervisor_id = sup.id
    db.commit()
    
    results = {}
    
    # ------------------------------------------------
    # EVENT 1: Profile Updated
    # ------------------------------------------------
    print("\n--- Testing Event 1: Profile Updated ---")
    try:
        timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        from backend.services.email_service import format_email_body
        details = {
            "Name": eng.name,
            "Email": eng.email,
            "Phone Number": eng.phone or "N/A"
        }
        email_body = format_email_body(eng.name, "Your profile information has been updated successfully.", details, timestamp_str)
        send_notification_sync(
            user_id=eng.id,
            notification_type="Profile Updated",
            message="Your profile information has been updated successfully.",
            to_email=eng.email,
            subject="Profile Updated Successfully",
            email_body=email_body
        )
        results["1. Profile Updated"] = "PASS"
    except Exception as e:
        results["1. Profile Updated"] = f"FAIL ({e})"

    # Create dummy part in inventory
    part = db.query(models.InventoryMaster).filter(models.InventoryMaster.part_number == "HYDRAULIC-PUMP-999").first()
    if not part:
        part = models.InventoryMaster(
            part_number="HYDRAULIC-PUMP-999",
            part_name="Hydraulic Actuator Pump",
            stock_qty=10,
            minimum_stock=2
        )
        db.add(part)
        db.commit()

    # ------------------------------------------------
    # EVENT 2: Inventory Request Submitted
    # ------------------------------------------------
    print("\n--- Testing Event 2: Inventory Request Submitted ---")
    try:
        msg = request_part(db, eng.id, "HYDRAULIC-PUMP-999", 2, "EQ-999")
        print(f"    Result: {msg}")
        results["2. Inventory Request Submitted"] = "PASS"
    except Exception as e:
        results["2. Inventory Request Submitted"] = f"FAIL ({e})"

    # Find the newly created transaction
    txn = db.query(models.InventoryTransaction).filter(
        models.InventoryTransaction.requested_by == eng.id,
        models.InventoryTransaction.transaction_type == "PENDING"
    ).order_by(models.InventoryTransaction.timestamp.desc()).first()

    # ------------------------------------------------
    # EVENT 3 & 5: Request Approved (Supervisor / Manager)
    # ------------------------------------------------
    print("\n--- Testing Event 3: Request Approved by Supervisor ---")
    try:
        # Supervisor approval
        msg = approve_issue(db, sup.id, txn.transaction_id)
        print(f"    Result: {msg}")
        results["3. Supervisor Approved Request"] = "PASS"
    except Exception as e:
        results["3. Supervisor Approved Request"] = f"FAIL ({e})"

    # Re-request for Manager Approve test
    txn2 = models.InventoryTransaction(
        part_number="HYDRAULIC-PUMP-999",
        part_name="Hydraulic Actuator Pump",
        equipment_id="EQ-999",
        requested_by=eng.id,
        quantity=1,
        transaction_type='PENDING'
    )
    db.add(txn2)
    db.commit()
    db.refresh(txn2)

    print("\n--- Testing Event 5: Request Approved by Manager ---")
    try:
        # Manager approval
        msg = approve_issue(db, mgr.id, txn2.transaction_id)
        print(f"    Result: {msg}")
        results["5. Manager Approved Request"] = "PASS"
    except Exception as e:
        results["5. Manager Approved Request"] = f"FAIL ({e})"

    # Re-request for Rejection tests
    txn3 = models.InventoryTransaction(
        part_number="HYDRAULIC-PUMP-999",
        part_name="Hydraulic Actuator Pump",
        equipment_id="EQ-999",
        requested_by=eng.id,
        quantity=1,
        transaction_type='PENDING'
    )
    db.add(txn3)
    db.commit()
    db.refresh(txn3)

    # ------------------------------------------------
    # EVENT 4: Request Rejected by Supervisor
    # ------------------------------------------------
    print("\n--- Testing Event 4: Request Rejected by Supervisor ---")
    try:
        msg = reject_issue(db, sup.id, txn3.transaction_id, "Incomplete documentation")
        print(f"    Result: {msg}")
        results["4. Supervisor Rejected Request"] = "PASS"
    except Exception as e:
        results["4. Supervisor Rejected Request"] = f"FAIL ({e})"

    # Re-request for Manager Reject test
    txn4 = models.InventoryTransaction(
        part_number="HYDRAULIC-PUMP-999",
        part_name="Hydraulic Actuator Pump",
        equipment_id="EQ-999",
        requested_by=eng.id,
        quantity=1,
        transaction_type='PENDING'
    )
    db.add(txn4)
    db.commit()
    db.refresh(txn4)

    # ------------------------------------------------
    # EVENT 6: Request Rejected by Manager
    # ------------------------------------------------
    print("\n--- Testing Event 6: Request Rejected by Manager ---")
    try:
        msg = reject_issue(db, mgr.id, txn4.transaction_id, "Budget cap exceeded")
        print(f"    Result: {msg}")
        results["6. Manager Rejected Request"] = "PASS"
    except Exception as e:
        results["6. Manager Rejected Request"] = f"FAIL ({e})"

    # ------------------------------------------------
    # EVENT 7: Work Order Generated
    # ------------------------------------------------
    print("\n--- Testing Event 7: Work Order Generated ---")
    try:
        wo = models.WorkOrder(
            title="Inspect Blast Furnace Leakage",
            description="Perform visual inspection on furnace 3 walls",
            priority="High",
            status="Open",
            assigned_to=eng.id,
            created_by=sup.id,
            equipment_id="BF-003"
        )
        db.add(wo)
        db.commit()
        db.refresh(wo)
        notify_work_order_generated(db, wo.id)
        results["7. Work Order Generated"] = "PASS"
    except Exception as e:
        results["7. Work Order Generated"] = f"FAIL ({e})"

    # ------------------------------------------------
    # EVENT 8: Critical Risk Alert
    # ------------------------------------------------
    print("\n--- Testing Event 8: Critical Risk Alert ---")
    try:
        notify_critical_risk_alert(
            db=db,
            asset="BF-003",
            risk_level="CRITICAL",
            root_cause="Gas leak valve pressure anomaly",
            recommended_action="Shutdown feed line B-12 and vent pressure",
            reporter_id=eng.id
        )
        results["8. Critical Risk Alert"] = "PASS"
    except Exception as e:
        results["8. Critical Risk Alert"] = f"FAIL ({e})"

    # ------------------------------------------------
    # EVENT 9: Maintenance Completed
    # ------------------------------------------------
    print("\n--- Testing Event 9: Maintenance Completed ---")
    try:
        wo.status = "Completed"
        wo.completed_at = datetime.datetime.utcnow()
        db.commit()
        notify_maintenance_completed(db, wo.id)
        results["9. Maintenance Completed"] = "PASS"
    except Exception as e:
        results["9. Maintenance Completed"] = f"FAIL ({e})"

    # ------------------------------------------------
    # EVENT 10: Engineering Report Generated
    # ------------------------------------------------
    print("\n--- Testing Event 10: Engineering Report Generated ---")
    try:
        report = models.EngineeringReport(
            session_id="dummy-session",
            title="RCA on Blast Furnace 3 leak",
            report_type="Root Cause Analysis",
            report_content="RCA analysis notes and findings...",
            generated_by=eng.id
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        notify_engineering_report_generated(db, report.id)
        results["10. Engineering Report Generated"] = "PASS"
    except Exception as e:
        results["10. Engineering Report Generated"] = f"FAIL ({e})"

    # Wait for background SMTP thread pools
    print("\n[+] Sleeping for 5 seconds to allow SMTP async tasks to process...")
    time.sleep(5)

    print("\n==================================================")
    print("EMAIL NOTIFICATION SYSTEM SCORECARD")
    print("==================================================")
    all_pass = True
    for event, res in results.items():
        print(f"{event.ljust(35)}: [{res}]")
        if res != "PASS":
            all_pass = False
            
    # Verify Notification Log counts
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM notification_logs")
    log_count = c.fetchone()[0]
    print(f"\nTotal entries in 'notification_logs': {log_count}")
    conn.close()

    print(f"\nFINAL SYSTEM STATUS: {'[PASS]' if all_pass else '[FAIL]'}")
    db.close()

if __name__ == "__main__":
    test_email_system()
