"""Unified fallback strategy utilities for agents."""
from typing import Dict, Any, Callable, Awaitable, Optional
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
        """Create standardized fallback result."""
        return {
            "fallback_used": True,
            "operation_type": operation_type,
            "agent": self.agent_name,
            "message": f"Fallback result for {operation_type}",
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
        await websocket_manager.send_message(user_id, message_data)
        return True
    except Exception as e:
        logger.debug(f"WebSocket {operation_description} failed: {e}")
        return False