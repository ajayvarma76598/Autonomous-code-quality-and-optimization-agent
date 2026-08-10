import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.workflows.state import AgentState
from backend.agents.guardrail.guardrail_agent import GuardrailAgent
from backend.agents.manager.manager_agent import ManagerAgent # This acts as our Intent Router now
from backend.agents.repository.repository_agent import RepositoryAgent
from backend.agents.analysis.performance_agent import PerformanceAgent
from backend.agents.analysis.architecture_agent import ArchitectureAgent
from backend.agents.analysis.coverage_agent import TestCoverageAgent
from backend.agents.documentation.documentation_agent import DocumentationAgent
from backend.agents.evaluation.evaluation_agent import EvaluationAgent
from backend.agents.analysis.reporter_agent import ReporterAgent

# Import pipeline nodes for deterministic code quality
from backend.agents.analysis.quality_pipeline import (
    repository_parser_node,
    sonarqube_metrics_node,
    architecture_reviewer_node,
    report_generator_node
)

logger = logging.getLogger(__name__)

def human_validation_node(state: AgentState) -> AgentState:
    """
    Dummy node that gets called when escalation is required. 
    LangGraph will physically pause execution *before* this node is run because we set `interrupt_before`.
    """
    logger.info(f"Human validation completed.")
    if "workflow" not in state:
        state["workflow"] = {}
    state["workflow"]["requires_escalation"] = False
    return state

