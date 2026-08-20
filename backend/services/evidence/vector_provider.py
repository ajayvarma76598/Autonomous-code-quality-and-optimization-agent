import logging

from backend.models.evidence import EvidenceBlock
from backend.services.evidence.base_provider import BaseEvidenceProvider

logger = logging.getLogger(__name__)


class VectorProvider(BaseEvidenceProvider):
    @property
    def provider_name(self) -> str:
        return "pgvector / HybridSearch"

    @property
    def default_confidence(self) -> float:
        return 0.85

    def fetch(
        self, repository_id: str, analysis_id: str | None = None, **kwargs
    ) -> EvidenceBlock | None:
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", 5)
        if not query:
            return None

        try:
            from backend.database.session import SessionLocal
            from backend.retrieval.hybrid import hybrid_retriever
            from backend.services.embedding_service import embedding_service

            db = SessionLocal()
            try:
                # 0. Resolve target repository snapshot_id
                from backend.database.models.models import RepositorySnapshot

                snap = None
                if repository_id:
                    try:
                        from uuid import UUID

                        repo_uuid = UUID(str(repository_id))
                        # Check if it was accidentally passed as a snapshot_id
                        snap = (
                            db.query(RepositorySnapshot)
                            .filter(RepositorySnapshot.snapshot_id == repo_uuid)
                            .first()
                        )
                        if not snap:
                            # Fallback to checking as a repository_id
                            snap = (
                                db.query(RepositorySnapshot)
                                .filter(RepositorySnapshot.repository_id == repo_uuid)
                                .order_by(RepositorySnapshot.indexed_at.desc())
                                .first()
                            )
                    except Exception:
                        snap = None

                if not snap:
                    # If we have a repository_id but no snapshot exists (e.g. ingestion failed), DO NOT fallback to another repo!
                    if repository_id:
                        logger.warning(
                            f"No snapshot found for repository {repository_id}. Skipping vector retrieval."
                        )
                        return None
                    # Only fallback to global latest if NO repository_id was provided (e.g. global search)
                    snap = (
                        db.query(RepositorySnapshot)
                        .order_by(RepositorySnapshot.indexed_at.desc())
                        .first()
                    )

                snapshot_id = snap.snapshot_id if snap else None

                # 1. Embed query vector
                query_embedding = embedding_service.embed_query(query)

                # 2. Inject LLM into retriever for cross-encoder re-ranking
                try:
                    from backend.services.llm import llm_service

                    llm = (
                        llm_service.get_llm()
                        if hasattr(llm_service, "get_llm")
                        else None
                    )
                    if llm:
                        hybrid_retriever.set_llm(llm)
                except Exception:
                    pass

                # 3. Execute Hybrid Retrieval (BM25 + pgvector + graph expansion + re-ranking)
                chunks = hybrid_retriever.retrieve(
                    db, query, query_embedding, top_k=top_k, snapshot_id=snapshot_id
                )

                # Filter out internal system paths from repository evidence
                clean_chunks = []
                for c in chunks:
                    clean_path = str(c.repository_path).replace("\\", "/")
                    if any(
                        internal_dir in clean_path
                        for internal_dir in [
                            "backend/agents/",
                            "backend/retrieval/",
                            "backend/tools/",
                            "backend/workflows/",
                            "backend/services/",
                        ]
                    ):
                        continue
                    clean_chunks.append(c)

                if clean_chunks:
                    avg_score = sum([c.score for c in clean_chunks]) / len(clean_chunks)
                    return EvidenceBlock(
                        data=clean_chunks,
                        confidence_score=round(float(avg_score * 20.0), 2)
                        if avg_score < 1.0
                        else 0.85,
                        provider_name=self.provider_name,
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"VectorProvider hybrid retrieval error for '{query}': {e}")

        return None


vector_provider = VectorProvider()
