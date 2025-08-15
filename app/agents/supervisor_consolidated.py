"""Refactored Supervisor Agent with modular architecture (<300 lines)."""

import uuid
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
from app.services.state_persistence_service import state_persistence_service
from starlette.websockets import WebSocketDisconnect
from langchain_core.messages import SystemMessage

# Import modular components
from app.agents.supervisor.execution_context import PipelineStep
from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.supervisor.execution_engine import ExecutionEngine
from app.agents.supervisor.pipeline_executor import PipelineExecutor
from app.agents.supervisor.state_manager import StateManager
from app.agents.supervisor.pipeline_builder import PipelineBuilder

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
        self.hooks = self._init_hooks()
        self._execution_lock = asyncio.Lock()
    
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
        self.registry = AgentRegistry(llm_manager, tool_dispatcher)
        self.registry.set_websocket_manager(websocket_manager)
        self.registry.register_default_agents()
        self.engine = ExecutionEngine(self.registry, websocket_manager)
        self.pipeline_executor = PipelineExecutor(
            self.engine, websocket_manager, self.db_session
        )
        # Create a factory that returns the existing session
        db_session_factory = lambda: self.db_session
        self.state_manager = StateManager(db_session_factory)
        self.pipeline_builder = PipelineBuilder()
    
    def _init_hooks(self) -> Dict[str, List]:
        """Initialize event hooks."""
        return {
            "before_agent": [],
            "after_agent": [],
            "on_error": [],
            "on_retry": [],
            "on_complete": []
        }
    
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
        # Delegate to run() method with extracted context from state
        thread_id = state.chat_thread_id or run_id
        user_id = state.user_id or "default_user"
        user_prompt = state.user_request or ""
        
        # Execute the main run method
        updated_state = await self.run(user_prompt, thread_id, user_id, run_id)
        
        # Merge results back into the original state
        if updated_state:
            state = state.merge_from(updated_state)
    
    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Run the supervisor agent workflow."""
        async with self._execution_lock:
            context = self._create_run_context(thread_id, user_id, run_id)
            state = await self.state_manager.initialize_state(
                user_prompt, thread_id, user_id, run_id
            )
            pipeline = self.pipeline_builder.get_execution_pipeline(
                user_prompt, state
            )
            await self._execute_with_context(pipeline, state, context)
            return state
    
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
        for handler in self.hooks.get(event, []):
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