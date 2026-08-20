"""
LLM-Based Cross-Encoder Re-ranker
===================================
Scores each (query, chunk_content) pair using Azure OpenAI to produce
a final relevance ordering. Used as the last step in the retrieval pipeline
before returning Top-K evidence to the agent.

Falls back to RRF rank order if LLM is unavailable or quota is exhausted.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_RERANK_SYSTEM = (
    "You are a relevance judge for a code-search system. "
    "Given a user query and a retrieved code/documentation chunk, "
    "score the relevance from 0 to 10 (10 = perfectly relevant). "
    "Reply with ONLY the integer score. No explanation."
)

_RERANK_USER_TMPL = """Query: {query}

Chunk ({chunk_type}, {language}):
{content}

Score (0-10):"""

MAX_CONTENT_CHARS = 800  # keep prompts short for speed


class Reranker:
    def __init__(self):
        self._llm = None

    def set_llm(self, llm) -> None:
        self._llm = llm

    def rerank(self, query: str, results: list[Any], top_k: int = 5) -> list[Any]:
        """
        Re-rank retrieved results using LLM relevance scoring.

        Args:
            query:   Original user query
            results: List of RetrievedContext objects (already sorted by RRF)
            top_k:   Number of results to return

        Returns:
            Re-ranked list (top_k items)
        """
        if not results:
            return []

        # If no LLM, return top-k by existing RRF score
        if not self._llm:
            return results[:top_k]

        scored: list[tuple[float, Any]] = []
        for item in results:
            score = self._score_item(query, item)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _score_item(self, query: str, item: Any) -> float:
        """Score a single (query, item) pair using LLM."""
        # Accept both dict and RetrievedContext objects
        if hasattr(item, "evidence"):
            content = " ".join(item.evidence or [])[:MAX_CONTENT_CHARS]
            chunk_type = "code"
            language = getattr(item, "language", "unknown")
            existing_score = getattr(item, "score", 0.5)
        elif isinstance(item, dict):
            content = str(item.get("content", ""))[:MAX_CONTENT_CHARS]
            chunk_type = item.get("chunk_type", "raw_code")
            language = (
                item.get("metadata", {}).get("language", "unknown")
                if isinstance(item.get("metadata"), dict)
                else "unknown"
            )
            existing_score = float(item.get("score", 0.5))
        else:
            return 0.5

        try:
            prompt = _RERANK_USER_TMPL.format(
                query=query,
                chunk_type=chunk_type,
                language=language,
                content=content,
            )
            response = self._llm.invoke(
                [
                    {"role": "system", "content": _RERANK_SYSTEM},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = response.content if hasattr(response, "content") else str(response)
            m = re.search(r"\b(\d+)\b", raw)
            if m:
                llm_score = int(m.group(1)) / 10.0
                # Blend LLM score (70%) with existing RRF score (30%)
                return 0.7 * llm_score + 0.3 * existing_score
        except Exception as e:
            logger.debug(f"[Reranker] LLM score failed: {e}")

        return existing_score  # fallback to RRF score


reranker = Reranker()
