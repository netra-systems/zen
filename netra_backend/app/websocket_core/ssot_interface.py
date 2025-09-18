"""SSOT WebSocket Interface - Single Source of Truth for WebSocket Operations

This module defines the canonical interface for all WebSocket operations,
ensuring consistency across all agents and execution contexts.

Business Value:
- Eliminates 27 duplicate WebSocket patterns
- Provides consistent event delivery for $500K+ ARR protection
- Enables atomic migration from legacy patterns to SSOT compliance
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketNotificationInterface(ABC):
    """SSOT interface for WebSocket notifications.

    All WebSocket operations must implement this interface to ensure
    consistent event delivery patterns across the system.
    """

    @abstractmethod
    async def notify_agent_started(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_started event - CRITICAL for Golden Path."""
        pass

    @abstractmethod
    async def notify_agent_thinking(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_thinking event - CRITICAL for Golden Path."""
        pass

    @abstractmethod
    async def notify_tool_executing(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send tool_executing event - CRITICAL for Golden Path."""
        pass

    @abstractmethod
    async def notify_tool_completed(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send tool_completed event - CRITICAL for Golden Path."""
        pass

    @abstractmethod
    async def notify_agent_completed(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        final_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_completed event - CRITICAL for Golden Path."""
        pass

    @abstractmethod
    async def notify_error(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send error event with proper context."""
        pass


class SSotWebSocketBridge(WebSocketNotificationInterface):
    """SSOT WebSocket Bridge - Canonical implementation.

    This class provides the single source of truth implementation
    for WebSocket notifications, coordinating with the unified manager.
    """

    def __init__(self, context: 'UserExecutionContext'):
        """Initialize SSOT bridge with user context."""
        self.context = context
        self.logger = logger.get_child(f"SSotBridge.{context.user_id}")

    async def notify_agent_started(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_started event via SSOT WebSocket manager."""
        try:
            # Get SSOT WebSocket manager from context
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_agent_started(
                        context.run_id, agent_name, metadata or {}
                    )
                    self.logger.debug(f"Sent agent_started for {agent_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for agent_started: {agent_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for agent_started: {agent_name}")
        except Exception as e:
            self.logger.error(f"Failed to send agent_started for {agent_name}: {e}")

    async def notify_agent_thinking(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_thinking event via SSOT WebSocket manager."""
        try:
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_agent_thinking(
                        context.run_id, agent_name, reasoning, metadata or {}
                    )
                    self.logger.debug(f"Sent agent_thinking for {agent_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for agent_thinking: {agent_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for agent_thinking: {agent_name}")
        except Exception as e:
            self.logger.error(f"Failed to send agent_thinking for {agent_name}: {e}")

    async def notify_tool_executing(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send tool_executing event via SSOT WebSocket manager."""
        try:
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_tool_executing(
                        context.run_id, agent_name, tool_name, tool_input
                    )
                    self.logger.debug(f"Sent tool_executing for {tool_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for tool_executing: {tool_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for tool_executing: {tool_name}")
        except Exception as e:
            self.logger.error(f"Failed to send tool_executing for {tool_name}: {e}")

    async def notify_tool_completed(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send tool_completed event via SSOT WebSocket manager."""
        try:
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_tool_completed(
                        context.run_id, agent_name, tool_name, tool_result
                    )
                    self.logger.debug(f"Sent tool_completed for {tool_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for tool_completed: {tool_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for tool_completed: {tool_name}")
        except Exception as e:
            self.logger.error(f"Failed to send tool_completed for {tool_name}: {e}")

    async def notify_agent_completed(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        final_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send agent_completed event via SSOT WebSocket manager."""
        try:
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_agent_completed(
                        context.run_id, agent_name, final_result
                    )
                    self.logger.debug(f"Sent agent_completed for {agent_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for agent_completed: {agent_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for agent_completed: {agent_name}")
        except Exception as e:
            self.logger.error(f"Failed to send agent_completed for {agent_name}: {e}")

    async def notify_error(
        self,
        context: 'UserExecutionContext',
        agent_name: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send error event via SSOT WebSocket manager."""
        try:
            if hasattr(context, 'websocket_bridge') and context.websocket_bridge:
                websocket_manager = context.websocket_bridge.websocket_manager
                if websocket_manager:
                    await websocket_manager.send_agent_error(
                        context.run_id, agent_name, error_message
                    )
                    self.logger.debug(f"Sent agent_error for {agent_name}")
                else:
                    self.logger.warning(f"No websocket_manager in context for agent_error: {agent_name}")
            else:
                self.logger.warning(f"No websocket_bridge in context for agent_error: {agent_name}")
        except Exception as e:
            self.logger.error(f"Failed to send agent_error for {agent_name}: {e}")


def create_ssot_websocket_bridge(context: 'UserExecutionContext') -> WebSocketNotificationInterface:
    """Create SSOT WebSocket bridge for user context.

    This is the canonical factory function for creating WebSocket bridges.
    All code should use this function instead of direct instantiation.
    """
    return SSotWebSocketBridge(context)


# Backward compatibility alias
WebSocketBridge = SSotWebSocketBridge