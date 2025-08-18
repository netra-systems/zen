"""Base Components for Modernized Corpus Handlers

Shared utilities and base patterns for corpus tool handlers.
Maintains 8-line function limit and modular architecture.

Business Value: Eliminates duplicate patterns across corpus handlers.
"""

from typing import Dict, Any
from app.agents.base.interface import ExecutionContext
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.executor import BaseExecutionEngine
from app.schemas.shared_types import RetryConfig
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from .corpus_models import CorpusToolRequest, CorpusToolResponse, CorpusToolType


class CorpusHandlerBase:
    """Base class for corpus handlers with common reliability setup."""
    
    def setup_reliability_components(self, handler_name: str, failure_threshold: int = 3, 
                                   recovery_timeout: int = 30) -> None:
        """Setup reliability and monitoring components."""
        circuit_config = CircuitBreakerConfig(handler_name, failure_threshold, recovery_timeout)
        retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=15.0)
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)


class CorpusContextHelper:
    """Helper for creating execution contexts from corpus tool requests."""
    
    @staticmethod
    def create_context_from_request(request: CorpusToolRequest) -> ExecutionContext:
        """Create execution context from tool request."""
        state = CorpusContextHelper._create_state_from_request(request)
        return CorpusContextHelper._build_execution_context(request, state)
        
    @staticmethod
    def _create_state_from_request(request: CorpusToolRequest):
        """Create agent state from request."""
        from app.agents.state import DeepAgentState
        return DeepAgentState(user_request=request.model_dump())
        
    @staticmethod
    def _build_execution_context(request: CorpusToolRequest, state) -> ExecutionContext:
        """Build execution context with proper configuration."""
        return ExecutionContext(
            run_id=f"corpus_tool_{request.tool_type.value}",
            agent_name="corpus_tool_handler",
            state=state,
            stream_updates=False
        )


class CorpusResponseConverter:
    """Converter for execution results to corpus tool responses."""
    
    @staticmethod
    def convert_result_to_response(result) -> CorpusToolResponse:
        """Convert execution result to corpus tool response."""
        if result.success and result.result:
            return CorpusResponseConverter._create_success_response(result.result)
        return CorpusResponseConverter._create_error_response(result.error)
        
    @staticmethod
    def _create_success_response(result_data: Dict[str, Any]) -> CorpusToolResponse:
        """Create successful corpus tool response."""
        return CorpusToolResponse(**result_data)
        
    @staticmethod
    def _create_error_response(error: str) -> CorpusToolResponse:
        """Create error corpus tool response."""
        return CorpusToolResponse(
            success=False,
            tool_type=CorpusToolType.CREATE,
            error=error or "Unknown error"
        )