import os
import sys

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
import backend.models as models
from backend.routers.auth import get_password_hash

def update_pwd():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.employee_id == 'ENG001').first()
        if user:
            user.password_hash = get_password_hash("123456")
            db.commit()
            print("[+] Updated password for ENG001 to '123456'")
        else:
            print("[-] User ENG001 not found.")
    except Exception as e:
        print("[-] Error:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_pwd()
