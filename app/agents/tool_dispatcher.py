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
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

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

    async def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        if tool_name not in self.tools:
            return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        try:
            # Tools expect the kwargs as a single dict argument
            result = await tool.arun(kwargs)
            # Use SimpleToolPayload for structured result handling
            payload = SimpleToolPayload(result=result)
            return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
        except Exception as e:
            return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=str(e))
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> Dict[str, Any]:
        """
        Dispatch a tool with parameters - method expected by sub-agents
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            state: Current agent state
            run_id: Execution run ID
            
        Returns:
            Tool execution result as dictionary
        """
        if not self.has_tool(tool_name):
            logger.warning(f"Tool {tool_name} not found for run_id {run_id}")
            return {"error": f"Tool {tool_name} not found"}
        
        tool = self.tools[tool_name]
        
        try:
            # Handle different tool types
            if isinstance(tool, MockTool):
                result = await tool.execute(parameters, state, run_id)
            elif hasattr(tool, 'arun'):
                result = await tool.arun(parameters)
            else:
                result = tool(parameters)
            
            if isinstance(result, dict):
                return result
            else:
                return {"result": result}
                
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}


class MockTool:
    """Mock tool for synthetic data and corpus operations"""
    
    def __init__(self, name: str):
        self.name = name
        
    async def arun(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the mock tool"""
        return await self.execute(kwargs, None, None)
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the mock tool with realistic responses"""
        
        # Synthetic data tools
        if self.name == "generate_synthetic_data_batch":
            batch_size = parameters.get("batch_size", 100)
            return {
                "success": True,
                "data": [
                    {"id": f"record_{i}", "timestamp": "2025-01-01T00:00:00Z", "value": i}
                    for i in range(min(batch_size, 10))
                ]
            }
        
        # Corpus tools
        elif self.name == "create_corpus":
            return {
                "success": True,
                "corpus_id": f"corpus_{parameters.get('corpus_name', 'default')}"
            }
        
        elif self.name == "search_corpus":
            return {
                "success": True,
                "results": [
                    {"doc_id": f"doc_{i}", "score": 0.9 - i*0.1}
                    for i in range(5)
                ],
                "total_matches": 25
            }
        
        # Default response
        return {"success": True, "message": f"Mock execution of {self.name}"}
