"""Modernized Supervisor Agent with BaseExecutionInterface pattern (<300 lines).

Business Value: Standardized execution patterns for 40+ agents,
improved reliability, and comprehensive monitoring.
"""

import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager

import asyncio
from datetime import datetime, timezone

from langchain_core.messages import SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.core.error_handlers.agents.execution_error_handler import ExecutionErrorHandler
from netra_backend.app.agents.base.executor import BaseExecutionEngine

# Modern execution pattern imports
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    WebSocketManagerProtocol,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_routing import SupervisorAgentRouter

# Import modular components
from netra_backend.app.agents.supervisor.execution_context import PipelineStep
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.initialization_helpers import (
    SupervisorInitializationHelpers,
)
from netra_backend.app.agents.supervisor.modern_execution_helpers import (
    SupervisorExecutionHelpers,
)
from netra_backend.app.agents.supervisor.observability_flow import (
    get_supervisor_flow_logger,
)
from netra_backend.app.agents.supervisor.pipeline_builder import PipelineBuilder
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.state_manager import StateManager
from netra_backend.app.agents.supervisor.supervisor_completion_helpers import (
    SupervisorCompletionHelpers,
)
from netra_backend.app.agents.supervisor.supervisor_utilities import SupervisorUtilities
from netra_backend.app.agents.supervisor.workflow_execution import (
    SupervisorWorkflowExecutor,
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Agent import (
    AgentCompleted,
    AgentStarted,
    SubAgentLifecycle,
    SubAgentState,
    SubAgentUpdate,
)
from netra_backend.app.schemas.registry import AgentResult
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.services.state_persistence import state_persistence_service

logger = central_logger.get_logger(__name__)
class SupervisorAgent(BaseExecutionInterface, BaseSubAgent):
    """Refactored Supervisor agent with modular design."""
    
    def __init__(self, 
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: 'WebSocketManager',
                 tool_dispatcher: ToolDispatcher):
        self._init_base(llm_manager, websocket_manager)
        self._init_services(db_session, websocket_manager, tool_dispatcher)
        self._init_all_components(llm_manager, tool_dispatcher, websocket_manager)
    
    def _init_base(self, llm_manager: LLMManager, websocket_manager: 'WebSocketManager') -> None:
        """Initialize base agent with modern execution interface."""
        BaseSubAgent.__init__(self, llm_manager, name="Supervisor", 
                            description="The supervisor agent that orchestrates sub-agents")
        BaseExecutionInterface.__init__(self, "Supervisor", websocket_manager)
    
    def _init_services(self, db_session: AsyncSession,
                       websocket_manager: 'WebSocketManager',
                       tool_dispatcher: ToolDispatcher) -> None:
        """Initialize services."""
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.state_persistence = state_persistence_service
    
    def _init_all_components(self, llm_manager: LLMManager,
                           tool_dispatcher: ToolDispatcher,
                           websocket_manager: 'WebSocketManager') -> None:
        """Initialize all modular components and infrastructure."""
        self._init_core_components(llm_manager, tool_dispatcher, websocket_manager)
        self._init_infrastructure_components()

    def _init_core_components(self, llm_manager: LLMManager,
                            tool_dispatcher: ToolDispatcher,
                            websocket_manager: 'WebSocketManager') -> None:
        """Initialize core agent components."""
        self._init_registry(llm_manager, tool_dispatcher, websocket_manager)
        self._init_execution_components(websocket_manager)
        self._init_state_components()

    def _init_infrastructure_components(self) -> None:
        """Initialize infrastructure and supporting components."""
        self._init_modern_execution_infrastructure()
        self._init_supervisor_state()
        self._init_supporting_components()

    def _init_modern_execution_infrastructure(self) -> None:
        """Initialize modern execution infrastructure."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = SupervisorInitializationHelpers.create_reliability_manager()
        # BaseExecutionEngine: Core reliability and monitoring infrastructure
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
        self.error_handler = ExecutionErrorHandler()
    
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
        # ExecutionEngine: Handles agent execution with WebSocket notifications
        self.engine = ExecutionEngine(self.registry, websocket_manager)
        # PipelineExecutor: Orchestrates multi-agent pipeline execution
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
        self.utilities = SupervisorInitializationHelpers.init_utilities_for_supervisor(self)
        helpers = SupervisorInitializationHelpers.init_helper_components(self)
        self.execution_helpers, self.workflow_executor, self.agent_router, self.completion_helpers = helpers

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
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for supervisor."""
        await self._validate_state_requirements(context.state)
        await self._validate_execution_resources(context)
        await self._validate_agent_dependencies()
        return True

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core supervisor orchestration logic."""
        self.monitor.start_operation(f"supervisor_execution_{context.run_id}")
        await self.send_status_update(context, "executing", "Starting orchestration...")
        
        result = await self._execute_orchestration_workflow(context)
        
        self.monitor.complete_operation(f"supervisor_execution_{context.run_id}")
        await self.send_status_update(context, "completed", "Orchestration completed")
        return result

    async def _validate_state_requirements(self, state: DeepAgentState) -> None:
        """Validate required state attributes."""
        if not hasattr(state, 'user_request') or not state.user_request:
            raise ValidationError("Missing required user_request in state")
    
    async def _validate_execution_resources(self, context: ExecutionContext) -> None:
        """Validate execution resources are available."""
        if not self.registry or not self.registry.agents:
            raise ValidationError("No agents registered for execution")
    
    async def _validate_agent_dependencies(self) -> None:
        """Validate agent dependencies are healthy."""
        if not self.reliability_manager.get_health_status().get('healthy', False):
            raise ValidationError("Agent dependencies not healthy")
    
    async def _execute_orchestration_workflow(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute orchestration workflow with monitoring."""
        updated_state = await self._run_supervisor_workflow(context.state, context.run_id)
        return {"supervisor_result": "completed", "updated_state": updated_state}

    async def execute(self, state: DeepAgentState, 
                     run_id: str, stream_updates: bool) -> None:
        """Modernized execute using BaseExecutionEngine."""
        context = self._create_supervisor_execution_context(state, run_id, stream_updates)
        await self._execute_with_modern_pattern_and_fallback(context, state, run_id, stream_updates)

    def _create_supervisor_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for supervisor."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=getattr(state, 'chat_thread_id', run_id),
            user_id=getattr(state, 'user_id', 'default_user'),
            metadata={"description": self.description}
        )

    async def _execute_with_modern_pattern_and_fallback(self, context: ExecutionContext, 
                                                       state: DeepAgentState, 
                                                       run_id: str, stream_updates: bool) -> None:
        """Execute with modern pattern and fallback handling."""
        try:
            await self._execute_with_modern_reliability_pattern(context)
        except Exception as e:
            await self._handle_execution_exception(e, context, state, run_id, stream_updates)

    async def _execute_with_modern_reliability_pattern(self, context: ExecutionContext) -> None:
        """Execute with modern reliability pattern."""
        result = await self.reliability_manager.execute_with_reliability(
            context, lambda: self.execution_engine.execute(self, context)
        )
        await self._handle_execution_result(result, context)

    async def _handle_execution_result(self, result, context: ExecutionContext) -> None:
        """Handle execution result with error handling."""
        if not result.success:
            await self.error_handler.handle_execution_error(result.error, context)

    async def _handle_execution_exception(self, exception: Exception, context: ExecutionContext,
                                        state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Handle execution exception with fallback."""
        await self.error_handler.handle_execution_error(str(exception), context)
        logger.error(f"Modern execution failed, falling back to legacy: {exception}")
        await self._execute_legacy_workflow(state, run_id, stream_updates)
    
    async def _run_supervisor_workflow(self, state: DeepAgentState, run_id: str) -> DeepAgentState:
        """Run supervisor workflow using legacy run method."""
        return await self.execution_helpers.run_supervisor_workflow(state, run_id)
    
    async def _handle_execution_failure(self, result: ExecutionResult, state: DeepAgentState) -> None:
        """Handle execution failure with proper error handling."""
        await self.execution_helpers.handle_execution_failure(result, state)
    
    async def _execute_legacy_workflow(self, state: DeepAgentState, 
                                     run_id: str, stream_updates: bool) -> None:
        """Legacy execution workflow for backward compatibility."""
        await self.execution_helpers.execute_legacy_workflow(state, run_id, stream_updates)

    
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
        return await self.workflow_executor.execute_workflow_steps(
            flow_id, user_prompt, thread_id, user_id, run_id
        )

    async def _run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        await self.utilities.run_hooks(event, state, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive supervisor statistics."""
        return self.completion_helpers.get_comprehensive_stats()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        return self.completion_helpers.get_agent_health_status()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from modern monitoring."""
        return self.completion_helpers.get_agent_performance_metrics()
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status from reliability manager."""
        return self.completion_helpers.get_reliability_status()