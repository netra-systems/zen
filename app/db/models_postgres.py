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
    Numeric,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime, timezone
import os
import enum

# Use JSON instead of ARRAY for SQLite compatibility during testing
if os.getenv("TESTING", "0") == "1":
    # For SQLite testing, use JSON instead of ARRAY
    ArrayType = JSON
else:
    # For PostgreSQL production, use ARRAY
    ArrayType = lambda t: ARRAY(t)

class User(Base):
    __tablename__ = "userbase"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, index=True)
    hashed_password = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    # Admin permission fields
    role = Column(String, default="standard_user")  # standard_user, power_user, developer, admin, super_admin
    permissions = Column(JSON, default=dict)  # Additional granular permissions
    is_developer = Column(Boolean(), default=False)  # Auto-detected developer status
    
    # New plan and tool permission fields
    plan_tier = Column(String, default="free")  # free, pro, enterprise, developer
    plan_expires_at = Column(DateTime(timezone=True), nullable=True)  # Plan expiration
    feature_flags = Column(JSON, default=dict)  # Enabled feature flags
    tool_permissions = Column(JSON, default=dict)  # Per-tool permission overrides
    
    # Plan billing fields
    plan_started_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    auto_renew = Column(Boolean(), default=False)  # Auto-renewal enabled
    payment_status = Column(String, default="active")  # active, suspended, cancelled
    trial_period = Column(Boolean(), default=False)  # Is in trial period
    
    # Relationships
    secrets = relationship("Secret", back_populates="user", cascade="all, delete-orphan")


class CorpusAuditLog(Base):
    """Corpus audit log table for tracking all corpus operations."""
    __tablename__ = "corpus_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    user_id = Column(String, ForeignKey("userbase.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)  # create, update, delete, etc.
    status = Column(String, nullable=False, index=True)  # success, failure, partial, etc.
    corpus_id = Column(String, nullable=True, index=True)
    resource_type = Column(String, nullable=False, index=True)  # corpus, document, embedding, etc.
    resource_id = Column(String, nullable=True, index=True)
    operation_duration_ms = Column(Float, nullable=True)
    result_data = Column(JSON, nullable=True)  # Operation results/output
    
    # Metadata fields
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True, index=True)
    request_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    configuration = Column(JSON, default=dict)  # Operation configuration
    performance_metrics = Column(JSON, default=dict)  # Performance data
    error_details = Column(JSON, nullable=True)  # Error information
    compliance_flags = Column(ArrayType(String), default=list)  # Compliance indicators
    
    # Relationships
    user = relationship("User", backref="audit_logs")



class Secret(Base):
    __tablename__ = "secrets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("userbase.id"), nullable=False)
    key = Column(String, nullable=False)
    encrypted_value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user = relationship("User", back_populates="secrets")


class ToolUsageLog(Base):
    __tablename__ = "tool_usage_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("userbase.id"), nullable=False)
    tool_name = Column(String, nullable=False, index=True)
    category = Column(String, index=True)
    execution_time_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    cost_cents = Column(Integer, nullable=True)
    status = Column(String, nullable=False, index=True)  # success, error, permission_denied, rate_limited
    plan_tier = Column(String, nullable=False)  # User's plan at time of usage
    permission_check_result = Column(JSON, nullable=True)  # Permission check details
    arguments = Column(JSON, nullable=True)  # Tool arguments (for analytics)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    
    user = relationship("User")


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
    created_by_id = Column(String, ForeignKey("userbase.id"))
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
    friendly_name = Column(String, nullable=False)  # -facing name
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
    domain = Column(String, nullable=True, default="general")  # Domain for the corpus
    metadata_ = Column(JSON, nullable=True)  # Metadata for the corpus
    created_by_id = Column(String, ForeignKey("userbase.id"))
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
    file_ids = Column(ArrayType(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)

class Thread(Base):
    __tablename__ = "threads"
    id = Column(String, primary_key=True)
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
    file_ids = Column(ArrayType(String), nullable=False, default=[])
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
    file_ids = Column(ArrayType(String), nullable=False, default=[])
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


# Supply Research Models

class AvailabilityStatus(enum.Enum):
    AVAILABLE = "available"
    DEPRECATED = "deprecated" 
    PREVIEW = "preview"
    WAITLIST = "waitlist"


class AISupplyItem(Base):
    """AI model supply information"""
    __tablename__ = "ai_supply_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=True)
    pricing_input = Column(Numeric(10, 4), nullable=True)  # Cost per 1M input tokens
    pricing_output = Column(Numeric(10, 4), nullable=True)  # Cost per 1M output tokens
    pricing_currency = Column(String, default="USD")
    context_window = Column(Integer, nullable=True)
    max_output_tokens = Column(Integer, nullable=True)
    capabilities = Column(JSON, nullable=True)  # Array of model capabilities
    availability_status = Column(String, default="available")
    api_endpoints = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    last_updated = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    research_source = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Relationships
    update_logs = relationship("SupplyUpdateLog", back_populates="supply_item")


class ResearchSessionStatus(enum.Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSession(Base):
    """Google Deep Research session tracking"""
    __tablename__ = "research_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(Text, nullable=False)
    session_id = Column(String, nullable=True)  # Google Deep Research session ID
    status = Column(String, default="pending")
    research_plan = Column(JSON, nullable=True)
    questions_answered = Column(JSON, nullable=True)
    raw_results = Column(JSON, nullable=True)
    processed_data = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    initiated_by = Column(String, nullable=True)  # user_id or "scheduler"
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    update_logs = relationship("SupplyUpdateLog", back_populates="research_session")


class SupplyUpdateLog(Base):
    """Audit log for supply data changes"""
    __tablename__ = "supply_update_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    supply_item_id = Column(String, ForeignKey("ai_supply_items.id"), nullable=False)
    field_updated = Column(String, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    research_session_id = Column(String, ForeignKey("research_sessions.id"), nullable=True)
    update_reason = Column(String, nullable=True)
    updated_by = Column(String, nullable=False)  # user_id or "system"
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Relationships
    supply_item = relationship("AISupplyItem", back_populates="update_logs")
    research_session = relationship("ResearchSession", back_populates="update_logs")
