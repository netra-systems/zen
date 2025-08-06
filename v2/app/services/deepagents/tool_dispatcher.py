from typing import List
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from app.logging_config import central_logger, LogEntry
from app.services.apex_optimizer_agent.models import ToolResult, ToolStatus
import asyncio

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    async def dispatch(self, tool_name: str, **kwargs):
        central_logger.log(LogEntry(event="dispatch_tool", data={"tool_name": tool_name, "kwargs": kwargs}))
        if tool_name in self.tools:
            try:
                # Check if the tool is async
                if asyncio.iscoroutinefunction(self.tools[tool_name].ainvoke):
                    result = await self.tools[tool_name].ainvoke(tool_input=kwargs)
                else:
                    result = self.tools[tool_name].invoke(tool_input=kwargs)
                
                if isinstance(result, ToolResult):
                    central_logger.log(LogEntry(event="tool_executed", data={"tool_name": tool_name, "result_status": result.status, "result_message": result.message}))
                    return result
                else:
                    central_logger.log(LogEntry(event="tool_executed", data={"tool_name": tool_name, "result": result}))
                    return ToolResult(status=ToolStatus.SUCCESS, message="Tool executed successfully.", payload=result)

            except Exception as e:
                central_logger.log(LogEntry(event="tool_error", data={"tool_name": tool_name, "error": str(e)}))
                return ToolResult(status=ToolStatus.ERROR, message=f"Error executing tool '{tool_name}': {e}")
        else:
            central_logger.log(LogEntry(event="tool_not_found", data={"tool_name": tool_name}))
            return ToolResult(status=ToolStatus.ERROR, message=f"Tool '{tool_name}' not found.")

    def as_runnable(self):
        async def dispatch_node(state):
            tool_messages = []
            if "messages" in state and state["messages"]:
                last_message = state["messages"][-1]
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    for tool_call in last_message.tool_calls:
                        result = await self.dispatch(tool_call["name"], **tool_call["args"])
                        tool_messages.append(ToolMessage(content=str(result.payload) if result.status == ToolStatus.SUCCESS else result.message, tool_call_id=tool_call["id"], is_error=result.status == ToolStatus.ERROR))
            return {"messages": tool_messages}
        return dispatch_node