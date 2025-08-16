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
"""Demo triage agent for categorizing optimization requests."""

from typing import Dict, Any, Optional, List
import json

from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


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
        try:
            return await self._process_triage_request(message, context)
        except Exception as e:
            return self._create_error_response(e)
            
    async def _process_triage_request(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the triage request with LLM generation."""
        prompt = self._prepare_triage_prompt(message, context)
        response = await self._generate_llm_response(prompt)
        result = self._parse_triage_response(response)
        return self._create_success_response(result)
        
    def _prepare_triage_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare triage prompt for categorization."""
        industry = self._get_industry_from_context(context)
        return self._build_triage_prompt_content(message, industry)
        
    def _get_industry_from_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Extract industry from context or use default."""
        if context and "industry" in context:
            return context["industry"]
        return "technology"
        
    def _build_triage_prompt_content(self, message: str, industry: str) -> str:
        """Build the complete triage prompt content."""
        return f"""As a demo triage agent, categorize this request and determine the best optimization approach to demonstrate.

Request: {message}
Industry: {industry}

Categorize the request into one or more of these optimization types:
1. Cost Optimization
2. Performance Optimization
3. Scalability Optimization
4. Accuracy Optimization
5. Compliance/Security Optimization

Provide a brief (2-3 sentence) assessment and recommendation for the demo flow.
Format as JSON with keys: category, priority, recommendation"""
        
    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate response from LLM with triage-optimized parameters."""
        return await self.llm_manager.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=200
        )
        
    def _parse_triage_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._create_fallback_result(response)
            
    def _create_fallback_result(self, response: str) -> Dict[str, Any]:
        """Create fallback result if JSON parsing fails."""
        return {
            "category": ["Cost Optimization", "Performance Optimization"],
            "priority": "high",
            "recommendation": response[:200]
        }
        
    def _create_success_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a successful triage response."""
        return {
            "status": "success",
            "result": result,
            "agent": self.agent_name
        }
        
    def _create_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create an error response dict."""
        logger.error(f"Demo triage error: {str(error)}")
        return {
            "status": "error",
            "error": str(error),
            "agent": self.agent_name
        }
        
    def get_optimization_categories(self) -> List[str]:
        """Get list of available optimization categories."""
        return [
            "Cost Optimization",
            "Performance Optimization", 
            "Scalability Optimization",
            "Accuracy Optimization",
            "Compliance/Security Optimization"
        ]