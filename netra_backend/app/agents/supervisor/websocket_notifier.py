"""WebSocket notification functionality."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import AgentStarted
from netra_backend.app.schemas.registry import AgentStatus
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
    
    async def send_agent_registered(self, context: AgentExecutionContext = None,
                                   agent_metadata: dict = None, agent_id: str = None,
                                   agent_type: str = None, thread_id: str = None) -> None:
        """Send agent registered notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach for full agent execution
            payload = self._build_agent_registered_payload(context, agent_metadata)
            message = WebSocketMessage(type="agent_registered", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager lifecycle events
            payload = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "status": "idle",
                "metadata": agent_metadata or {},
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_registered", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_failed(self, context: AgentExecutionContext = None,
                               error_message: str = None, error_details: dict = None,
                               agent_id: str = None, error: str = None, 
                               thread_id: str = None) -> None:
        """Send agent failed notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_failed_payload(context, error_message, error_details)
            message = WebSocketMessage(type="agent_failed", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "agent_id": agent_id,
                "status": "failed",
                "error": error or error_message,
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_failed", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_cancelled(self, context: AgentExecutionContext = None,
                                  cancellation_reason: str = None, agent_id: str = None,
                                  thread_id: str = None) -> None:
        """Send agent cancelled notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_cancelled_payload(context, cancellation_reason)
            message = WebSocketMessage(type="agent_cancelled", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "agent_id": agent_id,
                "status": "cancelled",
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_cancelled", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_metrics_updated(self, context: AgentExecutionContext = None,
                                        metrics: dict = None, system_metrics: dict = None,
                                        thread_id: str = None) -> None:
        """Send agent metrics updated notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_metrics_updated_payload(context, metrics)
            message = WebSocketMessage(type="agent_metrics_updated", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "system_metrics": system_metrics or metrics,
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_metrics_updated", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_unregistered(self, context: AgentExecutionContext = None,
                                     unregistration_reason: str = None, agent_id: str = None,
                                     thread_id: str = None) -> None:
        """Send agent unregistered notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_unregistered_payload(context, unregistration_reason)
            message = WebSocketMessage(type="agent_unregistered", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "agent_id": agent_id,
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_unregistered", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_status_changed(self, context: AgentExecutionContext = None,
                                       old_status = None, new_status = None, agent_id: str = None,
                                       thread_id: str = None, metadata: dict = None) -> None:
        """Send agent status changed notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_status_changed_payload(context, old_status, new_status)
            message = WebSocketMessage(type="agent_status_changed", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status,
                "metadata": metadata or {},
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_status_changed", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_manager_shutdown(self, context: AgentExecutionContext = None,
                                         shutdown_reason: str = None, agents_affected: int = 0,
                                         thread_id: str = None) -> None:
        """Send agent manager shutdown notification."""
        if not self.websocket_manager:
            return
        
        if context:
            # Use context-based approach
            payload = self._build_agent_manager_shutdown_payload(context, shutdown_reason)
            message = WebSocketMessage(type="agent_manager_shutdown", payload=payload)
            await self._send_websocket_message(context.thread_id, message)
        else:
            # Use simple parameters for agent manager
            payload = {
                "agents_affected": agents_affected,
                "timestamp": self._get_timestamp()
            }
            message = WebSocketMessage(type="agent_manager_shutdown", payload=payload)
            await self._send_websocket_message_safe(thread_id, message)
    
    async def send_agent_stopped(self, context: AgentExecutionContext,
                                stop_reason: str = None) -> None:
        """Send agent stopped notification."""
        if not self.websocket_manager:
            return
        payload = self._build_agent_stopped_payload(context, stop_reason)
        message = WebSocketMessage(type="agent_stopped", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_agent_error(self, context: AgentExecutionContext,
                              error_message: str, error_type: str = None,
                              error_details: dict = None) -> None:
        """Send structured agent error notification."""
        if not self.websocket_manager:
            return
        payload = self._build_agent_error_payload(context, error_message, error_type, error_details)
        message = WebSocketMessage(type="agent_error", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_agent_log(self, context: AgentExecutionContext,
                            level: str, log_message: str,
                            metadata: dict = None) -> None:
        """Send agent debug logging notification."""
        if not self.websocket_manager:
            return
        payload = self._build_agent_log_payload(context, level, log_message, metadata)
        message = WebSocketMessage(type="agent_log", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_tool_started(self, context: AgentExecutionContext,
                               tool_name: str, parameters: dict = None) -> None:
        """Send tool started notification (before execution)."""
        if not self.websocket_manager:
            return
        payload = self._build_tool_started_payload(context, tool_name, parameters)
        message = WebSocketMessage(type="tool_started", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_stream_chunk(self, context: AgentExecutionContext,
                               chunk_id: str, content: str,
                               is_final: bool = False) -> None:
        """Send incremental content streaming chunk."""
        if not self.websocket_manager:
            return
        payload = self._build_stream_chunk_payload(context, chunk_id, content, is_final)
        message = WebSocketMessage(type="stream_chunk", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_stream_complete(self, context: AgentExecutionContext,
                                  stream_id: str, total_chunks: int,
                                  metadata: dict = None) -> None:
        """Send stream completion signal."""
        if not self.websocket_manager:
            return
        payload = self._build_stream_complete_payload(context, stream_id, total_chunks, metadata)
        message = WebSocketMessage(type="stream_complete", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_subagent_started(self, context: AgentExecutionContext,
                                   subagent_name: str, subagent_id: str = None) -> None:
        """Send sub-agent lifecycle start notification."""
        if not self.websocket_manager:
            return
        payload = self._build_subagent_started_payload(context, subagent_name, subagent_id)
        message = WebSocketMessage(type="subagent_started", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_subagent_completed(self, context: AgentExecutionContext,
                                     subagent_name: str, subagent_id: str = None,
                                     result: dict = None, duration_ms: float = 0) -> None:
        """Send sub-agent lifecycle completion notification."""
        if not self.websocket_manager:
            return
        payload = self._build_subagent_completed_payload(context, subagent_name, subagent_id, result, duration_ms)
        message = WebSocketMessage(type="subagent_completed", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
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
    
    def _build_agent_registered_payload(self, context: AgentExecutionContext,
                                       agent_metadata: dict) -> dict:
        """Build agent registered payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "metadata": agent_metadata or {},
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_failed_payload(self, context: AgentExecutionContext,
                                   error_message: str, error_details: dict) -> dict:
        """Build agent failed payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "error_message": error_message,
            "error_details": error_details or {},
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_cancelled_payload(self, context: AgentExecutionContext,
                                      cancellation_reason: str) -> dict:
        """Build agent cancelled payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "cancellation_reason": cancellation_reason or "User requested cancellation",
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_metrics_updated_payload(self, context: AgentExecutionContext,
                                           metrics: dict) -> dict:
        """Build agent metrics updated payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "metrics": metrics,
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_unregistered_payload(self, context: AgentExecutionContext,
                                         unregistration_reason: str) -> dict:
        """Build agent unregistered payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "unregistration_reason": unregistration_reason or "Agent completed execution",
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_status_changed_payload(self, context: AgentExecutionContext,
                                           old_status: AgentStatus, new_status: AgentStatus) -> dict:
        """Build agent status changed payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_manager_shutdown_payload(self, context: AgentExecutionContext,
                                             shutdown_reason: str) -> dict:
        """Build agent manager shutdown payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "shutdown_reason": shutdown_reason or "Manager shutdown requested",
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_stopped_payload(self, context: AgentExecutionContext,
                                    stop_reason: str) -> dict:
        """Build agent stopped payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "stop_reason": stop_reason or "Agent execution stopped",
            "status": "stopped",
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_error_payload(self, context: AgentExecutionContext,
                                  error_message: str, error_type: str, 
                                  error_details: dict) -> dict:
        """Build structured agent error payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "error_message": error_message,
            "error_type": error_type or "general",
            "error_details": error_details or {},
            "severity": "high",
            "timestamp": self._get_timestamp()
        }
    
    def _build_agent_log_payload(self, context: AgentExecutionContext,
                                level: str, log_message: str, 
                                metadata: dict) -> dict:
        """Build agent log payload."""
        return {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "level": level,
            "message": log_message,
            "metadata": metadata or {},
            "timestamp": self._get_timestamp()
        }
    
    def _build_tool_started_payload(self, context: AgentExecutionContext,
                                   tool_name: str, parameters: dict) -> dict:
        """Build tool started payload."""
        return {
            "tool_name": tool_name,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "parameters": parameters or {},
            "status": "started",
            "timestamp": self._get_timestamp()
        }
    
    def _build_stream_chunk_payload(self, context: AgentExecutionContext,
                                   chunk_id: str, content: str, 
                                   is_final: bool) -> dict:
        """Build stream chunk payload."""
        return {
            "chunk_id": chunk_id,
            "content": content,
            "is_final": is_final,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "timestamp": self._get_timestamp()
        }
    
    def _build_stream_complete_payload(self, context: AgentExecutionContext,
                                      stream_id: str, total_chunks: int,
                                      metadata: dict) -> dict:
        """Build stream complete payload."""
        return {
            "stream_id": stream_id,
            "total_chunks": total_chunks,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "metadata": metadata or {},
            "timestamp": self._get_timestamp()
        }
    
    def _build_subagent_started_payload(self, context: AgentExecutionContext,
                                       subagent_name: str, subagent_id: str) -> dict:
        """Build sub-agent started payload."""
        return {
            "subagent_name": subagent_name,
            "subagent_id": subagent_id or f"{context.run_id}_{subagent_name}",
            "parent_agent_name": context.agent_name,
            "parent_run_id": context.run_id,
            "status": "started",
            "timestamp": self._get_timestamp()
        }
    
    def _build_subagent_completed_payload(self, context: AgentExecutionContext,
                                         subagent_name: str, subagent_id: str,
                                         result: dict, duration_ms: float) -> dict:
        """Build sub-agent completed payload."""
        return {
            "subagent_name": subagent_name,
            "subagent_id": subagent_id or f"{context.run_id}_{subagent_name}",
            "parent_agent_name": context.agent_name,
            "parent_run_id": context.run_id,
            "result": result or {},
            "duration_ms": duration_ms,
            "status": "completed",
            "timestamp": self._get_timestamp()
        }
    
    async def _send_websocket_message(self, thread_id: str, 
                                     message: WebSocketMessage) -> None:
        """Send message via websocket."""
        await self.websocket_manager.send_to_thread(
            thread_id, message.model_dump())
    
    async def _send_websocket_message_safe(self, thread_id: str, 
                                          message: WebSocketMessage) -> None:
        """Safely send websocket message, handles None thread_id."""
        try:
            if thread_id:
                await self.websocket_manager.send_to_thread(
                    thread_id, message.model_dump())
            else:
                # Send to all threads if no specific thread_id
                await self.websocket_manager.broadcast(message.model_dump())
        except Exception as e:
            logger.debug(f"Failed to send websocket notification: {e}")
    
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