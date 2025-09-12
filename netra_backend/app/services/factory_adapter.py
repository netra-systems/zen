"""
FactoryAdapter - Backward Compatibility Adapter for Factory Pattern Migration

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Enables seamless migration from singleton to factory patterns without breaking existing code
- Strategic Impact: Critical - Provides safe migration path with zero downtime

This module implements the FactoryAdapter pattern that bridges old singleton calls to new factory patterns,
enabling gradual migration with feature flags and comprehensive logging for migration tracking.

Key Features:
1. Backward Compatibility - Existing code continues to work during migration
2. Feature Flag Control - Enable factory patterns per route or globally  
3. Migration Tracking - Log all legacy calls to identify migration progress
4. Error Resilience - Fallback to legacy patterns if factory patterns fail
5. Zero Downtime - No service interruptions during migration
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory, UserExecutionContext, IsolatedExecutionEngine
    from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketEmitter
    from netra_backend.app.agents.execution_engine_interface import IExecutionEngine
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

logger = central_logger.get_logger(__name__)


class MigrationMode(Enum):
    """Migration modes for factory adapter."""
    LEGACY_ONLY = "legacy_only"          # Use legacy singletons only
    FACTORY_PREFERRED = "factory_preferred"  # Try factory first, fallback to legacy
    FACTORY_ONLY = "factory_only"        # Use factory patterns only
    GRADUAL = "gradual"                   # Route-specific migration with feature flags


@dataclass
class AdapterConfig:
    """Configuration for FactoryAdapter."""
    migration_mode: MigrationMode = MigrationMode.FACTORY_PREFERRED
    enable_migration_logging: bool = True
    log_legacy_calls: bool = True
    track_migration_metrics: bool = True
    factory_timeout_seconds: float = 30.0
    legacy_fallback_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'AdapterConfig':
        """Create config from environment variables."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        mode_str = env.get('FACTORY_MIGRATION_MODE', 'factory_preferred')
        try:
            migration_mode = MigrationMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid migration mode '{mode_str}', defaulting to factory_preferred")
            migration_mode = MigrationMode.FACTORY_PREFERRED
            
        return cls(
            migration_mode=migration_mode,
            enable_migration_logging=env.get('FACTORY_ENABLE_MIGRATION_LOGGING', 'true').lower() == 'true',
            log_legacy_calls=env.get('FACTORY_LOG_LEGACY_CALLS', 'true').lower() == 'true',
            track_migration_metrics=env.get('FACTORY_TRACK_METRICS', 'true').lower() == 'true',
            factory_timeout_seconds=float(env.get('FACTORY_TIMEOUT_SECONDS', '30.0')),
            legacy_fallback_enabled=env.get('FACTORY_LEGACY_FALLBACK', 'true').lower() == 'true'
        )


@dataclass
class MigrationMetrics:
    """Metrics for tracking migration progress."""
    legacy_calls_count: int = 0
    factory_calls_count: int = 0
    factory_successes_count: int = 0
    factory_failures_count: int = 0
    fallback_to_legacy_count: int = 0
    total_requests_count: int = 0
    
    # Performance metrics
    factory_avg_time_ms: float = 0.0
    legacy_avg_time_ms: float = 0.0
    
    # Error tracking
    recent_factory_errors: List[str] = field(default_factory=list)
    recent_legacy_errors: List[str] = field(default_factory=list)
    
    def get_migration_progress(self) -> float:
        """Get migration progress as percentage (0-100)."""
        if self.total_requests_count == 0:
            return 0.0
        return (self.factory_successes_count / self.total_requests_count) * 100
    
    def get_factory_success_rate(self) -> float:
        """Get factory pattern success rate."""
        if self.factory_calls_count == 0:
            return 0.0
        return (self.factory_successes_count / self.factory_calls_count) * 100


