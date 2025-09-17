"""Content, corpus, and analysis database models.

Defines models for corpus management, analysis operations, and content audit logging.
Focused module adhering to modular architecture and single responsibility.
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, JSON, Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from netra_backend.app.config import config_manager
from netra_backend.app.db.base import Base


# Use JSON instead of ARRAY for SQLite compatibility during testing
# For tests, always use JSON for array-like columns since SQLite doesn't support ARRAY
# SSOT compliance: Import from project_utils
from netra_backend.app.core.project_utils import is_test_environment as _is_test_environment

# Original function replaced:

# Always use JSON for array columns in tests
if _is_test_environment():
    ArrayType = lambda column_type: JSON
else:
    ArrayType = lambda column_type: ARRAY(column_type)


class CorpusAuditLog(Base):
    """Corpus audit log table for tracking all corpus operations."""
    __tablename__ = "corpus_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
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
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    created_by = relationship("User")