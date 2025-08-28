"""Tool execution engine for the dispatcher - delegates to core implementation."""
from typing import TYPE_CHECKING, Any, Dict

from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.interfaces_tools import (
    ToolExecutionEngine as CoreToolExecutionEngine,
)
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

logger = central_logger.get_logger(__name__)

class ToolExecutionEngine(ToolExecutionEngineInterface):
    """Handles tool execution with proper error handling - delegates to core implementation"""
    
    def __init__(self):
        """Initialize with core tool execution engine."""
        self._core_engine = CoreToolExecutionEngine()
    
    async def execute_tool_with_input(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result"""
        return await self._core_engine.execute_tool(tool_input, tool, kwargs)
    
    async def execute_with_state(
        self,
        tool: Any,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> "ToolDispatchResponse":
        """Execute tool with state and comprehensive error handling"""
        try:
            result = await self._execute_tool_with_core_engine(tool, tool_name, parameters, state, run_id)
            return self._create_success_response(result["result"], tool_name, run_id)
        except Exception as e:
            return self._create_error_response(e, tool_name, run_id)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create successful tool execution response"""
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        metadata = {"tool_name": tool_name, "run_id": run_id}
        return ToolDispatchResponse(success=True, result=result, metadata=metadata)
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create error response for tool execution failure"""
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        logger.error(f"Tool {tool_name} execution failed: {error}")
        return ToolDispatchResponse(
            success=False,
            error=str(error),
            metadata={"tool_name": tool_name, "run_id": run_id}
        )
    
    # Interface Implementation Method
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters - implements ToolExecutionEngineInterface"""
        try:
            result = await self._execute_production_tool(tool_name, parameters)
            return self._create_success_tool_response(result, tool_name)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return self._create_error_tool_response(e, tool_name)
    
    async def _execute_production_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute production tool instance."""
        tool = ProductionTool(tool_name)
        
        if hasattr(tool, 'arun'):
            return await tool.arun(parameters)
        else:
            return tool(parameters)
    
    def _create_success_tool_response(self, result: Any, tool_name: str) -> ToolExecuteResponse:
        """Create successful tool execution response."""
        return ToolExecuteResponse(
            success=True,
            data=result,
            message="Tool executed successfully",
            metadata={"tool_name": tool_name}
        )
    
    def _create_error_tool_response(self, error: Exception, tool_name: str) -> ToolExecuteResponse:
        """Create error tool execution response."""
        return ToolExecuteResponse(
            success=False,
            data=None,
            message=str(error),
            metadata={"tool_name": tool_name}
        )
    
    async def _execute_tool_with_core_engine(
        self, tool: Any, tool_name: str, parameters: Dict[str, Any], 
        state: DeepAgentState, run_id: str
    ) -> Dict[str, Any]:
        """Execute tool using core engine."""
        return await self._core_engine.execute_with_state(tool, tool_name, parameters, state, run_id)