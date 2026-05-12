import sqlite3
import os

db_path = "instance/app.db"
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE users ADD COLUMN last_synced_at DATETIME;")
        conn.commit()
        conn.close()
        print("Successfully added 'last_synced_at' column to 'users' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'last_synced_at' already exists.")
        else:
            print(f"Error updating database: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
else:
    print("Database file not found. It will be created when the app starts.")
