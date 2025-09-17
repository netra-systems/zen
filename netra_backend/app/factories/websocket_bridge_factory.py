"""
WebSocket Bridge Factory - Factory pattern for WebSocket bridge components

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test infrastructure support and modular WebSocket integration
- Value Impact: Enables proper factory-based WebSocket bridge creation for tests
- Revenue Impact: Critical for test infrastructure that validates $500K+ ARR chat functionality

This factory provides standardized creation patterns for WebSocket bridge components,
enabling proper dependency injection and testing isolation for chat functionality.

Key Components:
- StandardWebSocketBridge: Standard WebSocket bridge implementation
- WebSocketBridgeAdapter: Adapter pattern for WebSocket integration
- Factory functions for clean instantiation patterns
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

# Import existing implementations that we'll expose through factory pattern
from netra_backend.app.agents.request_scoped_tool_dispatcher import WebSocketBridgeAdapter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.logging.unified_logging_ssot import get_logger

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager

logger = get_logger(__name__)


class StandardWebSocketBridge:
    """
    Standard WebSocket bridge implementation that provides a consistent interface
    for WebSocket communication within agent execution contexts.

    This class wraps the AgentWebSocketBridge with factory pattern support.
    """

    def __init__(
        self,
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None,
        bridge_id: Optional[str] = None
    ):
        """Initialize StandardWebSocketBridge with optional dependencies."""
        self.bridge_id = bridge_id or f"bridge_{uuid.uuid4().hex[:8]}"
        self.websocket_manager = websocket_manager
        self.user_context = user_context
        self._initialized = False
        self._agent_bridge: Optional[AgentWebSocketBridge] = None

        logger.info(
            f"StandardWebSocketBridge initialized",
            extra={
                "bridge_id": self.bridge_id,
                "has_websocket_manager": websocket_manager is not None,
                "has_user_context": user_context is not None
            }
        )

    async def initialize(self) -> None:
        """Initialize the bridge with required dependencies."""
        if self._initialized:
            return

        # Create underlying agent bridge if we have dependencies
        if self.websocket_manager and self.user_context:
            self._agent_bridge = create_agent_websocket_bridge(
                websocket_manager=self.websocket_manager,
                user_context=self.user_context
            )

        self._initialized = True
        logger.info(f"StandardWebSocketBridge {self.bridge_id} initialized")

    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Emit a WebSocket event through the bridge."""
        if not self._initialized:
            await self.initialize()

        if self._agent_bridge:
            try:
                # Use the agent bridge to emit events
                await self._agent_bridge.emit_agent_event(event_type, data)
                return True
            except Exception as e:
                logger.error(f"Failed to emit event via agent bridge: {e}")
                return False
        else:
            # Fallback: log the event
            logger.info(
                f"StandardWebSocketBridge {self.bridge_id} would emit event",
                extra={"event_type": event_type, "data": data}
            )
            return True

    async def cleanup(self) -> None:
        """Clean up bridge resources."""
        if self._agent_bridge:
            # AgentWebSocketBridge doesn't have explicit cleanup, but we can clear reference
            self._agent_bridge = None

        self._initialized = False
        logger.info(f"StandardWebSocketBridge {self.bridge_id} cleaned up")


class WebSocketBridgeFactory:
    """
    Factory class for creating WebSocket bridge components with proper dependency injection.
    """

    def configure(self) -> None:
        """
        Configure the WebSocket bridge factory.

        This method provides compatibility with test infrastructure that expects
        a configure() method on factory instances. The actual configuration
        is handled during individual bridge creation.
        """
        logger.info("WebSocketBridgeFactory.configure() called - factory ready")

    @staticmethod
    def create_standard_bridge(
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None,
        bridge_id: Optional[str] = None
    ) -> StandardWebSocketBridge:
        """Create a StandardWebSocketBridge instance."""
        return StandardWebSocketBridge(
            websocket_manager=websocket_manager,
            user_context=user_context,
            bridge_id=bridge_id
        )

    @staticmethod
    def create_bridge_adapter(
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None
    ) -> WebSocketBridgeAdapter:
        """Create a WebSocketBridgeAdapter instance."""
        # The WebSocketBridgeAdapter from request_scoped_tool_dispatcher expects specific parameters
        return WebSocketBridgeAdapter(
            websocket_manager=websocket_manager
        )

    @staticmethod
    def create_agent_bridge(
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None
    ) -> AgentWebSocketBridge:
        """Create an AgentWebSocketBridge instance."""
        if websocket_manager and user_context:
            return create_agent_websocket_bridge(
                websocket_manager=websocket_manager,
                user_context=user_context
            )
        else:
            # Return minimal bridge for testing
            return AgentWebSocketBridge()


