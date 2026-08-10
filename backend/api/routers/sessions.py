from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from backend.api.dependencies import get_db
from backend.repositories.session_repository import session_repo
from backend.repositories.query_repository import query_repo
from backend.schemas.session import Session as SessionSchema, SessionCreate, QueryHistory

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("/", response_model=List[SessionSchema])
def list_sessions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve all sessions.
    """
    return session_repo.get_multi(db=db, skip=skip, limit=limit)

@router.post("/", response_model=SessionSchema, status_code=status.HTTP_201_CREATED)
def create_session(
    *,
    db: Session = Depends(get_db),
    session_in: SessionCreate
) -> Any:
    """
    Create a new Chat/Agent session.
    """
    db_session = session_repo.create(db=db, obj_in=session_in)
    return db_session

@router.get("/{id}", response_model=SessionSchema)
def read_session(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Get session by ID.
    """
    db_session = session_repo.get(db=db, id=id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session

@router.get("/{id}/history", response_model=List[QueryHistory])
def get_session_history(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Get the query history for a given session.
    """
    db_session = session_repo.get(db=db, id=id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return query_repo.get_by_session(db=db, session_id=str(id))

@router.delete("/{id}", response_model=SessionSchema)
def delete_session(
    *,
    db: Session = Depends(get_db),
    id: UUID
) -> Any:
    """
    Delete a session.
    """
    db_session = session_repo.get(db=db, id=id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_session = session_repo.remove(db=db, id=id)
    return db_session
