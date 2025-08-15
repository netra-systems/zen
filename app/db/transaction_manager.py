"""Transaction Manager with Retry Logic and Best Practices

Provides comprehensive transaction management with automatic retry,
deadlock detection, and performance optimization.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    OperationalError, 
    IntegrityError, 
    DisconnectionError,
    StatementError,
    TimeoutError as SQLTimeoutError
)
from sqlalchemy import text

from app.logging_config import central_logger
from app.core.enhanced_retry_strategies import RetryConfig

logger = central_logger.get_logger(__name__)


class TransactionIsolationLevel(Enum):
    """SQL transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


class DeadlockError(TransactionError):
    """Raised when a deadlock is detected."""
    pass


class ConnectionError(TransactionError):
    """Raised when connection issues occur."""
    pass


@dataclass
class TransactionConfig:
    """Configuration for transaction behavior."""
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 0.1
    retry_backoff: float = 2.0
    enable_deadlock_retry: bool = True
    enable_connection_retry: bool = True
    enable_metrics: bool = True


@dataclass
class TransactionMetrics:
    """Metrics for transaction performance."""
    transaction_id: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    retry_count: int = 0
    error_count: int = 0
    success: bool = False
    isolation_level: Optional[str] = None
    
    def complete(self, success: bool = True) -> None:
        """Mark transaction as complete."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success


class TransactionManager:
    """Advanced transaction manager with retry logic."""
    
    def __init__(self, config: Optional[TransactionConfig] = None):
        """Initialize transaction manager."""
        self.config = config or TransactionConfig()
        self.active_transactions: Dict[str, TransactionMetrics] = {}
        self._transaction_counter = 0
        
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID."""
        self._transaction_counter += 1
        return f"txn_{int(time.time())}_{self._transaction_counter}"
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable."""
        if isinstance(error, DisconnectionError):
            return self.config.enable_connection_retry
        
        if isinstance(error, OperationalError):
            error_msg = str(error).lower()
            
            # Deadlock detection
            if any(keyword in error_msg for keyword in [
                'deadlock', 'lock timeout', 'lock wait timeout'
            ]):
                return self.config.enable_deadlock_retry
            
            # Connection issues
            if any(keyword in error_msg for keyword in [
                'connection', 'network', 'timeout', 'broken pipe'
            ]):
                return self.config.enable_connection_retry
        
        return False
    
    def _classify_error(self, error: Exception) -> Exception:
        """Classify and potentially wrap errors."""
        if isinstance(error, OperationalError):
            error_msg = str(error).lower()
            
            if any(keyword in error_msg for keyword in [
                'deadlock', 'lock timeout', 'lock wait timeout'
            ]):
                return DeadlockError(f"Deadlock detected: {error}")
            
            if any(keyword in error_msg for keyword in [
                'connection', 'network', 'timeout', 'broken pipe'
            ]):
                return ConnectionError(f"Connection error: {error}")
        
        return error
    
    @asynccontextmanager
    async def transaction(
        self,
        session: AsyncSession,
        config: Optional[TransactionConfig] = None
    ) -> AsyncGenerator[TransactionMetrics, None]:
        """Context manager for robust transactions."""
        tx_config = config or self.config
        tx_id = self._generate_transaction_id()
        
        metrics = TransactionMetrics(
            transaction_id=tx_id,
            start_time=time.time(),
            isolation_level=tx_config.isolation_level.value
        )
        
        if tx_config.enable_metrics:
            self.active_transactions[tx_id] = metrics
        
        retry_config = RetryConfig(
            max_attempts=tx_config.retry_attempts,
            base_delay=tx_config.retry_delay,
            backoff_factor=tx_config.retry_backoff,
            max_delay=30.0
        )
        
        async def _execute_transaction():
            """Execute transaction with proper setup."""
            async with session.begin() as transaction:
                # Set isolation level if specified
                if tx_config.isolation_level != TransactionIsolationLevel.READ_COMMITTED:
                    await session.execute(
                        text(f"SET TRANSACTION ISOLATION LEVEL {tx_config.isolation_level.value}")
                    )
                
                # Set transaction timeout
                if tx_config.timeout_seconds > 0:
                    timeout_ms = int(tx_config.timeout_seconds * 1000)
                    await session.execute(
                        text(f"SET LOCAL statement_timeout = {timeout_ms}")
                    )
                
                yield metrics
                
                # Transaction will be committed automatically
        
        try:
            async for result in exponential_backoff_retry(
                _execute_transaction(),
                retry_config,
                retryable_exceptions=(
                    OperationalError,
                    DisconnectionError,
                    SQLTimeoutError
                ),
                exception_classifier=self._classify_error,
                logger=logger
            ):
                metrics.retry_count = getattr(result, 'retry_count', 0)
                yield result
                metrics.complete(success=True)
                return
                
        except Exception as e:
            metrics.error_count += 1
            metrics.complete(success=False)
            
            classified_error = self._classify_error(e)
            logger.error(
                f"Transaction {tx_id} failed after {metrics.retry_count} retries: {classified_error}"
            )
            raise classified_error
        
        finally:
            if tx_config.enable_metrics and tx_id in self.active_transactions:
                del self.active_transactions[tx_id]
    
    async def execute_with_retry(
        self,
        session: AsyncSession,
        operation: Callable[[], Any],
        config: Optional[TransactionConfig] = None
    ) -> Any:
        """Execute operation with transaction retry logic."""
        async with self.transaction(session, config) as tx_metrics:
            return await operation()
    
    def get_active_transactions(self) -> Dict[str, TransactionMetrics]:
        """Get currently active transactions."""
        return self.active_transactions.copy()
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        active_count = len(self.active_transactions)
        
        if not self.active_transactions:
            return {
                "active_transactions": 0,
                "avg_duration": 0.0,
                "max_duration": 0.0,
                "total_retries": 0
            }
        
        current_time = time.time()
        durations = []
        total_retries = 0
        
        for metrics in self.active_transactions.values():
            duration = current_time - metrics.start_time
            durations.append(duration)
            total_retries += metrics.retry_count
        
        return {
            "active_transactions": active_count,
            "avg_duration": sum(durations) / len(durations) if durations else 0.0,
            "max_duration": max(durations) if durations else 0.0,
            "total_retries": total_retries
        }


# Global transaction manager instance
transaction_manager = TransactionManager()


@asynccontextmanager
async def transactional(
    session: AsyncSession,
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    timeout_seconds: float = 30.0,
    retry_attempts: int = 3
) -> AsyncGenerator[TransactionMetrics, None]:
    """Convenience function for transactional operations."""
    config = TransactionConfig(
        isolation_level=isolation_level,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts
    )
    
    async with transaction_manager.transaction(session, config) as tx_metrics:
        yield tx_metrics


async def with_deadlock_retry(
    session: AsyncSession,
    operation: Callable[[], Any],
    max_attempts: int = 5
) -> Any:
    """Execute operation with deadlock retry logic."""
    config = TransactionConfig(
        retry_attempts=max_attempts,
        enable_deadlock_retry=True,
        isolation_level=TransactionIsolationLevel.REPEATABLE_READ
    )
    
    return await transaction_manager.execute_with_retry(session, operation, config)


async def with_serializable_retry(
    session: AsyncSession,
    operation: Callable[[], Any],
    max_attempts: int = 3
) -> Any:
    """Execute operation with serializable isolation and retry."""
    config = TransactionConfig(
        retry_attempts=max_attempts,
        isolation_level=TransactionIsolationLevel.SERIALIZABLE,
        timeout_seconds=60.0
    )
    
    return await transaction_manager.execute_with_retry(session, operation, config)