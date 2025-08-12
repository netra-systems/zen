# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:05.519978+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to agent support files
# Git: v6 | 2c55fb99 | dirty (32 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 3338d1f9-246a-461a-8cae-a81a10615db4 | Seq: 6
# Review: Pending | Score: 85
# ================================
"""Demo-specific agent configuration for enterprise demonstrations."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class DemoAgent(BaseSubAgent):
    """
    Specialized agent for handling demo interactions.
    
    This agent is optimized for demonstrating the platform's capabilities
    with a focus on business value, performance metrics, and actionable insights.
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        websocket_manager: WebSocketManager,
        industry: str = "technology",
        demo_mode: bool = True
    ):
        super().__init__(llm_manager, websocket_manager)
        self.industry = industry
        self.demo_mode = demo_mode
        self.agent_name = "DemoAgent"
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a demo request with industry-specific optimizations.
        
        Args:
            message: User's message
            context: Additional context including industry and session info
            
        Returns:
            Dict containing optimization recommendations and metrics
        """
        try:
            # Prepare the demo-specific prompt
            prompt = self._prepare_demo_prompt(message, context)
            
            # Get response from LLM with demo-optimized parameters
            response = await self.llm_manager.generate(
                prompt=prompt,
                temperature=0.7,  # Balanced creativity for demos
                max_tokens=1500,  # Comprehensive but concise responses
                model="claude-3-sonnet-20240229"  # Fast, high-quality model for demos
            )
            
            # Parse and enhance the response with metrics
            enhanced_response = self._enhance_with_metrics(response, context)
            
            return {
                "status": "success",
                "response": enhanced_response,
                "agent": self.agent_name,
                "industry": self.industry,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Demo agent processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "agent": self.agent_name
            }
            
    def _prepare_demo_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare a demo-optimized prompt."""
        
        industry = context.get("industry", self.industry) if context else self.industry
        
        prompt = f"""You are an AI optimization expert demonstrating the Netra platform to a {industry} enterprise customer.

Your role is to:
1. Analyze their specific AI workload challenges
2. Provide concrete, quantified optimization recommendations
3. Show immediate business value with specific metrics
4. Be professional yet engaging

Industry Context: {industry}
Customer Message: {message}

Provide a response that:
- Identifies 2-3 specific optimization opportunities
- Quantifies potential improvements (cost, latency, throughput)
- Suggests immediate next steps
- Maintains enterprise-level professionalism
- Uses industry-specific terminology and examples

Focus on demonstrable value and actionable insights."""
        
        return prompt
        
    def _enhance_with_metrics(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhance the response with specific metrics and visualizations."""
        
        # Add performance metrics badge if not already present
        if "metrics" not in response.lower():
            metrics_section = """

**Key Performance Indicators:**
- Cost Reduction: 40-60%
- Latency Improvement: 50-70%
- Throughput Increase: 2-3x
- ROI Timeline: 2-3 months"""
            
            response += metrics_section
            
        return response


class DemoTriageAgent(BaseSubAgent):
    """Specialized triage agent for demo scenarios."""
    
    def __init__(self, llm_manager: LLMManager, websocket_manager: WebSocketManager):
        super().__init__(llm_manager, websocket_manager)
        self.agent_name = "DemoTriageAgent"
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Triage demo requests to determine optimization approach.
        
        This agent quickly categorizes the request and determines
        which optimization strategies to demonstrate.
        """
        
        prompt = f"""As a demo triage agent, categorize this request and determine the best optimization approach to demonstrate.

Request: {message}
Industry: {context.get('industry', 'technology') if context else 'technology'}

Categorize the request into one or more of these optimization types:
1. Cost Optimization
2. Performance Optimization
3. Scalability Optimization
4. Accuracy Optimization
5. Compliance/Security Optimization

Provide a brief (2-3 sentence) assessment and recommendation for the demo flow.
Format as JSON with keys: category, priority, recommendation"""
        
        try:
            response = await self.llm_manager.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistent categorization
                max_tokens=200
            )
            
            # Parse JSON response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if response isn't valid JSON
                result = {
                    "category": ["Cost Optimization", "Performance Optimization"],
                    "priority": "high",
                    "recommendation": response[:200]
                }
                
            return {
                "status": "success",
                "result": result,
                "agent": self.agent_name
            }
            
        except Exception as e:
            logger.error(f"Demo triage error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "agent": self.agent_name
            }


class DemoOptimizationAgent(BaseSubAgent):
    """Specialized optimization agent for demo scenarios."""
    
    def __init__(self, llm_manager: LLMManager, websocket_manager: WebSocketManager):
        super().__init__(llm_manager, websocket_manager)
        self.agent_name = "DemoOptimizationAgent"
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate specific optimization recommendations for demos.
        
        This agent creates detailed, actionable optimization strategies
        with quantified benefits.
        """
        
        industry = context.get('industry', 'technology') if context else 'technology'
        triage_result = context.get('triage_result', {}) if context else {}
        
        prompt = f"""As an AI optimization expert, provide specific optimization recommendations for this {industry} use case.

Request: {message}
Optimization Focus: {triage_result.get('category', ['General Optimization'])}

Generate 3 specific optimization strategies with:
1. Strategy name and description
2. Implementation approach (2-3 steps)
3. Quantified benefits (use realistic percentages/metrics)
4. Timeline for implementation
5. Risk mitigation approach

Format each strategy clearly with headers and bullet points.
Use industry-specific terminology and examples."""
        
        try:
            response = await self.llm_manager.generate(
                prompt=prompt,
                temperature=0.6,
                max_tokens=1000
            )
            
            return {
                "status": "success",
                "recommendations": response,
                "agent": self.agent_name,
                "industry": industry
            }
            
        except Exception as e:
            logger.error(f"Demo optimization error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "agent": self.agent_name
            }


class DemoReportingAgent(BaseSubAgent):
    """Specialized reporting agent for demo scenarios."""
    
    def __init__(self, llm_manager: LLMManager, websocket_manager: WebSocketManager):
        super().__init__(llm_manager, websocket_manager)
        self.agent_name = "DemoReportingAgent"
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate executive-ready reports for demo sessions.
        
        This agent compiles insights and recommendations into
        a professional report format.
        """
        
        optimization_data = context.get('optimization_data', {}) if context else {}
        industry = context.get('industry', 'technology') if context else 'technology'
        
        prompt = f"""Create an executive summary report for this AI optimization analysis.

Industry: {industry}
Original Request: {message}
Optimization Recommendations: {optimization_data.get('recommendations', 'Standard optimizations')}

Generate a professional report with:
1. Executive Summary (2-3 sentences)
2. Key Findings (3-4 bullet points)
3. Recommended Actions (prioritized list)
4. Expected Outcomes (quantified benefits)
5. Next Steps (clear action items)

Use professional language appropriate for C-suite executives.
Include specific metrics and timelines where possible."""
        
        try:
            response = await self.llm_manager.generate(
                prompt=prompt,
                temperature=0.4,  # Lower temperature for professional consistency
                max_tokens=800
            )
            
            # Add report metadata
            report = {
                "status": "success",
                "report": response,
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "industry": industry,
                    "report_type": "executive_summary",
                    "agent": self.agent_name
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Demo reporting error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "agent": self.agent_name
            }