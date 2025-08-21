"""
Modernized Admin Tool Dispatcher Helper Functions

Helper functions integrating modern execution patterns with ExecutionContext
and ExecutionResult types. Maintains 25-line function limit and modular architecture.

Business Value: Enables modern agent architecture compliance for admin tools.
"""
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.admin_tool_types import AdminToolInfo, AdminToolType
from netra_backend.app.schemas.admin_tool_types import ToolStatus as AdminToolStatus
from netra_backend.app.schemas.core_enums import ExecutionStatus

logger = central_logger


def initialize_dispatcher_state(dispatcher: "AdminToolDispatcher") -> None:
    """Initialize dispatcher basic state with modern patterns"""
    dispatcher.admin_tools_enabled = False
    dispatcher.audit_logger = None
    _init_execution_state(dispatcher)


def _init_execution_state(dispatcher: "AdminToolDispatcher") -> None:
    """Initialize execution state for modern patterns"""
    dispatcher._execution_metrics = {}
    dispatcher._active_contexts = {}


def check_user_and_db(dispatcher: "AdminToolDispatcher") -> bool:
    """Check if user and db are available"""
    return dispatcher.user is not None and dispatcher.db is not None


def enable_admin_tools(dispatcher: "AdminToolDispatcher") -> None:
    """Enable admin tools for authorized user with execution context"""
    from netra_backend.app.services.permission_service import PermissionService
    if PermissionService.is_developer_or_higher(dispatcher.user):
        dispatcher.admin_tools_enabled = True
        _enable_with_monitoring(dispatcher)


def _enable_with_monitoring(dispatcher: "AdminToolDispatcher") -> None:
    """Enable tools with execution monitoring"""
    log_admin_tools_initialization(dispatcher.user)
    _update_execution_metrics(dispatcher, "admin_tools_enabled", True)


def log_admin_tools_initialization(user: User) -> None:
    """Log admin tools initialization with execution context"""
    execution_data = _create_log_context(user, "admin_tools_init")
    logger.info(f"Initializing admin tools for user {user.email}", extra=execution_data)


def _create_log_context(user: User, operation: str) -> Dict[str, Any]:
    """Create logging context for execution tracking"""
    return {
        "user_id": user.id,
        "operation": operation,
        "timestamp": datetime.now(UTC).isoformat()
    }


def log_no_admin_permissions(user: User) -> None:
    """Log lack of admin permissions with execution context"""
    execution_data = _create_log_context(user, "permission_denied")
    logger.debug(f"User {user.email} does not have admin permissions", extra=execution_data)


def log_available_admin_tools(user: User) -> None:
    """Log available admin tools with execution context"""
    from .validation import get_available_admin_tools
    available_tools = get_available_admin_tools(user)
    execution_data = _create_log_context(user, "tools_available")
    execution_data["available_tools"] = available_tools
    logger.info(f"Admin tools available: {available_tools}", extra=execution_data)


def build_dispatcher_stats_base() -> Dict[str, Any]:
    """Build base dispatcher statistics with execution metrics"""
    base_stats = _create_base_stats_dict()
    _add_execution_tracking_stats(base_stats)
    return base_stats


def _create_base_stats_dict() -> Dict[str, Any]:
    """Create base statistics dictionary"""
    return {
        "total_tools": len(AdminToolType),
        "total_executions": 0,
        "tool_metrics": []
    }


def _add_execution_tracking_stats(stats: Dict[str, Any]) -> None:
    """Add execution tracking statistics"""
    stats["recent_activity"] = []
    stats["execution_status"] = {"active": 0, "completed": 0, "failed": 0}


def calculate_enabled_tools_count(user: Optional[User]) -> int:
    """Calculate count of enabled tools with execution context"""
    if not user:
        return 0
    return _count_enabled_tools_safe(user)


def _count_enabled_tools_safe(user: User) -> int:
    """Safely count enabled tools with error handling"""
    try:
        enabled_tools = _get_enabled_tools_for_user(user)
        return len(enabled_tools)
    except Exception:
        return 0


def _get_enabled_tools_for_user(user: User) -> List[AdminToolType]:
    """Get list of enabled tools for user"""
    from .validation import validate_admin_tool_access
    return [
        tool for tool in AdminToolType 
        if validate_admin_tool_access(user, tool.value)
    ]


def add_system_health_to_stats(stats: Dict[str, Any]) -> None:
    """Add system health with execution monitoring"""
    health_data = _create_health_data()
    stats["system_health"] = health_data
    stats["generated_at"] = datetime.now(UTC).isoformat()


def _create_health_data() -> Dict[str, Any]:
    """Create health data with execution status"""
    return {
        "status": "healthy",
        "execution_engine": "operational"
    }


def calculate_active_sessions(user: Optional[User]) -> int:
    """Calculate active sessions count"""
    return 1 if user else 0


