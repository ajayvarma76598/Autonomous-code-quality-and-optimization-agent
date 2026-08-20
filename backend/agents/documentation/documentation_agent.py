import logging

from backend.agents.base_agent import BaseAgent
from backend.tools.documentation_tools import generate_readme
from backend.tools.retrieval_tools import hybrid_search
from backend.workflows.state import AgentState

logger = logging.getLogger(__name__)


class DocumentationAgent(BaseAgent):
    def __init__(self):
        super().__init__("documentation")
        # Bind the MCP-compatible tools to the LLM
        self.agent_llm = self.llm.bind_tools([generate_readme, hybrid_search])

    def execute(self, state: AgentState) -> AgentState:
        """
        Handles requests to generate or explain code documentation.
        """
        logger.info(
            f"Documentation Agent processing state for session {state.get('shared', {}).get('session_id', 'unknown')}"
        )
        state = self.execute_with_tools(state, [generate_readme, hybrid_search])

        final_resp = state.get("final_response") or ""
        if final_resp:
            from backend.workflows.state import StateManager

            state = StateManager.save_analysis(
                state, "documentation", {"summary": final_resp, "report": final_resp}
            )
        return state
