"""Comprehensive error recovery system for Netra AI platform.

Provides centralized error recovery mechanisms with rollback capabilities,
compensating transactions, and agent-specific recovery strategies.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

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
        if self._has_exceeded_retry_limit(context):
            return False
        return self._is_error_retryable(context)
    
    def _has_exceeded_retry_limit(self, context: RecoveryContext) -> bool:
        """Check if retry limit has been exceeded."""
        return context.retry_count >= self.max_retries
    
    def _is_error_retryable(self, context: RecoveryContext) -> bool:
        """Check if error type is retryable."""
        if isinstance(context.error, ValueError):
            return False
        if context.severity == ErrorSeverity.CRITICAL:
            return False
        return True
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay before retry (exponential backoff)."""
        return min(self.base_delay * (2 ** retry_count), 30.0)


# Import CircuitBreaker from canonical location - CONSOLIDATED
from netra_backend.app.core.circuit_breaker import (
    CircuitBreaker as CoreCircuitBreaker,
)
from netra_backend.app.core.circuit_breaker_types import CircuitConfig


class ErrorRecoveryCircuitBreaker(CoreCircuitBreaker):
    """Specialized circuit breaker for error recovery operations."""
    
    def __init__(self, 
                 failure_threshold: int = 5, 
                 timeout: int = 60,
                 name: str = "error_recovery_circuit"):
        """Initialize circuit breaker with error recovery defaults."""
        config = self._create_circuit_config(name, failure_threshold, timeout)
        super().__init__(config)
    
    def _create_circuit_config(self, name: str, failure_threshold: int, timeout: int) -> CircuitConfig:
        """Create circuit configuration with recovery defaults."""
        return CircuitConfig(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=float(timeout),
            timeout_seconds=float(timeout)
        )
    
    def should_allow_request(self) -> bool:
        """Synchronous check if request should be allowed through."""
        return self.can_execute()
    
    def record_success(self) -> None:
        """Record successful operation synchronously."""
        super().record_success()
    
    def record_failure(self, error_type: str = "ErrorRecoveryFailure") -> None:
        """Record failed operation synchronously."""
        super().record_failure(error_type)


# Compatibility alias for legacy code
CircuitBreaker = ErrorRecoveryCircuitBreaker


class ErrorRecoveryManager:
    """Central manager for error recovery operations."""
    
    def __init__(self):
        """Initialize error recovery manager."""
        self._init_storage_attributes()
        self._setup_default_strategies()
    
    def _init_storage_attributes(self) -> None:
        """Initialize storage attributes for recovery manager."""
        self.compensation_actions: List[CompensationAction] = []
        self.retry_strategies: Dict[OperationType, RetryStrategy] = {}
        self.circuit_breakers: Dict[str, ErrorRecoveryCircuitBreaker] = {}
        self.active_operations: Dict[str, RecoveryContext] = {}
    
    def _setup_default_strategies(self) -> None:
        """Set up default retry strategies for different operation types."""
        database_strategies = self._create_database_strategies()
        service_strategies = self._create_service_strategies()
        self.retry_strategies = {**database_strategies, **service_strategies}
    
    def _create_database_strategies(self) -> Dict[OperationType, RetryStrategy]:
        """Create retry strategies for database operations."""
        return {
            OperationType.DATABASE_WRITE: RetryStrategy(max_retries=2, base_delay=0.5),
            OperationType.DATABASE_READ: RetryStrategy(max_retries=3, base_delay=0.1),
            OperationType.CACHE_OPERATION: RetryStrategy(max_retries=1, base_delay=0.1),
            OperationType.FILE_OPERATION: RetryStrategy(max_retries=2, base_delay=0.5)
        }
    
    def _create_service_strategies(self) -> Dict[OperationType, RetryStrategy]:
        """Create retry strategies for service operations."""
        return {
            OperationType.LLM_REQUEST: RetryStrategy(max_retries=3, base_delay=2.0),
            OperationType.WEBSOCKET_SEND: RetryStrategy(max_retries=1, base_delay=0.1),
            OperationType.EXTERNAL_API: RetryStrategy(max_retries=3, base_delay=1.0),
            OperationType.AGENT_EXECUTION: RetryStrategy(max_retries=2, base_delay=1.0)
        }
    
    def register_compensation_action(self, action: CompensationAction) -> None:
        """Register a compensation action."""
        self.compensation_actions.append(action)
    
    def get_circuit_breaker(self, service_name: str) -> ErrorRecoveryCircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = ErrorRecoveryCircuitBreaker(
                name=f"recovery_{service_name}"
            )
        return self.circuit_breakers[service_name]


