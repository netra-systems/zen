"""Quality message router.

Coordinates all quality-related WebSocket message handlers.
Follows 450-line limit with 25-line function limit.
"""

from typing import Any, Dict
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

from netra_backend.app.logging_config import central_logger
from netra_backend.app.dependencies import get_user_execution_context
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
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

logger = central_logger.get_logger(__name__)


class QualityMessageRouter:
    """Router for all quality-related WebSocket messages."""
    
    def __init__(self, supervisor, db_session_factory, 
                 quality_gate_service: QualityGateService,
                 monitoring_service: QualityMonitoringService):
        """Initialize quality message router."""
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
        self.quality_gate_service = quality_gate_service
        self.monitoring_service = monitoring_service
        self.handlers = self._initialize_handlers()
    
    def _initialize_handlers(self) -> Dict[str, Any]:
        """Initialize all quality message handlers."""
        return {
            "get_quality_metrics": self._create_metrics_handler(),
            "subscribe_quality_alerts": self._create_alert_handler(),
            "start_agent": self._create_enhanced_start_handler(),
            "validate_content": self._create_validation_handler(),
            "generate_quality_report": self._create_report_handler()
        }

    def _create_metrics_handler(self) -> QualityMetricsHandler:
        """Create quality metrics handler."""
        return QualityMetricsHandler(self.monitoring_service)

    def _create_alert_handler(self) -> QualityAlertHandler:
        """Create quality alert handler."""
        return QualityAlertHandler(self.monitoring_service)

    def _create_enhanced_start_handler(self) -> QualityEnhancedStartAgentHandler:
        """Create enhanced start agent handler."""
        return QualityEnhancedStartAgentHandler(
            self.supervisor, 
            self.db_session_factory, 
            self.quality_gate_service
        )

    def _create_validation_handler(self) -> QualityValidationHandler:
        """Create validation handler."""
        return QualityValidationHandler(self.quality_gate_service)

    def _create_report_handler(self) -> QualityReportHandler:
        """Create report handler."""
        return QualityReportHandler(self.monitoring_service)
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Route message to appropriate handler."""
        message_type = message.get("type")
        
        # Extract and store context IDs for session continuity
        self._current_thread_id = message.get("thread_id")
        self._current_run_id = message.get("run_id")
        
        if self._is_valid_message_type(message_type):
            await self._route_to_handler(user_id, message, message_type)
        else:
            await self._handle_unknown_message_type(user_id, message_type)

    def _is_valid_message_type(self, message_type: str) -> bool:
        """Check if message type is valid."""
        return message_type in self.handlers

    async def _route_to_handler(self, user_id: str, message: Dict[str, Any], message_type: str) -> None:
        """Route message to specific handler."""
        handler = self.handlers[message_type]
        payload = message.get("payload", {})
        
        # Ensure context IDs are available to handlers for session continuity
        if self._current_thread_id:
            payload["thread_id"] = self._current_thread_id
        if self._current_run_id:
            payload["run_id"] = self._current_run_id
        
        await handler.handle(user_id, payload)

    async def _handle_unknown_message_type(self, user_id: str, message_type: str) -> None:
        """Handle unknown message type."""
        logger.warning(f"Unknown message type: {message_type}")
        error_message = f"Unknown message type: {message_type}"
        try:
            # Use existing context IDs instead of generating new ones
            thread_id = getattr(self, '_current_thread_id', None)
            run_id = getattr(self, '_current_run_id', None)
            
            if not thread_id or not run_id:
                thread_id = UnifiedIdGenerator.generate_base_id("thread")
                run_id = UnifiedIdGenerator.generate_base_id("run")
            
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            manager = create_websocket_manager(user_context)
            await manager.send_to_user({"type": "error", "message": error_message})
        except Exception as e:
            logger.error(f"Failed to send error message to user {user_id}: {e}")
    
    async def broadcast_quality_update(self, update: Dict[str, Any]) -> None:
        """Broadcast quality update to all subscribers."""
        subscribers = self.monitoring_service.subscribers
        
        for user_id in subscribers:
            await self._send_update_to_subscriber(user_id, update)

    async def _send_update_to_subscriber(self, user_id: str, update: Dict[str, Any]) -> None:
        """Send quality update to a single subscriber."""
        try:
            message = self._build_update_message(update)
            
            # Use existing context IDs instead of generating new ones
            thread_id = getattr(self, '_current_thread_id', None)
            run_id = getattr(self, '_current_run_id', None)
            
            if not thread_id or not run_id:
                thread_id = UnifiedIdGenerator.generate_base_id("thread")
                run_id = UnifiedIdGenerator.generate_base_id("run")
            
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            manager = create_websocket_manager(user_context)
            await manager.send_to_user(message)
        except Exception as e:
            logger.error(f"Error broadcasting to {user_id}: {str(e)}")

    def _build_update_message(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Build quality update message."""
        return {
            "type": "quality_update",
            "payload": update
        }
    
    async def broadcast_quality_alert(self, alert: Dict[str, Any]) -> None:
        """Broadcast quality alert to all subscribers."""
        subscribers = self.monitoring_service.subscribers
        
        for user_id in subscribers:
            await self._send_alert_to_subscriber(user_id, alert)

    async def _send_alert_to_subscriber(self, user_id: str, alert: Dict[str, Any]) -> None:
        """Send quality alert to a single subscriber."""
        try:
            alert_message = self._build_alert_message(alert)
            
            # Use existing context IDs instead of generating new ones
            thread_id = getattr(self, '_current_thread_id', None)
            run_id = getattr(self, '_current_run_id', None)
            
            if not thread_id or not run_id:
                thread_id = UnifiedIdGenerator.generate_base_id("thread")
                run_id = UnifiedIdGenerator.generate_base_id("run")
            
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            manager = create_websocket_manager(user_context)
            await manager.send_to_user(alert_message)
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