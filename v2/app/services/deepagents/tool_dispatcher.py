from typing import List
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from app.logging_config import central_logger, LogEntry

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    def dispatch(self, tool_name: str, **kwargs):
        central_logger.log(LogEntry(event="dispatch_tool", data={"tool_name": tool_name, "kwargs": kwargs}))
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name].run(tool_input=kwargs)
                central_logger.log(LogEntry(event="tool_executed", data={"tool_name": tool_name, "result": result}))
                return result
            except Exception as e:
                central_logger.log(LogEntry(event="tool_error", data={"tool_name": tool_name, "error": str(e)}))
                return f"Error executing tool '{tool_name}': {e}"
        else:
            central_logger.log(LogEntry(event="tool_not_found", data={"tool_name": tool_name}))
            return f"Tool '{tool_name}' not found."

    def as_runnable(self):
        def dispatch_node(state):
            tool_messages = []
            if "messages" in state and state["messages"]:
                last_message = state["messages"][-1]
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    for tool_call in last_message.tool_calls:
                        result = self.dispatch(tool_call["name"], **tool_call["args"])
                        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            return {"messages": tool_messages}
        return dispatch_node
