"""
Dependency Graph
================
Builds a lightweight in-memory directed graph of code relationships
extracted during ingestion, and supports graph-based context expansion
at retrieval time.

Edge Types (aligned with DB DependencyRelationship.relationship_type):
  IMPORTS       — file/module imports another
  EXTENDS       — class extends another class
  IMPLEMENTS    — class implements an interface
  CALLS         — function/method calls another
  INJECTS       — dependency injection (@Autowired, constructor params)
  ANNOTATED_WITH — class/method carries a specific annotation
  USES          — generic "uses" relationship
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from backend.retrieval.universal_parser import CodeNode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class DependencyEdge:
    source: str  # fully-qualified name or "file::ClassName"
    target: str  # fully-qualified name or plain class name
    edge_type: (
        str  # IMPORTS | EXTENDS | IMPLEMENTS | CALLS | INJECTS | ANNOTATED_WITH | USES
    )
    source_file: str = ""
    target_file: str = ""
    metadata: dict = field(default_factory=dict)


class DependencyGraph:
    """
    Directed graph: source → [edges]
    """

    def __init__(self):
        self._edges: dict[str, list[DependencyEdge]] = defaultdict(list)
        self._reverse: dict[str, list[DependencyEdge]] = defaultdict(list)
        self._node_to_file: dict[str, str] = {}  # symbol name → file path

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_from_nodes(self, nodes: list[CodeNode]) -> None:
        """
        Populate the graph from a list of parsed CodeNodes.
        Clears existing data first.
        """
        self._edges.clear()
        self._reverse.clear()
        self._node_to_file.clear()

        for node in nodes:
            self._register_node(node)

        for node in nodes:
            self._add_edges_for_node(node)

        logger.info(
            f"[DependencyGraph] Built graph: "
            f"{len(self._node_to_file)} symbols, "
            f"{sum(len(v) for v in self._edges.values())} edges"
        )

    def _register_node(self, node: CodeNode) -> None:
        key = self._key(node.name, node.file_path)
        self._node_to_file[node.name] = node.file_path
        self._node_to_file[key] = node.file_path

    def _add_edges_for_node(self, node: CodeNode) -> None:
        src = node.name
        src_file = node.file_path

        # EXTENDS
        for parent in node.extends:
            self._add(src, parent, "EXTENDS", src_file)

        # IMPLEMENTS
        for iface in node.implements:
            self._add(src, iface, "IMPLEMENTS", src_file)

        # CALLS (heuristic — filter to known symbols)
        for callee in node.calls:
            if callee in self._node_to_file:
                self._add(src, callee, "CALLS", src_file, self._node_to_file[callee])

        # IMPORTS (from the file-level import block, rough parse)
        if node.imports:
            for imp in _parse_import_targets(node.imports, node.language):
                self._add(src, imp, "IMPORTS", src_file)

        # ANNOTATED_WITH
        for ann in node.annotations:
            self._add(src, ann.lstrip("@"), "ANNOTATED_WITH", src_file)

        # INJECTS — look for @Autowired or constructor injection patterns
        if "@Autowired" in node.code or "constructor(" in node.code.lower():
            for dep in _extract_injected(node.code):
                if dep in self._node_to_file:
                    self._add(src, dep, "INJECTS", src_file, self._node_to_file[dep])

    def _add(
        self,
        source: str,
        target: str,
        edge_type: str,
        source_file: str = "",
        target_file: str = "",
    ) -> None:
        if not target or target == source:
            return
        edge = DependencyEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            source_file=source_file,
            target_file=target_file or self._node_to_file.get(target, ""),
        )
        self._edges[source].append(edge)
        self._reverse[target].append(edge)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_outgoing(
        self, symbol: str, edge_types: list[str] | None = None
    ) -> list[DependencyEdge]:
        edges = self._edges.get(symbol, [])
        if edge_types:
            edges = [e for e in edges if e.edge_type in edge_types]
        return edges

    def get_incoming(
        self, symbol: str, edge_types: list[str] | None = None
    ) -> list[DependencyEdge]:
        edges = self._reverse.get(symbol, [])
        if edge_types:
            edges = [e for e in edges if e.edge_type in edge_types]
        return edges

    def expand_context(
        self,
        symbol_names: list[str],
        depth: int = 1,
        edge_types: list[str] | None = None,
    ) -> list[str]:
        """
        Given a list of retrieved symbol names, walk the graph to collect
        additional context symbols (parent class, called services, etc.).
        Returns a deduplicated list of additional symbol names.
        """
        if edge_types is None:
            edge_types = ["EXTENDS", "IMPLEMENTS", "CALLS", "INJECTS", "IMPORTS"]

        visited: set[str] = set(symbol_names)
        frontier: set[str] = set(symbol_names)

        for _ in range(depth):
            next_frontier: set[str] = set()
            for sym in frontier:
                for edge in self.get_outgoing(sym, edge_types):
                    if edge.target not in visited:
                        visited.add(edge.target)
                        next_frontier.add(edge.target)
                for edge in self.get_incoming(sym, ["EXTENDS", "IMPLEMENTS"]):
                    if edge.source not in visited:
                        visited.add(edge.source)
                        next_frontier.add(edge.source)
            frontier = next_frontier
            if not frontier:
                break

        return [s for s in visited if s not in symbol_names]

    def get_all_edges(self) -> list[DependencyEdge]:
        edges: list[DependencyEdge] = []
        for edge_list in self._edges.values():
            edges.extend(edge_list)
        return edges

    def symbol_to_file(self, symbol: str) -> str | None:
        return self._node_to_file.get(symbol)

    @staticmethod
    def _key(name: str, file_path: str) -> str:
        return f"{file_path}::{name}"

    def summary(self) -> str:
        total_edges = sum(len(v) for v in self._edges.values())
        return (
            f"Symbols: {len(self._node_to_file)} | "
            f"Edges: {total_edges} | "
            f"Edge types: {set(e.edge_type for edges in self._edges.values() for e in edges)}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_import_targets(imports_block: str, language: str) -> list[str]:
    """Extract imported class/module names from a raw import block."""
    targets: list[str] = []
    for line in imports_block.splitlines():
        line = line.strip()
        if not line:
            continue
        # Java/Kotlin: import com.package.ClassName;
        m = re.search(r"import\s+[\w.]+\.(\w+)", line)
        if m:
            targets.append(m.group(1))
            continue
        # Python: from module import Name  /  import name
        m = re.search(r"from\s+[\w.]+\s+import\s+(.+)", line)
        if m:
            for sym in m.group(1).split(","):
                targets.append(sym.strip().split(" as ")[0].strip())
            continue
        m = re.search(r"^import\s+([\w.]+)", line)
        if m:
            targets.append(m.group(1).split(".")[-1])
    return [t for t in targets if t and len(t) > 1]


def _extract_injected(code: str) -> list[str]:
    """Heuristic: find @Autowired fields or constructor param types."""
    injected: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if "@Autowired" in stripped or "private" in stripped:
            m = re.search(r"(?:private|protected|public)\s+(\w+)\s+\w+\s*;", stripped)
            if m:
                injected.append(m.group(1))
    return injected


import re  # noqa: E402 — placed here to keep helpers readable

# Global singleton — rebuilt on each ingestion
dependency_graph = DependencyGraph()
