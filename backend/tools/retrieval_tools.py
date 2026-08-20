from typing import Any

from langchain_core.tools import tool

from backend.database.session import SessionLocal
from backend.retrieval.hybrid import hybrid_retriever
from backend.services.retrieval_cache import retrieval_cache


@tool
def hybrid_search(
    query: str, query_embedding: list[float] = None, top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Performs a Hybrid RAG search (BM25 + pgvector) across the repository context using Reciprocal Rank Fusion.
    If query_embedding is not provided, an empty vector search fallback occurs.
    """
    # Check cache first
    cached_results = retrieval_cache.get(query, top_k)
    if cached_results is not None:
        return cached_results

    db = SessionLocal()
    try:
        if not query_embedding:
            from backend.services.embedding_service import embedding_service

            query_embedding = embedding_service.embed_query(query)
        results = hybrid_retriever.retrieve(db, query, query_embedding, top_k)
        retrieval_cache.set(query, top_k, results)
        return [
            r.model_dump()
            if hasattr(r, "model_dump")
            else r.dict()
            if hasattr(r, "dict")
            else r
            for r in results
        ]
    finally:
        db.close()
