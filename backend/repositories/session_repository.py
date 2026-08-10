from typing import List
from sqlalchemy.orm import Session
from backend.repositories.base_repository import BaseRepository
from backend.database.models.models import Session as DBSession
from backend.schemas.session import SessionCreate, SessionUpdate

class SessionRepository(BaseRepository[DBSession, SessionCreate, SessionUpdate]):
    def get_by_user(self, db: Session, *, user_id: str) -> List[DBSession]:
        return db.query(self.model).filter(DBSession.user_id == user_id).all()
        
    def get_by_repository(self, db: Session, *, repository_id: str) -> List[DBSession]:
        return db.query(self.model).filter(DBSession.repository_id == repository_id).all()

session_repo = SessionRepository(DBSession)
