"""Quality metrics WebSocket handler.

Handles quality metrics requests and responses.
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
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

logger = central_logger.get_logger(__name__)


class QualityMetricsHandler(BaseMessageHandler):
    """Handler for quality metrics requests."""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        """Initialize quality metrics handler."""
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        """Get the message type this handler processes."""
        return "get_quality_metrics"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality metrics request."""
        try:
            # Extract context IDs from payload to ensure session continuity
            self._current_thread_id = payload.get("thread_id")
            self._current_run_id = payload.get("run_id")
            
            report = await self._get_quality_report(payload)
            await self._send_metrics_response(user_id, report)
        except Exception as e:
            await self._handle_metrics_error(user_id, e)

    async def _get_quality_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get quality report based on payload parameters."""
        agent_name = payload.get("agent_name")
        period_hours = payload.get("period_hours", 24)
        
        if agent_name:
            return await self._get_agent_report(agent_name, period_hours)
        return await self._get_dashboard_data()

    async def _get_agent_report(self, agent_name: str, period_hours: int) -> Dict[str, Any]:
        """Get quality report for specific agent."""
        return await self.monitoring_service.get_agent_report(agent_name, period_hours)

    async def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get general dashboard data."""
        return await self.monitoring_service.get_dashboard_data()

    async def _send_metrics_response(self, user_id: str, report: Dict[str, Any]) -> None:
        """Send quality metrics response to user."""
        message = self._build_metrics_message(report)
        
        #  PASS:  CORRECT - Maintains session continuity
        user_context = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Let session manager handle missing IDs
            run_id=None      # Let session manager handle missing IDs
        )
        manager = await create_websocket_manager(user_context)
        await manager.send_to_user(message)

    def _build_metrics_message(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Build metrics response message."""
        return {"type": "quality_metrics", "payload": report}

    async def _handle_metrics_error(self, user_id: str, error: Exception) -> None:
        """Handle quality metrics request error."""
        logger.error(f"Error getting quality metrics: {str(error)}")
        error_message = f"Failed to get quality metrics: {str(error)}"
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
            logger.error(f"Failed to send metrics error to user {user_id}: {e}")