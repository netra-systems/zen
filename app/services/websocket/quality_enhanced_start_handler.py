"""Quality enhanced start agent WebSocket handler.

Enhanced start_agent handler with quality tracking.
Follows 300-line limit with 8-line function limit.
"""

from typing import Dict, Any
from datetime import datetime, UTC
from app.logging_config import central_logger
from app.services.websocket.message_handler import StartAgentHandler
from app.services.quality_gate_service import QualityGateService
from app.ws_manager import manager

logger = central_logger.get_logger(__name__)


class QualityEnhancedStartAgentHandler(StartAgentHandler):
    """Enhanced start_agent handler with quality tracking."""
    
    def __init__(self, supervisor, db_session_factory, quality_gate_service: QualityGateService):
        """Initialize enhanced start agent handler."""
        super().__init__(supervisor, db_session_factory)
        self.quality_gate_service = quality_gate_service
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle start_agent message with quality tracking."""
        try:
            start_time = datetime.now(UTC)
            await super().handle(user_id, payload)
            await self._send_quality_tracking_update(user_id, start_time)
        except Exception as e:
            self._log_handler_error(e)
            raise

    async def _send_quality_tracking_update(self, user_id: str, start_time: datetime) -> None:
        """Send quality tracking update after agent start."""
        if not self._has_quality_dashboard():
            return
        
        response_time = self._calculate_response_time(start_time)
        quality_data = await self._get_enhanced_quality_data(response_time)
        await self._send_quality_update_message(user_id, quality_data)

    def _has_quality_dashboard(self) -> bool:
        """Check if supervisor has quality dashboard capability."""
        return hasattr(self.supervisor, 'get_quality_dashboard')

    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time from start to now."""
        return (datetime.now(UTC) - start_time).total_seconds()

    async def _get_enhanced_quality_data(self, response_time: float) -> Dict[str, Any]:
        """Get quality data enhanced with response time."""
        quality_data = await self.supervisor.get_quality_dashboard()
        quality_data['response_time'] = response_time
        return quality_data

    async def _send_quality_update_message(self, user_id: str, quality_data: Dict[str, Any]) -> None:
        """Send quality update message to user."""
        message = self._build_quality_update_message(quality_data)
        await manager.send_message(user_id, message)

    def _build_quality_update_message(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build quality update message."""
        return {
            "type": "quality_update",
            "payload": quality_data
        }

    def _log_handler_error(self, error: Exception) -> None:
        """Log error in quality-enhanced handler."""
        logger.error(f"Error in quality-enhanced handler: {str(error)}")