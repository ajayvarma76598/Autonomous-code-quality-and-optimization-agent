from langfuse import Langfuse
from backend.config import settings
from langfuse.langchain import CallbackHandler
import logging

logger = logging.getLogger(__name__)


class LangfuseService:
    def __init__(self):
        self.public_key = settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = settings.LANGFUSE_SECRET_KEY
        self.host = settings.LANGFUSE_BASE_URL
        
        try:
            self.langfuse = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            logger.info("Langfuse service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            self.langfuse = None

    def get_callback_handler(self, session_id: str, user_id: str = None) -> CallbackHandler:
        """
        Returns a Langchain-compatible callback handler linked to a specific session.
        This enables full graph-based tracing of the LangGraph execution.
        """
        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
        os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
        os.environ["LANGFUSE_HOST"] = self.host

        # In this SDK version, CallbackHandler doesn't accept user_id. We must set it via trace.
        if user_id:
            try:
                self.langfuse.trace(id=session_id, user_id=user_id)
            except Exception:
                pass
                
        return CallbackHandler(
            public_key=self.public_key,
            trace_context={"trace_id": session_id}
        )

    def get_prompt(self, prompt_name: str, version: int = None):
        """
        Retrieve a prompt from the Langfuse Prompt Registry.
        """
        if not self.langfuse:
            return None
        
        try:
            prompt = self.langfuse.get_prompt(prompt_name, version=version)
            return prompt
        except Exception as e:
            logger.error(f"Failed to retrieve prompt '{prompt_name}': {e}")
            return None
            
    def score(self, trace_id: str, name: str, value: float, comment: str = None):
        """
        Create a score on a trace in Langfuse, supporting multiple SDK versions.
        """
        if not self.langfuse:
            return
        try:
            if hasattr(self.langfuse, "create_score"):
                self.langfuse.create_score(trace_id=trace_id, name=name, value=float(value), comment=comment)
            elif hasattr(self.langfuse, "score"):
                self.langfuse.score(trace_id=trace_id, name=name, value=float(value), comment=comment)
            elif hasattr(self.langfuse, "score_current_trace"):
                self.langfuse.score_current_trace(name=name, value=float(value), comment=comment)
        except Exception as e:
            logger.warning(f"Could not score trace in Langfuse: {e}")

    def trace(self, id: str = None, name: str = None, user_id: str = None, metadata: dict = None):
        """
        Start or update an execution trace in Langfuse.
        """
        if not self.langfuse:
            return None
            
        try:
            if hasattr(self.langfuse, "trace"):
                return self.langfuse.trace(id=id, name=name, user_id=user_id, metadata=metadata or {})
            elif hasattr(self.langfuse, "start_observation"):
                return self.langfuse.start_observation(name=name or "execution", metadata=metadata or {})
        except Exception as e:
            logger.warning(f"Could not update trace execution in Langfuse: {e}")
            return None

    def create_span(self, trace_id: str, name: str, input_data: any = None, output_data: any = None, metadata: dict = None):
        """
        Creates an explicit observation span under a trace_id for agent step visibility in Langfuse.
        """
        if not self.langfuse:
            return None
        try:
            if hasattr(self.langfuse, "span"):
                return self.langfuse.span(
                    trace_id=trace_id,
                    name=name,
                    input=input_data,
                    output=output_data,
                    metadata=metadata or {}
                )
        except Exception as e:
            logger.warning(f"Could not create span in Langfuse: {e}")
            return None

    def trace_execution(self, name: str, session_id: str, metadata: dict = None):
        """
        Backward-compatible alias for trace.
        """
        return self.trace(id=session_id, name=name, metadata=metadata)

langfuse_service = LangfuseService()
