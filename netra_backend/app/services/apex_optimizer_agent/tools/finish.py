from langchain_core.tools import tool


@tool
async def finish() -> str:
    """Signals that the agent has completed its work."""
    return "Finished."