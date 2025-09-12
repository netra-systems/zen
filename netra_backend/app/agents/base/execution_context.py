"""
Execution Context Module

Provides context management for agent execution.
Tracks execution state, metadata, and resource usage.
"""

import logging
import time
import uuid
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum
import threading

from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionMetadata:
    """Metadata for execution tracking"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def update_duration(self) -> None:
        """Update duration based on start and end times"""
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time


@dataclass
class ResourceUsage:
    """Resource usage tracking"""
    cpu_time: float = 0.0
    memory_peak: int = 0
    network_requests: int = 0
    database_queries: int = 0
    llm_tokens: int = 0
    cost_estimate: float = 0.0


class ExecutionContext:
    """
    Execution context for agent operations.
    
    Provides context management, tracking, and resource monitoring
    for agent execution within the Netra platform.
    """
    
    def __init__(self, 
                 execution_id: Optional[str] = None,
                 metadata: Optional[ExecutionMetadata] = None):
        self.execution_id = execution_id or UnifiedIdGenerator.generate_agent_execution_id(
            agent_type=getattr(self, 'agent_type', 'unknown'), 
            user_id=getattr(self, 'user_id', 'system')
        )
        self.metadata = metadata or ExecutionMetadata()
        self.status = ExecutionStatus.PENDING
        self.resource_usage = ResourceUsage()
        
        # Context tracking
        self._context_data: Dict[str, Any] = {}
        self._error_info: Optional[Dict[str, Any]] = None
        self._logs: List[str] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.debug(f"ExecutionContext created: {self.execution_id}")
    
    def start_execution(self) -> None:
        """Mark execution as started"""
        with self._lock:
            self.status = ExecutionStatus.RUNNING
            self.metadata.start_time = time.time()
            self._add_log(f"Execution started: {self.execution_id}")
    
    def complete_execution(self, success: bool = True) -> None:
        """Mark execution as completed"""
        with self._lock:
            self.metadata.end_time = time.time()
            self.metadata.update_duration()
            
            if success:
                self.status = ExecutionStatus.COMPLETED
                self._add_log(f"Execution completed successfully: {self.execution_id}")
            else:
                self.status = ExecutionStatus.FAILED
                self._add_log(f"Execution failed: {self.execution_id}")
    
    def fail_execution(self, error: Exception) -> None:
        """Mark execution as failed with error info"""
        with self._lock:
            self.status = ExecutionStatus.FAILED
            self.metadata.end_time = time.time()
            self.metadata.update_duration()
            
            self._error_info = {
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': time.time()
            }
            
            self._add_log(f"Execution failed with error: {error}")
    
    def cancel_execution(self) -> None:
        """Mark execution as cancelled"""
        with self._lock:
            self.status = ExecutionStatus.CANCELLED
            self.metadata.end_time = time.time()
            self.metadata.update_duration()
            self._add_log(f"Execution cancelled: {self.execution_id}")
    
    def timeout_execution(self) -> None:
        """Mark execution as timed out"""
        with self._lock:
            self.status = ExecutionStatus.TIMEOUT
            self.metadata.end_time = time.time()
            self.metadata.update_duration()
            self._add_log(f"Execution timed out: {self.execution_id}")
    
    def set_context_data(self, key: str, value: Any) -> None:
        """Set context data"""
        with self._lock:
            self._context_data[key] = value
    
    def get_context_data(self, key: str, default: Any = None) -> Any:
        """Get context data"""
        with self._lock:
            return self._context_data.get(key, default)
    
    def update_resource_usage(self, **kwargs) -> None:
        """Update resource usage metrics"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.resource_usage, key):
                    if key in ['network_requests', 'database_queries', 'llm_tokens']:
                        # Increment counters
                        current_value = getattr(self.resource_usage, key)
                        setattr(self.resource_usage, key, current_value + value)
                    else:
                        # Set absolute values
                        setattr(self.resource_usage, key, value)
    
    def _add_log(self, message: str) -> None:
        """Add log entry"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self._logs.append(log_entry)
        
        # Keep only last 100 log entries
        if len(self._logs) > 100:
            self._logs = self._logs[-100:]
    
    def get_status(self) -> ExecutionStatus:
        """Get current execution status"""
        return self.status
    
    def is_running(self) -> bool:
        """Check if execution is currently running"""
        return self.status == ExecutionStatus.RUNNING
    
    def is_completed(self) -> bool:
        """Check if execution is completed (success or failure)"""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        with self._lock:
            return {
                'execution_id': self.execution_id,
                'status': self.status.value,
                'metadata': {
                    'user_id': self.metadata.user_id,
                    'session_id': self.metadata.session_id,
                    'request_id': self.metadata.request_id,
                    'agent_name': self.metadata.agent_name,
                    'tool_name': self.metadata.tool_name,
                    'start_time': self.metadata.start_time,
                    'end_time': self.metadata.end_time,
                    'duration': self.metadata.duration,
                    'custom_data': self.metadata.custom_data.copy()
                },
                'resource_usage': {
                    'cpu_time': self.resource_usage.cpu_time,
                    'memory_peak': self.resource_usage.memory_peak,
                    'network_requests': self.resource_usage.network_requests,
                    'database_queries': self.resource_usage.database_queries,
                    'llm_tokens': self.resource_usage.llm_tokens,
                    'cost_estimate': self.resource_usage.cost_estimate
                },
                'error_info': self._error_info,
                'log_count': len(self._logs),
                'context_keys': list(self._context_data.keys())
            }
    
    def get_logs(self, limit: Optional[int] = None) -> List[str]:
        """Get execution logs"""
        with self._lock:
            if limit:
                return self._logs[-limit:]
            return self._logs.copy()
    
    def clear_logs(self) -> None:
        """Clear execution logs"""
        with self._lock:
            self._logs.clear()


class ExecutionContextManager:
    """
    Manager for execution contexts.
    
    Provides context lifecycle management and tracking
    across multiple executions.
    """
    
    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
        self._lock = threading.RLock()
        logger.info("ExecutionContextManager initialized")
    
    def create_context(self, 
                      execution_id: Optional[str] = None,
                      metadata: Optional[ExecutionMetadata] = None) -> ExecutionContext:
        """Create a new execution context"""
        context = ExecutionContext(execution_id, metadata)
        
        with self._lock:
            self._contexts[context.execution_id] = context
        
        return context
    
    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context by ID"""
        with self._lock:
            return self._contexts.get(execution_id)
    
    def remove_context(self, execution_id: str) -> bool:
        """Remove execution context"""
        with self._lock:
            if execution_id in self._contexts:
                del self._contexts[execution_id]
                return True
            return False
    
    def get_active_contexts(self) -> List[ExecutionContext]:
        """Get all active (running) contexts"""
        with self._lock:
            return [
                context for context in self._contexts.values()
                if context.is_running()
            ]
    
    def get_all_contexts(self) -> List[ExecutionContext]:
        """Get all contexts"""
        with self._lock:
            return list(self._contexts.values())
    
    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Clean up completed contexts older than max_age_seconds"""
        current_time = time.time()
        removed_count = 0
        
        with self._lock:
            to_remove = []
            
            for execution_id, context in self._contexts.items():
                if (context.is_completed() and 
                    context.metadata.end_time and
                    current_time - context.metadata.end_time > max_age_seconds):
                    to_remove.append(execution_id)
            
            for execution_id in to_remove:
                del self._contexts[execution_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} completed execution contexts")
        
        return removed_count


# Global context manager
_context_manager = None


def get_context_manager() -> ExecutionContextManager:
    """Get global execution context manager"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ExecutionContextManager()
    return _context_manager


def create_execution_context(**kwargs) -> ExecutionContext:
    """Convenience function to create execution context"""
    return get_context_manager().create_context(**kwargs)


class AgentExecutionContext(ExecutionContext):
    """
    Agent-specific execution context.
    
    Extends ExecutionContext with agent-specific functionality
    and maintains backwards compatibility.
    """
    
    def __init__(self, 
                 execution_id: Optional[str] = None,
                 metadata: Optional[ExecutionMetadata] = None):
        super().__init__(execution_id, metadata)
        # Add timestamp for backwards compatibility
        self.timestamp = self.metadata.start_time or time.time()
        logger.debug(f"AgentExecutionContext created: {self.execution_id}")
    
    def update_timestamp(self) -> None:
        """Update timestamp to current time"""
        self.timestamp = time.time()
        if self.metadata.start_time is None:
            self.metadata.start_time = self.timestamp


def create_agent_execution_context(**kwargs) -> AgentExecutionContext:
    """Convenience function to create agent execution context"""
    return AgentExecutionContext(**kwargs)