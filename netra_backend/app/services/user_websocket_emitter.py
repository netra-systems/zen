"""
UserWebSocketEmitter - Per-request WebSocket event emission with complete user isolation.

Business Value Justification:
- Segment: ALL (Free → Enterprise)
- Business Goal: User Isolation & Chat Value Delivery
- Value Impact: Guarantees events go only to intended users, enables secure multi-user chat
- Strategic Impact: Prevents cross-user event leakage, delivers real AI value through chat

This emitter is created per-request with UserExecutionContext and ensures all events
are sent only to the specific user making the request. It replaces the global singleton
pattern with isolated per-user event emission.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

logger = central_logger.get_logger(__name__)


class UserWebSocketEmitter:
    """Per-user WebSocket event emitter with guaranteed isolation.
    
    This class is created per-request and ensures all events are sent only
    to the specific user associated with the UserExecutionContext. It provides
    the same event interface as the old singleton bridge but with complete
    user isolation.
    """
    
    def __init__(self, context: UserExecutionContext, router: WebSocketEventRouter, 
                 connection_id: Optional[str] = None):
        """Initialize emitter for specific user context.
        
        Args:
            context: User execution context with validated IDs
            router: WebSocket event router for infrastructure
            connection_id: Optional specific connection ID to target
        """
        self.user_id = context.user_id
        self.thread_id = context.thread_id
        self.run_id = context.run_id
        self.request_id = context.request_id
        self.connection_id = connection_id
        self.router = router
        
        # Event tracking for debugging and metrics
        self.events_sent = 0
        self.events_failed = 0
        self.created_at = datetime.now(timezone.utc)
        
        logger.info(f"UserWebSocketEmitter created for user {self.user_id[:8]}... "
                   f"(run_id: {self.run_id})")
    
    async def notify_agent_started(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent started event to this user only.
        
        Args:
            agent_name: Name of the agent starting
            metadata: Optional metadata about the agent execution
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": "agent_started",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "status": "started",
                "metadata": metadata or {},
                "message": f"{agent_name} has started processing your request"
            }
        }
        
        return await self._send_event(event, "agent_started")
    
    async def notify_agent_thinking(self, agent_name: str, thought: str, 
                                  step: Optional[str] = None) -> bool:
        """Send thinking event to this user only.
        
        Args:
            agent_name: Name of the thinking agent
            thought: The agent's reasoning or thought process
            step: Optional step identifier
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": "agent_thinking",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "thought": thought,
                "step": step,
                "message": f"{agent_name} is analyzing: {thought[:100]}..."
            }
        }
        
        return await self._send_event(event, "agent_thinking")
    
    async def notify_tool_executing(self, agent_name: str, tool_name: str, 
                                  tool_input: Optional[Dict[str, Any]] = None) -> bool:
        """Send tool execution event to this user only.
        
        Args:
            agent_name: Name of the agent using the tool
            tool_name: Name of the tool being executed
            tool_input: Optional tool input parameters (sanitized)
            
        Returns:
            bool: True if event sent successfully
        """
        # Sanitize tool input for security
        safe_input = self._sanitize_tool_input(tool_input) if tool_input else {}
        
        event = {
            "type": "tool_executing",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "tool_name": tool_name,
                "tool_input": safe_input,
                "message": f"{agent_name} is using {tool_name}"
            }
        }
        
        return await self._send_event(event, "tool_executing")
    
    async def notify_tool_completed(self, agent_name: str, tool_name: str, 
                                  success: bool, result_summary: Optional[str] = None) -> bool:
        """Send tool completion event to this user only.
        
        Args:
            agent_name: Name of the agent that used the tool
            tool_name: Name of the completed tool
            success: Whether tool execution was successful
            result_summary: Optional summary of tool results
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": "tool_completed",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "tool_name": tool_name,
                "success": success,
                "result_summary": result_summary,
                "message": f"{agent_name} {'completed' if success else 'failed to complete'} {tool_name}"
            }
        }
        
        return await self._send_event(event, "tool_completed")
    
    async def notify_agent_completed(self, agent_name: str, result: Dict[str, Any], 
                                   success: bool = True) -> bool:
        """Send agent completion event to this user only.
        
        Args:
            agent_name: Name of the completed agent
            result: Agent execution results
            success: Whether agent completed successfully
            
        Returns:
            bool: True if event sent successfully
        """
        # Sanitize result for user consumption
        safe_result = self._sanitize_agent_result(result)
        
        event = {
            "type": "agent_completed",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "success": success,
                "result": safe_result,
                "message": f"{agent_name} has {'completed' if success else 'failed'} processing your request"
            }
        }
        
        return await self._send_event(event, "agent_completed")
    
    async def notify_agent_error(self, agent_name: str, error_type: str, 
                               error_message: str, recoverable: bool = False) -> bool:
        """Send agent error event to this user only.
        
        Args:
            agent_name: Name of the agent that encountered error
            error_type: Type/category of error
            error_message: User-friendly error message
            recoverable: Whether the error is recoverable
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": "agent_error",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "error_type": error_type,
                "error_message": error_message,
                "recoverable": recoverable,
                "message": f"{agent_name} encountered an error: {error_message}"
            }
        }
        
        return await self._send_event(event, "agent_error")
    
    async def notify_progress_update(self, agent_name: str, progress_percentage: float, 
                                   current_step: str, estimated_completion: Optional[str] = None) -> bool:
        """Send progress update event to this user only.
        
        Args:
            agent_name: Name of the agent reporting progress
            progress_percentage: Progress as percentage (0-100)
            current_step: Description of current step
            estimated_completion: Optional estimated completion time
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": "progress_update",
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "progress_percentage": min(100, max(0, progress_percentage)),
                "current_step": current_step,
                "estimated_completion": estimated_completion,
                "message": f"{agent_name}: {current_step} ({progress_percentage:.1f}% complete)"
            }
        }
        
        return await self._send_event(event, "progress_update")
    
    async def notify_custom(self, event_type: str, payload: Dict[str, Any], 
                          agent_name: Optional[str] = None) -> bool:
        """Send custom event to this user only.
        
        Args:
            event_type: Custom event type
            payload: Event payload
            agent_name: Optional agent name
            
        Returns:
            bool: True if event sent successfully
        """
        event = {
            "type": event_type,
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        
        return await self._send_event(event, event_type)
    
    # Statistics and debugging methods
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics.
        
        Returns:
            Dictionary with emitter statistics
        """
        uptime = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        success_rate = (
            self.events_sent / (self.events_sent + self.events_failed) * 100
            if (self.events_sent + self.events_failed) > 0 else 0
        )
        
        return {
            "user_id": self.user_id[:8] + "...",  # Truncated for security
            "run_id": self.run_id,
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "success_rate": success_rate,
            "uptime_seconds": uptime,
            "connection_id": self.connection_id
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"UserWebSocketEmitter(user={self.user_id[:8]}..., run_id={self.run_id})"
    
    # Private helper methods
    
    async def _send_event(self, event: Dict[str, Any], event_type: str) -> bool:
        """Send event through the router with proper error handling.
        
        Args:
            event: Event data to send
            event_type: Type of event for logging
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Add request_id for complete traceability
            event["request_id"] = self.request_id
            
            if self.connection_id:
                # Send to specific connection
                success = await self.router.route_event(self.user_id, self.connection_id, event)
            else:
                # Broadcast to all user connections
                sent_count = await self.router.broadcast_to_user(self.user_id, event)
                success = sent_count > 0
            
            if success:
                self.events_sent += 1
                logger.debug(f"Sent {event_type} event to user {self.user_id[:8]}... (run_id: {self.run_id})")
            else:
                self.events_failed += 1
                logger.warning(f"Failed to send {event_type} event to user {self.user_id[:8]}... (run_id: {self.run_id})")
            
            return success
            
        except Exception as e:
            self.events_failed += 1
            logger.error(f"Error sending {event_type} event to user {self.user_id[:8]}...: {e}")
            return False
    
    def _sanitize_tool_input(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool input for user-facing events.
        
        Removes sensitive information and truncates large inputs.
        """
        sensitive_keys = {'password', 'token', 'key', 'secret', 'api_key', 'auth'}
        sanitized = {}
        
        for key, value in tool_input.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            elif isinstance(value, (dict, list)) and len(str(value)) > 500:
                sanitized[key] = "[LARGE_DATA]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_agent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize agent results for user consumption.
        
        Removes internal details and sensitive information.
        """
        # Remove internal keys
        internal_keys = {'_internal', 'debug_info', 'system_context', 'raw_response'}
        
        sanitized = {}
        for key, value in result.items():
            if key not in internal_keys:
                if isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "..."
                else:
                    sanitized[key] = value
        
        return sanitized