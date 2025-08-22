"""Execution context management for agent operations."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetadata:
    """Metadata for execution context."""
    
    start_time: float = field(default_factory=time.time)
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    

class ExecutionContext:
    """Context manager for agent execution operations."""
    
    def __init__(
        self,
        context_id: str,
        metadata: Optional[ExecutionMetadata] = None,
        timeout: Optional[float] = None
    ):
        """Initialize execution context.
        
        Args:
            context_id: Unique identifier for this context
            metadata: Execution metadata
            timeout: Execution timeout in seconds
        """
        self.context_id = context_id
        self.metadata = metadata or ExecutionMetadata()
        self.timeout = timeout
        self.state: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self.errors: List[Exception] = []
        self.callbacks: List[Callable] = []
        self._start_time = time.time()
        self._end_time: Optional[float] = None
        self._cancelled = False
        
    @property
    def duration(self) -> float:
        """Get execution duration in seconds."""
        end_time = self._end_time or time.time()
        return end_time - self._start_time
        
    @property
    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self._end_time is not None
        
    @property
    def is_cancelled(self) -> bool:
        """Check if execution was cancelled."""
        return self._cancelled
        
    def set_state(self, key: str, value: Any):
        """Set state value."""
        self.state[key] = value
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self.state.get(key, default)
        
    def set_result(self, key: str, value: Any):
        """Set result value."""
        self.results[key] = value
        
    def get_result(self, key: str, default: Any = None) -> Any:
        """Get result value."""
        return self.results.get(key, default)
        
    def add_error(self, error: Exception):
        """Add error to context."""
        self.errors.append(error)
        logger.error(f"Error in execution context {self.context_id}: {error}")
        
    def add_callback(self, callback: Callable):
        """Add completion callback."""
        self.callbacks.append(callback)
        
    def cancel(self):
        """Cancel the execution."""
        self._cancelled = True
        logger.warning(f"Execution context {self.context_id} cancelled")
        
    def complete(self):
        """Mark execution as completed."""
        if self._end_time is None:
            self._end_time = time.time()
            
            # Execute callbacks
            for callback in self.callbacks:
                try:
                    callback(self)
                except Exception as e:
                    logger.error(f"Callback error in context {self.context_id}: {e}")
                    
            logger.info(f"Execution context {self.context_id} completed in {self.duration:.3f}s")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "context_id": self.context_id,
            "metadata": {
                "start_time": self.metadata.start_time,
                "agent_id": self.metadata.agent_id,
                "operation": self.metadata.operation,
                "request_id": self.metadata.request_id,
                "user_id": self.metadata.user_id,
                "session_id": self.metadata.session_id,
                "parent_context_id": self.metadata.parent_context_id,
                "tags": self.metadata.tags
            },
            "state": self.state,
            "results": self.results,
            "errors": [str(e) for e in self.errors],
            "duration": self.duration,
            "completed": self.is_completed,
            "cancelled": self.is_cancelled
        }


class ContextManager:
    """Global context manager for execution contexts."""
    
    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
        self._lock = asyncio.Lock()
        
    async def create_context(
        self,
        context_id: str,
        metadata: Optional[ExecutionMetadata] = None,
        timeout: Optional[float] = None
    ) -> ExecutionContext:
        """Create new execution context.
        
        Args:
            context_id: Unique identifier for context
            metadata: Execution metadata
            timeout: Execution timeout
            
        Returns:
            Created execution context
        """
        async with self._lock:
            if context_id in self._contexts:
                raise ValueError(f"Context {context_id} already exists")
                
            context = ExecutionContext(context_id, metadata, timeout)
            self._contexts[context_id] = context
            
            logger.debug(f"Created execution context: {context_id}")
            return context
            
    async def get_context(self, context_id: str) -> Optional[ExecutionContext]:
        """Get execution context by ID.
        
        Args:
            context_id: Context identifier
            
        Returns:
            Execution context if found
        """
        async with self._lock:
            return self._contexts.get(context_id)
            
    async def complete_context(self, context_id: str):
        """Complete and remove execution context.
        
        Args:
            context_id: Context identifier
        """
        async with self._lock:
            context = self._contexts.get(context_id)
            if context:
                context.complete()
                del self._contexts[context_id]
                logger.debug(f"Completed and removed context: {context_id}")
                
    async def cancel_context(self, context_id: str):
        """Cancel execution context.
        
        Args:
            context_id: Context identifier
        """
        async with self._lock:
            context = self._contexts.get(context_id)
            if context:
                context.cancel()
                
    async def cleanup_completed(self):
        """Clean up completed contexts."""
        async with self._lock:
            completed = [
                ctx_id for ctx_id, ctx in self._contexts.items()
                if ctx.is_completed or ctx.is_cancelled
            ]
            
            for ctx_id in completed:
                del self._contexts[ctx_id]
                
            if completed:
                logger.debug(f"Cleaned up {len(completed)} completed contexts")
                
    def get_active_count(self) -> int:
        """Get count of active contexts."""
        return len(self._contexts)


class AgentExecutionContext(ExecutionContext):
    """Specialized execution context for agent operations."""
    
    def __init__(
        self,
        context_id: str,
        agent_id: str,
        operation: str,
        metadata: Optional[ExecutionMetadata] = None,
        timeout: Optional[float] = None
    ):
        """Initialize agent execution context.
        
        Args:
            context_id: Unique identifier for context
            agent_id: Agent identifier
            operation: Operation being performed
            metadata: Additional execution metadata
            timeout: Execution timeout in seconds
        """
        if metadata is None:
            metadata = ExecutionMetadata()
        metadata.agent_id = agent_id
        metadata.operation = operation
        
        super().__init__(context_id, metadata, timeout)
        self.agent_id = agent_id
        self.operation = operation
        self.metrics: Dict[str, Any] = {}
        
    def record_metric(self, key: str, value: Any):
        """Record a metric for this execution."""
        self.metrics[key] = value
        
    def get_metric(self, key: str, default: Any = None) -> Any:
        """Get a recorded metric."""
        return self.metrics.get(key, default)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent context to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            "agent_id": self.agent_id,
            "operation": self.operation,
            "metrics": self.metrics
        })
        return base_dict


@dataclass 
class AgentExecutionResult:
    """Result of agent execution."""
    
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    context_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "context_id": self.context_id,
            "metrics": self.metrics
        }


# Global context manager instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get global context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


@asynccontextmanager
async def execution_context(
    context_id: str,
    metadata: Optional[ExecutionMetadata] = None,
    timeout: Optional[float] = None
):
    """Async context manager for execution contexts.
    
    Args:
        context_id: Unique identifier for context
        metadata: Execution metadata
        timeout: Execution timeout
        
    Yields:
        Execution context instance
    """
    manager = get_context_manager()
    context = await manager.create_context(context_id, metadata, timeout)
    
    try:
        if timeout:
            async with asyncio.timeout(timeout):
                yield context
        else:
            yield context
    except asyncio.TimeoutError:
        logger.warning(f"Execution context {context_id} timed out after {timeout}s")
        context.add_error(asyncio.TimeoutError(f"Execution timed out after {timeout}s"))
        raise
    except Exception as e:
        context.add_error(e)
        raise
    finally:
        await manager.complete_context(context_id)