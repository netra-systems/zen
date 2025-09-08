"""
Models for the Unified Tool Registry

Contains the data models and schemas used by the tool registry system.
"""
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from netra_backend.app.schemas.tool_permission import PermissionCheckResult


class UnifiedTool(BaseModel):
    """Unified tool definition"""
    id: str = Field(description="Unique tool identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Human-readable description")
    category: str = Field(description="Tool category")
    permissions_required: List[str] = Field(default_factory=list, description="Required permissions")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="JSON schema for outputs")
    handler: Optional[Callable] = Field(default=None, exclude=True, description="Execution handler")
    version: str = Field(default="1.0.0", description="Tool version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Business requirements (can override permission defaults)
    plan_tiers: Optional[List[str]] = Field(default=None, description="Required plan tiers")
    feature_flags: Optional[List[str]] = Field(default=None, description="Required feature flags")
    rate_limits: Optional[Dict[str, int]] = Field(default=None, description="Custom rate limits")
    
    # Metadata
    examples: Optional[List[Dict[str, Any]]] = Field(default=None, description="Usage examples")
    documentation_url: Optional[str] = Field(default=None, description="Documentation URL")
    deprecated: bool = Field(default=False, description="Is tool deprecated")
    experimental: bool = Field(default=False, description="Is tool experimental")


class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = None  # "success", "error", "permission_denied", "rate_limited"
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    permission_check: Optional[PermissionCheckResult] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    @property
    def user_context(self):
        """Get user context object for compatibility."""
        # Create a simple object with user_id for test compatibility
        class UserContext:
            def __init__(self, user_id):
                self.user_id = user_id
        return UserContext(self.user_id) if self.user_id else None