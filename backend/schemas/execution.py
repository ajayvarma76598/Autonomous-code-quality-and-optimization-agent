from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class WorkflowRunBase(BaseModel):
    workflow_type: str
    status: Optional[str] = "RUNNING"
    latency_ms: Optional[int] = None

class WorkflowRunCreate(WorkflowRunBase):
    session_id: UUID
    snapshot_id: UUID

class WorkflowRunUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    latency_ms: Optional[int] = None

class WorkflowRunInDBBase(WorkflowRunBase):
    workflow_id: UUID
    session_id: UUID
    snapshot_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class WorkflowRun(WorkflowRunInDBBase):
    pass

