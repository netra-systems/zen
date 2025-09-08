"""WebSocket notification functionality with guaranteed event delivery and concurrency optimization.

⚠️  DEPRECATION WARNING ⚠️ 
This module is DEPRECATED. Use AgentWebSocketBridge instead.

AgentWebSocketBridge provides:
- Single source of truth for all WebSocket notifications
- Better integration with the execution lifecycle
- Simplified API with guaranteed message delivery
- Built-in health monitoring and recovery

Business Value: Ensures reliable real-time user feedback under load, preventing user abandonment.
Optimizations: Event queuing, delivery confirmation, backlog handling, concurrent user support.
"""

import asyncio
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Deque, Dict, Optional

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import WebSocketManager

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import AgentStarted
from netra_backend.app.schemas.registry import AgentStatus
from netra_backend.app.schemas.shared_types import AgentStatus as SharedAgentStatus
from netra_backend.app.schemas.websocket_models import WebSocketMessage

logger = central_logger.get_logger(__name__)

# Import event monitor for runtime monitoring
try:
    from netra_backend.app.websocket_core.event_monitor import chat_event_monitor
except ImportError:
    chat_event_monitor = None
    logger.warning("Chat event monitor not available - runtime monitoring disabled")


class WebSocketNotifier:
    """Handles WebSocket notifications for agent execution with guaranteed delivery.
    
    ⚠️  DEPRECATION WARNING ⚠️ 
    This class is DEPRECATED. Use netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge instead.
    
    Features:
    - Guaranteed delivery of critical events (agent_started, tool_executing, tool_completed, agent_completed)
    - Event queuing for backlog scenarios with user feedback
    - Concurrent execution optimization with proper ordering
    - Delivery confirmation tracking
    - Backlog processing indicators
    """
    
    def __init__(self, websocket_manager: 'WebSocketManager'):
        import warnings
        warnings.warn(
            "WebSocketNotifier is deprecated. Use AgentWebSocketBridge instead. "
            "This class will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning("⚠️  DEPRECATION: WebSocketNotifier is deprecated. Use AgentWebSocketBridge instead.")
        
        self.websocket_manager = websocket_manager
        
        # CONCURRENCY OPTIMIZATION: Event delivery guarantees
        self.event_queue: Deque[Dict] = deque()  # Queue for failed deliveries
        self.delivery_confirmations: Dict[str, float] = {}  # message_id -> timestamp
        self.active_operations: Dict[str, Dict] = {}  # thread_id -> operation_info
        self.backlog_notifications: Dict[str, float] = {}  # thread_id -> last_notification
        
        # PERFORMANCE SETTINGS for <500ms event delivery
        self.max_queue_size = 1000
        self.retry_delay = 0.1  # 100ms retry delay
        self.backlog_notification_interval = 5.0  # 5s between backlog notifications
        self.critical_events = {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}
        
        # Background task for queue processing
        self._queue_processor_task = None
        self._shutdown = False
        self._processing_lock = asyncio.Lock()
    
    async def send_agent_started(self, context: AgentExecutionContext) -> None:
        """Send agent started notification with guaranteed delivery."""
        if not self.websocket_manager:
            return
        
        # Mark operation as active for backlog handling
        self._mark_operation_active(context)
        
        message = self._build_started_message(context)
        await self._send_critical_event(context.thread_id, message, 'agent_started')
    
    async def send_agent_thinking(self, context: AgentExecutionContext, 
                                  thought: str, step_number: int = None, 
                                  progress_percentage: float = None,
                                  estimated_remaining_ms: int = None,
                                  current_operation: str = None) -> None:
        """Send enhanced agent thinking notification with context and progress."""
        if not self.websocket_manager:
            return
        payload = self._build_enhanced_thinking_payload(
            context, thought, step_number, progress_percentage, 
            estimated_remaining_ms, current_operation
        )
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
                                  tool_name: str, tool_purpose: str = None,
                                  estimated_duration_ms: int = None,
                                  parameters_summary: str = None) -> None:
        """Send enhanced tool executing notification with purpose and timing."""
        if not self.websocket_manager:
            return
        payload = self._build_enhanced_tool_executing_payload(
            context, tool_name, tool_purpose, estimated_duration_ms, parameters_summary
        )
        message = WebSocketMessage(type="tool_executing", payload=payload)
        await self._send_critical_event(context.thread_id, message, 'tool_executing')
    
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
        
        # Mark operation as complete
        self._mark_operation_complete(context)
        
        payload = self._build_agent_completed_payload(context, result, duration_ms)
        message = WebSocketMessage(type="agent_completed", payload=payload)
        await self._send_critical_event(context.thread_id, message, 'agent_completed')
    
    async def send_tool_completed(self, context: AgentExecutionContext,
                                 tool_name: str, result: dict = None) -> None:
        """Send tool completed notification."""
        if not self.websocket_manager:
            return
        payload = self._build_tool_completed_payload(context, tool_name, result)
        message = WebSocketMessage(type="tool_completed", payload=payload)
        await self._send_critical_event(context.thread_id, message, 'tool_completed')
    
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
                              error_details: dict = None, recovery_suggestions: list = None,
                              is_recoverable: bool = True, 
                              estimated_retry_delay_ms: int = None) -> None:
        """Send enhanced agent error notification with recovery guidance."""
        if not self.websocket_manager:
            return
        payload = self._build_enhanced_agent_error_payload(
            context, error_message, error_type, error_details, 
            recovery_suggestions, is_recoverable, estimated_retry_delay_ms
        )
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
            run_id=str(context.run_id),
            timestamp=datetime.now(timezone.utc).timestamp()
        )
    
    def _build_thinking_payload(self, context: AgentExecutionContext, 
                               thought: str, step_number: int) -> dict:
        """Build basic thinking notification payload (legacy support)."""
        return self._build_enhanced_thinking_payload(context, thought, step_number)
    
    def _build_enhanced_thinking_payload(self, context: AgentExecutionContext, 
                                       thought: str, step_number: int = None,
                                       progress_percentage: float = None,
                                       estimated_remaining_ms: int = None,
                                       current_operation: str = None) -> dict:
        """Build enhanced thinking notification payload with context and progress."""
        payload = {
            "thought": thought, 
            "agent_name": context.agent_name,
            "step_number": step_number, 
            "total_steps": getattr(context, 'total_steps', 0),
            "timestamp": self._get_timestamp()
        }
        
        # Add enhanced context information
        if progress_percentage is not None:
            payload["progress_percentage"] = min(100, max(0, progress_percentage))
        if estimated_remaining_ms is not None:
            payload["estimated_remaining_ms"] = estimated_remaining_ms
        if current_operation:
            payload["current_operation"] = current_operation
            
        # Add contextual urgency indicator
        if estimated_remaining_ms and estimated_remaining_ms > 10000:  # >10 seconds
            payload["urgency"] = "low_priority"
        elif estimated_remaining_ms and estimated_remaining_ms > 5000:  # >5 seconds
            payload["urgency"] = "medium_priority"
        else:
            payload["urgency"] = "high_priority"
            
        return payload
    
    def _build_partial_result_payload(self, context: AgentExecutionContext,
                                     content: str, is_complete: bool) -> dict:
        """Build partial result payload."""
        return {
            "content": content, "agent_name": context.agent_name,
            "is_complete": is_complete, "timestamp": self._get_timestamp()
        }
    
    def _build_tool_executing_payload(self, context: AgentExecutionContext,
                                     tool_name: str) -> dict:
        """Build basic tool executing payload (legacy support)."""
        return self._build_enhanced_tool_executing_payload(context, tool_name)
    
    def _build_enhanced_tool_executing_payload(self, context: AgentExecutionContext,
                                             tool_name: str, tool_purpose: str = None,
                                             estimated_duration_ms: int = None,
                                             parameters_summary: str = None) -> dict:
        """Build enhanced tool executing payload with purpose and context."""
        payload = {
            "tool_name": tool_name, 
            "agent_name": context.agent_name,
            "timestamp": self._get_timestamp()
        }
        
        # Add enhanced tool context
        if tool_purpose:
            payload["tool_purpose"] = tool_purpose
        if estimated_duration_ms is not None:
            payload["estimated_duration_ms"] = estimated_duration_ms
        if parameters_summary:
            payload["parameters_summary"] = parameters_summary
            
        # Add execution hints for UI
        payload["execution_phase"] = "starting"
        
        # Add contextual information based on tool name
        tool_context = self._get_tool_context_hints(tool_name)
        if tool_context:
            payload.update(tool_context)
            
        return payload
    
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
        """Build basic agent error payload (legacy support)."""
        return self._build_enhanced_agent_error_payload(
            context, error_message, error_type, error_details
        )
    
    def _build_enhanced_agent_error_payload(self, context: AgentExecutionContext,
                                          error_message: str, error_type: str = None,
                                          error_details: dict = None, 
                                          recovery_suggestions: list = None,
                                          is_recoverable: bool = True,
                                          estimated_retry_delay_ms: int = None) -> dict:
        """Build enhanced agent error payload with recovery guidance."""
        payload = {
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "error_message": error_message,
            "error_type": error_type or "general",
            "error_details": error_details or {},
            "severity": self._determine_error_severity(error_type, error_message),
            "timestamp": self._get_timestamp(),
            "is_recoverable": is_recoverable
        }
        
        # Add recovery guidance
        if recovery_suggestions:
            payload["recovery_suggestions"] = recovery_suggestions
        else:
            payload["recovery_suggestions"] = self._generate_default_recovery_suggestions(
                error_type, error_message
            )
            
        if estimated_retry_delay_ms is not None:
            payload["estimated_retry_delay_ms"] = estimated_retry_delay_ms
            
        # Add user-friendly error explanation
        payload["user_friendly_message"] = self._generate_user_friendly_error_message(
            error_type, error_message, context.agent_name
        )
            
        return payload
    
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
    
    # Enhanced utility methods for better WebSocket context
    
    def _get_tool_context_hints(self, tool_name: str) -> dict:
        """Get contextual hints for tools based on their name."""
        tool_contexts = {
            "search": {"category": "information_retrieval", "expected_duration": "medium"},
            "analyze": {"category": "data_processing", "expected_duration": "long"},
            "query": {"category": "database_operation", "expected_duration": "short"},
            "generate": {"category": "content_creation", "expected_duration": "medium"},
            "validate": {"category": "verification", "expected_duration": "short"},
            "optimize": {"category": "performance_tuning", "expected_duration": "long"},
            "export": {"category": "data_export", "expected_duration": "medium"},
            "import": {"category": "data_import", "expected_duration": "long"}
        }
        
        # Find matching context based on tool name patterns
        for pattern, context in tool_contexts.items():
            if pattern.lower() in tool_name.lower():
                return context
        
        return {"category": "general", "expected_duration": "medium"}
    
    def _determine_error_severity(self, error_type: str, error_message: str) -> str:
        """Determine error severity based on type and message."""
        if not error_type:
            return "medium"
            
        critical_errors = ["authentication", "authorization", "database", "network"]
        high_errors = ["timeout", "rate_limit", "validation"]
        
        error_type_lower = error_type.lower()
        error_message_lower = error_message.lower() if error_message else ""
        
        if any(critical in error_type_lower or critical in error_message_lower 
               for critical in critical_errors):
            return "critical"
        elif any(high in error_type_lower or high in error_message_lower 
                 for high in high_errors):
            return "high"
        else:
            return "medium"
    
    def _generate_default_recovery_suggestions(self, error_type: str, error_message: str) -> list:
        """Generate contextual recovery suggestions based on error details."""
        suggestions = []
        
        if not error_type:
            return ["Please try again", "Check your request and retry"]
            
        error_type_lower = error_type.lower()
        error_message_lower = error_message.lower() if error_message else ""
        
        if "timeout" in error_type_lower or "timeout" in error_message_lower:
            suggestions = [
                "The operation took longer than expected",
                "Try breaking your request into smaller parts",
                "Check if the system is under heavy load"
            ]
        elif "rate_limit" in error_type_lower or "rate limit" in error_message_lower:
            suggestions = [
                "You've hit a rate limit",
                "Please wait a moment before trying again",
                "Consider upgrading your plan for higher limits"
            ]
        elif "validation" in error_type_lower or "invalid" in error_message_lower:
            suggestions = [
                "Please check your request format",
                "Ensure all required fields are provided",
                "Review the request parameters and try again"
            ]
        elif "database" in error_type_lower or "db" in error_message_lower:
            suggestions = [
                "There was a temporary database issue",
                "Your data is safe, please try again",
                "If this persists, please contact support"
            ]
        elif "network" in error_type_lower or "connection" in error_message_lower:
            suggestions = [
                "There was a network connectivity issue",
                "Please check your internet connection",
                "The issue may resolve automatically"
            ]
        else:
            suggestions = [
                f"An unexpected error occurred in {error_type or 'the system'}",
                "Please try your request again",
                "If the issue persists, please contact support"
            ]
            
        return suggestions
    
    def _generate_user_friendly_error_message(self, error_type: str, 
                                            error_message: str, agent_name: str) -> str:
        """Generate user-friendly error message."""
        if not error_type:
            return f"The {agent_name} encountered an issue while processing your request."
            
        error_type_lower = error_type.lower()
        
        if "timeout" in error_type_lower:
            return f"The {agent_name} is taking longer than usual. This might be due to high system load."
        elif "rate_limit" in error_type_lower:
            return "You've made many requests recently. Please wait a moment before trying again."
        elif "validation" in error_type_lower:
            return "There's an issue with your request format. Please check the details and try again."
        elif "network" in error_type_lower:
            return "There's a temporary connectivity issue. Please try again in a moment."
        elif "database" in error_type_lower:
            return "We're experiencing a temporary data access issue. Your information is safe."
        else:
            return f"The {agent_name} encountered an unexpected issue while processing your request."
    
    # Enhanced event types for improved user experience
    
    async def send_periodic_update(self, context: AgentExecutionContext,
                                  operation_name: str, progress_percentage: float = None,
                                  status_message: str = None, 
                                  estimated_remaining_ms: int = None,
                                  current_step: str = None) -> None:
        """Send periodic update for long-running operations (>5 seconds)."""
        if not self.websocket_manager:
            return
        payload = self._build_periodic_update_payload(
            context, operation_name, progress_percentage, status_message,
            estimated_remaining_ms, current_step
        )
        message = WebSocketMessage(type="periodic_update", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_operation_started(self, context: AgentExecutionContext,
                                   operation_name: str, operation_type: str = None,
                                   expected_duration_ms: int = None,
                                   operation_description: str = None) -> None:
        """Send operation started notification for long-running tasks."""
        if not self.websocket_manager:
            return
        payload = self._build_operation_started_payload(
            context, operation_name, operation_type, expected_duration_ms, operation_description
        )
        message = WebSocketMessage(type="operation_started", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    async def send_operation_completed(self, context: AgentExecutionContext,
                                     operation_name: str, duration_ms: float,
                                     result_summary: str = None,
                                     metrics: dict = None) -> None:
        """Send operation completed notification."""
        if not self.websocket_manager:
            return
        payload = self._build_operation_completed_payload(
            context, operation_name, duration_ms, result_summary, metrics
        )
        message = WebSocketMessage(type="operation_completed", payload=payload)
        await self._send_websocket_message(context.thread_id, message)
    
    # Enhanced payload builders
    
    def _build_periodic_update_payload(self, context: AgentExecutionContext,
                                      operation_name: str, progress_percentage: float,
                                      status_message: str, estimated_remaining_ms: int,
                                      current_step: str) -> dict:
        """Build periodic update payload for long-running operations."""
        payload = {
            "operation_name": operation_name,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "timestamp": self._get_timestamp(),
            "update_type": "periodic_progress"
        }
        
        if progress_percentage is not None:
            payload["progress_percentage"] = min(100, max(0, progress_percentage))
        if status_message:
            payload["status_message"] = status_message
        if estimated_remaining_ms is not None:
            payload["estimated_remaining_ms"] = estimated_remaining_ms
        if current_step:
            payload["current_step"] = current_step
            
        return payload
    
    def _build_operation_started_payload(self, context: AgentExecutionContext,
                                       operation_name: str, operation_type: str,
                                       expected_duration_ms: int, operation_description: str) -> dict:
        """Build operation started payload."""
        payload = {
            "operation_name": operation_name,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "timestamp": self._get_timestamp(),
            "status": "started"
        }
        
        if operation_type:
            payload["operation_type"] = operation_type
        if expected_duration_ms is not None:
            payload["expected_duration_ms"] = expected_duration_ms
        if operation_description:
            payload["operation_description"] = operation_description
            
        return payload
    
    def _build_operation_completed_payload(self, context: AgentExecutionContext,
                                         operation_name: str, duration_ms: float,
                                         result_summary: str, metrics: dict) -> dict:
        """Build operation completed payload."""
        payload = {
            "operation_name": operation_name,
            "agent_name": context.agent_name,
            "run_id": context.run_id,
            "duration_ms": duration_ms,
            "timestamp": self._get_timestamp(),
            "status": "completed"
        }
        
        if result_summary:
            payload["result_summary"] = result_summary
        if metrics:
            payload["metrics"] = metrics
            
        return payload
    
    # ============================================================================
    # CRITICAL: Guaranteed Event Delivery and Concurrency Optimization
    # ============================================================================
    
    def _mark_operation_active(self, context: AgentExecutionContext) -> None:
        """Mark an operation as active for backlog handling."""
        self.active_operations[context.thread_id] = {
            'agent_name': context.agent_name,
            'run_id': context.run_id,
            'start_time': time.time(),
            'last_event_time': time.time(),
            'event_count': 0,
            'processing': True
        }
    
    def _mark_operation_complete(self, context: AgentExecutionContext) -> None:
        """Mark an operation as complete."""
        if context.thread_id in self.active_operations:
            self.active_operations[context.thread_id]['processing'] = False
            # Keep for a short time for final events
            asyncio.create_task(self._cleanup_operation_after_delay(context.thread_id, 10.0))
    
    async def _cleanup_operation_after_delay(self, thread_id: str, delay: float) -> None:
        """Clean up operation data after delay."""
        await asyncio.sleep(delay)
        self.active_operations.pop(thread_id, None)
    
    async def _send_critical_event(self, thread_id: str, message: WebSocketMessage, event_type: str) -> bool:
        """Send critical event with guaranteed delivery, retry logic, and confirmation tracking."""
        message_id = str(uuid.uuid4())
        
        # Add confirmation requirement for critical events
        requires_confirmation = event_type in self.critical_events
        
        event_data = {
            'message_id': message_id,
            'thread_id': thread_id,
            'message': message,
            'event_type': event_type,
            'timestamp': time.time(),
            'retry_count': 0,
            'max_retries': 3 if event_type in self.critical_events else 1,
            'requires_confirmation': requires_confirmation
        }
        
        # Track pending confirmation if required
        if requires_confirmation:
            self.delivery_confirmations[message_id] = {
                'thread_id': thread_id,
                'event_type': event_type,
                'timestamp': time.time(),
                'confirmed': False
            }
        
        # Try immediate delivery first
        success = await self._attempt_delivery(event_data)
        
        if success:
            self._update_operation_activity(thread_id)
            
            # Record event in monitor
            if chat_event_monitor:
                await chat_event_monitor.record_event(
                    event_type=event_type,
                    thread_id=thread_id,
                    metadata={"message_id": message_id, "requires_confirmation": requires_confirmation}
                )
            
            # For critical events, log if confirmation is pending
            if requires_confirmation:
                logger.info(f"Critical event {event_type} sent to thread {thread_id}, awaiting confirmation (id: {message_id})")
            return True
        else:
            # Log critical failure
            logger.critical(f"CRITICAL EVENT DELIVERY FAILED: {event_type} for thread {thread_id}")
            
            # Queue for retry if critical
            if event_type in self.critical_events:
                await self._queue_for_retry(event_data)
                
                # Trigger emergency notification if this is a critical event
                await self._trigger_emergency_notification(thread_id, event_type)
            await self._notify_user_of_backlog(thread_id)
        
        return False
    
    async def _trigger_emergency_notification(self, thread_id: str, event_type: str) -> None:
        """Trigger emergency notification system when critical events fail to deliver."""
        try:
            # Log to critical monitoring system
            logger.critical(
                f"EMERGENCY: Critical event '{event_type}' failed to deliver for thread {thread_id}. "
                f"User experience severely impacted. Immediate intervention required."
            )
            
            # Could trigger alerts to ops team, write to Redis, send to monitoring system, etc.
            # For now, ensure it's logged at CRITICAL level for alerting
            
            # Track in metrics for dashboard visibility
            if hasattr(self, '_failed_critical_events'):
                self._failed_critical_events.append({
                    'thread_id': thread_id,
                    'event_type': event_type,
                    'timestamp': time.time()
                })
            else:
                self._failed_critical_events = [{
                    'thread_id': thread_id,
                    'event_type': event_type,
                    'timestamp': time.time()
                }]
            
        except Exception as e:
            # Even emergency notification shouldn't crash the system
            logger.error(f"Failed to send emergency notification: {e}")
    
    async def _attempt_delivery(self, event_data: Dict) -> bool:
        """Attempt to deliver a single event with confirmation tracking."""
        try:
            # Prepare message with confirmation requirement if needed
            message_dict = event_data['message'].model_dump() if hasattr(event_data['message'], 'model_dump') else event_data['message']
            
            # Add confirmation metadata for critical events
            if event_data.get('requires_confirmation', False):
                message_dict['requires_confirmation'] = True
                message_dict['message_id'] = event_data['message_id']
            
            success = await self.websocket_manager.send_to_thread(
                event_data['thread_id'], 
                message_dict
            )
            
            if success:
                # Track that message was sent (not yet confirmed)
                if event_data.get('requires_confirmation', False):
                    # Message sent but not confirmed yet
                    logger.debug(f"Critical event {event_data['event_type']} sent, awaiting confirmation")
                else:
                    # Non-critical events are considered delivered on send
                    self.delivery_confirmations[event_data['message_id']] = time.time()
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Event delivery failed for {event_data['event_type']}: {e}")
            return False
    
    async def _queue_for_retry(self, event_data: Dict) -> None:
        """Queue event for retry with backlog management."""
        async with self._processing_lock:
            if len(self.event_queue) >= self.max_queue_size:
                # Remove oldest non-critical events to make room
                removed = 0
                temp_queue = deque()
                while self.event_queue and removed < 10:
                    old_event = self.event_queue.popleft()
                    if old_event['event_type'] in self.critical_events:
                        temp_queue.append(old_event)
                    else:
                        removed += 1
                
                # Put critical events back
                while temp_queue:
                    self.event_queue.appendleft(temp_queue.pop())
                
                logger.warning(f"Removed {removed} non-critical events from queue due to backlog")
            
            self.event_queue.append(event_data)
            await self._ensure_queue_processor_running()
    
    async def _ensure_queue_processor_running(self) -> None:
        """Ensure the background queue processor is running."""
        if (self._queue_processor_task is None or 
            self._queue_processor_task.done()) and not self._shutdown:
            self._queue_processor_task = asyncio.create_task(self._process_event_queue())
    
    async def _process_event_queue(self) -> None:
        """Background task to process queued events."""
        while not self._shutdown and self.event_queue:
            try:
                async with self._processing_lock:
                    if not self.event_queue:
                        break
                    
                    event_data = self.event_queue.popleft()
                
                # Try delivery with exponential backoff
                event_data['retry_count'] += 1
                if event_data['retry_count'] <= event_data['max_retries']:
                    if await self._attempt_delivery(event_data):
                        logger.debug(f"Successfully delivered queued {event_data['event_type']} after {event_data['retry_count']} retries")
                        continue
                    else:
                        # Re-queue with delay
                        await asyncio.sleep(self.retry_delay * (2 ** event_data['retry_count']))
                        async with self._processing_lock:
                            self.event_queue.append(event_data)
                else:
                    logger.error(f"Failed to deliver {event_data['event_type']} after {event_data['max_retries']} retries")
                
                # Small delay between processing attempts
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(0.1)
    
    async def _notify_user_of_backlog(self, thread_id: str) -> None:
        """Notify user that events are being processed from backlog."""
        current_time = time.time()
        last_notification = self.backlog_notifications.get(thread_id, 0)
        
        if current_time - last_notification >= self.backlog_notification_interval:
            # Use agent_update for backlog notifications (valid message type)
            from netra_backend.app.schemas.websocket_models import AgentUpdatePayload
            backlog_payload = AgentUpdatePayload(
                run_id="system",
                agent_id="system",
                status="executing",
                message="Processing your request - there may be a slight delay due to high system load",
                progress=None,
                current_task="backlog_processing",
                metadata={"queue_size": len(self.event_queue)}
            )
            backlog_message = WebSocketMessage(
                type="agent_update",
                payload=backlog_payload.model_dump()
            )
            
            # Send directly without queuing (to avoid recursion)
            try:
                await self.websocket_manager.send_to_thread(thread_id, backlog_message.model_dump())
                self.backlog_notifications[thread_id] = current_time
            except Exception as e:
                logger.debug(f"Failed to send backlog notification: {e}")
    
    def _update_operation_activity(self, thread_id: str) -> None:
        """Update operation activity timestamp."""
        if thread_id in self.active_operations:
            self.active_operations[thread_id]['last_event_time'] = time.time()
            self.active_operations[thread_id]['event_count'] += 1
    
    async def get_delivery_stats(self) -> Dict[str, int]:
        """Get event delivery statistics."""
        return {
            'queued_events': len(self.event_queue),
            'active_operations': len(self.active_operations),
            'delivery_confirmations': len(self.delivery_confirmations),
            'backlog_notifications_sent': len(self.backlog_notifications)
        }
    
    async def shutdown(self) -> None:
        """Shutdown the notifier and clean up resources."""
        self._shutdown = True
        
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Clear queues
        self.event_queue.clear()
        self.delivery_confirmations.clear()
        self.active_operations.clear()
        self.backlog_notifications.clear()

