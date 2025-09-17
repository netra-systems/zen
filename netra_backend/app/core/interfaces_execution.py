"""
Core execution interfaces and protocols.
Defines common interfaces for execution patterns across the system.
"""

from typing import Any, Dict, List, Optional, Protocol, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from enum import Enum

# ISSUE #1184 REMEDIATION: Fix deprecated logging pattern
from shared.logging.unified_logging_ssot import get_logger
# SSOT: Import ExecutionStatus from core_enums instead of defining duplicate
from netra_backend.app.schemas.core_enums import ExecutionStatus

logger = get_logger(__name__)


class ExecutionStrategy(Enum):
    """Execution strategy options."""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    BATCH = "batch"
    PRIORITY = "priority"


@dataclass
class ExecutionContext:
    """Standard execution context for operations."""
    execution_id: str
    operation_name: str
    parameters: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    timeout_seconds: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


@dataclass 
class ExecutionResult:
    """Standard execution result structure."""
    execution_id: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.completed_at is None and self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            self.completed_at = datetime.now(UTC)
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete (success or failure)."""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT]


class ExecutorProtocol(Protocol):
    """Protocol for execution interfaces."""
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute operation with given context."""
        ...
    
    async def cancel(self, execution_id: str) -> bool:
        """Cancel running execution."""
        ...
    
    def get_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """Get status of execution."""
        ...


class BaseExecutor(ABC):
    """Base class for executors implementing common patterns."""
    
    def __init__(self, name: str):
        self.name = name
        self._active_executions: Dict[str, ExecutionContext] = {}
        logger.debug(f"Initialized BaseExecutor: {name}")
    
    @abstractmethod
    async def _execute_operation(self, context: ExecutionContext) -> Any:
        """Execute the specific operation. Override in subclasses."""
        pass
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute operation with standard error handling and monitoring."""
        start_time = datetime.now(UTC)
        self._active_executions[context.execution_id] = context
        
        try:
            logger.info(f"Starting execution: {context.operation_name} (id: {context.execution_id})")
            
            # Execute the operation
            result = await self._execute_operation(context)
            
            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            # Create successful result
            execution_result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED,
                result=result,
                duration_ms=duration_ms
            )
            
            logger.info(f"Completed execution: {context.operation_name} in {duration_ms:.2f}ms")
            return execution_result
            
        except Exception as e:
            # Calculate duration for failed execution
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            # Create failed result
            execution_result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms
            )
            
            logger.error(f"Failed execution: {context.operation_name} after {duration_ms:.2f}ms - {e}")
            return execution_result
            
        finally:
            # Clean up active execution
            if context.execution_id in self._active_executions:
                del self._active_executions[context.execution_id]
    
    async def cancel(self, execution_id: str) -> bool:
        """Cancel running execution."""
        if execution_id in self._active_executions:
            logger.info(f"Cancelling execution: {execution_id}")
            # In a more sophisticated implementation, this would signal the running operation
            del self._active_executions[execution_id]
            return True
        return False
    
    def get_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """Get status of execution."""
        if execution_id in self._active_executions:
            return ExecutionStatus.RUNNING
        return None
    
    def get_active_executions(self) -> List[ExecutionContext]:
        """Get list of currently active executions."""
        return list(self._active_executions.values())


class BatchExecutor(BaseExecutor):
    """Executor that handles batch operations."""
    
    def __init__(self, name: str, batch_size: int = 10):
        super().__init__(name)
        self.batch_size = batch_size
    
    async def execute_batch(self, contexts: List[ExecutionContext]) -> List[ExecutionResult]:
        """Execute multiple operations in batch."""
        results = []
        
        # Process in batches
        for i in range(0, len(contexts), self.batch_size):
            batch = contexts[i:i + self.batch_size]
            batch_results = await self._execute_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def _execute_batch(self, batch: List[ExecutionContext]) -> List[ExecutionResult]:
        """Execute a single batch of operations."""
        import asyncio
        
        # Execute all operations in the batch concurrently
        tasks = [self.execute(context) for context in batch]
        return await asyncio.gather(*tasks, return_exceptions=True)


class PriorityExecutor(BaseExecutor):
    """Executor that handles operations with priority queuing."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._priority_queue: List[tuple[int, ExecutionContext]] = []
    
    async def execute_with_priority(self, context: ExecutionContext, priority: int = 5) -> ExecutionResult:
        """Execute operation with specified priority (lower number = higher priority)."""
        # Add to priority queue
        import heapq
        heapq.heappush(self._priority_queue, (priority, context))
        
        # Process queue
        if self._priority_queue:
            _, next_context = heapq.heappop(self._priority_queue)
            return await self.execute(next_context)
        else:
            # Fallback to direct execution
            return await self.execute(context)


class ExecutionMetrics:
    """Tracks execution metrics and performance."""
    
    def __init__(self):
        self._metrics: List[Dict[str, Any]] = []
        logger.debug("Initialized ExecutionMetrics")
    
    def record_execution(self, result: ExecutionResult) -> None:
        """Record execution metrics."""
        metric = {
            "execution_id": result.execution_id,
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "success": result.is_success,
            "error_type": result.error_type,
            "timestamp": result.completed_at or datetime.now(UTC)
        }
        
        self._metrics.append(metric)
        
        # Keep only last 10000 metrics
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for specified time period."""
        from datetime import timedelta
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_metrics = [
            m for m in self._metrics
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "period_hours": hours,
                "total_executions": 0,
                "summary": "No executions in time period"
            }
        
        total_executions = len(recent_metrics)
        successful_executions = len([m for m in recent_metrics if m.get("success")])
        failed_executions = total_executions - successful_executions
        
        # Calculate average duration
        durations = [m.get("duration_ms", 0) for m in recent_metrics if m.get("duration_ms")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Error breakdown
        error_types = {}
        for metric in recent_metrics:
            if not metric.get("success") and metric.get("error_type"):
                error_type = metric["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "period_hours": hours,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_duration_ms": avg_duration,
            "error_types": error_types,
            "timestamp": datetime.now(UTC)
        }


# Global metrics instance
execution_metrics = ExecutionMetrics()


__all__ = [
    "ExecutionStatus",
    "ExecutionStrategy", 
    "ExecutionContext",
    "ExecutionResult",
    "ExecutorProtocol",
    "BaseExecutor",
    "BatchExecutor",
    "PriorityExecutor",
    "ExecutionMetrics",
    "execution_metrics",
]