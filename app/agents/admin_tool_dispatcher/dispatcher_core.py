"""
Modernized Admin Tool Dispatcher Core

Provides AdminToolDispatcher with modern agent architecture:
- Inherits from BaseExecutionInterface for consistency
- Integrates ReliabilityManager for robust execution
- Uses ExecutionMonitor for performance tracking
- Implements ExecutionErrorHandler for error management

Business Value: 100% compliant with modern agent patterns.
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session

from app.schemas import ToolResult, ToolStatus, ToolInput
from app.schemas.admin_tool_types import (
    ToolResponse, ToolSuccessResponse, ToolFailureResponse,
    AdminToolType, AdminToolInfo,
    ToolStatus as AdminToolStatus
)
from app.schemas.shared_types import RetryConfig

from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.base.interface import BaseExecutionInterface, ExecutionContext, ExecutionResult
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.errors import ExecutionErrorHandler

from app.db.models_postgres import User
from app.services.permission_service import PermissionService
from app.logging_config import central_logger
from datetime import datetime, UTC

logger = central_logger


class AdminToolDispatcher(ToolDispatcher, BaseExecutionInterface):
    """Modernized admin tool dispatcher with BaseExecutionInterface compliance.
    
    Provides advanced error handling, circuit breaker patterns, and monitoring.
    """
    
    def __init__(self, llm_manager=None, tool_dispatcher=None, tools: List[BaseTool] = None,
                 db: Optional[Session] = None, user: Optional[User] = None, 
                 websocket_manager=None) -> None:
        """Initialize with modern agent architecture components."""
        ToolDispatcher.__init__(self, tools or [])
        BaseExecutionInterface.__init__(self, "AdminToolDispatcher", websocket_manager)
        self._setup_dispatcher_components(llm_manager, tool_dispatcher, db, user)
        self._initialize_modern_components()
    
    def _setup_dispatcher_components(self, llm_manager, tool_dispatcher, db, user) -> None:
        """Setup dispatcher components and initialize access"""
        self._set_manager_properties(llm_manager, tool_dispatcher, db, user)
        self._initialize_admin_access()
        
    def _initialize_modern_components(self) -> None:
        """Initialize modern agent architecture components."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
    
    def _set_manager_properties(self, llm_manager, tool_dispatcher, db, user) -> None:
        """Set manager properties and initialize state"""
        from .dispatcher_helpers import initialize_dispatcher_state
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.db = db
        self.user = user
        initialize_dispatcher_state(self)
        
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="admin_tool_dispatcher",
            failure_threshold=3,
            recovery_timeout=30
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )

    def _initialize_admin_access(self) -> None:
        """Initialize admin tools based on user permissions"""
        from .dispatcher_helpers import check_user_and_db
        if not check_user_and_db(self):
            return
        self._enable_admin_tools_if_authorized()
    
    def _enable_admin_tools_if_authorized(self) -> None:
        """Enable admin tools if user has proper permissions"""
        from .dispatcher_helpers import enable_admin_tools, log_no_admin_permissions
        if PermissionService.is_developer_or_higher(self.user):
            enable_admin_tools(self)
            self._log_available_admin_tools()
        else:
            log_no_admin_permissions(self.user)
    
    def _log_available_admin_tools(self) -> None:
        """Log available admin tools for the current user"""
        from .dispatcher_helpers import log_available_admin_tools
        log_available_admin_tools(self.user)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute admin tool dispatch with modern architecture patterns."""
        tool_name = context.metadata.get("tool_name")
        kwargs = context.metadata.get("kwargs", {})
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        
        if self._is_admin_tool(tool_name):
            response = await self._dispatch_admin_tool_safe(tool_name, tool_input, **kwargs)
        else:
            response = await self._dispatch_base_tool(tool_name, **kwargs)
            
        return self._convert_response_to_dict(response)
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for admin tool dispatch."""
        tool_name = context.metadata.get("tool_name")
        if not tool_name:
            return False
        return self._validate_tool_access(tool_name)
        
    async def dispatch(self, tool_name: str, **kwargs) -> ToolResponse:
        """Main dispatch method using modern execution engine."""
        context = self._create_dispatch_context(tool_name, kwargs)
        result = await self.execution_engine.execute(self, context)
        return self._convert_result_to_response(result, tool_name)
    
    def _is_admin_tool(self, tool_name: str) -> bool:
        """Check if a tool is an admin tool"""
        admin_tool_names = [tool.value for tool in AdminToolType]
        return tool_name in admin_tool_names
    
    async def _dispatch_admin_tool_safe(self, 
                                        tool_name: str, 
                                        tool_input: ToolInput,
                                        **kwargs) -> ToolResponse:
        """Safely dispatch admin tool with validation"""
        from .admin_tool_execution import dispatch_admin_tool
        return await dispatch_admin_tool(self, tool_name, tool_input, **kwargs)
    
    async def _dispatch_base_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """Dispatch base tool and convert to typed response"""
        base_result = await super().dispatch(tool_name, **kwargs)
        return self._convert_base_result_to_response(tool_name, base_result)
    
    def _convert_base_result_to_response(self, 
                                         tool_name: str, 
                                         base_result: ToolResult) -> ToolResponse:
        """Convert base ToolResult to typed ToolResponse"""
        response_data = self._prepare_response_data(base_result)
        if base_result.status == ToolStatus.SUCCESS:
            return self._create_success_response(tool_name, base_result, response_data['time'], response_data['user_id'])
        return self._create_failure_response(tool_name, base_result, response_data['time'], response_data['user_id'])
    
    def _prepare_response_data(self, base_result: ToolResult) -> Dict[str, Any]:
        """Prepare common response data."""
        return {
            'time': datetime.now(UTC),
            'user_id': self.user.id if self.user else "unknown"
        }
    
    def _create_success_response(self, 
                                 tool_name: str, 
                                 base_result: ToolResult,
                                 current_time: datetime,
                                 user_id: str) -> ToolSuccessResponse:
        """Create successful tool response"""
        params = self._build_success_response_params(tool_name, base_result, current_time, user_id)
        return ToolSuccessResponse(**params)
    
    def _build_success_response_params(self, tool_name: str, base_result: ToolResult,
                                      current_time: datetime, user_id: str) -> Dict[str, Any]:
        """Build parameters for success response."""
        return self._merge_response_params(
            self._get_base_response_params(tool_name, current_time, user_id),
            self._get_success_specific_params(base_result)
        )
    
    def _get_base_response_params(self, tool_name: str, current_time: datetime, user_id: str) -> Dict[str, Any]:
        """Get base response parameters"""
        return {
            "tool_name": tool_name,
            "execution_time_ms": 0.0,
            "started_at": current_time,
            "completed_at": current_time,
            "user_id": user_id
        }
    
    def _get_success_specific_params(self, base_result: ToolResult) -> Dict[str, Any]:
        """Get success-specific response parameters"""
        return {
            "status": AdminToolStatus.COMPLETED,
            "result": base_result.payload or {},
            "message": base_result.message
        }
    
    def _create_failure_response(self, 
                                 tool_name: str, 
                                 base_result: ToolResult,
                                 current_time: datetime,
                                 user_id: str) -> ToolFailureResponse:
        """Create failed tool response"""
        return ToolFailureResponse(**self._build_failure_response_params(
            tool_name, base_result, current_time, user_id
        ))
    
    def _build_failure_response_params(self, tool_name: str, base_result: ToolResult,
                                      current_time: datetime, user_id: str) -> Dict[str, Any]:
        """Build parameters for failure response."""
        return self._merge_response_params(
            self._get_base_response_params(tool_name, current_time, user_id),
            self._get_failure_specific_params(base_result)
        )
    
    def _get_failure_specific_params(self, base_result: ToolResult) -> Dict[str, Any]:
        """Get failure-specific response parameters"""
        return {
            "status": AdminToolStatus.FAILED,
            "error": base_result.message or "Unknown error"
        }
    
    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the admin tool dispatcher"""
        from .tool_info_helpers import get_dispatcher_stats
        return get_dispatcher_stats(self)
    
    def has_admin_access(self) -> bool:
        """Check if the current user has admin access"""
        return self.admin_tools_enabled
    
    def list_all_tools(self) -> List[AdminToolInfo]:
        """List all available tools including admin tools"""
        from .tool_info_helpers import list_all_tools
        return list_all_tools(self)
    
    def get_tool_info(self, tool_name: str) -> AdminToolInfo:
        """Get information about a specific tool"""
        from .tool_info_helpers import get_tool_info
        return get_tool_info(self, tool_name)
    
    def _merge_response_params(self, base_params: Dict[str, Any], 
                               specific_params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base and specific response parameters."""
        return {**base_params, **specific_params}
    
    async def dispatch_admin_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch admin operation based on operation type"""
        from .operation_helpers import dispatch_admin_operation
        return await dispatch_admin_operation(self, operation)
    
    def _has_valid_tool_dispatcher(self) -> bool:
        """Check if tool dispatcher is available and valid."""
        from .operation_helpers import has_valid_tool_dispatcher
        return has_valid_tool_dispatcher(self)
    
    def _has_valid_audit_logger(self) -> bool:
        """Check if audit logger is available and valid."""
        from .operation_helpers import has_valid_audit_logger
        return has_valid_audit_logger(self)
    
    # Modern execution pattern helper methods
    
    def _create_dispatch_context(self, tool_name: str, kwargs: Dict[str, Any]) -> ExecutionContext:
        """Create execution context for tool dispatch."""
        from .modern_execution_helpers import create_dispatch_context
        return create_dispatch_context(self, tool_name, kwargs)
        
    def _validate_tool_access(self, tool_name: str) -> bool:
        """Validate user has access to the specified tool."""
        from .modern_execution_helpers import validate_tool_access
        return validate_tool_access(self, tool_name)
        
    def _convert_response_to_dict(self, response: ToolResponse) -> Dict[str, Any]:
        """Convert ToolResponse to dictionary format."""
        from .modern_execution_helpers import convert_response_to_dict
        return convert_response_to_dict(response)
        
    def _convert_result_to_response(self, result: ExecutionResult, tool_name: str) -> ToolResponse:
        """Convert ExecutionResult back to ToolResponse format."""
        from .modern_execution_helpers import convert_result_to_response
        return convert_result_to_response(self, result, tool_name)
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including modern components."""
        from .modern_execution_helpers import get_modern_health_status
        return get_modern_health_status(self)