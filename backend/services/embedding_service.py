import logging
import os

from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        import dotenv

        dotenv.load_dotenv()
        self.provider = os.getenv("LLM_PROVIDER", "azure").strip().lower()

        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_deployment = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        )
        self.model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        try:
            if self.provider == "azure":
                self.embeddings = AzureOpenAIEmbeddings(
                    azure_endpoint=self.azure_endpoint,
                    api_key=self.azure_api_key,
                    openai_api_version=self.azure_api_version,
                    azure_deployment=self.azure_deployment,
                    model=self.model,
                )
            else:
                self.embeddings = OpenAIEmbeddings(model=self.model)
            logger.info("Embedding service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Embedding service: {e}")
            self.embeddings = None

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generates vector embeddings for a batch of texts.
        """
        if not self.embeddings:
            logger.warning(
                "[EmbeddingService] Embeddings object uninitialized. Returning zero vectors."
            )
            return [[0.0] * 1536 for _ in texts]
        if not texts:
            return []

        try:
            logger.info(
                f"[EmbeddingService] Generating embeddings for batch of {len(texts)} texts..."
            )
            res = self.embeddings.embed_documents(texts)
            logger.info(
                f"[EmbeddingService] Batch embedding generation complete ({len(res)} vectors generated)."
            )
            return res
        except Exception as e:
            logger.warning(
                f"[EmbeddingService] Error generating document embeddings: {e}"
            )
            return [[0.0] * 1536 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        """
        Generates a single vector embedding for query text.
        """
        if not self.embeddings or not text:
            return [0.0] * 1536
        try:
            logger.info(
                f"[EmbeddingService] Embedding single query (len={len(text)})..."
            )
            res = self.embeddings.embed_query(text)
            logger.info(
                f"[EmbeddingService] Query embedding complete (dim={len(res)})."
            )
            return res
        except Exception as e:
            logger.warning(f"[EmbeddingService] Error embedding query text: {e}")
            return [0.0] * 1536

    def get_embed_model(self):
        """
        Returns self for backward compatibility with get_embed_model().embed_query() calls.
        """
        return self


embedding_service = EmbeddingService()
