"""Agent recovery strategy functionality.

This module provides recovery strategies and recovery attempt management.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from netra_backend.app.core.agent_reliability_types import AgentError
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentRecoveryManager:
    """Manager for agent recovery strategies and execution."""
    
    def __init__(self):
        self.recovery_strategies: Dict[str, Callable] = {}
        self._register_default_recovery_strategies()

    def register_recovery_strategy(
        self,
        operation_name: str,
        recovery_func: Callable[[Exception, Optional[Dict[str, Any]]], Awaitable[Optional[Any]]]
    ) -> None:
        """Register a recovery strategy for a specific operation."""
        self.recovery_strategies[operation_name] = recovery_func

    def _register_default_recovery_strategies(self) -> None:
        """Register default recovery strategies."""
        self.register_recovery_strategy("llm_call", self._default_llm_recovery)
        self.register_recovery_strategy("database_query", self._default_db_recovery)
        self.register_recovery_strategy("api_call", self._default_api_recovery)

    async def attempt_operation_recovery(
        self,
        operation_name: str,
        error: Exception,
        context: Optional[Dict[str, Any]],
        error_history: List[AgentError]
    ) -> Optional[Any]:
        """Attempt to recover from operation failure."""
        if operation_name not in self.recovery_strategies:
            return None
        return await self._execute_recovery_strategy(operation_name, error, context, error_history)

    async def _execute_recovery_strategy(
        self, operation_name: str, error: Exception, context: Optional[Dict[str, Any]], error_history: List[AgentError]
    ) -> Optional[Any]:
        """Execute recovery strategy for operation."""
        try:
            recovery_func = self.recovery_strategies[operation_name]
            recovery_result = await recovery_func(error, context)
            self._update_recovery_status(recovery_result, error_history)
            return recovery_result
        except Exception as recovery_error:
            logger.error(f"Recovery failed for {operation_name}: {recovery_error}")
            return None

    def _update_recovery_status(self, recovery_result: Optional[Any], error_history: List[AgentError]) -> None:
        """Update error record with recovery status."""
        if error_history:
            error_history[-1].recovery_attempted = True
            error_history[-1].recovery_successful = recovery_result is not None

    async def _default_llm_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for LLM failures."""
        return {
            "status": "fallback",
            "message": "Operation completed with limited functionality",
            "error": str(error),
            "fallback_used": True
        }

    async def _default_db_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for database failures."""
        return {
            "data": [],
            "cached": True,
            "error": str(error),
            "fallback_used": True
        }

    async def _default_api_recovery(self, error: Exception, context: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Default recovery strategy for API failures."""
        return {
            "result": "limited",
            "data": {},
            "error": str(error),
            "fallback_used": True
        }