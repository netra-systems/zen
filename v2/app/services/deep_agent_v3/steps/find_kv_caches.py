
from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

async def find_kv_caches(state: AgentState, system_inspector: Any) -> str:
    """
    Finds all KV caches in the system.
    """
    resources = await system_inspector.find_resources("kv_cache")
    state.tool_result = resources
    return "KV caches found."
