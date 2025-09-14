"""UnifiedExecutionEngineFactory - SSOT Compatibility Wrapper.

This module provides backward compatibility for code expecting UnifiedExecutionEngineFactory
while delegating to the canonical ExecutionEngineFactory implementation.

CRITICAL: This is a compatibility shim only. All new code should use:
- netra_backend.app.agents.supervisor.execution_engine_factory.ExecutionEngineFactory
- netra_backend.app.agents.supervisor.execution_engine_factory.configure_execution_engine_factory()

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Compatibility
- Value Impact: Prevents production outages during SSOT migration
- Strategic Impact: Maintains Golden Path functionality during factory pattern consolidation
"""

import asyncio
import warnings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    configure_execution_engine_factory,
    ExecutionEngineFactoryError
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedExecutionEngineFactory:
    """COMPATIBILITY WRAPPER: Provides backward compatibility for legacy UnifiedExecutionEngineFactory usage.

    DEPRECATED: This class is a compatibility shim only.

    All new code should use:
    - ExecutionEngineFactory from netra_backend.app.agents.supervisor.execution_engine_factory
    - configure_execution_engine_factory() function for SSOT initialization

    This wrapper delegates all operations to the canonical ExecutionEngineFactory
    while providing the expected interface for legacy code.
    """

    def __init__(self,
                 websocket_bridge: Optional['AgentWebSocketBridge'] = None,
                 database_session_manager=None,
                 redis_manager=None):
        """Initialize compatibility wrapper by delegating to ExecutionEngineFactory.

        Args:
            websocket_bridge: WebSocket bridge for agent notifications
            database_session_manager: Database session manager
            redis_manager: Redis manager
        """
        # Issue deprecation warning
        warnings.warn(
            "UnifiedExecutionEngineFactory is deprecated. Use ExecutionEngineFactory "
            "from netra_backend.app.agents.supervisor.execution_engine_factory instead. "
            "This compatibility wrapper will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )

        logger.warning(
            "🚨 COMPATIBILITY MODE: UnifiedExecutionEngineFactory is deprecated. "
            "Using ExecutionEngineFactory via compatibility wrapper. "
            "Update code to use ExecutionEngineFactory directly."
        )

        # Delegate to canonical ExecutionEngineFactory
        self._delegate = ExecutionEngineFactory(
            websocket_bridge=websocket_bridge,
            database_session_manager=database_session_manager,
            redis_manager=redis_manager
        )

        logger.info("✅ UnifiedExecutionEngineFactory compatibility wrapper initialized")

    @classmethod
    async def configure(cls,
                       websocket_bridge: 'AgentWebSocketBridge',
                       database_session_manager=None,
                       redis_manager=None) -> 'UnifiedExecutionEngineFactory':
        """Configure UnifiedExecutionEngineFactory - COMPATIBILITY METHOD.

        DEPRECATED: Use configure_execution_engine_factory() from the supervisor module instead.

        This method provides backward compatibility for code expecting:
        UnifiedExecutionEngineFactory.configure()

        Args:
            websocket_bridge: WebSocket bridge for agent notifications
            database_session_manager: Database session manager
            redis_manager: Redis manager

        Returns:
            UnifiedExecutionEngineFactory: Compatibility wrapper instance
        """
        logger.warning(
            "🚨 COMPATIBILITY: UnifiedExecutionEngineFactory.configure() is deprecated. "
            "Use configure_execution_engine_factory() from supervisor.execution_engine_factory instead."
        )

        try:
            # Use the canonical SSOT configuration function
            canonical_factory = await configure_execution_engine_factory(
                websocket_bridge=websocket_bridge,
                database_session_manager=database_session_manager,
                redis_manager=redis_manager
            )

            # Create wrapper that delegates to canonical factory
            wrapper = cls.__new__(cls)  # Create without calling __init__
            wrapper._delegate = canonical_factory

            logger.info("✅ UnifiedExecutionEngineFactory.configure() compatibility wrapper created")
            return wrapper

        except Exception as e:
            logger.error(f"❌ UnifiedExecutionEngineFactory.configure() compatibility wrapper failed: {e}")
            raise ExecutionEngineFactoryError(f"UnifiedExecutionEngineFactory configuration failed: {e}")

    # Delegate all methods to canonical ExecutionEngineFactory
    async def create_for_user(self, context):
        """Create execution engine for user - delegates to canonical factory."""
        return await self._delegate.create_for_user(context)

    async def create_execution_engine(self, user_context):
        """Create execution engine - delegates to canonical factory."""
        return await self._delegate.create_execution_engine(user_context)

    def user_execution_scope(self, context):
        """User execution scope context manager - delegates to canonical factory."""
        return self._delegate.user_execution_scope(context)

    async def cleanup_engine(self, engine):
        """Cleanup engine - delegates to canonical factory."""
        return await self._delegate.cleanup_engine(engine)

    async def cleanup_user_context(self, user_id: str):
        """Cleanup user context - delegates to canonical factory."""
        return await self._delegate.cleanup_user_context(user_id)

    async def cleanup_all_contexts(self):
        """Cleanup all contexts - delegates to canonical factory."""
        return await self._delegate.cleanup_all_contexts()

    async def shutdown(self):
        """Shutdown factory - delegates to canonical factory."""
        return await self._delegate.shutdown()

    def get_factory_metrics(self):
        """Get factory metrics - delegates to canonical factory."""
        return self._delegate.get_factory_metrics()

    def get_active_engines_summary(self):
        """Get active engines summary - delegates to canonical factory."""
        return self._delegate.get_active_engines_summary()

    def get_active_contexts(self):
        """Get active contexts - delegates to canonical factory."""
        return self._delegate.get_active_contexts()

    def set_tool_dispatcher_factory(self, tool_dispatcher_factory):
        """Set tool dispatcher factory - delegates to canonical factory."""
        return self._delegate.set_tool_dispatcher_factory(tool_dispatcher_factory)


# Provide function-level compatibility as well
async def configure_unified_execution_engine_factory(
    websocket_bridge: 'AgentWebSocketBridge',
    database_session_manager=None,
    redis_manager=None
) -> UnifiedExecutionEngineFactory:
    """Configure unified execution engine factory - COMPATIBILITY FUNCTION.

    DEPRECATED: Use configure_execution_engine_factory() from supervisor module instead.

    Args:
        websocket_bridge: WebSocket bridge for agent notifications
        database_session_manager: Database session manager
        redis_manager: Redis manager

    Returns:
        UnifiedExecutionEngineFactory: Compatibility wrapper
    """
    return await UnifiedExecutionEngineFactory.configure(
        websocket_bridge=websocket_bridge,
        database_session_manager=database_session_manager,
        redis_manager=redis_manager
    )


# Legacy aliases for complete backward compatibility
RequestScopedUnifiedExecutionEngineFactory = UnifiedExecutionEngineFactory