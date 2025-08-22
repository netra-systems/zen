"""
Tool Information Management Helpers

Helper functions for tool information retrieval and management.
Split from dispatcher_core.py to maintain 450-line limit.

Business Value: Provides comprehensive tool information for admin operations.
"""
from typing import Any, Dict, List

from netra_backend.app.schemas.admin_tool_types import AdminToolInfo, AdminToolType


def list_all_tools(dispatcher) -> List[AdminToolInfo]:
    """List all available tools including admin tools"""
    all_tools = get_base_tool_info(dispatcher)
    if dispatcher.admin_tools_enabled:
        all_tools.extend(get_admin_tool_info(dispatcher))
    return all_tools


def get_base_tool_info(dispatcher) -> List[AdminToolInfo]:
    """Get information about base tools"""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import get_base_tools_list
    return get_base_tools_list(dispatcher)


def get_admin_tool_info(dispatcher) -> List[AdminToolInfo]:
    """Get information about admin tools"""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import get_admin_tools_list
    return get_admin_tools_list(dispatcher)


def get_tool_info(dispatcher, tool_name: str) -> AdminToolInfo:
    """Get information about a specific tool"""
    if is_admin_tool(tool_name):
        return get_admin_tool_info_detail(dispatcher, tool_name)
    return get_regular_tool_info(dispatcher, tool_name)


def is_admin_tool(tool_name: str) -> bool:
    """Check if a tool is an admin tool"""
    admin_tool_names = [tool.value for tool in AdminToolType]
    return tool_name in admin_tool_names


def get_regular_tool_info(dispatcher, tool_name: str) -> AdminToolInfo:
    """Get information for regular (non-admin) tools"""
    if tool_name in dispatcher.tools:
        return get_base_tool_info_detail(dispatcher, tool_name)
    return get_not_found_tool_info(tool_name)


def get_admin_tool_info_detail(dispatcher, tool_name: str) -> AdminToolInfo:
    """Get detailed information about an admin tool"""
    try:
        admin_tool_type = AdminToolType(tool_name)
        return create_admin_tool_info(dispatcher, tool_name, admin_tool_type)
    except ValueError:
        return get_not_found_tool_info(tool_name)


def create_admin_tool_info(dispatcher, tool_name: str, admin_tool_type: AdminToolType) -> AdminToolInfo:
    """Create admin tool info object."""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import create_admin_tool_info
    return create_admin_tool_info(
        tool_name, admin_tool_type, dispatcher.user, dispatcher.admin_tools_enabled
    )


def get_base_tool_info_detail(dispatcher, tool_name: str) -> AdminToolInfo:
    """Get detailed information about a base tool"""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import create_base_tool_info
    tool = dispatcher.tools[tool_name]
    return create_base_tool_info(tool_name, tool)


def get_not_found_tool_info(tool_name: str) -> AdminToolInfo:
    """Get information for a tool that was not found"""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import create_not_found_tool_info
    return create_not_found_tool_info(tool_name)


def get_dispatcher_stats(dispatcher) -> Dict[str, Any]:
    """Get comprehensive statistics for the admin tool dispatcher"""
    stats = build_base_stats(dispatcher)
    enhance_stats_with_user_and_health(dispatcher, stats)
    return stats


def build_base_stats(dispatcher) -> Dict[str, Any]:
    """Build base dispatcher statistics."""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import build_dispatcher_stats_base
    return build_dispatcher_stats_base()


def enhance_stats_with_user_and_health(dispatcher, stats: Dict[str, Any]) -> None:
    """Add user-specific and health statistics to stats dict."""
    add_user_specific_stats(dispatcher, stats)
    add_system_health_stats(stats)


def add_user_specific_stats(dispatcher, stats: Dict[str, Any]) -> None:
    """Add user-specific statistics."""
    from .dispatcher_helpers import (
        calculate_active_sessions,
        calculate_enabled_tools_count,
    )
    stats["enabled_tools"] = calculate_enabled_tools_count(dispatcher.user)
    stats["active_sessions"] = calculate_active_sessions(dispatcher.user)


def add_system_health_stats(stats: Dict[str, Any]) -> None:
    """Add system health statistics."""
    from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_helpers import add_system_health_to_stats
    add_system_health_to_stats(stats)