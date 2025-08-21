"""Supply research and AI model database models.

Defines models for AI supply research, model catalogs, and research sessions.
Focused module adhering to modular architecture and single responsibility.
"""

from sqlalchemy import (
    Column, String, DateTime, Boolean, JSON, Text, ForeignKey, 
    Float, Numeric, Integer
)
from sqlalchemy.orm import relationship
from netra_backend.app.base import Base
import uuid
from datetime import datetime, timezone
import enum


class Supply(Base):
    __tablename__ = "supplies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


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