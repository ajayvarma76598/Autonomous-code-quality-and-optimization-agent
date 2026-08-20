from typing import Any

from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    chunk_id: str = Field(description="Unique ID for citation reference, e.g., C1, C2")
    file_path: str = Field(description="Source file repository path")
    start_line: int | None = Field(default=None, description="Start line number")
    end_line: int | None = Field(default=None, description="End line number")
    content: str = Field(description="Code or documentation snippet")
    confidence: float = Field(default=1.0, description="Confidence score")


class EvidenceBundle(BaseModel):
    chunks: list[EvidenceChunk] = Field(default_factory=list)
    confidence: float = Field(default=1.0)
    query_coverage: float = Field(default=1.0)
    is_sufficient: bool = Field(default=True)
    missing_topics: list[str] = Field(default_factory=list)


class EvidenceBlock(BaseModel):
    data: Any = Field(description="The actual evidence data.")
    confidence_score: float = Field(
        description="Confidence score for this evidence block (0.0 to 1.0)."
    )
    provider_name: str = Field(description="The provider that supplied this evidence.")


class EvidenceContext(BaseModel):
    repository_metadata: EvidenceBlock | None = Field(
        default=None, description="Metadata such as package structure and entry points."
    )
    dependency_graph: EvidenceBlock | None = Field(
        default=None, description="Graph of cross-file dependencies."
    )
    sonar_metrics: EvidenceBlock | None = Field(
        default=None, description="Static analysis metrics from SonarQube."
    )
    sql_results: EvidenceBlock | None = Field(
        default=None, description="SQL table schema and relationships."
    )
    retrieved_chunks: EvidenceBlock | None = Field(
        default=None, description="Code chunks retrieved via vector search."
    )
    structured_outputs: EvidenceBlock | None = Field(
        default=None, description="Structured outputs from other agents."
    )
    historical_analysis: EvidenceBlock | None = Field(
        default=None, description="Historical analysis for the repository."
    )
    is_complete: bool = Field(
        default=True, description="True if all expected evidence sources were gathered."
    )
    is_sufficient: bool = Field(
        default=True, description="True if evidence confidence >= 0.45 threshold."
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings regarding missing or incomplete evidence sources.",
    )

    def format_for_prompt(self) -> str:
        """Serializes the typed evidence into a clean Markdown string with explicit [C1], [C2] Citation IDs for the LLM."""
        parts = []
        if self.validation_warnings:
            warning_text = "\n".join([f"- {w}" for w in self.validation_warnings])
            parts.append(
                f"### [EVIDENCE WARNINGS]\n{warning_text}\n*DO NOT invent placeholder file names (e.g. CoreService1.java, DTO1.java) or metrics for missing evidence.*"
            )

        if self.repository_metadata:
            parts.append(
                f"### Repository Metadata (Confidence: {self.repository_metadata.confidence_score})\n{self.repository_metadata.data}"
            )
        if self.dependency_graph:
            parts.append(
                f"### Dependency Graph (Confidence: {self.dependency_graph.confidence_score})\n{self.dependency_graph.data}"
            )
        if self.sonar_metrics:
            parts.append(
                f"### SonarQube Metrics (Confidence: {self.sonar_metrics.confidence_score})\n{self.sonar_metrics.data}"
            )
        if self.sql_results:
            parts.append(
                f"### SQL Data (Confidence: {self.sql_results.confidence_score})\n{self.sql_results.data}"
            )

        if self.retrieved_chunks:
            parts.append(
                f"### Retrieved Source Evidence [C1..CN] (Confidence: {self.retrieved_chunks.confidence_score})"
            )
            chunks_data = self.retrieved_chunks.data
            if isinstance(chunks_data, list):
                for idx, c in enumerate(chunks_data, 1):
                    c_id = f"C{idx}"
                    file_path = getattr(c, "repository_path", None) or (
                        c.get("repository_path") if isinstance(c, dict) else "unknown"
                    )
                    start_l = getattr(c, "start_line", None) or (
                        c.get("start_line") if isinstance(c, dict) else None
                    )
                    end_l = getattr(c, "end_line", None) or (
                        c.get("end_line") if isinstance(c, dict) else None
                    )
                    lines_str = (
                        f"Lines {start_l}-{end_l}"
                        if start_l and end_l
                        else "File Chunk"
                    )
                    ev_list = getattr(c, "evidence", None) or (
                        c.get("evidence") if isinstance(c, dict) else []
                    )
                    snippet = (
                        ev_list[0]
                        if isinstance(ev_list, list) and ev_list
                        else str(ev_list)
                    )

                    parts.append(
                        f"[{c_id}] File: {file_path} ({lines_str})\nContent:\n{snippet}"
                    )
            else:
                parts.append(f"[C1] Evidence:\n{chunks_data}")

        if self.structured_outputs:
            parts.append(
                f"### Structured Outputs (Confidence: {self.structured_outputs.confidence_score})\n{self.structured_outputs.data}"
            )
        if self.historical_analysis:
            parts.append(
                f"### Historical Analysis (Confidence: {self.historical_analysis.confidence_score})\n{self.historical_analysis.data}"
            )
        return "\n\n".join(parts)
