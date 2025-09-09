"""Base MCP Agent with Modern Execution Patterns

Standardizes MCP execution with 99.9% reliability target using:
- Standardized execution patterns for consistent execution
- ReliabilityManager for circuit breaker/retry patterns
- ExecutionMonitor for performance tracking
- MCPContextManager for context management
- MCPIntentDetector for request routing

Business Value: Standardizes MCP execution across all agents,
eliminates duplicate patterns, ensures 99.9% reliability.
Target: Enterprise & Growth segments.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability import (
    CircuitBreakerConfig,
    ReliabilityManager,
)
from netra_backend.app.agents.mcp_integration.context_manager import (
    MCPAgentContext,
    MCPContextManager,
)
from netra_backend.app.agents.mcp_integration.mcp_intent_detector import (
    MCPIntent,
    MCPIntentDetector,
)
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.services.mcp_client_service import MCPClientService

logger = central_logger.get_logger(__name__)


@dataclass
class MCPExecutionConfig:
    """Configuration for MCP execution behavior."""
    enable_intent_detection: bool = True
    auto_route_mcp_requests: bool = True
    fallback_to_regular_execution: bool = True
    timeout_seconds: int = 30
    max_concurrent_tools: int = 3


@dataclass
class MCPExecutionResult:
    """Extended execution result with MCP-specific data."""
    base_result: ExecutionResult
    mcp_tools_executed: List[str] = None
    mcp_context: Optional[MCPAgentContext] = None
    intent_detected: Optional[MCPIntent] = None
    
    def __post_init__(self):
        """Initialize empty lists if not provided."""
        if self.mcp_tools_executed is None:
            self.mcp_tools_executed = []


class MCPExecutionErrorHandler:
    """Handles MCP-specific execution errors."""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, str]:
        """Load MCP error patterns for classification."""
        return {
            "connection_timeout": "MCP server connection timeout",
            "tool_not_found": "Requested MCP tool not available",
            "permission_denied": "MCP tool execution not permitted",
            "server_unavailable": "MCP server temporarily unavailable"
        }
    
    async def handle_mcp_error(self, context: ExecutionContext, 
                              error: Exception) -> ExecutionResult:
        """Handle MCP-specific errors with fallback strategies."""
        error_type = self._classify_error(error)
        error_message = self._create_error_message(error_type, error)
        should_fallback = self._should_attempt_fallback(error_type)
        return self._build_error_execution_result(error_message, should_fallback)

    def _build_error_execution_result(self, error_message: str, should_fallback: bool) -> ExecutionResult:
        """Build execution result for error scenarios."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_message,
            execution_time_ms=0.0,
            fallback_used=should_fallback
        )
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling."""
        error_str = str(error).lower()
        for pattern, classification in self.error_patterns.items():
            if pattern in error_str:
                return classification
        return "unknown_mcp_error"
    
    def _create_error_message(self, error_type: str, error: Exception) -> str:
        """Create formatted error message."""
        return f"MCP execution failed ({error_type}): {str(error)}"
    
    def _should_attempt_fallback(self, error_type: str) -> bool:
        """Determine if fallback execution should be attempted."""
        fallback_eligible = {"server_unavailable", "connection_timeout"}
        return error_type in fallback_eligible


class BaseMCPAgent(ABC):
    """Base MCP agent with standardized execution patterns.
    
    Provides MCP execution with reliability patterns, monitoring, and error handling.
    Uses ExecutionContext/ExecutionResult types for consistency.
    """
    
    def __init__(self, agent_name: str, 
                 mcp_service: Optional[MCPClientService] = None,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 config: Optional[MCPExecutionConfig] = None):
        self.agent_name = agent_name
        # Using single inheritance with standardized execution patterns
        self.mcp_service = mcp_service or MCPClientService()
        self.config = config or MCPExecutionConfig()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize MCP execution components."""
        self.mcp_context_manager = MCPContextManager(self.mcp_service)
        self.intent_detector = MCPIntentDetector()
        self.error_handler = MCPExecutionErrorHandler
        self._setup_reliability_patterns()
        self._setup_execution_engine()
    
    def _setup_reliability_patterns(self) -> None:
        """Setup circuit breaker and retry patterns."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.monitor = ExecutionMonitor()

    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name=f"mcp_{self.agent_name}",
            failure_threshold=3,
            recovery_timeout=30
        )

    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0
        )
    
    def _setup_execution_engine(self) -> None:
        """Setup execution engine with reliability components."""
        self.execution_engine = BaseExecutionEngine(
            reliability_manager=self.reliability_manager,
            monitor=self.monitor
        )
    
    async def execute_with_mcp_patterns(self, context: ExecutionContext) -> MCPExecutionResult:
        """Execute with full MCP patterns and monitoring."""
        base_result = await self.execution_engine.execute(self, context)
        return self._build_mcp_execution_result(context, base_result)

    def _build_mcp_execution_result(self, context: ExecutionContext, base_result: ExecutionResult) -> MCPExecutionResult:
        """Build MCP execution result from context and base result."""
        return MCPExecutionResult(
            base_result=base_result,
            mcp_tools_executed=getattr(context, 'mcp_tools_used', []),
            mcp_context=getattr(context, 'mcp_context', None),
            intent_detected=getattr(context, 'mcp_intent', None)
        )
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core MCP logic with intent detection and routing."""
        if not self._should_process_mcp(context):
            return await self.execute_regular_logic(context)
        
        return await self._execute_mcp_workflow(context)
    
    def _should_process_mcp(self, context: ExecutionContext) -> bool:
        """Determine if request should be processed with MCP patterns."""
        if not self.config.enable_intent_detection:
            return False
        
        request_text = self._extract_request_text(context)
        return self.intent_detector.should_route_to_mcp(request_text)
    
    def _extract_request_text(self, context: ExecutionContext) -> str:
        """Extract request text from execution context."""
        state_data = getattr(context.state, 'data', {})
        return state_data.get('request', state_data.get('message', ''))
    
    async def _execute_mcp_workflow(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute complete MCP workflow."""
        mcp_context = await self._create_mcp_context(context)
        intent = await self._detect_and_validate_intent(context, mcp_context)
        results = await self._execute_mcp_tools(context, mcp_context, intent)
        return await self._process_mcp_results(context, results)
    
    async def _create_mcp_context(self, context: ExecutionContext) -> MCPAgentContext:
        """Create MCP agent context for execution."""
        mcp_context = await self._build_mcp_agent_context(context)
        context.mcp_context = mcp_context
        return mcp_context

    async def _build_mcp_agent_context(self, context: ExecutionContext) -> MCPAgentContext:
        """Build MCP agent context from execution context."""
        return await self.mcp_context_manager.create_agent_context(
            agent_name=context.agent_name,
            user_id=context.user_id or "system",
            run_id=context.run_id,
            thread_id=context.thread_id or context.run_id
        )
    
    async def _detect_and_validate_intent(self, context: ExecutionContext,
                                        mcp_context: MCPAgentContext) -> MCPIntent:
        """Detect and validate MCP intent from request."""
        request_text = self._extract_request_text(context)
        intent = self.intent_detector.detect_intent(request_text)
        self._validate_intent_requires_mcp(intent)
        context.mcp_intent = intent
        return intent

    def _validate_intent_requires_mcp(self, intent: MCPIntent) -> None:
        """Validate that intent requires MCP processing."""
        if not intent.requires_mcp:
            raise ServiceError("No MCP intent detected in request")
    
    async def _execute_mcp_tools(self, context: ExecutionContext,
                                mcp_context: MCPAgentContext,
                                intent: MCPIntent) -> Dict[str, Any]:
        """Execute MCP tools based on detected intent."""
        if not intent.server_name or not intent.tool_name:
            return await self._execute_discovery_workflow(mcp_context)
        
        return await self._execute_specific_tool(context, mcp_context, intent)
    
    async def _execute_discovery_workflow(self, mcp_context: MCPAgentContext) -> Dict[str, Any]:
        """Execute tool discovery workflow."""
        available_servers = self._get_available_server_list()
        all_tools = await self._discover_tools_from_servers(mcp_context, available_servers)
        return {"available_tools": all_tools, "discovery_completed": True}

    def _get_available_server_list(self) -> List[str]:
        """Get list of available MCP servers."""
        return ["filesystem", "web_scraper", "database"]

    async def _discover_tools_from_servers(self, mcp_context: MCPAgentContext, servers: List[str]) -> List[Dict[str, str]]:
        """Discover tools from all available servers."""
        all_tools = []
        for server in servers:
            tools = await self.mcp_context_manager.get_available_tools(mcp_context, server)
            all_tools.extend([{"server": server, "tool": tool.name} for tool in tools])
        return all_tools
    
    async def _execute_specific_tool(self, context: ExecutionContext,
                                   mcp_context: MCPAgentContext,
                                   intent: MCPIntent) -> Dict[str, Any]:
        """Execute specific MCP tool with parameters."""
        try:
            result = await self._execute_mcp_tool_with_intent(mcp_context, intent)
            self._track_successful_tool_execution(context, intent)
            return {"tool_result": result, "tool_executed": True}
        except Exception as e:
            return await self._handle_tool_execution_error(context, e)

    async def _execute_mcp_tool_with_intent(self, mcp_context: MCPAgentContext, 
                                           intent: MCPIntent) -> Any:
        """Execute MCP tool using context and intent."""
        return await self.mcp_context_manager.execute_tool_with_context(
            context=mcp_context,
            server_name=intent.server_name,
            tool_name=intent.tool_name,
            arguments=intent.parameters
        )

    def _track_successful_tool_execution(self, context: ExecutionContext, 
                                       intent: MCPIntent) -> None:
        """Track successful tool execution in context."""
        tools_used = getattr(context, 'mcp_tools_used', [])
        tools_used.append(f"{intent.server_name}.{intent.tool_name}")
        context.mcp_tools_used = tools_used

    async def _handle_tool_execution_error(self, context: ExecutionContext, 
                                         error: Exception) -> Dict[str, Any]:
        """Handle MCP tool execution errors with fallback."""
        logger.error(f"MCP tool execution failed: {error}")
        if self.config.fallback_to_regular_execution:
            return await self.execute_regular_logic(context)
        raise error
    
    async def _process_mcp_results(self, context: ExecutionContext,
                                  results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format MCP execution results."""
        return self._build_mcp_result_response(context, results)

    def _build_mcp_result_response(self, context: ExecutionContext, results: Dict[str, Any]) -> Dict[str, Any]:
        """Build formatted MCP result response."""
        return {
            "mcp_execution": True,
            "agent_name": context.agent_name,
            "execution_time": context.start_time,
            "results": results,
            "tools_used": getattr(context, 'mcp_tools_used', [])
        }
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate MCP execution preconditions."""
        basic_validation = await self._validate_basic_preconditions(context)
        mcp_validation = await self._validate_mcp_preconditions(context)
        return basic_validation and mcp_validation
    
    async def _validate_basic_preconditions(self, context: ExecutionContext) -> bool:
        """Validate basic execution preconditions."""
        return (context.run_id and 
                context.agent_name and 
                context.state is not None)
    
    async def _validate_mcp_preconditions(self, context: ExecutionContext) -> bool:
        """Validate MCP-specific preconditions."""
        if not self.mcp_service:
            logger.warning("No MCP service available")
            return self.config.fallback_to_regular_execution
        
        # Basic connectivity check would go here
        return True
    
    async def execute_regular_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute regular agent logic (non-MCP)."""
        # This should be overridden by implementing agents
        # Default implementation for base agent
        return {
            "message": "Regular execution completed",
            "agent": context.agent_name,
            "fallback_execution": True
        }
    
    def cleanup_mcp_context(self, context: ExecutionContext) -> None:
        """Cleanup MCP context after execution."""
        mcp_context = getattr(context, 'mcp_context', None)
        if mcp_context:
            self.mcp_context_manager.cleanup_context(context.run_id)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including MCP components."""
        return {
            "agent_name": self.agent_name,
            "execution_engine": self.execution_engine.get_health_status(),
            "reliability": self.reliability_manager.get_health_status(),
            "monitor": self.monitor.get_health_status(),
            "mcp_service": "available" if self.mcp_service else "unavailable",
            "config": {
                "intent_detection": self.config.enable_intent_detection,
                "auto_routing": self.config.auto_route_mcp_requests,
                "fallback_enabled": self.config.fallback_to_regular_execution
            }
        }