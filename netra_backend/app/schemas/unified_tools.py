"""
Unified Tools API Schemas
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from netra_backend.app.schemas.agent import AgentCompleted, SubAgentLifecycle

# Import agent-related types from their canonical locations
from netra_backend.app.schemas.registry import AgentResult, AgentState


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""
    tool_name: str
    arguments: Dict[str, Any] = {}
    action: str = "execute"


class ToolAvailabilityResponse(BaseModel):
    """Response with available tools for user"""
    tools: List[Any]  # ToolAvailability from schemas
    user_plan: str
    total_tools: int
    available_tools: int
    categories: List[str]


class UserPlanResponse(BaseModel):
    """Response with user's plan information"""
    current_plan: str
    plan_expires_at: Optional[str]
    features: List[str]
    available_upgrades: List[str]
    usage_summary: Dict[str, Any]