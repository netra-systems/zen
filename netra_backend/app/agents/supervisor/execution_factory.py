"""
ExecutionEngineFactory - Factory Pattern for Per-User Isolated Execution Engines

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Enables 10+ concurrent users with zero shared state
- Strategic Impact: Critical - Replaces dangerous singleton patterns with per-user isolation

This module implements the ExecutionEngineFactory pattern that provides complete user isolation
by creating per-request execution engines with their own state, eliminating the shared state
issues of the legacy ExecutionEngine singleton.

Key Features:
1. Complete User Isolation - Each user gets their own execution context and engine
2. Thread Safety - No shared dictionaries or race conditions  
3. Resource Management - Proper cleanup and lifecycle management
4. Scalability - Support for 10+ concurrent users with bounded resources
5. Backward Compatibility - Seamless migration from singleton pattern
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ExecutionStatus

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
    from netra_backend.app.services.websocket_bridge_factory import UserWebSocketEmitter
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    # Legacy import removed - use SSOT from resilience
    # from netra_backend.app.agents.supervisor.fallback_manager import FallbackManager
    from netra_backend.app.core.resilience.fallback import FallbackManager
    from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
    from netra_backend.app.core.types import AgentExecutionResult, AgentExecutionContext
    # DeepAgentState removed - using UserExecutionContext pattern

logger = central_logger.get_logger(__name__)

# Import UserExecutionEngine for SSOT remediation (Phase 1)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# SSOT COMPLIANCE: ExecutionStatus imported from core_enums
# Mapping for execution_factory specific states:
# - ACTIVE -> EXECUTING (agent is actively working)  
# - CLEANED -> COMPLETED (execution finished and resources cleaned up)


# SSOT CONSOLIDATION: Import UserExecutionContext from authoritative services implementation
# This eliminates duplicate implementation and ensures consistent security validation
from netra_backend.app.services.user_execution_context import UserExecutionContext

@dataclass
class ExecutionFactoryContext:
    """
    Factory-specific execution state wrapper for UserExecutionContext.
    
    This dataclass provides execution factory-specific functionality while
    delegating core context management to the SSOT UserExecutionContext.
    
    Business Value: Prevents user context leakage and enables reliable multi-user execution
    """
    context: UserExecutionContext
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # User-specific execution state - ISOLATED per request
    active_runs: Dict[str, 'AgentExecutionContext'] = field(default_factory=dict)
    run_history: List['AgentExecutionResult'] = field(default_factory=list)
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Resource management
    cleanup_callbacks: List[Callable] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.INITIALIZING
    _is_cleaned: bool = False
    
    def __post_init__(self):
        """Initialize metrics tracking after object creation."""
        self.execution_metrics.update({
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_execution_time_ms': 0.0,
            'avg_execution_time_ms': 0.0,
            'context_created_at': self.created_at.isoformat(),
            'last_activity_at': self.created_at.isoformat()
        })
        self.status = ExecutionStatus.EXECUTING  # SSOT: ACTIVE -> EXECUTING
        logger.debug(f"ExecutionFactoryContext created: user_id={self.context.user_id}, request_id={self.context.request_id}")
    
    @property
    def user_id(self) -> str:
        """Delegate to SSOT UserExecutionContext."""
        return self.context.user_id
    
    @property
    def request_id(self) -> str:
        """Delegate to SSOT UserExecutionContext."""
        return self.context.request_id
        
    @property
    def thread_id(self) -> str:
        """Delegate to SSOT UserExecutionContext."""
        return self.context.thread_id
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.execution_metrics['last_activity_at'] = datetime.now(timezone.utc).isoformat()
    
    def record_run_start(self, run_id: str, agent_name: str) -> None:
        """Record start of a new agent run."""
        self.update_activity()
        self.execution_metrics['total_runs'] += 1
        logger.debug(f"Run started: {run_id} for user {self.user_id}")
    
    def record_run_success(self, run_id: str, execution_time_ms: float) -> None:
        """Record successful completion of an agent run."""
        self.update_activity()
        self.execution_metrics['successful_runs'] += 1
        self.execution_metrics['total_execution_time_ms'] += execution_time_ms
        
        # Update average execution time
        total_runs = self.execution_metrics['successful_runs']
        self.execution_metrics['avg_execution_time_ms'] = (
            self.execution_metrics['total_execution_time_ms'] / total_runs
        )
        logger.debug(f"Run completed successfully: {run_id} for user {self.user_id} in {execution_time_ms:.1f}ms")
    
    def record_run_failure(self, run_id: str, error: Exception) -> None:
        """Record failure of an agent run."""
        self.update_activity()
        self.execution_metrics['failed_runs'] += 1
        logger.warning(f"Run failed: {run_id} for user {self.user_id}: {error}")
    
    def create_child_context(self, child_id: str) -> 'UserExecutionContext':
        """Create a child execution context for agent isolation.
        
        Args:
            child_id: Identifier for the child context (e.g., "agent_triage")
            
        Returns:
            UserExecutionContext: New isolated context for the agent
        """
        child_request_id = f"{self.request_id}_{child_id}"
        child_thread_id = f"{self.thread_id}_{child_id}"
        
        child_context = UserExecutionContext(
            user_id=self.user_id,
            request_id=child_request_id,
            thread_id=child_thread_id,
            session_id=self.session_id
        )
        
        # Inherit parent metrics but start fresh
        child_context.execution_metrics = self.execution_metrics.copy()
        child_context.execution_metrics['parent_request_id'] = self.request_id
        child_context.execution_metrics['child_id'] = child_id
        
        logger.debug(f"Created child context {child_request_id} for user {self.user_id}")
        return child_context
    
    async def cleanup(self) -> None:
        """Clean up user-specific resources."""
        if self._is_cleaned:
            logger.debug(f"UserExecutionContext already cleaned for user {self.user_id}")
            return
            
        logger.info(f"🧹 Cleaning up UserExecutionContext for user {self.user_id}")
        self.status = ExecutionStatus.COMPLETED  # SSOT: CLEANED -> COMPLETED
        
        try:
            # Run cleanup callbacks in reverse order (LIFO)
            for callback in reversed(self.cleanup_callbacks):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Cleanup callback failed for user {self.user_id}: {e}")
                    
            # Clear all execution state
            self.active_runs.clear()
            
            # Trim run history to prevent memory leaks
            if len(self.run_history) > 10:
                self.run_history = self.run_history[-5:]  # Keep last 5
                
            # Clear cleanup callbacks
            self.cleanup_callbacks.clear()
            
            self._is_cleaned = True
            logger.info(f"✅ UserExecutionContext cleanup completed for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"❌ UserExecutionContext cleanup failed for user {self.user_id}: {e}")
            self._is_cleaned = True  # Mark as cleaned even if there were errors
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of context status for monitoring."""
        return {
            'user_id': self.user_id,
            'request_id': self.request_id,
            'thread_id': self.thread_id,
            'status': self.status.value,
            'active_runs_count': len(self.active_runs),
            'run_history_count': len(self.run_history),
            'is_cleaned': self._is_cleaned,
            'created_at': self.created_at.isoformat(),
            'metrics': self.execution_metrics.copy()
        }


