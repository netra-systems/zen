"""
AgentInstanceFactory - Per-Request Agent Instantiation with Complete Isolation

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Scalability
- Value Impact: Enables 10+ concurrent users with zero context leakage and proper isolation
- Strategic Impact: Critical infrastructure for multi-user production deployment

This factory creates fresh agent instances for each user request with complete isolation:
- Separate WebSocket emitters bound to specific users
- Request-scoped database sessions (no global state)
- User-specific execution contexts and run tracking
- Proper resource cleanup and lifecycle management

CRITICAL: This is the request layer that creates isolated instances for each user request.
No global state is shared between instances. Each user gets their own execution environment.
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type, Union, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class UserExecutionContext:
    """
    Per-request execution context with complete user isolation.
    
    This context contains all user-specific state and ensures no data leakage
    between concurrent users. Each request gets its own isolated context.
    
    Business Value: Enables safe concurrent user operations, prevents data leakage
    """
    user_id: str
    thread_id: str
    run_id: str
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Request-scoped database session (NEVER global!)
    db_session: Optional[AsyncSession] = None
    
    # User-specific execution state (completely isolated)
    active_runs: Dict[str, Any] = field(default_factory=dict)
    run_history: List[Dict[str, Any]] = field(default_factory=list)
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # User-specific WebSocket state
    websocket_emitter: Optional['UserWebSocketEmitter'] = None
    
    # Resource management for cleanup
    cleanup_callbacks: List[Callable[[], Awaitable[None]]] = field(default_factory=list)
    _is_cleaned: bool = False
    
    # Request metadata
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize context after creation."""
        # Initialize execution metrics with user-specific data
        self.execution_metrics = {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'created_at': self.created_at.isoformat(),
            'active_agent_count': 0,
            'completed_agent_count': 0,
            'total_execution_time_ms': 0.0
        }
        
        # Initialize request metadata
        self.request_metadata = {
            'context_id': f"{self.user_id}_{self.thread_id}_{uuid.uuid4().hex[:8]}",
            'isolation_level': 'complete',
            'resource_scope': 'request'
        }
    
    async def cleanup(self) -> None:
        """
        Clean up user-specific resources with comprehensive error handling.
        
        This method ensures all user resources are properly cleaned up
        to prevent memory leaks and resource exhaustion.
        """
        if self._is_cleaned:
            logger.debug(f"Context already cleaned for user {self.user_id}")
            return
        
        logger.info(f"Starting cleanup for user execution context: {self.user_id}")
        cleanup_errors = []
        
        # Execute all cleanup callbacks with error resilience
        for i, callback in enumerate(self.cleanup_callbacks):
            try:
                logger.debug(f"Executing cleanup callback {i+1}/{len(self.cleanup_callbacks)} for user {self.user_id}")
                await callback()
            except Exception as e:
                error_msg = f"Cleanup callback {i+1} failed for user {self.user_id}: {e}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Close database session if present
        if self.db_session:
            try:
                logger.debug(f"Closing database session for user {self.user_id}")
                await self.db_session.close()
                self.db_session = None
            except Exception as e:
                error_msg = f"Failed to close database session for user {self.user_id}: {e}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Clean up WebSocket emitter
        if self.websocket_emitter:
            try:
                logger.debug(f"Cleaning up WebSocket emitter for user {self.user_id}")
                await self.websocket_emitter.cleanup()
                self.websocket_emitter = None
            except Exception as e:
                error_msg = f"Failed to cleanup WebSocket emitter for user {self.user_id}: {e}"
                logger.error(error_msg)
                cleanup_errors.append(error_msg)
        
        # Clear user-specific state collections
        try:
            self.active_runs.clear()
            self.run_history.clear()
            self.cleanup_callbacks.clear()
        except Exception as e:
            error_msg = f"Failed to clear state collections for user {self.user_id}: {e}"
            logger.error(error_msg)
            cleanup_errors.append(error_msg)
        
        self._is_cleaned = True
        
        if cleanup_errors:
            logger.warning(f"Context cleanup completed with {len(cleanup_errors)} errors for user {self.user_id}")
            for error in cleanup_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info(f"Context cleanup completed successfully for user {self.user_id}")
    
    def add_cleanup_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Add a cleanup callback for resource management."""
        if not self._is_cleaned:
            self.cleanup_callbacks.append(callback)
        else:
            logger.warning(f"Cannot add cleanup callback - context already cleaned for user {self.user_id}")
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of context state for debugging."""
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'created_at': self.created_at.isoformat(),
            'session_id': self.session_id,
            'active_runs_count': len(self.active_runs),
            'run_history_count': len(self.run_history),
            'has_db_session': self.db_session is not None,
            'has_websocket_emitter': self.websocket_emitter is not None,
            'cleanup_callbacks_count': len(self.cleanup_callbacks),
            'is_cleaned': self._is_cleaned,
            'context_id': self.request_metadata.get('context_id'),
            'isolation_level': self.request_metadata.get('isolation_level'),
            'execution_metrics': self.execution_metrics.copy()
        }


