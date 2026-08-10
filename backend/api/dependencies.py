from typing import Generator
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session for each request.
    Closes the session after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# For a production app, we would add auth dependencies here as well
# e.g., get_current_user() that decodes JWT from Auth0.
