"""Tool execution engine for the dispatcher - delegates to core implementation."""
from typing import Dict, Any, TYPE_CHECKING
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from app.schemas.Tool import ToolExecutionEngineInterface, ToolExecuteResponse
from app.core.interfaces_tools import ToolExecutionEngine as CoreToolExecutionEngine
from app.agents.state import DeepAgentState
from app.agents.production_tool import ProductionTool
from app.logging_config import central_logger

if TYPE_CHECKING:
    from app.agents.tool_dispatcher_core import ToolDispatchResponse

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
            result = await self._core_engine.execute_with_state(tool, tool_name, parameters, state, run_id)
            return self._create_success_response(result["result"], tool_name, run_id)
        except Exception as e:
            return self._create_error_response(e, tool_name, run_id)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create successful tool execution response"""
        from app.agents.tool_dispatcher_core import ToolDispatchResponse
        metadata = {"tool_name": tool_name, "run_id": run_id}
        return ToolDispatchResponse(success=True, result=result, metadata=metadata)
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create error response for tool execution failure"""
        from app.agents.tool_dispatcher_core import ToolDispatchResponse
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
            # Create a basic tool instance
            tool = ProductionTool(tool_name)
            
            # Execute using core engine infrastructure
            if hasattr(tool, 'arun'):
                result = await tool.arun(parameters)
            else:
                result = tool(parameters)
            
            return ToolExecuteResponse(
                success=True,
                data=result,
                message="Tool executed successfully",
                metadata={"tool_name": tool_name}
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return ToolExecuteResponse(
                success=False,
                data=None,
                message=str(e),
                metadata={"tool_name": tool_name}
            )