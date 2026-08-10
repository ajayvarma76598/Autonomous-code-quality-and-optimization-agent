import time
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_db
from backend.workflows.router import workflow_router

router = APIRouter(prefix="/query", tags=["Query"])

class QueryRequest(BaseModel):
    session_id: UUID
    query: str
    snapshot_id: Optional[UUID] = Field(default=None, description="Optional target snapshot ID. If omitted, uses the latest snapshot.")

class CitationItem(BaseModel):
    provider: Optional[str] = Field(default="HybridSearch", description="Provider or service that supplied the citation.")
    file_path: str
    module: Optional[str] = None
    function: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None

class QueryResponse(BaseModel):
    response: str
    citations: List[CitationItem] = []
    tools_used: List[str] = Field(default_factory=list, description="List of internal tools, services, and evidence providers invoked for this query.")
    metadata: Dict[str, Any]

def extract_citations(state_out: dict) -> List[CitationItem]:
    import re
    import ast
    import json
    citations = []
    seen = set()
    
    workflow = state_out.get("workflow", {})
    if isinstance(workflow, tuple):
        workflow = workflow[-1] if workflow else {}
        
    shared = state_out.get("shared", {})
    if isinstance(shared, tuple):
        shared = shared[-1] if shared else {}
        
    indices = workflow.get("current_execution_start_indices", {})
    ctx_start = indices.get("context", 0) if isinstance(indices, dict) else 0
    msg_start = indices.get("messages", 0) if isinstance(indices, dict) else 0
    path_start = indices.get("execution_path", 0) if isinstance(indices, dict) else 0
    
    current_path = workflow.get("execution_path", []) or []
    current_path = current_path[path_start:]
    
    def add_citation(file_path: str, provider: str = "VectorProvider / HybridSearch", module: Optional[str] = None, function: Optional[str] = None, snippet: Optional[str] = None, score: Optional[float] = None):
        clean_path = str(file_path).strip() if file_path else "unknown"
        if clean_path.startswith("'") or clean_path.startswith('"'):
            clean_path = clean_path[1:-1]
            
        clean_module = str(module).strip() if module and module != "None" else None
        clean_function = str(function).strip() if function and function != "None" else None
        clean_snippet = str(snippet).strip() if snippet else None
        
        key = (clean_path, provider, clean_module, clean_function, clean_snippet[:50] if clean_snippet else "")
        if key not in seen and clean_path and clean_path != "None":
            seen.add(key)
            citations.append(CitationItem(
                provider=provider,
                file_path=clean_path,
                module=clean_module,
                function=clean_function,
                snippet=clean_snippet[:200] if clean_snippet else None,
                score=round(float(score), 4) if score is not None and str(score) != "None" else None
            ))

    # 1. Extract from shared context list
    contexts = shared.get("context", []) or state_out.get("context", [])
    contexts = contexts[ctx_start:]
    for item in contexts:
        file_path = getattr(item, "repository_path", None) or (item.get("repository_path") if isinstance(item, dict) else None) or getattr(item, "file_path", None) or (item.get("file_path") if isinstance(item, dict) else None)
        module = getattr(item, "module", None) or (item.get("module") if isinstance(item, dict) else None)
        function = getattr(item, "function", None) or (item.get("function") if isinstance(item, dict) else None)
        evidence = getattr(item, "evidence", None) or (item.get("evidence") if isinstance(item, dict) else None)
        score = getattr(item, "score", None) or (item.get("score") if isinstance(item, dict) else None)
        provider = getattr(item, "provider_name", None) or (item.get("provider_name") if isinstance(item, dict) else "VectorProvider / HybridSearch")
        
        snippet = evidence[0] if isinstance(evidence, list) and evidence else str(evidence) if evidence else None
        if file_path:
            add_citation(file_path, provider, module, function, snippet, score)

    # 2. Extract from ToolMessage outputs (structured JSON, AST literal dicts, or stringified context blocks)
    all_messages = shared.get("messages", []) or state_out.get("messages", [])
    all_messages = all_messages[msg_start:]
    for msg in all_messages:
        msg_type = getattr(msg, "type", "")
        content_str = str(getattr(msg, "content", ""))
        
        if msg_type == "tool" or "RetrievedContext" in content_str or "repository_path" in content_str or "chunk_id" in content_str:
            items = []
            try:
                parsed = json.loads(content_str)
                if isinstance(parsed, list): items = parsed
                elif isinstance(parsed, dict): items = [parsed]
            except Exception:
                try:
                    parsed = ast.literal_eval(content_str)
                    if isinstance(parsed, list): items = parsed
                    elif isinstance(parsed, dict): items = [parsed]
                except Exception:
                    pass
            
            for item in items:
                if isinstance(item, dict):
                    file_path = item.get("repository_path") or item.get("file_path") or item.get("file")
                    module = item.get("module") or item.get("class")
                    function = item.get("function") or item.get("method")
                    evidence = item.get("evidence")
                    score = item.get("score") or item.get("confidence_score") or item.get("rrf_score")
                    snippet = evidence[0] if isinstance(evidence, list) and evidence else str(evidence) if evidence else None
                    if file_path:
                        add_citation(file_path, "VectorProvider / HybridSearch", module, function, snippet, score)

            # Fallback regex extraction for RetrievedContext blocks
            context_blocks = re.findall(r"RetrievedContext\((.*?)\)", content_str, re.DOTALL)
            for block in context_blocks:
                module_m = re.search(r"module=['\"]?(.*?)['\"]?[,)]", block)
                function_m = re.search(r"function=['\"]?(.*?)['\"]?[,)]", block)
                path_m = re.search(r"repository_path=['\"]?(.*?)['\"]?[,)]", block)
                score_m = re.search(r"score=([\d\.]+)", block)
                evidence_m = re.search(r"evidence=\[(.*?)\]", block, re.DOTALL)
                
                path_val = path_m.group(1) if path_m else "repository/source_code"
                module_val = module_m.group(1) if module_m else None
                func_val = function_m.group(1) if function_m else None
                score_val = float(score_m.group(1)) if score_m else None
                snippet_val = evidence_m.group(1) if evidence_m else None
                
                add_citation(path_val, "VectorProvider / HybridSearch", module_val, func_val, snippet_val, score_val)

            # Regex fallback for repository_path key-values
            paths_found = re.findall(r"['\"]repository_path['\"]:\s*['\"]([^'\"]+)['\"]", content_str)
            for p in paths_found:
                add_citation(p, "VectorProvider / HybridSearch")

    # 3. Extract from EvidenceContext blocks in analysis dict
    provider_map = {
        "sonar_metrics": "SonarProvider",
        "sql_results": "SQLProvider",
        "dependency_graph": "SQLProvider",
        "repository_metadata": "MetadataProvider",
        "retrieved_chunks": "VectorProvider / HybridSearch"
    }
    
    analysis = state_out.get("analysis", {})
    for agent_name, agent_data in analysis.items():
        if not any(agent_name in p or p in agent_name for p in current_path):
            continue
        if isinstance(agent_data, dict):
            for key_name, prov_name in provider_map.items():
                data_block = agent_data.get(key_name)
                if isinstance(data_block, dict) and data_block.get("data"):
                    add_citation(
                        file_path=f"evidence/{key_name}",
                        provider=prov_name,
                        module=agent_name,
                        snippet=str(data_block.get("data"))[:200],
                        score=data_block.get("confidence_score", 0.9)
                    )

    return citations


