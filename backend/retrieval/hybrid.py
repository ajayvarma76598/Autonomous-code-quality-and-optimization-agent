"""
Hybrid Retriever — Full Production Pipeline
============================================

Retrieval Flow:
  1. Intent Detection → select content_type collection
  2. Query Expansion
  3. BM25 (keyword, snapshot-isolated)
  4. Vector Search (semantic, snapshot-isolated, collection-filtered)
  5. Dependency Graph Expansion (parent classes, called services)
  6. RRF Fusion + Metadata Path Boosting
  7. Diversification (max chunks per file)
  8. LLM Cross-Encoder Re-ranking
  9. Return Top-K Evidence
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.retrieval.bm25 import bm25_retriever
from backend.retrieval.dependency_graph import dependency_graph
from backend.retrieval.models import RetrievedContext
from backend.retrieval.reranker import reranker
from backend.retrieval.vector_store import vector_store

# ---------------------------------------------------------------------------
# Intent → Content-Type Routing
# ---------------------------------------------------------------------------

_INTENT_ROUTES: dict[str, str] = {
    # Architecture / design questions
    "architecture": "architecture",
    "design": "architecture",
    "overview": "architecture",
    "readme": "architecture",
    "adr": "architecture",
    "diagram": "architecture",
    "microservice": "architecture",
    "service": "architecture",
    # API / endpoint questions
    "api": "api",
    "endpoint": "api",
    "controller": "api",
    "route": "api",
    "rest": "api",
    "swagger": "api",
    "openapi": "api",
    "request": "api",
    "response": "api",
    # Config
    "config": "config",
    "configuration": "config",
    "yaml": "config",
    "docker": "config",
    "kubernetes": "config",
    "k8s": "config",
    "terraform": "config",
    "env": "config",
    "property": "config",
}


def _detect_content_type(query: str) -> str | None:
    """Return the best content_type collection for the query, or None for all."""
    q_lower = query.lower()
    for keyword, ctype in _INTENT_ROUTES.items():
        if keyword in q_lower:
            return ctype
    return None  # search all collections


def _expand_query(query: str, content_type: str | None) -> str:
    """Expand query with domain vocabulary for better BM25 recall."""
    parts = [query]
    q_lower = query.lower()

    if (
        content_type == "architecture"
        or "architecture" in q_lower
        or "summary" in q_lower
    ):
        parts.append("README architecture design ADR microservice overview")
    if content_type == "api" or any(
        w in q_lower for w in ("api", "endpoint", "controller")
    ):
        parts.append("RestController PostMapping GetMapping route handler endpoint")
    if "database" in q_lower or "schema" in q_lower or "sql" in q_lower:
        parts.append("schema SQL CREATE TABLE migration DDL repository")
    if "payment" in q_lower:
        parts.append("PaymentService PaymentController Stripe transaction process")
    if "auth" in q_lower or "login" in q_lower:
        parts.append("AuthService JWT token authentication login security")
    if "test" in q_lower:
        parts.append("test unit integration assertion mock stub")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# RRF Fusion
# ---------------------------------------------------------------------------

_RRF_K = 60

_EXTENSION_BOOST: dict[str, float] = {
    ".java": 0.60,
    ".py": 0.60,
    ".ts": 0.55,
    ".kt": 0.55,
    ".go": 0.55,
    ".cs": 0.55,
    ".js": 0.50,
    ".sql": 0.45,
    ".md": 0.20,
}

_DOWNWEIGHT_PATTERNS = ["pdf", "guidelines", "capstone", "dataset"]


class HybridRetriever:
    def __init__(self):
        self.k = _RRF_K
        self._llm = None

    def set_llm(self, llm) -> None:
        self._llm = llm
        reranker.set_llm(llm)

    # ------------------------------------------------------------------
    # Main retrieve
    # ------------------------------------------------------------------

    def retrieve(
        self,
        db: Session,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        snapshot_id: Any | None = None,
        use_reranker: bool = True,
    ) -> list[RetrievedContext]:
        """
        Full hybrid retrieval pipeline.
        """
        # 1. Detect intent → collection
        content_type = _detect_content_type(query)

        # 2. Expand query
        expanded_query = _expand_query(query, content_type)

        # 3. BM25 (keyword)
        if db:
            bm25_retriever.fit_from_db(db, snapshot_id=snapshot_id)
        bm25_results = bm25_retriever.retrieve(expanded_query, top_k=top_k * 4)

        # 4. Vector search (semantic, collection-filtered)
        vector_results = vector_store.retrieve(
            db,
            query_embedding,
            top_k=top_k * 4,
            snapshot_id=snapshot_id,
            content_type=content_type,
        )

        # 5. Dependency graph expansion — augment vector results
        if vector_results:
            vector_results = self._expand_with_graph(
                db, vector_results, query_embedding, snapshot_id, top_k
            )

        # 6. RRF Fusion + Path Boosting
        fused = self._rrf_fuse(bm25_results, vector_results, top_k=top_k * 2)

        # 7. Diversification
        diverse = self._diversify(fused, max_per_file=3, target=top_k * 2)

        # 8. LLM Cross-Encoder Re-ranking
        if use_reranker and self._llm and diverse:
            diverse = reranker.rerank(query, diverse, top_k=top_k)
        else:
            diverse = diverse[:top_k]

        return diverse

    # ------------------------------------------------------------------
    # Graph Expansion
    # ------------------------------------------------------------------

    def _expand_with_graph(
        self,
        db: Session,
        vector_results: list[dict[str, Any]],
        query_embedding: list[float],
        snapshot_id: Any | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch parent classes and called services for retrieved symbols.
        Adds their chunks to the result set (if available in DB).
        """
        symbol_names = [
            r.get("metadata", {}).get("symbol_name")
            for r in vector_results
            if r.get("metadata", {}).get("symbol_name")
        ]
        if not symbol_names:
            return vector_results

        expanded_names = dependency_graph.expand_context(
            symbol_names,
            depth=1,
            edge_types=["EXTENDS", "IMPLEMENTS", "CALLS", "INJECTS"],
        )
        if not expanded_names:
            return vector_results

        # Fetch chunks for expanded symbols from DB
        try:
            from uuid import UUID

            from sqlalchemy import select

            from backend.database.models.models import DocumentChunk, RepositoryFile

            snap_uuid = UUID(str(snapshot_id)) if snapshot_id else None
            for sym_name in expanded_names[:5]:  # cap extra fetches
                stmt = (
                    select(DocumentChunk)
                    .join(
                        RepositoryFile, DocumentChunk.file_id == RepositoryFile.file_id
                    )
                    .where(DocumentChunk.chunk_type == "raw_code")
                )
                if snap_uuid:
                    stmt = stmt.where(RepositoryFile.snapshot_id == snap_uuid)

                rows = db.execute(stmt).scalars().all()
                for chunk in rows:
                    meta = chunk.metadata_ or {}
                    if meta.get("symbol_name") == sym_name:
                        vector_results.append(
                            {
                                "chunk_id": str(chunk.chunk_id),
                                "content": chunk.content,
                                "chunk_type": chunk.chunk_type,
                                "repository_path": meta.get("path", ""),
                                "score": 0.60,
                                "vector_score": 0.60,
                                "metadata": meta,
                            }
                        )
                        break  # one chunk per symbol is enough
        except Exception:
            pass

        return vector_results

    # ------------------------------------------------------------------
    # RRF Fusion
    # ------------------------------------------------------------------

    def _rrf_fuse(
        self,
        bm25_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]],
        top_k: int,
    ) -> list[RetrievedContext]:
        rrf_scores: dict[str, float] = {}
        bm25_scores: dict[str, float] = {}
        vec_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(bm25_results or []):
            if not doc or not isinstance(doc, dict):
                continue
            doc_id = doc.get("chunk_id") or str(rank)
            doc_map[doc_id] = doc
            raw = float(doc.get("score") or (1.0 / (rank + 1)))
            bm25_scores[doc_id] = raw
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.k + rank + 1)

        for rank, doc in enumerate(vector_results or []):
            if not doc or not isinstance(doc, dict):
                continue
            doc_id = doc.get("chunk_id") or f"v_{rank}"
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            raw = float(
                doc.get("vector_score") or doc.get("score") or (1.0 / (rank + 1))
            )
            vec_scores[doc_id] = raw
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.k + rank + 1)

        # Path boosting
        for doc_id, doc in doc_map.items():
            meta = doc.get("metadata") or {}
            path = (meta.get("path") or doc.get("repository_path") or "").lower()

            boost = 1.0
            for file_ext, b in _EXTENSION_BOOST.items():
                if path.endswith(file_ext):
                    boost += b
                    break
            if any(p in path for p in _DOWNWEIGHT_PATTERNS):
                boost *= 0.50

            # Prefer raw_code over metadata chunks
            chunk_type = doc.get("chunk_type", "raw_code")
            if chunk_type == "raw_code":
                boost += 0.10
            elif chunk_type == "summary":
                boost += 0.05

            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) * boost

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        results: list[RetrievedContext] = []
        for doc_id, rrf_val in sorted_docs[:top_k]:
            doc = doc_map[doc_id].copy()
            meta = doc.get("metadata") or {}
            repo_path = meta.get("path") or doc.get("repository_path") or "unknown"

            # Filter out internal framework paths
            clean = str(repo_path).replace("\\", "/")
            if any(
                d in clean
                for d in [
                    "backend/agents/",
                    "backend/retrieval/",
                    "backend/tools/",
                    "backend/workflows/",
                    "backend/services/",
                ]
            ):
                continue

            normalized = min(0.99, round(rrf_val * 25.0, 4))

            ctx = RetrievedContext(
                chunk_id=doc_id,
                document_id=doc.get("document_id") or meta.get("document_id"),
                module=meta.get("module") or repo_path.split("/")[-1].split(".")[0],
                function=meta.get("function") or meta.get("symbol_name"),
                symbol_name=meta.get("symbol_name"),
                start_line=meta.get("start_line"),
                end_line=meta.get("end_line"),
                evidence=[doc.get("content") or ""],
                related_symbols=meta.get("related_symbols") or [],
                repository_path=repo_path,
                bm25_score=bm25_scores.get(doc_id),
                vector_score=vec_scores.get(doc_id),
                rrf_score=rrf_val,
                score=normalized,
                confidence_score=normalized,
            )
            results.append(ctx)

        return results

    # ------------------------------------------------------------------
    # Diversification
    # ------------------------------------------------------------------

    @staticmethod
    def _diversify(
        results: list[RetrievedContext],
        max_per_file: int = 3,
        target: int = 10,
    ) -> list[RetrievedContext]:
        file_counts: dict[str, int] = {}
        diverse: list[RetrievedContext] = []
        for ctx in results:
            fp = ctx.repository_path or "unknown"
            if file_counts.get(fp, 0) >= max_per_file and len(diverse) >= target:
                continue
            file_counts[fp] = file_counts.get(fp, 0) + 1
            diverse.append(ctx)
        return diverse


hybrid_retriever = HybridRetriever()
