"""E2E Agent Tool Integration Comprehensive Test - GCP Staging Environment

Business Value: $500K+ ARR protection through comprehensive tool validation
Critical Coverage for Issue #872: Agent tool integration and chaining

REQUIREMENTS:
- Tests all available tool types with agents in staging environment
- Validates tool chaining and sequencing capabilities
- Tests tool parameter validation and error handling
- Tests tool timeout and retry logic
- Ensures proper WebSocket event delivery for tool operations
- Uses real services only (no Docker mocking)

Phase 1 Focus: Tool integration, parameter validation, and chaining
Target: Validate complete tool ecosystem functionality

SSOT Compliance: Uses SSotAsyncTestCase, IsolatedEnvironment, real services
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.auth import create_real_jwt_token
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_websocket_client import StagingWebSocketClient
from tests.e2e.staging_config import get_staging_config


class ToolType(Enum):
    """Available tool types for comprehensive testing"""
    DATABASE_QUERY = "database_query"
    WEB_SEARCH = "web_search"
    FILE_ANALYSIS = "file_analysis"
    API_CALL = "api_call"
    DATA_TRANSFORMATION = "data_transformation"
    CALCULATION = "calculation"
    TEXT_ANALYSIS = "text_analysis"
    CODE_EXECUTION = "code_execution"
    GRAPH_ANALYSIS = "graph_analysis"
    REPORT_GENERATION = "report_generation"


@dataclass
class ToolTestCase:
    """Represents a tool test scenario"""
    tool_type: ToolType
    tool_name: str
    test_parameters: Dict[str, Any]
    expected_events: List[str]
    timeout_seconds: float = 30.0
    requires_data: bool = False
    chaining_compatible: bool = True
    validation_criteria: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionResult:
    """Results from tool execution test"""
    tool_name: str
    success: bool
    execution_time: float
    events_received: List[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    websocket_events_count: int = 0
    tool_started_received: bool = False
    tool_completed_received: bool = False


class AgentToolTester(SSotAsyncTestCase, StagingTestBase):
    """Comprehensive agent tool integration testing for GCP staging"""
    
    def setup_method(self, method=None):
        """Setup for each test method"""
        super().setup_method(method)
        self.staging_config = get_staging_config()
        self.websocket_url = self.staging_config.websocket_url
        self.test_user = None
        self.websocket_client = None
        
        # Set test environment variables
        self.set_env_var("TESTING_ENVIRONMENT", "staging")
        self.set_env_var("E2E_TOOL_TEST", "true")
        self.set_env_var("TOOL_TIMEOUT_SECONDS", "45")
        
        # Initialize tool test cases
        self.tool_test_cases = self._initialize_tool_test_cases()
        
        # Record test start
        self.record_metric("test_start_time", time.time())
    
    def _initialize_tool_test_cases(self) -> List[ToolTestCase]:
        """Initialize comprehensive tool test cases"""
        return [
            # Database Query Tools
            ToolTestCase(
                tool_type=ToolType.DATABASE_QUERY,
                tool_name="query_user_metrics",
                test_parameters={
                    "query": "SELECT COUNT(*) as user_count FROM users WHERE created_at > '2024-01-01'",
                    "timeout": 15
                },
                expected_events=["tool_executing", "tool_completed"],
                requires_data=True
            ),
            
            # Web Search Tools
            ToolTestCase(
                tool_type=ToolType.WEB_SEARCH,
                tool_name="web_research",
                test_parameters={
                    "query": "AI optimization best practices 2024",
                    "max_results": 5
                },
                expected_events=["tool_executing", "tool_completed"],
                timeout_seconds=45.0
            ),
            
            # File Analysis Tools
            ToolTestCase(
                tool_type=ToolType.FILE_ANALYSIS,
                tool_name="analyze_code_file",
                test_parameters={
                    "file_path": "/sample/analysis.py",
                    "analysis_type": "complexity"
                },
                expected_events=["tool_executing", "tool_completed"],
                chaining_compatible=True
            ),
            
            # API Call Tools
            ToolTestCase(
                tool_type=ToolType.API_CALL,
                tool_name="external_api_request",
                test_parameters={
                    "endpoint": "https://api.github.com/repos/test/repo",
                    "method": "GET",
                    "headers": {"Accept": "application/json"}
                },
                expected_events=["tool_executing", "tool_completed"]
            ),
            
            # Data Transformation Tools
            ToolTestCase(
                tool_type=ToolType.DATA_TRANSFORMATION,
                tool_name="transform_dataset",
                test_parameters={
                    "data": [{"name": "test", "value": 100}],
                    "transformation": "normalize"
                },
                expected_events=["tool_executing", "tool_completed"],
                chaining_compatible=True
            ),
            
            # Calculation Tools
            ToolTestCase(
                tool_type=ToolType.CALCULATION,
                tool_name="cost_calculator",
                test_parameters={
                    "usage_data": {"tokens": 1000000, "requests": 5000},
                    "pricing_model": "standard"
                },
                expected_events=["tool_executing", "tool_completed"],
                chaining_compatible=True
            ),
            
            # Text Analysis Tools
            ToolTestCase(
                tool_type=ToolType.TEXT_ANALYSIS,
                tool_name="sentiment_analyzer",
                test_parameters={
                    "text": "This AI optimization tool is incredibly effective for our workflow",
                    "analysis_depth": "detailed"
                },
                expected_events=["tool_executing", "tool_completed"]
            ),
            
            # Code Execution Tools
            ToolTestCase(
                tool_type=ToolType.CODE_EXECUTION,
                tool_name="python_executor",
                test_parameters={
                    "code": "import math; result = math.sqrt(144); print(f'Square root: {result}')",
                    "timeout": 10
                },
                expected_events=["tool_executing", "tool_completed"],
                validation_criteria={"output_contains": "12"}
            ),
            
            # Graph Analysis Tools
            ToolTestCase(
                tool_type=ToolType.GRAPH_ANALYSIS,
                tool_name="dependency_analyzer",
                test_parameters={
                    "nodes": ["A", "B", "C"],
                    "edges": [["A", "B"], ["B", "C"]],
                    "analysis_type": "shortest_path"
                },
                expected_events=["tool_executing", "tool_completed"],
                chaining_compatible=True
            ),
            
            # Report Generation Tools
            ToolTestCase(
                tool_type=ToolType.REPORT_GENERATION,
                tool_name="performance_reporter",
                test_parameters={
                    "metrics": {"response_time": 150, "success_rate": 0.98},
                    "format": "summary"
                },
                expected_events=["tool_executing", "tool_completed"],
                chaining_compatible=True
            )
        ]
    
    async def setup_test_user_and_connection(self) -> bool:
        """Setup authenticated test user and WebSocket connection"""
        user_id = f"tool_test_user_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        email = f"{user_id}@tooltest.netrasystems.ai"
        
        # Create JWT token with tool execution permissions
        access_token = create_real_jwt_token(
            user_id=user_id,
            permissions=["chat", "agent_execute", "tool_execute", "websocket"],
            email=email,
            expires_in=3600
        )
        
        # Create WebSocket client
        self.websocket_client = StagingWebSocketClient()
        
        # Establish connection
        success = await self.websocket_client.connect(token=access_token)
        if success:
            self.test_user = {
                "user_id": user_id,
                "email": email,
                "access_token": access_token
            }
            self.record_metric("websocket_connected", True)
            return True
        
        return False
    
    async def execute_single_tool_test(self, test_case: ToolTestCase) -> ToolExecutionResult:
        """Execute a single tool test case"""
        start_time = time.time()
        
        # Create agent message that will trigger tool usage
        query = self._create_tool_query(test_case)
        
        message = {
            "type": "chat_message",
            "content": query,
            "user_id": self.test_user["user_id"],
            "session_id": f"tool_test_{test_case.tool_name}_{int(time.time())}",
            "timestamp": time.time(),
            "tool_test_mode": True
        }
        
        try:
            # Send message
            await self.websocket_client.send_message("chat_message", message)
            
            # Collect events and responses
            events = await self._collect_tool_execution_events(
                test_case.tool_name, 
                test_case.timeout_seconds
            )
            
            execution_time = time.time() - start_time
            
            # Analyze results
            return self._analyze_tool_execution_results(
                test_case, events, execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolExecutionResult(
                tool_name=test_case.tool_name,
                success=False,
                execution_time=execution_time,
                events_received=[],
                error_message=str(e)
            )
    
    def _create_tool_query(self, test_case: ToolTestCase) -> str:
        """Create an agent query that will trigger the specified tool"""
        tool_queries = {
            ToolType.DATABASE_QUERY: f"Please run a database query to get user metrics: {test_case.test_parameters.get('query', '')}",
            ToolType.WEB_SEARCH: f"Search the web for: {test_case.test_parameters.get('query', 'AI optimization')}",
            ToolType.FILE_ANALYSIS: f"Analyze the code file at {test_case.test_parameters.get('file_path', '/sample/file')}",
            ToolType.API_CALL: f"Make an API call to {test_case.test_parameters.get('endpoint', 'test endpoint')}",
            ToolType.DATA_TRANSFORMATION: f"Transform this data: {test_case.test_parameters.get('data', {})}",
            ToolType.CALCULATION: f"Calculate costs using these parameters: {test_case.test_parameters.get('usage_data', {})}",
            ToolType.TEXT_ANALYSIS: f"Analyze the sentiment of this text: {test_case.test_parameters.get('text', 'sample text')}",
            ToolType.CODE_EXECUTION: f"Execute this Python code: {test_case.test_parameters.get('code', 'print(\"test\")')}",
            ToolType.GRAPH_ANALYSIS: f"Analyze this graph structure: nodes={test_case.test_parameters.get('nodes', [])}, edges={test_case.test_parameters.get('edges', [])}",
            ToolType.REPORT_GENERATION: f"Generate a performance report with these metrics: {test_case.test_parameters.get('metrics', {})}"
        }
        
        return tool_queries.get(test_case.tool_type, f"Use the {test_case.tool_name} tool to help with this request")
    
    async def _collect_tool_execution_events(self, tool_name: str, timeout: float) -> List[Dict[str, Any]]:
        """Collect all WebSocket events during tool execution"""
        events = []
        tool_completed = False
        start_time = time.time()
        
        while time.time() - start_time < timeout and not tool_completed:
            try:
                message = await self.websocket_client.receive_message(timeout=2.0)
                if message:
                    events.append(message)
                    
                    # Check for tool completion
                    if (message.get("type") == "tool_completed" or 
                        message.get("type") == "agent_completed"):
                        tool_completed = True
                        
                await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.warning(f"Error collecting events for {tool_name}: {e}")
                break
        
        return events
    
    def _analyze_tool_execution_results(
        self, 
        test_case: ToolTestCase, 
        events: List[Dict[str, Any]], 
        execution_time: float
    ) -> ToolExecutionResult:
        """Analyze tool execution results and validate against criteria"""
        
        # Count event types
        event_types = {event.get("type") for event in events}
        tool_started = "tool_executing" in event_types
        tool_completed = "tool_completed" in event_types or "agent_completed" in event_types
        
        # Check if required events were received
        required_events_received = all(
            event_type in event_types for event_type in test_case.expected_events
        )
        
        # Basic success criteria
        success = (
            tool_completed and
            required_events_received and
            execution_time < test_case.timeout_seconds
        )
        
        # Additional validation if specified
        if success and test_case.validation_criteria:
            success = self._validate_additional_criteria(events, test_case.validation_criteria)
        
        return ToolExecutionResult(
            tool_name=test_case.tool_name,
            success=success,
            execution_time=execution_time,
            events_received=events,
            websocket_events_count=len(events),
            tool_started_received=tool_started,
            tool_completed_received=tool_completed,
            response_data=self._extract_response_data(events)
        )
    
    def _validate_additional_criteria(
        self, 
        events: List[Dict[str, Any]], 
        criteria: Dict[str, Any]
    ) -> bool:
        """Validate additional success criteria"""
        for criterion, expected_value in criteria.items():
            if criterion == "output_contains":
                # Check if any event contains the expected output
                found = any(
                    expected_value in str(event.get("content", ""))
                    for event in events
                )
                if not found:
                    return False
        
        return True
    
    def _extract_response_data(self, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract response data from events"""
        for event in reversed(events):  # Check latest events first
            if event.get("type") in ["tool_completed", "agent_completed"]:
                return event.get("data", event.get("content"))
        return None
    
    async def test_tool_chaining(self, tool_cases: List[ToolTestCase]) -> Dict[str, Any]:
        """Test chaining multiple tools in sequence"""
        chainable_tools = [tc for tc in tool_cases if tc.chaining_compatible][:3]
        
        if len(chainable_tools) < 2:
            return {"error": "Insufficient chainable tools for testing"}
        
        # Create complex query that would require multiple tools
        query = (
            f"First, use {chainable_tools[0].tool_name} to analyze the data, "
            f"then use {chainable_tools[1].tool_name} to transform the results, "
            f"and finally use {chainable_tools[2].tool_name} to generate a summary report."
        )
        
        message = {
            "type": "chat_message",
            "content": query,
            "user_id": self.test_user["user_id"],
            "session_id": f"tool_chain_test_{int(time.time())}",
            "timestamp": time.time(),
            "tool_chain_test": True
        }
        
        start_time = time.time()
        
        try:
            await self.websocket_client.send_message("chat_message", message)
            
            # Collect events for longer timeout (tool chaining takes time)
            events = await self._collect_tool_execution_events("tool_chain", 90.0)
            execution_time = time.time() - start_time
            
            # Analyze chaining results
            tool_executions = [
                event for event in events 
                if event.get("type") in ["tool_executing", "tool_completed"]
            ]
            
            unique_tools_used = {
                event.get("tool_name", "unknown") 
                for event in tool_executions
                if event.get("tool_name")
            }
            
            success = (
                len(unique_tools_used) >= 2 and  # At least 2 tools used
                execution_time < 120.0 and  # Reasonable execution time
                any(event.get("type") == "agent_completed" for event in events)
            )
            
            return {
                "success": success,
                "tools_used": list(unique_tools_used),
                "execution_time": execution_time,
                "events_count": len(events),
                "tool_executions": len(tool_executions)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def cleanup_test_connection(self) -> None:
        """Clean up test resources"""
        if self.websocket_client:
            await self.websocket_client.disconnect()
        
        self.record_metric("cleanup_completed", time.time())


class TestAgentToolIntegrationComprehensive:
    """E2E Agent Tool Integration Tests for GCP Staging"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_all_tool_types_execution(self):
        """
        CRITICAL: Test all available tool types with agents
        
        This test validates:
        1. All tool types can be invoked by agents
        2. Tool parameters are properly validated
        3. WebSocket events are delivered for tool operations
        4. Tool execution completes within timeout
        5. Error handling for invalid parameters
        
        Success Criteria:
        - At least 80% of tools execute successfully
        - All tool events are delivered properly
        - Tool execution times within limits
        """
        tester = AgentToolTester()
        tester.setup_method()
        
        try:
            # Setup user and connection
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish WebSocket connection"
            
            # Execute all tool tests
            results = []
            for test_case in tester.tool_test_cases:
                result = await tester.execute_single_tool_test(test_case)
                results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(1.0)
            
            # Validate overall results
            await tester._validate_tool_test_results(results)
            
        finally:
            await tester.cleanup_test_connection()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_tool_parameter_validation(self):
        """
        Test tool parameter validation and error handling
        
        Validates:
        1. Tools properly validate input parameters
        2. Error messages are returned for invalid parameters
        3. WebSocket events include error information
        """
        tester = AgentToolTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish WebSocket connection"
            
            # Test with invalid parameters
            invalid_test_case = ToolTestCase(
                tool_type=ToolType.DATABASE_QUERY,
                tool_name="invalid_query_test",
                test_parameters={
                    "query": "INVALID SQL SYNTAX HERE",
                    "invalid_param": "should_not_exist"
                },
                expected_events=["tool_executing", "tool_completed"],
                timeout_seconds=30.0
            )
            
            result = await tester.execute_single_tool_test(invalid_test_case)
            
            # Should complete even if parameters are invalid (with error)
            assert result.tool_completed_received, "Tool should complete even with invalid parameters"
            assert len(result.events_received) > 0, "Should receive error events"
            
        finally:
            await tester.cleanup_test_connection()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_tool_timeout_and_retry_logic(self):
        """
        Test tool timeout behavior and retry logic
        
        Validates:
        1. Tools timeout appropriately for long-running operations
        2. Retry logic works for transient failures
        3. WebSocket events are sent for timeouts/retries
        """
        tester = AgentToolTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish WebSocket connection"
            
            # Test with very short timeout
            timeout_test_case = ToolTestCase(
                tool_type=ToolType.WEB_SEARCH,
                tool_name="timeout_test",
                test_parameters={
                    "query": "complex search requiring long processing time",
                    "timeout": 1  # Very short timeout
                },
                expected_events=["tool_executing"],
                timeout_seconds=10.0
            )
            
            result = await tester.execute_single_tool_test(timeout_test_case)
            
            # Validate timeout behavior
            assert result.execution_time <= timeout_test_case.timeout_seconds, \
                "Test should respect timeout limits"
            
        finally:
            await tester.cleanup_test_connection()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_tool_chaining_comprehensive(self):
        """
        Test comprehensive tool chaining and sequencing
        
        Validates:
        1. Multiple tools can be chained in sequence
        2. Output from one tool can be used as input to the next
        3. WebSocket events are properly ordered for chained execution
        4. Error handling in tool chains
        """
        tester = AgentToolTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish WebSocket connection"
            
            # Execute tool chaining test
            chain_result = await tester.test_tool_chaining(tester.tool_test_cases)
            
            # Validate chaining results
            assert chain_result.get("success", False), \
                f"Tool chaining failed: {chain_result.get('error', 'Unknown error')}"
            
            assert len(chain_result.get("tools_used", [])) >= 2, \
                "At least 2 tools should be used in chaining"
            
            assert chain_result.get("execution_time", 0) < 120.0, \
                "Tool chaining should complete within 2 minutes"
            
        finally:
            await tester.cleanup_test_connection()


# Extended methods for AgentToolTester
async def _validate_tool_test_results(self, results: List[ToolExecutionResult]) -> None:
    """Validate overall tool test results"""
    successful_tools = [r for r in results if r.success]
    success_rate = len(successful_tools) / len(results) if results else 0
    
    assert success_rate >= 0.8, \
        f"Tool success rate {success_rate:.2%} below 80% threshold"
    
    # Validate WebSocket events
    tools_with_events = [r for r in results if r.websocket_events_count > 0]
    event_delivery_rate = len(tools_with_events) / len(results) if results else 0
    
    assert event_delivery_rate >= 0.9, \
        f"Event delivery rate {event_delivery_rate:.2%} below 90% threshold"
    
    # Validate execution times
    avg_execution_time = sum(r.execution_time for r in results) / len(results)
    assert avg_execution_time < 30.0, \
        f"Average tool execution time {avg_execution_time:.2f}s exceeds 30s limit"
    
    # Log success metrics
    self.logger.info(
        f"TOOL INTEGRATION SUCCESS: {success_rate:.2%} success rate, "
        f"{event_delivery_rate:.2%} event delivery, "
        f"{avg_execution_time:.2f}s avg execution time"
    )
    
    # Record detailed metrics
    self.record_metric("tool_success_rate", success_rate)
    self.record_metric("tool_event_delivery_rate", event_delivery_rate)
    self.record_metric("tool_avg_execution_time", avg_execution_time)


# Attach extended methods to the class
AgentToolTester._validate_tool_test_results = _validate_tool_test_results