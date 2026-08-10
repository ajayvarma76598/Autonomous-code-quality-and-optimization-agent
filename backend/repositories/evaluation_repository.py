import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from backend.database.models.models import EvaluationRun, EvaluationResult

logger = logging.getLogger(__name__)

class EvaluationRepository:
    def __init__(self):
        pass

    def save_evaluation(
        self,
        db: Session,
        workflow_id: Optional[UUID],
        metrics_data: dict,
        passed: bool,
        benchmark_id: Optional[UUID] = None
    ) -> EvaluationResult:
        """
        Persists the structured evaluation metrics into the database.
        Creates an EvaluationRun (if it doesn't exist for the workflow) and attaches an EvaluationResult.
        """
        try:
            # 1. Ensure an EvaluationRun exists
            eval_run = None
            if workflow_id:
                eval_run = db.query(EvaluationRun).filter(EvaluationRun.workflow_id == workflow_id).first()
                
            if not eval_run:
                eval_run = EvaluationRun(
                    workflow_id=workflow_id,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc)
                )
                db.add(eval_run)
                db.flush() # flush to generate evaluation_id

            # Calculate Latency (ms)
            now_utc = datetime.now(timezone.utc)
            eval_run.completed_at = now_utc
            latency_ms = int((now_utc - eval_run.started_at).total_seconds() * 1000)

            # 2. Create the EvaluationResult attached to the Run
            eval_result = EvaluationResult(
                evaluation_id=eval_run.evaluation_id,
                faithfulness=metrics_data.get('faithfulness', 0.0),
                answer_relevancy=metrics_data.get('relevancy', 0.0),
                context_precision=metrics_data.get('context_precision', 0.0),
                latency_ms=latency_ms,
                context_recall=metrics_data.get('recall', 0.0),
                llm_confidence=metrics_data.get('confidence', 0.0),
                task_success_rate=1.0 if passed else 0.0,
                passed=passed
            )
            db.add(eval_result)
            db.commit()
            
            logger.info(f"Successfully persisted evaluation metrics for workflow {workflow_id}")
            return eval_result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist evaluation metrics: {e}")
            raise

evaluation_repository = EvaluationRepository()
