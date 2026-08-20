import logging
import os

from langchain_openai import AzureChatOpenAI, ChatOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        # We read from the env since the Settings model allows extra vars now.
        self.provider = os.getenv("LLM_PROVIDER", "azure").strip().lower()

        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_deployment = os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT")
        self.azure_fast_deployment = os.getenv(
            "AZURE_OPENAI_FAST_LLM_DEPLOYMENT", self.azure_deployment
        )
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.openai_fast_model = os.getenv("OPENAI_FAST_MODEL", "gpt-4o-mini")

    def get_llm(self, temperature: float = 0.0, model_type: str = "default"):
        if self.provider == "azure":
            deployment = (
                self.azure_fast_deployment
                if model_type == "fast"
                else self.azure_deployment
            )
            logger.info(
                f"[LLMService] Initializing AzureChatOpenAI (Deployment='{deployment}', Type='{model_type}', Temp={temperature})"
            )
            return AzureChatOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_version=self.azure_api_version,
                api_key=self.azure_api_key,
                azure_deployment=deployment,
                temperature=temperature,
            )
        else:
            model = (
                self.openai_fast_model if model_type == "fast" else self.openai_model
            )
            logger.info(
                f"[LLMService] Initializing ChatOpenAI (Model='{model}', Type='{model_type}', Temp={temperature})"
            )
            return ChatOpenAI(model=model, temperature=temperature)


llm_service = LLMService()
