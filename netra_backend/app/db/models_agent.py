"""Agent, assistant, and workflow database models.

Defines models for AI assistants, threads, messages, runs, and agent operations.
Focused module adhering to modular architecture and single responsibility.
"""

import os
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, 
    ARRAY, Text
)
from sqlalchemy.orm import relationship
from netra_backend.app.db.base import Base
import uuid
from datetime import datetime, timezone
from netra_backend.app.core.configuration.base import config_manager

# Use JSON instead of ARRAY for SQLite compatibility during testing
def _get_array_type(column_type):
    """Get appropriate array type based on configuration."""
    try:
        config = config_manager.get_config()
        if getattr(config, 'testing', False):
            # For SQLite testing, use JSON instead of ARRAY
            return JSON
        else:
            # For PostgreSQL production, use ARRAY
            return ARRAY(column_type)
    except Exception:
        # Fallback to ARRAY if config not available during import
        return ARRAY(column_type)

# Lazy evaluation - only call config when creating actual columns
ArrayType = _get_array_type


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