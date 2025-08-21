"""Compensation registry and handlers for transaction rollback.

Manages compensation handlers for different operation types
to enable proper transaction rollback.
"""

from typing import Dict, Optional, Callable, Awaitable

from app.core.error_recovery import OperationType
from app.logging_config import central_logger
from netra_backend.app.types import Operation, OperationState

logger = central_logger.get_logger(__name__)


class CompensationRegistry:
    """Registry for compensation handlers."""
    
    def __init__(self):
        """Initialize compensation registry."""
        self.handlers: Dict[OperationType, Callable] = {}
    
    def register(self, operation_type: OperationType, handler: Callable):
        """Register compensation handler for operation type."""
        self.handlers[operation_type] = handler
        logger.debug(f"Registered compensation handler for {operation_type}")
    
    def get_handler(self, operation_type: OperationType) -> Optional[Callable]:
        """Get compensation handler for operation type."""
        return self.handlers.get(operation_type)


class CompensationExecutor:
    """Executes compensation for operations."""
    
    def __init__(self, registry: CompensationRegistry):
        """Initialize compensation executor."""
        self.registry = registry
    
    async def compensate_operation(self, operation: Operation) -> None:
        """Execute compensation for completed operation."""
        handler = self._get_handler_for_operation(operation)
        if handler:
            await self._execute_compensation(handler, operation)
        else:
            self._log_missing_handler(operation)
    
    def _get_handler_for_operation(self, operation: Operation) -> Optional[Callable]:
        """Get compensation handler for operation."""
        return self.registry.get_handler(operation.operation_type)
    
    async def _execute_compensation(self, handler: Callable, operation: Operation) -> None:
        """Execute compensation handler with error handling."""
        try:
            await handler(operation)
            self._mark_operation_compensated(operation)
            logger.debug(f"Compensated operation: {operation.operation_id}")
        except Exception as e:
            self._log_compensation_error(operation, e)
    
    def _mark_operation_compensated(self, operation: Operation) -> None:
        """Mark operation as compensated."""
        operation.state = OperationState.COMPENSATED
    
    def _log_missing_handler(self, operation: Operation) -> None:
        """Log missing handler warning."""
        logger.warning(f"No compensation handler for {operation.operation_type}")
    
    def _log_compensation_error(self, operation: Operation, error: Exception) -> None:
        """Log compensation error."""
        logger.error(f"Compensation failed for {operation.operation_id}: {error}")


class DefaultHandlers:
    """Default compensation handlers."""
    
    async def compensate_postgres_write(self, operation: Operation) -> None:
        """Compensate PostgreSQL write operation."""
        # PostgreSQL compensation is handled by transaction rollback
        logger.debug(f"PostgreSQL write compensation: {operation.operation_id}")
    
    async def compensate_postgres_read(self, operation: Operation) -> None:
        """Compensate PostgreSQL read operation."""
        # Read operations typically don't need compensation
        logger.debug(f"PostgreSQL read compensation: {operation.operation_id}")


def create_compensation_system() -> tuple[CompensationRegistry, CompensationExecutor]:
    """Create compensation system with default handlers."""
    registry = CompensationRegistry()
    executor = CompensationExecutor(registry)
    
    # Register default handlers
    handlers = DefaultHandlers()
    registry.register(OperationType.DATABASE_WRITE, handlers.compensate_postgres_write)
    registry.register(OperationType.DATABASE_READ, handlers.compensate_postgres_read)
    
    return registry, executor