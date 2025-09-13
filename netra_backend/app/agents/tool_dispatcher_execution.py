"""Tool execution engine for the dispatcher - delegates to unified implementation."""
from typing import TYPE_CHECKING, Any, Dict, Optional

from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolExecuteResponse,
    ToolExecutionEngineInterface,
    ToolInput,
    ToolResult,
    ToolStatus,
)

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
    from netra_backend.app.websocket_core import WebSocketManager

logger = central_logger.get_logger(__name__)

class ToolExecutionEngine(ToolExecutionEngineInterface):
    """Handles tool execution with proper error handling - delegates to unified implementation"""
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize with unified tool execution engine."""
        self._core_engine = UnifiedToolExecutionEngine(websocket_manager)

        # Store deprecation metadata for debugging
        self._deprecated = True
        self._migration_issue = "#686"
        self._ssot_replacement = "UnifiedToolDispatcher"

        # MIGRATION HELPER: Add method to assist migration to UnifiedToolDispatcher
        self._migration_helper = {
            'new_pattern': 'await UnifiedToolDispatcher.create_from_deprecated_execution_engine(websocket_manager, None, user_context)',
            'best_practice': 'await UnifiedToolDispatcher.create_for_user(user_context)',
            'migration_guide': 'Issue #686 ExecutionEngine consolidation'
        }
    
    async def execute_tool_with_input(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result"""
        return await self._core_engine.execute_tool_with_input(tool_input, tool, kwargs)
    
    async def execute_with_state(
        self,
        tool: Any,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> "ToolDispatchResponse":
        """Execute tool with state and comprehensive error handling"""
        result = await self._core_engine.execute_with_state(tool, tool_name, parameters, state, run_id)
        
        # Convert result to ToolDispatchResponse
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        if result.get("success"):
            return ToolDispatchResponse(
                success=True,
                result=result.get("result"),
                metadata=result.get("metadata", {})
            )
        else:
            return ToolDispatchResponse(
                success=False,
                error=result.get("error"),
                metadata=result.get("metadata", {})
            )
    
    # Interface Implementation Method
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters - implements ToolExecutionEngineInterface"""
        return await self._core_engine.execute_tool(tool_name, parameters)