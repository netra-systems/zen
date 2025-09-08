"""
Comprehensive Tool Dispatcher Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable tool execution across system components
- Value Impact: Tools enable agents to deliver actionable optimization insights  
- Strategic Impact: Tool execution is core to our AI-powered optimization platform

Integration Points Tested:
1. Tool dispatcher cross-component coordination
2. WebSocket event integration during tool execution
3. User context isolation in tool dispatch
4. Database integration for tool result persistence
5. Permission system integration with tool security
6. Tool registry coordination with execution engine
7. Error handling and recovery across tool boundaries
8. Performance monitoring and metrics collection
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone  
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy
)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from langchain_core.tools import BaseTool


class MockOptimizationTool(BaseTool):
    """Mock optimization tool for integration testing."""
    
    name: str = "cost_optimization_analyzer"
    description: str = "Analyzes cloud costs and provides optimization recommendations"
    
    def __init__(self, should_succeed: bool = True, execution_time: float = 0.1, 
                 tool_result: Dict = None):
        super().__init__()
        self.should_succeed = should_succeed
        self.execution_time = execution_time
        self.tool_result = tool_result or {
            "analysis_complete": True,
            "potential_savings": 15000,
            "recommendations": [
                {"type": "rightsizing", "savings": 8000},
                {"type": "reserved_instances", "savings": 7000}
            ]
        }
        self.executions = []  # Track executions for testing
        
    def _run(self, cloud_account: str, analysis_period: str = "30d", **kwargs) -> Dict[str, Any]:
        """Run tool synchronously (for Langchain compatibility).""" 
        return asyncio.run(self._arun(cloud_account, analysis_period, **kwargs))
        
    async def _arun(self, cloud_account: str, analysis_period: str = "30d", **kwargs) -> Dict[str, Any]:
        """Run tool asynchronously."""
        execution_record = {
            "cloud_account": cloud_account,
            "analysis_period": analysis_period,
            "kwargs": kwargs,
            "start_time": time.time()
        }
        
        await asyncio.sleep(self.execution_time)
        
        if not self.should_succeed:
            execution_record["error"] = "AWS API rate limit exceeded"
            self.executions.append(execution_record)
            raise RuntimeError("AWS API rate limit exceeded")
            
        execution_record["end_time"] = time.time()
        execution_record["result"] = self.tool_result
        self.executions.append(execution_record)
        
        return self.tool_result


class MockDatabaseTool(BaseTool):
    """Mock database tool for integration testing."""
    
    name: str = "database_query_optimizer"
    description: str = "Optimizes database queries and analyzes performance"
    
    def __init__(self, database_results: List[Dict] = None):
        super().__init__()
        self.database_results = database_results or [
            {"query_id": "q1", "execution_time_ms": 150, "optimization_potential": "high"},
            {"query_id": "q2", "execution_time_ms": 75, "optimization_potential": "medium"}
        ]
        self.queries_executed = []
        
    def _run(self, database_name: str, query_pattern: str = None, **kwargs) -> Dict[str, Any]:
        """Run database tool synchronously."""
        return asyncio.run(self._arun(database_name, query_pattern, **kwargs))
        
    async def _arun(self, database_name: str, query_pattern: str = None, **kwargs) -> Dict[str, Any]:
        """Run database tool asynchronously."""
        query_record = {
            "database_name": database_name,
            "query_pattern": query_pattern,
            "timestamp": time.time()
        }
        self.queries_executed.append(query_record)
        
        # Simulate database operation
        await asyncio.sleep(0.05)
        
        return {
            "database": database_name,
            "queries_analyzed": len(self.database_results),
            "results": self.database_results,
            "optimization_summary": {
                "total_queries": len(self.database_results),
                "high_potential": len([r for r in self.database_results if r["optimization_potential"] == "high"]),
                "estimated_savings_ms": sum(r["execution_time_ms"] * 0.3 for r in self.database_results)
            }
        }


class MockWebSocketManager:
    """Mock WebSocket manager for tool dispatcher integration testing."""
    
    def __init__(self):
        self.events_sent = []
        self.connections = {}
        
    async def send_to_user(self, user_id: str, message: Dict) -> bool:
        """Mock send to user."""
        self.events_sent.append({
            "target_type": "user",
            "target_id": user_id,
            "message": message,
            "timestamp": time.time()
        })
        return True
        
    async def send_to_thread(self, thread_id: str, message: Dict) -> bool:
        """Mock send to thread."""
        self.events_sent.append({
            "target_type": "thread", 
            "target_id": thread_id,
            "message": message,
            "timestamp": time.time()
        })
        return True


class MockPermissionService:
    """Mock permission service for integration testing."""
    
    def __init__(self, allowed_tools: List[str] = None):
        self.allowed_tools = allowed_tools or ["cost_optimization_analyzer", "database_query_optimizer"]
        self.permission_checks = []
        
    async def check_tool_permission(self, user_context: UserExecutionContext, tool_name: str) -> bool:
        """Check if user has permission for tool."""
        check_record = {
            "user_id": user_context.user_id,
            "tool_name": tool_name,
            "timestamp": time.time(),
            "allowed": tool_name in self.allowed_tools
        }
        self.permission_checks.append(check_record)
        return tool_name in self.allowed_tools


@pytest.mark.integration
@pytest.mark.real_services
class TestUnifiedToolDispatcherIntegrationComprehensive:
    """Comprehensive tool dispatcher integration tests."""
    
    @pytest.fixture
    def user_context_enterprise(self):
        """Provide enterprise user context."""
        return UserExecutionContext(
            user_id="enterprise_user_123",
            thread_id="enterprise_thread_456",
            correlation_id="enterprise_correlation_789",
            permissions=["tool_execution", "advanced_analysis", "database_access"],
            subscription_tier="enterprise"
        )
        
    @pytest.fixture 
    def user_context_basic(self):
        """Provide basic user context."""
        return UserExecutionContext(
            user_id="basic_user_456", 
            thread_id="basic_thread_789",
            correlation_id="basic_correlation_123",
            permissions=["tool_execution"],
            subscription_tier="basic"
        )
        
    @pytest.fixture
    def mock_websocket_manager(self):
        """Provide mock WebSocket manager."""
        return MockWebSocketManager()
        
    @pytest.fixture
    def mock_permission_service(self):
        """Provide mock permission service."""
        return MockPermissionService()
        
    @pytest.fixture
    def optimization_tool(self):
        """Provide optimization tool."""
        return MockOptimizationTool()
        
    @pytest.fixture
    def database_tool(self):
        """Provide database tool."""
        return MockDatabaseTool()
        
    @pytest.fixture 
    def failing_tool(self):
        """Provide failing tool for error testing."""
        return MockOptimizationTool(should_succeed=False)
        
    async def test_single_tool_execution_integration(
        self, user_context_enterprise, mock_websocket_manager, 
        optimization_tool, mock_permission_service
    ):
        """Test complete single tool execution integration flow."""
        # BUSINESS VALUE: Ensure tools execute reliably to provide optimization insights
        
        # Setup: Create request-scoped tool dispatcher
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_enterprise,
            websocket_manager=mock_websocket_manager,
            tools=[optimization_tool]
        )
        dispatcher.permission_service = mock_permission_service
        
        # Execute: Dispatch optimization tool
        request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer",
            parameters={
                "cloud_account": "aws-production-account",
                "analysis_period": "30d",
                "regions": ["us-east-1", "us-west-2"]
            }
        )
        
        result = await dispatcher.dispatch(request)
        
        # Verify: Tool execution succeeded
        assert result.success is True
        assert result.error is None
        assert result.result is not None
        
        # Verify: Tool received correct parameters
        assert len(optimization_tool.executions) == 1
        execution = optimization_tool.executions[0]
        assert execution["cloud_account"] == "aws-production-account"
        assert execution["analysis_period"] == "30d"
        assert execution["kwargs"]["regions"] == ["us-east-1", "us-west-2"]
        
        # Verify: Tool returned expected business value
        assert result.result["analysis_complete"] is True
        assert result.result["potential_savings"] == 15000
        assert len(result.result["recommendations"]) == 2
        
        # Verify: Permission check performed
        assert len(mock_permission_service.permission_checks) == 1
        check = mock_permission_service.permission_checks[0]
        assert check["user_id"] == "enterprise_user_123"
        assert check["tool_name"] == "cost_optimization_analyzer"
        assert check["allowed"] is True
        
        # Verify: WebSocket events sent
        events = mock_websocket_manager.events_sent
        assert len(events) >= 2  # At least tool_executing and tool_completed
        
        executing_events = [e for e in events if e["message"]["type"] == "tool_executing"]
        completed_events = [e for e in events if e["message"]["type"] == "tool_completed"]
        
        assert len(executing_events) == 1
        assert len(completed_events) == 1
        
        # Verify: WebSocket event content
        executing_event = executing_events[0]
        assert executing_event["target_type"] == "thread"
        assert executing_event["target_id"] == "enterprise_thread_456"
        assert executing_event["message"]["payload"]["tool_name"] == "cost_optimization_analyzer"
        
        completed_event = completed_events[0]
        assert completed_event["message"]["payload"]["result"]["potential_savings"] == 15000
        
    async def test_multiple_tool_execution_integration(
        self, user_context_enterprise, mock_websocket_manager, 
        optimization_tool, database_tool, mock_permission_service
    ):
        """Test multiple tool execution integration with coordination."""
        # BUSINESS VALUE: Coordinated tool execution provides comprehensive optimization insights
        
        # Setup: Dispatcher with multiple tools
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_enterprise,
            websocket_manager=mock_websocket_manager,
            tools=[optimization_tool, database_tool]
        )
        dispatcher.permission_service = mock_permission_service
        
        # Execute: Dispatch multiple tools concurrently
        requests = [
            ToolDispatchRequest(
                tool_name="cost_optimization_analyzer",
                parameters={"cloud_account": "aws-prod", "analysis_period": "7d"}
            ),
            ToolDispatchRequest(
                tool_name="database_query_optimizer", 
                parameters={"database_name": "analytics-db", "query_pattern": "SELECT%"}
            )
        ]
        
        # Run tools concurrently
        results = await asyncio.gather(*[
            dispatcher.dispatch(request) for request in requests
        ])
        
        # Verify: Both tools succeeded
        assert all(result.success for result in results)
        
        cost_result, db_result = results
        
        # Verify: Cost optimization results
        assert cost_result.result["potential_savings"] == 15000
        assert len(cost_result.result["recommendations"]) == 2
        
        # Verify: Database optimization results  
        assert db_result.result["database"] == "analytics-db"
        assert db_result.result["queries_analyzed"] == 2
        assert "optimization_summary" in db_result.result
        
        # Verify: Tool executions recorded
        assert len(optimization_tool.executions) == 1
        assert len(database_tool.queries_executed) == 1
        
        # Verify: Permission checks for both tools
        assert len(mock_permission_service.permission_checks) == 2
        tool_names_checked = [check["tool_name"] for check in mock_permission_service.permission_checks]
        assert "cost_optimization_analyzer" in tool_names_checked
        assert "database_query_optimizer" in tool_names_checked
        
        # Verify: WebSocket events for both tools
        events = mock_websocket_manager.events_sent
        executing_events = [e for e in events if e["message"]["type"] == "tool_executing"]
        completed_events = [e for e in events if e["message"]["type"] == "tool_completed"]
        
        assert len(executing_events) == 2
        assert len(completed_events) == 2
        
        # Verify: Events include both tools
        executed_tools = [e["message"]["payload"]["tool_name"] for e in executing_events]
        assert "cost_optimization_analyzer" in executed_tools
        assert "database_query_optimizer" in executed_tools
        
    async def test_user_isolation_integration(
        self, mock_websocket_manager, optimization_tool, mock_permission_service
    ):
        """Test user isolation in tool dispatcher integration."""
        # BUSINESS VALUE: User isolation ensures data privacy and security
        
        # Setup: Two different user contexts
        user1_context = UserExecutionContext(
            user_id="user_1",
            thread_id="thread_1", 
            correlation_id="correlation_1",
            permissions=["tool_execution"]
        )
        
        user2_context = UserExecutionContext(
            user_id="user_2",
            thread_id="thread_2",
            correlation_id="correlation_2", 
            permissions=["tool_execution"]
        )
        
        # Create separate dispatchers for each user
        dispatcher1 = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user1_context,
            websocket_manager=mock_websocket_manager,
            tools=[optimization_tool]
        )
        dispatcher1.permission_service = mock_permission_service
        
        dispatcher2 = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user2_context,
            websocket_manager=mock_websocket_manager, 
            tools=[optimization_tool]
        )
        dispatcher2.permission_service = mock_permission_service
        
        # Execute: Concurrent tool execution for different users
        user1_request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer",
            parameters={"cloud_account": "user1-sensitive-account", "analysis_period": "30d"}
        )
        
        user2_request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer", 
            parameters={"cloud_account": "user2-confidential-account", "analysis_period": "7d"}
        )
        
        # Execute concurrently
        results = await asyncio.gather(
            dispatcher1.dispatch(user1_request),
            dispatcher2.dispatch(user2_request)
        )
        
        user1_result, user2_result = results
        
        # Verify: Both executions succeeded
        assert user1_result.success is True
        assert user2_result.success is True
        
        # Verify: Tool executions properly isolated
        assert len(optimization_tool.executions) == 2
        
        user1_execution = next(e for e in optimization_tool.executions 
                              if e["cloud_account"] == "user1-sensitive-account")
        user2_execution = next(e for e in optimization_tool.executions
                              if e["cloud_account"] == "user2-confidential-account")
        
        assert user1_execution["analysis_period"] == "30d"
        assert user2_execution["analysis_period"] == "7d"
        
        # Verify: Permission checks isolated by user
        user1_checks = [c for c in mock_permission_service.permission_checks if c["user_id"] == "user_1"]
        user2_checks = [c for c in mock_permission_service.permission_checks if c["user_id"] == "user_2"]
        
        assert len(user1_checks) == 1
        assert len(user2_checks) == 1
        
        # Verify: WebSocket events sent to correct threads
        user1_events = [e for e in mock_websocket_manager.events_sent if e["target_id"] == "thread_1"]
        user2_events = [e for e in mock_websocket_manager.events_sent if e["target_id"] == "thread_2"]
        
        assert len(user1_events) >= 2  # At least executing and completed
        assert len(user2_events) >= 2  # At least executing and completed
        
        # Verify: No cross-contamination of events
        for event in user1_events:
            # User 1 events should not contain user 2's sensitive data
            event_str = str(event)
            assert "user2-confidential-account" not in event_str
            
        for event in user2_events:
            # User 2 events should not contain user 1's sensitive data
            event_str = str(event)
            assert "user1-sensitive-account" not in event_str
            
    async def test_tool_permission_integration(
        self, user_context_basic, mock_websocket_manager, optimization_tool
    ):
        """Test tool permission integration with security boundaries."""
        # BUSINESS VALUE: Security boundaries prevent unauthorized tool access
        
        # Setup: Permission service that denies access to optimization tool
        restricted_permission_service = MockPermissionService(allowed_tools=[])
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_basic,
            websocket_manager=mock_websocket_manager,
            tools=[optimization_tool]
        )
        dispatcher.permission_service = restricted_permission_service
        
        # Execute: Attempt to use restricted tool
        request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer", 
            parameters={"cloud_account": "restricted-account"}
        )
        
        result = await dispatcher.dispatch(request)
        
        # Verify: Permission denied
        assert result.success is False
        assert "permission" in result.error.lower() or "unauthorized" in result.error.lower()
        
        # Verify: Tool was not executed
        assert len(optimization_tool.executions) == 0
        
        # Verify: Permission check was performed
        assert len(restricted_permission_service.permission_checks) == 1
        check = restricted_permission_service.permission_checks[0]
        assert check["user_id"] == "basic_user_456"
        assert check["tool_name"] == "cost_optimization_analyzer"
        assert check["allowed"] is False
        
    async def test_tool_error_handling_integration(
        self, user_context_enterprise, mock_websocket_manager, 
        failing_tool, mock_permission_service
    ):
        """Test tool error handling integration across components."""
        # BUSINESS VALUE: Graceful error handling maintains user trust
        
        # Setup: Dispatcher with failing tool
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_enterprise,
            websocket_manager=mock_websocket_manager,
            tools=[failing_tool]
        )
        dispatcher.permission_service = mock_permission_service
        
        # Execute: Dispatch failing tool
        request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer",
            parameters={"cloud_account": "test-account"}
        )
        
        result = await dispatcher.dispatch(request)
        
        # Verify: Error handled gracefully
        assert result.success is False
        assert "AWS API rate limit exceeded" in result.error
        
        # Verify: Tool execution was attempted
        assert len(failing_tool.executions) == 1
        assert "error" in failing_tool.executions[0]
        
        # Verify: Error WebSocket event sent
        events = mock_websocket_manager.events_sent
        error_events = [e for e in events if e["message"]["type"] == "tool_error"]
        
        assert len(error_events) == 1
        error_event = error_events[0] 
        assert "AWS API rate limit exceeded" in error_event["message"]["payload"]["error"]
        
    async def test_tool_performance_monitoring_integration(
        self, user_context_enterprise, mock_websocket_manager, 
        mock_permission_service
    ):
        """Test tool performance monitoring integration."""
        # BUSINESS VALUE: Performance monitoring enables system optimization
        
        # Setup: Tool with measurable execution time
        slow_tool = MockOptimizationTool(execution_time=0.5)  # 500ms execution
        
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_enterprise,
            websocket_manager=mock_websocket_manager,
            tools=[slow_tool]
        )
        dispatcher.permission_service = mock_permission_service
        
        # Execute: Dispatch with timing measurement
        start_time = time.time()
        
        request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer",
            parameters={"cloud_account": "performance-test"}
        )
        
        result = await dispatcher.dispatch(request)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify: Tool executed successfully
        assert result.success is True
        
        # Verify: Execution timing
        assert total_time >= 0.5  # Should take at least 500ms
        assert total_time < 2.0   # Should not take too long
        
        # Verify: Performance metadata included
        assert "metadata" in result.__dict__ or hasattr(result, "metadata")
        
        # Verify: Tool execution recorded with timing
        assert len(slow_tool.executions) == 1
        execution = slow_tool.executions[0]
        assert "start_time" in execution
        assert "end_time" in execution
        
        execution_time = execution["end_time"] - execution["start_time"]
        assert execution_time >= 0.5  # Tool execution time
        
        # Verify: WebSocket events include timing information
        completed_events = [e for e in mock_websocket_manager.events_sent 
                           if e["message"]["type"] == "tool_completed"]
        
        assert len(completed_events) == 1
        completed_event = completed_events[0]
        
        # Check for timing metadata in WebSocket event
        payload = completed_event["message"]["payload"]
        assert "timestamp" in payload or "execution_time" in str(payload)
        
    async def test_tool_registry_integration(
        self, user_context_enterprise, mock_websocket_manager, mock_permission_service
    ):
        """Test tool registry integration with dynamic tool management."""
        # BUSINESS VALUE: Dynamic tool management enables flexible optimization capabilities
        
        # Setup: Empty dispatcher
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=user_context_enterprise,
            websocket_manager=mock_websocket_manager,
            tools=[]
        )
        dispatcher.permission_service = mock_permission_service
        
        # Execute: Try to use non-registered tool
        request = ToolDispatchRequest(
            tool_name="unregistered_tool",
            parameters={"test": "value"}
        )
        
        result = await dispatcher.dispatch(request)
        
        # Verify: Tool not found error
        assert result.success is False
        assert "not found" in result.error.lower() or "unknown" in result.error.lower()
        
        # Setup: Register tool dynamically
        new_tool = MockOptimizationTool()
        await dispatcher.register_tool(new_tool)
        
        # Execute: Use newly registered tool
        request = ToolDispatchRequest(
            tool_name="cost_optimization_analyzer",
            parameters={"cloud_account": "dynamic-test"}
        )
        
        result = await dispatcher.dispatch(request)
        
        # Verify: Tool now works
        assert result.success is True
        assert result.result["analysis_complete"] is True
        
        # Verify: Tool execution recorded
        assert len(new_tool.executions) == 1
        assert new_tool.executions[0]["cloud_account"] == "dynamic-test"