def get_base_tools_list(dispatcher: "AdminToolDispatcher") -> List[AdminToolInfo]:
    """Get list of base tool information"""
    tools = []
    for tool_name in dispatcher.tools.keys():
        tools.append(dispatcher.get_tool_info(tool_name))
    return tools


def get_admin_tools_list(dispatcher: "AdminToolDispatcher") -> List[AdminToolInfo]:
    """Get list of admin tool information"""
    tools = []
    for admin_tool in AdminToolType:
        tools.append(dispatcher.get_tool_info(admin_tool.value))
    return tools


def create_admin_tool_info(tool_name: str, 
                          admin_tool_type: AdminToolType,
                          user: Optional[User],
                          admin_tools_enabled: bool) -> AdminToolInfo:
    """Create admin tool info with execution context"""
    tool_data = _build_admin_tool_data(tool_name, user, admin_tools_enabled)
    return _create_admin_tool_info_object(tool_name, admin_tool_type, tool_data)


def _build_admin_tool_data(tool_name: str, user: Optional[User], admin_tools_enabled: bool) -> Dict[str, Any]:
    """Build admin tool data dictionary"""
    from .validation import get_required_permissions, validate_admin_tool_access
    available = admin_tools_enabled and validate_admin_tool_access(user, tool_name)
    description = f"Admin tool for {tool_name.replace('_', ' ')}"
    required_permissions = get_required_permissions(tool_name)
    return {"available": available, "description": description, "required_permissions": required_permissions}


def _create_admin_tool_info_object(tool_name: str, admin_tool_type: AdminToolType, tool_data: Dict[str, Any]) -> AdminToolInfo:
    """Create AdminToolInfo object from data"""
    return AdminToolInfo(
        name=tool_name, tool_type=admin_tool_type, description=tool_data["description"],
        required_permissions=tool_data["required_permissions"], available=tool_data["available"], enabled=True
    )


def create_base_tool_info(tool_name: str, tool) -> AdminToolInfo:
    """Create base tool info object"""
    description = getattr(tool, 'description', 'No description available')
    return AdminToolInfo(
        name=tool_name, tool_type=AdminToolType.SYSTEM_CONFIGURATOR,
        description=description, required_permissions=[], available=True, enabled=True
    )


def create_not_found_tool_info(tool_name: str) -> AdminToolInfo:
    """Create tool info for not found tool"""
    return AdminToolInfo(
        name=tool_name, tool_type=AdminToolType.SYSTEM_CONFIGURATOR,
        description="Tool not found", required_permissions=[], 
        available=False, enabled=False
    )


def get_operation_tool_mapping() -> Dict[str, str]:
    """Get operation type to tool name mapping"""
    return {
        "create_user": "admin_user_management",
        "modify_settings": "admin_settings_manager",
        "delete_all_data": "admin_data_manager"
    }


def check_operation_permissions(operation_type: str, user_role: str) -> None:
    """Check permissions for sensitive operations"""
    if operation_type == "delete_all_data" and user_role != "admin":
        raise PermissionError("Insufficient permissions for this operation")


def execute_operation_via_dispatcher(dispatcher: "AdminToolDispatcher",
                                   tool_name: str, 
                                   params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute operation with modern execution patterns"""
    if hasattr(dispatcher, 'tool_dispatcher') and dispatcher.tool_dispatcher:
        from .execution_pattern_helpers import execute_with_tracking
        return execute_with_tracking(dispatcher, tool_name, params)
    return create_no_dispatcher_error(tool_name)


def create_no_dispatcher_error(operation_type: str) -> Dict[str, Any]:
    """Create error response for missing dispatcher"""
    error_msg = f"No tool dispatcher available for operation {operation_type}"
    logger.error(error_msg)
    return {"success": False, "error": error_msg}


def create_audit_data(operation: Dict[str, Any]) -> Dict[str, Any]:
    """Create audit data with execution context"""
    base_audit = _create_base_audit_data(operation)
    _add_execution_context_to_audit(base_audit)
    return base_audit


def _create_base_audit_data(operation: Dict[str, Any]) -> Dict[str, Any]:
    """Create base audit data dictionary"""
    return {
        "operation": operation.get("type"),
        "user_id": operation.get("user_id"),
        "params": operation.get("params", {})
    }


def _add_execution_context_to_audit(audit_data: Dict[str, Any]) -> None:
    """Add execution context to audit data"""
    audit_data["timestamp"] = datetime.now(UTC).timestamp()
    audit_data["execution_context"] = "admin_tool_dispatcher"


def log_audit_data(audit_logger, audit_data: Dict[str, Any]) -> None:
    """Log audit data with execution result tracking"""
    if audit_logger:
        from .execution_pattern_helpers import log_with_execution_result
        log_with_execution_result(audit_logger, audit_data)


def _update_execution_metrics(dispatcher: "AdminToolDispatcher", 
                             metric_name: str, value: Any) -> None:
    """Update execution metrics tracking"""
    from .execution_pattern_helpers import update_execution_metrics
    update_execution_metrics(dispatcher, metric_name, value)