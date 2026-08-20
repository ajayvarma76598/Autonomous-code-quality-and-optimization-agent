from abc import ABC, abstractmethod

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
    def fetch(
        self, repository_id: str, analysis_id: str | None = None, **kwargs
    ) -> EvidenceBlock | None:
        """Fetches evidence from the specific provider."""
        pass
