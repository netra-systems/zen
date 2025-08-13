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
            agent_name = payload.get("agent_name")
            period_hours = payload.get("period_hours", 24)
            
            if agent_name:
                # Get specific agent report
                report = await self.monitoring_service.get_agent_report(agent_name, period_hours)
            else:
                # Get overall dashboard
                report = await self.monitoring_service.get_dashboard_data()
            
            await manager.send_message(
                user_id,
                {
                    "type": "quality_metrics",
                    "payload": report
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting quality metrics: {str(e)}")
            await manager.send_error(user_id, f"Failed to get quality metrics: {str(e)}")


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
            
            if action == "subscribe":
                await self.monitoring_service.subscribe_to_updates(user_id)
                await manager.send_message(
                    user_id,
                    {
                        "type": "quality_alerts_subscribed",
                        "payload": {"status": "subscribed"}
                    }
                )
            elif action == "unsubscribe":
                await self.monitoring_service.unsubscribe_from_updates(user_id)
                await manager.send_message(
                    user_id,
                    {
                        "type": "quality_alerts_unsubscribed",
                        "payload": {"status": "unsubscribed"}
                    }
                )
            
        except Exception as e:
            logger.error(f"Error handling quality alert subscription: {str(e)}")
            await manager.send_error(user_id, f"Failed to handle subscription: {str(e)}")


class QualityEnhancedStartAgentHandler(StartAgentHandler):
    """Enhanced start_agent handler with quality tracking"""
    
    def __init__(self, supervisor, db_session_factory, quality_gate_service: QualityGateService):
        super().__init__(supervisor, db_session_factory)
        self.quality_gate_service = quality_gate_service
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle start_agent message with quality tracking"""
        try:
            # Store start time for performance tracking
            start_time = datetime.now(UTC)
            
            # Call parent handler
            await super().handle(user_id, payload)
            
            # Calculate response time
            response_time = (datetime.now(UTC) - start_time).total_seconds()
            
            # Send quality update
            if hasattr(self.supervisor, 'get_quality_dashboard'):
                quality_data = await self.supervisor.get_quality_dashboard()
                quality_data['response_time'] = response_time
                
                await manager.send_message(
                    user_id,
                    {
                        "type": "quality_update",
                        "payload": quality_data
                    }
                )
            
        except Exception as e:
            logger.error(f"Error in quality-enhanced handler: {str(e)}")
            raise


class QualityValidationHandler(BaseMessageHandler):
    """Handler for on-demand quality validation"""
    
    def __init__(self, quality_gate_service: QualityGateService):
        self.quality_gate_service = quality_gate_service
    
    def get_message_type(self) -> str:
        return "validate_content"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle content validation request"""
        try:
            content = payload.get("content", "")
            content_type_str = payload.get("content_type", "general")
            strict_mode = payload.get("strict_mode", False)
            
            # Map string to ContentType enum
            content_type_map = {
                "optimization": ContentType.OPTIMIZATION,
                "data_analysis": ContentType.DATA_ANALYSIS,
                "action_plan": ContentType.ACTION_PLAN,
                "report": ContentType.REPORT,
                "triage": ContentType.TRIAGE,
                "error": ContentType.ERROR_MESSAGE,
                "general": ContentType.GENERAL
            }
            content_type = content_type_map.get(content_type_str, ContentType.GENERAL)
            
            # Validate content
            result = await self.quality_gate_service.validate_content(
                content=content,
                content_type=content_type,
                context={"user_id": user_id},
                strict_mode=strict_mode
            )
            
            # Send validation result
            await manager.send_message(
                user_id,
                {
                    "type": "content_validated",
                    "payload": {
                        "passed": result.passed,
                        "metrics": {
                            "overall_score": result.metrics.overall_score,
                            "quality_level": result.metrics.quality_level.value,
                            "specificity": result.metrics.specificity_score,
                            "actionability": result.metrics.actionability_score,
                            "quantification": result.metrics.quantification_score,
                            "issues": result.metrics.issues,
                            "suggestions": result.metrics.suggestions
                        },
                        "retry_suggested": result.retry_suggested
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            await manager.send_error(user_id, f"Failed to validate content: {str(e)}")


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