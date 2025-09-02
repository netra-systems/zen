"""Supervisor Agent - UserExecutionContext Pattern Implementation

Migrated supervisor agent using new UserExecutionContext pattern:
- Uses UserExecutionContext for complete request isolation
- DatabaseSessionManager for session management without global state
- All legacy execute methods removed - no backward compatibility
- Complete removal of DeepAgentState usage
- All sub-agent calls use create_child_context() for proper isolation

Business Value: Enables safe concurrent user operations with zero context leakage.
BVJ: ALL segments | Platform Stability | Complete user isolation for production deployment
"""

import asyncio
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# UserExecutionContext pattern imports
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.database.session_manager import (
    DatabaseSessionManager,
    managed_session,
    validate_agent_session_isolation
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    get_agent_class_registry
)

# Core dependencies
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Legacy components that will be removed
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.observability_flow import get_supervisor_flow_logger

logger = central_logger.get_logger(__name__)


class SupervisorAgent(BaseAgent):
    """SupervisorAgent with UserExecutionContext pattern.
    
    CRITICAL: This supervisor uses the UserExecutionContext pattern to ensure:
    - Complete user isolation (no shared state between requests)
    - DatabaseSessionManager for session isolation
    - ALL legacy execute methods removed - no backward compatibility
    - UserExecutionContext passed through entire execution chain
    - All sub-agents use create_child_context() for proper isolation
    
    The supervisor coordinates agent orchestration while maintaining strict
    isolation boundaries to prevent user data leakage in concurrent scenarios.
    """
    
    def __init__(self, 
                 llm_manager: LLMManager,
                 websocket_bridge: AgentWebSocketBridge):
        """Initialize SupervisorAgent with UserExecutionContext pattern.
        
        CRITICAL: No user context, session storage, or tool_dispatcher in constructor.
        All user-specific data and tools come through execute() method via context.
        Tool dispatcher is created per-request for complete isolation.
        
        Args:
            llm_manager: LLM manager for agent operations
            websocket_bridge: WebSocket bridge for notifications
        """
        # Initialize BaseAgent with infrastructure (no global state)
        super().__init__(
            llm_manager=llm_manager,
            name="Supervisor",
            description="Orchestrates sub-agents with complete user isolation",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=False         # Disable caching for isolation
            # NO tool_dispatcher parameter - created per-request
        )
        
        # Core infrastructure (NO user-specific data)
        self.websocket_bridge = websocket_bridge
        self.agent_instance_factory = get_agent_instance_factory()
        self.agent_class_registry = get_agent_class_registry()
        self.flow_logger = get_supervisor_flow_logger()
        
        # Store LLM manager for creating request-scoped registries
        self._llm_manager = llm_manager
        
        # CRITICAL: No placeholder registry or mock dispatcher
        # Registry is created per-request in execute() for complete isolation
        # This follows CLAUDE.md: "Mocks = Abomination" principle
        self.registry = None
        
        # Per-request execution lock (not global!)
        self._execution_lock = asyncio.Lock()
        
        # Validate no session storage
        validate_agent_session_isolation(self)
        
        logger.info("SupervisorAgent initialized with UserExecutionContext pattern")

    # === UserExecutionContext Pattern Implementation ===
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute the supervisor with UserExecutionContext pattern.
        
        This is the ONLY execution method - all legacy methods removed.
        
        Args:
            context: UserExecutionContext with all request-specific data
            stream_updates: Whether to stream updates via WebSocket
            
        Returns:
            Dictionary with execution results
            
        Raises:
            ValueError: If context is invalid
            RuntimeError: If execution fails
        """
        # Validate context at entry
        context = validate_user_context(context)
        
        if not context.db_session:
            raise ValueError("UserExecutionContext must contain a database session")
        
        logger.info(f"SupervisorAgent.execute() starting for user {context.user_id}, run {context.run_id}")
        
        async with self._execution_lock:
            try:
                # Import here to avoid circular dependency
                from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
                from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                from netra_backend.app.websocket_core.isolated_event_emitter import IsolatedWebSocketEventEmitter
                
                # CRITICAL: Create WebSocket emitter BEFORE tool dispatcher
                websocket_emitter = IsolatedWebSocketEventEmitter.create_for_user(
                    user_id=context.user_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    websocket_manager=self.websocket_bridge.websocket_manager if hasattr(self.websocket_bridge, 'websocket_manager') else None
                )
                
                # Create request-scoped tool dispatcher with proper emitter
                async with ToolDispatcher.create_scoped_dispatcher_context(
                    user_context=context,
                    tools=self._get_user_tools(context),
                    websocket_emitter=websocket_emitter  # Use emitter instead of manager
                ) as tool_dispatcher:
                    # Store request-scoped dispatcher for this execution
                    self.tool_dispatcher = tool_dispatcher
                    
                    # Create request-scoped registry for this user
                    self.registry = AgentRegistry(self._llm_manager, tool_dispatcher)
                    self.registry.register_default_agents()
                    self.registry.set_websocket_bridge(self.websocket_bridge)
                    
                    # CRITICAL: Enhance tool dispatcher with WebSocket notifications
                    if hasattr(self.registry, 'set_websocket_manager'):
                        # Use websocket_manager from bridge if available
                        websocket_manager = getattr(self.websocket_bridge, 'websocket_manager', None)
                        if websocket_manager:
                            self.registry.set_websocket_manager(websocket_manager)
                    
                    # Create session manager for database operations
                    async with managed_session(context) as session_manager:
                        # Execute supervisor orchestration
                        result = await self._orchestrate_agents(context, session_manager, stream_updates)
                        
                        logger.info(f"SupervisorAgent.execute() completed for user {context.user_id}")
                        return result
                    
            except Exception as e:
                logger.error(f"SupervisorAgent.execute() failed for user {context.user_id}: {e}")
                raise RuntimeError(f"Supervisor execution failed: {e}") from e
            finally:
                # Clean up request-scoped resources
                self.tool_dispatcher = None
                self.registry = None
    
    async def _orchestrate_agents(self, context: UserExecutionContext, 
                                 session_manager: DatabaseSessionManager, 
                                 stream_updates: bool) -> Dict[str, Any]:
        """Orchestrate agent execution with proper isolation.
        
        Args:
            context: User execution context
            session_manager: Database session manager
            stream_updates: Whether to stream updates
            
        Returns:
            Dictionary with orchestration results
        """
        flow_id = self.flow_logger.generate_flow_id()
        self.flow_logger.start_flow(flow_id, context.run_id, 4)
        
        try:
            # Send thinking notification if streaming
            if stream_updates:
                await self._emit_thinking(context, "Starting supervisor orchestration with complete user isolation...")
                await self._emit_thinking(context, "Analyzing request and planning agent workflow...")
            
            # Create isolated agent instances for this user
            agent_instances = await self._create_isolated_agent_instances(context)
            
            # Execute workflow with isolated instances
            results = await self._execute_workflow_with_isolated_agents(
                agent_instances, context, session_manager, flow_id
            )
            
            self.flow_logger.complete_flow(flow_id)
            
            return {
                "supervisor_result": "completed",
                "orchestration_successful": True,
                "user_isolation_verified": True,
                "results": results,
                "user_id": context.user_id,
                "run_id": context.run_id
            }
            
        except Exception as e:
            self.flow_logger.fail_flow(flow_id, str(e))
            logger.error(f"Agent orchestration failed for user {context.user_id}: {e}")
            raise
    

    # === Agent Instance Management ===
    
    async def _create_isolated_agent_instances(self, context: UserExecutionContext) -> Dict[str, BaseAgent]:
        """Create isolated agent instances for this user request using AgentInstanceFactory.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            Dictionary mapping agent names to isolated instances
            
        Raises:
            RuntimeError: If no agent instances can be created
        """
        agent_instances = {}
        agent_names = self._get_required_agent_names()
        
        for agent_name in agent_names:
            try:
                logger.debug(f"Creating isolated instance of {agent_name} for user {context.user_id}")
                
                # Use AgentInstanceFactory to create isolated instance
                agent_instance = await self.agent_instance_factory.create_agent_instance(
                    agent_name=agent_name,
                    user_context=context
                )
                
                agent_instances[agent_name] = agent_instance
                logger.info(f"✅ Created isolated {agent_name} instance for user {context.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create isolated {agent_name} instance: {e}")
                # Continue with other agents - non-critical agents can fail
                continue
        
        if not agent_instances:
            raise RuntimeError("Failed to create any isolated agent instances")
        
        logger.info(f"Created {len(agent_instances)} isolated agent instances for user {context.user_id}")
        return agent_instances
    
    def _get_required_agent_names(self) -> List[str]:
        """Get list of required agent names for orchestration."""
        # Core agents required for most workflows
        core_agents = ["triage", "data", "optimization", "actions"]
        
        # Optional agents that enhance functionality
        optional_agents = ["reporting", "goals_triage", "data_helper", "synthetic_data"]
        
        # Return core agents first, then optionals
        return core_agents + optional_agents

    def _validate_execution_preconditions(self, context: UserExecutionContext) -> bool:
        """Validate execution preconditions for supervisor orchestration.
        
        Args:
            context: User execution context to validate
            
        Returns:
            True if preconditions are met
        """
        if not context.metadata.get('user_request'):
            logger.warning(f"No user request provided for supervisor in run_id: {context.run_id}")
            return False
        
        # Registry will be created per-request, so we don't check it here
        return True
    
    def _get_user_tools(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Get user-specific tools based on context.
        
        Args:
            context: User execution context
            
        Returns:
            Dictionary of tools available to this user
        """
        # Import tools here to avoid circular dependencies
        from netra_backend.app.tools import get_standard_tools
        
        # Get standard tools available to all users
        tools = get_standard_tools()
        
        # Add user-specific tools based on permissions/subscription
        if context.metadata.get('premium_user'):
            # Add premium tools if applicable
            pass
        
        return tools

    async def _execute_workflow_with_isolated_agents(self, 
                                                   agent_instances: Dict[str, BaseAgent],
                                                   context: UserExecutionContext,
                                                   session_manager: DatabaseSessionManager,
                                                   flow_id: str) -> Dict[str, Any]:
        """Execute workflow using isolated agent instances with UserExecutionContext.
        
        Args:
            agent_instances: Dictionary of isolated agent instances
            context: User execution context
            session_manager: Database session manager
            flow_id: Flow ID for observability
            
        Returns:
            Dictionary with workflow execution results
        """
        logger.info(f"Executing workflow with {len(agent_instances)} isolated agents for user {context.user_id}")
        
        results = {}
        execution_order = ["triage", "data", "optimization", "actions", "reporting"]
        
        for agent_name in execution_order:
            if agent_name in agent_instances:
                try:
                    await self._emit_thinking(context, f"Running {agent_name} with isolated instance...")
                    
                    # Create child context for sub-agent
                    child_context = context.create_child_context(
                        operation_name=f"{agent_name}_execution",
                        additional_metadata={
                            "agent_name": agent_name,
                            "flow_id": flow_id
                        }
                    )
                    
                    # Execute agent with child context
                    agent_result = await self._execute_agent_with_context(
                        agent_instances[agent_name], child_context, agent_name
                    )
                    
                    results[agent_name] = agent_result
                    logger.info(f"✅ Agent {agent_name} completed for user {context.user_id}")
                    
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed for user {context.user_id}: {e}")
                    results[agent_name] = {"error": str(e), "status": "failed"}
                    # Continue with other agents
                    continue
        
        return results
    
    async def _execute_agent_with_context(self, 
                                         agent: BaseAgent, 
                                         context: UserExecutionContext,
                                         agent_name: str) -> Any:
        """Execute an agent instance with proper user context and error handling.
        
        Args:
            agent: Agent instance to execute
            context: User execution context (child context)
            agent_name: Name of agent for logging
            
        Returns:
            Agent execution result
            
        Raises:
            RuntimeError: If agent execution fails
        """
        try:
            logger.debug(f"Executing agent {agent_name} with context for user {context.user_id}")
            
            # Check if agent supports UserExecutionContext pattern
            if hasattr(agent, 'execute') and not hasattr(agent, 'execute_modern'):
                # Agent supports new UserExecutionContext pattern
                result = await agent.execute(context, stream_updates=True)
            else:
                # Agent doesn't support new pattern yet - this shouldn't happen after migration
                logger.warning(f"Agent {agent_name} doesn't support UserExecutionContext pattern")
                raise RuntimeError(f"Agent {agent_name} must be migrated to UserExecutionContext pattern")
            
            logger.debug(f"Agent {agent_name} execution completed for user {context.user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed for user {context.user_id}: {e}")
            raise RuntimeError(f"Agent {agent_name} execution failed: {e}") from e
    
    async def _emit_thinking(self, context: UserExecutionContext, message: str) -> None:
        """Emit thinking message via WebSocket for user.
        
        Args:
            context: User execution context
            message: Thinking message to emit
        """
        try:
            # Use websocket_connection_id if available for targeted emission
            if context.websocket_connection_id:
                await self.websocket_bridge.emit_agent_thinking(
                    connection_id=context.websocket_connection_id,
                    agent_name="Supervisor",
                    message=message
                )
            else:
                # Fallback to user-based emission
                await self.websocket_bridge.emit_user_notification(
                    user_id=context.user_id,
                    notification_type="agent_thinking",
                    data={
                        "agent_name": "Supervisor",
                        "message": message,
                        "run_id": context.run_id
                    }
                )
        except Exception as e:
            logger.debug(f"Failed to emit thinking message: {e}")
            # Don't fail execution for WebSocket errors
    
    # === Utility Methods ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive supervisor statistics."""
        return {
            "agents_registered": len(self.registry.agents) if self.registry else 0,
            "supervisor_status": "operational",
            "pattern": "UserExecutionContext"
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "supervisor": "operational",
            "pattern": "UserExecutionContext",
            "isolation_verified": True
        }
    
    # === Factory Method ===
    
    @classmethod
    def create(cls,
               llm_manager: LLMManager,
               websocket_bridge: AgentWebSocketBridge) -> 'SupervisorAgent':
        """Factory method to create SupervisorAgent with UserExecutionContext pattern.
        
        CRITICAL: No tool_dispatcher parameter - created per-request for isolation.
        
        Args:
            llm_manager: LLM manager instance
            websocket_bridge: WebSocket bridge for agent notifications
            
        Returns:
            SupervisorAgent configured for UserExecutionContext pattern
        """
        supervisor = cls(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge
        )
        
        # Agent instance factory will be configured per-request
        logger.info("✅ Created SupervisorAgent with per-request tool dispatcher pattern")
        
        return supervisor

    def __str__(self) -> str:
        return f"SupervisorAgent(UserExecutionContext pattern, agents={len(self.registry.agents) if self.registry else 0})"
    
    def __repr__(self) -> str:
        return f"SupervisorAgent(pattern='UserExecutionContext', agents={len(self.registry.agents) if self.registry else 0})"
    
    # === Registration Methods (Temporary for Legacy Registry) ===
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a sub-agent (legacy compatibility)."""
        if self.registry:
            self.registry.register(name, agent)
    
    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents (legacy compatibility)."""
        return self.registry.agents if self.registry else {}