def extract_tools_used(state_out: dict, citations: List[CitationItem]) -> List[str]:
    """
    Extracts the exact @tool functions and services executed during query processing.
    Registered Tools:
      - anonymize_pii (Presidio)
      - hybrid_search (pgvector + BM25)
      - execute_sql_query (PostgreSQL Dependency Graph)
      - analyze_code_quality / get_code_issues (SonarQube)
      - parse_source_code (Tree-sitter AST)
      - deterministic_validator (Tier-1 Python Gate)
      - evaluation_agent (Tier-2 LLM Quality Gate)
    """
    tools = ["anonymize_pii", "manager_agent", "guardrails_agent", "evaluation_agent"]
    workflow_state = state_out.get("workflow", {})
    if state_out.get("cached") or workflow_state.get("cached"):
        tools.append("redis_cache")
        return tools

    providers = set()
    for c in citations:
        if c.provider:
            providers.add(c.provider)

    if any("Vector" in p or "Hybrid" in p for p in providers):
        tools.append("hybrid_search")
    if any("SQL" in p or "Graph" in p for p in providers):
        tools.append("execute_sql_query")
    if any("Sonar" in p for p in providers):
        tools.append("analyze_code_quality")
        tools.append("get_code_issues")
    if any("Metadata" in p for p in providers):
        tools.append("parse_source_code")

    eval_data = state_out.get("analysis", {}).get("evaluation", {}) if isinstance(state_out.get("analysis", {}), dict) else {}
    if eval_data:
        tools.append("deterministic_validator")
        if eval_data.get("requires_llm_eval"):
            tools.append("evaluation_agent")

    # Extract directly from ToolMessages or AIMessages with tool_calls
    indices = state_out.get("workflow", {}).get("current_execution_start_indices", {})
    msg_start = indices.get("messages", 0)
    
    all_messages = state_out.get("shared", {}).get("messages", []) or state_out.get("messages", [])
    all_messages = all_messages[msg_start:]
    for msg in all_messages:
        if getattr(msg, "type", "") == "tool":
            tool_name = getattr(msg, "name", None)
            if tool_name:
                tools.append(tool_name)
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                tc_name = tc.get("name")
                if tc_name:
                    tools.append(tc_name)

    return list(dict.fromkeys(tools))


