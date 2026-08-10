from langchain_core.tools import tool
from typing import Dict
from backend.ingestion.git import git_service

@tool
def clone_repository(git_url: str, branch: str = "main") -> str:
    """
    Clones a remote git repository into a temporary workspace.
    Returns the absolute path to the cloned repository.
    """
    return git_service.clone_repository(git_url, branch)

@tool
def get_repository_info(repo_path: str) -> Dict[str, str]:
    """
    Retrieves the latest commit hash, author, and commit message for a local repository path.
    """
    try:
        return git_service.get_latest_commit(repo_path)
    except Exception as e:
        return {"error": f"Failed to access repository at {repo_path}: {e}"}
