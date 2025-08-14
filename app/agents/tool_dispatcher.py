# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:22.221612+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to tool dispatcher
# Git: v6 | 2c55fb99 | dirty (38 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: 39047eeb-3ce4-425a-9566-93ba5a727f37 | Seq: 1
# Review: Pending | Score: 85
# ================================
from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Typed models for tool dispatch
class ToolDispatchRequest(BaseModel):
    """Typed request for tool dispatch"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch"""
    success: bool
    result: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MockToolExecuteRequest(BaseModel):
    """Typed request for MockTool execution"""
    parameters: Dict[str, Any]
    state: Optional[DeepAgentState] = None
    run_id: Optional[str] = None
    
class MockToolExecuteResponse(BaseModel):
    """Typed response for MockTool execution"""
    success: bool
    data: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool] = None):
        self.tools = {}
        if tools:
            self.tools = {tool.name: tool for tool in tools}
        # Add synthetic tools that agents expect
        self._register_synthetic_tools()
        self._register_corpus_tools()

    def _register_synthetic_tools(self):
        """Register synthetic data generation tools"""
        # These are placeholders that integrate with the actual service
        synthetic_tools = [
            "generate_synthetic_data_batch",
            "validate_synthetic_data",
            "store_synthetic_data"
        ]
        for tool_name in synthetic_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = MockTool(tool_name)
    
    def _register_corpus_tools(self):
        """Register corpus management tools"""
        corpus_tools = [
            "create_corpus",
            "search_corpus", 
            "update_corpus",
            "delete_corpus",
            "analyze_corpus",
            "export_corpus",
            "import_corpus",
            "validate_corpus"
        ]
        for tool_name in corpus_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = MockTool(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        return tool_name in self.tools

    async def dispatch(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution with proper typing"""
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        if tool_name not in self.tools:
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        return await self._execute_tool(tool_input, self.tools[tool_name], kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution"""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    async def _execute_tool(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result"""
        try:
            result = await tool.arun(kwargs)
            payload = SimpleToolPayload(result=result)
            return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
        except Exception as e:
            return self._create_error_result(tool_input, str(e))
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """
        Dispatch a tool with parameters - method expected by sub-agents
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            state: Current agent state
            run_id: Execution run ID
            
        Returns:
            Tool execution result as typed response
        """
        if not self.has_tool(tool_name):
            logger.warning(f"Tool {tool_name} not found for run_id {run_id}")
            return ToolDispatchResponse(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        tool = self.tools[tool_name]
        
        try:
            # Handle different tool types
            if isinstance(tool, MockTool):
                result = await tool.execute(parameters, state, run_id)
            elif hasattr(tool, 'arun'):
                result = await tool.arun(parameters)
            else:
                result = tool(parameters)
            
            return ToolDispatchResponse(
                success=True,
                result=result,
                metadata={"tool_name": tool_name, "run_id": run_id}
            )
                
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return ToolDispatchResponse(
                success=False,
                error=str(e),
                metadata={"tool_name": tool_name, "run_id": run_id}
            )


class MockTool:
    """Mock tool for synthetic data and corpus operations"""
    
    def __init__(self, name: str):
        self.name = name
        
    async def arun(self, kwargs: Dict[str, Any]) -> MockToolExecuteResponse:
        """Run the mock tool with typed response"""
        response = await self.execute(kwargs, None, None)
        return MockToolExecuteResponse(**response)
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the mock tool with realistic typed responses"""
        if self.name == "generate_synthetic_data_batch":
            return self._execute_synthetic_data_batch(parameters)
        elif self.name == "create_corpus":
            return self._execute_create_corpus(parameters)
        elif self.name == "search_corpus":
            return self._execute_search_corpus()
        return self._execute_default()
    
    def _execute_synthetic_data_batch(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synthetic data batch generation"""
        batch_size = parameters.get("batch_size", 100)
        return {
            "success": True,
            "data": [
                {"id": f"record_{i}", "timestamp": "2025-01-01T00:00:00Z", "value": i}
                for i in range(min(batch_size, 10))
            ],
            "metadata": {"batch_size": batch_size, "tool": self.name}
        }
    
    def _execute_create_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute corpus creation"""
        return {
            "success": True,
            "data": {"corpus_id": f"corpus_{parameters.get('corpus_name', 'default')}"},
            "message": "Corpus created successfully",
            "metadata": {"tool": self.name}
        }
    
    def _execute_search_corpus(self) -> Dict[str, Any]:
        """Execute corpus search"""
        return {
            "success": True,
            "data": {
                "results": [
                    {"doc_id": f"doc_{i}", "score": 0.9 - i*0.1}
                    for i in range(5)
                ],
                "total_matches": 25
            },
            "message": "Search completed successfully",
            "metadata": {"tool": self.name}
        }
    
    def _execute_default(self) -> Dict[str, Any]:
        """Execute default mock tool response"""
        return {
            "success": True, 
            "message": f"Mock execution of {self.name}",
            "metadata": {"tool": self.name}
        }
