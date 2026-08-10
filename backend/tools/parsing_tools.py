from langchain_core.tools import tool
from typing import List, Dict, Any
from backend.ingestion.tree_sitter_parser import code_parser

@tool
def parse_source_code(file_path: str, language: str = "python") -> Any:
    """
    Parses a source code file using Tree-Sitter and extracts code objects (functions, classes).
    Returns a list of extracted syntax objects with their signatures and complexity metrics.
    """
    try:
        return code_parser.parse_file(file_path, language)
    except Exception as e:
        return f"Tool Error: {str(e)}"

@tool
def ingest_document(file_path: str) -> str:
    """
    Ingests an unstructured document (PDF, Image) containing complex diagrams or tables.
    Returns a highly structured Markdown representation extracted via LlamaParse Multimodal OCR.
    """
    from backend.ingestion.document_parser import document_parser
    from backend.ingestion.indexer import indexer
    from backend.database.session import SessionLocal
    
    try:
        # 1. Parse document (Markdown string)
        markdown_text = document_parser.parse_document(file_path)
        
        # 2. Index the document (Generate embeddings & store in DB)
        db = SessionLocal()
        try:
            chunks_indexed = indexer.index_text(db=db, text=markdown_text)
            return f"Successfully ingested {file_path}. Generated {chunks_indexed} embedding chunks."
        finally:
            db.close()
    except Exception as e:
        return f"Tool Error: {str(e)}"
