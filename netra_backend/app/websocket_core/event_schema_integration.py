"""
WebSocket Event Schema Integration - Production Bridge for Issue #984 Fix

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Bridge unified schema to production WebSocket infrastructure  
- Value Impact: Ensures production events match test expectations (Issue #984 fix)
- Strategic Impact: Prevents schema drift between test/production environments

CRITICAL: This module bridges the unified event schema (SSOT) with the existing
WebSocket manager infrastructure to ensure production events contain the required
tool_name and results fields that were missing in Issue #984.

Architecture: Event creation adapter that wraps production WebSocket manager calls
with unified schema generation to maintain consistency.
"""

import time
from typing import Dict, Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.event_schema import (
    create_agent_started_event,
    create_agent_thinking_event,
    create_tool_executing_event,
    create_tool_completed_event,
    create_agent_completed_event,
    create_error_event,
    validate_event_schema
)

logger = central_logger.get_logger(__name__)


class WebSocketEventAdapter:
    """
    Adapter that creates production WebSocket events using unified schema.
    
    This adapter ensures all WebSocket events sent by the production system
    conform to the unified schema, preventing Issue #984 from recurring.
    """
    
    def __init__(self, websocket_manager=None):
        """Initialize adapter with WebSocket manager."""
        self.websocket_manager = websocket_manager
        self.schema_validation_enabled = True
        self.events_sent = 0
        self.validation_errors = []
    
    async def send_agent_started(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str,
        message: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send agent_started event with unified schema."""
        try:
            # Create event using unified schema
            event = create_agent_started_event(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                message=message,
                **kwargs
            )
            
            # Validate event against schema
            if self.schema_validation_enabled:
                errors = validate_event_schema(event, "agent_started")
                if errors:
                    self.validation_errors.extend(errors)
                    logger.error(f"agent_started schema validation failed: {errors}")
                    return False
            
            # Send via WebSocket manager
            success = await self._emit_event(user_id, event)
            if success:
                self.events_sent += 1
                logger.debug(f"agent_started event sent successfully for {agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send agent_started event: {e}")
            return False
    
    async def send_agent_thinking(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str,
        thought: Optional[str] = None,
        reasoning: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send agent_thinking event with unified schema."""
        try:
            # Create event using unified schema
            event = create_agent_thinking_event(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                thought=thought,
                reasoning=reasoning,
                **kwargs
            )
            
            # Validate event against schema
            if self.schema_validation_enabled:
                errors = validate_event_schema(event, "agent_thinking")
                if errors:
                    self.validation_errors.extend(errors)
                    logger.error(f"agent_thinking schema validation failed: {errors}")
                    return False
            
            # Send via WebSocket manager
            success = await self._emit_event(user_id, event)
            if success:
                self.events_sent += 1
                logger.debug(f"agent_thinking event sent successfully for {agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send agent_thinking event: {e}")
            return False
    
    async def send_tool_executing(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str,
        tool_name: str,  # CRITICAL: Required field (Issue #984 fix)
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """Send tool_executing event with unified schema - Issue #984 fix."""
        try:
            # Create event using unified schema
            event = create_tool_executing_event(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                tool_name=tool_name,  # CRITICAL: Required field (Issue #984 fix)
                parameters=parameters,
                **kwargs
            )
            
            # Validate event against schema
            if self.schema_validation_enabled:
                errors = validate_event_schema(event, "tool_executing")
                if errors:
                    self.validation_errors.extend(errors)
                    logger.error(f"tool_executing schema validation failed: {errors}")
                    return False
            
            # Send via WebSocket manager
            success = await self._emit_event(user_id, event)
            if success:
                self.events_sent += 1
                logger.debug(f"tool_executing event sent successfully for {tool_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send tool_executing event: {e}")
            return False
    
    async def send_tool_completed(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str,
        tool_name: str,  # CRITICAL: Required field (Issue #984 fix)
        results: Optional[Dict[str, Any]] = None,  # CRITICAL: Required field (Issue #984 fix)
        success: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ) -> bool:
        """Send tool_completed event with unified schema - Issue #984 fix."""
        try:
            # Create event using unified schema
            event = create_tool_completed_event(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                tool_name=tool_name,  # CRITICAL: Required field (Issue #984 fix)
                results=results,  # CRITICAL: Required field (Issue #984 fix)
                success=success,
                duration_ms=duration_ms,
                **kwargs
            )
            
            # Validate event against schema
            if self.schema_validation_enabled:
                errors = validate_event_schema(event, "tool_completed")
                if errors:
                    self.validation_errors.extend(errors)
                    logger.error(f"tool_completed schema validation failed: {errors}")
                    return False
            
            # Send via WebSocket manager
            success_result = await self._emit_event(user_id, event)
            if success_result:
                self.events_sent += 1
                logger.debug(f"tool_completed event sent successfully for {tool_name}")
            
            return success_result
            
        except Exception as e:
            logger.error(f"Failed to send tool_completed event: {e}")
            return False
    
    async def send_agent_completed(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        agent_name: str,
        final_response: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """Send agent_completed event with unified schema."""
        try:
            # Create event using unified schema
            event = create_agent_completed_event(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name=agent_name,
                final_response=final_response,
                result=result,
                **kwargs
            )
            
            # Validate event against schema
            if self.schema_validation_enabled:
                errors = validate_event_schema(event, "agent_completed")
                if errors:
                    self.validation_errors.extend(errors)
                    logger.error(f"agent_completed schema validation failed: {errors}")
                    return False
            
            # Send via WebSocket manager
            success = await self._emit_event(user_id, event)
            if success:
                self.events_sent += 1
                logger.debug(f"agent_completed event sent successfully for {agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send agent_completed event: {e}")
            return False
    
    async def send_error_event(
        self,
        user_id: str,
        thread_id: str,
        error: str,
        run_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send error event with unified schema."""
        try:
            # Create event using unified schema
            event = create_error_event(
                user_id=user_id,
                thread_id=thread_id,
                error=error,
                run_id=run_id,
                agent_name=agent_name,
                **kwargs
            )
            
            # Send via WebSocket manager
            success = await self._emit_event(user_id, event)
            if success:
                self.events_sent += 1
                logger.debug(f"error event sent successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send error event: {e}")
            return False
    
    async def _emit_event(self, user_id: str, event: Dict[str, Any]) -> bool:
        """Emit event via WebSocket manager."""
        if not self.websocket_manager:
            logger.warning("No WebSocket manager configured - event not sent")
            return False
        
        try:
            # Use WebSocket manager to emit event
            if hasattr(self.websocket_manager, 'emit_to_user'):
                await self.websocket_manager.emit_to_user(user_id, event)
                return True
            elif hasattr(self.websocket_manager, 'send_message'):
                await self.websocket_manager.send_message(user_id, event)
                return True
            else:
                logger.error("WebSocket manager missing required emission method")
                return False
                
        except Exception as e:
            logger.error(f"Failed to emit event via WebSocket manager: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "events_sent": self.events_sent,
            "validation_errors_count": len(self.validation_errors),
            "validation_errors": self.validation_errors,
            "schema_validation_enabled": self.schema_validation_enabled
        }
    
    def reset_stats(self) -> None:
        """Reset adapter statistics."""
        self.events_sent = 0
        self.validation_errors.clear()


def create_websocket_event_adapter(websocket_manager=None) -> WebSocketEventAdapter:
    """Factory function to create WebSocket event adapter."""
    return WebSocketEventAdapter(websocket_manager=websocket_manager)


# For backward compatibility with existing code
def create_agent_event(event_type: str, **kwargs) -> Dict[str, Any]:
    """
    DEPRECATED: Create agent event using legacy pattern.
    
    This function is provided for backward compatibility but should be replaced
    with the specific event creation functions from the unified schema.
    """
    import warnings
    warnings.warn(
        "create_agent_event is deprecated. Use specific event creation functions "
        "from netra_backend.app.websocket_core.event_schema instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Map legacy event types to unified schema functions
    if event_type == "agent_started":
        return create_agent_started_event(**kwargs)
    elif event_type == "agent_thinking":
        return create_agent_thinking_event(**kwargs)
    elif event_type == "tool_executing":
        return create_tool_executing_event(**kwargs)
    elif event_type == "tool_completed":
        return create_tool_completed_event(**kwargs)
    elif event_type == "agent_completed":
        return create_agent_completed_event(**kwargs)
    else:
        raise ValueError(f"Unknown event type: {event_type}")


# Export the main adapter class and factory function
__all__ = [
    'WebSocketEventAdapter',
    'create_websocket_event_adapter',
    'create_agent_event'  # Deprecated, for backward compatibility
]