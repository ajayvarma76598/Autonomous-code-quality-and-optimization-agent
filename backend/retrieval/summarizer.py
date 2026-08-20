"""
Code Summarizer — LLM-Powered Summary Generation During Ingestion
=================================================================
Generates concise natural-language summaries for every class and function
parsed during repository ingestion. These summaries are embedded as a
separate chunk view, dramatically improving retrieval for natural-language
queries like "How are payments processed?".

Strategy:
  - Batch up to BATCH_SIZE nodes per LLM call to minimise latency
  - Structured fallback if LLM is unavailable or quota exhausted
  - Summaries are stored as separate DocumentChunk rows (chunk_type="summary")
"""

from __future__ import annotations

import logging

from backend.retrieval.universal_parser import CodeNode

logger = logging.getLogger(__name__)

# Only summarise meaningful code nodes, not raw sliding-window chunks
SUMMARISE_TYPES = {"class", "function", "section"}
BATCH_SIZE = 15  # nodes per LLM call
MAX_CODE_CHARS = 1800  # truncate code before sending to LLM


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a senior software architect. Your job is to write concise, "
    "accurate 2-3 sentence summaries of code components for a RAG index. "
    "Focus on: what the component does, key dependencies, and patterns used. "
    "Do NOT include code. Be precise and factual."
)

_BATCH_TEMPLATE = """Summarise each of the following {n} code components.
Return EXACTLY {n} summaries, one per line, separated by '---'.
No numbering, no extra text.

{items}"""

_SINGLE_ITEM_TEMPLATE = """Component {idx}:
Language: {language}
Type: {node_type}
Name: {name}{parent}{package}{framework}{annotations}
Code:
```{language}
{code}
```"""


# ---------------------------------------------------------------------------
# Fallback (Structured Header Summary)
# ---------------------------------------------------------------------------


def _fallback_summary(node: CodeNode) -> str:
    parts = [f"{node.node_type.capitalize()} '{node.name}'"]
    if node.parent_name:
        parts.append(f"defined inside '{node.parent_name}'")
    if node.package:
        parts.append(f"in package '{node.package}'")
    if node.framework:
        parts.append(f"using {node.framework} framework")
    if node.docstring:
        parts.append(f"— {node.docstring[:200]}")
    if node.extends:
        parts.append(f"extends {', '.join(node.extends)}")
    if node.implements:
        parts.append(f"implements {', '.join(node.implements)}")
    parts.append(f"(File: {node.file_path}, L{node.start_line}–{node.end_line})")
    return ". ".join(parts).replace(". .", ".")


# ---------------------------------------------------------------------------
# Single-item fallback text builder
# ---------------------------------------------------------------------------


def _item_text(node: CodeNode, idx: int) -> str:
    return _SINGLE_ITEM_TEMPLATE.format(
        idx=idx + 1,
        language=node.language,
        node_type=node.node_type,
        name=node.name,
        parent=f"\nParent Class: {node.parent_name}" if node.parent_name else "",
        package=f"\nPackage: {node.package}" if node.package else "",
        framework=f"\nFramework: {node.framework}" if node.framework else "",
        annotations=f"\nAnnotations: {', '.join(node.annotations)}"
        if node.annotations
        else "",
        code=node.code[:MAX_CODE_CHARS],
    )


# ---------------------------------------------------------------------------
# Core Summarizer
# ---------------------------------------------------------------------------


class CodeSummarizer:
    def __init__(self, llm=None):
        self.llm = llm

    def set_llm(self, llm) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize_node(self, node: CodeNode) -> str:
        """Generate a summary for a single CodeNode."""
        if node.node_type not in SUMMARISE_TYPES:
            return _fallback_summary(node)
        if not self.llm:
            return _fallback_summary(node)
        try:
            prompt = f"{_SYSTEM_PROMPT}\n\n{_item_text(node, 0)}"
            response = self.llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            return text.strip()[:600] or _fallback_summary(node)
        except Exception as e:
            logger.warning(f"[Summarizer] LLM call failed for '{node.name}': {e}")
            return _fallback_summary(node)

    def batch_summarize(self, nodes: list[CodeNode]) -> list[str]:
        """
        Generate summaries for a list of nodes in batches.
        Returns one summary string per node (same order).
        """
        results: list[str] = [""] * len(nodes)

        # Filter to summarisable types; others get fallback immediately
        summarisable: list[tuple[int, CodeNode]] = []
        for i, node in enumerate(nodes):
            if node.node_type in SUMMARISE_TYPES and self.llm:
                summarisable.append((i, node))
            else:
                results[i] = _fallback_summary(node)

        if not summarisable:
            return results

        # Process in batches
        for batch_start in range(0, len(summarisable), BATCH_SIZE):
            batch = summarisable[batch_start : batch_start + BATCH_SIZE]
            batch_summaries = self._call_llm_batch(batch)
            for (orig_idx, _), summary in zip(batch, batch_summaries):
                results[orig_idx] = summary

        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_llm_batch(self, batch: list[tuple[int, CodeNode]]) -> list[str]:
        """Call LLM with a batch of nodes, return one summary per node."""
        n = len(batch)
        items_text = "\n\n".join(
            _item_text(node, i) for i, (_, node) in enumerate(batch)
        )
        prompt = f"{_SYSTEM_PROMPT}\n\n" + _BATCH_TEMPLATE.format(n=n, items=items_text)

        try:
            response = self.llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            parts = [p.strip() for p in raw.split("---")]

            # Pad / trim to exactly n summaries
            if len(parts) < n:
                parts += [_fallback_summary(node) for _, node in batch[len(parts) :]]
            parts = parts[:n]
            return [
                p[:600] if p else _fallback_summary(node)
                for p, (_, node) in zip(parts, batch)
            ]
        except Exception as e:
            logger.warning(f"[Summarizer] Batch LLM call failed: {e}")
            return [_fallback_summary(node) for _, node in batch]


# Singleton — LLM is injected by RepositoryIndexer during ingestion
code_summarizer = CodeSummarizer()
