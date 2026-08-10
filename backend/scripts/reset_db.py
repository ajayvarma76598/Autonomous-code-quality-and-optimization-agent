import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.session import engine, init_db
from backend.database.models.models import Base
from sqlalchemy import text

def reset_database():
    try:
        print("Dropping all existing tables...")
        # Drop all tables. Cascade will ensure constraints are ignored.
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped.")
        
        print("Re-initializing database tables...")
        init_db()
        print("Database reset complete. All data has been cleared.")
        
    except Exception as e:
        print(f"Failed to reset database: {e}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to clear ALL data from the database? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Operation cancelled.")
