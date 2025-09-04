"""Base Components for Modernized Corpus Handlers

Shared utilities and base patterns for corpus tool handlers.
Maintains 25-line function limit and modular architecture.

Business Value: Eliminates duplicate patterns across corpus handlers.
"""

from typing import Any, Dict

from netra_backend.app.agents.admin_tool_dispatcher.corpus_models import (
    CorpusToolRequest,
    CorpusToolResponse,
    CorpusToolType,
)
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.schemas.shared_types import RetryConfig


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
        user_context = CorpusContextHelper._create_user_context_from_request(request)
        return CorpusContextHelper._build_execution_context(request, user_context)
        
    @staticmethod
    def _create_user_context_from_request(request: CorpusToolRequest):
        """Create UserExecutionContext from request."""
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        import uuid
        
        # Extract user_id from request or use placeholder
        user_id = getattr(request, 'user_id', None) or f"corpus_user_{uuid.uuid4().hex[:8]}"
        
        # Use UnifiedIDManager for consistent thread ID generation
        base_thread_id = UnifiedIDManager.generate_thread_id()
        thread_id = f"corpus_{request.tool_type.value}_{base_thread_id}"
        
        # Generate run_id using the canonical format
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            metadata={'user_request': request.model_dump()}
        )
        
    @staticmethod
    def _build_execution_context(request: CorpusToolRequest, user_context) -> ExecutionContext:
        """Build execution context with proper configuration."""
        return ExecutionContext(
            run_id=user_context.run_id,
            agent_name="corpus_tool_handler",
            state=user_context,
            metadata=user_context.metadata,
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