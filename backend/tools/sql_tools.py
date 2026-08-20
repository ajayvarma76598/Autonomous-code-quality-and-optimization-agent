import logging

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.tools import tool

from backend.config import settings

logger = logging.getLogger(__name__)

_sql_db = None


def get_sql_db():
    global _sql_db
    if _sql_db is None:
        db_url = settings.DATABASE_URL
        if db_url and db_url.startswith("postgresql+asyncpg"):
            db_url = db_url.replace("postgresql+asyncpg", "postgresql")
        try:
            # Use sample_rows_in_table_info=0 for fast lazy initialization without heavy table reflection
            _sql_db = SQLDatabase.from_uri(db_url, sample_rows_in_table_info=0)
        except Exception as e:
            logger.error(f"Failed to initialize SQLDatabase in tools: {e}")
            _sql_db = None
    return _sql_db


@tool
def execute_sql_query(query: str) -> str:
    """
    Executes a raw SQL query against the PostgreSQL database containing code metrics and performance logs.
    Available tables:
    - repositories: repository_id, name, git_provider, description
    - repository_files: file_id, path, filename, extension, line_count
    - code_quality_metrics: metric_id, file_id, cyclomatic_complexity, maintainability_index,
      code_smell_count, test_coverage_percentage
    - performance_logs: log_id, repository_id, service_name, average_response_time_ms,
      error_rate_percentage, throughput_requests_per_second

    Use this tool to find files with high complexity, low maintainability, or services with high error rates.
    Make sure to write valid PostgreSQL queries.
    """
    db = get_sql_db()
    if not db:
        return "Error: Database connection not available."

    try:
        result = db.run(query)
        return result
    except Exception as e:
        return f"Error executing SQL query: {str(e)}"
