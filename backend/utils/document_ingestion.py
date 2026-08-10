import os
import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.models.models import User, Repository, RepositorySnapshot, RepositoryFile
from backend.ingestion.document_parser import document_parser
from backend.ingestion.indexer import indexer

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "Documents"
)

def _get_or_create_capstone_repo(db: Session) -> RepositorySnapshot:
    """Gets or creates the 'capstone_knowledge_base' dummy repository for PDFs."""
    user = db.query(User).filter_by(email="capstone@example.com").first()
    if not user:
        user = User(email="capstone@example.com", username="capstone_admin", role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)

    repo = db.query(Repository).filter_by(name="capstone_knowledge_base").first()
    if not repo:
        repo = Repository(
            user_id=user.user_id,
            name="capstone_knowledge_base",
            git_provider="local",
            description="Capstone PDF rulebooks and handbooks",
            status="Active"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    snapshot = db.query(RepositorySnapshot).filter_by(repository_id=repo.repository_id).first()
    if not snapshot:
        snapshot = RepositorySnapshot(
            repository_id=repo.repository_id,
            commit_hash="documents_v1",
            branch="main",
            is_latest=True
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

    return snapshot

def ingest_documents_if_missing():
    """
    Scans the Documents/ folder and ingests any PDFs that are missing from the database.
    Can be toggled via AUTO_INGEST_PDFS env variable.
    """
    if os.environ.get("AUTO_INGEST_PDFS", "false").lower() != "true":
        logger.info("Capstone auto-ingestion disabled via AUTO_INGEST_PDFS=false.")
        return
        
    logger.info("Starting Capstone auto-ingestion check...")
    
    if not os.path.exists(DOCUMENTS_DIR):
        logger.warning(f"Documents directory not found at {DOCUMENTS_DIR}")
        return

    db = SessionLocal()
    try:
        snapshot = _get_or_create_capstone_repo(db)
        
        for filename in os.listdir(DOCUMENTS_DIR):
            if not filename.endswith(".pdf"):
                continue
                
            filepath = os.path.join(DOCUMENTS_DIR, filename)
            
            # Check if this document is already in the database
            existing_file = db.query(RepositoryFile).filter_by(
                snapshot_id=snapshot.snapshot_id, 
                filename=filename
            ).first()
            
            if existing_file:
                logger.info(f"Document {filename} already indexed. Skipping.")
                continue
                
            logger.info(f"[Auto-Ingestion Task] Starting processing for missing document: {filename}...")
            
            # Parse the PDF using PyMuPDF / LlamaParse
            try:
                logger.info(f"[Auto-Ingestion Task] Invoking DocumentParser on '{filepath}'...")
                markdown_text = document_parser.parse_document(filepath)
                logger.info(f"[Auto-Ingestion Task] DocumentParser finished '{filename}'. Extracted {len(markdown_text) if markdown_text else 0} characters.")
            except Exception as e:
                logger.error(f"[Auto-Ingestion Task] Failed to parse {filename}: {e}", exc_info=True)
                continue
                
            if not markdown_text:
                logger.warning(f"[Auto-Ingestion Task] No text extracted from {filename}")
                continue
                
            # Create a file record
            repo_file = RepositoryFile(
                snapshot_id=snapshot.snapshot_id,
                path=filename,
                filename=filename,
                extension=".pdf",
                language="markdown",
                line_count=len(markdown_text.splitlines())
            )
            db.add(repo_file)
            db.commit()
            db.refresh(repo_file)
            logger.info(f"[Auto-Ingestion Task] Saved RepositoryFile record (ID={repo_file.file_id}) for {filename}")
            
            # Index the text to generate embeddings
            try:
                logger.info(f"[Auto-Ingestion Task] Indexing & generating embeddings for '{filename}'...")
                chunks = indexer.index_text(db=db, text=markdown_text, file_id=repo_file.file_id)
                logger.info(f"[Auto-Ingestion Task] Successfully indexed {chunks} chunks for {filename}")
            except Exception as e:
                logger.error(f"[Auto-Ingestion Task] Failed to index {filename}: {e}", exc_info=True)
                
        logger.info("[Auto-Ingestion Task] Capstone auto-ingestion check complete.")
    finally:
        db.close()
