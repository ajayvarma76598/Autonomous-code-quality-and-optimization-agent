from abc import ABC, abstractmethod
from typing import Optional, Any
from backend.models.evidence import EvidenceBlock

class BaseEvidenceProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def default_confidence(self) -> float:
        pass
        
    @abstractmethod
    def fetch(self, repository_id: str, analysis_id: Optional[str] = None, **kwargs) -> Optional[EvidenceBlock]:
        """Fetches evidence from the specific provider."""
        pass
