"""MCP-Enhanced Execution Engine for Supervisor Agent.

Extends base execution engine with MCP tool routing and execution capabilities.
Follows strict 25-line function design and 450-line limit.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # CANONICAL IMPORT: Use direct import path for better SSOT compliance
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.mcp_integration.context_manager import MCPContextManager
from netra_backend.app.agents.mcp_integration.mcp_intent_detector import (
    MCPIntentDetector,
)
# DeepAgentState removed - using UserExecutionContext pattern
# from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.agents.execution_engine_interface import IExecutionEngine as ExecutionEngine
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.agent_mcp_bridge import AgentMCPBridge
# Import ExecutionEngine dependencies for _init_from_factory
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.observability_flow import get_supervisor_flow_logger

logger = central_logger.get_logger(__name__)


class MCPExecutionContext:
    """Context for MCP-enabled execution."""
    
    def __init__(self, base_context: AgentExecutionContext):
        self.base_context = base_context
        self.mcp_context = None
        self.requires_mcp = False
        self.mcp_server = None
        self.mcp_tool = None
    
    def set_mcp_requirements(self, server: str, tool: str) -> None:
        """Set MCP execution requirements."""
        self.requires_mcp = True
        self.mcp_server = server
        self.mcp_tool = tool
    
    def clear_mcp_requirements(self) -> None:
        """Clear MCP execution requirements."""
        self.requires_mcp = False
        self.mcp_server = None
        self.mcp_tool = None


class MCPRequestRouter:
    """Routes requests to appropriate execution path."""
    
    def __init__(self, intent_detector: MCPIntentDetector):
        self.intent_detector = intent_detector
    
    def analyze_request(self, user_context: Optional['UserExecutionContext']) -> Dict[str, Any]:
        """Analyze request for MCP requirements."""
        if not user_context or not user_context.metadata.get('current_request'):
            return {"requires_mcp": False}
        
        intent = self.intent_detector.detect_intent(user_context.metadata['current_request'])
        return self._build_routing_decision(intent)
    
    def _build_routing_decision(self, intent) -> Dict[str, Any]:
        """Build routing decision from MCP intent."""
        decision_data = self._extract_intent_data(intent)
        return self._format_routing_decision(decision_data)
    
    def _extract_intent_data(self, intent) -> Dict[str, Any]:
        """Extract data from MCP intent."""
        core_data = self._extract_intent_core_data(intent)
        meta_data = self._extract_intent_meta_data(intent)
        return {**core_data, **meta_data}

    def _extract_intent_core_data(self, intent) -> Dict[str, Any]:
        """Extract core intent data."""
        return {
            "requires_mcp": intent.requires_mcp,
            "server_name": intent.server_name,
            "tool_name": intent.tool_name
        }

    def _extract_intent_meta_data(self, intent) -> Dict[str, Any]:
        """Extract intent metadata."""
        return {
            "confidence": intent.confidence,
            "parameters": intent.parameters
        }
    
    def _format_routing_decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format routing decision data."""
        return decision_data
    
    def should_use_mcp(self, routing_info: Dict[str, Any]) -> bool:
        """Check if request should use MCP execution."""
        return (routing_info.get("requires_mcp", False) and 
                routing_info.get("confidence", 0) >= 0.5)


