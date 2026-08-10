import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from backend.workflows.state import AgentState
from backend.services.llm import llm_service
from backend.database.session import SessionLocal
from backend.database.models.models import RepositorySnapshot
from backend.prompts.registry import get_fallback_prompt

logger = logging.getLogger(__name__)

# --- Structured Output Models ---
class ExtractedFiles(BaseModel):
    files: List[str] = Field(description="List of file paths mentioned in the query.")

# --- Helper Functions ---
def get_project_key(snapshot_id: str) -> str:
    if not snapshot_id: return ""
    db = SessionLocal()
    try:
        snap = db.query(RepositorySnapshot).filter_by(snapshot_id=snapshot_id).first()
        if snap:
            return str(snap.repository_id)
    finally:
        db.close()
    return ""

def get_repo_path(snapshot_id: str) -> str:
    if not snapshot_id: return ""
    db = SessionLocal()
    try:
        snap = db.query(RepositorySnapshot).filter_by(snapshot_id=snapshot_id).first()
        if snap:
            temp_dir = os.environ.get("TEMP", "/tmp")
            return os.path.join(temp_dir, f"repo_{snap.repository_id}")
    finally:
        db.close()
    return ""

# --- Pipeline Nodes ---

def repository_parser_node(state: AgentState) -> dict:
    """Extracts files requested in the query and fetches their source code."""
    logger.info(f"Pipeline Node: repository_parser_node for session {state.get('shared', {}).get('session_id', 'unknown')}")
    
    query = state.get('shared', {}).get('query', '')
    llm = llm_service.get_llm(model_type="fast")
    
    # 1. Extract file names
    structured_llm = llm.with_structured_output(ExtractedFiles, method="function_calling")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract any specific file paths or names mentioned in the user query. If none, return an empty list."),
        ("human", "{query}")
    ])
    messages = prompt.format_messages(query=query)
    extracted = structured_llm.invoke(messages)
    
    context = state.get("quality_context", {}) or {}
    context["requested_files"] = extracted.files
    
    # 2. Fetch source code from disk (if repo path is known)
    snapshot_id = state.get("shared", {}).get("snapshot_id")
    project_key = get_project_key(snapshot_id)
    repo_path = get_repo_path(snapshot_id)
    
    parsed_code = {}
    if repo_path and os.path.exists(repo_path):
        for file in extracted.files:
            # Clean path to match standard
            clean_path = file.replace("\\", "/").lstrip("./")
            full_path = os.path.join(repo_path, clean_path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    parsed_code[clean_path] = f.read()
    
    context["parsed_code"] = parsed_code
    return {"quality_context": context}

def sonarqube_metrics_node(state: AgentState) -> dict:
    """Fetches SonarQube metrics for the parsed files."""
    logger.info(f"Pipeline Node: sonarqube_metrics_node for session {state.get('shared', {}).get('session_id', 'unknown')}")
    
    context = state.get("quality_context", {})
    files = context.get("requested_files", [])
    
    snapshot_id = state.get("shared", {}).get("snapshot_id")
    project_key = get_project_key(snapshot_id)
    sonar_host = os.environ.get("SONAR_HOST_URL", "").rstrip("/")
    sonar_token = os.environ.get("SONAR_TOKEN", "")
    
    metrics_data = {}
    analysis_error = None
    
    if not project_key:
        analysis_error = "No ingested repository found."
    elif not sonar_host or not sonar_token:
        analysis_error = "SonarQube credentials not configured."
    else:
        # If specific files are requested, query them. Otherwise, query the entire project.
        components_to_query = []
        if files:
            for file in files:
                clean_path = file.replace("\\", "/").lstrip("./")
                components_to_query.append((clean_path, f"{project_key}:{clean_path}"))
        else:
            components_to_query.append(("Project-Level", project_key))
            
        for name, component_key in components_to_query:
            url = f"{sonar_host}/api/measures/component?component={component_key}&metricKeys=bugs,vulnerabilities,code_smells,complexity,sqale_index"
            try:
                resp = requests.get(url, auth=(sonar_token, ""), timeout=10)
                if resp.status_code == 404:
                    continue # Component not found
                resp.raise_for_status()
                measures = resp.json().get("component", {}).get("measures", [])
                
                if measures:
                    metrics_data[name] = {m["metric"]: m["value"] for m in measures}
                    
                    # Fetch specific issues to show WHERE the code has bugs
                    issues_url = f"{sonar_host}/api/issues/search?componentKeys={component_key}&statuses=OPEN,CONFIRMED,REOPENED&ps=20"
                    try:
                        issues_resp = requests.get(issues_url, auth=(sonar_token, ""), timeout=10)
                        if issues_resp.status_code == 200:
                            issues = issues_resp.json().get("issues", [])
                            metrics_data[name]["specific_issues"] = [
                                {
                                    "type": i.get("type"),
                                    "severity": i.get("severity"),
                                    "message": i.get("message"),
                                    "file": i.get("component", "").split(":")[-1],
                                    "line": i.get("line", "N/A")
                                }
                                for i in issues
                            ]
                    except Exception as ie:
                        logger.error(f"SonarQube issues API error for {component_key}: {ie}")
                        
            except Exception as e:
                logger.error(f"SonarQube API error for {component_key}: {e}")
                
        if not metrics_data:
            analysis_error = "SonarQube has no analysis data for the requested scope. Ensure the repository has been successfully scanned."
            
    context["metrics"] = metrics_data
    return {"quality_context": context, "analysis_error": analysis_error}

def architecture_reviewer_node(state: AgentState) -> dict:
    """Evaluates the source code against Capstone guidelines (only if code was parsed)."""
    logger.info(f"Pipeline Node: architecture_reviewer_node for session {state.get('shared', {}).get('session_id', 'unknown')}")
    
    context = state.get("quality_context", {})
    parsed_code = context.get("parsed_code", {})
    
    if not parsed_code:
        return {} # Nothing to review
        
    llm = llm_service.get_llm(model_type="fast")
    reviews = {}
    
    for file, code in parsed_code.items():
        prompt = f"Analyze the following code for {file} against standard Capstone Architecture Guidelines (separation of concerns, dependency injection, clear interfaces, no global state).\n\nCode:\n{code}"
        messages = [
            SystemMessage(content="You are a strict architecture reviewer. Provide concise feedback."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages)
        reviews[file] = response.content
        
    context["architecture_reviews"] = reviews
    return {"quality_context": context}

def report_generator_node(state: AgentState) -> dict:
    """Generates the final grounded report or gracefully degrades if analysis_error exists."""
    logger.info(f"Pipeline Node: report_generator_node for session {state.get('shared', {}).get('session_id', 'unknown')}")
    
    context = state.get("quality_context", {})
    analysis_error = state.get("analysis_error")
    query = state.get('shared', {}).get('query', '')
    
    llm = llm_service.get_llm(model_type="fast")
    
    if analysis_error:
        # Graceful Degradation
        prompt = f"The user asked: '{query}'.\n\nHowever, we cannot fulfill this request because: {analysis_error}.\n\nPlease generate a direct, helpful response to the user. Explicitly state that we cannot draw code quality conclusions without SonarQube analysis data and explain the reason provided. Do NOT format this as an email or letter (no 'Dear User', no 'Best regards'). Speak directly as an AI coding assistant."
    else:
        # Grounded Report
        metrics = context.get("metrics", {})
        reviews = context.get("architecture_reviews", {})
        
        context_str = f"SonarQube Metrics: {json.dumps(metrics, indent=2)}\n\nArchitecture Reviews: {json.dumps(reviews, indent=2)}"
        
        system_prompt = get_fallback_prompt("quality_prompt")
        prompt = f"User Query: {query}\n\nEvidence Context:\n{context_str}\n\nGenerate a polished, straight-to-the-point code quality report grounded STRICTLY in this evidence. Use clear markdown formatting, summarize the metrics at the top, and list any specific issues clearly with their corresponding file paths and line numbers. Do not include fluffy introductions or conclusions."
        
    messages = [
        SystemMessage(content="You are a highly efficient Code Quality AI. Your outputs must be polished, structured, and straight to the point without unnecessary filler."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    # Give the response a name for routing logic
    response.name = "quality_pipeline"
    
    return {
        "shared": {"messages": [response]},
        "final_response": response.content,
        "workflow": {"next_node": "evaluation"}
    }