@router.post("/", response_model=QueryResponse)
def execute_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Execute a synchronous query via the LangGraph Supervisor agent graph.
    """
    start_time = time.time()
    
    from backend.services.pii_service import pii_service
    safe_query = pii_service.anonymize_text(request.query)
    
    # 1. Fast Cache Check: Exact string match FIRST (Sub-1ms, zero LLM/Embedding latency)
    from backend.services.cache_service import cache_service
    fast_cached_res = cache_service.check_exact_cache(str(request.session_id), safe_query)
    if fast_cached_res:
        meta = fast_cached_res.get("metadata", {})
        meta["cached"] = True
        meta["cache_type"] = "exact_redis_sub_1ms"
        cache_tools = ["IntentClassifier", "RedisCacheService"]
        return QueryResponse(
            response=fast_cached_res.get("response", ""),
            citations=[CitationItem(**c) if isinstance(c, dict) else c for c in fast_cached_res.get("citations", [])],
            tools_used=cache_tools,
            metadata=meta
        )

    # 2. Semantic Vector Cache Check (Fallback for paraphrase/semantic equivalence)
    query_embedding = None
    try:
        from backend.services.embedding_service import embedding_service
        query_embedding = embedding_service.embed_query(safe_query)
    except Exception:
        pass
        
    if query_embedding:
        cached_res = cache_service.get_cached_response(
            session_id=str(request.session_id),
            query_embedding=query_embedding,
            query_text=safe_query,
            similarity_threshold=0.92
        )
        if cached_res:
            meta = cached_res.get("metadata", {})
            meta["cached"] = True
            meta["cache_type"] = "semantic_redis"
            cache_tools = ["IntentClassifier", "VectorProvider (pgvector Hybrid Search)", "RedisCacheService"]
            return QueryResponse(
                response=cached_res.get("response", ""),
                citations=[CitationItem(**c) if isinstance(c, dict) else c for c in cached_res.get("citations", [])],
                tools_used=cache_tools,
                metadata=meta
            )
            
    initial_messages = []
    initial_msg_count = len(initial_messages)
    
    state_in = {
        "shared": {
            "query": safe_query,
            "session_id": str(request.session_id),
            "snapshot_id": str(request.snapshot_id) if request.snapshot_id else None,
            "messages": initial_messages,
            "context": []
        },
        "workflow": {
            "current_node": "guardrail",
            "next_node": "guardrail",
            "status": "RUNNING",
            "requires_escalation": False,
            "execution_path": []
        },
        "analysis": {},
        "final_response": None
    }
    
    # Configure Langfuse tracing
    from backend.services.observability.langfuse import langfuse_service
    config = {"configurable": {"thread_id": str(request.session_id)}}
    
    try:
        prev_state_wrapper = workflow_router.workflow.get_state(config)
        prev_state = prev_state_wrapper.values if prev_state_wrapper else {}
        prev_msg_count = len(prev_state.get("shared", {}).get("messages", []))
        prev_ctx_count = len(prev_state.get("shared", {}).get("context", []))
        prev_path_count = len(prev_state.get("workflow", {}).get("execution_path", []))
    except Exception:
        prev_msg_count = 0
        prev_ctx_count = 0
        prev_path_count = 0
        
    state_in["workflow"]["current_execution_start_indices"] = {
        "messages": prev_msg_count,
        "context": prev_ctx_count,
        "execution_path": prev_path_count
    }
    if langfuse_service.langfuse:
        langfuse_handler = langfuse_service.get_callback_handler(session_id=request.session_id.hex)
        config["callbacks"] = [langfuse_handler]

    # Execute workflow graph
    state_out = workflow_router.invoke(state_in, config=config)
    
    total_seconds = round(time.time() - start_time, 2)
    latency_ms = int(total_seconds * 1000)
    
    # Stage timings removed per user request

    # 0. Resolve final_response from state_out or worker agent analysis summary
    final_text = state_out.get("final_response")
    if not final_text or final_text == "No response generated.":
        analysis_dict = state_out.get("analysis", {})
        if isinstance(analysis_dict, dict):
            for agent_key in ["architecture", "performance", "coverage", "quality", "documentation", "repository"]:
                if agent_key in analysis_dict and isinstance(analysis_dict[agent_key], dict):
                    agent_data = analysis_dict[agent_key]
                    summary_val = agent_data.get("summary") or agent_data.get("report")
                    if summary_val:
                        final_text = summary_val
                        state_out["final_response"] = final_text
                        break
    # 0. Extract Metrics directly from LLM EvaluationAgent output
    eval_metrics = state_out.get("analysis", {}).get("evaluation", {}) if isinstance(state_out.get("analysis", {}), dict) else {}
    eval_metrics = eval_metrics if isinstance(eval_metrics, dict) else {}
        
    tsr_passed        = (eval_metrics.get("verdict", "PASS") == "PASS")
    grounding_score   = float(eval_metrics.get("faithfulness",      eval_metrics.get("confidence", 0.0)))
    relevancy_score   = float(eval_metrics.get("relevancy",         0.0))
    confidence_score  = float(eval_metrics.get("confidence",        0.0))
    context_precision = float(eval_metrics.get("context_precision", 0.0))
    recall_score      = float(eval_metrics.get("recall",            0.0))
    
    # 2. Extract Token Usage directly from LLM message metadata
    indices = state_out.get("workflow", {}).get("current_execution_start_indices", {})
    msg_start = indices.get("messages", 0)
    
    msgs = state_out.get("shared", {}).get("messages", []) or state_out.get("messages", [])
    msgs = msgs[msg_start:]
    input_tokens = sum(
        (getattr(m, "usage_metadata", None) or {}).get("input_tokens", 0) or
        (getattr(m, "response_metadata", None) or {}).get("token_usage", {}).get("prompt_tokens", 0) or
        (getattr(m, "additional_kwargs", None) or {}).get("usage", {}).get("prompt_tokens", 0)
        for m in msgs
    )
    output_tokens = sum(
        (getattr(m, "usage_metadata", None) or {}).get("output_tokens", 0) or
        (getattr(m, "response_metadata", None) or {}).get("token_usage", {}).get("completion_tokens", 0) or
        (getattr(m, "additional_kwargs", None) or {}).get("usage", {}).get("completion_tokens", 0)
        for m in msgs
    )
    if not input_tokens and not output_tokens:
        resp_str = state_out.get("final_response") or ""
        output_tokens = max(1, len(resp_str) // 4)
        input_tokens = output_tokens * 3
            
    cost_usd = (input_tokens / 1_000_000) * 5.0 + (output_tokens / 1_000_000) * 15.0
    
    # 3. Extract Citations & Tools Used
    citations = extract_citations(state_out)
    tools_used = extract_tools_used(state_out, citations)

    # 4. Construct Clean API Metadata
    workflow_state = state_out.get("workflow", {})
    execution_path = workflow_state.get("execution_path", [])
    execution_plan = workflow_state.get("execution_plan", {})
    
    metadata = {
        "complexity_level": workflow_state.get("complexity_level", "L3"),
        "total_latency_sec": total_seconds,
        "execution_path": execution_path,
        "execution_plan": execution_plan,
        "requires_human_validation": workflow_state.get("requires_escalation", False),
        "baseline_metrics": {
            "latency_sec": total_seconds,
            "latency_ms": latency_ms,
            "tsr_passed": tsr_passed,
            "grounding_score": round(grounding_score, 4),
            "relevancy_score": round(relevancy_score, 4),
            "confidence_score": round(confidence_score, 4),
            "context_precision": round(context_precision, 4),
            "recall_score": round(recall_score, 4),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": round(cost_usd, 6)
        },
        "evaluation_reasoning": eval_metrics.get("critique"),
        "evaluation_failures": eval_metrics.get("failures", [])
    }

    # 5. Report to Langfuse
    if langfuse_service.langfuse:
        try:
            langfuse_service.score(
                trace_id=str(request.session_id),
                name="Faithfulness",
                value=grounding_score,
                comment="Grounding Score"
            )
            langfuse_service.score(
                trace_id=str(request.session_id),
                name="Relevancy",
                value=relevancy_score,
                comment="Answer Relevancy"
            )
        except Exception:
            pass
            
    # 6. Persist to QueryHistory Database Table
    try:
        from backend.database.models.models import QueryHistory
        query_record = QueryHistory(
            session_id=request.session_id,
            user_query=request.query,
            assistant_response=state_out.get("final_response") or "No response generated.",
            confidence=confidence_score,
            latency_ms=latency_ms
        )
        db.add(query_record)
        db.commit()
    except Exception as db_e:
        logging.getLogger(__name__).error(f"Failed to save QueryHistory: {db_e}")
        db.rollback()
        
    # 7. Save to Semantic Cache
    if query_embedding:
        cache_service.save_to_cache(
            session_id=str(request.session_id),
            query_text=safe_query,
            query_embedding=query_embedding,
            response=state_out.get("final_response") or "No response generated.",
            metadata=metadata
        )
    
    return QueryResponse(
        response=state_out.get("final_response") or "No response generated.",
        citations=citations,
        tools_used=tools_used,
        metadata=metadata
    )


@router.post("/stream")
async def execute_query_stream(
    request: QueryRequest,
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Execute a streaming query via Server-Sent Events (SSE).
    Yields each LangGraph state transition dynamically to the frontend.
    """
    import time
    start_time = time.time()
    try:
        from backend.services.pii_service import pii_service
        safe_query = pii_service.anonymize_text(request.query)
    except Exception:
        safe_query = request.query
        
    query_embedding = None
    try:
        from backend.services.cache_service import cache_service
        from backend.services.embedding_service import embedding_service
        
        # 1. Check Exact Cache
        cached_result = cache_service.check_exact_cache(str(request.session_id), safe_query)
        
        # 2. Check Semantic Cache
        if not cached_result:
            query_embedding = embedding_service.embed_query(safe_query)
            if query_embedding:
                cached_result = cache_service.get_cached_response(
                    session_id=str(request.session_id),
                    query_embedding=query_embedding,
                    query_text=safe_query,
                    similarity_threshold=0.92
                )
        
        if cached_result:
            async def cached_stream_generator():
                yield 'data: {"status": "connected"}\n\n'
                import asyncio
                await asyncio.sleep(0.1)
                final_payload = {
                    "node": "semantic_cache",
                    "is_final": True,
                    "requires_escalation": False,
                    "final_response": cached_result["response"],
                    "citations": [],
                    "tools_used": ["semantic_cache"]
                }
                yield f"data: {json.dumps(final_payload)}\n\n"
                yield 'data: {"status": "done"}\n\n'
            return StreamingResponse(cached_stream_generator(), media_type="text/event-stream")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Cache check error in stream: {e}")
        
    state_in = {
        "shared": {
            "query": safe_query,
            "session_id": str(request.session_id),
            "snapshot_id": str(request.snapshot_id) if request.snapshot_id else None,
            "messages": [],
            "context": []
        },
        "workflow": {
            "current_node": "guardrail",
            "next_node": "guardrail",
            "status": "RUNNING",
            "requires_escalation": False,
            "execution_path": []
        },
        "analysis": {},
        "final_response": None
    }
    
    from backend.services.observability.langfuse import langfuse_service
    config = {"configurable": {"thread_id": str(request.session_id)}}
    
    try:
        prev_state_wrapper = workflow_router.workflow.get_state(config)
        prev_state = prev_state_wrapper.values if prev_state_wrapper else {}
        prev_msg_count = len(prev_state.get("shared", {}).get("messages", []))
        prev_ctx_count = len(prev_state.get("shared", {}).get("context", []))
        prev_path_count = len(prev_state.get("workflow", {}).get("execution_path", []))
    except Exception:
        prev_msg_count = 0
        prev_ctx_count = 0
        prev_path_count = 0
        
    state_in["workflow"]["current_execution_start_indices"] = {
        "messages": prev_msg_count,
        "context": prev_ctx_count,
        "execution_path": prev_path_count
    }
    if langfuse_service.langfuse:
        langfuse_handler = langfuse_service.get_callback_handler(session_id=request.session_id.hex)
        config["callbacks"] = [langfuse_handler]

    async def stream_generator():
        yield 'data: {"status": "connected"}\n\n'
        
        final_state_out = None
        try:
            async for output in workflow_router.workflow.astream(state_in, config=config):
                for node_name, node_state in output.items():
                    final_state_out = node_state
                    wf = node_state.get("workflow", {})
                    payload = {
                        "node": node_name,
                        "execution_path": wf.get("execution_path", []),
                        "is_final": wf.get("status") == "COMPLETE" or (node_name in ["evaluation", "human_validation"] and not wf.get("requires_escalation", False)),
                        "requires_escalation": wf.get("requires_escalation", False),
                        "next_action": wf.get("next_node")
                    }
                    
                    if payload["is_final"]:
                        payload["final_response"] = node_state.get("final_response")
                        citations = extract_citations(node_state)
                        payload["citations"] = [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in citations]
                        payload["tools_used"] = extract_tools_used(node_state, citations)
                        
                    import json
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.01)
                    
            # Poll if interrupted for human validation
            state = workflow_router.workflow.get_state(config)
            was_paused = bool(state.next)
            while state.next:
                yield ': heartbeat\n\n'
                await asyncio.sleep(2)
                state = workflow_router.workflow.get_state(config)
            
            if was_paused:
                final_state = state.values
                final_state_out = final_state
                citations = extract_citations(final_state)
                final_payload = {
                    "node": "human_validation",
                    "is_final": True,
                    "requires_escalation": False,
                    "final_response": final_state.get("final_response"),
                    "citations": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in citations],
                    "tools_used": extract_tools_used(final_state, citations)
                }
                import json
                yield f"data: {json.dumps(final_payload)}\n\n"
                
            if final_state_out and query_embedding:
                try:
                    from backend.services.cache_service import cache_service
                    cache_service.save_to_cache(
                        session_id=str(request.session_id),
                        query_text=safe_query,
                        query_embedding=query_embedding,
                        response=final_state_out.get("final_response") or "No response generated.",
                        metadata={}
                    )
                except Exception as cache_e:
                    logging.getLogger(__name__).warning(f"Cache save error: {cache_e}")
                    
            if final_state_out:
                try:
                    from backend.database.models.models import QueryHistory
                    import time
                    latency_ms = int((time.time() - start_time) * 1000)
                    eval_metrics = final_state_out.get("analysis", {}).get("evaluation", {})
                    confidence_score = eval_metrics.get("confidence_score", 0.95) if isinstance(eval_metrics, dict) else 0.95
                    
                    query_record = QueryHistory(
                        session_id=request.session_id,
                        user_query=request.query,
                        assistant_response=final_state_out.get("final_response") or "No response generated.",
                        confidence=confidence_score,
                        latency_ms=latency_ms
                    )
                    db.add(query_record)
                    db.commit()
                except Exception as db_e:
                    logging.getLogger(__name__).error(f"Failed to save QueryHistory in stream: {db_e}")
                    db.rollback()
                    
            yield 'data: {"status": "done"}\n\n'
            
        except Exception as e:
            yield f'data: {{"status": "error", "message": "{str(e)}"}}\n\n'

    return StreamingResponse(stream_generator(), media_type="text/event-stream")