"""
Tool Permission Service - Modular Facade

This module provides backward compatibility while using the new modular architecture.
All functionality has been split into focused modules  <= 300 lines with functions  <= 8 lines.
"""

# Import all modular components for backward compatibility
from typing import Any, Dict, List, Optional

# MIGRATED: Use SSOT Redis import pattern
from shared.isolated_environment import get_env
from netra_backend.app.schemas.tool_permission import (
    BusinessRequirement,
    PermissionCheckResult,
    PermissionLevel,
    RateLimit,
    ToolAvailability,
    ToolExecutionContext,
    ToolPermission,
)
from netra_backend.app.schemas.user_plan import PLAN_DEFINITIONS, PlanTier, UserPlan
from netra_backend.app.services.tool_permissions.permission_checker import (
    PermissionChecker,
)
from netra_backend.app.services.tool_permissions.permission_definitions import (
    PermissionDefinitions,
)
from netra_backend.app.services.tool_permissions.rate_limiter import RateLimiter
from netra_backend.app.services.tool_permissions.tool_availability_processor import (
    ToolAvailabilityProcessor,
)
from netra_backend.app.services.tool_permissions.tool_permission_service_main import (
    ToolPermissionService,
)

# Re-export classes and functions for backward compatibility
__all__ = [
    "ToolPermissionService",
    "PermissionDefinitions",
    "PermissionChecker",
    "RateLimiter",
    "ToolAvailabilityProcessor",
    "ToolPermission",
    "ToolExecutionContext",
    "PermissionCheckResult",
    "ToolAvailability",
    "PermissionLevel",
    "BusinessRequirement",
    "RateLimit",
    "UserPlan",
    "PlanTier",
    "PLAN_DEFINITIONS"
]
