"""
Agent Execution Registry - Minimal implementation for startup validation.

This module provides the basic AgentExecutionRegistry class required by startup validator.
Created as a minimal stub to resolve missing import errors during startup.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Reliability
- Value Impact: Enables successful service startup and health checks
- Strategic Impact: Foundation for agent orchestration and execution tracking
"""

import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import threading

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentExecution:
    """Agent execution record."""
    execution_id: str
    agent_type: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class AgentExecutionRegistry:
    """
    Minimal agent execution registry for startup validation.
    
    Provides basic tracking of agent executions and health checks.
    This is a simplified implementation to satisfy startup validator requirements.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._executions: Dict[str, AgentExecution] = {}
        self._lock = threading.RLock()
        self._agent_types: Set[str] = set()
        logger.info("AgentExecutionRegistry initialized (minimal implementation)")
    
    def register_execution(self, execution_id: str, agent_type: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Register a new agent execution."""
        with self._lock:
            if execution_id in self._executions:
                return False
            
            execution = AgentExecution(
                execution_id=execution_id,
                agent_type=agent_type,
                context=context or {}
            )
            
            self._executions[execution_id] = execution
            self._agent_types.add(agent_type)
            logger.debug(f"Registered execution {execution_id} for agent type {agent_type}")
            return True
    
    def update_status(self, execution_id: str, status: ExecutionStatus, error: Optional[str] = None) -> bool:
        """Update execution status."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return False
            
            execution.status = status
            if error:
                execution.error = error
            
            current_time = time.time()
            if status == ExecutionStatus.RUNNING and not execution.started_at:
                execution.started_at = current_time
            elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                execution.completed_at = current_time
            
            logger.debug(f"Updated execution {execution_id} to status {status.value}")
            return True
    
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Get execution record."""
        return self._executions.get(execution_id)
    
    def get_executions_by_status(self, status: ExecutionStatus) -> List[AgentExecution]:
        """Get executions by status."""
        with self._lock:
            return [ex for ex in self._executions.values() if ex.status == status]
    
    def get_active_executions(self) -> List[AgentExecution]:
        """Get currently active (pending/running) executions."""
        active_statuses = {ExecutionStatus.PENDING, ExecutionStatus.RUNNING}
        with self._lock:
            return [ex for ex in self._executions.values() if ex.status in active_statuses]
    
    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Clean up old completed executions."""
        current_time = time.time()
        cleanup_count = 0
        
        with self._lock:
            completed_statuses = {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}
            to_remove = []
            
            for execution_id, execution in self._executions.items():
                if (execution.status in completed_statuses and
                    execution.completed_at and 
                    current_time - execution.completed_at > max_age_seconds):
                    to_remove.append(execution_id)
            
            for execution_id in to_remove:
                del self._executions[execution_id]
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} completed executions")
        
        return cleanup_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            stats = {
                'total_executions': len(self._executions),
                'active_executions': len(self.get_active_executions()),
                'agent_types': len(self._agent_types),
                'status_counts': {}
            }
            
            for status in ExecutionStatus:
                count = len(self.get_executions_by_status(status))
                stats['status_counts'][status.value] = count
            
            return stats
    
    def is_healthy(self) -> bool:
        """Check if registry is healthy (for startup validation)."""
        # Basic health check - registry is healthy if it's initialized
        return True
    
    def clear(self) -> None:
        """Clear all executions (use with caution)."""
        with self._lock:
            self._executions.clear()
            self._agent_types.clear()
            logger.warning("AgentExecutionRegistry cleared")


# Global registry instance for backward compatibility
_global_registry: Optional[AgentExecutionRegistry] = None


def get_agent_execution_registry() -> AgentExecutionRegistry:
    """Get global agent execution registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentExecutionRegistry()
    return _global_registry


def create_agent_execution_registry() -> AgentExecutionRegistry:
    """Create a new agent execution registry instance."""
    return AgentExecutionRegistry()