"""Mock Tool Dispatcher for Issue #686 Migration.

Provides a minimal UnifiedToolDispatcher implementation for migration compatibility.
This allows deprecated execution engines to continue working while the full SSOT
implementation is being developed.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.unified_tool_registry.models import ToolExecutionResult

logger = central_logger.get_logger(__name__)


class MockToolDispatcher:
    """Mock implementation of UnifiedToolDispatcher for Issue #686 migration support."""

    def __init__(
        self,
        user_context: 'UserExecutionContext',
        websocket_bridge: Optional[Any] = None,
        migration_mode: bool = False,
        migration_metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize mock dispatcher with migration support."""
        self.user_context = user_context
        self.websocket_bridge = websocket_bridge
        self.migration_mode = migration_mode
        self.migration_metadata = migration_metadata or {}

        # Basic properties for compatibility
        self.dispatcher_id = f"mock_{user_context.user_id}_{user_context.run_id}"
        self.created_at = datetime.now(timezone.utc)
        self._is_active = True
        self._tools = {}

        logger.info(
            f"🔄 Issue #686: Created MockToolDispatcher for migration compatibility "
            f"(user: {user_context.user_id}, migration: {migration_mode})"
        )

    @property
    def tools(self) -> Dict[str, Any]:
        """Get registered tools."""
        return self._tools.copy()

    @property
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is available."""
        return self.websocket_bridge is not None

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

    def register_tool(self, tool: 'BaseTool') -> None:
        """Register a tool with the dispatcher."""
        if hasattr(tool, 'name'):
            self._tools[tool.name] = tool
            logger.debug(f"Registered tool {tool.name} in mock dispatcher {self.dispatcher_id}")

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tools.keys())

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        **kwargs
    ) -> ToolExecutionResult:
        """Execute a tool (mock implementation for migration)."""
        logger.info(
            f"🔄 Issue #686: Mock tool execution - {tool_name} "
            f"(user: {self.user_context.user_id})"
        )

        # Simulate successful tool execution
        return ToolExecutionResult(
            success=True,
            result=f"Mock execution of {tool_name} with parameters: {parameters}",
            tool_name=tool_name,
            user_id=self.user_context.user_id,
            status="success",
            execution_time_ms=100
        )

    async def dispatch(self, tool_name: str, **kwargs) -> Any:
        """Legacy compatibility method."""
        result = await self.execute_tool(tool_name, kwargs)
        return result.result if result.success else f"Error: {result.error}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get dispatcher metrics."""
        return {
            'dispatcher_id': self.dispatcher_id,
            'user_id': self.user_context.user_id,
            'migration_mode': self.migration_mode,
            'migration_metadata': self.migration_metadata,
            'tools_registered': len(self._tools),
            'created_at': self.created_at.isoformat()
        }

    async def cleanup(self):
        """Clean up dispatcher resources."""
        self._is_active = False
        self._tools.clear()
        logger.info(f"🔄 Issue #686: Cleaned up MockToolDispatcher {self.dispatcher_id}")