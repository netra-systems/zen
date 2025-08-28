# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T12:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Modernize demo agent with BaseExecutionInterface pattern
# Git: 8-18-25-AM | Current | Clean
# Change: Modernization | Scope: Module | Risk: Low
# Session: Demo Service Modernization
# Review: Pending | Score: TBD
# ================================
"""Modernized core demo service for enterprise demonstrations.

Inherits from BaseExecutionInterface for standardized execution patterns:
- Implements execute_core_logic() for core demo processing
- Implements validate_preconditions() for validation
- Integrates ReliabilityManager for circuit breaker and retry
- Uses ExecutionMonitor for performance tracking
- Utilizes ExecutionErrorHandler for structured errors

Business Value: Customer-facing demo reliability and performance.
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import BaseExecutionInterface, ExecutionContext, ExecutionResult
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

logger = central_logger.get_logger(__name__)


class DemoService(BaseSubAgent, BaseExecutionInterface):
    """
    Modernized demo service with BaseExecutionInterface compliance.
    
    Provides advanced error handling, circuit breaker patterns, and monitoring
    for reliable customer-facing demonstrations.
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        websocket_manager: WebSocketManager,
        industry: str = "technology",
        demo_mode: bool = True
    ):
        BaseSubAgent.__init__(self, llm_manager, websocket_manager)
        BaseExecutionInterface.__init__(self, "DemoService", websocket_manager)
        self._initialize_demo_properties(industry, demo_mode)
        self._initialize_modern_components()
        
    def _initialize_demo_properties(self, industry: str, demo_mode: bool) -> None:
        """Initialize demo-specific properties."""
        self.industry = industry
        self.demo_mode = demo_mode
        self.agent_name = "DemoService"
        
    def _initialize_modern_components(self) -> None:
        """Initialize modern agent architecture components."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
        
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
        
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for demo reliability."""
        return CircuitBreakerConfig(
            name="demo_service",
            failure_threshold=3,
            recovery_timeout=30
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration for demo resilience."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=5.0
        )
        
    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a demo request using modern execution engine.
        
        Args:
            message: User's message
            context: Additional context including industry and session info
            
        Returns:
            Dict containing optimization recommendations and metrics
        """
        execution_context = self._create_process_context(message, context)
        result = await self.execution_engine.execute(self, execution_context)
        return self._convert_result_to_response(result)
        
    def _create_process_context(self, message: str, context: Optional[Dict[str, Any]]) -> ExecutionContext:
        """Create execution context for demo processing."""
        from netra_backend.app.agents.state import DeepAgentState
        state = DeepAgentState()
        exec_context = self._build_execution_context(state)
        exec_context.metadata = self._build_context_metadata(message, context)
        return exec_context

    def _build_execution_context(self, state) -> ExecutionContext:
        """Build the base execution context."""
        return ExecutionContext(
            run_id=f"demo_{datetime.now(UTC).timestamp()}",
            agent_name=self.agent_name,
            state=state,
            stream_updates=True
        )

    def _build_context_metadata(self, message: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build the metadata for execution context."""
        return {
            "message": message,
            "context": context or {},
            "industry": self._get_industry_from_context(context)
        }
        
    def _convert_result_to_response(self, result: ExecutionResult) -> Dict[str, Any]:
        """Convert execution result to process response format."""
        if result.success:
            return result.result
        return self._create_error_response_from_result(result)
            
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute demo core logic with modern architecture patterns."""
        message = context.metadata.get("message")
        demo_context = context.metadata.get("context", {})
        
        prompt = self._prepare_demo_prompt(message, demo_context)
        response = await self._generate_llm_response(prompt)
        enhanced_response = self._enhance_with_metrics(response, demo_context)
        return self._create_success_response(enhanced_response, demo_context)
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for demo processing."""
        message = context.metadata.get("message")
        if not message or not isinstance(message, str):
            return False
        if len(message.strip()) == 0:
            return False
        return self._validate_demo_context(context)
        
    def _validate_demo_context(self, context: ExecutionContext) -> bool:
        """Validate demo-specific context requirements."""
        industry = context.metadata.get("industry")
        if not industry or not isinstance(industry, str):
            return False
        return True
        
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
        role_section = self._build_role_section(industry)
        context_section = self._build_context_section(industry, message)
        requirements_section = self._build_requirements_section()
        return f"{role_section}\n\n{context_section}\n\n{requirements_section}"

    def _build_role_section(self, industry: str) -> str:
        """Build the role definition section of the prompt."""
        role_intro = f"You are an AI optimization expert demonstrating the Netra platform to a {industry} enterprise customer."
        responsibilities = self._build_role_responsibilities()
        return f"{role_intro}\n\n{responsibilities}"

    def _build_role_responsibilities(self) -> str:
        """Build the role responsibilities section."""
        return """Your role is to:
1. Analyze their specific AI workload challenges
2. Provide concrete, quantified optimization recommendations
3. Show immediate business value with specific metrics
4. Be professional yet engaging"""

    def _build_context_section(self, industry: str, message: str) -> str:
        """Build the context section of the prompt."""
        return f"""Industry Context: {industry}
Customer Message: {message}"""

    def _build_requirements_section(self) -> str:
        """Build the requirements section of the prompt."""
        requirements = self._get_response_requirements()
        focus = "Focus on demonstrable value and actionable insights."
        return f"Provide a response that:\n{requirements}\n\n{focus}"

    def _get_response_requirements(self) -> str:
        """Get the specific response requirements."""
        return """- Identifies 2-3 specific optimization opportunities
- Quantifies potential improvements (cost, latency, throughput)
- Suggests immediate next steps
- Maintains enterprise-level professionalism
- Uses industry-specific terminology and examples"""
        
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
        logger.error(f"Demo service processing error: {str(error)}")
        return {
            "status": "error",
            "error": str(error),
            "agent": self.agent_name
        }
        
    def _create_error_response_from_result(self, result: ExecutionResult) -> Dict[str, Any]:
        """Create error response from execution result."""
        return {
            "status": "error",
            "error": result.error,
            "agent": self.agent_name,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": result.retry_count
        }
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get demo service health status."""
        return {
            "agent_name": self.agent_name,
            "industry": self.industry,
            "demo_mode": self.demo_mode,
            "execution_engine": self.execution_engine.get_health_status(),
            "reliability": self.reliability_manager.get_health_status()
        }