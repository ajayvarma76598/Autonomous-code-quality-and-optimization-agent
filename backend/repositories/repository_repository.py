from sqlalchemy.orm import Session

from backend.database.models.models import Repository
from backend.repositories.base_repository import BaseRepository
from backend.schemas.repository import RepositoryCreate, RepositoryUpdate


class RepositoryRepository(
    BaseRepository[Repository, RepositoryCreate, RepositoryUpdate]
):
    def get_by_user(self, db: Session, *, user_id: str) -> list[Repository]:
        return db.query(self.model).filter(Repository.user_id == user_id).all()

    def get_by_name(self, db: Session, *, name: str) -> Repository:
        return db.query(self.model).filter(Repository.name == name).first()


repository_repo = RepositoryRepository(Repository)
