"""Comprehensive error recovery system for Netra AI platform.

Provides centralized error recovery mechanisms with rollback capabilities,
compensating transactions, and agent-specific recovery strategies.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta

from app.core.error_codes import ErrorCode, ErrorSeverity
from app.core.exceptions_base import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RecoveryAction(Enum):
    """Types of recovery actions available."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    COMPENSATE = "compensate"
    FALLBACK = "fallback"
    ABORT = "abort"
    CIRCUIT_BREAK = "circuit_break"


class OperationType(Enum):
    """Types of operations that can be recovered."""
    DATABASE_WRITE = "database_write"
    DATABASE_READ = "database_read"
    LLM_REQUEST = "llm_request"
    WEBSOCKET_SEND = "websocket_send"
    FILE_OPERATION = "file_operation"
    EXTERNAL_API = "external_api"
    AGENT_EXECUTION = "agent_execution"
    CACHE_OPERATION = "cache_operation"


@dataclass
class RecoveryContext:
    """Context for error recovery operations."""
    operation_id: str
    operation_type: OperationType
    error: Exception
    severity: ErrorSeverity
    retry_count: int = 0
    max_retries: int = 3
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time since operation started."""
        return datetime.now() - self.started_at


@dataclass 
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    action_taken: RecoveryAction
    result_data: Any = None
    error_message: Optional[str] = None
    compensation_required: bool = False
    circuit_broken: bool = False


class CompensationAction(ABC):
    """Abstract base for compensation actions."""
    
    @abstractmethod
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute compensation action. Returns True if successful."""
        pass
    
    @abstractmethod
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if this action can compensate for the given context."""
        pass


class DatabaseRollbackAction(CompensationAction):
    """Rollback database transactions."""
    
    def __init__(self, transaction_manager):
        """Initialize with transaction manager reference."""
        self.transaction_manager = transaction_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute database rollback."""
        try:
            await self.transaction_manager.rollback_operation(
                context.operation_id
            )
            logger.info(f"Rollback successful for {context.operation_id}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed for {context.operation_id}: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if database rollback is applicable."""
        return context.operation_type in [
            OperationType.DATABASE_WRITE,
            OperationType.DATABASE_READ
        ]


class CacheInvalidationAction(CompensationAction):
    """Invalidate cache entries on failure."""
    
    def __init__(self, cache_manager):
        """Initialize with cache manager reference."""
        self.cache_manager = cache_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute cache invalidation."""
        try:
            cache_keys = context.metadata.get('cache_keys', [])
            if cache_keys:
                await self.cache_manager.invalidate_keys(cache_keys)
                logger.info(f"Cache invalidated: {cache_keys}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return False
    
    def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if cache invalidation is applicable."""
        return 'cache_keys' in context.metadata


class RetryStrategy:
    """Defines retry behavior for different error types."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """Initialize retry strategy."""
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if operation should be retried."""
        if context.retry_count >= self.max_retries:
            return False
        
        # Don't retry validation errors
        if isinstance(context.error, ValueError):
            return False
        
        # Don't retry critical errors
        if context.severity == ErrorSeverity.CRITICAL:
            return False
        
        return True
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay before retry (exponential backoff)."""
        return min(self.base_delay * (2 ** retry_count), 30.0)


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed through."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                return True
            return False
        
        # half_open state - allow single request to test
        return True
    
    def record_success(self) -> None:
        """Record successful operation."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if not self.last_failure_time:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout


class ErrorRecoveryManager:
    """Central manager for error recovery operations."""
    
    def __init__(self):
        """Initialize error recovery manager."""
        self.compensation_actions: List[CompensationAction] = []
        self.retry_strategies: Dict[OperationType, RetryStrategy] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.active_operations: Dict[str, RecoveryContext] = {}
        
        # Initialize default retry strategies
        self._setup_default_strategies()
    
    def _setup_default_strategies(self) -> None:
        """Set up default retry strategies for different operation types."""
        self.retry_strategies = {
            OperationType.DATABASE_WRITE: RetryStrategy(max_retries=2, base_delay=0.5),
            OperationType.DATABASE_READ: RetryStrategy(max_retries=3, base_delay=0.1),
            OperationType.LLM_REQUEST: RetryStrategy(max_retries=3, base_delay=2.0),
            OperationType.WEBSOCKET_SEND: RetryStrategy(max_retries=1, base_delay=0.1),
            OperationType.EXTERNAL_API: RetryStrategy(max_retries=3, base_delay=1.0),
            OperationType.AGENT_EXECUTION: RetryStrategy(max_retries=2, base_delay=1.0),
            OperationType.CACHE_OPERATION: RetryStrategy(max_retries=1, base_delay=0.1),
            OperationType.FILE_OPERATION: RetryStrategy(max_retries=2, base_delay=0.5),
        }
    
    def register_compensation_action(self, action: CompensationAction) -> None:
        """Register a compensation action."""
        self.compensation_actions.append(action)
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]


class RecoveryExecutor:
    """Executes recovery operations."""
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        """Initialize with recovery manager."""
        self.recovery_manager = recovery_manager
    
    async def attempt_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Attempt to recover from an error."""
        try:
            # Check circuit breaker
            circuit_breaker = self._get_circuit_breaker(context)
            if not circuit_breaker.should_allow_request():
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.CIRCUIT_BREAK,
                    circuit_broken=True
                )
            
            # Try retry first
            if self._should_retry(context):
                return await self._execute_retry(context)
            
            # Try compensation
            compensation_result = await self._execute_compensation(context)
            if compensation_result:
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.COMPENSATE,
                    compensation_required=True
                )
            
            # Fallback to abort
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.ABORT,
                error_message=f"No recovery possible for {context.operation_id}"
            )
            
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.ABORT,
                error_message=str(e)
            )
    
    def _get_circuit_breaker(self, context: RecoveryContext) -> CircuitBreaker:
        """Get circuit breaker for operation."""
        service_name = f"{context.operation_type.value}"
        return self.recovery_manager.get_circuit_breaker(service_name)
    
    def _should_retry(self, context: RecoveryContext) -> bool:
        """Check if operation should be retried."""
        strategy = self.recovery_manager.retry_strategies.get(
            context.operation_type
        )
        return strategy.should_retry(context) if strategy else False
    
    async def _execute_retry(self, context: RecoveryContext) -> RecoveryResult:
        """Execute retry logic."""
        strategy = self.recovery_manager.retry_strategies[context.operation_type]
        delay = strategy.get_delay(context.retry_count)
        
        logger.info(f"Retrying {context.operation_id} in {delay}s")
        await asyncio.sleep(delay)
        
        return RecoveryResult(
            success=True,
            action_taken=RecoveryAction.RETRY
        )
    
    async def _execute_compensation(self, context: RecoveryContext) -> bool:
        """Execute applicable compensation actions."""
        compensation_success = True
        
        for action in self.recovery_manager.compensation_actions:
            if action.can_compensate(context):
                try:
                    result = await action.execute(context)
                    if not result:
                        compensation_success = False
                        logger.warning(
                            f"Compensation action failed: {type(action).__name__}"
                        )
                except Exception as e:
                    logger.error(f"Compensation action error: {e}")
                    compensation_success = False
        
        return compensation_success


# Global recovery manager instance
recovery_manager = ErrorRecoveryManager()
recovery_executor = RecoveryExecutor(recovery_manager)