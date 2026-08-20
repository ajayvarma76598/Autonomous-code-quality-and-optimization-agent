from typing import Any

from pydantic import BaseModel, Field


class RepositoryFingerprint(BaseModel):
    commit: str = Field(description="The latest commit hash.")
    branch: str = Field(description="The branch name.")
    repo_id: str = Field(
        description="A unique identifier for the repository (e.g. org/repo)."
    )
    language_hash: str | None = Field(
        default=None, description="A hash representing the language distribution."
    )
    dependency_hash: str | None = Field(
        default=None,
        description="A hash representing the dependency versions (e.g., package.json, requirements.txt).",
    )


class RepositoryContext(BaseModel):
    fingerprint: RepositoryFingerprint = Field(
        description="The unique fingerprint identifying this exact repository state."
    )
    local_path: str = Field(
        description="The absolute path to the local cloned repository."
    )
    parsed_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata such as package structure, entry points, and framework versions.",
    )
    affected_files: list[str] | None = Field(
        default=None,
        description="If this is an incremental analysis, the list of files that changed.",
    )
