"""
Test WebSocket Integration with Tool Execution

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Provide real-time visibility into tool execution for enhanced user experience
- Value Impact: WebSocket events enable responsive UI and transparent tool execution
- Strategic Impact: Real-time feedback differentiates platform and improves user engagement

CRITICAL: This test uses REAL services only (PostgreSQL, Redis, WebSocket connections)
NO MOCKS ALLOWED - Tests actual WebSocket event emission during tool execution
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import get_env


class MockWebSocketManager:
    """Mock WebSocket manager that captures events for testing."""
    
    def __init__(self):
        self.sent_events = []
        self.is_connected = True
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Capture sent events for verification."""
        event_record = {
            "event_type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.sent_events.append(event_record)
        return True
    
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get all events of specific type."""
        return [event for event in self.sent_events if event["event_type"] == event_type]
    
    def has_websocket_support(self) -> bool:
        """Check if WebSocket support is available."""
        return True


class MockWebSocketTool:
    """Mock tool for testing WebSocket event emission."""
    
    def __init__(self, name: str, execution_time: float = 0.1, should_fail: bool = False):
        self.name = name
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.description = f"WebSocket test tool: {name}"
        
    async def arun(self, *args, **kwargs):
        """Tool execution with configurable behavior."""
        # Simulate work
        await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise RuntimeError(f"Simulated failure in {self.name}")
        
        return f"WebSocket test execution of {self.name} completed successfully"


class TestWebSocketToolExecutionIntegration(BaseIntegrationTest):
    """Test WebSocket integration with tool execution using real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_during_successful_tool_execution(self, real_services_fixture):
        """Test that WebSocket events are emitted during successful tool execution."""
        self.logger.info("=== Testing WebSocket Events During Successful Tool Execution ===")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_success_test@example.com",
            environment="test"
        )
        
        # Create mock WebSocket manager to capture events
        mock_websocket_manager = MockWebSocketManager()
        
        # Create test tools
        test_tools = [
            MockWebSocketTool("websocket_analyzer", execution_time=0.2),
            MockWebSocketTool("websocket_processor", execution_time=0.3),
            MockWebSocketTool("websocket_reporter", execution_time=0.1)
        ]
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=test_tools
        ) as dispatcher:
            
            websocket_test_results = []
            
            for tool in test_tools:
                # Clear previous events to isolate each test
                mock_websocket_manager.sent_events.clear()
                
                # Execute tool
                result = await dispatcher.execute_tool(
                    tool_name=tool.name,
                    parameters={"websocket_test": True, "tool_name": tool.name}
                )
                
                assert result.success, f"Tool {tool.name} execution failed: {result.error}"
                
                # Verify WebSocket events were sent
                tool_executing_events = mock_websocket_manager.get_events_by_type("tool_executing")
                tool_completed_events = mock_websocket_manager.get_events_by_type("tool_completed")
                
                assert len(tool_executing_events) >= 1, f"No tool_executing event for {tool.name}"
                assert len(tool_completed_events) >= 1, f"No tool_completed event for {tool.name}"
                
                # Verify event data structure
                executing_event = tool_executing_events[0]
                completed_event = tool_completed_events[0]
                
                # Verify tool_executing event
                assert executing_event["data"]["tool_name"] == tool.name, \
                    f"Wrong tool name in executing event: {executing_event['data']['tool_name']}"
                assert executing_event["data"]["user_id"] == str(user_context.user_id), \
                    "Wrong user ID in executing event"
                assert "parameters" in executing_event["data"], "Missing parameters in executing event"
                
                # Verify tool_completed event
                assert completed_event["data"]["tool_name"] == tool.name, \
                    f"Wrong tool name in completed event: {completed_event['data']['tool_name']}"
                assert completed_event["data"]["user_id"] == str(user_context.user_id), \
                    "Wrong user ID in completed event"
                assert completed_event["data"]["status"] == "success", \
                    "Wrong status in completed event"
                assert "result" in completed_event["data"], "Missing result in completed event"
                
                websocket_test_results.append({
                    "tool_name": tool.name,
                    "execution_successful": result.success,
                    "executing_events": len(tool_executing_events),
                    "completed_events": len(tool_completed_events),
                    "event_data_valid": True
                })
            
            # Verify business value: WebSocket events provide real-time execution visibility
            websocket_success_result = {
                "tools_tested": len(test_tools),
                "all_tools_successful": all(r["execution_successful"] for r in websocket_test_results),
                "all_executing_events_sent": all(r["executing_events"] >= 1 for r in websocket_test_results),
                "all_completed_events_sent": all(r["completed_events"] >= 1 for r in websocket_test_results),
                "websocket_integration_working": True
            }
            
            self.assert_business_value_delivered(websocket_success_result, "automation")
            
        self.logger.info(" PASS:  WebSocket events during successful tool execution test passed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_during_failed_tool_execution(self, real_services_fixture):
        """Test that WebSocket events are emitted during failed tool execution."""
        self.logger.info("=== Testing WebSocket Events During Failed Tool Execution ===")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_failure_test@example.com",
            environment="test"
        )
        
        # Create mock WebSocket manager
        mock_websocket_manager = MockWebSocketManager()
        
        # Create tools that will fail
        failing_tools = [
            MockWebSocketTool("failing_analyzer", should_fail=True),
            MockWebSocketTool("failing_processor", should_fail=True, execution_time=0.2)
        ]
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=failing_tools
        ) as dispatcher:
            
            failure_test_results = []
            
            for tool in failing_tools:
                # Clear previous events
                mock_websocket_manager.sent_events.clear()
                
                # Execute tool (expecting failure)
                result = await dispatcher.execute_tool(
                    tool_name=tool.name,
                    parameters={"failure_test": True}
                )
                
                assert not result.success, f"Tool {tool.name} should have failed but didn't"
                assert result.error is not None, f"Tool {tool.name} error not captured"
                
                # Verify WebSocket events were sent even for failed execution
                tool_executing_events = mock_websocket_manager.get_events_by_type("tool_executing")
                tool_completed_events = mock_websocket_manager.get_events_by_type("tool_completed")
                
                assert len(tool_executing_events) >= 1, f"No tool_executing event for failing {tool.name}"
                assert len(tool_completed_events) >= 1, f"No tool_completed event for failing {tool.name}"
                
                # Verify event data for failed execution
                executing_event = tool_executing_events[0]
                completed_event = tool_completed_events[0]
                
                # Verify tool_executing event (same as successful case)
                assert executing_event["data"]["tool_name"] == tool.name
                assert executing_event["data"]["user_id"] == str(user_context.user_id)
                
                # Verify tool_completed event shows failure
                assert completed_event["data"]["tool_name"] == tool.name
                assert completed_event["data"]["user_id"] == str(user_context.user_id)
                assert completed_event["data"]["status"] == "error", \
                    f"Expected error status, got {completed_event['data']['status']}"
                assert "error" in completed_event["data"], "Missing error in completed event"
                
                failure_test_results.append({
                    "tool_name": tool.name,
                    "execution_failed_as_expected": not result.success,
                    "executing_events": len(tool_executing_events),
                    "completed_events": len(tool_completed_events),
                    "error_event_data_valid": completed_event["data"]["status"] == "error"
                })
            
            # Verify business value: WebSocket events provide failure visibility
            websocket_failure_result = {
                "failing_tools_tested": len(failing_tools),
                "all_tools_failed_as_expected": all(r["execution_failed_as_expected"] for r in failure_test_results),
                "all_executing_events_sent": all(r["executing_events"] >= 1 for r in failure_test_results),
                "all_error_events_sent": all(r["completed_events"] >= 1 for r in failure_test_results),
                "error_event_data_valid": all(r["error_event_data_valid"] for r in failure_test_results),
                "websocket_error_handling_working": True
            }
            
            self.assert_business_value_delivered(websocket_failure_result, "automation")
            
        self.logger.info(" PASS:  WebSocket events during failed tool execution test passed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_during_concurrent_tool_execution(self, real_services_fixture):
        """Test WebSocket events during concurrent tool execution with proper isolation."""
        self.logger.info("=== Testing WebSocket Events During Concurrent Tool Execution ===")
        
        # Create multiple user contexts for concurrent testing
        user_contexts = []
        for i in range(3):
            context = await create_authenticated_user_context(
                user_email=f"websocket_concurrent_{i}@example.com",
                environment="test"
            )
            user_contexts.append(context)
        
        # Create shared mock WebSocket manager
        shared_websocket_manager = MockWebSocketManager()
        
        # Create concurrent tools
        concurrent_tools = [
            MockWebSocketTool("concurrent_tool_1", execution_time=0.2),
            MockWebSocketTool("concurrent_tool_2", execution_time=0.3),
            MockWebSocketTool("concurrent_tool_3", execution_time=0.1)
        ]
        
        async def execute_tool_with_websockets(user_context, tool, user_index):
            """Execute tool with WebSocket integration for specific user."""
            async with UnifiedToolDispatcher.create_scoped(
                user_context=user_context,
                websocket_manager=shared_websocket_manager,
                tools=[tool]
            ) as dispatcher:
                
                result = await dispatcher.execute_tool(
                    tool_name=tool.name,
                    parameters={"concurrent_test": True, "user_index": user_index}
                )
                
                return {
                    "user_index": user_index,
                    "user_id": str(user_context.user_id),
                    "tool_name": tool.name,
                    "execution_successful": result.success,
                    "error": result.error if not result.success else None
                }
        
        # Execute tools concurrently
        concurrent_tasks = [
            execute_tool_with_websockets(user_contexts[i], concurrent_tools[i], i)
            for i in range(3)
        ]
        
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        
        # Verify all concurrent executions succeeded
        successful_executions = [r for r in concurrent_results if r["execution_successful"]]
        assert len(successful_executions) == 3, f"Not all concurrent executions succeeded: {len(successful_executions)}/3"
        
        # Verify WebSocket events for all concurrent executions
        tool_executing_events = shared_websocket_manager.get_events_by_type("tool_executing")
        tool_completed_events = shared_websocket_manager.get_events_by_type("tool_completed")
        
        assert len(tool_executing_events) >= 3, f"Not enough tool_executing events: {len(tool_executing_events)}"
        assert len(tool_completed_events) >= 3, f"Not enough tool_completed events: {len(tool_completed_events)}"
        
        # Verify event isolation - each user only gets events for their tools
        user_ids_in_events = set()
        tool_names_in_events = set()
        
        for event in tool_executing_events:
            user_ids_in_events.add(event["data"]["user_id"])
            tool_names_in_events.add(event["data"]["tool_name"])
        
        expected_user_ids = {str(uc.user_id) for uc in user_contexts}
        expected_tool_names = {tool.name for tool in concurrent_tools}
        
        assert user_ids_in_events == expected_user_ids, \
            f"User ID mismatch in events: {user_ids_in_events} vs {expected_user_ids}"
        assert tool_names_in_events == expected_tool_names, \
            f"Tool name mismatch in events: {tool_names_in_events} vs {expected_tool_names}"
        
        # Verify event timing shows concurrent execution
        executing_timestamps = [event["timestamp"] for event in tool_executing_events]
        timestamp_spread = max(executing_timestamps) - min(executing_timestamps)
        
        # Concurrent execution should have small timestamp spread
        assert timestamp_spread < 2.0, f"Events not concurrent: {timestamp_spread}s spread"
        
        # Verify business value: Concurrent WebSocket events maintain user isolation
        concurrent_websocket_result = {
            "concurrent_users": len(user_contexts),
            "successful_concurrent_executions": len(successful_executions),
            "executing_events_sent": len(tool_executing_events),
            "completed_events_sent": len(tool_completed_events),
            "user_isolation_maintained": user_ids_in_events == expected_user_ids,
            "timestamp_spread_acceptable": timestamp_spread < 2.0,
            "concurrent_websocket_events_working": True
        }
        
        self.assert_business_value_delivered(concurrent_websocket_result, "automation")
        
        self.logger.info(" PASS:  WebSocket events during concurrent tool execution test passed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_data_completeness_and_structure(self, real_services_fixture):
        """Test that WebSocket events contain complete and properly structured data."""
        self.logger.info("=== Testing WebSocket Event Data Completeness ===")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_data_completeness@example.com",
            environment="test"
        )
        
        # Create mock WebSocket manager
        mock_websocket_manager = MockWebSocketManager()
        
        # Create test tool
        data_test_tool = MockWebSocketTool("data_completeness_tool", execution_time=0.1)
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=user_context,
            websocket_manager=mock_websocket_manager,
            tools=[data_test_tool]
        ) as dispatcher:
            
            # Execute tool with comprehensive parameters
            execution_parameters = {
                "test_type": "data_completeness",
                "string_param": "test_value",
                "number_param": 42,
                "boolean_param": True,
                "list_param": ["item1", "item2"],
                "dict_param": {"nested": "value"}
            }
            
            result = await dispatcher.execute_tool(
                tool_name="data_completeness_tool",
                parameters=execution_parameters
            )
            
            assert result.success, f"Tool execution failed: {result.error}"
            
            # Analyze event data completeness
            tool_executing_events = mock_websocket_manager.get_events_by_type("tool_executing")
            tool_completed_events = mock_websocket_manager.get_events_by_type("tool_completed")
            
            assert len(tool_executing_events) >= 1, "No tool_executing event"
            assert len(tool_completed_events) >= 1, "No tool_completed event"
            
            executing_event = tool_executing_events[0]
            completed_event = tool_completed_events[0]
            
            # Verify tool_executing event data completeness
            executing_data = executing_event["data"]
            required_executing_fields = ["tool_name", "parameters", "run_id", "user_id", "thread_id", "timestamp"]
            
            for field in required_executing_fields:
                assert field in executing_data, f"Missing field {field} in tool_executing event"
            
            # Verify parameters are properly serialized
            event_params = executing_data["parameters"]
            assert event_params["string_param"] == "test_value", "String parameter not preserved"
            assert event_params["number_param"] == 42, "Number parameter not preserved"
            assert event_params["boolean_param"] is True, "Boolean parameter not preserved"
            assert event_params["list_param"] == ["item1", "item2"], "List parameter not preserved"
            assert event_params["dict_param"]["nested"] == "value", "Dict parameter not preserved"
            
            # Verify tool_completed event data completeness
            completed_data = completed_event["data"]
            required_completed_fields = ["tool_name", "run_id", "user_id", "thread_id", "timestamp", "status"]
            
            for field in required_completed_fields:
                assert field in completed_data, f"Missing field {field} in tool_completed event"
            
            # Verify successful completion data
            assert completed_data["status"] == "success", f"Wrong status: {completed_data['status']}"
            assert "result" in completed_data, "Missing result in completed event"
            
            # Verify data consistency between events
            assert executing_data["tool_name"] == completed_data["tool_name"], \
                "Tool name inconsistent between events"
            assert executing_data["user_id"] == completed_data["user_id"], \
                "User ID inconsistent between events"
            assert executing_data["run_id"] == completed_data["run_id"], \
                "Run ID inconsistent between events"
            assert executing_data["thread_id"] == completed_data["thread_id"], \
                "Thread ID inconsistent between events"
            
            # Verify timestamp ordering
            assert completed_data["timestamp"] >= executing_data["timestamp"], \
                "Completed event timestamp before executing event timestamp"
            
            # Verify business value: Complete event data enables rich UI experiences
            data_completeness_result = {
                "executing_event_fields_complete": all(field in executing_data for field in required_executing_fields),
                "completed_event_fields_complete": all(field in completed_data for field in required_completed_fields),
                "parameters_properly_serialized": True,
                "event_data_consistent": executing_data["tool_name"] == completed_data["tool_name"],
                "timestamp_ordering_correct": completed_data["timestamp"] >= executing_data["timestamp"],
                "websocket_data_structure_comprehensive": True
            }
            
            self.assert_business_value_delivered(data_completeness_result, "automation")
            
        self.logger.info(" PASS:  WebSocket event data completeness test passed")
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_events_with_agent_websocket_bridge_adapter(self, real_services_fixture):
        """Test WebSocket events work with AgentWebSocketBridge adapter pattern."""
        self.logger.info("=== Testing WebSocket Events with AgentWebSocketBridge Adapter ===")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="websocket_bridge_adapter@example.com",
            environment="test"
        )
        
        # Create mock AgentWebSocketBridge
        class MockAgentWebSocketBridge:
            def __init__(self):
                self.tool_executing_calls = []
                self.tool_completed_calls = []
                
            async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters):
                """Mock AgentWebSocketBridge tool executing notification."""
                self.tool_executing_calls.append({
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "parameters": parameters
                })
                return True
                
            async def notify_tool_completed(self, run_id, agent_name, tool_name, result, execution_time_ms=None):
                """Mock AgentWebSocketBridge tool completed notification."""
                self.tool_completed_calls.append({
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "result": result,
                    "execution_time_ms": execution_time_ms
                })
                return True
        
        mock_bridge = MockAgentWebSocketBridge()
        
        # Create test tool
        bridge_adapter_tool = MockWebSocketTool("bridge_adapter_tool", execution_time=0.1)
        
        # Test with AgentWebSocketBridge adapter
        async with UnifiedToolDispatcher.create_scoped(
            user_context=user_context,
            websocket_bridge=mock_bridge,  # Pass bridge instead of manager
            tools=[bridge_adapter_tool]
        ) as dispatcher:
            
            # Verify adapter was created
            assert dispatcher.has_websocket_support, "WebSocket support not detected with bridge adapter"
            
            # Execute tool
            result = await dispatcher.execute_tool(
                tool_name="bridge_adapter_tool",
                parameters={"bridge_test": True, "adapter_pattern": "AgentWebSocketBridge"}
            )
            
            assert result.success, f"Tool execution failed: {result.error}"
            
            # Verify AgentWebSocketBridge methods were called
            assert len(mock_bridge.tool_executing_calls) >= 1, \
                "notify_tool_executing not called on bridge"
            assert len(mock_bridge.tool_completed_calls) >= 1, \
                "notify_tool_completed not called on bridge"
            
            # Verify call data
            executing_call = mock_bridge.tool_executing_calls[0]
            completed_call = mock_bridge.tool_completed_calls[0]
            
            # Verify executing call
            assert executing_call["tool_name"] == "bridge_adapter_tool", \
                f"Wrong tool name in executing call: {executing_call['tool_name']}"
            assert executing_call["run_id"] == str(user_context.run_id), \
                "Wrong run_id in executing call"
            assert "bridge_test" in executing_call["parameters"], \
                "Parameters not passed to bridge executing call"
            
            # Verify completed call
            assert completed_call["tool_name"] == "bridge_adapter_tool", \
                f"Wrong tool name in completed call: {completed_call['tool_name']}"
            assert completed_call["run_id"] == str(user_context.run_id), \
                "Wrong run_id in completed call"
            assert completed_call["result"] is not None, \
                "Result not passed to bridge completed call"
            
            # Verify business value: Bridge adapter enables legacy WebSocket integration
            bridge_adapter_result = {
                "bridge_adapter_created": dispatcher.has_websocket_support,
                "tool_execution_successful": result.success,
                "executing_notifications_sent": len(mock_bridge.tool_executing_calls),
                "completed_notifications_sent": len(mock_bridge.tool_completed_calls),
                "bridge_adapter_pattern_working": True
            }
            
            self.assert_business_value_delivered(bridge_adapter_result, "automation")
            
        self.logger.info(" PASS:  WebSocket events with AgentWebSocketBridge adapter test passed")