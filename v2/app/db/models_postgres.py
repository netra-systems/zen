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
from .base import Base
import uuid
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, index=True)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    secrets = relationship("Secret", back_populates="user", cascade="all, delete-orphan")

class Secret(Base):
    __tablename__ = "secrets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    encrypted_value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user = relationship("User", back_populates="secrets")


class Supply(Base):
    __tablename__ = "supplies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    status = Column(String, default="pending")  # e.g., pending, running, completed, failed
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    created_by = relationship("User")
    results = relationship("AnalysisResult", back_populates="analysis")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("analyses.id"))
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

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
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class ApexOptimizerAgentRun(Base):
    __tablename__ = "apex_optimizer_agent_runs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, index=True, nullable=False)
    step_name = Column(String, nullable=False)
    step_input = Column(JSON, nullable=True)
    step_output = Column(JSON, nullable=True)
    run_log = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class ApexOptimizerAgentRunReport(Base):
    __tablename__ = "apex_optimizer_agent_run_reports"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, index=True, unique=True, nullable=False)
    report = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class Reference(Base):
    __tablename__ = "references"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)  # backend literal name
    friendly_name = Column(String, nullable=False)  # user-facing name
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)  # e.g., 'source', 'time_period'
    value = Column(String, nullable=False)
    version = Column(String, nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class Corpus(Base):
    __tablename__ = "corpora"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False, unique=True)
    description = Column(String, nullable=True)
    table_name = Column(String, nullable=True)
    status = Column(String, default="pending")  # e.g., pending, running, completed, failed
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    created_by = relationship("User")

class Assistant(Base):
    __tablename__ = "assistants"
    id = Column(String, primary_key=True)
    object = Column(String, nullable=False, default="assistant")
    created_at = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    model = Column(String, nullable=False)
    instructions = Column(String, nullable=True)
    tools = Column(JSON, nullable=False, default=[])
    file_ids = Column(ARRAY(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)

class Thread(Base):
    __tablename__ = "threads"
    id = Column(String, primary_key=Ture)
    object = Column(String, nullable=False, default="thread")
    created_at = Column(Integer, nullable=False)
    metadata_ = Column(JSON, nullable=True)
    messages = relationship("Message", back_populates="thread")
    runs = relationship("Run", back_populates="thread")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    object = Column(String, nullable=False, default="thread.message")
    created_at = Column(Integer, nullable=False)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(JSON, nullable=False)
    assistant_id = Column(String, ForeignKey("assistants.id"), nullable=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=True)
    file_ids = Column(ARRAY(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)
    thread = relationship("Thread", back_populates="messages")
    run = relationship("Run", back_populates="messages")
    assistant = relationship("Assistant")

class Run(Base):
    __tablename__ = "runs"
    id = Column(String, primary_key=True)
    object = Column(String, nullable=False, default="thread.run")
    created_at = Column(Integer, nullable=False)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=False)
    assistant_id = Column(String, ForeignKey("assistants.id"), nullable=False)
    status = Column(String, nullable=False)
    required_action = Column(JSON, nullable=True)
    last_error = Column(JSON, nullable=True)
    expires_at = Column(Integer, nullable=True)
    started_at = Column(Integer, nullable=True)
    cancelled_at = Column(Integer, nullable=True)
    failed_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    model = Column(String, nullable=True)
    instructions = Column(String, nullable=True)
    tools = Column(JSON, nullable=False, default=[])
    file_ids = Column(ARRAY(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)
    thread = relationship("Thread", back_populates="runs")
    assistant = relationship("Assistant")
    messages = relationship("Message", back_populates="run")
    steps = relationship("Step", back_populates="run")

class Step(Base):
    __tablename__ = "steps"
    id = Column(String, primary_key=True)
    object = Column(String, nullable=False, default="thread.run.step")
    created_at = Column(Integer, nullable=False)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    assistant_id = Column(String, ForeignKey("assistants.id"), nullable=False)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    step_details = Column(JSON, nullable=False)
    last_error = Column(JSON, nullable=True)
    expired_at = Column(Integer, nullable=True)
    cancelled_at = Column(Integer, nullable=True)
    failed_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    metadata_ = Column(JSON, nullable=True)
    run = relationship("Run", back_populates="steps")
