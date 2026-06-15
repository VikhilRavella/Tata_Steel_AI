from backend.database import engine
from backend.models import Base
import sqlite3
import datetime

db_path = "backend/maintenance.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
    print("Added updated_at to users table")
except sqlite3.OperationalError as e:
    print(f"OperationalError (maybe column exists): {e}")

conn.close()

# Create all other missing tables (NotificationLog, MaintenanceOutcome)
Base.metadata.create_all(bind=engine)
print("Created missing tables.")
