"""Enhanced core agent execution with death detection and recovery.

CRITICAL: This module adds execution tracking, heartbeat monitoring, and error boundaries
to prevent silent agent deaths.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.core.agent_heartbeat import AgentHeartbeat
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedAgentExecutionCore:
    """Enhanced agent execution with death detection and recovery."""
    
    # Timeout configuration
    DEFAULT_TIMEOUT = 30.0  # 30 seconds default
    HEARTBEAT_INTERVAL = 5.0  # Send heartbeat every 5 seconds
    
    def __init__(self, registry: 'AgentRegistry', websocket_notifier: Optional['WebSocketNotifier'] = None):
        self.registry = registry
        self.websocket_notifier = websocket_notifier
        self.execution_tracker = get_execution_tracker()
        
    async def execute_agent(
        self, 
        context: AgentExecutionContext,
        state: DeepAgentState,
        timeout: Optional[float] = None
    ) -> AgentExecutionResult:
        """Execute agent with full lifecycle tracking and death detection."""
        
        # Register execution with tracker
        exec_id = await self.execution_tracker.register_execution(
            agent_name=context.agent_name,
            correlation_id=getattr(context, 'correlation_id', None),
            thread_id=getattr(state, 'thread_id', None),
            user_id=getattr(state, 'user_id', None),
            timeout_seconds=timeout or self.DEFAULT_TIMEOUT
        )
        
        # Create heartbeat context
        heartbeat = AgentHeartbeat(
            exec_id=exec_id,
            agent_name=context.agent_name,
            interval=self.HEARTBEAT_INTERVAL,
            websocket_callback=self._create_websocket_callback(context)
        )
        
        try:
            # Start execution tracking
            await self.execution_tracker.start_execution(exec_id)
            
            # Send agent started notification
            if self.websocket_notifier:
                await self.websocket_notifier.send_agent_started(context)
            
            # Get agent from registry
            agent = self._get_agent_or_error(context.agent_name)
            if isinstance(agent, AgentExecutionResult):
                # Agent not found - mark as failed
                await self.execution_tracker.complete_execution(
                    exec_id, 
                    error=f"Agent {context.agent_name} not found"
                )
                if self.websocket_notifier:
                    await self.websocket_notifier.send_agent_error(
                        context, agent.error, "agent_not_found"
                    )
                return agent
            
            # Execute with heartbeat monitoring
            async with heartbeat:
                result = await self._execute_with_protection(
                    agent, context, state, exec_id, heartbeat, timeout
                )
            
            # Mark execution complete
            if result.success:
                await self.execution_tracker.complete_execution(exec_id, result=result)
            else:
                await self.execution_tracker.complete_execution(
                    exec_id, 
                    error=result.error or "Unknown error"
                )
            
            # Send completion notification
            if self.websocket_notifier:
                if result.success:
                    await self.websocket_notifier.send_agent_completed(
                        context,
                        {"success": True, "agent_name": context.agent_name},
                        (result.duration * 1000) if result.duration else 0
                    )
                else:
                    await self.websocket_notifier.send_agent_error(
                        context, result.error or "Unknown error", "execution_failure"
                    )
            
            return result
            
        except Exception as e:
            # Ensure execution is marked as failed
            await self.execution_tracker.complete_execution(
                exec_id,
                error=f"Unexpected error: {str(e)}"
            )
            
            # Send error notification
            if self.websocket_notifier:
                await self.websocket_notifier.send_agent_error(
                    context, str(e), "unexpected_error"
                )
            
            return AgentExecutionResult(
                success=False,
                error=f"Agent execution failed: {str(e)}"
            )
    
    async def _execute_with_protection(
        self,
        agent: Any,
        context: AgentExecutionContext,
        state: DeepAgentState,
        exec_id: UUID,
        heartbeat: AgentHeartbeat,
        timeout: Optional[float]
    ) -> AgentExecutionResult:
        """Execute agent with multiple layers of protection."""
        
        start_time = time.time()
        timeout_seconds = timeout or self.DEFAULT_TIMEOUT
        
        try:
            # CRITICAL ERROR BOUNDARY 1: Timeout protection
            async with asyncio.timeout(timeout_seconds):
                
                # CRITICAL ERROR BOUNDARY 2: Result validation
                result = await self._execute_with_result_validation(
                    agent, context, state, heartbeat
                )
                
                # CRITICAL: Validate result is not None (agent death signature)
                if result is None:
                    logger.error(f"CRITICAL: Agent {context.agent_name} returned None - DEAD AGENT DETECTED")
                    raise RuntimeError(f"Agent {context.agent_name} died silently - returned None")
                
                duration = time.time() - start_time
                
                # Create proper result
                if isinstance(result, AgentExecutionResult):
                    return result
                else:
                    # Agent didn't return proper result format
                    return AgentExecutionResult(
                        success=True,
                        state=state,
                        duration=duration
                    )
                    
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"Agent {context.agent_name} timed out after {timeout_seconds}s")
            return AgentExecutionResult(
                success=False,
                error=f"Agent execution timeout after {timeout_seconds}s",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Agent {context.agent_name} failed with error: {e}")
            return AgentExecutionResult(
                success=False,
                error=str(e),
                duration=duration
            )
    
    async def _execute_with_result_validation(
        self,
        agent: Any,
        context: AgentExecutionContext,
        state: DeepAgentState,
        heartbeat: AgentHeartbeat
    ) -> Any:
        """Execute agent and validate result."""
        
        # Set up websocket context on agent
        await self._setup_agent_websocket(agent, context, state)
        
        # Create execution wrapper that sends heartbeats
        async def execute_with_heartbeat():
            # Send initial heartbeat
            await heartbeat.pulse({"status": "executing"})
            
            # Execute the agent
            try:
                # CRITICAL: This is where agent.execute() is called
                result = await agent.execute(state, context.run_id, True)
                
                # Send final heartbeat
                await heartbeat.pulse({"status": "completed"})
                
                return result
                
            except Exception as e:
                # Send error heartbeat
                await heartbeat.pulse({"status": "error", "error": str(e)})
                raise
        
        # Execute with heartbeat wrapper
        return await execute_with_heartbeat()
    
    async def _setup_agent_websocket(
        self,
        agent: Any,
        context: AgentExecutionContext,
        state: DeepAgentState
    ) -> None:
        """Set up websocket context on agent."""
        
        # Set user_id on agent if available
        if hasattr(state, 'user_id') and state.user_id:
            agent._user_id = state.user_id
        
        # Propagate WebSocket context
        if self.websocket_notifier:
            if hasattr(agent, 'set_websocket_context'):
                agent.set_websocket_context(context, self.websocket_notifier)
                if hasattr(agent, 'propagate_websocket_context_to_state'):
                    agent.propagate_websocket_context_to_state(state)
            elif hasattr(agent, 'websocket_notifier'):
                agent.websocket_notifier = self.websocket_notifier
            elif hasattr(agent, 'websocket_manager'):
                agent.websocket_manager = self.websocket_notifier.websocket_manager
    
    def _create_websocket_callback(self, context: AgentExecutionContext):
        """Create WebSocket callback for heartbeat updates."""
        
        async def callback(data: dict):
            if self.websocket_notifier:
                # Send heartbeat as agent_thinking update
                await self.websocket_notifier.send_agent_thinking(
                    context,
                    f"Processing... (heartbeat #{data.get('pulse', 0)})",
                    metadata=data
                )
        
        return callback if self.websocket_notifier else None
    
    def _get_agent_or_error(self, agent_name: str):
        """Get agent from registry or return error result."""
        agent = self.registry.get(agent_name)
        if not agent:
            return AgentExecutionResult(
                success=False,
                error=f"Agent {agent_name} not found"
            )
        return agent