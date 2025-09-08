"""Quality report WebSocket handler.

Handles quality report generation and formatting.
Follows 450-line limit with 25-line function limit.
"""

from datetime import UTC, datetime
from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_monitoring_service import (
    QualityMonitoringService,
)
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

logger = central_logger.get_logger(__name__)


class QualityReportHandler(BaseMessageHandler):
    """Handler for quality report generation."""
    
    def __init__(self, monitoring_service: QualityMonitoringService):
        """Initialize quality report handler."""
        self.monitoring_service = monitoring_service
    
    def get_message_type(self) -> str:
        """Get the message type this handler processes."""
        return "generate_quality_report"
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle quality report generation request."""
        try:
            # Extract context IDs from payload to ensure session continuity
            self._current_thread_id = payload.get("thread_id")
            self._current_run_id = payload.get("run_id")
            
            report_params = self._extract_report_params(payload)
            report_data = await self._generate_report_data(report_params)
            markdown_report = self._format_quality_report(report_data, report_params["report_type"])
            await self._send_report_response(user_id, markdown_report, report_data)
        except Exception as e:
            await self._handle_report_error(user_id, e)

    def _extract_report_params(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract and validate report parameters from payload."""
        report_type = payload.get("report_type", "summary")
        period = payload.get("period", "day")
        return {"report_type": report_type, "period": period}

    async def _generate_report_data(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Generate report data based on parameters."""
        report_type = params["report_type"]
        
        if report_type == "summary":
            return await self._generate_summary_report()
        elif report_type == "detailed":
            return await self._generate_detailed_report(params["period"])
        return {"error": "Unknown report type"}

    async def _generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report data."""
        return await self.monitoring_service.get_dashboard_data()

    async def _generate_detailed_report(self, period: str) -> Dict[str, Any]:
        """Generate detailed report with agent data."""
        agent_names = self._get_monitored_agent_names()
        period_hours = self._convert_period_to_hours(period)
        agent_reports = await self._collect_agent_reports(agent_names, period_hours)
        summary_data = await self.monitoring_service.get_dashboard_data()
        return self._build_detailed_report_dict(summary_data, agent_reports)

    def _build_detailed_report_dict(self, summary_data: Dict[str, Any], agent_reports: Dict[str, Any]) -> Dict[str, Any]:
        """Build detailed report dictionary."""
        return {"summary": summary_data, "agents": agent_reports}

    def _get_monitored_agent_names(self) -> list[str]:
        """Get list of agent names to monitor."""
        return [
            "TriageSubAgent", "DataSubAgent", "OptimizationsCoreSubAgent",
            "ActionsToMeetGoalsSubAgent", "ReportingSubAgent"
        ]

    def _convert_period_to_hours(self, period: str) -> int:
        """Convert period string to hours."""
        period_mapping = {"day": 24, "week": 168}
        return period_mapping.get(period, 24)

    async def _collect_agent_reports(self, agent_names: list[str], period_hours: int) -> Dict[str, Any]:
        """Collect reports for all monitored agents."""
        agent_reports = {}
        for agent_name in agent_names:
            agent_reports[agent_name] = await self._get_agent_report(agent_name, period_hours)
        return agent_reports

    async def _get_agent_report(self, agent_name: str, period_hours: int) -> Dict[str, Any]:
        """Get report for a single agent."""
        return await self.monitoring_service.get_agent_report(agent_name, period_hours)

    async def _send_report_response(self, user_id: str, markdown_report: str, report_data: Dict[str, Any]) -> None:
        """Send formatted report response to user."""
        payload = self._build_report_payload(markdown_report, report_data)
        message = {"type": "quality_report_generated", "payload": payload}
        
        # Use existing context IDs instead of generating new ones
        thread_id = getattr(self, '_current_thread_id', None)
        run_id = getattr(self, '_current_run_id', None)
        
        if not thread_id or not run_id:
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            thread_id = UnifiedIdGenerator.generate_base_id("report_thread")
            run_id = UnifiedIdGenerator.generate_base_id("report_run")
        
        user_context = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        manager = create_websocket_manager(user_context)
        await manager.send_to_user(message)

    def _build_report_payload(self, markdown_report: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build report response payload."""
        return {
            "report": markdown_report,
            "raw_data": report_data,
            "timestamp": datetime.now(UTC).isoformat()
        }

    async def _handle_report_error(self, user_id: str, error: Exception) -> None:
        """Handle report generation error."""
        logger.error(f"Error generating quality report: {str(error)}")
        error_message = f"Failed to generate report: {str(error)}"
        try:
            # Use existing context IDs instead of generating new ones
            thread_id = getattr(self, '_current_thread_id', None)
            run_id = getattr(self, '_current_run_id', None)
            
            if not thread_id or not run_id:
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                thread_id = UnifiedIdGenerator.generate_base_id("report_error_thread")
                run_id = UnifiedIdGenerator.generate_base_id("report_error_run")
            
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            manager = create_websocket_manager(user_context)
            await manager.send_to_user({"type": "error", "message": error_message})
        except Exception as e:
            logger.error(f"Failed to send report error to user {user_id}: {e}")
    
    def _format_quality_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Format quality data as markdown report."""
        report = self._format_report_header(report_type)
        report = self._add_report_sections(report, data)
        return report

    def _add_report_sections(self, report: str, data: Dict[str, Any]) -> str:
        """Add all report sections to the base report."""
        report += self._format_overall_stats_section(data)
        report += self._format_quality_distribution_section(data)
        report += self._format_agent_performance_section(data)
        report += self._format_recent_alerts_section(data)
        return report

    def _format_report_header(self, report_type: str) -> str:
        """Format report header with title and metadata."""
        header = f"# AI Quality Report\n\n"
        header += f"**Generated:** {datetime.now(UTC).isoformat()}\n"
        header += f"**Type:** {report_type.title()}\n\n"
        return header

    def _format_overall_stats_section(self, data: Dict[str, Any]) -> str:
        """Format overall statistics section."""
        return f"## Overall Statistics\n\n{self._extract_stats_summary(data)}\n\n"

    def _format_quality_distribution_section(self, data: Dict[str, Any]) -> str:
        """Format quality distribution section."""
        return f"## Quality Distribution\n\n{self._extract_quality_dist(data)}\n\n"

    def _format_agent_performance_section(self, data: Dict[str, Any]) -> str:
        """Format agent performance section."""
        return f"## Agent Performance\n\n{self._extract_agent_perf(data)}\n\n"

    def _format_recent_alerts_section(self, data: Dict[str, Any]) -> str:
        """Format recent alerts section."""
        return f"## Recent Alerts\n\n{self._extract_recent_alerts(data)}\n\n"

    def _extract_stats_summary(self, data: Dict[str, Any]) -> str:
        """Extract statistics summary from data."""
        return f"Total responses: {data.get('total_responses', 0)}"

    def _extract_quality_dist(self, data: Dict[str, Any]) -> str:
        """Extract quality distribution from data."""
        return f"Quality scores: {data.get('quality_scores', {})}"

    def _extract_agent_perf(self, data: Dict[str, Any]) -> str:
        """Extract agent performance from data."""
        return f"Agent metrics: {data.get('agent_metrics', {})}"

    def _extract_recent_alerts(self, data: Dict[str, Any]) -> str:
        """Extract recent alerts from data."""
        return f"Recent alerts: {data.get('recent_alerts', [])}"