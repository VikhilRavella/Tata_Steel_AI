
import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('c:/Users/ravel/Desktop/TATA_HACKATHON/backend/tata_ai.db')
        c = conn.cursor()
        
        # Create engineering_files table if not exists
        c.execute('''
        CREATE TABLE IF NOT EXISTS engineering_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id VARCHAR NOT NULL,
            user_id INTEGER NOT NULL,
            file_name VARCHAR NOT NULL,
            file_type VARCHAR NOT NULL,
            file_path VARCHAR NOT NULL,
            extracted_text TEXT,
            uploaded_at DATETIME,
            FOREIGN KEY(session_id) REFERENCES engineering_sessions(session_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Add columns to engineering_messages
        try:
            c.execute('ALTER TABLE engineering_messages ADD COLUMN message_type VARCHAR DEFAULT "text"')
        except sqlite3.OperationalError as e:
            print("message_type:", e)
            
        try:
            c.execute('ALTER TABLE engineering_messages ADD COLUMN attachment_id INTEGER')
        except sqlite3.OperationalError as e:
            print("attachment_id:", e)
            
        try:
            c.execute('ALTER TABLE engineering_messages ADD COLUMN image_path VARCHAR')
        except sqlite3.OperationalError as e:
            print("image_path:", e)
            
        try:
            c.execute('ALTER TABLE engineering_messages ADD COLUMN image_analysis TEXT')
        except sqlite3.OperationalError as e:
            print("image_analysis:", e)
            
        conn.commit()
        conn.close()
        print("Migration successful")
    except Exception as e:
        print("Migration error:", e)

if __name__ == '__main__':
    migrate()
