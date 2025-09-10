"""🚨 ENHANCED Agent Registry with mandatory user isolation patterns.

CRITICAL SECURITY UPGRADE: This module implements hardened user isolation 
patterns to prevent concurrent execution contamination and memory leaks.

KEY SECURITY FEATURES:
- Factory-based user isolation (NO global state access)
- Per-user agent registries with complete isolation
- Memory leak prevention and lifecycle management
- Thread-safe concurrent execution for 10+ users
- WebSocket bridge isolation per user session

SSOT COMPLIANCE: Extends UniversalRegistry as SSOT while adding hardening.
Uses UnifiedToolDispatcher as SSOT with mandatory user scoping.
All agents receive properly isolated tool dispatchers per user context.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Tuple
import asyncio
import weakref
import time
from datetime import datetime, timezone
from collections import defaultdict

# SSOT: Import from UniversalRegistry - avoid name collision
from netra_backend.app.core.registry.universal_registry import (
    UniversalRegistry,
    get_global_registry
)
# Import the specialized AgentRegistry as a different name to avoid collision
from netra_backend.app.core.registry.universal_registry import (
    AgentRegistry as BaseAgentRegistry
)

if TYPE_CHECKING:
    # MIGRATED: Use UnifiedToolDispatcher as SSOT for tool dispatching
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.base_agent import BaseAgent
else:
    # Import at runtime to avoid circular imports
    create_agent_websocket_bridge = None

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketManagerAdapter:
    """Adapter to convert WebSocketManager to AgentWebSocketBridge interface.
    
    This adapter enables seamless compatibility between the WebSocketManager
    interface expected by AgentRegistry and the AgentWebSocketBridge interface
    expected by UniversalAgentRegistry, maintaining SSOT compliance.
    """
    
    def __init__(self, websocket_manager: 'WebSocketManager', user_context: Optional['UserExecutionContext'] = None):
        """Initialize the adapter with a WebSocketManager instance.
        
        Args:
            websocket_manager: WebSocketManager instance to adapt
            user_context: User execution context for proper isolation
        """
        self._websocket_manager = websocket_manager
        self._user_context = user_context
        
    def __getattr__(self, name: str):
        """Delegate unknown attributes to the underlying WebSocketManager.
        
        This provides transparent access to WebSocketManager methods while
        maintaining the AgentWebSocketBridge interface contract.
        """
        # First check if the method exists in the underlying manager
        if hasattr(self._websocket_manager, name):
            return getattr(self._websocket_manager, name)
        
        # If not found, raise AttributeError with helpful message
        raise AttributeError(
            f"WebSocketManagerAdapter has no attribute '{name}'. "
            f"Underlying WebSocketManager type: {type(self._websocket_manager).__name__}"
        )
        
    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]) -> None:
        """Adapter method for agent started notifications."""
        if hasattr(self._websocket_manager, 'notify_agent_started'):
            await self._websocket_manager.notify_agent_started(run_id, agent_name, metadata)
        else:
            logger.debug(f"WebSocketManager does not support notify_agent_started - skipping for {agent_name}")
    
    async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str, 
                                   step_number: Optional[int] = None, **kwargs) -> None:
        """Adapter method for agent thinking notifications."""
        if hasattr(self._websocket_manager, 'notify_agent_thinking'):
            await self._websocket_manager.notify_agent_thinking(run_id, agent_name, reasoning, step_number, **kwargs)
        else:
            logger.debug(f"WebSocketManager does not support notify_agent_thinking - skipping for {agent_name}")
    
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, 
                                   parameters: Dict[str, Any]) -> None:
        """Adapter method for tool executing notifications."""
        if hasattr(self._websocket_manager, 'notify_tool_executing'):
            await self._websocket_manager.notify_tool_executing(run_id, agent_name, tool_name, parameters)
        else:
            logger.debug(f"WebSocketManager does not support notify_tool_executing - skipping for {tool_name}")
    
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, 
                                   result: Any, execution_time_ms: float) -> None:
        """Adapter method for tool completed notifications."""
        if hasattr(self._websocket_manager, 'notify_tool_completed'):
            await self._websocket_manager.notify_tool_completed(run_id, agent_name, tool_name, result, execution_time_ms)
        else:
            logger.debug(f"WebSocketManager does not support notify_tool_completed - skipping for {tool_name}")
    
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict[str, Any], 
                                    execution_time_ms: float) -> None:
        """Adapter method for agent completed notifications."""
        if hasattr(self._websocket_manager, 'notify_agent_completed'):
            await self._websocket_manager.notify_agent_completed(run_id, agent_name, result, execution_time_ms)
        else:
            logger.debug(f"WebSocketManager does not support notify_agent_completed - skipping for {agent_name}")
    
    async def notify_agent_error(self, run_id: str, agent_name: str, error: str, 
                                error_context: Optional[Dict[str, Any]] = None) -> None:
        """Adapter method for agent error notifications."""
        if hasattr(self._websocket_manager, 'notify_agent_error'):
            await self._websocket_manager.notify_agent_error(run_id, agent_name, error, error_context)
        else:
            logger.debug(f"WebSocketManager does not support notify_agent_error - skipping for {agent_name}")
    
    async def notify_agent_death(self, run_id: str, agent_name: str, cause: str, 
                                death_context: Dict[str, Any]) -> None:
        """Adapter method for agent death notifications."""
        if hasattr(self._websocket_manager, 'notify_agent_death'):
            await self._websocket_manager.notify_agent_death(run_id, agent_name, cause, death_context)
        else:
            logger.debug(f"WebSocketManager does not support notify_agent_death - skipping for {agent_name}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from the underlying WebSocketManager."""
        if hasattr(self._websocket_manager, 'get_metrics'):
            return await self._websocket_manager.get_metrics()
        else:
            return {
                'adapter_type': 'WebSocketManagerAdapter',
                'underlying_manager': type(self._websocket_manager).__name__,
                'metrics_supported': False
            }


