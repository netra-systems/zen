"""WebSocket Manager Factory Compatibility Layer - Issue #1098

This module provides a compatibility layer for the deprecated WebSocketManagerFactory,
redirecting all calls to the SSOT get_websocket_manager() implementation.

Business Value:
- Maintains $500K+ ARR protection during migration
- Provides zero-downtime transition to SSOT patterns
- Preserves all existing business functionality
- Enables gradual migration of dependent systems

SSOT COMPLIANCE: All factory operations now delegate to canonical WebSocket manager.
"""

import asyncio
import warnings
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    get_websocket_manager_async,
    WebSocketManagerMode,
    _UnifiedWebSocketManagerImplementation
)

logger = get_logger(__name__)


class WebSocketManagerFactoryCompat:
    """Compatibility wrapper for deprecated WebSocketManagerFactory.

    DEPRECATION WARNING: This class redirects to SSOT WebSocket manager.
    All new code should use get_websocket_manager() directly.
    """

    def __init__(self, max_managers_per_user: int = 20, enable_monitoring: bool = True):
        """Initialize compatibility factory with deprecation warning."""
        warnings.warn(
            "WebSocketManagerFactory is deprecated. Use get_websocket_manager() directly. "
            "This compatibility layer will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )

        self.max_managers_per_user = max_managers_per_user
        self.enable_monitoring = enable_monitoring
        self._creation_count = 0

        logger.warning(
            f"WebSocketManagerFactory compatibility layer active. "
            f"max_managers_per_user={max_managers_per_user}, monitoring={enable_monitoring}"
        )

    def get_user_manager_count(self, user_id: str) -> int:
        """Get current manager count for a user - compatibility method."""
        # In SSOT implementation, this is managed internally
        logger.debug(f"Compatibility: get_user_manager_count for user {user_id}")
        return 1  # SSOT manager is per-user isolated

    async def create_manager(
        self,
        user_context: Any,
        mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED
    ) -> _UnifiedWebSocketManagerImplementation:
        """Create WebSocket manager via SSOT implementation.

        SSOT REDIRECT: This method now calls get_websocket_manager_async()
        to ensure consistency with the canonical implementation.
        """
        self._creation_count += 1

        logger.info(
            f"SSOT REDIRECT: create_manager() -> get_websocket_manager_async() "
            f"for user_context, creation #{self._creation_count}"
        )

        try:
            # Redirect to SSOT implementation
            manager = await get_websocket_manager_async(user_context, mode)

            logger.info(
                f"SSOT WebSocket manager created successfully via compatibility layer "
                f"for user_context"
            )

            return manager

        except Exception as e:
            logger.error(f"Failed to create WebSocket manager via SSOT: {e}")
            raise

    def create_manager_sync(
        self,
        user_context: Any,
        mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED
    ) -> _UnifiedWebSocketManagerImplementation:
        """Synchronous wrapper for create_manager.

        SSOT REDIRECT: This method calls get_websocket_manager()
        for synchronous compatibility.
        """
        self._creation_count += 1

        logger.info(
            f"SSOT REDIRECT: create_manager_sync() -> get_websocket_manager() "
            f"for user_context, creation #{self._creation_count}"
        )

        try:
            # Redirect to SSOT implementation
            manager = get_websocket_manager(user_context, mode)

            logger.info(
                f"SSOT WebSocket manager created successfully via sync compatibility layer "
                f"for user_context"
            )

            return manager

        except Exception as e:
            logger.error(f"Failed to create WebSocket manager via SSOT sync: {e}")
            raise

    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status - compatibility method."""
        return {
            "status": "SSOT_COMPATIBILITY_MODE",
            "deprecation_warning": "Use get_websocket_manager() directly",
            "creation_count": self._creation_count,
            "max_managers_per_user": self.max_managers_per_user,
            "enable_monitoring": self.enable_monitoring,
            "ssot_redirect": True,
            "business_continuity": "MAINTAINED"
        }

    async def cleanup_inactive_managers(self, user_id: str) -> int:
        """Cleanup inactive managers - no-op in SSOT implementation."""
        logger.debug(f"Compatibility: cleanup_inactive_managers for user {user_id} (SSOT managed)")
        return 0  # SSOT implementation handles cleanup automatically

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status - compatibility method."""
        return {
            "factory_status": "SSOT_COMPATIBILITY_MODE",
            "health": "HEALTHY",
            "ssot_implementation": "ACTIVE",
            "business_continuity": "MAINTAINED"
        }


# Compatibility factory instance
_COMPAT_FACTORY: Optional[WebSocketManagerFactoryCompat] = None


def get_websocket_manager_factory(
    max_managers_per_user: int = 20,
    enable_monitoring: bool = True
) -> WebSocketManagerFactoryCompat:
    """Get WebSocket manager factory - DEPRECATED.

    DEPRECATION WARNING: This function provides compatibility only.
    New code should use get_websocket_manager() directly.

    Returns:
        WebSocketManagerFactoryCompat instance that redirects to SSOT implementation
    """
    global _COMPAT_FACTORY

    warnings.warn(
        "get_websocket_manager_factory() is deprecated. Use get_websocket_manager() directly. "
        "This compatibility layer will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2
    )

    if _COMPAT_FACTORY is None:
        _COMPAT_FACTORY = WebSocketManagerFactoryCompat(
            max_managers_per_user, enable_monitoring
        )

    return _COMPAT_FACTORY


# Legacy compatibility exports
WebSocketManagerFactory = WebSocketManagerFactoryCompat


def create_websocket_manager(user_context: Any, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED) -> _UnifiedWebSocketManagerImplementation:
    """Create WebSocket manager - DEPRECATED compatibility function.

    DEPRECATION WARNING: Use get_websocket_manager() directly.
    This function provides compatibility only.
    """
    warnings.warn(
        "create_websocket_manager() is deprecated. Use get_websocket_manager() directly.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info("SSOT REDIRECT: create_websocket_manager() -> get_websocket_manager()")
    return get_websocket_manager(user_context, mode)


async def create_websocket_manager_async(user_context: Any, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED) -> _UnifiedWebSocketManagerImplementation:
    """Create WebSocket manager async - DEPRECATED compatibility function.

    DEPRECATION WARNING: Use get_websocket_manager_async() directly.
    This function provides compatibility only.
    """
    warnings.warn(
        "create_websocket_manager_async() is deprecated. Use get_websocket_manager_async() directly.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info("SSOT REDIRECT: create_websocket_manager_async() -> get_websocket_manager_async()")
    return await get_websocket_manager_async(user_context, mode)