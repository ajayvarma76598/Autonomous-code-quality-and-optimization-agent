"""
Chunk Builder — Parent-Child Hierarchy + Multiple Chunk Views
=============================================================
For every CodeNode, produces up to 3 complementary chunk views:

  1. raw_code   — imports + annotations + header + code body
  2. summary    — LLM-generated natural-language summary + metadata
  3. metadata   — JSON-style structured metadata block (for exact-match filtering)

Parent-Child linking:
  - Method chunks carry a reference to their parent class chunk
  - During retrieval, when a method chunk is returned, the retriever
    also fetches its parent class chunk for surrounding context

Content-type routing (collection):
  code | architecture | config | api | summary
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from backend.retrieval.universal_parser import CodeNode, build_chunk_content

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built Chunk
# ---------------------------------------------------------------------------

@dataclass
class BuiltChunk:
    """
    A single embeddable unit ready for storage.
    Maps 1-to-1 to a DocumentChunk row in the DB.
    """
    chunk_id_hint: str          # Deterministic ID hint: "filepath::name::line::view"
    chunk_type: str             # raw_code | summary | metadata
    content: str                # Text that will be embedded
    content_type: str           # code | architecture | config | api | summary
    start_line: int
    end_line: int
    node: CodeNode              # Original parsed node (for DB writes)
    parent_symbol: Optional[str] = None   # Parent class name (for method chunks)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chunk Builder
# ---------------------------------------------------------------------------

class ChunkBuilder:
    """
    Converts a list of CodeNodes into BuiltChunks with 3 views each.
    """

    def build(self, nodes: List[CodeNode],
              summaries: Optional[List[str]] = None) -> List[BuiltChunk]:
        """
        Build all chunk views for a list of nodes.

        Args:
            nodes:     Parsed CodeNode list from universal_parser
            summaries: Optional parallel list of LLM summaries (same length as nodes).
                       If None, only raw_code and metadata views are produced.

        Returns:
            List of BuiltChunk objects ready for embedding + DB storage.
        """
        if summaries and len(summaries) != len(nodes):
            logger.warning("[ChunkBuilder] Summary list length mismatch — ignoring summaries")
            summaries = None

        chunks: List[BuiltChunk] = []
        for i, node in enumerate(nodes):
            summary_text = summaries[i] if summaries else None
            node_chunks = self._build_node_chunks(node, summary_text)
            chunks.extend(node_chunks)

        logger.debug(f"[ChunkBuilder] Built {len(chunks)} chunks from {len(nodes)} nodes")
        return chunks

    # ------------------------------------------------------------------
    # Per-node: up to 3 views
    # ------------------------------------------------------------------

    def _build_node_chunks(self, node: CodeNode,
                           summary_text: Optional[str] = None) -> List[BuiltChunk]:
        chunks: List[BuiltChunk] = []
        base_id = f"{node.file_path}::{node.name}::{node.start_line}"

        rich_meta = self._rich_metadata(node)

        # View 1 — Raw Code (always produced)
        raw_content = build_chunk_content(node)
        chunks.append(BuiltChunk(
            chunk_id_hint=f"{base_id}::raw_code",
            chunk_type="raw_code",
            content=raw_content,
            content_type=node.content_type,
            start_line=node.start_line,
            end_line=node.end_line,
            node=node,
            parent_symbol=node.parent_name,
            metadata=rich_meta,
        ))

        # View 2 — LLM Summary (only when summary available)
        if summary_text and summary_text.strip():
            summary_content = self._build_summary_content(node, summary_text)
            chunks.append(BuiltChunk(
                chunk_id_hint=f"{base_id}::summary",
                chunk_type="summary",
                content=summary_content,
                content_type="summary",
                start_line=node.start_line,
                end_line=node.end_line,
                node=node,
                parent_symbol=node.parent_name,
                metadata={**rich_meta, "summary_text": summary_text},
            ))

        # View 3 — Structured Metadata (always produced for source code)
        if node.node_type in ("class", "function"):
            meta_content = self._build_metadata_content(node, rich_meta)
            chunks.append(BuiltChunk(
                chunk_id_hint=f"{base_id}::metadata",
                chunk_type="metadata",
                content=meta_content,
                content_type=node.content_type,
                start_line=node.start_line,
                end_line=node.end_line,
                node=node,
                parent_symbol=node.parent_name,
                metadata=rich_meta,
            ))

        return chunks

    # ------------------------------------------------------------------
    # Content builders for each view
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary_content(node: CodeNode, summary: str) -> str:
        """Summary view: header + LLM summary + key metadata."""
        lines = [
            f"[SUMMARY] {node.language.upper()} {node.node_type.capitalize()}: {node.name}",
        ]
        if node.parent_name:
            lines.append(f"Belongs to: {node.parent_name}")
        if node.package:
            lines.append(f"Package: {node.package}")
        if node.framework:
            lines.append(f"Framework: {node.framework}")
        if node.annotations:
            lines.append(f"Annotations: {', '.join(node.annotations)}")
        lines.append(f"File: {node.file_path} (L{node.start_line}–{node.end_line})")
        lines.append(f"\nSummary:\n{summary}")
        return "\n".join(lines)

    @staticmethod
    def _build_metadata_content(node: CodeNode, meta: Dict[str, Any]) -> str:
        """Metadata view: compact JSON-style block for exact-match / filtering queries."""
        # Build a clean JSON-serialisable dict
        payload = {
            "repo": meta.get("repo", ""),
            "language": node.language,
            "framework": node.framework,
            "package": node.package,
            "class": node.name if node.node_type == "class" else (node.parent_name or ""),
            "method": node.name if node.node_type == "function" else "",
            "type": node.node_type,
            "file": node.file_path,
            "imports": [imp.strip() for imp in node.imports.splitlines() if imp.strip()][:10],
            "annotations": node.annotations,
            "extends": node.extends,
            "implements": node.implements,
            "return_type": node.return_type,
            "calls": node.calls[:10],
        }
        return (
            f"[METADATA] {node.language.upper()} {node.node_type}: {node.name}\n"
            + json.dumps(payload, indent=2)
        )

    @staticmethod
    def _rich_metadata(node: CodeNode) -> Dict[str, Any]:
        """Flat metadata dict attached to every chunk (stored in DocumentChunk.metadata_)."""
        return {
            "path":          node.file_path,
            "language":      node.language,
            "framework":     node.framework,
            "package":       node.package,
            "module":        node.file_path.split("/")[-1].split(".")[0],
            "symbol_name":   node.name,
            "symbol_type":   node.node_type,
            "parent_name":   node.parent_name or "",
            "annotations":   node.annotations,
            "extends":       node.extends,
            "implements":    node.implements,
            "calls":         node.calls[:10],
            "return_type":   node.return_type,
            "signature":     node.signature,
            "docstring":     node.docstring[:200] if node.docstring else "",
            "content_type":  node.content_type,
            "start_line":    node.start_line,
            "end_line":      node.end_line,
        }


# Singleton
chunk_builder = ChunkBuilder()
