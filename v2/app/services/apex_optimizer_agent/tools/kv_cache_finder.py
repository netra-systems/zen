from typing import Any, Dict
from app.services.apex_optimizer_agent.state import AgentState

class KVCacheFinder:
    def __init__(self, system_inspector: any):
        self.system_inspector = system_inspector

    async def run(self, state: AgentState) -> str:
        """
        Finds all KV caches in the system.
        """
        resources = await self.system_inspector.find_resources("kv_cache")
        state.tool_result = resources
        return "KV caches found."