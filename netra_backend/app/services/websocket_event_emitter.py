"""
WebSocketEventEmitter - Per-Request WebSocket Event Emission

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Isolation 
- Value Impact: Eliminates user isolation issues in WebSocket events, prevents cross-user leakage
- Strategic Impact: Enables proper per-request scoped WebSocket notifications without global state

This module provides a per-request WebSocketEventEmitter that replaces the singleton 
AgentWebSocketBridge pattern to ensure complete user isolation for WebSocket events.

Key Architecture Principles:
- Per-request isolation (NOT singleton)
- Bound to specific UserExecutionContext
- Uses WebSocketManager as connection pool
- Thread-safe with no shared global state
- Comprehensive error handling and logging
- Async context manager support for proper cleanup

The WebSocketEventEmitter follows SSOT principles and provides the same interface
as AgentWebSocketBridge but with proper request-scoped isolation.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.manager import WebSocketManager

if TYPE_CHECKING:
    # Import UserExecutionContext under TYPE_CHECKING to break circular imports
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)

# Runtime import function to break circular dependencies
def get_user_execution_context_class():
    """Import UserExecutionContext at runtime to break circular imports."""
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    return UserExecutionContext


class WebSocketEventEmitter:
    """
    Per-request WebSocket event emitter for user-isolated notifications.
    
    This class provides WebSocket event emission scoped to a specific user execution
    context, ensuring complete isolation between users and preventing the singleton
    pattern issues found in AgentWebSocketBridge.
    
    Key Features:
    - Bound to UserExecutionContext for complete isolation
    - Uses WebSocketManager as a connection pool (doesn't own connections)
    - Thread-safe with no global state
    - Comprehensive logging and error handling
    - Async context manager support for proper lifecycle
    - Compatible interface with existing AgentWebSocketBridge usage
    
    Business Value:
    - Prevents cross-user WebSocket event leakage
    - Enables reliable per-request WebSocket notifications  
    - Maintains chat functionality while ensuring user privacy
    - Eliminates race conditions from singleton pattern
    """
    
    def __init__(
        self,
        user_context: 'UserExecutionContext',
        websocket_manager: WebSocketManager
    ):
        """
        Initialize per-request WebSocket event emitter.
        
        Args:
            user_context: Immutable user execution context for this request
            websocket_manager: WebSocket manager instance (connection pool)
            
        Raises:
            ValueError: If user_context or websocket_manager is invalid
        """
        # Validate inputs with comprehensive error handling using runtime import
        UserExecutionContext = get_user_execution_context_class()
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError(f"user_context must be UserExecutionContext, got {type(user_context)}")
        
        if not websocket_manager:
            raise ValueError("websocket_manager cannot be None")
        
        if not hasattr(websocket_manager, 'send_to_thread'):
            raise ValueError("websocket_manager missing required 'send_to_thread' method")
        
        # Store immutable context and connection pool reference
        self._user_context = user_context
        self._websocket_manager = websocket_manager
        self._created_at = datetime.now(timezone.utc)
        self._disposed = False
        
        # Per-request metrics
        self._metrics = {
            'events_sent': 0,
            'events_failed': 0,
            'last_event_time': None,
            'created_at': self._created_at,
            'context_id': user_context.get_correlation_id()
        }
        
        logger.debug(f"📡 EMITTER CREATED: {self._get_log_prefix()} - bound to context")
        
        # Verify user context integrity
        try:
            user_context.verify_isolation()
            logger.debug(f"✅ ISOLATION VERIFIED: {self._get_log_prefix()}")
        except Exception as e:
            logger.error(f"🚨 ISOLATION VIOLATION: {self._get_log_prefix()} - {e}")
            raise ValueError(f"User context failed isolation verification: {e}")
    
    def _get_log_prefix(self) -> str:
        """Get consistent logging prefix for this emitter instance."""
        return f"[{self._user_context.get_correlation_id()}]"
    
    def _ensure_not_disposed(self) -> None:
        """Ensure emitter hasn't been disposed."""
        if self._disposed:
            raise RuntimeError(f"WebSocketEventEmitter {self._get_log_prefix()} has been disposed")
    
    async def _emit_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Core event emission with comprehensive error handling.
        
        Args:
            event_type: Type of event being emitted
            event_data: Event payload data
            
        Returns:
            bool: True if event was successfully queued/sent
        """
        self._ensure_not_disposed()
        
        try:
            # Add standard event metadata
            standardized_event = {
                "type": event_type,
                "run_id": self._user_context.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event_data
            }
            
            # CRYSTAL CLEAR EMISSION PATH: Context → WebSocket Manager → User Chat
            success = await self._websocket_manager.send_to_thread(
                self._user_context.thread_id, 
                standardized_event
            )
            
            # Update metrics
            self._metrics['last_event_time'] = datetime.now(timezone.utc)
            if success:
                self._metrics['events_sent'] += 1
                logger.debug(f"✅ EVENT EMITTED: {self._get_log_prefix()} {event_type} → thread={self._user_context.thread_id}")
            else:
                self._metrics['events_failed'] += 1
                logger.error(f"🚨 EVENT FAILED: {self._get_log_prefix()} {event_type} send failed")
            
            return success
            
        except Exception as e:
            self._metrics['events_failed'] += 1
            logger.error(f"🚨 EVENT EXCEPTION: {self._get_log_prefix()} {event_type} failed: {e}")
            return False
    
    # ===================== STANDARD AGENT EVENT METHODS =====================
    # These methods provide the same interface as AgentWebSocketBridge
    
    async def notify_agent_started(
        self, 
        run_id: str, 
        agent_name: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send agent started notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of the agent starting
            context: Optional context data
            
        Returns:
            bool: True if notification sent successfully
        """
        # Validate run_id matches our context for security
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "status": "started",
                "context": context or {},
                "message": f"{agent_name} has started processing your request"
            }
        }
        
        success = await self._emit_event("agent_started", event_data)
        if success:
            logger.info(f"🚀 AGENT STARTED: {self._get_log_prefix()} {agent_name}")
        
        return success
    
    async def notify_agent_thinking(
        self, 
        run_id: str, 
        agent_name: str, 
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """
        Send agent thinking notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of the thinking agent
            reasoning: Agent's reasoning process
            step_number: Optional step number
            progress_percentage: Optional progress percentage
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "reasoning": reasoning,
                "step_number": step_number,
                "progress_percentage": progress_percentage,
                "status": "thinking"
            }
        }
        
        success = await self._emit_event("agent_thinking", event_data)
        if success:
            logger.debug(f"🧠 AGENT THINKING: {self._get_log_prefix()} {agent_name}")
        
        return success
    
    async def notify_tool_executing(
        self, 
        run_id: str, 
        agent_name: str, 
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send tool execution notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of agent executing tool
            tool_name: Name of tool being executed
            parameters: Optional tool parameters (sanitized)
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "tool_name": tool_name,
                "parameters": self._sanitize_parameters(parameters) if parameters else {},
                "status": "executing",
                "message": f"{agent_name} is using {tool_name}"
            }
        }
        
        success = await self._emit_event("tool_executing", event_data)
        if success:
            logger.debug(f"🔧 TOOL EXECUTING: {self._get_log_prefix()} {tool_name}")
        
        return success
    
    async def notify_tool_completed(
        self, 
        run_id: str, 
        agent_name: str, 
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """
        Send tool completion notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of agent that completed tool
            tool_name: Name of completed tool
            result: Optional tool results (sanitized)
            execution_time_ms: Optional execution time
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "tool_name": tool_name,
                "result": self._sanitize_result(result) if result else {},
                "execution_time_ms": execution_time_ms,
                "status": "completed",
                "message": f"{agent_name} completed {tool_name}"
            }
        }
        
        success = await self._emit_event("tool_completed", event_data)
        if success:
            logger.debug(f"✅ TOOL COMPLETED: {self._get_log_prefix()} {tool_name}")
        
        return success
    
    async def notify_agent_completed(
        self, 
        run_id: str, 
        agent_name: str, 
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """
        Send agent completion notification.
        
        Args:
            run_id: Run identifier (must match context run_id) 
            agent_name: Name of completed agent
            result: Optional agent results (sanitized)
            execution_time_ms: Optional execution time
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "status": "completed",
                "result": self._sanitize_result(result) if result else {},
                "execution_time_ms": execution_time_ms,
                "message": f"{agent_name} has completed processing your request"
            }
        }
        
        success = await self._emit_event("agent_completed", event_data)
        if success:
            logger.info(f"🎉 AGENT COMPLETED: {self._get_log_prefix()} {agent_name}")
        
        return success
    
    async def notify_agent_error(
        self, 
        run_id: str, 
        agent_name: str, 
        error: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send agent error notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of agent with error
            error: Error message (sanitized)
            error_context: Optional error context (sanitized)
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "status": "error",
                "error_message": self._sanitize_error_message(error),
                "error_context": self._sanitize_error_context(error_context) if error_context else {},
                "message": f"{agent_name} encountered an issue processing your request"
            }
        }
        
        success = await self._emit_event("agent_error", event_data)
        if success:
            logger.warning(f"⚠️ AGENT ERROR: {self._get_log_prefix()} {agent_name}")
        
        return success
    
    async def notify_progress_update(
        self, 
        run_id: str, 
        agent_name: str, 
        progress: Dict[str, Any]
    ) -> bool:
        """
        Send agent progress update notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of agent reporting progress
            progress: Progress data
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": {
                "status": "progress",
                "progress_data": self._sanitize_progress_data(progress),
                "message": progress.get("message", f"{agent_name} is making progress")
            }
        }
        
        success = await self._emit_event("progress_update", event_data)
        if success:
            logger.debug(f"📊 PROGRESS UPDATE: {self._get_log_prefix()} {agent_name}")
        
        return success
    
    async def notify_custom(
        self, 
        run_id: str, 
        agent_name: str, 
        notification_type: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Send custom notification.
        
        Args:
            run_id: Run identifier (must match context run_id)
            agent_name: Name of agent sending notification
            notification_type: Custom notification type
            data: Custom notification data
            
        Returns:
            bool: True if notification sent successfully
        """
        if run_id != self._user_context.run_id:
            logger.error(f"🚨 RUN_ID MISMATCH: {self._get_log_prefix()} expected {self._user_context.run_id}, got {run_id}")
            return False
        
        event_data = {
            "agent_name": agent_name,
            "payload": self._sanitize_custom_data(data)
        }
        
        success = await self._emit_event(notification_type, event_data)
        if success:
            logger.debug(f"📨 CUSTOM EVENT: {self._get_log_prefix()} {notification_type}")
        
        return success
    
    # ===================== SANITIZATION METHODS =====================
    
    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool parameters for user display."""
        if not params:
            return {}
        
        sanitized = {}
        sensitive_keys = {'password', 'secret', 'key', 'token', 'api_key', 'auth', 'credential'}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_parameters(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool results for user display."""
        if not result:
            return {}
        
        sanitized = {}
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_result(value)
            elif isinstance(value, list) and len(value) > 10:
                sanitized[key] = value[:10] + ["...(truncated)"]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_error_message(self, error: str) -> str:
        """Sanitize error message for user display."""
        if not error:
            return "An error occurred"
        
        # Remove file paths and internal details
        sanitized = error.replace("/Users/", "/home/").replace("/home/", "[PATH]/")
        
        # Truncate very long errors
        if len(sanitized) > 300:
            sanitized = sanitized[:300] + "..."
        
        return sanitized
    
    def _sanitize_error_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize error context for user display."""
        if not context:
            return {}
        
        return {
            "error_type": context.get("error_type", "unknown"),
            "agent_step": context.get("agent_step", "unknown"),
            "user_facing": True
        }
    
    def _sanitize_progress_data(self, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize progress data for user display."""
        if not progress:
            return {}
        
        sanitized = {}
        allowed_keys = {
            'percentage', 'current_step', 'total_steps', 'message', 
            'status', 'estimated_remaining', 'progress_type'
        }
        
        for key, value in progress.items():
            if key in allowed_keys:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_custom_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize custom notification data for user display."""
        if not data:
            return {}
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_custom_data(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    # ===================== LIFECYCLE AND METRICS METHODS =====================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get emitter metrics for monitoring."""
        self._ensure_not_disposed()
        
        now = datetime.now(timezone.utc)
        uptime = (now - self._created_at).total_seconds()
        
        return {
            **self._metrics,
            'uptime_seconds': uptime,
            'success_rate': (
                self._metrics['events_sent'] / 
                max(1, self._metrics['events_sent'] + self._metrics['events_failed'])
            ),
            'user_context': self._user_context.to_dict(),
            'disposed': self._disposed
        }
    
    def get_context(self) -> 'UserExecutionContext':
        """Get the bound user execution context."""
        return self._user_context
    
    async def dispose(self) -> None:
        """
        Dispose of the emitter and clean up resources.
        
        This method should be called when the emitter is no longer needed
        to ensure proper cleanup and prevent memory leaks.
        """
        if self._disposed:
            return
        
        logger.debug(f"🗑️ EMITTER DISPOSING: {self._get_log_prefix()}")
        
        # Mark as disposed to prevent further usage
        self._disposed = True
        
        # Clear references 
        self._websocket_manager = None
        
        logger.debug(f"✅ EMITTER DISPOSED: {self._get_log_prefix()}")
    
    async def __aenter__(self) -> 'WebSocketEventEmitter':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.dispose()


class WebSocketEventEmitterFactory:
    """
    Factory for creating WebSocketEventEmitter instances with proper dependencies.
    
    This factory handles the creation of WebSocketEventEmitter instances with
    proper dependency injection and validation, ensuring consistent creation
    patterns across the application.
    
    Business Value:
    - Ensures consistent WebSocketEventEmitter creation
    - Handles dependency validation and injection
    - Provides clear factory pattern for better testing
    - Enables easier mocking and test isolation
    """
    
    @staticmethod
    async def create_emitter(
        user_context: 'UserExecutionContext',
        websocket_manager: Optional[WebSocketManager] = None
    ) -> WebSocketEventEmitter:
        """
        Create a WebSocketEventEmitter for the given user context.
        
        Args:
            user_context: User execution context to bind emitter to
            websocket_manager: Optional WebSocket manager (uses default if None)
            
        Returns:
            Configured WebSocketEventEmitter instance
            
        Raises:
            ValueError: If dependencies are invalid or unavailable
        """
        # Import here to avoid circular imports
        from netra_backend.app.websocket_core.manager import get_websocket_manager
        
        # Get WebSocket manager if not provided
        if websocket_manager is None:
            try:
                websocket_manager = get_websocket_manager()
            except Exception as e:
                logger.error(f"🚨 FACTORY ERROR: Failed to get WebSocket manager: {e}")
                raise ValueError(f"Failed to get WebSocket manager: {e}")
        
        # Create emitter
        try:
            emitter = WebSocketEventEmitter(user_context, websocket_manager)
            logger.info(f"🏭 EMITTER CREATED: {emitter._get_log_prefix()} via factory")
            return emitter
        except Exception as e:
            logger.error(f"🚨 FACTORY ERROR: Failed to create emitter: {e}")
            raise ValueError(f"Failed to create WebSocketEventEmitter: {e}")
    
    @staticmethod
    @asynccontextmanager
    async def create_scoped_emitter(
        user_context: 'UserExecutionContext',
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Create a scoped WebSocketEventEmitter with automatic cleanup.
        
        This is the recommended way to create emitters as it ensures proper
        resource cleanup even if exceptions occur.
        
        Args:
            user_context: User execution context to bind emitter to
            websocket_manager: Optional WebSocket manager
            
        Yields:
            WebSocketEventEmitter: Configured emitter with automatic cleanup
            
        Example:
            async with WebSocketEventEmitterFactory.create_scoped_emitter(context) as emitter:
                await emitter.notify_agent_started(run_id, "MyAgent")
                # Automatic cleanup happens here
        """
        emitter = None
        try:
            emitter = await WebSocketEventEmitterFactory.create_emitter(
                user_context, websocket_manager
            )
            logger.debug(f"📦 SCOPED EMITTER: {emitter._get_log_prefix()} created with auto-cleanup")
            yield emitter
        finally:
            if emitter:
                await emitter.dispose()
                logger.debug(f"📦 SCOPED EMITTER: {emitter._get_log_prefix()} disposed")


# ===================== CONVENIENCE FUNCTIONS =====================

async def create_websocket_event_emitter(
    user_context: 'UserExecutionContext',
    websocket_manager: Optional[WebSocketManager] = None
) -> WebSocketEventEmitter:
    """
    Convenience function to create a WebSocketEventEmitter.
    
    Args:
        user_context: User execution context
        websocket_manager: Optional WebSocket manager
        
    Returns:
        WebSocketEventEmitter instance
    """
    return await WebSocketEventEmitterFactory.create_emitter(
        user_context, websocket_manager
    )


@asynccontextmanager
async def websocket_event_emitter_scope(
    user_context: 'UserExecutionContext',
    websocket_manager: Optional[WebSocketManager] = None
):
    """
    Convenience async context manager for scoped WebSocketEventEmitter.
    
    Args:
        user_context: User execution context
        websocket_manager: Optional WebSocket manager
        
    Yields:
        WebSocketEventEmitter with automatic cleanup
    """
    async with WebSocketEventEmitterFactory.create_scoped_emitter(
        user_context, websocket_manager
    ) as emitter:
        yield emitter