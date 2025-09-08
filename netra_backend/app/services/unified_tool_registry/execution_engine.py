"""
Tool Execution Engine

Handles the execution of tools with permission checking, validation, and error handling.
Delegates to core implementation to maintain single source of truth.
"""
import inspect
from datetime import UTC, datetime
from typing import Any, Dict

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.interfaces_tools import (
    ToolExecutionEngine as CoreToolExecutionEngine,
)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    ToolExecuteResponse,
    ToolExecutionEngineInterface,
)
from netra_backend.app.schemas.tool_permission import (
    PermissionCheckResult,
    ToolExecutionContext,
)
from netra_backend.app.services.tool_permission_service import ToolPermissionService

logger = central_logger


class ToolExecutionEngine(ToolExecutionEngineInterface):
    """Handles secure tool execution with permission checks and validation - delegates to core"""
    
    def __init__(self, permission_service: ToolPermissionService):
        self.permission_service = permission_service
        self._core_engine = CoreToolExecutionEngine(permission_service)
    
    async def execute_unified_tool(
        self, 
        tool: UnifiedTool,
        arguments: Dict[str, Any],
        user: User,
        db_session = None
    ) -> ToolExecutionResult:
        """Execute a tool with full permission checking and validation"""
        return await self._core_engine.execute_with_permissions(tool, arguments, user)
    
    # Interface Implementation Method
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters - implements ToolExecutionEngineInterface"""
        from netra_backend.app.services.unified_tool_registry.unified_tool_registry import UnifiedToolRegistry
        
        # Get tool from registry  
        registry = UnifiedToolRegistry(self.permission_service)
        tool = registry.get_tool(tool_name)
        
        if not tool:
            return ToolExecuteResponse(
                success=False,
                message=f"Tool '{tool_name}' not found",
                metadata={"tool_name": tool_name}
            )
        
        # Create mock user for interface compatibility
        mock_user = self._create_mock_user_for_interface()
        
        # Execute tool using core engine
        result = await self.execute_unified_tool(tool, parameters, mock_user)
        
        # Convert ToolExecutionResult to ToolExecuteResponse
        return self._convert_execution_result_to_response(result, tool_name)
    
    def _create_mock_user_for_interface(self) -> User:
        """Create mock user for interface method compatibility with SSOT protection."""
        from shared.test_only_guard import require_test_mode
        
        # SSOT Guard: This function should only run in test mode
        require_test_mode("_create_mock_user_for_interface", 
                         "Mock user creation should only happen in tests - production should pass proper user context")
        
        # This is a temporary solution for interface compatibility
        # In production, proper user should be passed through context
        mock_user = User()
        mock_user.id = "interface_user"
        mock_user.plan_tier = "free"
        mock_user.roles = []
        mock_user.feature_flags = {}
        mock_user.is_developer = False
        return mock_user
    
    def _convert_execution_result_to_response(
        self, 
        result: ToolExecutionResult, 
        tool_name: str
    ) -> ToolExecuteResponse:
        """Convert ToolExecutionResult to ToolExecuteResponse"""
        return ToolExecuteResponse(
            success=(result.status == "success"),
            data=result.result if result.status == "success" else None,
            message=result.error_message if result.status != "success" else "Success",
            metadata={
                "tool_name": tool_name,
                "execution_time_ms": result.execution_time_ms,
                "status": result.status
            }
        )