from typing import Any, Dict

from langchain_core.tools import tool

from netra_backend.app.services.context import ToolContext


@tool
async def kv_cache_finder(context: ToolContext) -> str:
    """
    Finds all KV caches in the system.
    """
    resources = await context.system_inspector.find_resources("kv_cache")
    return "KV caches found."