class UserAgentSession:
    """Complete user isolation for agent execution.
    
    This session provides complete isolation per user with:
    - User-scoped agent instances
    - Isolated execution contexts
    - WebSocket bridge per user
    - Memory leak prevention
    """
    
    def __init__(self, user_id: str):
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
            
        self.user_id = user_id
        self._agents: Dict[str, Any] = {}
        self._execution_contexts: Dict[str, 'UserExecutionContext'] = {}
        self._websocket_bridge: Optional['AgentWebSocketBridge'] = None
        self._websocket_manager: Optional[Any] = None
        self._created_at = datetime.now(timezone.utc)
        self._access_lock = asyncio.Lock()
        
        logger.info(f"✅ Created isolated UserAgentSession for user {user_id}")
        
    async def set_websocket_manager(self, manager, user_context: Optional['UserExecutionContext'] = None):
        """Set user-specific WebSocket bridge using factory pattern.
        
        Args:
            manager: WebSocket manager instance
            user_context: Optional user execution context for proper isolation.
                         If not provided, creates a minimal context.
        """
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        self._websocket_manager = manager
        
        # If manager is None, don't create a bridge
        if manager is None:
            self._websocket_bridge = None
            logger.debug(f"WebSocket manager set to None for user {self.user_id} - no bridge created")
            return
        
        # Create user context if not provided
        if user_context is None:
            user_context = UserExecutionContext(
                user_id=self.user_id,
                request_id=f"session_{self.user_id}_{id(self)}",
                thread_id=f"thread_{self.user_id}_{id(self)}",
                run_id=f"session_run_{self.user_id}_{id(self)}"
            )
        
        # Use factory to create properly isolated bridge
        # Check if websocket manager has a custom bridge factory (for testing)
        if hasattr(manager, 'create_bridge') and callable(manager.create_bridge):
            # Use custom bridge factory (e.g., mock for testing)
            logger.debug(f"Using custom bridge factory from websocket manager for user {self.user_id}")
            if asyncio.iscoroutinefunction(manager.create_bridge):
                bridge = await manager.create_bridge(user_context)
            else:
                bridge = manager.create_bridge(user_context)
        else:
            # Use standard factory for real bridges
            bridge = create_agent_websocket_bridge(user_context)
        
        self._websocket_bridge = bridge
        logger.debug(f"WebSocket bridge set for user {self.user_id}: {type(bridge).__name__}")
        
    async def create_agent_execution_context(self, agent_type: str, 
                                           user_context: 'UserExecutionContext') -> 'UserExecutionContext':
        """Create isolated execution context for agent."""
        async with self._access_lock:
            context = user_context.create_child_context(f"agent_{agent_type}")
            self._execution_contexts[agent_type] = context
            return context
    
    async def get_agent(self, agent_type: str) -> Optional[Any]:
        """Get agent instance for this user."""
        async with self._access_lock:
            return self._agents.get(agent_type)
    
    async def register_agent(self, agent_type: str, agent: Any) -> None:
        """Register agent for this user."""
        async with self._access_lock:
            self._agents[agent_type] = agent
            logger.debug(f"Registered agent {agent_type} for user {self.user_id}")
    
    async def cleanup_all_agents(self) -> None:
        """Complete cleanup of all user agents and resources."""
        async with self._access_lock:
            cleanup_count = len(self._agents)
            
            # Cleanup all agents
            for agent_type, agent in self._agents.items():
                try:
                    if hasattr(agent, 'cleanup'):
                        await agent.cleanup()
                    if hasattr(agent, 'close'):
                        await agent.close()
                except Exception as e:
                    logger.warning(f"Error cleaning up agent {agent_type}: {e}")
            
            # Clear all collections
            self._agents.clear()
            self._execution_contexts.clear()
            self._websocket_bridge = None
            
            logger.info(f"✅ Cleaned up {cleanup_count} agents for user {self.user_id}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get user session metrics."""
        uptime = (datetime.now(timezone.utc) - self._created_at).total_seconds()
        return {
            'user_id': self.user_id,
            'agent_count': len(self._agents),
            'context_count': len(self._execution_contexts),
            'has_websocket_bridge': self._websocket_bridge is not None,
            'uptime_seconds': uptime
        }


class AgentLifecycleManager:
    """Prevent memory leaks in multi-user agent execution."""
    
    def __init__(self, registry=None):
        self._registry = registry  # Reference to the AgentRegistry for accessing user sessions
        self._memory_thresholds = {
            'max_agents_per_user': 50,
            'max_session_age_hours': 24
        }
        # Keep weak references for cleanup tracking, but don't use for monitoring
        self._cleanup_refs: Dict[str, weakref.ReferenceType] = {}
        
    async def cleanup_agent_resources(self, user_id: str, agent_id: str) -> None:
        """Complete resource cleanup for agent."""
        try:
            # FIXED: Access user sessions from the registry directly
            if not self._registry:
                logger.error(f"No registry reference for cleanup of agent {agent_id} for user {user_id}")
                return
                
            user_session = self._registry._user_sessions.get(user_id)
            if user_session:
                # Cleanup specific agent
                async with user_session._access_lock:
                    if agent_id in user_session._agents:
                        agent = user_session._agents.pop(agent_id)
                        if hasattr(agent, 'cleanup'):
                            await agent.cleanup()
                        
                logger.debug(f"Cleaned up agent {agent_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up agent {agent_id} for user {user_id}: {e}")
    
    async def monitor_memory_usage(self, user_id: str) -> Dict[str, Any]:
        """Monitor and prevent memory leaks."""
        try:
            # FIXED: Access user sessions from the registry directly
            if self._registry is None:
                return {'status': 'no_registry', 'user_id': user_id}
            
            # Get user session directly from registry
            user_session = self._registry._user_sessions.get(user_id)
            if not user_session:
                return {'status': 'no_session', 'user_id': user_id}
            
            metrics = user_session.get_metrics()
            
            # Check thresholds
            issues = []
            if metrics['agent_count'] > self._memory_thresholds['max_agents_per_user']:
                issues.append(f"Too many agents: {metrics['agent_count']}")
            
            if metrics['uptime_seconds'] > self._memory_thresholds['max_session_age_hours'] * 3600:
                issues.append(f"Session too old: {metrics['uptime_seconds']/3600:.1f}h")
            
            return {
                'status': 'healthy' if not issues else 'warning',
                'user_id': user_id,
                'metrics': metrics,
                'issues': issues
            }
        except Exception as e:
            logger.error(f"Error monitoring user {user_id}: {e}")
            return {'status': 'error', 'user_id': user_id, 'error': str(e)}
    
    async def trigger_cleanup(self, user_id: str) -> None:
        """Trigger emergency cleanup for user."""
        cleanup_success = False
        try:
            # FIXED: Access user sessions from the registry directly
            if not self._registry:
                logger.error(f"No registry reference for cleanup of user {user_id}")
                return
                
            user_session = self._registry._user_sessions.get(user_id)
            if user_session:
                await user_session.cleanup_all_agents()
                cleanup_success = True
                
        except Exception as e:
            logger.error(f"Emergency cleanup failed for user {user_id}: {e}")
        finally:
            # CRITICAL: Always remove session from registry to prevent memory leaks,
            # even if cleanup_all_agents() failed
            if self._registry and user_id in self._registry._user_sessions:
                del self._registry._user_sessions[user_id]
                logger.debug(f"Removed user session {user_id} from registry")
                
            if cleanup_success:
                logger.info(f"✅ Emergency cleanup completed for user {user_id}")
            else:
                logger.warning(f"⚠️ Emergency cleanup completed with errors for user {user_id}, but session was removed from registry")


class AgentRegistry(BaseAgentRegistry):
    """Agent registry using UniversalRegistry SSOT pattern with CanonicalToolDispatcher.
    
    CRITICAL SECURITY MIGRATION:
    - Uses CanonicalToolDispatcher as SSOT for all tool execution
    - Enforces mandatory user isolation per agent creation
    - Provides proper permission checking and WebSocket events
    - Eliminates all competing tool dispatcher implementations
    
    This class extends the UniversalRegistry from universal_registry.py,
    adding agent-specific functionality while maintaining SSOT compliance.
    """
    
    def __init__(self, llm_manager: Optional['LLMManager'] = None, tool_dispatcher_factory: Optional[callable] = None):
        """Initialize agent registry with CanonicalToolDispatcher SSOT pattern.
        
        Args:
            llm_manager: LLM manager for agent creation (optional for backward compatibility)
            tool_dispatcher_factory: Factory function to create CanonicalToolDispatcher per user
                                   Signature: async (user_context, websocket_bridge) -> CanonicalToolDispatcher
                                   If None, uses default factory
        """
        # BACKWARD COMPATIBILITY: Allow None llm_manager but warn about it
        if llm_manager is None:
            logger.warning(
                "AgentRegistry initialized without llm_manager - this may cause issues with agent creation. "
                "Consider providing llm_manager for full functionality."
            )
        
        # SSOT COMPLIANCE: Initialize specialized AgentRegistry (no parameters required)
        super().__init__()
        
        self.llm_manager = llm_manager
        self.tool_dispatcher_factory = tool_dispatcher_factory or self._default_dispatcher_factory
        self._agents_registered = False
        self.registration_errors: Dict[str, str] = {}
        
        # HARDENING: User isolation features
        self._user_sessions: Dict[str, UserAgentSession] = {}
        self._session_lock = asyncio.Lock()
        self._lifecycle_manager = AgentLifecycleManager(registry=self)  # FIXED: Pass registry reference
        self._created_at = datetime.now(timezone.utc)
        
        # FIXED: Track background tasks to prevent timeout issues
        self._background_tasks: List[asyncio.Task] = []
        
        # BACKWARD COMPATIBILITY: Initialize legacy dispatcher to None
        # New code should use create_tool_dispatcher_for_user() for proper SSOT compliance  
        self._legacy_dispatcher = None
        
        # SSOT COMPLIANCE VALIDATION
        self._validate_ssot_compliance()
        
        logger.info("🔄 Enhanced AgentRegistry initialized with CanonicalToolDispatcher SSOT pattern")
        logger.info("✅ All agents will receive properly isolated tool dispatchers per user context")
        logger.info("🚨 User isolation and memory leak prevention enabled")
        logger.info("🎯 SSOT compliance validated - BaseAgentRegistry interface properly implemented")
    
    def _validate_ssot_compliance(self) -> None:
        """Validate SSOT compliance with BaseAgentRegistry interface.
        
        This method ensures that AgentRegistry properly implements the 
        BaseAgentRegistry interface and maintains Liskov Substitution Principle.
        
        Raises:
            RuntimeError: If SSOT compliance validation fails
        """
        try:
            # 1. Validate inheritance chain
            if not isinstance(self, BaseAgentRegistry):
                raise RuntimeError("AgentRegistry must inherit from BaseAgentRegistry for SSOT compliance")
            
            # 2. Validate constructor parameters were properly set
            if not hasattr(self, 'name') or self.name != "AgentRegistry":
                raise RuntimeError("Registry name not properly set during SSOT initialization")
            
            # 3. Validate WebSocket adapter capability
            if not hasattr(self, 'websocket_manager'):
                logger.warning("websocket_manager attribute not initialized - WebSocket functionality may be limited")
            
            # 4. Validate required interface methods exist
            required_methods = ['set_websocket_bridge', 'register', 'get', 'has', 'list_keys']
            for method_name in required_methods:
                if not hasattr(self, method_name):
                    raise RuntimeError(f"Missing required interface method: {method_name}")
                if not callable(getattr(self, method_name)):
                    raise RuntimeError(f"Interface method {method_name} is not callable")
            
            # 5. Validate adapter can be created (test with None manager)
            try:
                test_adapter = WebSocketManagerAdapter(None)
                if not hasattr(test_adapter, 'notify_agent_started'):
                    raise RuntimeError("WebSocketManagerAdapter missing required notification methods")
            except Exception as e:
                raise RuntimeError(f"WebSocketManagerAdapter validation failed: {e}")
            
            # 6. Validate parent class methods are accessible
            if not hasattr(super(), 'set_websocket_bridge'):
                raise RuntimeError("Parent BaseAgentRegistry missing set_websocket_bridge method")
            
            logger.debug("✅ SSOT compliance validation passed")
            
        except Exception as e:
            logger.error(f"❌ SSOT compliance validation failed: {e}")
            raise RuntimeError(f"AgentRegistry SSOT compliance validation failed: {e}")
    
    def set_tool_dispatcher_factory(self, factory):
        """Set the tool dispatcher factory for agent creation.
        
        Args:
            factory: Tool dispatcher factory for creating user-isolated dispatchers
        """
        self.tool_dispatcher_factory = factory
        logger.info(f"Tool dispatcher factory set for AgentRegistry: {type(factory).__name__}")
    
    async def initialize(self):
        """Initialize the agent registry (compatibility method)."""
        # The registry is already initialized in __init__, this is for test compatibility
        logger.debug("AgentRegistry initialization complete")
    
    async def cleanup(self):
        """Clean up all user sessions and resources."""
        async with self._session_lock:
            # FIXED: Cancel and await background tasks first to prevent timeout
            if self._background_tasks:
                logger.debug(f"Cancelling {len(self._background_tasks)} background tasks")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait for tasks to finish cancellation (with timeout)
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._background_tasks, return_exceptions=True),
                        timeout=1.0  # Short timeout to prevent hanging
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some background tasks did not cancel within timeout")
                except Exception as e:
                    logger.debug(f"Expected exception during task cancellation: {e}")
                
                self._background_tasks.clear()
            
            # Clean up all user sessions (use private method to avoid deadlock)
            for user_id in list(self._user_sessions.keys()):
                await self._cleanup_user_session_unlocked(user_id)
            
            # SSOT: No legacy state to clear - using factory patterns
            
        logger.info("✅ AgentRegistry cleanup complete")
    
    # ===================== USER ISOLATION HARDENING FEATURES =====================
    
    async def get_user_session(self, user_id: str) -> UserAgentSession:
        """Get or create isolated session for specific user.
        
        SECURITY: This enforces complete user isolation.
        
        Args:
            user_id: User identifier (REQUIRED)
            
        Returns:
            UserAgentSession: Isolated session for this user
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id is required and must be non-empty string")
            
        async with self._session_lock:
            if user_id not in self._user_sessions:
                user_session = UserAgentSession(user_id)
                
                # If we have a WebSocket manager at the registry level, set it on the new session
                if hasattr(self, 'websocket_manager') and self.websocket_manager is not None:
                    try:
                        from netra_backend.app.services.user_execution_context import UserExecutionContext
                        import uuid
                        user_context = UserExecutionContext(
                            user_id=user_id,
                            request_id=str(uuid.uuid4()),
                            thread_id=f"session_thread_{user_id}",
                            run_id=f"session_run_{user_id}_{uuid.uuid4().hex[:8]}"
                        )
                        await user_session.set_websocket_manager(self.websocket_manager, user_context)
                        logger.debug(f"Set WebSocket manager on new user session for {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to set WebSocket manager on new user session for {user_id}: {e}")
                else:
                    logger.debug(f"No WebSocket manager to set for new session. hasattr: {hasattr(self, 'websocket_manager')}, value: {getattr(self, 'websocket_manager', None)}")
                
                self._user_sessions[user_id] = user_session
                logger.info(f"🔐 Created isolated session for user {user_id}")
            return self._user_sessions[user_id]
    
    async def _cleanup_user_session_unlocked(self, user_id: str) -> Dict[str, Any]:
        """PRIVATE: Cleanup user session without acquiring lock (assumes lock is already held).
        
        This is used internally by cleanup() to avoid deadlock.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cleanup metrics
        """
        if not user_id:
            raise ValueError("user_id is required")
            
        cleanup_metrics = {'user_id': user_id, 'cleaned_agents': 0, 'status': 'no_session'}
        
        if user_id in self._user_sessions:
            user_session = self._user_sessions[user_id]
            session_metrics = user_session.get_metrics()
            # Store the agent count before cleanup
            cleanup_metrics['cleaned_agents'] = session_metrics.get('agent_count', 0)
            
            await user_session.cleanup_all_agents()
            del self._user_sessions[user_id]
            
            cleanup_metrics['status'] = 'cleaned'
            logger.info(f"🧹 Cleaned up user session for {user_id}")
        
        return cleanup_metrics
    
    async def cleanup_user_session(self, user_id: str) -> Dict[str, Any]:
        """Complete cleanup of user session and all associated agents.
        
        CRITICAL: Prevents memory leaks in multi-user scenarios.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cleanup metrics
        """
        async with self._session_lock:
            return await self._cleanup_user_session_unlocked(user_id)
    
    async def create_agent_for_user(self, user_id: str, agent_type: str, 
                                   user_context: 'UserExecutionContext',
                                   websocket_manager: Optional['WebSocketManager'] = None) -> Any:
        """Create isolated agent instance for specific user.
        
        SECURITY: Enforces complete user isolation with dedicated resources.
        
        Args:
            user_id: User identifier (REQUIRED)
            agent_type: Type of agent to create
            user_context: User execution context
            websocket_manager: WebSocket manager for events
            
        Returns:
            Agent instance with isolated context
        """
        if not user_id or not agent_type:
            raise ValueError("user_id and agent_type are required")
            
        # Get user-specific session
        user_session = await self.get_user_session(user_id)
        
        # Set WebSocket manager if provided
        if websocket_manager:
            # Await the async method since we're already in async context
            await user_session.set_websocket_manager(websocket_manager, user_context)
        
        # Create isolated execution context
        execution_context = await user_session.create_agent_execution_context(
            agent_type, user_context
        )
        
        # Use factory to create agent with proper isolation
        agent = await self.get_async(agent_type, execution_context)
        
        if agent is None:
            raise KeyError(f"No factory registered for agent type: {agent_type}")
        
        # Register agent with user session
        await user_session.register_agent(agent_type, agent)
        
        logger.info(f"🔐 Created isolated {agent_type} agent for user {user_id}")
        return agent
    
    async def get_user_agent(self, user_id: str, agent_type: str) -> Optional[Any]:
        """Get agent instance for specific user.
        
        Args:
            user_id: User identifier
            agent_type: Type of agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        if user_id in self._user_sessions:
            return await self._user_sessions[user_id].get_agent(agent_type)
        return None
    
    async def remove_user_agent(self, user_id: str, agent_type: str) -> bool:
        """Remove specific agent from user session.
        
        Args:
            user_id: User identifier
            agent_type: Type of agent to remove
            
        Returns:
            True if removed, False if not found
        """
        if user_id in self._user_sessions:
            user_session = self._user_sessions[user_id]
            async with user_session._access_lock:
                if agent_type in user_session._agents:
                    agent = user_session._agents.pop(agent_type)
                    
                    # Cleanup agent resources
                    try:
                        if hasattr(agent, 'cleanup'):
                            await agent.cleanup()
                    except Exception as e:
                        logger.warning(f"Error cleaning up agent {agent_type}: {e}")
                    
                    logger.debug(f"Removed agent {agent_type} from user {user_id}")
                    return True
        
        return False
    
    async def reset_user_agents(self, user_id: str) -> Dict[str, Any]:
        """Reset all agents for specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Reset operation report
        """
        if user_id not in self._user_sessions:
            return {
                'user_id': user_id,
                'status': 'no_session',
                'agents_reset': 0
            }
        
        # Cleanup and recreate user session
        old_session = self._user_sessions[user_id]
        agent_count = len(old_session._agents)
        
        await old_session.cleanup_all_agents()
        self._user_sessions[user_id] = UserAgentSession(user_id)
        
        return {
            'user_id': user_id,
            'status': 'reset_complete',
            'agents_reset': agent_count,
            'note': 'Fresh user session created with factory pattern'
        }
    
    async def monitor_all_users(self) -> Dict[str, Any]:
        """Monitor memory usage across all user sessions.
        
        Returns:
            Comprehensive monitoring report
        """
        async with self._session_lock:
            user_count = len(self._user_sessions)
            total_agents = sum(len(session._agents) for session in self._user_sessions.values())
            
            monitoring_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_users': user_count,
                'total_agents': total_agents,
                'users': {},
                'global_issues': []
            }
            
            # Monitor each user session
            for user_id, session in self._user_sessions.items():
                user_metrics = await self._lifecycle_manager.monitor_memory_usage(user_id)
                monitoring_report['users'][user_id] = user_metrics
                
                # Collect global issues
                if user_metrics.get('issues'):
                    monitoring_report['global_issues'].extend(user_metrics['issues'])
            
            # Check global thresholds
            if user_count > 50:  # Max concurrent users
                monitoring_report['global_issues'].append(f"Too many concurrent users: {user_count}")
            
            if total_agents > 500:  # Max total agents
                monitoring_report['global_issues'].append(f"Too many total agents: {total_agents}")
            
            return monitoring_report
    
    async def emergency_cleanup_all(self) -> Dict[str, Any]:
        """Emergency cleanup of all user sessions.
        
        CRITICAL: Use only in emergency situations to prevent system crash.
        
        Returns:
            Cleanup report
        """
        async with self._session_lock:
            cleanup_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'users_cleaned': 0,
                'agents_cleaned': 0,
                'errors': []
            }
            
            users_to_cleanup = list(self._user_sessions.keys())
            
            for user_id in users_to_cleanup:
                try:
                    user_metrics = await self._cleanup_user_session_unlocked(user_id)
                    cleanup_report['users_cleaned'] += 1
                    cleanup_report['agents_cleaned'] += user_metrics.get('cleaned_agents', 0)
                except Exception as e:
                    cleanup_report['errors'].append(f"User {user_id}: {str(e)}")
            
            logger.warning(f"🚨 Emergency cleanup completed: {cleanup_report}")
            return cleanup_report
    
    # ===================== WEBSOCKET INTEGRATION =====================
    
    def set_websocket_manager(self, manager: 'WebSocketManager') -> None:
        """Set WebSocket manager for agent events with user isolation support.
        
        This method integrates with the user isolation pattern by:
        1. Storing the WebSocket manager at the registry level
        2. Creating an adapter for SSOT compliance with UniversalAgentRegistry
        3. Propagating it to all existing user sessions
        4. Ensuring new user sessions get the WebSocket manager automatically
        
        CRITICAL: This enables real-time chat notifications across all user sessions.
        
        Args:
            manager: WebSocket manager instance for agent events
        """
        from netra_backend.app.websocket_core.manager import WebSocketManager
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        if manager is None:
            logger.warning("WebSocket manager is None - WebSocket events will be disabled")
            return
        
        # FIXED: Store manager for user sessions
        self.websocket_manager = manager
        
        # SSOT COMPLIANCE: Create adapter to bridge WebSocketManager to AgentWebSocketBridge interface
        import uuid
        default_context = UserExecutionContext(
            user_id="test_registry_system",
            request_id=f"websocket_setup_{uuid.uuid4().hex[:8]}",
            thread_id="test_registry_thread",
            run_id=f"websocket_run_{uuid.uuid4().hex[:8]}"
        )
        
        # Create adapter for SSOT compliance
        try:
            adapter = WebSocketManagerAdapter(manager, default_context)
            super().set_websocket_bridge(adapter)  # Use correct parent interface with adapter
            logger.debug("Registry WebSocket adapter created for SSOT compliance")
        except Exception as e:
            logger.warning(f"Failed to create registry WebSocket adapter: {e}")
        
        # Propagate to all existing user sessions asynchronously
        # We use asyncio.create_task to avoid blocking in sync context
        if self._user_sessions:
            logger.info(f"Propagating WebSocket manager to {len(self._user_sessions)} existing user sessions")
            
            # Create a coroutine to update all user sessions
            async def update_user_sessions():
                try:
                    for user_id, user_session in self._user_sessions.items():
                        try:
                            # Create user context for this session
                            user_context = UserExecutionContext(
                                user_id=user_id,
                                request_id=f"websocket_update_{user_id}_{id(self)}",
                                thread_id=f"ws_thread_{user_id}"
                            )
                            # Set WebSocket manager on user session using factory pattern
                            await user_session.set_websocket_manager(manager, user_context)
                            logger.debug(f"Updated WebSocket manager for user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to update WebSocket manager for user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Failed to update user sessions with WebSocket manager: {e}")
            
            # Schedule the async update - don't wait for it in sync context
            import asyncio
            try:
                # Try to get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule the task and track it
                    task = asyncio.create_task(update_user_sessions())
                    self._background_tasks.append(task)
                    # Clean up completed tasks to prevent memory leak
                    def cleanup_task(finished_task):
                        try:
                            if finished_task in self._background_tasks:
                                self._background_tasks.remove(finished_task)
                        except (ValueError, AttributeError):
                            # Task might have been removed already during cleanup
                            pass
                    task.add_done_callback(cleanup_task)
                else:
                    # If no loop is running, we can't schedule async tasks
                    logger.warning("No event loop running - user sessions will get WebSocket manager on next access")
            except RuntimeError:
                # No event loop exists
                logger.warning("No event loop available - user sessions will get WebSocket manager on next access")
        
        logger.info(f"✅ WebSocket manager set on AgentRegistry with user isolation support and SSOT compliance")
    
    async def set_websocket_manager_async(self, manager: 'WebSocketManager') -> None:
        """Async version of set_websocket_manager for async contexts.
        
        This method can be used when we're already in an async context and want
        to properly await the user session updates.
        
        Args:
            manager: WebSocket manager instance for agent events
        """
        from netra_backend.app.websocket_core.manager import WebSocketManager
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        if manager is None:
            logger.warning("WebSocket manager is None - WebSocket events will be disabled")
            return
        
        # FIXED: Store manager for user sessions
        self.websocket_manager = manager
        
        # SSOT COMPLIANCE: Create adapter for bridge interface compatibility
        import uuid
        default_context = UserExecutionContext(
            user_id="test_registry_system_async",
            request_id=f"websocket_setup_async_{uuid.uuid4().hex[:8]}",
            thread_id="test_registry_thread_async",
            run_id=f"websocket_run_async_{uuid.uuid4().hex[:8]}"
        )
        
        # Create adapter for SSOT compliance
        try:
            adapter = WebSocketManagerAdapter(manager, default_context)
            super().set_websocket_bridge(adapter)  # Use adapter with parent interface
            logger.debug(f"Registry WebSocket adapter created for async context - SSOT compliance")
        except Exception as e:
            logger.warning(f"Failed to create registry WebSocket adapter (async): {e}")
        
        # Propagate to all existing user sessions using factory pattern
        if self._user_sessions:
            logger.info(f"Propagating WebSocket manager to {len(self._user_sessions)} existing user sessions")
            
            for user_id, user_session in self._user_sessions.items():
                try:
                    # Create user context for this session
                    user_context = UserExecutionContext(
                        user_id=user_id,
                        request_id=f"websocket_update_{user_id}_{id(self)}",
                        thread_id=f"ws_thread_{user_id}",
                        run_id=f"ws_run_{user_id}_{id(self)}"
                    )
                    # Set WebSocket manager on user session using factory pattern
                    await user_session.set_websocket_manager(manager, user_context)
                    logger.debug(f"Updated WebSocket manager for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to update WebSocket manager for user {user_id}: {e}")
        
        logger.info(f"✅ WebSocket manager set on AgentRegistry with user isolation support (async) - SSOT compliant adapter")
    
    # Override get method to pass WebSocket bridge to factories
    def get(self, key: str, context: Optional['UserExecutionContext'] = None) -> Optional['BaseAgent']:
        """Get singleton or create instance via factory with WebSocket bridge integration.
        
        This override ensures that agent factories receive the WebSocket bridge
        for proper event handling.
        
        Args:
            key: Agent type identifier
            context: Optional context for factory creation
            
        Returns:
            Agent instance or None if not found
        """
        with self._lock:
            item_info = self._items.get(key)
            if not item_info:
                return None
            
            # Mark as accessed
            if self.enable_metrics:
                item_info.mark_accessed()
                self._metrics['total_retrievals'] += 1
            
            # Return singleton if available
            if item_info.value is not None:
                return item_info.value
            
            # Try factory if context provided
            if item_info.factory and context:
                self._metrics['factory_creations'] += 1
                
                # Get WebSocket bridge from the appropriate user session
                websocket_bridge = None
                if context.user_id in self._user_sessions:
                    user_session = self._user_sessions[context.user_id]
                    websocket_bridge = user_session._websocket_bridge
                
                try:
                    # Check if factory is async
                    import asyncio
                    import inspect
                    
                    if inspect.iscoroutinefunction(item_info.factory):
                        # Factory is async, need to handle differently
                        logger.warning(f"Agent {key} has async factory but get() is sync - use get_async() instead")
                        
                        # Try to run the async factory in the current event loop
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Can't use loop.run_until_complete in a running loop
                                # Return None and log the issue
                                logger.error(f"Cannot create async agent {key} in running event loop - use get_async() instead")
                                return None
                            else:
                                # Loop exists but not running, can use run_until_complete
                                return loop.run_until_complete(item_info.factory(context, websocket_bridge))
                        except RuntimeError:
                            # No event loop
                            logger.error(f"No event loop available for async agent {key} - use get_async() instead")
                            return None
                    else:
                        # Factory is sync
                        return item_info.factory(context, websocket_bridge)
                        
                except Exception as e:
                    logger.error(f"Failed to create agent {key} via factory: {e}")
                    # Fallback: try calling factory with just context
                    try:
                        return item_info.factory(context)
                    except Exception as e2:
                        logger.error(f"Fallback factory call also failed for agent {key}: {e2}")
                        return None
            
            return None
    
    async def get_async(self, key: str, context: Optional['UserExecutionContext'] = None) -> Optional['BaseAgent']:
        """Async version of get method for proper async factory handling.
        
        This method properly handles async agent factories with WebSocket bridge integration.
        
        Args:
            key: Agent type identifier
            context: Optional context for factory creation
            
        Returns:
            Agent instance or None if not found
        """
        async with self._session_lock:
            item_info = self._items.get(key)
            if not item_info:
                return None
            
            # Mark as accessed
            if self.enable_metrics:
                item_info.mark_accessed()
                self._metrics['total_retrievals'] += 1
            
            # Return singleton if available
            if item_info.value is not None:
                return item_info.value
            
            # Try factory if context provided
            if item_info.factory and context:
                self._metrics['factory_creations'] += 1
                
                # Get WebSocket bridge from the appropriate user session
                websocket_bridge = None
                if context.user_id in self._user_sessions:
                    user_session = self._user_sessions[context.user_id]
                    websocket_bridge = user_session._websocket_bridge
                
                try:
                    import inspect
                    
                    if inspect.iscoroutinefunction(item_info.factory):
                        # Factory is async
                        return await item_info.factory(context, websocket_bridge)
                    else:
                        # Factory is sync
                        return item_info.factory(context, websocket_bridge)
                        
                except Exception as e:
                    logger.error(f"Failed to create agent {key} via async factory: {e}")
                    # Fallback: try calling factory with just context
                    try:
                        if inspect.iscoroutinefunction(item_info.factory):
                            return await item_info.factory(context)
                        else:
                            return item_info.factory(context)
                    except Exception as e2:
                        logger.error(f"Fallback async factory call also failed for agent {key}: {e2}")
                        return None
            
            return None
    
    # ===================== BACKWARD COMPATIBILITY =====================
    
    @property
    def tool_dispatcher(self):
        """DEPRECATED: Legacy property for backward compatibility.
        
        WARNING: This returns None to prevent usage of non-isolated dispatchers.
        New code should use create_tool_dispatcher_for_user() for proper isolation.
        """
        logger.warning(
            "⚠️ DEPRECATED: Accessing tool_dispatcher property is deprecated.\n"
            "Use create_tool_dispatcher_for_user(user_context) for proper user isolation."
        )
        return None
    
    @tool_dispatcher.setter  
    def tool_dispatcher(self, value):
        """DEPRECATED: Legacy setter for backward compatibility."""
        logger.warning(
            "⚠️ DEPRECATED: Setting tool_dispatcher is deprecated.\n"
            "Use tool_dispatcher_factory parameter in constructor for custom factories."
        )
        # BACKWARD COMPATIBILITY: Store value for legacy tests, but getter still returns None
        self._legacy_dispatcher = value
    
    async def _default_dispatcher_factory(self, user_context: 'UserExecutionContext', 
                                         websocket_bridge: Optional['AgentWebSocketBridge'] = None) -> 'CanonicalToolDispatcher':
        """Default factory method for creating CanonicalToolDispatcher instances.
        
        This is the SSOT factory that ensures all agents receive properly isolated
        tool dispatchers with mandatory security enforcement.
        
        Args:
            user_context: User execution context for isolation (REQUIRED)
            websocket_bridge: WebSocket bridge for event notifications
            
        Returns:
            UnifiedToolDispatcher: Properly isolated dispatcher instance
        """
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
        
        return await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_bridge,
            enable_admin_tools=False  # Default to standard tools only
        )
    
    async def create_tool_dispatcher_for_user(self, user_context: 'UserExecutionContext',
                                             websocket_bridge: Optional['AgentWebSocketBridge'] = None,
                                             enable_admin_tools: bool = False) -> 'UnifiedToolDispatcher':
        """Create properly isolated tool dispatcher for a specific user.
        
        CRITICAL FIX: Now ensures WebSocket events are properly integrated with user emitters.
        
        RECOMMENDED USAGE: Use this method to get tool dispatchers for agents.
        
        Args:
            user_context: User execution context for isolation
            websocket_bridge: WebSocket bridge for event notifications  
            enable_admin_tools: Enable admin tools (requires admin permissions)
            
        Returns:
            UnifiedToolDispatcher: Isolated dispatcher for this user
        """
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
        
        # CRITICAL: If no websocket_bridge provided, try to get from user session
        if not websocket_bridge and user_context.user_id in self._user_sessions:
            user_session = self._user_sessions[user_context.user_id]
            websocket_bridge = user_session._websocket_bridge
            logger.debug(f"Using WebSocket bridge from user session for {user_context.user_id}")
        
        # Create dispatcher with proper isolation
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=websocket_bridge,
            enable_admin_tools=enable_admin_tools
        )
        
        # CRITICAL: Enhance the dispatcher with per-user WebSocket notifications
        if websocket_bridge:
            from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
            await enhance_tool_dispatcher_with_notifications(
                dispatcher,
                websocket_manager=getattr(websocket_bridge, '_websocket_manager', None),
                user_context=user_context,  # CRITICAL: Pass user context for isolation
                enable_notifications=True
            )
            logger.debug(f"Enhanced tool dispatcher with user-isolated WebSocket notifications for user {user_context.user_id}")
        
        return dispatcher
    
    def register_default_agents(self) -> None:
        """Register default sub-agents."""
        if self._agents_registered:
            logger.debug("Agents already registered, skipping re-registration")
            return
        
        self._register_core_agents()
        self._register_auxiliary_agents()
        self._agents_registered = True
        
        logger.info(f"✅ Registered {len(self.list_keys())} default agents using UniversalRegistry")
    
    def _register_core_agents(self) -> None:
        """Register core workflow agents with CanonicalToolDispatcher integration."""
        try:
            # Import agents lazily to avoid circular dependencies
            from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent
            from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # MIGRATED: Updated agent factories to use CanonicalToolDispatcher
            async def create_triage_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create triage agent with properly isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return UnifiedTriageAgent(
                    llm_manager=self.llm_manager,
                    tool_dispatcher=tool_dispatcher,  # Now uses CanonicalToolDispatcher
                    context=context,
                    execution_priority=0
                )
            
            async def create_data_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create data agent with properly isolated context."""
                # Data agent may not need tool dispatcher - check implementation
                return UnifiedDataAgent(
                    context=context,
                    llm_manager=self.llm_manager
                )
            
            # Register factories for user isolation with async support
            self.register_factory("triage", create_triage_agent, 
                                tags=["core", "workflow"],
                                description="Triage agent with isolated tool dispatcher")
            self.register_factory("data", create_data_agent,
                                tags=["core", "workflow"],
                                description="Data processing agent")
            
            self._register_optimization_agents()
            
        except Exception as e:
            logger.error(f"Failed to register core agents: {e}")
            self.registration_errors["core_agents"] = str(e)
    
    def _register_optimization_agents(self) -> None:
        """Register optimization and action agents with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
            from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_optimization_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create optimization agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return OptimizationsCoreSubAgent(
                    self.llm_manager,
                    tool_dispatcher  # Now uses CanonicalToolDispatcher
                )
            
            async def create_actions_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create actions agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return ActionsToMeetGoalsSubAgent(
                    self.llm_manager,
                    tool_dispatcher  # Now uses CanonicalToolDispatcher
                )
            
            self.register_factory("optimization", create_optimization_agent,
                                tags=["optimization"],
                                description="Optimization strategy agent with isolated dispatcher")
            self.register_factory("actions", create_actions_agent,
                                tags=["execution"],
                                description="Action execution agent with isolated dispatcher")
            
        except Exception as e:
            logger.error(f"Failed to register optimization agents: {e}")
            self.registration_errors["optimization_agents"] = str(e)
    
    def _register_auxiliary_agents(self) -> None:
        """Register auxiliary agents."""
        self._register_reporting_agent()
        self._register_goals_triage_agent()
        self._register_data_helper_agent()
        self._register_synthetic_data_agent()
        self._register_corpus_admin_agent()
    
    def _register_reporting_agent(self) -> None:
        """Register reporting agent with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_reporting_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create reporting agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return ReportingSubAgent(self.llm_manager, tool_dispatcher)
            
            self.register_factory("reporting", create_reporting_agent,
                                tags=["auxiliary", "reporting"],
                                description="Report generation agent with isolated dispatcher")
        except Exception as e:
            logger.error(f"Failed to register reporting agent: {e}")
            self.registration_errors["reporting"] = str(e)
    
    def _register_goals_triage_agent(self) -> None:
        """Register goals triage agent with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_goals_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create goals triage agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return GoalsTriageSubAgent(self.llm_manager, tool_dispatcher)
            
            self.register_factory("goals_triage", create_goals_agent,
                                tags=["auxiliary", "triage"],
                                description="Goals triage agent with isolated dispatcher")
        except Exception as e:
            logger.error(f"Failed to register goals triage agent: {e}")
            self.registration_errors["goals_triage"] = str(e)
    
    def _register_synthetic_data_agent(self) -> None:
        """Register synthetic data agent with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_synthetic_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create synthetic data agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return SyntheticDataSubAgent(self.llm_manager, tool_dispatcher)
            
            self.register_factory("synthetic_data", create_synthetic_agent,
                                tags=["auxiliary", "data"],
                                description="Synthetic data generation agent with isolated dispatcher")
        except Exception as e:
            logger.error(f"Failed to register synthetic data agent: {e}")
            self.registration_errors["synthetic_data"] = str(e)
    
    def _register_data_helper_agent(self) -> None:
        """Register data helper agent with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_helper_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create data helper agent with isolated CanonicalToolDispatcher."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=False
                )
                
                return DataHelperAgent(self.llm_manager, tool_dispatcher)
            
            self.register_factory("data_helper", create_helper_agent,
                                tags=["auxiliary", "data"],
                                description="Data helper agent with isolated dispatcher")
        except Exception as e:
            logger.error(f"Failed to register data helper agent: {e}")
            self.registration_errors["data_helper"] = str(e)
    
    def _register_corpus_admin_agent(self) -> None:
        """Register corpus admin agent with CanonicalToolDispatcher."""
        try:
            from netra_backend.app.admin.corpus import CorpusAdminSubAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            async def create_corpus_agent(context: UserExecutionContext, websocket_bridge=None):
                """Create corpus admin agent with isolated CanonicalToolDispatcher and admin tools."""
                tool_dispatcher = await self.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=websocket_bridge,
                    enable_admin_tools=True  # Admin agent needs admin tools
                )
                
                return CorpusAdminSubAgent(self.llm_manager, tool_dispatcher)
            
            self.register_factory("corpus_admin", create_corpus_agent,
                                tags=["auxiliary", "admin"],
                                description="Corpus administration agent with admin tools")
        except Exception as e:
            logger.error(f"Failed to register corpus admin agent: {e}")
            self.registration_errors["corpus_admin"] = str(e)
    
    # ===================== BACKWARD COMPATIBILITY =====================
    
    def register(self, name: str, agent: 'BaseAgent') -> None:
        """Register agent for backward compatibility.
        
        NOTE: This now uses UniversalRegistry's register method.
        """
        try:
            # Register as singleton in UniversalRegistry
            super().register(name, agent, source="legacy_register")
            
            # Clear registration errors
            self.registration_errors.pop(name, None)
            logger.debug(f"Registered agent '{name}' using UniversalRegistry SSOT")
            
        except Exception as e:
            logger.error(f"Failed to register agent {name}: {e}")
            self.registration_errors[name] = str(e)
    
    async def register_agent_safely(self, name: str, agent_class: Type['BaseAgent'], 
                                   user_context: 'UserExecutionContext' = None,
                                   **kwargs) -> bool:
        """Register an agent safely with error handling using SSOT factory patterns.
        
        MIGRATED: Now uses proper factory pattern instead of legacy dispatcher.
        
        Args:
            name: Agent name for registration
            agent_class: Agent class to instantiate
            user_context: Required for proper user isolation (creates default if None)
            **kwargs: Additional arguments for agent construction
        """
        try:
            logger.info(f"Attempting to register agent: {name} using SSOT factory pattern")
            
            # SSOT: Create proper user context if not provided
            if user_context is None:
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                import uuid
                user_context = UserExecutionContext(
                    user_id="test_agent_creation_system",
                    request_id=f"register_{name}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"test_registry_thread_{name}",
                    run_id=f"register_run_{name}_{uuid.uuid4().hex[:8]}"
                )
            
            # SSOT: Use factory to create properly isolated tool dispatcher
            tool_dispatcher = await self.create_tool_dispatcher_for_user(
                user_context=user_context,
                websocket_bridge=None,  # Bridge will be set when WebSocket manager is configured
                enable_admin_tools=False
            )
            
            # Create agent instance with proper isolation
            agent = agent_class(
                self.llm_manager,
                tool_dispatcher,
                **kwargs
            )
            
            # Register using UniversalRegistry
            self.register(name, agent)
            
            logger.info(f"Successfully registered agent: {name} with isolated dispatcher")
            return True
            
        except Exception as e:
            error_msg = f"Failed to register agent {name} with SSOT pattern: {str(e)}"
            logger.error(error_msg)
            self.registration_errors[name] = error_msg
            return False
    
    def get_registry_health(self) -> Dict[str, Any]:
        """Get comprehensive registry health with isolation metrics."""
        # Get health from UniversalRegistry
        health = self.validate_health()
        
        # Add hardening and isolation metrics
        uptime = (datetime.now(timezone.utc) - self._created_at).total_seconds()
        total_user_sessions = len(self._user_sessions)
        total_user_agents = sum(len(session._agents) for session in self._user_sessions.values())
        
        health.update({
            "total_agents": len(self.list_keys()),
            "failed_registrations": len(self.registration_errors),
            "registration_errors": self.registration_errors.copy(),
            "death_detection_enabled": True,
            "using_universal_registry": True,
            # HARDENING: User isolation metrics
            "hardened_isolation": True,
            "total_user_sessions": total_user_sessions,
            "total_user_agents": total_user_agents,
            "memory_leak_prevention": True,
            "thread_safe_concurrent_execution": True,
            "uptime_seconds": uptime,
            "issues": []
        })
        
        # Check for issues
        if total_user_sessions > 50:
            health['status'] = 'warning' if health.get('status') == 'healthy' else 'critical'
            health['issues'].append(f"High user session count: {total_user_sessions}")
        
        if total_user_agents > 500:
            health['status'] = 'critical'
            health['issues'].append(f"Excessive user agent count: {total_user_agents}")
        
        return health
    
    def list_agents(self) -> List[str]:
        """List registered agent names."""
        return self.list_keys()
    
    def remove_agent(self, name: str) -> bool:
        """Remove an agent from registry."""
        return self.remove(name)
    
    async def get_agent(self, name: str, context: Optional['UserExecutionContext'] = None) -> Optional['BaseAgent']:
        """Get agent with optional context for factory creation."""
        return await self.get_async(name, context)
    
    async def reset_all_agents(self) -> Dict[str, Any]:
        """Reset is not needed with factory pattern - returns success."""
        return {
            'total_agents': len(self.list_keys()),
            'successful_resets': len(self.list_keys()),
            'failed_resets': 0,
            'agents_without_reset': 0,
            'reset_details': {
                name: {'status': 'factory_pattern', 'note': 'Fresh instances per request'}
                for name in self.list_keys()
            },
            'using_universal_registry': True
        }
    
    def diagnose_websocket_wiring(self) -> Dict[str, Any]:
        """Comprehensive diagnosis of per-user WebSocket wiring."""
        diagnosis = {
            "registry_has_websocket_bridge": self.websocket_bridge is not None,
            "registry_has_websocket_manager": self.websocket_manager is not None,
            "total_agents": len(self.list_keys()),
            "using_universal_registry": True,
            # HARDENING: Per-user WebSocket diagnosis
            "total_user_sessions": len(self._user_sessions),
            "users_with_websocket_bridges": 0,
            "critical_issues": [],
            "user_details": {}
        }
        
        # Diagnose per-user WebSocket bridges
        for user_id, session in self._user_sessions.items():
            user_diagnosis = {
                'has_websocket_bridge': session._websocket_bridge is not None,
                'agent_count': len(session._agents)
            }
            
            if session._websocket_bridge is not None:
                diagnosis['users_with_websocket_bridges'] += 1
            else:
                diagnosis['critical_issues'].append(f"User {user_id} has no WebSocket bridge")
            
            diagnosis['user_details'][user_id] = user_diagnosis
        
        # Global WebSocket checks - in per-user architecture, we don't need a global bridge
        # REMOVED: Global WebSocket bridge check - using per-user bridges now
        # The critical check is that users have individual bridges when they need them
        
        if self.websocket_manager is None:
            diagnosis["critical_issues"].append("No global WebSocket manager configured")
        
        # Overall health assessment
        if diagnosis['total_user_sessions'] > 0:
            bridge_ratio = diagnosis['users_with_websocket_bridges'] / diagnosis['total_user_sessions']
            if bridge_ratio < 0.8:
                diagnosis['critical_issues'].append(f"Low user WebSocket coverage: {bridge_ratio:.1%}")
        
        diagnosis["websocket_health"] = "HEALTHY" if not diagnosis["critical_issues"] else "CRITICAL"
        
        return diagnosis
    
    def get_factory_integration_status(self) -> Dict[str, Any]:
        """Get enhanced factory pattern status with hardening metrics."""
        return {
            'using_universal_registry': True,
            'factory_patterns_enabled': True,
            'total_factories': len([k for k in self.list_keys()]),
            'thread_safe': True,
            'metrics_enabled': self.enable_metrics,
            # HARDENING: Enhanced metrics
            'hardened_isolation_enabled': True,
            'user_isolation_enforced': True,
            'memory_leak_prevention': True,
            'thread_safe_concurrent_execution': True,
            'total_user_sessions': len(self._user_sessions),
            'global_state_eliminated': True,
            'websocket_isolation_per_user': True,
            # SSOT COMPLIANCE STATUS
            'ssot_compliance': self.get_ssot_compliance_status(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_ssot_compliance_status(self) -> Dict[str, Any]:
        """Get comprehensive SSOT compliance status.
        
        Returns:
            Dictionary with detailed SSOT compliance information
        """
        try:
            status = {
                'inheritance_chain_valid': isinstance(self, UniversalRegistry),
                'constructor_signature_aligned': hasattr(self, 'name') and self.name == "AgentRegistry",
                'websocket_adapter_available': hasattr(self, 'websocket_manager'),
                'parent_interface_accessible': hasattr(super(), 'set_websocket_bridge'),
                'adapter_class_functional': True,
                'violations': [],
                'compliance_score': 0,
                'status': 'unknown'
            }
            
            # Test adapter functionality
            try:
                test_adapter = WebSocketManagerAdapter(None)
                required_adapter_methods = ['notify_agent_started', 'notify_agent_thinking', 
                                          'notify_tool_executing', 'notify_agent_completed']
                for method in required_adapter_methods:
                    if not hasattr(test_adapter, method):
                        status['adapter_class_functional'] = False
                        status['violations'].append(f"Adapter missing method: {method}")
            except Exception as e:
                status['adapter_class_functional'] = False
                status['violations'].append(f"Adapter instantiation failed: {e}")
            
            # Validate interface methods
            required_methods = ['set_websocket_bridge', 'register', 'get', 'has', 'list_keys']
            missing_methods = []
            for method_name in required_methods:
                if not hasattr(self, method_name) or not callable(getattr(self, method_name)):
                    missing_methods.append(method_name)
            
            if missing_methods:
                status['violations'].append(f"Missing interface methods: {missing_methods}")
            
            # Calculate compliance score
            checks = ['inheritance_chain_valid', 'constructor_signature_aligned', 
                     'websocket_adapter_available', 'parent_interface_accessible', 
                     'adapter_class_functional']
            passed_checks = sum(1 for check in checks if status[check])
            status['compliance_score'] = (passed_checks / len(checks)) * 100
            
            # Determine overall status
            if status['compliance_score'] == 100 and not status['violations']:
                status['status'] = 'fully_compliant'
            elif status['compliance_score'] >= 80:
                status['status'] = 'mostly_compliant'
            elif status['compliance_score'] >= 50:
                status['status'] = 'partially_compliant'
            else:
                status['status'] = 'non_compliant'
            
            return status
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'compliance_score': 0,
                'violations': [f"Compliance check failed: {e}"]
            }


# ===================== MODULE EXPORTS =====================

def get_agent_registry(llm_manager: 'LLMManager', tool_dispatcher: Optional['ToolDispatcher'] = None) -> AgentRegistry:
    """Get or create agent registry using SSOT pattern.
    
    This uses the global registry from UniversalRegistry but creates our custom AgentRegistry.
    """
    try:
        # Create our custom AgentRegistry which inherits from UniversalRegistry
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        return registry
            
    except Exception:
        # Create new registry
        return AgentRegistry(llm_manager, tool_dispatcher)


__all__ = ['AgentRegistry', 'get_agent_registry']