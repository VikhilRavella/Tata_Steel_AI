import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'maintenance.db')
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Add skills column if not exists
    try:
        c.execute("ALTER TABLE users ADD COLUMN skills TEXT")
        print("[+] Added 'skills' column to 'users' table.")
    except sqlite3.OperationalError as e:
        print(f"[-] 'skills' column status: {e}")
        
    # 2. Add profile_image column if not exists
    try:
        c.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
        print("[+] Added 'profile_image' column to 'users' table.")
    except sqlite3.OperationalError as e:
        print(f"[-] 'profile_image' column status: {e}")
        
    conn.commit()
    conn.close()
    print("[+] Migration finished successfully.")

if __name__ == '__main__':
    migrate()
