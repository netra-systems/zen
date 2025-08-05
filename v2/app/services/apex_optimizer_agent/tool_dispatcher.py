from typing import Any, Dict, List
from app.llm.llm_manager import LLMManager


class ToolDispatcher:
    def __init__(self, llm_manager: LLMManager, tools: Dict[str, Any]):
        self.llm_manager = llm_manager
        self.tools = tools

    def dispatch(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found.")
        return tool.run(tool_input)
