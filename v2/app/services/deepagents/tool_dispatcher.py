from typing import List
from langchain_core.tools import BaseTool

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    def dispatch(self, tool_name: str, **kwargs):
        if tool_name in self.tools:
            return self.tools[tool_name].run(tool_input=kwargs)
        else:
            return f"Tool '{tool_name}' not found."

    def as_runnable(self):
        def dispatch_node(state):
            tool_calls = state["messages"][-1].tool_calls
            # Here you would typically dispatch to the tools and return the results
            # For simplicity, we'll just return a message
            return {"messages": ["Tool results would be here"]}
        return dispatch_node
