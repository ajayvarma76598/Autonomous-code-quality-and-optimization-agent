import logging

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base_agent import BaseAgent
from backend.workflows.state import AgentState

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    def __init__(self):
        super().__init__("reporter")
        # No tools needed, just synthesis

    def execute(self, state: AgentState) -> AgentState:
        """
        Synthesizes the structured Pydantic results from the parallel analysis agents
        into a cohesive narrative report.
        """
        logger.info(
            f"Reporter Agent processing state for session {state.get('shared', {}).get('session_id', 'unknown')}"
        )

        analysis = state.get("analysis", {})
        if not analysis:
            state["final_response"] = "No analysis results to report."
            return state

        import json

        context_str = json.dumps(analysis, indent=2)
        query = state.get("shared", {}).get("query", "Summarize the findings.")

        prompt = f"User Query: {query}\n\nStructured Evidence:\n{context_str}\n\nGenerate a polished, cohesive narrative report summarizing these findings. Do not hallucinate outside the structured evidence."

        system_prompt = (
            "You are a Senior Principal Engineer and Technical Writer.\n"
            "RESPONSE & TECHNICAL CLARITY CONSTRAINTS:\n"
            "1. Answer the user's specific query directly and cleanly without introductory filler or preambles (e.g. 'Based on the analysis...').\n"
            "2. TECHNICAL CLARITY & ADEQUATE DEPTH: Provide full technical clarity, thorough explanations, and code snippets needed to explain performance bottlenecks, architectural patterns, or documentation details clearly. Do not artificially truncate important technical details.\n"
            "3. ZERO UNRELATED ADD-UPS: Keep the output 100% focused on answering the query. Do NOT add generic boilerplate, unsolicited disclaimers, or next steps unless explicitly requested in the query.\n"
            "4. STRICT TRUTHFULNESS & GROUNDING: You must be absolutely true to the data provided to you. Answer ONLY using the supplied structured evidence. Do not hallucinate, guess, or use external knowledge.\n"
            "5. NO INVENTED DATA: If the provided evidence does not contain the answer, you must state 'I cannot answer this based on the provided data.' Cite exact file paths when referencing code."
        )

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]

        try:
            response = self.llm.invoke(messages)
            state["final_response"] = response.content

            # Queue report for persistence (Phase 16C)
            from backend.services.persistence_service import persistence_service

            analysis_id = state.get("shared", {}).get("session_id", "unknown")
            persistence_service.queue_report(
                analysis_id, {"type": "markdown", "content": response.content}
            )

        except Exception as e:
            logger.error(f"Reporter agent failed: {e}")
            state["final_response"] = f"Failed to generate report: {e}"

        return state
