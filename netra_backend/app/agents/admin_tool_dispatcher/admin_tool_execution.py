# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Modernize admin_tool_execution.py to use standardized execution patterns
# Git: 8-18-25-AM | Modernizing to standard agent patterns
# Change: Modernize | Scope: Module | Risk: Low
# Session: admin-tool-modernization | Seq: 1
# Review: Complete | Score: 100
# ================================

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from netra_backend.app.core.resilience.domain_circuit_breakers import (
    AgentCircuitBreaker,
    AgentCircuitBreakerConfig
)
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability import ReliabilityManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.admin_tool_types import (
    ToolFailureResponse,
    ToolResponse,
    ToolStatus,
    ToolSuccessResponse,
)
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.schemas.tool import ToolInput

if TYPE_CHECKING:
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_core import AdminToolDispatcher

logger = central_logger.get_logger(__name__)


class AdminToolExecutionEngine:
    """Modern admin tool execution engine.
    
    Provides execution patterns with integrated reliability.
    """
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.agent_name = "admin_tool_execution"
        self.execution_engine = self._create_execution_engine()
        self.dispatcher_instance = None  # Set by dispatch_admin_tool
        
    def _create_execution_engine(self) -> BaseExecutionEngine:
        """Create execution engine with reliability patterns."""
        reliability_manager = self._create_reliability_manager()
        monitor = ExecutionMonitor()
        return BaseExecutionEngine(reliability_manager, monitor)


    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with unified agent circuit breaker."""
        circuit_config = AgentCircuitBreakerConfig(
            failure_threshold=3, 
            recovery_timeout_seconds=30.0,
            task_timeout_seconds=180.0  # Admin tools may take longer
        )
        self.circuit_breaker = AgentCircuitBreaker("admin_tool_execution", config=circuit_config)
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)


    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute admin tool with modern patterns."""
        dispatcher = self.dispatcher_instance
        tool_name = context.metadata.get('tool_name')
        kwargs = context.metadata.get('kwargs', {})
        return await self._execute_tool_with_validation(dispatcher, tool_name, kwargs)


    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate admin tool execution preconditions."""
        dispatcher = self.dispatcher_instance
        tool_name = context.metadata.get('tool_name')
        return self._check_permissions_and_access(dispatcher, tool_name)


    def _check_permissions_and_access(self, dispatcher, tool_name: str) -> bool:
        """Check permissions and tool access."""
        if not dispatcher.admin_tools_enabled:
            return False
        return self._validate_tool_access(dispatcher, tool_name)


    def _validate_tool_access(self, dispatcher, tool_name: str) -> bool:
        """Validate specific tool access."""
        from netra_backend.app.agents.admin_tool_dispatcher.validation import validate_admin_tool_access
        return validate_admin_tool_access(dispatcher.user, tool_name)


    async def _execute_tool_with_validation(self, dispatcher, tool_name: str, 
                                           kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with validation."""
        action = kwargs.get('action', 'default')
        result = await self._execute_tool_by_name(dispatcher, tool_name, action, kwargs)
        return self._format_execution_result(result)


    async def _execute_tool_by_name(self, dispatcher, tool_name: str, 
                                   action: str, kwargs: Dict[str, Any]) -> Any:
        """Execute admin tool by name."""
        from netra_backend.app.agents.admin_tool_dispatcher.tool_handlers import execute_admin_tool
        return await execute_admin_tool(
            tool_name, dispatcher.user, dispatcher.db, action, **kwargs
        )


    def _format_execution_result(self, result: Any) -> Dict[str, Any]:
        """Format raw execution result for standardized return."""
        if isinstance(result, dict):
            return result
        return {"data": result, "formatted": True}


# Global execution engine instance for backward compatibility
_execution_engine = AdminToolExecutionEngine()


async def dispatch_admin_tool(dispatcher, tool_name: str, tool_input, **kwargs):
    """Main dispatch function - backward compatible interface."""
    _execution_engine.dispatcher_instance = dispatcher
    context = _create_execution_context(dispatcher, tool_name, kwargs)
    result = await _execution_engine.execution_engine.execute(_execution_engine, context)
    return _convert_to_tool_response(result, tool_name, dispatcher, kwargs)