class FactoryAdapter:
    """
    Comprehensive adapter for gradual migration to factory pattern.
    
    This adapter provides a bridge between old singleton calls and new factory patterns,
    enabling safe migration with feature flags and comprehensive tracking.
    
    Business Value: Enables zero-downtime migration to user-isolated factory patterns
    """
    
    def __init__(self, 
                 execution_engine_factory: 'ExecutionEngineFactory',
                 websocket_bridge_factory: 'WebSocketBridgeFactory',
                 config: Optional[AdapterConfig] = None):
        
        self.config = config or AdapterConfig.from_env()
        self._execution_engine_factory = execution_engine_factory
        self._websocket_bridge_factory = websocket_bridge_factory
        
        # Legacy components (for backward compatibility)
        self._legacy_execution_engine: Optional['ExecutionEngine'] = None
        # REMOVED: _legacy_websocket_bridge caching - factory pattern creates isolated instances
        
        # Migration tracking
        self.metrics = MigrationMetrics()
        self._metrics_lock = asyncio.Lock()
        
        # Route-specific feature flags for gradual migration
        self._route_feature_flags: Dict[str, bool] = {}
        self._route_lock = asyncio.Lock()
        
        # Active contexts tracking for cleanup
        self._active_contexts: Dict[str, 'UserExecutionContext'] = {}
        self._contexts_lock = asyncio.Lock()
        
        logger.info(f"FactoryAdapter initialized - Migration mode: {self.config.migration_mode.value}")
        
    async def get_execution_engine(self, 
                                 request_context: Optional[Dict[str, Any]] = None,
                                 route_path: Optional[str] = None,
                                 **legacy_kwargs) -> Union['IsolatedExecutionEngine', 'ExecutionEngine']:
        """
        Get execution engine - factory or legacy based on configuration and route.
        
        Args:
            request_context: Request context for factory pattern (user_id, request_id, etc.)
            route_path: Route path for route-specific feature flags
            **legacy_kwargs: Legacy parameters for backward compatibility
            
        Returns:
            Either IsolatedExecutionEngine (factory) or ExecutionEngine (legacy)
        """
        start_time = time.time()
        
        try:
            # Determine whether to use factory pattern
            use_factory = await self._should_use_factory(route_path, request_context)
            
            if use_factory and request_context:
                return await self._get_factory_execution_engine(request_context)
            else:
                return await self._get_legacy_execution_engine(**legacy_kwargs)
                
        finally:
            # Update metrics
            await self._update_metrics('execution_engine', time.time() - start_time, use_factory if 'use_factory' in locals() else False)
            
    async def _should_use_factory(self, route_path: Optional[str], request_context: Optional[Dict[str, Any]]) -> bool:
        """Determine whether to use factory pattern based on configuration and context."""
        
        # Check migration mode
        if self.config.migration_mode == MigrationMode.LEGACY_ONLY:
            return False
        elif self.config.migration_mode == MigrationMode.FACTORY_ONLY:
            return True
        elif self.config.migration_mode == MigrationMode.FACTORY_PREFERRED:
            # Use factory if request context available, otherwise legacy
            return request_context is not None
        elif self.config.migration_mode == MigrationMode.GRADUAL:
            # Check route-specific feature flags
            if route_path:
                async with self._route_lock:
                    return self._route_feature_flags.get(route_path, False)
            return False
        
        return False
        
    async def _get_factory_execution_engine(self, request_context: Dict[str, Any]) -> 'IsolatedExecutionEngine':
        """Get execution engine using factory pattern."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        start_time = time.time()
        
        try:
            # Create user execution context
            user_context = UserExecutionContext(
                user_id=request_context.get('user_id'),
                request_id=request_context.get('request_id', str(uuid.uuid4())),
                thread_id=request_context.get('thread_id', f"thread_{int(time.time())}")
            )
            
            # Create isolated execution engine
            engine = await self._execution_engine_factory.create_execution_engine(user_context)
            
            # Track active context for cleanup
            async with self._contexts_lock:
                self._active_contexts[user_context.request_id] = user_context
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            if self.config.enable_migration_logging:
                logger.info(f" PASS:  Factory execution engine created for user {user_context.user_id} in {creation_time_ms:.1f}ms")
            
            async with self._metrics_lock:
                self.metrics.factory_calls_count += 1
                self.metrics.factory_successes_count += 1
                self.metrics.total_requests_count += 1
                
                # Update average time
                if self.metrics.factory_successes_count == 1:
                    self.metrics.factory_avg_time_ms = creation_time_ms
                else:
                    current_avg = self.metrics.factory_avg_time_ms
                    count = self.metrics.factory_successes_count
                    self.metrics.factory_avg_time_ms = ((current_avg * (count - 1)) + creation_time_ms) / count
            
            return engine
            
        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Factory execution engine creation failed in {creation_time_ms:.1f}ms: {e}"
            logger.error(error_msg)
            
            # Track error
            async with self._metrics_lock:
                self.metrics.factory_calls_count += 1
                self.metrics.factory_failures_count += 1
                self.metrics.total_requests_count += 1
                self.metrics.recent_factory_errors.append(f"{datetime.now(timezone.utc).isoformat()}: {error_msg}")
                if len(self.metrics.recent_factory_errors) > 10:
                    self.metrics.recent_factory_errors.pop(0)
            
            # Fallback to legacy if enabled
            if self.config.legacy_fallback_enabled:
                logger.warning(" CYCLE:  Falling back to legacy execution engine due to factory failure")
                async with self._metrics_lock:
                    self.metrics.fallback_to_legacy_count += 1
                
                # Extract legacy parameters from request context
                legacy_kwargs = {
                    'registry': request_context.get('registry'),
                    'websocket_bridge': request_context.get('websocket_bridge')
                }
                return await self._get_legacy_execution_engine(**legacy_kwargs)
            else:
                raise RuntimeError(f"Factory execution engine creation failed: {e}")
                
    async def _get_legacy_execution_engine(self, **legacy_kwargs) -> 'ExecutionEngine':
        """Get execution engine using legacy singleton pattern."""
        start_time = time.time()
        
        try:
            if not self._legacy_execution_engine:
                # Create legacy engine with passed parameters
                registry = legacy_kwargs.get('registry')
                websocket_bridge = legacy_kwargs.get('websocket_bridge')
                
                if not registry or not websocket_bridge:
                    # Try to get legacy WebSocket bridge if not provided
                    if not websocket_bridge:
                        websocket_bridge = await self._get_legacy_websocket_bridge()
                    
                    if not registry:
                        raise ValueError("Legacy mode requires 'registry' parameter")
                
                from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory
                unified_factory = UnifiedExecutionEngineFactory()
                self._legacy_execution_engine = await unified_factory.create_execution_engine(
                    registry=registry, 
                    websocket_bridge=websocket_bridge
                )
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            if self.config.log_legacy_calls:
                logger.warning(f" WARNING: [U+FE0F] Legacy execution engine used - consider migrating to factory pattern (created in {creation_time_ms:.1f}ms)")
            
            # Update metrics
            async with self._metrics_lock:
                self.metrics.legacy_calls_count += 1
                self.metrics.total_requests_count += 1
                
                # Update average time
                if self.metrics.legacy_calls_count == 1:
                    self.metrics.legacy_avg_time_ms = creation_time_ms
                else:
                    current_avg = self.metrics.legacy_avg_time_ms
                    count = self.metrics.legacy_calls_count
                    self.metrics.legacy_avg_time_ms = ((current_avg * (count - 1)) + creation_time_ms) / count
            
            return self._legacy_execution_engine
            
        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Legacy execution engine creation failed in {creation_time_ms:.1f}ms: {e}"
            logger.error(error_msg)
            
            # Track error
            async with self._metrics_lock:
                self.metrics.recent_legacy_errors.append(f"{datetime.now(timezone.utc).isoformat()}: {error_msg}")
                if len(self.metrics.recent_legacy_errors) > 10:
                    self.metrics.recent_legacy_errors.pop(0)
            
            raise RuntimeError(f"Legacy execution engine creation failed: {e}")
            
    async def get_websocket_bridge(self, 
                                 request_context: Optional[Dict[str, Any]] = None,
                                 route_path: Optional[str] = None,
                                 **legacy_kwargs) -> Union['UserWebSocketEmitter', 'AgentWebSocketBridge']:
        """
        Get WebSocket bridge - factory or legacy based on configuration.
        
        Args:
            request_context: Request context for factory pattern
            route_path: Route path for route-specific feature flags
            **legacy_kwargs: Legacy parameters for backward compatibility
            
        Returns:
            Either UserWebSocketEmitter (factory) or AgentWebSocketBridge (legacy)
        """
        start_time = time.time()
        
        try:
            # Determine whether to use factory pattern
            use_factory = await self._should_use_factory(route_path, request_context)
            
            if use_factory and request_context:
                return await self._get_factory_websocket_bridge(request_context)
            else:
                return await self._get_legacy_websocket_bridge(**legacy_kwargs)
                
        finally:
            # Update metrics
            await self._update_metrics('websocket_bridge', time.time() - start_time, use_factory if 'use_factory' in locals() else False)
            
    async def _get_factory_websocket_bridge(self, request_context: Dict[str, Any]) -> 'UserWebSocketEmitter':
        """Get WebSocket bridge using factory pattern."""
        start_time = time.time()
        
        try:
            # Create user-specific emitter
            user_id = request_context.get('user_id')
            thread_id = request_context.get('thread_id', f"thread_{user_id}")
            connection_id = request_context.get('connection_id', f"conn_{user_id}")
            
            emitter = await self._websocket_bridge_factory.create_user_emitter(
                user_id, thread_id, connection_id
            )
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            if self.config.enable_migration_logging:
                logger.info(f" PASS:  Factory WebSocket emitter created for user {user_id} in {creation_time_ms:.1f}ms")
            
            return emitter
            
        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Factory WebSocket emitter creation failed in {creation_time_ms:.1f}ms: {e}"
            logger.error(error_msg)
            
            # Fallback to legacy if enabled
            if self.config.legacy_fallback_enabled:
                logger.warning(" CYCLE:  Falling back to legacy WebSocket bridge due to factory failure")
                return await self._get_legacy_websocket_bridge()
            else:
                raise RuntimeError(f"Factory WebSocket emitter creation failed: {e}")
                
    async def _get_legacy_websocket_bridge(self, **legacy_kwargs) -> 'AgentWebSocketBridge':
        """Get WebSocket bridge using factory pattern (FIXED: removed singleton usage)."""
        start_time = time.time()
        
        try:
            # CRITICAL FIX: Always create new instances instead of using singleton
            # Import here to avoid circular imports
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            import uuid
            
            # Create a user context for the factory method
            # Try to extract from legacy_kwargs if available, otherwise use defaults
            user_id = legacy_kwargs.get('user_id', f"legacy_user_{uuid.uuid4()}")
            request_id = legacy_kwargs.get('request_id', f"legacy_req_{uuid.uuid4()}")
            thread_id = legacy_kwargs.get('thread_id', f"legacy_thread_{uuid.uuid4()}")
            
            # Create user context for factory pattern
            user_context = UserExecutionContext(
                user_id=user_id,
                request_id=request_id,
                thread_id=thread_id
            )
            
            # CRITICAL: Use factory method with user context for proper isolation
            # Pass the user_context to ensure complete isolation
            # Fix: create_agent_websocket_bridge is synchronous, not async
            bridge = create_agent_websocket_bridge(user_context)
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            if self.config.log_legacy_calls:
                logger.warning(f" WARNING: [U+FE0F] Legacy WebSocket bridge using factory pattern for user {user_id} (created in {creation_time_ms:.1f}ms)")
            
            return bridge
            
        except Exception as e:
            creation_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Legacy WebSocket bridge creation failed in {creation_time_ms:.1f}ms: {e}"
            logger.error(error_msg)
            raise RuntimeError(f"Legacy WebSocket bridge creation failed: {e}")
            
    async def _update_metrics(self, component_type: str, execution_time: float, used_factory: bool) -> None:
        """Update performance metrics."""
        if not self.config.track_migration_metrics:
            return
            
        # This method can be extended to track component-specific metrics
        # For now, metrics are updated in the individual methods
        pass
    
    # Route-specific feature flag management
    
    async def enable_factory_for_route(self, route_path: str) -> None:
        """Enable factory pattern for specific route."""
        async with self._route_lock:
            self._route_feature_flags[route_path] = True
            logger.info(f" PASS:  Factory pattern enabled for route: {route_path}")
    
    async def disable_factory_for_route(self, route_path: str) -> None:
        """Disable factory pattern for specific route."""
        async with self._route_lock:
            self._route_feature_flags[route_path] = False
            logger.info(f" WARNING: [U+FE0F] Factory pattern disabled for route: {route_path}")
    
    async def enable_factory_pattern_globally(self) -> None:
        """Enable factory pattern globally."""
        self.config.migration_mode = MigrationMode.FACTORY_PREFERRED
        logger.info(" PASS:  Factory pattern enabled globally")
    
    async def disable_factory_pattern_globally(self) -> None:
        """Disable factory pattern globally (use legacy only)."""
        self.config.migration_mode = MigrationMode.LEGACY_ONLY
        logger.info(" WARNING: [U+FE0F] Factory pattern disabled globally - using legacy mode")
    
    # Migration status and metrics
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status and metrics."""
        return {
            'migration_mode': self.config.migration_mode.value,
            'metrics': {
                'total_requests': self.metrics.total_requests_count,
                'factory_calls': self.metrics.factory_calls_count,
                'legacy_calls': self.metrics.legacy_calls_count,
                'factory_successes': self.metrics.factory_successes_count,
                'factory_failures': self.metrics.factory_failures_count,
                'fallback_to_legacy': self.metrics.fallback_to_legacy_count,
                'migration_progress_pct': round(self.metrics.get_migration_progress(), 2),
                'factory_success_rate_pct': round(self.metrics.get_factory_success_rate(), 2),
                'factory_avg_time_ms': round(self.metrics.factory_avg_time_ms, 2),
                'legacy_avg_time_ms': round(self.metrics.legacy_avg_time_ms, 2)
            },
            'route_flags': self._route_feature_flags.copy(),
            'active_contexts': len(self._active_contexts),
            'config': {
                'legacy_fallback_enabled': self.config.legacy_fallback_enabled,
                'migration_logging_enabled': self.config.enable_migration_logging,
                'legacy_call_logging': self.config.log_legacy_calls
            },
            'recent_errors': {
                'factory_errors': self.metrics.recent_factory_errors[-5:],
                'legacy_errors': self.metrics.recent_legacy_errors[-5:]
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def cleanup_context(self, request_id: str) -> None:
        """Clean up a specific user context."""
        async with self._contexts_lock:
            if request_id in self._active_contexts:
                context = self._active_contexts.pop(request_id)
                await context.cleanup()
                logger.debug(f"Factory adapter context cleaned for request {request_id}")
    
    async def cleanup_all_contexts(self) -> None:
        """Clean up all active user contexts."""
        async with self._contexts_lock:
            cleanup_tasks = []
            for request_id, context in self._active_contexts.items():
                cleanup_tasks.append(context.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self._active_contexts.clear()
            logger.info("All factory adapter contexts cleaned up")


# Utility functions for creating request contexts

def create_request_context(user_id: str, 
                          thread_id: Optional[str] = None, 
                          request_id: Optional[str] = None,
                          connection_id: Optional[str] = None,
                          **additional_context) -> Dict[str, Any]:
    """
    Create a standardized request context for factory patterns.
    
    Args:
        user_id: Unique user identifier
        thread_id: Optional thread identifier (auto-generated if not provided)
        request_id: Optional request identifier (auto-generated if not provided)
        connection_id: Optional WebSocket connection identifier
        **additional_context: Additional context fields
        
    Returns:
        Dictionary with standardized request context
    """
    context = {
        'user_id': user_id,
        'request_id': request_id or str(uuid.uuid4()),
        'thread_id': thread_id or f"thread_{user_id}_{int(time.time())}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **additional_context
    }
    
    if connection_id:
        context['connection_id'] = connection_id
    
    return context


async def migrate_to_factory_pattern(app, 
                                   enable_gradually: bool = True,
                                   target_routes: Optional[List[str]] = None) -> None:
    """
    Helper function to migrate existing routes to factory pattern.
    
    Args:
        app: FastAPI application instance
        enable_gradually: Whether to enable gradually by route
        target_routes: Specific routes to migrate (None = all routes)
    """
    adapter: FactoryAdapter = getattr(app.state, 'factory_adapter', None)
    if not adapter:
        logger.error("FactoryAdapter not found in app.state - ensure it's configured during startup")
        return
    
    if enable_gradually and target_routes:
        # Enable for specific routes
        for route_path in target_routes:
            await adapter.enable_factory_for_route(route_path)
            logger.info(f" PASS:  Factory pattern enabled for route: {route_path}")
    elif enable_gradually:
        # Enable for common routes
        default_routes = [
            "/api/agents/execute",
            "/api/agents/status", 
            "/ws"
        ]
        for route_path in default_routes:
            await adapter.enable_factory_for_route(route_path)
            logger.info(f" PASS:  Factory pattern enabled for route: {route_path}")
    else:
        # Enable globally
        await adapter.enable_factory_pattern_globally()
        logger.info(" PASS:  Factory pattern enabled globally")
    
    # Log migration status
    status = adapter.get_migration_status()
    logger.info(f" CHART:  Migration status: {status['metrics']['migration_progress_pct']}% factory adoption")


# Migration helper for dependency injection

def get_adapter_dependencies(adapter: FactoryAdapter, request_context: Dict[str, Any]):
    """
    Get adapter dependencies for dependency injection in FastAPI routes.
    
    This helper function provides the appropriate execution engine and WebSocket bridge
    based on the adapter configuration and request context.
    """
    async def get_execution_engine():
        return await adapter.get_execution_engine(request_context=request_context)
    
    async def get_websocket_bridge():
        return await adapter.get_websocket_bridge(request_context=request_context)
    
    return {
        'execution_engine': get_execution_engine,
        'websocket_bridge': get_websocket_bridge
    }