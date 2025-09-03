from shared.isolated_environment import get_env
"""Base Agent Core Module

Main base agent class that composes functionality from focused modular components.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Callable, Awaitable
import time

# Remove mixin imports since we're using single inheritance now
# from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
# from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
# from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
# from netra_backend.app.agents.agent_state import AgentStateMixin
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.agents.interfaces import BaseAgentProtocol
# DEPRECATED: DeepAgentState import for migration compatibility only - will be removed in v3.0.0
from netra_backend.app.schemas.agent_models import DeepAgentState
import warnings
from netra_backend.app.core.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import generate_llm_correlation_id
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Import timing components
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector

# Import reliability and execution infrastructure using UnifiedRetryHandler as SSOT foundation
from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    RetryConfig,
    AGENT_RETRY_POLICY
)
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_error_handler import agent_error_handler
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.config import agent_config
from netra_backend.app.agents.utils import extract_thread_id

# Import domain-specific circuit breaker and reliability manager
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    AgentCircuitBreaker,
    AgentCircuitBreakerConfig
)
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.schemas.shared_types import RetryConfig as SharedRetryConfig

# Import telemetry components for distributed tracing
from netra_backend.app.core.telemetry import telemetry_manager, agent_tracer
from opentelemetry.trace import Status, StatusCode

# CRITICAL: Import session management for proper per-request isolation
# Use TYPE_CHECKING imports to avoid circular dependency
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.database.session_manager import DatabaseSessionManager
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class BaseAgent(ABC):
    """Base agent class with simplified single inheritance pattern.
    
    Uses WebSocketBridgeAdapter for centralized WebSocket event emission through
    the SSOT AgentWebSocketBridge. All sub-agents can emit WebSocket events:
    - emit_thinking() - For real-time reasoning visibility
    - emit_tool_executing() / emit_tool_completed() - For tool usage transparency
    - emit_progress() - For partial results and progress updates
    - emit_error() - For structured error reporting
    - emit_subagent_started() / emit_subagent_completed() - For sub-agent lifecycle
    
    CRITICAL: WebSocket bridge must be set via set_websocket_bridge() before
    any WebSocket events can be emitted. This is handled by the supervisor/execution engine.
    
    Now includes functionality from mixins directly for simplified inheritance:
    - Agent lifecycle management
    - Communication capabilities
    - State management
    - Observability features
    """
    
    def __init__(self, 
                 llm_manager: Optional[LLMManager] = None, 
                 name: str = "BaseAgent", 
                 description: str = "This is the base sub-agent.", 
                 agent_id: Optional[str] = None, 
                 user_id: Optional[str] = None,
                 enable_reliability: bool = True,
                 enable_execution_engine: bool = True,
                 enable_caching: bool = False,
                 tool_dispatcher: Optional[ToolDispatcher] = None,  # DEPRECATED: Use create_agent_with_context() factory
                 redis_manager: Optional[RedisManager] = None):
        
        # Initialize with simple single inheritance pattern
        super().__init__()
        
        self.llm_manager = llm_manager
        self.state = SubAgentLifecycle.PENDING
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.context = {}  # Protected context for this agent
# Legacy user_id instance variables removed
        self.logger = central_logger.get_logger(name)
        self.correlation_id = generate_llm_correlation_id()  # Unique ID for tracing
        self._subagent_logging_enabled = self._get_subagent_logging_enabled()
        
        # Initialize attributes required by AgentCommunicationMixin
        self.agent_id = agent_id or f"{name}_{self.correlation_id}"  # Unique agent identifier
# Legacy user_id instance variables removed
        
        # Initialize WebSocket bridge adapter (SSOT for WebSocket events)
        self._websocket_adapter = WebSocketBridgeAdapter()
        
        # Initialize timing collector
        self.timing_collector = ExecutionTimingCollector(agent_name=name)
        
        # Initialize core properties pattern
        # DEPRECATED WARNING: Direct tool_dispatcher assignment uses global state
        if tool_dispatcher is not None:
            import warnings
            warnings.warn(
                f"BaseAgent.__init__ with tool_dispatcher parameter creates global state risks. "
                f"Use BaseAgent.create_agent_with_context() factory method instead. "
                f"Global state support will be removed in v3.0.0 (Q2 2025).",
                DeprecationWarning,
                stacklevel=2
            )
            self.logger.warning(f"🚨 DEPRECATED: {name} initialized with global tool_dispatcher")
            self.logger.warning("📋 MIGRATION: Use BaseAgent.create_agent_with_context() factory instead")
        
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600  # Default cache TTL
        self.max_retries = 3   # Default retry count
        
        # Initialize circuit breaker for agent-specific reliability
        self.circuit_breaker = AgentCircuitBreaker(
            name=name,
            config=AgentCircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=60.0,
                success_threshold=3,
                task_timeout_seconds=120.0,
                sliding_window_size=10,
                error_rate_threshold=0.5,
                slow_task_threshold_seconds=120.0,
                max_backoff_seconds=300.0,
                preserve_context_on_failure=True,
                nested_task_support=True
            )
        )
        # Store the original name for test compatibility
        self.circuit_breaker.name = name  # Override the prefixed name for test compatibility
        
        # Initialize execution monitor first (needed by reliability manager)
        self.monitor = ExecutionMonitor(max_history_size=1000)
        # Store monitor as _execution_monitor for property access
        self._execution_monitor = self.monitor
        
        # Initialize reliability manager with circuit breaker and retry config
        self._reliability_manager_instance = ReliabilityManager(
            circuit_breaker_config=self.circuit_breaker.config,
            retry_config=SharedRetryConfig(
                max_retries=3,
                backoff_multiplier=2.0,
                base_delay=1.0,
                max_delay=30.0,
                retryable_exceptions=["TimeoutError", "ConnectionError"],
                non_retryable_exceptions=["ValueError", "TypeError"]
            )
        )
        
        # Connect circuit breaker to reliability manager
        if hasattr(self._reliability_manager_instance, 'circuit_breaker'):
            self._reliability_manager_instance.circuit_breaker = self.circuit_breaker._circuit_breaker
        
        # Initialize unified reliability management (SSOT pattern with UnifiedRetryHandler)
        self._enable_reliability = enable_reliability
        self._unified_reliability_handler = None
        if enable_reliability:
            self._init_unified_reliability_infrastructure()
        
        # Initialize execution engine (unified SSOT)
        self._enable_execution_engine = enable_execution_engine
        self._execution_engine = None
        # _execution_monitor is already set above
        if enable_execution_engine:
            self._init_execution_infrastructure()
        
        # Initialize caching (optional SSOT)
        self._enable_caching = enable_caching
        if enable_caching and redis_manager:
            self._init_caching_infrastructure()
        
        # CRITICAL: Validate agent doesn't store database sessions
        self._validate_session_isolation()

    # === State Management Methods (from AgentStateMixin) ===
    
    def set_state(self, new_state: SubAgentLifecycle) -> None:
        """Set agent state with transition validation."""
        current_state = self.state
        
        # Validate state transition
        if not self._is_valid_transition(current_state, new_state):
            self._raise_transition_error(current_state, new_state)
        
        self.logger.debug(f"{self.name} transitioning from {current_state} to {new_state}")
        self.state = new_state
    
    def _raise_transition_error(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> None:
        """Raise transition error with proper message"""
        raise ValueError(
            f"Invalid state transition from {from_state} to {to_state} "
            f"for agent {self.name}"
        )
    
    def _is_valid_transition(self, from_state: SubAgentLifecycle, to_state: SubAgentLifecycle) -> bool:
        """Validate if state transition is allowed."""
        valid_transitions = self._get_valid_transitions()
        return to_state in valid_transitions.get(from_state, [])
    
    def _get_valid_transitions(self) -> Dict[SubAgentLifecycle, List[SubAgentLifecycle]]:
        """Get mapping of valid state transitions."""
        return {
            SubAgentLifecycle.PENDING: [
                SubAgentLifecycle.RUNNING,
                SubAgentLifecycle.FAILED,
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.RUNNING: [
                SubAgentLifecycle.RUNNING,    # Allow staying in running state
                SubAgentLifecycle.COMPLETED,
                SubAgentLifecycle.FAILED,
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.FAILED: [
                SubAgentLifecycle.PENDING,  # Allow retry via pending
                SubAgentLifecycle.RUNNING,  # Allow direct retry
                SubAgentLifecycle.SHUTDOWN
            ],
            SubAgentLifecycle.COMPLETED: [
                SubAgentLifecycle.RUNNING,   # Allow retry from completed state
                SubAgentLifecycle.PENDING,   # Allow reset to pending
                SubAgentLifecycle.SHUTDOWN   # Allow final shutdown
            ],
            SubAgentLifecycle.SHUTDOWN: []  # Terminal state
        }

    def get_state(self) -> SubAgentLifecycle:
        """Get current agent state."""
        return self.state
    
    # === Communication and Observability Methods ===
    
    def _log_agent_start(self, run_id: str) -> None:
        """Log agent start event."""
        if self._subagent_logging_enabled:
            self.logger.info(f"{self.name} started for run_id: {run_id}")
    
    def _log_agent_completion(self, run_id: str, status: str) -> None:
        """Log agent completion event."""
        if self._subagent_logging_enabled:
            self.logger.info(f"{self.name} {status} for run_id: {run_id}")
    
    # === Session Isolation Methods ===
    
    def _validate_session_isolation(self) -> None:
        """Validate agent doesn't store database sessions.
        
        CRITICAL: This method ensures agents never store AsyncSession instances,
        which would violate per-request isolation requirements.
        
        Raises:
            SessionIsolationError: If agent stores sessions
        """
        try:
            # Import dynamically to avoid circular dependency
            from netra_backend.app.database.session_manager import validate_agent_session_isolation
            validate_agent_session_isolation(self)
            self.logger.debug(f"Agent {self.name} passed session isolation validation")
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed session isolation validation: {e}")
            raise
    
    def _get_session_manager(self, context: 'UserExecutionContext') -> 'DatabaseSessionManager':
        """Get database session manager for the given context.
        
        Args:
            context: User execution context with database session
            
        Returns:
            DatabaseSessionManager for database operations
            
        Raises:
            SessionManagerError: If context is invalid or lacks session
        """
        # Import dynamically to avoid circular dependency
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        from netra_backend.app.database.session_manager import DatabaseSessionManager
        
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        return DatabaseSessionManager(context)
    
    # === Abstract Methods ===
    
    async def execute(self, context: 'UserExecutionContext', stream_updates: bool = False) -> Any:
        """Execute the agent with user execution context.
        
        CRITICAL: Only supports UserExecutionContext pattern - no legacy support.
        This ensures proper session isolation and prevents parameter proliferation.
        
        Args:
            context: User execution context containing all request-scoped state
            stream_updates: Whether to stream progress updates
            
        Returns:
            Execution result
            
        Raises:
            NotImplementedError: If neither execute_with_context nor execute_core_logic is implemented
        """
        # Import dynamically to avoid circular dependency
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # Validate context type
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        # Validate session isolation before execution
        self._validate_session_isolation()
        
        # Use context-based execution - no legacy support
        if hasattr(self, 'execute_with_context'):
            return await self.execute_with_context(context, stream_updates)
        
        # Fallback - agents should implement execute_with_context or execute_core_logic
        raise NotImplementedError(
            f"Agent {self.name} must implement execute_with_context() or execute_core_logic(). "
        )
    
    async def execute_with_context(self, context: 'UserExecutionContext', stream_updates: bool = False) -> Any:
        """Execute agent with proper context-based session management and telemetry.
        
        This is the primary execution pattern. Subclasses should override this method.
        Includes OpenTelemetry span creation for distributed tracing.
        
        Args:
            context: User execution context with database session and user info
            stream_updates: Whether to stream progress updates
            
        Returns:
            Execution result
            
        Raises:
            NotImplementedError: If agent doesn't implement UserExecutionContext pattern
            DeprecationWarning: If agent falls back to legacy patterns
        """
        # Create telemetry span for agent execution
        span_attributes = {
            "agent.id": self.agent_id,
            "agent.name": self.name,
            "user.id": context.user_id,
            "thread.id": context.thread_id,
            "run.id": context.run_id,
            "session.id": getattr(context, 'session_id', None),
            "stream_updates": stream_updates
        }
        
        # Filter out None values
        span_attributes = {k: v for k, v in span_attributes.items() if v is not None}
        
        # Start span for agent execution
        async with telemetry_manager.start_agent_span(
            agent_name=self.name,
            operation="execute",
            attributes=span_attributes
        ) as span:
            try:
                # Log agent execution start
                if span:
                    telemetry_manager.add_event(
                        span, 
                        "agent_started",
                        {"message": f"Agent {self.name} execution started"}
                    )
                
                # Check if agent has modern implementation first
                if hasattr(self, '_execute_with_user_context') and callable(getattr(self, '_execute_with_user_context')):
                    # Modern UserExecutionContext pattern
                    result = await self._execute_with_user_context(context, stream_updates)
                    
                    # Record successful completion
                    if span:
                        telemetry_manager.add_event(
                            span,
                            "agent_completed",
                            {"message": f"Agent {self.name} completed successfully"}
                        )
                    
                    return result
                
            except Exception as e:
                # Record exception in span
                if span:
                    telemetry_manager.record_exception(span, e)
                    telemetry_manager.add_event(
                        span,
                        "agent_failed", 
                        {"error": str(e), "error_type": type(e).__name__}
                    )
                raise
        
        # DEPRECATED: Legacy fallback using execute_core_logic with DeepAgentState bridge
        if hasattr(self, 'execute_core_logic'):
            # Issue comprehensive deprecation warning
            warnings.warn(
                f"🚨 CRITICAL DEPRECATION: Agent '{self.name}' is using legacy DeepAgentState bridge pattern. "
                f"This creates user isolation risks and will be REMOVED in v3.0.0 (Q1 2025). "
                f"\n"
                f"📋 IMMEDIATE ACTION REQUIRED:"
                f"\n1. Implement '_execute_with_user_context(context, stream_updates)' method"
                f"\n2. Remove 'execute_core_logic' method"  
                f"\n3. Use 'context.metadata.get(\"user_request\", \"\")' instead of DeepAgentState.user_request"
                f"\n4. Access database via 'context.db_session' instead of global sessions"
                f"\n"
                f"📖 Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md"
                f"\n⚠️  USER ISOLATION AT RISK: Multiple users may see each other's data",
                DeprecationWarning,
                stacklevel=3  # Point to the calling code, not this method
            )
            
            # Log critical warning
            self.logger.critical(f"🚨 AGENT MIGRATION REQUIRED: {self.name} using deprecated DeepAgentState pattern")
            self.logger.warning(f"📋 MIGRATION: Implement '_execute_with_user_context()' method in {self.__class__.__module__}.{self.__class__.__name__}")
            self.logger.error(f"⚠️  USER DATA AT RISK: Agent {self.name} may cause data leakage between users")
            
            # Create temporary DeepAgentState bridge (DEPRECATED - will be removed)
            temp_state = DeepAgentState(
                user_request=context.metadata.get('user_request', 'default_request'),
                chat_thread_id=context.thread_id,
                user_id=context.user_id,
                run_id=context.run_id
            )
            execution_context = ExecutionContext(
                run_id=context.run_id,
                agent_name=self.name,
                state=temp_state,  # DEPRECATED: Bridge pattern only
                stream_updates=stream_updates,
                thread_id=context.thread_id,
                user_id=context.user_id,
                start_time=time.time(),
                correlation_id=self.correlation_id
            )
            
            # Execute with deprecated bridge
            return await self.execute_core_logic(execution_context)
        
        # No implementation found - agent must be migrated
        raise NotImplementedError(
            f"🚨 AGENT MIGRATION REQUIRED: Agent '{self.name}' must implement UserExecutionContext pattern.\n"
            f"\n📋 REQUIRED IMPLEMENTATION:"
            f"\n1. Add '_execute_with_user_context(context, stream_updates)' method"
            f"\n2. Use 'context.metadata.get(\"user_request\", \"\")' for user request data"
            f"\n3. Use 'context.db_session' for database operations" 
            f"\n4. Use 'context.user_id', 'context.thread_id', 'context.run_id' for identifiers"
            f"\n\n📖 Migration Guide: See EXECUTION_PATTERN_TECHNICAL_DESIGN.md"
        )
    
# _convert_context_to_state method removed - legacy support removed
    
# Legacy execute_legacy method removed - no backward compatibility

    def _get_subagent_logging_enabled(self) -> bool:
        """Get subagent logging configuration setting."""
        import os
        # Skip heavy config loading during test collection
        if get_env().get('TEST_COLLECTION_MODE') == '1':
            return False
        try:
            config = get_config()
            return getattr(config, 'subagent_logging_enabled', True)
        except Exception:
            return True  # Default to enabled if config unavailable

    async def shutdown(self) -> None:
        """Graceful shutdown of the agent."""
        # Make shutdown idempotent - avoid multiple shutdowns
        if self.state == SubAgentLifecycle.SHUTDOWN:
            return
            
        self.logger.info(f"Shutting down {self.name}")
        self.set_state(SubAgentLifecycle.SHUTDOWN)
        
        # Clear any remaining context safely
        try:
            self.context.clear()
        except Exception as e:
            self.logger.warning(f"Error clearing context during shutdown: {e}")
        
        # Cleanup timing collector if it has pending operations
        try:
            if hasattr(self, 'timing_collector') and self.timing_collector:
                # Complete any pending timing tree to avoid resource leaks
                if hasattr(self.timing_collector, 'current_tree') and self.timing_collector.current_tree:
                    self.timing_collector.complete_execution()
        except Exception as e:
            self.logger.warning(f"Error cleaning up timing collector during shutdown: {e}")
        
        # Cleanup unified reliability infrastructure
        try:
            if hasattr(self, '_unified_reliability_handler') and self._unified_reliability_handler:
                # Circuit breaker cleanup if enabled
                circuit_status = self._unified_reliability_handler.get_circuit_breaker_status()
                if circuit_status:
                    self.logger.debug(f"Cleaned up unified reliability handler during shutdown")
        except Exception as e:
            self.logger.warning(f"Error cleaning up unified reliability handler during shutdown: {e}")
        
        # Subclasses can override to add specific shutdown logic
    
    # WebSocket Bridge Integration Methods (SSOT Pattern)
    
    def set_websocket_bridge(self, bridge, run_id: str) -> None:
        """Set the WebSocket bridge for event emission (SSOT pattern).
        
        Args:
            bridge: The AgentWebSocketBridge instance
            run_id: The execution run ID
        """
        self._websocket_adapter.set_websocket_bridge(bridge, run_id, self.name)
    
    def propagate_websocket_context_to_state(self, context: Dict[str, Any]) -> None:
        """Propagate WebSocket context to agent state for critical path validation.
        
        This method is required by the critical path validator to ensure 
        WebSocket bridge capabilities are properly implemented.
        """
        # Store WebSocket context information in agent state
        if not hasattr(self, '_websocket_context'):
            self._websocket_context = {}
        self._websocket_context.update(context)
    
    # Delegate WebSocket methods to the adapter
    
    async def emit_agent_started(self, message: Optional[str] = None) -> None:
        """Emit agent started event via WebSocket bridge."""
        await self._websocket_adapter.emit_agent_started(message)
    
    async def emit_thinking(self, thought: str, step_number: Optional[int] = None) -> None:
        """Emit agent thinking event via WebSocket bridge."""
        await self._websocket_adapter.emit_thinking(thought, step_number)
    
    async def emit_tool_executing(self, tool_name: str, parameters: Optional[Dict] = None) -> None:
        """Emit tool executing event via WebSocket bridge."""
        await self._websocket_adapter.emit_tool_executing(tool_name, parameters)
    
    async def emit_tool_completed(self, tool_name: str, result: Optional[Dict] = None) -> None:
        """Emit tool completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_tool_completed(tool_name, result)
    
    async def emit_agent_completed(self, result: Optional[Dict] = None) -> None:
        """Emit agent completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_agent_completed(result)
    
    async def emit_progress(self, content: str, is_complete: bool = False) -> None:
        """Emit progress update via WebSocket bridge."""
        await self._websocket_adapter.emit_progress(content, is_complete)
    
    async def emit_error(self, error_message: str, error_type: Optional[str] = None,
                        error_details: Optional[Dict] = None) -> None:
        """Emit error event via WebSocket bridge."""
        await self._websocket_adapter.emit_error(error_message, error_type, error_details)
    
    # Backward compatibility methods for legacy code
    
    async def emit_tool_started(self, tool_name: str, parameters: Optional[Dict] = None) -> None:
        """Backward compatibility: emit_tool_started maps to emit_tool_executing."""
        await self._websocket_adapter.emit_tool_started(tool_name, parameters)
    
    async def emit_subagent_started(self, subagent_name: str, subagent_id: Optional[str] = None) -> None:
        """Emit subagent started event via WebSocket bridge."""
        await self._websocket_adapter.emit_subagent_started(subagent_name, subagent_id)
    
    async def emit_subagent_completed(self, subagent_name: str, subagent_id: Optional[str] = None,
                                     result: Optional[Dict] = None, duration_ms: float = 0) -> None:
        """Emit subagent completed event via WebSocket bridge."""
        await self._websocket_adapter.emit_subagent_completed(subagent_name, subagent_id, result, duration_ms)
    
    def has_websocket_context(self) -> bool:
        """Check if WebSocket bridge is available."""
        return self._websocket_adapter.has_websocket_bridge()
    
    # === SSOT Reliability Management Infrastructure ===
    
    def _init_unified_reliability_infrastructure(self) -> None:
        """Initialize unified reliability infrastructure using UnifiedRetryHandler as SSOT foundation."""
        # Create custom retry configuration for agents based on AGENT_RETRY_POLICY
        # Enable circuit breaker for agents (overriding AGENT_RETRY_POLICY default)
        custom_config = RetryConfig(
            max_attempts=getattr(agent_config.retry, 'max_retries', AGENT_RETRY_POLICY.max_attempts),
            base_delay=getattr(agent_config.retry, 'base_delay', AGENT_RETRY_POLICY.base_delay),
            max_delay=getattr(agent_config.retry, 'max_delay', AGENT_RETRY_POLICY.max_delay),
            strategy=AGENT_RETRY_POLICY.strategy,
            backoff_multiplier=AGENT_RETRY_POLICY.backoff_multiplier,
            jitter_range=AGENT_RETRY_POLICY.jitter_range,
            timeout_seconds=getattr(agent_config.timeout, 'default_timeout', AGENT_RETRY_POLICY.timeout_seconds),
            retryable_exceptions=AGENT_RETRY_POLICY.retryable_exceptions,
            non_retryable_exceptions=AGENT_RETRY_POLICY.non_retryable_exceptions,
            circuit_breaker_enabled=True,  # Enable circuit breaker for BaseAgent reliability
            circuit_breaker_failure_threshold=getattr(agent_config, 'failure_threshold', 5),
            circuit_breaker_recovery_timeout=getattr(agent_config.timeout, 'default_timeout', 30.0),
            metrics_enabled=True
        )
        
        # Initialize single unified reliability handler (SSOT)
        self._unified_reliability_handler = UnifiedRetryHandler(
            service_name=f"agent_{self.name}",
            config=custom_config
        )
    
    def _init_execution_infrastructure(self) -> None:
        """Initialize unified execution infrastructure (SSOT pattern)."""
        # Use the already initialized monitor from __init__
        # Note: BaseExecutionEngine will be updated separately to use UnifiedRetryHandler
        # For now, passing None to avoid breaking changes
        self._execution_engine = BaseExecutionEngine(
            reliability_manager=None,  # Will be integrated with UnifiedRetryHandler in future update
            monitor=self._execution_monitor
        )
    
    def _init_caching_infrastructure(self) -> None:
        """Initialize optional caching infrastructure (SSOT pattern)."""
        # Caching infrastructure can be extended here when needed
        self.logger.debug(f"Caching infrastructure initialized for {self.name}")
    
    # === SSOT Property Access Pattern ===
    
    @property
    def unified_reliability_handler(self) -> Optional[UnifiedRetryHandler]:
        """Get unified reliability handler (SSOT pattern)."""
        return self._unified_reliability_handler
    
    @property
    def reliability_manager(self):
        """Get reliability manager - returns the actual ReliabilityManager instance."""
        # Return the ReliabilityManager instance if it exists
        if hasattr(self, '_reliability_manager_instance'):
            return self._reliability_manager_instance
        # Fall back to unified handler for backward compatibility
        return self._unified_reliability_handler
    
    @property
    def legacy_reliability(self) -> Optional[UnifiedRetryHandler]:
        """Get legacy reliability wrapper - now delegates to unified handler for backward compatibility."""
        return self._unified_reliability_handler
    
    @property
    def execution_engine(self) -> Optional[BaseExecutionEngine]:
        """Get execution engine (SSOT pattern)."""
        return self._execution_engine
    
    @property
    def execution_monitor(self) -> Optional[ExecutionMonitor]:
        """Get execution monitor (SSOT pattern)."""
        return self._execution_monitor
    
    # === SSOT Standardized Execution Patterns ===
    
    async def execute_with_reliability(self, 
                                      operation: Callable[[], Awaitable[Any]], 
                                      operation_name: str,
                                      fallback: Optional[Callable[[], Awaitable[Any]]] = None,
                                      timeout: Optional[float] = None) -> Any:
        """Execute operation with unified reliability patterns using UnifiedRetryHandler (SSOT)."""
        if not self._unified_reliability_handler:
            raise RuntimeError(f"Reliability not enabled for {self.name}")
        
        # Use UnifiedRetryHandler for unified execution with retry logic
        result = await self._unified_reliability_handler.execute_with_retry_async(
            operation
        )
        
        if result.success:
            return result.result
        elif fallback:
            # Try fallback if primary operation failed
            self.logger.info(f"{self.name}.{operation_name}: Primary operation failed, trying fallback")
            fallback_result = await self._unified_reliability_handler.execute_with_retry_async(
                fallback
            )
            if fallback_result.success:
                return fallback_result.result
            else:
                raise fallback_result.final_exception
        else:
            raise result.final_exception
    
# execute_modern method removed - legacy support removed
    
    # === SSOT Abstract Methods for Execution Patterns ===
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions. Subclasses should override."""
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core business logic. Subclasses should override."""
        # Default implementation that can be overridden
        await self.emit_thinking(f"Executing {self.name} core logic")
        return {"status": "completed", "message": f"{self.name} executed successfully"}
    
    async def send_status_update(self, context: ExecutionContext, status: str, message: str) -> None:
        """Send status update via WebSocket bridge."""
        if status == "executing":
            await self.emit_thinking(message)
        elif status == "completed":
            await self.emit_progress(message, is_complete=True)
        elif status == "failed":
            await self.emit_error(message)
        else:
            await self.emit_progress(message)
    
    # Backward compatibility for _send_update pattern
    async def send_legacy_update(self, run_id: str, status: str, message: str, 
                               result: Optional[Dict[str, Any]] = None) -> None:
        """Send update in legacy format for backward compatibility."""
        update = {"status": status, "message": message}
        if result:
            update["result"] = result
        await self._send_update(run_id, update)
    
    # === SSOT Health Status Infrastructure ===
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive agent health status using unified reliability handler (SSOT pattern)."""
        health_status = {
            "agent_name": self.name,
            "state": self.state.value,
            "websocket_available": self.has_websocket_context(),
            "uses_unified_reliability": True  # Flag to indicate new architecture
        }
        
        # Get circuit breaker status (primary component)
        if hasattr(self, 'circuit_breaker') and self.circuit_breaker:
            cb_state = self.circuit_breaker.get_state()
            health_status["circuit_breaker"] = {
                "state": cb_state,
                "can_execute": self.circuit_breaker.can_execute()
            }
            health_status["circuit_breaker_state"] = cb_state
        
        # Get reliability manager status
        if hasattr(self, '_reliability_manager_instance') and self._reliability_manager_instance:
            rm_health = self._reliability_manager_instance.get_health_status()
            health_status["reliability_manager"] = rm_health
            # Extract key metrics for flat structure
            if isinstance(rm_health, dict):
                for key in ['total_executions', 'success_rate', 'circuit_breaker_state']:
                    if key in rm_health:
                        health_status[key] = rm_health[key]
        
        # Get monitor/execution monitor status
        if hasattr(self, 'monitor') and self.monitor:
            monitor_health = self.monitor.get_health_status()
            health_status["monitor"] = monitor_health
            # Extract key metrics for test compatibility
            if isinstance(monitor_health, dict):
                for key in ['total_executions', 'success_rate', 'average_execution_time']:
                    if key in monitor_health:
                        health_status[key] = monitor_health[key]
        
        # Get execution engine status
        if hasattr(self, '_execution_engine') and self._execution_engine:
            health_status["execution_engine"] = self._execution_engine.get_health_status()
            health_status["modern_execution"] = self._execution_engine.get_health_status()
        
        # Get unified reliability handler status (if enabled)
        if self._unified_reliability_handler:
            circuit_status = self._unified_reliability_handler.get_circuit_breaker_status()
            if circuit_status:
                health_status["unified_reliability"] = {
                    "circuit_breaker": circuit_status,
                    "service_name": self._unified_reliability_handler.service_name,
                    "config": {
                        "max_attempts": self._unified_reliability_handler.config.max_attempts,
                        "strategy": self._unified_reliability_handler.config.strategy.value,
                        "circuit_breaker_enabled": self._unified_reliability_handler.config.circuit_breaker_enabled
                    }
                }
        
        # Add aggregate metrics if not already present
        if 'total_executions' not in health_status and hasattr(self, 'monitor'):
            # Try to get from monitor
            monitor_health = self.monitor.get_health_status() if hasattr(self.monitor, 'get_health_status') else {}
            health_status['total_executions'] = monitor_health.get('total_executions', 0)
            health_status['success_rate'] = monitor_health.get('success_rate', 0.0)
            health_status['average_execution_time'] = monitor_health.get('average_execution_time', 0.0)
            health_status['error_rate'] = monitor_health.get('error_rate', 0.0)
            health_status['last_execution'] = monitor_health.get('last_execution', None)
        
        # Determine overall health
        health_status["overall_status"] = self._determine_overall_health_status(health_status)
        health_status["status"] = health_status["overall_status"]  # Alias for compatibility
        
        return health_status
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status using unified reliability handler (SSOT pattern)."""
        # First check primary circuit breaker
        if hasattr(self, 'circuit_breaker') and self.circuit_breaker:
            cb_state = self.circuit_breaker.get_state()
            return {
                "state": cb_state,
                "can_execute": self.circuit_breaker.can_execute(),
                "status": "available"
            }
        
        # Fall back to unified reliability handler if available
        if self._unified_reliability_handler:
            status = self._unified_reliability_handler.get_circuit_breaker_status()
            if status:
                return status
        
        return {"status": "not_available", "reason": "reliability not enabled or circuit breaker disabled"}
    
    def _determine_overall_health_status(self, health_data: Dict[str, Any]) -> str:
        """Determine overall health status from component health data."""
        # Check primary circuit breaker status
        if "circuit_breaker" in health_data:
            cb_state = health_data["circuit_breaker"].get("state", "").lower()
            if "open" in cb_state:
                return "degraded"
            if not health_data["circuit_breaker"].get("can_execute", True):
                return "degraded"
        
        # Check unified reliability status
        if "unified_reliability" in health_data:
            circuit_status = health_data["unified_reliability"].get("circuit_breaker", {})
            if circuit_status.get("state") == "OPEN":
                return "degraded"
        
        # Check monitor status
        if "monitor" in health_data:
            monitor_data = health_data["monitor"]
            if isinstance(monitor_data, dict):
                error_rate = monitor_data.get("error_rate", 0.0)
                if error_rate > 0.2:  # More than 20% error rate
                    return "degraded"
        
        if "modern_execution" in health_data:
            modern_status = health_data["modern_execution"].get("monitor", {}).get("status", "unknown")
            if modern_status != "healthy":
                return "degraded"
        
        return "healthy"
    
    # === SSOT WebSocket Update Infrastructure ===
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via AgentWebSocketBridge for standardized emission (SSOT pattern)."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            bridge = await get_agent_websocket_bridge()
            status = update.get('status', 'processing')
            message = update.get('message', '')
            
            # Map update status to appropriate bridge notification
            if status == 'processing':
                await bridge.notify_agent_thinking(run_id, self.name, message)
            elif status == 'completed' or status == 'completed_with_fallback':
                await bridge.notify_agent_completed(run_id, self.name, 
                                                   result=update.get('result'), 
                                                   execution_time_ms=None)
            else:
                # Custom status updates
                await bridge.notify_custom(run_id, self.name, f"agent_{status}", update)
            
        except Exception as e:
            self.logger.debug(f"Failed to send WebSocket update via bridge: {e}")
    
    async def send_processing_update(self, run_id: str, message: str = "") -> None:
        """Send processing status update (SSOT pattern)."""
        await self._send_update(run_id, {"status": "processing", "message": message})
    
    async def send_completion_update(self, run_id: str, result: Optional[Dict[str, Any]] = None, 
                                   fallback: bool = False) -> None:
        """Send completion status update (SSOT pattern)."""
        status = "completed_with_fallback" if fallback else "completed"
        update = {"status": status, "result": result}
        if not fallback:
            update["message"] = "Operation completed successfully"
        else:
            update["message"] = "Operation completed with fallback method"
        await self._send_update(run_id, update)
    
    # === Factory Methods for Modern Agent Creation ===
    
    @classmethod
    def create_with_context(
        cls, 
        context: 'UserExecutionContext',
        agent_config: Optional[Dict[str, Any]] = None
    ) -> 'BaseAgent':
        """MODERN: Factory method for creating context-aware agent instances.
        
        This is the recommended way to create agents in the UserExecutionContext pattern.
        Agents created this way are guaranteed to have proper user isolation.
        
        Args:
            context: User execution context for complete isolation
            agent_config: Optional agent-specific configuration
            
        Returns:
            BaseAgent configured for UserExecutionContext pattern
            
        Raises:
            ValueError: If context is invalid or agent doesn't support pattern
        """
        # Import dynamically to avoid circular dependency
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        if not isinstance(context, UserExecutionContext):
            raise ValueError(f"Expected UserExecutionContext, got {type(context)}")
        
        # Create agent instance without singleton dependencies
        agent = cls()
        
        # Inject context-scoped dependencies (following factory pattern from design doc)
        agent._user_context = context
        
        # Apply agent-specific configuration
        if agent_config:
            for key, value in agent_config.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
        
        # Validate agent implements modern pattern
        if not hasattr(agent, '_execute_with_user_context') and not hasattr(agent, 'execute_core_logic'):
            raise ValueError(
                f"Agent {cls.__name__} must implement either '_execute_with_user_context()' "
                f"or provide 'execute_core_logic()' for legacy bridge support"
            )
        
        return agent
    
    @classmethod
    def create_legacy_with_warnings(
        cls,
        llm_manager: Optional[LLMManager] = None,
        tool_dispatcher: Optional['ToolDispatcher'] = None,
        redis_manager: Optional['RedisManager'] = None,
        **kwargs
    ) -> 'BaseAgent':
        """DEPRECATED: Legacy factory method with comprehensive warnings.
        
        This method creates agents using legacy patterns and issues warnings
        about user isolation risks. Use create_with_context() instead.
        
        Args:
            llm_manager: LLM manager (creates global state risks)
            tool_dispatcher: Tool dispatcher (creates global state risks)  
            redis_manager: Redis manager (creates global state risks)
            **kwargs: Additional legacy parameters
            
        Returns:
            BaseAgent with legacy initialization
            
        Raises:
            DeprecationWarning: Always - this pattern is deprecated
        """
        warnings.warn(
            f"🚨 DEPRECATED: BaseAgent.create_legacy_with_warnings() creates global state risks. "
            f"Use BaseAgent.create_with_context() instead. "
            f"Legacy support will be removed in v3.0.0 (Q1 2025).",
            DeprecationWarning,
            stacklevel=2
        )
        
        return cls(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=redis_manager,
            **kwargs
        )
    
    # === UserExecutionContext Compatibility Validation ===
    
    def validate_modern_implementation(self) -> Dict[str, Any]:
        """Validate agent implements modern UserExecutionContext pattern properly.
        
        This method checks agent compliance with the modern execution pattern
        and provides detailed feedback for migration requirements.
        
        Returns:
            Dictionary with validation results and recommendations
        """
        validation_result = {
            "compliant": False,
            "pattern": "unknown",
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check for modern implementation
        has_modern_method = hasattr(self, '_execute_with_user_context') and callable(
            getattr(self, '_execute_with_user_context')
        )
        
        # Check for legacy implementation
        has_legacy_method = hasattr(self, 'execute_core_logic') and callable(
            getattr(self, 'execute_core_logic')
        )
        
        if has_modern_method:
            validation_result["pattern"] = "modern"
            validation_result["compliant"] = True
            
            # Additional modern pattern validations
            if has_legacy_method:
                validation_result["warnings"].append(
                    "Agent has both modern '_execute_with_user_context()' and legacy 'execute_core_logic()' methods. "
                    "Remove 'execute_core_logic()' for full modernization."
                )
            
            # Check for session isolation compliance
            if hasattr(self, 'db_session') or hasattr(self, '_db_session'):
                validation_result["errors"].append(
                    "CRITICAL: Agent stores database session as instance variable. "
                    "This violates user isolation requirements. Use context.db_session instead."
                )
                validation_result["compliant"] = False
            
            # Check for user_id storage (isolation violation)
            if hasattr(self, 'user_id') or hasattr(self, '_user_id'):
                validation_result["warnings"].append(
                    "Agent stores user_id as instance variable. "
                    "Use context.user_id for proper user isolation."
                )
            
        elif has_legacy_method:
            validation_result["pattern"] = "legacy_bridge"
            validation_result["compliant"] = False
            validation_result["warnings"].append(
                "🚨 DEPRECATED: Agent uses legacy 'execute_core_logic()' pattern. "
                "This creates user isolation risks and will be removed in v3.0.0."
            )
            validation_result["recommendations"].extend([
                "1. Implement '_execute_with_user_context(context, stream_updates)' method",
                "2. Use 'context.metadata.get(\"user_request\", \"\")' for request data",
                "3. Use 'context.db_session' for database operations",
                "4. Use 'context.user_id', 'context.thread_id', 'context.run_id' for identifiers",
                "5. Remove 'execute_core_logic()' method after migration"
            ])
        
        else:
            validation_result["pattern"] = "none"
            validation_result["compliant"] = False
            validation_result["errors"].append(
                f"MIGRATION REQUIRED: Agent '{self.name}' has no execution implementation. "
                f"Must implement '_execute_with_user_context()' method."
            )
            validation_result["recommendations"].extend([
                "1. Add '_execute_with_user_context(context, stream_updates)' method",
                "2. Follow patterns in EXECUTION_PATTERN_TECHNICAL_DESIGN.md",
                "3. Test with concurrent user scenarios",
                "4. Validate user isolation with compatibility tests"
            ])
        
        # Check factory usage patterns
        if hasattr(self, 'tool_dispatcher') and self.tool_dispatcher is not None:
            validation_result["warnings"].append(
                "Agent initialized with tool_dispatcher parameter. "
                "Use create_with_context() factory for better isolation."
            )
        
        return validation_result
    
    def assert_user_execution_context_pattern(self) -> None:
        """Assert that agent implements UserExecutionContext pattern correctly.
        
        This method performs runtime validation and raises exceptions for
        critical compliance violations that could cause user data issues.
        
        Raises:
            RuntimeError: If agent has critical compliance violations
            DeprecationWarning: If agent uses deprecated patterns
        """
        validation = self.validate_modern_implementation()
        
        # Fail hard on critical errors
        if validation["errors"]:
            error_details = "\n".join([f"- {error}" for error in validation["errors"]])
            raise RuntimeError(
                f"CRITICAL COMPLIANCE VIOLATIONS in agent '{self.name}':\n"
                f"{error_details}\n"
                f"\nThese violations create user data contamination risks and must be fixed immediately."
            )
        
        # Issue warnings for deprecated patterns
        if validation["warnings"]:
            for warning in validation["warnings"]:
                if "DEPRECATED" in warning:
                    warnings.warn(warning, DeprecationWarning, stacklevel=2)
                else:
                    self.logger.warning(f"Agent '{self.name}': {warning}")
        
        # Log compliance status
        if validation["compliant"]:
            self.logger.info(f"✅ Agent '{self.name}' complies with UserExecutionContext pattern")
        else:
            self.logger.warning(f"⚠️ Agent '{self.name}' needs migration to UserExecutionContext pattern")
            
            if validation["recommendations"]:
                rec_details = "\n".join([f"  {rec}" for rec in validation["recommendations"]])
                self.logger.info(f"📋 Migration recommendations for '{self.name}':\n{rec_details}")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get detailed migration status for monitoring and reporting.
        
        Returns:
            Dictionary with migration progress and status information
        """
        validation = self.validate_modern_implementation()
        
        return {
            "agent_name": self.name,
            "agent_class": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "migration_status": "compliant" if validation["compliant"] else "needs_migration",
            "execution_pattern": validation["pattern"],
            "user_isolation_safe": validation["compliant"] and not validation["errors"],
            "warnings_count": len(validation["warnings"]),
            "errors_count": len(validation["errors"]),
            "recommendations_count": len(validation["recommendations"]),
            "validation_timestamp": time.time(),
            "compliance_details": validation
        }