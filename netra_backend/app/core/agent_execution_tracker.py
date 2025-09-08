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
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


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


class AgentExecutionTracker:
    """
    Central tracker for all agent executions.
    
    CRITICAL: This is the SSOT for agent execution state.
    All agent execution must be tracked through this module.
    """
    
    def __init__(self, 
                 heartbeat_timeout: int = 10,
                 execution_timeout: int = 15,  # WEBSOCKET OPTIMIZATION: Reduced from 30s to 15s for faster failure detection
                 cleanup_interval: int = 60):
        """
        Initialize execution tracker.
        
        Args:
            heartbeat_timeout: Seconds before considering agent dead (no heartbeat)
            execution_timeout: Default execution timeout in seconds
            cleanup_interval: Interval for cleaning up old executions
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.execution_timeout = execution_timeout
        self.cleanup_interval = cleanup_interval
        
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
        execution_id = f"exec_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
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
        
        Returns:
            True if successful, False if execution not found
        """
        record = self._executions.get(execution_id)
        if not record:
            return False
        
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