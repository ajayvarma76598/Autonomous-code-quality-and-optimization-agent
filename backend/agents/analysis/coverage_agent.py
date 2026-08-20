import logging
from typing import Literal

from pydantic import Field

from backend.agents.base_agent import BaseAgent
from backend.models.analysis import BaseAnalysisFinding, BaseAnalysisResult
from backend.workflows.state import AgentState

logger = logging.getLogger(__name__)


class CoverageFinding(BaseAnalysisFinding):
    tested_status: Literal["FULLY_TESTED", "PARTIALLY_TESTED", "UNTESTED"] = Field(
        description="The test coverage status of this specific module/file."
    )
    risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        description="The risk level of this missing coverage, influenced by architectural importance."
    )
    file_path: str | None = Field(
        default=None, description="The file path lacking coverage."
    )
    suggested_test_cases: list[str] | None = Field(
        default=None,
        description="A descriptive list of specific test cases that should be written to cover the missing lines (e.g., 'Write a test for the null user edge case').",
    )


class CoverageResult(BaseAnalysisResult):
    findings: list[CoverageFinding] = Field(
        description="List of structured test coverage findings."
    )


class TestCoverageAgent(BaseAgent):
    def __init__(self):
        super().__init__("coverage", output_schema=CoverageResult)

    def execute(self, state: AgentState) -> AgentState:
        """
        Scans for edge cases and missing unit tests.
        It explicitly consumes both the RepositoryContext AND the ArchitectureResult to provide risk-aware coverage metrics.
        """
        session_id = state.get("shared", {}).get("session_id", "unknown")
        logger.info(f"Test Coverage Agent processing state for session {session_id}")

        # In a real LangGraph setup, repository_id and analysis_id would be in the workflow state
        repository_id = (
            state.get("shared", {}).get("snapshot_id")
            or state.get("shared", {}).get("repository_id")
            or session_id
        )
        analysis_id = session_id

        query = state.get("shared", {}).get("query")
        # 1. Fetch typed evidence payload from EvidenceService
        from backend.services.evidence_service import evidence_service

        evidence_context = evidence_service.gather_evidence(
            "coverage", repository_id, analysis_id, query=query
        )
        architecture_result = state.get("analysis", {}).get("architecture", {})

        if not evidence_context:
            logger.error("CoverageAgent: Missing repository_context in shared state.")
            from backend.workflows.state import StateManager, TaskStatus

            state = StateManager.update_workflow_status(state, TaskStatus.FAILED)
            return state

        architecture_str = str(
            architecture_result.get("findings", "No architecture findings available.")
        )

        # --- NEW: Fetch Uncovered Files & Source Code Snippets ---
        import os

        import requests

        uncovered_files_context = "No uncovered files data fetched from SonarQube."
        try:
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            if sonar_host and sonar_token:
                # Fetch components with the most uncovered lines
                tree_url = f"{sonar_host}/api/measures/component_tree?component={repository_id}&metricKeys=uncovered_lines,coverage&qualifiers=FIL&ps=5"
                resp = requests.get(tree_url, auth=(sonar_token, ""), timeout=10)
                if resp.status_code == 200:
                    components = resp.json().get("components", [])

                    # Filter for files with actual uncovered lines > 0
                    worst_files = []
                    for c in components:
                        uncov = 0
                        for m in c.get("measures", []):
                            if m["metric"] == "uncovered_lines":
                                uncov = int(m.get("value", 0))
                        if uncov > 0:
                            worst_files.append(
                                {"path": c.get("path"), "uncovered": uncov}
                            )

                    # Sort descending by uncovered lines
                    worst_files.sort(key=lambda x: x["uncovered"], reverse=True)

                    if worst_files:
                        local_path = (
                            evidence_context.repository_metadata.get("local_path")
                            if evidence_context.repository_metadata
                            else None
                        )
                        file_blocks = []
                        for wf in worst_files[:5]:  # Top 5 worst
                            file_path = wf["path"]
                            uncovered = wf["uncovered"]

                            snippet = "Source code not available locally."
                            if local_path and file_path:
                                full_file_path = os.path.join(local_path, file_path)
                                if os.path.exists(full_file_path):
                                    try:
                                        with open(
                                            full_file_path, encoding="utf-8"
                                        ) as f:
                                            lines = f.readlines()
                                            # Grab up to the first 100 lines for context
                                            snippet_lines = lines[:100]
                                            snippet = "".join(
                                                [
                                                    f"{idx + 1}: {snippet_lines[idx]}"
                                                    for idx in range(len(snippet_lines))
                                                ]
                                            )
                                            if len(lines) > 100:
                                                snippet += "\n... (file truncated) ..."
                                    except Exception:
                                        pass

                            file_blocks.append(
                                f"File: {file_path}\nUncovered Lines: {uncovered}\n"
                                f"Source Code Snippet:\n{snippet}\n"
                            )
                        uncovered_files_context = "\n".join(file_blocks)
        except Exception as e:
            logger.warning(f"Failed to fetch uncovered files from SonarQube: {e}")
        # --------------------------------------------------------------------

        from langchain_core.prompts import ChatPromptTemplate

        # 2. Formulate explicit risk-aware prompt using typed evidence
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert Test Engineer. Review the Evidence Context, Architecture Findings, and Uncovered Files.\n"
                    "You must provide structured coverage findings.\n"
                    "Crucially, DO NOT re-calculate raw coverage. You MUST use SonarQube metrics as the absolute priority and primary source of truth for test coverage data. Cross-reference coverage gaps with Architecture Findings to determine the true Risk Level.\n"
                    "A missing test in a Core Service is CRITICAL risk. A missing test in a DTO is LOW risk.\n"
                    "For the specific files provided in 'Uncovered Files', analyze the source code and describe exactly WHAT test cases should be written to cover the missing lines in the `suggested_test_cases` field. DO NOT generate the actual test code, just provide descriptive instructions.",
                ),
                (
                    "human",
                    "Evidence Context:\n{evidence_context}\n\nArchitecture Findings:\n{architecture_str}\n\nUncovered Files:\n{uncovered_files_context}",
                ),
            ]
        )

        # 3. Invoke LLM strictly for structured output
        structured_llm = self.llm.with_structured_output(
            CoverageResult, method="function_calling"
        )
        result: CoverageResult = structured_llm.invoke(
            prompt.format_messages(
                evidence_context=evidence_context.format_for_prompt(),
                architecture_str=architecture_str,
                uncovered_files_context=uncovered_files_context,
            )
        )

        # 4. Save analysis results and persist
        from backend.services.persistence_service import persistence_service
        from backend.workflows.state import StateManager, TaskStatus

        # Queue for database persistence
        persistence_service.queue_agent_result(analysis_id, "CoverageAgent", result)

        analysis_payload = {
            "summary": result.summary,
            "findings": [f.dict() for f in result.findings],
            "metrics": result.metrics,
            "overall_score": result.overall_score,
        }
        if evidence_context.sql_results:
            analysis_payload["sql_results"] = (
                evidence_context.sql_results.model_dump()
                if hasattr(evidence_context.sql_results, "model_dump")
                else evidence_context.sql_results.dict()
            )
        if evidence_context.sonar_metrics:
            analysis_payload["sonar_metrics"] = (
                evidence_context.sonar_metrics.model_dump()
                if hasattr(evidence_context.sonar_metrics, "model_dump")
                else evidence_context.sonar_metrics.dict()
            )
        if evidence_context.retrieved_chunks:
            analysis_payload["retrieved_chunks"] = (
                evidence_context.retrieved_chunks.model_dump()
                if hasattr(evidence_context.retrieved_chunks, "model_dump")
                else evidence_context.retrieved_chunks.dict()
            )
            if "context" not in state["shared"] or state["shared"]["context"] is None:
                state["shared"]["context"] = []
            if isinstance(evidence_context.retrieved_chunks.data, list):
                state["shared"]["context"].extend(
                    evidence_context.retrieved_chunks.data
                )

        state = StateManager.save_analysis(state, "coverage", analysis_payload)

        if "workflow" not in state or state["workflow"] is None:
            state["workflow"] = {}
        state["workflow"]["current_node"] = self.name
        if (
            "execution_path" not in state["workflow"]
            or state["workflow"]["execution_path"] is None
        ):
            state["workflow"]["execution_path"] = []
        state["workflow"]["execution_path"].append(self.name)

        state = StateManager.update_workflow_status(state, TaskStatus.COMPLETE)
        return state
