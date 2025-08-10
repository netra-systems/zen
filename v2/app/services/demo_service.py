"""Demo service for handling enterprise demonstration functionality."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import numpy as np

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
from app.redis_manager import redis_manager
from app.agents.supervisor import SupervisorAgent
from app.services.agent_service import AgentService

class DemoService:
    """Service for managing demo sessions and functionality."""
    
    # Industry-specific optimization factors
    INDUSTRY_FACTORS = {
        "financial": {
            "cost_reduction": 0.45,
            "latency_improvement": 0.60,
            "throughput_increase": 2.5,
            "accuracy_boost": 0.08,
            "typical_scenarios": ["fraud_detection", "risk_assessment", "trading_algorithms"],
            "key_metrics": ["transaction_volume", "detection_accuracy", "processing_time"]
        },
        "healthcare": {
            "cost_reduction": 0.40,
            "latency_improvement": 0.55,
            "throughput_increase": 2.0,
            "accuracy_boost": 0.12,
            "typical_scenarios": ["diagnostic_ai", "patient_triage", "drug_discovery"],
            "key_metrics": ["diagnostic_accuracy", "patient_throughput", "compliance_score"]
        },
        "ecommerce": {
            "cost_reduction": 0.50,
            "latency_improvement": 0.65,
            "throughput_increase": 3.0,
            "accuracy_boost": 0.10,
            "typical_scenarios": ["recommendation_engine", "search_optimization", "inventory_prediction"],
            "key_metrics": ["conversion_rate", "cart_value", "search_relevance"]
        },
        "manufacturing": {
            "cost_reduction": 0.35,
            "latency_improvement": 0.50,
            "throughput_increase": 1.8,
            "accuracy_boost": 0.15,
            "typical_scenarios": ["predictive_maintenance", "quality_control", "supply_chain"],
            "key_metrics": ["downtime_reduction", "defect_rate", "efficiency_score"]
        },
        "technology": {
            "cost_reduction": 0.55,
            "latency_improvement": 0.70,
            "throughput_increase": 3.5,
            "accuracy_boost": 0.09,
            "typical_scenarios": ["code_generation", "bug_detection", "system_optimization"],
            "key_metrics": ["deployment_frequency", "bug_resolution_time", "system_uptime"]
        }
    }
    
    def __init__(
        self,
        agent_service: Optional[AgentService] = None
    ):
        self.agent_service = agent_service
        self.redis_client = None
        
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client
        
    async def process_demo_chat(
        self,
        message: str,
        industry: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a demo chat interaction with simulated multi-agent response.
        
        Args:
            message: User's message
            industry: Industry context
            session_id: Demo session identifier
            context: Additional context
            user_id: Optional user ID
            
        Returns:
            Dict containing response, agents involved, and metrics
        """
        try:
            # Get industry-specific factors
            industry_data = self.INDUSTRY_FACTORS.get(
                industry.lower(), 
                self.INDUSTRY_FACTORS["technology"]
            )
            
            # Store session in Redis
            redis = await self._get_redis()
            session_key = f"demo:session:{session_id}"
            session_data = {
                "industry": industry,
                "user_id": user_id,
                "started_at": datetime.utcnow().isoformat(),
                "messages": []
            }
            
            # Get existing session or create new
            existing = await redis.get(session_key)
            if existing:
                session_data = json.loads(existing)
            
            # Add message to session
            session_data["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Simulate multi-agent processing
            agents_involved = ["TriageAgent", "DataAgent", "OptimizationAgent", "ReportingAgent"]
            
            # Generate optimization metrics based on industry
            optimization_metrics = {
                "cost_reduction_percentage": industry_data["cost_reduction"] * 100,
                "latency_improvement_ms": random.uniform(50, 200) * industry_data["latency_improvement"],
                "throughput_increase_factor": industry_data["throughput_increase"],
                "accuracy_improvement_percentage": industry_data["accuracy_boost"] * 100,
                "estimated_annual_savings": self._calculate_savings(industry_data),
                "implementation_time_weeks": random.randint(2, 8),
                "confidence_score": random.uniform(0.85, 0.98)
            }
            
            # Create contextual response
            response = self._generate_demo_response(message, industry, optimization_metrics)
            
            # Add response to session
            session_data["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.utcnow().isoformat(),
                "agents": agents_involved,
                "metrics": optimization_metrics
            })
            
            # Store updated session
            await redis.setex(
                session_key,
                3600 * 24,  # 24 hour expiry
                json.dumps(session_data)
            )
            
            return {
                "response": response,
                "agents": agents_involved,
                "metrics": optimization_metrics
            }
            
        except Exception as e:
            logger.error(f"Demo chat processing error: {str(e)}")
            raise
            
    def _generate_demo_response(
        self, 
        message: str, 
        industry: str, 
        metrics: Dict[str, Any]
    ) -> str:
        """Generate a contextual demo response."""
        # Create industry-specific response
        industry_context = self.INDUSTRY_FACTORS.get(
            industry.lower(), 
            self.INDUSTRY_FACTORS["technology"]
        )
        
        response = f"""Based on my analysis of your {industry} AI workloads, I've identified several optimization opportunities:

**Cost Optimization:**
- Reduce infrastructure costs by {metrics['cost_reduction_percentage']:.1f}% through intelligent model routing
- Estimated annual savings: ${metrics['estimated_annual_savings']:,.0f}

**Performance Improvements:**
- Decrease latency by {metrics['latency_improvement_ms']:.0f}ms (average)
- Increase throughput by {metrics['throughput_increase_factor']:.1f}x
- Improve model accuracy by {metrics['accuracy_improvement_percentage']:.1f}%

**Implementation Timeline:**
- Full optimization achievable in {metrics['implementation_time_weeks']} weeks
- ROI typically realized within 2-3 months

**Key Areas for {industry.title()} Optimization:**
"""
        
        # Add industry-specific scenarios
        for scenario in industry_context["typical_scenarios"][:3]:
            response += f"- {scenario.replace('_', ' ').title()}\n"
            
        response += f"\nConfidence Score: {metrics['confidence_score']:.2%}"
        
        return response
        
    def _calculate_savings(self, industry_data: Dict[str, Any]) -> float:
        """Calculate estimated annual savings based on industry data."""
        base_savings = random.uniform(500000, 2000000)
        return base_savings * industry_data["cost_reduction"]
        
    async def get_industry_templates(self, industry: str) -> List[Dict[str, Any]]:
        """
        Get industry-specific templates and scenarios.
        
        Args:
            industry: Industry identifier
            
        Returns:
            List of industry templates
        """
        industry_lower = industry.lower()
        if industry_lower not in self.INDUSTRY_FACTORS:
            raise ValueError(f"Unknown industry: {industry}")
            
        industry_data = self.INDUSTRY_FACTORS[industry_lower]
        templates = []
        
        # Generate templates for each scenario
        for scenario in industry_data["typical_scenarios"]:
            template = {
                "industry": industry,
                "name": scenario.replace("_", " ").title(),
                "description": f"Optimization template for {scenario.replace('_', ' ')} in {industry}",
                "prompt_template": self._generate_prompt_template(industry, scenario),
                "optimization_scenarios": self._generate_optimization_scenarios(industry, scenario),
                "typical_metrics": {
                    "baseline": self._generate_baseline_metrics(industry),
                    "optimized": self._generate_optimized_metrics(industry)
                }
            }
            templates.append(template)
            
        return templates
        
    def _generate_prompt_template(self, industry: str, scenario: str) -> str:
        """Generate a prompt template for a specific scenario."""
        return f"""Analyze and optimize {scenario.replace('_', ' ')} workloads for {industry} industry.
Consider:
- Current infrastructure and model usage
- Latency requirements and SLAs
- Cost constraints and budget
- Compliance and regulatory requirements
- Scale and growth projections

Provide specific optimization recommendations."""
        
    def _generate_optimization_scenarios(self, industry: str, scenario: str) -> List[Dict[str, Any]]:
        """Generate optimization scenarios for demonstration."""
        return [
            {
                "name": "Model Selection Optimization",
                "description": "Intelligently route requests to optimal models",
                "impact": "30-40% cost reduction",
                "implementation": "2-3 weeks"
            },
            {
                "name": "Caching Strategy",
                "description": "Implement intelligent caching for common queries",
                "impact": "50-70% latency reduction",
                "implementation": "1-2 weeks"
            },
            {
                "name": "Batch Processing Optimization",
                "description": "Optimize batch sizes and processing windows",
                "impact": "2-3x throughput increase",
                "implementation": "3-4 weeks"
            }
        ]
        
    def _generate_baseline_metrics(self, industry: str) -> Dict[str, Any]:
        """Generate baseline metrics for industry."""
        return {
            "avg_latency_ms": random.uniform(200, 500),
            "requests_per_second": random.randint(100, 1000),
            "error_rate": random.uniform(0.01, 0.05),
            "cost_per_1k_requests": random.uniform(5, 20),
            "model_accuracy": random.uniform(0.80, 0.90)
        }
        
    def _generate_optimized_metrics(self, industry: str) -> Dict[str, Any]:
        """Generate optimized metrics showing improvement."""
        baseline = self._generate_baseline_metrics(industry)
        factors = self.INDUSTRY_FACTORS[industry.lower()]
        
        return {
            "avg_latency_ms": baseline["avg_latency_ms"] * (1 - factors["latency_improvement"]),
            "requests_per_second": baseline["requests_per_second"] * factors["throughput_increase"],
            "error_rate": baseline["error_rate"] * 0.5,
            "cost_per_1k_requests": baseline["cost_per_1k_requests"] * (1 - factors["cost_reduction"]),
            "model_accuracy": min(0.99, baseline["model_accuracy"] + factors["accuracy_boost"])
        }
        
    async def calculate_roi(
        self,
        current_spend: float,
        request_volume: int,
        average_latency: float,
        industry: str
    ) -> Dict[str, Any]:
        """
        Calculate ROI for AI optimization.
        
        Args:
            current_spend: Current monthly spend
            request_volume: Monthly request volume
            average_latency: Current average latency
            industry: Industry context
            
        Returns:
            ROI calculation results
        """
        try:
            factors = self.INDUSTRY_FACTORS.get(
                industry.lower(),
                self.INDUSTRY_FACTORS["technology"]
            )
            
            # Calculate current annual cost
            current_annual_cost = current_spend * 12
            
            # Calculate optimized cost
            optimized_annual_cost = current_annual_cost * (1 - factors["cost_reduction"])
            
            # Calculate savings
            annual_savings = current_annual_cost - optimized_annual_cost
            savings_percentage = (annual_savings / current_annual_cost) * 100
            
            # Calculate ROI timeline (months to break even)
            implementation_cost = current_spend * 0.5  # Assume 0.5 month cost for implementation
            roi_months = int(np.ceil(implementation_cost / (annual_savings / 12)))
            
            # Calculate 3-year TCO reduction
            three_year_savings = annual_savings * 3
            three_year_tco_reduction = three_year_savings - implementation_cost
            
            # Performance improvements
            performance_improvements = {
                "latency_reduction_percentage": factors["latency_improvement"] * 100,
                "throughput_increase_factor": factors["throughput_increase"],
                "accuracy_improvement_percentage": factors["accuracy_boost"] * 100,
                "error_rate_reduction_percentage": 50.0  # Typical error rate reduction
            }
            
            return {
                "current_annual_cost": current_annual_cost,
                "optimized_annual_cost": optimized_annual_cost,
                "annual_savings": annual_savings,
                "savings_percentage": savings_percentage,
                "roi_months": roi_months,
                "three_year_tco_reduction": three_year_tco_reduction,
                "performance_improvements": performance_improvements
            }
            
        except Exception as e:
            logger.error(f"ROI calculation error: {str(e)}")
            raise
            
    async def generate_synthetic_metrics(
        self,
        scenario: str = "standard",
        duration_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate synthetic performance metrics for demonstration.
        
        Args:
            scenario: Type of scenario to simulate
            duration_hours: Duration of metrics to generate
            
        Returns:
            Synthetic metrics data
        """
        try:
            # Generate timestamps
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=duration_hours)
            timestamps = []
            current = start_time
            
            while current <= end_time:
                timestamps.append(current)
                current += timedelta(minutes=15)
                
            num_points = len(timestamps)
            
            # Generate baseline metrics with noise
            baseline_latency = 250 + np.random.normal(0, 20, num_points)
            baseline_throughput = 500 + np.random.normal(0, 50, num_points)
            baseline_cost = 10 + np.random.normal(0, 1, num_points)
            
            # Generate optimized metrics showing improvement over time
            improvement_curve = np.linspace(0, 1, num_points)
            optimized_latency = baseline_latency * (1 - 0.6 * improvement_curve)
            optimized_throughput = baseline_throughput * (1 + 2 * improvement_curve)
            optimized_cost = baseline_cost * (1 - 0.45 * improvement_curve)
            
            # Add some realistic variations
            optimized_latency += np.random.normal(0, 10, num_points)
            optimized_throughput += np.random.normal(0, 30, num_points)
            optimized_cost += np.random.normal(0, 0.5, num_points)
            
            return {
                "latency_reduction": 60.0,
                "throughput_increase": 200.0,
                "cost_reduction": 45.0,
                "accuracy_improvement": 8.5,
                "timestamps": timestamps,
                "values": {
                    "baseline_latency": baseline_latency.tolist(),
                    "optimized_latency": optimized_latency.tolist(),
                    "baseline_throughput": baseline_throughput.tolist(),
                    "optimized_throughput": optimized_throughput.tolist(),
                    "baseline_cost": baseline_cost.tolist(),
                    "optimized_cost": optimized_cost.tolist()
                }
            }
            
        except Exception as e:
            logger.error(f"Synthetic metrics generation error: {str(e)}")
            raise
            
    async def generate_report(
        self,
        session_id: str,
        format: str = "pdf",
        include_sections: List[str] = None,
        user_id: Optional[int] = None
    ) -> str:
        """
        Generate a demo report for export.
        
        Args:
            session_id: Demo session identifier
            format: Export format (pdf, docx, html)
            include_sections: Sections to include
            user_id: Optional user ID
            
        Returns:
            URL or path to generated report
        """
        try:
            # Get session data from Redis
            redis = await self._get_redis()
            session_key = f"demo:session:{session_id}"
            session_data = await redis.get(session_key)
            
            if not session_data:
                raise ValueError(f"Session not found: {session_id}")
                
            session_data = json.loads(session_data)
            
            # Generate report content based on format
            # For now, return a placeholder URL
            report_id = str(uuid.uuid4())
            report_url = f"/api/demo/reports/{report_id}.{format}"
            
            # Store report metadata
            report_key = f"demo:report:{report_id}"
            report_data = {
                "session_id": session_id,
                "format": format,
                "sections": include_sections or ["summary", "metrics", "recommendations"],
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "url": report_url
            }
            
            await redis.setex(
                report_key,
                3600 * 24,  # 24 hour expiry
                json.dumps(report_data)
            )
            
            return report_url
            
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            raise
            
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a demo session.
        
        Args:
            session_id: Demo session identifier
            
        Returns:
            Session status information
        """
        try:
            redis = await self._get_redis()
            session_key = f"demo:session:{session_id}"
            session_data = await redis.get(session_key)
            
            if not session_data:
                raise ValueError(f"Session not found: {session_id}")
                
            session_data = json.loads(session_data)
            
            # Calculate progress based on messages
            message_count = len(session_data.get("messages", []))
            expected_steps = 6  # Typical demo flow steps
            progress = min(100, (message_count / expected_steps) * 100)
            
            return {
                "session_id": session_id,
                "industry": session_data.get("industry"),
                "started_at": session_data.get("started_at"),
                "message_count": message_count,
                "progress_percentage": progress,
                "status": "active" if progress < 100 else "completed",
                "last_interaction": session_data["messages"][-1]["timestamp"] if session_data.get("messages") else None
            }
            
        except Exception as e:
            logger.error(f"Session status error: {str(e)}")
            raise
            
    async def submit_feedback(
        self,
        session_id: str,
        feedback: Dict[str, Any]
    ) -> None:
        """
        Submit feedback for a demo session.
        
        Args:
            session_id: Demo session identifier
            feedback: Feedback data
        """
        try:
            redis = await self._get_redis()
            feedback_key = f"demo:feedback:{session_id}"
            
            feedback_data = {
                "session_id": session_id,
                "feedback": feedback,
                "submitted_at": datetime.utcnow().isoformat()
            }
            
            await redis.setex(
                feedback_key,
                3600 * 24 * 30,  # 30 day expiry
                json.dumps(feedback_data)
            )
            
        except Exception as e:
            logger.error(f"Feedback submission error: {str(e)}")
            raise
            
    async def track_demo_interaction(
        self,
        session_id: str,
        interaction_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Track demo interaction for analytics.
        
        Args:
            session_id: Demo session identifier
            interaction_type: Type of interaction
            data: Interaction data
        """
        try:
            redis = await self._get_redis()
            analytics_key = f"demo:analytics:{datetime.utcnow().strftime('%Y%m%d')}"
            
            interaction_data = {
                "session_id": session_id,
                "type": interaction_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await redis.lpush(analytics_key, json.dumps(interaction_data))
            await redis.expire(analytics_key, 3600 * 24 * 90)  # 90 day expiry
            
        except Exception as e:
            logger.error(f"Analytics tracking error: {str(e)}")
            # Don't raise - analytics shouldn't break the flow
            
    async def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics summary for demo usage.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics summary
        """
        try:
            redis = await self._get_redis()
            
            # Aggregate analytics from Redis
            total_sessions = 0
            total_interactions = 0
            industries = {}
            conversion_events = 0
            
            # Get data for specified days
            end_date = datetime.utcnow()
            for i in range(days):
                date = end_date - timedelta(days=i)
                key = f"demo:analytics:{date.strftime('%Y%m%d')}"
                
                data = await redis.lrange(key, 0, -1)
                for item in data:
                    if item:
                        interaction = json.loads(item)
                        total_interactions += 1
                        
                        if interaction["type"] == "chat":
                            total_sessions += 1
                            industry = interaction["data"].get("industry", "unknown")
                            industries[industry] = industries.get(industry, 0) + 1
                            
                        if interaction["type"] == "report_export":
                            conversion_events += 1
                            
            # Calculate metrics
            conversion_rate = (conversion_events / total_sessions * 100) if total_sessions > 0 else 0
            
            return {
                "period_days": days,
                "total_sessions": total_sessions,
                "total_interactions": total_interactions,
                "conversion_rate": conversion_rate,
                "industries": industries,
                "avg_interactions_per_session": total_interactions / total_sessions if total_sessions > 0 else 0,
                "report_exports": conversion_events
            }
            
        except Exception as e:
            logger.error(f"Analytics summary error: {str(e)}")
            raise

from fastapi import Depends

def get_demo_service(
    agent_service: Optional[AgentService] = None
) -> DemoService:
    """
    Factory function to create DemoService instance for dependency injection.
    
    Returns:
        DemoService instance ready for use in FastAPI routes
    """
    # Import here to avoid circular dependency
    try:
        from app.services.agent_service import get_agent_service
        # If we can import agent_service, use it
        if not agent_service:
            # Note: This is a simplified version, in production you'd properly inject this
            agent_service = None  # AgentService is optional for demo
    except ImportError:
        agent_service = None
    
    return DemoService(agent_service=agent_service)