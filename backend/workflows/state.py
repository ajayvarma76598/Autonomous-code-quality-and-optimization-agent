from enum import Enum
from typing import Annotated, Dict, Any, List, Optional, Sequence
from typing_extensions import TypedDict
import operator
from backend.models.repository import RepositoryContext

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"
    WAITING_FOR_USER = "WAITING_FOR_USER"

class WorkflowType(str, Enum):
    REPOSITORY = "repository"
    DOCUMENTATION = "documentation"
    QUALITY = "quality"
    PARALLEL_ANALYSIS = "parallel_analysis"
    SINGLE_AGENT = "single_agent"

class SharedState(TypedDict, total=False):
    query: str
    session_id: str
    repository_context: RepositoryContext
    snapshot_id: str
    repository_metadata: Dict[str, Any]
    messages: Annotated[Sequence[Any], operator.add]
    context: Annotated[List[Dict[str, Any]], operator.add]

class WorkflowState(TypedDict, total=False):
    current_node: str
    next_node: str
    workflow_type: WorkflowType
    execution_plan: Dict[str, Any]
    execution_path: Annotated[List[str], operator.add]
    status: TaskStatus
    retry_count: int
    requires_escalation: bool
    evaluation_score: float
    evaluator_feedback: str

class AnalysisResults(TypedDict, total=False):
    architecture: Dict[str, Any]
    coverage: Dict[str, Any]
    performance: Dict[str, Any]
    metrics: Dict[str, Any]
    quality: Dict[str, Any]

def merge_dicts(left: Any, right: Any) -> Any:
    if not left:
        return right or {}
    if not right:
        return left or {}
    if not isinstance(left, dict) or not isinstance(right, dict):
        return right
    res = dict(left)
    for k, v in right.items():
        if isinstance(v, dict) and isinstance(res.get(k), dict):
            res[k] = merge_dicts(res[k], v)
        else:
            res[k] = v
    return res

def pick_latest(left: Any, right: Any) -> Any:
    return right if right is not None else left

class AgentState(TypedDict, total=False):
    """
    State structured to avoid a 'God Object'.
    Each workflow reads only the sub-dictionary it needs.
    """
    shared: Annotated[SharedState, merge_dicts]
    workflow: Annotated[WorkflowState, merge_dicts]
    analysis: Annotated[AnalysisResults, merge_dicts]
    
    # Final output payload
    final_response: Annotated[Optional[str], pick_latest]
    
    # Pipeline specific execution state (can be migrated to workflow state)
    quality_context: Annotated[Dict[str, Any], merge_dicts]
    analysis_error: Annotated[Optional[str], pick_latest]
    evaluation_metrics: Annotated[Dict[str, Any], merge_dicts]

class StateManager:
    """Centralizes state mutation logic to avoid arbitrary dictionary assignments in agents."""
    
    @staticmethod
    def initialize_state(state: AgentState) -> AgentState:
        if "shared" not in state: state["shared"] = {}
        if "workflow" not in state: state["workflow"] = {}
        if "analysis" not in state: state["analysis"] = {}
        return state

    @staticmethod
    def save_analysis(state: AgentState, agent_name: str, result: Any) -> AgentState:
        state = StateManager.initialize_state(state)
        state["analysis"][agent_name] = result.dict() if hasattr(result, "dict") else result
        return state

    @staticmethod
    def append_message(state: AgentState, message: Any) -> AgentState:
        state = StateManager.initialize_state(state)
        messages = list(state["shared"].get("messages", []))
        messages.append(message)
        
        # Simple pruning: keep only the last N messages to prevent infinite growth
        if len(messages) > 10:
            messages = [messages[0]] + messages[-9:]  # keep system prompt and last 9
            
        state["shared"]["messages"] = messages
        return state
        
    @staticmethod
    def get_messages(state: AgentState) -> List[Any]:
        return list(state.get("shared", {}).get("messages", []))

    @staticmethod
    def update_workflow_status(state: AgentState, status: TaskStatus) -> AgentState:
        state = StateManager.initialize_state(state)
        state["workflow"]["status"] = status
        return state
