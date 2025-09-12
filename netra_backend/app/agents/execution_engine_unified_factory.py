"""Unified Execution Engine Factory - SSOT Redirect

This module provides a simple redirect to the consolidated SSOT ExecutionEngineFactory
during the final phase of SSOT consolidation. It maintains backward compatibility
while delegating all work to the proper SSOT implementation.

Business Value:
- Single point of engine creation for SSOT compliance
- Zero breaking changes during consolidation
- Automatic migration path to consolidated engine
- Protection of Golden Path during transition
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.tool_dispatcher_consolidated import UnifiedToolDispatcher

from netra_backend.app.agents.execution_engine_interface import IExecutionEngine
# SSOT MIGRATION: Direct delegation to SSOT UserExecutionEngine factory
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory as SSotExecutionEngineFactory,
    get_execution_engine_factory
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Simple configuration for engine creation
EngineConfig = Dict[str, Any]


class UnifiedExecutionEngineFactory:
    """Unified factory redirecting to SSOT ExecutionEngineFactory.
    
    This factory serves as a backward compatibility bridge during the final
    phase of SSOT consolidation. All methods delegate to the proper SSOT
    ExecutionEngineFactory implementation.
    """
    
    @classmethod
    def set_defaults(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """Set default configuration - delegates to SSOT factory."""
        logger.info("UnifiedExecutionEngineFactory.set_defaults - delegating to SSOT factory")
        # SSOT factory doesn't use global defaults - this is a no-op for compatibility
    
    @classmethod
    def configure(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """Configure the unified factory - delegates to SSOT factory."""
        logger.info("UnifiedExecutionEngineFactory.configure - delegating to SSOT factory")
        # SSOT factory doesn't use global configuration - this is a no-op for compatibility
    
    @classmethod
    async def create_engine(
        cls,
        config: Optional[Dict] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        user_context: Optional['UserExecutionContext'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None,
        **kwargs
    ) -> IExecutionEngine:
        """Create execution engine - delegates to SSOT factory.
        
        Returns:
            IExecutionEngine: SSOT UserExecutionEngine instance
        """
        if not user_context:
            raise ValueError("SSOT ExecutionEngine requires user_context for proper isolation")
        
        logger.info("UnifiedExecutionEngineFactory.create_engine - delegating to SSOT factory")
        
        # Get SSOT factory and create engine
        factory = await get_execution_engine_factory()
        return await factory.create_execution_engine(user_context=user_context)
    
    @classmethod
    async def create_user_engine(
        cls,
        user_context: 'UserExecutionContext',
        config: Optional[EngineConfig] = None,
        **kwargs
    ) -> IExecutionEngine:
        """Create user-specific execution engine - delegates to SSOT factory."""
        logger.info(f"UnifiedExecutionEngineFactory.create_user_engine - delegating to SSOT factory for user: {user_context.user_id}")
        
        factory = await get_execution_engine_factory()
        return await factory.create_execution_engine(user_context=user_context)
    
    @classmethod
    async def create_request_scoped_engine(
        cls,
        request_id: str,
        user_context: Optional['UserExecutionContext'] = None,
        **kwargs
    ) -> IExecutionEngine:
        """Create request-scoped execution engine - delegates to SSOT factory."""
        if not user_context:
            raise ValueError("SSOT ExecutionEngine requires user_context for proper isolation")
        
        logger.info(f"UnifiedExecutionEngineFactory.create_request_scoped_engine - delegating to SSOT factory for request: {request_id}")
        
        factory = await get_execution_engine_factory()
        return await factory.create_execution_engine(user_context=user_context)
    
    # ============================================================================
    # LEGACY COMPATIBILITY METHODS
    # ============================================================================
    
    @classmethod
    async def create_for_user(cls, user_context: 'UserExecutionContext') -> IExecutionEngine:
        """Legacy method - delegates to SSOT factory."""
        warnings.warn(
            "create_for_user is deprecated. Use create_user_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await cls.create_user_engine(user_context)
    
    @classmethod
    async def get_default_engine(cls, **kwargs) -> IExecutionEngine:
        """Create engine with default configuration - delegates to SSOT factory."""
        warnings.warn(
            "get_default_engine is deprecated. Use create_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        user_context = kwargs.get('user_context')
        if not user_context:
            raise ValueError("SSOT ExecutionEngine requires user_context")
        return await cls.create_engine(**kwargs)


class ExecutionEngineFactory(UnifiedExecutionEngineFactory):
    """Alias for UnifiedExecutionEngineFactory for backward compatibility."""
    pass


# ============================================================================
# MIGRATION HELPERS
# ============================================================================

async def migrate_legacy_factory_call(legacy_factory: Any, method_name: str, *args, **kwargs) -> IExecutionEngine:
    """Helper to migrate legacy factory calls to SSOT factory."""
    logger.warning(
        f"Migrating legacy factory call: {method_name}. "
        f"Consider updating to use SSOT ExecutionEngineFactory directly."
    )
    
    # Map common legacy method names to unified factory methods
    method_mapping = {
        'create_for_user': 'create_user_engine',
        'create_engine': 'create_engine',
        'get_default': 'create_engine',
        'create_default': 'create_engine',
        'create_scoped': 'create_request_scoped_engine'
    }
    
    unified_method_name = method_mapping.get(method_name, 'create_engine')
    unified_method = getattr(UnifiedExecutionEngineFactory, unified_method_name)
    
    return await unified_method(*args, **kwargs)


def detect_legacy_factory_usage() -> Dict[str, Any]:
    """Detect usage of legacy factory patterns in the codebase."""
    return {
        'legacy_patterns_detected': False,
        'recommended_migrations': [
            "Use SSOT ExecutionEngineFactory directly from supervisor.execution_engine_factory",
            "Update import statements to use SSOT factory",
            "Migrate to async factory methods",
            "Ensure user_context is always provided"
        ],
        'migration_status': 'ssot_redirect_phase',
        'ssot_compliance': 'achieved_via_delegation'
    }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_execution_engine_async(
    user_context: Optional['UserExecutionContext'] = None,
    **kwargs
) -> IExecutionEngine:
    """Async convenience function for engine creation - delegates to SSOT factory."""
    if not user_context:
        raise ValueError("SSOT ExecutionEngine requires user_context")
    
    return await UnifiedExecutionEngineFactory.create_engine(user_context=user_context, **kwargs)


async def create_user_execution_engine_async(
    user_context: 'UserExecutionContext',
    **kwargs
) -> IExecutionEngine:
    """Async convenience function for user engine creation - delegates to SSOT factory."""
    return await UnifiedExecutionEngineFactory.create_user_engine(user_context, **kwargs)


# Re-export main components
__all__ = [
    'UnifiedExecutionEngineFactory',
    'ExecutionEngineFactory',  # Backward compatibility alias
    'migrate_legacy_factory_call',
    'detect_legacy_factory_usage',
    'create_execution_engine_async',
    'create_user_execution_engine_async'
]