# Factory function aliases for backward compatibility and easier imports
def create_standard_websocket_bridge(
    websocket_manager: Optional["WebSocketManager"] = None,
    user_context: Optional[UserExecutionContext] = None,
    bridge_id: Optional[str] = None
) -> StandardWebSocketBridge:
    """Factory function to create a StandardWebSocketBridge."""
    return WebSocketBridgeFactory.create_standard_bridge(
        websocket_manager=websocket_manager,
        user_context=user_context,
        bridge_id=bridge_id
    )


def create_agent_bridge_adapter(
    websocket_manager: Optional["WebSocketManager"] = None,
    user_context: Optional[UserExecutionContext] = None
) -> WebSocketBridgeAdapter:
    """Factory function to create a WebSocketBridgeAdapter."""
    return WebSocketBridgeFactory.create_bridge_adapter(
        websocket_manager=websocket_manager,
        user_context=user_context
    )


# Additional factory functions for common patterns
def create_websocket_bridge_for_testing() -> StandardWebSocketBridge:
    """Create a minimal WebSocket bridge suitable for testing scenarios."""
    return StandardWebSocketBridge(bridge_id="test_bridge")


def create_websocket_bridge_with_context(
    user_context: UserExecutionContext
) -> StandardWebSocketBridge:
    """Create a WebSocket bridge with user context but without WebSocket manager."""
    return StandardWebSocketBridge(
        user_context=user_context,
        bridge_id=f"ctx_bridge_{user_context.user_id[:8] if user_context.user_id else 'unknown'}"
    )


# Singleton instance for factory pattern
_websocket_bridge_factory_instance: Optional[WebSocketBridgeFactory] = None


def get_websocket_bridge_factory() -> WebSocketBridgeFactory:
    """Get WebSocketBridgeFactory instance using singleton pattern.

    This function provides a single source of truth for WebSocketBridgeFactory
    instances, ensuring consistency across the application while maintaining
    proper factory pattern support.

    Returns:
        WebSocketBridgeFactory: Singleton factory instance
    """
    global _websocket_bridge_factory_instance

    if _websocket_bridge_factory_instance is None:
        _websocket_bridge_factory_instance = WebSocketBridgeFactory()
        logger.info("Created new WebSocketBridgeFactory singleton instance")
    else:
        logger.debug("Returning existing WebSocketBridgeFactory singleton instance")

    return _websocket_bridge_factory_instance


def reset_websocket_bridge_factory() -> None:
    """Reset the WebSocketBridgeFactory singleton instance (for testing).

    This function is primarily intended for testing scenarios where you need
    to reset the singleton state between tests.
    """
    global _websocket_bridge_factory_instance
    _websocket_bridge_factory_instance = None
    logger.debug("Reset WebSocketBridgeFactory singleton instance")


# Export all public classes and functions
__all__ = [
    "StandardWebSocketBridge",
    "WebSocketBridgeAdapter",
    "WebSocketBridgeFactory",
    "get_websocket_bridge_factory",  # Added missing function
    "reset_websocket_bridge_factory",
    "create_standard_websocket_bridge",
    "create_agent_bridge_adapter",
    "create_websocket_bridge_for_testing",
    "create_websocket_bridge_with_context",
    # Re-export AgentWebSocketBridge for convenience
    "AgentWebSocketBridge",
    "create_agent_websocket_bridge",
]