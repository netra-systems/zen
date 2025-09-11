"""
Agent Execution Tracker
========================
CRITICAL MODULE for tracking agent execution lifecycle and detecting death.

This module is the SSOT for agent execution state tracking, providing:
1. Unique execution ID generation
2. Real-time execution state tracking
3. Death detection through heartbeat monitoring
4. Timeout enforcement
5. Execution history and metrics

Business Value: Prevents silent agent failures that break chat interactions.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, TypeVar
from collections import defaultdict
# Import UnifiedIDManager for SSOT ID generation  
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class ExecutionState(Enum):
    """Agent execution states"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DEAD = "dead"
    CANCELLED = "cancelled"


class AgentExecutionPhase(Enum):
    """Explicit phases of agent execution for comprehensive tracking."""
    # Initialization phases
    CREATED = "created"
    WEBSOCKET_SETUP = "websocket_setup"
    CONTEXT_VALIDATION = "context_validation"
    
    # Execution phases
    STARTING = "starting"
    THINKING = "thinking"
    TOOL_PREPARATION = "tool_preparation"
    LLM_INTERACTION = "llm_interaction"
    TOOL_EXECUTION = "tool_execution"
    RESULT_PROCESSING = "result_processing"
    
    # Completion phases
    COMPLETING = "completing"
    COMPLETED = "completed"
    
    # Error phases
    TIMEOUT = "timeout"
    FAILED = "failed"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class CircuitBreakerState(Enum):
    """Circuit breaker states for LLM integration resilience."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, block requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class TimeoutConfig:
    """Configuration for agent execution timeouts."""
    # Individual agent execution timeout
    agent_execution_timeout: float = 25.0  # Reduced from 30s for faster feedback
    
    # LLM API call timeout  
    llm_api_timeout: float = 15.0  # Individual LLM calls
    
    # Circuit breaker configuration
    failure_threshold: int = 3  # Open circuit after 3 failures
    recovery_timeout: float = 30.0  # Wait 30s before testing recovery
    success_threshold: int = 2  # Require 2 successes to close circuit
    
    # Retry configuration
    max_retries: int = 2
    retry_base_delay: float = 1.0  # Start with 1s delay
    retry_max_delay: float = 5.0   # Max 5s delay
    retry_exponential_base: float = 2.0  # Exponential backoff multiplier


@dataclass
class PhaseTransition:
    """Records a transition between execution phases."""
    from_phase: Optional[AgentExecutionPhase]
    to_phase: AgentExecutionPhase
    timestamp: datetime
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    websocket_event_sent: bool = False


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass


@dataclass
class ExecutionRecord:
    """Record of a single agent execution"""
    execution_id: str
    agent_name: str
    thread_id: str
    user_id: str
    state: ExecutionState
    started_at: datetime
    last_heartbeat: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    heartbeat_count: int = 0
    timeout_seconds: int = 15  # WEBSOCKET OPTIMIZATION: Reduced from 30s to 15s for faster failure detection
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Enhanced state management fields (consolidated from AgentStateTracker)
    current_phase: AgentExecutionPhase = AgentExecutionPhase.CREATED
    phase_history: List[PhaseTransition] = field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0
    
    # Enhanced timeout management fields (consolidated from AgentExecutionTimeoutManager)
    timeout_config: Optional[TimeoutConfig] = None
    circuit_breaker_failures: int = 0
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    last_failure_time: float = 0.0
    next_attempt_time: float = 0.0
    
    @property
    def is_alive(self) -> bool:
        """Check if execution is still alive"""
        return self.state in [ExecutionState.PENDING, ExecutionState.STARTING, 
                             ExecutionState.RUNNING, ExecutionState.COMPLETING]
    
    @property
    def is_terminal(self) -> bool:
        """Check if execution is in terminal state"""
        return self.state in [ExecutionState.COMPLETED, ExecutionState.FAILED, 
                             ExecutionState.TIMEOUT, ExecutionState.DEAD, 
                             ExecutionState.CANCELLED]
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get execution duration"""
        if self.completed_at:
            return self.completed_at - self.started_at
        elif self.is_alive:
            return datetime.now(timezone.utc) - self.started_at
        return None
    
    @property
    def time_since_heartbeat(self) -> timedelta:
        """Time since last heartbeat"""
        return datetime.now(timezone.utc) - self.last_heartbeat
    
    def is_timed_out(self) -> bool:
        """Check if execution has timed out"""
        if self.is_terminal:
            return self.state == ExecutionState.TIMEOUT
        
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def is_dead(self, heartbeat_timeout: int = 10) -> bool:
        """Check if agent is dead (no heartbeat)"""
        if self.is_terminal:
            return self.state == ExecutionState.DEAD
        
        seconds_since_heartbeat = self.time_since_heartbeat.total_seconds()
        return seconds_since_heartbeat > heartbeat_timeout
    
    # Enhanced state management methods (consolidated from AgentStateTracker)
    def get_total_duration_ms(self) -> float:
        """Get total execution duration in milliseconds."""
        current_time = datetime.now(timezone.utc)
        return (current_time - self.started_at).total_seconds() * 1000
    
    def get_phase_duration_ms(self, phase: AgentExecutionPhase) -> float:
        """Get duration spent in a specific phase."""
        total_duration = 0.0
        for transition in self.phase_history:
            if transition.to_phase == phase:
                total_duration += transition.duration_ms
        return total_duration
    
    def get_current_phase_duration_ms(self) -> float:
        """Get duration of current phase."""
        if not self.phase_history:
            return self.get_total_duration_ms()
        
        last_transition = self.phase_history[-1]
        current_time = datetime.now(timezone.utc)
        return (current_time - last_transition.timestamp).total_seconds() * 1000
    
    # Enhanced timeout management methods (consolidated from AgentExecutionTimeoutManager)
    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.circuit_breaker_state == CircuitBreakerState.OPEN:
            current_time = time.time()
            return current_time < self.next_attempt_time
        return False
    
    def should_retry(self, max_retries: int = 2) -> bool:
        """Check if execution should be retried based on circuit breaker state."""
        return (self.circuit_breaker_failures <= max_retries and 
                self.circuit_breaker_state != CircuitBreakerState.OPEN)


