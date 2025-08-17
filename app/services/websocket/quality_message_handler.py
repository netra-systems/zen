"""Quality-Enhanced WebSocket Message Handler

This module extends the WebSocket message handling with quality metrics tracking
and real-time quality reporting.
"""

from typing import Dict, Any, Optional
from datetime import datetime, UTC
import json

from app.logging_config import central_logger
from app.services.websocket.message_handler import BaseMessageHandler, StartAgentHandler
from app.services.quality_gate_service import QualityGateService, ContentType
from app.services.quality_monitoring_service import QualityMonitoringService
from app.ws_manager import manager
from app.services.database.unit_of_work import get_unit_of_work

logger = central_logger.get_logger(__name__)


class QualityMetricsHandler(BaseMessageHandler):
    """Handler for quality metrics requests"""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        return "get_quality_metrics"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality metrics request"""
        try:
            report = await self._get_quality_report(payload)
            await self._send_metrics_response(user_id, report)
        except Exception as e:
            await self._handle_metrics_error(user_id, e)

    async def _get_quality_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get quality report based on payload parameters."""
        agent_name = payload.get("agent_name")
        period_hours = payload.get("period_hours", 24)
        if agent_name:
            return await self.monitoring_service.get_agent_report(agent_name, period_hours)
        return await self.monitoring_service.get_dashboard_data()

    async def _send_metrics_response(self, user_id: str, report: Dict[str, Any]) -> None:
        """Send quality metrics response to user."""
        await manager.send_message(
            user_id,
            {"type": "quality_metrics", "payload": report}
        )

    async def _handle_metrics_error(self, user_id: str, error: Exception) -> None:
        """Handle quality metrics request error."""
        logger.error(f"Error getting quality metrics: {str(error)}")
        await manager.send_error(user_id, f"Failed to get quality metrics: {str(error)}")


class QualityAlertHandler(BaseMessageHandler):
    """Handler for quality alert subscriptions"""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        return "subscribe_quality_alerts"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality alert subscription"""
        try:
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

    async def _handle_subscribe_action(self, user_id: str) -> None:
        """Handle subscribe action for quality alerts."""
        await self.monitoring_service.subscribe_to_updates(user_id)
        await manager.send_message(
            user_id,
            {"type": "quality_alerts_subscribed", "payload": {"status": "subscribed"}}
        )

    async def _handle_unsubscribe_action(self, user_id: str) -> None:
        """Handle unsubscribe action for quality alerts."""
        await self.monitoring_service.unsubscribe_from_updates(user_id)
        await manager.send_message(
            user_id,
            {"type": "quality_alerts_unsubscribed", "payload": {"status": "unsubscribed"}}
        )

    async def _handle_subscription_error(self, user_id: str, error: Exception) -> None:
        """Handle quality alert subscription error."""
        logger.error(f"Error handling quality alert subscription: {str(error)}")
        await manager.send_error(user_id, f"Failed to handle subscription: {str(error)}")


class QualityEnhancedStartAgentHandler(StartAgentHandler):
    """Enhanced start_agent handler with quality tracking"""
    
    def __init__(self, supervisor, db_session_factory, quality_gate_service: QualityGateService):
        super().__init__(supervisor, db_session_factory)
        self.quality_gate_service = quality_gate_service
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle start_agent message with quality tracking"""
        try:
            start_time = datetime.now(UTC)
            await super().handle(user_id, payload)
            await self._send_quality_tracking_update(user_id, start_time)
        except Exception as e:
            self._log_handler_error(e)
            raise

    async def _send_quality_tracking_update(self, user_id: str, start_time: datetime) -> None:
        """Send quality tracking update after agent start."""
        if not hasattr(self.supervisor, 'get_quality_dashboard'):
            return
        response_time = self._calculate_response_time(start_time)
        quality_data = await self._get_enhanced_quality_data(response_time)
        await self._send_quality_update_message(user_id, quality_data)

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
        await manager.send_message(
            user_id,
            {"type": "quality_update", "payload": quality_data}
        )

    def _log_handler_error(self, error: Exception) -> None:
        """Log error in quality-enhanced handler."""
        logger.error(f"Error in quality-enhanced handler: {str(error)}")


