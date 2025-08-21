"""Production-ready tool dispatcher with modular architecture."""
from typing import List
from langchain_core.tools import BaseTool
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher as CoreToolDispatcher
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchRequest, ToolDispatchResponse
from netra_backend.app.agents.production_tool import ProductionTool, ToolExecuteResponse

# Re-export for backward compatibility
ToolDispatcher = CoreToolDispatcher

# Keep the original interface intact by re-exporting the models
__all__ = ["ToolDispatcher", "ToolDispatchRequest", "ToolDispatchResponse", "ProductionTool", "ToolExecuteResponse"]