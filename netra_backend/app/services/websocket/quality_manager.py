"""WebSocket Quality Manager - Main coordinator for quality-enhanced WebSocket handling"""

from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.quality_enhanced_start_handler import (
    QualityEnhancedStartAgentHandler,
)
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)
from netra_backend.app.services.websocket.quality_alert_handler import (
    QualityAlertHandler,
)
from netra_backend.app.services.websocket.quality_metrics_handler import (
    QualityMetricsHandler,
)
from netra_backend.app.services.websocket.quality_report_handler import (
    QualityReportHandler,
)
from netra_backend.app.services.websocket.quality_validation_handler import (
    QualityValidationHandler,
)
from netra_backend.app.ws_manager import manager

logger = central_logger.get_logger(__name__)


class WebSocketQualityManager:
    """Manager for quality-enhanced WebSocket handling"""
    
    def __init__(self, supervisor, db_session_factory):
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
        self._initialize_services()
        self._initialize_handlers()
        
    def _initialize_services(self) -> None:
        """Initialize quality services."""
        self.quality_gate_service = QualityGateService()
        self.monitoring_service = QualityMonitoringService()
        
    def _initialize_handlers(self) -> None:
        """Initialize message handlers."""
        self.handlers = {
            "start_agent": self._create_start_agent_handler(),
            "get_quality_metrics": self._create_metrics_handler(),
            "subscribe_quality_alerts": self._create_alert_handler(),
            "validate_content": self._create_validation_handler(),
            "generate_quality_report": self._create_report_handler()
        }

    def _create_start_agent_handler(self) -> QualityEnhancedStartAgentHandler:
        """Create enhanced start agent handler."""
        return QualityEnhancedStartAgentHandler(
            self.supervisor, self.db_session_factory, self.quality_gate_service
        )

    def _create_metrics_handler(self) -> QualityMetricsHandler:
        """Create quality metrics handler."""
        return QualityMetricsHandler(self.monitoring_service)

    def _create_alert_handler(self) -> QualityAlertHandler:
        """Create quality alert handler."""
        return QualityAlertHandler(self.monitoring_service)

    def _create_validation_handler(self) -> QualityValidationHandler:
        """Create quality validation handler."""
        return QualityValidationHandler(self.quality_gate_service)

    def _create_report_handler(self) -> QualityReportHandler:
        """Create quality report handler."""
        return QualityReportHandler(self.monitoring_service)
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Route message to appropriate handler"""
        message_type = message.get("type")
        if message_type in self.handlers:
            handler = self.handlers[message_type]
            await handler.handle(user_id, message.get("payload", {}))
        else:
            await self._handle_unknown_message(user_id, message_type)

    async def _handle_unknown_message(self, user_id: str, message_type: str) -> None:
        """Handle unknown message type."""
        logger.warning(f"Unknown message type: {message_type}")
        await manager.send_error(user_id, f"Unknown message type: {message_type}")
    
    async def broadcast_quality_update(self, update: Dict[str, Any]) -> None:
        """Broadcast quality update to all subscribers"""
        subscribers = self.monitoring_service.subscribers
        for user_id in subscribers:
            await self._send_update_to_subscriber(user_id, update)

    async def _send_update_to_subscriber(self, user_id: str, update: Dict[str, Any]) -> None:
        """Send quality update to a subscriber."""
        try:
            message = self._build_update_message(update)
            await manager.send_message(user_id, message)
        except Exception as e:
            logger.error(f"Error broadcasting to {user_id}: {str(e)}")

    def _build_update_message(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Build quality update message."""
        return {"type": "quality_update", "payload": update}

    async def broadcast_quality_alert(self, alert: Dict[str, Any]) -> None:
        """Broadcast quality alert to all subscribers"""
        subscribers = self.monitoring_service.subscribers
        for user_id in subscribers:
            await self._send_alert_to_subscriber(user_id, alert)

    async def _send_alert_to_subscriber(self, user_id: str, alert: Dict[str, Any]) -> None:
        """Send quality alert to a single subscriber."""
        try:
            alert_message = self._build_alert_message(alert)
            await manager.send_message(user_id, alert_message)
        except Exception as e:
            logger.error(f"Error broadcasting alert to {user_id}: {str(e)}")

    def _build_alert_message(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Build alert message for broadcasting."""
        return {
            "type": "quality_alert",
            "payload": {
                **alert,
                "severity": alert.get("severity", "info")
            }
        }