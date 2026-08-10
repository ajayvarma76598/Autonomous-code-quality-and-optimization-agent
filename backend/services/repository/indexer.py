"""
Repository Indexer — Full Production Ingestion Pipeline
========================================================

Pipeline Stages:
  1.  Walk repository files (respecting exclusion rules)
  2.  Language Detection + Content-Type Routing
  3.  Tree-sitter / AST Parsing (universal_parser)
  4.  Build Dependency Graph (IMPORTS, EXTENDS, IMPLEMENTS, CALLS, INJECTS)
  5.  Batch Generate LLM Summaries
  6.  Build Parent-Child Chunk Hierarchy + 3 Views (chunk_builder)
  7.  Store RepositoryFile rows in DB
  8.  Store CodeObject rows with parent-child links in DB
  9.  Store DependencyRelationship edges in DB
  10. Batch Generate Embeddings
  11. Store DocumentChunk + Embedding rows in DB
  12. Fit BM25 on all raw_code chunks

All DB writes are fully aligned with the existing schema in models.py.
No migrations required.
"""
from __future__ import annotations
import os
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

from backend.services.base_service import BaseService
from backend.retrieval.universal_parser import universal_parser, CodeNode
from backend.retrieval.dependency_graph import dependency_graph
from backend.retrieval.summarizer import code_summarizer
from backend.retrieval.chunk_builder import chunk_builder, BuiltChunk
from backend.retrieval.bm25 import bm25_retriever
from backend.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File Exclusion Rules
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    ".venv", ".git", "node_modules", "__pycache__", "sonar-scanner",
    ".pytest_cache", ".idea", ".vscode", "dist", "build", "target",
    "out", ".gradle", ".mvn", "coverage", ".nyc_output", "vendor",
    ".scannerwork", ".eggs", "bin", "obj",
}

EXCLUDE_FILE_NAMES = {
    "golden_dataset.md", "capstone_code_quality_and_optimization_dataset.md",
    ".gitignore", ".gitattributes", ".editorconfig", "package-lock.json",
    "yarn.lock", "poetry.lock", "pipfile.lock", "gradlew", "gradlew.bat",
    "mvnw", "mvnw.cmd",
}

EXCLUDE_PATTERNS = ["dataset", ".min.js", ".min.css", ".min.ts", "bundle.js",
                    "vendor.js", "generated", "proto.pb"]

INDEXABLE_EXTENSIONS = {
    ".py", ".java", ".kt", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".cs", ".cpp", ".c", ".rs", ".rb", ".php", ".scala",
    ".sql",
    ".md", ".txt", ".rst",
    ".yaml", ".yml", ".json", ".xml", ".toml", ".properties",
    ".tf", ".sh", ".gradle",
}

SPECIAL_FILENAMES = {"dockerfile", "makefile", "jenkinsfile", "procfile",
                     "vagrantfile", ".env.example"}


def _should_index(filename: str) -> bool:
    fn_lower = filename.lower()
    if fn_lower in EXCLUDE_FILE_NAMES:
        return False
    if any(pat in fn_lower for pat in EXCLUDE_PATTERNS):
        return False
    _, ext = os.path.splitext(filename)
    if ext.lower() in INDEXABLE_EXTENSIONS:
        return True
    if fn_lower in SPECIAL_FILENAMES:
        return True
    return False


# ---------------------------------------------------------------------------
# Repository Indexer
# ---------------------------------------------------------------------------

