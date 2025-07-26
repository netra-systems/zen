# /v2/app/db/postgres.py
import logging
from sqlmodel import create_engine, SQLModel, Session
from ..config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, echo=True, connect_args=connect_args)

def create_postgres_db_and_tables():
    """
    Creates all PostgreSQL database tables defined by SQLModel metadata.
    """
    logger.info("Initializing PostgreSQL database and creating tables...")
    from . import models_postgres
    SQLModel.metadata.create_all(engine)
    logger.info("PostgreSQL database initialization complete.")

def get_db_session():
    """
    FastAPI dependency that provides a database session per request.
    """
    with Session(engine) as session:
        yield session
