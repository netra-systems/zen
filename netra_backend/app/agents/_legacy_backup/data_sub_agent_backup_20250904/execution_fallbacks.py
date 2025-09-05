"""Fallback handling for DataSubAgent execution."""

from typing import Any, Callable, Dict, List

from netra_backend.app.llm.fallback_handler import FallbackConfig, LLMFallbackHandler
from netra_backend.app.logging_config import central_logger as logger


class ExecutionFallbackHandler:
    """Handles fallback scenarios during execution."""
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
        self._init_fallback_handler()
    
    def _init_fallback_handler(self) -> None:
        """Initialize LLM fallback handler."""
        self.fallback_handler = LLMFallbackHandler(
            FallbackConfig(
                max_retries=2,
                base_delay=1.0
            )
        )
    
    async def handle_execution_error(
        self, state: 'DeepAgentState', run_id: str, stream_updates: bool, send_update_fn: Callable, error: Exception
    ) -> None:
        """Handle execution errors using fallback mechanisms."""
        logger.warning(f"DataSubAgent falling back due to error: {error}")
        
        try:
            result = await self._attempt_llm_fallback_analysis(state, error)
        except Exception as fallback_error:
            logger.error(f"LLM fallback also failed: {fallback_error}")
            result = self._create_emergency_data_fallback(state, error)
        
        state.data_result = result
        await self._send_fallback_completion(run_id, send_update_fn, result)
    
    async def _attempt_llm_fallback_analysis(self, state: 'DeepAgentState', original_error: Exception) -> Dict[str, Any]:
        """Attempt to generate insights using LLM as fallback."""
        triage_result = state.triage_result
        if not triage_result:
            raise ValueError("No triage result available for LLM fallback")
        result = await self._execute_llm_fallback(triage_result)
        self._update_fallback_metadata(result, original_error)
        return result

    async def _execute_llm_fallback(self, triage_result) -> Dict[str, Any]:
        """Execute LLM fallback with error handling."""
        result = self._create_fallback_base_result()
        try:
            llm_insights = await self._generate_llm_insights(triage_result)
            result.update(llm_insights)
        except Exception as llm_error:
            logger.warning(f"LLM insight generation failed: {llm_error}")
            result = self._create_basic_fallback_result(triage_result)
        return result

    def _update_fallback_metadata(self, result: Dict[str, Any], original_error: Exception) -> None:
        """Update result with fallback metadata."""
        result["metadata"].update({
            "fallback_used": True,
            "original_error": str(original_error),
            "fallback_type": "llm_analysis",
            "data_quality": "degraded"
        })
    
    def _create_fallback_base_result(self) -> Dict[str, Any]:
        """Create base structure for fallback results."""
        return {
            "analysis_type": "fallback_analysis",
            "results": {},
            "metadata": {
                "confidence": 0.3,
                "source": "fallback_mechanism"
            }
        }
    
    async def _generate_llm_insights(self, triage_result) -> Dict[str, Any]:
        """Generate insights using LLM fallback."""
        category = getattr(triage_result, 'category', 'General')
        
        insights_prompt = f"""
        Based on this {category} request, provide general insights and recommendations
        when detailed data analysis is unavailable.
        """
        
        llm_response = await self.fallback_handler.generate_fallback_response(
            insights_prompt, self.engine.llm_manager
        )
        
        return self._parse_llm_fallback_response(llm_response, category)
    
    def _parse_llm_fallback_response(self, llm_response: str, category: str) -> Dict[str, Any]:
        """Parse LLM fallback response into structured result."""
        return {
            "insights": self._extract_insights_from_response(llm_response),
            "recommendations": self._extract_recommendations_from_response(llm_response),
            "category": category,
            "data": {
                "status": "fallback_generated",
                "available": False
            }
        }
    
    def _extract_insights_from_response(self, response: str) -> List[str]:
        """Extract insights from LLM response."""
        lines = response.split('\n')
        insights = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                insights.append(line.strip())
        return insights[:5]  # Limit to 5 insights
    
    def _extract_recommendations_from_response(self, response: str) -> List[str]:
        """Extract recommendations from LLM response."""
        recommendations = [
            "Review system configuration",
            "Check data availability",
            "Consider alternative analysis methods",
            "Monitor system performance"
        ]
        return recommendations
    
    def _create_basic_fallback_result(self, triage_result) -> Dict[str, Any]:
        """Create basic fallback result when LLM also fails."""
        category = getattr(triage_result, 'category', 'Unknown')
        return {
            "analysis_type": "basic_fallback",
            "category": category,
            **self._build_basic_fallback_content(category),
            **self._build_basic_fallback_metadata()
        }
    
    def _build_basic_fallback_content(self, category: str) -> Dict[str, Any]:
        """Build content sections for basic fallback."""
        return {
            "insights": self._create_basic_insights(category),
            "recommendations": self._create_basic_recommendations(),
            "data": {
                "status": "basic_fallback",
                "available": False
            }
        }
    
    def _build_basic_fallback_metadata(self) -> Dict[str, Any]:
        """Build metadata section for basic fallback."""
        return {
            "metadata": {
                "fallback_used": True,
                "fallback_type": "basic",
                "confidence": 0.1
            }
        }
    
    def _create_basic_insights(self, category: str) -> List[str]:
        """Create basic insights for fallback."""
        return [
            f"Analysis request categorized as: {category}",
            "Detailed analysis temporarily unavailable",
            "System is working to restore full functionality"
        ]
    
    def _create_basic_recommendations(self) -> List[str]:
        """Create basic recommendations for fallback."""
        return [
            "Check system status",
            "Retry request in a few minutes",
            "Contact support if issue persists"
        ]
    
    def _create_emergency_data_fallback(self, state: 'DeepAgentState', error: Exception) -> Dict[str, Any]:
        """Create emergency fallback when all analysis methods fail."""
        triage_result = state.triage_result
        category = getattr(triage_result, 'category', 'Unknown') if triage_result else 'Unknown'
        
        return {
            "analysis_type": "emergency_fallback",
            "category": category,
            "insights": self._create_emergency_insights(category),
            "recommendations": self._create_emergency_recommendations(),
            "data": self._create_emergency_data_section(error),
            "metadata": self._create_emergency_metadata()
        }
    
    def _create_emergency_insights(self, category: str) -> List[str]:
        """Create emergency fallback insights."""
        return [
            f"Analysis for {category} request is temporarily unavailable",
            "System is experiencing technical difficulties",
            "Please try again in a few minutes"
        ]
    
    def _create_emergency_recommendations(self) -> List[str]:
        """Create emergency fallback recommendations."""
        return [
            "Check system status",
            "Retry with simpler parameters",
            "Contact support if issue persists"
        ]
    
    def _create_emergency_data_section(self, error: Exception) -> Dict[str, Any]:
        """Create emergency data section."""
        return {
            "status": "emergency_fallback",
            "error": str(error),
            "available": False
        }
    
    def _create_emergency_metadata(self) -> Dict[str, Any]:
        """Create emergency metadata section."""
        return {
            "fallback_used": True,
            "fallback_type": "emergency",
            "data_quality": "unavailable",
            "confidence": 0.0
        }
    
    async def _send_fallback_completion(
        self,
        run_id: str,
        send_update_fn: Callable,
        result: Dict[str, Any]
    ) -> None:
        """Send completion update for fallback results."""
        fallback_type = result.get("metadata", {}).get("fallback_type", "unknown")
        status, message = self._get_completion_status_message(fallback_type)
        completion_data = self._build_completion_data(status, message, result)
        await send_update_fn(run_id, completion_data)
    
    def _get_completion_status_message(self, fallback_type: str) -> tuple[str, str]:
        """Get status and message for completion based on fallback type."""
        if fallback_type == "emergency":
            return "completed_with_emergency_fallback", "Analysis completed using emergency fallback"
        return "completed_with_fallback", "Data analysis completed with limited capabilities"
    
    def _build_completion_data(self, status: str, message: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Build completion data structure."""
        return {
            "status": status,
            "message": message,
            "result": result
        }
    
    def get_fallback_health_status(self) -> Dict[str, Any]:
        """Get health status of fallback mechanisms."""
        return self.fallback_handler.get_health_status()