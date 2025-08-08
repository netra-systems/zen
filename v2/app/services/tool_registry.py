from typing import List
from langchain_core.tools import BaseTool

class ToolRegistry:
    def __init__(self, db_session):
        self.db_session = db_session
        self._tool_configs = {
            "triage": [],
            "data": [],
            "optimizations_core": [],
            "actions_to_meet_goals": [],
            "reporting": [],
        }

    def get_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """Returns a list of tools for the given tool names."""
        tools = []
        for name in tool_names:
            if name in self._tool_configs:
                tools.extend(self._tool_configs[name])
        return tools
