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
            # Tools expect the kwargs as a single dict argument
            result = await tool.arun(kwargs)
            return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=result)
        except Exception as e:
            return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=str(e))
