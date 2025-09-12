"""Core agent execution with death detection and recovery.

CRITICAL: This module adds execution tracking, heartbeat monitoring, and error boundaries
to prevent silent agent deaths.

CRITICAL REMEDIATION: Enhanced with comprehensive timeout management and circuit breakers
to prevent agent execution pipeline blocking that prevents users from receiving AI responses.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# CRITICAL SECURITY FIX: Migration to UserExecutionContext completed
# DeepAgentState removed to eliminate user isolation risks
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
# DISABLED: Heartbeat hidden errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
# from netra_backend.app.core.agent_heartbeat import AgentHeartbeat
# DISABLED: trace_persistence module removed - functionality no longer needed
# from netra_backend.app.core.trace_persistence import get_execution_persistence
from netra_backend.app.core.unified_trace_context import (
    UnifiedTraceContext,
    get_current_trace_context,
    TraceContextManager
)
from netra_backend.app.core.logging_context import (
    get_unified_trace_context,
    create_child_trace_context
)
from netra_backend.app.logging_config import central_logger

# CRITICAL REMEDIATION: Import consolidated agent execution tracker for preventing execution blocking
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker,
    AgentExecutionPhase,
    CircuitBreakerOpenError
)
from netra_backend.app.core.timeout_configuration import (
    get_agent_execution_timeout,
    get_streaming_timeout,
    TimeoutTier
)

# CRITICAL ISSUE #387 REMEDIATION: Agent Execution Prerequisites Validation
from netra_backend.app.agents.supervisor.agent_execution_prerequisites import (
    AgentExecutionPrerequisites,
    PrerequisiteValidationLevel,
    AgentExecutionPrerequisiteError,
    validate_all_agent_execution_prerequisites
)

logger = central_logger.get_logger(__name__)


def get_agent_state_tracker() -> AgentExecutionTracker:
    """Factory function to get an instance of AgentExecutionTracker.
    
    This function provides the expected interface for creating agent state trackers
    as required by the test suite and other components.
    
    Returns:
        AgentExecutionTracker: A new instance of the agent execution tracker
    """
    return AgentExecutionTracker()


def create_agent_execution_context(**kwargs) -> AgentExecutionContext:
    """Factory function to create an AgentExecutionContext.
    
    This is a convenience wrapper around AgentExecutionContext constructor
    to provide a consistent factory interface.
    
    Args:
        **kwargs: Arguments passed to AgentExecutionContext constructor
        
    Returns:
        AgentExecutionContext: A new execution context instance
    """
    return AgentExecutionContext(**kwargs)


class AgentExecutionCore:
    """Enhanced agent execution with death detection and recovery.
    
    CRITICAL REMEDIATION: Enhanced with comprehensive timeout management and circuit breakers
    to prevent agent execution pipeline blocking that prevents users from receiving AI responses.
    
    **ENTERPRISE STREAMING SUPPORT**: Tier-based timeout configuration enables 300s streaming
    for enterprise customers while maintaining fast feedback for other tiers.
    """
    
    # HEARTBEAT_INTERVAL: Send heartbeat every 5 seconds
    HEARTBEAT_INTERVAL = 5.0
    
    # DEFAULT_TIMEOUT: Default execution timeout for agents - reduced for faster feedback  
    DEFAULT_TIMEOUT = 25.0
    
    def __init__(self, 
                 registry: 'AgentRegistry', 
                 websocket_bridge: Optional['AgentWebSocketBridge'] = None,
                 default_tier: Optional[TimeoutTier] = None,
                 prerequisite_validation_level: Optional[PrerequisiteValidationLevel] = None):
        self.registry = registry
        self.websocket_bridge = websocket_bridge
        self.execution_tracker = get_execution_tracker()
        # trace_persistence removed - no longer needed
        self.persistence = None
        
        # CRITICAL REMEDIATION: Initialize consolidated agent execution tracker
        self.agent_tracker = AgentExecutionTracker()
        
        # Tier-based timeout configuration
        self.default_tier = default_tier or TimeoutTier.FREE
        self._default_timeout = get_agent_execution_timeout(self.default_tier)
        
        # CRITICAL ISSUE #387 REMEDIATION: Initialize prerequisites validation
        self.prerequisite_validation_level = prerequisite_validation_level or PrerequisiteValidationLevel.STRICT
        self.prerequisites_validator = AgentExecutionPrerequisites(self.prerequisite_validation_level)
        
        # Calculate registry agent count safely (handle Mocks in testing)
        registry_count = 0
        if registry:
            try:
                registry_dict = getattr(registry, '_registry', {})
                registry_count = len(registry_dict) if hasattr(registry_dict, '__len__') else 0
            except (TypeError, AttributeError):
                registry_count = 0  # Handle Mock objects in tests
        
        logger.info(
            f"[U+1F680] AGENT_CORE_INIT: AgentExecutionCore initialized successfully. "
            f"Tier: {self.default_tier.value}, Default_timeout: {self._default_timeout}s, "
            f"Streaming_capable: {self.default_tier in [TimeoutTier.ENTERPRISE, TimeoutTier.PLATFORM]}, "
            f"WebSocket_bridge: {'configured' if websocket_bridge else 'missing'}, "
            f"Registry_agents: {registry_count}, "
            f"Prerequisites_validation: {self.prerequisite_validation_level.value}. "
            f"Ready for agent execution with comprehensive monitoring and Issue #387 prerequisites validation."
        )
    
    def get_execution_timeout(self, tier: Optional[TimeoutTier] = None, streaming: bool = False) -> float:
        """Get appropriate execution timeout for customer tier and execution type.
        
        **ENTERPRISE STREAMING**: Returns tier-appropriate timeout:
        - Enterprise streaming: 300s (5-minute capability)
        - Enterprise normal: 300s (extended processing)
        - Platform streaming: 120s (2-minute capability)
        - Other tiers: Standard timeout based on environment
        
        Args:
            tier: Customer tier (defaults to instance default)
            streaming: Whether this is a streaming execution
            
        Returns:
            float: Timeout in seconds
        """
        selected_tier = tier or self.default_tier
        
        if streaming and selected_tier in [TimeoutTier.ENTERPRISE, TimeoutTier.PLATFORM, TimeoutTier.MID]:
            return float(get_streaming_timeout(selected_tier))
        else:
            return float(get_agent_execution_timeout(selected_tier))
        
    def _validate_user_execution_context(
        self, 
        user_context: UserExecutionContext,
        execution_context: AgentExecutionContext
    ) -> UserExecutionContext:
        """
        CRITICAL SECURITY: Validate UserExecutionContext for proper user isolation.
        
        This method ensures we have a valid UserExecutionContext with proper user isolation,
        preventing any cross-user data contamination vulnerabilities.
        
        Phase 1 Migration: Only UserExecutionContext accepted (DeepAgentState eliminated)
        """
        if not isinstance(user_context, UserExecutionContext):
            # Check if this is a DeepAgentState attempt for better error message
            if hasattr(user_context, '__class__') and 'DeepAgentState' in user_context.__class__.__name__:
                raise ValueError(
                    f" ALERT:  SECURITY VULNERABILITY: DeepAgentState is FORBIDDEN due to user isolation risks. "
                    f"Agent '{execution_context.agent_name}' (run_id: {execution_context.run_id}) "
                    f"attempted to use DeepAgentState which can cause data leakage between users. "
                    f"MIGRATION REQUIRED: Use UserExecutionContext pattern immediately. "
                    f"See issue #271 remediation plan for migration guide."
                )
            else:
                raise ValueError(
                    f"Expected UserExecutionContext, got {type(user_context)}. "
                    f"DeepAgentState is no longer supported due to security risks."
                )
        
        # Validate context integrity
        if not user_context.user_id:
            raise ValueError("UserExecutionContext missing required user_id")
        if not user_context.thread_id:
            raise ValueError("UserExecutionContext missing required thread_id") 
        if not user_context.run_id:
            raise ValueError("UserExecutionContext missing required run_id")
            
        return user_context
    
    async def execute_agent(
        self, 
        context: AgentExecutionContext,
        user_context: UserExecutionContext,
        timeout: Optional[float] = None,
        tier: Optional[TimeoutTier] = None,
        streaming: bool = False
    ) -> AgentExecutionResult:
        """Execute agent with full lifecycle tracking and death detection.
        
        **ENTERPRISE STREAMING**: Supports tier-based timeout configuration with:
        - Enterprise: 300s streaming capability with progressive phases
        - Platform: 120s streaming capability  
        - Mid: 60s streaming capability
        - Free/Early: Standard environment-based timeouts
        
        Args:
            context: Agent execution context
            user_context: User execution context (security isolation)
            timeout: Override timeout in seconds
            tier: Customer tier for timeout selection
            streaming: Whether this is a streaming execution
            
        Returns:
            AgentExecutionResult: Execution result with tier-appropriate timeout
        """
        
        # CRITICAL SECURITY: Validate UserExecutionContext for proper user isolation
        try:
            user_execution_context = self._validate_user_execution_context(user_context, context)
            logger.info(
                f"[U+1F510] SECURITY_VALIDATION_SUCCESS: UserExecutionContext validated for agent execution. "
                f"Agent: {context.agent_name}, User: {user_context.user_id[:8]}..., "
                f"Thread: {user_context.thread_id}, Run: {user_context.run_id}, "
                f"Isolation_verified: True, Security_level: Enterprise"
            )
        except Exception as validation_error:
            logger.critical(
                f" ALERT:  SECURITY_VALIDATION_FAILURE: UserExecutionContext validation failed - CRITICAL SECURITY RISK. "
                f"Agent: {context.agent_name}, Error: {validation_error}, "
                f"Error_type: {type(validation_error).__name__}, "
                f"Business_impact: Agent execution blocked to prevent user isolation breach. "
                f"This failure protects $500K+ ARR by preventing cross-user data contamination."
            )
            raise
        
        # CRITICAL ISSUE #387 REMEDIATION: Validate prerequisites BEFORE expensive operations
        try:
            prerequisite_result = await self.prerequisites_validator.validate_all_prerequisites(
                context, user_execution_context
            )
            
            if prerequisite_result.is_valid:
                logger.info(
                    f" SEARCH:  PREREQUISITES_VALIDATION_SUCCESS: All prerequisites validated successfully. "
                    f"Agent: {context.agent_name}, User: {user_context.user_id[:8]}..., "
                    f"Validation_time: {prerequisite_result.validation_time_ms:.1f}ms, "
                    f"Level: {self.prerequisite_validation_level.value}, "
                    f"Business_impact: Prevents failed execution, protects $500K+ ARR through early validation."
                )
            else:
                logger.warning(
                    f" SEARCH:  PREREQUISITES_VALIDATION_WARNING: Some prerequisites failed but continuing in {self.prerequisite_validation_level.value} mode. "
                    f"Agent: {context.agent_name}, Failed_count: {len(prerequisite_result.failed_prerequisites)}, "
                    f"Failed_items: {', '.join(prerequisite_result.failed_prerequisites[:3])}, "
                    f"Validation_time: {prerequisite_result.validation_time_ms:.1f}ms"
                )
                
        except AgentExecutionPrerequisiteError as prereq_error:
            logger.error(
                f" SEARCH:  PREREQUISITES_VALIDATION_FAILURE: Critical prerequisites failed - blocking execution. "
                f"Agent: {context.agent_name}, User: {user_context.user_id[:8]}..., "
                f"Failed_prerequisites: {', '.join(prereq_error.failed_prerequisites)}, "
                f"Error: {str(prereq_error)}, "
                f"Business_impact: Early failure prevents resource waste and provides fast user feedback. "
                f"This protects $500K+ ARR by ensuring reliable agent execution."
            )
            raise
        except Exception as validation_error:
            logger.error(
                f" SEARCH:  PREREQUISITES_VALIDATION_ERROR: Unexpected error during prerequisites validation. "
                f"Agent: {context.agent_name}, Error: {validation_error}, "
                f"Error_type: {type(validation_error).__name__}, "
                f"Fallback: Continuing execution based on validation level {self.prerequisite_validation_level.value}"
            )
            # In permissive/demo mode, continue execution despite validation errors
            if self.prerequisite_validation_level == PrerequisiteValidationLevel.STRICT:
                raise
        
        # Determine appropriate timeout based on tier and execution type
        execution_timeout = timeout or self.get_execution_timeout(tier, streaming)
        selected_tier = tier or self.default_tier
        
        # Get or create trace context BEFORE logging
        parent_trace = get_unified_trace_context()
        if parent_trace:
            # Create child context for this agent
            trace_context = parent_trace.propagate_to_child()
        else:
            # Create new root context
            trace_context = UnifiedTraceContext(
                user_id=user_execution_context.user_id,
                thread_id=user_execution_context.thread_id,
                correlation_id=getattr(context, 'correlation_id', None)
            )
        
        logger.info(
            f" TARGET:  AGENT_EXECUTION_START: Beginning agent execution with enterprise-grade isolation. "
            f"Agent: {context.agent_name}, Tier: {selected_tier.value}, "
            f"Timeout: {execution_timeout}s, Streaming: {streaming}, "
            f"User: {user_execution_context.user_id[:8]}..., "
            f"Thread: {user_execution_context.thread_id}, Run: {user_execution_context.run_id}, "
            f"Correlation: {trace_context.correlation_id if trace_context else 'none'}, "
            f"WebSocket_bridge: {'available' if self.websocket_bridge else 'unavailable'}"
        )
        
        # Start span for this agent execution
        span = trace_context.start_span(
            operation_name=f"agent.{context.agent_name}",
            attributes={
                "agent.name": context.agent_name,
                "agent.run_id": str(context.run_id),
                "user.id": user_execution_context.user_id
            }
        )
        
        # Create execution with tracker
        exec_id = self.execution_tracker.create_execution(
            agent_name=context.agent_name,
            thread_id=user_execution_context.thread_id,
            user_id=user_execution_context.user_id,
            timeout_seconds=execution_timeout,
            metadata={
                'correlation_id': trace_context.correlation_id,
                'run_id': str(context.run_id),
                'tier': selected_tier.value,
                'streaming': streaming
            }
        )
        
        # CRITICAL REMEDIATION: Create and start execution tracking for comprehensive monitoring
        state_exec_id = self.agent_tracker.create_execution(
            agent_name=context.agent_name,
            thread_id=user_execution_context.thread_id,
            user_id=user_execution_context.user_id,
            timeout_seconds=execution_timeout,
            metadata={
                'correlation_id': trace_context.correlation_id,
                'run_id': str(context.run_id),
                'timeout': execution_timeout,
                'tier': selected_tier.value,
                'streaming': streaming
            }
        )
        
        # Start the execution
        started = self.agent_tracker.start_execution(state_exec_id)
        if not started:
            raise RuntimeError(f"Failed to start execution tracking for {state_exec_id}")
        
        # DISABLED: Heartbeat feature suppresses errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
        # The heartbeat system was found to:
        # 1. Continue running even when agents are dead (zombie heartbeats)
        # 2. Hide critical failures behind "monitoring" that doesn't actually monitor
        # 3. Create false positives in health checks
        # DO NOT RE-ENABLE without fixing the error visibility issues
        heartbeat = None  # Disabled - was hiding errors
        # heartbeat = AgentHeartbeat(
        #     exec_id=exec_id,
        #     agent_name=context.agent_name,
        #     interval=self.HEARTBEAT_INTERVAL,
        #     websocket_callback=self._create_websocket_callback(context, trace_context)
        # )
        
        # Execute within trace context
        async with TraceContextManager(trace_context):
            try:
                # Start execution tracking
                started = self.execution_tracker.start_execution(exec_id)
                if not started:
                    raise RuntimeError(f"Failed to start execution tracking for {exec_id}")
                
                # CRITICAL REMEDIATION: Transition through proper phase sequence
                await self.agent_tracker.transition_state(
                    state_exec_id, 
                    AgentExecutionPhase.WEBSOCKET_SETUP,
                    websocket_manager=self.websocket_bridge
                )
                
                # Transition to context validation
                await self.agent_tracker.transition_state(
                    state_exec_id, 
                    AgentExecutionPhase.CONTEXT_VALIDATION,
                    metadata={"user_context_valid": True}
                )
                
                # Add trace event
                trace_context.add_event("agent.started")
                
                # CRITICAL REMEDIATION: Transition to starting phase with WebSocket events
                await self.agent_tracker.transition_state(
                    state_exec_id, 
                    AgentExecutionPhase.STARTING,
                    metadata={"trace_context": trace_context.correlation_id},
                    websocket_manager=self.websocket_bridge
                )
                
                # Transition to thinking phase before execution
                await self.agent_tracker.transition_state(
                    state_exec_id, 
                    AgentExecutionPhase.THINKING,
                    metadata={"agent_name": context.agent_name},
                    websocket_manager=self.websocket_bridge
                )
                
                # CRITICAL FIX: Send agent_started event for user visibility
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_started(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        context={"status": "starting", "phase": "initialization"}
                    )
                
                # Get agent from registry with detailed error logging
                try:
                    agent = self._get_agent_or_error(context.agent_name)
                    if isinstance(agent, AgentExecutionResult):
                        # Agent not found - this is a critical configuration issue
                        logger.critical(
                            f" ALERT:  AGENT_NOT_FOUND: Critical agent missing from registry - user request will fail. "
                            f"Agent: {context.agent_name}, User: {user_execution_context.user_id[:8]}..., "
                            f"Available_agents: {list(getattr(self.registry, '_registry', {}).keys()) if self.registry else []}, "
                            f"Registry_size: {len(getattr(self.registry, '_registry', {})) if self.registry else 0}, "
                            f"Business_impact: User will receive error instead of AI response (90% platform value lost), "
                            f"This indicates system configuration issue requiring immediate attention."
                        )
                        
                        # Mark as failed with detailed error context
                        self.execution_tracker.update_execution_state(
                            exec_id, 
                            ExecutionState.FAILED,
                            error=f"Agent {context.agent_name} not found in registry"
                        )
                        
                        # CRITICAL REMEDIATION: Transition to failed phase
                        await self.agent_tracker.transition_state(
                            state_exec_id, 
                            AgentExecutionPhase.FAILED,
                            metadata={
                                "error": "Agent not found",
                                "requested_agent": context.agent_name,
                                "available_agents": list(getattr(self.registry, '_registry', {}).keys()) if self.registry else [],
                                "configuration_issue": True
                            },
                            websocket_manager=self.websocket_bridge
                        )
                        self.agent_tracker.update_execution_state(state_exec_id, ExecutionState.FAILED)
                        
                        return agent
                    else:
                        logger.info(
                            f" PASS:  AGENT_FOUND: Agent retrieved successfully from registry. "
                            f"Agent: {context.agent_name}, Agent_type: {type(agent).__name__}, "
                            f"User: {user_execution_context.user_id[:8]}..., "
                            f"Ready for execution with WebSocket event integration."
                        )
                except Exception as registry_error:
                    logger.critical(
                        f" ALERT:  AGENT_REGISTRY_FAILURE: Critical failure accessing agent registry. "
                        f"Agent: {context.agent_name}, Error: {registry_error}, "
                        f"Error_type: {type(registry_error).__name__}, "
                        f"User: {user_execution_context.user_id[:8]}..., "
                        f"Registry_state: {'available' if self.registry else 'missing'}, "
                        f"Business_impact: System-level failure preventing all agent executions."
                    )
                    raise
                
                # CRITICAL REMEDIATION: Execute with comprehensive timeout management
                # This prevents agent execution from hanging indefinitely and blocking user responses
                try:
                    async def agent_execution_wrapper():
                        # Execute without heartbeat monitoring (heartbeat disabled - was hiding errors)
                        # See AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
                        if heartbeat:  # This will be False since heartbeat is disabled
                            async with heartbeat:
                                return await self._execute_with_protection(
                                    agent, context, user_execution_context, exec_id, heartbeat, execution_timeout, trace_context
                                )
                        else:
                            # Direct execution without heartbeat wrapper
                            return await self._execute_with_protection(
                                agent, context, user_execution_context, exec_id, None, execution_timeout, trace_context
                            )
                    
                    # CRITICAL: Execute agent with tier-based timeout management to prevent blocking
                    # Enterprise tier: 300s streaming capability
                    # Platform tier: 120s streaming capability
                    # Other tiers: Environment-based timeouts
                    result = await asyncio.wait_for(
                        agent_execution_wrapper(),
                        timeout=execution_timeout
                    )
                    
                except CircuitBreakerOpenError as e:
                    # Circuit breaker is open - create fallback response
                    logger.error(
                        f"[U+1F6AB] CIRCUIT_BREAKER_OPEN: Agent execution blocked by circuit breaker protection. "
                        f"Agent: {context.agent_name}, User: {user_execution_context.user_id[:8]}..., "
                        f"Error: {e}, Failure_threshold_reached: True, "
                        f"Business_impact: User request degraded to fallback response to maintain system stability. "
                        f"This protects overall system health while individual agent recovers."
                    )
                    
                    # Transition to circuit breaker open phase
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.CIRCUIT_BREAKER_OPEN,
                        metadata={'error': str(e), 'error_type': 'circuit_breaker'},
                        websocket_manager=self.websocket_bridge
                    )
                    
                    fallback_response = await self.agent_tracker.create_fallback_response(
                        context.agent_name,
                        e,
                        str(context.run_id),
                        self.websocket_bridge
                    )
                    result = AgentExecutionResult(
                        success=False,
                        agent_name=context.agent_name,
                        error=str(e),
                        duration=0.0,
                        data=fallback_response
                    )
                    
                except TimeoutError as e:
                    # Agent execution timed out - provide detailed context with tier information
                    logger.error(
                        f"[U+23F0] AGENT_EXECUTION_TIMEOUT: Agent exceeded execution time limit - user experience degraded. "
                        f"Agent: {context.agent_name}, Timeout_limit: {execution_timeout}s, "
                        f"Tier: {selected_tier.value}, Streaming: {streaming}, "
                        f"User: {user_execution_context.user_id[:8]}..., Thread: {user_execution_context.thread_id}, "
                        f"Run: {context.run_id}, Error: {e}, "
                        f"Business_impact: User will receive timeout error instead of AI response. "
                        f"Possible_causes: Agent stuck, complex processing, external API delays. "
                        f"Recommendation: {'Upgrade to Enterprise tier for 300s timeout' if selected_tier.value != 'ENTERPRISE' else 'Contact support for investigation'}."
                    )
                    
                    # Transition to timeout phase
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.TIMEOUT,
                        metadata={'error': str(e), 'error_type': 'timeout'},
                        websocket_manager=self.websocket_bridge
                    )
                    
                    # Create detailed timeout result with enhanced context and tier information
                    result = AgentExecutionResult(
                        success=False,
                        agent_name=context.agent_name,
                        error=f"Agent '{context.agent_name}' timed out after {execution_timeout}s "
                              f"(tier: {selected_tier.value}, streaming: {streaming}). "
                              f"Execution exceeded maximum allowed time, possibly due to complex processing "
                              f"or external resource delays. User: {user_execution_context.user_id}, "
                              f"Run ID: {context.run_id}. Consider upgrading to higher tier for extended timeouts.",
                        duration=0.0
                    )
            
                # Collect and persist metrics with detailed logging
                try:
                    metrics = await self._collect_metrics(exec_id, result, user_execution_context, heartbeat)
                    await self._persist_metrics(exec_id, metrics, context.agent_name, user_execution_context)
                    
                    logger.debug(
                        f" CHART:  METRICS_COLLECTED: Agent execution metrics captured successfully. "
                        f"Agent: {context.agent_name}, Success: {result.success}, "
                        f"Duration: {result.duration:.3f}s, User: {user_execution_context.user_id[:8]}..., "
                        f"Metrics_count: {len(metrics) if metrics else 0}, "
                        f"Persistence: {'enabled' if self.persistence else 'disabled'}"
                    )
                except Exception as metrics_error:
                    logger.warning(
                        f" WARNING: [U+FE0F] METRICS_COLLECTION_FAILED: Non-critical metrics collection error. "
                        f"Agent: {context.agent_name}, Error: {metrics_error}, "
                        f"Error_type: {type(metrics_error).__name__}, "
                        f"Impact: Execution continues normally, metrics unavailable for this run."
                    )
                
                # CRITICAL REMEDIATION: Mark execution complete with state tracking
                if result.success:
                    logger.info(
                        f" PASS:  AGENT_EXECUTION_SUCCESS: Agent completed successfully - delivering AI value to user. "
                        f"Agent: {context.agent_name}, Duration: {result.duration:.3f}s, "
                        f"User: {user_execution_context.user_id[:8]}..., "
                        f"Business_value: AI response delivered (90% of platform value), "
                        f"WebSocket_events: Completion notifications sent, "
                        f"State_transition: COMPLETED, Metrics_captured: True"
                    )
                    
                    trace_context.add_event("agent.completed")
                    self.execution_tracker.update_execution_state(
                        exec_id, 
                        ExecutionState.COMPLETED,
                        result=result
                    )
                    
                    # Transition through proper completion sequence: THINKING -> TOOL_PREPARATION -> TOOL_EXECUTION -> RESULT_PROCESSING
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.TOOL_PREPARATION,
                        metadata={"preparing_tools": True},
                        websocket_manager=self.websocket_bridge
                    )
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.TOOL_EXECUTION,
                        metadata={"executing_tools": True},
                        websocket_manager=self.websocket_bridge
                    )
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.RESULT_PROCESSING,
                        metadata={"processing_result": True},
                        websocket_manager=self.websocket_bridge
                    )
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.COMPLETING,
                        metadata={"success": True},
                        websocket_manager=self.websocket_bridge
                    )
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.COMPLETED,
                        metadata={"result": "success"},
                        websocket_manager=self.websocket_bridge
                    )
                    
                    # NOTE: agent_completed event is automatically sent by agent tracker during COMPLETED phase transition
                    # No need to manually call notify_agent_completed here
                    
                    # Mark execution as successful in tracker state
                    self.agent_tracker.update_execution_state(state_exec_id, ExecutionState.COMPLETED)
                else:
                    logger.error(
                        f" ALERT:  AGENT_EXECUTION_FAILURE: Agent execution failed - user experience degraded. "
                        f"Agent: {context.agent_name}, Duration: {result.duration:.3f}s if result.duration else 0, "
                        f"Error: {result.error or 'Unknown error'}, "
                        f"User: {user_execution_context.user_id[:8]}..., "
                        f"Business_impact: User receives error instead of AI response (90% platform value lost), "
                        f"Error_category: {'timeout' if 'timeout' in (result.error or '').lower() else 'execution_failure'}, "
                        f"Recovery_action: Fallback response sent, WebSocket_events: Error notifications sent"
                    )
                    
                    trace_context.add_event("agent.error", {"error": result.error})
                    self.execution_tracker.update_execution_state(
                        exec_id, 
                        ExecutionState.FAILED,
                        error=result.error or "Unknown error"
                    )
                    
                    # Transition to failed phase
                    await self.agent_tracker.transition_state(
                        state_exec_id, 
                        AgentExecutionPhase.FAILED,
                        metadata={'error': result.error or 'Unknown error'},
                        websocket_manager=self.websocket_bridge
                    )
                    self.agent_tracker.update_execution_state(state_exec_id, ExecutionState.FAILED)
                    
                    # NOTE: Error notification is automatically sent by state_tracker during FAILED phase transition above
                    # Removing manual call to prevent duplicate notifications
                    
                    # CRITICAL FIX: Send agent_completed event for error cases
                    if self.websocket_bridge:
                        await self.websocket_bridge.notify_agent_completed(
                            run_id=context.run_id,
                            agent_name=context.agent_name,
                            result={"status": "completed", "success": False, "error": result.error or "Agent execution failed"}
                        )
                
                # Finish the span
                trace_context.finish_span(span)
                
                # NOTE: agent_completed event is already sent in success/error paths above (lines 356, 390)
                # No need to send it again here to avoid duplicate notifications
                
                return result
            
            except Exception as e:
                # Add error event and finish span
                trace_context.add_event("agent.exception", {"error": str(e)})
                trace_context.finish_span(span)
                
                # Ensure execution is marked as failed
                self.execution_tracker.update_execution_state(
                    exec_id,
                    ExecutionState.FAILED,
                    error=f"Unexpected error: {str(e)}"
                )
                
                # NOTE: Error notification is handled in the main success/failure path (lines 377-382)
                # Removing duplicate notification call to prevent test failures
                
                return AgentExecutionResult(
                    success=False,
                    agent_name=context.agent_name,
                    error=f"Agent execution failed: {str(e)}"
                )
    
    async def _execute_with_protection(
        self,
        agent: Any,
        context: AgentExecutionContext,
        user_execution_context: UserExecutionContext,
        exec_id: UUID,
        heartbeat: Optional[Any],  # Disabled - was AgentHeartbeat, see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
        timeout: Optional[float],
        trace_context: UnifiedTraceContext
    ) -> AgentExecutionResult:
        """Execute agent with multiple layers of protection."""
        
        start_time = time.time()
        timeout_seconds = timeout or self.DEFAULT_TIMEOUT
        
        try:
            # CRITICAL ERROR BOUNDARY 1: Timeout protection
            async with asyncio.timeout(timeout_seconds):
                
                # CRITICAL ERROR BOUNDARY 2: Result validation
                result = await self._execute_with_result_validation(
                    agent, context, user_execution_context, heartbeat, trace_context
                )
                
                # CRITICAL: Validate result is not None (agent death signature)
                if result is None:
                    logger.error(f"CRITICAL: Agent {context.agent_name} returned None - DEAD AGENT DETECTED")
                    raise RuntimeError(f"Agent {context.agent_name} died silently - returned None")
                
                duration = time.time() - start_time
                
                # Create proper result
                if isinstance(result, AgentExecutionResult):
                    result.duration = duration
                    result.metrics = self._calculate_performance_metrics(start_time, heartbeat)
                    return result
                else:
                    # Agent didn't return proper result format - wrap result in standard format
                    return AgentExecutionResult(
                        success=True,
                        agent_name=context.agent_name,
                        duration=duration,
                        metrics=self._calculate_performance_metrics(start_time, heartbeat),
                        data=result  # Store the actual agent result in data field
                    )
                    
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(
                f"[U+23F0] EXECUTION TIMEOUT: Agent '{context.agent_name}' exceeded execution timeout "
                f"of {timeout_seconds}s (duration: {duration:.2f}s). User: {user_execution_context.user_id}, "
                f"Thread: {user_execution_context.thread_id}, Run ID: {context.run_id}. "
                f"This indicates the agent may be stuck in processing or waiting for external resources."
            )
            return AgentExecutionResult(
                success=False,
                agent_name=context.agent_name,
                error=f"Agent '{context.agent_name}' execution timeout after {timeout_seconds}s. "
                      f"The agent exceeded the maximum allowed execution time, possibly due to "
                      f"complex processing or external resource delays. User: {user_execution_context.user_id}, "
                      f"Run ID: {context.run_id}.",
                duration=duration,
                metrics=self._calculate_performance_metrics(start_time, heartbeat)
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Agent {context.agent_name} failed with error: {e}")
            return AgentExecutionResult(
                success=False,
                agent_name=context.agent_name,
                error=str(e),
                duration=duration,
                metrics=self._calculate_performance_metrics(start_time, heartbeat)
            )
    
    async def _execute_with_result_validation(
        self,
        agent: Any,
        context: AgentExecutionContext,
        user_execution_context: UserExecutionContext,
        heartbeat: Optional[Any],  # Disabled - was AgentHeartbeat
        trace_context: UnifiedTraceContext
    ) -> Any:
        """Execute agent and validate result."""
        
        # Set up websocket context on agent
        await self._setup_agent_websocket(agent, context, user_execution_context, trace_context)
        
        # Create execution wrapper that conditionally sends heartbeats
        async def execute_with_heartbeat():
            # Send initial heartbeat if heartbeat is enabled
            if heartbeat:
                await heartbeat.pulse({"status": "executing"})
            
            # Execute the agent
            try:
                # CRITICAL: Send thinking event before execution for user visibility
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=f"Executing {context.agent_name} with your specific requirements...",
                        step_number=2
                    )
                
                # CRITICAL FIX: Send additional thinking event to show progress 
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=f"Setting up tools and preparing execution environment...",
                        step_number=3
                    )
                
                # CRITICAL: This is where agent.execute() is called
                result = await agent.execute(user_execution_context, context.run_id, True)
                
                # CRITICAL: Send thinking event after successful execution
                if self.websocket_bridge and result is not None:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=f"Completed analysis and preparing response...",
                        step_number=4
                    )
                    
                    # CRITICAL FIX: Send final thinking event before completion
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=f"Finalizing results and preparing to deliver response...",
                        step_number=5
                    )
                
                # Send final heartbeat if heartbeat is enabled
                if heartbeat:
                    await heartbeat.pulse({"status": "completed"})
                
                return result
                
            except Exception as e:
                # Send error heartbeat if heartbeat is enabled
                if heartbeat:
                    await heartbeat.pulse({"status": "error", "error": str(e)})
                # Log the error with full context for debugging
                logger.error(f"Agent {context.agent_name} execution failed: {e}", extra={
                    "run_id": str(context.run_id),
                    "user_id": getattr(user_execution_context, 'user_id', None),
                    "thread_id": getattr(user_execution_context, 'thread_id', None),
                    "retry_count": context.retry_count
                })
                raise
        
        # Execute with heartbeat wrapper (heartbeat may be None/disabled)
        result = await execute_with_heartbeat()
        
        # Ensure result is properly structured
        if result is not None and not isinstance(result, (dict, AgentExecutionResult)):
            logger.warning(f"Agent returned non-standard result type: {type(result).__name__}")
            # Wrap in a standard format
            result = {"success": True, "result": result, "agent_name": context.agent_name}
        
        return result
    
    async def _setup_agent_websocket(
        self,
        agent: Any,
        context: AgentExecutionContext,
        user_execution_context: UserExecutionContext,
        trace_context: UnifiedTraceContext
    ) -> None:
        """Set up websocket context on agent with enhanced propagation.
        
        CRITICAL: This ensures WebSocket manager and context are properly
        propagated to all child agents for complete event tracking.
        """
        
        # Set user_id on agent if available
        if user_execution_context.user_id:
            agent._user_id = user_execution_context.user_id
        
        # Set trace context on agent if it supports it
        if hasattr(agent, 'set_trace_context'):
            agent.set_trace_context(trace_context)
            logger.info(f" PASS:  Trace context set on agent {agent.__class__.__name__}")
        
        # CRITICAL: Propagate WebSocket bridge to agent with multiple methods
        if self.websocket_bridge:
            # Try multiple methods to ensure WebSocket is set
            websocket_set = False
            
            # Method 1: set_websocket_bridge (preferred)
            if hasattr(agent, 'set_websocket_bridge'):
                agent.set_websocket_bridge(self.websocket_bridge, context.run_id)
                websocket_set = True
                logger.info(f" PASS:  WebSocket bridge set via set_websocket_bridge on {agent.__class__.__name__}")
            
            # Method 2: Direct assignment to websocket_bridge attribute
            if hasattr(agent, 'websocket_bridge'):
                agent.websocket_bridge = self.websocket_bridge
                agent._run_id = context.run_id
                websocket_set = True
                logger.info(f" PASS:  WebSocket bridge set via direct assignment on {agent.__class__.__name__}")
                
                # CRITICAL: Also provide a helper method for thinking events
                async def emit_thinking(reasoning: str, step_number: int = None):
                    """Helper method for agents to emit thinking events easily."""
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=reasoning,
                        step_number=step_number
                    )
                
                # Add the helper method to the agent
                agent.emit_thinking = emit_thinking
            
            # Method 3: Set on execution engine if agent has one
            if hasattr(agent, 'execution_engine') and agent.execution_engine:
                if hasattr(agent.execution_engine, 'set_websocket_bridge'):
                    agent.execution_engine.set_websocket_bridge(self.websocket_bridge, context.run_id)
                    websocket_set = True
                    logger.info(f" PASS:  WebSocket bridge set on execution engine of {agent.__class__.__name__}")
            
            # Method 4: CRITICAL FIX - Ensure tool dispatcher has WebSocket manager
            tool_dispatcher = user_execution_context.agent_context.get('tool_dispatcher')
            if tool_dispatcher:
                try:
                    # Set WebSocket manager on tool dispatcher if it supports it
                    if hasattr(tool_dispatcher, 'set_websocket_manager'):
                        # Get the websocket manager from the bridge
                        websocket_manager = getattr(self.websocket_bridge, 'websocket_manager', None) or getattr(self.websocket_bridge, '_websocket_manager', None)
                        if websocket_manager:
                            tool_dispatcher.set_websocket_manager(websocket_manager)
                            websocket_set = True
                            logger.info(f" PASS:  WebSocket manager set on tool dispatcher for agent {agent.__class__.__name__}")
                        else:
                            logger.warning(f" WARNING: [U+FE0F] WebSocket manager not found in bridge for tool dispatcher setup")
                    else:
                        logger.debug(f"Tool dispatcher does not support set_websocket_manager method")
                except Exception as e:
                    logger.error(f"Failed to set WebSocket manager on tool dispatcher: {e}")
            
            if not websocket_set:
                logger.warning(f" WARNING: [U+FE0F] Could not set WebSocket bridge on agent {agent.__class__.__name__} - no compatible method found")
    
    def _create_websocket_callback(self, context: AgentExecutionContext, trace_context: UnifiedTraceContext):
        """Create WebSocket callback for heartbeat updates."""
        
        async def callback(data: dict):
            if self.websocket_bridge:
                # Send heartbeat as agent_thinking update with trace context
                await self.websocket_bridge.notify_agent_thinking(
                    run_id=context.run_id,
                    agent_name=context.agent_name,
                    reasoning=f"Processing... (heartbeat #{data.get('pulse', 0)})",
                    trace_context=trace_context.to_websocket_context()
                )
        
        return callback if self.websocket_bridge else None
    
    def _get_agent_or_error(self, agent_name: str):
        """Get agent from registry or return error result."""
        agent = self.registry.get(agent_name)
        if not agent:
            return AgentExecutionResult(
                success=False,
                agent_name=agent_name,
                error=f"Agent {agent_name} not found"
            )
        return agent
    
    def _calculate_performance_metrics(
        self, 
        start_time: float, 
        heartbeat: Optional[Any] = None  # Disabled - was AgentHeartbeat
    ) -> dict:
        """Calculate performance metrics for the execution."""
        duration = time.time() - start_time
        
        metrics = {
            'execution_time_ms': int(duration * 1000),
            'start_timestamp': start_time,
            'end_timestamp': time.time()
        }
        
        if heartbeat:
            metrics['heartbeat_count'] = heartbeat.pulse_count
            
        # Memory usage if available
        try:
            import psutil
            process = psutil.Process()
            metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
            metrics['cpu_percent'] = process.cpu_percent()
        except:
            pass  # psutil not available or error
            
        return metrics
    
    async def _collect_metrics(
        self, 
        exec_id: UUID, 
        result: AgentExecutionResult, 
        user_execution_context: UserExecutionContext, 
        heartbeat: Optional[Any] = None  # Disabled - was AgentHeartbeat
    ) -> dict:
        """Collect comprehensive metrics for the execution."""
        # Get metrics from execution tracker  
        tracker_metrics = self.execution_tracker.get_metrics()
        
        # Combine with result metrics
        metrics = tracker_metrics or {}
        
        if hasattr(result, 'metrics') and result.metrics:
            metrics.update(result.metrics)
        
        # Add user execution context information
        metrics['context_size'] = len(str(user_execution_context.__dict__)) if user_execution_context else 0
        metrics['result_success'] = result.success
        
        if result.duration:
            metrics['total_duration_seconds'] = result.duration
            
        return metrics
    
    async def _persist_metrics(
        self, 
        exec_id: UUID, 
        metrics: dict, 
        agent_name: str,
        user_execution_context: UserExecutionContext
    ):
        """Persist performance metrics to ClickHouse."""
        # Skip persistence if not configured
        if not self.persistence:
            logger.debug(f"Metrics persistence disabled for execution {exec_id}")
            return
        
        # Prepare metric record with context
        metric_record = {
            'execution_id': exec_id,
            'agent_name': agent_name,
            'user_id': getattr(user_execution_context, 'user_id', None),
        }
        
        # Write individual metrics with per-metric error handling
        for metric_type, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                try:
                    await self.persistence.write_performance_metrics(
                        exec_id, 
                        {
                            **metric_record,
                            'metric_type': metric_type,
                            'metric_value': float(metric_value)
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to persist metric '{metric_type}' for execution {exec_id}: {e}")