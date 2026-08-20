import logging
import time
from typing import Any

from langchain_core.messages import ToolMessage

from backend.workflows.state import AgentState, StateManager

logger = logging.getLogger(__name__)


# Typed Exceptions
class AgentExecutionError(Exception):
    pass


class ToolExecutionError(AgentExecutionError):
    pass


class LLMInvocationError(AgentExecutionError):
    pass


class PromptResolutionError(AgentExecutionError):
    pass


class ToolExecutor:
    """Handles deterministic execution of tools and metrics recording."""

    @staticmethod
    def execute(
        llm_with_tools,
        tools: list,
        messages: list,
        state: AgentState,
        max_iterations: int = 5,
        plain_llm=None,
    ) -> Any:
        """
        Executes the LLM in a loop until it returns a final text response (no tool calls) or max_iterations is reached.
        """
        start_time = time.time()

        # O(1) tool lookup
        tool_map = {tool.name: tool for tool in tools}

        try:
            from backend.agents.base_agent import get_agent_full_name

            node_name = state.get("workflow", {}).get("current_node") or "Agent"
            agent_name = get_agent_full_name(node_name)

            # Attach full agent name run_name to llm_with_tools for Langfuse trace visibility
            llm_with_tools = llm_with_tools.with_config({"run_name": agent_name})

            iteration = 0
            result_msg = None

            while iteration < max_iterations:
                iteration += 1
                logger.info(
                    f"[LLM REQUEST] [{agent_name}] (Iteration {iteration}) -> Messages count: {len(messages)}"
                )

                llm_start = time.time()
                result_msg = llm_with_tools.invoke(messages)
                llm_duration = time.time() - llm_start
                tool_calls = getattr(result_msg, "tool_calls", []) or []
                logger.info(
                    f"[LLM RESPONSE] [{agent_name}] -> Took {llm_duration:.2f}s | Tool calls count: {len(tool_calls)}"
                )

                messages.append(result_msg)

                if not tool_calls:
                    # No tool calls; LLM provided text output or completed.
                    break

                # Tool execution step
                tool_start = time.time()
                for tool_call in tool_calls:
                    t_name = tool_call["name"]
                    t_args = tool_call.get("args", {})
                    logger.info(
                        f"   [TOOL REQUEST] [{agent_name} -> Tool: {t_name}] | Arguments: {t_args}"
                    )

                    tool = tool_map.get(t_name)
                    if tool:
                        try:
                            tool_result = tool.invoke(t_args)
                        except Exception as e:
                            logger.error(f"   [TOOL ERROR] [{t_name}] failed: {e}")
                            tool_result = f"Tool execution failed: {str(e)}"
                    else:
                        tool_result = f"Unknown tool: {t_name}"

                    res_str = str(tool_result)
                    logger.info(
                        f"   [TOOL RESPONSE] [{t_name}] -> Output Length: {len(res_str)} chars | Snippet: {res_str[:120]}..."
                    )
                    messages.append(
                        ToolMessage(content=res_str, tool_call_id=tool_call["id"])
                    )

                tool_duration = time.time() - tool_start
                logger.info(
                    f"[TOOL LAYER COMPLETED] [{agent_name}] (Iteration {iteration}) -> Took {tool_duration:.2f}s"
                )

            # If the final result content is empty after tool loop, perform synthesis call without tool binding
            content = getattr(result_msg, "content", "")
            if not content or not str(content).strip():
                logger.info(
                    f"[LLM SYNTHESIS FORCED] [{agent_name}] -> Synthesizing tool outputs into final response text..."
                )
                target_llm = plain_llm if plain_llm else llm_with_tools
                synthesis_start = time.time()
                result_msg = target_llm.invoke(messages)
                synthesis_duration = time.time() - synthesis_start
                logger.info(
                    f"[LLM SYNTHESIS COMPLETED] [{agent_name}] -> Took {synthesis_duration:.2f}s | Final Content Length: {len(str(getattr(result_msg, 'content', '')))}"
                )
                messages.append(result_msg)

            total_duration = time.time() - start_time
            logger.info(
                f"[EXECUTOR FINISHED] [{agent_name}] -> Total agent execution took {total_duration:.2f}s"
            )

            # Update state with new messages using StateManager
            for msg in messages:
                if msg not in StateManager.get_messages(state):
                    state = StateManager.append_message(state, msg)

            return result_msg

        except Exception as e:
            raise LLMInvocationError(f"LLM invocation failed: {e}")
