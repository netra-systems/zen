"""Agent state database models for persistence and recovery."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from netra_backend.app.db.base import Base


class AgentStateSnapshot(Base):
    """Agent state snapshots for persistence and recovery."""
    __tablename__ = "agent_state_snapshots"
    
    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, index=True)
    thread_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)  # Removed FK for test compatibility
    
    # State versioning
    version: Mapped[str] = mapped_column(String, default="1.0")
    schema_version: Mapped[str] = mapped_column(String, default="1.0")
    checkpoint_type: Mapped[str] = mapped_column(String, default="manual")  # manual, auto, recovery
    
    # State data
    state_data: Mapped[dict] = mapped_column(JSON)
    serialization_format: Mapped[str] = mapped_column(String, default="json")
    compression_type: Mapped[Optional[str]] = mapped_column(String)  # None, gzip, zstd
    
    # Metadata
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_phase: Mapped[Optional[str]] = mapped_column(String)  # triage, data_analysis, etc.
    execution_context: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    
    # Recovery metadata
    is_recovery_point: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_reason: Mapped[Optional[str]] = mapped_column(String)
    parent_snapshot_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("agent_state_snapshots.id"))
    
    # Relationships - commented out for test compatibility
    # user: Mapped["User"] = relationship("User")
    parent_snapshot: Mapped[Optional["AgentStateSnapshot"]] = relationship("AgentStateSnapshot", remote_side=[id], back_populates="child_snapshots")
    child_snapshots: Mapped[List["AgentStateSnapshot"]] = relationship("AgentStateSnapshot", back_populates="parent_snapshot")
    
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
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(String, ForeignKey("agent_state_snapshots.id"), index=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    
    # Transaction details
    operation_type: Mapped[str] = mapped_column(String)  # create, update, merge, restore
    field_changes: Mapped[Optional[dict]] = mapped_column(JSON)  # Changed fields
    previous_values: Mapped[Optional[dict]] = mapped_column(JSON)  # Previous values for rollback
    
    # Execution context
    triggered_by: Mapped[str] = mapped_column(String)  # agent_name or system
    execution_phase: Mapped[Optional[str]] = mapped_column(String)
    
    # Performance tracking
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    memory_usage_mb: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, committed, failed, rolled_back
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    snapshot: Mapped["AgentStateSnapshot"] = relationship("AgentStateSnapshot")
    
    # Indexes
    __table_args__ = (
        Index('idx_state_tx_run_status', 'run_id', 'status'),
        Index('idx_state_tx_started', 'started_at'),
    )


class AgentRecoveryLog(Base):
    """Log for agent recovery operations."""
    __tablename__ = "agent_recovery_logs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, index=True)
    thread_id: Mapped[str] = mapped_column(String, index=True)
    
    # Recovery details
    recovery_type: Mapped[str] = mapped_column(String)  # restart, resume, rollback
    source_snapshot_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("agent_state_snapshots.id"))
    target_snapshot_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("agent_state_snapshots.id"))
    
    # Recovery triggers
    failure_reason: Mapped[Optional[str]] = mapped_column(String)
    trigger_event: Mapped[str] = mapped_column(String)  # crash, timeout, user_request
    auto_recovery: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Recovery results
    recovery_status: Mapped[str] = mapped_column(String, default="initiated")  # initiated, in_progress, completed, failed
    recovered_data: Mapped[Optional[dict]] = mapped_column(JSON)
    lost_data: Mapped[Optional[dict]] = mapped_column(JSON)
    data_integrity_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    
    # Performance metrics
    recovery_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    data_size_kb: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    source_snapshot: Mapped[Optional["AgentStateSnapshot"]] = relationship("AgentStateSnapshot", foreign_keys=[source_snapshot_id])
    target_snapshot: Mapped[Optional["AgentStateSnapshot"]] = relationship("AgentStateSnapshot", foreign_keys=[target_snapshot_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_recovery_run_initiated', 'run_id', 'initiated_at'),
        Index('idx_recovery_status', 'recovery_status'),
        Index('idx_recovery_auto', 'auto_recovery', 'initiated_at'),
    )