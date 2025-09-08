"""
WebSocket-specific exceptions for Phase 1 remediation foundation.

These exceptions provide structured error handling for WebSocket event emissions
and notifications, enabling progression from warnings to errors while preserving
business value and user experience.

Business Value:
- Protects critical chat UX WebSocket events (agent_started, agent_thinking, etc.)
- Enables progressive error escalation (dev warnings -> staging errors -> prod failures)
- Provides diagnostic context for WebSocket troubleshooting
- Maintains backward compatibility during Phase 1 foundation
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class WebSocketEventEmissionError(NetraException):
    """
    Exception for WebSocket event emission failures.
    
    Covers critical agent events: agent_started, agent_completed, agent_error.
    These are essential for user chat experience and business value delivery.
    
    Business Impact: Failed events = degraded chat UX = reduced user satisfaction
    Recovery Guidance: Check WebSocket connection health, retry with backoff
    """
    
    def __init__(
        self,
        event_type: str,
        agent_name: str = None,
        run_id: str = None,
        original_error: Exception = None,
        context: Optional[Dict[str, Any]] = None
    ):
        # Build diagnostic context
        error_context = context or {}
        error_context.update({
            "event_type": event_type,
            "agent_name": agent_name,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_error_type": type(original_error).__name__ if original_error else None,
            "original_error_message": str(original_error) if original_error else None
        })
        
        # Build business-focused error message
        business_message = f"Critical WebSocket event '{event_type}' emission failed"
        if agent_name:
            business_message += f" for agent '{agent_name}'"
        if run_id:
            business_message += f" (run_id: {run_id})"
        
        # Recovery guidance
        user_message = (
            f"Agent event notification failed. This may impact real-time updates in your chat. "
            f"The agent execution continues normally, but you may not see live progress updates."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            severity=ErrorSeverity.HIGH,  # HIGH because it impacts user experience
            details={"recovery_actions": [
                "Check WebSocket connection health",
                "Verify agent_websocket_bridge is initialized", 
                "Check network connectivity",
                "Retry operation with exponential backoff"
            ]},
            user_message=user_message,
            context=error_context
        )


class WebSocketNotificationError(NetraException):
    """
    Exception for general WebSocket notification failures.
    
    Covers non-critical notifications that enhance UX but don't block core functionality.
    
    Business Impact: Reduced visibility into system operations
    Recovery Guidance: Log for monitoring, continue operation
    """
    
    def __init__(
        self,
        notification_type: str,
        message: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "notification_type": notification_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        business_message = message or f"WebSocket notification '{notification_type}' failed"
        
        super().__init__(
            message=business_message,
            code=ErrorCode.WEBSOCKET_MESSAGE_INVALID,
            severity=ErrorSeverity.MEDIUM,  # MEDIUM because it doesn't block core functionality
            details={"recovery_actions": [
                "Log for monitoring and analysis",
                "Continue operation without notification",
                "Check WebSocket message format validation"
            ]},
            context=error_context
        )


class WebSocketAgentEventError(NetraException):
    """
    Exception for agent-specific WebSocket event failures.
    
    Critical for agent execution visibility: tool_executing, tool_completed, agent_thinking.
    These events are essential for demonstrating AI value to users.
    
    Business Impact: Users can't see AI working = perceived system failure
    Recovery Guidance: Critical event failure requires immediate attention
    """
    
    def __init__(
        self,
        event_type: str,
        agent_name: str,
        execution_phase: str = None,
        run_id: str = None,
        tool_name: str = None,
        original_error: Exception = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "event_type": event_type,
            "agent_name": agent_name,
            "execution_phase": execution_phase,
            "run_id": run_id,
            "tool_name": tool_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_impact": "high_user_experience_degradation"
        })
        
        business_message = f"Critical agent event '{event_type}' failed for '{agent_name}'"
        if execution_phase:
            business_message += f" during {execution_phase}"
        
        user_message = (
            f"Unable to show real-time progress for your AI agent. "
            f"Your request is still being processed, but live updates are unavailable."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.AGENT_EXECUTION_FAILED,
            severity=ErrorSeverity.CRITICAL,  # CRITICAL because it impacts core business value
            details={
                "business_impact": "Users cannot see AI value being delivered",
                "recovery_actions": [
                    "Immediate WebSocket health check required",
                    "Verify AgentWebSocketBridge initialization",
                    "Check agent execution context integrity",
                    "Escalate to on-call if persistent"
                ]
            },
            user_message=user_message,
            context=error_context
        )


class WebSocketEventValidationError(NetraException):
    """
    Exception for WebSocket event validation failures.
    
    Covers malformed events, invalid payloads, and protocol violations.
    
    Business Impact: System reliability and data integrity
    Recovery Guidance: Validate event structure, check serialization
    """
    
    def __init__(
        self,
        validation_error: str,
        event_data: Dict[str, Any] = None,
        expected_schema: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "validation_error": validation_error,
            "event_data_keys": list(event_data.keys()) if event_data else None,
            "expected_schema": expected_schema,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        business_message = f"WebSocket event validation failed: {validation_error}"
        
        super().__init__(
            message=business_message,
            code=ErrorCode.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details={
                "recovery_actions": [
                    "Validate event payload structure",
                    "Check event serialization logic",
                    "Verify WebSocket message protocol compliance",
                    "Review event schema definitions"
                ]
            },
            context=error_context
        )