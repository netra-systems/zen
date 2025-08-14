"""Production-ready tool dispatcher with modular architecture."""
from typing import List
from langchain_core.tools import BaseTool
from app.agents.tool_dispatcher_core import ToolDispatcher as CoreToolDispatcher
from app.agents.tool_dispatcher_core import ToolDispatchRequest, ToolDispatchResponse

# Re-export for backward compatibility
ToolDispatcher = CoreToolDispatcher

# Keep the original interface intact by re-exporting the models
__all__ = ["ToolDispatcher", "ToolDispatchRequest", "ToolDispatchResponse"]