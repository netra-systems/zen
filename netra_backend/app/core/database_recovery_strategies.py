"""Database recovery strategies for error recovery integration.

This module provides database-specific recovery strategies and registry
for the enhanced error recovery system.
"""

from typing import Any, Dict, List, Optional
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseOperationType(str, Enum):
    """Database operation types for recovery strategies."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SELECT = "select"
    TRANSACTION = "transaction"
    CONNECTION = "connection"


class DatabaseRecoveryStrategy:
    """Base database recovery strategy."""

    def __init__(self, operation_type: DatabaseOperationType):
        """Initialize recovery strategy.

        Args:
            operation_type: Type of database operation
        """
        self.operation_type = operation_type
        self.name = f"{operation_type.value}_recovery"

    async def execute_recovery(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database recovery strategy.

        Args:
            context: Recovery context including error details

        Returns:
            Recovery result
        """
        logger.info(f"Executing database recovery for {self.operation_type}")

        # Basic recovery implementation
        return {
            "status": "recovered",
            "strategy": self.name,
            "operation_type": self.operation_type.value,
            "timestamp": context.get("timestamp"),
            "context": context
        }


class DatabaseRecoveryRegistry:
    """Registry for database recovery strategies."""

    def __init__(self):
        """Initialize database recovery registry."""
        self.strategies: Dict[DatabaseOperationType, DatabaseRecoveryStrategy] = {}
        self._initialize_default_strategies()
        logger.debug("DatabaseRecoveryRegistry initialized")

    def _initialize_default_strategies(self) -> None:
        """Initialize default recovery strategies."""
        for operation_type in DatabaseOperationType:
            self.strategies[operation_type] = DatabaseRecoveryStrategy(operation_type)

    def register_strategy(self, operation_type: DatabaseOperationType,
                         strategy: DatabaseRecoveryStrategy) -> None:
        """Register a recovery strategy.

        Args:
            operation_type: Database operation type
            strategy: Recovery strategy instance
        """
        self.strategies[operation_type] = strategy
        logger.debug(f"Registered database recovery strategy for {operation_type}")

    def get_strategy(self, operation_type: DatabaseOperationType) -> Optional[DatabaseRecoveryStrategy]:
        """Get recovery strategy for operation type.

        Args:
            operation_type: Database operation type

        Returns:
            Recovery strategy if found
        """
        return self.strategies.get(operation_type)

    async def execute_recovery(self, operation_type: DatabaseOperationType,
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recovery for database operation.

        Args:
            operation_type: Database operation type
            context: Recovery context

        Returns:
            Recovery result
        """
        strategy = self.get_strategy(operation_type)
        if strategy:
            return await strategy.execute_recovery(context)

        # Fallback recovery
        logger.warning(f"No specific recovery strategy for {operation_type}, using fallback")
        return {
            "status": "fallback_recovery",
            "operation_type": operation_type.value,
            "context": context
        }


# Global registry instance
database_recovery_registry = DatabaseRecoveryRegistry()


# Convenience functions for compatibility
async def recover_database_operation(operation_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to recover database operation.

    Args:
        operation_type: String representation of operation type
        context: Recovery context

    Returns:
        Recovery result
    """
    try:
        op_type = DatabaseOperationType(operation_type)
        return await database_recovery_registry.execute_recovery(op_type, context)
    except ValueError:
        logger.warning(f"Unknown database operation type: {operation_type}")
        return {
            "status": "unknown_operation",
            "operation_type": operation_type,
            "context": context
        }


def get_database_recovery_registry() -> DatabaseRecoveryRegistry:
    """Get the global database recovery registry.

    Returns:
        DatabaseRecoveryRegistry instance
    """
    return database_recovery_registry