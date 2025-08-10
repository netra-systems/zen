"""Consolidated Supervisor Agent with improved architecture

This module combines the best patterns from both supervisor implementations
to provide a robust, maintainable agent orchestration system.
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from app.logging_config import central_logger
from app.agents.base import BaseSubAgent
from app.schemas import (
    SubAgentLifecycle, WebSocketMessage, AgentStarted, 
    SubAgentUpdate, AgentCompleted, SubAgentState
)
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.services.state_persistence_service import state_persistence_service
from starlette.websockets import WebSocketDisconnect

# Import all sub-agents
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent

logger = central_logger.get_logger(__name__)

class ExecutionStrategy(Enum):
    """Execution strategies for agent pipelines"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"

@dataclass
class AgentExecutionContext:
    """Context for agent execution"""
    run_id: str
    thread_id: str
    user_id: str
    agent_name: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)

@dataclass 
class AgentExecutionResult:
    """Result of agent execution"""
    success: bool
    state: Optional[DeepAgentState] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class SupervisorAgent(BaseSubAgent):
    """Consolidated Supervisor agent with improved lifecycle management"""
    
    def __init__(self, 
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: Any,
                 tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager, 
            name="Supervisor", 
            description="The supervisor agent that orchestrates sub-agents"
        )
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.thread_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.state_persistence = state_persistence_service
        
        # Agent registry
        self.agents: Dict[str, BaseSubAgent] = {}
        self._register_default_agents()
        
        # Execution tracking
        self.active_runs: Dict[str, AgentExecutionContext] = {}
        self.run_history: List[AgentExecutionResult] = []
        
        # Hooks for extensibility
        self.hooks = {
            "before_agent": [],
            "after_agent": [],
            "on_error": [],
            "on_retry": [],
            "on_complete": []
        }
    
    def _register_default_agents(self) -> None:
        """Register default sub-agents"""
        self.register_agent("triage", TriageSubAgent(self.llm_manager, self.tool_dispatcher))
        self.register_agent("data", DataSubAgent(self.llm_manager, self.tool_dispatcher))
        self.register_agent("optimization", OptimizationsCoreSubAgent(self.llm_manager, self.tool_dispatcher))
        self.register_agent("actions", ActionsToMeetGoalsSubAgent(self.llm_manager, self.tool_dispatcher))
        self.register_agent("reporting", ReportingSubAgent(self.llm_manager, self.tool_dispatcher))
    
    def register_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register a sub-agent"""
        agent.websocket_manager = self.websocket_manager
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    def register_hook(self, event: str, handler: callable) -> None:
        """Register an event hook"""
        if event in self.hooks:
            self.hooks[event].append(handler)
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute method for BaseSubAgent compatibility"""
        # This method is here to satisfy the abstract method requirement
        # The actual execution logic is in the run method
        pass
    
    async def run(self, 
                  user_request: str, 
                  run_id: str, 
                  stream_updates: bool = True) -> DeepAgentState:
        """Run the supervisor workflow with improved error handling and lifecycle management"""
        
        context = AgentExecutionContext(
            run_id=run_id,
            thread_id=self.thread_id or "",
            user_id=self.user_id or run_id,
            agent_name="Supervisor"
        )
        
        self.active_runs[run_id] = context
        
        try:
            logger.info(f"Supervisor starting for run_id: {run_id}")
            self.set_state(SubAgentLifecycle.RUNNING)
            
            # Send start notification
            if stream_updates:
                await self._send_websocket_update(
                    context.user_id,
                    "agent_started",
                    AgentStarted(run_id=run_id)
                )
            
            # Initialize or load state
            state = await self._initialize_state(user_request, run_id, context)
            
            # Execute the agent pipeline
            state = await self._execute_pipeline(state, context, stream_updates)
            
            # Save final state
            await self._save_state(state, run_id, context)
            
            # Send completion notification
            if stream_updates:
                await self._send_websocket_update(
                    context.user_id,
                    "agent_completed",
                    AgentCompleted(
                        run_id=run_id,
                        final_report=state.get("final_report", "Workflow completed successfully")
                    )
                )
            
            # Record successful execution
            result = AgentExecutionResult(
                success=True,
                state=state,
                duration=(datetime.utcnow() - context.started_at).total_seconds()
            )
            self.run_history.append(result)
            
            # Execute completion hooks
            await self._execute_hooks("on_complete", context, state)
            
            logger.info(f"Supervisor completed successfully for run_id: {run_id}")
            return state
            
        except Exception as e:
            logger.error(f"Supervisor failed for run_id {run_id}: {e}", exc_info=True)
            
            # Record failed execution
            result = AgentExecutionResult(
                success=False,
                error=str(e),
                duration=(datetime.utcnow() - context.started_at).total_seconds()
            )
            self.run_history.append(result)
            
            # Execute error hooks
            await self._execute_hooks("on_error", context, e)
            
            # Send error notification
            if stream_updates:
                await self._send_error(context.user_id, str(e))
            
            raise
            
        finally:
            # Cleanup
            self.set_state(SubAgentLifecycle.COMPLETED)
            if run_id in self.active_runs:
                del self.active_runs[run_id]
    
    async def _initialize_state(self, 
                                user_request: str, 
                                run_id: str,
                                context: AgentExecutionContext) -> DeepAgentState:
        """Initialize or load agent state"""
        state = None
        
        # Try to load existing state from previous runs
        if self.thread_id and self.db_session:
            thread_context = await self.state_persistence.get_thread_context(self.thread_id)
            if thread_context and thread_context.get("current_run_id"):
                state = await self.state_persistence.load_agent_state(
                    thread_context["current_run_id"],
                    self.db_session
                )
                if state:
                    logger.info(f"Loaded previous state from run {thread_context['current_run_id']}")
                    state.user_request = user_request
        
        # Create new state if needed
        if not state:
            state = DeepAgentState(user_request=user_request)
        
        # Save initial state
        await self._save_state(state, run_id, context)
        
        return state
    
    async def _execute_pipeline(self, 
                                state: DeepAgentState,
                                context: AgentExecutionContext,
                                stream_updates: bool) -> DeepAgentState:
        """Execute the agent pipeline with proper error handling"""
        
        pipeline = self._get_execution_pipeline()
        
        for step_idx, step in enumerate(pipeline):
            agent_name = step["agent"]
            condition = step.get("condition")
            strategy = step.get("strategy", ExecutionStrategy.SEQUENTIAL)
            
            # Check condition if specified
            if condition and not self._evaluate_condition(condition, state):
                logger.info(f"Skipping {agent_name} due to condition")
                continue
            
            # Get the agent
            agent = self.agents.get(agent_name)
            if not agent:
                logger.error(f"Agent {agent_name} not found")
                continue
            
            # Execute before hooks
            await self._execute_hooks("before_agent", context, agent_name)
            
            try:
                # Execute the agent with retry logic
                state = await self._execute_agent_with_retry(
                    agent, state, context, stream_updates
                )
                
                # Save intermediate state
                await self._save_state(state, context.run_id, context)
                
                # Execute after hooks
                await self._execute_hooks("after_agent", context, agent_name, state)
                
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                
                # Check if we should continue or fail the pipeline
                if step.get("critical", True):
                    raise
                else:
                    logger.warning(f"Continuing pipeline despite {agent_name} failure")
        
        return state
    
    async def _execute_agent_with_retry(self,
                                       agent: BaseSubAgent,
                                       state: DeepAgentState,
                                       context: AgentExecutionContext,
                                       stream_updates: bool) -> DeepAgentState:
        """Execute an agent with retry logic"""
        
        retry_count = 0
        last_error = None
        
        while retry_count <= context.max_retries:
            try:
                # Set up agent context
                agent.websocket_manager = self.websocket_manager
                agent.user_id = context.user_id
                
                # Update agent lifecycle
                agent.set_state(SubAgentLifecycle.RUNNING)
                
                # Send update if streaming
                if stream_updates:
                    from langchain_core.messages import SystemMessage
                    state_obj = SubAgentState(
                        messages=[SystemMessage(content=f"Starting {agent.name}")],
                        next_node="",
                        lifecycle=SubAgentLifecycle.RUNNING
                    )
                    await self._send_websocket_update(
                        context.user_id,
                        "sub_agent_update",
                        SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=state_obj
                        )
                    )
                
                # Execute the agent
                if context.timeout:
                    await asyncio.wait_for(
                        agent.execute(state, context.run_id, stream_updates),
                        timeout=context.timeout
                    )
                else:
                    await agent.execute(state, context.run_id, stream_updates)
                
                # Update agent lifecycle
                agent.set_state(SubAgentLifecycle.COMPLETED)
                
                # Send update if streaming
                if stream_updates:
                    from langchain_core.messages import SystemMessage
                    state_obj = SubAgentState(
                        messages=[SystemMessage(content=f"{agent.name} completed")],
                        next_node="",
                        lifecycle=SubAgentLifecycle.COMPLETED
                    )
                    await self._send_websocket_update(
                        context.user_id,
                        "sub_agent_update",
                        SubAgentUpdate(
                            sub_agent_name=agent.name,
                            state=state_obj
                        )
                    )
                
                return state
                
            except asyncio.TimeoutError:
                last_error = f"Agent {agent.name} timed out after {context.timeout} seconds"
                logger.error(last_error)
                
            except Exception as e:
                last_error = e
                logger.error(f"Agent {agent.name} failed (attempt {retry_count + 1}): {e}")
                
            # Execute retry hook
            if retry_count < context.max_retries:
                await self._execute_hooks("on_retry", context, agent.name, retry_count + 1)
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            else:
                break
        
        # All retries exhausted
        raise Exception(f"Agent {agent.name} failed after {retry_count + 1} attempts: {last_error}")
    
    def _get_execution_pipeline(self) -> List[Dict[str, Any]]:
        """Get the default execution pipeline"""
        return [
            {"agent": "triage", "critical": True},
            {"agent": "data", "critical": True},
            {"agent": "optimization", "critical": True},
            {"agent": "actions", "critical": True},
            {"agent": "reporting", "critical": False}
        ]
    
    def _evaluate_condition(self, condition: Dict[str, Any], state: DeepAgentState) -> bool:
        """Evaluate a pipeline condition"""
        condition_type = condition.get("type")
        
        if condition_type == "has_data":
            field = condition.get("field")
            return hasattr(state, field) and getattr(state, field) is not None
        
        if condition_type == "equals":
            field = condition.get("field")
            value = condition.get("value")
            return hasattr(state, field) and getattr(state, field) == value
        
        return True
    
    async def _save_state(self, 
                         state: DeepAgentState, 
                         run_id: str,
                         context: AgentExecutionContext) -> None:
        """Save agent state to persistence"""
        if self.thread_id and self.user_id and self.db_session:
            try:
                await self.state_persistence.save_agent_state(
                    run_id=run_id,
                    thread_id=self.thread_id,
                    user_id=self.user_id,
                    state=state,
                    db_session=self.db_session
                )
            except Exception as e:
                logger.error(f"Failed to save state: {e}")
    
    async def _send_websocket_update(self, 
                                    user_id: str, 
                                    message_type: str, 
                                    payload: Any) -> None:
        """Send WebSocket update with error handling"""
        try:
            await self.websocket_manager.send_message(
                user_id,
                WebSocketMessage(
                    type=message_type, 
                    payload=payload.model_dump() if hasattr(payload, 'model_dump') else payload
                ).model_dump()
            )
        except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
            logger.debug(f"WebSocket disconnected when sending {message_type}: {e}")
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def _send_error(self, user_id: str, error_message: str) -> None:
        """Send error message via WebSocket"""
        await self.websocket_manager.send_error(user_id, error_message, "Supervisor")
    
    async def _execute_hooks(self, event: str, *args, **kwargs) -> None:
        """Execute registered hooks for an event"""
        for hook in self.hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook failed for event {event}: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the supervisor"""
        logger.info("Shutting down supervisor...")
        
        # Cancel any active runs
        for run_id in list(self.active_runs.keys()):
            context = self.active_runs[run_id]
            await self._send_error(
                context.user_id, 
                "Supervisor shutting down"
            )
        
        self.active_runs.clear()
        logger.info("Supervisor shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics"""
        return {
            "active_runs": len(self.active_runs),
            "total_runs": len(self.run_history),
            "successful_runs": sum(1 for r in self.run_history if r.success),
            "failed_runs": sum(1 for r in self.run_history if not r.success),
            "registered_agents": list(self.agents.keys()),
            "average_duration": (
                sum(r.duration for r in self.run_history) / len(self.run_history)
                if self.run_history else 0
            )
        }