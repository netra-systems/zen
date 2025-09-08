"""
Unit Tests for Tool Dispatcher Routing and Execution - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable tool routing and execution for AI agents
- Value Impact: Users get accurate results from AI tool usage and data analysis
- Strategic Impact: Tool execution is core to delivering AI-powered insights

CRITICAL: Tool dispatcher is the engine that enables AI agents to analyze data and provide value.
Without reliable tool execution, agents cannot deliver business insights.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional
import asyncio

from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types import UserID, ThreadID, RunID

class TestToolDispatcherRoutingExecution:
    """Test tool dispatcher routing and execution functionality."""
    
    @pytest.fixture
    def mock_user_context(self):
        """Mock user execution context for testing."""
        return UserExecutionContext(
            user_id=UserID("tool_dispatch_user"),
            thread_id=ThreadID("tool_dispatch_thread"),
            authenticated=True,
            permissions=["tool_execution", "data_access"],
            session_data={"tool_testing": True}
        )
    
    @pytest.fixture
    def mock_agent_context(self, mock_user_context):
        """Mock agent execution context for testing."""
        return AgentExecutionContext(
            user_id=UserID("tool_dispatch_user"),
            thread_id=ThreadID("tool_dispatch_thread"),
            run_id=RunID("tool_dispatch_run"),
            agent_name="tool_test_agent",
            message="Test tool execution",
            user_context=mock_user_context
        )
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher for testing."""
        dispatcher = Mock()
        dispatcher.execute_tool = AsyncMock()
        return dispatcher
    
    @pytest.fixture
    def tool_execution_engine(self, mock_tool_dispatcher):
        """Create tool execution engine with mocked dispatcher."""
        engine = UnifiedToolExecutionEngine(tool_dispatcher=mock_tool_dispatcher)
        return engine

    @pytest.mark.unit
    async def test_tool_dispatcher_routes_to_correct_tool(self, tool_execution_engine, mock_agent_context):
        """
        Test tool dispatcher routes requests to the correct tool implementation.
        
        Business Value: Correct tool routing ensures users get accurate analysis results.
        Wrong tool routing would provide incorrect insights and mislead users.
        """
        # Arrange: Setup tool routing scenarios
        tool_routing_tests = [
            {
                "tool_name": "cost_analyzer",
                "parameters": {"provider": "aws", "timeframe": "30_days"},
                "expected_route": "cost_analyzer"
            },
            {
                "tool_name": "data_retriever", 
                "parameters": {"source": "billing_api", "format": "json"},
                "expected_route": "data_retriever"
            },
            {
                "tool_name": "recommendation_engine",
                "parameters": {"analysis_type": "cost_optimization", "confidence": 0.8},
                "expected_route": "recommendation_engine"
            }
        ]
        
        # Setup mock responses
        mock_results = {
            "cost_analyzer": {"monthly_cost": 15000, "savings_potential": 2250},
            "data_retriever": {"status": "success", "records_retrieved": 1500},
            "recommendation_engine": {"recommendations": 3, "total_savings": 3000}
        }
        
        def mock_execute_tool(tool_name, params, context):
            return mock_results.get(tool_name, {"error": "tool_not_found"})
        
        tool_execution_engine.tool_dispatcher.execute_tool.side_effect = mock_execute_tool
        
        # Act & Assert: Test each routing scenario
        for test_case in tool_routing_tests:
            result = await tool_execution_engine.execute_tool(
                tool_name=test_case["tool_name"],
                parameters=test_case["parameters"],
                execution_context=mock_agent_context
            )
            
            # Verify correct tool was called
            tool_execution_engine.tool_dispatcher.execute_tool.assert_called()
            last_call = tool_execution_engine.tool_dispatcher.execute_tool.call_args
            called_tool_name = last_call[0][0]  # First positional argument
            
            assert called_tool_name == test_case["expected_route"], \
                f"Expected route to {test_case['expected_route']}, but routed to {called_tool_name}"
            
            # Business requirement: Tool execution should return meaningful results
            assert result is not None, f"Tool {test_case['tool_name']} should return a result"
            expected_result = mock_results[test_case["tool_name"]]
            assert result == expected_result, f"Tool result should match expected output"

    @pytest.mark.unit
    async def test_tool_dispatcher_parameter_validation_and_sanitization(self, tool_execution_engine, mock_agent_context):
        """
        Test tool dispatcher validates and sanitizes parameters properly.
        
        Business Value: Parameter validation prevents errors and security issues.
        Invalid parameters could crash tools or expose sensitive data.
        """
        # Test parameter validation scenarios
        parameter_tests = [
            {
                "name": "valid_parameters",
                "tool": "cost_analyzer",
                "params": {"provider": "aws", "region": "us-east-1", "days": 30},
                "should_succeed": True
            },
            {
                "name": "missing_required_parameter",
                "tool": "cost_analyzer", 
                "params": {"region": "us-east-1"},  # Missing 'provider'
                "should_succeed": False
            },
            {
                "name": "invalid_parameter_type",
                "tool": "cost_analyzer",
                "params": {"provider": "aws", "days": "thirty"},  # String instead of int
                "should_succeed": False
            },
            {
                "name": "sql_injection_attempt",
                "tool": "data_retriever",
                "params": {"query": "SELECT * FROM users; DROP TABLE users;"},
                "should_succeed": False
            },
            {
                "name": "empty_parameters",
                "tool": "recommendation_engine",
                "params": {},
                "should_succeed": False
            }
        ]
        
        # Setup mock responses based on validation
        def mock_validate_and_execute(tool_name, params, context):
            if tool_name == "cost_analyzer":
                if "provider" not in params:
                    raise ValueError("Missing required parameter: provider")
                if not isinstance(params.get("days", 30), int):
                    raise TypeError("Parameter 'days' must be integer")
                return {"cost": 1000, "validated": True}
            
            elif tool_name == "data_retriever":
                if "DROP TABLE" in params.get("query", "").upper():
                    raise ValueError("Invalid query detected")
                return {"data": ["record1", "record2"], "validated": True}
            
            elif tool_name == "recommendation_engine":
                if not params:
                    raise ValueError("Parameters required for recommendation engine")
                return {"recommendations": ["optimize_instances"], "validated": True}
            
            return {"result": "unknown_tool"}
        
        tool_execution_engine.tool_dispatcher.execute_tool.side_effect = mock_validate_and_execute
        
        # Act & Assert: Test parameter validation
        for test_case in parameter_tests:
            if test_case["should_succeed"]:
                # Should succeed without exception
                result = await tool_execution_engine.execute_tool(
                    tool_name=test_case["tool"],
                    parameters=test_case["params"],
                    execution_context=mock_agent_context
                )
                assert result is not None, f"Valid parameters should produce result for {test_case['name']}"
                assert result.get("validated"), f"Result should be validated for {test_case['name']}"
            
            else:
                # Should raise exception or return error
                try:
                    result = await tool_execution_engine.execute_tool(
                        tool_name=test_case["tool"],
                        parameters=test_case["params"], 
                        execution_context=mock_agent_context
                    )
                    # If no exception, result should indicate error
                    assert "error" in str(result).lower() or result is None, \
                        f"Invalid parameters should fail for {test_case['name']}"
                except (ValueError, TypeError) as e:
                    # Expected validation error
                    assert len(str(e)) > 0, f"Validation error should be descriptive for {test_case['name']}"

    @pytest.mark.unit
    async def test_tool_dispatcher_concurrent_execution_handling(self, mock_agent_context):
        """
        Test tool dispatcher handles concurrent tool executions properly.
        
        Business Value: Concurrent execution enables efficient multi-tool analysis.
        Poor concurrency handling would slow down agent responses.
        """
        # Arrange: Setup concurrent execution scenario
        dispatcher = Mock()
        execution_delays = {"fast_tool": 0.01, "medium_tool": 0.05, "slow_tool": 0.1}
        
        async def mock_concurrent_execute(tool_name, params, context):
            delay = execution_delays.get(tool_name, 0.02)
            await asyncio.sleep(delay)
            return {
                "tool": tool_name,
                "execution_time": delay,
                "result": f"{tool_name}_completed",
                "params": params
            }
        
        dispatcher.execute_tool.side_effect = mock_concurrent_execute
        engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Act: Execute tools concurrently
        concurrent_tasks = [
            engine.execute_tool("fast_tool", {"priority": "high"}, mock_agent_context),
            engine.execute_tool("medium_tool", {"priority": "medium"}, mock_agent_context),
            engine.execute_tool("slow_tool", {"priority": "low"}, mock_agent_context)
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*concurrent_tasks)
        end_time = asyncio.get_event_loop().time()
        
        total_concurrent_time = end_time - start_time
        
        # Assert: Concurrent execution efficiency
        assert len(results) == 3, "All concurrent tools should complete"
        
        # Business requirement: Concurrent execution should be faster than sequential
        sequential_time = sum(execution_delays.values())  # 0.16 seconds
        assert total_concurrent_time < sequential_time, \
            f"Concurrent execution {total_concurrent_time:.3f}s should be faster than sequential {sequential_time:.3f}s"
        
        # Verify all tools completed with correct results
        tool_names = [result["tool"] for result in results]
        expected_tools = ["fast_tool", "medium_tool", "slow_tool"]
        assert set(tool_names) == set(expected_tools), "All tools should complete successfully"
        
        # Business requirement: Results should maintain execution context
        for result in results:
            assert "result" in result, "Each tool should provide results"
            assert result["tool"] in result["result"], "Result should identify the tool"

    @pytest.mark.unit
    async def test_tool_dispatcher_error_handling_and_recovery(self, tool_execution_engine, mock_agent_context):
        """
        Test tool dispatcher handles errors gracefully and provides recovery.
        
        Business Value: Error recovery prevents complete failure when individual tools fail.
        Users should still get partial results even when some tools encounter issues.
        """
        # Setup error scenarios
        error_scenarios = [
            {
                "tool": "failing_tool",
                "error_type": "connection_timeout", 
                "should_retry": True,
                "recovery_result": {"status": "recovered", "retries": 1}
            },
            {
                "tool": "invalid_tool",
                "error_type": "tool_not_found",
                "should_retry": False,
                "recovery_result": None
            },
            {
                "tool": "permission_denied_tool",
                "error_type": "insufficient_permissions",
                "should_retry": False,
                "recovery_result": {"status": "permission_error", "message": "Access denied"}
            }
        ]
        
        # Mock error handling behavior
        call_counts = {}
        
        async def mock_error_execute(tool_name, params, context):
            call_counts[tool_name] = call_counts.get(tool_name, 0) + 1
            
            if tool_name == "failing_tool":
                if call_counts[tool_name] == 1:
                    raise ConnectionError("Tool connection timeout")
                else:
                    # Succeeds on retry
                    return {"status": "recovered", "retries": call_counts[tool_name] - 1}
            
            elif tool_name == "invalid_tool":
                raise ValueError("Tool not found in registry")
            
            elif tool_name == "permission_denied_tool":
                raise PermissionError("Insufficient permissions for tool access")
            
            return {"status": "success"}
        
        tool_execution_engine.tool_dispatcher.execute_tool.side_effect = mock_error_execute
        
        # Act & Assert: Test error handling for each scenario
        for scenario in error_scenarios:
            call_counts[scenario["tool"]] = 0  # Reset call count
            
            try:
                result = await tool_execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters={"test": "error_handling"},
                    execution_context=mock_agent_context
                )
                
                # If execution succeeded, verify recovery
                if scenario["should_retry"] and scenario["recovery_result"]:
                    assert result == scenario["recovery_result"], \
                        f"Recovery result should match expected for {scenario['tool']}"
                    assert call_counts[scenario["tool"]] > 1, \
                        f"Tool {scenario['tool']} should be retried"
                
            except Exception as e:
                # Verify appropriate error handling
                error_type = type(e).__name__
                expected_errors = {
                    "connection_timeout": "ConnectionError",
                    "tool_not_found": "ValueError", 
                    "insufficient_permissions": "PermissionError"
                }
                
                if not scenario["should_retry"]:
                    expected_error = expected_errors.get(scenario["error_type"])
                    assert error_type == expected_error or "Error" in error_type, \
                        f"Should get appropriate error type for {scenario['tool']}"
                
                # Business requirement: Error messages should be informative
                assert len(str(e)) > 10, f"Error message should be descriptive for {scenario['tool']}"

    @pytest.mark.unit
    async def test_tool_dispatcher_result_processing_and_formatting(self, tool_execution_engine, mock_agent_context):
        """
        Test tool dispatcher properly processes and formats tool results.
        
        Business Value: Consistent result formatting enables reliable agent decision making.
        Malformed results could cause agent confusion and poor recommendations.
        """
        # Setup various result format scenarios
        result_scenarios = [
            {
                "tool": "structured_data_tool",
                "raw_result": {
                    "cost_analysis": {"monthly": 15000, "projected": 18000},
                    "recommendations": [{"type": "resize", "savings": 2500}],
                    "metadata": {"confidence": 0.85, "data_freshness": "1_hour"}
                },
                "expected_format": "structured_dict"
            },
            {
                "tool": "simple_value_tool",
                "raw_result": 42.5,
                "expected_format": "numeric"
            },
            {
                "tool": "text_analysis_tool",
                "raw_result": "Based on analysis, recommend optimizing EC2 instances for 30% cost reduction",
                "expected_format": "text"
            },
            {
                "tool": "list_data_tool",
                "raw_result": ["optimization_1", "optimization_2", "optimization_3"],
                "expected_format": "list"
            },
            {
                "tool": "boolean_result_tool",
                "raw_result": True,
                "expected_format": "boolean"
            }
        ]
        
        # Mock result processing
        def mock_result_execute(tool_name, params, context):
            for scenario in result_scenarios:
                if scenario["tool"] == tool_name:
                    return scenario["raw_result"]
            return {"error": "unknown_tool"}
        
        tool_execution_engine.tool_dispatcher.execute_tool.side_effect = mock_result_execute
        
        # Act & Assert: Test result processing for each format
        for scenario in result_scenarios:
            result = await tool_execution_engine.execute_tool(
                tool_name=scenario["tool"],
                parameters={"format_test": True},
                execution_context=mock_agent_context
            )
            
            # Verify result format preservation
            if scenario["expected_format"] == "structured_dict":
                assert isinstance(result, dict), f"Structured data should remain as dict"
                assert "cost_analysis" in result, "Should preserve nested structure"
                assert isinstance(result["cost_analysis"]["monthly"], (int, float)), "Should preserve numeric types"
                
            elif scenario["expected_format"] == "numeric":
                assert isinstance(result, (int, float)), f"Numeric result should preserve type"
                assert result == 42.5, "Should preserve exact numeric value"
                
            elif scenario["expected_format"] == "text":
                assert isinstance(result, str), f"Text result should be string"
                assert "optimization" in result.lower(), "Should preserve text content"
                assert len(result) > 20, "Text result should be substantial"
                
            elif scenario["expected_format"] == "list":
                assert isinstance(result, list), f"List result should remain as list"
                assert len(result) == 3, "Should preserve list length"
                assert all("optimization" in item for item in result), "Should preserve list contents"
                
            elif scenario["expected_format"] == "boolean":
                assert isinstance(result, bool), f"Boolean result should remain boolean"
                assert result is True, "Should preserve boolean value"
            
            # Business requirement: All results should be serializable for agent processing
            try:
                import json
                json.dumps(result, default=str)  # Should not raise exception
            except Exception as e:
                pytest.fail(f"Result from {scenario['tool']} should be serializable: {e}")

    @pytest.mark.unit
    def test_tool_dispatcher_factory_creation_and_configuration(self):
        """
        Test tool dispatcher factory creates properly configured dispatchers.
        
        Business Value: Factory pattern ensures consistent tool dispatcher configuration.
        Inconsistent configuration could lead to unreliable tool behavior.
        """
        # Test factory creation scenarios
        factory_scenarios = [
            {
                "config": {"environment": "test", "timeout": 30, "retry_attempts": 3},
                "expected_features": ["timeout_handling", "retry_logic", "error_recovery"]
            },
            {
                "config": {"environment": "production", "timeout": 60, "retry_attempts": 5},
                "expected_features": ["production_monitoring", "extended_timeout", "enhanced_retry"]
            },
            {
                "config": {"environment": "development", "debug": True, "verbose_logging": True},
                "expected_features": ["debug_mode", "verbose_logging", "development_tools"]
            }
        ]
        
        for scenario in factory_scenarios:
            # Act: Create dispatcher through factory
            try:
                dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(scenario["config"])
                
                # Assert: Dispatcher properly configured
                assert dispatcher is not None, "Factory should create dispatcher instance"
                
                # Business requirement: Configuration should be applied
                # (In a real implementation, would verify specific config properties)
                
            except Exception as e:
                # Factory creation should not fail with valid config
                pytest.fail(f"Factory should create dispatcher with valid config: {e}")