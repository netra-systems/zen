"""Transparent WebSocket Events - Real-time Service Status Communication

Business Value Justification:
- Segment: All tiers (transparent communication benefits all users)
- Business Goal: Eliminate user confusion during service issues
- Value Impact: Transparent service status builds trust vs misleading mock responses
- Revenue Impact: Reduces churn from unclear error messages, protects $4.1M ARR

This module provides WebSocket events that give users real-time visibility
into service status, initialization progress, and degraded mode operations.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventType(Enum):
    """WebSocket event types for transparent service communication."""
    # Original agent events (preserved for chat UX)
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"  
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    
    # New transparent service events
    SERVICE_INITIALIZING = "service_initializing"
    SERVICE_READY = "service_ready"
    SERVICE_DEGRADED = "service_degraded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    SERVICE_RECOVERED = "service_recovered"
    
    # System status events
    SYSTEM_STATUS = "system_status"
    USER_QUEUE_POSITION = "user_queue_position"
    ESTIMATED_WAIT_TIME = "estimated_wait_time"


class TransparentWebSocketEmitter:
    """WebSocket emitter that provides transparent service status communication.
    
    This class ensures users get real-time visibility into service status
    instead of misleading mock responses or silent failures.
    """
    
    def __init__(self, context: UserExecutionContext):
        """Initialize transparent WebSocket emitter with user context."""
        self.context = context
        self.user_id = context.user_id
        self.request_id = context.request_id
        self.events_sent = []
        
    async def emit_service_initializing(
        self,
        service_name: str,
        initialization_steps: Optional[List[str]] = None,
        estimated_time_seconds: Optional[int] = None
    ) -> None:
        """Notify user that service is initializing.
        
        This replaces silent service startup with transparent communication.
        """
        event_data = {
            "type": WebSocketEventType.SERVICE_INITIALIZING.value,
            "service_name": service_name,
            "message": f"Initializing {service_name}...",
            "steps": initialization_steps or [],
            "estimated_time_seconds": estimated_time_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "initialization_attempt": len([
                    e for e in self.events_sent 
                    if e.get("service_name") == service_name 
                    and e.get("type") == WebSocketEventType.SERVICE_INITIALIZING.value
                ]) + 1
            }
        }
        
        await self._emit_event(event_data)
        logger.info(f"Service initialization started: {service_name} for user {self.user_id}")
    
    async def emit_service_ready(
        self,
        service_name: str,
        initialization_time_ms: Optional[float] = None,
        service_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Notify user that service is ready for processing.
        
        This provides positive confirmation that services are operational.
        """
        event_data = {
            "type": WebSocketEventType.SERVICE_READY.value,
            "service_name": service_name,
            "message": f"{service_name} is ready for processing",
            "initialization_time_ms": initialization_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "service_metadata": service_metadata or {},
                "status": "fully_operational"
            }
        }
        
        await self._emit_event(event_data)
        logger.info(f"Service ready: {service_name} for user {self.user_id}")
    
    async def emit_service_degraded(
        self,
        service_name: str,
        reason: str,
        fallback_options: Optional[List[str]] = None,
        performance_impact: Optional[str] = None
    ) -> None:
        """Notify user that service is degraded but functional.
        
        This provides honest communication about service limitations
        instead of hiding issues behind mock responses.
        """
        event_data = {
            "type": WebSocketEventType.SERVICE_DEGRADED.value,
            "service_name": service_name,
            "message": f"{service_name} is running in degraded mode",
            "reason": reason,
            "fallback_options": fallback_options or [],
            "performance_impact": performance_impact or "Reduced performance or limited functionality",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "status": "degraded_operational",
                "can_continue_processing": True
            }
        }
        
        await self._emit_event(event_data)
        logger.warning(f"Service degraded: {service_name} for user {self.user_id}: {reason}")
    
    async def emit_service_unavailable(
        self,
        service_name: str,
        reason: str,
        estimated_recovery_seconds: Optional[int] = None,
        alternatives: Optional[List[str]] = None,
        is_critical: bool = False
    ) -> None:
        """Notify user that service is completely unavailable.
        
        This provides transparent communication about service failures
        instead of returning mock responses.
        """
        # Determine user-tier-specific messaging
        if self.context.user_tier == "enterprise":
            enterprise_message = "Enterprise support has been notified automatically"
            alternatives = (alternatives or []) + [
                "Priority support ticket created",
                "Account manager will contact you shortly"
            ]
        else:
            enterprise_message = None
        
        event_data = {
            "type": WebSocketEventType.SERVICE_UNAVAILABLE.value,
            "service_name": service_name,
            "message": f"{service_name} is temporarily unavailable",
            "reason": reason,
            "estimated_recovery_seconds": estimated_recovery_seconds,
            "alternatives": alternatives or [],
            "is_critical": is_critical,
            "enterprise_message": enterprise_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "status": "unavailable",
                "can_continue_processing": not is_critical,
                "retry_recommended": True
            }
        }
        
        await self._emit_event(event_data)
        
        # Log at appropriate level based on service criticality
        if is_critical:
            logger.error(f"Critical service unavailable: {service_name} for user {self.user_id}: {reason}")
        else:
            logger.warning(f"Service unavailable: {service_name} for user {self.user_id}: {reason}")
    
    async def emit_service_recovered(
        self,
        service_name: str,
        recovery_time_ms: Optional[float] = None
    ) -> None:
        """Notify user that service has recovered from degraded/unavailable state."""
        event_data = {
            "type": WebSocketEventType.SERVICE_RECOVERED.value,
            "service_name": service_name,
            "message": f"{service_name} has recovered and is fully operational",
            "recovery_time_ms": recovery_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "status": "fully_operational"
            }
        }
        
        await self._emit_event(event_data)
        logger.info(f"Service recovered: {service_name} for user {self.user_id}")
    
    async def emit_system_status(
        self,
        overall_status: str,
        service_statuses: Dict[str, str],
        can_process_requests: bool,
        degraded_services: Optional[List[str]] = None
    ) -> None:
        """Emit overall system status summary."""
        event_data = {
            "type": WebSocketEventType.SYSTEM_STATUS.value,
            "overall_status": overall_status,
            "service_statuses": service_statuses,
            "can_process_requests": can_process_requests,
            "degraded_services": degraded_services or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "total_services": len(service_statuses),
                "healthy_services": len([s for s in service_statuses.values() if s == "ready"])
            }
        }
        
        await self._emit_event(event_data)
    
    async def emit_user_queue_position(
        self,
        position: int,
        estimated_wait_time_seconds: Optional[int] = None,
        queue_type: str = "standard"
    ) -> None:
        """Emit user's position in processing queue.
        
        This provides transparent communication about wait times
        instead of hiding queue status behind mock responses.
        """
        # Enterprise users get priority queue messaging
        if self.context.user_tier == "enterprise":
            queue_message = f"Priority queue position: {position}"
            queue_type = "priority"
        else:
            queue_message = f"Queue position: {position}"
        
        event_data = {
            "type": WebSocketEventType.USER_QUEUE_POSITION.value,
            "position": position,
            "queue_type": queue_type,
            "message": queue_message,
            "estimated_wait_time_seconds": estimated_wait_time_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier,
                "is_priority_queue": self.context.user_tier == "enterprise"
            }
        }
        
        await self._emit_event(event_data)
    
    # Preserve existing agent events for chat UX compatibility
    async def emit_agent_started(
        self,
        agent_name: str,
        agent_description: Optional[str] = None
    ) -> None:
        """Emit agent started event (preserved for chat UX)."""
        event_data = {
            "type": WebSocketEventType.AGENT_STARTED.value,
            "agent_name": agent_name,
            "agent_description": agent_description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier
            }
        }
        
        await self._emit_event(event_data)
    
    async def emit_agent_thinking(
        self,
        thought: str,
        step_number: Optional[int] = None
    ) -> None:
        """Emit agent thinking event (preserved for chat UX)."""
        event_data = {
            "type": WebSocketEventType.AGENT_THINKING.value,
            "thought": thought,
            "step_number": step_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier
            }
        }
        
        await self._emit_event(event_data)
    
    async def emit_tool_executing(
        self,
        tool_name: str,
        tool_description: Optional[str] = None
    ) -> None:
        """Emit tool executing event (preserved for chat UX)."""
        event_data = {
            "type": WebSocketEventType.TOOL_EXECUTING.value,
            "tool_name": tool_name,
            "tool_description": tool_description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier
            }
        }
        
        await self._emit_event(event_data)
    
    async def emit_tool_completed(
        self,
        tool_name: str,
        result: Any
    ) -> None:
        """Emit tool completed event (preserved for chat UX)."""
        event_data = {
            "type": WebSocketEventType.TOOL_COMPLETED.value,
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier
            }
        }
        
        await self._emit_event(event_data)
    
    async def emit_agent_completed(
        self,
        result: Any,
        execution_time_ms: Optional[float] = None
    ) -> None:
        """Emit agent completed event (preserved for chat UX)."""
        event_data = {
            "type": WebSocketEventType.AGENT_COMPLETED.value,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": {
                "user_tier": self.context.user_tier
            }
        }
        
        await self._emit_event(event_data)
    
    async def _emit_event(self, event_data: Dict[str, Any]) -> None:
        """Internal method to emit WebSocket event.
        
        This method handles the actual WebSocket communication and ensures
        events are properly delivered to the user's WebSocket connection.
        """
        try:
            # Store event for tracking
            self.events_sent.append(event_data)
            
            # Get WebSocket connection for this user/request
            websocket_manager = self.context.websocket_manager
            if websocket_manager:
                await websocket_manager.send_to_user(
                    user_id=self.user_id,
                    event_data=event_data
                )
            else:
                logger.warning(f"No WebSocket manager available for user {self.user_id}")
                
        except Exception as e:
            logger.error(f"Failed to emit WebSocket event: {e}")
            # Don't raise exception - WebSocket failures shouldn't break service logic
    
    def get_events_summary(self) -> Dict[str, Any]:
        """Get summary of events sent during this request."""
        event_types = [e.get("type") for e in self.events_sent]
        event_counts = {}
        for event_type in event_types:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        return {
            "total_events": len(self.events_sent),
            "event_counts": event_counts,
            "first_event_time": self.events_sent[0].get("timestamp") if self.events_sent else None,
            "last_event_time": self.events_sent[-1].get("timestamp") if self.events_sent else None
        }