class MCPExecutionPlanner:
    """Plans MCP tool execution within agent pipeline."""
    
    def __init__(self, mcp_bridge: AgentMCPBridge):
        self.mcp_bridge = mcp_bridge
    
    async def plan_mcp_execution(self, context: MCPExecutionContext,
                                user_context: Optional['UserExecutionContext']) -> Dict[str, Any]:
        """Plan MCP tool execution strategy."""
        if not context.requires_mcp:
            return {"execution_type": "standard"}
        
        return await self._create_mcp_execution_plan(context, user_context)
    
    async def _create_mcp_execution_plan(self, context: MCPExecutionContext,
                                       user_context: Optional['UserExecutionContext']) -> Dict[str, Any]:
        """Create detailed MCP execution plan."""
        available_tools = await self._get_available_tools(context)
        plan_data = self._build_execution_plan_data(context, available_tools)
        return plan_data
    
    def _build_execution_plan_data(self, context: MCPExecutionContext,
                                  available_tools: List[str]) -> Dict[str, Any]:
        """Build execution plan data structure."""
        base_plan = self._create_base_plan(context)
        return self._add_plan_metadata(base_plan, available_tools)
    
    def _create_base_plan(self, context: MCPExecutionContext) -> Dict[str, Any]:
        """Create base execution plan."""
        return {
            "execution_type": "mcp",
            "server": context.mcp_server,
            "tool": context.mcp_tool
        }
    
    def _add_plan_metadata(self, base_plan: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """Add metadata to execution plan."""
        base_plan["available_tools"] = available_tools
        base_plan["fallback_strategy"] = "standard_agent"
        return base_plan
    
    async def _get_available_tools(self, context: MCPExecutionContext) -> List[str]:
        """Get available tools for MCP server."""
        if not context.mcp_context:
            return []
        return await self._discover_tools_safely(context)
    
    async def _discover_tools_safely(self, context: MCPExecutionContext) -> List[str]:
        """Discover tools with error handling."""
        try:
            tools = await self.mcp_bridge.discover_tools(
                context.mcp_context, context.mcp_server)
            return [tool.name for tool in tools]
        except Exception as e:
            return self._handle_tool_discovery_error(e)
    
    def _handle_tool_discovery_error(self, error: Exception) -> List[str]:
        """Handle tool discovery error."""
        logger.error(f"Failed to get available tools: {error}")
        return []


def create_mcp_enhanced_engine(user_context: 'UserExecutionContext',
                             registry: 'AgentRegistry',
                             websocket_bridge: 'WebSocketManager') -> 'MCPEnhancedExecutionEngine':
    """Factory method to create MCPEnhancedExecutionEngine for safe concurrent usage.
    
    This factory method ensures proper user isolation and follows the SSOT pattern
    for execution engine creation.
    
    Args:
        user_context: User execution context for complete isolation
        registry: Agent registry for agent lookup
        websocket_bridge: WebSocket bridge for event emission
        
    Returns:
        MCPEnhancedExecutionEngine: Isolated MCP execution engine for this request
    """
    return MCPEnhancedExecutionEngine._init_from_factory(
        registry=registry,
        websocket_manager=websocket_bridge,
        user_context=user_context
    )


class MCPEnhancedExecutionEngine(ExecutionEngine):
    """Execution engine enhanced with MCP capabilities."""
    
    MAX_CONCURRENT_AGENTS = 10  # Support 5 concurrent users (2 agents each)
    AGENT_EXECUTION_TIMEOUT = 30.0  # 30 seconds max per agent
    
    def __init__(self, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager', 
                 user_context: Optional['UserExecutionContext'] = None):
        """Private initializer - use factory methods instead.
        
        This raises RuntimeError to enforce factory pattern usage for user isolation.
        Use create_mcp_enhanced_engine() for proper instantiation.
        """
        raise RuntimeError(
            "Direct MCPEnhancedExecutionEngine instantiation is no longer supported. "
            "Use create_mcp_enhanced_engine(user_context, registry, websocket_bridge) "
            "for proper user isolation and concurrent execution safety."
        )
    
    @classmethod
    def _init_from_factory(cls, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager',
                          user_context: Optional['UserExecutionContext'] = None):
        """Internal factory initializer for creating request-scoped MCP engines.
        
        This method bypasses the __init__ RuntimeError and is only called
        by factory methods to create properly isolated instances.
        """
        # DEPRECATION WARNING: This execution engine is being phased out in favor of UserExecutionEngine
        import warnings
        warnings.warn(
            "This execution engine is deprecated. Use UserExecutionEngine via ExecutionEngineFactory.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Create instance without calling __init__
        instance = cls.__new__(cls)
        
        # Initialize parent ExecutionEngine attributes directly
        instance.registry = registry
        instance.websocket_bridge = websocket_manager
        instance.user_context = user_context
        
        # SECURITY FIX: Enforce mandatory AgentWebSocketBridge usage - no fallbacks allowed
        if not websocket_manager:
            raise RuntimeError(
                "AgentWebSocketBridge is mandatory for WebSocket security and user isolation. "
                "No fallback paths allowed."
            )
        
        # Validate that websocket_manager is an AgentWebSocketBridge (not a deprecated notifier)
        if not hasattr(websocket_manager, 'notify_agent_started'):
            raise RuntimeError(
                f"websocket_bridge must be AgentWebSocketBridge instance with proper notification methods. "
                f"Got: {type(websocket_manager)}. Deprecated WebSocketNotifier fallbacks are eliminated for security."
            )
        
        # Initialize ExecutionEngine state management attributes
        instance.active_runs = {}
        instance.run_history = []
        
        # Import execution tracker
        from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
        instance.execution_tracker = get_execution_tracker()
        
        # NEW: Per-user state isolation to prevent race conditions
        instance._user_execution_states = {}
        instance._user_state_locks = {}
        
        import asyncio
        instance._state_lock_creation_lock = asyncio.Lock()
        
        # Initialize parent components (ExecutionEngine methods)
        instance._init_execution_engine_components()
        instance._init_execution_engine_death_monitoring()
        
        # Initialize MCP-specific components
        instance._init_mcp_components()
        
        if instance.user_context:
            logger.info(f"MCPEnhancedExecutionEngine initialized with UserExecutionContext for user {instance.user_context.user_id}")
        
        return instance
    
    def _init_execution_engine_components(self) -> None:
        """Initialize execution engine components (copied from parent class)."""
        # Use AgentWebSocketBridge instead of creating WebSocketNotifier
        # periodic_update_manager removed - no longer needed
        self.periodic_update_manager = None
        self.agent_core = AgentExecutionCore(self.registry, self.websocket_bridge)
        # fallback_manager removed - no longer needed
        self.fallback_manager = None
        self.flow_logger = get_supervisor_flow_logger()
        
        # CONCURRENCY OPTIMIZATION: Semaphore for agent execution control
        self.execution_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_AGENTS)
        self.execution_stats = {
            'total_executions': 0,
            'concurrent_executions': 0,
            'queue_wait_times': [],
            'execution_times': [],
            'failed_executions': 0,
            'dead_executions': 0,
            'timeout_executions': 0
        }
    
    def _init_execution_engine_death_monitoring(self) -> None:
        """Initialize agent death monitoring callbacks (copied from parent class)."""
        # Register callbacks for death detection
        self.execution_tracker.register_death_callback(self._handle_agent_death)
        self.execution_tracker.register_timeout_callback(self._handle_agent_timeout)
    
    async def _handle_agent_death(self, execution_record) -> None:
        """Handle agent death detection (copied from parent class)."""
        logger.critical(f"💀 AGENT DEATH DETECTED: {execution_record.agent_name} (execution_id={execution_record.execution_id})")
        
        # Send death notification via WebSocket
        if hasattr(self.websocket_bridge, 'notify_agent_error'):
            await self.websocket_bridge.notify_agent_error(
                agent_name=execution_record.agent_name,
                error_message="Agent execution died unexpectedly",
                execution_id=execution_record.execution_id
            )
    
    async def _handle_agent_timeout(self, execution_record) -> None:
        """Handle agent timeout detection (copied from parent class)."""
        logger.warning(f"⏱️ AGENT TIMEOUT DETECTED: {execution_record.agent_name} (execution_id={execution_record.execution_id})")
        
        # Send timeout notification via WebSocket  
        if hasattr(self.websocket_bridge, 'notify_agent_error'):
            await self.websocket_bridge.notify_agent_error(
                agent_name=execution_record.agent_name,
                error_message="Agent execution timed out",
                execution_id=execution_record.execution_id
            )

    def _init_mcp_components(self) -> None:
        """Initialize MCP-specific components."""
        self.mcp_context_manager = MCPContextManager()
        self.mcp_intent_detector = MCPIntentDetector()
        self.mcp_bridge = AgentMCPBridge()
        self.request_router = MCPRequestRouter(self.mcp_intent_detector)
        self.execution_planner = MCPExecutionPlanner(self.mcp_bridge)
    
    async def execute_agent(self, context: AgentExecutionContext,
                           user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute agent with MCP capability detection."""
        mcp_context = await self._prepare_mcp_context(context, user_context)
        
        if mcp_context.requires_mcp:
            return await self._execute_with_mcp(mcp_context, user_context)
        return await super().execute_agent(context, user_context)
    
    async def _prepare_mcp_context(self, context: AgentExecutionContext,
                                  user_context: Optional['UserExecutionContext']) -> MCPExecutionContext:
        """Prepare MCP execution context."""
        mcp_context = MCPExecutionContext(context)
        routing_info = self.request_router.analyze_request(user_context)
        await self._apply_mcp_routing(mcp_context, routing_info, context)
        return mcp_context

    async def _apply_mcp_routing(self, mcp_context: MCPExecutionContext, 
                                routing_info: Dict[str, Any], context: AgentExecutionContext) -> None:
        """Apply MCP routing if required."""
        if self.request_router.should_use_mcp(routing_info):
            await self._setup_mcp_execution(mcp_context, routing_info, context)
    
    async def _setup_mcp_execution(self, mcp_context: MCPExecutionContext,
                                  routing_info: Dict[str, Any],
                                  base_context: AgentExecutionContext) -> None:
        """Setup MCP execution requirements."""
        server, tool = self._extract_routing_params(routing_info)
        if server and tool:
            await self._configure_mcp_context(mcp_context, server, tool, base_context)

    def _extract_routing_params(self, routing_info: Dict[str, Any]) -> tuple[str, str]:
        """Extract server and tool from routing info."""
        return routing_info.get("server_name"), routing_info.get("tool_name")

    async def _configure_mcp_context(self, mcp_context: MCPExecutionContext, 
                                    server: str, tool: str, base_context: AgentExecutionContext) -> None:
        """Configure MCP context with server and tool."""
        mcp_context.set_mcp_requirements(server, tool)
        mcp_context.mcp_context = await self._create_agent_mcp_context(base_context)
    
    async def _create_agent_mcp_context(self, context: AgentExecutionContext):
        """Create MCP context for agent."""
        return await self.mcp_context_manager.create_agent_context(
            agent_name=context.agent_name,
            user_id=context.user_id,
            run_id=context.run_id,
            thread_id=context.thread_id
        )
    
    async def _execute_with_mcp(self, mcp_context: MCPExecutionContext,
                               user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Execute agent with MCP tool integration."""
        try:
            execution_plan = await self.execution_planner.plan_mcp_execution(mcp_context, user_context)
            return await self._execute_mcp_plan(mcp_context, user_context, execution_plan)
        except Exception as e:
            return await self._handle_mcp_execution_error(e, mcp_context, user_context)

    async def _handle_mcp_execution_error(self, error: Exception, mcp_context: MCPExecutionContext, 
                                         user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Handle MCP execution error with fallback."""
        logger.error(f"MCP execution failed: {error}")
        return await self._fallback_to_standard_execution(mcp_context.base_context, user_context)
    
    async def _execute_mcp_plan(self, mcp_context: MCPExecutionContext,
                               user_context: Optional['UserExecutionContext'],
                               execution_plan: Dict[str, Any]) -> AgentExecutionResult:
        """Execute the planned MCP strategy."""
        if execution_plan["execution_type"] == "mcp":
            return await self._execute_mcp_tool(mcp_context, user_context, execution_plan)
        return await super().execute_agent(mcp_context.base_context, user_context)
    
    async def _execute_mcp_tool(self, mcp_context: MCPExecutionContext,
                               user_context: Optional['UserExecutionContext'],
                               execution_plan: Dict[str, Any]) -> AgentExecutionResult:
        """Execute MCP tool directly."""
        try:
            result = await self._perform_mcp_tool_execution(mcp_context, user_context, execution_plan)
            return self._create_mcp_success_result(mcp_context, user_context, result)
        except Exception as e:
            return self._handle_mcp_tool_error(mcp_context, user_context, e)

    async def _perform_mcp_tool_execution(self, mcp_context: MCPExecutionContext, 
                                         user_context: Optional['UserExecutionContext'], execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual MCP tool execution."""
        await self._notify_tool_execution(mcp_context, execution_plan)
        return await self._execute_tool_with_bridge(mcp_context, user_context, execution_plan)
    
    async def _notify_tool_execution(self, mcp_context: MCPExecutionContext,
                                    execution_plan: Dict[str, Any]) -> None:
        """Notify about tool execution start."""
        await self.websocket_notifier.send_tool_executing(
            mcp_context.base_context, execution_plan["tool"])
    
    async def _execute_tool_with_bridge(self, mcp_context: MCPExecutionContext,
                                       user_context: Optional['UserExecutionContext'],
                                       execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool using MCP bridge."""
        return await self._call_bridge_execution(mcp_context, user_context, execution_plan)
    
    async def _call_bridge_execution(self, mcp_context: MCPExecutionContext,
                                    user_context: Optional['UserExecutionContext'],
                                    execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Call bridge for tool execution."""
        bridge_params = self._prepare_bridge_params(mcp_context, execution_plan, user_context)
        return await self.mcp_bridge.execute_tool_for_agent(**bridge_params)

    def _prepare_bridge_params(self, mcp_context: MCPExecutionContext, 
                              execution_plan: Dict[str, Any], user_context: Optional['UserExecutionContext']) -> Dict[str, Any]:
        """Prepare parameters for bridge execution."""
        return {
            "mcp_context": mcp_context.mcp_context,
            "server": execution_plan["server"],
            "tool": execution_plan["tool"],
            "arguments": self._extract_tool_arguments(user_context)
        }
    
    def _handle_mcp_tool_error(self, mcp_context: MCPExecutionContext, user_context: Optional['UserExecutionContext'], error: Exception) -> AgentExecutionResult:
        """Handle MCP tool execution error."""
        logger.error(f"MCP tool execution failed: {error}")
        return self._create_mcp_error_result(mcp_context, user_context, error)
    
    def _extract_tool_arguments(self, user_context: Optional['UserExecutionContext']) -> Dict[str, Any]:
        """Extract tool arguments from state."""
        return user_context.metadata.get('tool_arguments', {}) if user_context else {}
    
    def _create_mcp_success_result(self, mcp_context: MCPExecutionContext,
                                  user_context: Optional['UserExecutionContext'], 
                                  mcp_result: Dict[str, Any]) -> AgentExecutionResult:
        """Create successful MCP execution result."""
        if user_context:
            user_context.metadata["mcp_tool_result"] = mcp_result
        metadata = self._build_success_metadata(mcp_result)
        return AgentExecutionResult(success=True, agent_name=mcp_context.base_context.agent_name, user_context=user_context, metadata=metadata)

    def _build_success_metadata(self, mcp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata for successful MCP result."""
        return {"execution_type": "mcp", "mcp_result": mcp_result}
    
    def _create_mcp_error_result(self, mcp_context: MCPExecutionContext,
                                user_context: Optional['UserExecutionContext'], 
                                error: Exception) -> AgentExecutionResult:
        """Create error result for MCP execution."""
        error_message = f"MCP execution failed: {str(error)}"
        metadata = {"execution_type": "mcp_failed"}
        return AgentExecutionResult(success=False, agent_name=mcp_context.base_context.agent_name, user_context=user_context, error=error_message, metadata=metadata)
    
    async def _fallback_to_standard_execution(self, context: AgentExecutionContext,
                                             user_context: Optional['UserExecutionContext']) -> AgentExecutionResult:
        """Fallback to standard agent execution."""
        logger.info(f"Falling back to standard execution for {context.agent_name}")
        return await super().execute_agent(context, user_context)
    
    def cleanup_mcp_context(self, run_id: str) -> None:
        """Cleanup MCP context after execution."""
        self.mcp_context_manager.cleanup_context(run_id)