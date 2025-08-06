from langchain_core.tools import tool
from typing import Any, Dict

@tool
async def kv_cache_finder(system_inspector: any, db_session: Any, llm_manager: Any) -> str:
    """
    Finds all KV caches in the system.
    """
    resources = await system_inspector.find_resources("kv_cache")
    return "KV caches found."
