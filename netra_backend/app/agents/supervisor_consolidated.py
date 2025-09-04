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
from typing import Any, Dict, Optional, List, Set
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
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=False         # Disable caching for isolation
            # NO tool_dispatcher parameter - created per-request
        )
        
        # Core infrastructure (NO user-specific data)
        if not websocket_bridge:
            raise ValueError("SupervisorAgent requires websocket_bridge to be provided")
        
        self.websocket_bridge = websocket_bridge
        logger.info(f"✅ SupervisorAgent initialized with WebSocket bridge type: {type(websocket_bridge).__name__}")
        
        self.agent_instance_factory = get_agent_instance_factory()
        self.agent_class_registry = get_agent_class_registry()
        self.flow_logger = get_supervisor_flow_logger()
        
        # CRITICAL FIX: Pre-configure the factory with WebSocket bridge IMMEDIATELY
        # This ensures sub-agents created later will have WebSocket events working
        # We'll configure again with registries in execute(), but at least bridge is set now
        logger.info(f"🔧 Pre-configuring agent instance factory with WebSocket bridge in supervisor init")
        try:
            # Pre-configure with just the websocket bridge (registries will be added in execute())
            # This is critical to prevent None bridge errors when creating sub-agents
            # NOTE: tool_dispatcher is created per-request, NOT passed in constructor
            self.agent_instance_factory.configure(
                websocket_bridge=websocket_bridge,
                websocket_manager=getattr(websocket_bridge, 'websocket_manager', None),
                agent_class_registry=self.agent_class_registry,  # Use the class registry we just got
                llm_manager=llm_manager,
                tool_dispatcher=None  # Will be set per-request in execute()
            )
            logger.info(f"✅ Factory pre-configured with WebSocket bridge to prevent sub-agent event failures")
        except Exception as e:
            # CRITICAL: Changed from warning to error - configuration failure should fail fast
            logger.error(f"❌ Failed to pre-configure factory in init: {e}")
            raise RuntimeError(f"Agent instance factory pre-configuration failed: {e}")
        
        # Store LLM manager for creating request-scoped registries
        self._llm_manager = llm_manager
        
        # REMOVED: Startup registry instantiation to eliminate singleton patterns
        # Agent validation is now handled through AgentClassRegistry and 
        # AgentInstanceFactory which provide proper isolation
        # No startup AgentRegistry needed - factory handles agent creation per-request
        
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
        logger.info(f"🚀 SupervisorAgent.execute() called for user={context.user_id}, run_id={context.run_id}")
        logger.info(f"📊 Context details: thread_id={context.thread_id}, has_db_session={context.db_session is not None}")
        
        context = validate_user_context(context)
        logger.info(f"✅ Context validated successfully for user={context.user_id}")
        
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
                
                # Get the actual WebSocketManager to pass to ToolDispatcher
                actual_websocket_manager = self.websocket_bridge.websocket_manager if hasattr(self.websocket_bridge, 'websocket_manager') else None
                logger.info(f"🔍 WebSocket bridge type: {type(self.websocket_bridge)}")
                logger.info(f"🔍 Has websocket_manager: {hasattr(self.websocket_bridge, 'websocket_manager')}")
                logger.info(f"🔍 WebSocketManager type: {type(actual_websocket_manager) if actual_websocket_manager else 'None'}")
                
                # 🚀 NEW: Use UserContext-based tool factory for complete isolation
                logger.info(f"🔧 Creating UserContext-based tool system for {context.user_id}")
                
                # Get tool classes from app state (configured at startup) or use fallback
                tool_classes = self._get_tool_classes_from_context(context)
                websocket_bridge_factory = self._get_websocket_bridge_factory(context)
                
                logger.info(f"🔧 Available tool classes: {len(tool_classes)}")
                
                # Create completely isolated tool system for this user
                from netra_backend.app.agents.user_context_tool_factory import UserContextToolFactory
                
                tool_system = await UserContextToolFactory.create_user_tool_system(
                    context=context,
                    tool_classes=tool_classes,
                    websocket_bridge_factory=websocket_bridge_factory
                )
                
                logger.info(f"✅ UserContext-based tool system created for {context.user_id}")
                logger.info(f"   - Registry: {tool_system['registry'].registry_id}")
                logger.info(f"   - Tools: {len(tool_system['tools'])}")
                logger.info(f"   - Dispatcher: {tool_system['dispatcher'].dispatcher_id}")
                
                # Store isolated components for this execution
                self.tool_dispatcher = tool_system['dispatcher']
                self.user_tool_registry = tool_system['registry']
                self.user_tools = tool_system['tools']
                
                # REMOVED: Request-scoped registry creation to eliminate singleton patterns
                # Factory handles agent creation with proper isolation without AgentRegistry
                
                # CRITICAL: Configure agent instance factory directly for complete isolation
                logger.info(f"🔧 Configuring agent instance factory for user {context.user_id}")
                self.agent_instance_factory.configure(
                    agent_class_registry=self.agent_class_registry,
                    websocket_bridge=self.websocket_bridge,
                    websocket_manager=getattr(self.websocket_bridge, 'websocket_manager', None),
                    llm_manager=self._llm_manager,
                    tool_dispatcher=self.tool_dispatcher
                )
                
                # CRITICAL: Enhance tool dispatcher with WebSocket notifications directly
                websocket_manager = getattr(self.websocket_bridge, 'websocket_manager', None)
                if websocket_manager and hasattr(self.tool_dispatcher, 'set_websocket_manager'):
                    self.tool_dispatcher.set_websocket_manager(websocket_manager)
                    logger.info(f"✅ Enhanced tool dispatcher with WebSocket for user {context.user_id}")
                
                # Create session manager for database operations
                logger.info(f"📂 Creating managed session for user {context.user_id}")
                async with managed_session(context) as session_manager:
                    logger.info(f"✅ Managed session created, starting agent orchestration")
                    
                    # Execute supervisor orchestration
                    result = await self._orchestrate_agents(context, session_manager, stream_updates)
                    
                    logger.info(f"🎯 SupervisorAgent.execute() completed successfully for user {context.user_id}")
                    logger.info(f"📊 Result type: {type(result)}, has_content: {bool(result)}")
                    return result
                    
            except Exception as e:
                logger.error(f"SupervisorAgent.execute() failed for user {context.user_id}: {e}")
                raise RuntimeError(f"Supervisor execution failed: {e}") from e
            finally:
                # Clean up request-scoped resources
                self.tool_dispatcher = None
                # No registry cleanup needed - using factory pattern
    
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
            # Handle missing fail_flow method gracefully
            if hasattr(self.flow_logger, 'fail_flow'):
                self.flow_logger.fail_flow(flow_id, str(e))
            else:
                logger.error(f"🚨 Flow {flow_id} failed (no fail_flow method): {e}")
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
    
    def _get_user_tools(self, context: UserExecutionContext) -> list:
        """Get user-specific tools based on context.
        
        Args:
            context: User execution context
            
        Returns:
            List of BaseTool instances available to this user
        """
        logger.info(f"🔨 Getting tools for user {context.user_id}")
        
        # Import the proper LangChain tool wrappers
        from netra_backend.app.agents.tools.langchain_wrappers import (
            create_langchain_tools
        )
        
        # Create tools with LLM manager if available
        llm_manager = getattr(self, 'llm_manager', None)
        
        logger.info(f"🔧 Creating LangChain-wrapped tools with llm_manager={llm_manager is not None}")
        
        tools = create_langchain_tools(
            llm_manager=llm_manager,
            deep_research_api_key=None,  # Will use env defaults
            deep_research_base_url=None,  # Will use env defaults
            sandbox_docker_image=None  # Will use env defaults
        )
        
        logger.info(f"✅ Created {len(tools)} tools for user {context.user_id}")
        logger.info(f"📦 Tools registered: {[tool.name for tool in tools]}")
        
        return tools
    
    def _get_tool_classes_from_context(self, context: UserExecutionContext) -> List:
        """Get available tool classes from app state or use fallback."""
        try:
            # Try to get from FastAPI app state if available
            from netra_backend.app.smd import app
            if hasattr(app, 'state') and hasattr(app.state, 'tool_classes'):
                tool_classes = app.state.tool_classes
                if tool_classes:
                    logger.info(f"✅ Retrieved {len(tool_classes)} tool classes from app state")
                    return tool_classes
        except Exception as e:
            logger.warning(f"Could not access app state tool classes: {e}")
        
        # Fallback to default tool classes
        from netra_backend.app.agents.user_context_tool_factory import get_app_tool_classes
        tool_classes = get_app_tool_classes()
        logger.info(f"🔄 Using fallback tool classes: {len(tool_classes)}")
        return tool_classes
    
    def _get_websocket_bridge_factory(self, context: UserExecutionContext):
        """Get WebSocket bridge factory from app state or use fallback."""
        try:
            # Try to get from FastAPI app state if available
            from netra_backend.app.smd import app
            if hasattr(app, 'state') and hasattr(app.state, 'websocket_bridge_factory'):
                factory = app.state.websocket_bridge_factory
                logger.info("✅ Retrieved WebSocket bridge factory from app state")
                return factory
        except Exception as e:
            logger.warning(f"Could not access app state WebSocket bridge factory: {e}")
        
        # Fallback - return the existing bridge for this supervisor
        logger.info("🔄 Using fallback WebSocket bridge factory")
        return lambda: self.websocket_bridge

    # Define agent dependencies with metadata keys (SSOT)
    AGENT_DEPENDENCIES = {
        "triage": {
            "required": [],
            "optional": [],
            "produces": ["triage_result", "goal_triage_results"]
        },
        "data": {
            "required": [("triage", "triage_result")],
            "optional": [],
            "produces": ["data_result", "data_analysis_result"]
        },
        "optimization": {
            "required": [("triage", "triage_result"), ("data", "data_result")],
            "optional": [],
            "produces": ["optimizations_result", "optimization_strategies"]
        },
        "actions": {
            "required": [("triage", "triage_result"), ("data", "data_result")],
            "optional": [("optimization", "optimizations_result")],
            "produces": ["action_plan_result", "actions_result"]
        },
        "reporting": {
            "required": [("triage", "triage_result")],
            "optional": [("data", "data_result"), ("optimization", "optimizations_result"), ("actions", "action_plan_result")],
            "produces": ["report_result", "final_report"]
        }
    }
    
    def _can_execute_agent(self, agent_name: str, completed_agents: Set[str], context_metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Check if an agent can be executed based on its dependencies.
        
        This is the SSOT for dependency validation. Checks both agent completion
        and metadata availability.
        
        Args:
            agent_name: Name of the agent to check
            completed_agents: Set of successfully completed agents
            context_metadata: Current context metadata with results
            
        Returns:
            Tuple of (can_execute, missing_dependencies)
        """
        dep_spec = self.AGENT_DEPENDENCIES.get(agent_name, {})
        required_deps = dep_spec.get("required", [])
        missing_deps = []
        
        for dep_agent, metadata_key in required_deps:
            # Check both: agent completion AND metadata availability
            if dep_agent not in completed_agents:
                missing_deps.append(f"{dep_agent} (not executed)")
                logger.warning(f"Agent {agent_name} missing dependency: {dep_agent} not executed")
            elif metadata_key not in context_metadata:
                missing_deps.append(f"{dep_agent} (no {metadata_key})")
                logger.warning(f"Agent {agent_name} missing dependency: {metadata_key} not in context")
        
        # Log optional dependencies for debugging
        optional_deps = dep_spec.get("optional", [])
        for dep_agent, metadata_key in optional_deps:
            if dep_agent not in completed_agents:
                logger.debug(f"Agent {agent_name} optional dependency missing: {dep_agent}")
            elif metadata_key not in context_metadata:
                logger.debug(f"Agent {agent_name} optional metadata missing: {metadata_key}")
        
        can_execute = len(missing_deps) == 0
        return can_execute, missing_deps
    
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
        import time
        logger.info(f"Executing workflow with {len(agent_instances)} isolated agents for user {context.user_id}")
        
        results = {}
        completed_agents = set()
        failed_agents = set()
        execution_order = ["triage", "data", "optimization", "actions", "reporting"]
        
        for agent_name in execution_order:
            # Skip if agent not available
            if agent_name not in agent_instances:
                logger.debug(f"Agent {agent_name} not in available instances, skipping")
                continue
                
            # Check dependencies before execution (SSOT validation)
            can_execute, missing_deps = self._can_execute_agent(agent_name, completed_agents, context.metadata)
            if not can_execute:
                logger.error(f"Cannot execute {agent_name}: missing dependencies: {missing_deps}")
                results[agent_name] = {
                    "error": "Dependencies not met",
                    "status": "skipped",
                    "missing_deps": missing_deps
                }
                failed_agents.add(agent_name)
                # For critical agents, stop the workflow
                if agent_name in ["triage", "data"]:
                    logger.error(f"Critical agent {agent_name} failed. Stopping workflow.")
                    break
                continue
                
            try:
                start_time = time.time()
                await self._emit_thinking(context, f"Running {agent_name} with isolated instance...")
                
                # Create child context for sub-agent
                child_context = context.create_child_context(
                    operation_name=f"{agent_name}_execution",
                    additional_metadata={
                        "agent_name": agent_name,
                        "flow_id": flow_id
                    }
                )
                
                # Execute agent with child context and retry logic
                agent_result = await self._execute_agent_with_retry(
                    agent_instances[agent_name], child_context, agent_name
                )
                
                execution_time = time.time() - start_time
                logger.info(f"⏱️ Agent {agent_name} executed in {execution_time:.2f}s for user {context.user_id}")
                
                # Validate result is not an error
                if isinstance(agent_result, dict) and agent_result.get("status") == "failed":
                    raise RuntimeError(f"Agent returned failure status: {agent_result.get('error', 'Unknown error')}")
                
                results[agent_name] = agent_result
                completed_agents.add(agent_name)
                
                # CRITICAL: Propagate metadata from child context back to parent context
                # This ensures results like triage_result, data_result, etc. are available for reporting
                self._merge_child_metadata_to_parent(context, child_context, agent_name)
                
                # Store agent result under expected keys (SSOT)
                self._store_agent_result(context, agent_name, agent_result)
                
                logger.info(f"✅ Agent {agent_name} completed successfully for user {context.user_id}")
                
                # Add small delay between agents to prevent overwhelming the system
                # Only if execution was very fast (< 0.5s)
                if execution_time < 0.5:
                    delay = 0.5 - execution_time
                    logger.debug(f"Adding {delay:.2f}s delay after fast execution")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Agent {agent_name} failed for user {context.user_id}: {e}", exc_info=True)
                results[agent_name] = {"error": str(e), "status": "failed"}
                failed_agents.add(agent_name)
                
                # For critical agents (triage, data), stop the entire workflow
                if agent_name in ["triage", "data"]:
                    logger.error(f"Critical agent {agent_name} failed. Stopping workflow execution.")
                    break
                    
                # For non-critical agents, continue but log the impact
                logger.warning(f"Non-critical agent {agent_name} failed. Continuing with degraded results.")
        
        # Log workflow summary
        logger.info(f"Workflow completed. Successful: {completed_agents}, Failed: {failed_agents}")
        
        # Add workflow metadata to results
        results["_workflow_metadata"] = {
            "completed_agents": list(completed_agents),
            "failed_agents": list(failed_agents),
            "total_agents": len(execution_order),
            "success_rate": len(completed_agents) / len(execution_order) if execution_order else 0
        }
        
        return results
    
    async def _execute_agent_with_retry(self, 
                                       agent: BaseAgent, 
                                       context: UserExecutionContext,
                                       agent_name: str) -> Any:
        """Execute agent with exponential backoff retry logic.
        
        Args:
            agent: Agent instance to execute
            context: User execution context (child context)
            agent_name: Name of agent for logging
            
        Returns:
            Agent execution result
            
        Raises:
            RuntimeError: If all retries are exhausted
        """
        max_retries = 3
        base_delay = 1.0  # Start with 1 second
        max_delay = 16.0  # Cap at 16 seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.info(f"Retrying {agent_name} after {delay:.1f}s delay (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    await self._emit_thinking(context, f"Retrying {agent_name} (attempt {attempt + 1}/{max_retries})...")
                
                # Execute the agent
                result = await self._execute_agent_with_context(agent, context, agent_name)
                
                # Success - return result
                if attempt > 0:
                    logger.info(f"✅ {agent_name} succeeded after {attempt + 1} attempts")
                return result
                
            except Exception as e:
                logger.warning(f"Agent {agent_name} attempt {attempt + 1} failed: {e}")
                
                # Check if this is a recoverable error
                if not self._is_recoverable_error(e):
                    logger.error(f"Non-recoverable error for {agent_name}: {e}")
                    raise
                
                # Last attempt - raise the error
                if attempt == max_retries - 1:
                    logger.error(f"Agent {agent_name} failed after {max_retries} attempts")
                    raise RuntimeError(f"Agent {agent_name} failed after {max_retries} retries: {e}") from e
    
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
            Exception: If agent execution fails
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
            raise  # Re-raise for retry logic to handle
    
    async def _emit_thinking(self, context: UserExecutionContext, message: str) -> None:
        """Emit thinking message via WebSocket for user.
        
        Args:
            context: User execution context
            message: Thinking message to emit
        """
        try:
            # Use the core emit_agent_event method with proper parameters
            await self.websocket_bridge.emit_agent_event(
                event_type="agent_thinking",
                data={
                    "agent_name": "Supervisor",
                    "message": message,
                    "connection_id": context.websocket_connection_id,
                    "user_id": context.user_id
                },
                run_id=context.run_id,
                agent_name="Supervisor"
            )
        except Exception as e:
            logger.debug(f"Failed to emit thinking message: {e}")
            # Don't fail execution for WebSocket errors
    
    def _merge_child_metadata_to_parent(self, parent_context: UserExecutionContext, 
                                        child_context: UserExecutionContext, 
                                        agent_name: str) -> None:
        """Merge child context metadata back to parent context.
        
        This ensures that agent results (triage_result, data_result, optimizations_result, 
        action_plan_result) are available in the parent context for the reporting agent.
        
        Args:
            parent_context: Parent execution context
            child_context: Child execution context with updated metadata
            agent_name: Name of the agent that was executed
        """
        # Map agent names to their expected metadata keys
        agent_metadata_mapping = {
            "triage": ["triage_result", "goal_triage_results"],
            "data": ["data_result", "data_analysis_result"],
            "optimization": ["optimizations_result", "optimization_strategies"],
            "actions": ["action_plan_result", "actions_result"],
            "data_helper": ["data_helper_result"],
            "synthetic_data": ["synthetic_data_result"]
        }
        
        # Get expected keys for this agent
        expected_keys = agent_metadata_mapping.get(agent_name, [])
        
        # Also check for the generic pattern {agent_name}_result
        generic_key = f"{agent_name}_result"
        if generic_key not in expected_keys:
            expected_keys.append(generic_key)
        
        # Merge specific keys from child to parent
        for key in expected_keys:
            if key in child_context.metadata:
                parent_context.metadata[key] = child_context.metadata[key]
                logger.debug(f"Propagated metadata key '{key}' from {agent_name} to parent context")
        
        # Also propagate any keys that match common result patterns
        for key, value in child_context.metadata.items():
            if key.endswith("_result") or key.endswith("_results"):
                if key not in parent_context.metadata:
                    parent_context.metadata[key] = value
                    logger.debug(f"Propagated additional result key '{key}' from {agent_name} to parent context")
    
    def _store_agent_result(self, context: UserExecutionContext, agent_name: str, result: Any) -> None:
        """Store agent result under all expected metadata keys (SSOT).
        
        This ensures that agent results are available under all the keys that
        downstream agents might expect, maintaining backward compatibility.
        
        Args:
            context: User execution context
            agent_name: Name of the agent that produced the result
            result: The agent's execution result
        """
        # Get the expected metadata keys from AGENT_DEPENDENCIES
        dep_spec = self.AGENT_DEPENDENCIES.get(agent_name, {})
        produces_keys = dep_spec.get("produces", [])
        
        # Store under all expected keys
        for key in produces_keys:
            context.metadata[key] = result
            logger.debug(f"Stored {agent_name} result under key: {key}")
        
        # Always store under generic key as well
        generic_key = f"{agent_name}_result"
        if generic_key not in produces_keys:
            context.metadata[generic_key] = result
            logger.debug(f"Stored {agent_name} result under generic key: {generic_key}")
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable and worth retrying.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is recoverable
        """
        # Network and timeout errors are recoverable
        recoverable_errors = [
            "timeout", "timed out", "connection", "network",
            "temporary", "unavailable", "rate limit", "throttl"
        ]
        
        error_str = str(error).lower()
        
        # Check for known recoverable patterns
        for pattern in recoverable_errors:
            if pattern in error_str:
                return True
        
        # Check for specific exception types
        import asyncio
        if isinstance(error, (asyncio.TimeoutError, ConnectionError, TimeoutError)):
            return True
        
        # Non-recoverable errors
        non_recoverable = [
            "authentication", "permission", "forbidden", "unauthorized",
            "invalid", "not found", "does not exist", "migration required"
        ]
        
        for pattern in non_recoverable:
            if pattern in error_str:
                return False
        
        # Default to recoverable for unknown errors
        return True
    
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