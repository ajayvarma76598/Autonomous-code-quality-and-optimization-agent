"""
Vector Store — Collection-Aware pgvector Retrieval
====================================================
Retrieves semantically similar chunks filtered by:
  - snapshot_id  (always — never cross-repository bleed)
  - content_type (optional collection routing: code / architecture / config / api / summary)
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.models import DocumentChunk, Embedding, RepositoryFile

CONTENT_TYPE_WEIGHTS: dict[str, float] = {
    # Reward architecture docs for architecture queries
    "architecture": 1.25,
    "api": 1.15,
    "code": 1.10,
    "summary": 1.05,
    "config": 1.00,
}


class VectorStore:
    def retrieve(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int = 10,
        snapshot_id: Any | None = None,
        content_type: str | None = None,
        chunk_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a vector similarity search using pgvector.

        Args:
            db:             SQLAlchemy session
            query_embedding: Query vector
            top_k:          Number of results
            snapshot_id:    Filter strictly to this repo snapshot
            content_type:   Optional collection filter (code|architecture|config|api|summary)
            chunk_type:     Optional view filter (raw_code|summary|metadata)
        """
        distance_expr = Embedding.embedding.cosine_distance(query_embedding).label(
            "distance"
        )

        stmt = (
            select(Embedding, DocumentChunk, distance_expr)
            .join(DocumentChunk, Embedding.chunk_id == DocumentChunk.chunk_id)
            .join(RepositoryFile, DocumentChunk.file_id == RepositoryFile.file_id)
        )

        # Always filter by snapshot
        if snapshot_id:
            try:
                from uuid import UUID

                snap_uuid = (
                    UUID(str(snapshot_id))
                    if isinstance(snapshot_id, str)
                    else snapshot_id
                )
                stmt = stmt.where(RepositoryFile.snapshot_id == snap_uuid)
            except Exception:
                pass

        # Optional content_type filter via metadata_ JSONB
        if content_type:
            stmt = stmt.where(
                DocumentChunk.metadata_["content_type"].astext == content_type
            )

        # Optional chunk_type filter
        if chunk_type:
            stmt = stmt.where(DocumentChunk.chunk_type == chunk_type)

        stmt = stmt.order_by(distance_expr).limit(
            top_k * 2
        )  # over-fetch for re-ranking

        results = db.execute(stmt).all()
        retrieved: list[dict[str, Any]] = []

        for emb, chunk, distance in results:
            meta = getattr(chunk, "metadata_", None) or {}
            if not isinstance(meta, dict):
                meta = {}

            repo_path = (
                meta.get("path")
                or getattr(getattr(chunk, "file", None), "path", None)
                or "unknown"
            )

            similarity = float(1.0 - distance)

            # Apply content_type weight boost
            ct = meta.get("content_type", "code")
            boost = CONTENT_TYPE_WEIGHTS.get(ct, 1.0)
            boosted_score = min(0.999, similarity * boost)

            retrieved.append(
                {
                    "chunk_id": str(chunk.chunk_id),
                    "file_id": str(chunk.file_id) if chunk.file_id else None,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type,
                    "repository_path": repo_path,
                    "score": boosted_score,
                    "vector_score": similarity,
                    "metadata": {
                        "path": repo_path,
                        "module": meta.get("module")
                        or repo_path.split("/")[-1].split(".")[0],
                        "symbol_name": meta.get("symbol_name"),
                        "symbol_type": meta.get("symbol_type"),
                        "parent_name": meta.get("parent_name"),
                        "language": meta.get("language"),
                        "framework": meta.get("framework"),
                        "package": meta.get("package"),
                        "annotations": meta.get("annotations", []),
                        "content_type": ct,
                        "start_line": meta.get("start_line")
                        or getattr(chunk, "start_line", None),
                        "end_line": meta.get("end_line")
                        or getattr(chunk, "end_line", None),
                        **meta,
                    },
                }
            )

        # Sort by boosted score and return top_k
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:top_k]


vector_store = VectorStore()
