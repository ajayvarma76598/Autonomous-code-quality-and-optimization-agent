from typing import Any, Literal

from pydantic import BaseModel, Field


class BaseAnalysisFinding(BaseModel):
    title: str = Field(description="A short title for the finding.")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        description="The severity of the issue."
    )
    impact: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="The impact of this finding."
    )
    confidence: float = Field(
        description="Score from 0.0 to 1.0 estimating confidence in this finding."
    )
    evidence_files: list[str] = Field(
        default_factory=list, description="Specific files backing up this finding."
    )
    reason: str = Field(description="Detailed reason for the finding.")
    recommendation: str = Field(
        description="Actionable recommendation to resolve the issue."
    )


class BaseAnalysisResult(BaseModel):
    summary: str = Field(description="A brief summary of the overall analysis.")
    findings: list[BaseAnalysisFinding] = Field(
        default_factory=list, description="List of structured findings."
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Numerical or structured metrics (e.g. coverage percentages, complexity scores).",
    )
    overall_score: int = Field(
        description="Score from 0 to 100 on the quality of this specific domain."
    )
