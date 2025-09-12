"""DEPRECATED - REDIRECTED TO SSOT: UnifiedWebSocketEmitter

This module has been converted to redirect to the SSOT UnifiedWebSocketEmitter.
All functionality is now provided by netra_backend.app.websocket_core.unified_emitter.

Business Value Justification:
- Segment: Platform/Internal (Migration phase)
- Business Goal: SSOT Compliance & System Reliability
- Value Impact: Reduces code duplication and improves maintainability
- Strategic Impact: Consolidates WebSocket emitter implementations into single source

## MIGRATION STATUS: PHASE 1 COMPLETE
- All methods redirect to UnifiedWebSocketEmitter
- Backward compatibility maintained
- Performance optimization inherited from SSOT implementation
- No breaking changes for existing consumers

OLD IMPLEMENTATION REPLACED BY: UnifiedWebSocketEmitter
"""

# SSOT REDIRECT: Import the unified implementation
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = central_logger.get_logger(__name__)


class UserWebSocketEmitter:
    """LEGACY COMPATIBILITY WRAPPER - Redirects to UnifiedWebSocketEmitter
    
    This class maintains backward compatibility while redirecting all functionality
    to the SSOT UnifiedWebSocketEmitter implementation. This ensures no breaking
    changes for existing code while consolidating to a single emitter implementation.
    
    Business Value: Maintains existing integrations while enabling SSOT benefits.
    """
    
    def __init__(self, context: UserExecutionContext, router: WebSocketEventRouter, 
                 connection_id: Optional[str] = None):
        """Initialize compatibility wrapper around UnifiedWebSocketEmitter.
        
        Args:
            context: User execution context with validated IDs
            router: WebSocket event router for infrastructure
            connection_id: Optional specific connection ID to target
        """
        logger.info(f" CYCLE:  UserWebSocketEmitter redirecting to UnifiedWebSocketEmitter for user {context.user_id[:8]}...")
        
        # Get the WebSocket manager from the router
        websocket_manager = getattr(router, 'websocket_manager', None)
        if not websocket_manager:
            raise ValueError("WebSocketEventRouter must have websocket_manager for SSOT integration")
        
        # Create the SSOT emitter with backward compatibility
        self._unified_emitter = UnifiedWebSocketEmitter(
            manager=websocket_manager,
            user_id=context.user_id,
            context=context
        )
        
        # Store legacy attributes for compatibility
        self.user_id = context.user_id
        self.thread_id = context.thread_id
        self.run_id = context.run_id
        self.request_id = context.request_id
        self.connection_id = connection_id
        self.router = router
        
        # Event tracking for debugging and metrics (delegated to SSOT)
        self.events_sent = 0
        self.events_failed = 0
        self.created_at = datetime.now(timezone.utc)
        
        logger.info(f" PASS:  UserWebSocketEmitter  ->  UnifiedWebSocketEmitter redirect complete for user {self.user_id[:8]}...")
    
    async def notify_agent_started(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent started event via SSOT emitter."""
        try:
            await self._unified_emitter.emit_agent_started({
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} has started processing your request"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for agent_started: {e}")
            return False
    
    async def notify_agent_thinking(self, agent_name: str, thought: str, 
                                  step: Optional[str] = None) -> bool:
        """Send thinking event via SSOT emitter."""
        try:
            await self._unified_emitter.emit_agent_thinking({
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "thought": thought,
                "step": step,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} is analyzing: {thought[:100]}..."
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for agent_thinking: {e}")
            return False
    
    async def notify_tool_executing(self, agent_name: str, tool_name: str, 
                                  tool_input: Optional[Dict[str, Any]] = None) -> bool:
        """Send tool execution event via SSOT emitter."""
        try:
            await self._unified_emitter.emit_tool_executing({
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "tool_name": tool_name,
                "tool_input": self._sanitize_tool_input(tool_input) if tool_input else {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} is using {tool_name}"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for tool_executing: {e}")
            return False
    
    async def notify_tool_completed(self, agent_name: str, tool_name: str, 
                                  success: bool, result_summary: Optional[str] = None) -> bool:
        """Send tool completion event via SSOT emitter."""
        try:
            await self._unified_emitter.emit_tool_completed({
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "tool_name": tool_name,
                "success": success,
                "result_summary": result_summary,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} {'completed' if success else 'failed to complete'} {tool_name}"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for tool_completed: {e}")
            return False
    
    async def notify_agent_completed(self, agent_name: str, result: Dict[str, Any], 
                                   success: bool = True) -> bool:
        """Send agent completion event via SSOT emitter."""
        try:
            await self._unified_emitter.emit_agent_completed({
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "success": success,
                "result": self._sanitize_agent_result(result),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} has {'completed' if success else 'failed'} processing your request"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for agent_completed: {e}")
            return False
    
    async def notify_agent_error(self, agent_name: str, error_type: str, 
                               error_message: str, recoverable: bool = False) -> bool:
        """Send agent error event via SSOT emitter."""
        try:
            await self._unified_emitter.emit("agent_error", {
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "error_type": error_type,
                "error_message": error_message,
                "recoverable": recoverable,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name} encountered an error: {error_message}"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for agent_error: {e}")
            return False
    
    async def notify_progress_update(self, agent_name: str, progress_percentage: float, 
                                   current_step: str, estimated_completion: Optional[str] = None) -> bool:
        """Send progress update event via SSOT emitter."""
        try:
            await self._unified_emitter.emit("progress_update", {
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "progress_percentage": min(100, max(0, progress_percentage)),
                "current_step": current_step,
                "estimated_completion": estimated_completion,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"{agent_name}: {current_step} ({progress_percentage:.1f}% complete)"
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for progress_update: {e}")
            return False
    
    async def notify_custom(self, event_type: str, payload: Dict[str, Any], 
                          agent_name: Optional[str] = None) -> bool:
        """Send custom event via SSOT emitter."""
        try:
            await self._unified_emitter.emit(event_type, {
                "agent_name": agent_name,
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **payload
            })
            self.events_sent += 1
            return True
        except Exception as e:
            self.events_failed += 1
            logger.error(f" ALERT:  SSOT redirect failed for {event_type}: {e}")
            return False
    
    # Statistics and debugging methods (delegated to SSOT)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics (includes SSOT metrics)."""
        ssot_metrics = self._unified_emitter.get_stats()
        
        # Merge legacy and SSOT stats
        uptime = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        success_rate = (
            self.events_sent / (self.events_sent + self.events_failed) * 100
            if (self.events_sent + self.events_failed) > 0 else 0
        )
        
        return {
            **ssot_metrics,
            "user_id": self.user_id[:8] + "...",  # Truncated for security
            "run_id": self.run_id,
            "events_sent": self.events_sent,
            "events_failed": self.events_failed,
            "success_rate": success_rate,
            "uptime_seconds": uptime,
            "connection_id": self.connection_id,
            "ssot_redirect": True,
            "emitter_type": "UserWebSocketEmitter  ->  UnifiedWebSocketEmitter"
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"UserWebSocketEmitter -> SSOT(user={self.user_id[:8]}..., run_id={self.run_id})"
    
    # Private helper methods (preserved for compatibility)
    
    def _sanitize_tool_input(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool input for user-facing events."""
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
        """Sanitize agent results for user consumption."""
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