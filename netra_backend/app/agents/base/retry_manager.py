"""
Retry management system for agent operations.
Handles retry logic, backoff strategies, and failure analysis.
"""

from typing import Any, Callable, Awaitable, Optional, Dict, List
from datetime import datetime, timedelta, UTC
import asyncio
import random
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BackoffStrategy(Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


class RetryResult:
    """Result of retry operation."""
    
    def __init__(self, 
                 success: bool,
                 result: Any = None,
                 attempts: int = 0,
                 total_duration: float = 0.0,
                 last_error: Optional[Exception] = None):
        self.success = success
        self.result = result
        self.attempts = attempts
        self.total_duration = total_duration
        self.last_error = last_error


class RetryManager:
    """Manages retry logic for agent operations."""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER):
        """
        Initialize retry manager.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_strategy: Strategy for calculating retry delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_strategy = backoff_strategy
        
        # Statistics
        self._retry_stats: List[Dict[str, Any]] = []
        
        logger.debug(f"Initialized RetryManager: max_attempts={max_attempts}, "
                    f"strategy={backoff_strategy.value}")
    
    async def execute_with_retry(self,
                               operation: Callable[[], Awaitable[Any]],
                               operation_name: str = "unknown",
                               max_attempts: Optional[int] = None,
                               retryable_exceptions: Optional[tuple] = None) -> RetryResult:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Async operation to execute
            operation_name: Name of operation for logging
            max_attempts: Override default max attempts
            retryable_exceptions: Tuple of exception types that should trigger retries
            
        Returns:
            RetryResult with success status and result/error
        """
        start_time = datetime.now(UTC)
        attempts = max_attempts or self.max_attempts
        last_error = None
        
        # Default retryable exceptions
        if retryable_exceptions is None:
            retryable_exceptions = (
                ConnectionError,
                TimeoutError,
                RuntimeError,
                # Add more retryable exceptions as needed
            )
        
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    # Calculate delay and wait
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying {operation_name} (attempt {attempt + 1}/{attempts}) "
                              f"after {delay:.2f}s delay")
                    await asyncio.sleep(delay)
                
                # Execute operation
                result = await operation()
                
                # Success
                total_duration = (datetime.now(UTC) - start_time).total_seconds()
                retry_result = RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_duration=total_duration
                )
                
                # Record statistics
                await self._record_retry_stats(operation_name, retry_result)
                
                if attempt > 0:
                    logger.info(f"Operation {operation_name} succeeded after {attempt} retries")
                
                return retry_result
                
            except Exception as e:
                last_error = e
                
                # Check if this error is retryable
                if not isinstance(e, retryable_exceptions):
                    logger.info(f"Non-retryable error for {operation_name}: {type(e).__name__}: {e}")
                    break
                
                logger.warning(f"Operation {operation_name} failed (attempt {attempt + 1}/{attempts}): "
                             f"{type(e).__name__}: {e}")
                
                # If this is the last attempt, don't log as a retry
                if attempt < attempts - 1:
                    logger.debug(f"Will retry {operation_name} in {self._calculate_delay(attempt + 1):.2f}s")
        
        # All attempts failed
        total_duration = (datetime.now(UTC) - start_time).total_seconds()
        retry_result = RetryResult(
            success=False,
            result=None,
            attempts=attempts,
            total_duration=total_duration,
            last_error=last_error
        )
        
        # Record statistics
        await self._record_retry_stats(operation_name, retry_result)
        
        logger.error(f"Operation {operation_name} failed after {attempts} attempts: {last_error}")
        
        return retry_result
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt based on backoff strategy."""
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.base_delay
            
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * attempt
            
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** (attempt - 1))
            
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            exponential_delay = self.base_delay * (2 ** (attempt - 1))
            # Add jitter to prevent thundering herd
            jitter = exponential_delay * random.uniform(0.1, 0.5)
            delay = exponential_delay + jitter
            
        else:
            delay = self.base_delay
        
        # Ensure delay doesn't exceed maximum
        return min(delay, self.max_delay)
    
    async def _record_retry_stats(self, operation_name: str, result: RetryResult) -> None:
        """Record retry statistics."""
        stat_entry = {
            "operation_name": operation_name,
            "timestamp": datetime.now(UTC),
            "success": result.success,
            "attempts": result.attempts,
            "total_duration": result.total_duration,
            "error_type": type(result.last_error).__name__ if result.last_error else None,
            "backoff_strategy": self.backoff_strategy.value
        }
        
        self._retry_stats.append(stat_entry)
        
        # Keep only last 1000 entries
        if len(self._retry_stats) > 1000:
            self._retry_stats = self._retry_stats[-1000:]
    
    def get_retry_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get retry statistics for specified time period."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_stats = [
            s for s in self._retry_stats
            if s.get("timestamp", datetime.min) > cutoff_time
        ]
        
        if not recent_stats:
            return {
                "time_period_hours": hours,
                "total_operations": 0,
                "summary": "No retry operations in time period"
            }
        
        # Calculate statistics
        total_ops = len(recent_stats)
        successful_ops = len([s for s in recent_stats if s["success"]])
        failed_ops = total_ops - successful_ops
        
        # Calculate average attempts
        total_attempts = sum(s["attempts"] for s in recent_stats)
        avg_attempts = total_attempts / total_ops if total_ops > 0 else 0
        
        # Calculate average duration
        total_duration = sum(s["total_duration"] for s in recent_stats)
        avg_duration = total_duration / total_ops if total_ops > 0 else 0
        
        # Most common error types
        error_types = [s["error_type"] for s in recent_stats if s["error_type"]]
        error_counts = {}
        for error_type in error_types:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Operations requiring retries (more than 1 attempt)
        retry_ops = [s for s in recent_stats if s["attempts"] > 1]
        retry_rate = len(retry_ops) / total_ops if total_ops > 0 else 0
        
        return {
            "time_period_hours": hours,
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "success_rate": successful_ops / total_ops if total_ops > 0 else 0,
            "retry_rate": retry_rate,
            "average_attempts": avg_attempts,
            "average_duration_seconds": avg_duration,
            "common_error_types": error_counts,
            "backoff_strategy": self.backoff_strategy.value,
            "configuration": {
                "max_attempts": self.max_attempts,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay
            }
        }
    
    def update_configuration(self,
                           max_attempts: Optional[int] = None,
                           base_delay: Optional[float] = None,
                           max_delay: Optional[float] = None,
                           backoff_strategy: Optional[BackoffStrategy] = None) -> None:
        """Update retry configuration."""
        if max_attempts is not None:
            self.max_attempts = max_attempts
        if base_delay is not None:
            self.base_delay = base_delay
        if max_delay is not None:
            self.max_delay = max_delay
        if backoff_strategy is not None:
            self.backoff_strategy = backoff_strategy
        
        logger.info(f"Updated RetryManager configuration: max_attempts={self.max_attempts}, "
                   f"base_delay={self.base_delay}, max_delay={self.max_delay}, "
                   f"strategy={self.backoff_strategy.value}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of retry manager."""
        recent_stats = self.get_retry_statistics(hours=1)
        
        # Determine health based on recent performance
        health_status = "healthy"
        issues = []
        
        if recent_stats["total_operations"] > 0:
            success_rate = recent_stats["success_rate"]
            retry_rate = recent_stats["retry_rate"]
            
            if success_rate < 0.8:
                health_status = "degraded"
                issues.append(f"Low success rate: {success_rate:.1%}")
            
            if retry_rate > 0.5:
                if health_status == "healthy":
                    health_status = "warning"
                issues.append(f"High retry rate: {retry_rate:.1%}")
        
        return {
            "status": health_status,
            "issues": issues,
            "recent_performance": recent_stats,
            "timestamp": datetime.now(UTC)
        }


__all__ = [
    "RetryManager",
    "RetryResult", 
    "BackoffStrategy",
]