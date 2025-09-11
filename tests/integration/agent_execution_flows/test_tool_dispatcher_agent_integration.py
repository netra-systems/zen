"""
Test Tool Dispatcher Agent Integration Workflows

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless integration between agents and tool execution system
- Value Impact: Enables agents to execute tools for data collection, analysis, and optimization
- Strategic Impact: Core functionality that enables AI-powered workflows to deliver business value

Tests the integration between agents and the tool dispatcher including tool selection,
execution coordination, result processing, and error handling in tool workflows.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcherCore
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestToolDispatcherAgentIntegration(BaseIntegrationTest):
    """Integration tests for tool dispatcher and agent coordination."""

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_agent_tool_selection_and_dispatch(self, real_services_fixture):
        """Test agent's ability to select and dispatch appropriate tools."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="tool_user_1400",
            thread_id="thread_1700",
            session_id="session_2000",
            workspace_id="tool_workspace_1300"
        )
        
        # Mock available tools
        mock_tool_registry = {
            "aws_cost_analyzer": {
                "description": "Analyzes AWS cost data and trends",
                "input_schema": {"account_id": "string", "time_period": "string"},
                "output_schema": {"cost_analysis": "object", "trends": "array"},
                "category": "cost_analysis",
                "complexity": "medium"
            },
            "resource_optimizer": {
                "description": "Identifies resource optimization opportunities",
                "input_schema": {"resource_data": "object", "optimization_goals": "array"},
                "output_schema": {"recommendations": "array", "savings_potential": "number"},
                "category": "optimization",
                "complexity": "high"
            },
            "usage_metrics_collector": {
                "description": "Collects resource usage metrics",
                "input_schema": {"services": "array", "metrics": "array"},
                "output_schema": {"usage_data": "object", "collection_metadata": "object"},
                "category": "data_collection",
                "complexity": "low"
            },
            "cost_report_generator": {
                "description": "Generates detailed cost reports",
                "input_schema": {"analysis_data": "object", "report_type": "string"},
                "output_schema": {"report": "object", "visualizations": "array"},
                "category": "reporting",
                "complexity": "medium"
            }
        }
        
        tool_dispatcher = ToolDispatcherCore(
            user_context=user_context,
            tool_registry=mock_tool_registry,
            selection_strategy="intelligent"
        )
        
        # Mock LLM for agent decision making
        mock_llm = AsyncMock()
        
        # Different agent requests that should select different tools
        agent_requests = [
            {
                "request": "I need to analyze my AWS costs for the last quarter",
                "expected_tools": ["usage_metrics_collector", "aws_cost_analyzer"],
                "agent_type": "data_helper"
            },
            {
                "request": "Find optimization opportunities to reduce my cloud spending",
                "expected_tools": ["aws_cost_analyzer", "resource_optimizer"],
                "agent_type": "apex_optimizer"
            },
            {
                "request": "Create a comprehensive cost report for the board meeting",
                "expected_tools": ["aws_cost_analyzer", "cost_report_generator"],
                "agent_type": "reporting"
            }
        ]
        
        tool_selection_results = []
        
        for request_data in agent_requests:
            # Mock LLM response for tool selection
            mock_llm.generate_response = AsyncMock(return_value={
                "status": "success",
                "tool_analysis": {
                    "request_category": request_data["agent_type"],
                    "required_capabilities": ["cost_analysis", "data_collection"],
                    "selected_tools": request_data["expected_tools"],
                    "execution_sequence": request_data["expected_tools"],
                    "reasoning": f"Selected tools based on {request_data['request']}"
                }
            })
            
            # Agent selects tools through dispatcher
            selection_result = await tool_dispatcher.select_tools_for_request(
                agent_request=request_data["request"],
                agent_type=request_data["agent_type"],
                llm_client=mock_llm,
                selection_criteria={
                    "prefer_efficiency": True,
                    "max_complexity": "high",
                    "required_categories": ["cost_analysis"]
                }
            )
            
            tool_selection_results.append({
                "request": request_data["request"],
                "agent_type": request_data["agent_type"],
                "selected_tools": selection_result["selected_tools"],
                "expected_tools": request_data["expected_tools"],
                "selection_reasoning": selection_result["reasoning"]
            })
        
        # Assert - Verify tool selection
        for result in tool_selection_results:
            assert result["selected_tools"] is not None
            assert len(result["selected_tools"]) > 0
            
            # Verify at least some expected tools were selected
            selected_tool_names = [tool["name"] for tool in result["selected_tools"]]
            expected_tools = result["expected_tools"]
            
            overlap = set(selected_tool_names) & set(expected_tools)
            assert len(overlap) > 0  # Should have some overlap with expected tools

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_sequential_tool_execution_workflow(self, real_services_fixture):
        """Test sequential execution of tools in agent workflows."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="sequential_user_1401",
            thread_id="thread_1701",
            session_id="session_2001",
            workspace_id="sequential_workspace_1301"
        )
        
        unified_tool_executor = UnifiedToolExecution(
            user_context=user_context,
            execution_mode="sequential",
            error_handling="graceful"
        )
        
        # Define a tool execution sequence for cost analysis workflow
        tool_sequence = [
            {
                "tool_name": "data_collector",
                "tool_params": {
                    "data_sources": ["aws_billing", "usage_metrics"],
                    "time_range": "last_30_days"
                },
                "expected_output": "collected_data",
                "dependencies": []
            },
            {
                "tool_name": "cost_analyzer",
                "tool_params": {
                    "input_data": "${data_collector.output}",
                    "analysis_type": "trend_analysis"
                },
                "expected_output": "cost_analysis",
                "dependencies": ["data_collector"]
            },
            {
                "tool_name": "optimizer",
                "tool_params": {
                    "cost_data": "${cost_analyzer.output}",
                    "optimization_targets": ["reduce_cost", "maintain_performance"]
                },
                "expected_output": "optimization_recommendations",
                "dependencies": ["cost_analyzer"]
            },
            {
                "tool_name": "report_generator",
                "tool_params": {
                    "analysis_data": "${cost_analyzer.output}",
                    "recommendations": "${optimizer.output}",
                    "report_format": "executive_summary"
                },
                "expected_output": "final_report",
                "dependencies": ["cost_analyzer", "optimizer"]
            }
        ]
        
        # Mock tool implementations
        mock_tool_implementations = {
            "data_collector": AsyncMock(return_value={
                "status": "success",
                "output": {
                    "collected_data": {
                        "total_cost": 25000,
                        "usage_metrics": {"cpu": 65, "memory": 80},
                        "billing_data": {"services": ["ec2", "rds", "s3"]}
                    }
                },
                "execution_time": 2.5
            }),
            "cost_analyzer": AsyncMock(return_value={
                "status": "success", 
                "output": {
                    "cost_analysis": {
                        "trend": "increasing",
                        "growth_rate": 0.15,
                        "cost_breakdown": {"compute": 15000, "storage": 7000, "network": 3000}
                    }
                },
                "execution_time": 5.2
            }),
            "optimizer": AsyncMock(return_value={
                "status": "success",
                "output": {
                    "optimization_recommendations": [
                        {"type": "rightsizing", "potential_savings": 6000, "confidence": 0.9},
                        {"type": "reserved_instances", "potential_savings": 4000, "confidence": 0.8}
                    ]
                },
                "execution_time": 8.1
            }),
            "report_generator": AsyncMock(return_value={
                "status": "success",
                "output": {
                    "final_report": {
                        "executive_summary": "Identified $10,000 monthly cost savings opportunity",
                        "detailed_recommendations": "Full optimization plan with implementation timeline",
                        "roi_projection": "3-month payback period"
                    }
                },
                "execution_time": 3.0
            })
        }
        
        # Configure tool executor with mock implementations
        unified_tool_executor.register_tool_implementations(mock_tool_implementations)
        
        # Act - Execute tool sequence
        execution_start = time.time()
        
        sequence_result = await unified_tool_executor.execute_tool_sequence(
            tool_sequence=tool_sequence,
            sequence_name="cost_optimization_workflow",
            dependency_resolution="automatic"
        )
        
        execution_end = time.time()
        total_execution_time = execution_end - execution_start
        
        # Assert - Verify sequential execution
        assert sequence_result is not None
        assert sequence_result["status"] == "success"
        assert sequence_result["sequence_completed"] is True
        
        # Verify all tools were executed
        executed_tools = sequence_result["executed_tools"]
        assert len(executed_tools) == len(tool_sequence)
        
        # Verify execution order (sequential)
        tool_names = [tool["tool_name"] for tool in executed_tools]
        expected_order = ["data_collector", "cost_analyzer", "optimizer", "report_generator"]
        assert tool_names == expected_order
        
        # Verify dependency resolution
        for i, executed_tool in enumerate(executed_tools):
            expected_tool = tool_sequence[i]
            if expected_tool["dependencies"]:
                # Tool should have received outputs from dependencies
                assert "resolved_dependencies" in executed_tool
                
        # Verify data flow between tools
        final_report = sequence_result["final_outputs"]["report_generator"]["final_report"]
        assert "executive_summary" in final_report
        assert "$10,000" in final_report["executive_summary"]  # Shows data flowed correctly
        
        # Verify reasonable execution time (sequential should be sum of individual times)
        expected_min_time = 2.5 + 5.2 + 8.1 + 3.0  # Sum of individual execution times
        assert total_execution_time >= (expected_min_time * 0.8)  # Allow some variance

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_parallel_tool_execution_coordination(self, real_services_fixture):
        """Test parallel execution of independent tools with coordination."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="parallel_user_1402",
            thread_id="thread_1702",
            session_id="session_2002",
            workspace_id="parallel_workspace_1302"
        )
        
        unified_tool_executor = UnifiedToolExecution(
            user_context=user_context,
            execution_mode="parallel",
            max_parallel_tools=4,
            coordination_enabled=True
        )
        
        # Define parallel tool execution groups
        parallel_workflow = {
            "phase_1_parallel": [
                {
                    "tool_name": "aws_data_collector",
                    "tool_params": {"provider": "aws", "services": ["ec2", "rds"]},
                    "parallel_group": "data_collection",
                    "estimated_time": 3.0
                },
                {
                    "tool_name": "azure_data_collector", 
                    "tool_params": {"provider": "azure", "services": ["vm", "sql"]},
                    "parallel_group": "data_collection",
                    "estimated_time": 2.5
                },
                {
                    "tool_name": "gcp_data_collector",
                    "tool_params": {"provider": "gcp", "services": ["compute", "cloud_sql"]},
                    "parallel_group": "data_collection", 
                    "estimated_time": 4.0
                }
            ],
            "synchronization_point": {
                "tool_name": "data_aggregator",
                "tool_params": {
                    "aws_data": "${aws_data_collector.output}",
                    "azure_data": "${azure_data_collector.output}",
                    "gcp_data": "${gcp_data_collector.output}"
                },
                "depends_on": ["data_collection"]
            },
            "phase_2_parallel": [
                {
                    "tool_name": "aws_optimizer",
                    "tool_params": {"data": "${data_aggregator.output.aws_data}"},
                    "parallel_group": "optimization",
                    "estimated_time": 6.0
                },
                {
                    "tool_name": "azure_optimizer",
                    "tool_params": {"data": "${data_aggregator.output.azure_data}"},
                    "parallel_group": "optimization",
                    "estimated_time": 5.5
                },
                {
                    "tool_name": "gcp_optimizer",
                    "tool_params": {"data": "${data_aggregator.output.gcp_data}"},
                    "parallel_group": "optimization",
                    "estimated_time": 7.0
                }
            ]
        }
        
        # Mock parallel tool implementations
        parallel_tool_mocks = {
            "aws_data_collector": AsyncMock(),
            "azure_data_collector": AsyncMock(),
            "gcp_data_collector": AsyncMock(),
            "data_aggregator": AsyncMock(),
            "aws_optimizer": AsyncMock(),
            "azure_optimizer": AsyncMock(),
            "gcp_optimizer": AsyncMock()
        }
        
        # Configure mock responses with simulated delays
        async def mock_data_collector_response(provider: str, delay: float):
            await asyncio.sleep(delay)
            return {
                "status": "success",
                "output": {
                    f"{provider}_data": {
                        "cost": 10000 + (hash(provider) % 5000),
                        "resources": f"{provider}_resource_list",
                        "collection_time": delay
                    }
                },
                "execution_time": delay
            }
        
        parallel_tool_mocks["aws_data_collector"].return_value = await mock_data_collector_response("aws", 0.3)
        parallel_tool_mocks["azure_data_collector"].return_value = await mock_data_collector_response("azure", 0.25) 
        parallel_tool_mocks["gcp_data_collector"].return_value = await mock_data_collector_response("gcp", 0.4)
        
        # Data aggregator mock
        parallel_tool_mocks["data_aggregator"].return_value = {
            "status": "success",
            "output": {
                "aggregated_data": {
                    "total_cost": 35000,
                    "providers": ["aws", "azure", "gcp"],
                    "aggregation_complete": True
                }
            },
            "execution_time": 0.5
        }
        
        # Optimizer mocks
        for provider in ["aws", "azure", "gcp"]:
            parallel_tool_mocks[f"{provider}_optimizer"].return_value = {
                "status": "success", 
                "output": {
                    f"{provider}_optimization": {
                        "savings": 3000 + (hash(provider) % 2000),
                        "recommendations": [f"{provider}_rec_1", f"{provider}_rec_2"]
                    }
                },
                "execution_time": 0.6
            }
        
        unified_tool_executor.register_tool_implementations(parallel_tool_mocks)
        
        # Act - Execute parallel workflow with coordination
        parallel_start = time.time()
        
        parallel_result = await unified_tool_executor.execute_parallel_workflow(
            workflow_definition=parallel_workflow,
            coordination_mode="phase_synchronization",
            max_phase_timeout=10.0
        )
        
        parallel_end = time.time()
        total_parallel_time = parallel_end - parallel_start
        
        # Assert - Verify parallel execution coordination
        assert parallel_result is not None
        assert parallel_result["status"] == "success"
        assert parallel_result["workflow_completed"] is True
        
        # Verify parallel execution efficiency
        # Parallel execution should be faster than sequential
        sequential_estimate = 3.0 + 2.5 + 4.0 + 0.5 + 6.0 + 5.5 + 7.0  # Sum of all times
        assert total_parallel_time < (sequential_estimate * 0.7)  # Should be significantly faster
        
        # Verify synchronization points worked
        assert "synchronization_points_completed" in parallel_result
        assert parallel_result["synchronization_points_completed"] >= 1
        
        # Verify all phases completed
        phase_results = parallel_result["phase_results"]
        assert "phase_1_parallel" in phase_results
        assert "phase_2_parallel" in phase_results
        
        # Verify data aggregation occurred
        aggregation_result = parallel_result["tool_outputs"]["data_aggregator"]
        assert aggregation_result["output"]["aggregated_data"]["aggregation_complete"] is True
        
        # Verify optimization results from all providers
        optimization_outputs = [
            parallel_result["tool_outputs"]["aws_optimizer"],
            parallel_result["tool_outputs"]["azure_optimizer"], 
            parallel_result["tool_outputs"]["gcp_optimizer"]
        ]
        
        assert len(optimization_outputs) == 3
        for output in optimization_outputs:
            assert output["status"] == "success"
            assert "optimization" in str(output["output"])

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_tool_error_handling_and_recovery(self, real_services_fixture):
        """Test tool execution error handling and recovery strategies."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="error_handling_user_1403",
            thread_id="thread_1703",
            session_id="session_2003",
            workspace_id="error_handling_workspace_1303"
        )
        
        unified_tool_executor = UnifiedToolExecution(
            user_context=user_context,
            error_handling="advanced_recovery",
            retry_strategy="exponential_backoff",
            fallback_tools_enabled=True
        )
        
        # Define tools with various failure scenarios
        error_prone_workflow = [
            {
                "tool_name": "unstable_data_source",
                "tool_params": {"endpoint": "unreliable_api", "timeout": 5},
                "retry_attempts": 3,
                "fallback_tool": "backup_data_source",
                "error_tolerance": "medium"
            },
            {
                "tool_name": "flaky_processor",
                "tool_params": {"processing_mode": "complex"},
                "retry_attempts": 2,
                "fallback_tool": "simple_processor",
                "error_tolerance": "low"
            },
            {
                "tool_name": "critical_analyzer",
                "tool_params": {"analysis_depth": "comprehensive"},
                "retry_attempts": 1,
                "fallback_tool": None,  # No fallback - must succeed
                "error_tolerance": "none"
            }
        ]
        
        # Mock tools with failure patterns
        failure_patterns = {
            "unstable_data_source": {
                "failure_rate": 0.7,  # Fails 70% of the time
                "failure_types": ["timeout", "connection_error", "invalid_response"]
            },
            "flaky_processor": {
                "failure_rate": 0.4,  # Fails 40% of the time
                "failure_types": ["processing_error", "memory_error"]
            },
            "critical_analyzer": {
                "failure_rate": 0.1,  # Fails 10% of the time
                "failure_types": ["analysis_error"]
            }
        }
        
        # Fallback tool implementations (more reliable)
        fallback_implementations = {
            "backup_data_source": AsyncMock(return_value={
                "status": "success",
                "output": {"backup_data": "reliable_fallback_data", "source": "backup"},
                "execution_time": 1.0
            }),
            "simple_processor": AsyncMock(return_value={
                "status": "success",
                "output": {"processed_data": "simple_processing_result", "method": "fallback"},
                "execution_time": 2.0
            })
        }
        
        # Create failing primary tools
        failing_tools = {}
        execution_attempts = {}
        
        for tool_name, pattern in failure_patterns.items():
            execution_attempts[tool_name] = 0
            
            async def create_failing_tool(name, fail_pattern):
                async def failing_tool_impl(*args, **kwargs):
                    nonlocal execution_attempts
                    execution_attempts[name] += 1
                    
                    # Simulate failure based on pattern
                    import random
                    if random.random() < fail_pattern["failure_rate"]:
                        error_type = random.choice(fail_pattern["failure_types"])
                        raise Exception(f"{error_type}: Simulated {name} failure (attempt {execution_attempts[name]})")
                    
                    # Success case
                    return {
                        "status": "success",
                        "output": {f"{name}_result": f"success_after_{execution_attempts[name]}_attempts"},
                        "execution_time": 1.5
                    }
                
                return failing_tool_impl
            
            failing_tools[tool_name] = await create_failing_tool(tool_name, pattern)
        
        # Register all tool implementations
        all_tools = {**failing_tools, **fallback_implementations}
        unified_tool_executor.register_tool_implementations(all_tools)
        
        # Act - Execute workflow with error handling
        error_handling_start = time.time()
        
        result = await unified_tool_executor.execute_workflow_with_recovery(
            workflow_tools=error_prone_workflow,
            recovery_strategy="retry_with_fallback",
            max_total_retries=10,
            circuit_breaker_threshold=5
        )
        
        error_handling_end = time.time()
        total_recovery_time = error_handling_end - error_handling_start
        
        # Assert - Verify error handling and recovery
        assert result is not None
        
        # Should complete despite errors (using fallbacks/retries)
        completed_tools = result.get("completed_tools", [])
        failed_tools = result.get("failed_tools", [])
        fallback_used_count = result.get("fallbacks_used", 0)
        retry_count = result.get("total_retries", 0)
        
        # Verify error recovery mechanisms were used
        assert retry_count > 0  # Should have retried failing tools
        assert fallback_used_count >= 0  # May have used fallbacks
        
        # Verify most tools completed (either primary or fallback)
        completion_rate = len(completed_tools) / len(error_prone_workflow)
        assert completion_rate >= 0.7  # Should complete at least 70% despite errors
        
        # Verify execution attempts tracking
        assert execution_attempts["unstable_data_source"] > 1  # Should have retried
        
        # Verify error information is captured
        if "error_summary" in result:
            error_summary = result["error_summary"]
            assert "total_errors_encountered" in error_summary
            assert error_summary["total_errors_encountered"] > 0
        
        # Verify reasonable recovery time (shouldn't hang indefinitely)
        assert total_recovery_time < 30.0  # Should recover within reasonable time

    @pytest.mark.integration
    @pytest.mark.tool_execution_workflows
    async def test_tool_result_processing_and_validation(self, real_services_fixture):
        """Test processing and validation of tool execution results."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="validation_user_1404",
            thread_id="thread_1704",
            session_id="session_2004",
            workspace_id="validation_workspace_1304"
        )
        
        unified_tool_executor = UnifiedToolExecution(
            user_context=user_context,
            result_validation=True,
            result_processing="comprehensive",
            quality_assurance=True
        )
        
        # Define tools with result validation requirements
        validation_workflow = [
            {
                "tool_name": "data_validator",
                "tool_params": {"validation_rules": ["completeness", "accuracy", "consistency"]},
                "result_schema": {
                    "required_fields": ["validation_status", "data_quality_score", "validation_details"],
                    "validation_rules": {
                        "data_quality_score": {"type": "number", "min": 0, "max": 1},
                        "validation_status": {"type": "string", "enum": ["passed", "failed", "partial"]}
                    }
                }
            },
            {
                "tool_name": "cost_calculator",
                "tool_params": {"calculation_method": "comprehensive"},
                "result_schema": {
                    "required_fields": ["total_cost", "cost_breakdown", "calculation_metadata"],
                    "validation_rules": {
                        "total_cost": {"type": "number", "min": 0},
                        "cost_breakdown": {"type": "object", "required_keys": ["compute", "storage", "network"]}
                    }
                }
            },
            {
                "tool_name": "recommendation_engine",
                "tool_params": {"recommendation_count": 5},
                "result_schema": {
                    "required_fields": ["recommendations", "confidence_scores", "implementation_complexity"],
                    "validation_rules": {
                        "recommendations": {"type": "array", "min_length": 1},
                        "confidence_scores": {"type": "array", "element_type": "number", "element_range": [0, 1]}
                    }
                }
            }
        ]
        
        # Mock tools with various result quality levels
        mock_tool_results = {
            "data_validator": {
                "status": "success",
                "output": {
                    "validation_status": "passed",
                    "data_quality_score": 0.94,
                    "validation_details": {
                        "completeness": 0.98,
                        "accuracy": 0.92,
                        "consistency": 0.91
                    },
                    "validated_records": 10000,
                    "validation_timestamp": time.time()
                },
                "execution_time": 3.2
            },
            "cost_calculator": {
                "status": "success",
                "output": {
                    "total_cost": 47850.25,
                    "cost_breakdown": {
                        "compute": 28500.00,
                        "storage": 12750.50, 
                        "network": 6599.75
                    },
                    "calculation_metadata": {
                        "method": "comprehensive",
                        "currency": "USD",
                        "calculation_date": "2024-01-15",
                        "precision": "high"
                    },
                    "cost_trends": {
                        "month_over_month": 0.12,
                        "year_over_year": 0.34
                    }
                },
                "execution_time": 5.8
            },
            "recommendation_engine": {
                "status": "success",
                "output": {
                    "recommendations": [
                        {
                            "id": "rec_001",
                            "type": "rightsizing",
                            "description": "Downsize underutilized EC2 instances",
                            "potential_savings": 8400.00,
                            "implementation_effort": "low"
                        },
                        {
                            "id": "rec_002", 
                            "type": "reserved_instances",
                            "description": "Purchase reserved instances for stable workloads",
                            "potential_savings": 12600.00,
                            "implementation_effort": "medium"
                        },
                        {
                            "id": "rec_003",
                            "type": "storage_optimization",
                            "description": "Move infrequently accessed data to cheaper storage tiers",
                            "potential_savings": 3200.00,
                            "implementation_effort": "high"
                        }
                    ],
                    "confidence_scores": [0.92, 0.87, 0.78],
                    "implementation_complexity": {
                        "overall": "medium",
                        "timeline_months": 3,
                        "resource_requirements": ["1 DevOps engineer", "0.5 Finance analyst"]
                    },
                    "total_potential_savings": 24200.00
                },
                "execution_time": 12.4
            }
        }
        
        # Register mock tools
        mock_implementations = {}
        for tool_name, result_data in mock_tool_results.items():
            mock_implementations[tool_name] = AsyncMock(return_value=result_data)
        
        unified_tool_executor.register_tool_implementations(mock_implementations)
        
        # Act - Execute workflow with result validation
        validation_result = await unified_tool_executor.execute_workflow_with_validation(
            workflow_tools=validation_workflow,
            validation_mode="strict",
            quality_threshold=0.8,
            result_processing_enabled=True
        )
        
        # Assert - Verify result processing and validation
        assert validation_result is not None
        assert validation_result["status"] == "success"
        assert validation_result["workflow_completed"] is True
        
        # Verify all tools passed validation
        validation_summary = validation_result["validation_summary"]
        assert validation_summary["tools_validated"] == len(validation_workflow)
        assert validation_summary["validation_failures"] == 0
        
        # Verify result schema validation
        schema_validation_results = validation_result["schema_validation_results"]
        for tool_name in mock_tool_results.keys():
            tool_validation = schema_validation_results[tool_name]
            assert tool_validation["schema_valid"] is True
            assert tool_validation["required_fields_present"] is True
        
        # Verify quality assurance metrics
        qa_results = validation_result["quality_assurance"]
        assert qa_results["overall_quality_score"] >= 0.8
        
        # Verify result processing
        processed_results = validation_result["processed_results"]
        
        # Data validator results should be processed
        validator_processed = processed_results["data_validator"]
        assert validator_processed["data_quality_score"] == 0.94
        assert validator_processed["quality_level"] == "high"  # Should be categorized
        
        # Cost calculator results should include derived metrics
        calculator_processed = processed_results["cost_calculator"]
        assert calculator_processed["total_cost"] == 47850.25
        assert "cost_per_service" in calculator_processed  # Should have derived metrics
        
        # Recommendation engine results should be ranked
        recommendations_processed = processed_results["recommendation_engine"]
        assert len(recommendations_processed["recommendations"]) == 3
        assert "recommendation_ranking" in recommendations_processed  # Should be ranked by confidence/impact
        
        # Verify cross-tool result correlation
        correlation_analysis = validation_result.get("result_correlation", {})
        if correlation_analysis:
            # Should identify relationships between tool results
            assert "cost_savings_consistency" in correlation_analysis
            
        # Verify final aggregated insights
        aggregated_insights = validation_result["aggregated_insights"]
        assert "total_potential_savings" in aggregated_insights
        assert aggregated_insights["total_potential_savings"] > 20000  # Should aggregate from recommendations