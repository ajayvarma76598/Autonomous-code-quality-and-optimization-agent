from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import (
    executions,
    ingestion,
    operational,
    query,
    repositories,
    sessions,
)
from backend.config import settings

# Setup tracking logging for system tasks
from backend.utils.logging_config import setup_logging

logger = setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Autonomous Code Quality & Optimization System",
        description="API for the AI Agent Git Repository Platform",
        version="1.0.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Middleware
    # app.add_middleware(TimingAndLoggingMiddleware)

    from fastapi import Depends

    from backend.api.auth import get_current_user, require_role

    # Include Routers with Authentication
    app.include_router(
        repositories.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],
    )
    app.include_router(
        sessions.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],
    )
    app.include_router(
        executions.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],
    )
    app.include_router(
        query.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],
    )
    app.include_router(
        ingestion.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],
    )

    # Manager/Admin only routes
    app.include_router(
        operational.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(require_role(["admin"]))],
    )
    from backend.api.routers import escalation

    app.include_router(escalation.router, prefix=settings.API_V1_STR)

    # Register Exception Handlers
    from sqlalchemy.exc import SQLAlchemyError

    from backend.api.error_handlers import (
        database_exception_handler,
        global_exception_handler,
    )

    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up API server...")

        # Pre-initialize Redis Caching Services

        # Auto-ingest Capstone PDFs if they are missing
        import asyncio

        from backend.utils.document_ingestion import ingest_documents_if_missing

        logger.info("Scheduling Capstone PDF auto-ingestion check...")
        asyncio.create_task(asyncio.to_thread(ingest_documents_if_missing))

        # Golden Dataset evaluation runs automatically on startup
        # from backend.tests.test_langfuse_dataset import run_evaluation
        # logger.info("Scheduling Golden Dataset evaluation (5 random items)...")
        # asyncio.create_task(run_evaluation(dataset_name="golden-eval-v3", limit=5, random_sample=True))

    return app


app = create_app()
