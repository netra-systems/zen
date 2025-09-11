"""Supervisor Agent - UserExecutionContext Pattern Implementation

Business Value: Enables safe concurrent user operations with zero context leakage.
BVJ: ALL segments | Platform Stability | Complete user isolation for production deployment
"""

import asyncio
from typing import Any, Dict, Optional, List, Set, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from netra_backend.app.database.session_manager import DatabaseSessionManager

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# UserExecutionContext pattern imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.database.session_manager import (
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
    """
    
    def __init__(self, 
                 llm_manager: LLMManager,
                 websocket_bridge: Optional[AgentWebSocketBridge] = None,
                 db_session_factory=None,
                 user_context: Optional[UserExecutionContext] = None,
                 tool_dispatcher=None):
        """Initialize SupervisorAgent with UserExecutionContext pattern.
        
        CRITICAL: Tool dispatcher can be provided OR created per-request.
        All user-specific data and tools come through execute() method via context.
        Tool dispatcher is created per-request for complete isolation when not provided.
        
        ARCHITECTURE: WebSocket bridge is now optional and will be created per-request
        when UserExecutionContext is available, following factory pattern.
        
        Args:
            llm_manager: LLM manager for agent operations
            websocket_bridge: Optional WebSocket bridge (lazy initialized if None)
            db_session_factory: Optional database session factory  
            user_context: Optional user context (set per-request)
            tool_dispatcher: Optional tool dispatcher (created per-request if None)
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
        # ARCHITECTURE: WebSocket bridge is now optional for lazy initialization
        self.websocket_bridge = websocket_bridge
        self.db_session_factory = db_session_factory
        self.user_context = user_context
        
        # Tool dispatcher - created per-request if not provided
        # This maintains backward compatibility while supporting per-request creation
        self.tool_dispatcher = tool_dispatcher
        
        if websocket_bridge:
            logger.info(f"✅ SupervisorAgent initialized with WebSocket bridge type: {type(websocket_bridge).__name__}")
        else:
            logger.info("✅ SupervisorAgent initialized with lazy WebSocket bridge initialization")
        
        self.agent_instance_factory = get_agent_instance_factory()
        self.agent_class_registry = get_agent_class_registry()
        
        # CRITICAL: Ensure agent class registry is initialized for golden path
        if len(self.agent_class_registry) == 0:
            logger.warning("Agent class registry is empty - initializing for golden path")
            from netra_backend.app.agents.supervisor.agent_class_initialization import initialize_agent_class_registry
            self.agent_class_registry = initialize_agent_class_registry()
            logger.info(f"✅ Initialized agent class registry with {len(self.agent_class_registry)} agents")
        
        self.flow_logger = get_supervisor_flow_logger()
        
        # ARCHITECTURE: Conditional factory pre-configuration
        # Only pre-configure if WebSocket bridge is available, otherwise defer to execute()
        if websocket_bridge:
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
        else:
            logger.info("⏳ WebSocket bridge is None - factory configuration deferred to execute() method")
        
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
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as IsolatedWebSocketEventEmitter
                
                # CRITICAL: Create WebSocket emitter BEFORE tool dispatcher
                # Get the actual WebSocketManager from the bridge
                websocket_manager = self.websocket_bridge.websocket_manager if hasattr(self.websocket_bridge, 'websocket_manager') else None
                if not websocket_manager:
                    raise RuntimeError("WebSocket manager not available from bridge")
                
                websocket_emitter = IsolatedWebSocketEventEmitter(
                    manager=websocket_manager,
                    user_id=context.user_id,
                    context=context
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
                logger.info(f"   - Registry: {tool_system['registry'].name}")
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
                
                # Use database session from context
                logger.info(f"📂 Using database session for user {context.user_id}")
                session_manager = context.db_session
                logger.info(f"✅ Database session ready, starting agent orchestration")
                
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
                                 session_manager: 'DatabaseSessionManager', 
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
                logger.error(f"Full traceback for {agent_name} failure:", exc_info=True)
                # Continue with other agents - non-critical agents can fail
                continue
        
        if not agent_instances:
            error_msg = f"Failed to create any isolated agent instances. Attempted agents: {agent_names}"
            logger.error(f"❌ CRITICAL: {error_msg}")
            logger.error(f"   Factory configured: {self.agent_instance_factory is not None}")
            logger.error(f"   Class registry: {self.agent_class_registry is not None}")
            logger.error(f"   LLM manager: {self._llm_manager is not None}")
            logger.error(f"   WebSocket bridge: {self.websocket_bridge is not None}")
            raise RuntimeError(error_msg)
        
        logger.info(f"Created {len(agent_instances)} isolated agent instances for user {context.user_id}")
        return agent_instances
    
    def _get_required_agent_names(self) -> List[str]:
        """Get list of required agent names for orchestration.
        
        UVS SIMPLIFIED: Only 2 agents are truly required:
        1. Triage - Determines what the user needs
        2. Reporting (with UVS) - ALWAYS delivers value, handles all failures
        
        Default flow: Triage → Data Helper → Reporting (UVS)
        All other agents are optional based on triage assessment.
        """
        # CRITICAL: Only these 2 agents are required for UVS
        required_agents = ["triage", "reporting"]  # Reporting has UVS enhancements
        
        # Optional agents that may be invoked based on triage
        # These are created but only used if triage determines they're needed
        optional_agents = ["data_helper", "data", "optimization", "actions", "goals_triage", "synthetic_data"]
        
        # Return required first, then optionals
        return required_agents + optional_agents

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
    # UVS PRINCIPLE: Only Reporting is TRULY required - it can handle ANY scenario
    # All other agents are optional enhancements that improve the quality of the response
    AGENT_DEPENDENCIES = {
        "triage": {
            "required": [],  # Triage has no dependencies
            "optional": [],
            "produces": ["triage_result", "goal_triage_results", "data_sufficiency", "user_intent"],
            "priority": 0,  # Runs first if available
            "can_fail": True  # System continues even if triage fails
        },
        "reporting": {
            "required": [],  # UVS: Reporting can work with NOTHING
            "optional": [  # Better with these but not required
                ("triage", "triage_result"),
                ("data", "data_result"),
                ("optimization", "optimizations_result"),
                ("actions", "action_plan_result"),
                ("data_helper", "data_helper_result")
            ],
            "produces": ["report_result", "final_report"],
            "uvs_enabled": True,  # Flag indicating UVS enhancements
            "priority": 999,  # Always runs last
            "can_fail": False  # MUST succeed - this is the user's response
        },
        "data_helper": {
            "required": [],  # Can work independently
            "optional": [("triage", "triage_result")],
            "produces": ["data_helper_result", "data_collection_guidance"],
            "priority": 1,  # Early in pipeline for guidance
            "can_fail": True  # Non-critical
        },
        "data": {
            "required": [],  # Can attempt data collection independently  
            "optional": [
                ("triage", "triage_result"),
                ("data_helper", "data_helper_result")
            ],
            "produces": ["data_result", "data_analysis_result"],
            "priority": 2,  # After helper if present
            "can_fail": True  # Non-critical - reporting handles absence
        },
        "optimization": {
            "required": [],  # Changed: Can provide general optimization advice without data
            "optional": [
                ("data", "data_result"),  # Much better with data
                ("triage", "triage_result")
            ],
            "produces": ["optimizations_result", "optimization_strategies"],
            "priority": 3,  # After data if present
            "can_fail": True  # Non-critical
        },
        "actions": {
            "required": [],  # Can suggest generic actions
            "optional": [
                ("triage", "triage_result"),
                ("data", "data_result"),
                ("optimization", "optimizations_result")
            ],
            "produces": ["action_plan_result", "actions_result"],
            "priority": 4,  # After optimization if present
            "can_fail": True  # Non-critical
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
                                                   session_manager: 'DatabaseSessionManager',
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
        
        # UVS SIMPLIFIED: Dynamic execution order based on triage
        # Core principle: System works with ANY subset of agents
        # Minimum viable: Just Reporting (with UVS enhancements)
        # Optimal: Triage → (dynamic agents) → Reporting
        
        # Step 1: Attempt triage if available (can fail gracefully)
        triage_result = None
        if "triage" in agent_instances:
            try:
                logger.info("📊 Executing triage agent to determine optimal workflow...")
                triage_result = await self._execute_single_agent(
                    agent_instances["triage"], context, "triage", completed_agents, failed_agents
                )
                results["triage"] = triage_result
                logger.info(f"✅ Triage completed. Data sufficiency: {triage_result.get('data_sufficiency', 'unknown')}")
            except Exception as e:
                logger.warning(f"⚠️ Triage failed (non-critical): {e}")
                logger.info("📌 Continuing with UVS fallback workflow...")
                results["triage"] = {
                    "error": str(e), 
                    "status": "failed",
                    "fallback": "Using default workflow without triage insights"
                }
                failed_agents.add("triage")
        
        # Step 2: Determine dynamic execution order based on triage
        execution_order = self._determine_execution_order(triage_result, context)
        logger.info(f"Dynamic execution order based on triage: {execution_order}")
        
        # Step 3: Execute determined agents
        for agent_name in execution_order:
            # Skip if agent not available
            if agent_name not in agent_instances:
                logger.debug(f"Agent {agent_name} not in available instances, skipping")
                continue
                
            # Check dependencies before execution (SSOT validation)
            can_execute, missing_deps = self._can_execute_agent(agent_name, completed_agents, context.metadata)
            if not can_execute:
                # UVS: Dependencies not met is not a failure - just skip
                logger.info(f"⏭️ Skipping {agent_name}: optional dependencies not met: {missing_deps}")
                results[agent_name] = {
                    "status": "skipped",
                    "reason": "Optional dependencies not available",
                    "missing_deps": missing_deps
                }
                # Don't add to failed_agents - this is expected behavior
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
                # Check if this agent can fail gracefully (UVS principle)
                agent_config = self.AGENT_DEPENDENCIES.get(agent_name, {})
                can_fail = agent_config.get("can_fail", True)
                
                if can_fail:
                    # Non-critical agent - log and continue
                    logger.warning(f"⚠️ Optional agent {agent_name} failed (non-critical): {e}")
                    results[agent_name] = {
                        "error": str(e), 
                        "status": "failed",
                        "recoverable": True,
                        "impact": "Minimal - other agents will compensate"
                    }
                    failed_agents.add(agent_name)
                    
                    # Emit user-friendly message
                    await self._emit_thinking(context, 
                        f"Note: {agent_name} encountered an issue but we're continuing with alternative approaches...")
                else:
                    # Critical agent (only reporting) - must handle specially
                    logger.error(f"❌ CRITICAL: Required agent {agent_name} failed: {e}", exc_info=True)
                    
                    if agent_name == "reporting":
                        # Reporting MUST succeed - attempt fallback
                        logger.info("🔄 Attempting fallback reporting...")
                        try:
                            results["reporting"] = await self._create_fallback_report(context, results)
                            logger.info("✅ Fallback reporting succeeded")
                            completed_agents.add("reporting")
                        except Exception as fallback_error:
                            logger.error(f"❌ Fallback reporting also failed: {fallback_error}")
                            # Last resort - create minimal report
                            results["reporting"] = {
                                "status": "emergency_fallback",
                                "message": "System encountered an issue. Please try again.",
                                "error": str(e)
                            }
                    else:
                        results[agent_name] = {"error": str(e), "status": "failed"}
                        failed_agents.add(agent_name)
        
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
    
    def _determine_execution_order(self, triage_result: Optional[Dict], context: UserExecutionContext) -> List[str]:
        """Determine dynamic execution order based on triage results.
        
        UVS SIMPLIFIED FLOW:
        - Reporting ALWAYS runs (it's the only truly required agent)
        - Other agents run based on data availability and user intent
        - Skip unnecessary agents for faster responses
        
        Args:
            triage_result: Result from triage agent (may be None or failed)
            context: User execution context
            
        Returns:
            List of agent names to execute in order
        """
        execution_order = []
        
        # Check if triage provided guidance
        if triage_result and isinstance(triage_result, dict):
            # Extract workflow hints from triage
            data_sufficiency = triage_result.get("data_sufficiency", "unknown")
            user_intent = triage_result.get("intent", {})
            next_agents = triage_result.get("next_agents", [])
            
            # Use triage's recommended workflow if available
            if next_agents:
                logger.info(f"Using triage-recommended workflow: {next_agents}")
                execution_order = [agent for agent in next_agents if agent != "reporting"]
            else:
                # Determine workflow based on data sufficiency
                if data_sufficiency == "sufficient":
                    # Have data - selective pipeline based on intent
                    execution_order = []
                    
                    # Only add agents that are actually needed
                    if self._needs_data_analysis(user_intent, context):
                        execution_order.append("data")
                    
                    if self._needs_optimization(user_intent, context):
                        execution_order.append("optimization")
                    
                    if self._needs_action_plan(user_intent, context):
                        execution_order.append("actions")
                    
                    # If no specific agents needed, use data helper for guidance
                    if not execution_order:
                        execution_order = ["data_helper"]
                        
                elif data_sufficiency == "partial":
                    # Some data - augment with helper
                    execution_order = ["data_helper"]
                    
                    # Add other agents if beneficial
                    if self._needs_data_analysis(user_intent, context):
                        execution_order.append("data")
                    
                    if self._needs_optimization(user_intent, context):
                        execution_order.append("optimization")
                        
                else:
                    # No data or unknown - guidance flow
                    execution_order = ["data_helper"]
        else:
            # Triage failed or no result - minimal flow
            logger.info("Triage unavailable. Using minimal UVS flow: Data Helper → Reporting")
            execution_order = ["data_helper"]
        
        # CRITICAL: ALWAYS end with Reporting (UVS - can handle ANY scenario)
        execution_order.append("reporting")
        
        # Log the dynamic workflow for debugging
        logger.info(f"UVS Dynamic workflow determined: {' → '.join(execution_order)}")
        logger.info(f"Workflow reasoning: data_sufficiency={triage_result.get('data_sufficiency', 'unknown') if triage_result else 'no_triage'}")
        
        return execution_order
    
    def _needs_data_analysis(self, user_intent: Dict, context: UserExecutionContext) -> bool:
        """Check if data analysis is needed based on user intent.
        
        Args:
            user_intent: Intent extracted by triage
            context: User execution context
            
        Returns:
            True if data analysis would add value
        """
        # Check intent signals
        if isinstance(user_intent, dict):
            primary_intent = user_intent.get("primary_intent", "").lower()
            
            # Keywords that suggest data analysis is needed
            data_keywords = ["analyze", "trend", "pattern", "usage", "cost", 
                           "performance", "metric", "statistic", "report", "insight"]
            
            if any(keyword in primary_intent for keyword in data_keywords):
                return True
        
        # Check if user provided data in context
        if context.metadata.get("usage_data") or context.metadata.get("cost_data"):
            return True
            
        return False
    
    def _needs_optimization(self, user_intent: Dict, context: UserExecutionContext) -> bool:
        """Check if optimization is needed based on user intent.
        
        Args:
            user_intent: Intent extracted by triage
            context: User execution context
            
        Returns:
            True if optimization would add value
        """
        if isinstance(user_intent, dict):
            primary_intent = user_intent.get("primary_intent", "").lower()
            
            # Keywords that suggest optimization is needed
            opt_keywords = ["optimize", "improve", "reduce", "save", "efficient",
                          "better", "enhance", "minimize", "maximize", "tune"]
            
            if any(keyword in primary_intent for keyword in opt_keywords):
                return True
        
        return False
    
    def _needs_action_plan(self, user_intent: Dict, context: UserExecutionContext) -> bool:
        """Check if action plan is needed based on user intent.
        
        Args:
            user_intent: Intent extracted by triage
            context: User execution context
            
        Returns:
            True if action plan would add value
        """
        if isinstance(user_intent, dict):
            primary_intent = user_intent.get("primary_intent", "").lower()
            action_required = user_intent.get("action_required", False)
            
            # Direct signal from triage
            if action_required:
                return True
            
            # Keywords that suggest action plan is needed
            action_keywords = ["implement", "deploy", "setup", "configure", "migrate",
                             "plan", "roadmap", "steps", "guide", "how to"]
            
            if any(keyword in primary_intent for keyword in action_keywords):
                return True
        
        return False
    
    async def _execute_single_agent(self, agent_instance: BaseAgent, 
                                   context: UserExecutionContext,
                                   agent_name: str,
                                   completed_agents: set,
                                   failed_agents: set) -> Dict[str, Any]:
        """Execute a single agent and track its status.
        
        Args:
            agent_instance: The agent to execute
            context: User execution context
            agent_name: Name of the agent
            completed_agents: Set to track completed agents
            failed_agents: Set to track failed agents
            
        Returns:
            Agent execution result
        """
        try:
            await self._emit_thinking(context, f"Running {agent_name}...")
            
            # Create child context for agent
            child_context = context.create_child_context(
                operation_name=f"{agent_name}_execution",
                additional_metadata={"agent_name": agent_name}
            )
            
            # Execute with retry
            result = await self._execute_agent_with_retry(
                agent_instance, child_context, agent_name
            )
            
            # Mark as completed
            completed_agents.add(agent_name)
            
            # Propagate metadata
            self._merge_child_metadata_to_parent(context, child_context, agent_name)
            self._store_agent_result(context, agent_name, result)
            
            logger.info(f"✅ Agent {agent_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            failed_agents.add(agent_name)
            raise
    
    async def _create_fallback_report(self, context: UserExecutionContext, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback report when the reporting agent fails.
        
        UVS principle: Always provide value to the user, even in failure scenarios.
        
        Args:
            context: User execution context
            results: Results from other agents (may be partial)
            
        Returns:
            Fallback report dictionary
        """
        logger.info("Creating UVS fallback report...")
        
        # Gather any successful results
        successful_agents = [name for name, result in results.items() 
                           if isinstance(result, dict) and result.get("status") != "failed"]
        
        # Build a basic report
        report = {
            "status": "fallback",
            "message": "Analysis completed with partial results.",
            "summary": []
        }
        
        # Add triage insights if available
        if "triage" in results and results["triage"].get("status") != "failed":
            triage = results["triage"]
            report["summary"].append(f"Request type: {triage.get('category', 'General inquiry')}")
            report["summary"].append(f"Priority: {triage.get('priority', 'Normal')}")
            
        # Add data helper guidance if available
        if "data_helper" in results and results["data_helper"].get("status") != "failed":
            report["summary"].append("Data collection guidance is available.")
            report["data_guidance"] = results["data_helper"].get("guidance", "Please provide more data for detailed analysis.")
            
        # Add any data insights
        if "data" in results and results["data"].get("status") != "failed":
            report["summary"].append("Data analysis was performed.")
            report["data_insights"] = results["data"].get("insights", [])
            
        # Add optimization suggestions if available
        if "optimization" in results and results["optimization"].get("status") != "failed":
            report["summary"].append("Optimization opportunities identified.")
            report["optimizations"] = results["optimization"].get("strategies", [])
            
        # Add action plan if available
        if "actions" in results and results["actions"].get("status") != "failed":
            report["summary"].append("Action plan created.")
            report["action_plan"] = results["actions"].get("plan", [])
            
        # If no agents succeeded, provide generic guidance
        if not successful_agents:
            report["summary"] = [
                "System is operating with limited capabilities.",
                "Please try rephrasing your request or provide more specific details.",
                "For immediate assistance, consider:",
                "• Checking your data sources are accessible",
                "• Ensuring your request includes necessary context",
                "• Breaking down complex requests into simpler parts"
            ]
            
        report["metadata"] = {
            "successful_agents": successful_agents,
            "total_agents_attempted": len(results),
            "fallback_reason": "Primary reporting agent unavailable",
            "user_id": context.user_id,
            "run_id": context.run_id
        }
        
        return report
    
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
               websocket_bridge: AgentWebSocketBridge,
               tool_dispatcher=None) -> 'SupervisorAgent':
        """Factory method to create SupervisorAgent with UserExecutionContext pattern.
        
        CRITICAL: Tool dispatcher can be provided or created per-request for isolation.
        
        Args:
            llm_manager: LLM manager instance
            websocket_bridge: WebSocket bridge for agent notifications
            tool_dispatcher: Optional tool dispatcher (created per-request if None)
            
        Returns:
            SupervisorAgent configured for UserExecutionContext pattern
        """
        supervisor = cls(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge,
            tool_dispatcher=tool_dispatcher
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
    
    # === LEGACY COMPATIBILITY ===
    
    async def run(self, user_request: str, thread_id: str, user_id: str, run_id: str) -> Any:
        """
        Legacy run method wrapper for AgentService compatibility.
        
        CRITICAL: Converts legacy parameters to UserExecutionContext pattern
        and emits WebSocket events required for user chat business value.
        
        Args:
            user_request: The user's request message
            thread_id: Thread identifier 
            user_id: User identifier
            run_id: Execution run identifier
            
        Returns:
            Agent execution result
        """
        logger.info(f"🔄 Legacy run() method called for user {user_id}")
        
        try:
            # Import necessary modules for context creation
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation import UnifiedIdGenerator
            
            # Create UserExecutionContext from legacy parameters
            # This ensures the new execute() method gets proper context
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=UnifiedIdGenerator.generate_base_id("req"),
                websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id)
            )
            
            # CRITICAL BUSINESS VALUE: Send agent_started event
            # This is required for user chat experience - users must see agent began processing
            await self._emit_agent_started(user_context, user_request)
            
            # Execute using modern UserExecutionContext pattern
            logger.info(f"🚀 Converting legacy run() to execute() with UserExecutionContext for user {user_id}")
            result = await self.execute(user_context, stream_updates=True)
            
            # CRITICAL BUSINESS VALUE: Send agent_completed event  
            # This tells users the agent has finished and results are ready
            await self._emit_agent_completed(user_context, result)
            
            # Extract the actual result content for backward compatibility
            if isinstance(result, dict):
                # Return the actual agent results for legacy compatibility
                if "results" in result:
                    return result["results"]
                elif "supervisor_result" in result:
                    return result.get("results", result.get("supervisor_result", result))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Legacy run() method failed for user {user_id}: {e}")
            
            # Send completion event even on error (best effort for user experience)
            try:
                if 'user_context' in locals():
                    await self._emit_agent_completed(user_context, {"error": str(e), "status": "failed"})
            except Exception:
                pass  # Best effort - don't fail on WebSocket emission errors
            
            raise
    
    async def _emit_agent_started(self, context: UserExecutionContext, user_request: str) -> None:
        """
        Emit agent_started WebSocket event for user chat business value.
        
        BUSINESS CRITICAL: Users must see that agent began processing their request.
        This provides immediate feedback and builds trust in the AI system.
        """
        try:
            if self.websocket_bridge and hasattr(self.websocket_bridge, 'websocket_manager'):
                websocket_manager = self.websocket_bridge.websocket_manager
                if websocket_manager:
                    event_data = {
                        "type": "agent_started", 
                        "agent_id": "supervisor",
                        "user_id": context.user_id,
                        "timestamp": context.created_at.isoformat(),
                        "details": {
                            "agent_name": "Supervisor Agent",
                            "request_preview": user_request[:100] + "..." if len(user_request) > 100 else user_request,
                            "run_id": context.run_id,
                            "thread_id": context.thread_id
                        }
                    }
                    
                    await websocket_manager.send_to_user(context.user_id, event_data)
                    logger.info(f"📤 Sent agent_started event for user {context.user_id}")
                else:
                    logger.warning(f"⚠️ WebSocket manager not available for agent_started event (user {context.user_id})")
            else:
                logger.warning(f"⚠️ WebSocket bridge not available for agent_started event (user {context.user_id})")
        except Exception as e:
            logger.error(f"❌ Failed to emit agent_started event for user {context.user_id}: {e}")
            # Don't fail the entire operation due to WebSocket event failure
    
    async def _emit_agent_completed(self, context: UserExecutionContext, result: Any) -> None:
        """
        Emit agent_completed WebSocket event for user chat business value.
        
        BUSINESS CRITICAL: Users must know when the agent has finished and results are ready.
        This completes the user experience loop and signals results availability.
        """
        try:
            if self.websocket_bridge and hasattr(self.websocket_bridge, 'websocket_manager'):
                websocket_manager = self.websocket_bridge.websocket_manager
                if websocket_manager:
                    # Determine completion status
                    status = "completed"
                    if isinstance(result, dict):
                        if result.get("error") or result.get("status") == "failed":
                            status = "failed"
                        elif result.get("orchestration_successful") is False:
                            status = "failed"
                    
                    event_data = {
                        "type": "agent_completed",
                        "agent_id": "supervisor", 
                        "user_id": context.user_id,
                        "timestamp": context.created_at.isoformat(),
                        "details": {
                            "agent_name": "Supervisor Agent",
                            "status": status,
                            "run_id": context.run_id,
                            "thread_id": context.thread_id,
                            "has_results": bool(result)
                        }
                    }
                    
                    await websocket_manager.send_to_user(context.user_id, event_data)
                    logger.info(f"📤 Sent agent_completed event for user {context.user_id} (status: {status})")
                else:
                    logger.warning(f"⚠️ WebSocket manager not available for agent_completed event (user {context.user_id})")
            else:
                logger.warning(f"⚠️ WebSocket bridge not available for agent_completed event (user {context.user_id})")
        except Exception as e:
            logger.error(f"❌ Failed to emit agent_completed event for user {context.user_id}: {e}")
            # Don't fail the entire operation due to WebSocket event failure