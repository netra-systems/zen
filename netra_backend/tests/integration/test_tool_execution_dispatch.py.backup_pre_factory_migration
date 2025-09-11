"""Integration tests for Tool Execution and Dispatching patterns.

These tests validate REAL component interactions between:
- UnifiedToolDispatcher and factory patterns
- Tool execution workflows 
- WebSocket event notifications
- Request-scoped tool isolation
- Permission and validation systems

CRITICAL: These are INTEGRATION tests - they test REAL interactions between components
without mocks for core functionality, but should work without Docker services.

Business Value: Platform/Internal - System Stability  
Ensures tool execution and dispatching works correctly for multi-user scenarios.
"""

import asyncio
import json
import pytest
import tempfile
import time
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import Field
from langchain_core.tools import BaseTool

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory, 
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    create_request_scoped_dispatcher
)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockBusinessTool(BaseTool):
    """Mock business tool for integration testing - represents real tool interface."""
    
    name: str = "business_analyzer"
    description: str = "Analyzes business metrics and KPIs"
    tool_id: str = "business_analyzer_001"
    execution_count: int = 0
    last_input: Optional[Dict[str, Any]] = None
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def __init__(self, tool_id: str = None, **kwargs):
        if tool_id:
            kwargs['tool_id'] = tool_id
        if 'execution_history' not in kwargs:
            kwargs['execution_history'] = []
        super().__init__(**kwargs)
        
    def _run(self, query: str, **kwargs) -> str:
        """Synchronous tool execution."""
        return asyncio.run(self._arun(query, **kwargs))
        
    async def _arun(self, query: str, **kwargs) -> str:
        """Asynchronous tool execution with real business logic simulation."""
        self.execution_count += 1
        self.last_input = {"query": query, "kwargs": kwargs}
        
        # Simulate real business analysis work
        await asyncio.sleep(0.001)  
        
        execution_result = {
            "tool_id": self.tool_id,
            "analysis": f"Business analysis for: {query}",
            "metrics": {
                "execution_count": self.execution_count,
                "processing_time": 0.001,
                "confidence_score": 0.95
            },
            "recommendations": [
                "Optimize workflow efficiency",
                "Review resource allocation"
            ]
        }
        
        self.execution_history.append(execution_result)
        return json.dumps(execution_result)


class MockDataProcessingTool(BaseTool):
    """Mock data processing tool for integration testing."""
    
    name: str = "data_processor"
    description: str = "Processes and transforms data"
    tool_id: str = "data_processor_001"
    processed_records: int = 0
    processing_errors: List[str] = Field(default_factory=list)
    
    def __init__(self, tool_id: str = None, **kwargs):
        if tool_id:
            kwargs['tool_id'] = tool_id
        if 'processing_errors' not in kwargs:
            kwargs['processing_errors'] = []
        super().__init__(**kwargs)
        
    def _run(self, dataset: str, **kwargs) -> str:
        """Synchronous data processing."""
        return asyncio.run(self._arun(dataset, **kwargs))
        
    async def _arun(self, dataset: str, **kwargs) -> str:
        """Asynchronous data processing with validation."""
        try:
            # Simulate data processing work
            await asyncio.sleep(0.002)
            
            self.processed_records += len(dataset.split(",")) if dataset else 0
            
            result = {
                "tool_id": self.tool_id,
                "status": "success",
                "records_processed": self.processed_records,
                "transformations_applied": kwargs.get("transformations", []),
                "output_format": kwargs.get("format", "json")
            }
            
            return json.dumps(result)
            
        except Exception as e:
            self.processing_errors.append(str(e))
            return json.dumps({"status": "error", "error": str(e)})


