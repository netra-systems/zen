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
import weakref
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Type, Union, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry, get_agent_class_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.factory_performance_config import (
    FactoryPerformanceConfig, 
    get_factory_performance_config
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core import (
    WebSocketEmitterPool,
)
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
# WebSocket exceptions module was deleted - using standard exceptions
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# UserExecutionContext is now imported from user_execution_context.py


# SSOT CONSOLIDATION COMPLETE: All functionality now provided by UnifiedWebSocketEmitter


class AgentInstanceFactory:
    """
    Factory for creating per-request agent instances with complete user isolation.
    
    Business Value: Ensures WebSocket events reach correct users, prevents notification leaks
    
    ## MIGRATION STATUS: PHASE 1 COMPLETE
    - Redirects to UnifiedWebSocketEmitter via AgentWebSocketBridge
    - Maintains full backward compatibility
    - No breaking changes for AgentInstanceFactory consumers
    """
    
    def __init__(self, user_id: str, thread_id: str, run_id: str, 
                 websocket_bridge: AgentWebSocketBridge):
        """Initialize compatibility wrapper that uses the AgentWebSocketBridge.
        
        The AgentWebSocketBridge now internally uses UnifiedWebSocketEmitter,
        so this wrapper maintains compatibility while getting SSOT benefits.
        """
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.websocket_bridge = websocket_bridge
        self.created_at = datetime.now(timezone.utc)
        self._event_count = 0
        self._last_event_time = None
        
        logger.info(f" CYCLE:  UnifiedWebSocketEmitter (factory pattern)  ->  AgentWebSocketBridge  ->  UnifiedWebSocketEmitter for user={user_id}, run={run_id}")
        logger.debug(f"Factory UnifiedWebSocketEmitter initialized with bridge type: {type(websocket_bridge).__name__}")
    
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
                logger.debug(f" PASS:  Agent started notification sent for user {self.user_id}: {agent_name}")
            else:
                error_msg = f"Agent started notification failed for user {self.user_id}: {agent_name}"
                logger.error(f" FAIL:  {error_msg}")
                
                # LOUD FAILURE: Raise exception for failed notifications
                raise ConnectionError(
                    f"WebSocket bridge returned failure for agent_started: {agent_name} "
                    f"(user: {self.user_id}, thread: {self.thread_id})"
                )
            
            return success
        except ConnectionError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            error_msg = f"Exception in notify_agent_started for user {self.user_id}: {e}"
            logger.error(f" ALERT:  AGENT COMMUNICATION FAILURE: {error_msg}")
            
            # LOUD FAILURE: Convert generic exceptions to specific ones
            raise RuntimeError(
                f"Agent communication failure from UnifiedWebSocketEmitter to {agent_name}: {str(e)} "
                f"(user: {self.user_id})"
            )
    
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
                logger.debug(f" PASS:  Agent thinking notification sent for user {self.user_id}: {agent_name}")
            else:
                error_msg = f"Agent thinking notification failed for user {self.user_id}: {agent_name}"
                logger.error(f" FAIL:  {error_msg}")
                
                # LOUD FAILURE: Raise exception
                raise ConnectionError(
                    f"WebSocket bridge returned failure for agent_thinking: {agent_name} "
                    f"(user: {self.user_id}, thread: {self.thread_id})"
                )
            
            return success
        except ConnectionError:
            raise
        except Exception as e:
            error_msg = f"Exception in notify_agent_thinking for user {self.user_id}: {e}"
            logger.error(f" ALERT:  AGENT COMMUNICATION FAILURE: {error_msg}")
            
            raise RuntimeError(
                f"Agent communication failure from UnifiedWebSocketEmitter to {agent_name}: {str(e)} "
                f"(user: {self.user_id})"
            )
    
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
                logger.debug(f" PASS:  Tool executing notification sent for user {self.user_id}: {tool_name}")
            else:
                error_msg = f"Tool executing notification failed for user {self.user_id}: {tool_name}"
                logger.error(f" FAIL:  {error_msg}")
                
                raise ConnectionError(
                    f"WebSocket bridge returned failure for tool_executing: {tool_name} "
                    f"(user: {self.user_id}, thread: {self.thread_id})"
                )
            
            return success
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f" ALERT:  TOOL NOTIFICATION FAILURE: Exception in notify_tool_executing for user {self.user_id}: {e}")
            raise RuntimeError(
                f"Agent communication failure from UnifiedWebSocketEmitter to {agent_name}: {str(e)} "
                f"(user: {self.user_id})"
            )
    
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
                logger.debug(f" PASS:  Tool completed notification sent for user {self.user_id}: {tool_name}")
            else:
                error_msg = f"Tool completed notification failed for user {self.user_id}: {tool_name}"
                logger.error(f" FAIL:  {error_msg}")
                
                raise ConnectionError(
                    f"WebSocket bridge returned failure for tool_completed: {tool_name} "
                    f"(user: {self.user_id}, thread: {self.thread_id})"
                )
            
            return success
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f" ALERT:  TOOL NOTIFICATION FAILURE: Exception in notify_tool_completed for user {self.user_id}: {e}")
            raise RuntimeError(
                f"Agent communication failure from UnifiedWebSocketEmitter to {agent_name}: {str(e)} "
                f"(user: {self.user_id})"
            )
    
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
                logger.debug(f" PASS:  Agent completed notification sent for user {self.user_id}: {agent_name}")
            else:
                error_msg = f"Agent completed notification failed for user {self.user_id}: {agent_name}"
                logger.error(f" FAIL:  {error_msg}")
                
                raise ConnectionError(
                    f"WebSocket bridge returned failure for agent_completed: {agent_name} "
                    f"(user: {self.user_id}, thread: {self.thread_id})"
                )
            
            return success
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f" ALERT:  AGENT COMPLETION FAILURE: Exception in notify_agent_completed for user {self.user_id}: {e}")
            raise RuntimeError(
                f"Agent communication failure from UnifiedWebSocketEmitter to {agent_name}: {str(e)} "
                f"(user: {self.user_id})"
            )
    
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
                logger.warning(f" WARNING: [U+FE0F] Agent error notification sent for user {self.user_id}: {agent_name}")
            else:
                logger.error(f" FAIL:  Agent error notification failed for user {self.user_id}: {agent_name}")
            
            return success
        except Exception as e:
            logger.error(f"Exception in notify_agent_error for user {self.user_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up WebSocket emitter resources."""
        try:
            logger.debug(f"Cleaning up UnifiedWebSocketEmitter for user {self.user_id} "
                        f"(sent {self._event_count} events)")
            
            # Log final statistics
            if self._last_event_time and self._event_count > 0:
                total_time = (datetime.now(timezone.utc) - self.created_at).total_seconds()
                logger.info(f"WebSocket emitter stats for user {self.user_id}: "
                           f"{self._event_count} events in {total_time:.1f}s")
            
            # Clear references
            self.websocket_bridge = None
            
        except Exception as e:
            logger.error(f"Error cleaning up UnifiedWebSocketEmitter for user {self.user_id}: {e}")
    
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
    - User-specific WebSocket emitters bound to specific UserExecutionContext
    - Request-scoped database sessions
    - Complete resource isolation and cleanup
    
    CRITICAL: This is the request layer that prevents user context leakage.
    Each user gets their own execution environment with no global state sharing.
    
    Business Value: Enables safe concurrent user operations, prevents data leakage,
    and provides the foundation for multi-user production deployment.
    
    The factory uses both the infrastructure-only AgentClassRegistry for agent
    classes and AgentRegistry for backward compatibility during the transition.
    """
    
    # CRITICAL: Define which agents require which dependencies
    AGENT_DEPENDENCIES = {
        'DataSubAgent': ['llm_manager'],
        'OptimizationsCoreSubAgent': ['llm_manager'],
        'ActionsToMeetGoalsSubAgent': ['llm_manager'],
        'DataHelperAgent': ['llm_manager'],
        'SyntheticDataSubAgent': ['llm_manager'],
    }
    
    def __init__(self):
        """Initialize the factory with infrastructure components."""
        # Infrastructure components (shared, immutable)
        self._agent_class_registry: Optional[AgentClassRegistry] = None
        self._agent_registry: Optional[AgentRegistry] = None
        self._websocket_bridge: Optional[AgentWebSocketBridge] = None
        self._websocket_manager: Optional[WebSocketManager] = None
        self._llm_manager: Optional[Any] = None
        self._tool_dispatcher: Optional[Any] = None
        
        # Performance configuration
        self._performance_config = get_factory_performance_config()
        
        # Factory configuration (use performance config where applicable)
        self._max_concurrent_per_user = self._performance_config.max_concurrent_per_user
        self._execution_timeout = self._performance_config.execution_timeout
        self._cleanup_interval = 300  # 5 minutes
        self._max_history_per_user = self._performance_config.max_history_per_user
        
        # Object pools (if enabled)
        self._emitter_pool = None
        if self._performance_config.enable_emitter_pooling:
            # Initialize emitter pool asynchronously when needed
            self._emitter_pool_task = None
        
        # Agent class cache (if enabled)
        if self._performance_config.enable_class_caching:
            self._agent_class_cache = {}
            self._cache_lock = asyncio.Lock()
        
        # Performance tracking (if enabled)
        if self._performance_config.enable_metrics:
            self._perf_stats = {
                'context_creation_ms': deque(maxlen=self._performance_config.metrics_buffer_size),
                'agent_creation_ms': deque(maxlen=self._performance_config.metrics_buffer_size),
                'cleanup_ms': deque(maxlen=self._performance_config.metrics_buffer_size)
            }
        
        # Use weak references if enabled
        if self._performance_config.enable_weak_references:
            self._active_contexts = weakref.WeakValueDictionary()
            self._user_semaphores = weakref.WeakValueDictionary()
        else:
            # Per-user concurrency control (infrastructure manages this)
            self._user_semaphores: Dict[str, asyncio.Semaphore] = {}
            # Active contexts tracking for monitoring
            self._active_contexts: Dict[str, UserExecutionContext] = {}
        
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
        
        logger.info(f"AgentInstanceFactory initialized with performance optimizations enabled: "
                   f"pooling={self._performance_config.enable_emitter_pooling}, "
                   f"caching={self._performance_config.enable_class_caching}, "
                   f"metrics={self._performance_config.enable_metrics}")
    
    def configure(self, 
                 agent_class_registry: Optional[AgentClassRegistry] = None,
                 agent_registry: Optional[AgentRegistry] = None,
                 websocket_bridge: Optional[AgentWebSocketBridge] = None,
                 websocket_manager: Optional[WebSocketManager] = None,
                 llm_manager: Optional[Any] = None,
                 tool_dispatcher: Optional[Any] = None) -> None:
        """
        Configure factory with infrastructure components.
        
        Args:
            agent_class_registry: Registry containing agent classes (preferred)
            agent_registry: Legacy agent registry (for backward compatibility)
            websocket_bridge: WebSocket bridge for agent notifications
            websocket_manager: Optional WebSocket manager for direct access
            llm_manager: LLM manager for agent communication
            tool_dispatcher: Tool dispatcher for agent tools
        """
        if not websocket_bridge:
            logger.warning(" WARNING: [U+FE0F] WARNING: Configuring AgentInstanceFactory with None websocket_bridge!")
            logger.warning("    Agent WebSocket events will not be available (testing/degraded mode)")
            logger.warning("    This is acceptable for basic agent creation but WebSocket functionality will be disabled")
        else:
            logger.info(f"[U+1F527] Configuring AgentInstanceFactory with WebSocket bridge type: {type(websocket_bridge).__name__}")
        
        # Prefer AgentClassRegistry but fallback to AgentRegistry for compatibility
        if agent_class_registry:
            self._agent_class_registry = agent_class_registry
            logger.info(" PASS:  AgentInstanceFactory configured with AgentClassRegistry")
        elif agent_registry:
            self._agent_registry = agent_registry
            logger.info(" PASS:  AgentInstanceFactory configured with legacy AgentRegistry")
        else:
            # Try to get global agent class registry
            try:
                self._agent_class_registry = get_agent_class_registry()
                # Validate registry is populated
                if self._agent_class_registry:
                    registry_size = len(self._agent_class_registry)
                    if registry_size == 0:
                        logger.warning(" WARNING: [U+FE0F] AgentClassRegistry is empty - no agents registered!")
                        logger.warning("    Ensure initialize_agent_class_registry() was called during startup")
                        logger.warning("    Factory will continue without registry (limited functionality)")
                        self._agent_class_registry = None
                    else:
                        logger.info(f" PASS:  AgentInstanceFactory configured with global AgentClassRegistry ({registry_size} agents)")
                else:
                    logger.warning(" WARNING: [U+FE0F] Global AgentClassRegistry is None - factory will have limited functionality")
                    logger.warning("    Agent creation will not be available, but other factory functions will work")
                    self._agent_class_registry = None
            except Exception as e:
                logger.warning(f" WARNING: [U+FE0F] Failed to get global agent class registry: {e}")
                logger.warning("    Factory will continue without registry (limited functionality)")
                self._agent_class_registry = None
        
        self._websocket_bridge = websocket_bridge
        self._websocket_manager = websocket_manager
        self._llm_manager = llm_manager
        self._tool_dispatcher = tool_dispatcher
        
        logger.info(f" PASS:  AgentInstanceFactory configured successfully:")
        logger.info(f"   - WebSocket bridge: {type(websocket_bridge).__name__}")
        logger.info(f"   - WebSocket manager: {type(websocket_manager).__name__ if websocket_manager else 'None'}")
        logger.info(f"   - Registry type: {'AgentClassRegistry' if self._agent_class_registry else 'AgentRegistry' if self._agent_registry else 'Unknown'}")
        logger.info(f"   - LLM manager: {'Configured' if llm_manager else 'None'}")
        logger.info(f"   - Tool dispatcher: {'Configured' if tool_dispatcher else 'None'}")
    
    def _agent_name_matches_class(self, agent_name: str, class_name: str) -> bool:
        """
        Check if an agent name matches a class name using flexible matching.
        
        Handles cases like:
        - "optimization_core" matches "OptimizationsCoreSubAgent"
        - "data" matches "DataSubAgent" 
        """
        # Normalize both names: lowercase, remove underscores, remove common suffixes
        def normalize(name: str) -> str:
            return name.lower().replace('_', '').replace('subagent', '').replace('agent', '')
        
        normalized_agent = normalize(agent_name)
        normalized_class = normalize(class_name)
        
        # Try different matching strategies
        return (
            normalized_agent == normalized_class or
            normalized_agent in normalized_class or  
            normalized_class in normalized_agent or
            # Handle "optimizations" vs "optimization" case
            normalized_agent.replace('s', '') == normalized_class.replace('s', '') or
            # Handle common word variations
            any(word in normalized_class for word in normalized_agent.split() if len(word) > 2)
        )
    
    def _validate_agent_dependencies(self, agent_name: str) -> None:
        """
        Validate that all required dependencies for an agent are available.
        
        Args:
            agent_name: Name of the agent or its class name
            
        Raises:
            RuntimeError: If required dependencies are missing
        """
        # Check both agent name and class name
        dependencies = []
        
        # Check by agent name (exact match first)
        if agent_name in self.AGENT_DEPENDENCIES:
            dependencies = self.AGENT_DEPENDENCIES[agent_name]
        
        # Also check by class name with flexible matching
        if not dependencies:
            for class_name, deps in self.AGENT_DEPENDENCIES.items():
                if self._agent_name_matches_class(agent_name, class_name):
                    dependencies = deps
                    break
        
        # Validate each required dependency
        for dep in dependencies:
            if dep == 'llm_manager' and not self._llm_manager:
                logger.error(f" FAIL:  CRITICAL: Agent {agent_name} requires LLM manager but none configured")
                logger.error(f"   Factory state: llm_manager={self._llm_manager}")
                logger.error(f"   This will cause agent execution to fail")
                raise RuntimeError(
                    f"Cannot create {agent_name}: Required dependency 'llm_manager' not available. "
                    f"Ensure LLM manager is initialized during startup and passed to factory."
                )
            elif dep == 'tool_dispatcher' and not self._tool_dispatcher:
                logger.warning(f" WARNING: [U+FE0F] Agent {agent_name} prefers tool_dispatcher but none configured (can use per-request)")
    
    async def create_user_execution_context(self, 
                                           user_id: str,
                                           thread_id: str,
                                           run_id: str,
                                           request_id: Optional[str] = None,
                                           db_session: Optional[AsyncSession] = None,
                                           websocket_client_id: Optional[str] = None,
                                           metadata: Optional[Dict[str, Any]] = None) -> UserExecutionContext:
        """
        Create isolated user execution context with all required resources.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            run_id: Unique run identifier for this execution
            request_id: Optional request identifier for this execution
            db_session: Optional request-scoped database session
            websocket_client_id: Optional WebSocket client ID
            metadata: Optional metadata for the context
            
        Returns:
            UserExecutionContext: Complete isolated execution context
            
        Raises:
            ValueError: If factory not configured or invalid parameters
            RuntimeError: If context creation fails
        """
        if not self._websocket_bridge:
            raise ValueError("Factory not configured - call configure() first")
        
        if not user_id or not thread_id or not run_id:
            raise ValueError("user_id, thread_id, and run_id are required")
        
        start_time = time.time()
        context_id = f"{user_id}_{thread_id}_{run_id}"
        
        # Performance tracking (if enabled)
        should_track_metrics = self._should_sample()
        
        try:
            logger.info(f"Creating user execution context: {context_id}")
            
            # Create user execution context using the standard from_request method
            context = UserExecutionContext.from_request_supervisor(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                db_session=db_session,
                websocket_connection_id=websocket_client_id,
                metadata=metadata or {}
            )
            
            # Create user-specific WebSocket emitter (with pooling support)
            websocket_emitter = await self._create_emitter(user_id, thread_id, run_id)
            
            # Store the emitter in a way that works with immutable context
            # We'll need to track these separately since context is immutable
            emitter_key = f"{context_id}_emitter"
            self._websocket_emitters = getattr(self, '_websocket_emitters', {})
            self._websocket_emitters[emitter_key] = websocket_emitter
            
            # Register run-thread mapping for reliable WebSocket routing
            if self._websocket_bridge:
                try:
                    if hasattr(self._websocket_bridge, 'register_run_thread_mapping'):
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
            
            # Track performance metrics if enabled
            if should_track_metrics and hasattr(self, '_perf_stats'):
                self._perf_stats['context_creation_ms'].append(creation_time_ms)
            
            logger.info(f" PASS:  Created user execution context {context_id} in {creation_time_ms:.1f}ms")
            
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
        
        # CRITICAL: Validate WebSocket bridge is configured
        if not self._websocket_bridge:
            logger.warning(f" WARNING: [U+FE0F] WARNING: AgentInstanceFactory._websocket_bridge is None when creating {agent_name}!")
            logger.warning(f"   WebSocket events from {agent_name} will be disabled (testing/degraded mode)")
            logger.warning(f"   This is acceptable for basic agent functionality but WebSocket notifications won't work")
            # Don't raise error - allow golden path to work without WebSocket functionality
        
        start_time = time.time()
        
        # Performance tracking (if enabled)
        should_track_metrics = self._should_sample()
        
        try:
            logger.debug(f"Creating agent instance: {agent_name} for user {user_context.user_id}")
            logger.debug(f"Factory has websocket_bridge: {self._websocket_bridge is not None}, type: {type(self._websocket_bridge).__name__ if self._websocket_bridge else 'None'}")
            
            # CRITICAL: Validate dependencies before attempting creation
            self._validate_agent_dependencies(agent_name)
            
            # Get agent class from registries or use provided class
            if agent_class:
                AgentClass = agent_class
                # CRITICAL FIX: Use configured dependencies even when agent_class is provided directly
                # This ensures dependency injection works in all code paths
                llm_manager = self._llm_manager
                tool_dispatcher = self._tool_dispatcher
            else:
                # Try cached lookup first (if caching enabled)
                AgentClass = None
                if self._performance_config.enable_class_caching:
                    AgentClass = self._get_cached_agent_class(agent_name)
                
                # Set dependencies for cached agent class
                if AgentClass:
                    # Agent class found in cache - set dependencies
                    if self._llm_manager:
                        llm_manager = self._llm_manager
                        tool_dispatcher = self._tool_dispatcher  # Can be None for per-request creation
                    elif self._agent_registry:
                        llm_manager = self._agent_registry.llm_manager
                        tool_dispatcher = self._agent_registry.tool_dispatcher
                    else:
                        # No LLM manager available - this is OK for agents that don't need one
                        llm_manager = None
                        tool_dispatcher = None
                
                # Fallback to registry lookup if not cached
                elif not AgentClass and self._agent_class_registry:
                    AgentClass = self._agent_class_registry.get_agent_class(agent_name)
                    if not AgentClass:
                        # Provide detailed debugging information
                        available_agents = self._agent_class_registry.list_agent_names()
                        error_msg = (
                            f"Agent '{agent_name}' not found in AgentClassRegistry. "
                            f"Available agents: {sorted(available_agents)}. "
                        )
                        
                        # Check for common issues
                        if agent_name == 'synthetic_data':
                            error_msg += (
                                "\n WARNING: [U+FE0F] KNOWN ISSUE: synthetic_data agent registration may have failed due to: "
                                "\n  1. Missing opentelemetry dependency (pip install opentelemetry-api) "
                                "\n  2. Import error in synthetic_data_sub_agent.py module "
                                "\n  3. Agent not registered during startup (check initialization logs)"
                            )
                        
                        raise ValueError(error_msg)
                    
                    # Use directly injected dependencies or fallback to legacy registry
                    # Note: tool_dispatcher can be None for per-request creation pattern
                    if self._llm_manager:
                        llm_manager = self._llm_manager
                        tool_dispatcher = self._tool_dispatcher  # Can be None for per-request creation
                    elif self._agent_registry:
                        llm_manager = self._agent_registry.llm_manager
                        tool_dispatcher = self._agent_registry.tool_dispatcher
                    else:
                        # No LLM manager available - this is OK for agents that don't need one
                        # They will handle the None values appropriately in their constructor
                        llm_manager = None
                        tool_dispatcher = None
                
                # Fallback to legacy AgentRegistry with state reset
                elif self._agent_registry:
                    # Use get_agent() instead of get() to ensure state reset
                    agent_instance = await self._agent_registry.get_agent(agent_name)
                    if not agent_instance:
                        raise ValueError(f"Agent '{agent_name}' not found in AgentRegistry")
                    
                    AgentClass = type(agent_instance)
                    llm_manager = self._agent_registry.llm_manager
                    tool_dispatcher = self._agent_registry.tool_dispatcher
                else:
                    logger.error(f" FAIL:  Cannot create agent '{agent_name}' - no registry configured")
                    logger.error("    Neither agent_class_registry nor agent_registry is available")
                    logger.error("    Ensure initialize_agent_class_registry() was called during startup")
                    raise ValueError(f"No agent registry configured - cannot create agent '{agent_name}'")
            
            # Create fresh agent instance with request-scoped dependencies
            # CRITICAL: Prefer factory methods to avoid deprecated global tool_dispatcher warnings
            
            logger.info(f"[U+1F527] Creating agent instance for {agent_name} with class {AgentClass.__name__}")
            
            # Map agent names to their class names for consistency
            agent_class_name = AgentClass.__name__
            
            try:
                # FIRST: Check if agent has create_agent_with_context factory method (preferred)
                if hasattr(AgentClass, 'create_agent_with_context'):
                    logger.info(f" PASS:  Using create_agent_with_context factory for {agent_name} ({agent_class_name})")
                    
                    # CRITICAL: Inject dependencies into context BEFORE calling factory method
                    # This enables the factory method to access dependencies via context.get_dependency()
                    if llm_manager is not None:
                        user_context.set_dependency('llm_manager', llm_manager)
                        logger.debug(f"Pre-injected llm_manager into context for {agent_name}")
                    if tool_dispatcher is not None:
                        user_context.set_dependency('tool_dispatcher', tool_dispatcher)
                        logger.debug(f"Pre-injected tool_dispatcher into context for {agent_name}")
                    if self._websocket_bridge is not None:
                        user_context.set_dependency('websocket_bridge', self._websocket_bridge)
                        logger.debug(f"Pre-injected websocket_bridge into context for {agent_name}")
                    
                    # Call factory method with dependencies available in context
                    agent = AgentClass.create_agent_with_context(user_context)
                    
                    # FALLBACK: Also inject dependencies directly as fallback for backward compatibility
                    # This ensures agents work even if they don't use context.get_dependency() methods
                    if hasattr(agent, 'llm_manager') and llm_manager is not None:
                        if agent.llm_manager is None:  # Only inject if not already set by factory
                            agent.llm_manager = llm_manager
                            logger.debug(f"Fallback: Injected llm_manager into {agent_name}")
                    if hasattr(agent, 'tool_dispatcher') and tool_dispatcher is not None:
                        if agent.tool_dispatcher is None:  # Only inject if not already set by factory
                            agent.tool_dispatcher = tool_dispatcher
                            logger.debug(f"Fallback: Injected tool_dispatcher into {agent_name}")
                    
                    # GOLDEN PATH COMPATIBILITY: Enable test mode when WebSocket bridge is unavailable
                    if not self._websocket_bridge and hasattr(agent, 'enable_websocket_test_mode'):
                        agent.enable_websocket_test_mode()
                        logger.debug(f"Enabled WebSocket test mode for {agent_name} (no bridge available)")
                else:
                    # FALLBACK: Use legacy constructor patterns (may trigger deprecation warnings)
                    logger.debug(f" WARNING: [U+FE0F] No factory method found for {agent_class_name}, using legacy constructor")
                    
                    # Agents that don't take any parameters
                    no_param_agents = [
                        'TriageSubAgent', 'GoalsTriageSubAgent', 'ReportingSubAgent'
                    ]
                    
                    # Agents that take llm_manager and tool_dispatcher (may trigger deprecation)
                    llm_tool_only_agents = [
                        'DataSubAgent', 'OptimizationsCoreSubAgent', 
                        'ActionsToMeetGoalsSubAgent', 'DataHelperAgent',
                        'SyntheticDataSubAgent'
                    ]
                    
                    # Check by class name for consistency
                    if agent_class_name in no_param_agents:
                        logger.info(f" PASS:  Creating {agent_name} ({agent_class_name}) with no parameters")
                        agent = AgentClass()
                    elif agent_class_name in llm_tool_only_agents:
                        # Note: tool_dispatcher can be None for per-request creation pattern
                        if llm_manager:
                            logger.info(f" PASS:  Creating {agent_name} ({agent_class_name}) with llm_manager (tool_dispatcher: {tool_dispatcher is not None})")
                            agent = AgentClass(
                                llm_manager=llm_manager,
                                tool_dispatcher=tool_dispatcher  # Can be None for per-request pattern
                            )
                        else:
                            # CRITICAL FIX: Never create LLM-requiring agents without LLM manager
                            logger.error(f" FAIL:  CRITICAL: {agent_name} ({agent_class_name}) requires llm_manager but none available")
                            raise RuntimeError(f"Cannot create {agent_name}: LLM manager is required but not available")
                    else:
                        # Try different parameter combinations based on what the agent accepts
                        logger.info(f"[U+1F527] Trying parameter combinations for {agent_name} ({agent_class_name})")
                        
                        # First try no parameters (simpler agents)
                        try:
                            logger.debug(f"   Trying: no parameters")
                            agent = AgentClass()
                            logger.info(f" PASS:  Created {agent_name} with no parameters")
                        except TypeError as e1:
                            # Then try with llm_manager and tool_dispatcher
                            # Note: tool_dispatcher can be None for per-request creation
                            if not llm_manager:
                                # CRITICAL FIX: Don't attempt to create agent without required dependencies
                                logger.error(f" FAIL:  CRITICAL: {agent_name} likely requires llm_manager but none available")
                                raise RuntimeError(f"Cannot create {agent_name}: LLM manager not available (TypeError: {e1})")
                            
                            if llm_manager:
                                try:
                                    logger.debug(f"   Trying: llm_manager + tool_dispatcher (tool_dispatcher: {tool_dispatcher is not None})")
                                    agent = AgentClass(
                                        llm_manager=llm_manager,
                                        tool_dispatcher=tool_dispatcher  # Can be None
                                    )
                                    logger.info(f" PASS:  Created {agent_name} with llm_manager and tool_dispatcher")
                                except TypeError as e2:
                                    # Log detailed error for debugging
                                    logger.error(f" FAIL:  Could not instantiate {agent_name}:")
                                    logger.error(f"   No params error: {e1}")
                                    logger.error(f"   LLM+tool error: {e2}") 
                                    raise RuntimeError(f"Could not instantiate {agent_name}: tried no params ({e1}), tried llm+tool ({e2})")
                            else:
                                raise RuntimeError(f"Could not instantiate {agent_name} without params and no llm/tool available: {e1}")
                        else:
                            # No llm_manager/tool_dispatcher available, try no parameters
                            try:
                                agent = AgentClass()
                                logger.info(f" PASS:  Created {agent_name} with no parameters")
                            except TypeError:
                                raise RuntimeError(f"Could not instantiate {agent_name} without llm_manager/tool_dispatcher")
                                
            except Exception as e:
                logger.error(f" FAIL:  Failed to instantiate {agent_name}: {e}")
                raise RuntimeError(f"Could not instantiate {agent_name}: {e}")
            
            # CRITICAL: Set WebSocket bridge on agent with REAL run_id (not placeholder)
            if hasattr(agent, 'set_websocket_bridge'):
                try:
                    # Validate bridge exists before setting
                    if not self._websocket_bridge:
                        logger.warning(f" WARNING: [U+FE0F] WebSocket bridge not available for {agent_name} - WebSocket events disabled")
                        logger.debug(f"   Agent {agent_name} will function but without WebSocket notifications")
                        # Don't raise error - allow agent to work without WebSocket functionality
                        # Skip WebSocket bridge setting but continue with rest of agent setup
                    else:
                        # Use the WebSocketBridgeAdapter pattern from BaseAgent
                        if hasattr(agent, '_websocket_adapter'):
                            logger.info(f"[U+1F527] Setting WebSocket bridge on {agent_name} via adapter")
                            logger.info(f"   Bridge type: {type(self._websocket_bridge).__name__}")
                            logger.info(f"   Run ID: {user_context.run_id}")
                            
                            agent._websocket_adapter.set_websocket_bridge(
                                self._websocket_bridge, 
                                user_context.run_id,  # REAL run_id from UserExecutionContext
                                agent_name
                            )
                            logger.info(f" PASS:  WebSocket bridge set via adapter for {agent_name} (run_id: {user_context.run_id})")
                        else:
                            # Fallback for older agent implementations
                            agent.set_websocket_bridge(self._websocket_bridge, user_context.run_id)
                            logger.debug(f" PASS:  WebSocket bridge set directly for {agent_name} (run_id: {user_context.run_id})")
                except Exception as e:
                    logger.warning(f"Failed to set WebSocket bridge on agent {agent_name}: {e}")
            
            # Store agent instance for tracking (not in immutable context)
            if not hasattr(self, '_agent_instances'):
                self._agent_instances = {}
            
            instance_key = f"{user_context.user_id}_{agent_name}_{int(time.time() * 1000)}"
            self._agent_instances[instance_key] = {
                'agent': agent,
                'user_context': user_context,
                'created_at': datetime.now(timezone.utc),
                'status': 'created'
            }
            
            creation_time_ms = (time.time() - start_time) * 1000
            
            # Track performance metrics if enabled
            if should_track_metrics and hasattr(self, '_perf_stats'):
                self._perf_stats['agent_creation_ms'].append(creation_time_ms)
            
            # GOLDEN PATH COMPATIBILITY: Enable test mode for agents when WebSocket bridge is unavailable
            # (This catches agents that weren't created via factory method)
            if not self._websocket_bridge and hasattr(agent, 'enable_websocket_test_mode'):
                agent.enable_websocket_test_mode()
                logger.debug(f"Enabled WebSocket test mode for {agent_name} (no bridge configured in factory)")
            
            logger.info(f" PASS:  Created agent instance {agent_name} for user {user_context.user_id} in {creation_time_ms:.1f}ms (run_id: {user_context.run_id})")
            
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
        
        # Performance tracking (if enabled)
        should_track_metrics = self._should_sample()
        
        try:
            logger.info(f"Cleaning up user execution context: {context_id}")
            
            # Unregister run-thread mapping
            if self._websocket_bridge:
                try:
                    if hasattr(self._websocket_bridge, 'unregister_run_mapping'):
                        await self._websocket_bridge.unregister_run_mapping(user_context.run_id)
                except Exception as e:
                    logger.warning(f"Failed to unregister run mapping for {context_id}: {e}")
            
            # Clean up WebSocket emitter if exists
            emitter_key = f"{context_id}_emitter"
            if hasattr(self, '_websocket_emitters') and emitter_key in self._websocket_emitters:
                try:
                    emitter = self._websocket_emitters[emitter_key]
                    
                    # Return to pool if pooling enabled
                    if self._performance_config.enable_emitter_pooling and self._emitter_pool:
                        if hasattr(emitter, 'reset'):  # Check if it's an optimized pooled emitter
                            await self._emitter_pool.release(emitter)
                        else:
                            await emitter.cleanup()
                    else:
                        await emitter.cleanup()
                    
                    del self._websocket_emitters[emitter_key]
                except Exception as e:
                    logger.error(f"Failed to cleanup WebSocket emitter for {context_id}: {e}")
            
            # Clean up agent instances for this context
            if hasattr(self, '_agent_instances'):
                instances_to_remove = []
                for key, instance_data in self._agent_instances.items():
                    if instance_data.get('user_context') == user_context:
                        instances_to_remove.append(key)
                
                for key in instances_to_remove:
                    del self._agent_instances[key]
                
                if instances_to_remove:
                    logger.debug(f"Cleaned up {len(instances_to_remove)} agent instances for {context_id}")
            
            # Close database session if present
            if user_context.db_session:
                try:
                    await user_context.db_session.close()
                    logger.debug(f"Closed database session for {context_id}")
                except Exception as e:
                    logger.warning(f"Failed to close database session for {context_id}: {e}")
            
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
            
            # Track performance metrics if enabled
            if should_track_metrics and hasattr(self, '_perf_stats'):
                self._perf_stats['cleanup_ms'].append(cleanup_time_ms)
            
            logger.info(f" PASS:  Cleaned up user execution context {context_id} in {cleanup_time_ms:.1f}ms")
            
        except Exception as e:
            self._factory_metrics['cleanup_errors'] += 1
            logger.error(f"Error cleaning up user execution context {context_id}: {e}")
    
    @asynccontextmanager
    async def user_execution_scope(self, 
                                  user_id: str,
                                  thread_id: str,
                                  run_id: str,
                                  db_session: Optional[AsyncSession] = None,
                                  websocket_client_id: Optional[str] = None,
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
                websocket_client_id=websocket_client_id,
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
            # Handle both regular dict and WeakValueDictionary cases
            try:
                existing_semaphore = self._user_semaphores.get(user_id)
                if existing_semaphore is not None:
                    return existing_semaphore
            except AttributeError:
                # Fallback for WeakValueDictionary which doesn't have .get() method
                try:
                    return self._user_semaphores[user_id]
                except KeyError:
                    pass
            
            # Create new semaphore if not found
            semaphore = asyncio.Semaphore(self._max_concurrent_per_user)
            self._user_semaphores[user_id] = semaphore
            logger.debug(f"Created semaphore for user {user_id} (max: {self._max_concurrent_per_user})")
            return semaphore
    
    async def _create_emitter(self, user_id: str, thread_id: str, run_id: str) -> UnifiedWebSocketEmitter:
        """Create WebSocket emitter with optional pooling."""
        if self._performance_config.enable_emitter_pooling:
            # Initialize emitter pool if needed
            if self._emitter_pool is None:
                # MIGRATION NOTE: WebSocket pooling requires user context but pool is shared
                # For now, disable pooling until architecture supports shared pools
                logger.debug("WebSocket emitter pooling temporarily disabled - requires user context migration")
                # Future implementation should use a different pooling strategy or
                # create user-agnostic pool managers
                pass
            
            # Get from pool (this will return an OptimizedUserWebSocketEmitter)
            # Note: For now we maintain backward compatibility by creating regular emitters
            # The pooling infrastructure is in place for future optimization
            try:
                # Future: Implement full pooling when UnifiedWebSocketEmitter is adapted
                # For now, the pool exists but we create compatible instances
                logger.debug(f"WebSocket emitter pool available but not yet fully integrated")
            except Exception as e:
                logger.warning(f"Failed to access emitter pool, falling back to direct creation: {e}")
        
        # Create new instance (backward compatible)
        # This maintains 100% compatibility with existing UnifiedWebSocketEmitter
        return UnifiedWebSocketEmitter(
            user_id, thread_id, run_id, self._websocket_bridge
        )
    
    @lru_cache(maxsize=128)
    def _get_cached_agent_class(self, agent_name: str) -> Optional[Type[BaseAgent]]:
        """Get agent class with LRU caching."""
        if not self._performance_config.enable_class_caching:
            return None
        
        # Try AgentClassRegistry first (preferred)
        if self._agent_class_registry:
            return self._agent_class_registry.get_agent_class(agent_name)
        
        return None
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics if pooling enabled."""
        if self._performance_config.enable_emitter_pooling and self._emitter_pool:
            stats = self._emitter_pool.get_statistics()
            return {
                'total_acquired': stats.total_acquired,
                'total_released': stats.total_released,
                'current_active': stats.current_active,
                'current_pooled': stats.current_pooled,
                'cache_hit_rate': stats.cache_hit_rate,
                'average_acquisition_time_ms': stats.average_acquisition_time_ms
            }
        return {}
    
    def _should_sample(self) -> bool:
        """Check if metrics should be sampled."""
        if not self._performance_config.enable_metrics:
            return False
        import random
        return random.random() < self._performance_config.metrics_sample_rate
    
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics for monitoring."""
        metrics = {
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
            },
            'performance_config': self._performance_config.to_dict()
        }
        
        # Add performance statistics if metrics enabled
        if self._performance_config.enable_metrics and hasattr(self, '_perf_stats'):
            perf_data = {}
            for metric_name, values in self._perf_stats.items():
                if values:
                    perf_data[metric_name] = {
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
            metrics['performance_stats'] = perf_data
        
        # Add pool statistics (always include, even if empty)
        metrics['pool_stats'] = self.get_pool_stats()
        
        return metrics
    
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
    
    async def create_agent(self, 
                          agent_name: str,
                          user_context: UserExecutionContext,
                          agent_class: Optional[Type[BaseAgent]] = None) -> BaseAgent:
        """
        COMPATIBILITY METHOD: create_agent() wrapper for create_agent_instance().
        
        This method provides backward compatibility for tests and code that expect
        a create_agent() method on the AgentInstanceFactory. It wraps the standard
        create_agent_instance() method with appropriate logging and deprecation warning.
        
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
        logger.warning(
            f" CYCLE:  COMPATIBILITY: create_agent() method called - redirecting to create_agent_instance(). "
            f"Consider updating calling code to use create_agent_instance() directly for {agent_name}"
        )
        
        # Use the standard create_agent_instance method
        return await self.create_agent_instance(
            agent_name=agent_name,
            user_context=user_context,
            agent_class=agent_class
        )
    
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
    
    def reset_for_testing(self) -> None:
        """
        Reset factory state for testing purposes.
        
        This method clears all internal state to ensure clean test isolation.
        It should only be called during test setup/teardown.
        
        CRITICAL: This method is for testing only and should never be called
        in production code as it will cause resource leaks and context loss.
        """
        logger.debug("Resetting AgentInstanceFactory state for testing")
        
        # Clear active contexts tracking
        self._active_contexts.clear()
        
        # Clear user semaphores
        self._user_semaphores.clear()
        
        # Clear WebSocket emitters if they exist
        if hasattr(self, '_websocket_emitters'):
            self._websocket_emitters.clear()
        
        # Clear agent instances if they exist
        if hasattr(self, '_agent_instances'):
            self._agent_instances.clear()
        
        # Reset factory metrics to initial state
        self._factory_metrics = {
            'total_instances_created': 0,
            'active_contexts': 0,
            'total_contexts_cleaned': 0,
            'creation_errors': 0,
            'cleanup_errors': 0,
            'average_context_lifetime_seconds': 0.0
        }
        
        # Clear performance statistics if enabled
        if self._performance_config.enable_metrics and hasattr(self, '_perf_stats'):
            for metric_name in self._perf_stats:
                self._perf_stats[metric_name].clear()
        
        # Clear agent class cache if enabled
        if self._performance_config.enable_class_caching and hasattr(self, '_agent_class_cache'):
            self._agent_class_cache.clear()
            # Reset the LRU cache
            if hasattr(self, '_get_cached_agent_class'):
                self._get_cached_agent_class.cache_clear()
        
        logger.debug("AgentInstanceFactory state reset completed")


# Singleton factory instance for application use
_factory_instance: Optional[AgentInstanceFactory] = None


def get_agent_instance_factory() -> AgentInstanceFactory:
    """Get singleton AgentInstanceFactory instance."""
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = AgentInstanceFactory()
    
    return _factory_instance


async def configure_agent_instance_factory(agent_class_registry: Optional[AgentClassRegistry] = None,
                                          agent_registry: Optional[AgentRegistry] = None,
                                          websocket_bridge: Optional[AgentWebSocketBridge] = None,
                                          websocket_manager: Optional[WebSocketManager] = None,
                                          llm_manager: Optional[Any] = None,
                                          tool_dispatcher: Optional[Any] = None) -> AgentInstanceFactory:
    """
    Configure the singleton AgentInstanceFactory with infrastructure components.
    
    Args:
        agent_class_registry: Registry containing agent classes (preferred)
        agent_registry: Legacy agent registry (for backward compatibility)
        websocket_bridge: WebSocket bridge for notifications
        websocket_manager: Optional WebSocket manager
        llm_manager: LLM manager for agent communication
        tool_dispatcher: Tool dispatcher for agent tools
        
    Returns:
        AgentInstanceFactory: Configured factory instance
    """
    factory = get_agent_instance_factory()
    factory.configure(
        agent_class_registry=agent_class_registry,
        agent_registry=agent_registry,
        websocket_bridge=websocket_bridge,
        websocket_manager=websocket_manager,
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher
    )
    
    logger.info(" PASS:  AgentInstanceFactory configured and ready for per-request agent instantiation")
    return factory