class UserWebSocketEmitter:
    """
    Per-user WebSocket event emitter with complete isolation.
    
    Each user gets their own emitter instance bound to their specific
    user_id and thread_id. No cross-user contamination possible.
    
    Business Value: Ensures WebSocket events reach correct users, prevents notification leaks
    """
    
    def __init__(self, user_id: str, thread_id: str, run_id: str, 
                 websocket_bridge: AgentWebSocketBridge):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.websocket_bridge = websocket_bridge
        self.created_at = datetime.now(timezone.utc)
        self._event_count = 0
        self._last_event_time = None
        
        logger.debug(f"Created UserWebSocketEmitter for user={user_id}, thread={thread_id}, run={run_id}")
    
    async def notify_agent_started(self, agent_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent started notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_agent_started(
                run_id=self.run_id,
                agent_name=agent_name,
                context=context
            )
            
            if success:
                logger.debug(f"✅ Agent started notification sent for user {self.user_id}: {agent_name}")
            else:
                logger.error(f"❌ Agent started notification failed for user {self.user_id}: {agent_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_agent_started for user {self.user_id}: {e}")
            return False
    
    async def notify_agent_thinking(self, agent_name: str, reasoning: str, 
                                   step_number: Optional[int] = None,
                                   progress_percentage: Optional[float] = None) -> bool:
        """Send agent thinking notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_agent_thinking(
                run_id=self.run_id,
                agent_name=agent_name,
                reasoning=reasoning,
                step_number=step_number,
                progress_percentage=progress_percentage
            )
            
            if success:
                logger.debug(f"✅ Agent thinking notification sent for user {self.user_id}: {agent_name}")
            else:
                logger.error(f"❌ Agent thinking notification failed for user {self.user_id}: {agent_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_agent_thinking for user {self.user_id}: {e}")
            return False
    
    async def notify_tool_executing(self, agent_name: str, tool_name: str, 
                                   parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Send tool executing notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_tool_executing(
                run_id=self.run_id,
                agent_name=agent_name,
                tool_name=tool_name,
                parameters=parameters
            )
            
            if success:
                logger.debug(f"✅ Tool executing notification sent for user {self.user_id}: {tool_name}")
            else:
                logger.error(f"❌ Tool executing notification failed for user {self.user_id}: {tool_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_tool_executing for user {self.user_id}: {e}")
            return False
    
    async def notify_tool_completed(self, agent_name: str, tool_name: str, 
                                   result: Optional[Dict[str, Any]] = None,
                                   execution_time_ms: Optional[float] = None) -> bool:
        """Send tool completed notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_tool_completed(
                run_id=self.run_id,
                agent_name=agent_name,
                tool_name=tool_name,
                result=result,
                execution_time_ms=execution_time_ms
            )
            
            if success:
                logger.debug(f"✅ Tool completed notification sent for user {self.user_id}: {tool_name}")
            else:
                logger.error(f"❌ Tool completed notification failed for user {self.user_id}: {tool_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_tool_completed for user {self.user_id}: {e}")
            return False
    
    async def notify_agent_completed(self, agent_name: str, result: Optional[Dict[str, Any]] = None,
                                    execution_time_ms: Optional[float] = None) -> bool:
        """Send agent completed notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_agent_completed(
                run_id=self.run_id,
                agent_name=agent_name,
                result=result,
                execution_time_ms=execution_time_ms
            )
            
            if success:
                logger.debug(f"✅ Agent completed notification sent for user {self.user_id}: {agent_name}")
            else:
                logger.error(f"❌ Agent completed notification failed for user {self.user_id}: {agent_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_agent_completed for user {self.user_id}: {e}")
            return False
    
    async def notify_agent_error(self, agent_name: str, error: str,
                                error_context: Optional[Dict[str, Any]] = None) -> bool:
        """Send agent error notification for this specific user."""
        try:
            self._event_count += 1
            self._last_event_time = datetime.now(timezone.utc)
            
            success = await self.websocket_bridge.notify_agent_error(
                run_id=self.run_id,
                agent_name=agent_name,
                error=error,
                error_context=error_context
            )
            
            if success:
                logger.warning(f"⚠️ Agent error notification sent for user {self.user_id}: {agent_name}")
            else:
                logger.error(f"❌ Agent error notification failed for user {self.user_id}: {agent_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_agent_error for user {self.user_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up WebSocket emitter resources."""
        try:
            logger.debug(f"Cleaning up UserWebSocketEmitter for user {self.user_id} "
                        f"(sent {self._event_count} events)")
            
            # Log final statistics
            if self._last_event_time and self._event_count > 0:
                total_time = (datetime.now(timezone.utc) - self.created_at).total_seconds()
                logger.info(f"WebSocket emitter stats for user {self.user_id}: "
                           f"{self._event_count} events in {total_time:.1f}s")
            
            # Clear references
            self.websocket_bridge = None
            
        except Exception as e:
            logger.error(f"Error cleaning up UserWebSocketEmitter for user {self.user_id}: {e}")
    
    def get_emitter_status(self) -> Dict[str, Any]:
        """Get emitter status for monitoring."""
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'event_count': self._event_count,
            'last_event_time': self._last_event_time.isoformat() if self._last_event_time else None,
            'created_at': self.created_at.isoformat(),
            'has_websocket_bridge': self.websocket_bridge is not None
        }


