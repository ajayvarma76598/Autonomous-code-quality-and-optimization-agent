import logging
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class ServiceResult(BaseModel):
    success: bool = Field(description="Whether the service execution was successful.")
    data: Any | None = Field(
        default=None, description="The payload returned by the service."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or metrics."
    )
    duration_ms: float = Field(
        default=0.0, description="Execution duration in milliseconds."
    )
    error: str | None = Field(
        default=None, description="Error message if execution failed."
    )


class BaseService:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def execute(self, func: Callable, *args, **kwargs) -> ServiceResult:
        """
        Wraps service execution with standardized logging, metrics, and exception handling.
        """
        start_time = time.time()
        self.logger.info(f"Executing {func.__name__}")

        try:
            result_data = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            self.logger.info(
                f"Successfully executed {func.__name__} in {duration_ms:.2f}ms"
            )

            return ServiceResult(
                success=True, data=result_data, duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Failed to execute {func.__name__}: {e}", exc_info=True)

            return ServiceResult(success=False, duration_ms=duration_ms, error=str(e))
