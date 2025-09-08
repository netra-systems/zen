"""Transaction core functionality module.

Core transaction management classes and decorators.
"""

from enum import Enum
from typing import Any, Callable, Optional
from dataclasses import dataclass
import functools
import asyncio
import logging

logger = logging.getLogger(__name__)


class TransactionIsolationLevel(Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"  
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass
class TransactionConfig:
    """Configuration for transaction management."""
    isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED
    timeout: int = 30
    max_retries: int = 3
    enable_deadlock_retry: bool = True
    enable_connection_retry: bool = True


class TransactionManager:
    """Core transaction management class."""
    
    def __init__(self, config: Optional[TransactionConfig] = None):
        """Initialize transaction manager."""
        self.config = config or TransactionConfig()
    
    async def begin_transaction(self):
        """Begin a new transaction."""
        logger.info("Beginning transaction")
        
    async def commit_transaction(self):
        """Commit current transaction."""
        logger.info("Committing transaction")
        
    async def rollback_transaction(self):
        """Rollback current transaction."""
        logger.info("Rolling back transaction")


# Global transaction manager instance
transaction_manager = TransactionManager()


def transactional(func: Callable) -> Callable:
    """Decorator to make a function transactional."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        """Transaction wrapper."""
        try:
            await transaction_manager.begin_transaction()
            result = await func(*args, **kwargs)
            await transaction_manager.commit_transaction()
            return result
        except Exception as e:
            await transaction_manager.rollback_transaction()
            raise e
    
    return wrapper


def with_deadlock_retry(max_retries: int = 3):
    """Decorator to retry on deadlock errors."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            """Deadlock retry wrapper."""
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    if "deadlock" in str(e).lower():
                        await asyncio.sleep(0.1 * (attempt + 1))
                        continue
                    raise
            
        return wrapper
    return decorator


def with_serializable_retry(max_retries: int = 3):
    """Decorator to retry serializable transaction conflicts."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            """Serializable retry wrapper."""
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    if "serialization" in str(e).lower():
                        await asyncio.sleep(0.1 * (attempt + 1))
                        continue
                    raise
            
        return wrapper
    return decorator