from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class RepositoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    git_provider: Optional[str] = None
    git_url: Optional[str] = None
    default_branch: Optional[str] = "main"
    status: Optional[str] = "Active"

class RepositoryCreate(RepositoryBase):
    user_id: UUID

class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: Optional[str] = None
    status: Optional[str] = None

class RepositoryInDBBase(RepositoryBase):
    repository_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Repository(RepositoryInDBBase):
    pass

class RepositorySnapshotBase(BaseModel):
    commit_hash: str
    branch: str
    commit_message: Optional[str] = None
    author: Optional[str] = None
    is_latest: bool = True

class RepositorySnapshot(RepositorySnapshotBase):
    snapshot_id: UUID
    repository_id: UUID
    indexed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class RepositoryFileBase(BaseModel):
    path: str
    filename: str
    extension: Optional[str] = None
    language: Optional[str] = None
    size_bytes: Optional[int] = None
    line_count: Optional[int] = None
    checksum: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None

class RepositoryFile(RepositoryFileBase):
    file_id: UUID
    snapshot_id: UUID

    model_config = ConfigDict(from_attributes=True)
