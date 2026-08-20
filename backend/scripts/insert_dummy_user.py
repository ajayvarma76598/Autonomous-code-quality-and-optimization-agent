import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid

from backend.database.models.models import User
from backend.database.session import SessionLocal


def create_dummy_user():
    db = SessionLocal()
    try:
        user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        existing = db.query(User).filter_by(user_id=user_id).first()
        if not existing:
            dummy_user = User(
                user_id=user_id,
                email="demo@example.com",
                username="swagger_demo_user",
                role="admin",
            )
            db.add(dummy_user)
            db.commit()
            print(
                "Successfully created dummy user with ID 11111111-1111-1111-1111-111111111111"
            )
        else:
            print("Dummy user already exists!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_dummy_user()
