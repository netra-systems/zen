"""ExecutionEngineFactory for creating and managing UserExecutionEngine instances.

This module provides the ExecutionEngineFactory class that creates UserExecutionEngine
instances per request and manages their lifecycle with proper cleanup.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Scalability  
- Value Impact: Enables safe concurrent user handling with automatic resource management
- Strategic Impact: Essential infrastructure for production multi-tenant deployment

Key Features:
- Creates UserExecutionEngine instances per request
- Manages lifecycle and cleanup automatically
- Provides context managers for safe usage
- Tracks active engines for monitoring
- Handles resource limits per user
- Automatic cleanup of inactive engines
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory,
    UserWebSocketEmitter
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngineFactoryError(Exception):
    """Raised when execution engine factory operations fail."""
    pass


class ExecutionEngineFactory:
    """Factory for creating and managing UserExecutionEngine instances.
    
    This factory provides:
    - Per-request UserExecutionEngine creation
    - Lifecycle management with automatic cleanup
    - Context managers for safe resource usage
    - Monitoring of active engines
    - Resource limit enforcement
    - Automatic cleanup of stale engines
    
    Design Pattern:
    This follows the "Factory + Registry" pattern where the factory creates
    engines and maintains a registry for lifecycle management. Each engine
    is completely isolated per user request.
    """
    
    def __init__(self):
        """Initialize the execution engine factory."""
        # Active engines registry for lifecycle management
        self._active_engines: Dict[str, UserExecutionEngine] = {}
        self._engine_lock = asyncio.Lock()
        
        # Factory configuration
        self._max_engines_per_user = 2  # Prevent resource exhaustion
        self._engine_timeout_seconds = 300  # 5 minutes max engine lifetime
        self._cleanup_interval = 60  # Cleanup check every minute
        
        # Factory metrics
        self._factory_metrics = {
            'total_engines_created': 0,
            'total_engines_cleaned': 0,
            'active_engines_count': 0,
            'creation_errors': 0,
            'cleanup_errors': 0,
            'timeout_cleanups': 0,
            'user_limit_rejections': 0
        }
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info("ExecutionEngineFactory initialized")
    
    async def create_for_user(self, context: UserExecutionContext) -> UserExecutionEngine:
        """Create UserExecutionEngine for specific user.
        
        This method creates a completely isolated execution engine for a user
        with proper resource limits and lifecycle management.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            UserExecutionEngine: Isolated execution engine for the user
            
        Raises:
            ExecutionEngineFactoryError: If engine creation fails
            InvalidContextError: If user context is invalid
        """
        # Validate user context
        try:
            validated_context = validate_user_context(context)
        except (TypeError, InvalidContextError) as e:
            logger.error(f"Invalid user context for engine creation: {e}")
            raise ExecutionEngineFactoryError(f"Invalid user context: {e}")
        
        start_time = time.time()
        engine_key = f"{validated_context.user_id}_{validated_context.run_id}_{int(time.time() * 1000)}"
        
        try:
            async with self._engine_lock:
                # Check per-user engine limits
                await self._enforce_user_engine_limits(validated_context.user_id)
                
                # Get agent factory instance (configured globally)
                agent_factory = get_agent_instance_factory()
                if not agent_factory:
                    raise ExecutionEngineFactoryError("AgentInstanceFactory not available")
                
                # Create user WebSocket emitter via factory
                websocket_emitter = await self._create_user_websocket_emitter(
                    validated_context, agent_factory
                )
                
                # Create UserExecutionEngine
                logger.info(f"Creating UserExecutionEngine for user {validated_context.user_id} "
                           f"(run_id: {validated_context.run_id})")
                
                engine = UserExecutionEngine(
                    context=validated_context,
                    agent_factory=agent_factory,
                    websocket_emitter=websocket_emitter
                )
                
                # Register engine for lifecycle management
                self._active_engines[engine_key] = engine
                
                # Update metrics
                self._factory_metrics['total_engines_created'] += 1
                self._factory_metrics['active_engines_count'] = len(self._active_engines)
                
                # Start cleanup task if not running
                if not self._cleanup_task:
                    self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                
                creation_time = (time.time() - start_time) * 1000
                logger.info(f"✅ Created UserExecutionEngine {engine.engine_id} "
                           f"in {creation_time:.1f}ms (user: {validated_context.user_id})")
                
                return engine
                
        except Exception as e:
            self._factory_metrics['creation_errors'] += 1
            logger.error(f"Failed to create UserExecutionEngine for user {validated_context.user_id}: {e}")
            raise ExecutionEngineFactoryError(f"Engine creation failed: {e}")
    
    async def _enforce_user_engine_limits(self, user_id: str) -> None:
        """Enforce per-user engine limits to prevent resource exhaustion.
        
        Args:
            user_id: User identifier
            
        Raises:
            ExecutionEngineFactoryError: If user has too many active engines
        """
        # Count active engines for this user
        user_engine_count = sum(
            1 for engine in self._active_engines.values()
            if engine.is_active() and engine.get_user_context().user_id == user_id
        )
        
        if user_engine_count >= self._max_engines_per_user:
            self._factory_metrics['user_limit_rejections'] += 1
            raise ExecutionEngineFactoryError(
                f"User {user_id} has reached maximum engine limit "
                f"({user_engine_count}/{self._max_engines_per_user})"
            )
        
        logger.debug(f"User {user_id} engine count: {user_engine_count}/{self._max_engines_per_user}")
    
    async def _create_user_websocket_emitter(self, 
                                            context: UserExecutionContext,
                                            agent_factory) -> UserWebSocketEmitter:
        """Create user WebSocket emitter via agent factory.
        
        Args:
            context: User execution context
            agent_factory: Agent instance factory
            
        Returns:
            UserWebSocketEmitter: User-specific WebSocket emitter
            
        Raises:
            ExecutionEngineFactoryError: If emitter creation fails
        """
        try:
            # Get WebSocket bridge from factory
            if not hasattr(agent_factory, '_websocket_bridge') or not agent_factory._websocket_bridge:
                raise ExecutionEngineFactoryError("WebSocket bridge not available in agent factory")
            
            websocket_bridge = agent_factory._websocket_bridge
            
            # Create user WebSocket emitter
            emitter = UserWebSocketEmitter(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                websocket_bridge=websocket_bridge
            )
            
            logger.debug(f"Created UserWebSocketEmitter for user {context.user_id}")
            return emitter
            
        except Exception as e:
            logger.error(f"Failed to create UserWebSocketEmitter: {e}")
            raise ExecutionEngineFactoryError(f"WebSocket emitter creation failed: {e}")
    
    @asynccontextmanager
    async def user_execution_scope(self, context: UserExecutionContext) -> AsyncGenerator[UserExecutionEngine, None]:
        """Context manager for user-scoped execution with automatic cleanup.
        
        This context manager provides:
        - Automatic engine creation for the user
        - Safe execution scope with error handling
        - Guaranteed cleanup even on exceptions
        - Performance and lifecycle tracking
        
        Args:
            context: User execution context
            
        Yields:
            UserExecutionEngine: Isolated engine for the user
            
        Usage:
            async with factory.user_execution_scope(user_context) as engine:
                result = await engine.execute_agent(context, state)
        """
        engine = None
        start_time = time.time()
        
        try:
            # Create engine for user
            engine = await self.create_for_user(context)
            
            logger.info(f"Entering user execution scope for user {context.user_id} "
                       f"(engine: {engine.engine_id})")
            
            yield engine
            
        except Exception as e:
            logger.error(f"Error in user execution scope for user {context.user_id}: {e}")
            raise
            
        finally:
            # Always cleanup engine, even on exceptions
            if engine:
                try:
                    await self.cleanup_engine(engine)
                    
                    total_time = (time.time() - start_time) * 1000
                    logger.info(f"✅ Completed user execution scope for user {context.user_id} "
                               f"in {total_time:.1f}ms")
                               
                except Exception as e:
                    logger.error(f"Error cleaning up user execution scope: {e}")
    
    async def cleanup_engine(self, engine: UserExecutionEngine) -> None:
        """Clean up a specific engine.
        
        Args:
            engine: Engine to clean up
        """
        if not engine:
            return
        
        engine_key = None
        
        try:
            # Find engine key
            async with self._engine_lock:
                for key, active_engine in self._active_engines.items():
                    if active_engine == engine:
                        engine_key = key
                        break
            
            if engine_key:
                logger.debug(f"Cleaning up UserExecutionEngine {engine.engine_id}")
                
                # Cleanup engine resources
                await engine.cleanup()
                
                # Remove from active engines
                async with self._engine_lock:
                    self._active_engines.pop(engine_key, None)
                    self._factory_metrics['total_engines_cleaned'] += 1
                    self._factory_metrics['active_engines_count'] = len(self._active_engines)
                
                logger.info(f"✅ Cleaned up UserExecutionEngine {engine.engine_id}")
            
        except Exception as e:
            self._factory_metrics['cleanup_errors'] += 1
            logger.error(f"Error cleaning up UserExecutionEngine: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for inactive engines."""
        logger.info("Starting ExecutionEngineFactory cleanup loop")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Wait for cleanup interval or shutdown
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self._cleanup_interval
                    )
                    break  # Shutdown event triggered
                    
                except asyncio.TimeoutError:
                    # Timeout reached, perform cleanup
                    await self._cleanup_inactive_engines()
                
        except asyncio.CancelledError:
            logger.info("ExecutionEngineFactory cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in ExecutionEngineFactory cleanup loop: {e}")
        
        logger.info("ExecutionEngineFactory cleanup loop stopped")
    
    async def _cleanup_inactive_engines(self) -> None:
        """Clean up inactive or timed-out engines."""
        if not self._active_engines:
            return
        
        current_time = time.time()
        engines_to_cleanup = []
        
        try:
            async with self._engine_lock:
                # Identify engines to cleanup
                for key, engine in self._active_engines.items():
                    try:
                        # Check if engine is inactive
                        if not engine.is_active():
                            engines_to_cleanup.append((key, engine, "inactive"))
                            continue
                        
                        # Check engine age
                        engine_age = current_time - engine.created_at.timestamp()
                        if engine_age > self._engine_timeout_seconds:
                            engines_to_cleanup.append((key, engine, "timeout"))
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Error checking engine {key}: {e}")
                        engines_to_cleanup.append((key, engine, "error"))
            
            # Cleanup identified engines
            for key, engine, reason in engines_to_cleanup:
                try:
                    logger.info(f"Cleaning up engine {engine.engine_id} (reason: {reason})")
                    
                    await engine.cleanup()
                    
                    async with self._engine_lock:
                        self._active_engines.pop(key, None)
                        self._factory_metrics['total_engines_cleaned'] += 1
                        
                        if reason == "timeout":
                            self._factory_metrics['timeout_cleanups'] += 1
                    
                except Exception as e:
                    logger.error(f"Error during cleanup of engine {key}: {e}")
            
            if engines_to_cleanup:
                async with self._engine_lock:
                    self._factory_metrics['active_engines_count'] = len(self._active_engines)
                
                logger.info(f"Cleaned up {len(engines_to_cleanup)} inactive engines")
                
        except Exception as e:
            logger.error(f"Error in inactive engine cleanup: {e}")
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics.
        
        Returns:
            Dictionary with factory performance and health metrics
        """
        return {
            **self._factory_metrics.copy(),
            'max_engines_per_user': self._max_engines_per_user,
            'engine_timeout_seconds': self._engine_timeout_seconds,
            'cleanup_interval': self._cleanup_interval,
            'active_engine_keys': list(self._active_engines.keys()),
            'cleanup_task_running': self._cleanup_task is not None and not self._cleanup_task.done(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_active_engines_summary(self) -> Dict[str, Any]:
        """Get summary of all active engines.
        
        Returns:
            Dictionary with active engines summary
        """
        engines_summary = {}
        
        try:
            for key, engine in self._active_engines.items():
                try:
                    engines_summary[key] = {
                        'engine_id': engine.engine_id,
                        'user_id': engine.get_user_context().user_id,
                        'run_id': engine.get_user_context().run_id,
                        'is_active': engine.is_active(),
                        'created_at': engine.created_at.isoformat(),
                        'active_runs': len(engine.active_runs),
                        'stats': engine.get_user_execution_stats()
                    }
                except Exception as e:
                    engines_summary[key] = {'error': str(e)}
                    
        except Exception as e:
            logger.error(f"Error getting active engines summary: {e}")
        
        return {
            'total_active_engines': len(self._active_engines),
            'engines': engines_summary,
            'summary_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def shutdown(self) -> None:
        """Shutdown factory and clean up all resources."""
        logger.info("Shutting down ExecutionEngineFactory")
        
        try:
            # Signal cleanup task to stop
            self._shutdown_event.set()
            
            # Wait for cleanup task to finish
            if self._cleanup_task:
                try:
                    await asyncio.wait_for(self._cleanup_task, timeout=10.0)
                except asyncio.TimeoutError:
                    logger.warning("Cleanup task did not finish in time, cancelling")
                    self._cleanup_task.cancel()
                    try:
                        await self._cleanup_task
                    except asyncio.CancelledError:
                        pass
            
            # Cleanup all active engines
            engines_to_cleanup = list(self._active_engines.values())
            if engines_to_cleanup:
                logger.info(f"Cleaning up {len(engines_to_cleanup)} active engines")
                
                for engine in engines_to_cleanup:
                    try:
                        await engine.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up engine during shutdown: {e}")
            
            # Clear state
            self._active_engines.clear()
            
            logger.info("✅ ExecutionEngineFactory shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during ExecutionEngineFactory shutdown: {e}")
            raise


# Singleton factory instance
_factory_instance: Optional[ExecutionEngineFactory] = None
_factory_lock = asyncio.Lock()


async def get_execution_engine_factory() -> ExecutionEngineFactory:
    """Get singleton ExecutionEngineFactory instance.
    
    Returns:
        ExecutionEngineFactory: Configured factory instance
    """
    global _factory_instance
    
    async with _factory_lock:
        if _factory_instance is None:
            _factory_instance = ExecutionEngineFactory()
            logger.info("Created singleton ExecutionEngineFactory instance")
        
        return _factory_instance


# Context manager function for easy usage
@asynccontextmanager
async def user_execution_engine(context: UserExecutionContext) -> AsyncGenerator[UserExecutionEngine, None]:
    """Create user execution engine with automatic cleanup.
    
    This is a convenience function that provides a simple interface for
    creating and managing user execution engines.
    
    Args:
        context: User execution context
        
    Yields:
        UserExecutionEngine: Isolated engine for the user
        
    Usage:
        async with user_execution_engine(user_context) as engine:
            result = await engine.execute_agent(context, state)
    """
    factory = await get_execution_engine_factory()
    async with factory.user_execution_scope(context) as engine:
        yield engine