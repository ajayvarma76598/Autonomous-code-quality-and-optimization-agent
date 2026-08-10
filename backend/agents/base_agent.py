import logging
from backend.workflows.state import AgentState
from backend.services.observability.langfuse import langfuse_service
from backend.services.llm import llm_service
from backend.workflows.state import StateManager
from backend.agents.executor import ToolExecutor, LLMInvocationError
from langchain_core.messages import HumanMessage, SystemMessage
from backend.prompts.registry import get_fallback_prompt

logger = logging.getLogger(__name__)

AGENT_FULL_NAMES = {
    "guardrail": "GuardrailAgent",
    "manager": "ManagerAgent",
    "repository": "RepositoryAgent",
    "architecture": "ArchitectureAgent",
    "coverage": "TestCoverageAgent",
    "performance": "PerformanceAgent",
    "documentation": "DocumentationAgent",
    "evaluation": "EvaluationAgent",
    "reporter": "ReporterAgent",
    "quality_parser": "QualityParserNode",
    "quality_sonarqube": "QualitySonarQubeNode",
    "quality_reviewer": "QualityReviewerNode",
    "quality_reporter": "QualityReporterNode",
}

def get_agent_full_name(name: str) -> str:
    if not name: return "Agent"
    return AGENT_FULL_NAMES.get(name.lower(), f"{name.capitalize()}Agent")

class BaseAgent:
    def __init__(self, name: str, model_type: str = "fast", output_schema=None):
        self.name = name
        self.full_name = get_agent_full_name(name)
        self.llm = llm_service.get_llm(temperature=0.0, model_type=model_type)
        self.output_schema = output_schema
        
    def get_system_prompt(self) -> str:
        """
        Fetches the system prompt for this agent from Langfuse Prompt Registry.
        Falls back to the local hardcoded registry if Langfuse is unavailable.
        """
        prompt = langfuse_service.get_prompt(f"{self.name}_prompt")
        if prompt:
            return prompt.get_langchain_prompt()
            
        logger.warning(f"Failed to fetch {self.name}_prompt from Langfuse. Using local fallback.")
        return get_fallback_prompt(f"{self.name}_prompt")

    def execute(self, state: AgentState) -> AgentState:
        raise NotImplementedError("Subclasses must implement execute")
        
    def execute_with_tools(self, state: AgentState, tools: list) -> AgentState:
        """
        Executes the agent using the extracted ToolExecutor and state management.
        """
        base_prompt = self.get_system_prompt()
        llm_with_tools = self.llm.bind_tools(tools).with_config({"run_name": self.full_name})
        
        state = StateManager.initialize_state(state)
        messages = StateManager.get_messages(state)
        
        # Ensure system prompt is present
        if not messages or getattr(messages[0], "type", "") != "system":
            messages.insert(0, SystemMessage(content=base_prompt))
            
        if state["shared"].get("query") and not any(getattr(m, "content", "") == state["shared"]["query"] for m in messages):
            messages.append(HumanMessage(content=state["shared"]["query"]))
            
        session_id = state.get("shared", {}).get("session_id", "unknown")
        user_query = state.get("shared", {}).get("query", "N/A")
        logger.info(f"[AGENT REQUEST] [{self.full_name}] -> Query: '{user_query}' | Session: {session_id}")
        
        langfuse_service.create_span(
            trace_id=session_id,
            name=f"Agent: {self.full_name}",
            input_data=user_query,
            metadata={"agent": self.full_name, "short_name": self.name}
        )
        
        try:
            # Delegate tool execution and metrics to ToolExecutor
            result_msg = ToolExecutor.execute(llm_with_tools, tools, messages, state, plain_llm=self.llm)
            result_msg.name = self.name
            
            if "workflow" not in state: state["workflow"] = {}
            state["workflow"]["current_node"] = self.name
            if "execution_path" not in state["workflow"] or state["workflow"]["execution_path"] is None:
                state["workflow"]["execution_path"] = []
            state["workflow"]["execution_path"].append(self.name)
            
            # Final synthesis step if schema is provided
            if self.output_schema:
                structured_llm = self.llm.with_structured_output(self.output_schema, method="function_calling")
                final_result = structured_llm.invoke(messages)
                state = StateManager.save_analysis(state, self.name, final_result)
                resp_content = str(final_result.dict() if hasattr(final_result, "dict") else final_result)
            else:
                resp_content = getattr(result_msg, "content", "")
                if not resp_content or not str(resp_content).strip():
                    from langchain_core.messages import AIMessage
                    for m in reversed(messages):
                        if (isinstance(m, AIMessage) or getattr(m, "type", "") == "ai") and getattr(m, "content", None) and str(m.content).strip():
                            resp_content = str(m.content)
                            break
                state["final_response"] = resp_content
                
            logger.info(f"[AGENT RESPONSE] [{self.name}] -> Output Length: {len(str(resp_content))} chars | Snippet: {str(resp_content)[:120]}...")
                
        except LLMInvocationError as e:
            logger.warning(f"Agent {self.name} hit an invocation error: {e}")
            state["final_response"] = f"Agent failed: {str(e)}"
        except Exception as e:
            logger.warning(f"Agent {self.name} hit an unexpected error: {e}")
            state["final_response"] = f"Agent failed unexpectedly: {str(e)}"
            
        return state