class RepositoryIndexer(BaseService):
    def __init__(self):
        super().__init__("RepositoryIndexer")

    def index(self, local_path: str, snapshot_id: Optional[str] = None,
              llm=None) -> bool:
        """
        Run the full ingestion pipeline for a repository at `local_path`.

        Args:
            local_path:  Absolute path to the cloned repo directory
            snapshot_id: UUID of the RepositorySnapshot row to link DB records
            llm:         Optional LangChain LLM for summary generation
        """
        def _index():
            if not local_path or not os.path.exists(str(local_path)):
                logger.warning(f"[RepositoryIndexer] Path invalid or does not exist: '{local_path}'")
                return True

            # Fast DB check: Skip indexing if repository chunks already exist in PostgreSQL for this snapshot
            try:
                from backend.database.session import SessionLocal
                from backend.database.models.models import DocumentChunk
                db_chk = SessionLocal()
                try:
                    from uuid import UUID
                    snap_uuid = UUID(str(snapshot_id))
                    existing_chunks = db_chk.query(DocumentChunk).filter(DocumentChunk.snapshot_id == snap_uuid).count()
                    if existing_chunks > 0:
                        logger.info(f"[RepositoryIndexer] Repository snapshot already indexed in PostgreSQL ({existing_chunks} chunks present). Skipping indexing.")
                        return True
                finally:
                    db_chk.close()
            except Exception as chk_e:
                logger.warning(f"[RepositoryIndexer] DB check error: {chk_e}")

            # Inject LLM into summarizer
            if llm:
                code_summarizer.set_llm(llm)

            # ----------------------------------------------------------------
            # Stage 1-3: Walk files → Detect language → Parse AST
            # ----------------------------------------------------------------
            all_nodes: List[CodeNode] = []
            file_node_map: Dict[str, List[CodeNode]] = {}  # rel_path → nodes
            file_stats: Dict[str, dict] = {}               # rel_path → {size, lines, lang}

            logger.info(f"[RepositoryIndexer] Stage 1-3: Scanning & parsing '{local_path}'...")
            file_count = 0

            for root, dirs, files in os.walk(local_path):
                dirs[:] = [d for d in dirs
                           if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")]

                for filename in files:
                    if not _should_index(filename):
                        continue
                    fp = os.path.join(root, filename)
                    rel_path = os.path.relpath(fp, local_path).replace("\\", "/")

                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        if not content.strip():
                            continue

                        nodes = universal_parser.parse(rel_path, content)
                        if not nodes:
                            continue

                        language = universal_parser.detect_language(filename)
                        file_count += 1
                        file_node_map[rel_path] = nodes
                        all_nodes.extend(nodes)
                        file_stats[rel_path] = {
                            "language": language,
                            "size_bytes": len(content.encode("utf-8")),
                            "line_count": content.count("\n") + 1,
                            "checksum": hashlib.md5(content.encode()).hexdigest(),
                            "extension": os.path.splitext(filename)[1].lower(),
                            "filename": filename,
                        }
                    except Exception as e:
                        logger.warning(f"[RepositoryIndexer] Parse error '{rel_path}': {e}")

            logger.info(
                f"[RepositoryIndexer] Stage 1-3 complete. "
                f"Files: {file_count} | Nodes: {len(all_nodes)}"
            )

            # ----------------------------------------------------------------
            # Stage 4: Build Dependency Graph
            # ----------------------------------------------------------------
            logger.info("[RepositoryIndexer] Stage 4: Building dependency graph...")
            dependency_graph.build_from_nodes(all_nodes)
            logger.info(f"[RepositoryIndexer] Graph: {dependency_graph.summary()}")

            # ----------------------------------------------------------------
            # Stage 5: Batch LLM Summaries
            # ----------------------------------------------------------------
            logger.info(f"[RepositoryIndexer] Stage 5: Generating LLM summaries for {len(all_nodes)} nodes...")
            summaries: List[str] = []
            if llm:
                summaries = code_summarizer.batch_summarize(all_nodes)
                logger.info("[RepositoryIndexer] Stage 5: Summaries generated.")
            else:
                logger.info("[RepositoryIndexer] Stage 5: No LLM — using structured fallbacks.")

            # ----------------------------------------------------------------
            # Stage 6: Build Parent-Child Chunks (3 views)
            # ----------------------------------------------------------------
            logger.info("[RepositoryIndexer] Stage 6: Building chunk views...")
            built_chunks: List[BuiltChunk] = chunk_builder.build(
                all_nodes,
                summaries=summaries if summaries else None,
            )
            logger.info(f"[RepositoryIndexer] Stage 6: {len(built_chunks)} chunks built.")

            # ----------------------------------------------------------------
            # Stages 7-11: DB Writes
            # ----------------------------------------------------------------
            from backend.database.session import SessionLocal
            db = SessionLocal()
            try:
                snap_uuid = _parse_uuid(snapshot_id)

                # Stage 7: RepositoryFile rows
                file_id_map: Dict[str, uuid.UUID] = {}
                if snap_uuid:
                    logger.info("[RepositoryIndexer] Stage 7: Writing RepositoryFile rows...")
                    file_id_map = _upsert_repository_files(db, snap_uuid, file_stats)
                    db.commit()

                # Stage 8: CodeObject rows (class/function hierarchy)
                object_id_map: Dict[str, uuid.UUID] = {}  # "rel_path::name" → object_id
                if snap_uuid:
                    logger.info("[RepositoryIndexer] Stage 8: Writing CodeObject rows...")
                    object_id_map = _upsert_code_objects(db, all_nodes, file_id_map)
                    db.commit()

                # Stage 9: DependencyRelationship rows
                if snap_uuid:
                    logger.info("[RepositoryIndexer] Stage 9: Writing DependencyRelationship rows...")
                    _write_dependency_edges(db, snap_uuid, object_id_map)
                    db.commit()

                # Stage 10: Batch Embeddings
                logger.info("[RepositoryIndexer] Stage 10: Generating embeddings...")
                texts = [c.content for c in built_chunks]
                vectors = _batch_embed(texts)
                logger.info(f"[RepositoryIndexer] Stage 10: {len(vectors)} vectors generated.")

                # Stage 11: DocumentChunk + Embedding rows
                logger.info("[RepositoryIndexer] Stage 11: Storing chunks + embeddings in DB...")
                bm25_docs = _write_chunks_and_embeddings(
                    db, built_chunks, vectors, file_id_map, object_id_map
                )
                db.commit()
                logger.info("[RepositoryIndexer] Stage 11: DB write complete.")

            except Exception as e:
                db.rollback()
                logger.error(f"[RepositoryIndexer] DB write failed: {e}", exc_info=True)
                # Don't re-raise — still fit BM25 in memory
                bm25_docs = _build_bm25_docs_fallback(built_chunks)
            finally:
                db.close()

            # ----------------------------------------------------------------
            # Stage 12: Fit BM25
            # ----------------------------------------------------------------
            if bm25_docs:
                logger.info(f"[RepositoryIndexer] Stage 12: Fitting BM25 on {len(bm25_docs)} docs...")
                bm25_retriever.fit(bm25_docs)
                logger.info("[RepositoryIndexer] Stage 12: BM25 fit complete.")

            logger.info(
                f"[RepositoryIndexer] Pipeline complete. "
                f"Files: {file_count} | Nodes: {len(all_nodes)} | "
                f"Chunks: {len(built_chunks)} | BM25 docs: {len(bm25_docs)}"
            )
            return True

        return self.execute(_index).data


# ---------------------------------------------------------------------------
# DB Helper Functions
# ---------------------------------------------------------------------------

def _parse_uuid(value) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except Exception:
        return None


def _upsert_repository_files(db, snap_uuid: uuid.UUID,
                              file_stats: Dict[str, dict]) -> Dict[str, uuid.UUID]:
    """Insert RepositoryFile rows; return rel_path → file_id map."""
    from backend.database.models.models import RepositoryFile
    file_id_map: Dict[str, uuid.UUID] = {}

    for rel_path, stats in file_stats.items():
        existing = db.query(RepositoryFile).filter(
            RepositoryFile.snapshot_id == snap_uuid,
            RepositoryFile.path == rel_path,
        ).first()
        if existing:
            file_id_map[rel_path] = existing.file_id
            continue

        rf = RepositoryFile(
            file_id=uuid.uuid4(),
            snapshot_id=snap_uuid,
            path=rel_path,
            filename=stats["filename"],
            extension=stats["extension"],
            language=stats["language"],
            size_bytes=stats["size_bytes"],
            line_count=stats["line_count"],
            checksum=stats["checksum"],
            metadata_={"language": stats["language"]},
        )
        db.add(rf)
        file_id_map[rel_path] = rf.file_id

    return file_id_map


def _upsert_code_objects(db, nodes: List[CodeNode],
                          file_id_map: Dict[str, uuid.UUID]) -> Dict[str, uuid.UUID]:
    """Insert CodeObject rows with parent-child links; return key → object_id map."""
    from backend.database.models.models import CodeObject
    object_id_map: Dict[str, uuid.UUID] = {}

    # Two passes: first classes (parents), then methods (children)
    class_nodes = [n for n in nodes if n.node_type == "class"]
    other_nodes  = [n for n in nodes if n.node_type != "class"]

    def _insert(node: CodeNode):
        key = f"{node.file_path}::{node.name}"
        file_id = file_id_map.get(node.file_path)
        if not file_id:
            return

        parent_id = None
        if node.parent_name:
            parent_key = f"{node.file_path}::{node.parent_name}"
            parent_id = object_id_map.get(parent_key)

        obj_id = uuid.uuid4()
        obj = CodeObject(
            object_id=obj_id,
            file_id=file_id,
            parent_object_id=parent_id,
            object_type=node.node_type,
            name=node.name,
            signature=node.signature or "",
            return_type=node.return_type or "",
            start_line=node.start_line,
            end_line=node.end_line,
            docstring=node.docstring or "",
            metadata_={
                "language":    node.language,
                "package":     node.package,
                "framework":   node.framework,
                "annotations": node.annotations,
                "extends":     node.extends,
                "implements":  node.implements,
                "calls":       node.calls[:10],
                "content_type": node.content_type,
            },
        )
        db.add(obj)
        object_id_map[key] = obj_id

    for node in class_nodes:
        _insert(node)
    for node in other_nodes:
        _insert(node)

    return object_id_map


def _write_dependency_edges(db, snap_uuid: uuid.UUID,
                             object_id_map: Dict[str, uuid.UUID]) -> None:
    """Write DependencyRelationship rows from the in-memory graph."""
    from backend.database.models.models import DependencyRelationship
    edges = dependency_graph.get_all_edges()

    for edge in edges:
        src_id = object_id_map.get(edge.source) or object_id_map.get(
            f"{edge.source_file}::{edge.source}")
        tgt_id = object_id_map.get(edge.target) or object_id_map.get(
            f"{edge.target_file}::{edge.target}")

        if not src_id or not tgt_id:
            continue

        db.add(DependencyRelationship(
            relationship_id=uuid.uuid4(),
            snapshot_id=snap_uuid,
            source_object_id=src_id,
            target_object_id=tgt_id,
            relationship_type=edge.edge_type,
            metadata_={"source_file": edge.source_file, "target_file": edge.target_file},
        ))


def _batch_embed(texts: List[str], batch_size: int = 50) -> List[List[float]]:
    """Embed all texts in batches; returns parallel list of vectors."""
    all_vectors: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        try:
            vecs = embedding_service.generate_embeddings(batch)
            all_vectors.extend(vecs)
        except Exception as e:
            logger.warning(f"[RepositoryIndexer] Embedding batch {i}-{i+batch_size} failed: {e}")
            all_vectors.extend([[0.0] * 1536] * len(batch))
    return all_vectors


def _write_chunks_and_embeddings(db, built_chunks: List[BuiltChunk],
                                   vectors: List[List[float]],
                                   file_id_map: Dict[str, uuid.UUID],
                                   object_id_map: Dict[str, uuid.UUID]) -> List[dict]:
    """Write DocumentChunk + Embedding rows; also build BM25 docs list."""
    from backend.database.models.models import DocumentChunk, Embedding
    bm25_docs: List[dict] = []

    for idx, (chunk, vector) in enumerate(zip(built_chunks, vectors)):
        file_id   = file_id_map.get(chunk.node.file_path)
        obj_key   = f"{chunk.node.file_path}::{chunk.node.name}"
        object_id = object_id_map.get(obj_key)

        chunk_id = uuid.uuid4()
        dc = DocumentChunk(
            chunk_id=chunk_id,
            file_id=file_id,
            object_id=object_id,
            chunk_index=idx,
            chunk_type=chunk.chunk_type,
            content=chunk.content,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            metadata_=chunk.metadata,
        )
        db.add(dc)

        emb = Embedding(
            embedding_id=uuid.uuid4(),
            chunk_id=chunk_id,
            provider="azure_openai",
            model_name="text-embedding-3-small",
            embedding_dimension=len(vector),
            embedding=vector,
            created_at=datetime.now(timezone.utc),
        )
        db.add(emb)

        # Only raw_code chunks go into BM25
        if chunk.chunk_type == "raw_code":
            bm25_docs.append({
                "chunk_id": str(chunk_id),
                "content": chunk.content,
                "repository_path": chunk.node.file_path,
                "metadata": chunk.metadata,
            })

    return bm25_docs


def _build_bm25_docs_fallback(built_chunks: List[BuiltChunk]) -> List[dict]:
    """Build BM25 docs without DB (fallback when DB write fails)."""
    return [
        {
            "chunk_id": chunk.chunk_id_hint,
            "content":  chunk.content,
            "repository_path": chunk.node.file_path,
            "metadata": chunk.metadata,
        }
        for chunk in built_chunks if chunk.chunk_type == "raw_code"
    ]