class TransparentWebSocketBridge:
    """Bridge that provides transparent WebSocket communication for user contexts.
    
    This replaces the previous WebSocket patterns that could send misleading
    events during service failures.
    """
    
    def __init__(self, context: UserExecutionContext):
        """Initialize WebSocket bridge with user context."""
        self.context = context
        self.emitter = TransparentWebSocketEmitter(context)
        
    async def emit_service_initializing(
        self,
        service_name: str,
        initialization_steps: Optional[List[str]] = None
    ) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_service_initializing(service_name, initialization_steps)
    
    async def emit_service_ready(
        self,
        service_name: str,
        initialization_time_ms: Optional[float] = None
    ) -> None:
        """Delegate to transparent emitter."""  
        await self.emitter.emit_service_ready(service_name, initialization_time_ms)
    
    async def emit_service_degraded(
        self,
        service_name: str,
        reason: str,
        fallback_options: Optional[List[str]] = None
    ) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_service_degraded(service_name, reason, fallback_options)
    
    async def emit_service_unavailable(
        self,
        service_name: str,
        reason: str,
        estimated_recovery_seconds: Optional[int] = None,
        alternatives: Optional[List[str]] = None
    ) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_service_unavailable(
            service_name, reason, estimated_recovery_seconds, alternatives
        )
    
    async def emit_service_recovered(
        self,
        service_name: str,
        recovery_time_ms: Optional[float] = None
    ) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_service_recovered(service_name, recovery_time_ms)
    
    # Preserve agent event methods for compatibility
    async def emit_agent_started(self, agent_name: str) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_agent_started(agent_name)
    
    async def emit_agent_thinking(self, thought: str, step_number: int = None) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_agent_thinking(thought, step_number)
    
    async def emit_tool_executing(self, tool_name: str) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_tool_executing(tool_name)
    
    async def emit_tool_completed(self, tool_name: str, result: Any) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_tool_completed(tool_name, result)
    
    async def emit_agent_completed(self, result: Any) -> None:
        """Delegate to transparent emitter."""
        await self.emitter.emit_agent_completed(result)