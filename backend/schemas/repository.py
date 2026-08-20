from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryBase(BaseModel):
    name: str
    description: str | None = None
    git_provider: str | None = None
    git_url: str | None = None
    default_branch: str | None = "main"
    status: str | None = "Active"


class RepositoryCreate(RepositoryBase):
    user_id: str | None = None


class RepositoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_branch: str | None = None
    status: str | None = None


class RepositoryInDBBase(RepositoryBase):
    repository_id: UUID
    user_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Repository(RepositoryInDBBase):
    pass


class RepositorySnapshotBase(BaseModel):
    commit_hash: str
    branch: str
    commit_message: str | None = None
    author: str | None = None
    is_latest: bool = True


class RepositorySnapshot(RepositorySnapshotBase):
    snapshot_id: UUID
    repository_id: UUID
    indexed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RepositoryFileBase(BaseModel):
    path: str
    filename: str
    extension: str | None = None
    language: str | None = None
    size_bytes: int | None = None
    line_count: int | None = None
    checksum: str | None = None
    metadata_: dict[str, Any] | None = None


class RepositoryFile(RepositoryFileBase):
    file_id: UUID
    snapshot_id: UUID

    model_config = ConfigDict(from_attributes=True)
