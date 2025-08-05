from typing import List
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from app.logging_config_custom.logger import app_logger

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    def dispatch(self, tool_name: str, **kwargs):
        app_logger.info(f"Dispatching tool '{tool_name}' with args: {kwargs}")
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name].run(tool_input=kwargs)
                app_logger.info(f"Tool '{tool_name}' executed successfully with result: {result}")
                return result
            except Exception as e:
                app_logger.error(f"Error executing tool '{tool_name}': {e}")
                return f"Error executing tool '{tool_name}': {e}"
        else:
            app_logger.warning(f"Tool '{tool_name}' not found.")
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