class QualityValidationHandler(BaseMessageHandler):
    """Handler for on-demand quality validation"""
    
    def __init__(self, quality_gate_service: QualityGateService):
        self.quality_gate_service = quality_gate_service
    
    def get_message_type(self) -> str:
        return "validate_content"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle content validation request"""
        try:
            validation_params = self._extract_validation_params(payload)
            result = await self._validate_content_with_params(user_id, validation_params)
            await self._send_validation_result(user_id, result)
        except Exception as e:
            await self._handle_validation_error(user_id, e)

    def _extract_validation_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract validation parameters from payload."""
        content = payload.get("content", "")
        content_type_str = payload.get("content_type", "general")
        strict_mode = payload.get("strict_mode", False)
        content_type = self._map_content_type(content_type_str)
        return {"content": content, "content_type": content_type, "strict_mode": strict_mode}

    def _map_content_type(self, content_type_str: str) -> ContentType:
        """Map string to ContentType enum."""
        content_type_map = self._get_content_type_mapping()
        return content_type_map.get(content_type_str, ContentType.GENERAL)

    def _get_content_type_mapping(self) -> Dict[str, ContentType]:
        """Get content type string to enum mapping."""
        return {
            "optimization": ContentType.OPTIMIZATION,
            "data_analysis": ContentType.DATA_ANALYSIS,
            "action_plan": ContentType.ACTION_PLAN,
            "report": ContentType.REPORT,
            "triage": ContentType.TRIAGE,
            "error": ContentType.ERROR_MESSAGE,
            "general": ContentType.GENERAL
        }

    async def _validate_content_with_params(self, user_id: str, params: Dict[str, Any]):
        """Validate content using extracted parameters."""
        return await self.quality_gate_service.validate_content(
            content=params["content"],
            content_type=params["content_type"],
            context={"user_id": user_id},
            strict_mode=params["strict_mode"]
        )

    async def _send_validation_result(self, user_id: str, result) -> None:
        """Send validation result to user."""
        payload = self._build_validation_payload(result)
        await manager.send_message(user_id, {"type": "content_validated", "payload": payload})

    def _build_validation_payload(self, result) -> Dict[str, Any]:
        """Build validation result payload."""
        return {
            "passed": result.passed,
            "metrics": self._build_metrics_payload(result.metrics),
            "retry_suggested": result.retry_suggested
        }

    def _build_metrics_payload(self, metrics) -> Dict[str, Any]:
        """Build metrics payload from validation result."""
        return {
            "overall_score": metrics.overall_score,
            "quality_level": metrics.quality_level.value,
            "specificity": metrics.specificity_score,
            "actionability": metrics.actionability_score,
            "quantification": metrics.quantification_score,
            "issues": metrics.issues,
            "suggestions": metrics.suggestions
        }

    async def _handle_validation_error(self, user_id: str, error: Exception) -> None:
        """Handle content validation error."""
        logger.error(f"Error validating content: {str(error)}")
        await manager.send_error(user_id, f"Failed to validate content: {str(error)}")


