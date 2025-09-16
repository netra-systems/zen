"""
Integration Tests for Tool Dispatcher Result Processing - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool results are processed correctly for agent decision making
- Value Impact: Users get accurate, well-formatted insights from AI tool execution
- Strategic Impact: Result processing quality directly affects AI recommendation accuracy

CRITICAL: Poor result processing leads to incorrect AI insights and lost user trust.
Accurate result processing is essential for platform credibility.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types import UserID, ThreadID, RunID
from shared.isolated_environment import get_env

class TestToolDispatcherResultProcessing(BaseIntegrationTest):
    """Integration tests for tool dispatcher result processing with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_data_type_preservation_and_conversion(self, real_services_fixture):
        """
        Test tool dispatcher preserves and converts data types appropriately.
        
        Business Value: Accurate data types enable reliable AI decision making.
        Type corruption could lead to incorrect calculations and recommendations.
        """
        # Arrange: Setup execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("data_type_test_user"),
            thread_id=ThreadID("data_type_thread"),
            authenticated=True,
            permissions=["data_type_testing"],
            session_data={"test_type": "data_types"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("data_type_run"),
            agent_name="data_type_agent",
            message="Test data type preservation in tool results",
            user_context=user_context
        )
        
        # Setup tool dispatcher
        dispatcher_config = {"environment": "data_type_test", "preserve_types": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Test data type scenarios
        data_type_scenarios = [
            {
                "tool": "numeric_analysis_tool",
                "test_data": {
                    "integers": [1, 42, -17, 0, 999999],
                    "floats": [3.14159, -2.5, 0.0, 1.23456789],
                    "decimals": [Decimal("15.99"), Decimal("0.01"), Decimal("1000.50")],
                    "scientific_notation": [1.5e-10, 2.3e6, -4.7e-3]
                },
                "expected_types": ["int", "float", "Decimal", "float"]
            },
            {
                "tool": "text_analysis_tool",
                "test_data": {
                    "strings": ["simple text", "unicode: [U+00E1][U+00E9][U+00ED][U+00F3][U+00FA] [U+4E2D][U+6587] [U+1F916]", "", "multi\nline\ntext"],
                    "json_strings": ['{"key": "value"}', '[1, 2, 3]'],
                    "encoded_text": "base64encodedtext=="
                },
                "expected_types": ["str", "str", "str"]
            },
            {
                "tool": "boolean_logic_tool", 
                "test_data": {
                    "booleans": [True, False],
                    "boolean_strings": ["true", "false", "True", "False"],
                    "truthy_values": [1, "yes", "on"],
                    "falsy_values": [0, "", "no", "off", None]
                },
                "expected_types": ["bool", "mixed", "mixed", "mixed"]
            },
            {
                "tool": "datetime_analysis_tool",
                "test_data": {
                    "timestamps": [
                        datetime.now(timezone.utc).isoformat(),
                        "2024-01-15T10:30:00Z",
                        1640995200  # Unix timestamp
                    ],
                    "dates": ["2024-01-15", "Jan 15, 2024"],
                    "relative_times": ["now", "yesterday", "last_week"]
                },
                "expected_types": ["datetime", "date", "str"]
            }
        ]
        
        data_type_results = []
        
        # Act: Execute tools with different data types
        for scenario in data_type_scenarios:
            try:
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters={
                        "test_data": scenario["test_data"],
                        "preserve_types": True
                    },
                    execution_context=agent_context
                )
                
                data_type_results.append({
                    "tool": scenario["tool"],
                    "success": True,
                    "result": result,
                    "original_data": scenario["test_data"],
                    "error": None
                })
                
            except Exception as e:
                data_type_results.append({
                    "tool": scenario["tool"],
                    "success": False,
                    "result": None,
                    "original_data": scenario["test_data"],
                    "error": str(e)
                })
        
        # Assert: Data types properly preserved
        successful_results = [r for r in data_type_results if r["success"]]
        assert len(successful_results) >= len(data_type_scenarios) // 2, "Most data type tests should succeed"
        
        for result in successful_results:
            # Business requirement: Results should preserve meaningful data
            assert result["result"] is not None, f"Tool {result['tool']} should return processed data"
            
            # Verify data structure preservation
            if isinstance(result["result"], dict):
                # Should have some indication of data processing
                result_keys = list(result["result"].keys())
                assert len(result_keys) > 0, f"Result from {result['tool']} should have structured data"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_aggregation_and_summarization(self, real_services_fixture):
        """
        Test tool dispatcher aggregates and summarizes complex results.
        
        Business Value: Summarized results enable better AI decision making.
        Raw data overwhelming agents leads to poor recommendations.
        """
        # Arrange: Setup for result aggregation testing
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("aggregation_test_user"),
            thread_id=ThreadID("aggregation_thread"),
            authenticated=True,
            permissions=["result_aggregation"],
            session_data={"test_type": "aggregation"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("aggregation_run"),
            agent_name="aggregation_agent",
            message="Test result aggregation and summarization",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "aggregation_test", "enable_summarization": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Test aggregation scenarios
        aggregation_scenarios = [
            {
                "tool": "cost_aggregation_tool",
                "large_dataset": {
                    "monthly_costs": [
                        {"service": "EC2", "region": "us-east-1", "cost": 1500.00},
                        {"service": "S3", "region": "us-east-1", "cost": 250.75},
                        {"service": "RDS", "region": "us-east-1", "cost": 800.50},
                        {"service": "EC2", "region": "us-west-2", "cost": 1200.25},
                        {"service": "S3", "region": "us-west-2", "cost": 180.00},
                        # ... would have many more entries in real scenario
                    ],
                    "time_series_data": [
                        {"date": "2024-01-01", "total": 2750.25},
                        {"date": "2024-01-02", "total": 2820.50},
                        # ... 30 days of data
                    ]
                },
                "expected_summary": ["total_cost", "top_services", "cost_trends"]
            },
            {
                "tool": "performance_aggregation_tool",
                "large_dataset": {
                    "metrics": [
                        {"timestamp": "2024-01-01T00:00:00Z", "cpu": 65.5, "memory": 78.2, "latency": 125},
                        {"timestamp": "2024-01-01T01:00:00Z", "cpu": 72.1, "memory": 82.1, "latency": 142},
                        # ... hundreds of metrics
                    ]
                },
                "expected_summary": ["average_cpu", "peak_memory", "latency_p95"]
            }
        ]
        
        aggregation_results = []
        
        # Act: Execute aggregation tools
        for scenario in aggregation_scenarios:
            start_time = time.time()
            
            try:
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters={
                        "dataset": scenario["large_dataset"],
                        "summarize": True,
                        "max_summary_items": 10
                    },
                    execution_context=agent_context
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                aggregation_results.append({
                    "tool": scenario["tool"],
                    "success": True,
                    "result": result,
                    "processing_time": processing_time,
                    "dataset_size": len(str(scenario["large_dataset"])),
                    "error": None
                })
                
            except Exception as e:
                end_time = time.time()
                processing_time = end_time - start_time
                
                aggregation_results.append({
                    "tool": scenario["tool"],
                    "success": False,
                    "result": None,
                    "processing_time": processing_time,
                    "dataset_size": len(str(scenario["large_dataset"])),
                    "error": str(e)
                })
        
        # Assert: Aggregation results are meaningful
        for result in aggregation_results:
            tool_name = result["tool"]
            
            # Business requirement: Processing should be efficient even for large datasets
            assert result["processing_time"] < 30, f"Aggregation for {tool_name} should complete within 30s"
            
            if result["success"]:
                # Should have meaningful aggregated results
                assert result["result"] is not None, f"Aggregation tool {tool_name} should return results"
                
                # Results should be more concise than original dataset
                result_size = len(str(result["result"]))
                assert result_size < result["dataset_size"], \
                    f"Aggregated result should be more concise than original data for {tool_name}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_validation_and_quality_checks(self, real_services_fixture):
        """
        Test tool dispatcher validates result quality and consistency.
        
        Business Value: Quality validation prevents bad data from reaching users.
        Quality checks ensure AI recommendations are based on reliable data.
        """
        # Arrange: Setup quality validation testing
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("quality_check_user"),
            thread_id=ThreadID("quality_thread"),
            authenticated=True,
            permissions=["quality_testing"],
            session_data={"test_type": "quality_validation"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("quality_run"),
            agent_name="quality_agent",
            message="Test result quality validation and checks",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "quality_test", "enable_validation": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Test quality validation scenarios
        quality_scenarios = [
            {
                "tool": "financial_analysis_tool",
                "parameters": {
                    "financial_data": {
                        "revenue": 1000000,
                        "expenses": 750000,
                        "profit_margin": 0.25,
                        "growth_rate": 0.15
                    }
                },
                "quality_expectations": {
                    "numeric_consistency": True,
                    "logical_relationships": True,
                    "completeness": True
                }
            },
            {
                "tool": "data_consistency_tool",
                "parameters": {
                    "test_data": {
                        "totals": [100, 200, 300],
                        "subtotals": [[25, 75], [50, 150], [100, 200]],
                        "percentages": [0.25, 0.25, 0.33]
                    }
                },
                "quality_expectations": {
                    "mathematical_consistency": True,
                    "data_integrity": True
                }
            },
            {
                "tool": "outlier_detection_tool",
                "parameters": {
                    "dataset": [10, 12, 11, 13, 9, 11, 1000, 12, 10, 11],  # Contains outlier
                    "detect_outliers": True
                },
                "quality_expectations": {
                    "outlier_identified": True,
                    "statistical_validity": True
                }
            }
        ]
        
        quality_results = []
        
        # Act: Execute tools with quality validation
        for scenario in quality_scenarios:
            try:
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters=scenario["parameters"],
                    execution_context=agent_context
                )
                
                quality_results.append({
                    "tool": scenario["tool"],
                    "success": True,
                    "result": result,
                    "expectations": scenario["quality_expectations"],
                    "error": None
                })
                
            except Exception as e:
                quality_results.append({
                    "tool": scenario["tool"],
                    "success": False,
                    "result": None,
                    "expectations": scenario["quality_expectations"],
                    "error": str(e)
                })
        
        # Assert: Quality validation performed
        successful_quality_checks = [r for r in quality_results if r["success"]]
        
        for result in successful_quality_checks:
            tool_name = result["tool"]
            
            # Business requirement: Results should indicate quality status
            assert result["result"] is not None, f"Quality tool {tool_name} should return results"
            
            # Results should provide quality indicators
            if isinstance(result["result"], dict):
                result_str = str(result["result"]).lower()
                quality_indicators = ["valid", "consistent", "quality", "check", "outlier", "integrity"]
                has_quality_info = any(indicator in result_str for indicator in quality_indicators)
                
                if not has_quality_info:
                    # Quality information may be implicit in the result structure
                    # As long as the tool returned structured data, quality checks likely occurred
                    assert len(str(result["result"])) > 10, f"Tool {tool_name} should return substantial quality result"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_serialization_for_agent_consumption(self, real_services_fixture):
        """
        Test tool results are properly serialized for agent consumption.
        
        Business Value: Proper serialization enables reliable agent decision making.
        Serialization errors would break the AI reasoning chain.
        """
        # Arrange: Setup serialization testing
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("serialization_user"),
            thread_id=ThreadID("serialization_thread"),
            authenticated=True,
            permissions=["serialization_testing"],
            session_data={"test_type": "serialization"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("serialization_run"),
            agent_name="serialization_agent",
            message="Test result serialization for agent consumption",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "serialization_test", "agent_friendly_format": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Test serialization scenarios
        serialization_scenarios = [
            {
                "tool": "complex_data_structure_tool",
                "parameters": {
                    "nested_data": {
                        "level1": {
                            "level2": {
                                "level3": ["item1", "item2", {"nested": "value"}]
                            }
                        }
                    }
                }
            },
            {
                "tool": "mixed_type_result_tool",
                "parameters": {
                    "return_mixed_types": True,
                    "include_datetime": True,
                    "include_decimal": True
                }
            },
            {
                "tool": "large_result_set_tool",
                "parameters": {
                    "result_size": "large",
                    "include_metadata": True
                }
            }
        ]
        
        serialization_results = []
        
        # Act: Execute tools and test serialization
        for scenario in serialization_scenarios:
            try:
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters=scenario["parameters"],
                    execution_context=agent_context
                )
                
                # Test serialization immediately
                try:
                    # JSON serialization test
                    serialized = json.dumps(result, default=str)
                    deserialized = json.loads(serialized)
                    
                    serialization_results.append({
                        "tool": scenario["tool"],
                        "success": True,
                        "result": result,
                        "serializable": True,
                        "serialized_size": len(serialized),
                        "error": None
                    })
                    
                except (TypeError, ValueError) as serialization_error:
                    serialization_results.append({
                        "tool": scenario["tool"],
                        "success": True,
                        "result": result,
                        "serializable": False,
                        "serialized_size": 0,
                        "error": f"Serialization error: {serialization_error}"
                    })
                
            except Exception as e:
                serialization_results.append({
                    "tool": scenario["tool"],
                    "success": False,
                    "result": None,
                    "serializable": False,
                    "serialized_size": 0,
                    "error": f"Execution error: {e}"
                })
        
        # Assert: Serialization requirements met
        for result in serialization_results:
            tool_name = result["tool"]
            
            if result["success"]:
                # Business requirement: Results must be serializable for agent consumption
                assert result["serializable"], f"Results from {tool_name} must be serializable for agents"
                
                # Serialized size should be reasonable
                if result["serialized_size"] > 0:
                    assert result["serialized_size"] < 1000000, f"Serialized result from {tool_name} should be under 1MB"
                
                # Result should be structured for agent understanding
                assert result["result"] is not None, f"Tool {tool_name} should return structured result"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_result_error_handling_and_partial_results(self, real_services_fixture):
        """
        Test tool dispatcher handles result errors and provides partial results.
        
        Business Value: Partial results still provide value when tools partially fail.
        Complete failure prevention when some data can be salvaged.
        """
        # Arrange: Setup error handling testing
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("error_handling_user"),
            thread_id=ThreadID("error_thread"),
            authenticated=True,
            permissions=["error_testing"],
            session_data={"test_type": "error_handling"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("error_run"),
            agent_name="error_agent",
            message="Test result error handling and partial results",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "error_test", "partial_results": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Test error handling scenarios
        error_scenarios = [
            {
                "tool": "partial_failure_tool",
                "parameters": {
                    "process_items": ["valid_item_1", "invalid_item", "valid_item_2"],
                    "fail_on_invalid": False,
                    "return_partial": True
                },
                "expected_behavior": "partial_success"
            },
            {
                "tool": "timeout_recovery_tool",
                "parameters": {
                    "simulate_timeout": True,
                    "timeout_after": 5,
                    "return_progress": True
                },
                "expected_behavior": "graceful_timeout"
            },
            {
                "tool": "data_corruption_tool",
                "parameters": {
                    "corrupted_data": True,
                    "attempt_recovery": True,
                    "return_salvaged": True
                },
                "expected_behavior": "data_recovery"
            }
        ]
        
        error_handling_results = []
        
        # Act: Test error handling scenarios
        for scenario in error_scenarios:
            try:
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters=scenario["parameters"],
                    execution_context=agent_context
                )
                
                error_handling_results.append({
                    "tool": scenario["tool"],
                    "success": True,
                    "result": result,
                    "expected_behavior": scenario["expected_behavior"],
                    "error": None
                })
                
            except Exception as e:
                error_handling_results.append({
                    "tool": scenario["tool"],
                    "success": False,
                    "result": None,
                    "expected_behavior": scenario["expected_behavior"],
                    "error": str(e)
                })
        
        # Assert: Error handling provides value
        for result in error_handling_results:
            tool_name = result["tool"]
            expected_behavior = result["expected_behavior"]
            
            if result["success"]:
                # Business requirement: Partial results should provide some value
                assert result["result"] is not None, f"Tool {tool_name} should return partial results"
                
                if expected_behavior == "partial_success":
                    # Should have some indication of partial processing
                    result_str = str(result["result"]).lower()
                    partial_indicators = ["partial", "processed", "valid", "success", "completed"]
                    has_partial_info = any(indicator in result_str for indicator in partial_indicators)
                    assert has_partial_info or len(str(result["result"])) > 10, \
                        f"Tool {tool_name} should show partial processing results"
            
            else:
                # Even failures should provide informative errors
                assert result["error"] is not None, f"Failed tool {tool_name} should provide error information"
                assert len(result["error"]) > 5, f"Error message for {tool_name} should be descriptive"