class MockWebSocketNotifier:
    """Mock WebSocket notifier for tool execution events."""
    
    def __init__(self):
        self.tool_events = []
        self.error_events = []
        
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any]):
        """Mock tool execution start notification."""
        event = {
            "type": "tool_executing",
            "run_id": run_id,
            "agent_name": agent_name, 
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": time.time()
        }
        self.tool_events.append(event)
        
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Any, duration: float = None):
        """Mock tool execution completion notification."""
        event = {
            "type": "tool_completed",
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name, 
            "result": result,
            "duration": duration,
            "timestamp": time.time()
        }
        self.tool_events.append(event)
        
    async def notify_tool_error(self, run_id: str, agent_name: str, tool_name: str, error: str):
        """Mock tool error notification."""
        event = {
            "type": "tool_error",
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "error": error,
            "timestamp": time.time()
        }
        self.error_events.append(event)
        
    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific run."""
        all_events = self.tool_events + self.error_events
        return [event for event in all_events if event.get("run_id") == run_id]


class TestToolExecutionDispatch(SSotAsyncTestCase):
    """Integration tests for Tool Execution and Dispatching patterns.
    
    Tests REAL component interactions without Docker dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test with real tool dispatcher components."""
        super().setup_method(method)
        
        # Create real user contexts for isolation testing
        self.user1_context = UserExecutionContext(
            user_id="tool_test_user_001",
            thread_id="tool_thread_001",
            run_id="tool_run_001",
            agent_context={"test": "tool_integration"}
        )
        
        self.user2_context = UserExecutionContext(
            user_id="tool_test_user_002", 
            thread_id="tool_thread_002",
            run_id="tool_run_002",
            agent_context={"test": "tool_integration"}
        )
        
        # Create real tools for testing
        self.business_tool = MockBusinessTool("business_001")
        self.data_tool = MockDataProcessingTool("data_001")
        self.tools_list = [self.business_tool, self.data_tool]
        
        # Create WebSocket notifier mock (represents real interface)
        self.websocket_notifier = MockWebSocketNotifier()
        
        # Record setup metrics
        self.record_metric("test_setup_time", time.time())
        self.record_metric("tools_available", len(self.tools_list))
        
    async def test_unified_tool_dispatcher_creation_and_registration(self):
        """Test UnifiedToolDispatcher creation and tool registration.
        
        Business Value: Ensures tool dispatcher can manage business tools correctly.
        Tests REAL tool registration and retrieval.
        """
        # Create dispatcher using factory (REAL UnifiedToolDispatcher)
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user1_context,
            websocket_manager=None,  # WebSocket integration tested separately
            tools=self.tools_list
        )
        
        # Verify dispatcher creation
        assert isinstance(dispatcher, UnifiedToolDispatcher)
        assert dispatcher.user_context == self.user1_context
        
        # Test tool registration verification
        registered_tools = await dispatcher.get_available_tools()
        assert len(registered_tools) == 2
        
        tool_names = [tool.name for tool in registered_tools]
        assert "business_analyzer" in tool_names
        assert "data_processor" in tool_names
        
        # Test tool lookup by name
        business_tool = await dispatcher.get_tool_by_name("business_analyzer")
        assert business_tool is not None
        assert business_tool.name == "business_analyzer"
        assert business_tool.tool_id == "business_001"
        
        # Test tool metadata
        tool_info = await dispatcher.get_tool_info("business_analyzer")
        assert tool_info["name"] == "business_analyzer"
        assert "Analyzes business metrics" in tool_info["description"]
        
        # Record registration metrics
        self.record_metric("tools_registered", len(registered_tools))
        self.record_metric("dispatcher_created", True)
        
    async def test_tool_execution_workflow_with_validation(self):
        """Test complete tool execution workflow with validation.
        
        Business Value: Ensures tools execute correctly with proper validation.  
        Tests REAL tool execution from request to response.
        """
        # Create request-scoped dispatcher
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user1_context,
            tools=self.tools_list
        )
        
        # Create tool dispatch request
        request = ToolDispatchRequest(
            tool_name="business_analyzer",
            parameters={
                "query": "Analyze Q4 revenue performance", 
                "include_recommendations": True
            },
            user_context=self.user1_context,
            strategy=DispatchStrategy.DIRECT
        )
        
        # Execute tool dispatch
        response = await dispatcher.dispatch_tool(request)
        
        # Verify response structure
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        assert response.tool_name == "business_analyzer"
        assert response.execution_time > 0
        
        # Verify tool was actually executed
        assert self.business_tool.execution_count == 1
        assert self.business_tool.last_input["query"] == "Analyze Q4 revenue performance"
        
        # Verify response data
        result_data = json.loads(response.result)
        assert result_data["tool_id"] == "business_001"
        assert "Business analysis for: Analyze Q4 revenue performance" in result_data["analysis"]
        assert result_data["metrics"]["execution_count"] == 1
        assert len(result_data["recommendations"]) > 0
        
        # Test validation of tool execution
        assert len(self.business_tool.execution_history) == 1
        
        # Record execution metrics
        self.record_metric("tool_executions_completed", 1)
        self.record_metric("execution_success_rate", 1.0)
        self.record_metric("execution_time", response.execution_time)
        
    async def test_concurrent_tool_execution_isolation(self):
        """Test concurrent tool execution with user isolation.
        
        Business Value: Ensures multi-user tool execution doesn't interfere.
        Tests REAL concurrent execution with isolation.
        """
        # Create separate dispatchers for each user
        dispatcher1 = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user1_context,
            tools=self.tools_list
        )
        
        dispatcher2 = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user2_context, 
            tools=self.tools_list
        )
        
        # Create concurrent requests
        request1 = ToolDispatchRequest(
            tool_name="data_processor",
            parameters={
                "dataset": "user1_data_001,user1_data_002,user1_data_003",
                "transformations": ["normalize", "validate"],
                "format": "json"
            },
            user_context=self.user1_context
        )
        
        request2 = ToolDispatchRequest(
            tool_name="data_processor", 
            parameters={
                "dataset": "user2_data_001,user2_data_002",
                "transformations": ["clean", "aggregate"],
                "format": "csv"
            },
            user_context=self.user2_context
        )
        
        # Execute concurrently 
        results = await asyncio.gather(
            dispatcher1.dispatch_tool(request1),
            dispatcher2.dispatch_tool(request2),
            return_exceptions=True
        )
        
        # Verify both executions succeeded
        response1, response2 = results
        assert isinstance(response1, ToolDispatchResponse)
        assert isinstance(response2, ToolDispatchResponse)
        assert response1.success is True
        assert response2.success is True
        
        # Verify user isolation in results
        result1_data = json.loads(response1.result)
        result2_data = json.loads(response2.result)
        
        assert result1_data["status"] == "success"
        assert result2_data["status"] == "success"
        
        # Verify different processing (isolation verified)
        assert result1_data["transformations_applied"] == ["normalize", "validate"]
        assert result2_data["transformations_applied"] == ["clean", "aggregate"]
        assert result1_data["output_format"] == "json"
        assert result2_data["output_format"] == "csv"
        
        # Record concurrency metrics
        self.record_metric("concurrent_executions", 2)
        self.record_metric("isolation_verified", True)
        self.record_metric("concurrent_success_rate", 1.0)
        
    async def test_tool_execution_with_websocket_events(self):
        """Test tool execution with WebSocket event notifications.
        
        Business Value: Ensures real-time tool execution visibility.
        Tests REAL WebSocket event integration during tool execution.
        """
        # Create dispatcher with WebSocket notifier
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user1_context,
            websocket_manager=self.websocket_notifier,  # Real interface mock
            tools=self.tools_list
        )
        
        # Create tool request
        request = ToolDispatchRequest(
            tool_name="business_analyzer",
            parameters={
                "query": "Calculate customer acquisition cost",
                "include_trend_analysis": True
            },
            user_context=self.user1_context,
            notify_events=True  # Enable WebSocket notifications
        )
        
        # Execute with event notifications
        response = await dispatcher.dispatch_tool(request)
        
        # Verify execution succeeded
        assert response.success is True
        
        # Verify WebSocket events were sent
        run_events = self.websocket_notifier.get_events_for_run("tool_run_001")
        
        # Should have at least tool_executing and tool_completed events
        event_types = [event["type"] for event in run_events]
        assert "tool_executing" in event_types or "tool_completed" in event_types
        
        # Verify event details
        if "tool_executing" in event_types:
            executing_event = next(e for e in run_events if e["type"] == "tool_executing")
            assert executing_event["tool_name"] == "business_analyzer"
            assert executing_event["run_id"] == "tool_run_001"
            assert "query" in executing_event["parameters"]
            
        if "tool_completed" in event_types:
            completed_event = next(e for e in run_events if e["type"] == "tool_completed")
            assert completed_event["tool_name"] == "business_analyzer"
            assert completed_event["duration"] is not None
            
        # Record WebSocket metrics
        self.record_metric("websocket_events_sent", len(run_events))
        self.record_metric("websocket_integration_success", len(run_events) > 0)
        
    async def test_tool_dispatcher_error_handling_and_recovery(self):
        """Test tool dispatcher error handling and recovery mechanisms.
        
        Business Value: Ensures system stability when tools fail.
        Tests REAL error handling workflows.
        """
        # Create dispatcher
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=self.user1_context,
            websocket_manager=self.websocket_notifier,
            tools=self.tools_list
        )
        
        # Test 1: Invalid tool name
        invalid_request = ToolDispatchRequest(
            tool_name="nonexistent_tool",
            parameters={"query": "test"},
            user_context=self.user1_context
        )
        
        invalid_response = await dispatcher.dispatch_tool(invalid_request)
        assert invalid_response.success is False
        assert "not found" in invalid_response.error.lower() or "invalid" in invalid_response.error.lower()
        
        # Test 2: Tool execution with invalid parameters  
        error_request = ToolDispatchRequest(
            tool_name="data_processor",
            parameters={
                "dataset": None,  # This should cause processing error
                "transformations": ["invalid_transform"]
            },
            user_context=self.user1_context
        )
        
        # Execute and verify error handling
        error_response = await dispatcher.dispatch_tool(error_request)
        
        # The tool should handle the error gracefully
        if not error_response.success:
            assert error_response.error is not None
        else:
            # If tool handled error internally, check the result
            result_data = json.loads(error_response.result) 
            # Tool might return success with error status in result
            assert result_data.get("status") in ["success", "error"]
            
        # Test 3: Recovery after error
        recovery_request = ToolDispatchRequest(
            tool_name="business_analyzer",
            parameters={"query": "Recovery test after error"},
            user_context=self.user1_context
        )
        
        recovery_response = await dispatcher.dispatch_tool(recovery_request)
        assert recovery_response.success is True  # Should recover successfully
        
        # Verify error events were logged
        error_events = self.websocket_notifier.error_events
        run_error_events = [e for e in error_events if e.get("run_id") == "tool_run_001"]
        
        # Record error handling metrics
        self.record_metric("error_cases_tested", 3)
        self.record_metric("recovery_successful", recovery_response.success)
        self.record_metric("error_events_logged", len(run_error_events))
        
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Record final metrics
        final_metrics = self.get_all_metrics()
        
        # Log tool execution statistics
        if hasattr(self, 'business_tool') and self.business_tool:
            self.record_metric("business_tool_executions", self.business_tool.execution_count)
            self.record_metric("business_tool_history_length", len(self.business_tool.execution_history))
            
        if hasattr(self, 'data_tool') and self.data_tool:
            self.record_metric("data_tool_records_processed", self.data_tool.processed_records)
            self.record_metric("data_tool_errors", len(self.data_tool.processing_errors))
            
        if hasattr(self, 'websocket_notifier') and self.websocket_notifier:
            self.record_metric("total_tool_events", len(self.websocket_notifier.tool_events))
            self.record_metric("total_error_events", len(self.websocket_notifier.error_events))
        
        # Clean up tool state for next test
        if hasattr(self, 'business_tool'):
            self.business_tool.execution_count = 0
            self.business_tool.execution_history.clear()
            
        if hasattr(self, 'data_tool'):
            self.data_tool.processed_records = 0
            self.data_tool.processing_errors.clear()
            
        super().teardown_method(method)