class RecoveryExecutor:
    """Executes recovery operations."""
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        """Initialize with recovery manager."""
        self.recovery_manager = recovery_manager
    
    async def attempt_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Attempt to recover from an error."""
        try:
            circuit_result = self._check_circuit_breaker(context)
            if circuit_result:
                return circuit_result
            return await self._execute_recovery_strategy(context)
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return self._create_abort_result(str(e))
    
    def _check_circuit_breaker(self, context: RecoveryContext) -> Optional[RecoveryResult]:
        """Check circuit breaker state and return result if blocked."""
        circuit_breaker = self._get_circuit_breaker(context)
        if not circuit_breaker.should_allow_request():
            return self._create_circuit_break_result()
        return None
    
    def _create_circuit_break_result(self) -> RecoveryResult:
        """Create circuit breaker result."""
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.CIRCUIT_BREAK,
            circuit_broken=True
        )
    
    async def _execute_recovery_strategy(self, context: RecoveryContext) -> RecoveryResult:
        """Execute recovery strategy (retry, compensation, or abort)."""
        if self._should_retry(context):
            return await self._execute_retry(context)
        compensation_result = await self._execute_compensation(context)
        if compensation_result:
            return self._create_compensation_result()
        return self._create_abort_result(f"No recovery possible for {context.operation_id}")
    
    def _create_compensation_result(self) -> RecoveryResult:
        """Create compensation recovery result."""
        return RecoveryResult(
            success=True,
            action_taken=RecoveryAction.COMPENSATE,
            compensation_required=True
        )
    
    def _create_abort_result(self, error_message: str) -> RecoveryResult:
        """Create abort recovery result."""
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.ABORT,
            error_message=error_message
        )
    
    def _get_circuit_breaker(self, context: RecoveryContext) -> ErrorRecoveryCircuitBreaker:
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
        return self._create_retry_result()
    
    def _create_retry_result(self) -> RecoveryResult:
        """Create retry recovery result."""
        return RecoveryResult(
            success=True,
            action_taken=RecoveryAction.RETRY
        )
    
    async def _execute_compensation(self, context: RecoveryContext) -> bool:
        """Execute applicable compensation actions."""
        compensation_success = True
        applicable_actions = self._get_applicable_actions(context)
        for action in applicable_actions:
            action_result = await self._execute_single_compensation(action, context)
            compensation_success = compensation_success and action_result
        return compensation_success
    
    def _get_applicable_actions(self, context: RecoveryContext) -> List[CompensationAction]:
        """Get compensation actions that can handle this context."""
        return [action for action in self.recovery_manager.compensation_actions
                if action.can_compensate(context)]
    
    async def _execute_single_compensation(self, action: CompensationAction, context: RecoveryContext) -> bool:
        """Execute a single compensation action with error handling."""
        try:
            result = await action.execute(context)
            if not result:
                logger.warning(f"Compensation action failed: {type(action).__name__}")
            return result
        except Exception as e:
            logger.error(f"Compensation action error: {e}")
            return False


# Global recovery manager instance
recovery_manager = ErrorRecoveryManager()
recovery_executor = RecoveryExecutor(recovery_manager)