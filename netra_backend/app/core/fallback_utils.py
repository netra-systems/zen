"""Unified fallback strategy utilities for agents."""
from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FallbackStrategy:
    """Unified fallback strategy for agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
    
    async def execute_with_fallback(
        self,
        primary_operation: Callable[[], Awaitable[Any]],
        fallback_operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        run_id: str
    ) -> Any:
        """Execute operation with fallback handling."""
        try:
            return await primary_operation()
        except Exception as e:
            logger.warning(
                f"{self.agent_name} primary {operation_name} failed for run_id: {run_id}. "
                f"Error: {e}. Using fallback."
            )
            return await fallback_operation()
    
    def create_default_fallback_result(self, operation_type: str, **kwargs: Any) -> Dict[str, Any]:
        """Create standardized fallback result.
        
        WARNING: This creates results that look like success but are actually failures.
        See AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md for why this is dangerous.
        """
        # Log at ERROR level so failures are visible
        logger.error(
            f"FALLBACK ACTIVE: {self.agent_name} using fallback for {operation_type} - "
            f"this indicates a failure that is being masked. Original error: {kwargs.get('error', 'Unknown')}"
        )
        
        return {
            "fallback_used": True,
            "operation_type": operation_type,
            "agent": self.agent_name,
            "message": f"Fallback result for {operation_type}",
            "_degraded": True,  # Make degradation explicit
            "_error_masked": True,  # Flag that an error is being hidden
            "metadata": kwargs.get("metadata", {}),
            **kwargs
        }


def create_agent_fallback_strategy(agent_name: str) -> FallbackStrategy:
    """Create fallback strategy for an agent."""
    return FallbackStrategy(agent_name)


async def safe_websocket_send(
    websocket_manager: Any,
    user_id: str,
    message_data: Dict[str, Any],
    operation_description: str = "WebSocket operation"
) -> bool:
    """Safely send WebSocket message with fallback."""
    if not websocket_manager:
        return False
    
    try:
        await websocket_manager.send_to_user(user_id, message_data)
        return True
    except Exception as e:
        # CHANGED: Elevated from DEBUG to ERROR per AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
        # WebSocket failures are critical for user experience - they must be visible
        logger.error(f"WebSocket {operation_description} failed: {e}", exc_info=True)
        return False