def _create_execution_context(dispatcher, tool_name: str, kwargs: Dict[str, Any]) -> ExecutionContext:
    """Create execution context for modern interface."""
    from netra_backend.app.agents.state import DeepAgentState
    state = DeepAgentState(user_id=getattr(dispatcher.user, 'id', 'unknown'))
    metadata = _build_context_metadata(tool_name, kwargs, dispatcher)
    run_id = _generate_run_id(tool_name)
    return ExecutionContext(run_id=run_id, agent_name="admin_tool_execution", state=state, metadata=metadata)


def _build_context_metadata(tool_name: str, kwargs: Dict[str, Any], dispatcher) -> Dict[str, Any]:
    """Build metadata for execution context."""
    return {'tool_name': tool_name, 'kwargs': kwargs, 'dispatcher': dispatcher}


def _generate_run_id(tool_name: str) -> str:
    """Generate unique run ID for execution."""
    return f"admin_tool_{tool_name}_{datetime.now(UTC).isoformat()}"


def _convert_to_tool_response(result: ExecutionResult, tool_name: str, 
                             dispatcher, kwargs: Dict[str, Any]) -> ToolResponse:
    """Convert ExecutionResult to ToolResponse for backward compatibility."""
    if result.success:
        return _create_success_response(result, tool_name, dispatcher, kwargs)
    return _create_failure_response(result, tool_name, dispatcher)


def _create_success_response(result: ExecutionResult, tool_name: str,
                           dispatcher, kwargs: Dict[str, Any]) -> ToolSuccessResponse:
    """Create success response from ExecutionResult."""
    user_id = _get_user_id_from_dispatcher(dispatcher)
    metadata = _create_response_metadata(kwargs)
    return ToolSuccessResponse(tool_name=tool_name, status=ToolStatus.COMPLETED, user_id=user_id, execution_time_ms=result.execution_time_ms, result=result.result or {}, metadata=metadata)


def _get_user_id_from_dispatcher(dispatcher) -> str:
    """Get user ID from dispatcher safely."""
    return getattr(dispatcher.user, 'id', 'unknown')


def _create_failure_response(result: ExecutionResult, tool_name: str,
                           dispatcher) -> ToolFailureResponse:
    """Create failure response from ExecutionResult."""
    user_id = _get_user_id_from_dispatcher(dispatcher)
    error_msg = result.error or "Execution failed"
    return ToolFailureResponse(tool_name=tool_name, status=ToolStatus.FAILED, user_id=user_id, execution_time_ms=result.execution_time_ms, error=error_msg)


def _create_response_metadata(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata for response."""
    return {
        "admin_action": True,
        "action": kwargs.get('action', 'default'),
        "modern_execution": True
    }


# =============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS - Legacy interface support
# =============================================================================


async def validate_tool_permissions(dispatcher, tool_name: str, 
                                   start_time: datetime) -> Optional[ToolResponse]:
    """Legacy validation function for backward compatibility."""
    engine = AdminToolExecutionEngine()
    if not engine._check_permissions_and_access(dispatcher, tool_name):
        return _create_permission_denied_response(tool_name, start_time)
    return None


def _create_permission_denied_response(tool_name: str, start_time: datetime) -> ToolFailureResponse:
    """Create permission denied response."""
    return ToolFailureResponse(
        tool_name=tool_name, status=ToolStatus.FAILED, execution_time_ms=0.0,
        started_at=start_time, completed_at=datetime.now(UTC),
        user_id="unknown", error="Admin tools not available - insufficient permissions"
    )


def check_admin_tools_enabled(dispatcher) -> bool:
    """Legacy function for checking admin tools enabled."""
    return dispatcher.admin_tools_enabled


def get_user_id_safe(dispatcher) -> str:
    """Legacy function for getting user ID safely."""
    return getattr(dispatcher.user, 'id', 'unknown') if dispatcher.user else 'unknown'


async def validate_tool_input_safely(tool_name: str, **kwargs) -> str | None:
    """Legacy function for input validation."""
    from netra_backend.app.agents.admin_tool_dispatcher.validation import validate_tool_input
    return validate_tool_input(tool_name, **kwargs)


# Export the execution engine for direct access if needed
__all__ = [
    'AdminToolExecutionEngine', 'dispatch_admin_tool', 'validate_tool_permissions',
    'check_admin_tools_enabled', 'get_user_id_safe', 'validate_tool_input_safely'
]