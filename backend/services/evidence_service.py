import logging
from typing import Dict, Any, Optional
from backend.services.base_service import BaseService
from backend.models.evidence import EvidenceContext, EvidenceBlock
from backend.services.evidence.sql_provider import sql_provider
from backend.services.evidence.sonar_provider import sonar_provider
from backend.services.evidence.metadata_provider import metadata_provider
from backend.services.evidence.vector_provider import vector_provider

logger = logging.getLogger(__name__)

class EvidenceService(BaseService):
    def __init__(self):
        super().__init__("EvidenceService")
        # Basic in-memory cache keyed by (agent_type, repository_id, analysis_id)
        self._cache = {}
        
    def gather_evidence(self, agent_type: str, repository_id: str, analysis_id: str, query: Optional[str] = None, top_k: int = 5) -> EvidenceContext:
        """
        Gathers EvidenceContext tailored to the requesting agent type.
        Implements lazy evaluation and caching.
        """
        cache_key = f"{agent_type}_{repository_id}_{analysis_id}_{top_k}"
        if cache_key in self._cache:
            logger.info(f"Returning cached evidence for {cache_key}")
            return self._cache[cache_key]

        def _gather() -> EvidenceContext:
            context = EvidenceContext()
            logger.info(f"[EVIDENCE GATHERING STARTED (PARALLEL)] Agent Type: '{agent_type}' | Repo: '{repository_id}' | Analysis: '{analysis_id}' | Top_K: {top_k}")
            
            import concurrent.futures
            
            futures = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # 1. Metadata Provider
                if agent_type in ["repository", "documentation"]:
                    futures["metadata"] = executor.submit(metadata_provider.fetch, repository_id, analysis_id)
                    
                # 2. SQL & Dependency Graph Provider
                if agent_type in ["repository", "architecture", "coverage", "performance"]:
                    futures["sql"] = executor.submit(sql_provider.fetch, repository_id, analysis_id, query=query, top_k=top_k)
                    
                # 3. SonarQube Provider
                if agent_type in ["coverage", "performance", "quality"]:
                    futures["sonar"] = executor.submit(sonar_provider.fetch, repository_id, analysis_id)
                    
                # 4. Vector & Hybrid Search Provider
                if query and agent_type in ["repository", "architecture", "performance", "documentation"]:
                    futures["vector"] = executor.submit(vector_provider.fetch, repository_id, analysis_id, query=query, top_k=top_k)

            # Collect parallel results
            if "metadata" in futures:
                context.repository_metadata = futures["metadata"].result()
            if "sql" in futures:
                fetched_sql = futures["sql"].result()
                if fetched_sql:
                    if agent_type == "architecture":
                        context.dependency_graph = fetched_sql
                        context.sql_results = None
                    else:
                        context.sql_results = fetched_sql
            if "sonar" in futures:
                context.sonar_metrics = futures["sonar"].result()
            if "vector" in futures:
                context.retrieved_chunks = futures["vector"].result()

            return context
            
        result = self.execute(_gather).data
        from backend.services.evidence.validator import evidence_validator
        validated_result = evidence_validator.validate(result, agent_type)
        self._cache[cache_key] = validated_result
        return validated_result

evidence_service = EvidenceService()
