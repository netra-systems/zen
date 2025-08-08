from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from app.schemas import ToolResult, ToolStatus, ToolInput

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    async def dispatch(self, tool_name: str, **kwargs) -> ToolResult:
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        if tool_name not in self.tools:
            return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        try:
            result = await tool.arun(**kwargs)
            return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=result)
        except Exception as e:
            return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=str(e))
