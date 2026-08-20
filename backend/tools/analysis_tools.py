import os
from typing import Any

import requests
from langchain_core.tools import tool


def get_latest_project_key() -> str:
    from backend.database.models.models import RepositorySnapshot
    from backend.database.session import SessionLocal

    db = SessionLocal()
    try:
        latest = (
            db.query(RepositorySnapshot)
            .filter_by(is_latest=True)
            .order_by(RepositorySnapshot.indexed_at.desc())
            .first()
        )
        if latest:
            return str(latest.repository_id)
    finally:
        db.close()
    return ""


@tool
def analyze_code_quality(file_path: str) -> dict[str, Any]:
    """
    Performs static analysis on the specified source code file using SonarQube.
    Returns metrics such as complexity, code smells, bugs, and vulnerabilities.
    """
    sonar_host = os.environ.get("SONAR_HOST_URL", "").rstrip("/")
    sonar_token = os.environ.get("SONAR_TOKEN", "")

    if not sonar_host or not sonar_token:
        return {"error": "SonarQube credentials are not configured in the environment."}

    project_key = get_latest_project_key()
    if not project_key:
        return {
            "error": "No ingested repository found in the database to determine the SonarQube project key."
        }

    # The component key in SonarQube is typically {projectKey}:{relative_path}
    # Clean up file path to ensure it matches standard relative paths
    clean_path = file_path.replace("\\", "/")
    if clean_path.startswith("./"):
        clean_path = clean_path[2:]

    component_key = f"{project_key}:{clean_path}"

    # Query SonarQube Web API
    metrics = "bugs,vulnerabilities,code_smells,complexity,sqale_index"
    url = f"{sonar_host}/api/measures/component?component={component_key}&metricKeys={metrics}"

    try:
        response = requests.get(url, auth=(sonar_token, ""), timeout=10)

        if response.status_code == 404:
            return {
                "error": f"File {clean_path} not found in SonarQube. "
                "Ensure the file exists and was scanned during ingestion."
            }

        response.raise_for_status()
        data = response.json()

        measures = data.get("component", {}).get("measures", [])
        result = {"file": clean_path}

        for measure in measures:
            metric = measure["metric"]
            value = measure["value"]
            result[metric] = value

        return result

    except Exception as e:
        return {"error": f"Failed to fetch metrics from SonarQube: {str(e)}"}


@tool
def get_code_issues(file_path: str = None) -> dict[str, Any]:
    """
    Fetches specific code issues (bugs, vulnerabilities, code smells) from SonarQube.
    If file_path is provided, it fetches issues for that specific file. Otherwise it fetches project-level issues.
    Returns the issue messages, line numbers, severity, and type.
    """
    sonar_host = os.environ.get("SONAR_HOST_URL", "").rstrip("/")
    sonar_token = os.environ.get("SONAR_TOKEN", "")

    if not sonar_host or not sonar_token:
        return {"error": "SonarQube credentials are not configured in the environment."}

    project_key = get_latest_project_key()
    if not project_key:
        return {
            "error": "No ingested repository found in the database to determine the SonarQube project key."
        }

    url = f"{sonar_host}/api/issues/search?componentKeys={project_key}"
    if file_path:
        clean_path = file_path.replace("\\", "/")
        if clean_path.startswith("./"):
            clean_path = clean_path[2:]
        url += f"&componentKeys={project_key}:{clean_path}"

    url += "&statuses=OPEN,CONFIRMED,REOPENED&ps=50"

    try:
        response = requests.get(url, auth=(sonar_token, ""), timeout=10)
        response.raise_for_status()
        data = response.json()

        issues = data.get("issues", [])
        result = []
        for issue in issues:
            result.append(
                {
                    "type": issue.get("type"),
                    "severity": issue.get("severity"),
                    "message": issue.get("message"),
                    "file": issue.get("component", "").replace(f"{project_key}:", ""),
                    "line": issue.get("line", "N/A"),
                    "status": issue.get("status"),
                }
            )

        return {"issues": result, "total": data.get("total", 0)}

    except Exception as e:
        return {"error": f"Failed to fetch issues from SonarQube: {str(e)}"}
