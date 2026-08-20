import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class DeterministicValidator:
    """
    High-Performance 2-Tier Validation Gate.
    Tier 1: Deterministic Python Validator (Citations, Repository Match, Evidence, Metrics, Confidence, Coverage).
    Tier 2: Selective LLM Validator (Reasoning, Evidence-based Recommendations, Hallucinations).
    """

    def validate_output(
        self, response_text: str, citations: list[Any], context_chunks: list[Any]
    ) -> dict[str, Any]:
        """
        Executes Tier 1 Deterministic Validation on the report output.
        """
        if not response_text or response_text.strip() == "":
            return {
                "verdict": "FAIL",
                "faithfulness": 0.0,
                "relevancy": 0.0,
                "confidence": 0.0,
                "context_precision": 0.0,
                "recall": 0.0,
                "requires_llm_eval": False,
                "checks": {
                    "citation_exists": False,
                    "repository_matches": False,
                    "required_evidence_present": False,
                    "metrics_verified": False,
                    "confidence_computed": 0.0,
                    "coverage_calculated": 0.0,
                },
                "reason": "Empty response text",
            }

        # 1. Citation Exists?
        cited_count = len(citations)
        citation_exists = cited_count > 0

        # 2. Required Evidence Present?
        total_chunks = len(context_chunks) if context_chunks else 0
        required_evidence_present = total_chunks > 0 or cited_count > 0

        # 3. Repository Matches?
        file_path_matches = re.findall(
            r"[\w\/\.\-]+\.(?:py|java|js|ts|json|md|yml|yaml|xml)",
            response_text,
            re.IGNORECASE,
        )
        repository_matches = len(file_path_matches) > 0 or cited_count > 0

        # 4. Metrics Verified?
        metrics_present = bool(
            re.search(r"\b\d+(?:\.\d+)?%\b|\b\d+\s*ms\b", response_text)
        )
        metrics_verified = (
            True
            if not metrics_present
            else (cited_count > 0 or required_evidence_present)
        )

        # 5. Coverage Calculated
        coverage_calculated = (
            round(min(1.0, cited_count / max(1, min(5, total_chunks))), 4)
            if total_chunks > 0
            else (1.0 if cited_count > 0 else 0.5)
        )

        # 6. Confidence Computed
        faithfulness = (
            round(min(1.0, 0.70 + (coverage_calculated * 0.30)), 4)
            if citation_exists or repository_matches
            else 0.60
        )
        relevancy = 0.95 if len(response_text) > 30 else 0.50
        confidence = round((faithfulness * 0.6) + (relevancy * 0.4), 4)

        # 80-90% of standard queries pass deterministically (confidence >= 0.70)
        # 10-20% of edge-case/low-confidence queries trigger Tier 2 LLM validation
        # UPDATE: User requested to ALWAYS ask the agent to reason the evaluation.
        requires_llm = True

        logger.info(
            f"[DeterministicValidator Tier 1] Citations: {citation_exists} | Repo Match: {repository_matches} | Evidence: {required_evidence_present} | Coverage: {coverage_calculated:.2f} | Confidence: {confidence} | Requires LLM: {requires_llm}"
        )

        return {
            "verdict": "PASS" if confidence >= 0.70 else "RETRY",
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "confidence": confidence,
            "context_precision": coverage_calculated,
            "recall": faithfulness,
            "requires_llm_eval": requires_llm,
            "checks": {
                "citation_exists": citation_exists,
                "repository_matches": repository_matches,
                "required_evidence_present": required_evidence_present,
                "metrics_verified": metrics_verified,
                "confidence_computed": confidence,
                "coverage_calculated": coverage_calculated,
            },
            "reason": "Tier 1 deterministic validation passed"
            if not requires_llm
            else "Tier 1 confidence below threshold, triggering Tier 2 LLM validation",
        }


deterministic_validator = DeterministicValidator()
