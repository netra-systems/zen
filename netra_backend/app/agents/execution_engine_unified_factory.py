"""Unified Execution Engine Factory - SSOT Implementation

This module provides the unified factory for creating execution engines
during the SSOT consolidation process. It automatically delegates to the
consolidated execution engine while maintaining backward compatibility.

Business Value:
- Single point of engine creation for SSOT compliance
- Zero breaking changes during consolidation
- Automatic migration path to consolidated engine
- Protection of Golden Path during transition

Migration Strategy:
1. All engine creation goes through this unified factory
2. Factory automatically creates consolidated engines with proper adapters
3. Legacy factory methods preserved for backward compatibility
4. Gradual migration to consolidated engine throughout codebase
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
# SSOT MIGRATION: Use UserExecutionEngine as the single source of truth
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory as UserExecutionEngineFactory,
    get_execution_engine_factory
)
from netra_backend.app.agents.execution_engine_legacy_adapter import (
    ExecutionEngineFactory as AdapterFactory
)
# Import RequestScopedExecutionEngine for return type annotation
try:
    from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine
except ImportError:
    # Fallback if not available - use IExecutionEngine
    RequestScopedExecutionEngine = IExecutionEngine
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Simple configuration for engine creation
EngineConfig = Dict[str, Any]


class UnifiedExecutionEngineFactory:
    """Unified factory for all execution engine creation.
    
    This factory serves as the SSOT for execution engine creation during
    the consolidation process. It automatically creates consolidated engines
    and provides backward compatibility for legacy usage patterns.
    
    Key Features:
    - Automatic delegation to ConsolidatedExecutionEngine
    - Backward compatibility for legacy factory methods
    - Interface compliance guarantee
    - Configuration-driven engine creation
    - User context support
    """
    
    # Class-level defaults for consistent configuration
    _default_config: Optional[EngineConfig] = None
    _default_registry: Optional['AgentRegistry'] = None
    _default_websocket_bridge: Optional['AgentWebSocketBridge'] = None
    _default_tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    
    @classmethod
    def set_defaults(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """Set default configuration for all engine creation.
        
        Args:
            config: Default engine configuration
            registry: Default agent registry
            websocket_bridge: Default WebSocket bridge
            tool_dispatcher: Default tool dispatcher
        """
        if config:
            cls._default_config = config
        if registry:
            cls._default_registry = registry
        if websocket_bridge:
            cls._default_websocket_bridge = websocket_bridge
        if tool_dispatcher:
            cls._default_tool_dispatcher = tool_dispatcher
        
        logger.info("UnifiedExecutionEngineFactory defaults configured")
    
    @classmethod
    def configure(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """Configure the unified factory with default dependencies.
        
        This method is required by the startup system to configure the factory
        with necessary dependencies before creating engines.
        
        Args:
            config: Default engine configuration
            registry: Default agent registry
            websocket_bridge: Default WebSocket bridge
            tool_dispatcher: Default tool dispatcher
        """
        cls.set_defaults(config, registry, websocket_bridge, tool_dispatcher)
        logger.info("UnifiedExecutionEngineFactory configured successfully")
    
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
        """Create a consolidated execution engine with interface guarantee.
        
        This is the primary method for creating execution engines. It always
        creates a ConsolidatedExecutionEngine and ensures it implements the
        IExecutionEngine interface.
        
        Args:
            config: Engine configuration (uses default if not provided)
            registry: Agent registry (uses default if not provided)
            websocket_bridge: WebSocket bridge (uses default if not provided)
            user_context: Optional user context for isolation
            tool_dispatcher: Tool dispatcher (uses default if not provided)
            **kwargs: Additional configuration options
            
        Returns:
            IExecutionEngine: Interface-compliant execution engine
        """
        # Use provided or default configuration
        effective_config = config or cls._default_config or {}
        effective_registry = registry or cls._default_registry
        effective_websocket_bridge = websocket_bridge or cls._default_websocket_bridge
        effective_tool_dispatcher = tool_dispatcher or cls._default_tool_dispatcher
        
        # Auto-configure based on user context
        if user_context:
            effective_config.update({
                'enable_user_features': True,
                'require_user_context': True,
                'enable_request_scoping': True
            })
        
        logger.info(
            f"Creating UserExecutionEngine (SSOT) with user_context={user_context is not None}"
        )
        
        # SSOT MIGRATION: Create UserExecutionEngine instead of ConsolidatedExecutionEngine
        if not user_context:
            raise ValueError("UserExecutionEngine requires user_context for proper isolation")
        
        # Get the factory and create UserExecutionEngine asynchronously
        factory = get_execution_engine_factory()
        engine = await factory.create_execution_engine(
            user_context=user_context
        )
        
        # Ensure interface compliance (ConsolidatedExecutionEngine should already implement it)
        interface_engine = AdapterFactory.ensure_interface_compliance(engine)
        
        logger.debug(f"Created engine type: {interface_engine.get_engine_type()}")
        return interface_engine
    
    @classmethod
    def create_user_engine(
        cls,
        user_context: 'UserExecutionContext',
        config: Optional[EngineConfig] = None,
        **kwargs
    ) -> IExecutionEngine:
        """Create user-specific execution engine with optimized configuration.
        
        Args:
            user_context: User execution context for isolation
            config: Optional engine configuration override
            **kwargs: Additional configuration options
            
        Returns:
            IExecutionEngine: User-configured execution engine
        """
        # Create user-optimized configuration
        user_config = config or {
            'enable_user_features': True,
            'enable_websocket_events': True,
            'require_user_context': True,
            'enable_request_scoping': True,
            'enable_metrics': True,
            'max_concurrent_agents': 5,  # Conservative limit for per-user
            'agent_execution_timeout': 30.0
        }
        
        logger.info(f"Creating user-specific engine for user: {user_context.user_id}")
        
        return cls.create_engine(
            config=user_config,
            user_context=user_context,
            **kwargs
        )
    
    @classmethod
    def create_request_scoped_engine(
        cls,
        request_id: str,
        user_context: Optional['UserExecutionContext'] = None,
        **kwargs
    ) -> RequestScopedExecutionEngine:
        """Create request-scoped execution engine for complete isolation.
        
        Args:
            request_id: Unique request identifier
            user_context: Optional user context
            **kwargs: Additional configuration options
            
        Returns:
            RequestScopedExecutionEngine: Request-isolated engine
        """
        logger.info(f"Creating request-scoped engine for request: {request_id}")
        
        # Create base consolidated engine
        base_engine = cls.create_engine(user_context=user_context, **kwargs)
        
        # Wrap in request scope (only works with ConsolidatedExecutionEngine)
        if hasattr(base_engine, 'with_request_scope'):
            return base_engine.with_request_scope(request_id)
        elif hasattr(base_engine, 'wrapped_engine') and hasattr(base_engine.wrapped_engine, 'with_request_scope'):
            # Handle case where engine is wrapped
            return base_engine.wrapped_engine.with_request_scope(request_id)
        else:
            raise RuntimeError(
                f"Engine type {type(base_engine)} does not support request scoping. "
                f"This should not happen with ConsolidatedExecutionEngine."
            )
    
    # ============================================================================
    # LEGACY COMPATIBILITY METHODS
    # ============================================================================
    
    @classmethod
    def create_for_user(cls, user_context: 'UserExecutionContext') -> IExecutionEngine:
        """Legacy method - creates user engine (backward compatibility).
        
        This method exists for backward compatibility with existing code
        that expects the create_for_user method signature.
        
        Args:
            user_context: User execution context
            
        Returns:
            IExecutionEngine: User-configured execution engine
        """
        warnings.warn(
            "create_for_user is deprecated. Use create_user_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return cls.create_user_engine(user_context)
    
    @classmethod
    def get_default_engine(cls, **kwargs) -> IExecutionEngine:
        """Create engine with default configuration (backward compatibility).
        
        Args:
            **kwargs: Configuration overrides
            
        Returns:
            IExecutionEngine: Default-configured execution engine
        """
        warnings.warn(
            "get_default_engine is deprecated. Use create_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return cls.create_engine(**kwargs)


class ExecutionEngineFactory(UnifiedExecutionEngineFactory):
    """Alias for UnifiedExecutionEngineFactory for backward compatibility.
    
    This class exists to provide backward compatibility for code that
    imports ExecutionEngineFactory from this module.
    """
    pass


# ============================================================================
# MIGRATION HELPERS
# ============================================================================

def migrate_legacy_factory_call(legacy_factory: Any, method_name: str, *args, **kwargs) -> IExecutionEngine:
    """Helper to migrate legacy factory calls to unified factory.
    
    Args:
        legacy_factory: Legacy factory instance (ignored)
        method_name: Method name that was called on legacy factory
        *args: Positional arguments from legacy call
        **kwargs: Keyword arguments from legacy call
        
    Returns:
        IExecutionEngine: Engine created through unified factory
    """
    logger.warning(
        f"Migrating legacy factory call: {method_name}. "
        f"Consider updating to use UnifiedExecutionEngineFactory directly."
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
    
    return unified_method(*args, **kwargs)


def detect_legacy_factory_usage() -> Dict[str, Any]:
    """Detect usage of legacy factory patterns in the codebase.
    
    This function can be used to identify places where legacy factory
    patterns are still being used and need migration.
    
    Returns:
        Dict containing detection results and recommendations
    """
    # This would be implemented to scan the codebase for legacy patterns
    # For now, return a template result
    return {
        'legacy_patterns_detected': False,
        'recommended_migrations': [
            "Replace SupervisorFactory usage with UnifiedExecutionEngineFactory",
            "Update import statements to use unified factory",
            "Migrate create_for_user calls to create_user_engine",
            "Use create_request_scoped_engine for request isolation"
        ],
        'migration_status': 'in_progress',
        'ssot_compliance': 'improving'
    }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_execution_engine_async(
    user_context: Optional['UserExecutionContext'] = None,
    **kwargs
) -> IExecutionEngine:
    """Async convenience function for engine creation.
    
    Args:
        user_context: Optional user context
        **kwargs: Engine configuration options
        
    Returns:
        IExecutionEngine: Initialized execution engine
    """
    engine = UnifiedExecutionEngineFactory.create_engine(user_context=user_context, **kwargs)
    await engine.initialize()
    return engine


async def create_user_execution_engine_async(
    user_context: 'UserExecutionContext',
    **kwargs
) -> IExecutionEngine:
    """Async convenience function for user engine creation.
    
    Args:
        user_context: User execution context
        **kwargs: Engine configuration options
        
    Returns:
        IExecutionEngine: Initialized user execution engine
    """
    engine = UnifiedExecutionEngineFactory.create_user_engine(user_context, **kwargs)
    await engine.initialize()
    return engine


# Re-export main components
__all__ = [
    'UnifiedExecutionEngineFactory',
    'ExecutionEngineFactory',  # Backward compatibility alias
    'migrate_legacy_factory_call',
    'detect_legacy_factory_usage',
    'create_execution_engine_async',
    'create_user_execution_engine_async'
]