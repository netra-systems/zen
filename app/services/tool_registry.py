# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:29.220184+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to tool registry
# Git: v6 | 2c55fb99 | dirty (23 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 362336ba-746a-4268-87b7-5852bc463078 | Seq: 1
# Review: Pending | Score: 85
# ================================
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