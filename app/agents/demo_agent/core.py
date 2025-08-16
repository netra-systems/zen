# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-15T12:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Split demo_agent.py into modular architecture
# Git: pr-10-anthony-branch | Current | Clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: Architecture Compliance Fix
# Review: Pending | Score: TBD
# ================================
"""Core demo agent for enterprise demonstrations."""

from typing import Dict, Any, Optional
from datetime import datetime, UTC

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
            return await self._process_demo_request(message, context)
        except Exception as e:
            return self._create_error_response(e)
            
    async def _process_demo_request(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the demo request with LLM generation."""
        prompt = self._prepare_demo_prompt(message, context)
        response = await self._generate_llm_response(prompt)
        enhanced_response = self._enhance_with_metrics(response, context)
        return self._create_success_response(enhanced_response, context)
        
    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate response from LLM with demo-optimized parameters."""
        return await self.llm_manager.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1500,
            model="claude-3-sonnet-20240229"
        )
        
    def _prepare_demo_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare a demo-optimized prompt."""
        industry = self._get_industry_from_context(context)
        return self._build_demo_prompt_content(message, industry)
        
    def _get_industry_from_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Extract industry from context or use default."""
        if context and "industry" in context:
            return context["industry"]
        return self.industry
        
    def _build_demo_prompt_content(self, message: str, industry: str) -> str:
        """Build the complete demo prompt content."""
        return f"""You are an AI optimization expert demonstrating the Netra platform to a {industry} enterprise customer.

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
        
    def _enhance_with_metrics(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhance the response with specific metrics and visualizations."""
        if self._should_add_metrics(response):
            return response + self._get_metrics_section()
        return response
        
    def _should_add_metrics(self, response: str) -> bool:
        """Check if metrics section should be added."""
        return "metrics" not in response.lower()
        
    def _get_metrics_section(self) -> str:
        """Get the standard metrics section for demos."""
        return """

**Key Performance Indicators:**
- Cost Reduction: 40-60%
- Latency Improvement: 50-70%
- Throughput Increase: 2-3x
- ROI Timeline: 2-3 months"""
        
    def _create_success_response(
        self,
        enhanced_response: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a successful response dict."""
        return {
            "status": "success",
            "response": enhanced_response,
            "agent": self.agent_name,
            "industry": self.industry,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    def _create_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create an error response dict."""
        logger.error(f"Demo agent processing error: {str(error)}")
        return {
            "status": "error",
            "error": str(error),
            "agent": self.agent_name
        }