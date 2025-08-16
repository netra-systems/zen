"""Transaction core logic and management module.

Handles transaction execution, isolation levels, and retry coordination.
Focused module adhering to 8-line function limit and modular architecture.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    OperationalError, 
    DisconnectionError,
    TimeoutError as SQLTimeoutError
)
from sqlalchemy import text

from app.logging_config import central_logger
from app.core.enhanced_retry_strategies import RetryConfig, exponential_backoff_retry
from .transaction_errors import classify_error, is_retryable_error
from .transaction_stats import TransactionMetrics, get_transaction_stats, generate_transaction_id

logger = central_logger.get_logger(__name__)


class TransactionIsolationLevel(Enum):
    """SQL transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


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
        """Check if error is retryable based on configuration."""
        return is_retryable_error(
            error, 
            self.config.enable_deadlock_retry,
            self.config.enable_connection_retry
        )
    
    def _classify_error(self, error: Exception) -> Exception:
        """Classify and potentially wrap errors."""
        return classify_error(error)
    
    def _setup_transaction_metrics(self, tx_config: TransactionConfig, tx_id: str) -> TransactionMetrics:
        """Setup transaction metrics and tracking."""
        metrics = TransactionMetrics(
            transaction_id=tx_id, start_time=time.time(),
            isolation_level=tx_config.isolation_level.value
        )
        
        if tx_config.enable_metrics:
            self.active_transactions[tx_id] = metrics
        return metrics
    
    def _create_retry_config(self, tx_config: TransactionConfig) -> RetryConfig:
        """Create retry configuration for transaction."""
        return RetryConfig(
            max_attempts=tx_config.retry_attempts, base_delay=tx_config.retry_delay,
            backoff_factor=tx_config.retry_backoff, max_delay=30.0
        )
    
    async def _set_isolation_level(self, session: AsyncSession, tx_config: TransactionConfig):
        """Set transaction isolation level if needed."""
        if tx_config.isolation_level != TransactionIsolationLevel.READ_COMMITTED:
            await session.execute(
                text(f"SET TRANSACTION ISOLATION LEVEL {tx_config.isolation_level.value}")
            )
    
    async def _set_transaction_timeout(self, session: AsyncSession, tx_config: TransactionConfig):
        """Set transaction timeout if configured."""
        if tx_config.timeout_seconds > 0:
            timeout_ms = int(tx_config.timeout_seconds * 1000)
            await session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
    
    async def _execute_transaction_core(self, session: AsyncSession, tx_config: TransactionConfig, metrics: TransactionMetrics):
        """Execute core transaction logic with proper setup."""
        async with session.begin() as transaction:
            await self._set_isolation_level(session, tx_config)
            await self._set_transaction_timeout(session, tx_config)
            yield metrics
    
    def _handle_transaction_success(self, metrics: TransactionMetrics, result):
        """Handle successful transaction completion."""
        metrics.retry_count = getattr(result, 'retry_count', 0)
        metrics.complete(success=True)
    
    def _handle_transaction_failure(self, metrics: TransactionMetrics, tx_id: str, e: Exception):
        """Handle transaction failure with logging and classification."""
        metrics.error_count += 1
        metrics.complete(success=False)
        
        classified_error = self._classify_error(e)
        logger.error(f"Transaction {tx_id} failed after {metrics.retry_count} retries: {classified_error}")
        return classified_error
    
    def _cleanup_transaction_metrics(self, tx_config: TransactionConfig, tx_id: str):
        """Clean up transaction metrics if enabled."""
        if tx_config.enable_metrics and tx_id in self.active_transactions:
            del self.active_transactions[tx_id]
    
    def _prepare_transaction_context(self, config: Optional[TransactionConfig]):
        """Prepare transaction context and configuration."""
        tx_config = config or self.config
        tx_id = self._generate_transaction_id()
        metrics = self._setup_transaction_metrics(tx_config, tx_id)
        retry_config = self._create_retry_config(tx_config)
        return tx_config, tx_id, metrics, retry_config
    
    def _get_retry_exceptions(self):
        """Get tuple of retryable exceptions."""
        return (OperationalError, DisconnectionError, SQLTimeoutError)
    
    async def _execute_transaction_with_retry(self, session, tx_config, metrics, retry_config):
        """Execute transaction with retry logic."""
        async for result in exponential_backoff_retry(
            self._execute_transaction_core(session, tx_config, metrics),
            retry_config, retryable_exceptions=self._get_retry_exceptions(),
            exception_classifier=self._classify_error, logger=logger
        ):
            self._handle_transaction_success(metrics, result)
            yield result
            return
    
    @asynccontextmanager
    async def transaction(
        self,
        session: AsyncSession,
        config: Optional[TransactionConfig] = None
    ) -> AsyncGenerator[TransactionMetrics, None]:
        """Context manager for robust transactions."""
        tx_config, tx_id, metrics, retry_config = self._prepare_transaction_context(config)
        try:
            async for result in self._execute_transaction_with_retry(session, tx_config, metrics, retry_config):
                yield result
                return
        except Exception as e:
            raise self._handle_transaction_failure(metrics, tx_id, e)
        finally:
            self._cleanup_transaction_metrics(tx_config, tx_id)
    
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
        return get_transaction_stats(self.active_transactions)


# Global transaction manager instance
transaction_manager = TransactionManager()


def _create_transactional_config(isolation_level, timeout_seconds, retry_attempts):
    """Create transaction configuration for transactional context."""
    return TransactionConfig(
        isolation_level=isolation_level,
        timeout_seconds=timeout_seconds,
        retry_attempts=retry_attempts
    )

@asynccontextmanager
async def transactional(
    session: AsyncSession,
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
    timeout_seconds: float = 30.0,
    retry_attempts: int = 3
) -> AsyncGenerator[TransactionMetrics, None]:
    """Convenience function for transactional operations."""
    config = _create_transactional_config(isolation_level, timeout_seconds, retry_attempts)
    async with transaction_manager.transaction(session, config) as tx_metrics:
        yield tx_metrics


def _create_deadlock_retry_config(max_attempts: int):
    """Create configuration for deadlock retry."""
    return TransactionConfig(
        retry_attempts=max_attempts,
        enable_deadlock_retry=True,
        isolation_level=TransactionIsolationLevel.REPEATABLE_READ
    )

async def with_deadlock_retry(
    session: AsyncSession,
    operation: Callable[[], Any],
    max_attempts: int = 5
) -> Any:
    """Execute operation with deadlock retry logic."""
    config = _create_deadlock_retry_config(max_attempts)
    return await transaction_manager.execute_with_retry(session, operation, config)


def _create_serializable_retry_config(max_attempts: int):
    """Create configuration for serializable retry."""
    return TransactionConfig(
        retry_attempts=max_attempts,
        isolation_level=TransactionIsolationLevel.SERIALIZABLE,
        timeout_seconds=60.0
    )

async def with_serializable_retry(
    session: AsyncSession,
    operation: Callable[[], Any],
    max_attempts: int = 3
) -> Any:
    """Execute operation with serializable isolation and retry."""
    config = _create_serializable_retry_config(max_attempts)
    return await transaction_manager.execute_with_retry(session, operation, config)