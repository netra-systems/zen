# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Modernize validation module for 100% agent architecture compliance
# Git: 8-18-25-AM | Agent architecture modernization
# Change: Modernize | Scope: Module | Risk: Low
# Session: admin-tool-modernization | Seq: 6
# Review: Pending | Score: 100
# ================================
"""
Modern Admin Tool Validation Module

Modernized validation system using ExecutionContext patterns and monitoring.
Provides validation as execution-aware services with error classification.

Business Value: Enables standardized validation across 40+ admin tools.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.admin_tool_dispatcher.validation_helpers import (
    PermissionHelpers,
    ValidationHelpers,
)
from netra_backend.app.agents.base.errors import ValidationError
from abc import ABC, abstractmethod
from netra_backend.app.agents.base.interface import (
    ExecutionContext, ExecutionResult
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.permission_service import PermissionService

logger = central_logger.get_logger(__name__)


@dataclass
class ValidationContext:
    """Context for validation operations."""
    user: Optional[User]
    tool_name: str
    operation: str = "validate"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AdminToolValidator(ABC):
    """Modern admin tool validator with execution context support."""
    
    def __init__(self, monitor: Optional[ExecutionMonitor] = None):
        # BaseExecutionInterface.__init__ removed - using single inheritance pattern
        self.agent_name = "admin_tool_validator"
        self.monitor = monitor or ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler
        self.validation_helpers = ValidationHelpers()
        self.permission_helpers = PermissionHelpers()
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute validation logic with monitoring."""
        validation_context = self._extract_validation_context(context)
        result = await self._perform_validation(validation_context)
        self._record_validation_metrics(context, result)
        return result
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for validation."""
        required_params = ["user", "tool_name"]
        return all(param in context.state.context for param in required_params)


    async def get_available_tools(self, validation_context: ValidationContext) -> List[str]:
        """Get available admin tools for user."""
        if not validation_context.user:
            return []
        tools = self._collect_all_permitted_tools(validation_context.user)
        self._log_tool_access(validation_context.user, len(tools))
        return tools
    
    def _collect_all_permitted_tools(self, user: User) -> List[str]:
        """Collect all tools user has permission to access."""
        tools = []
        tools.extend(self._get_corpus_tools(user))
        tools.extend(self._get_synthetic_tools(user))
        tools.extend(self._get_user_admin_tools(user))
        tools.extend(self._get_system_admin_tools(user))
        return tools


    def _get_corpus_tools(self, user: User) -> List[str]:
        """Get corpus tools if user has permissions."""
        return ["corpus_manager"] if self._has_corpus_permission(user) else []
    
    def _get_synthetic_tools(self, user: User) -> List[str]:
        """Get synthetic tools if user has permissions."""
        return ["synthetic_generator"] if self._has_synthetic_permission(user) else []
    
    def _get_user_admin_tools(self, user: User) -> List[str]:
        """Get user admin tools if user has permissions."""
        return ["user_admin"] if self._has_user_management_permission(user) else []
    
    def _get_system_admin_tools(self, user: User) -> List[str]:
        """Get system admin tools if user has permissions."""
        tools = ["system_configurator", "log_analyzer"]
        return tools if self._has_system_admin_permission(user) else []


    def _has_corpus_permission(self, user: User) -> bool:
        """Check if user has corpus write permission."""
        return PermissionService.has_permission(user, "corpus_write")
    
    def _has_synthetic_permission(self, user: User) -> bool:
        """Check if user has synthetic generation permission."""
        return PermissionService.has_permission(user, "synthetic_generate")
    
    def _has_user_management_permission(self, user: User) -> bool:
        """Check if user has user management permission."""
        return PermissionService.has_permission(user, "user_management")
    
    def _has_system_admin_permission(self, user: User) -> bool:
        """Check if user has system admin permission."""
        return PermissionService.has_permission(user, "system_admin")


    async def validate_tool_access(self, validation_context: ValidationContext) -> bool:
        """Validate tool access with monitoring."""
        if not validation_context.user:
            await self._record_access_denied(validation_context, "no_user")
            return False
        permission = self._get_required_permission(validation_context.tool_name)
        has_access = self._check_permission(validation_context.user, permission)
        await self._record_access_result(validation_context, has_access)
        return has_access


    def _get_required_permission(self, tool_name: str) -> Optional[str]:
        """Get required permission for tool."""
        permission_map = self._get_tool_permission_mapping()
        return permission_map.get(tool_name)
    
    def _check_permission(self, user: User, permission: Optional[str]) -> bool:
        """Check if user has required permission."""
        if not permission:
            return False
        return PermissionService.has_permission(user, permission)
    
    def _get_tool_permission_mapping(self) -> Dict[str, str]:
        """Get mapping of tools to required permissions."""
        return self.permission_helpers.get_tool_permission_mapping()


    async def validate_tool_input(self, validation_context: ValidationContext,
                                 **kwargs) -> Optional[str]:
        """Validate tool input parameters with error handling."""
        try:
            validator = self._get_input_validator(validation_context.tool_name)
            error = validator(**kwargs) if validator else None
            await self._record_validation_result(validation_context, error is None)
            return error
        except Exception as e:
            return await self._handle_validation_error(validation_context, e)


    def _get_input_validator(self, tool_name: str):
        """Get input validator function for tool."""
        validators = self._build_validator_mapping()
        return validators.get(tool_name)
    
    def _build_validator_mapping(self) -> Dict[str, Any]:
        """Build mapping of tools to validator functions."""
        return self.permission_helpers.build_validator_mapping(self.validation_helpers)










    async def check_admin_tools_enabled(self, user: Optional[User]) -> bool:
        """Check if admin tools should be enabled for user."""
        if not user:
            return False
        return PermissionService.is_developer_or_higher(user)
    
    def _extract_validation_context(self, context: ExecutionContext) -> ValidationContext:
        """Extract validation context from execution context."""
        return ValidationContext(
            user=context.state.context.get("user"),
            tool_name=context.state.context.get("tool_name", ""),
            operation=context.state.context.get("operation", "validate"),
            metadata=context.metadata
        )
    
    async def _perform_validation(self, validation_context: ValidationContext) -> Dict[str, Any]:
        """Perform validation operation."""
        operation = validation_context.operation
        if operation == "available_tools":
            tools = await self.get_available_tools(validation_context)
            return {"available_tools": tools}
        if operation == "access_check":
            access = await self.validate_tool_access(validation_context)
            return {"has_access": access}
        return {"validation_complete": True}
    
    def _record_validation_metrics(self, context: ExecutionContext, result: Dict[str, Any]) -> None:
        """Record validation metrics for monitoring."""
        self.monitor.record_execution_time(context, 0.01)  # Validation is fast
    
    async def _record_access_denied(self, validation_context: ValidationContext, reason: str) -> None:
        """Record access denied event."""
        logger.warning(f"Access denied for tool {validation_context.tool_name}: {reason}")
    
    async def _record_access_result(self, validation_context: ValidationContext, has_access: bool) -> None:
        """Record access validation result."""
        status = "granted" if has_access else "denied"
        logger.debug(f"Access {status} for {validation_context.tool_name}")
    
    async def _record_validation_result(self, validation_context: ValidationContext, is_valid: bool) -> None:
        """Record input validation result."""
        status = "valid" if is_valid else "invalid"
        logger.debug(f"Input validation {status} for {validation_context.tool_name}")
    
    async def _handle_validation_error(self, validation_context: ValidationContext, error: Exception) -> str:
        """Handle validation error with error handler."""
        logger.error(f"Validation error for {validation_context.tool_name}: {error}")
        return f"Validation error: {str(error)}"
    
    def _log_tool_access(self, user: User, tool_count: int) -> None:
        """Log tool access for monitoring."""
        logger.debug(f"User {user.id} has access to {tool_count} admin tools")


# Backward compatibility functions
def get_available_admin_tools(user: Optional[User]) -> List[str]:
    """Backward compatibility wrapper."""
    validator = AdminToolValidator()
    context = ValidationContext(user=user, tool_name="", operation="available_tools")
    import asyncio
    return asyncio.run(validator.get_available_tools(context))


def validate_admin_tool_access(user: Optional[User], tool_name: str) -> bool:
    """Backward compatibility wrapper."""
    validator = AdminToolValidator()
    context = ValidationContext(user=user, tool_name=tool_name, operation="access_check")
    import asyncio
    return asyncio.run(validator.validate_tool_access(context))