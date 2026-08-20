import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.api.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Operational"])


@router.get("/health")
def get_health(db: Session = Depends(get_db)) -> Any:
    """
    Check system and database health.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}


@router.get("/metrics", dependencies=[Depends(require_role(["manager", "admin"]))])
def get_metrics(db: Session = Depends(get_db)) -> Any:
    """
    Retrieve application operational metrics from the database.
    Calculates summary metrics and a time-series array for charting.
    """
    from sqlalchemy import Date, Integer, cast, func

    from backend.database.models.models import (
        EvaluationResult,
        EvaluationRun,
        QueryHistory,
    )

    try:
        # --- SUMMARY METRICS ---
        total_evals = db.query(func.count(EvaluationResult.result_id)).scalar() or 0
        passed_evals = (
            db.query(func.count(EvaluationResult.result_id))
            .filter(EvaluationResult.passed.is_(True))
            .scalar()
            or 0
        )
        tsr = (passed_evals / total_evals * 100) if total_evals > 0 else 0.0

        avg_faithfulness = (
            db.query(func.avg(EvaluationResult.faithfulness)).scalar() or 0.0
        )
        avg_latency = db.query(func.avg(EvaluationResult.latency_ms)).scalar() or 0.0
        total_queries = db.query(func.count(QueryHistory.query_id)).scalar() or 0

        # New Enterprise Metrics
        avg_relevancy = (
            db.query(func.avg(EvaluationResult.answer_relevancy)).scalar() or 0.0
        )
        avg_context_precision = (
            db.query(func.avg(EvaluationResult.context_precision)).scalar() or 0.0
        )
        avg_recall = db.query(func.avg(EvaluationResult.context_recall)).scalar() or 0.0
        avg_llm_confidence = (
            db.query(func.avg(EvaluationResult.llm_confidence)).scalar() or 0.0
        )

        # --- TIME-SERIES METRICS ---
        # 1. Queries per day
        query_stats = (
            db.query(
                cast(QueryHistory.created_at, Date).label("date"),
                func.count(QueryHistory.query_id).label("queries"),
                func.avg(QueryHistory.latency_ms).label("avg_latency"),
            )
            .group_by(cast(QueryHistory.created_at, Date))
            .all()
        )

        # 2. Evaluations per day
        eval_stats = (
            db.query(
                cast(EvaluationRun.started_at, Date).label("date"),
                func.count(EvaluationResult.result_id).label("total_evals"),
                func.sum(cast(EvaluationResult.passed, Integer)).label("passed_evals"),
                func.avg(EvaluationResult.faithfulness).label("avg_faithfulness"),
                func.avg(EvaluationResult.answer_relevancy).label("avg_relevancy"),
            )
            .join(
                EvaluationRun,
                EvaluationResult.evaluation_id == EvaluationRun.evaluation_id,
            )
            .group_by(cast(EvaluationRun.started_at, Date))
            .all()
        )

        # Merge data by date
        timeseries_dict = {}

        for q in query_stats:
            date_str = str(q.date)
            timeseries_dict[date_str] = {
                "date": date_str,
                "queries": q.queries,
                "avg_latency": float(q.avg_latency) if q.avg_latency else 0.0,
                "tsr": 0.0,
                "faithfulness": 0.0,
                "relevancy": 0.0,
            }

        for e in eval_stats:
            date_str = str(e.date)
            if date_str not in timeseries_dict:
                timeseries_dict[date_str] = {
                    "date": date_str,
                    "queries": 0,
                    "avg_latency": 0.0,
                }

            day_tsr = (
                (int(e.passed_evals) / int(e.total_evals) * 100)
                if e.total_evals and e.passed_evals
                else 0.0
            )
            timeseries_dict[date_str]["tsr"] = round(day_tsr, 2)
            timeseries_dict[date_str]["faithfulness"] = round(
                float(e.avg_faithfulness or 0), 4
            )
            timeseries_dict[date_str]["relevancy"] = round(
                float(e.avg_relevancy or 0), 4
            )

        # Sort chronologically
        timeseries = sorted(timeseries_dict.values(), key=lambda x: x["date"])

        response = {
            "summary": {
                "total_queries": total_queries,
                "total_evaluations": total_evals,
                "task_success_rate": round(tsr, 2),
                "faithfulness": round(avg_faithfulness, 4),
                "answer_relevancy": round(avg_relevancy, 4),
                "context_precision": round(avg_context_precision, 4),
                "latency_ms": round(avg_latency, 2),
                "recall": round(avg_recall, 4),
                "llm_confidence": round(avg_llm_confidence, 4),
            },
            "timeseries": timeseries,
        }
        logger.info(f"Metrics API response: {response}")
        return response
    except Exception as e:
        logger.error(f"Metrics API error: {str(e)}")
        return {"error": str(e)}


@router.get("/repositories/{id}/explorer")
def get_repository_explorer(id: UUID, db: Session = Depends(get_db)) -> Any:
    """
    Repository explorer endpoint to fetch directory trees.
    """
    from backend.database.models.models import RepositoryFile, RepositorySnapshot

    latest_snapshot = (
        db.query(RepositorySnapshot).filter_by(repository_id=id, is_latest=True).first()
    )

    if not latest_snapshot:
        return {"error": "No ingested snapshot found for this repository."}

    files = (
        db.query(RepositoryFile)
        .filter_by(snapshot_id=latest_snapshot.snapshot_id)
        .all()
    )

    tree = {}
    for rf in files:
        if not rf.path:
            continue

        clean_path = rf.path.replace("\\", "/")
        parts = clean_path.split("/")

        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {"type": "directory", "name": part, "children": {}}
            current = current[part]["children"]

        current[parts[-1]] = {
            "type": "file",
            "name": rf.filename,
            "file_id": str(rf.file_id),
            "extension": rf.extension,
            "size_bytes": rf.size_bytes,
            "language": rf.language,
        }

    return {"tree": tree}
