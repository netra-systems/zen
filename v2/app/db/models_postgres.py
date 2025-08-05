from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Float,
    ARRAY,
)
from sqlalchemy.orm import relationship
from .base import Base  # Corrected: Import Base from the new central location.
import uuid
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    picture = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    secrets = relationship("Secret", back_populates="user")


class Secret(Base):
    __tablename__ = "secrets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    encrypted_value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="secrets")


class Supply(Base):
    __tablename__ = "supplies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    status = Column(String, default="pending")  # e.g., pending, running, completed, failed
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("User")
    results = relationship("AnalysisResult", back_populates="analysis")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("analyses.id"))
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="results")


class SupplyOption(Base):
    __tablename__ = "supply_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)
    family = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True, index=True)
    hosting_type = Column(String, default="api_provider")
    cost_per_million_tokens_usd = Column(JSON, nullable=False)
    quality_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DeepAgentRun(Base):
    __tablename__ = "deep_agent_runs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, index=True, nullable=False)
    step_name = Column(String, nullable=False)
    step_input = Column(JSON, nullable=True)
    step_output = Column(JSON, nullable=True)
    run_log = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)