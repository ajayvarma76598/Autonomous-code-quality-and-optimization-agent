from langchain_core.tools import tool


@tool
def generate_readme(repo_summary: str, architecture_summary: str) -> str:
    """
    Generates a comprehensive README.md string based on repository and architecture summaries.
    """
    readme = f"# Repository Documentation\n\n## Overview\n{repo_summary}\n\n## Architecture\n{architecture_summary}\n"
    return readme
