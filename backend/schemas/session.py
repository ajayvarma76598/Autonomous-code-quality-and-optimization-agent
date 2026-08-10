from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class SessionBase(BaseModel):
    session_name: Optional[str] = None
    status: Optional[str] = "Active"

class SessionCreate(SessionBase):
    user_id: UUID
    repository_id: UUID

class SessionUpdate(BaseModel):
    session_name: Optional[str] = None
    status: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class SessionInDBBase(SessionBase):
    session_id: UUID
    user_id: UUID
    repository_id: UUID
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Session(SessionInDBBase):
    pass

class QueryHistoryBase(BaseModel):
    user_query: str
    assistant_response: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[int] = None

class QueryHistoryCreate(QueryHistoryBase):
    session_id: UUID
    workflow_id: Optional[UUID] = None

class QueryHistoryInDBBase(QueryHistoryBase):
    query_id: UUID
    session_id: UUID
    workflow_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QueryHistory(QueryHistoryInDBBase):
    pass
