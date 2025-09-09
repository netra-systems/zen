"""Core agent execution with death detection and recovery.

CRITICAL: This module adds execution tracking, heartbeat monitoring, and error boundaries
to prevent silent agent deaths.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.state import DeepAgentState
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

logger = central_logger.get_logger(__name__)


class AgentExecutionCore:
    """Enhanced agent execution with death detection and recovery."""
    
    # Timeout configuration
    DEFAULT_TIMEOUT = 30.0  # 30 seconds default
    HEARTBEAT_INTERVAL = 5.0  # Send heartbeat every 5 seconds
    
    def __init__(self, registry: 'AgentRegistry', websocket_bridge: Optional['AgentWebSocketBridge'] = None):
        self.registry = registry
        self.websocket_bridge = websocket_bridge
        self.execution_tracker = get_execution_tracker()
        # trace_persistence removed - no longer needed
        self.persistence = None
        
    async def execute_agent(
        self, 
        context: AgentExecutionContext,
        state: DeepAgentState,
        timeout: Optional[float] = None
    ) -> AgentExecutionResult:
        """Execute agent with full lifecycle tracking and death detection."""
        
        # Get or create trace context
        parent_trace = get_unified_trace_context()
        if parent_trace:
            # Create child context for this agent
            trace_context = parent_trace.propagate_to_child()
        else:
            # Create new root context
            trace_context = UnifiedTraceContext(
                user_id=getattr(state, 'user_id', None),
                thread_id=getattr(state, 'thread_id', None),
                correlation_id=getattr(context, 'correlation_id', None)
            )
        
        # Start span for this agent execution
        span = trace_context.start_span(
            operation_name=f"agent.{context.agent_name}",
            attributes={
                "agent.name": context.agent_name,
                "agent.run_id": str(context.run_id),
                "user.id": getattr(state, 'user_id', None)
            }
        )
        
        # Register execution with tracker
        exec_id = await self.execution_tracker.register_execution(
            agent_name=context.agent_name,
            correlation_id=trace_context.correlation_id,
            thread_id=getattr(state, 'thread_id', None),
            user_id=getattr(state, 'user_id', None),
            timeout_seconds=timeout or self.DEFAULT_TIMEOUT
        )
        
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
                await self.execution_tracker.start_execution(exec_id)
                
                # Add trace event
                trace_context.add_event("agent.started")
                
                # CRITICAL: Send agent_started event for business value and user transparency
                # Business Value: Users must know agent has started working on their problem
                # This is MISSION CRITICAL per CLAUDE.md Section 6 - WebSocket Agent Events
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_started(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        trace_context=trace_context.to_websocket_context()
                    )
                    # CRITICAL: Send agent thinking event for real-time user feedback
                    # Business Value: Users see AI is working on their problem (Trust Building)
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        reasoning=f"Analyzing your request and determining the best approach...",
                        step_number=1
                    )
                
                # Get agent from registry
                agent = self._get_agent_or_error(context.agent_name)
                if isinstance(agent, AgentExecutionResult):
                    # Agent not found - mark as failed
                    await self.execution_tracker.complete_execution(
                        exec_id, 
                        error=f"Agent {context.agent_name} not found"
                    )
                    if self.websocket_bridge:
                        await self.websocket_bridge.notify_agent_error(
                            run_id=context.run_id,
                            agent_name=context.agent_name,
                            error=agent.error or "Agent not found"
                        )
                    return agent
                
                # Execute without heartbeat monitoring (heartbeat disabled - was hiding errors)
                # See AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
                if heartbeat:  # This will be False since heartbeat is disabled
                    async with heartbeat:
                        result = await self._execute_with_protection(
                            agent, context, state, exec_id, heartbeat, timeout, trace_context
                        )
                else:
                    # Direct execution without heartbeat wrapper
                    result = await self._execute_with_protection(
                        agent, context, state, exec_id, None, timeout, trace_context
                    )
            
                # Collect and persist metrics
                metrics = await self._collect_metrics(exec_id, result, state, heartbeat)
                await self._persist_metrics(exec_id, metrics, context.agent_name, state)
                
                # Mark execution complete
                if result.success:
                    trace_context.add_event("agent.completed")
                    await self.execution_tracker.complete_execution(exec_id, result=result)
                else:
                    trace_context.add_event("agent.error", {"error": result.error})
                    await self.execution_tracker.complete_execution(
                        exec_id, 
                        error=result.error or "Unknown error"
                    )
                    
                    # CRITICAL: Send error notification for agent failures including death detection
                    # Business Value: Users must be notified when agent fails or dies silently
                    # This is MISSION CRITICAL per CLAUDE.md Section 6 - WebSocket Agent Events
                    if self.websocket_bridge:
                        await self.websocket_bridge.notify_agent_error(
                            run_id=context.run_id,
                            agent_name=context.agent_name,
                            error=result.error or "Agent execution failed"
                        )
                
                # Finish the span
                trace_context.finish_span(span)
                
                # CRITICAL: Send agent_completed event for business value and user closure
                # Business Value: Users must know when agent has finished working on their problem
                # This is MISSION CRITICAL per CLAUDE.md Section 6 - WebSocket Agent Events
                if self.websocket_bridge and result.success:
                    await self.websocket_bridge.notify_agent_completed(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        result=result.data if hasattr(result, 'data') else {"success": True},
                        execution_time_ms=int((result.duration * 1000) if result.duration else 0)
                    )
                
                return result
            
            except Exception as e:
                # Add error event and finish span
                trace_context.add_event("agent.exception", {"error": str(e)})
                trace_context.finish_span(span)
                
                # Ensure execution is marked as failed
                await self.execution_tracker.complete_execution(
                    exec_id,
                    error=f"Unexpected error: {str(e)}"
                )
                
                # Send error notification with trace context
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_error(
                        run_id=context.run_id,
                        agent_name=context.agent_name,
                        error=str(e),
                        trace_context=trace_context.to_websocket_context()
                    )
                
                return AgentExecutionResult(
                    success=False,
                    agent_name=context.agent_name,
                    error=f"Agent execution failed: {str(e)}"
                )
    
    async def _execute_with_protection(
        self,
        agent: Any,
        context: AgentExecutionContext,
        state: DeepAgentState,
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
                    agent, context, state, heartbeat, trace_context
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
            logger.error(f"Agent {context.agent_name} timed out after {timeout_seconds}s")
            return AgentExecutionResult(
                success=False,
                agent_name=context.agent_name,
                error=f"Agent execution timeout after {timeout_seconds}s",
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
        state: DeepAgentState,
        heartbeat: Optional[Any],  # Disabled - was AgentHeartbeat
        trace_context: UnifiedTraceContext
    ) -> Any:
        """Execute agent and validate result."""
        
        # Set up websocket context on agent
        await self._setup_agent_websocket(agent, context, state, trace_context)
        
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
                result = await agent.execute(state, context.run_id, True)
                
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
                    "user_id": getattr(state, 'user_id', None),
                    "thread_id": getattr(state, 'thread_id', None),
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
        state: DeepAgentState,
        trace_context: UnifiedTraceContext
    ) -> None:
        """Set up websocket context on agent with enhanced propagation.
        
        CRITICAL: This ensures WebSocket manager and context are properly
        propagated to all child agents for complete event tracking.
        """
        
        # Set user_id on agent if available
        if hasattr(state, 'user_id') and state.user_id:
            agent._user_id = state.user_id
        
        # Set trace context on agent if it supports it
        if hasattr(agent, 'set_trace_context'):
            agent.set_trace_context(trace_context)
            logger.info(f"✅ Trace context set on agent {agent.__class__.__name__}")
        
        # CRITICAL: Propagate WebSocket bridge to agent with multiple methods
        if self.websocket_bridge:
            # Try multiple methods to ensure WebSocket is set
            websocket_set = False
            
            # Method 1: set_websocket_bridge (preferred)
            if hasattr(agent, 'set_websocket_bridge'):
                agent.set_websocket_bridge(self.websocket_bridge, context.run_id)
                websocket_set = True
                logger.info(f"✅ WebSocket bridge set via set_websocket_bridge on {agent.__class__.__name__}")
            
            # Method 2: Direct assignment to websocket_bridge attribute
            if hasattr(agent, 'websocket_bridge'):
                agent.websocket_bridge = self.websocket_bridge
                agent._run_id = context.run_id
                websocket_set = True
                logger.info(f"✅ WebSocket bridge set via direct assignment on {agent.__class__.__name__}")
                
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
                    logger.info(f"✅ WebSocket bridge set on execution engine of {agent.__class__.__name__}")
            
            # Method 4: CRITICAL FIX - Ensure tool dispatcher has WebSocket manager
            if hasattr(state, 'tool_dispatcher') and state.tool_dispatcher:
                try:
                    # Set WebSocket manager on tool dispatcher if it supports it
                    if hasattr(state.tool_dispatcher, 'set_websocket_manager'):
                        # Get the websocket manager from the bridge
                        websocket_manager = getattr(self.websocket_bridge, 'websocket_manager', None) or getattr(self.websocket_bridge, '_websocket_manager', None)
                        if websocket_manager:
                            state.tool_dispatcher.set_websocket_manager(websocket_manager)
                            websocket_set = True
                            logger.info(f"✅ WebSocket manager set on tool dispatcher for agent {agent.__class__.__name__}")
                        else:
                            logger.warning(f"⚠️ WebSocket manager not found in bridge for tool dispatcher setup")
                    else:
                        logger.debug(f"Tool dispatcher does not support set_websocket_manager method")
                except Exception as e:
                    logger.error(f"Failed to set WebSocket manager on tool dispatcher: {e}")
            
            if not websocket_set:
                logger.warning(f"⚠️ Could not set WebSocket bridge on agent {agent.__class__.__name__} - no compatible method found")
    
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
        state: DeepAgentState, 
        heartbeat: Optional[Any] = None  # Disabled - was AgentHeartbeat
    ) -> dict:
        """Collect comprehensive metrics for the execution."""
        # Get metrics from execution tracker
        tracker_metrics = await self.execution_tracker.collect_metrics(exec_id)
        
        # Combine with result metrics
        metrics = tracker_metrics or {}
        
        if hasattr(result, 'metrics') and result.metrics:
            metrics.update(result.metrics)
        
        # Add state information
        metrics['state_size'] = len(str(state.__dict__)) if state else 0
        metrics['result_success'] = result.success
        
        if result.duration:
            metrics['total_duration_seconds'] = result.duration
            
        return metrics
    
    async def _persist_metrics(
        self, 
        exec_id: UUID, 
        metrics: dict, 
        agent_name: str,
        state: DeepAgentState
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
            'user_id': getattr(state, 'user_id', None),
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