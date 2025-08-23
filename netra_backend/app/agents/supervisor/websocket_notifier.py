"""WebSocket notification functionality."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Agent import AgentStarted
from netra_backend.app.schemas.websocket_models import WebSocketMessage

logger = central_logger.get_logger(__name__)


class WebSocketNotifier:
    """Handles WebSocket notifications for agent execution."""
    
    def __init__(self, websocket_manager: 'WebSocketManager'):
        self.websocket_manager = websocket_manager
    
    async def send_agent_started(self, context: AgentExecutionContext) -> None:
        """Send agent started notification."""
        if not self.websocket_manager:
            return
        message = self._build_started_message(context)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_agent_thinking(self, context: AgentExecutionContext, 
                                  thought: str, step_number: int = None) -> None:
        """Send agent thinking notification."""
        if not self.websocket_manager:
            return
        payload = self._build_thinking_payload(context, thought, step_number)
        message = WebSocketMessage(type="agent_thinking", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_partial_result(self, context: AgentExecutionContext,
                                  content: str, is_complete: bool = False) -> None:
        """Send partial result notification."""
        if not self.websocket_manager:
            return
        payload = self._build_partial_result_payload(context, content, is_complete)
        message = WebSocketMessage(type="partial_result", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_tool_executing(self, context: AgentExecutionContext,
                                  tool_name: str) -> None:
        """Send tool executing notification."""
        if not self.websocket_manager:
            return
        payload = self._build_tool_executing_payload(context, tool_name)
        message = WebSocketMessage(type="tool_executing", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_final_report(self, context: AgentExecutionContext,
                               report: dict, duration_ms: float) -> None:
        """Send final report notification."""
        if not self.websocket_manager:
            return
        payload = self._build_final_report_payload(context, report, duration_ms)
        message = WebSocketMessage(type="final_report", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_agent_completed(self, context: AgentExecutionContext,
                                  result: dict = None, duration_ms: float = 0) -> None:
        """Send agent completed notification."""
        if not self.websocket_manager:
            return
        payload = self._build_agent_completed_payload(context, result, duration_ms)
        message = WebSocketMessage(type="agent_completed", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_tool_completed(self, context: AgentExecutionContext,
                                 tool_name: str, result: dict = None) -> None:
        """Send tool completed notification."""
        if not self.websocket_manager:
            return
        payload = self._build_tool_completed_payload(context, tool_name, result)
        message = WebSocketMessage(type="tool_completed", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_fallback_notification(self, context: AgentExecutionContext,
                                        fallback_type: str) -> None:
        """Send notification about fallback usage."""
        if not self.websocket_manager:
            return
        message = self._build_fallback_notification_message(context, fallback_type)
        await self._send_fallback_message_safe(context.thread_id, message)
    
    def _build_started_message(self, context: AgentExecutionContext) -> WebSocketMessage:
        """Build agent started message."""
        return WebSocketMessage(
            type="agent_started",
            payload=self._create_started_content(context).model_dump()
        )
    
    def _create_started_content(self, context: AgentExecutionContext) -> AgentStarted:
        """Create agent started content."""
        return AgentStarted(
            agent_name=context.agent_name,
            run_id=context.run_id,
            timestamp=datetime.now(timezone.utc).timestamp()
        )
    
    def _build_thinking_payload(self, context: AgentExecutionContext, 
                               thought: str, step_number: int) -> dict:
        """Build thinking notification payload."""
        return {
            "thought": thought, "agent_name": context.agent_name,
            "step_number": step_number, "total_steps": getattr(context, 'total_steps', 0),
            "timestamp": self._get_timestamp()
        }
    
    def _build_partial_result_payload(self, context: AgentExecutionContext,
                                     content: str, is_complete: bool) -> dict:
        """Build partial result payload."""
        return {
            "content": content, "agent_name": context.agent_name,
            "is_complete": is_complete, "timestamp": self._get_timestamp()
        }
    
    def _build_tool_executing_payload(self, context: AgentExecutionContext,
                                     tool_name: str) -> dict:
        """Build tool executing payload."""
        return {
            "tool_name": tool_name, "agent_name": context.agent_name,
            "timestamp": self._get_timestamp()
        }
    
    def _build_final_report_payload(self, context: AgentExecutionContext,
                                   report: dict, duration_ms: float) -> dict:
        """Build final report payload."""
        return {
            "report": report, "total_duration_ms": duration_ms,
            "agent_name": context.agent_name, "timestamp": self._get_timestamp()
        }
    
    def _build_fallback_notification_message(self, context: AgentExecutionContext,
                                            fallback_type: str) -> WebSocketMessage:
        """Build fallback notification message."""
        payload = self._create_fallback_payload(context, fallback_type)
        return WebSocketMessage(type="agent_fallback", payload=payload)
    
    def _build_agent_completed_payload(self, context: AgentExecutionContext,
                                      result: dict, duration_ms: float) -> dict:
        """Build agent completed payload."""
        return {
            "agent_name": context.agent_name, "run_id": context.run_id,
            "duration_ms": duration_ms, "result": result or {},
            "timestamp": self._get_timestamp()
        }
    
    def _build_tool_completed_payload(self, context: AgentExecutionContext,
                                     tool_name: str, result: dict) -> dict:
        """Build tool completed payload."""
        return {
            "tool_name": tool_name, "agent_name": context.agent_name,
            "result": result or {}, "timestamp": self._get_timestamp()
        }
    
    def _create_fallback_payload(self, context: AgentExecutionContext,
                                fallback_type: str) -> dict:
        """Create fallback notification payload."""
        return {
            "agent_name": context.agent_name, "run_id": context.run_id,
            "fallback_type": fallback_type, "timestamp": self._get_timestamp(),
            "message": f"{context.agent_name} is using fallback response"
        }
    
    async def _send_websocket_message(self, thread_id: str, 
                                     message: WebSocketMessage) -> None:
        """Send message via websocket."""
        await self.websocket_manager.send_to_thread(
            thread_id, message.model_dump())
    
    async def _send_fallback_message_safe(self, thread_id: str, 
                                         message: WebSocketMessage) -> None:
        """Safely send fallback message."""
        try:
            await self.websocket_manager.send_to_thread(
                thread_id, message.model_dump())
        except Exception as e:
            logger.debug(f"Failed to send fallback notification: {e}")
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        return datetime.now(timezone.utc).timestamp()