from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionBase(BaseModel):
    session_name: str | None = None
    status: str | None = "Active"


class SessionCreate(SessionBase):
    user_id: str | None = None
    repository_id: UUID


class SessionUpdate(BaseModel):
    session_name: str | None = None
    status: str | None = None
    last_activity_at: datetime | None = None
    ended_at: datetime | None = None


class SessionInDBBase(SessionBase):
    session_id: UUID
    user_id: str | None = None
    repository_id: UUID
    created_at: datetime
    last_activity_at: datetime | None = None
    ended_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class Session(SessionInDBBase):
    pass


class QueryHistoryBase(BaseModel):
    user_query: str
    assistant_response: str | None = None
    intent: str | None = None
    confidence: float | None = None
    latency_ms: int | None = None


class QueryHistoryCreate(QueryHistoryBase):
    session_id: UUID
    workflow_id: UUID | None = None


class QueryHistoryInDBBase(QueryHistoryBase):
    query_id: UUID
    session_id: UUID
    workflow_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryHistory(QueryHistoryInDBBase):
    pass
