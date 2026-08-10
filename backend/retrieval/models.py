from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RetrievedContext(BaseModel):
    chunk_id: Optional[str] = Field(default=None, description="Unique chunk ID.")
    document_id: Optional[str] = Field(default=None, description="Document ID.")
    module: str = Field(description="The source file or module.")
    function: Optional[str] = Field(default=None, description="The specific function or class name.")
    symbol_name: Optional[str] = Field(default=None, description="Symbol name.")
    start_line: Optional[int] = Field(default=None, description="Start line number in source file.")
    end_line: Optional[int] = Field(default=None, description="End line number in source file.")
    evidence: List[str] = Field(default_factory=list, description="The raw code or text chunk.")
    related_symbols: List[str] = Field(default_factory=list, description="Related imports, parents, or subclasses.")
    repository_path: str = Field(description="The local repository path.")
    bm25_score: Optional[float] = Field(default=None, description="Raw BM25 score.")
    vector_score: Optional[float] = Field(default=None, description="Raw Vector cosine similarity score.")
    rrf_score: Optional[float] = Field(default=None, description="Combined RRF score.")
    score: float = Field(default=0.0, description="The primary relevance score.")
    confidence_score: float = Field(default=1.0, description="Confidence score.")
