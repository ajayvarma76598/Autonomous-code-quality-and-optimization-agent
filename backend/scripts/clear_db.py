import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database.models.models import Base
from backend.database.session import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_db():
    try:
        logger.warning("DROPPING all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Tables dropped successfully.")

        logger.info("Re-initializing database tables...")
        init_db()
        logger.info("Database reset complete.")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")


if __name__ == "__main__":
    reset_db()
