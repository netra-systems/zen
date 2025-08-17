"""Quality message handler facade.

Provides backward compatibility while using modular architecture.
Follows 300-line limit with 8-line function limit.
"""

from typing import Dict, Any
from app.services.quality_gate_service import QualityGateService
from app.services.quality_monitoring_service import QualityMonitoringService
from .quality_message_router import QualityMessageRouter
from .quality_metrics_handler import QualityMetricsHandler
from .quality_alert_handler import QualityAlertHandler
from .quality_enhanced_start_handler import QualityEnhancedStartAgentHandler
from .quality_validation_handler import QualityValidationHandler
from .quality_report_handler import QualityReportHandler


class QualityMessageRouter:
    """Router for all quality-related WebSocket messages."""
    
    def __init__(self, supervisor, db_session_factory, 
                 quality_gate_service: QualityGateService,
                 monitoring_service: QualityMonitoringService):
        """Initialize quality message router."""
        self.router = QualityMessageRouter(
            supervisor, db_session_factory, 
            quality_gate_service, monitoring_service
        )
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Route message to appropriate handler."""
        await self.router.handle_message(user_id, message)
    
    async def broadcast_quality_update(self, update: Dict[str, Any]) -> None:
        """Broadcast quality update to all subscribers."""
        await self.router.broadcast_quality_update(update)
    
    async def broadcast_quality_alert(self, alert: Dict[str, Any]) -> None:
        """Broadcast quality alert to all subscribers."""
        await self.router.broadcast_quality_alert(alert)