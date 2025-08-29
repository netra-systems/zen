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


class AgentStateMetadata(Base):
    """Agent state metadata for run tracking and recovery checkpoints.
    
    This table now stores ONLY critical metadata and recovery checkpoints,
    not the full state data which is now in Redis (active) and ClickHouse (historical).
    """
    __tablename__ = "agent_state_metadata"
    
    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, index=True, unique=True)  # One record per run
    thread_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    
    # Run configuration and status
    run_status: Mapped[str] = mapped_column(String, default="active")  # active, completed, failed, abandoned
    agent_type: Mapped[Optional[str]] = mapped_column(String)  # supervisor, analysis, etc.
    initial_phase: Mapped[Optional[str]] = mapped_column(String)  # Starting phase
    current_phase: Mapped[Optional[str]] = mapped_column(String)  # Current/final phase
    
    # Timestamps for run lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Recovery and persistence strategy
    redis_key: Mapped[Optional[str]] = mapped_column(String)  # Current Redis key for active state
    last_checkpoint_id: Mapped[Optional[str]] = mapped_column(String)  # Last recovery checkpoint
    checkpoint_frequency: Mapped[int] = mapped_column(Integer, default=10)  # Steps between checkpoints
    
    # Performance and resource tracking
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    peak_memory_mb: Mapped[Optional[int]] = mapped_column(Integer)
    total_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_agent_metadata_status_updated', 'run_status', 'last_updated'),
        Index('idx_agent_metadata_thread_created', 'thread_id', 'created_at'),
        Index('idx_agent_metadata_user_status', 'user_id', 'run_status'),
    )


class AgentStateCheckpoint(Base):
    """Critical recovery checkpoints stored in PostgreSQL.
    
    Only stores essential recovery points, not frequent state snapshots.
    Full state data is in Redis (active) and ClickHouse (historical).
    """
    __tablename__ = "agent_state_checkpoints"
    
    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, ForeignKey("agent_state_metadata.run_id"), index=True)
    checkpoint_sequence: Mapped[int] = mapped_column(Integer)  # Sequential checkpoint number
    
    # Checkpoint metadata
    checkpoint_type: Mapped[str] = mapped_column(String, default="recovery")  # recovery, milestone, final
    agent_phase: Mapped[str] = mapped_column(String)  # Phase when checkpoint was created
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Essential state for recovery (minimal data)
    essential_state: Mapped[Optional[dict]] = mapped_column(JSON)  # Only critical recovery data
    state_size_kb: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Redis and ClickHouse references
    redis_key: Mapped[Optional[str]] = mapped_column(String)  # Redis key at time of checkpoint
    clickhouse_ref: Mapped[Optional[str]] = mapped_column(String)  # Reference to ClickHouse record
    
    # Recovery metadata
    recovery_priority: Mapped[str] = mapped_column(String, default="normal")  # critical, high, normal, low
    recovery_tested: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    run_metadata: Mapped["AgentStateMetadata"] = relationship("AgentStateMetadata")
    
    # Indexes for recovery performance
    __table_args__ = (
        Index('idx_checkpoint_run_sequence', 'run_id', 'checkpoint_sequence'),
        Index('idx_checkpoint_priority_created', 'recovery_priority', 'created_at'),
        Index('idx_checkpoint_expires', 'expires_at'),
        UniqueConstraint('run_id', 'checkpoint_sequence', name='uq_run_checkpoint_seq'),
    )


class AgentStateSnapshot(Base):
    """DEPRECATED: Legacy agent state snapshots - kept for backward compatibility.
    
    This table is being phased out in favor of the new 3-tier architecture:
    - Redis: Primary active state storage
    - ClickHouse: Historical analytics and time-series data  
    - PostgreSQL: Metadata and critical recovery checkpoints only
    
    New code should use AgentStateMetadata and AgentStateCheckpoint instead.
    """
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