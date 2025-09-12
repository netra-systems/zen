"""Demo service for handling enterprise demonstration functionality."""

from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.demo.demo_session_manager import DemoSessionManager as SessionManager
from netra_backend.app.services.demo.analytics_tracker import AnalyticsTracker
from netra_backend.app.services.demo.metrics_generator import (
    calculate_roi,
    generate_optimization_metrics,
    generate_synthetic_metrics,
)
from netra_backend.app.services.demo.report_generator import ReportGenerator
from netra_backend.app.services.demo.response_generator import generate_demo_response
from netra_backend.app.services.demo.template_manager import get_industry_templates

logger = central_logger.get_logger(__name__)

class DemoService:
    """Service for managing demo sessions and functionality."""
    
    def __init__(self, agent_service: Optional[AgentService] = None):
        self.agent_service = agent_service
        self.session_manager = SessionManager()
        self.analytics_tracker = AnalyticsTracker()
        self.report_generator = ReportGenerator()
        
    async def process_demo_chat(self, message: str, industry: str,
                               session_id: str, 
                               context: Optional[Dict[str, Any]] = None,
                               user_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a demo chat interaction with simulated multi-agent response."""
        try:
            session_data = await self.session_manager.get_demo_session(session_id)
            if not session_data:
                session_data = await self.session_manager.create_demo_session(
                    session_id, industry, user_id)
            await self.session_manager.add_demo_message(session_id, "user", message)
            agents_involved = ["TriageAgent", "DataAgent", 
                             "OptimizationAgent", "ReportingAgent"]
            optimization_metrics = generate_optimization_metrics(industry)
            response = generate_demo_response(message, industry, optimization_metrics)
            await self.session_manager.add_demo_message(
                session_id, "assistant", response,
                agents=agents_involved, metrics=optimization_metrics)
            return {
                "response": response,
                "agents": agents_involved,
                "metrics": optimization_metrics
            }
        except Exception as e:
            logger.error(f"Demo chat processing error: {str(e)}")
            raise
            
    async def get_industry_templates(self, industry: str) -> List[Dict[str, Any]]:
        """Get industry-specific templates and scenarios."""
        return await get_industry_templates(industry)
        
    async def calculate_roi(self, current_spend: float, request_volume: int,
                          average_latency: float, 
                          industry: str) -> Dict[str, Any]:
        """Calculate ROI for AI optimization."""
        return await calculate_roi(current_spend, request_volume, 
                                 average_latency, industry)
        
    async def generate_synthetic_metrics(self, scenario: str = "standard",
                                        duration_hours: int = 24) -> Dict[str, Any]:
        """Generate synthetic performance metrics for demonstration."""
        return await generate_synthetic_metrics(scenario, duration_hours)
        
    async def generate_report(self, session_id: str, format: str = "pdf",
                            include_sections: List[str] = None,
                            user_id: Optional[int] = None) -> str:
        """Generate a demo report for export."""
        return await self.report_generator.generate_report(
            session_id, format, include_sections, user_id)
        
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a demo session."""
        return await self.session_manager.get_demo_session_status(session_id)
        
    async def submit_feedback(self, session_id: str, 
                            feedback: Dict[str, Any]) -> None:
        """Submit feedback for a demo session."""
        await self.analytics_tracker.submit_feedback(session_id, feedback)
        
    async def track_demo_interaction(self, session_id: str, 
                                    interaction_type: str,
                                    data: Dict[str, Any]) -> None:
        """Track demo interaction for analytics."""
        await self.analytics_tracker.track_interaction(
            session_id, interaction_type, data)
        
    async def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for demo usage."""
        return await self.analytics_tracker.get_analytics_summary(days)

def get_demo_service() -> DemoService:
    """Factory function to create DemoService instance for dependency injection."""
    agent_service = None
    try:
        from netra_backend.app.services.agent_service import get_agent_service
        agent_service = None
    except ImportError:
        agent_service = None
    return DemoService(agent_service=agent_service)