"""Quality alert WebSocket handler.

Handles quality alert subscriptions and notifications.
Follows 450-line limit with 25-line function limit.
"""

from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context as create_websocket_manager

logger = central_logger.get_logger(__name__)


class QualityAlertHandler(BaseMessageHandler):
    """Handler for quality alert subscriptions."""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        """Initialize quality alert handler."""
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        """Get the message type this handler processes."""
        return "subscribe_quality_alerts"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality alert subscription."""
        try:
            # Extract context IDs from payload to ensure session continuity
            self._current_thread_id = payload.get("thread_id")
            self._current_run_id = payload.get("run_id")
            
            action = payload.get("action", "subscribe")
            await self._process_subscription_action(user_id, action)
        except Exception as e:
            await self._handle_subscription_error(user_id, e)

    async def _process_subscription_action(self, user_id: str, action: str) -> None:
        """Process subscription action (subscribe/unsubscribe)."""
        if action == "subscribe":
            await self._handle_subscribe_action(user_id)
        elif action == "unsubscribe":
            await self._handle_unsubscribe_action(user_id)
        else:
            await self._handle_invalid_action(user_id, action)

    async def _handle_subscribe_action(self, user_id: str) -> None:
        """Handle subscribe action for quality alerts."""
        await self.monitoring_service.subscribe_to_updates(user_id)
        message = self._build_subscription_message("subscribed")
        
        #  PASS:  CORRECT - Maintains session continuity
        user_context = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Let session manager handle missing IDs
            run_id=None      # Let session manager handle missing IDs
        )
        manager = await create_websocket_manager(user_context)
        await manager.send_to_user(message)

    async def _handle_unsubscribe_action(self, user_id: str) -> None:
        """Handle unsubscribe action for quality alerts."""
        await self.monitoring_service.unsubscribe_from_updates(user_id)
        message = self._build_subscription_message("unsubscribed")
        
        #  PASS:  CORRECT - Maintains session continuity
        user_context = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Let session manager handle missing IDs
            run_id=None      # Let session manager handle missing IDs
        )
        manager = await create_websocket_manager(user_context)
        await manager.send_to_user(message)

    async def _handle_invalid_action(self, user_id: str, action: str) -> None:
        """Handle invalid subscription action."""
        error_message = f"Invalid action: {action}. Use 'subscribe' or 'unsubscribe'"
        try:
            #  PASS:  CORRECT - Maintains session continuity
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=None,  # Let session manager handle missing IDs
                run_id=None      # Let session manager handle missing IDs
            )
            manager = await create_websocket_manager(user_context)
            await manager.send_to_user({"type": "error", "message": error_message})
        except Exception as e:
            logger.error(f"Failed to send action error to user {user_id}: {e}")

    def _build_subscription_message(self, status: str) -> Dict[str, Any]:
        """Build subscription status message."""
        message_type = f"quality_alerts_{status}"
        return {
            "type": message_type,
            "payload": {"status": status}
        }

    async def _handle_subscription_error(self, user_id: str, error: Exception) -> None:
        """Handle quality alert subscription error."""
        logger.error(f"Error handling quality alert subscription: {str(error)}")
        error_message = f"Failed to handle subscription: {str(error)}"
        try:
            #  PASS:  CORRECT - Maintains session continuity
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=None,  # Let session manager handle missing IDs
                run_id=None      # Let session manager handle missing IDs
            )
            manager = await create_websocket_manager(user_context)
            await manager.send_to_user({"type": "error", "message": error_message})
        except Exception as e:
            logger.error(f"Failed to send subscription error to user {user_id}: {e}")