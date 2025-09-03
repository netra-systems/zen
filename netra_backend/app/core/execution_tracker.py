"""
Execution Tracker for Agent Lifecycle Monitoring
=================================================
CRITICAL: This module tracks all agent executions to prevent silent deaths.

Problem Solved:
- Agents dying silently without detection
- No tracking of in-flight executions
- Health service reporting "healthy" for dead agents
- No timeout mechanisms for stuck agents

Solution:
- Track all agent executions with unique IDs
- Monitor execution duration and enforce timeouts
- Provide real-time execution state
- Enable recovery from agent deaths
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionState(Enum):
    """States an agent execution can be in."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DEAD = "dead"


@dataclass
class ExecutionRecord:
    """Track a single agent execution."""
    execution_id: UUID
    agent_name: str
    correlation_id: Optional[str]
    thread_id: Optional[str]
    user_id: Optional[str]
    start_time: float
    state: ExecutionState
    last_heartbeat: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    heartbeat_count: int = 0
    websocket_updates_sent: int = 0
    timeout_seconds: float = 30.0  # Default 30s timeout
    
    def duration(self) -> float:
        """Get execution duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def is_timeout(self) -> bool:
        """Check if execution has timed out."""
        return self.duration() > self.timeout_seconds and self.state == ExecutionState.RUNNING
    
    def is_dead(self, heartbeat_timeout: float = 10.0) -> bool:
        """Check if agent is dead (no heartbeat for heartbeat_timeout seconds)."""
        if self.state != ExecutionState.RUNNING:
            return False
        return (time.time() - self.last_heartbeat) > heartbeat_timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": str(self.execution_id),
            "agent_name": self.agent_name,
            "correlation_id": self.correlation_id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "state": self.state.value,
            "last_heartbeat": self.last_heartbeat,
            "end_time": self.end_time,
            "error": self.error,
            "heartbeat_count": self.heartbeat_count,
            "websocket_updates_sent": self.websocket_updates_sent,
            "duration": self.duration(),
            "is_timeout": self.is_timeout(),
            "is_dead": self.is_dead()
        }


class ExecutionTracker:
    """
    Track and monitor all agent executions.
    
    This is the CRITICAL component that prevents agent deaths from going undetected.
    """
    
    def __init__(self):
        self.executions: Dict[UUID, ExecutionRecord] = {}
        self.active_executions: Set[UUID] = set()
        self.failed_executions: List[UUID] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.recovery_callbacks: List[Any] = []
        self._lock = asyncio.Lock()
        self._persistence = None  # Lazy loaded to avoid circular imports
        
    async def start_monitoring(self):
        """Start the monitoring task that checks for dead/timeout agents."""
        if self.monitoring_task and not self.monitoring_task.done():
            logger.debug("Monitoring task already running")
            return
            
        self.monitoring_task = asyncio.create_task(self._monitor_executions())
        logger.info("Started execution monitoring")
        
        # Initialize persistence if not already done
        await self._ensure_persistence()
        
    async def stop_monitoring(self):
        """Stop the monitoring task."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Stopped execution monitoring")
        
        # Shutdown persistence
        if self._persistence:
            from netra_backend.app.core.trace_persistence import get_execution_persistence
            persistence = get_execution_persistence()
            await persistence.shutdown()
    
    async def _monitor_executions(self):
        """Monitor all executions for timeouts and deaths."""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                await self._check_executions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in execution monitoring: {e}")
    
    async def _check_executions(self):
        """Check all active executions for issues."""
        async with self._lock:
            for exec_id in list(self.active_executions):
                execution = self.executions.get(exec_id)
                if not execution:
                    continue
                
                # Check for timeout
                if execution.is_timeout():
                    logger.error(f"TIMEOUT: Agent {execution.agent_name} (exec_id={exec_id}) exceeded {execution.timeout_seconds}s")
                    await self._handle_timeout(execution)
                    
                # Check for death (no heartbeat)
                elif execution.is_dead():
                    logger.error(f"DEAD: Agent {execution.agent_name} (exec_id={exec_id}) no heartbeat for 10s")
                    await self._handle_death(execution)
    
    async def register_execution(
        self,
        agent_name: str,
        correlation_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout_seconds: float = 30.0
    ) -> UUID:
        """
        Register a new agent execution.
        
        Returns:
            UUID: Unique execution ID for tracking
        """
        exec_id = uuid4()
        
        async with self._lock:
            execution = ExecutionRecord(
                execution_id=exec_id,
                agent_name=agent_name,
                correlation_id=correlation_id,
                thread_id=thread_id,
                user_id=user_id,
                start_time=time.time(),
                state=ExecutionState.PENDING,
                last_heartbeat=time.time(),
                timeout_seconds=timeout_seconds
            )
            
            self.executions[exec_id] = execution
            self.active_executions.add(exec_id)
            
        logger.info(f"Registered execution: agent={agent_name}, exec_id={exec_id}, timeout={timeout_seconds}s")
        
        # Persist execution start
        await self._persist_execution_start(exec_id, {
            'agent_name': agent_name,
            'correlation_id': correlation_id,
            'thread_id': thread_id,
            'user_id': user_id,
            'timeout_seconds': timeout_seconds
        })
        
        return exec_id
    
    async def start_execution(self, exec_id: UUID):
        """Mark execution as running."""
        async with self._lock:
            if exec_id in self.executions:
                self.executions[exec_id].state = ExecutionState.RUNNING
                self.executions[exec_id].last_heartbeat = time.time()
                logger.debug(f"Started execution: {exec_id}")
                
        # Persist state change
        await self._persist_state_update(exec_id, ExecutionState.RUNNING.value)
    
    async def heartbeat(self, exec_id: UUID) -> bool:
        """
        Send heartbeat for an execution.
        
        Returns:
            bool: True if heartbeat recorded, False if execution not found
        """
        async with self._lock:
            if exec_id not in self.executions:
                logger.warning(f"Heartbeat for unknown execution: {exec_id}")
                return False
                
            execution = self.executions[exec_id]
            execution.last_heartbeat = time.time()
            execution.heartbeat_count += 1
            
            if execution.state != ExecutionState.RUNNING:
                logger.warning(f"Heartbeat for non-running execution: {exec_id} (state={execution.state})")
            
        return True
    
    async def complete_execution(
        self, 
        exec_id: UUID, 
        result: Any = None,
        error: Optional[str] = None
    ):
        """Mark execution as completed."""
        async with self._lock:
            if exec_id not in self.executions:
                logger.error(f"Attempting to complete unknown execution: {exec_id}")
                return
                
            execution = self.executions[exec_id]
            execution.end_time = time.time()
            execution.result = result
            execution.error = error
            
            if error:
                execution.state = ExecutionState.FAILED
                self.failed_executions.append(exec_id)
            else:
                execution.state = ExecutionState.COMPLETED
            
            self.active_executions.discard(exec_id)
            
            logger.info(
                f"Completed execution: agent={execution.agent_name}, "
                f"exec_id={exec_id}, duration={execution.duration():.2f}s, "
                f"state={execution.state.value}"
            )
            
        # Persist execution completion
        await self._persist_execution_complete(exec_id, execution)
    
    async def _handle_timeout(self, execution: ExecutionRecord):
        """Handle a timed-out execution."""
        execution.state = ExecutionState.TIMEOUT
        execution.end_time = time.time()
        execution.error = f"Execution timeout after {execution.timeout_seconds}s"
        
        self.active_executions.discard(execution.execution_id)
        self.failed_executions.append(execution.execution_id)
        
        # Persist timeout event
        await self._persist_execution_complete(execution.execution_id, execution)
        
        # Trigger recovery callbacks
        for callback in self.recovery_callbacks:
            try:
                await callback(execution)
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")
    
    async def _handle_death(self, execution: ExecutionRecord):
        """Handle a dead execution (no heartbeat)."""
        execution.state = ExecutionState.DEAD
        execution.end_time = time.time()
        execution.error = "Agent died - no heartbeat received"
        
        self.active_executions.discard(execution.execution_id)
        self.failed_executions.append(execution.execution_id)
        
        # Persist death event
        await self._persist_execution_complete(execution.execution_id, execution)
        
        # Trigger recovery callbacks
        for callback in self.recovery_callbacks:
            try:
                await callback(execution)
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")
    
    def get_execution(self, exec_id: UUID) -> Optional[ExecutionRecord]:
        """Get execution record by ID."""
        return self.executions.get(exec_id)
    
    def get_active_executions(self) -> List[ExecutionRecord]:
        """Get all active executions."""
        return [
            self.executions[exec_id] 
            for exec_id in self.active_executions 
            if exec_id in self.executions
        ]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of execution tracker."""
        active = self.get_active_executions()
        
        # Check for stuck executions
        stuck_executions = [
            e for e in active 
            if e.is_timeout() or e.is_dead()
        ]
        
        health_status = {
            "healthy": len(stuck_executions) == 0,
            "total_executions": len(self.executions),
            "active_executions": len(active),
            "failed_executions": len(self.failed_executions),
            "stuck_executions": len(stuck_executions),
            "monitoring_active": self.monitoring_task is not None and not self.monitoring_task.done()
        }
        
        if stuck_executions:
            health_status["stuck_details"] = [
                {
                    "exec_id": str(e.execution_id),
                    "agent": e.agent_name,
                    "duration": e.duration(),
                    "is_timeout": e.is_timeout(),
                    "is_dead": e.is_dead()
                }
                for e in stuck_executions
            ]
        
        return health_status
    
    def register_recovery_callback(self, callback):
        """Register a callback to be called when execution fails."""
        self.recovery_callbacks.append(callback)
    
    async def kill_execution(self, exec_id: UUID):
        """Force kill an execution."""
        async with self._lock:
            if exec_id in self.executions:
                execution = self.executions[exec_id]
                execution.state = ExecutionState.FAILED
                execution.end_time = time.time()
                execution.error = "Execution killed manually"
                self.active_executions.discard(exec_id)
                self.failed_executions.append(exec_id)
                logger.info(f"Killed execution: {exec_id}")
                
                # Persist kill event
                await self._persist_execution_complete(exec_id, execution)
    
    async def _ensure_persistence(self):
        """Ensure persistence is initialized."""
        if not self._persistence:
            try:
                from netra_backend.app.core.trace_persistence import get_execution_persistence
                self._persistence = get_execution_persistence()
                await self._persistence.ensure_started()
            except Exception as e:
                logger.warning(f"Failed to initialize persistence: {e}")
                self._persistence = None
    
    async def _persist_execution_start(self, exec_id: UUID, context: Dict[str, Any]):
        """Persist execution start event."""
        if not self._persistence:
            await self._ensure_persistence()
        
        if self._persistence:
            try:
                await self._persistence.write_execution_start(exec_id, context)
            except Exception as e:
                logger.error(f"Failed to persist execution start: {e}")
    
    async def _persist_state_update(self, exec_id: UUID, state: str):
        """Persist state update."""
        if not self._persistence:
            await self._ensure_persistence()
        
        if self._persistence:
            try:
                execution = self.executions.get(exec_id)
                metadata = {}
                if execution:
                    metadata = {
                        'agent_name': execution.agent_name,
                        'user_id': execution.user_id,
                        'thread_id': execution.thread_id
                    }
                await self._persistence.write_execution_update(exec_id, state, metadata)
            except Exception as e:
                logger.error(f"Failed to persist state update: {e}")
    
    async def _persist_execution_complete(self, exec_id: UUID, execution: ExecutionRecord):
        """Persist execution completion."""
        if not self._persistence:
            await self._ensure_persistence()
        
        if self._persistence:
            try:
                # Persist the full execution record
                await self._persistence.persist_execution_record(execution)
                
                # Also persist completion event
                result = {
                    'agent_name': execution.agent_name,
                    'user_id': execution.user_id,
                    'thread_id': execution.thread_id,
                    'state': execution.state.value,
                    'duration': execution.duration(),
                    'error': execution.error,
                    'heartbeat_count': execution.heartbeat_count,
                    'websocket_updates_sent': execution.websocket_updates_sent
                }
                await self._persistence.write_execution_complete(exec_id, result)
                
                # Persist performance metrics
                metrics = {
                    'agent_name': execution.agent_name,
                    'user_id': execution.user_id,
                    'duration_seconds': execution.duration(),
                    'heartbeat_count': execution.heartbeat_count,
                    'websocket_updates_sent': execution.websocket_updates_sent
                }
                await self._persistence.write_performance_metrics(exec_id, metrics)
            except Exception as e:
                logger.error(f"Failed to persist execution completion: {e}")
    
    async def collect_metrics(self, exec_id: UUID) -> Optional[Dict[str, Any]]:
        """Collect performance metrics for an execution."""
        execution = self.get_execution(exec_id)
        if not execution:
            return None
        
        return {
            'execution_id': str(exec_id),
            'agent_name': execution.agent_name,
            'duration_seconds': execution.duration(),
            'state': execution.state.value,
            'heartbeat_count': execution.heartbeat_count,
            'websocket_updates_sent': execution.websocket_updates_sent,
            'is_timeout': execution.is_timeout(),
            'is_dead': execution.is_dead()
        }


# Global instance for easy access
_execution_tracker: Optional[ExecutionTracker] = None


def get_execution_tracker() -> ExecutionTracker:
    """Get or create the global execution tracker."""
    global _execution_tracker
    if _execution_tracker is None:
        _execution_tracker = ExecutionTracker()
    return _execution_tracker


async def init_execution_tracker():
    """Initialize and start the execution tracker."""
    tracker = get_execution_tracker()
    await tracker.start_monitoring()
    logger.info("Execution tracker initialized and monitoring started")
    return tracker