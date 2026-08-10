import logging
from typing import List, Literal, Optional
from pydantic import Field
from langchain_core.messages import SystemMessage, HumanMessage
from backend.workflows.state import AgentState
from backend.agents.base_agent import BaseAgent
from backend.tools.parsing_tools import parse_source_code
from backend.tools.sql_tools import execute_sql_query
from backend.tools.retrieval_tools import hybrid_search
from backend.models.analysis import BaseAnalysisFinding, BaseAnalysisResult

logger = logging.getLogger(__name__)

class PerformanceFinding(BaseAnalysisFinding):
    category: Literal["STATIC", "RUNTIME", "BUG", "VULNERABILITY"] = Field(description="Whether this is a static algorithm issue, a runtime latency/bottleneck issue, a BUG, or a VULNERABILITY.")
    estimated_complexity: str = Field(description="Estimated Big-O complexity (e.g. O(n^2), O(n)) if applicable.")
    cost_estimate: str = Field(description="Estimated cost or benefit (e.g. '30-50% latency reduction', 'High memory usage').")
    suggested_fix: Optional[str] = Field(default=None, description="The complete, corrected code snippet provided as a drop-in fix for this specific issue.")
    file_path: Optional[str] = Field(default=None, description="The file path where the issue occurs.")
    line_number: Optional[str] = Field(default=None, description="The specific line number where the issue occurs.")

class PerformanceResult(BaseAnalysisResult):
    findings: List[PerformanceFinding] = Field(description="List of structured performance bottlenecks and optimization findings.")

