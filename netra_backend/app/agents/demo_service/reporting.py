# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-15T12:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Split demo_agent.py into modular architecture
# Git: pr-10-anthony-branch | Current | Clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: Demo Service Modernization
# Review: Pending | Score: TBD
# ================================
"""Demo reporting service for generating executive-ready reports."""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager

logger = central_logger.get_logger(__name__)


class DemoReportingService(BaseSubAgent, BaseExecutionInterface):
    """Specialized reporting service for demo scenarios."""
    
    def __init__(self, llm_manager: LLMManager, websocket_manager: WebSocketManager):
        BaseSubAgent.__init__(self, llm_manager, websocket_manager)
        BaseExecutionInterface.__init__(self, "DemoReportingService", websocket_manager)
        self.agent_name = "DemoReportingService"
        self._initialize_modern_components()
        
    async def execute(self, state: 'DeepAgentState', run_id: str, stream_updates: bool) -> None:
        """
        AgentLifecycleMixin execute method implementation.
        
        This method bridges the lifecycle mixin requirements with the modern execution interface.
        """
        try:
            # Create execution context from lifecycle parameters
            execution_context = ExecutionContext(
                run_id=run_id,
                agent_name=self.agent_name,
                state=state,
                stream_updates=stream_updates
            )
            
            # Execute using the modern execution engine
            await self.execution_engine.execute(self, execution_context)
            
        except Exception as e:
            logger.error(f"Execution failed in {self.agent_name}: {e}")
            raise
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate executive-ready reports for demo sessions.
        
        This service compiles insights and recommendations into
        a professional report format.
        """
        try:
            return await self._process_reporting_request(message, context)
        except Exception as e:
            return self._create_error_response(e)
            
    async def _process_reporting_request(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the reporting request with LLM generation."""
        prompt = self._prepare_reporting_prompt(message, context)
        response = await self._generate_llm_response(prompt)
        industry = self._get_industry_from_context(context)
        return self._create_success_response(response, industry)
        
    def _prepare_reporting_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare reporting prompt for executive summary generation."""
        optimization_data = self._get_optimization_data_from_context(context)
        industry = self._get_industry_from_context(context)
        return self._build_reporting_prompt_content(message, optimization_data, industry)
        
    def _get_optimization_data_from_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract optimization data from context or use default."""
        if context and "optimization_data" in context:
            return context["optimization_data"]
        return {}
        
    def _get_industry_from_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Extract industry from context or use default."""
        if context and "industry" in context:
            return context["industry"]
        return "technology"
        
    def _build_reporting_prompt_content(
        self,
        message: str,
        optimization_data: Dict[str, Any],
        industry: str
    ) -> str:
        """Build the complete reporting prompt content."""
        recommendations = optimization_data.get('recommendations', 'Standard optimizations')
        return f"""Create an executive summary report for this AI optimization analysis.

Industry: {industry}
Original Request: {message}
Optimization Recommendations: {recommendations}

Generate a professional report with:
1. Executive Summary (2-3 sentences)
2. Key Findings (3-4 bullet points)
3. Recommended Actions (prioritized list)
4. Expected Outcomes (quantified benefits)
5. Next Steps (clear action items)

Use professional language appropriate for C-suite executives.
Include specific metrics and timelines where possible."""
        
    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate response from LLM with reporting-focused parameters."""
        return await self.llm_manager.generate(
            prompt=prompt,
            temperature=0.4,
            max_tokens=800
        )
        
    def _create_success_response(self, response: str, industry: str) -> Dict[str, Any]:
        """Create a successful reporting response with metadata."""
        return {
            "status": "success",
            "report": response,
            "metadata": self._create_report_metadata(industry)
        }
        
    def _create_report_metadata(self, industry: str) -> Dict[str, Any]:
        """Create report metadata for tracking and auditing."""
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "industry": industry,
            "report_type": "executive_summary",
            "agent": self.agent_name
        }
        
    def _create_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create an error response dict."""
        logger.error(f"Demo reporting service error: {str(error)}")
        return {
            "status": "error",
            "error": str(error),
            "agent": self.agent_name
        }
        
    def get_report_types(self) -> list:
        """Get list of available report types."""
        return [
            "executive_summary",
            "technical_analysis",
            "cost_benefit_analysis",
            "implementation_roadmap"
        ]
    
    def _initialize_modern_components(self) -> None:
        """Initialize modern execution components."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.execution_monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.execution_monitor)
        
    def get_executive_summary_sections(self) -> list:
        """Get standard sections for executive summary reports."""
        return [
            "Executive Summary",
            "Key Findings", 
            "Recommended Actions",
            "Expected Outcomes",
            "Next Steps"
        ]
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for reporting."""
        return CircuitBreakerConfig(
            name=f"{self.agent_name}_circuit_breaker",
            failure_threshold=3,
            recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration for reporting."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=True
        )
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core reporting logic with modern patterns."""
        message = self._extract_message_from_context(context)
        report_context = self._extract_report_context_from_context(context)
        return await self._process_reporting_request(message, report_context)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for reporting."""
        return self._validate_context_has_message(context) and self._validate_llm_available()
    
    def _extract_message_from_context(self, context: ExecutionContext) -> str:
        """Extract message from execution context."""
        return context.state.message or context.metadata.get('message', '')
    
    def _extract_report_context_from_context(self, context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """Extract report context from execution context."""
        return context.metadata.get('context')
    
    def _validate_context_has_message(self, context: ExecutionContext) -> bool:
        """Validate context contains a message."""
        message = self._extract_message_from_context(context)
        return bool(message and message.strip())
    
    def _validate_llm_available(self) -> bool:
        """Validate LLM manager is available."""
        return self.llm_manager is not None
    
    async def execute_with_modern_interface(self, context: ExecutionContext) -> ExecutionResult:
        """Execute with modern interface for external callers."""
        return await self.execution_engine.execute(self, context)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for reporting service."""
        return {
            "agent_name": self.agent_name,
            "reliability": self.reliability_manager.get_health_status(),
            "monitoring": self.execution_monitor.get_health_status(),
            "execution_engine": self.execution_engine.get_health_status()
        }