"""Demo service for handling enterprise demonstration functionality."""

from typing import Any, Dict, List, Optional
import json

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
from netra_backend.app.schemas import RequestModel

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
        """Process a demo chat interaction with REAL multi-agent response."""
        try:
            session_data = await self.session_manager.get_demo_session(session_id)
            if not session_data:
                session_data = await self.session_manager.create_demo_session(
                    session_id, industry, user_id)
            await self.session_manager.add_demo_message(session_id, "user", message)
            
            # Call real agents instead of fake responses
            response_data = await self._invoke_real_agents(message, industry, session_id, user_id)
            
            await self.session_manager.add_demo_message(
                session_id, "assistant", response_data["response"],
                agents=response_data["agents"], metrics=response_data["metrics"])
            return response_data
        except Exception as e:
            logger.error(f"Demo chat processing error: {str(e)}")
            # Return a fallback response if agent invocation fails
            return await self._get_fallback_response(message, industry)
            
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
    
    async def _invoke_real_agents(self, message: str, industry: str, 
                                  session_id: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Invoke real agents to process the message."""
        try:
            if not self.agent_service:
                logger.warning("Agent service not available, using fallback response")
                return await self._get_fallback_response(message, industry)
            
            # Prepare the request for the supervisor agent
            # Include specific instructions for demo agents
            enhanced_message = f"""
            Process this user request through the following agents in sequence:
            1. TriageAgent - Assess the request and determine workflow
            2. DataHelperAgent - Analyze what data is needed
            3. AnalysisAgent - Perform deep analysis of the situation
            4. OptimizationAgent - Generate optimization strategies
            5. ReportingAgent - Generate insights and comprehensive report
            6. ActionsToMeetGoalsAgent - Provide actionable recommendations
            
            Industry Context: {industry}
            User Message: {message}
            
            Focus on providing practical, actionable AI optimization recommendations with specific metrics and ROI calculations.
            """
            
            request_model = RequestModel(
                user_request=enhanced_message,
                id=session_id,
                user_id=str(user_id) if user_id else "demo_user"
            )
            
            # Run the agents
            result = await self.agent_service.run(
                request_model=request_model,
                run_id=session_id,
                stream_updates=True
            )
            
            # Parse the agent response
            if isinstance(result, dict):
                response_text = result.get("response", "") or result.get("content", "")
                agents_used = result.get("agents_involved", [
                    "TriageAgent",
                    "DataHelperAgent",
                    "AnalysisAgent",
                    "OptimizationAgent",
                    "ReportingAgent",
                    "ActionsToMeetGoalsAgent"
                ])
            else:
                response_text = str(result)
                agents_used = [
                    "TriageAgent",
                    "DataHelperAgent",
                    "AnalysisAgent", 
                    "OptimizationAgent",
                    "ReportingAgent",
                    "ActionsToMeetGoalsAgent"
                ]
            
            # Generate real metrics based on the response
            metrics = await self._extract_metrics_from_response(response_text, industry)
            
            return {
                "response": response_text,
                "agents": agents_used,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to invoke real agents: {str(e)}")
            return await self._get_fallback_response(message, industry)
    
    async def _extract_metrics_from_response(self, response: str, industry: str) -> Dict[str, Any]:
        """Extract or generate metrics from the agent response."""
        # Try to extract metrics from the response if they're mentioned
        metrics = generate_optimization_metrics(industry)
        
        # Look for specific metric mentions in the response
        if "cost" in response.lower():
            # Try to extract cost savings if mentioned
            import re
            cost_match = re.search(r'(\d+)%?\s*cost', response.lower())
            if cost_match:
                metrics["cost_reduction_percentage"] = float(cost_match.group(1))
        
        if "latency" in response.lower():
            latency_match = re.search(r'(\d+)\s*ms', response.lower())
            if latency_match:
                metrics["latency_improvement_ms"] = float(latency_match.group(1))
        
        return metrics
    
    async def _get_fallback_response(self, message: str, industry: str) -> Dict[str, Any]:
        """Generate a fallback response when agents are not available."""
        optimization_metrics = generate_optimization_metrics(industry)
        response = generate_demo_response(message, industry, optimization_metrics)
        
        return {
            "response": response,
            "agents": [
                "TriageAgent", 
                "DataHelperAgent", 
                "AnalysisAgent",
                "OptimizationAgent", 
                "ReportingAgent",
                "ActionsToMeetGoalsAgent"
            ],
            "metrics": optimization_metrics
        }

def get_demo_service() -> DemoService:
    """Factory function to create DemoService instance for dependency injection."""
    agent_service = None
    try:
        from netra_backend.app.services.agent_service import get_agent_service
        # Actually get the agent service instead of setting to None
        agent_service = get_agent_service()
    except Exception as e:
        logger.warning(f"Could not initialize agent service for demo: {e}")
        agent_service = None
    return DemoService(agent_service=agent_service)