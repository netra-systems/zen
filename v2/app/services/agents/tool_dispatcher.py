from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from app.services.apex_optimizer_agent.models import ToolResult, ToolStatus

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    async def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        if tool_name not in self.tools:
            return ToolResult(status=ToolStatus.ERROR, payload=f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        try:
            result = await tool.arun(**kwargs)
            return ToolResult(status=ToolStatus.SUCCESS, payload=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, payload=str(e))
