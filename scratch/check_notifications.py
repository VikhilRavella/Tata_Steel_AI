import sqlite3
import json

DB_PATH = r"C:\Users\ravel\Downloads\Tata_Steel_AI-main\Tata_Steel_AI-main\backend\maintenance.db"

def check():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get user id
    c.execute("SELECT id, name FROM users WHERE employee_id='ENG001'")
    user = c.fetchone()
    if not user:
        print("User ENG001 not found.")
        return
    user_id, name = user
    print(f"User ID: {user_id}, Name: {name}")
    
    # Fetch all notifications for this user
    c.execute("SELECT id, type, title, body, is_read, created_at FROM notifications WHERE recipient_id=? ORDER BY created_at DESC", (user_id,))
    notifs = c.fetchall()
    print(f"\nFound {len(notifs)} in-app notifications for ENG001:")
    for n in notifs:
        print(f"- [{n[5]}] [{n[1]}] Title: {n[2]} | Body: {n[3]} | Read: {n[4]}")
        
    conn.close()

if __name__ == "__main__":
    check()
