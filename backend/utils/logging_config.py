import os
import sys
import logging
from logging.handlers import RotatingFileHandler

LOGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "logs"
)

def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Configures comprehensive logging output to stdout and logs/app.log.
    Purely adds tracking loggers without modifying business logic.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    if not log_level:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    level = getattr(logging, log_level, logging.INFO)

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicate output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 2. File Handler (logs/app.log)
    app_log_file = os.path.join(LOGS_DIR, "app.log")
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # Enable logging for backend namespaces
    logging.getLogger("backend").setLevel(level)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logger = logging.getLogger("backend.logging")
    logger.info(f"=== System Tracking Logger Initialized (Level={log_level}, File={app_log_file}) ===")
    return logger