class WorkflowRouter:
    def __init__(self):
        self.guardrail_agent = GuardrailAgent()
        self.manager_agent = ManagerAgent()
        self.repository_agent = RepositoryAgent()
        self.performance_agent = PerformanceAgent()
        self.architecture_agent = ArchitectureAgent()
        self.coverage_agent = TestCoverageAgent()
        self.documentation_agent = DocumentationAgent()
        self.evaluation_agent = EvaluationAgent()
        self.reporter_agent = ReporterAgent()
        
        self.memory = MemorySaver()
        self.workflow = self._build_graph()

    def _build_graph(self):
        """
        Constructs the Supervisor pattern state machine using LangGraph.
        Includes a human_validation node that pauses execution for high-impact actions.
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("guardrail", self.guardrail_agent.execute)
        workflow.add_node("manager", self.manager_agent.execute)
        workflow.add_node("repository", self.repository_agent.execute)
        workflow.add_node("performance", self.performance_agent.execute)
        workflow.add_node("architecture", self.architecture_agent.execute)
        workflow.add_node("coverage", self.coverage_agent.execute)
        workflow.add_node("documentation", self.documentation_agent.execute)
        workflow.add_node("evaluation", self.evaluation_agent.execute)
        workflow.add_node("reporter", self.reporter_agent.execute)
        workflow.add_node("human_validation", human_validation_node)
        
        # Add new Code Quality deterministic pipeline nodes
        workflow.add_node("quality_parser", repository_parser_node)
        workflow.add_node("quality_sonarqube", sonarqube_metrics_node)
        workflow.add_node("quality_reviewer", architecture_reviewer_node)
        workflow.add_node("quality_reporter", report_generator_node)
        
        # The guardrail is the entry point
        workflow.set_entry_point("guardrail")
        
        # Guardrail routes to manager or FINISH
        workflow.add_conditional_edges(
            "guardrail",
            lambda x: x.get("workflow", {}).get("next_node"),
            {
                "manager": "manager",
                "FINISH": END
            }
        )
        
        # Conditional edges from the manager
        def manager_router(x):
            plan = x.get("workflow", {}).get("execution_plan", {})
            next_node = x.get("workflow", {}).get("next_node")
            
            # 1. Check for termination condition
            if next_node == "FINISH":
                return END
                
            workflow_type = plan.get("workflow_type")
            
            # 2. Route according to workflow registry rules
            if workflow_type == "quality":
                return "quality_parser"
                
            # For all repository-based workflows, Manager routes directly to Repository
            return "repository"
            
        workflow.add_conditional_edges(
            "manager",
            manager_router
        )
        
        def route_after_repository(x):
            plan = x.get("workflow", {}).get("execution_plan", {})
            workflow_type = plan.get("workflow_type")
            agents = plan.get("agents", [])
            
            if workflow_type == "documentation" or agents == ["documentation"]:
                return "documentation"
                
            if workflow_type == "repository" or agents == ["repository"]:
                return "evaluation"
                
            if agents:
                return agents
                
            return ["architecture", "coverage", "performance"]
            
        workflow.add_conditional_edges(
            "repository",
            route_after_repository
        )
        
        # Domain agent fan-in routing: Always route to reporter so final_response is generated
        def route_after_analysis(x):
            return "reporter"

        workflow.add_conditional_edges("performance", route_after_analysis)
        workflow.add_conditional_edges("architecture", route_after_analysis)
        workflow.add_conditional_edges("coverage", route_after_analysis)

        # Reporter, Documentation & Quality pipeline route to Evaluation Quality Gate before END
        workflow.add_edge("reporter", "evaluation")
        workflow.add_edge("documentation", "evaluation")
        workflow.add_edge("quality_reporter", "evaluation")
        
        # Evaluation Agent evaluates claims & anti-hallucination metrics
        def route_after_evaluation(x):
            eval_data = x.get("analysis", {}).get("evaluation", {})
            verdict = eval_data.get("verdict", "PASS") if isinstance(eval_data, dict) else "PASS"
            if verdict == "FAIL":
                if "workflow" not in x:
                    x["workflow"] = {}
                x["workflow"]["requires_escalation"] = True
                
                # Broadcast the escalation asynchronously via a background task so it doesn't block the graph router
                session_id = x.get("shared", {}).get("session_id", "unknown")
                query = x.get("shared", {}).get("query", "Unknown query")
                reasoning = eval_data.get("critique", "No reasoning provided.")
                
                from backend.api.routers.escalation import trigger_escalation_alert
                
                # Update the pending list synchronously and broadcast
                trigger_escalation_alert(session_id, query, reasoning, verdict)
                
                return "human_validation"
            return "FINISH"
            
        workflow.add_conditional_edges(
            "evaluation",
            route_after_evaluation,
            {
                "human_validation": "human_validation",
                "FINISH": END
            }
        )
        
        # Human validation terminates the graph (or we could route back if we wanted a retry, but we terminate to prevent loops)
        workflow.add_edge("human_validation", END)
        
        # Compile with a checkpointer and interrupt
        return workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["human_validation"]
        )

    def invoke(self, state: dict, config: dict = None) -> dict:
        """
        Executes the workflow given an initial state.
        Integrates IntentClassifier (L1-L4), Deterministic Validation, and micro-timing tracking.
        """
        import time
        t_start = time.perf_counter()
        
        user_query = state.get("shared", {}).get("query", "")
        
        # 1. Rule-Based Intent & Complexity Classification (Sub-millisecond)
        from backend.workflows.intent_classifier import intent_classifier, ComplexityLevel
        t_ic_start = time.perf_counter()
        level, target_agent, workers = intent_classifier.classify(user_query)
        ic_ms = round((time.perf_counter() - t_ic_start) * 1000, 2)
        
        if "workflow" not in state:
            state["workflow"] = {}
        state["workflow"]["complexity_level"] = level.value
        state["workflow"]["execution_plan"] = {"workflow_type": "single_agent" if level in (ComplexityLevel.L1_RETRIEVAL, ComplexityLevel.L2_SINGLE_AGENT) else "multi_agent", "agents": workers}
        
        logger.info(f"[WorkflowRouter] Invoking query (Level: {level.value} | Intent MS: {ic_ms}ms | Workers: {workers})")
        
        invoke_config = config or {}
        if "configurable" not in invoke_config:
            invoke_config["configurable"] = {}
        invoke_config["configurable"]["thread_id"] = state.get("shared", {}).get("session_id", "default_thread")
        
        try:
            prev_state_wrapper = self.workflow.get_state(invoke_config)
            prev_state = prev_state_wrapper.values if prev_state_wrapper else {}
            prev_msg_count = len(prev_state.get("shared", {}).get("messages", []))
            prev_ctx_count = len(prev_state.get("shared", {}).get("context", []))
        except Exception:
            prev_msg_count = 0
            prev_ctx_count = 0
        
        from backend.services.observability.langfuse import langfuse_service
        
        t_exec_start = time.perf_counter()
        logger.info("--- AGENT EXECUTION LOG ---")
        for event in self.workflow.stream(state, config=invoke_config):
            for agent_name, agent_state in event.items():
                logger.info(f"[Agent Transition] -> {agent_name} executed.")
                if "messages" in agent_state and agent_state["messages"]:
                    messages_to_log = agent_state["messages"] if isinstance(agent_state["messages"], list) else [agent_state["messages"]]
                    for msg in messages_to_log:
                        msg_type = getattr(msg, "type", "")
                        if msg_type == "tool":
                            tool_name = getattr(msg, "name", "unknown_tool")
                            logger.info(f"[Tool Output - {tool_name}]:\n{str(msg.content)}")
                        elif getattr(msg, "tool_calls", []):
                            tools_called = ", ".join([tc.get("name", "unknown") for tc in getattr(msg, "tool_calls", [])])
                            logger.info(f"[{agent_name} Called Tools] -> {tools_called}")
                            if msg.content:
                                logger.info(f"[{agent_name} Reasoning]:\n{str(msg.content)}")
                        else:
                            content = getattr(msg, "content", "")
                            if content:
                                logger.info(f"[{agent_name} Output]:\n{str(content)}")
                                
                    last_msg = messages_to_log[-1] if messages_to_log else None
                    if last_msg:
                        session_id = state.get("shared", {}).get("session_id", "unknown")
                    if langfuse_service.langfuse:
                        try:
                            from backend.agents.base_agent import get_agent_full_name
                            full_agent_name = get_agent_full_name(agent_name)
                            langfuse_service.langfuse.event(
                                trace_id=session_id,
                                name=f"Agent Execution: {full_agent_name}",
                                output={"message": str(last_msg.content)[:300]}
                            )
                        except Exception:
                            pass
                            
        logger.info("--- END AGENT EXECUTION LOG ---")
        agent_ms = round((time.perf_counter() - t_exec_start) * 1000, 2)
        
        final_state = self.workflow.get_state(invoke_config).values
        
        # 2. Deterministic Citation & Confidence Validation
        t_eval_start = time.perf_counter()
        from backend.agents.evaluation.validator import deterministic_validator
        final_resp = final_state.get("final_response") or ""
        shared_ctx = final_state.get("shared", {}).get("context", [])
        
        from backend.api.routers.query import extract_citations
        citations = extract_citations(final_state)
        
        det_eval = deterministic_validator.validate_output(final_resp, citations, shared_ctx)
        eval_ms = round((time.perf_counter() - t_eval_start) * 1000, 2)
        
        # Store metrics in state
        if "evaluation" not in final_state.get("analysis", {}):
            if "analysis" not in final_state:
                final_state["analysis"] = {}
            final_state["analysis"]["evaluation"] = det_eval

        total_ms = round((time.perf_counter() - t_start) * 1000, 2)
        
        final_state["stage_timings"] = {
            "intent_classification_ms": ic_ms,
            "agent_execution_ms": agent_ms,
            "evaluation_ms": eval_ms,
            "total_latency_ms": total_ms
        }
        
        if "workflow" not in final_state:
            final_state["workflow"] = {}
        final_state["workflow"]["current_execution_start_indices"] = {
            "messages": prev_msg_count,
            "context": prev_ctx_count
        }
        
        # Phase 16: Asynchronously persist the entire AnalysisRun
        from backend.services.persistence_service import persistence_service
        session_id = state.get("shared", {}).get("session_id", "unknown")
        final_status = final_state.get("workflow", {}).get("status", "COMPLETED")
        
        try:
            persistence_service.flush_transaction(analysis_id=session_id, repository_id=session_id, final_status=final_status)
        except Exception as e:
            logger.error(f"Failed to flush database transaction: {e}")
        
        return final_state

workflow_router = WorkflowRouter()
