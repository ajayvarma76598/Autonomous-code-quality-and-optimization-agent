import sys
import os

# Add the backend to sys.path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.database.session import engine, Base
from backend.database.models.models import *

def reset_db():
    print("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")
    
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database cleared and reset successfully.")

if __name__ == "__main__":
    # Ask for confirmation just to be safe, but since this is automated we'll just run it
    reset_db()
