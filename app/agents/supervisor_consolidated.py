"""Refactored Supervisor Agent with modular architecture (<300 lines)."""

import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Tuple, Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager
from datetime import datetime, timezone
import asyncio
from app.logging_config import central_logger
from app.agents.base import BaseSubAgent
from app.schemas import (
    SubAgentLifecycle, WebSocketMessage, AgentStarted, 
    SubAgentUpdate, AgentCompleted, SubAgentState
)
from app.schemas.registry import AgentResult
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.services.state_persistence import state_persistence_service
from starlette.websockets import WebSocketDisconnect
from langchain_core.messages import SystemMessage

# Import modular components
from app.agents.supervisor.execution_context import PipelineStep
from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.supervisor.execution_engine import ExecutionEngine
from app.agents.supervisor.pipeline_executor import PipelineExecutor
from app.agents.supervisor.state_manager import StateManager
from app.agents.supervisor.pipeline_builder import PipelineBuilder
from app.agents.supervisor.observability_flow import get_supervisor_flow_logger

logger = central_logger.get_logger(__name__)


class SupervisorAgent(BaseSubAgent):
    """Refactored Supervisor agent with modular design."""
    
    def __init__(self, 
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: 'WebSocketManager',
                 tool_dispatcher: ToolDispatcher):
        self._init_base(llm_manager)
        self._init_services(db_session, websocket_manager, tool_dispatcher)
        self._init_components(llm_manager, tool_dispatcher, websocket_manager)
        self._init_supervisor_state()
    
    def _init_base(self, llm_manager: LLMManager) -> None:
        """Initialize base agent."""
        super().__init__(
            llm_manager, 
            name="Supervisor", 
            description="The supervisor agent that orchestrates sub-agents"
        )
    
    def _init_services(self, db_session: AsyncSession,
                       websocket_manager: 'WebSocketManager',
                       tool_dispatcher: ToolDispatcher) -> None:
        """Initialize services."""
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.state_persistence = state_persistence_service
    
    def _init_components(self, llm_manager: LLMManager,
                        tool_dispatcher: ToolDispatcher,
                        websocket_manager: 'WebSocketManager') -> None:
        """Initialize modular components."""
        self._init_registry(llm_manager, tool_dispatcher, websocket_manager)
        self._init_execution_components(websocket_manager)
        self._init_state_components()
        self._init_supporting_components()

    def _init_supervisor_state(self) -> None:
        """Initialize supervisor state and hooks."""
        self.hooks = self._init_hooks()
        self._execution_lock = asyncio.Lock()

    def _init_registry(self, llm_manager: LLMManager, 
                      tool_dispatcher: ToolDispatcher,
                      websocket_manager: 'WebSocketManager') -> None:
        """Initialize agent registry."""
        self.registry = AgentRegistry(llm_manager, tool_dispatcher)
        self.registry.set_websocket_manager(websocket_manager)
        self.registry.register_default_agents()

    def _init_execution_components(self, websocket_manager: 'WebSocketManager') -> None:
        """Initialize execution components."""
        self.engine = ExecutionEngine(self.registry, websocket_manager)
        self.pipeline_executor = PipelineExecutor(
            self.engine, websocket_manager, self.db_session
        )

    def _init_state_components(self) -> None:
        """Initialize state management components."""
        # Pass the session directly instead of a complex context manager
        self.state_manager = StateManager(self.db_session)

    def _init_supporting_components(self) -> None:
        """Initialize supporting components."""
        self.pipeline_builder = PipelineBuilder()
        self.flow_logger = get_supervisor_flow_logger()

    @asynccontextmanager
    async def _create_db_session_factory(self):
        """Create database session factory."""
        yield self.db_session
    
    def _init_hooks(self) -> Dict[str, List]:
        """Initialize event hooks."""
        hook_types = ["before_agent", "after_agent", "on_error", "on_retry", "on_complete"]
        return {hook_type: [] for hook_type in hook_types}
    
    def register_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register a sub-agent."""
        self.registry.register(name, agent)
    
    def register_hook(self, event: str, handler: callable) -> None:
        """Register an event hook."""
        if event in self.hooks:
            self.hooks[event].append(handler)
    
    @property
    def agents(self) -> Dict[str, BaseSubAgent]:
        """Get all registered agents."""
        return self.registry.agents
    
    @property
    def sub_agents(self) -> list:
        """Backward compatibility property."""
        return self.registry.get_all_agents()
    
    @sub_agents.setter
    def sub_agents(self, agents: list) -> None:
        """Backward compatibility setter."""
        for i, agent in enumerate(agents):
            self.registry.register(f"agent_{i}", agent)
    
    async def execute(self, state: DeepAgentState, 
                     run_id: str, stream_updates: bool) -> None:
        """Execute method for BaseSubAgent compatibility."""
        flow_id = self._start_execution_flow(run_id)
        context = self._extract_context_from_state(state, run_id)
        updated_state = await self._execute_run_with_logging(flow_id, context)
        self._finalize_execution(flow_id, state, updated_state)

    def _start_execution_flow(self, run_id: str) -> str:
        """Start execution flow logging."""
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, run_id, 3)
        return flow_id

    def _extract_context_from_state(self, state: DeepAgentState, run_id: str) -> dict:
        """Extract execution context from state."""
        return {
            "thread_id": state.chat_thread_id or run_id,
            "user_id": state.user_id or "default_user",
            "user_prompt": state.user_request or "",
            "run_id": run_id
        }

    async def _execute_run_with_logging(self, flow_id: str, context: dict) -> DeepAgentState:
        """Execute run with flow logging."""
        self.flow_logger.step_started(flow_id, "execute_run", "supervisor")
        updated_state = await self.run(
            context["user_prompt"], context["thread_id"], context["user_id"], context["run_id"]
        )
        self.flow_logger.step_completed(flow_id, "execute_run", "supervisor")
        return updated_state

    def _finalize_execution(self, flow_id: str, state: DeepAgentState, updated_state: DeepAgentState) -> None:
        """Finalize execution and merge states."""
        if updated_state:
            state = state.merge_from(updated_state)
        self.flow_logger.complete_flow(flow_id)
    
    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Run the supervisor agent workflow."""
        flow_id = self._start_run_flow(run_id)
        async with self._execution_lock:
            state = await self._execute_workflow_steps(flow_id, user_prompt, thread_id, user_id, run_id)
            self.flow_logger.complete_flow(flow_id)
            return state

    def _start_run_flow(self, run_id: str) -> str:
        """Start run flow logging."""
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, run_id, 4)
        return flow_id

    async def _execute_workflow_steps(self, flow_id: str, user_prompt: str, 
                                    thread_id: str, user_id: str, run_id: str) -> DeepAgentState:
        """Execute all workflow steps."""
        context = await self._create_context_step(flow_id, thread_id, user_id, run_id)
        state = await self._initialize_state_step(flow_id, user_prompt, thread_id, user_id, run_id)
        pipeline = await self._build_pipeline_step(flow_id, user_prompt, state)
        await self._execute_pipeline_step(flow_id, pipeline, state, context)
        return state

    async def _create_context_step(self, flow_id: str, thread_id: str, user_id: str, run_id: str) -> dict:
        """Execute create context step."""
        self.flow_logger.step_started(flow_id, "create_context", "initialization")
        context = self._create_run_context(thread_id, user_id, run_id)
        self.flow_logger.step_completed(flow_id, "create_context", "initialization")
        return context

    async def _initialize_state_step(self, flow_id: str, user_prompt: str, 
                                   thread_id: str, user_id: str, run_id: str) -> DeepAgentState:
        """Execute initialize state step."""
        self.flow_logger.step_started(flow_id, "initialize_state", "state_management")
        state = await self.state_manager.initialize_state(user_prompt, thread_id, user_id, run_id)
        self.flow_logger.step_completed(flow_id, "initialize_state", "state_management")
        return state

    async def _build_pipeline_step(self, flow_id: str, user_prompt: str, state: DeepAgentState) -> List[PipelineStep]:
        """Execute build pipeline step."""
        self.flow_logger.step_started(flow_id, "build_pipeline", "planning")
        pipeline = self.pipeline_builder.get_execution_pipeline(user_prompt, state)
        self.flow_logger.step_completed(flow_id, "build_pipeline", "planning")
        return pipeline

    async def _execute_pipeline_step(self, flow_id: str, pipeline: List[PipelineStep], 
                                   state: DeepAgentState, context: dict) -> None:
        """Execute pipeline step."""
        self.flow_logger.step_started(flow_id, "execute_pipeline", "execution")
        await self._execute_with_context(pipeline, state, context)
        self.flow_logger.step_completed(flow_id, "execute_pipeline", "execution")
    
    def _create_run_context(self, thread_id: str, 
                           user_id: str, run_id: str) -> Dict[str, str]:
        """Create execution context."""
        return {
            "thread_id": thread_id,
            "user_id": user_id,
            "run_id": run_id
        }
    
    async def _execute_with_context(self, pipeline: List[PipelineStep],
                                   state: DeepAgentState, 
                                   context: Dict[str, str]) -> None:
        """Execute pipeline with context."""
        await self.pipeline_executor.execute_pipeline(
            pipeline, state, context["run_id"], context
        )
        await self.pipeline_executor.finalize_state(state, context)
    
    async def _route_to_agent(self, state: DeepAgentState, 
                             context: 'AgentExecutionContext', 
                             agent_name: str) -> 'AgentExecutionResult':
        """Route request to specific agent with basic execution."""
        from app.agents.supervisor.execution_context import AgentExecutionContext
        exec_context = self._create_agent_execution_context(context, agent_name)
        return await self.engine.execute_agent(exec_context, state)
    
    async def _route_to_agent_with_retry(self, state: DeepAgentState,
                                        context: 'AgentExecutionContext',
                                        agent_name: str) -> 'AgentExecutionResult':
        """Route request to agent with retry logic."""
        from app.agents.supervisor.execution_context import AgentExecutionContext  
        exec_context = self._create_agent_execution_context(context, agent_name)
        exec_context.max_retries = context.max_retries
        return await self.engine.execute_agent(exec_context, state)
    
    async def _route_to_agent_with_circuit_breaker(self, state: DeepAgentState,
                                                  context: 'AgentExecutionContext',
                                                  agent_name: str) -> 'AgentExecutionResult':
        """Route request to agent with circuit breaker protection."""
        from app.agents.supervisor.execution_context import AgentExecutionContext
        exec_context = self._create_agent_execution_context(context, agent_name)
        return await self.engine._execute_with_fallback(exec_context, state)
    
    def _create_agent_execution_context(self, base_context, agent_name: str):
        """Create AgentExecutionContext from base context."""
        from app.agents.supervisor.execution_context import AgentExecutionContext
        return AgentExecutionContext(
            run_id=base_context.run_id, thread_id=base_context.thread_id,
            user_id=base_context.user_id, agent_name=agent_name,
            max_retries=getattr(base_context, 'max_retries', 3)
        )
    
    async def _run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        handlers = self.hooks.get(event, [])
        for handler in handlers:
            await self._execute_single_hook(handler, event, state, **kwargs)

    async def _execute_single_hook(self, handler, event: str, state: DeepAgentState, **kwargs) -> None:
        """Execute a single hook with error handling."""
        try:
            await handler(state, **kwargs)
        except Exception as e:
            logger.error(f"Hook {handler.__name__} failed: {e}")
            if event == "on_error":
                raise
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics."""
        return {
            "registered_agents": len(self.registry.agents),
            "active_runs": len(self.engine.active_runs),
            "completed_runs": len(self.engine.run_history),
            "hooks_registered": {k: len(v) for k, v in self.hooks.items()}
        }