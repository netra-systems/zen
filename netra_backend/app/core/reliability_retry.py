"""Retry logic and backoff strategies for Netra agents.

This module provides exponential backoff retry handlers with jitter
and configurable retry policies for robust error recovery.
"""

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Tuple

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


# RetryConfig now imported from shared_types.py
# Using compatibility wrapper for existing code
@dataclass
class ReliabilityRetryConfig:
    """Compatibility wrapper for reliability retry configuration."""
    base_config: RetryConfig
    exponential_base: float = 2.0
    
    @classmethod
    def from_retry_config(cls, config: RetryConfig) -> 'ReliabilityRetryConfig':
        """Create from base RetryConfig."""
        return cls(base_config=config)


class RetryHandler:
    """Exponential backoff retry handler with jitter"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute_with_retry(
        self, 
        func: Callable[[], Awaitable[Any]], 
        operation_name: str = "operation",
        error_classifier: Optional[Callable[[Exception], bool]] = None
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            result, error = await self._attempt_execution(
                func, attempt, operation_name, error_classifier
            )
            if error is None:
                return result
            last_exception = error
        raise last_exception
    
    async def _attempt_execution(
        self,
        func: Callable[[], Awaitable[Any]],
        attempt: int,
        operation_name: str,
        error_classifier: Optional[Callable[[Exception], bool]]
    ) -> Tuple[Any, Optional[Exception]]:
        """Attempt single execution with error handling"""
        try:
            result = await func()
            return result, None
        except Exception as e:
            error = await self._handle_execution_error(
                e, attempt, operation_name, error_classifier
            )
            return None, error
    
    async def _handle_execution_error(
        self,
        error: Exception,
        attempt: int,
        operation_name: str,
        error_classifier: Optional[Callable[[Exception], bool]]
    ) -> Exception:
        """Handle execution error with retry logic"""
        if not self._should_retry(error, error_classifier, attempt):
            raise error
        
        await self._handle_retry_delay(attempt, operation_name, error)
        return error
    
    def _should_retry(
        self, 
        error: Exception, 
        error_classifier: Optional[Callable[[Exception], bool]], 
        attempt: int
    ) -> bool:
        """Determine if operation should be retried"""
        if attempt == self.config.max_retries:
            return False
        
        if error_classifier and not error_classifier(error):
            return False
        
        return True
    
    async def _handle_retry_delay(
        self, 
        attempt: int, 
        operation_name: str, 
        error: Exception
    ) -> None:
        """Handle delay and logging for retry attempt"""
        if attempt == self.config.max_retries:
            logger.error(
                f"{operation_name}: Final attempt {attempt + 1} failed: {error}"
            )
            return
        
        delay = self._calculate_delay(attempt)
        self._log_retry_attempt(operation_name, attempt, error, delay)
        await asyncio.sleep(delay)
    
    def _log_retry_attempt(
        self, 
        operation_name: str, 
        attempt: int, 
        error: Exception, 
        delay: float
    ) -> None:
        """Log retry attempt with details"""
        logger.warning(
            f"{operation_name}: Attempt {attempt + 1} failed: {error}. "
            f"Retrying in {delay:.2f}s..."
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        base_delay = self._calculate_exponential_delay(attempt)
        return self._apply_jitter(base_delay) if self.config.jitter else base_delay
    
    def _calculate_exponential_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        exponential_delay = (
            self.config.base_delay * 
            (self.config.exponential_base ** attempt)
        )
        return min(exponential_delay, self.config.max_delay)
    
    def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to delay (up to 25% random variation)"""
        jitter = delay * 0.25 * random.random()
        return delay + jitter