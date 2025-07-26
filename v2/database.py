# /v2/database.py
import logging
from sqlmodel import create_engine, SQLModel, Session
from .config import settings

# For SQLite, the connect_args are important to allow multithreading, which is
# how FastAPI handles requests. This is not needed for PostgreSQL.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

# Create the main database engine instance
engine = create_engine(settings.DATABASE_URL, echo=True, connect_args=connect_args)


def create_db_and_tables():
    """
    Creates all database tables defined by SQLModel metadata.
    This function is called on application startup.
    """
    logging.info("Initializing database and creating tables...")
    # The import of models here ensures that all classes inheriting from SQLModel
    # are registered with the metadata object before we call create_all.
    from . import models 
    SQLModel.metadata.create_all(engine)
    logging.info("Database initialization complete.")


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    It uses a 'yield' pattern to ensure the session is always closed,
    even if an error occurs.
    """
    with Session(engine) as session:
        yield session
