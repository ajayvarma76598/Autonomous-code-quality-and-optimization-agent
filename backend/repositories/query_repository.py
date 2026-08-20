from sqlalchemy.orm import Session

from backend.database.models.models import QueryHistory
from backend.repositories.base_repository import BaseRepository
from backend.schemas.session import QueryHistoryBase, QueryHistoryCreate


class QueryRepository(
    BaseRepository[QueryHistory, QueryHistoryCreate, QueryHistoryBase]
):
    def get_by_session(self, db: Session, *, session_id: str) -> list[QueryHistory]:
        return (
            db.query(self.model)
            .filter(QueryHistory.session_id == session_id)
            .order_by(QueryHistory.created_at.desc())
            .all()
        )


query_repo = QueryRepository(QueryHistory)
