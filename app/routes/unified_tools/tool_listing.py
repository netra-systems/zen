"""
Tool Listing Logic for Unified Tools API
"""
from typing import List, Dict, Any, Optional
from app.db.models_postgres import User
from app.schemas.ToolPermission import ToolAvailability
from app.logging_config import central_logger
from .schemas import ToolAvailabilityResponse

logger = central_logger


async def get_available_tools_for_user(
    tool_registry, current_user: User, category: Optional[str]
) -> List[Dict]:
    """Get available tools for user with optional category filter."""
    return await tool_registry.list_available_tools(
        user=current_user,
        category=category
    )


def get_tool_category_names(tool_registry) -> List[str]:
    """Get list of tool category names."""
    return [cat["name"] for cat in tool_registry.get_tool_categories()]


def filter_available_tools(available_tools: List[Dict]) -> List[Dict]:
    """Filter tools to only include available ones."""
    return [tool for tool in available_tools if tool.get("available", False)]


def extract_tool_basic_info(tool: Dict) -> Dict:
    """Extract basic tool information."""
    return {
        "tool_name": tool["name"],
        "category": tool["category"],
        "description": tool["description"]
    }


def extract_tool_requirements(tool: Dict) -> Dict:
    """Extract tool requirements information."""
    return {
        "available": tool.get("available", False),
        "required_permissions": tool.get("required_permissions", []),
        "missing_requirements": tool.get("missing_requirements", []),
        "upgrade_required": tool.get("upgrade_path")
    }


def create_tool_availability(tool: Dict) -> ToolAvailability:
    """Create ToolAvailability object from tool dict."""
    basic_info = extract_tool_basic_info(tool)
    requirements = extract_tool_requirements(tool)
    return ToolAvailability(**{**basic_info, **requirements})


def create_tool_availability_objects(available_tools: List[Dict]) -> List[ToolAvailability]:
    """Create tool availability objects from tool dicts."""
    return [create_tool_availability(tool) for tool in available_tools]


def build_response_params(
    tool_objects: List[ToolAvailability], available_tools: List[Dict],
    tools_available: List[Dict], categories: List[str], current_user: User
) -> Dict[str, Any]:
    """Build response parameters for ToolAvailabilityResponse."""
    return {
        "tools": tool_objects, "user_plan": current_user.plan_tier,
        "total_tools": len(available_tools), "available_tools": len(tools_available),
        "categories": categories
    }


def build_tool_availability_response(
    available_tools: List[Dict], tools_available: List[Dict],
    categories: List[str], current_user: User
) -> ToolAvailabilityResponse:
    """Build the tool availability response."""
    tool_objects = create_tool_availability_objects(available_tools)
    params = build_response_params(
        tool_objects, available_tools, tools_available, categories, current_user
    )
    return ToolAvailabilityResponse(**params)


async def gather_tool_data(
    tool_registry, current_user: User, category: Optional[str]
) -> tuple[List[Dict], List[str], List[Dict]]:
    """Gather tool data for user."""
    available_tools = await get_available_tools_for_user(
        tool_registry, current_user, category)
    categories = get_tool_category_names(tool_registry)
    tools_available = filter_available_tools(available_tools)
    return available_tools, categories, tools_available