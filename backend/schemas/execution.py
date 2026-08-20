from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowRunBase(BaseModel):
    workflow_type: str
    status: str | None = "RUNNING"
    latency_ms: int | None = None


class WorkflowRunCreate(WorkflowRunBase):
    session_id: UUID
    snapshot_id: UUID


class WorkflowRunUpdate(BaseModel):
    status: str | None = None
    completed_at: datetime | None = None
    latency_ms: int | None = None


class WorkflowRunInDBBase(WorkflowRunBase):
    workflow_id: UUID
    session_id: UUID
    snapshot_id: UUID
    started_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowRun(WorkflowRunInDBBase):
    pass