class QualityReportHandler(BaseMessageHandler):
    """Handler for generating quality reports"""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        return "generate_quality_report"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality report generation request"""
        try:
            report_type = payload.get("report_type", "summary")
            period = payload.get("period", "day")
            
            # Generate report based on type
            if report_type == "summary":
                report_data = await self.monitoring_service.get_dashboard_data()
            elif report_type == "detailed":
                # Get detailed reports for all agents
                agent_reports = {}
                for agent_name in ["TriageSubAgent", "DataSubAgent", "OptimizationsCoreSubAgent", 
                                 "ActionsToMeetGoalsSubAgent", "ReportingSubAgent"]:
                    agent_reports[agent_name] = await self.monitoring_service.get_agent_report(
                        agent_name, 
                        period_hours=24 if period == "day" else 168 if period == "week" else 24
                    )
                report_data = {
                    "summary": await self.monitoring_service.get_dashboard_data(),
                    "agents": agent_reports
                }
            else:
                report_data = {"error": "Unknown report type"}
            
            # Format as markdown report
            markdown_report = self._format_quality_report(report_data, report_type)
            
            await manager.send_message(
                user_id,
                {
                    "type": "quality_report_generated",
                    "payload": {
                        "report": markdown_report,
                        "raw_data": report_data,
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating quality report: {str(e)}")
            await manager.send_error(user_id, f"Failed to generate report: {str(e)}")
    
    def _format_quality_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Format quality data as markdown report"""
        report = f"# AI Quality Report\n\n"
        report += f"**Generated:** {datetime.now(UTC).isoformat()}\n"
        report += f"**Type:** {report_type.title()}\n\n"
        
        if "overall_stats" in data:
            stats = data["overall_stats"]
            report += "## Overall Statistics\n\n"
            report += f"- **Average Quality Score:** {stats.get('average_quality', 0):.2f}\n"
            report += f"- **Total Events:** {stats.get('total_events', 0)}\n"
            report += f"- **Active Alerts:** {stats.get('active_alerts', 0)}\n"
            report += f"- **Critical Alerts:** {stats.get('critical_alerts', 0)}\n\n"
        
        if "quality_distribution" in data:
            dist = data["quality_distribution"]
            report += "## Quality Distribution\n\n"
            for level, count in dist.items():
                report += f"- **{level}:** {count}\n"
            report += "\n"
        
        if "agent_profiles" in data:
            report += "## Agent Performance\n\n"
            for agent_name, profile in data["agent_profiles"].items():
                report += f"### {agent_name}\n"
                report += f"- Average Score: {profile.get('average_quality_score', 0):.2f}\n"
                report += f"- Total Requests: {profile.get('total_requests', 0)}\n"
                report += f"- Slop Detections: {profile.get('slop_detection_count', 0)}\n"
                if profile.get('issues'):
                    report += f"- Issues: {', '.join(profile['issues'])}\n"
                report += "\n"
        
        if "recent_alerts" in data:
            report += "## Recent Alerts\n\n"
            for alert in data["recent_alerts"][:5]:
                report += f"- **{alert['severity']}** [{alert['timestamp']}]: {alert['message']}\n"
            report += "\n"
        
        return report


class WebSocketQualityManager:
    """Manager for quality-enhanced WebSocket handling"""
    
    def __init__(self, supervisor, db_session_factory):
        self.supervisor = supervisor
        self.db_session_factory = db_session_factory
        
        # Initialize quality services
        self.quality_gate_service = QualityGateService()
        self.monitoring_service = QualityMonitoringService()
        
        # Initialize handlers
        self.handlers = {
            "start_agent": QualityEnhancedStartAgentHandler(
                supervisor, db_session_factory, self.quality_gate_service
            ),
            "get_quality_metrics": QualityMetricsHandler(self.monitoring_service),
            "subscribe_quality_alerts": QualityAlertHandler(self.monitoring_service),
            "validate_content": QualityValidationHandler(self.quality_gate_service),
            "generate_quality_report": QualityReportHandler(self.monitoring_service)
        }
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """Route message to appropriate handler"""
        message_type = message.get("type")
        
        if message_type in self.handlers:
            handler = self.handlers[message_type]
            await handler.handle(user_id, message.get("payload", {}))
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await manager.send_error(user_id, f"Unknown message type: {message_type}")
    
    async def broadcast_quality_update(self, update: Dict[str, Any]) -> None:
        """Broadcast quality update to all subscribers"""
        subscribers = self.monitoring_service.subscribers
        
        for user_id in subscribers:
            try:
                await manager.send_message(
                    user_id,
                    {
                        "type": "quality_update",
                        "payload": update
                    }
                )
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {str(e)}")
    
    async def broadcast_quality_alert(self, alert: Dict[str, Any]) -> None:
        """Broadcast quality alert to all subscribers"""
        subscribers = self.monitoring_service.subscribers
        
        for user_id in subscribers:
            try:
                await manager.send_message(
                    user_id,
                    {
                        "type": "quality_alert",
                        "payload": {
                            **alert,
                            "severity": alert.get("severity", "info")
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Error broadcasting alert to {user_id}: {str(e)}")