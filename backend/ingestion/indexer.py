import logging
from typing import Optional
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from backend.database.models.models import DocumentChunk, Embedding
from backend.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class Indexer:
    def __init__(self):
        # We use LangChain's recursive splitter for sensible markdown/code chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def index_text(self, db: Session, text: str, file_id: Optional[UUID] = None, object_id: Optional[UUID] = None) -> int:
        """
        Chunks the provided text, generates embeddings, and persists them to the database.
        Returns the number of chunks created.
        """
        if not text.strip():
            logger.warning("Empty text provided to indexer. Skipping.")
            return 0

        # 1. Chunk the text
        chunks = self.text_splitter.split_text(text)
        logger.info(f"Split document into {len(chunks)} chunks.")

        if not chunks:
            return 0

        # 2. Generate embeddings via Azure OpenAI
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        vectors = embedding_service.generate_embeddings(chunks)

        if not vectors or len(vectors) != len(chunks):
            logger.error("Failed to generate embeddings or mismatched count.")
            return 0

        # 3. Persist to PostgreSQL via SQLAlchemy using Bulk Inserts
        import uuid
        try:
            doc_chunks = []
            embeddings = []
            
            for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
                chunk_id = uuid.uuid4()
                # Create DocumentChunk
                doc_chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    file_id=file_id,
                    object_id=object_id,
                    chunk_index=i,
                    chunk_type="markdown",
                    content=chunk_text
                ))

                # Create Embedding
                embeddings.append(Embedding(
                    embedding_id=uuid.uuid4(),
                    chunk_id=chunk_id,
                    provider=embedding_service.provider,
                    model_name=embedding_service.model,
                    embedding_dimension=len(vector),
                    embedding=vector
                ))
                
            db.add_all(doc_chunks)
            db.add_all(embeddings)
            db.commit()
            inserted_chunks = len(chunks)
            logger.info(f"Successfully indexed {inserted_chunks} chunks with embeddings via bulk insert.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist embeddings to database: {e}")
            raise

        return inserted_chunks

indexer = Indexer()
