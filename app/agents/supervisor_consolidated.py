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
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.services.state_persistence_service import state_persistence_service
from starlette.websockets import WebSocketDisconnect
from langchain_core.messages import SystemMessage

# Import modular components
from app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, 
    ExecutionStrategy, PipelineStep
)
from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.supervisor.execution_engine import ExecutionEngine

logger = central_logger.get_logger(__name__)


class SupervisorAgent(BaseSubAgent):
    """Refactored Supervisor agent with modular design."""
    
    def __init__(self, 
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: 'WebSocketManager',
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
        
        # Initialize modular components
        self.registry = AgentRegistry(llm_manager, tool_dispatcher)
        self.registry.set_websocket_manager(websocket_manager)
        self.registry.register_default_agents()
        
        self.engine = ExecutionEngine(self.registry, websocket_manager)
        
        # Hooks for extensibility
        self.hooks = self._init_hooks()
    
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
        pass
    
    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Run the supervisor agent workflow."""
        self.thread_id = thread_id
        self.user_id = user_id
        self.current_run_id = run_id
        
        state = await self._initialize_state(user_prompt, thread_id, user_id)
        pipeline = self._get_execution_pipeline(user_prompt, state)
        
        await self._execute_pipeline(pipeline, state, run_id)
        await self._finalize_state(state)
        
        return state
    
    async def _initialize_state(self, prompt: str, 
                              thread_id: str, user_id: str) -> DeepAgentState:
        """Initialize agent state."""
        state = DeepAgentState(
            user_request=prompt,
            chat_thread_id=thread_id,
            user_id=user_id
        )
        
        # Try to restore previous state from thread context
        thread_context = await self.state_persistence.get_thread_context(thread_id)
        if thread_context and thread_context.get('current_run_id'):
            restored = await self.state_persistence.load_agent_state(
                thread_context['current_run_id'], 
                self.db_session
            )
            if restored:
                # Merge restored state with new request
                state.triage_result = restored.triage_result
                state.data_result = restored.data_result
                state.optimizations_result = restored.optimizations_result
                state.action_plan_result = restored.action_plan_result
                state.report_result = restored.report_result
                logger.info(f"Restored state for thread {thread_id}")
        
        return state
    
    async def _execute_pipeline(self, pipeline: List[PipelineStep],
                               state: DeepAgentState, run_id: str) -> None:
        """Execute the agent pipeline."""
        context = AgentExecutionContext(
            run_id=run_id,
            thread_id=self.thread_id,
            user_id=self.user_id,
            agent_name="supervisor"
        )
        
        # Execute hooks
        await self._run_hooks("before_agent", state)
        
        try:
            results = await self.engine.execute_pipeline(pipeline, context, state)
            self._process_results(results, state)
            await self._run_hooks("on_complete", state)
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            await self._run_hooks("on_error", state, error=e)
            raise
        finally:
            await self._run_hooks("after_agent", state)
    
    async def _finalize_state(self, state: DeepAgentState) -> None:
        """Finalize and persist state."""
        # Save final state to persistence
        await self.state_persistence.save_agent_state(
            run_id=self.current_run_id if hasattr(self, 'current_run_id') else str(uuid.uuid4()),
            thread_id=self.thread_id,
            user_id=self.user_id,
            state=state,
            db_session=self.db_session
        )
        
        # Send completion message
        if self.websocket_manager:
            await self._send_completion_message(state)
    
    def _get_execution_pipeline(self, prompt: str, 
                               state: DeepAgentState) -> List[PipelineStep]:
        """Determine execution pipeline based on prompt."""
        pipeline = []
        
        # Always start with triage
        pipeline.append(PipelineStep(agent_name="triage"))
        
        # Determine next steps based on triage results
        if self._needs_data_analysis(state):
            pipeline.append(PipelineStep(agent_name="data"))
        
        if self._needs_optimization(state):
            pipeline.append(PipelineStep(agent_name="optimization"))
        
        if self._needs_actions(state):
            pipeline.append(PipelineStep(agent_name="actions"))
        
        # Always end with reporting
        pipeline.append(PipelineStep(agent_name="reporting"))
        
        return pipeline
    
    def _needs_data_analysis(self, state: DeepAgentState) -> bool:
        """Check if data analysis is needed."""
        # Default to True if no triage result yet or analysis is recommended
        if not state.triage_result:
            return True
        return state.triage_result.get("requires_data", True)
    
    def _needs_optimization(self, state: DeepAgentState) -> bool:
        """Check if optimization is needed."""
        # Default to True if no triage result yet or optimization is recommended
        if not state.triage_result:
            return True
        return state.triage_result.get("requires_optimization", True)
    
    def _needs_actions(self, state: DeepAgentState) -> bool:
        """Check if action planning is needed."""
        # Default to True if no triage result yet or actions are recommended
        if not state.triage_result:
            return True
        return state.triage_result.get("requires_actions", True)
    
    def _process_results(self, results: List[AgentExecutionResult],
                        state: DeepAgentState) -> None:
        """Process execution results."""
        for result in results:
            if result.success and result.state:
                state.merge_from(result.state)
    
    async def _run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        for handler in self.hooks.get(event, []):
            try:
                await handler(state, **kwargs)
            except Exception as e:
                logger.error(f"Hook {handler.__name__} failed: {e}")
    
    async def _send_completion_message(self, state: DeepAgentState) -> None:
        """Send completion message via WebSocket."""
        message = WebSocketMessage(
            type="agent_completed",
            content=AgentCompleted(
                agent_name="supervisor",
                run_id=state.metadata.get("run_id", ""),
                thread_id=self.thread_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                result=state.to_dict()
            )
        )
        await self.websocket_manager.send_to_thread(
            self.thread_id, message.model_dump())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics."""
        return {
            "registered_agents": len(self.registry.agents),
            "active_runs": len(self.engine.active_runs),
            "completed_runs": len(self.engine.run_history),
            "hooks_registered": {k: len(v) for k, v in self.hooks.items()}
        }