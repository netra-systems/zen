"""Core dispatcher logic and initialization for tool dispatching."""
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.tool_dispatcher_registry import ToolRegistry
from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.tool import (
    SimpleToolPayload,
    ToolInput,
    ToolResult,
    ToolStatus,
)

logger = central_logger.get_logger(__name__)

# Typed models for tool dispatch
class ToolDispatchRequest(BaseModel):
    """Typed request for tool dispatch"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDispatcher:
    """Core tool dispatcher with modular architecture"""
    
    def __init__(self, tools: List[BaseTool] = None):
        self._init_components()
        self._register_initial_tools(tools)
    
    @property
    def tools(self) -> Dict[str, Any]:
        """Expose tools registry for backward compatibility"""
        return self.registry.tools
    
    def _init_components(self) -> None:
        """Initialize dispatcher components"""
        self.registry = ToolRegistry()
        self.executor = ToolExecutionEngine()
        self.validator = ToolValidator()
    
    def _register_initial_tools(self, tools: List[BaseTool]) -> None:
        """Register initial tools if provided"""
        if tools:
            self.registry.register_tools(tools)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        return self.registry.has_tool(tool_name)
    
    async def dispatch(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution with proper typing"""
        tool_input = self._create_tool_input(tool_name, kwargs)
        if not self.has_tool(tool_name):
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        tool = self.registry.get_tool(tool_name)
        return await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
    
    def _create_tool_input(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInput:
        """Create tool input from parameters"""
        return ToolInput(tool_name=tool_name, kwargs=kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution"""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """Dispatch a tool with parameters - method expected by sub-agents"""
        if not self.has_tool(tool_name):
            return self._create_tool_not_found_response(tool_name, run_id)
        
        tool = self.registry.get_tool(tool_name)
        return await self.executor.execute_with_state(tool, tool_name, parameters, state, run_id)
    
    def _create_tool_not_found_response(self, tool_name: str, run_id: str) -> ToolDispatchResponse:
        """Create response for tool not found scenario"""
        logger.warning(f"Tool {tool_name} not found for run_id {run_id}")
        return ToolDispatchResponse(
            success=False,
            error=f"Tool {tool_name} not found"
        )
    
    async def _execute_tool(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool via executor - backward compatibility method"""
        return await self.executor.execute_tool_with_input(tool_input, tool, kwargs)
    
    async def _execute_tool_with_error_handling(
        self,
        tool: Any,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """Execute tool with comprehensive error handling"""
        return await self.executor.execute_with_state(tool, tool_name, parameters, state, run_id)
    
    async def _execute_tool_by_type(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> Any:
        """Execute tool by type - backward compatibility method"""
        return await self.executor._execute_by_type(tool, parameters, state, run_id)
    
    def _create_success_response(self, result: Any, tool_name: str, run_id: str) -> ToolDispatchResponse:
        """Create success response - backward compatibility method"""
        return self.executor._create_success_response(result, tool_name, run_id)
    
    def _create_error_response(self, error: Exception, tool_name: str, run_id: str) -> ToolDispatchResponse:
        """Create error response - backward compatibility method"""
        return self.executor._create_error_response(error, tool_name, run_id)
    
    def _register_tool_batch(self, tool_names: List[str]) -> None:
        """Register batch of tools - backward compatibility method"""
        return self.registry._register_tool_batch(tool_names)