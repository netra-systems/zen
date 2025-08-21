"""
Operation Management Helpers for Admin Tool Dispatcher

Helper functions for operation dispatch and audit management.
Split from dispatcher_core.py to maintain 450-line limit.

Business Value: Enables secure admin operations with full audit trail.
"""
from typing import Dict, Any
from netra_backend.app.logging_config import central_logger

logger = central_logger


async def dispatch_admin_operation(dispatcher, operation: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch admin operation based on operation type"""
    operation_params = extract_operation_params(operation)
    validate_operation_security(operation_params)
    tool_name = get_operation_tool_name(operation_params["type"])
    return await execute_operation_with_audit(dispatcher, tool_name, operation_params["params"], operation)


def extract_operation_params(operation: Dict[str, Any]) -> Dict[str, Any]:
    """Extract operation parameters"""
    return {
        "type": operation.get("type"),
        "params": operation.get("params", {}),
        "user_role": operation.get("user_role", "user")
    }


def validate_operation_security(operation_params: Dict[str, Any]) -> None:
    """Validate operation security and permissions."""
    check_operation_permissions(operation_params["type"], operation_params["user_role"])


def check_operation_permissions(operation_type: str, user_role: str) -> None:
    """Check permissions for sensitive operations"""
    from .dispatcher_helpers import check_operation_permissions
    check_operation_permissions(operation_type, user_role)


def get_operation_tool_name(operation_type: str) -> str:
    """Get tool name for operation type"""
    from .dispatcher_helpers import get_operation_tool_mapping
    tool_mapping = get_operation_tool_mapping()
    tool_name = tool_mapping.get(operation_type)
    if not tool_name:
        raise ValueError(f"Unknown operation type: {operation_type}")
    return tool_name


async def execute_operation_with_audit(dispatcher, tool_name: str, 
                                     params: Dict[str, Any],
                                     operation: Dict[str, Any]) -> Dict[str, Any]:
    """Execute operation and audit the result"""
    try:
        return await execute_and_audit_success(dispatcher, tool_name, params, operation)
    except Exception as e:
        return await handle_operation_error(dispatcher, e, operation)


async def execute_and_audit_success(dispatcher, tool_name: str, 
                                  params: Dict[str, Any],
                                  operation: Dict[str, Any]) -> Dict[str, Any]:
    """Execute operation and audit successful result"""
    result = await execute_operation_safely(dispatcher, tool_name, params)
    await log_audit_operation(dispatcher, operation)
    return result


async def handle_operation_error(dispatcher, error: Exception, operation: Dict[str, Any]) -> Dict[str, Any]:
    """Handle operation execution error."""
    await log_audit_operation(dispatcher, operation)
    return {"success": False, "error": str(error)}


async def execute_operation_safely(dispatcher, tool_name: str, 
                                 params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute operation via tool dispatcher if available"""
    from .dispatcher_helpers import execute_operation_via_dispatcher, create_no_dispatcher_error
    if has_valid_tool_dispatcher(dispatcher):
        return await execute_operation_via_dispatcher(dispatcher, tool_name, params)
    return create_no_dispatcher_error(tool_name)


async def log_audit_operation(dispatcher, operation: Dict[str, Any]) -> None:
    """Log audit information for admin operations"""
    from .dispatcher_helpers import create_audit_data, log_audit_data
    if has_valid_audit_logger(dispatcher):
        audit_data = create_audit_data(operation)
        await log_audit_data(dispatcher.audit_logger, audit_data)


def has_valid_tool_dispatcher(dispatcher) -> bool:
    """Check if tool dispatcher is available and valid."""
    return hasattr(dispatcher, 'tool_dispatcher') and dispatcher.tool_dispatcher


def has_valid_audit_logger(dispatcher) -> bool:
    """Check if audit logger is available and valid."""
    return hasattr(dispatcher, 'audit_logger') and dispatcher.audit_logger