@dataclass 
class ExecutionFactoryConfig:
    """Configuration for ExecutionEngineFactory."""
    max_concurrent_per_user: int = 5
    execution_timeout_seconds: float = 30.0
    cleanup_interval_seconds: int = 300  # 5 minutes
    max_history_per_user: int = 100
    enable_user_semaphores: bool = True
    enable_execution_tracking: bool = True
    
    # Resource limits
    max_active_users: int = 100
    memory_threshold_mb: int = 1024
    
    @classmethod
    def from_env(cls) -> 'ExecutionFactoryConfig':
        """Create config from environment variables."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        return cls(
            max_concurrent_per_user=int(env.get('EXECUTION_MAX_CONCURRENT_PER_USER', '5')),
            execution_timeout_seconds=float(env.get('EXECUTION_TIMEOUT_SECONDS', '30.0')),
            cleanup_interval_seconds=int(env.get('EXECUTION_CLEANUP_INTERVAL', '300')),
            max_history_per_user=int(env.get('EXECUTION_MAX_HISTORY_PER_USER', '100')),
            enable_user_semaphores=env.get('EXECUTION_ENABLE_USER_SEMAPHORES', 'true').lower() == 'true',
            enable_execution_tracking=env.get('EXECUTION_ENABLE_TRACKING', 'true').lower() == 'true',
        )


class ExecutionEngineFactory:
    """
    Factory for creating per-request ExecutionEngine instances with complete user isolation.
    
    This factory creates isolated execution engines for each user request, eliminating
    the shared state issues of the legacy ExecutionEngine singleton.
    
    Key Features:
    - Complete user isolation
    - Per-user resource limits
    - Automatic cleanup
    - Thread safety
    - Performance monitoring
    """
    
    def __init__(self, config: Optional[ExecutionFactoryConfig] = None):
        """Initialize the execution engine factory."""
        self.config = config or ExecutionFactoryConfig.from_env()
        
        # Infrastructure components (shared, immutable)
        self._agent_registry: Optional['AgentRegistry'] = None
        self._websocket_bridge_factory: Optional['WebSocketBridgeFactory'] = None
        self._db_connection_pool: Optional[Any] = None
        
        # Per-user semaphores (infrastructure manages this)
        self._user_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._semaphore_lock = asyncio.Lock()
        
        # Factory metrics
        self._factory_metrics = {
            'engines_created': 0,
            'engines_active': 0,
            'engines_cleaned': 0,
            'total_users': 0,
            'concurrent_peak': 0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Active contexts tracking
        self._active_contexts: Dict[str, UserExecutionContext] = {}
        self._contexts_lock = asyncio.Lock()
        
        logger.info("ExecutionEngineFactory initialized")
        
    def configure(self, 
                 agent_registry: Optional['AgentRegistry'],
                 websocket_bridge_factory: 'WebSocketBridgeFactory',
                 db_connection_pool: Any) -> None:
        """Configure factory with infrastructure components.
        
        Note: agent_registry can be None when using UserExecutionContext pattern
        where registry is created per-request.
        """
        self._agent_registry = agent_registry
        self._websocket_bridge_factory = websocket_bridge_factory
        self._db_connection_pool = db_connection_pool
        
        if agent_registry:
            logger.info("✅ ExecutionEngineFactory configured with agent registry")
        else:
            logger.info("✅ ExecutionEngineFactory configured (per-request registry pattern)")
        
    async def create_execution_engine(self, 
                                    user_context: UserExecutionContext) -> 'IsolatedExecutionEngine':
        """
        Create a per-request ExecutionEngine instance with complete user isolation.
        
        Args:
            user_context: User execution context containing user_id, request_id, etc.
            
        Returns:
            IsolatedExecutionEngine: New execution engine for this specific user/request
            
        Raises:
            RuntimeError: If factory not configured or resource limits exceeded
        """
        # Note: agent_registry can be None when using UserExecutionContext pattern
        # where registry is created per-request - this is valid
            
        start_time = time.time()
        
        try:
            # Check resource limits
            await self._enforce_resource_limits(user_context.user_id)
            
            # Get or create user-specific semaphore
            user_semaphore = await self._get_user_semaphore(user_context.user_id)
            
            # Create user-specific WebSocket event emitter
            websocket_emitter = None
            if self._websocket_bridge_factory:
                try:
                    websocket_emitter = await self._websocket_bridge_factory.create_user_emitter(
                        user_context.user_id, 
                        user_context.thread_id,
                        f"conn_{user_context.user_id}_{int(time.time() * 1000)}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create WebSocket emitter via factory: {e}")
            
            # Fallback: Create isolated WebSocket emitter directly
            if not websocket_emitter:
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as IsolatedWebSocketEventEmitter
                websocket_emitter = IsolatedWebSocketEventEmitter.create_for_user(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.request_id,
                    websocket_manager=None  # Will be set when available
                )
                logger.info(f"Created fallback WebSocket emitter for user {user_context.user_id}")
            
            # SSOT REMEDIATION PHASE 1: Delegate to UserExecutionEngine
            # This maintains backward compatibility while routing through the preferred engine
            try:
                # Try to create UserExecutionEngine (preferred SSOT approach)
                from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
                
                agent_factory = get_agent_instance_factory()
                
                # Create UserExecutionEngine instead of IsolatedExecutionEngine
                user_engine = UserExecutionEngine(
                    context=user_context,
                    agent_factory=agent_factory,
                    websocket_emitter=websocket_emitter
                )
                
                # Create a delegation wrapper that maintains IsolatedExecutionEngine interface
                engine = UserExecutionEngineWrapper(
                    user_engine=user_engine,
                    user_context=user_context,
                    agent_registry=self._agent_registry,
                    websocket_emitter=websocket_emitter,
                    execution_semaphore=user_semaphore,
                    execution_timeout=self.config.execution_timeout_seconds,
                    factory=self
                )
                
                logger.info(f"✅ Created UserExecutionEngine (via wrapper) for user {user_context.user_id}")
                
            except Exception as e:
                logger.warning(f"Failed to create UserExecutionEngine: {e}. Falling back to IsolatedExecutionEngine")
                # Fallback to original IsolatedExecutionEngine for safety
                engine = IsolatedExecutionEngine(
                    user_context=user_context,
                    agent_registry=self._agent_registry,  # Shared, immutable
                    websocket_emitter=websocket_emitter,  # Per-user
                    execution_semaphore=user_semaphore,   # Per-user
                    execution_timeout=self.config.execution_timeout_seconds,
                    factory=self  # Reference back for cleanup
                )
            
            # Register cleanup callbacks
            user_context.cleanup_callbacks.append(engine.cleanup)
            user_context.cleanup_callbacks.append(websocket_emitter.cleanup)
            
            # Track active context
            async with self._contexts_lock:
                self._active_contexts[user_context.request_id] = user_context
                self._factory_metrics['engines_created'] += 1
                self._factory_metrics['engines_active'] += 1
                
                # Track unique users
                if user_context.user_id not in [ctx.user_id for ctx in self._active_contexts.values() if ctx.request_id != user_context.request_id]:
                    self._factory_metrics['total_users'] += 1
                
                # Track peak concurrency
                current_active = len(self._active_contexts)
                if current_active > self._factory_metrics['concurrent_peak']:
                    self._factory_metrics['concurrent_peak'] = current_active
            
            creation_time_ms = (time.time() - start_time) * 1000
            logger.info(f"✅ IsolatedExecutionEngine created for user {user_context.user_id} in {creation_time_ms:.1f}ms")
            
            return engine
            
        except Exception as e:
            logger.error(f"❌ Failed to create execution engine for user {user_context.user_id}: {e}")
            raise RuntimeError(f"Execution engine creation failed: {e}")
            
    async def _enforce_resource_limits(self, user_id: str) -> None:
        """Enforce resource limits to prevent resource exhaustion."""
        async with self._contexts_lock:
            active_count = len(self._active_contexts)
            
            if active_count >= self.config.max_active_users:
                raise RuntimeError(f"Maximum active users ({self.config.max_active_users}) exceeded")
                
        # Check memory usage (simplified check)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.config.memory_threshold_mb:
            logger.warning(f"Memory usage ({memory_mb:.1f}MB) exceeds threshold ({self.config.memory_threshold_mb}MB)")
            
    async def _get_user_semaphore(self, user_id: str) -> asyncio.Semaphore:
        """Get or create per-user execution semaphore."""
        if not self.config.enable_user_semaphores:
            # Return a high-limit semaphore if disabled
            return asyncio.Semaphore(100)
            
        async with self._semaphore_lock:
            if user_id not in self._user_semaphores:
                self._user_semaphores[user_id] = asyncio.Semaphore(self.config.max_concurrent_per_user)
                logger.debug(f"Created semaphore for user {user_id} (limit: {self.config.max_concurrent_per_user})")
            return self._user_semaphores[user_id]
            
    async def cleanup_context(self, request_id: str) -> None:
        """Clean up a specific user context."""
        async with self._contexts_lock:
            if request_id in self._active_contexts:
                context = self._active_contexts.pop(request_id)
                await context.cleanup()
                self._factory_metrics['engines_active'] -= 1
                self._factory_metrics['engines_cleaned'] += 1
                logger.debug(f"Context cleaned for request {request_id}")
                
    def get_factory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive factory metrics."""
        return {
            **self._factory_metrics,
            'active_contexts': len(self._active_contexts),
            'user_semaphores': len(self._user_semaphores),
            'config': {
                'max_concurrent_per_user': self.config.max_concurrent_per_user,
                'execution_timeout_seconds': self.config.execution_timeout_seconds,
                'max_active_users': self.config.max_active_users
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


class UserExecutionEngineWrapper:
    """
    Wrapper that delegates to UserExecutionEngine while maintaining IsolatedExecutionEngine interface.
    
    This is part of SSOT remediation Phase 1 - providing backward compatibility
    while routing all operations through UserExecutionEngine.
    
    Business Value: Enables gradual migration to SSOT without breaking existing code
    """
    
    def __init__(self, 
                 user_engine: UserExecutionEngine,
                 user_context: UserExecutionContext,
                 agent_registry: 'AgentRegistry',
                 websocket_emitter: 'UserWebSocketEmitter',
                 execution_semaphore: asyncio.Semaphore,
                 execution_timeout: float,
                 factory: ExecutionEngineFactory):
        """Initialize wrapper with UserExecutionEngine delegation."""
        self.user_engine = user_engine  # Primary engine
        self.user_context = user_context
        self.agent_registry = agent_registry
        self.websocket_emitter = websocket_emitter
        self.execution_semaphore = execution_semaphore
        self.execution_timeout = execution_timeout
        self.factory = factory
        
        logger.debug(f"UserExecutionEngineWrapper initialized for user {user_context.user_id} - delegating to UserExecutionEngine")
    
    # Delegate all methods to UserExecutionEngine
    def __getattr__(self, name):
        """Delegate unknown methods to the wrapped UserExecutionEngine."""
        return getattr(self.user_engine, name)
    
    async def cleanup(self):
        """Cleanup delegation - call UserExecutionEngine cleanup."""
        try:
            await self.user_engine.cleanup()
        except Exception as e:
            logger.error(f"Error during UserExecutionEngine cleanup: {e}")


class IsolatedExecutionEngine:
    """
    Per-request ExecutionEngine with complete user isolation.
    
    Each instance handles execution for a single user request with its own state,
    eliminating the shared state issues of the legacy ExecutionEngine.
    
    Business Value: Enables reliable concurrent execution for 10+ users
    """
    
    def __init__(self, 
                 user_context: UserExecutionContext,
                 agent_registry: 'AgentRegistry',
                 websocket_emitter: 'UserWebSocketEmitter',
                 execution_semaphore: asyncio.Semaphore,
                 execution_timeout: float,
                 factory: ExecutionEngineFactory):
        
        # DEPRECATION WARNING: This execution engine is being phased out in favor of UserExecutionEngine
        import warnings
        warnings.warn(
            "This execution engine is deprecated. Use UserExecutionEngine via ExecutionEngineFactory.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.user_context = user_context
        self.agent_registry = agent_registry  # Shared, immutable
        
        # CRITICAL: Validate WebSocket emitter
        if websocket_emitter is None:
            logger.warning(f"WebSocket emitter is None for user {user_context.user_id} - creating fallback")
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as IsolatedWebSocketEventEmitter
            websocket_emitter = IsolatedWebSocketEventEmitter.create_for_user(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.request_id,
                websocket_manager=None  # Will be set when available
            )
        
        self.websocket_emitter = websocket_emitter  # Per-user
        self.execution_semaphore = execution_semaphore  # Per-user
        self.execution_timeout = execution_timeout
        self.factory = factory  # Reference for cleanup
        
        # Initialize per-request components
        self._init_user_components()
        
        logger.debug(f"IsolatedExecutionEngine initialized for user {user_context.user_id} with validated emitter")
        
    def _init_user_components(self) -> None:
        """Initialize user-specific execution components."""
        # Components will be lazily initialized to avoid circular imports
        self._periodic_update_manager: Optional['PeriodicUpdateManager'] = None
        self._agent_core: Optional['AgentExecutionCore'] = None
        self._fallback_manager: Optional['FallbackManager'] = None
        
        logger.debug(f"User components initialized for {self.user_context.user_id}")
        
    async def _get_or_create_periodic_update_manager(self) -> 'PeriodicUpdateManager':
        """Get or create periodic update manager."""
        if self._periodic_update_manager is None:
            from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
            self._periodic_update_manager = PeriodicUpdateManager(
                self.websocket_emitter, 
                self.user_context
            )
        return self._periodic_update_manager
        
    async def _get_or_create_agent_core(self) -> 'AgentExecutionCore':
        """Get or create agent execution core."""
        if self._agent_core is None:
            from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
            self._agent_core = AgentExecutionCore(
                self.agent_registry,  # Shared
                self.websocket_emitter,  # Per-user
                self.user_context  # Per-user
            )
        return self._agent_core
        
    async def _get_or_create_fallback_manager(self) -> 'FallbackManager':
        """Get or create fallback manager."""
        if self._fallback_manager is None:
            # Legacy import removed - use SSOT from resilience
            # from netra_backend.app.agents.supervisor.fallback_manager import FallbackManager
            from netra_backend.app.core.resilience.fallback import FallbackManager
            self._fallback_manager = FallbackManager(
                self.websocket_emitter,
                self.user_context
            )
        return self._fallback_manager
        
    async def execute_agent_pipeline(self, 
                                   agent_name: str, 
                                   user_context: Optional['UserExecutionContext'] = None) -> 'AgentExecutionResult':
        """
        Execute agent pipeline with complete user isolation.
        
        Args:
            agent_name: Name of the agent to execute
            state: Agent state containing user message, context, etc.
            
        Returns:
            AgentExecutionResult: Results of agent execution
            
        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
            RuntimeError: If execution fails
        """
        run_id = f"{self.user_context.user_id}_{agent_name}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Import here to avoid circular imports
        from netra_backend.app.core.types import AgentExecutionContext, AgentExecutionResult
        
        # Use provided user_context or instance context
        effective_user_context = user_context or self.user_context
        
        # Create execution context - stored in USER-SPECIFIC active_runs
        execution_context = AgentExecutionContext(
            run_id=run_id,
            agent_name=agent_name,
            user_context=effective_user_context,
            user_id=effective_user_context.user_id,
            thread_id=effective_user_context.thread_id,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Store in USER-SPECIFIC dictionary
            self.user_context.active_runs[run_id] = execution_context
            self.user_context.record_run_start(run_id, agent_name)
            
            # Acquire USER-SPECIFIC semaphore
            async with self.execution_semaphore:
                
                # User-specific WebSocket notification
                await self.websocket_emitter.notify_agent_started(
                    agent_name=agent_name,
                    run_id=run_id
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._execute_with_monitoring(execution_context, effective_user_context),
                    timeout=self.execution_timeout
                )
                
                # Store in USER-SPECIFIC history
                self.user_context.run_history.append(result)
                
                # Trim history to prevent memory leaks
                if len(self.user_context.run_history) > self.factory.config.max_history_per_user:
                    keep_count = self.factory.config.max_history_per_user // 2
                    self.user_context.run_history = self.user_context.run_history[-keep_count:]
                
                execution_time_ms = (time.time() - start_time) * 1000
                self.user_context.record_run_success(run_id, execution_time_ms)
                
                logger.info(f"✅ Agent {agent_name} completed for user {self.user_context.user_id} in {execution_time_ms:.1f}ms")
                
                return result
                
        except asyncio.TimeoutError:
            error_msg = f"Agent execution timeout for user {self.user_context.user_id}: {agent_name}"
            logger.error(error_msg)
            
            await self.websocket_emitter.notify_agent_error(
                agent_name=agent_name,
                run_id=run_id,
                error="Execution timeout - please try again"
            )
            
            self.user_context.record_run_failure(run_id, asyncio.TimeoutError(error_msg))
            raise
            
        except Exception as e:
            error_msg = f"Agent execution failed for user {self.user_context.user_id}: {e}"
            logger.error(error_msg)
            
            await self.websocket_emitter.notify_agent_error(
                agent_name=agent_name,
                run_id=run_id,
                error=str(e)
            )
            
            self.user_context.record_run_failure(run_id, e)
            raise RuntimeError(error_msg) from e
            
        finally:
            # Clean up USER-SPECIFIC active run
            self.user_context.active_runs.pop(run_id, None)
            
    async def _execute_with_monitoring(self, context: 'AgentExecutionContext', user_context: 'UserExecutionContext') -> 'AgentExecutionResult':
        """Execute agent with user-specific monitoring."""
        from netra_backend.app.core.types import AgentExecutionResult
        
        try:
            # Get components (lazily initialized)
            agent_core = await self._get_or_create_agent_core()
            
            # Execute through user-specific core
            result = await agent_core.execute_agent(context, user_context)
            
            # Send completion notification
            await self.websocket_emitter.notify_agent_completed(
                agent_name=context.agent_name,
                run_id=context.run_id,
                result={"status": "completed", "message": "Agent execution completed successfully"}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution monitoring failed for user {self.user_context.user_id}: {e}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up execution engine resources."""
        try:
            # Clean up any remaining active runs
            for run_id, context in list(self.user_context.active_runs.items()):
                logger.warning(f"Force cleaning active run {run_id} for user {self.user_context.user_id}")
                
            self.user_context.active_runs.clear()
            
            # Clean up components
            if self._periodic_update_manager:
                if hasattr(self._periodic_update_manager, 'cleanup'):
                    await self._periodic_update_manager.cleanup()
                    
            if self._agent_core:
                if hasattr(self._agent_core, 'cleanup'):
                    await self._agent_core.cleanup()
                    
            if self._fallback_manager:
                if hasattr(self._fallback_manager, 'cleanup'):
                    await self._fallback_manager.cleanup()
                    
            # Notify factory of cleanup
            await self.factory.cleanup_context(self.user_context.request_id)
            
            logger.info(f"✅ IsolatedExecutionEngine cleanup completed for user {self.user_context.user_id}")
            
        except Exception as e:
            logger.error(f"❌ IsolatedExecutionEngine cleanup failed for user {self.user_context.user_id}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get execution engine status."""
        return {
            'user_id': self.user_context.user_id,
            'request_id': self.user_context.request_id,
            'thread_id': self.user_context.thread_id,
            'status': self.user_context.status.value,
            'active_runs': list(self.user_context.active_runs.keys()),
            'run_history_count': len(self.user_context.run_history),
            'execution_metrics': self.user_context.execution_metrics.copy(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Factory instance management
_execution_engine_factory: Optional['ExecutionEngineFactory'] = None


def get_execution_engine_factory() -> ExecutionEngineFactory:
    """Get or create the singleton ExecutionEngineFactory instance.
    
    Returns:
        ExecutionEngineFactory: The singleton factory instance
    """
    global _execution_engine_factory
    if _execution_engine_factory is None:
        _execution_engine_factory = ExecutionEngineFactory()
    return _execution_engine_factory
