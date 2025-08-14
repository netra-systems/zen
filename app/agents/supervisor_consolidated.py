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
from app.schemas.Agent import AgentResult
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
        raise NotImplementedError("Use run() method instead")
    
    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Run the supervisor agent workflow."""
        async with self._execution_lock:
            context = self._create_run_context(thread_id, user_id, run_id)
            state = await self._initialize_state(user_prompt, thread_id, user_id)
            pipeline = self._get_execution_pipeline(user_prompt, state)
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
        await self._execute_pipeline(pipeline, state, context["run_id"], context)
        await self._finalize_state(state, context)
    
    async def _initialize_state(self, prompt: str, 
                              thread_id: str, user_id: str) -> DeepAgentState:
        """Initialize agent state."""
        state = self._create_new_state(prompt, thread_id, user_id)
        await self._restore_previous_state(state, thread_id)
        return state
    
    def _create_new_state(self, prompt: str, 
                         thread_id: str, user_id: str) -> DeepAgentState:
        """Create new agent state."""
        return DeepAgentState(
            user_request=prompt,
            chat_thread_id=thread_id,
            user_id=user_id
        )
    
    async def _restore_previous_state(self, state: DeepAgentState, 
                                     thread_id: str) -> None:
        """Restore previous state if available."""
        thread_context = await self.state_persistence.get_thread_context(thread_id)
        if not thread_context or not thread_context.get('current_run_id'):
            return
        await self._merge_restored_state(state, thread_context, thread_id)
    
    async def _merge_restored_state(self, state: DeepAgentState,
                                   thread_context: Dict, thread_id: str) -> None:
        """Merge restored state into current state."""
        restored = await self.state_persistence.load_agent_state(
            thread_context['current_run_id'], self.db_session)
        if not restored:
            return
        self._apply_restored_fields(state, restored)
        logger.info(f"Restored state for thread {thread_id}")
    
    def _apply_restored_fields(self, state: DeepAgentState, 
                              restored: DeepAgentState) -> None:
        """Apply restored fields to state."""
        self._restore_core_fields(state, restored)
        self._restore_report_field(state, restored)
    
    def _restore_core_fields(self, state: DeepAgentState, restored: DeepAgentState) -> None:
        """Restore core workflow fields."""
        if restored.triage_result:
            state.triage_result = restored.triage_result
        if restored.data_result:
            state.data_result = restored.data_result
        if restored.optimizations_result:
            state.optimizations_result = restored.optimizations_result
        if restored.action_plan_result:
            state.action_plan_result = restored.action_plan_result
    
    def _restore_report_field(self, state: DeepAgentState, restored: DeepAgentState) -> None:
        """Restore report field."""
        if restored.report_result:
            state.report_result = restored.report_result
    
    async def _execute_pipeline(self, pipeline: List[PipelineStep],
                               state: DeepAgentState, run_id: str,
                               context: Dict[str, str]) -> None:
        """Execute the agent pipeline."""
        exec_context = self._build_execution_context(run_id, context)
        await self._run_pipeline_with_hooks(pipeline, state, exec_context)
    
    def _build_execution_context(self, run_id: str, 
                                context: Dict[str, str]) -> AgentExecutionContext:
        """Build execution context."""
        return AgentExecutionContext(
            run_id=run_id,
            thread_id=context["thread_id"],
            user_id=context["user_id"],
            agent_name="supervisor"
        )
    
    async def _run_pipeline_with_hooks(self, pipeline: List[PipelineStep],
                                      state: DeepAgentState,
                                      context: AgentExecutionContext) -> None:
        """Run pipeline with hooks."""
        await self._run_hooks("before_agent", state)
        try:
            await self._execute_and_process(pipeline, state, context)
            await self._run_hooks("on_complete", state)
        except Exception as e:
            await self._handle_pipeline_error(state, e)
        finally:
            await self._run_hooks("after_agent", state)
    
    async def _execute_and_process(self, pipeline: List[PipelineStep],
                                  state: DeepAgentState,
                                  context: AgentExecutionContext) -> None:
        """Execute pipeline and process results."""
        results = await self.engine.execute_pipeline(pipeline, context, state)
        self._process_results(results, state)
    
    async def _handle_pipeline_error(self, state: DeepAgentState, 
                                    error: Exception) -> None:
        """Handle pipeline execution error."""
        logger.error(f"Pipeline execution failed: {error}")
        await self._run_hooks("on_error", state, error=error)
        raise
    
    async def _finalize_state(self, state: DeepAgentState, 
                            context: Dict[str, str]) -> None:
        """Finalize and persist state."""
        await self._persist_final_state(state, context)
        await self._notify_completion(state, context)
    
    async def _persist_final_state(self, state: DeepAgentState,
                                  context: Dict[str, str]) -> None:
        """Save final state to persistence."""
        await self.state_persistence.save_agent_state(
            run_id=context["run_id"],
            thread_id=context["thread_id"],
            user_id=context["user_id"],
            state=state,
            db_session=self.db_session
        )
    
    async def _notify_completion(self, state: DeepAgentState,
                                context: Dict[str, str]) -> None:
        """Send completion notification."""
        if self.websocket_manager:
            await self._send_completion_message(state, context["thread_id"], context["run_id"])
    
    def _get_execution_pipeline(self, prompt: str, 
                               state: DeepAgentState) -> List[PipelineStep]:
        """Determine execution pipeline based on prompt."""
        pipeline = self._build_base_pipeline()
        self._add_conditional_steps(pipeline, state)
        pipeline.append(PipelineStep(agent_name="reporting"))
        return pipeline
    
    def _build_base_pipeline(self) -> List[PipelineStep]:
        """Build base pipeline with triage."""
        return [PipelineStep(agent_name="triage")]
    
    def _add_conditional_steps(self, pipeline: List[PipelineStep],
                              state: DeepAgentState) -> None:
        """Add conditional pipeline steps."""
        if self._needs_data_analysis(state):
            pipeline.append(PipelineStep(agent_name="data"))
        if self._needs_optimization(state):
            pipeline.append(PipelineStep(agent_name="optimization"))
        if self._needs_actions(state):
            pipeline.append(PipelineStep(agent_name="actions"))
    
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
                if hasattr(state, 'merge_from'):
                    state.merge_from(result.state)
                else:
                    logger.warning("State lacks merge_from method")
    
    async def _run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        for handler in self.hooks.get(event, []):
            try:
                await handler(state, **kwargs)
            except Exception as e:
                logger.error(f"Hook {handler.__name__} failed: {e}")
                if event == "on_error":
                    raise
    
    async def _send_completion_message(self, state: DeepAgentState, 
                                      thread_id: str, run_id: str) -> None:
        """Send completion message via WebSocket."""
        try:
            message = self._build_completion_message(state, thread_id, run_id)
            await self.websocket_manager.send_to_thread(
                thread_id, message.model_dump())
        except WebSocketDisconnect:
            logger.warning(f"WebSocket disconnected for thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to send completion: {e}")
    
    def _build_completion_message(self, state: DeepAgentState,
                                 thread_id: str, run_id: str) -> WebSocketMessage:
        """Build completion message."""
        content = self._create_completion_content(state, thread_id, run_id)
        return WebSocketMessage(type="agent_completed", content=content)
    
    def _create_completion_content(self, state: DeepAgentState, 
                                  thread_id: str, run_id: str) -> AgentCompleted:
        """Create completion content."""
        return AgentCompleted(
            run_id=run_id,
            result=AgentResult(
                success=True,
                output=state.to_dict()
            ),
            execution_time_ms=0.0
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics."""
        return {
            "registered_agents": len(self.registry.agents),
            "active_runs": len(self.engine.active_runs),
            "completed_runs": len(self.engine.run_history),
            "hooks_registered": {k: len(v) for k, v in self.hooks.items()}
        }