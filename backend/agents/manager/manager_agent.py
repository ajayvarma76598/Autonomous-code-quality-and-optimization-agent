import logging

from backend.agents.base_agent import BaseAgent
from backend.workflows.state import AgentState

logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("manager")

    def execute(self, state: AgentState) -> AgentState:
        """
        The Supervisor agent evaluates the state and decides the next agent to route to.
        """
        logger.info(
            f"Manager evaluating state for session {state.get('shared', {}).get('session_id', 'unknown')}"
        )

        query = state.get("shared", {}).get("query", "")

        # If we have enough context or a final answer has been set by another agent, finish.
        if state.get("workflow", {}).get("status") == "COMPLETE":
            if "workflow" not in state:
                state["workflow"] = {}
            state["workflow"]["next_node"] = "FINISH"
            return state

        try:
            from typing import Literal

            from langchain_core.prompts import ChatPromptTemplate
            from pydantic import BaseModel, Field

            from backend.services.llm import llm_service
            from backend.workflows.state import WorkflowType

            class ExecutionPlan(BaseModel):
                workflow_type: WorkflowType = Field(
                    description="The core workflow to execute."
                )
                agents: list[str] = Field(
                    description="List of specific agents that will be executed."
                )
                parallel: bool = Field(
                    default=False,
                    description="True if the agents can be executed in parallel.",
                )
                dependencies: list[str] = Field(
                    default_factory=list,
                    description="Any strict dependencies required before execution.",
                )
                status: Literal["PLANNED"] = Field(default="PLANNED")

            llm = llm_service.get_llm(temperature=0.0, model_type="fast")
            structured_llm = llm.with_structured_output(
                ExecutionPlan, method="function_calling"
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an expert routing supervisor. Classify the user query into the appropriate workflow_type and set the exact list of target agents.\n\n"
                        "Classification Rules:\n"
                        "- 'documentation': Select this if the query asks for inline documentation, docstrings, explaining code/functions, or documenting schemas/codebase. Set agents=['documentation'].\n"
                        "- 'repository': Select this for general repository questions, finding files, or codebase overview. Set agents=['repository'].\n"
                        "- 'quality': Select this for code quality metrics, code smells, SonarQube refactoring. Set agents=['quality'].\n"
                        "- 'parallel_analysis': Select this ONLY if the user explicitly requests a full comprehensive multi-perspective audit (analyzing architecture, coverage, AND performance together). Set agents=['architecture', 'coverage', 'performance'].\n"
                        "- 'single_agent': Select this if only ONE specialist agent is requested, e.g., agents=['architecture'], agents=['coverage'], or agents=['performance'].\n\n"
                        "Strict Requirement: If the user asks for documentation, docstrings, or code explanations, you MUST select workflow_type='documentation' with agents=['documentation']. DO NOT select parallel_analysis for documentation requests.",
                    ),
                    ("human", "{query}"),
                ]
            )

            chain = prompt | structured_llm
            result = chain.invoke({"query": query})

            if "workflow" not in state:
                state["workflow"] = {}
            # Manager no longer routes by string, but rather drops a plan
            plan_dict = result.dict()
            plan_dict["workflow_type"] = (
                result.workflow_type.value
                if hasattr(result.workflow_type, "value")
                else str(result.workflow_type)
            )
            state["workflow"]["execution_plan"] = plan_dict
            state["workflow"]["workflow_type"] = result.workflow_type
            state["workflow"]["next_node"] = (
                result.workflow_type.value
                if hasattr(result.workflow_type, "value")
                else str(result.workflow_type)
            )
        except Exception as e:
            logger.error(f"LLM routing failed, falling back to repository: {e}")
            if "workflow" not in state:
                state["workflow"] = {}
            # Fallback plan
            state["workflow"]["execution_plan"] = {
                "workflow_type": "repository",
                "agents": ["repository"],
                "parallel": False,
                "dependencies": [],
                "status": "PLANNED",
            }
            state["workflow"]["workflow_type"] = "repository"
            state["workflow"]["next_node"] = "repository"

        logger.info(
            f"Manager created execution plan: {state.get('workflow', {}).get('execution_plan')}"
        )

        # Add a trace to Langfuse
        from backend.services.observability.langfuse import langfuse_service

        langfuse_service.trace_execution(
            name="manager_routing",
            session_id=state.get("shared", {}).get("session_id", "unknown"),
            metadata={
                "query": query,
                "routed_to": state.get("workflow", {}).get("next_node"),
            },
        )

        return state
