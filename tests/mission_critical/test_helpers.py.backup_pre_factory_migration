"""Helper utilities for mission-critical WebSocket tests."""

import time
from typing import Optional
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.isolated_environment import IsolatedEnvironment


class SimpleWebSocketNotifier:
    """Simplified WebSocket notifier for testing that accepts direct parameters."""
    
    def __init__(self, websocket_manager):
        # Create user context for SSOT pattern
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run"
        )
        self.notifier = AgentWebSocketBridge.WebSocketNotifier(websocket_manager, user_context)
    
    def _create_context(self, connection_id: str, request_id: str, agent_name: str = "test_agent") -> AgentExecutionContext:
        """Create a context object from simple parameters."""
        return AgentExecutionContext(
            agent_name=agent_name,
            thread_id=connection_id,  # Use connection_id as thread_id
            run_id=request_id,  # Use request_id as run_id
            user_id=connection_id,  # Use connection_id as user_id
            retry_count=0,
            max_retries=1
        )
    
    async def send_agent_started(self, connection_id: str, request_id: str, agent_name: str) -> None:
        """Send agent started with simple parameters."""
        context = self._create_context(connection_id, request_id, agent_name)
        await self.notifier.send_agent_started(context)
    
    async def send_agent_thinking(self, connection_id: str, request_id: str, message: str, step: int = 1) -> None:
        """Send agent thinking with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_agent_thinking(context, message, step)
    
    async def send_partial_result(self, connection_id: str, request_id: str, content: str, is_complete: bool = False) -> None:
        """Send partial result with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_partial_result(context, content, is_complete)
    
    async def send_tool_executing(self, connection_id: str, request_id: str, tool_name: str, args: dict = None) -> None:
        """Send tool executing with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_tool_executing(context, tool_name)
    
    async def send_tool_completed(self, connection_id: str, request_id: str, tool_name: str, result: dict = None) -> None:
        """Send tool completed with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_tool_completed(context, tool_name, result or {})
    
    async def send_final_report(self, connection_id: str, request_id: str, report: dict, duration_ms: float = 0) -> None:
        """Send final report with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_final_report(context, report, duration_ms)
    
    async def send_agent_completed(self, connection_id: str, request_id: str, result: dict = None) -> None:
        """Send agent completed with simple parameters."""
        context = self._create_context(connection_id, request_id)
        duration_ms = (time.time() - context.started_at.timestamp()) * 1000
        await self.notifier.send_agent_completed(context, result or {}, duration_ms)
    
    async def send_agent_fallback(self, connection_id: str, request_id: str, fallback_type: str) -> None:
        """Send agent fallback with simple parameters."""
        context = self._create_context(connection_id, request_id)
        await self.notifier.send_fallback_notification(context, fallback_type)