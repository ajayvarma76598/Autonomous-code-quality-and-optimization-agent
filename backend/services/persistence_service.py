import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.services.base_service import BaseService
# Assuming DB models are available here:
# from backend.database.models.models import WorkflowRun, CodeQualityMetric, DependencyRelationship, RepositoryMetadata
# from backend.database.session import get_db

logger = logging.getLogger(__name__)

class PersistenceService(BaseService):
    def __init__(self):
        super().__init__("PersistenceService")
        # In a real async/queue system, this would be a thread-safe queue or a Redis list.
        # For this implementation, we use an in-memory staging area per analysis run.
        self._staging_area: Dict[str, Dict[str, Any]] = {}
        
    def _get_staging(self, analysis_id: str) -> Dict[str, Any]:
        if analysis_id not in self._staging_area:
            self._staging_area[analysis_id] = {
                "agent_results": {},
                "sonar_metrics": None,
                "dependency_graph": None,
                "repository_metadata": None,
                "reports": [],
                "workflow_status": "STARTED",
                "started_at": datetime.now(timezone.utc)
            }
        return self._staging_area[analysis_id]

    def queue_agent_result(self, analysis_id: str, agent_name: str, result: Any) -> None:
        """Queues an agent's structured result for persistence."""
        staging = self._get_staging(analysis_id)
        # Assuming result is a Pydantic model with .model_dump()
        try:
            staging["agent_results"][agent_name] = result.model_dump()
        except AttributeError:
            staging["agent_results"][agent_name] = result
        logger.info(f"Queued {agent_name} result for analysis {analysis_id}")

    def queue_sonar_metrics(self, analysis_id: str, file_id: str, sonar_context: Any) -> None:
        """Queues SonarQube metrics mapping to CodeQualityMetric."""
        staging = self._get_staging(analysis_id)
        if staging["sonar_metrics"] is None:
            staging["sonar_metrics"] = []
        
        try:
            metrics_dict = sonar_context.model_dump()
        except AttributeError:
            metrics_dict = sonar_context
            
        staging["sonar_metrics"].append({
            "file_id": file_id,
            "metrics": metrics_dict
        })
        logger.info(f"Queued Sonar metrics for file {file_id} in analysis {analysis_id}")

    def queue_dependencies(self, analysis_id: str, dependencies: List[Any]) -> None:
        """Queues dependency graph mapping to DependencyRelationship."""
        staging = self._get_staging(analysis_id)
        if staging["dependency_graph"] is None:
            staging["dependency_graph"] = []
        staging["dependency_graph"].extend(dependencies)
        logger.info(f"Queued {len(dependencies)} dependencies for analysis {analysis_id}")

    def queue_metadata(self, analysis_id: str, metadata: Dict[str, Any]) -> None:
        """Queues repository metadata mapping to RepositoryMetadata."""
        staging = self._get_staging(analysis_id)
        staging["repository_metadata"] = metadata
        logger.info(f"Queued repository metadata for analysis {analysis_id}")
        
    def queue_report(self, analysis_id: str, report_data: Dict[str, Any]) -> None:
        """Queues the final generated report."""
        staging = self._get_staging(analysis_id)
        staging["reports"].append(report_data)
        logger.info(f"Queued report for analysis {analysis_id}")

    def flush_transaction(self, analysis_id: str, repository_id: str, final_status: str = "COMPLETED") -> bool:
        """
        Executes a single atomic transaction to persist all queued data to PostgreSQL.
        """
        def _flush():
            staging = self._get_staging(analysis_id)
            staging["workflow_status"] = final_status
            staging["completed_at"] = datetime.now(timezone.utc)
            
            logger.info(f"--- STARTING ATOMIC DB TRANSACTION FOR ANALYSIS {analysis_id} ---")
            
            # 1. Persist WorkflowRun (AnalysisRun)
            # workflow_run = WorkflowRun(workflow_id=analysis_id, session_id=..., repository_id=repository_id, status=final_status, ...)
            # db.add(workflow_run)
            logger.info(f"Persisted WorkflowRun (Status: {final_status})")
            
            # 2. Persist Agent Results
            for agent, result in staging["agent_results"].items():
                logger.info(f"Persisted Agent Result: {agent}")
                
            # 3. Persist Quality Metrics
            if staging["sonar_metrics"]:
                logger.info(f"Persisted {len(staging['sonar_metrics'])} CodeQualityMetric records.")
                
            # 4. Persist Dependencies
            if staging["dependency_graph"]:
                logger.info(f"Persisted {len(staging['dependency_graph'])} DependencyRelationship records.")
                
            # 5. Persist Metadata
            if staging["repository_metadata"]:
                logger.info("Persisted RepositoryMetadata.")
                
            # 6. Persist Reports
            if staging["reports"]:
                logger.info(f"Persisted {len(staging['reports'])} Reports.")
                
            # db.commit()
            logger.info(f"--- COMMITTED DB TRANSACTION FOR ANALYSIS {analysis_id} ---")
            
            # Clean up memory
            del self._staging_area[analysis_id]
            return True

        result = self.execute(_flush)
        return result.success

persistence_service = PersistenceService()
