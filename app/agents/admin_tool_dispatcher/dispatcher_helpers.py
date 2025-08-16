"""
Admin Tool Dispatcher Helper Functions

Helper functions to support the core dispatcher while maintaining 
the 8-line function limit and modular architecture.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.schemas.admin_tool_types import (
    AdminToolType, AdminToolInfo, ToolStatus as AdminToolStatus
)
from app.logging_config import central_logger

logger = central_logger


def initialize_dispatcher_state(dispatcher: "AdminToolDispatcher") -> None:
    """Initialize dispatcher basic state"""
    dispatcher.admin_tools_enabled = False
    dispatcher.audit_logger = None


def check_user_and_db(dispatcher: "AdminToolDispatcher") -> bool:
    """Check if user and db are available"""
    return dispatcher.user is not None and dispatcher.db is not None


def enable_admin_tools(dispatcher: "AdminToolDispatcher") -> None:
    """Enable admin tools for authorized user"""
    from app.services.permission_service import PermissionService
    if PermissionService.is_developer_or_higher(dispatcher.user):
        dispatcher.admin_tools_enabled = True
        log_admin_tools_initialization(dispatcher.user)


def log_admin_tools_initialization(user: User) -> None:
    """Log admin tools initialization"""
    logger.info(f"Initializing admin tools for user {user.email}")


def log_no_admin_permissions(user: User) -> None:
    """Log lack of admin permissions"""
    logger.debug(f"User {user.email} does not have admin permissions")


def log_available_admin_tools(user: User) -> None:
    """Log available admin tools for user"""
    from .validation import get_available_admin_tools
    available_tools = get_available_admin_tools(user)
    logger.info(f"Admin tools available: {available_tools}")


def build_dispatcher_stats_base() -> Dict[str, Any]:
    """Build base dispatcher statistics"""
    return {
        "total_tools": len(AdminToolType),
        "total_executions": 0,
        "tool_metrics": [],
        "recent_activity": []
    }


def calculate_enabled_tools_count(user: Optional[User]) -> int:
    """Calculate count of enabled tools for user"""
    if not user:
        return 0
    enabled_tools = _get_enabled_tools_for_user(user)
    return len(enabled_tools)


def _get_enabled_tools_for_user(user: User) -> List[AdminToolType]:
    """Get list of enabled tools for user"""
    from .validation import validate_admin_tool_access
    return [
        tool for tool in AdminToolType 
        if validate_admin_tool_access(user, tool.value)
    ]


def add_system_health_to_stats(stats: Dict[str, Any]) -> None:
    """Add system health information to stats"""
    stats["system_health"] = {"status": "healthy"}
    stats["generated_at"] = datetime.now(UTC).isoformat()


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
    """Create admin tool info object"""
    tool_data = _build_admin_tool_data(tool_name, user, admin_tools_enabled)
    return _create_admin_tool_info_object(tool_name, admin_tool_type, tool_data)


def _build_admin_tool_data(tool_name: str, user: Optional[User], admin_tools_enabled: bool) -> Dict[str, Any]:
    """Build admin tool data dictionary"""
    from .validation import validate_admin_tool_access, get_required_permissions
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
    """Execute operation via tool dispatcher if available"""
    if hasattr(dispatcher, 'tool_dispatcher') and dispatcher.tool_dispatcher:
        return dispatcher.tool_dispatcher.execute_tool(tool_name, params)
    return create_no_dispatcher_error(tool_name)


def create_no_dispatcher_error(operation_type: str) -> Dict[str, Any]:
    """Create error response for missing dispatcher"""
    error_msg = f"No tool dispatcher available for operation {operation_type}"
    logger.error(error_msg)
    return {"success": False, "error": error_msg}


def create_audit_data(operation: Dict[str, Any]) -> Dict[str, Any]:
    """Create audit data for logging"""
    return {
        "operation": operation.get("type"),
        "user_id": operation.get("user_id"),
        "params": operation.get("params", {}),
        "timestamp": datetime.now(UTC).timestamp()
    }


def log_audit_data(audit_logger, audit_data: Dict[str, Any]) -> None:
    """Log audit data if logger available"""
    if audit_logger:
        audit_logger.log(audit_data)