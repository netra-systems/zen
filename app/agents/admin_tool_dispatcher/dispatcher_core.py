"""
Core Admin Tool Dispatcher Module

Provides the main AdminToolDispatcher class with core functionality
for handling admin-level tool operations with proper authorization.
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
from app.agents.tool_dispatcher import ToolDispatcher
from app.db.models_postgres import User
from app.services.permission_service import PermissionService
from app.logging_config import central_logger
from datetime import datetime, UTC

logger = central_logger


class AdminToolDispatcher(ToolDispatcher):
    """Extended tool dispatcher that includes admin tools for privileged users"""
    
    def __init__(self, 
                 llm_manager=None,
                 tool_dispatcher=None,
                 tools: List[BaseTool] = None, 
                 db: Optional[Session] = None,
                 user: Optional[User] = None) -> None:
        """Initialize the admin tool dispatcher with proper type annotations"""
        super().__init__(tools or [])
        self._set_manager_properties(llm_manager, tool_dispatcher, db, user)
        self._initialize_admin_access()
    
    def _set_manager_properties(self, llm_manager, tool_dispatcher, db, user) -> None:
        """Set manager properties and initialize state"""
        from .dispatcher_helpers import initialize_dispatcher_state
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.db = db
        self.user = user
        initialize_dispatcher_state(self)

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
    
    async def dispatch(self, tool_name: str, **kwargs) -> ToolResponse:
        """Dispatch tool execution with admin tool support and proper typing"""
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        
        if self._is_admin_tool(tool_name):
            return await self._dispatch_admin_tool_safe(tool_name, tool_input, **kwargs)
        
        return await self._dispatch_base_tool(tool_name, **kwargs)
    
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
        return await dispatch_admin_tool(
            self, tool_name, tool_input, **kwargs
        )
    
    async def _dispatch_base_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """Dispatch base tool and convert to typed response"""
        base_result = await super().dispatch(tool_name, **kwargs)
        return self._convert_base_result_to_response(tool_name, base_result)
    
    def _convert_base_result_to_response(self, 
                                         tool_name: str, 
                                         base_result: ToolResult) -> ToolResponse:
        """Convert base ToolResult to typed ToolResponse"""
        current_time = datetime.now(UTC)
        user_id = self.user.id if self.user else "unknown"
        
        if base_result.status == ToolStatus.SUCCESS:
            return self._create_success_response(tool_name, base_result, current_time, user_id)
        else:
            return self._create_failure_response(tool_name, base_result, current_time, user_id)
    
    def _create_success_response(self, 
                                 tool_name: str, 
                                 base_result: ToolResult,
                                 current_time: datetime,
                                 user_id: str) -> ToolSuccessResponse:
        """Create successful tool response"""
        return ToolSuccessResponse(
            tool_name=tool_name,
            status=AdminToolStatus.COMPLETED,
            execution_time_ms=0.0,
            started_at=current_time,
            completed_at=current_time,
            user_id=user_id,
            result=base_result.payload or {},
            message=base_result.message
        )
    
    def _create_failure_response(self, 
                                 tool_name: str, 
                                 base_result: ToolResult,
                                 current_time: datetime,
                                 user_id: str) -> ToolFailureResponse:
        """Create failed tool response"""
        return ToolFailureResponse(
            tool_name=tool_name,
            status=AdminToolStatus.FAILED,
            execution_time_ms=0.0,
            started_at=current_time,
            completed_at=current_time,
            user_id=user_id,
            error=base_result.message or "Unknown error"
        )
    
    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the admin tool dispatcher"""
        from .dispatcher_helpers import (
            build_dispatcher_stats_base, calculate_enabled_tools_count,
            add_system_health_to_stats, calculate_active_sessions
        )
        stats = build_dispatcher_stats_base()
        stats["enabled_tools"] = calculate_enabled_tools_count(self.user)
        stats["active_sessions"] = calculate_active_sessions(self.user)
        add_system_health_to_stats(stats)
        return stats
    
    def has_admin_access(self) -> bool:
        """Check if the current user has admin access"""
        return self.admin_tools_enabled
    
    def list_all_tools(self) -> List[AdminToolInfo]:
        """List all available tools including admin tools"""
        all_tools = self._get_base_tool_info()
        if self.admin_tools_enabled:
            all_tools.extend(self._get_admin_tool_info())
        return all_tools
    
    def _get_base_tool_info(self) -> List[AdminToolInfo]:
        """Get information about base tools"""
        from .dispatcher_helpers import get_base_tools_list
        return get_base_tools_list(self)
    
    def _get_admin_tool_info(self) -> List[AdminToolInfo]:
        """Get information about admin tools"""
        from .dispatcher_helpers import get_admin_tools_list
        return get_admin_tools_list(self)
    
    def get_tool_info(self, tool_name: str) -> AdminToolInfo:
        """Get information about a specific tool"""
        if self._is_admin_tool(tool_name):
            return self._get_admin_tool_info_detail(tool_name)
        
        if tool_name in self.tools:
            return self._get_base_tool_info_detail(tool_name)
        
        return self._get_not_found_tool_info(tool_name)
    
    def _get_admin_tool_info_detail(self, tool_name: str) -> AdminToolInfo:
        """Get detailed information about an admin tool"""
        from .dispatcher_helpers import create_admin_tool_info
        try:
            admin_tool_type = AdminToolType(tool_name)
            return create_admin_tool_info(
                tool_name, admin_tool_type, self.user, self.admin_tools_enabled
            )
        except ValueError:
            return self._get_not_found_tool_info(tool_name)
    
    def _get_base_tool_info_detail(self, tool_name: str) -> AdminToolInfo:
        """Get detailed information about a base tool"""
        from .dispatcher_helpers import create_base_tool_info
        tool = self.tools[tool_name]
        return create_base_tool_info(tool_name, tool)
    
    def _get_not_found_tool_info(self, tool_name: str) -> AdminToolInfo:
        """Get information for a tool that was not found"""
        from .dispatcher_helpers import create_not_found_tool_info
        return create_not_found_tool_info(tool_name)
    
    async def dispatch_admin_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch admin operation based on operation type"""
        operation_type = operation.get("type")
        params = operation.get("params", {})
        user_role = operation.get("user_role", "user")
        
        self._check_operation_permissions(operation_type, user_role)
        tool_name = self._get_operation_tool_name(operation_type)
        return await self._execute_operation_with_audit(tool_name, params, operation)
    
    def _check_operation_permissions(self, operation_type: str, user_role: str) -> None:
        """Check permissions for sensitive operations"""
        from .dispatcher_helpers import check_operation_permissions
        check_operation_permissions(operation_type, user_role)
    
    def _get_operation_tool_name(self, operation_type: str) -> str:
        """Get tool name for operation type"""
        from .dispatcher_helpers import get_operation_tool_mapping
        tool_mapping = get_operation_tool_mapping()
        tool_name = tool_mapping.get(operation_type)
        if not tool_name:
            raise ValueError(f"Unknown operation type: {operation_type}")
        return tool_name
    
    async def _execute_operation_with_audit(self, tool_name: str, 
                                           params: Dict[str, Any],
                                           operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation and audit the result"""
        try:
            result = await self._execute_operation_safely(tool_name, params)
            await self._log_audit_operation(operation)
            return result
        except Exception as e:
            await self._log_audit_operation(operation)
            return {"success": False, "error": str(e)}
    
    async def _execute_operation_safely(self, tool_name: str, 
                                       params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation via tool dispatcher if available"""
        from .dispatcher_helpers import execute_operation_via_dispatcher, create_no_dispatcher_error
        if hasattr(self, 'tool_dispatcher') and self.tool_dispatcher:
            return await execute_operation_via_dispatcher(self, tool_name, params)
        return create_no_dispatcher_error(tool_name)
    
    async def _log_audit_operation(self, operation: Dict[str, Any]) -> None:
        """Log audit information for admin operations"""
        from .dispatcher_helpers import create_audit_data, log_audit_data
        if hasattr(self, 'audit_logger') and self.audit_logger:
            audit_data = create_audit_data(operation)
            await log_audit_data(self.audit_logger, audit_data)