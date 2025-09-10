"""ToolExecutorFactory for creating request-scoped tool execution environments.

This module provides the ToolExecutorFactory class that creates isolated
tool execution environments per request, eliminating global state issues.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Isolation
- Value Impact: Ensures proper tool executor creation with user context isolation
- Strategic Impact: Enables reliable factory pattern for concurrent tool execution

Key Architecture Principles:
- Factory pattern for consistent creation
- Per-request WebSocket event emitter integration
- Automatic dependency injection and validation
- Thread-safe executor creation
- Comprehensive error handling and logging
- Resource lifecycle management

The ToolExecutorFactory provides a centralized way to create properly configured
tool execution environments with complete user isolation and WebSocket integration.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.core.tools.unified_tool_dispatcher import RequestScopedToolDispatcher
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.websocket_core import (
    WebSocketEventEmitter,
)
# WebSocketEventEmitterFactory is actually UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitterFactory
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ToolExecutorFactory:
    """Factory for creating request-scoped tool execution environments.
    
    This factory creates properly configured tool execution environments with:
    - Request-scoped UnifiedToolExecutionEngine instances
    - Isolated WebSocket event emitters bound to user context
    - Proper dependency injection and validation
    - Automatic resource lifecycle management
    - Thread-safe creation patterns
    
    Key Features:
    - Creates isolated tool executors per request
    - Integrates WebSocket events for correct user routing
    - Validates user context for security
    - Handles dependency resolution automatically
    - Provides both direct and scoped creation patterns
    - Comprehensive error handling and logging
    
    Business Value:
    - Eliminates tool execution context leakage between users
    - Enables reliable concurrent tool execution
    - Provides consistent creation patterns across the application
    - Simplifies testing and dependency management
    """
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        """Initialize the tool executor factory.
        
        Args:
            websocket_manager: Optional WebSocket manager for event emission
        """
        self.websocket_manager = websocket_manager
        self.factory_id = f"factory_{int(time.time() * 1000)}"
        self.created_at = datetime.now(timezone.utc)
        
        # Factory metrics
        self._metrics = {
            'executors_created': 0,
            'dispatchers_created': 0,
            'failed_creations': 0,
            'active_instances': 0,
            'last_creation_time': None
        }
        
        logger.info(f"🏭 ToolExecutorFactory {self.factory_id} initialized")
    
    async def create_tool_executor(
        self,
        user_context: UserExecutionContext,
        websocket_manager: Optional['WebSocketManager'] = None
    ) -> UnifiedToolExecutionEngine:
        """Create a request-scoped UnifiedToolExecutionEngine.
        
        Args:
            user_context: User execution context for isolation
            websocket_manager: Optional WebSocket manager (uses factory default if None)
            
        Returns:
            UnifiedToolExecutionEngine: Isolated tool executor for this request
            
        Raises:
            ValueError: If user_context is invalid or dependencies are unavailable
        """
        # Validate user context
        user_context = validate_user_context(user_context)
        
        try:
            start_time = time.time()
            
            # Use provided manager or factory default
            ws_manager = websocket_manager or self.websocket_manager
            
            # Create WebSocket event emitter for this request if manager available
            websocket_bridge = None
            if ws_manager:
                websocket_emitter = await WebSocketEventEmitterFactory.create_emitter(
                    user_context, ws_manager
                )
                # Create adapter for backward compatibility
                from netra_backend.app.core.tools.unified_tool_dispatcher import WebSocketBridgeAdapter
                websocket_bridge = WebSocketBridgeAdapter(websocket_emitter, user_context)
                logger.debug(f"🔌 Created WebSocket bridge adapter for {user_context.get_correlation_id()}")
            else:
                logger.warning(f"⚠️ No WebSocket manager available for {user_context.get_correlation_id()} - events will be disabled")
            
            # Create isolated tool executor
            executor = UnifiedToolExecutionEngine(websocket_bridge=websocket_bridge)
            
            # Update metrics
            creation_time_ms = (time.time() - start_time) * 1000
            self._metrics['executors_created'] += 1
            self._metrics['active_instances'] += 1
            self._metrics['last_creation_time'] = datetime.now(timezone.utc)
            
            logger.info(f"🔧 Created UnifiedToolExecutionEngine for {user_context.get_correlation_id()} "
                       f"in {creation_time_ms:.1f}ms (WebSocket: {'enabled' if websocket_bridge else 'disabled'})")
            
            return executor
            
        except Exception as e:
            self._metrics['failed_creations'] += 1
            logger.error(f"🚨 Failed to create tool executor for {user_context.get_correlation_id()}: {e}")
            raise ValueError(f"Failed to create tool executor: {e}")
    
    async def create_request_scoped_dispatcher(
        self,
        user_context: UserExecutionContext,
        tools: List[Any] = None,
        websocket_manager: Optional['WebSocketManager'] = None
    ) -> RequestScopedToolDispatcher:
        """Create a request-scoped tool dispatcher with integrated WebSocket events.
        
        Args:
            user_context: User execution context for isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager (uses factory default if None)
            
        Returns:
            RequestScopedToolDispatcher: Isolated tool dispatcher for this request
            
        Raises:
            ValueError: If user_context is invalid or dependencies are unavailable
        """
        # Validate user context
        user_context = validate_user_context(user_context)
        
        try:
            start_time = time.time()
            
            # Use provided manager or factory default
            ws_manager = websocket_manager or self.websocket_manager
            
            # Create WebSocket event emitter for this request if manager available
            websocket_emitter = None
            if ws_manager:
                websocket_emitter = await WebSocketEventEmitterFactory.create_emitter(
                    user_context, ws_manager
                )
                logger.debug(f"🔌 Created WebSocket emitter for {user_context.get_correlation_id()}")
            else:
                logger.warning(f"⚠️ No WebSocket manager available for {user_context.get_correlation_id()} - events will be disabled")
            
            # Create request-scoped dispatcher
            dispatcher = RequestScopedToolDispatcher(
                user_context=user_context,
                tools=tools,
                websocket_emitter=websocket_emitter
            )
            
            # Update metrics
            creation_time_ms = (time.time() - start_time) * 1000
            self._metrics['dispatchers_created'] += 1
            self._metrics['active_instances'] += 1
            self._metrics['last_creation_time'] = datetime.now(timezone.utc)
            
            logger.info(f"📦 Created RequestScopedToolDispatcher for {user_context.get_correlation_id()} "
                       f"in {creation_time_ms:.1f}ms (WebSocket: {'enabled' if websocket_emitter else 'disabled'})")
            
            return dispatcher
            
        except Exception as e:
            self._metrics['failed_creations'] += 1
            logger.error(f"🚨 Failed to create request-scoped dispatcher for {user_context.get_correlation_id()}: {e}")
            raise ValueError(f"Failed to create request-scoped dispatcher: {e}")
    
    @asynccontextmanager
    async def create_scoped_tool_executor(
        self,
        user_context: UserExecutionContext,
        websocket_manager: Optional['WebSocketManager'] = None
    ):
        """Create scoped UnifiedToolExecutionEngine with automatic cleanup.
        
        This is the recommended way to create tool executors as it ensures proper
        resource cleanup even if exceptions occur.
        
        Args:
            user_context: User execution context for isolation
            websocket_manager: Optional WebSocket manager
            
        Yields:
            UnifiedToolExecutionEngine: Tool executor with automatic cleanup
            
        Example:
            async with factory.create_scoped_tool_executor(context) as executor:
                result = await executor.execute_tool_with_input(tool_input, tool, kwargs)
                # Automatic cleanup happens here
        """
        executor = None
        try:
            executor = await self.create_tool_executor(user_context, websocket_manager)
            logger.debug(f"📦 SCOPED EXECUTOR: {user_context.get_correlation_id()} created with auto-cleanup")
            yield executor
        finally:
            if executor:
                # Clean up any resources (currently UnifiedToolExecutionEngine doesn't need explicit cleanup)
                self._metrics['active_instances'] -= 1
                logger.debug(f"📦 SCOPED EXECUTOR: {user_context.get_correlation_id()} disposed")
    
    @asynccontextmanager
    async def create_scoped_dispatcher(
        self,
        user_context: UserExecutionContext,
        tools: List[Any] = None,
        websocket_manager: Optional['WebSocketManager'] = None
    ):
        """Create scoped RequestScopedToolDispatcher with automatic cleanup.
        
        This is the recommended way to create dispatchers as it ensures proper
        resource cleanup even if exceptions occur.
        
        Args:
            user_context: User execution context for isolation
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager
            
        Yields:
            RequestScopedToolDispatcher: Tool dispatcher with automatic cleanup
            
        Example:
            async with factory.create_scoped_dispatcher(context) as dispatcher:
                result = await dispatcher.dispatch("my_tool", param1="value1")
                # Automatic cleanup happens here
        """
        dispatcher = None
        try:
            dispatcher = await self.create_request_scoped_dispatcher(
                user_context, tools, websocket_manager
            )
            logger.debug(f"📦 SCOPED DISPATCHER: {user_context.get_correlation_id()} created with auto-cleanup")
            yield dispatcher
        finally:
            if dispatcher:
                await dispatcher.cleanup()
                self._metrics['active_instances'] -= 1
                logger.debug(f"📦 SCOPED DISPATCHER: {user_context.get_correlation_id()} disposed")
    
    def set_websocket_manager(self, websocket_manager: 'WebSocketManager') -> None:
        """Set the default WebSocket manager for this factory.
        
        Args:
            websocket_manager: WebSocket manager to use as default
        """
        self.websocket_manager = websocket_manager
        logger.info(f"🔌 Set WebSocket manager for ToolExecutorFactory {self.factory_id}")
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get factory metrics for monitoring and debugging.
        
        Returns:
            Dictionary with factory metrics and statistics
        """
        uptime_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        return {
            **self._metrics,
            'factory_id': self.factory_id,
            'uptime_seconds': uptime_seconds,
            'has_websocket_manager': self.websocket_manager is not None,
            'success_rate': (
                (self._metrics['executors_created'] + self._metrics['dispatchers_created']) /
                max(1, self._metrics['executors_created'] + self._metrics['dispatchers_created'] + self._metrics['failed_creations'])
            ),
            'created_at': self.created_at.isoformat()
        }
    
    async def validate_factory_health(self) -> Dict[str, Any]:
        """Validate factory health by attempting to create test instances.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issues': [],
            'factory_metrics': self.get_factory_metrics()
        }
        
        try:
            # Create test user context
            test_context = UserExecutionContext(
                user_id="health_check_user",
                thread_id="health_check_thread",
                run_id="health_check_run"
            )
            
            # Test executor creation
            start_time = time.time()
            try:
                async with self.create_scoped_tool_executor(test_context) as executor:
                    executor_creation_time = time.time() - start_time
                    if executor_creation_time > 1.0:  # Should be fast
                        health_status['issues'].append(f"Slow executor creation: {executor_creation_time:.2f}s")
                        health_status['status'] = 'degraded'
            except Exception as e:
                health_status['issues'].append(f"Executor creation failed: {e}")
                health_status['status'] = 'unhealthy'
            
            # Test dispatcher creation
            start_time = time.time()
            try:
                async with self.create_scoped_dispatcher(test_context) as dispatcher:
                    dispatcher_creation_time = time.time() - start_time
                    if dispatcher_creation_time > 1.0:  # Should be fast
                        health_status['issues'].append(f"Slow dispatcher creation: {dispatcher_creation_time:.2f}s")
                        if health_status['status'] == 'healthy':
                            health_status['status'] = 'degraded'
            except Exception as e:
                health_status['issues'].append(f"Dispatcher creation failed: {e}")
                health_status['status'] = 'unhealthy'
            
            # Check for too many active instances (potential memory leak)
            if self._metrics['active_instances'] > 50:
                health_status['issues'].append(f"High active instances: {self._metrics['active_instances']}")
                health_status['status'] = 'degraded'
            
            # Check success rate
            if self.get_factory_metrics()['success_rate'] < 0.95:
                health_status['issues'].append(f"Low success rate: {self.get_factory_metrics()['success_rate']:.2%}")
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['issues'].append(f"Health check failed: {e}")
            health_status['status'] = 'unhealthy'
        
        return health_status


# Global factory instance for shared usage
_global_tool_executor_factory: Optional[ToolExecutorFactory] = None


def get_tool_executor_factory() -> ToolExecutorFactory:
    """Get the global ToolExecutorFactory instance.
    
    Returns:
        ToolExecutorFactory: Global factory instance
    """
    global _global_tool_executor_factory
    if _global_tool_executor_factory is None:
        _global_tool_executor_factory = ToolExecutorFactory()
        logger.info("🏭 Created global ToolExecutorFactory instance")
    return _global_tool_executor_factory


def set_tool_executor_factory_websocket_manager(websocket_manager: 'WebSocketManager') -> None:
    """Set WebSocket manager on the global factory.
    
    Args:
        websocket_manager: WebSocket manager to configure
    """
    factory = get_tool_executor_factory()
    factory.set_websocket_manager(websocket_manager)


# Convenience functions for easy usage

async def create_isolated_tool_executor(
    user_context: UserExecutionContext,
    websocket_manager: Optional['WebSocketManager'] = None
) -> UnifiedToolExecutionEngine:
    """Convenience function to create an isolated tool executor.
    
    Args:
        user_context: User execution context
        websocket_manager: Optional WebSocket manager
        
    Returns:
        UnifiedToolExecutionEngine: Isolated tool executor
    """
    factory = get_tool_executor_factory()
    return await factory.create_tool_executor(user_context, websocket_manager)


async def create_isolated_tool_dispatcher(
    user_context: UserExecutionContext,
    tools: List[Any] = None,
    websocket_manager: Optional['WebSocketManager'] = None
) -> RequestScopedToolDispatcher:
    """Convenience function to create an isolated tool dispatcher.
    
    Args:
        user_context: User execution context
        tools: Optional list of tools to register initially
        websocket_manager: Optional WebSocket manager
        
    Returns:
        RequestScopedToolDispatcher: Isolated tool dispatcher
    """
    factory = get_tool_executor_factory()
    return await factory.create_request_scoped_dispatcher(user_context, tools, websocket_manager)


@asynccontextmanager
async def isolated_tool_executor_scope(
    user_context: UserExecutionContext,
    websocket_manager: Optional['WebSocketManager'] = None
):
    """Convenience context manager for scoped tool executor.
    
    Args:
        user_context: User execution context
        websocket_manager: Optional WebSocket manager
        
    Yields:
        UnifiedToolExecutionEngine: Tool executor with automatic cleanup
    """
    factory = get_tool_executor_factory()
    async with factory.create_scoped_tool_executor(user_context, websocket_manager) as executor:
        yield executor


@asynccontextmanager
async def isolated_tool_dispatcher_scope(
    user_context: UserExecutionContext,
    tools: List[Any] = None,
    websocket_manager: Optional['WebSocketManager'] = None
):
    """Convenience context manager for scoped tool dispatcher.
    
    Args:
        user_context: User execution context
        tools: Optional list of tools to register initially
        websocket_manager: Optional WebSocket manager
        
    Yields:
        RequestScopedToolDispatcher: Tool dispatcher with automatic cleanup
    """
    factory = get_tool_executor_factory()
    async with factory.create_scoped_dispatcher(user_context, tools, websocket_manager) as dispatcher:
        yield dispatcher