class AgentInstanceFactory:
    """
    Factory for creating per-request agent instances with complete user isolation.
    
    This factory ensures that each user request gets completely isolated agent instances:
    - Fresh agent instances with no shared state
    - User-specific WebSocket emitters
    - Request-scoped database sessions
    - Complete resource isolation and cleanup
    
    CRITICAL: This is the request layer that prevents user context leakage.
    Each user gets their own execution environment with no global state sharing.
    
    Business Value: Enables safe concurrent user operations, prevents data leakage,
    and provides the foundation for multi-user production deployment.
    """
    
    def __init__(self):
        """Initialize the factory with infrastructure components."""
        # Infrastructure components (shared, immutable)
        self._agent_registry: Optional[AgentRegistry] = None
        self._websocket_bridge: Optional[AgentWebSocketBridge] = None
        self._websocket_manager: Optional[WebSocketManager] = None
        
        # Factory configuration
        self._max_concurrent_per_user = 5
        self._execution_timeout = 30.0
        self._cleanup_interval = 300  # 5 minutes
        self._max_history_per_user = 100
        
        # Per-user concurrency control (infrastructure manages this)
        self._user_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._semaphore_lock = asyncio.Lock()
        
        # Factory metrics
        self._factory_metrics = {
            'total_instances_created': 0,
            'active_contexts': 0,
            'total_contexts_cleaned': 0,
            'creation_errors': 0,
            'cleanup_errors': 0,
            'average_context_lifetime_seconds': 0.0
        }
        
        # Active contexts tracking for monitoring
        self._active_contexts: Dict[str, UserExecutionContext] = {}
        
        logger.info("AgentInstanceFactory initialized")
    
    def configure(self, 
                 agent_registry: AgentRegistry,
                 websocket_bridge: AgentWebSocketBridge,
                 websocket_manager: Optional[WebSocketManager] = None) -> None:
        """
        Configure factory with infrastructure components.
        
        Args:
            agent_registry: Registry containing agent classes and configurations
            websocket_bridge: WebSocket bridge for agent notifications
            websocket_manager: Optional WebSocket manager for direct access
        """
        if not agent_registry:
            raise ValueError("AgentRegistry cannot be None")
        if not websocket_bridge:
            raise ValueError("AgentWebSocketBridge cannot be None")
        
        self._agent_registry = agent_registry
        self._websocket_bridge = websocket_bridge
        self._websocket_manager = websocket_manager
        
        logger.info("✅ AgentInstanceFactory configured with infrastructure components")
    
    async def create_user_execution_context(self, 
                                           user_id: str,
                                           thread_id: str,
                                           run_id: str,
                                           db_session: AsyncSession,
                                           session_id: Optional[str] = None,
                                           metadata: Optional[Dict[str, Any]] = None) -> UserExecutionContext:
        """
        Create isolated user execution context with all required resources.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            run_id: Unique run identifier for this execution
            db_session: Request-scoped database session
            session_id: Optional session identifier
            metadata: Optional metadata for the context
            
        Returns:
            UserExecutionContext: Complete isolated execution context
            
        Raises:
            ValueError: If factory not configured or invalid parameters
            RuntimeError: If context creation fails
        """
        if not self._agent_registry or not self._websocket_bridge:
            raise ValueError("Factory not configured - call configure() first")
        
        if not user_id or not thread_id or not run_id:
            raise ValueError("user_id, thread_id, and run_id are required")
        
        if not db_session:
            raise ValueError("db_session is required for request isolation")
        
        start_time = time.time()
        context_id = f"{user_id}_{thread_id}_{run_id}"
        
        try:
            logger.info(f"Creating user execution context: {context_id}")
            
            # Create user execution context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                session_id=session_id
            )
            
            # Add metadata if provided
            if metadata:
                context.request_metadata.update(metadata)
            
            # Create user-specific WebSocket emitter
            websocket_emitter = UserWebSocketEmitter(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_bridge=self._websocket_bridge
            )
            context.websocket_emitter = websocket_emitter
            
            # Register cleanup callback for WebSocket emitter
            context.add_cleanup_callback(websocket_emitter.cleanup)
            
            # Register run-thread mapping for reliable WebSocket routing
            if self._websocket_bridge:
                try:
                    mapping_success = await self._websocket_bridge.register_run_thread_mapping(
                        run_id=run_id,
                        thread_id=thread_id,
                        metadata={
                            'user_id': user_id,
                            'created_at': context.created_at.isoformat(),
                            'factory_context_id': context_id
                        }
                    )
                    if not mapping_success:
                        logger.warning(f"Failed to register run-thread mapping for {context_id}")
                except Exception as e:
                    logger.error(f"Error registering run-thread mapping for {context_id}: {e}")
            
            # Track active context
            self._active_contexts[context_id] = context
            
            # Update metrics
            self._factory_metrics['total_instances_created'] += 1
            self._factory_metrics['active_contexts'] = len(self._active_contexts)
            
            creation_time_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Created user execution context {context_id} in {creation_time_ms:.1f}ms")
            
            return context
            
        except Exception as e:
            self._factory_metrics['creation_errors'] += 1
            logger.error(f"Failed to create user execution context {context_id}: {e}")
            raise RuntimeError(f"Context creation failed for {context_id}: {e}")
    
    async def create_agent_instance(self, 
                                   agent_name: str,
                                   user_context: UserExecutionContext,
                                   agent_class: Optional[Type[BaseAgent]] = None) -> BaseAgent:
        """
        Create isolated agent instance for specific user context.
        
        Args:
            agent_name: Name of the agent to create
            user_context: User execution context for isolation
            agent_class: Optional specific agent class (if not using registry)
            
        Returns:
            BaseAgent: Fresh agent instance configured for the user context
            
        Raises:
            ValueError: If agent not found or invalid parameters
            RuntimeError: If agent creation fails
        """
        if not user_context:
            raise ValueError("UserExecutionContext is required")
        
        start_time = time.time()
        
        try:
            logger.debug(f"Creating agent instance: {agent_name} for user {user_context.user_id}")
            
            # Get agent class from registry or use provided class
            if agent_class:
                AgentClass = agent_class
            else:
                agent_instance = self._agent_registry.get(agent_name)
                if not agent_instance:
                    raise ValueError(f"Agent '{agent_name}' not found in registry")
                
                # Create fresh instance of the same class
                AgentClass = type(agent_instance)
            
            # Create fresh agent instance with request-scoped dependencies
            agent = AgentClass(
                llm_manager=self._agent_registry.llm_manager,
                tool_dispatcher=self._agent_registry.tool_dispatcher,
                name=agent_name,
                user_id=user_context.user_id  # Bind to specific user
            )
            
            # Set WebSocket bridge on agent for event emission
            if hasattr(agent, 'set_websocket_bridge') and user_context.websocket_emitter:
                try:
                    agent.set_websocket_bridge(self._websocket_bridge, user_context.run_id)
                    logger.debug(f"✅ WebSocket bridge set on agent {agent_name} for user {user_context.user_id}")
                except Exception as e:
                    logger.warning(f"Failed to set WebSocket bridge on agent {agent_name}: {e}")
            
            # Store agent reference in user context for cleanup
            user_context.active_runs[f"{agent_name}_{int(time.time() * 1000)}"] = {
                'agent_instance': agent,
                'agent_name': agent_name,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'created'
            }
            
            # Update metrics
            user_context.execution_metrics['active_agent_count'] += 1
            
            creation_time_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Created agent instance {agent_name} for user {user_context.user_id} in {creation_time_ms:.1f}ms")
            
            return agent
            
        except Exception as e:
            self._factory_metrics['creation_errors'] += 1
            logger.error(f"Failed to create agent instance {agent_name} for user {user_context.user_id}: {e}")
            raise RuntimeError(f"Agent creation failed: {e}")
    
    async def cleanup_user_context(self, user_context: UserExecutionContext) -> None:
        """
        Clean up user execution context and all associated resources.
        
        Args:
            user_context: Context to clean up
        """
        if not user_context:
            return
        
        context_id = f"{user_context.user_id}_{user_context.thread_id}_{user_context.run_id}"
        start_time = time.time()
        
        try:
            logger.info(f"Cleaning up user execution context: {context_id}")
            
            # Unregister run-thread mapping
            if self._websocket_bridge:
                try:
                    await self._websocket_bridge.unregister_run_mapping(user_context.run_id)
                except Exception as e:
                    logger.warning(f"Failed to unregister run mapping for {context_id}: {e}")
            
            # Execute context cleanup
            await user_context.cleanup()
            
            # Remove from active contexts tracking
            self._active_contexts.pop(context_id, None)
            
            # Update metrics
            self._factory_metrics['total_contexts_cleaned'] += 1
            self._factory_metrics['active_contexts'] = len(self._active_contexts)
            
            # Calculate and update average context lifetime
            lifetime_seconds = (time.time() - start_time)
            current_avg = self._factory_metrics['average_context_lifetime_seconds']
            total_cleaned = self._factory_metrics['total_contexts_cleaned']
            
            if total_cleaned == 1:
                self._factory_metrics['average_context_lifetime_seconds'] = lifetime_seconds
            else:
                # Rolling average
                self._factory_metrics['average_context_lifetime_seconds'] = (
                    (current_avg * (total_cleaned - 1) + lifetime_seconds) / total_cleaned
                )
            
            cleanup_time_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ Cleaned up user execution context {context_id} in {cleanup_time_ms:.1f}ms")
            
        except Exception as e:
            self._factory_metrics['cleanup_errors'] += 1
            logger.error(f"Error cleaning up user execution context {context_id}: {e}")
    
    @asynccontextmanager
    async def user_execution_scope(self, 
                                  user_id: str,
                                  thread_id: str,
                                  run_id: str,
                                  db_session: AsyncSession,
                                  session_id: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for user execution scope with automatic cleanup.
        
        Usage:
            async with factory.user_execution_scope(user_id, thread_id, run_id, db_session) as context:
                agent = await factory.create_agent_instance("triage", context)
                result = await agent.execute(state, run_id)
        """
        context = None
        try:
            # Create user execution context
            context = await self.create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                session_id=session_id,
                metadata=metadata
            )
            
            yield context
            
        finally:
            # Always cleanup, even if an exception occurred
            if context:
                await self.cleanup_user_context(context)
    
    async def get_user_semaphore(self, user_id: str) -> asyncio.Semaphore:
        """
        Get or create per-user execution semaphore for concurrency control.
        
        Args:
            user_id: User identifier
            
        Returns:
            asyncio.Semaphore: User-specific semaphore
        """
        async with self._semaphore_lock:
            if user_id not in self._user_semaphores:
                self._user_semaphores[user_id] = asyncio.Semaphore(self._max_concurrent_per_user)
                logger.debug(f"Created semaphore for user {user_id} (max: {self._max_concurrent_per_user})")
            return self._user_semaphores[user_id]
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics for monitoring."""
        return {
            **self._factory_metrics.copy(),
            'user_semaphores_count': len(self._user_semaphores),
            'max_concurrent_per_user': self._max_concurrent_per_user,
            'execution_timeout': self._execution_timeout,
            'cleanup_interval': self._cleanup_interval,
            'active_context_ids': list(self._active_contexts.keys()),
            'configuration_status': {
                'agent_registry_configured': self._agent_registry is not None,
                'websocket_bridge_configured': self._websocket_bridge is not None,
                'websocket_manager_configured': self._websocket_manager is not None
            }
        }
    
    def get_active_contexts_summary(self) -> Dict[str, Any]:
        """Get summary of all active user contexts."""
        contexts_summary = {}
        for context_id, context in self._active_contexts.items():
            try:
                contexts_summary[context_id] = context.get_context_summary()
            except Exception as e:
                contexts_summary[context_id] = {
                    'error': f'Failed to get context summary: {e}',
                    'context_id': context_id
                }
        
        return {
            'total_active_contexts': len(self._active_contexts),
            'contexts': contexts_summary,
            'summary_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def cleanup_inactive_contexts(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up inactive contexts older than specified age.
        
        Args:
            max_age_seconds: Maximum age for contexts before cleanup
            
        Returns:
            int: Number of contexts cleaned up
        """
        if not self._active_contexts:
            return 0
        
        cleanup_count = 0
        current_time = datetime.now(timezone.utc)
        contexts_to_cleanup = []
        
        # Identify old contexts
        for context_id, context in self._active_contexts.items():
            try:
                age_seconds = (current_time - context.created_at).total_seconds()
                if age_seconds > max_age_seconds:
                    contexts_to_cleanup.append(context)
            except Exception as e:
                logger.warning(f"Error checking context age for {context_id}: {e}")
                contexts_to_cleanup.append(context)  # Clean up problematic contexts
        
        # Clean up old contexts
        for context in contexts_to_cleanup:
            try:
                await self.cleanup_user_context(context)
                cleanup_count += 1
            except Exception as e:
                logger.error(f"Error during inactive context cleanup: {e}")
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} inactive contexts (max age: {max_age_seconds}s)")
        
        return cleanup_count


# Singleton factory instance for application use
_factory_instance: Optional[AgentInstanceFactory] = None


def get_agent_instance_factory() -> AgentInstanceFactory:
    """Get singleton AgentInstanceFactory instance."""
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = AgentInstanceFactory()
    
    return _factory_instance


async def configure_agent_instance_factory(agent_registry: AgentRegistry,
                                          websocket_bridge: AgentWebSocketBridge,
                                          websocket_manager: Optional[WebSocketManager] = None) -> AgentInstanceFactory:
    """
    Configure the singleton AgentInstanceFactory with infrastructure components.
    
    Args:
        agent_registry: Registry containing agent classes
        websocket_bridge: WebSocket bridge for notifications
        websocket_manager: Optional WebSocket manager
        
    Returns:
        AgentInstanceFactory: Configured factory instance
    """
    factory = get_agent_instance_factory()
    factory.configure(
        agent_registry=agent_registry,
        websocket_bridge=websocket_bridge,
        websocket_manager=websocket_manager
    )
    
    logger.info("✅ AgentInstanceFactory configured and ready for per-request agent instantiation")
    return factory