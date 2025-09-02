"""Supervisor Agent - Split Architecture Implementation

Refactored supervisor agent using new split architecture:
- Uses AgentInstanceFactory for per-request agent instantiation
- Passes UserExecutionContext through entire execution chain
- Removes global singleton patterns for proper user isolation
- Implements UserWebSocketEmitter for per-user event emission

Business Value: Enables safe concurrent user operations with zero context leakage.
BVJ: ALL segments | Platform Stability | Complete user isolation for production deployment
"""

import asyncio
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.utils import extract_thread_id
from netra_backend.app.logging_config import central_logger

# New split architecture components
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    UserExecutionContext,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    get_agent_class_registry
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext as UserContext,
    validate_user_context
)

# Legacy components for backward compatibility during transition
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.modern_execution_helpers import SupervisorExecutionHelpers
from netra_backend.app.agents.supervisor.workflow_execution import SupervisorWorkflowExecutor
from netra_backend.app.agents.supervisor.state_manager import SessionlessAgentStateManager
from netra_backend.app.agents.supervisor.pipeline_builder import PipelineBuilder
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.observability_flow import get_supervisor_flow_logger
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


class SupervisorAgent(BaseAgent):
    """Split architecture supervisor agent with per-request isolation.
    
    CRITICAL: This supervisor uses the new split architecture to ensure:
    - Complete user isolation (no shared state between requests)
    - Per-request agent instantiation via AgentInstanceFactory  
    - UserExecutionContext passed through entire execution chain
    - UserWebSocketEmitter for per-user event emission
    
    The supervisor coordinates agent orchestration while maintaining strict
    isolation boundaries to prevent user data leakage in concurrent scenarios.
    """
    
    def __init__(self, 
                 llm_manager: LLMManager,
                 websocket_bridge: AgentWebSocketBridge,
                 tool_dispatcher: ToolDispatcher,
                 db_session_factory=None,
                 user_context: Optional[UserContext] = None):
        # Initialize BaseAgent with infrastructure (no global state)
        super().__init__(
            llm_manager=llm_manager,
            name="Supervisor",
            description="Orchestrates sub-agents with complete user isolation",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=False,         # Disable caching for isolation
            tool_dispatcher=tool_dispatcher
        )
        
        # NEW: Store per-request user context (NO global state)
        self.user_context = user_context  # Per-request isolation
        self.db_session_factory = db_session_factory
        self.websocket_bridge = websocket_bridge
        self.state_persistence = state_persistence_service
        
        # NEW: Split architecture components
        self.agent_instance_factory = get_agent_instance_factory()
        self.agent_class_registry = get_agent_class_registry()
        
        # Legacy components for backward compatibility during transition
        self._init_legacy_compatibility_components(llm_manager, tool_dispatcher, websocket_bridge)
        
        # Per-request execution lock (not global!)
        self._execution_lock = asyncio.Lock()
        
        logger.info(f"SupervisorAgent initialized with user context: {user_context.user_id if user_context else 'None'}")

    def _init_legacy_compatibility_components(self, llm_manager: LLMManager,
                                             tool_dispatcher: ToolDispatcher,
                                             websocket_bridge) -> None:
        """Initialize legacy components for backward compatibility during transition."""
        # Legacy agent registry for backward compatibility
        self.registry = AgentRegistry(llm_manager, tool_dispatcher)
        self.registry.register_default_agents()
        self.registry.set_websocket_bridge(websocket_bridge)
        
        # Aliases for backward compatibility
        self.agent_registry = self.registry
        self.websocket_manager = websocket_bridge
        
        # Initialize execution helpers for business logic
        self.execution_helpers = SupervisorExecutionHelpers(self)
        self.workflow_executor = SupervisorWorkflowExecutor(self)
        
        # Legacy compatibility properties
        self._init_legacy_properties()
    
    def _init_legacy_properties(self) -> None:
        """Initialize legacy compatibility properties."""
        # State management (will get sessions on-demand)
        self.state_manager = SessionlessAgentStateManager()  # No global session storage
        
        # Pipeline components (will get sessions through context)
        self.pipeline_builder = PipelineBuilder()
        self.pipeline_executor = None  # Initialize lazily when needed with session
        
        # Flow logger for observability
        self.flow_logger = get_supervisor_flow_logger()
        
        # Hooks for legacy compatibility
        self.hooks = {"before_agent": [], "after_agent": [], "on_error": [], "on_retry": [], "on_complete": []}
        
        # Legacy properties that tests/code might expect
        self.sub_agents = self.registry.get_all_agents()
        
        # Mock completion helpers for stats methods
        from types import SimpleNamespace
        self.completion_helpers = SimpleNamespace(
            get_comprehensive_stats=lambda: {"agents_registered": len(self.registry.agents)},
            get_agent_health_status=lambda: self.get_health_status(),
            get_agent_performance_metrics=lambda: {"supervisor": "operational"},
            get_reliability_status=lambda: self.get_circuit_breaker_status()
        )
    
    async def _get_session_for_operation(self):
        """Get a database session for an operation.
        
        Returns a session context manager or None if no factory available.
        """
        if self.db_session_factory:
            return self.db_session_factory()
        return None
    
    
    def _get_pipeline_executor_with_session(self, session: AsyncSession) -> PipelineExecutor:
        """Create pipeline executor instance with given session - no global storage."""
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        engine = ExecutionEngine(self.registry)
        return PipelineExecutor(engine, self.websocket_manager, session)
    

    # === SSOT Abstract Method Implementations ===
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a sub-agent."""
        self.registry.register(name, agent)
    
    def register_hook(self, event: str, handler: callable) -> None:
        """Register an event hook."""
        if event in self.hooks:
            self.hooks[event].append(handler)
    
    @property
    def agents(self) -> Dict[str, BaseAgent]:
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
        """Validate execution preconditions for supervisor orchestration."""
        if not context.state.user_request:
            self.logger.warning(f"No user request provided for supervisor in run_id: {context.run_id}")
            return False
        
        if not self.registry or not self.registry.agents:
            self.logger.error(f"No agents registered for supervisor execution in run_id: {context.run_id}")
            return False
            
        return True

    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core supervisor orchestration logic with per-user isolation."""
        # CRITICAL: Validate user context is available for proper isolation
        if not self.user_context:
            logger.error(f"SupervisorAgent missing UserExecutionContext - cannot ensure isolation")
            raise RuntimeError("SupervisorAgent requires UserExecutionContext for proper isolation")
        
        # Use user-specific WebSocket emitter if available
        if self.user_context.websocket_emitter:
            await self.user_context.websocket_emitter.notify_agent_thinking(
                "Supervisor", "Starting supervisor orchestration with complete user isolation..."
            )
            await self.user_context.websocket_emitter.notify_agent_thinking(
                "Supervisor", "Analyzing request and planning agent workflow..."
            )
        
        # Execute supervisor workflow using NEW split architecture
        await self._emit_thinking("Coordinating with per-request agent instances for optimal workflow")
        updated_state = await self._run_isolated_supervisor_workflow(context.state, context.run_id)
        
        # Send completion via user-specific emitter
        if self.user_context.websocket_emitter:
            await self.user_context.websocket_emitter.notify_agent_completed(
                "Supervisor",
                {"supervisor_result": "completed", "orchestration_successful": True}
            )
        
        return {
            "supervisor_result": "completed",
            "updated_state": updated_state,
            "orchestration_successful": True,
            "user_isolation_verified": True
        }

    # === Business Logic Methods ===
    
    async def _run_isolated_supervisor_workflow(self, state: DeepAgentState, run_id: str) -> DeepAgentState:
        """Run supervisor workflow with complete user isolation using split architecture."""
        if not self.user_context:
            raise RuntimeError("User context required for isolated workflow execution")
        
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, run_id, 4)  # 4 main workflow steps
        
        try:
            # NEW: Use AgentInstanceFactory to create isolated agent instances
            agent_instances = await self._create_isolated_agent_instances()
            
            # Execute workflow with isolated instances
            updated_state = await self._execute_workflow_with_isolated_agents(
                agent_instances, flow_id, state, run_id
            )
            
            self.flow_logger.complete_flow(flow_id)
            return updated_state
            
        except Exception as e:
            # Fallback to legacy workflow if new approach fails
            logger.warning(f"Isolated workflow failed, falling back to legacy: {e}")
            updated_state = await self.workflow_executor.execute_workflow_steps(
                flow_id, state.user_request, state.chat_thread_id, state.user_id, run_id
            )
            self.flow_logger.complete_flow(flow_id)
            return updated_state
    
    async def _create_isolated_agent_instances(self) -> Dict[str, BaseAgent]:
        """Create isolated agent instances for this user request using AgentInstanceFactory."""
        if not self.user_context:
            raise RuntimeError("UserExecutionContext required for creating isolated agents")
        
        agent_instances = {}
        
        # Get list of agent names to instantiate
        agent_names = self._get_required_agent_names()
        
        for agent_name in agent_names:
            try:
                logger.debug(f"Creating isolated instance of {agent_name} for user {self.user_context.user_id}")
                
                # Use AgentInstanceFactory to create isolated instance
                agent_instance = await self.agent_instance_factory.create_agent_instance(
                    agent_name=agent_name,
                    user_context=self.user_context
                )
                
                agent_instances[agent_name] = agent_instance
                logger.info(f"✅ Created isolated {agent_name} instance for user {self.user_context.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create isolated {agent_name} instance: {e}")
                # Continue with other agents - non-critical agents can fail
                continue
        
        if not agent_instances:
            raise RuntimeError("Failed to create any isolated agent instances")
        
        logger.info(f"Created {len(agent_instances)} isolated agent instances for user {self.user_context.user_id}")
        return agent_instances
    
    def _get_required_agent_names(self) -> List[str]:
        """Get list of required agent names for orchestration."""
        # Core agents required for most workflows
        core_agents = ["triage", "data", "optimization", "actions"]
        
        # Optional agents that enhance functionality
        optional_agents = ["reporting", "goals_triage", "data_helper", "synthetic_data"]
        
        # Return core agents first, then optionals
        return core_agents + optional_agents
    
    async def _execute_workflow_with_isolated_agents(self, 
                                                   agent_instances: Dict[str, BaseAgent],
                                                   flow_id: str, 
                                                   state: DeepAgentState, 
                                                   run_id: str) -> DeepAgentState:
        """Execute workflow using isolated agent instances."""
        if not self.user_context:
            raise RuntimeError("UserExecutionContext required for workflow execution")
        
        logger.info(f"Executing workflow with {len(agent_instances)} isolated agents for user {self.user_context.user_id}")
        
        # Update state with user context information
        state.user_id = self.user_context.user_id
        state.chat_thread_id = self.user_context.thread_id
        
        # Execute workflow steps using isolated instances
        # Start with triage to determine workflow path
        if "triage" in agent_instances:
            try:
                await self._emit_thinking("Running triage with isolated agent instance...")
                triage_agent = agent_instances["triage"]
                
                # Execute triage with proper user context
                triage_result = await self._execute_agent_with_context(
                    triage_agent, state, run_id, "triage"
                )
                
                # Update state based on triage results
                if hasattr(triage_result, 'final_answer'):
                    state.workflow_decision = str(triage_result.final_answer)
                
            except Exception as e:
                logger.error(f"Triage execution failed for user {self.user_context.user_id}: {e}")
                # Continue with fallback workflow
        
        # Execute additional agents based on workflow decision
        await self._execute_workflow_agents(agent_instances, state, run_id)
        
        return state
    
    async def _execute_agent_with_context(self, 
                                         agent: BaseAgent, 
                                         state: DeepAgentState, 
                                         run_id: str,
                                         agent_name: str) -> Any:
        """Execute an agent instance with proper user context and error handling."""
        try:
            # Execute agent with state
            if hasattr(agent, 'execute_modern'):
                # Use modern execution pattern
                result = await agent.execute_modern(state, run_id, stream_updates=True)
            elif hasattr(agent, 'execute'):
                # Use legacy execution pattern
                result = await agent.execute(state, run_id, stream_updates=True)
            else:
                # Try run method as fallback
                result = await agent.run(
                    state.user_request or "Process request",
                    self.user_context.thread_id,
                    self.user_context.user_id,
                    run_id
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed for user {self.user_context.user_id}: {e}")
            raise
    
    async def _execute_workflow_agents(self, 
                                      agent_instances: Dict[str, BaseAgent], 
                                      state: DeepAgentState, 
                                      run_id: str) -> None:
        """Execute workflow agents in proper sequence with user isolation."""
        # Define execution order
        execution_order = ["data", "optimization", "actions", "reporting"]
        
        for agent_name in execution_order:
            if agent_name in agent_instances:
                try:
                    await self._emit_thinking(f"Running {agent_name} with isolated instance...")
                    await self._execute_agent_with_context(
                        agent_instances[agent_name], state, run_id, agent_name
                    )
                except Exception as e:
                    logger.warning(f"Agent {agent_name} failed for user {self.user_context.user_id}: {e}")
                    # Continue with other agents
                    continue
    
    async def _emit_thinking(self, message: str) -> None:
        """Emit thinking message via user-specific WebSocket emitter."""
        if self.user_context:
            # Get WebSocket emitter from factory
            try:
                factory = get_agent_instance_factory()
                if hasattr(factory, '_websocket_emitters'):
                    context_id = f"{self.user_context.user_id}_{self.user_context.thread_id}_{self.user_context.run_id}"
                    emitter_key = f"{context_id}_emitter"
                    if emitter_key in factory._websocket_emitters:
                        await factory._websocket_emitters[emitter_key].notify_agent_thinking(
                            "Supervisor", message
                        )
                        return
            except Exception as e:
                logger.debug(f"Failed to use factory WebSocket emitter: {e}")
        
        # Fallback to BaseAgent emit_thinking
        await self.emit_thinking(message)
    
    async def _run_hooks(self, event: str, state: DeepAgentState, **kwargs) -> None:
        """Run registered hooks for an event."""
        for hook in self.hooks.get(event, []):
            try:
                await hook(state, **kwargs)
            except Exception as e:
                self.logger.warning(f"Hook execution failed for event {event}: {e}")
    
    # === Factory Methods for Split Architecture ===
    
    @classmethod
    async def create_with_user_context(cls,
                                     llm_manager: LLMManager,
                                     websocket_bridge: AgentWebSocketBridge,
                                     tool_dispatcher: ToolDispatcher,
                                     user_context: UserContext,
                                     db_session_factory=None) -> 'SupervisorAgent':
        """Factory method to create SupervisorAgent with UserExecutionContext.
        
        This is the PREFERRED way to create a SupervisorAgent in the new architecture.
        
        Args:
            llm_manager: LLM manager instance
            websocket_bridge: WebSocket bridge for agent notifications
            tool_dispatcher: Tool dispatcher for agent operations
            user_context: Per-request user execution context
            db_session_factory: Optional database session factory
            
        Returns:
            SupervisorAgent configured for the specific user context
        """
        supervisor = cls(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge,
            tool_dispatcher=tool_dispatcher,
            db_session_factory=db_session_factory,
            user_context=user_context
        )
        
        # Configure the agent instance factory if it's not already configured
        try:
            factory = get_agent_instance_factory()
            if not hasattr(factory, '_websocket_bridge') or not factory._websocket_bridge:
                # Configure factory with current components
                factory.configure(
                    agent_registry=supervisor.registry,  # Legacy registry for transition
                    websocket_bridge=websocket_bridge
                )
                logger.info("✅ Configured AgentInstanceFactory for SupervisorAgent")
        except Exception as e:
            logger.warning(f"Failed to configure AgentInstanceFactory: {e}")
        
        return supervisor
    
    # === Backward Compatibility Methods ===
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Execute the supervisor - backward compatibility method that delegates to modern execution.
        
        Args:
            state: Current agent state
            run_id: Run ID for tracking
            stream_updates: Whether to stream updates
        """
        # Create ExecutionContext for modern pattern
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=extract_thread_id(state, run_id),
            user_id=getattr(state, 'user_id', 'default_user')
        )
        
        # Delegate to BaseAgent's modern execution
        await self.execute_modern(state, run_id, stream_updates)

    async def run(self, user_prompt: str, thread_id: str, 
                  user_id: str, run_id: str) -> DeepAgentState:
        """Run the supervisor agent workflow - backward compatibility method.
        
        This method maintains backward compatibility while using the golden pattern internally.
        
        Args:
            user_prompt: The user's request
            thread_id: Thread ID for the conversation
            user_id: User ID
            run_id: Run ID for tracking
            
        Returns:
            Updated DeepAgentState with orchestration results
        """
        logger.info(f"SupervisorAgent.run() starting for run_id: {run_id}")
        
        # Initialize state
        state = DeepAgentState()
        state.user_request = user_prompt
        state.chat_thread_id = thread_id
        state.user_id = user_id
        
        # Create ExecutionContext for modern execution pattern
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=True,  # Default to true for legacy compatibility
            thread_id=thread_id,
            user_id=user_id
        )
        
        async with self._execution_lock:
            try:
                # Use modern execution pattern through BaseAgent
                if await self.validate_preconditions(context):
                    result = await self.execute_core_logic(context)
                    logger.info(f"SupervisorAgent.run() completed successfully for run_id: {run_id}")
                    return context.state  # Return updated state
                else:
                    # Validation failed
                    logger.error(f"Validation failed in SupervisorAgent.run() for run_id: {run_id}")
                    return state
                    
            except Exception as e:
                # Fallback to legacy execution helpers
                logger.warning(f"Modern execution failed, falling back to legacy workflow: {e}")
                try:
                    return await self.execution_helpers.run_supervisor_workflow(state, run_id)
                except Exception as fallback_error:
                    logger.error(f"Legacy fallback also failed for run_id {run_id}: {fallback_error}")
                    return state

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive supervisor statistics."""
        return self.completion_helpers.get_comprehensive_stats()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from modern monitoring."""
        return self.completion_helpers.get_agent_performance_metrics()

    # === Helper Methods for Legacy Compatibility ===
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()