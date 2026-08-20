import logging
from typing import Literal

from pydantic import Field

from backend.agents.base_agent import BaseAgent
from backend.models.analysis import BaseAnalysisFinding, BaseAnalysisResult
from backend.workflows.state import AgentState

logger = logging.getLogger(__name__)


class ArchitectureFinding(BaseAnalysisFinding):
    issue_type: Literal["FACT", "OPINION", "SUGGESTION"] = Field(
        description="Whether this is an objective fact, an opinion on design, or a suggestion."
    )


class ArchitectureResult(BaseAnalysisResult):
    findings: list[ArchitectureFinding] = Field(
        description="List of structured architectural findings."
    )


class ArchitectureAgent(BaseAgent):
    def __init__(self):
        super().__init__("architecture", output_schema=ArchitectureResult)

    def execute(self, state: AgentState) -> AgentState:
        """
        Validates against SOLID principles, dependency injection patterns, and microservice boundaries.
        Strictly consumes the immutable RepositoryContext without executing tools.
        """
        session_id = state.get("shared", {}).get("session_id", "unknown")
        logger.info(f"Architecture Agent processing state for session {session_id}")

        # In a real LangGraph setup, repository_id and analysis_id would be in the workflow state
        repository_id = (
            state.get("shared", {}).get("snapshot_id")
            or state.get("shared", {}).get("repository_id")
            or session_id
        )
        analysis_id = session_id

        query = state.get("shared", {}).get("query")
        # 1. Fetch typed evidence context from EvidenceService (Lazy evaluated & Cached)
        from backend.services.evidence_service import evidence_service

        evidence_context = evidence_service.gather_evidence(
            "architecture", repository_id, analysis_id, query=query
        )

        if not evidence_context:
            logger.error(
                "ArchitectureAgent: Missing repository_context in shared state."
            )
            from backend.workflows.state import StateManager, TaskStatus

            state = StateManager.update_workflow_status(state, TaskStatus.FAILED)
            return state

        from langchain_core.prompts import ChatPromptTemplate

        # 2. Formulate specific prompt using typed evidence
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an Expert Software Architect reviewing a repository.\n\n"
                    "EVIDENCE HIERARCHY RULES:\n"
                    "1. Tier 1 - AST & Symbol Index (Highest Priority / Deterministic): Use for class names, method counts, interfaces, and exact file line numbers.\n"
                    "2. Tier 2 - SQL Dependency Graph: Use for cross-file imports, call graphs, and module relationships.\n"
                    "3. Tier 3 - SonarQube Metrics: Use for code coverage, cyclomatic complexity, code smells, and quality gates.\n"
                    "4. Tier 4 - Architecture Docs & Build Configs (README.md, ARCHITECTURE.md, docker-compose, pom.xml): Use for design intent, tech stack, and API definitions.\n"
                    "5. Tier 5 - Vector Semantic Chunks: Use for semantic context search.\n\n"
                    "STRICT GROUNDING RULES:\n"
                    "- Do NOT invent SOLID violations or cyclomatic complexity numbers out of thin air.\n"
                    "- Structural facts and metrics MUST come from AST / Static Analysis / SonarQube.\n"
                    "- Design intent and tech stack MUST come from Architecture Docs & Configs.\n"
                    "- Explicitly separate Observed Facts (file paths, method counts, imports) from Inferences and Recommendations.",
                ),
                ("human", "Evidence Context:\n{evidence_context}"),
            ]
        )

        # 3. Invoke LLM strictly for structured output
        structured_llm = self.llm.with_structured_output(
            ArchitectureResult, method="function_calling"
        )
        result: ArchitectureResult = structured_llm.invoke(
            prompt.format_messages(
                evidence_context=evidence_context.format_for_prompt()
            )
        )

        # 4. Save analysis results and persist
        from backend.services.persistence_service import persistence_service
        from backend.workflows.state import StateManager, TaskStatus

        # Queue for database persistence
        persistence_service.queue_agent_result(analysis_id, "ArchitectureAgent", result)

        analysis_payload = {
            "summary": result.summary,
            "findings": [f.dict() for f in result.findings],
            "metrics": result.metrics,
            "overall_score": result.overall_score,
        }
        if evidence_context.dependency_graph:
            analysis_payload["dependency_graph"] = (
                evidence_context.dependency_graph.model_dump()
                if hasattr(evidence_context.dependency_graph, "model_dump")
                else evidence_context.dependency_graph.dict()
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

        state = StateManager.save_analysis(state, "architecture", analysis_payload)
        state["final_response"] = result.summary

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
