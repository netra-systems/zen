# /v2/database.py
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from .config import settings

# --- Database Engine Setup ---
# Use PostgreSQL for production, but allow SQLite for simple local testing
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ORM Models ---

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    analysis_runs = relationship("AnalysisRun", back_populates="user")

class SupplyOption(Base):
    """
    Represents an LLM supply option in the database.
    """
    __tablename__ = "supply_options"

    id = Column(String, primary_key=True, default=generate_uuid)
    provider = Column(String, index=True, nullable=False)
    family = Column(String, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    hosting_type = Column(String, nullable=False, default="api_provider")
    cost_per_million_tokens_usd = Column(JSONB, nullable=False)
    quality_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AnalysisRun(Base):
    """
    Persists the state and results of a given analysis run.
    """
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending", index=True, nullable=False) # pending, running, completed, failed
    
    # Configuration used for the run
    config = Column(JSONB)
    
    # Results
    execution_log = Column(Text)
    result_summary = Column(JSONB) # For high-level results like cost savings
    result_details = Column(JSONB) # For detailed patterns, policies, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="analysis_runs")

def create_db_and_tables():
    """
    Creates all database tables defined as ORM models.
    This is useful for initial setup, especially with SQLite.
    For production PostgreSQL, Alembic migrations are preferred.
    """
    Base.metadata.create_all(bind=engine)
