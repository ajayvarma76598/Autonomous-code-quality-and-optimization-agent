from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.database.models.models import WorkflowRun
from backend.repositories.base_repository import BaseRepository
from backend.schemas.execution import WorkflowRun as WorkflowRunSchema
from backend.schemas.execution import WorkflowRunCreate

# In-file repository instantiation for simplicity
workflow_repo = BaseRepository[WorkflowRun, WorkflowRunCreate, Any](WorkflowRun)

router = APIRouter(prefix="/executions", tags=["Executions"])


@router.post("/", response_model=WorkflowRunSchema, status_code=status.HTTP_201_CREATED)
def create_execution(
    *, db: Session = Depends(get_db), execution_in: WorkflowRunCreate
) -> Any:
    """
    Start a new workflow execution trace.
    """
    db_exec = workflow_repo.create(db=db, obj_in=execution_in)
    return db_exec


@router.get("/{id}", response_model=WorkflowRunSchema)
def read_execution(*, db: Session = Depends(get_db), id: UUID) -> Any:
    """
    Get workflow execution status.
    """
    db_exec = workflow_repo.get(db=db, id=id)
    if not db_exec:
        raise HTTPException(status_code=404, detail="Execution not found")
    return db_exec
