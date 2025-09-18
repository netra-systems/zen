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
    from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager

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
    DEPRECATED: Unnecessary factory abstraction for WebSocket bridge components.

    This factory adds no value over direct instantiation and has been deprecated
    as part of Issue #1194 factory pattern over-engineering cleanup.

    MIGRATION PATH:
    - Replace WebSocketBridgeFactory.create_standard_bridge() with StandardWebSocketBridge()
    - Replace WebSocketBridgeFactory.create_bridge_adapter() with WebSocketBridgeAdapter()
    - Replace WebSocketBridgeFactory.create_agent_bridge() with create_agent_websocket_bridge()

    This class is maintained temporarily for backward compatibility but will be
    removed in a future release.
    """

    @staticmethod
    def create_standard_bridge(
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None,
        bridge_id: Optional[str] = None
    ) -> StandardWebSocketBridge:
        """
        DEPRECATED: Use StandardWebSocketBridge() directly.

        Example:
            # OLD (over-engineered)
            bridge = WebSocketBridgeFactory.create_standard_bridge(manager, context, id)

            # NEW (direct instantiation)
            bridge = StandardWebSocketBridge(manager, context, id)
        """
        logger.warning(
            "WebSocketBridgeFactory.create_standard_bridge() is deprecated. "
            "Use StandardWebSocketBridge() directly for Issue #1194 compliance."
        )
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
        """
        DEPRECATED: Use WebSocketBridgeAdapter() directly.

        Example:
            # OLD (over-engineered)
            adapter = WebSocketBridgeFactory.create_bridge_adapter(manager)

            # NEW (direct instantiation)
            adapter = WebSocketBridgeAdapter(websocket_manager=manager)
        """
        logger.warning(
            "WebSocketBridgeFactory.create_bridge_adapter() is deprecated. "
            "Use WebSocketBridgeAdapter() directly for Issue #1194 compliance."
        )
        return WebSocketBridgeAdapter(
            websocket_manager=websocket_manager
        )

    @staticmethod
    def create_agent_bridge(
        websocket_manager: Optional["WebSocketManager"] = None,
        user_context: Optional[UserExecutionContext] = None
    ) -> AgentWebSocketBridge:
        """
        DEPRECATED: Use create_agent_websocket_bridge() function directly.

        Example:
            # OLD (over-engineered)
            bridge = WebSocketBridgeFactory.create_agent_bridge(manager, context)

            # NEW (direct function call)
            bridge = create_agent_websocket_bridge(manager, context)
        """
        logger.warning(
            "WebSocketBridgeFactory.create_agent_bridge() is deprecated. "
            "Use create_agent_websocket_bridge() directly for Issue #1194 compliance."
        )
        if websocket_manager and user_context:
            return create_agent_websocket_bridge(
                websocket_manager=websocket_manager,
                user_context=user_context
            )
        else:
            # Return minimal bridge for testing
            return AgentWebSocketBridge()


# DEPRECATED: Factory function aliases - use direct instantiation instead
def create_standard_websocket_bridge(
    websocket_manager: Optional["WebSocketManager"] = None,
    user_context: Optional[UserExecutionContext] = None,
    bridge_id: Optional[str] = None
) -> StandardWebSocketBridge:
    """
    DEPRECATED: Factory function wrapper adds no value.

    Use StandardWebSocketBridge() directly instead of this function wrapper.
    This eliminates unnecessary indirection per Issue #1194 factory cleanup.
    """
    logger.warning(
        "create_standard_websocket_bridge() is deprecated. "
        "Use StandardWebSocketBridge() directly for Issue #1194 compliance."
    )
    return StandardWebSocketBridge(
        websocket_manager=websocket_manager,
        user_context=user_context,
        bridge_id=bridge_id
    )


def create_agent_bridge_adapter(
    websocket_manager: Optional["WebSocketManager"] = None,
    user_context: Optional[UserExecutionContext] = None
) -> WebSocketBridgeAdapter:
    """
    DEPRECATED: Factory function wrapper adds no value.

    Use WebSocketBridgeAdapter() directly instead of this function wrapper.
    This eliminates unnecessary indirection per Issue #1194 factory cleanup.
    """
    logger.warning(
        "create_agent_bridge_adapter() is deprecated. "
        "Use WebSocketBridgeAdapter() directly for Issue #1194 compliance."
    )
    return WebSocketBridgeAdapter(
        websocket_manager=websocket_manager
    )


# DEPRECATED: Additional factory wrapper functions
def create_websocket_bridge_for_testing() -> StandardWebSocketBridge:
    """
    DEPRECATED: Use StandardWebSocketBridge(bridge_id="test_bridge") directly.

    This wrapper function adds no value over direct instantiation.
    """
    logger.warning(
        "create_websocket_bridge_for_testing() is deprecated. "
        "Use StandardWebSocketBridge(bridge_id='test_bridge') directly."
    )
    return StandardWebSocketBridge(bridge_id="test_bridge")


def create_websocket_bridge_with_context(
    user_context: UserExecutionContext
) -> StandardWebSocketBridge:
    """
    DEPRECATED: Use StandardWebSocketBridge(user_context=context, bridge_id=...) directly.

    This wrapper function adds no value over direct instantiation.
    """
    logger.warning(
        "create_websocket_bridge_with_context() is deprecated. "
        "Use StandardWebSocketBridge() constructor directly."
    )
    return StandardWebSocketBridge(
        user_context=user_context,
        bridge_id=f"ctx_bridge_{user_context.user_id[:8] if user_context.user_id else 'unknown'}"
    )


def get_websocket_bridge_factory() -> WebSocketBridgeFactory:
    """
    DEPRECATED: WebSocketBridgeFactory adds no value over direct instantiation.

    This function exists only for backward compatibility and will be removed.
    Use direct instantiation instead.
    """
    logger.warning(
        "get_websocket_bridge_factory() is deprecated. "
        "Use direct instantiation instead of factory pattern."
    )
    return WebSocketBridgeFactory()


def reset_websocket_bridge_factory() -> None:
    """Reset any global factory state - FOR TESTING ONLY.

    This function provides compatibility with testing infrastructure that expects
    a reset function for factory patterns. Currently this factory doesn't maintain
    global state, but this function is provided for consistency and future-proofing.

    Note: This factory is deprecated as part of Issue #1194 factory cleanup.
    """
    logger.info("WebSocket bridge factory reset called - no global state to reset")
    # Note: This factory doesn't currently maintain global state like the
    # WebSocketManagerFactory does, but this function is provided for:
    # 1. Backward compatibility with existing test infrastructure
    # 2. Consistency with other factory reset patterns
    # 3. Future-proofing if global state is added later


# Export all public classes and functions
__all__ = [
    "StandardWebSocketBridge",
    "WebSocketBridgeAdapter",
    "WebSocketBridgeFactory",
    "create_standard_websocket_bridge",
    "create_agent_bridge_adapter",
    "create_websocket_bridge_for_testing",
    "create_websocket_bridge_with_context",
    "get_websocket_bridge_factory",
    "reset_websocket_bridge_factory",  # Added missing function
    # Re-export AgentWebSocketBridge for convenience
    "AgentWebSocketBridge",
    "create_agent_websocket_bridge",
]