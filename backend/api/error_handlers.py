import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unhandled exceptions to prevent crashing the server
    or leaking stack traces to the client.
    """
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later."}
    )

async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Catches specific database errors to avoid exposing schema details.
    """
    logger.error(f"Database Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Database Error", "detail": "A database operation failed."}
    )
