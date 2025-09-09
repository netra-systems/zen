"""Agent state schemas for state persistence and recovery."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class CheckpointType(str, Enum):
    """Types of state checkpoints."""
    MANUAL = "manual"
    AUTO = "auto"
    RECOVERY = "recovery"
    PHASE_TRANSITION = "phase_transition"
    FULL = "full"
    CRITICAL = "critical"
    INTERMEDIATE = "intermediate"
    PIPELINE_COMPLETE = "pipeline_complete"


class RecoveryType(str, Enum):
    """Types of agent recovery operations."""
    RESTART = "restart"
    RESUME = "resume"
    ROLLBACK = "rollback"


class SerializationFormat(str, Enum):
    """State serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"


class AgentPhase(str, Enum):
    """Agent execution phases."""
    INITIALIZATION = "initialization"
    TRIAGE = "triage"
    DATA_ANALYSIS = "data_analysis"
    OPTIMIZATION = "optimization"
    ACTION_PLANNING = "action_planning"
    REPORTING = "reporting"
    COMPLETION = "completion"


class StateTransactionStatus(str, Enum):
    """Status of state transactions."""
    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RecoveryStatus(str, Enum):
    """Status of recovery operations."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStateMetadata(BaseModel):
    """Metadata for agent state snapshots."""
    model_config = ConfigDict(use_enum_values=True)
    
    version: str = "1.0"
    schema_version: str = "1.0"
    checkpoint_type: CheckpointType = CheckpointType.MANUAL
    step_count: int = 0
    agent_phase: Optional[AgentPhase] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = None


class StateSnapshot(BaseModel):
    """Complete agent state snapshot."""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    run_id: str
    thread_id: str
    user_id: Optional[str] = None
    metadata: AgentStateMetadata
    state_data: Dict[str, Any]
    serialization_format: SerializationFormat = SerializationFormat.JSON
    is_recovery_point: bool = False
    recovery_reason: Optional[str] = None
    parent_snapshot_id: Optional[str] = None


class StateTransaction(BaseModel):
    """Agent state transaction record."""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    snapshot_id: str
    run_id: str
    operation_type: str
    field_changes: Optional[Dict[str, Any]] = None
    previous_values: Optional[Dict[str, Any]] = None
    triggered_by: str
    execution_phase: Optional[AgentPhase] = None
    status: StateTransactionStatus = StateTransactionStatus.PENDING
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None


class RecoveryOperation(BaseModel):
    """Agent recovery operation record."""
    model_config = ConfigDict(use_enum_values=True)
    
    id: str
    run_id: str
    thread_id: str
    recovery_type: RecoveryType
    source_snapshot_id: Optional[str] = None
    target_snapshot_id: Optional[str] = None
    failure_reason: Optional[str] = None
    trigger_event: str
    auto_recovery: bool = False
    recovery_status: RecoveryStatus = RecoveryStatus.INITIATED
    recovered_data: Optional[Dict[str, Any]] = None
    lost_data: Optional[Dict[str, Any]] = None
    data_integrity_score: Optional[int] = None
    recovery_time_ms: Optional[int] = None
    initiated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None


class StateCompressionInfo(BaseModel):
    """Information about state compression."""
    compression_type: Optional[str] = None
    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float = Field(ge=0.0, le=1.0)


class StatePersistenceRequest(BaseModel):
    """Request to persist agent state."""
    model_config = ConfigDict(use_enum_values=True)
    
    run_id: str
    thread_id: str
    user_id: Optional[str] = None
    state_data: Dict[str, Any]
    checkpoint_type: CheckpointType = CheckpointType.MANUAL
    agent_phase: Optional[AgentPhase] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    is_recovery_point: bool = False
    expires_at: Optional[datetime] = None


class StateRecoveryRequest(BaseModel):
    """Request to recover agent state."""
    model_config = ConfigDict(use_enum_values=True)
    
    run_id: str
    thread_id: str
    recovery_type: RecoveryType = RecoveryType.RESUME
    target_snapshot_id: Optional[str] = None
    failure_reason: Optional[str] = None
    auto_recovery: bool = False


class StateValidationResult(BaseModel):
    """Result of state validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    corrupted_fields: List[str] = Field(default_factory=list)
    validation_score: float = Field(ge=0.0, le=1.0, default=1.0)


class StateMergeResult(BaseModel):
    """Result of state merge operation."""
    success: bool
    merged_state: Optional[Dict[str, Any]] = None
    conflicts: List[str] = Field(default_factory=list)
    merge_strategy_used: str
    data_integrity_maintained: bool = True


class StateBackupInfo(BaseModel):
    """Information about state backup."""
    backup_id: str
    snapshot_ids: List[str]
    backup_type: str  # full, incremental, differential
    file_path: Optional[str] = None
    size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retention_days: int = 30


class StateHealthCheck(BaseModel):
    """Health check result for agent state."""
    run_id: str
    is_healthy: bool
    last_checkpoint: Optional[datetime] = None
    checkpoint_count: int = 0
    data_integrity_score: float = Field(ge=0.0, le=1.0, default=1.0)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))