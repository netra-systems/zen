"""MCP-Enhanced Execution Engine for Supervisor Agent.

Extends base execution engine with MCP tool routing and execution capabilities.
Follows strict 25-line function design and 450-line limit.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.agents.mcp_integration.context_manager import MCPContextManager
from netra_backend.app.agents.mcp_integration.mcp_intent_detector import (
    MCPIntentDetector,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.agent_mcp_bridge import AgentMCPBridge

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
    
    def analyze_request(self, state: DeepAgentState) -> Dict[str, Any]:
        """Analyze request for MCP requirements."""
        if not state.current_request:
            return {"requires_mcp": False}
        
        intent = self.intent_detector.detect_intent(state.current_request)
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
                                state: DeepAgentState) -> Dict[str, Any]:
        """Plan MCP tool execution strategy."""
        if not context.requires_mcp:
            return {"execution_type": "standard"}
        
        return await self._create_mcp_execution_plan(context, state)
    
    async def _create_mcp_execution_plan(self, context: MCPExecutionContext,
                                       state: DeepAgentState) -> Dict[str, Any]:
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


class MCPEnhancedExecutionEngine(ExecutionEngine):
    """Execution engine enhanced with MCP capabilities."""
    
    def __init__(self, registry: 'AgentRegistry', websocket_manager: 'WebSocketManager'):
        super().__init__(registry, websocket_manager)
        self._init_mcp_components()
    
    def _init_mcp_components(self) -> None:
        """Initialize MCP-specific components."""
        self.mcp_context_manager = MCPContextManager()
        self.mcp_intent_detector = MCPIntentDetector()
        self.mcp_bridge = AgentMCPBridge()
        self.request_router = MCPRequestRouter(self.mcp_intent_detector)
        self.execution_planner = MCPExecutionPlanner(self.mcp_bridge)
    
    async def execute_agent(self, context: AgentExecutionContext,
                           state: DeepAgentState) -> AgentExecutionResult:
        """Execute agent with MCP capability detection."""
        mcp_context = await self._prepare_mcp_context(context, state)
        
        if mcp_context.requires_mcp:
            return await self._execute_with_mcp(mcp_context, state)
        return await super().execute_agent(context, state)
    
    async def _prepare_mcp_context(self, context: AgentExecutionContext,
                                  state: DeepAgentState) -> MCPExecutionContext:
        """Prepare MCP execution context."""
        mcp_context = MCPExecutionContext(context)
        routing_info = self.request_router.analyze_request(state)
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
                               state: DeepAgentState) -> AgentExecutionResult:
        """Execute agent with MCP tool integration."""
        try:
            execution_plan = await self.execution_planner.plan_mcp_execution(mcp_context, state)
            return await self._execute_mcp_plan(mcp_context, state, execution_plan)
        except Exception as e:
            return await self._handle_mcp_execution_error(e, mcp_context, state)

    async def _handle_mcp_execution_error(self, error: Exception, mcp_context: MCPExecutionContext, 
                                         state: DeepAgentState) -> AgentExecutionResult:
        """Handle MCP execution error with fallback."""
        logger.error(f"MCP execution failed: {error}")
        return await self._fallback_to_standard_execution(mcp_context.base_context, state)
    
    async def _execute_mcp_plan(self, mcp_context: MCPExecutionContext,
                               state: DeepAgentState,
                               execution_plan: Dict[str, Any]) -> AgentExecutionResult:
        """Execute the planned MCP strategy."""
        if execution_plan["execution_type"] == "mcp":
            return await self._execute_mcp_tool(mcp_context, state, execution_plan)
        return await super().execute_agent(mcp_context.base_context, state)
    
    async def _execute_mcp_tool(self, mcp_context: MCPExecutionContext,
                               state: DeepAgentState,
                               execution_plan: Dict[str, Any]) -> AgentExecutionResult:
        """Execute MCP tool directly."""
        try:
            result = await self._perform_mcp_tool_execution(mcp_context, state, execution_plan)
            return self._create_mcp_success_result(state, result)
        except Exception as e:
            return self._handle_mcp_tool_error(state, e)

    async def _perform_mcp_tool_execution(self, mcp_context: MCPExecutionContext, 
                                         state: DeepAgentState, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual MCP tool execution."""
        await self._notify_tool_execution(mcp_context, execution_plan)
        return await self._execute_tool_with_bridge(mcp_context, state, execution_plan)
    
    async def _notify_tool_execution(self, mcp_context: MCPExecutionContext,
                                    execution_plan: Dict[str, Any]) -> None:
        """Notify about tool execution start."""
        await self.websocket_notifier.send_tool_executing(
            mcp_context.base_context, execution_plan["tool"])
    
    async def _execute_tool_with_bridge(self, mcp_context: MCPExecutionContext,
                                       state: DeepAgentState,
                                       execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool using MCP bridge."""
        return await self._call_bridge_execution(mcp_context, state, execution_plan)
    
    async def _call_bridge_execution(self, mcp_context: MCPExecutionContext,
                                    state: DeepAgentState,
                                    execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Call bridge for tool execution."""
        bridge_params = self._prepare_bridge_params(mcp_context, execution_plan, state)
        return await self.mcp_bridge.execute_tool_for_agent(**bridge_params)

    def _prepare_bridge_params(self, mcp_context: MCPExecutionContext, 
                              execution_plan: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:
        """Prepare parameters for bridge execution."""
        return {
            "mcp_context": mcp_context.mcp_context,
            "server": execution_plan["server"],
            "tool": execution_plan["tool"],
            "arguments": self._extract_tool_arguments(state)
        }
    
    def _handle_mcp_tool_error(self, state: DeepAgentState, error: Exception) -> AgentExecutionResult:
        """Handle MCP tool execution error."""
        logger.error(f"MCP tool execution failed: {error}")
        return self._create_mcp_error_result(state, error)
    
    def _extract_tool_arguments(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract tool arguments from state."""
        return getattr(state, 'tool_arguments', {})
    
    def _create_mcp_success_result(self, state: DeepAgentState, 
                                  mcp_result: Dict[str, Any]) -> AgentExecutionResult:
        """Create successful MCP execution result."""
        state.add_result("mcp_tool_result", mcp_result)
        metadata = self._build_success_metadata(mcp_result)
        return AgentExecutionResult(success=True, state=state, metadata=metadata)

    def _build_success_metadata(self, mcp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata for successful MCP result."""
        return {"execution_type": "mcp", "mcp_result": mcp_result}
    
    def _create_mcp_error_result(self, state: DeepAgentState, 
                                error: Exception) -> AgentExecutionResult:
        """Create error result for MCP execution."""
        error_message = f"MCP execution failed: {str(error)}"
        metadata = {"execution_type": "mcp_failed"}
        return AgentExecutionResult(success=False, state=state, error=error_message, metadata=metadata)
    
    async def _fallback_to_standard_execution(self, context: AgentExecutionContext,
                                             state: DeepAgentState) -> AgentExecutionResult:
        """Fallback to standard agent execution."""
        logger.info(f"Falling back to standard execution for {context.agent_name}")
        return await super().execute_agent(context, state)
    
    def cleanup_mcp_context(self, run_id: str) -> None:
        """Cleanup MCP context after execution."""
        self.mcp_context_manager.cleanup_context(run_id)