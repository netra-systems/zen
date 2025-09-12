"""ExecutionRegistry - Central tracking of all agent executions.

This module provides the Single Source of Truth for all agent execution state,
implementing thread-safe tracking to prevent silent failures and enable
comprehensive death detection and recovery.

Business Value: Core component that enables detection of silent agent failures
that cause infinite loading states and 100% UX degradation.
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# BACKWARD COMPATIBILITY: Import SSOT ExecutionState and create compatibility mapping
from netra_backend.app.core.agent_execution_tracker import ExecutionState as _SSOT_ExecutionState
import warnings

# Create compatibility ExecutionState class that maps to SSOT values
class ExecutionState(str, Enum):
    """
    DEPRECATED: Execution state enumeration with backward compatibility mapping.
    
     WARNING: [U+FE0F]  This ExecutionState is now mapped to the SSOT implementation.
        New code should import directly:
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
    """
    # Map registry-specific values to SSOT canonical values
    PENDING = _SSOT_ExecutionState.PENDING.value          # "pending"
    INITIALIZING = _SSOT_ExecutionState.STARTING.value    # "starting"  
    RUNNING = _SSOT_ExecutionState.RUNNING.value          # "running"
    SUCCESS = _SSOT_ExecutionState.COMPLETED.value        # "completed"
    FAILED = _SSOT_ExecutionState.FAILED.value            # "failed"
    TIMEOUT = _SSOT_ExecutionState.TIMEOUT.value          # "timeout"
    ABORTED = _SSOT_ExecutionState.CANCELLED.value        # "cancelled"
    RECOVERING = _SSOT_ExecutionState.STARTING.value  # Map RECOVERING -> STARTING for recovery scenarios

# Issue deprecation warning
warnings.warn(
    "ExecutionState from execution_tracking.registry is deprecated. "
    "Use 'from netra_backend.app.core.agent_execution_tracker import ExecutionState' instead.",
    DeprecationWarning,
    stacklevel=2
)


class ExecutionProgress(BaseModel):
    """Progress tracking for agent execution."""
    stage: str = "unknown"
    percentage: float = Field(ge=0.0, le=1.0, default=0.0)
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    tool_executions: List[str] = Field(default_factory=list)


class ExecutionRecord(BaseModel):
    """Complete execution record with all metadata."""
    execution_id: str
    run_id: str
    agent_name: str
    state: ExecutionState
    created_at: datetime
    updated_at: datetime
    timeout_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    progress: Optional[ExecutionProgress] = None
    error: Optional[str] = None
    retry_count: int = 0
    recovery_actions: List[str] = Field(default_factory=list)

    class Config:
        # Allow datetime serialization
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionMetrics(BaseModel):
    """Execution metrics for monitoring and dashboards."""
    active_executions: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_executions: int = 0
    average_execution_time_ms: float = 0.0
    success_rate: float = 0.0


class ExecutionRegistry:
    """Central registry for tracking all active agent executions.
    
    This is the Single Source of Truth (SSOT) for execution state tracking,
    providing thread-safe operations and comprehensive metrics.
    
    Key Features:
    - Thread-safe execution tracking
    - State transition validation
    - Automatic cleanup of expired executions
    - Comprehensive metrics and health reporting
    - Query interface for execution status
    """
    
    def __init__(self, cleanup_interval_seconds: int = 60):
        """Initialize ExecutionRegistry with cleanup configuration.
        
        Args:
            cleanup_interval_seconds: How often to clean up expired executions
        """
        self._executions: Dict[str, ExecutionRecord] = {}
        self._lock = asyncio.Lock()
        self._metrics = ExecutionMetrics()
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self._state_transitions = self._init_valid_transitions()
        
        # Start background cleanup task
        self._start_cleanup_task()
        
        logger.info(f" PASS:  ExecutionRegistry initialized with cleanup every {cleanup_interval_seconds}s")
    
    def _init_valid_transitions(self) -> Dict[ExecutionState, List[ExecutionState]]:
        """Initialize valid state transitions."""
        return {
            ExecutionState.PENDING: [ExecutionState.INITIALIZING, ExecutionState.ABORTED],
            ExecutionState.INITIALIZING: [ExecutionState.RUNNING, ExecutionState.FAILED, ExecutionState.ABORTED],
            ExecutionState.RUNNING: [ExecutionState.RUNNING, ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.RECOVERING],
            ExecutionState.FAILED: [ExecutionState.RECOVERING, ExecutionState.ABORTED],
            ExecutionState.TIMEOUT: [ExecutionState.RECOVERING, ExecutionState.ABORTED],
            ExecutionState.RECOVERING: [ExecutionState.RUNNING, ExecutionState.ABORTED, ExecutionState.SUCCESS],
            ExecutionState.SUCCESS: [],  # Terminal state
            ExecutionState.ABORTED: []   # Terminal state
        }
    
    async def register_execution(
        self, 
        run_id: str, 
        agent_name: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionRecord:
        """Register a new execution and return its record.
        
        Args:
            run_id: Original run ID from agent execution
            agent_name: Name of the executing agent
            context: Optional context metadata
            
        Returns:
            ExecutionRecord: The created execution record
            
        Raises:
            ValueError: If run_id or agent_name is invalid
        """
        if not run_id or not agent_name:
            raise ValueError("run_id and agent_name are required")
        
        execution_id = f"{agent_name}_{run_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        
        record = ExecutionRecord(
            execution_id=execution_id,
            run_id=run_id,
            agent_name=agent_name,
            state=ExecutionState.PENDING,
            created_at=now,
            updated_at=now,
            context=context or {}
        )
        
        async with self._lock:
            self._executions[execution_id] = record
            self._metrics.total_executions += 1
            self._metrics.active_executions = len([
                r for r in self._executions.values()
                if r.state not in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]
            ])
        
        logger.info(f"[U+1F4DD] Registered execution {execution_id} for {agent_name} (run_id: {run_id})")
        return record
    
    async def update_execution_state(
        self, 
        execution_id: str, 
        new_state: ExecutionState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update execution state with validation.
        
        Args:
            execution_id: The execution ID to update
            new_state: New state to transition to
            metadata: Optional metadata to include
            
        Returns:
            bool: True if update was successful, False if execution not found
            
        Raises:
            ValueError: If state transition is invalid
        """
        async with self._lock:
            if execution_id not in self._executions:
                logger.warning(f" WARNING: [U+FE0F] Attempted to update non-existent execution: {execution_id}")
                return False
            
            record = self._executions[execution_id]
            current_state = record.state
            
            # Validate state transition (allow same state for updates)
            if current_state != new_state and not self._is_valid_transition(current_state, new_state):
                raise ValueError(
                    f"Invalid state transition for {execution_id}: {current_state} -> {new_state}"
                )
            
            # Update record
            record.state = new_state
            record.updated_at = datetime.now(UTC)
            
            # Handle state-specific updates
            if new_state == ExecutionState.RUNNING:
                record.heartbeat_at = datetime.now(UTC)
            elif new_state in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]:
                self._update_completion_metrics(new_state, record)
            
            # Add metadata if provided
            if metadata:
                if "error" in metadata:
                    record.error = str(metadata["error"])
                if "progress" in metadata:
                    record.progress = ExecutionProgress(**metadata["progress"])
                if "recovery_action" in metadata:
                    record.recovery_actions.append(metadata["recovery_action"])
                if "retry_count" in metadata:
                    record.retry_count = metadata["retry_count"]
        
        logger.debug(f" CYCLE:  Updated execution {execution_id}: {current_state} -> {new_state}")
        return True
    
    def _is_valid_transition(self, current: ExecutionState, new: ExecutionState) -> bool:
        """Check if state transition is valid."""
        return new in self._state_transitions.get(current, [])
    
    def _update_completion_metrics(self, final_state: ExecutionState, record: ExecutionRecord) -> None:
        """Update metrics when execution completes."""
        if final_state == ExecutionState.SUCCESS:
            self._metrics.successful_executions += 1
        elif final_state == ExecutionState.FAILED:
            self._metrics.failed_executions += 1
        elif final_state == ExecutionState.TIMEOUT:
            self._metrics.timeout_executions += 1
        
        # Update active count
        self._metrics.active_executions = len([
            r for r in self._executions.values()
            if r.state not in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]
        ])
        
        # Update success rate
        total_completed = (
            self._metrics.successful_executions + 
            self._metrics.failed_executions + 
            self._metrics.timeout_executions
        )
        if total_completed > 0:
            self._metrics.success_rate = self._metrics.successful_executions / total_completed
        
        # Update average execution time
        execution_time_ms = (record.updated_at - record.created_at).total_seconds() * 1000
        if self._metrics.average_execution_time_ms == 0:
            self._metrics.average_execution_time_ms = execution_time_ms
        else:
            # Rolling average
            self._metrics.average_execution_time_ms = (
                self._metrics.average_execution_time_ms * 0.9 + execution_time_ms * 0.1
            )
    
    async def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get execution record by ID.
        
        Args:
            execution_id: The execution ID to retrieve
            
        Returns:
            ExecutionRecord or None if not found
        """
        async with self._lock:
            return self._executions.get(execution_id)
    
    async def get_active_executions(self) -> List[ExecutionRecord]:
        """Get all currently active executions.
        
        Returns:
            List of active ExecutionRecord objects
        """
        async with self._lock:
            return [
                record for record in self._executions.values()
                if record.state not in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]
            ]
    
    async def get_executions_by_agent(self, agent_name: str) -> List[ExecutionRecord]:
        """Get all executions for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of ExecutionRecord objects for the agent
        """
        async with self._lock:
            return [
                record for record in self._executions.values()
                if record.agent_name == agent_name
            ]
    
    async def get_executions_by_run_id(self, run_id: str) -> List[ExecutionRecord]:
        """Get all executions for a specific run ID.
        
        Args:
            run_id: The run ID to search for
            
        Returns:
            List of ExecutionRecord objects for the run ID
        """
        async with self._lock:
            return [
                record for record in self._executions.values()
                if record.run_id == run_id
            ]
    
    async def update_heartbeat(self, execution_id: str) -> bool:
        """Update heartbeat timestamp for execution.
        
        Args:
            execution_id: The execution ID to update
            
        Returns:
            bool: True if updated, False if execution not found
        """
        async with self._lock:
            if execution_id not in self._executions:
                return False
            
            self._executions[execution_id].heartbeat_at = datetime.now(UTC)
            self._executions[execution_id].updated_at = datetime.now(UTC)
            return True
    
    async def set_execution_timeout(self, execution_id: str, timeout_seconds: float) -> bool:
        """Set timeout for an execution.
        
        Args:
            execution_id: The execution ID
            timeout_seconds: Timeout in seconds from now
            
        Returns:
            bool: True if set, False if execution not found
        """
        async with self._lock:
            if execution_id not in self._executions:
                return False
            
            timeout_at = datetime.now(UTC) + timedelta(seconds=timeout_seconds)
            self._executions[execution_id].timeout_at = timeout_at
            self._executions[execution_id].updated_at = datetime.now(UTC)
            return True
    
    async def get_timed_out_executions(self) -> List[ExecutionRecord]:
        """Get executions that have exceeded their timeout.
        
        Returns:
            List of timed out ExecutionRecord objects
        """
        now = datetime.now(UTC)
        async with self._lock:
            return [
                record for record in self._executions.values()
                if record.timeout_at and record.timeout_at < now and record.state == ExecutionState.RUNNING
            ]
    
    async def get_stale_executions(self, stale_threshold_seconds: int = 300) -> List[ExecutionRecord]:
        """Get executions that haven't been updated recently.
        
        Args:
            stale_threshold_seconds: How old updates can be before considered stale
            
        Returns:
            List of stale ExecutionRecord objects
        """
        threshold = datetime.now(UTC) - timedelta(seconds=stale_threshold_seconds)
        async with self._lock:
            return [
                record for record in self._executions.values()
                if record.updated_at < threshold and record.state in [
                    ExecutionState.RUNNING, ExecutionState.INITIALIZING, ExecutionState.RECOVERING
                ]
            ]
    
    async def cleanup_expired_executions(self, retention_hours: int = 24) -> int:
        """Clean up old completed executions.
        
        Args:
            retention_hours: How many hours to retain completed executions
            
        Returns:
            int: Number of executions cleaned up
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=retention_hours)
        cleaned_count = 0
        
        async with self._lock:
            to_remove = []
            for execution_id, record in self._executions.items():
                if (record.state in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED] and
                    record.updated_at < cutoff_time):
                    to_remove.append(execution_id)
            
            for execution_id in to_remove:
                del self._executions[execution_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"[U+1F9F9] Cleaned up {cleaned_count} expired executions")
        
        return cleaned_count
    
    async def get_execution_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics.
        
        Returns:
            ExecutionMetrics object with current statistics
        """
        async with self._lock:
            # Update active count in case it's stale
            self._metrics.active_executions = len([
                r for r in self._executions.values()
                if r.state not in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]
            ])
            return self._metrics.copy()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with health information
        """
        metrics = await self.get_execution_metrics()
        active_executions = await self.get_active_executions()
        stale_executions = await self.get_stale_executions()
        
        return {
            "status": "healthy" if len(stale_executions) == 0 else "degraded",
            "total_tracked": len(self._executions),
            "active_executions": metrics.active_executions,
            "stale_executions": len(stale_executions),
            "success_rate": metrics.success_rate,
            "average_execution_time_ms": metrics.average_execution_time_ms,
            "agents_with_active_executions": list(set(r.agent_name for r in active_executions)),
            "oldest_active_execution": (
                min(active_executions, key=lambda r: r.created_at).created_at.isoformat()
                if active_executions else None
            )
        }
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self.cleanup_expired_executions()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def shutdown(self) -> None:
        """Shutdown the registry and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[U+1F6D1] ExecutionRegistry shutdown completed")
    
    def __len__(self) -> int:
        """Return number of tracked executions."""
        return len(self._executions)