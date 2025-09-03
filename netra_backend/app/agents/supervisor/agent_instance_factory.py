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
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry, get_agent_class_registry
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# UserExecutionContext is now imported from user_execution_context.py


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
    
    def __init__(self):
        """Initialize the factory with infrastructure components."""
        # Infrastructure components (shared, immutable)
        self._agent_class_registry: Optional[AgentClassRegistry] = None
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
                 agent_class_registry: Optional[AgentClassRegistry] = None,
                 agent_registry: Optional[AgentRegistry] = None,
                 websocket_bridge: Optional[AgentWebSocketBridge] = None,
                 websocket_manager: Optional[WebSocketManager] = None) -> None:
        """
        Configure factory with infrastructure components.
        
        Args:
            agent_class_registry: Registry containing agent classes (preferred)
            agent_registry: Legacy agent registry (for backward compatibility)
            websocket_bridge: WebSocket bridge for agent notifications
            websocket_manager: Optional WebSocket manager for direct access
        """
        if not websocket_bridge:
            raise ValueError("AgentWebSocketBridge cannot be None")
        
        # Prefer AgentClassRegistry but fallback to AgentRegistry for compatibility
        if agent_class_registry:
            self._agent_class_registry = agent_class_registry
            logger.info("✅ AgentInstanceFactory configured with AgentClassRegistry")
        elif agent_registry:
            self._agent_registry = agent_registry
            logger.info("✅ AgentInstanceFactory configured with legacy AgentRegistry")
        else:
            # Try to get global agent class registry
            try:
                self._agent_class_registry = get_agent_class_registry()
                logger.info("✅ AgentInstanceFactory configured with global AgentClassRegistry")
            except Exception as e:
                raise ValueError("Either agent_class_registry or agent_registry must be provided")
        
        self._websocket_bridge = websocket_bridge
        self._websocket_manager = websocket_manager
        
        logger.info("✅ AgentInstanceFactory configured with infrastructure components")
    
    async def create_user_execution_context(self, 
                                           user_id: str,
                                           thread_id: str,
                                           run_id: str,
                                           db_session: Optional[AsyncSession] = None,
                                           websocket_connection_id: Optional[str] = None,
                                           metadata: Optional[Dict[str, Any]] = None) -> UserExecutionContext:
        """
        Create isolated user execution context with all required resources.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            run_id: Unique run identifier for this execution
            db_session: Optional request-scoped database session
            websocket_connection_id: Optional WebSocket connection ID
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
        
        try:
            logger.info(f"Creating user execution context: {context_id}")
            
            # Create user execution context using the proper immutable class
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                websocket_connection_id=websocket_connection_id,
                metadata=metadata or {}
            )
            
            # Create user-specific WebSocket emitter
            websocket_emitter = UserWebSocketEmitter(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_bridge=self._websocket_bridge
            )
            
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
            
            # Get agent class from registries or use provided class
            if agent_class:
                AgentClass = agent_class
                llm_manager = None
                tool_dispatcher = None
            else:
                # Try AgentClassRegistry first (preferred)
                if self._agent_class_registry:
                    AgentClass = self._agent_class_registry.get_agent_class(agent_name)
                    if not AgentClass:
                        raise ValueError(f"Agent '{agent_name}' not found in AgentClassRegistry")
                    
                    # For class registry, we need to get dependencies from legacy registry for now
                    if self._agent_registry:
                        llm_manager = self._agent_registry.llm_manager
                        tool_dispatcher = self._agent_registry.tool_dispatcher
                    else:
                        raise ValueError("No LLM manager or tool dispatcher available")
                
                # Fallback to legacy AgentRegistry
                elif self._agent_registry:
                    agent_instance = self._agent_registry.get(agent_name)
                    if not agent_instance:
                        raise ValueError(f"Agent '{agent_name}' not found in AgentRegistry")
                    
                    AgentClass = type(agent_instance)
                    llm_manager = self._agent_registry.llm_manager
                    tool_dispatcher = self._agent_registry.tool_dispatcher
                else:
                    raise ValueError("No agent registry configured")
            
            # Create fresh agent instance with request-scoped dependencies
            # CRITICAL: Different agents have different constructor signatures
            # We need to handle each pattern appropriately
            
            logger.info(f"🔧 Creating agent instance for {agent_name} with class {AgentClass.__name__}")
            
            # Map agent names to their class names for consistency
            agent_class_name = AgentClass.__name__
            
            # Agents that don't take any parameters
            no_param_agents = [
                'TriageSubAgent', 'GoalsTriageSubAgent', 'ReportingSubAgent'
            ]
            
            # ReportingSubAgent takes optional context parameter (removed - now in no_param)
            optional_context_agents = [
            ]
            
            # Agents that take llm_manager and tool_dispatcher (no name parameter)
            llm_tool_only_agents = [
                'DataSubAgent', 'OptimizationsCoreSubAgent', 
                'ActionsToMeetGoalsSubAgent', 'DataHelperAgent',
                'SyntheticDataSubAgent'
            ]
            
            # Add debug logging
            logger.debug(f"🔍 Agent {agent_class_name} categorization:")
            logger.debug(f"   - Is no_param: {agent_class_name in no_param_agents}")
            logger.debug(f"   - Is llm_tool_only: {agent_class_name in llm_tool_only_agents}")
            
            try:
                # Check by class name for consistency
                if agent_class_name in no_param_agents:
                    logger.info(f"✅ Creating {agent_name} ({agent_class_name}) with no parameters")
                    agent = AgentClass()
                elif agent_class_name in optional_context_agents:
                    logger.info(f"✅ Creating {agent_name} ({agent_class_name}) with optional context")
                    agent = AgentClass(context=user_context)
                elif agent_class_name in llm_tool_only_agents:
                    if llm_manager and tool_dispatcher:
                        logger.info(f"✅ Creating {agent_name} ({agent_class_name}) with llm_manager and tool_dispatcher only")
                        agent = AgentClass(
                            llm_manager=llm_manager,
                            tool_dispatcher=tool_dispatcher
                        )
                    else:
                        logger.warning(f"⚠️ {agent_name} ({agent_class_name}) requires llm_manager and tool_dispatcher, attempting no-param init")
                        agent = AgentClass()
                else:
                    # Try different parameter combinations based on what the agent accepts
                    logger.info(f"🔧 Trying parameter combinations for {agent_name} ({agent_class_name})")
                    
                    # First try no parameters (simpler agents)
                    try:
                        logger.debug(f"   Trying: no parameters")
                        agent = AgentClass()
                        logger.info(f"✅ Created {agent_name} with no parameters")
                    except TypeError as e1:
                        # Then try with llm_manager and tool_dispatcher
                        if llm_manager and tool_dispatcher:
                            try:
                                logger.debug(f"   Trying: llm_manager + tool_dispatcher")
                                agent = AgentClass(
                                    llm_manager=llm_manager,
                                    tool_dispatcher=tool_dispatcher
                                )
                                logger.info(f"✅ Created {agent_name} with llm_manager and tool_dispatcher")
                            except TypeError as e2:
                                # Log detailed error for debugging
                                logger.error(f"❌ Could not instantiate {agent_name}:")
                                logger.error(f"   No params error: {e1}")
                                logger.error(f"   LLM+tool error: {e2}") 
                                raise RuntimeError(f"Could not instantiate {agent_name}: tried no params ({e1}), tried llm+tool ({e2})")
                        else:
                            raise RuntimeError(f"Could not instantiate {agent_name} without params and no llm/tool available: {e1}")
                    else:
                        # No llm_manager/tool_dispatcher available, try no parameters
                        try:
                            agent = AgentClass()
                            logger.info(f"✅ Created {agent_name} with no parameters")
                        except TypeError:
                            raise RuntimeError(f"Could not instantiate {agent_name} without llm_manager/tool_dispatcher")
            except Exception as e:
                logger.error(f"❌ Failed to instantiate {agent_name}: {e}")
                raise RuntimeError(f"Could not instantiate {agent_name}: {e}")
            
            # CRITICAL: Set WebSocket bridge on agent with REAL run_id (not placeholder)
            if hasattr(agent, 'set_websocket_bridge'):
                try:
                    # Use the WebSocketBridgeAdapter pattern from BaseAgent
                    if hasattr(agent, '_websocket_adapter'):
                        agent._websocket_adapter.set_websocket_bridge(
                            self._websocket_bridge, 
                            user_context.run_id,  # REAL run_id from UserExecutionContext
                            agent_name
                        )
                        logger.debug(f"✅ WebSocket bridge set via adapter for {agent_name} (run_id: {user_context.run_id})")
                    else:
                        # Fallback for older agent implementations
                        agent.set_websocket_bridge(self._websocket_bridge, user_context.run_id)
                        logger.debug(f"✅ WebSocket bridge set directly for {agent_name} (run_id: {user_context.run_id})")
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
            logger.info(f"✅ Created agent instance {agent_name} for user {user_context.user_id} in {creation_time_ms:.1f}ms (run_id: {user_context.run_id})")
            
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
                    if hasattr(self._websocket_bridge, 'unregister_run_mapping'):
                        await self._websocket_bridge.unregister_run_mapping(user_context.run_id)
                except Exception as e:
                    logger.warning(f"Failed to unregister run mapping for {context_id}: {e}")
            
            # Clean up WebSocket emitter if exists
            emitter_key = f"{context_id}_emitter"
            if hasattr(self, '_websocket_emitters') and emitter_key in self._websocket_emitters:
                try:
                    await self._websocket_emitters[emitter_key].cleanup()
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
            logger.info(f"✅ Cleaned up user execution context {context_id} in {cleanup_time_ms:.1f}ms")
            
        except Exception as e:
            self._factory_metrics['cleanup_errors'] += 1
            logger.error(f"Error cleaning up user execution context {context_id}: {e}")
    
    @asynccontextmanager
    async def user_execution_scope(self, 
                                  user_id: str,
                                  thread_id: str,
                                  run_id: str,
                                  db_session: Optional[AsyncSession] = None,
                                  websocket_connection_id: Optional[str] = None,
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
                websocket_connection_id=websocket_connection_id,
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


async def configure_agent_instance_factory(agent_class_registry: Optional[AgentClassRegistry] = None,
                                          agent_registry: Optional[AgentRegistry] = None,
                                          websocket_bridge: Optional[AgentWebSocketBridge] = None,
                                          websocket_manager: Optional[WebSocketManager] = None) -> AgentInstanceFactory:
    """
    Configure the singleton AgentInstanceFactory with infrastructure components.
    
    Args:
        agent_class_registry: Registry containing agent classes (preferred)
        agent_registry: Legacy agent registry (for backward compatibility)
        websocket_bridge: WebSocket bridge for notifications
        websocket_manager: Optional WebSocket manager
        
    Returns:
        AgentInstanceFactory: Configured factory instance
    """
    factory = get_agent_instance_factory()
    factory.configure(
        agent_class_registry=agent_class_registry,
        agent_registry=agent_registry,
        websocket_bridge=websocket_bridge,
        websocket_manager=websocket_manager
    )
    
    logger.info("✅ AgentInstanceFactory configured and ready for per-request agent instantiation")
    return factory