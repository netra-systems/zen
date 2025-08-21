"""Agent state database models for persistence and recovery."""

from sqlalchemy import (
    Column, String, DateTime, Boolean, JSON, Text, Integer, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from netra_backend.app.db.base import Base


class AgentStateSnapshot(Base):
    """Agent state snapshots for persistence and recovery."""
    __tablename__ = "agent_state_snapshots"
    
    # Primary identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # State versioning
    version = Column(String, nullable=False, default="1.0")
    schema_version = Column(String, nullable=False, default="1.0")
    checkpoint_type = Column(String, nullable=False, default="manual")  # manual, auto, recovery
    
    # State data
    state_data = Column(JSON, nullable=False)
    serialization_format = Column(String, nullable=False, default="json")
    compression_type = Column(String, nullable=True)  # None, gzip, zstd
    
    # Metadata
    step_count = Column(Integer, nullable=False, default=0)
    agent_phase = Column(String, nullable=True)  # triage, data_analysis, etc.
    execution_context = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Recovery metadata
    is_recovery_point = Column(Boolean, default=False)
    recovery_reason = Column(String, nullable=True)
    parent_snapshot_id = Column(String, ForeignKey("agent_state_snapshots.id"), nullable=True)
    
    # Relationships
    user = relationship("User")
    parent_snapshot = relationship("AgentStateSnapshot", remote_side=[id], back_populates="child_snapshots")
    child_snapshots = relationship("AgentStateSnapshot", back_populates="parent_snapshot")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_agent_state_run_created', 'run_id', 'created_at'),
        Index('idx_agent_state_thread_created', 'thread_id', 'created_at'),
        Index('idx_agent_state_recovery', 'is_recovery_point', 'created_at'),
        Index('idx_agent_state_expires', 'expires_at'),
        UniqueConstraint('run_id', 'checkpoint_type', 'created_at', 
                        name='uq_run_checkpoint_time'),
    )


class AgentStateTransaction(Base):
    """Transaction log for agent state changes."""
    __tablename__ = "agent_state_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id = Column(String, ForeignKey("agent_state_snapshots.id"), nullable=False, index=True)
    run_id = Column(String, nullable=False, index=True)
    
    # Transaction details
    operation_type = Column(String, nullable=False)  # create, update, merge, restore
    field_changes = Column(JSON, nullable=True)  # Changed fields
    previous_values = Column(JSON, nullable=True)  # Previous values for rollback
    
    # Execution context
    triggered_by = Column(String, nullable=False)  # agent_name or system
    execution_phase = Column(String, nullable=True)
    
    # Performance tracking
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    
    # Status tracking
    status = Column(String, nullable=False, default="pending")  # pending, committed, failed, rolled_back
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    snapshot = relationship("AgentStateSnapshot")
    
    # Indexes
    __table_args__ = (
        Index('idx_state_tx_run_status', 'run_id', 'status'),
        Index('idx_state_tx_started', 'started_at'),
    )


class AgentRecoveryLog(Base):
    """Log for agent recovery operations."""
    __tablename__ = "agent_recovery_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    
    # Recovery details
    recovery_type = Column(String, nullable=False)  # restart, resume, rollback
    source_snapshot_id = Column(String, ForeignKey("agent_state_snapshots.id"), nullable=True)
    target_snapshot_id = Column(String, ForeignKey("agent_state_snapshots.id"), nullable=True)
    
    # Recovery triggers
    failure_reason = Column(String, nullable=True)
    trigger_event = Column(String, nullable=False)  # crash, timeout, user_request
    auto_recovery = Column(Boolean, default=False)
    
    # Recovery results
    recovery_status = Column(String, nullable=False, default="initiated")  # initiated, in_progress, completed, failed
    recovered_data = Column(JSON, nullable=True)
    lost_data = Column(JSON, nullable=True)
    data_integrity_score = Column(Integer, nullable=True)  # 0-100
    
    # Performance metrics
    recovery_time_ms = Column(Integer, nullable=True)
    data_size_kb = Column(Integer, nullable=True)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    source_snapshot = relationship("AgentStateSnapshot", foreign_keys=[source_snapshot_id])
    target_snapshot = relationship("AgentStateSnapshot", foreign_keys=[target_snapshot_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_recovery_run_initiated', 'run_id', 'initiated_at'),
        Index('idx_recovery_status', 'recovery_status'),
        Index('idx_recovery_auto', 'auto_recovery', 'initiated_at'),
    )