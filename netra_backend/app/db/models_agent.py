"""Agent, assistant, and workflow database models.

Defines models for AI assistants, threads, messages, runs, and agent operations.
Focused module adhering to modular architecture and single responsibility.
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from netra_backend.app.config import config_manager
from netra_backend.app.db.base import Base


# Use JSON instead of ARRAY for SQLite compatibility during testing
# For tests, always use JSON for array-like columns since SQLite doesn't support ARRAY
# SSOT compliance: Import from project_utils
from netra_backend.app.core.project_utils import is_test_environment as _is_test_environment

# Original function replaced:

# Always use JSON for file_ids and other array columns in tests
# Debug: Check test environment detection
_test_env = _is_test_environment()
if _test_env:
    ArrayType = lambda column_type: JSON
else:
    ArrayType = lambda column_type: ARRAY(column_type)


class Assistant(Base):
    __tablename__ = "assistants"
    id = Column(String(255), primary_key=True)
    object = Column(String(255), nullable=False, default="assistant")
    created_at = Column(Integer, nullable=False)
    name = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    model = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=True)
    tools = Column(JSON, nullable=False, default=[])
    file_ids = Column(ArrayType(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)


class Thread(Base):
    __tablename__ = "threads"
    id = Column(String(255), primary_key=True)
    object = Column(String(255), nullable=False, default="thread")
    created_at = Column(Integer, nullable=False)
    metadata_ = Column(JSON, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Add soft delete support
    messages = relationship("Message", back_populates="thread")
    runs = relationship("Run", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"
    id = Column(String(255), primary_key=True)
    object = Column(String(255), nullable=False, default="thread.message")
    created_at = Column(Integer, nullable=False)
    thread_id = Column(String(255), ForeignKey("threads.id"), nullable=False)
    role = Column(String(255), nullable=False)
    content = Column(JSON, nullable=False)
    assistant_id = Column(String(255), ForeignKey("assistants.id"), nullable=True)
    run_id = Column(String(255), ForeignKey("runs.id"), nullable=True)
    file_ids = Column(ArrayType(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)
    thread = relationship("Thread", back_populates="messages")
    run = relationship("Run", back_populates="messages")
    assistant = relationship("Assistant")


class Run(Base):
    __tablename__ = "runs"
    id = Column(String(255), primary_key=True)
    object = Column(String(255), nullable=False, default="thread.run")
    created_at = Column(Integer, nullable=False)
    thread_id = Column(String(255), ForeignKey("threads.id"), nullable=False)
    assistant_id = Column(String(255), ForeignKey("assistants.id"), nullable=False)
    status = Column(String(255), nullable=False)
    required_action = Column(JSON, nullable=True)
    last_error = Column(JSON, nullable=True)
    expires_at = Column(Integer, nullable=True)
    started_at = Column(Integer, nullable=True)
    cancelled_at = Column(Integer, nullable=True)
    failed_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    model = Column(String(255), nullable=True)
    instructions = Column(Text, nullable=True)
    tools = Column(JSON, nullable=False, default=[])
    file_ids = Column(ArrayType(String), nullable=False, default=[])
    metadata_ = Column(JSON, nullable=True)
    thread = relationship("Thread", back_populates="runs")
    assistant = relationship("Assistant")
    messages = relationship("Message", back_populates="run")
    steps = relationship("Step", back_populates="run")


class Step(Base):
    __tablename__ = "steps"
    id = Column(String(255), primary_key=True)
    object = Column(String(255), nullable=False, default="thread.run.step")
    created_at = Column(Integer, nullable=False)
    run_id = Column(String(255), ForeignKey("runs.id"), nullable=False)
    assistant_id = Column(String(255), ForeignKey("assistants.id"), nullable=False)
    thread_id = Column(String(255), ForeignKey("threads.id"), nullable=False)
    type = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False)
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
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(255), index=True, nullable=False)
    step_name = Column(String(255), nullable=False)
    step_input = Column(JSON, nullable=True)
    step_output = Column(JSON, nullable=True)
    run_log = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class ApexOptimizerAgentRunReport(Base):
    __tablename__ = "apex_optimizer_agent_run_reports"
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(255), index=True, unique=True, nullable=False)
    report = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))