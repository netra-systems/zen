"""Tool execution engine for the dispatcher."""
from typing import Dict, Any, TYPE_CHECKING
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from app.agents.state import DeepAgentState
from app.agents.production_tool import ProductionTool
from app.logging_config import central_logger

if TYPE_CHECKING:
    from app.agents.tool_dispatcher_core import ToolDispatchResponse

logger = central_logger.get_logger(__name__)

class ToolExecutionEngine:
    """Handles tool execution with proper error handling"""
    
    async def execute_tool(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result"""
        try:
            result = await self._run_tool(tool, kwargs)
            return self._create_success_result(tool_input, result)
        except Exception as e:
            return self._create_error_result(tool_input, str(e))
    
    async def _run_tool(self, tool: Any, kwargs: Dict[str, Any]) -> Any:
        """Run tool based on its interface"""
        if hasattr(tool, 'arun'):
            return await tool.arun(kwargs)
        else:
            return tool(kwargs)
    
    def _create_success_result(self, tool_input: ToolInput, result: Any) -> ToolResult:
        """Create successful tool result"""
        payload = SimpleToolPayload(result=result)
        return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution"""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
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
            result = await self._execute_by_type(tool, parameters, state, run_id)
            return self._create_success_response(result, tool_name, run_id)
        except Exception as e:
            return self._create_error_response(e, tool_name, run_id)
    
    async def _execute_by_type(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> Any:
        """Execute tool based on its type"""
        if isinstance(tool, ProductionTool):
            return await tool.execute(parameters, state, run_id)
        elif hasattr(tool, 'arun'):
            return await tool.arun(parameters)
        else:
            return tool(parameters)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create successful tool execution response"""
        from app.agents.tool_dispatcher_core import ToolDispatchResponse
        return ToolDispatchResponse(
            success=True,
            result=result,
            metadata={"tool_name": tool_name, "run_id": run_id}
        )
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> "ToolDispatchResponse":
        """Create error response for tool execution failure"""
        from app.agents.tool_dispatcher_core import ToolDispatchResponse
        logger.error(f"Tool {tool_name} execution failed: {error}")
        return ToolDispatchResponse(
            success=False,
            error=str(error),
            metadata={"tool_name": tool_name, "run_id": run_id}
        )