from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from backend.api.dependencies import get_db
from backend.repositories.repository_repository import repository_repo
from backend.schemas.repository import Repository, RepositoryCreate, RepositoryUpdate

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.post("/", response_model=Repository, status_code=status.HTTP_201_CREATED)
def create_repository(
    *,
    db: Session = Depends(get_db),
    repository_in: RepositoryCreate,
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create new repository ingestion entry and trigger ingestion pipeline in background.
    """
    from backend.ingestion.git import git_service
    from backend.api.routers.ingestion import _detect_languages, _run_ingestion_pipeline
    from backend.database.models.models import Repository as DBRepository, RepositorySnapshot
    
    # 0. Fast pre-check: verify if the latest remote commit is already ingested
    remote_hash = git_service.get_remote_commit_hash(repository_in.git_url, repository_in.default_branch or "main")
    if remote_hash:
        existing_repo = db.query(DBRepository).filter(DBRepository.git_url == repository_in.git_url).first()
        if existing_repo:
            latest_snapshot = db.query(RepositorySnapshot).filter_by(repository_id=existing_repo.repository_id, is_latest=True).first()
            if latest_snapshot and latest_snapshot.commit_hash == remote_hash:
                raise HTTPException(
                    status_code=400, 
                    detail="This repository is already ingested with the latest commit. No new changes detected."
                )

    # 1. Clone synchronously to detect language before DB insertion
    repo_path = git_service.clone_repository(repository_in.git_url, branch=repository_in.default_branch or "main")
    primary_lang = _detect_languages(repo_path)
    
    # 2. Insert into DB with detected language
    repo_data = repository_in.model_dump(exclude_unset=True)
    repo_data["default_language"] = primary_lang
    db_obj = DBRepository(**repo_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    
    # 3. Trigger ingestion (clone inside will be instant)
    background_tasks.add_task(_run_ingestion_pipeline, db_obj.repository_id)
    
    return db_obj

@router.get("/", response_model=List[Repository])
def read_repositories(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve all repositories.
    """
    repos = repository_repo.get_multi(db=db, skip=skip, limit=limit)
    return repos

@router.get("/{id}", response_model=Repository)
def read_repository(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Get a specific repository by ID.
    """
    repo = repository_repo.get(db=db, id=id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.patch("/{id}", response_model=Repository)
def update_repository(
    *,
    db: Session = Depends(get_db),
    id: UUID,
    repository_in: RepositoryUpdate
) -> Any:
    """
    Update a repository.
    """
    repo = repository_repo.get(db=db, id=id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo = repository_repo.update(db=db, db_obj=repo, obj_in=repository_in)
    return repo

@router.delete("/{id}", response_model=Repository)
def delete_repository(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Delete a repository.
    """
    repo = repository_repo.get(db=db, id=id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo = repository_repo.remove(db=db, id=id)
    return repo

@router.get("/{id}/snapshots")
def list_snapshots(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    List all commit/ingestion snapshots for a given repository.
    """
    from backend.database.models.models import RepositorySnapshot
    snapshots = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == id).order_by(RepositorySnapshot.indexed_at.desc()).all()
    return [
        {
            "snapshot_id": str(s.snapshot_id),
            "repository_id": str(s.repository_id),
            "commit_hash": s.commit_hash,
            "branch": s.branch,
            "commit_message": s.commit_message,
            "author": s.author,
            "indexed_at": s.indexed_at,
            "is_latest": s.is_latest
        }
        for s in snapshots
    ]

@router.get("/{id}/latest-snapshot")
def get_latest_snapshot(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Get the latest ingestion snapshot ID and metadata for a repository.
    """
    from backend.database.models.models import RepositorySnapshot
    snap = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == id).order_by(RepositorySnapshot.indexed_at.desc()).first()
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot found for this repository. Please trigger ingestion first.")
    return {
        "snapshot_id": str(snap.snapshot_id),
        "repository_id": str(snap.repository_id),
        "commit_hash": snap.commit_hash,
        "branch": snap.branch,
        "indexed_at": snap.indexed_at,
        "is_latest": snap.is_latest
    }