class AgentExecutionTracker:
    """
    Central tracker for all agent executions.
    
    CRITICAL: This is the SSOT for agent execution state.
    All agent execution must be tracked through this module.
    """
    
    def __init__(self, 
                 heartbeat_timeout: int = 10,
                 execution_timeout: int = 15,  # WEBSOCKET OPTIMIZATION: Reduced from 30s to 15s for faster failure detection
                 cleanup_interval: int = 60,
                 timeout_config: Optional[TimeoutConfig] = None):
        """
        Initialize execution tracker.
        
        Args:
            heartbeat_timeout: Seconds before considering agent dead (no heartbeat)
            execution_timeout: Default execution timeout in seconds
            cleanup_interval: Interval for cleaning up old executions
            timeout_config: Optional timeout configuration for consolidated timeout management
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.execution_timeout = execution_timeout
        self.cleanup_interval = cleanup_interval
        self.timeout_config = timeout_config or TimeoutConfig()
        
        # Storage
        self._executions: Dict[str, ExecutionRecord] = {}
        self._active_executions: Set[str] = set()
        self._executions_by_agent: Dict[str, Set[str]] = defaultdict(set)
        self._executions_by_thread: Dict[str, Set[str]] = defaultdict(set)
        
        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._death_callbacks: List[Any] = []
        self._timeout_callbacks: List[Any] = []
        
        # Metrics
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._timeout_executions = 0
        self._dead_executions = 0
        
        # Enhanced state management (consolidated from AgentStateTracker)
        self._phase_transition_rules = self._initialize_phase_transition_rules()
        self._max_completed_history = 100
        self._completed_executions: List[ExecutionRecord] = []
        
        # Enhanced timeout management (consolidated from AgentExecutionTimeoutManager)
        self._circuit_breaker_callbacks: List[Any] = []
        self._retry_callbacks: List[Any] = []
        
    async def start_monitoring(self):
        """Start background monitoring for dead/timed-out agents"""
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self._monitor_executions())
            logger.info("Started agent execution monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("Stopped agent execution monitoring")
    
    def create_execution(self,
                        agent_name: str,
                        thread_id: str,
                        user_id: str,
                        timeout_seconds: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new execution record.
        
        Returns:
            Unique execution ID
        """
        # Use UnifiedIDManager for structured execution ID with audit trail
        id_manager = UnifiedIDManager()
        execution_id = id_manager.generate_id(
            IDType.EXECUTION,
            prefix="exec",
            context={
                "agent_name": agent_name,
                "operation": "execution",
                "timestamp": int(time.time())
            }
        )
        
        now = datetime.now(timezone.utc)
        record = ExecutionRecord(
            execution_id=execution_id,
            agent_name=agent_name,
            thread_id=thread_id,
            user_id=user_id,
            state=ExecutionState.PENDING,
            started_at=now,
            last_heartbeat=now,
            updated_at=now,
            timeout_seconds=timeout_seconds or self.execution_timeout,
            metadata=metadata or {}
        )
        
        # Store execution
        self._executions[execution_id] = record
        self._active_executions.add(execution_id)
        self._executions_by_agent[agent_name].add(execution_id)
        self._executions_by_thread[thread_id].add(execution_id)
        
        # Update metrics
        self._total_executions += 1
        
        logger.info(f"Created execution {execution_id} for agent {agent_name}")
        return execution_id
    
    def start_execution(self, execution_id: str) -> bool:
        """
        Mark execution as started.
        
        Returns:
            True if successful, False if execution not found or invalid state
        """
        record = self._executions.get(execution_id)
        if not record or record.state != ExecutionState.PENDING:
            return False
        
        record.state = ExecutionState.STARTING
        record.updated_at = datetime.now(timezone.utc)
        record.last_heartbeat = datetime.now(timezone.utc)
        
        logger.info(f"Started execution {execution_id}")
        return True
    
    def update_execution_state(self, 
                              execution_id: str,
                              state: ExecutionState,
                              error: Optional[str] = None,
                              result: Optional[Any] = None) -> bool:
        """
        Update execution state.
        
        CRITICAL VALIDATION (Issue #305): Only ExecutionState enum values accepted.
        Rejects dict objects that were causing "'dict' object has no attribute 'value'" errors.
        
        Args:
            execution_id: The execution ID to update
            state: ExecutionState enum value (NOT dict objects)
            error: Optional error message
            result: Optional execution result
        
        Returns:
            True if successful, False if execution not found
            
        Raises:
            TypeError: If state is not an ExecutionState enum value
            ValueError: If state is a dict object (Issue #305 root cause)
        """
        # CRITICAL VALIDATION: Issue #305 - Prevent dict objects being passed as state
        if not isinstance(state, ExecutionState):
            if isinstance(state, dict):
                # Specific error for the exact Issue #305 pattern
                raise ValueError(
                    f"🚨 Issue #305 CRITICAL: Dict object passed as ExecutionState: {state}. "
                    f"This was causing \"'dict' object has no attribute 'value'\" errors. "
                    f"Use ExecutionState enum instead: ExecutionState.COMPLETED, ExecutionState.FAILED, etc. "
                    f"Agent execution ID: {execution_id}"
                )
            else:
                # General type error for other invalid types
                raise TypeError(
                    f"Expected ExecutionState enum, got {type(state).__name__}: {state}. "
                    f"Valid ExecutionState values: {[s.value for s in ExecutionState]}. "
                    f"Agent execution ID: {execution_id}"
                )
        
        record = self._executions.get(execution_id)
        if not record:
            # BACKWARD COMPATIBILITY: Auto-create execution record if it doesn't exist
            # This maintains compatibility with legacy code patterns where update_execution_state
            # could be called without explicitly creating the execution first
            logger.warning(f"Auto-creating execution record for {execution_id} (backward compatibility)")
            now = datetime.now(timezone.utc)
            self._executions[execution_id] = ExecutionRecord(
                execution_id=execution_id,
                agent_name="unknown",  # Default when auto-created
                thread_id="unknown",
                user_id="unknown",
                state=ExecutionState.PENDING,
                started_at=now,
                last_heartbeat=now,
                updated_at=now,
                timeout_seconds=int(self.timeout_config.agent_execution_timeout)
            )
            record = self._executions[execution_id]
            self._active_executions.add(execution_id)
        
        # Don't update terminal states
        if record.is_terminal:
            logger.warning(f"Cannot update terminal execution {execution_id}")
            return False
        
        now = datetime.now(timezone.utc)
        record.state = state
        record.updated_at = now
        record.last_heartbeat = now
        
        if error:
            record.error = error
        if result:
            record.result = result
        
        # Handle terminal states
        if state in [ExecutionState.COMPLETED, ExecutionState.FAILED,
                    ExecutionState.TIMEOUT, ExecutionState.DEAD, 
                    ExecutionState.CANCELLED]:
            record.completed_at = now
            self._active_executions.discard(execution_id)
            
            # Update metrics
            if state == ExecutionState.COMPLETED:
                self._successful_executions += 1
            elif state == ExecutionState.FAILED:
                self._failed_executions += 1
            elif state == ExecutionState.TIMEOUT:
                self._timeout_executions += 1
            elif state == ExecutionState.DEAD:
                self._dead_executions += 1
        
        logger.info(f"Updated execution {execution_id} to state {state.value}")
        return True
    
    def get_execution_state(self, execution_id: str) -> Optional[ExecutionState]:
        """
        Get current execution state.
        
        Args:
            execution_id: The execution ID to query
            
        Returns:
            ExecutionState enum value if execution exists, None otherwise
        """
        record = self._executions.get(execution_id)
        return record.state if record else None
    
    def heartbeat(self, execution_id: str) -> bool:
        """
        Update heartbeat for execution.
        
        Returns:
            True if successful, False if execution not found or terminal
        """
        record = self._executions.get(execution_id)
        if not record or record.is_terminal:
            return False
        
        record.last_heartbeat = datetime.now(timezone.utc)
        record.heartbeat_count += 1
        
        # Transition to RUNNING if still STARTING
        if record.state == ExecutionState.STARTING:
            record.state = ExecutionState.RUNNING
            record.updated_at = datetime.now(timezone.utc)
        
        return True
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get execution record by ID"""
        return self._executions.get(execution_id)
    
    def get_active_executions(self) -> List[ExecutionRecord]:
        """Get all active executions"""
        return [
            self._executions[exec_id]
            for exec_id in self._active_executions
            if exec_id in self._executions
        ]
    
    def get_executions_by_agent(self, agent_name: str) -> List[ExecutionRecord]:
        """Get all executions for an agent"""
        return [
            self._executions[exec_id]
            for exec_id in self._executions_by_agent.get(agent_name, set())
            if exec_id in self._executions
        ]
    
    def get_executions_by_thread(self, thread_id: str) -> List[ExecutionRecord]:
        """Get all executions for a thread"""
        return [
            self._executions[exec_id]
            for exec_id in self._executions_by_thread.get(thread_id, set())
            if exec_id in self._executions
        ]
    
    def detect_dead_executions(self) -> List[ExecutionRecord]:
        """Detect all dead executions"""
        dead_executions = []
        
        for exec_id in list(self._active_executions):
            record = self._executions.get(exec_id)
            if not record:
                continue
            
            # Check for death conditions
            if record.is_dead(self.heartbeat_timeout):
                dead_executions.append(record)
                logger.warning(f"Detected dead execution: {exec_id}")
            elif record.is_timed_out():
                dead_executions.append(record)
                logger.warning(f"Detected timed-out execution: {exec_id}")
        
        return dead_executions
    
    def register_death_callback(self, callback):
        """Register callback for agent death detection"""
        self._death_callbacks.append(callback)
    
    def register_timeout_callback(self, callback):
        """Register callback for execution timeout"""
        self._timeout_callbacks.append(callback)
    
    async def _monitor_executions(self):
        """Background task to monitor executions"""
        logger.info("Started execution monitoring loop")
        
        while True:
            try:
                # Check for dead/timed-out executions
                dead_executions = self.detect_dead_executions()
                
                for record in dead_executions:
                    if record.is_dead(self.heartbeat_timeout):
                        # Mark as dead
                        self.update_execution_state(
                            record.execution_id,
                            ExecutionState.DEAD,
                            error=f"No heartbeat for {record.time_since_heartbeat.total_seconds():.1f}s"
                        )
                        
                        # Trigger callbacks
                        for callback in self._death_callbacks:
                            try:
                                await callback(record)
                            except Exception as e:
                                logger.error(f"Death callback error: {e}")
                    
                    elif record.is_timed_out():
                        # Mark as timed out
                        self.update_execution_state(
                            record.execution_id,
                            ExecutionState.TIMEOUT,
                            error=f"Execution exceeded {record.timeout_seconds}s timeout"
                        )
                        
                        # Trigger callbacks
                        for callback in self._timeout_callbacks:
                            try:
                                await callback(record)
                            except Exception as e:
                                logger.error(f"Timeout callback error: {e}")
                
                # Cleanup old executions periodically
                await self._cleanup_old_executions()
                
                # Wait before next check
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_old_executions(self):
        """Clean up old completed executions"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.cleanup_interval)
        
        to_remove = []
        for exec_id, record in self._executions.items():
            if record.is_terminal and record.completed_at and record.completed_at < cutoff:
                to_remove.append(exec_id)
        
        for exec_id in to_remove:
            record = self._executions.pop(exec_id, None)
            if record:
                self._executions_by_agent[record.agent_name].discard(exec_id)
                self._executions_by_thread[record.thread_id].discard(exec_id)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old executions")
    
    def _initialize_phase_transition_rules(self) -> Dict[Optional[AgentExecutionPhase], List[AgentExecutionPhase]]:
        """Initialize valid phase transition rules (consolidated from AgentStateTracker)."""
        return {
            None: [AgentExecutionPhase.CREATED],
            AgentExecutionPhase.CREATED: [
                AgentExecutionPhase.WEBSOCKET_SETUP,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.WEBSOCKET_SETUP: [
                AgentExecutionPhase.CONTEXT_VALIDATION,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.CONTEXT_VALIDATION: [
                AgentExecutionPhase.STARTING,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.STARTING: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.THINKING: [
                AgentExecutionPhase.TOOL_PREPARATION,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.TOOL_PREPARATION: [
                AgentExecutionPhase.TOOL_EXECUTION,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.LLM_INTERACTION: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.TOOL_EXECUTION,
                AgentExecutionPhase.RESULT_PROCESSING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT,
                AgentExecutionPhase.CIRCUIT_BREAKER_OPEN
            ],
            AgentExecutionPhase.TOOL_EXECUTION: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.RESULT_PROCESSING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.RESULT_PROCESSING: [
                AgentExecutionPhase.COMPLETING,
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.COMPLETING: [
                AgentExecutionPhase.COMPLETED,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ]
        }
    
    # ========== CONSOLIDATED STATE MANAGEMENT METHODS (from AgentStateTracker) ==========
    
    def get_agent_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current agent state (consolidated from AgentStateTracker)."""
        record = self._executions.get(execution_id)
        if not record:
            return None
        
        return {
            "execution_id": execution_id,
            "agent_name": record.agent_name,
            "user_id": record.user_id,
            "thread_id": record.thread_id,
            "state": record.state.value,
            "current_phase": record.current_phase.value,
            "started_at": record.started_at.isoformat(),
            "last_heartbeat": record.last_heartbeat.isoformat(),
            "total_duration_ms": record.get_total_duration_ms(),
            "current_phase_duration_ms": record.get_current_phase_duration_ms(),
            "phase_count": len(record.phase_history),
            "warning_count": record.warning_count,
            "error_count": record.error_count,
            "metadata": record.metadata
        }
    
    def set_agent_state(self, execution_id: str, state_updates: Dict[str, Any]) -> bool:
        """Set agent state (consolidated from AgentStateTracker)."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        # Update allowed fields
        if "warning_count" in state_updates:
            record.warning_count = state_updates["warning_count"]
        if "error_count" in state_updates:
            record.error_count = state_updates["error_count"]
        if "metadata" in state_updates:
            record.metadata.update(state_updates["metadata"])
        
        record.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated agent state for {execution_id}")
        return True
    
    async def transition_state(self, 
                              execution_id: str, 
                              new_phase: AgentExecutionPhase,
                              metadata: Optional[Dict[str, Any]] = None,
                              websocket_manager: Optional[Any] = None) -> bool:
        """Transition agent to new phase (consolidated from AgentStateTracker)."""
        record = self._executions.get(execution_id)
        if not record:
            logger.error(f"Unknown execution ID: {execution_id}")
            return False
        
        current_time = datetime.now(timezone.utc)
        
        # Validate transition
        if not self.validate_state_transition(record.current_phase, new_phase):
            logger.warning(
                f"Invalid phase transition for {execution_id}: "
                f"{record.current_phase} -> {new_phase}"
            )
            # Allow the transition but log as warning
        
        # Calculate duration of previous phase
        duration_ms = (current_time - record.updated_at).total_seconds() * 1000
        
        # Create transition record
        transition = PhaseTransition(
            from_phase=record.current_phase,
            to_phase=new_phase,
            timestamp=current_time,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Update record
        record.current_phase = new_phase
        record.updated_at = current_time
        record.last_heartbeat = current_time
        record.phase_history.append(transition)
        
        # Emit WebSocket event if manager available
        websocket_event_sent = False
        if websocket_manager:
            try:
                await self._emit_phase_event(record, transition, websocket_manager)
                transition.websocket_event_sent = True
                websocket_event_sent = True
            except Exception as e:
                logger.error(f"Failed to emit WebSocket event for phase transition: {e}")
        
        logger.info(
            f"Phase transition {execution_id}: {transition.from_phase} -> {new_phase} "
            f"(duration: {duration_ms:.1f}ms, websocket: {websocket_event_sent})"
        )
        
        return True
    
    def validate_state_transition(self, 
                                 current_phase: Optional[AgentExecutionPhase], 
                                 new_phase: AgentExecutionPhase) -> bool:
        """Validate if phase transition is allowed (consolidated from AgentStateTracker)."""
        valid_next_phases = self._phase_transition_rules.get(current_phase, [])
        return new_phase in valid_next_phases
    
    def get_state_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get state transition history (consolidated from AgentStateTracker)."""
        record = self._executions.get(execution_id)
        if not record:
            return []
        
        return [
            {
                "from_phase": transition.from_phase.value if transition.from_phase else None,
                "to_phase": transition.to_phase.value,
                "timestamp": transition.timestamp.isoformat(),
                "duration_ms": transition.duration_ms,
                "metadata": transition.metadata,
                "websocket_event_sent": transition.websocket_event_sent
            }
            for transition in record.phase_history
        ]
    
    def cleanup_state(self, execution_id: str) -> bool:
        """Clean up state for completed execution (consolidated from AgentStateTracker)."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        if not record.is_terminal:
            logger.warning(f"Cannot cleanup non-terminal execution: {execution_id}")
            return False
        
        # Move to completed history
        self._completed_executions.append(record)
        if len(self._completed_executions) > self._max_completed_history:
            self._completed_executions = self._completed_executions[-self._max_completed_history:]
        
        # Remove from active tracking
        self._executions.pop(execution_id, None)
        self._active_executions.discard(execution_id)
        self._executions_by_agent[record.agent_name].discard(execution_id)
        self._executions_by_thread[record.thread_id].discard(execution_id)
        
        logger.info(f"Cleaned up state for execution: {execution_id}")
        return True
    
    async def _emit_phase_event(self, 
                               record: ExecutionRecord, 
                               transition: PhaseTransition,
                               websocket_manager: Any) -> None:
        """Emit WebSocket event for phase transition (consolidated from AgentStateTracker)."""
        # Map phases to appropriate WebSocket events
        phase_to_event = {
            AgentExecutionPhase.STARTING: ("agent_started", "Agent is starting execution"),
            AgentExecutionPhase.THINKING: ("agent_thinking", f"Agent is thinking... (step {len(record.phase_history)})"),
            AgentExecutionPhase.TOOL_PREPARATION: ("agent_thinking", "Preparing tools for execution..."),
            AgentExecutionPhase.LLM_INTERACTION: ("agent_thinking", "Interacting with AI language model..."),
            AgentExecutionPhase.TOOL_EXECUTION: ("tool_executing", "Executing tools..."),
            AgentExecutionPhase.RESULT_PROCESSING: ("agent_thinking", "Processing results..."),
            AgentExecutionPhase.COMPLETING: ("agent_thinking", "Finalizing response..."),
            AgentExecutionPhase.COMPLETED: ("agent_completed", "Agent execution completed successfully"),
            AgentExecutionPhase.FAILED: ("agent_error", "Agent execution failed"),
            AgentExecutionPhase.TIMEOUT: ("agent_error", "Agent execution timed out"),
            AgentExecutionPhase.CIRCUIT_BREAKER_OPEN: ("agent_error", "Service temporarily unavailable")
        }
        
        event_info = phase_to_event.get(transition.to_phase)
        if not event_info:
            return
        
        event_type, message = event_info
        
        try:
            if event_type == "agent_started":
                await websocket_manager.notify_agent_started(
                    run_id=record.thread_id,  # Use thread_id as run_id
                    agent_name=record.agent_name,
                    context={
                        "phase": transition.to_phase.value,
                        "total_duration_ms": record.get_total_duration_ms(),
                        "metadata": transition.metadata
                    }
                )
            elif event_type == "agent_thinking":
                await websocket_manager.notify_agent_thinking(
                    run_id=record.thread_id,
                    agent_name=record.agent_name,
                    reasoning=message,
                    step_number=len(record.phase_history)
                )
            elif event_type == "tool_executing":
                await websocket_manager.notify_tool_executing(
                    run_id=record.thread_id,
                    agent_name=record.agent_name,
                    tool_name="execution_tools",
                    parameters=transition.metadata
                )
            elif event_type == "agent_completed":
                await websocket_manager.notify_agent_completed(
                    run_id=record.thread_id,
                    agent_name=record.agent_name,
                    result={
                        "success": True,
                        "total_duration_ms": record.get_total_duration_ms(),
                        "phase_count": len(record.phase_history),
                        "warnings": record.warning_count,
                        "metadata": record.metadata
                    },
                    execution_time_ms=int(record.get_total_duration_ms())
                )
            elif event_type == "agent_error":
                await websocket_manager.notify_agent_error(
                    run_id=record.thread_id,
                    agent_name=record.agent_name,
                    error=message,
                    error_context={
                        "phase": transition.to_phase.value,
                        "total_duration_ms": record.get_total_duration_ms(),
                        "metadata": transition.metadata
                    }
                )
            
            logger.debug(f"Emitted {event_type} event for {record.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to emit {event_type} event: {e}")
            raise
    
    # ========== CONSOLIDATED TIMEOUT MANAGEMENT METHODS (from AgentExecutionTimeoutManager) ==========
    
    def set_timeout(self, execution_id: str, timeout_config: TimeoutConfig) -> bool:
        """Set timeout configuration for execution (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        record.timeout_config = timeout_config
        record.timeout_seconds = int(timeout_config.agent_execution_timeout)
        record.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Set timeout config for {execution_id}: {timeout_config.agent_execution_timeout}s")
        return True
    
    def check_timeout(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Check timeout status for execution (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            return None
        
        current_time = time.time()
        elapsed = current_time - record.started_at.timestamp()
        
        timeout_config = record.timeout_config or self.timeout_config
        is_timed_out = elapsed > timeout_config.agent_execution_timeout
        
        return {
            "execution_id": execution_id,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout_config.agent_execution_timeout,
            "is_timed_out": is_timed_out,
            "circuit_breaker_state": record.circuit_breaker_state.value,
            "circuit_breaker_failures": record.circuit_breaker_failures,
            "time_until_timeout": max(0, timeout_config.agent_execution_timeout - elapsed)
        }
    
    def register_circuit_breaker(self, execution_id: str) -> bool:
        """Register circuit breaker for execution (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        record.circuit_breaker_state = CircuitBreakerState.CLOSED
        record.circuit_breaker_failures = 0
        record.last_failure_time = 0.0
        record.next_attempt_time = 0.0
        
        logger.info(f"Registered circuit breaker for {execution_id}")
        return True
    
    def circuit_breaker_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            return None
        
        current_time = time.time()
        timeout_config = record.timeout_config or self.timeout_config
        
        return {
            "execution_id": execution_id,
            "state": record.circuit_breaker_state.value,
            "failure_count": record.circuit_breaker_failures,
            "failure_threshold": timeout_config.failure_threshold,
            "last_failure_time": record.last_failure_time,
            "next_attempt_time": record.next_attempt_time,
            "is_open": record.is_circuit_breaker_open(),
            "can_retry": record.should_retry(timeout_config.max_retries),
            "recovery_timeout": timeout_config.recovery_timeout
        }
    
    def reset_circuit_breaker(self, execution_id: str) -> bool:
        """Reset circuit breaker to closed state (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        record.circuit_breaker_state = CircuitBreakerState.CLOSED
        record.circuit_breaker_failures = 0
        record.last_failure_time = 0.0
        record.next_attempt_time = 0.0
        
        logger.info(f"Reset circuit breaker for {execution_id}")
        return True
    
    async def execute_with_circuit_breaker(self, 
                                          execution_id: str,
                                          func: Callable[[], T], 
                                          operation_name: str = "operation") -> T:
        """Execute function with circuit breaker protection (consolidated from AgentExecutionTimeoutManager)."""
        record = self._executions.get(execution_id)
        if not record:
            raise ValueError(f"Unknown execution ID: {execution_id}")
        
        timeout_config = record.timeout_config or self.timeout_config
        current_time = time.time()
        
        # Check circuit breaker state
        if record.circuit_breaker_state == CircuitBreakerState.OPEN:
            if current_time < record.next_attempt_time:
                logger.warning(f"Circuit breaker OPEN for {execution_id} - blocking request")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {operation_name}. "
                    f"Next attempt allowed in {record.next_attempt_time - current_time:.1f}s"
                )
            else:
                # Transition to half-open
                record.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker transition to HALF_OPEN for {execution_id}")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(func(), timeout=timeout_config.llm_api_timeout)
            
            # Success - update circuit breaker state
            await self._on_circuit_breaker_success(execution_id, operation_name)
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Operation {operation_name} timed out for {execution_id}")
            await self._on_circuit_breaker_failure(execution_id, operation_name, "timeout")
            raise TimeoutError(f"Operation {operation_name} timed out")
            
        except Exception as e:
            logger.error(f"Operation {operation_name} failed for {execution_id}: {e}")
            await self._on_circuit_breaker_failure(execution_id, operation_name, str(e))
            raise
    
    async def _on_circuit_breaker_success(self, execution_id: str, operation_name: str) -> None:
        """Handle successful circuit breaker operation."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        timeout_config = record.timeout_config or self.timeout_config
        
        if record.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            # For half-open, we need multiple successes before closing
            success_count = getattr(record, '_circuit_breaker_success_count', 0) + 1
            record._circuit_breaker_success_count = success_count
            
            logger.debug(f"Success {success_count}/{timeout_config.success_threshold} for {execution_id}")
            
            if success_count >= timeout_config.success_threshold:
                # Close the circuit
                record.circuit_breaker_state = CircuitBreakerState.CLOSED
                record.circuit_breaker_failures = 0
                record._circuit_breaker_success_count = 0
                logger.info(f"Circuit breaker CLOSED for {execution_id} - normal operation resumed")
        else:
            # Reset failure count on success in closed state
            record.circuit_breaker_failures = 0
    
    async def _on_circuit_breaker_failure(self, execution_id: str, operation_name: str, error: str) -> None:
        """Handle failed circuit breaker operation."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        timeout_config = record.timeout_config or self.timeout_config
        record.circuit_breaker_failures += 1
        record.last_failure_time = time.time()
        
        if record.circuit_breaker_failures >= timeout_config.failure_threshold:
            # Open the circuit
            record.circuit_breaker_state = CircuitBreakerState.OPEN
            record.next_attempt_time = record.last_failure_time + timeout_config.recovery_timeout
            logger.critical(
                f"Circuit breaker OPENED for {execution_id} after {record.circuit_breaker_failures} failures. "
                f"Next attempt in {timeout_config.recovery_timeout}s"
            )
        else:
            logger.warning(
                f"Failure {record.circuit_breaker_failures}/{timeout_config.failure_threshold} for {execution_id}: {error}"
            )
    
    # ========== CONSOLIDATED EXECUTION CREATION METHODS ==========
    
    def create_execution_with_full_context(self,
                                          agent_name: str,
                                          user_context: Dict[str, Any],
                                          timeout_config: Optional[Dict[str, Any]] = None,
                                          initial_state: str = "PENDING") -> str:
        """Create execution with full consolidated context (integration method)."""
        # Extract context
        user_id = user_context.get('user_id', 'unknown')
        thread_id = user_context.get('thread_id', 'unknown')
        
        # Build timeout config
        if timeout_config:
            config = TimeoutConfig(
                agent_execution_timeout=timeout_config.get('timeout_seconds', 25.0),
                llm_api_timeout=timeout_config.get('llm_timeout', 15.0),
                failure_threshold=timeout_config.get('failure_threshold', 3),
                recovery_timeout=timeout_config.get('recovery_timeout', 30.0),
                success_threshold=timeout_config.get('success_threshold', 2),
                max_retries=timeout_config.get('max_retries', 2)
            )
        else:
            config = self.timeout_config
        
        # Create execution
        execution_id = self.create_execution(
            agent_name=agent_name,
            thread_id=thread_id,
            user_id=user_id,
            timeout_seconds=int(config.agent_execution_timeout),
            metadata=user_context.get('metadata', {})
        )
        
        # Set timeout config
        record = self._executions[execution_id]
        record.timeout_config = config
        
        # Register circuit breaker
        self.register_circuit_breaker(execution_id)
        
        # Set initial state if provided
        if initial_state and hasattr(ExecutionState, initial_state):
            initial_enum_state = getattr(ExecutionState, initial_state)
            record.state = initial_enum_state
        
        logger.info(f"Created execution with full context: {execution_id}")
        return execution_id
    
    def get_execution_with_full_context(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution with full consolidated context (integration method)."""
        record = self._executions.get(execution_id)
        if not record:
            return None
        
        timeout_status = self.check_timeout(execution_id)
        circuit_breaker_status = self.circuit_breaker_status(execution_id)
        state_info = self.get_agent_state(execution_id)
        state_history = self.get_state_history(execution_id)
        
        return {
            "execution_id": execution_id,
            "agent_name": record.agent_name,
            "user_id": record.user_id,
            "thread_id": record.thread_id,
            "state": record.state.value.upper(),  # Return uppercase for test compatibility
            "timeout_seconds": record.timeout_seconds,
            "metadata": record.metadata,
            "state_info": state_info,
            "timeout_status": timeout_status,
            "circuit_breaker_status": circuit_breaker_status,
            "state_history": state_history,
            "consolidated": True,
            "created_with_ssot": True
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        active_count = len(self._active_executions)
        
        return {
            "total_executions": self._total_executions,
            "active_executions": active_count,
            "successful_executions": self._successful_executions,
            "failed_executions": self._failed_executions,
            "timeout_executions": self._timeout_executions,
            "dead_executions": self._dead_executions,
            "success_rate": (
                self._successful_executions / self._total_executions 
                if self._total_executions > 0 else 0
            ),
            "failure_rate": (
                (self._failed_executions + self._timeout_executions + self._dead_executions) / 
                self._total_executions if self._total_executions > 0 else 0
            )
        }


# Global singleton instance
_tracker_instance: Optional[AgentExecutionTracker] = None


def get_execution_tracker() -> AgentExecutionTracker:
    """Get the global execution tracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = AgentExecutionTracker()
    return _tracker_instance


async def initialize_tracker():
    """Initialize and start the execution tracker"""
    tracker = get_execution_tracker()
    await tracker.start_monitoring()
    logger.info("Initialized agent execution tracker")
    return tracker


async def shutdown_tracker():
    """Shutdown the execution tracker"""
    tracker = get_execution_tracker()
    await tracker.stop_monitoring()
    logger.info("Shutdown agent execution tracker")


# COMPATIBILITY ALIAS: Export AgentExecutionTracker as ExecutionTracker for backward compatibility
ExecutionTracker = AgentExecutionTracker


# COMPATIBILITY FUNCTION: get_agent_state_tracker for backward compatibility
def get_agent_state_tracker() -> AgentExecutionTracker:
    """
    Get the global agent state tracker instance.
    
    This is a compatibility function that returns the same instance as get_execution_tracker().
    Added to support legacy imports that expect this function name.
    
    Returns:
        AgentExecutionTracker: The global execution tracker instance
    """
    return get_execution_tracker()