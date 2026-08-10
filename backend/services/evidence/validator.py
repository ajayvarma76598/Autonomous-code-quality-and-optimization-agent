import logging
from typing import List
from backend.models.evidence import EvidenceContext

logger = logging.getLogger(__name__)

class EvidenceValidator:
    """
    Validates gathered EvidenceContext blocks before passing to agent prompts.
    Flags missing or incomplete evidence and appends explicit warning notices.
    """
    
    @staticmethod
    def validate(context: EvidenceContext, agent_type: str) -> EvidenceContext:
        warnings = []
        is_complete = True
        is_sufficient = True

        # 1. Quality / Coverage / Performance agents need SonarQube metrics
        if agent_type in ["coverage", "performance", "quality"]:
            if not context.sonar_metrics or not context.sonar_metrics.data or "uninitialized" in str(context.sonar_metrics.data):
                is_complete = False
                warnings.append(f"SonarQube metrics are uninitialized or unavailable for agent '{agent_type}'.")

        # 2. Retrieval / Architecture / Documentation agents need retrieved code/doc chunks
        if agent_type in ["repository", "architecture", "performance", "documentation"]:
            if not context.retrieved_chunks or not context.retrieved_chunks.data:
                is_sufficient = False
                warnings.append(f"No retrieved code or documentation chunks found for query in agent '{agent_type}'.")

        context.is_complete = is_complete
        context.is_sufficient = is_sufficient
        context.validation_warnings = warnings
        return context

evidence_validator = EvidenceValidator()
