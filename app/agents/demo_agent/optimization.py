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
"""Demo optimization agent for generating specific recommendations."""

from typing import Dict, Any, Optional, List

from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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
        try:
            return await self._process_optimization_request(message, context)
        except Exception as e:
            return self._create_error_response(e)
            
    async def _process_optimization_request(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the optimization request with LLM generation."""
        prompt = self._prepare_optimization_prompt(message, context)
        response = await self._generate_llm_response(prompt)
        industry = self._get_industry_from_context(context)
        return self._create_success_response(response, industry)
        
    def _prepare_optimization_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare optimization prompt for strategy generation."""
        industry = self._get_industry_from_context(context)
        triage_result = self._get_triage_result_from_context(context)
        return self._build_optimization_prompt_content(message, industry, triage_result)
        
    def _get_industry_from_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Extract industry from context or use default."""
        if context and "industry" in context:
            return context["industry"]
        return "technology"
        
    def _get_triage_result_from_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract triage result from context or use default."""
        if context and "triage_result" in context:
            return context["triage_result"]
        return {}
        
    def _build_optimization_prompt_content(
        self,
        message: str,
        industry: str,
        triage_result: Dict[str, Any]
    ) -> str:
        """Build the complete optimization prompt content."""
        categories = triage_result.get('category', ['General Optimization'])
        return f"""As an AI optimization expert, provide specific optimization recommendations for this {industry} use case.

Request: {message}
Optimization Focus: {categories}

Generate 3 specific optimization strategies with:
1. Strategy name and description
2. Implementation approach (2-3 steps)
3. Quantified benefits (use realistic percentages/metrics)
4. Timeline for implementation
5. Risk mitigation approach

Format each strategy clearly with headers and bullet points.
Use industry-specific terminology and examples."""
        
    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate response from LLM with optimization-focused parameters."""
        return await self.llm_manager.generate(
            prompt=prompt,
            temperature=0.6,
            max_tokens=1000
        )
        
    def _create_success_response(self, response: str, industry: str) -> Dict[str, Any]:
        """Create a successful optimization response."""
        return {
            "status": "success",
            "recommendations": response,
            "agent": self.agent_name,
            "industry": industry
        }
        
    def _create_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create an error response dict."""
        logger.error(f"Demo optimization error: {str(error)}")
        return {
            "status": "error",
            "error": str(error),
            "agent": self.agent_name
        }
        
    def get_optimization_strategies(self) -> List[str]:
        """Get list of available optimization strategy types."""
        return [
            "Cost Reduction",
            "Performance Enhancement", 
            "Scalability Improvement",
            "Accuracy Optimization",
            "Security Enhancement"
        ]
        
    def get_implementation_timelines(self) -> List[str]:
        """Get list of typical implementation timelines."""
        return [
            "Immediate (1-2 days)",
            "Short-term (1-2 weeks)",
            "Medium-term (1-2 months)",
            "Long-term (3-6 months)"
        ]