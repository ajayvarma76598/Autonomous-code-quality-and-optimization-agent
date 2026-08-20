import string
from typing import Any

from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self):
        self.corpus: list[dict[str, Any]] = []
        self.tokenized_corpus: list[list[str]] = []
        self.bm25 = None

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace tokenizer with punctuation removal."""
        text = text.lower().translate(str.maketrans("", "", string.punctuation))
        return text.split()

    def fit(self, documents: list[dict[str, Any]], text_key: str = "content"):
        """
        Fit the BM25 model on a corpus of documents.
        Each document should be a dictionary containing at least the text_key.
        """
        self.corpus = documents
        self.tokenized_corpus = [self._tokenize(doc[text_key]) for doc in self.corpus]

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def fit_from_db(self, db, snapshot_id=None):
        """Fit BM25 model strictly on document chunks belonging to target snapshot_id."""
        from backend.database.models.models import DocumentChunk, RepositoryFile

        query = db.query(DocumentChunk, RepositoryFile).join(
            RepositoryFile, DocumentChunk.file_id == RepositoryFile.file_id
        )
        if snapshot_id:
            query = query.filter(RepositoryFile.snapshot_id == snapshot_id)

        chunks = query.all()
        docs = []
        for chunk, rfile in chunks:
            docs.append(
                {
                    "chunk_id": str(chunk.chunk_id),
                    "content": chunk.content or "",
                    "repository_path": rfile.path,
                    "metadata": {
                        "path": rfile.path,
                        "module": rfile.filename.split(".")[0],
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                    },
                }
            )

        if docs:
            self.fit(docs)

    def _auto_fit_workspace(self):
        """Automatically index cloned repository files under Temp directory (repo_*) for BM25 keyword retrieval."""
        import os
        import tempfile

        repo_docs = []
        temp_dir = tempfile.gettempdir()

        if os.path.exists(temp_dir):
            for entry in os.listdir(temp_dir):
                if entry.startswith("repo_") and os.path.isdir(
                    os.path.join(temp_dir, entry)
                ):
                    target_path = os.path.join(temp_dir, entry)
                    for root, dirs, files in os.walk(target_path):
                        # Prune git and build folders
                        dirs[:] = [
                            d
                            for d in dirs
                            if d
                            not in [
                                ".git",
                                "node_modules",
                                "target",
                                "build",
                                "dist",
                                "__pycache__",
                            ]
                        ]
                        for f in files:
                            if f.endswith(
                                (
                                    ".java",
                                    ".py",
                                    ".ts",
                                    ".js",
                                    ".go",
                                    ".cs",
                                    ".sql",
                                    ".md",
                                    ".json",
                                    ".xml",
                                    ".yml",
                                )
                            ):
                                file_path = os.path.join(root, f)
                                rel_path = os.path.relpath(
                                    file_path, target_path
                                ).replace("\\", "/")
                                try:
                                    with open(
                                        file_path, encoding="utf-8", errors="ignore"
                                    ) as fh:
                                        content = fh.read()
                                        if content.strip():
                                            repo_docs.append(
                                                {
                                                    "chunk_id": f"bm25_{rel_path}",
                                                    "content": content[:2500],
                                                    "repository_path": rel_path,
                                                    "metadata": {
                                                        "path": rel_path,
                                                        "module": f.split(".")[0],
                                                        "start_line": 1,
                                                        "end_line": len(
                                                            content.splitlines()
                                                        ),
                                                    },
                                                }
                                            )
                                except Exception:
                                    pass

        if repo_docs:
            self.fit(repo_docs)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve the top_k most relevant documents for a given query.
        Returns the original document dictionaries augmented with a 'bm25_score'.
        """
        if not self.bm25 or not self.corpus:
            self._auto_fit_workspace()

        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
            :top_k
        ]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = self.corpus[idx].copy()
                doc["bm25_score"] = float(scores[idx])
                doc["score"] = float(scores[idx])
                results.append(doc)

        return results


bm25_retriever = BM25Retriever()
