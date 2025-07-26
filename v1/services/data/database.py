# /services/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON

# --- Database Configuration ---
# Use an environment variable for the database URL, default to a local SQLite file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./netra_main.db")

# create_engine is the starting point for any SQLAlchemy application.
# `connect_args` is needed only for SQLite to allow multi-threaded access.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our ORM models.
Base = declarative_base()

# --- ORM Model for SupplyOption ---
class SupplyOptionDB(Base):
    """
    SQLAlchemy ORM model representing a supply option in the database.
    This model maps the Python object to the database table.
    """
    __tablename__ = "supply_options"

    id = Column(String, primary_key=True, index=True)
    provider = Column(String, index=True, nullable=False)
    family = Column(String, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    hosting_type = Column(String, nullable=False)
    quantization = Column(String, nullable=True)
    cost_per_million_tokens_usd = Column(JSON, nullable=False)
    base_latency_ms = Column(Integer, nullable=False)
    time_to_first_token_ms = Column(Integer, nullable=False)
    quality_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    


def create_db_and_tables():
    """
    Creates the database and all tables defined by models that inherit from Base.
    This is typically called once on application startup.
    """
    Base.metadata.create_all(bind=engine)

