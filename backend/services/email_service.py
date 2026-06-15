import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import asyncio
import logging
import threading
from backend.database import SessionLocal
from backend.models import NotificationLog, Notification

# Configure logger
logger = logging.getLogger("email_service")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Load configuration from environment variables
ENABLE_EMAIL_NOTIFICATIONS = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").strip().lower() == "true"
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "ravellavikhil2004@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "fkzt qyom lxfm atev")

# Set to keep strong references to background tasks to prevent garbage collection
_background_tasks = set()

def make_table_rows(details: dict) -> str:
    rows = []
    for k, v in details.items():
        rows.append(f"""
        <tr>
            <td style="padding: 6px 0; font-weight: 600; color: #475569; width: 40%; vertical-align: top; border-bottom: 1px solid #f1f5f9;">{k}</td>
            <td style="padding: 6px 0; color: #0f172a; vertical-align: top; border-bottom: 1px solid #f1f5f9;">{v}</td>
        </tr>
        """)
    return "".join(rows)

def format_email_body(name: str, message: str, details: dict, timestamp_str: str) -> str:
    details_html = make_table_rows(details)
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; color: #333; line-height: 1.6; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="font-weight: bold; font-size: 1.2rem; color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">
            Industrial AI Maintenance Platform
        </div>
        <p>Hello {name},</p>
        <p>{message}</p>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <strong style="display: block; margin-bottom: 10px; color: #0f172a;">Details:</strong>
            <table style="width: 100%; border-collapse: collapse;">
                {details_html}
            </table>
        </div>
        <p style="font-size: 0.85rem; color: #64748b; margin-top: 20px;">Date: {timestamp_str}</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
        <p style="margin-bottom: 0;">Thank you,</p>
        <p style="font-weight: bold; margin-top: 4px; color: #1e3a8a;">Industrial AI Maintenance Platform</p>
    </div>
    """

def _send_email_sync(to_email: str, subject: str, body: str):
    """Synchronous internal method to send an email via SMTP with timeout"""
    if not to_email:
        logger.warning("Skipping email: to_email is empty.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        # Connect to server with a 10-second timeout
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10.0)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via SMTP: {e}")
        return False

def _run_email_in_thread(log_id: int, to_email: str, subject: str, body_content: str):
    """Background task to run SMTP and update database log & audit log"""
    try:
        success = _send_email_sync(to_email, subject, body_content)
        
        # Update NotificationLog status in DB and create an AuditLog
        db = SessionLocal()
        try:
            log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
            if log:
                from backend.services.audit_service import log_action
                if success:
                    log.email_sent = True
                    db.commit()
                    log_action(
                        db=db,
                        user_id=log.user_id,
                        action="EMAIL_NOTIFICATION_SENT",
                        entity_type="NotificationLog",
                        entity_id=str(log.id),
                        details={"to_email": to_email, "subject": subject}
                    )
                else:
                    log_action(
                        db=db,
                        user_id=log.user_id,
                        action="EMAIL_NOTIFICATION_FAILED",
                        entity_type="NotificationLog",
                        entity_id=str(log.id),
                        details={"to_email": to_email, "subject": subject, "error": "SMTP delivery failed"}
                    )
        except Exception as e:
            logger.error(f"Failed to update NotificationLog/AuditLog in thread task: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Exception in background email thread: {e}")

def send_notification_sync(user_id: int, notification_type: str, message: str, to_email: str = None, subject: str = None, email_body: str = None):
    """
    Creates an in-app Notification/NotificationLog synchronously and schedules background thread email sending.
    If email_body is provided, it is sent via SMTP, while message is used for in-app logs.
    This call is non-blocking and will never crash FastAPI or the Engineering Agent.
    """
    log_id = None
    db = SessionLocal()
    
    try:
        # 1. Create in-app Notification for Notification Center (recipient view)
        in_app_notif = Notification(
            recipient_id=user_id,
            type=notification_type,
            title=notification_type, # Keep the title clean
            body=message,
            is_read=False
        )
        db.add(in_app_notif)
        
        # 2. Store NotificationLog
        log = NotificationLog(
            user_id=user_id,
            notification_type=notification_type,
            message=message,
            email_sent=False,
            is_read=False
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id
    except Exception as e:
        logger.error(f"Failed to save notifications in DB: {e}")
        db.rollback()
    finally:
        db.close()

    # 3. Schedule email sending in a daemon background thread
    if ENABLE_EMAIL_NOTIFICATIONS:
        if to_email and subject and log_id is not None:
            body_to_send = email_body if email_body is not None else message
            t = threading.Thread(
                target=_run_email_in_thread,
                args=(log_id, to_email, subject, body_to_send),
                daemon=True
            )
            t.start()
        else:
            logger.info("Skipping email delivery: to_email or subject missing.")
    else:
        logger.info("Skipping email delivery: ENABLE_EMAIL_NOTIFICATIONS is set to False.")

async def send_notification(user_id: int, notification_type: str, message: str, to_email: str = None, subject: str = None, email_body: str = None):
    """
    Asynchronous version of send_notification to preserve backward compatibility.
    Calls send_notification_sync in a thread or directly since it does not block the event loop.
    """
    send_notification_sync(user_id, notification_type, message, to_email, subject, email_body)

def notify_work_order_generated(db: SessionLocal, wo_id: int):
    """Notify assigned engineer when a work order is generated/assigned"""
    try:
        from backend.models import WorkOrder, User
        import datetime
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if not wo or not wo.assigned_to:
            return
            
        engineer = db.query(User).filter(User.id == wo.assigned_to).first()
        if engineer and engineer.email:
            timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            due_date_str = (wo.created_at + datetime.timedelta(days=7)).strftime('%Y-%m-%d') if wo.created_at else datetime.datetime.utcnow().strftime('%Y-%m-%d')
            details = {
                "Work Order ID": f"#{wo.id}",
                "Asset Name": wo.equipment_id or "N/A",
                "Priority": wo.priority or "Medium",
                "Due Date": due_date_str
            }
            email_body = format_email_body(
                name=engineer.name,
                message="A new work order has been generated and assigned to you.",
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=wo.assigned_to,
                notification_type="Work Order Generated",
                message=f"Work order #{wo.id} has been generated and assigned to you.",
                to_email=engineer.email,
                subject="Work Order Generated",
                email_body=email_body
            )
    except Exception as e:
        logger.error(f"Failed to send Work Order Generated email: {e}")

def notify_maintenance_completed(db: SessionLocal, wo_id: int):
    """Notify engineer, supervisor, and all managers when a work order is Completed"""
    try:
        from backend.models import WorkOrder, User
        import datetime
        wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
        if not wo:
            return
            
        completion_date_str = wo.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if wo.completed_at else datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        details = {
            "Asset Name": wo.equipment_id or 'N/A',
            "Work Order ID": f"#{wo.id}",
            "Completion Date": completion_date_str,
            "Outcome": wo.status or 'Completed'
        }
        
        message = "A maintenance operation has been completed successfully."
        in_app_message = f"Maintenance completed for Asset: {wo.equipment_id or 'N/A'} (Work Order #{wo.id})."
        
        # 1. Send to assigned engineer
        if wo.assigned_to:
            eng = db.query(User).filter(User.id == wo.assigned_to).first()
            if eng and eng.email:
                email_body = format_email_body(eng.name, message, details, timestamp_str)
                send_notification_sync(
                    user_id=eng.id,
                    notification_type="Maintenance Completed",
                    message=in_app_message,
                    to_email=eng.email,
                    subject="Maintenance Completed",
                    email_body=email_body
                )
                
            # 2. Send to supervisor of engineer
            if eng and eng.supervisor_id:
                sup = db.query(User).filter(User.id == eng.supervisor_id).first()
                if sup and sup.email:
                    email_body = format_email_body(sup.name, message, details, timestamp_str)
                    send_notification_sync(
                        user_id=sup.id,
                        notification_type="Maintenance Completed",
                        message=in_app_message,
                        to_email=sup.email,
                        subject="Maintenance Completed",
                        email_body=email_body
                    )
                    
        # 3. Send to all managers in the plant
        managers = db.query(User).filter(User.role.ilike("manager")).all()
        for mgr in managers:
            if mgr.email:
                email_body = format_email_body(mgr.name, message, details, timestamp_str)
                send_notification_sync(
                    user_id=mgr.id,
                    notification_type="Maintenance Completed",
                    message=in_app_message,
                    to_email=mgr.email,
                    subject="Maintenance Completed",
                    email_body=email_body
                )
    except Exception as e:
        logger.error(f"Failed to send Maintenance Completed email: {e}")

def notify_engineering_report_generated(db: SessionLocal, report_id: int):
    """Notify engineer when their engineering report is ready"""
    try:
        from backend.models import EngineeringReport, User
        import datetime
        report = db.query(EngineeringReport).filter(EngineeringReport.id == report_id).first()
        if not report:
            return
            
        engineer = db.query(User).filter(User.id == report.generated_by).first()
        if engineer and engineer.email:
            timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            details = {
                "Report ID": f"#{report.id}",
                "Title": report.title or "Root Cause Analysis",
                "Report Type": report.report_type or "Root Cause Analysis"
            }
            email_body = format_email_body(
                name=engineer.name,
                message="Your engineering report has been successfully generated and is now ready for review.",
                details=details,
                timestamp_str=timestamp_str
            )
            send_notification_sync(
                user_id=report.generated_by,
                notification_type="Engineering Report Ready",
                message=f"Engineering report '{report.title}' is ready.",
                to_email=engineer.email,
                subject="Engineering Report Ready",
                email_body=email_body
            )
    except Exception as e:
        logger.error(f"Failed to send Engineering Report Generated email: {e}")

def notify_safety_escalation(db: SessionLocal, asset_name: str, asset_id: str, location: str, risk_level: str, issue_description: str, root_cause: str, recommended_action: str, priority_level: str, reporter_id: int):
    """Notify engineer, supervisor, and conditionally manager when a safety/critical risk is detected"""
    try:
        from backend.services.audit_service import log_action
        try:
            log_action(
                db=db,
                user_id=reporter_id,
                action="SAFETY_ESCALATION_GENERATED",
                entity_type="Equipment",
                entity_id=asset_id,
                details={
                    "risk_level": risk_level,
                    "issue": issue_description,
                    "root_cause": root_cause,
                    "recommended_action": recommended_action,
                    "priority": priority_level
                }
            )
        except Exception as ae:
            logger.error(f"Failed to log safety escalation action: {ae}")

        from backend.models import User
        import datetime
        timestamp_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        details = {
            "Asset Name": asset_name,
            "Asset ID": asset_id,
            "Location": location,
            "Risk Level": risk_level,
            "Issue Detected": issue_description,
            "Root Cause": root_cause,
            "Recommended Action": recommended_action,
            "Priority": priority_level,
            "Generated By": "Engineering Agent"
        }
        
        is_critical = risk_level.upper() == "CRITICAL"
        notification_type = "CRITICAL RISK ALERT" if is_critical else "HIGH RISK ALERT"
        subject = f"[{notification_type}] Equipment Failure Risk Detected" if is_critical else f"[{notification_type}] Immediate Attention Required"
        
        message = "CRITICAL MAINTENANCE ALERT\nPlease review and take immediate action."
        in_app_message = f"[{notification_type}] Asset: {asset_name} ({asset_id}). Issue: {issue_description}"
        
        # 1. Send to reporter (Engineer)
        reporter = db.query(User).filter(User.id == reporter_id).first()
        if reporter and reporter.email:
            email_body = format_email_body(reporter.name, message, details, timestamp_str)
            send_notification_sync(
                user_id=reporter.id,
                notification_type=notification_type,
                message=in_app_message,
                to_email=reporter.email,
                subject=subject,
                email_body=email_body
            )
            
        # 2. Send to supervisor of reporter
        if reporter and reporter.supervisor_id:
            sup = db.query(User).filter(User.id == reporter.supervisor_id).first()
            if sup and sup.email:
                email_body = format_email_body(sup.name, message, details, timestamp_str)
                send_notification_sync(
                    user_id=sup.id,
                    notification_type=notification_type,
                    message=in_app_message,
                    to_email=sup.email,
                    subject=subject,
                    email_body=email_body
                )
                
        # 3. Send to Manager if CRITICAL
        if is_critical:
            managers = db.query(User).filter(User.role.ilike('manager')).all()
            for mgr in managers:
                if mgr.email:
                    email_body = format_email_body(mgr.name, message, details, timestamp_str)
                    send_notification_sync(
                        user_id=mgr.id,
                        notification_type=notification_type,
                        message=in_app_message,
                        to_email=mgr.email,
                        subject=subject,
                        email_body=email_body
                    )
    except Exception as e:
        logger.error(f"Failed to send Safety Escalation email: {e}")