class PerformanceAgent(BaseAgent):
    def __init__(self):
        super().__init__("performance", output_schema=PerformanceResult)

    def execute(self, state: AgentState) -> AgentState:
        """
        Focuses strictly on algorithmic time complexity (Big O), memory leaks, and inefficient DB queries.
        Consumes the RepositoryContext and ArchitectureResult for critical path performance analysis.
        """
        session_id = state.get('shared', {}).get('session_id', 'unknown')
        logger.info(f"Performance Agent processing state for session {session_id}")
        
        # In a real LangGraph setup, repository_id and analysis_id would be in the workflow state
        repository_id = state.get("shared", {}).get("snapshot_id") or state.get("shared", {}).get("repository_id") or session_id
        analysis_id = session_id
        
        query = state.get("shared", {}).get("query")
        # 1. Fetch typed evidence payload from EvidenceService
        from backend.services.evidence_service import evidence_service
        evidence_context = evidence_service.gather_evidence("performance", repository_id, analysis_id, query=query)
        architecture_result = state.get("analysis", {}).get("architecture", {})
        
        if not evidence_context:
            logger.error("PerformanceAgent: Missing repository_context in shared state.")
            from backend.workflows.state import StateManager, TaskStatus
            state = StateManager.update_workflow_status(state, TaskStatus.FAILED)
            return state
            
        architecture_str = str(architecture_result.get("findings", "No architecture findings available."))
        
        # --- NEW: Fetch Specific SonarQube Issues & Source Code Snippets ---
        import os
        import requests
        issues_context = "No specific SonarQube issues fetched."
        try:
            sonar_host = os.environ.get("SONAR_HOST_URL")
            sonar_token = os.environ.get("SONAR_TOKEN")
            if sonar_host and sonar_token:
                # Assuming repository_id is the project key used in SonarQube
                issues_url = f"{sonar_host}/api/issues/search?componentKeys={repository_id}&statuses=OPEN,CONFIRMED,REOPENED&ps=10"
                resp = requests.get(issues_url, auth=(sonar_token, ""), timeout=10)
                if resp.status_code == 200:
                    issues = resp.json().get("issues", [])
                    if issues:
                        local_path = evidence_context.repository_metadata.get("local_path") if evidence_context.repository_metadata else None
                        issues_blocks = []
                        for i, issue in enumerate(issues):
                            file_path = issue.get("component", "").split(":")[-1]
                            line_num = issue.get("line")
                            msg = issue.get("message")
                            sev = issue.get("severity")
                            typ = issue.get("type")
                            
                            snippet = "Source code not available locally."
                            if local_path and line_num:
                                full_file_path = os.path.join(local_path, file_path)
                                if os.path.exists(full_file_path):
                                    try:
                                        with open(full_file_path, "r", encoding="utf-8") as f:
                                            lines = f.readlines()
                                            start_idx = max(0, int(line_num) - 5)
                                            end_idx = min(len(lines), int(line_num) + 5)
                                            snippet = "".join([f"{idx+1}: {lines[idx]}" for idx in range(start_idx, end_idx)])
                                    except Exception:
                                        pass
                                        
                            issues_blocks.append(
                                f"Issue {i+1}:\nType: {typ}\nSeverity: {sev}\nFile: {file_path}\nLine: {line_num}\nMessage: {msg}\n"
                                f"Source Code Snippet:\n{snippet}\n"
                            )
                        issues_context = "\n".join(issues_blocks)
        except Exception as e:
            logger.warning(f"Failed to fetch detailed SonarQube issues: {e}")
        # --------------------------------------------------------------------

        from langchain_core.prompts import ChatPromptTemplate
        
        # 2. Formulate explicit risk-aware prompt using typed evidence
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Performance and Code Quality Engineer. Review the Evidence Context, Architecture Findings, and Specific SonarQube Issues provided.\n"
                       "You must provide structured findings.\n"
                       "Crucially, you must cross-reference bottlenecks with Architecture Findings to determine the true Impact.\n"
                       "For the specific SonarQube Issues (Bugs, Vulnerabilities), you MUST write a targeted code fix in the `suggested_fix` field, and include the `file_path` and `line_number`. "
                       "Make sure your fix is a fully working code replacement for the issue."),
            ("human", "Evidence Context:\n{evidence_context}\n\nArchitecture Findings:\n{architecture_str}\n\nSpecific SonarQube Issues:\n{issues_context}")
        ])
        
        # 3. Invoke LLM strictly for structured output
        structured_llm = self.llm.with_structured_output(PerformanceResult, method="function_calling")
        result: PerformanceResult = structured_llm.invoke(prompt.format_messages(
            evidence_context=evidence_context.format_for_prompt(),
            architecture_str=architecture_str,
            issues_context=issues_context
        ))
        
        # 4. Save analysis results and persist
        from backend.workflows.state import StateManager, TaskStatus
        from backend.services.persistence_service import persistence_service
        
        # Queue for database persistence
        persistence_service.queue_agent_result(analysis_id, "PerformanceAgent", result)
        
        analysis_payload = {
            "summary": result.summary,
            "findings": [f.dict() for f in result.findings],
            "metrics": result.metrics,
            "overall_score": result.overall_score
        }
        if evidence_context.sql_results:
            analysis_payload["sql_results"] = evidence_context.sql_results.model_dump() if hasattr(evidence_context.sql_results, "model_dump") else evidence_context.sql_results.dict()
        if evidence_context.sonar_metrics:
            analysis_payload["sonar_metrics"] = evidence_context.sonar_metrics.model_dump() if hasattr(evidence_context.sonar_metrics, "model_dump") else evidence_context.sonar_metrics.dict()
        if evidence_context.retrieved_chunks:
            analysis_payload["retrieved_chunks"] = evidence_context.retrieved_chunks.model_dump() if hasattr(evidence_context.retrieved_chunks, "model_dump") else evidence_context.retrieved_chunks.dict()
            if "context" not in state["shared"] or state["shared"]["context"] is None:
                state["shared"]["context"] = []
            if isinstance(evidence_context.retrieved_chunks.data, list):
                state["shared"]["context"].extend(evidence_context.retrieved_chunks.data)
                
        state = StateManager.save_analysis(state, "performance", analysis_payload)
        state["final_response"] = result.summary
        
        if "workflow" not in state or state["workflow"] is None: state["workflow"] = {}
        state["workflow"]["current_node"] = self.name
        if "execution_path" not in state["workflow"] or state["workflow"]["execution_path"] is None:
            state["workflow"]["execution_path"] = []
        state["workflow"]["execution_path"].append(self.name)
        
        state = StateManager.update_workflow_status(state, TaskStatus.COMPLETE)
        return state
