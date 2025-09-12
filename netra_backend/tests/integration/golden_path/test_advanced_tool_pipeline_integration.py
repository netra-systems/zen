"""
Advanced Tool Pipeline and Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complex tool pipelines deliver reliable AI analysis results
- Value Impact: Validates sophisticated agent tool chains that provide deep business insights
- Strategic Impact: CRITICAL for competitive differentiation - complex analysis = higher value

ADVANCED TOOL PIPELINE TEST SCENARIOS:
1. Complex multi-tool chaining with dependency validation
2. Tool error propagation and recovery mechanisms
3. Tool output transformation and data flow validation
4. Parallel tool execution with result aggregation
5. Tool timeout handling and circuit breaker patterns
6. Dynamic tool selection and execution path optimization

CRITICAL REQUIREMENTS:
- NO MOCKS - Real tool execution and data processing
- E2E authentication throughout tool pipeline
- WebSocket events for all tool execution stages
- Performance benchmarks for complex tool chains
- Data integrity validation through entire pipeline
"""

import asyncio
import json
import logging
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import hashlib

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import create_request_scoped_engine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.factories.tool_dispatcher_factory import get_tool_dispatcher_factory
from netra_backend.app.tools.enhanced_tool_execution_engine import EnhancedToolExecutionEngine
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.api.websocket.events import WebSocketEventType
from netra_backend.app.llm.llm_manager import LLMManager
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class ToolPipelineStage(Enum):
    """Stages of tool pipeline execution."""
    INITIALIZATION = "initialization"
    TOOL_SELECTION = "tool_selection"
    DEPENDENCY_RESOLUTION = "dependency_resolution"
    PARALLEL_EXECUTION = "parallel_execution"
    SEQUENTIAL_EXECUTION = "sequential_execution"
    OUTPUT_TRANSFORMATION = "output_transformation"
    RESULT_AGGREGATION = "result_aggregation"
    VALIDATION = "validation"
    COMPLETION = "completion"


@dataclass
class ToolExecutionMetrics:
    """Metrics for individual tool execution."""
    tool_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    output_size_bytes: int = 0
    error_message: Optional[str] = None
    dependencies_met: bool = True
    parallel_group: Optional[str] = None


@dataclass
class PipelineExecutionResult:
    """Result of complete pipeline execution."""
    pipeline_id: str
    user_id: str
    total_tools_executed: int
    successful_tools: int
    failed_tools: int
    total_duration_ms: float
    data_integrity_verified: bool
    websocket_events_count: int
    final_output: Optional[Dict[str, Any]] = None


class TestAdvancedToolPipelineIntegration(BaseIntegrationTest):
    """Advanced integration tests for tool pipeline and integration scenarios."""

    @pytest.mark.asyncio
    async def test_complex_multi_tool_chaining_with_dependencies(self, real_services_fixture):
        """
        Test complex multi-tool chaining with dependency validation.
        
        BUSINESS SCENARIO: Complex analysis requiring data gathering, processing,
        transformation, and reporting in a specific order with dependencies.
        """
        logger.info("Starting complex multi-tool chaining test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_tool_chain_user")
        user_id = auth_context.user_id  # Use the same user_id from auth_context
        
        # Initialize components with SSOT patterns
        llm_manager = LLMManager()  # SSOT: Create LLM manager for agent registry
        agent_registry = AgentRegistry(llm_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        # Use factory method for proper user isolation
        tool_dispatcher_factory = get_tool_dispatcher_factory()
        tool_dispatcher = await tool_dispatcher_factory.create_for_request(
            user_context=auth_context,
            websocket_manager=websocket_manager
        )
        enhanced_tool_engine = EnhancedToolExecutionEngine()
        
        # Track tool executions and pipeline progress
        tool_executions = []
        pipeline_stages = []
        websocket_events = []
        dependency_graph = {}
        
        def capture_websocket_event(event):
            websocket_events.append({
                **event,
                "captured_at": datetime.now(timezone.utc)
            })
        
        websocket_manager.add_event_listener(capture_websocket_event)
        
        def track_pipeline_stage(stage: ToolPipelineStage, data: Dict[str, Any]):
            pipeline_stages.append({
                "stage": stage.value,
                "timestamp": datetime.now(timezone.utc),
                "data": data
            })
            logger.info(f"Pipeline stage: {stage.value}")
        
        # Phase 1: Initialize complex tool chain
        track_pipeline_stage(ToolPipelineStage.INITIALIZATION, {"user_id": str(user_id)})
        
        # Start agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            user_id=str(user_id),
            thread_id=str(thread_id),
            run_id=str(run_id),
            agent_name="supervisor_agent",
            request_id=str(uuid.uuid4()),
            metadata={
                "message": "Perform comprehensive analysis requiring complex tool chain: data collection -> processing -> validation -> optimization -> reporting"
            }
        )
        
        # Execute agent with user context
        agent_execution = await execution_engine.execute_agent(agent_context, auth_context)
        
        # Phase 2: Define complex tool chain with dependencies
        track_pipeline_stage(ToolPipelineStage.TOOL_SELECTION, {})
        
        # Define tool chain with explicit dependencies
        tool_chain_definition = {
            # Stage 1: Data Collection (no dependencies)
            "data_collector": {
                "tool_name": "data_collection_tool",
                "dependencies": [],
                "inputs": {"source": "user_infrastructure", "scope": "comprehensive"},
                "expected_outputs": ["infrastructure_data", "cost_data", "usage_metrics"]
            },
            
            # Stage 2: Data Validation (depends on data_collector)
            "data_validator": {
                "tool_name": "data_validation_tool", 
                "dependencies": ["data_collector"],
                "inputs": {"data_source": "data_collector.infrastructure_data"},
                "expected_outputs": ["validation_report", "cleaned_data"]
            },
            
            # Stage 3: Parallel Analysis (depends on data_validator)
            "cost_analyzer": {
                "tool_name": "cost_analysis_tool",
                "dependencies": ["data_validator"],
                "inputs": {"cost_data": "data_collector.cost_data", "validated_data": "data_validator.cleaned_data"},
                "expected_outputs": ["cost_breakdown", "optimization_opportunities"],
                "parallel_group": "analysis"
            },
            
            "performance_analyzer": {
                "tool_name": "performance_analysis_tool", 
                "dependencies": ["data_validator"],
                "inputs": {"usage_metrics": "data_collector.usage_metrics", "validated_data": "data_validator.cleaned_data"},
                "expected_outputs": ["performance_metrics", "bottlenecks"],
                "parallel_group": "analysis"
            },
            
            # Stage 4: Optimization (depends on both analyzers)
            "optimizer": {
                "tool_name": "infrastructure_optimization_tool",
                "dependencies": ["cost_analyzer", "performance_analyzer"],
                "inputs": {
                    "cost_breakdown": "cost_analyzer.cost_breakdown",
                    "performance_metrics": "performance_analyzer.performance_metrics",
                    "optimization_opportunities": "cost_analyzer.optimization_opportunities"
                },
                "expected_outputs": ["optimization_plan", "projected_savings"]
            },
            
            # Stage 5: Report Generation (depends on optimizer)
            "report_generator": {
                "tool_name": "comprehensive_report_tool",
                "dependencies": ["optimizer"],
                "inputs": {
                    "optimization_plan": "optimizer.optimization_plan",
                    "projected_savings": "optimizer.projected_savings",
                    "validation_report": "data_validator.validation_report"
                },
                "expected_outputs": ["comprehensive_report", "executive_summary"]
            }
        }
        
        # Build dependency graph
        for tool_id, tool_config in tool_chain_definition.items():
            dependency_graph[tool_id] = tool_config["dependencies"]
        
        track_pipeline_stage(ToolPipelineStage.DEPENDENCY_RESOLUTION, {
            "total_tools": len(tool_chain_definition),
            "dependency_graph": dependency_graph
        })
        
        # Phase 3: Execute tool chain respecting dependencies
        executed_tools = set()
        tool_outputs = {}
        
        async def execute_tool_with_dependencies(tool_id: str, tool_config: Dict[str, Any]) -> ToolExecutionMetrics:
            """Execute a tool ensuring all dependencies are met."""
            
            # Wait for dependencies
            while not all(dep in executed_tools for dep in tool_config["dependencies"]):
                await asyncio.sleep(0.1)
            
            execution_id = f"{tool_id}_{uuid.uuid4().hex[:8]}"
            metrics = ToolExecutionMetrics(
                tool_name=tool_config["tool_name"],
                execution_id=execution_id,
                start_time=datetime.now(timezone.utc),
                parallel_group=tool_config.get("parallel_group")
            )
            
            try:
                # Resolve input dependencies
                resolved_inputs = {}
                for input_key, input_source in tool_config["inputs"].items():
                    if "." in input_source:  # Dependency reference
                        dep_tool, output_key = input_source.split(".", 1)
                        if dep_tool in tool_outputs and output_key in tool_outputs[dep_tool]:
                            resolved_inputs[input_key] = tool_outputs[dep_tool][output_key]
                        else:
                            raise ValueError(f"Dependency output not found: {input_source}")
                    else:  # Direct input
                        resolved_inputs[input_key] = input_source
                
                metrics.dependencies_met = True
                
                # Execute tool
                tool_result = await enhanced_tool_engine.execute_tool(
                    tool_name=tool_config["tool_name"],
                    tool_inputs=resolved_inputs,
                    user_id=user_id,
                    execution_context=auth_context,
                    agent_execution_id=str(agent_execution.id)
                )
                
                metrics.end_time = datetime.now(timezone.utc)
                metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
                metrics.success = tool_result.get("success", False)
                
                if metrics.success:
                    # Store tool outputs for dependent tools
                    tool_outputs[tool_id] = tool_result.get("outputs", {})
                    metrics.output_size_bytes = len(json.dumps(tool_outputs[tool_id]))
                    
                    executed_tools.add(tool_id)
                    logger.info(f"Tool {tool_id} executed successfully in {metrics.duration_ms:.1f}ms")
                else:
                    metrics.error_message = tool_result.get("error", "Unknown error")
                    logger.error(f"Tool {tool_id} failed: {metrics.error_message}")
                
            except Exception as e:
                metrics.end_time = datetime.now(timezone.utc)
                metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
                metrics.error_message = str(e)
                metrics.dependencies_met = False
                logger.error(f"Tool {tool_id} execution error: {e}")
            
            tool_executions.append(metrics)
            return metrics
        
        # Execute tools in dependency order, with parallelization where possible
        execution_groups = []
        remaining_tools = set(tool_chain_definition.keys())
        
        while remaining_tools:
            # Find tools whose dependencies are satisfied
            ready_tools = []
            for tool_id in remaining_tools:
                tool_config = tool_chain_definition[tool_id]
                if all(dep in executed_tools for dep in tool_config["dependencies"]):
                    ready_tools.append((tool_id, tool_config))
            
            if not ready_tools:
                logger.error("Circular dependency detected or missing dependencies")
                break
            
            # Group parallel tools
            parallel_groups = {}
            sequential_tools = []
            
            for tool_id, tool_config in ready_tools:
                parallel_group = tool_config.get("parallel_group")
                if parallel_group:
                    if parallel_group not in parallel_groups:
                        parallel_groups[parallel_group] = []
                    parallel_groups[parallel_group].append((tool_id, tool_config))
                else:
                    sequential_tools.append((tool_id, tool_config))
            
            # Execute parallel groups
            for group_name, group_tools in parallel_groups.items():
                track_pipeline_stage(ToolPipelineStage.PARALLEL_EXECUTION, {
                    "group": group_name,
                    "tools": [tool_id for tool_id, _ in group_tools]
                })
                
                parallel_tasks = [execute_tool_with_dependencies(tool_id, tool_config) 
                                for tool_id, tool_config in group_tools]
                await asyncio.gather(*parallel_tasks)
                
                for tool_id, _ in group_tools:
                    remaining_tools.discard(tool_id)
            
            # Execute sequential tools
            for tool_id, tool_config in sequential_tools:
                track_pipeline_stage(ToolPipelineStage.SEQUENTIAL_EXECUTION, {"tool": tool_id})
                await execute_tool_with_dependencies(tool_id, tool_config)
                remaining_tools.discard(tool_id)
        
        # Phase 4: Validate tool chain execution
        track_pipeline_stage(ToolPipelineStage.RESULT_AGGREGATION, {})
        
        successful_executions = [exe for exe in tool_executions if exe.success]
        failed_executions = [exe for exe in tool_executions if not exe.success]
        
        success_rate = len(successful_executions) / len(tool_executions) if tool_executions else 0.0
        
        logger.info(f"Tool Chain Results: {len(successful_executions)}/{len(tool_executions)} successful ({success_rate:.2%})")
        
        # Validate tool chain success
        assert success_rate >= 0.95, f"Tool chain success rate too low: {success_rate:.2%} (expected  >= 95%)"
        
        # Validate dependency execution order
        dependency_violations = []
        for execution in tool_executions:
            tool_id = next((tid for tid, config in tool_chain_definition.items() 
                           if config["tool_name"] == execution.tool_name), None)
            if tool_id:
                tool_config = tool_chain_definition[tool_id]
                for dep in tool_config["dependencies"]:
                    dep_execution = next((exe for exe in tool_executions 
                                        if any(config["tool_name"] == exe.tool_name 
                                              for tid, config in tool_chain_definition.items() 
                                              if tid == dep)), None)
                    if dep_execution and execution.start_time < dep_execution.end_time:
                        dependency_violations.append({
                            "tool": tool_id,
                            "dependency": dep,
                            "violation_type": "execution_order"
                        })
        
        assert len(dependency_violations) == 0, f"Dependency violations detected: {dependency_violations}"
        
        # Phase 5: Validate data flow integrity
        track_pipeline_stage(ToolPipelineStage.VALIDATION, {})
        
        # Check that each tool's expected outputs were produced
        output_validation_errors = []
        for tool_id, tool_config in tool_chain_definition.items():
            if tool_id in tool_outputs:
                tool_output = tool_outputs[tool_id]
                for expected_output in tool_config["expected_outputs"]:
                    if expected_output not in tool_output:
                        output_validation_errors.append({
                            "tool": tool_id,
                            "missing_output": expected_output
                        })
        
        assert len(output_validation_errors) == 0, f"Tool output validation errors: {output_validation_errors}"
        
        # Phase 6: Generate final pipeline result
        final_output = {}
        if "report_generator" in tool_outputs:
            final_output = tool_outputs["report_generator"]
        
        pipeline_result = PipelineExecutionResult(
            pipeline_id=str(uuid.uuid4()),
            user_id=str(user_id),
            total_tools_executed=len(tool_executions),
            successful_tools=len(successful_executions),
            failed_tools=len(failed_executions),
            total_duration_ms=(time.time() - start_time) * 1000,
            data_integrity_verified=len(output_validation_errors) == 0,
            websocket_events_count=len(websocket_events),
            final_output=final_output
        )
        
        # Complete agent execution
        await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result={
                "pipeline_result": pipeline_result.__dict__,
                "tool_chain_completed": True
            }
        )
        
        track_pipeline_stage(ToolPipelineStage.COMPLETION, {"pipeline_result": pipeline_result.__dict__})
        
        # Validate WebSocket events for tool execution
        tool_events = [e for e in websocket_events if e.get("type") in [
            WebSocketEventType.TOOL_EXECUTING.value,
            WebSocketEventType.TOOL_COMPLETED.value
        ]]
        
        expected_tool_events = len(successful_executions) * 2  # executing + completed per tool
        assert len(tool_events) >= expected_tool_events * 0.8, f"Insufficient WebSocket tool events: {len(tool_events)} (expected  >= {expected_tool_events * 0.8:.0f})"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 180.0, f"Complex tool chain should complete in <180s, took {execution_time:.2f}s"
        
        # Validate average tool execution time
        successful_durations = [exe.duration_ms for exe in successful_executions if exe.duration_ms]
        if successful_durations:
            avg_duration = sum(successful_durations) / len(successful_durations)
            assert avg_duration < 30000.0, f"Average tool execution too slow: {avg_duration:.1f}ms (expected <30s)"
        
        logger.info(f"Complex multi-tool chaining test completed in {execution_time:.2f}s with {success_rate:.2%} success rate")

    @pytest.mark.asyncio
    async def test_tool_error_propagation_and_recovery_mechanisms(self, real_services_fixture):
        """
        Test tool error propagation and recovery mechanisms.
        
        RESILIENCE SCENARIO: Validates system handles tool failures gracefully
        with proper error propagation and recovery strategies.
        """
        logger.info("Starting tool error propagation and recovery test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_error_recovery_user")
        user_id = auth_context.user_id  # Use the same user_id from auth_context
        
        # Initialize components with SSOT patterns
        llm_manager = LLMManager()  # SSOT: Create LLM manager for agent registry
        agent_registry = AgentRegistry(llm_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        enhanced_tool_engine = EnhancedToolExecutionEngine()
        
        # Track error scenarios and recovery attempts
        error_scenarios = []
        recovery_attempts = []
        websocket_events = []
        
        def capture_websocket_event(event):
            websocket_events.append({
                **event,
                "captured_at": datetime.now(timezone.utc)
            })
        
        websocket_manager.add_event_listener(capture_websocket_event)
        
        # Start agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            user_id=str(user_id),
            thread_id=str(thread_id),
            run_id=str(run_id),
            agent_name="supervisor_agent",
            request_id=str(uuid.uuid4()),
            metadata={
                "message": "Test error recovery mechanisms with various tool failure scenarios"
            }
        )
        
        # Execute agent with user context
        agent_execution = await execution_engine.execute_agent(agent_context, auth_context)
        
        # Phase 1: Test various error scenarios
        error_test_cases = [
            {
                "scenario": "timeout_error",
                "tool_name": "slow_analysis_tool",
                "inputs": {"timeout_seconds": 0.1, "simulate_delay": 5.0},
                "expected_error_type": "timeout",
                "recovery_strategy": "retry_with_longer_timeout"
            },
            {
                "scenario": "invalid_input_error", 
                "tool_name": "data_validation_tool",
                "inputs": {"invalid_data": "this_will_cause_validation_error"},
                "expected_error_type": "validation_error",
                "recovery_strategy": "input_correction"
            },
            {
                "scenario": "resource_unavailable_error",
                "tool_name": "external_api_tool",
                "inputs": {"api_endpoint": "http://nonexistent-service.local"},
                "expected_error_type": "connection_error",
                "recovery_strategy": "fallback_tool"
            },
            {
                "scenario": "tool_crash_error",
                "tool_name": "unstable_tool",
                "inputs": {"force_crash": True},
                "expected_error_type": "execution_error",
                "recovery_strategy": "restart_and_retry"
            },
            {
                "scenario": "partial_failure",
                "tool_name": "batch_processing_tool",
                "inputs": {"batch_size": 100, "failure_rate": 0.3},
                "expected_error_type": "partial_failure",
                "recovery_strategy": "process_successful_items"
            }
        ]
        
        async def test_error_scenario(test_case: Dict[str, Any]) -> Dict[str, Any]:
            """Test a specific error scenario and recovery mechanism."""
            scenario_start = time.time()
            scenario_result = {
                "scenario": test_case["scenario"],
                "success": False,
                "error_detected": False,
                "error_type_correct": False,
                "recovery_attempted": False,
                "recovery_successful": False,
                "total_attempts": 0,
                "duration_ms": 0.0
            }
            
            try:
                logger.info(f"Testing error scenario: {test_case['scenario']}")
                
                # Initial tool execution (expected to fail)
                scenario_result["total_attempts"] = 1
                
                initial_result = await enhanced_tool_engine.execute_tool(
                    tool_name=test_case["tool_name"],
                    tool_inputs=test_case["inputs"],
                    user_id=user_id,
                    execution_context=auth_context,
                    agent_execution_id=str(agent_execution.id),
                    timeout_seconds=1.0  # Short timeout for testing
                )
                
                if not initial_result.get("success", False):
                    scenario_result["error_detected"] = True
                    error_type = initial_result.get("error_type", "unknown")
                    scenario_result["error_type_correct"] = test_case["expected_error_type"] in error_type.lower()
                    
                    error_scenarios.append({
                        "scenario": test_case["scenario"],
                        "error_type": error_type,
                        "error_message": initial_result.get("error", ""),
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                    # Attempt recovery based on strategy
                    recovery_strategy = test_case["recovery_strategy"]
                    scenario_result["recovery_attempted"] = True
                    
                    recovery_start = time.time()
                    recovery_result = None
                    
                    if recovery_strategy == "retry_with_longer_timeout":
                        # Retry with longer timeout
                        scenario_result["total_attempts"] += 1
                        recovery_result = await enhanced_tool_engine.execute_tool(
                            tool_name=test_case["tool_name"],
                            tool_inputs={**test_case["inputs"], "timeout_seconds": 10.0},
                            user_id=user_id,
                            execution_context=auth_context,
                            agent_execution_id=str(agent_execution.id),
                            timeout_seconds=10.0
                        )
                    
                    elif recovery_strategy == "input_correction":
                        # Retry with corrected input
                        scenario_result["total_attempts"] += 1
                        corrected_inputs = {
                            "valid_data": "corrected_input_data",
                            "validation_strict": False
                        }
                        recovery_result = await enhanced_tool_engine.execute_tool(
                            tool_name=test_case["tool_name"],
                            tool_inputs=corrected_inputs,
                            user_id=user_id,
                            execution_context=auth_context,
                            agent_execution_id=str(agent_execution.id)
                        )
                    
                    elif recovery_strategy == "fallback_tool":
                        # Use fallback tool
                        scenario_result["total_attempts"] += 1
                        fallback_inputs = {"use_local_fallback": True}
                        recovery_result = await enhanced_tool_engine.execute_tool(
                            tool_name="local_fallback_tool",
                            tool_inputs=fallback_inputs,
                            user_id=user_id,
                            execution_context=auth_context,
                            agent_execution_id=str(agent_execution.id)
                        )
                    
                    elif recovery_strategy == "restart_and_retry":
                        # Simulate tool restart and retry
                        await asyncio.sleep(1)  # Simulate restart time
                        scenario_result["total_attempts"] += 1
                        recovery_result = await enhanced_tool_engine.execute_tool(
                            tool_name=test_case["tool_name"],
                            tool_inputs={**test_case["inputs"], "force_crash": False},
                            user_id=user_id,
                            execution_context=auth_context,
                            agent_execution_id=str(agent_execution.id)
                        )
                    
                    elif recovery_strategy == "process_successful_items":
                        # Process only successful items from partial failure
                        scenario_result["total_attempts"] += 1
                        recovery_inputs = {
                            **test_case["inputs"],
                            "process_partial": True,
                            "ignore_failures": True
                        }
                        recovery_result = await enhanced_tool_engine.execute_tool(
                            tool_name=test_case["tool_name"],
                            tool_inputs=recovery_inputs,
                            user_id=user_id,
                            execution_context=auth_context,
                            agent_execution_id=str(agent_execution.id)
                        )
                    
                    recovery_duration = time.time() - recovery_start
                    
                    if recovery_result and recovery_result.get("success", False):
                        scenario_result["recovery_successful"] = True
                        scenario_result["success"] = True
                    
                    recovery_attempts.append({
                        "scenario": test_case["scenario"],
                        "strategy": recovery_strategy,
                        "success": scenario_result["recovery_successful"],
                        "duration_ms": recovery_duration * 1000,
                        "attempts": scenario_result["total_attempts"]
                    })
                
                else:
                    # Tool succeeded unexpectedly - this might be a test issue
                    logger.warning(f"Error scenario {test_case['scenario']} unexpectedly succeeded")
                    scenario_result["success"] = True
            
            except Exception as e:
                logger.error(f"Error scenario {test_case['scenario']} test failed: {e}")
                scenario_result["error_detected"] = True
            
            scenario_result["duration_ms"] = (time.time() - scenario_start) * 1000
            return scenario_result
        
        # Execute all error scenario tests
        scenario_results = []
        for test_case in error_test_cases:
            result = await test_error_scenario(test_case)
            scenario_results.append(result)
            await asyncio.sleep(1)  # Brief pause between error tests
        
        # Phase 2: Analyze error detection and recovery effectiveness
        
        error_detection_rate = sum(1 for result in scenario_results if result["error_detected"]) / len(scenario_results)
        recovery_attempt_rate = sum(1 for result in scenario_results if result["recovery_attempted"]) / len(scenario_results)
        recovery_success_rate = sum(1 for result in scenario_results if result["recovery_successful"]) / len([r for r in scenario_results if r["recovery_attempted"]])
        
        logger.info(f"Error Handling Results:")
        logger.info(f"  Error Detection Rate: {error_detection_rate:.2%}")
        logger.info(f"  Recovery Attempt Rate: {recovery_attempt_rate:.2%}")
        logger.info(f"  Recovery Success Rate: {recovery_success_rate:.2%}")
        
        # Validate error handling effectiveness
        assert error_detection_rate >= 0.8, f"Error detection rate too low: {error_detection_rate:.2%} (expected  >= 80%)"
        assert recovery_attempt_rate >= 0.8, f"Recovery attempt rate too low: {recovery_attempt_rate:.2%} (expected  >= 80%)"
        assert recovery_success_rate >= 0.6, f"Recovery success rate too low: {recovery_success_rate:.2%} (expected  >= 60%)"
        
        # Phase 3: Test error propagation in tool chains
        logger.info("Testing error propagation in tool chains")
        
        # Create a tool chain where one tool failure should be handled gracefully
        chain_with_error = [
            {"tool": "data_collector", "inputs": {"source": "valid"}},
            {"tool": "failing_processor", "inputs": {"force_error": True}},  # This will fail
            {"tool": "error_handler", "inputs": {"handle_upstream_errors": True}},  # Should handle error
            {"tool": "final_reporter", "inputs": {"include_error_summary": True}}
        ]
        
        chain_results = []
        for i, tool_config in enumerate(chain_with_error):
            try:
                # For the error handler tool, provide error context from previous failure
                if tool_config["tool"] == "error_handler" and chain_results:
                    prev_result = chain_results[-1]
                    if not prev_result.get("success", False):
                        tool_config["inputs"]["upstream_error"] = prev_result.get("error", "Unknown error")
                
                result = await enhanced_tool_engine.execute_tool(
                    tool_name=tool_config["tool"],
                    tool_inputs=tool_config["inputs"],
                    user_id=user_id,
                    execution_context=auth_context,
                    agent_execution_id=str(agent_execution.id)
                )
                
                chain_results.append(result)
                
            except Exception as e:
                chain_results.append({
                    "success": False,
                    "error": str(e),
                    "tool": tool_config["tool"]
                })
        
        # Validate that error propagation was handled correctly
        successful_chain_steps = sum(1 for result in chain_results if result.get("success", False))
        
        # We expect at least the error handler and final reporter to succeed
        assert successful_chain_steps >= 2, f"Tool chain error propagation failed: only {successful_chain_steps} steps succeeded"
        
        # Complete agent execution
        await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result={
                "error_recovery_test": "completed",
                "scenarios_tested": len(error_test_cases),
                "recovery_success_rate": recovery_success_rate,
                "error_detection_rate": error_detection_rate
            }
        )
        
        # Phase 4: Validate WebSocket error events
        error_events = [e for e in websocket_events if "error" in e.get("type", "").lower()]
        recovery_events = [e for e in websocket_events if "recovery" in e.get("type", "").lower()]
        
        logger.info(f"WebSocket Events: {len(error_events)} error events, {len(recovery_events)} recovery events")
        
        # Should have error events for failures and recovery events for successful recoveries
        assert len(error_events) >= len(error_scenarios) * 0.5, f"Insufficient error WebSocket events: {len(error_events)}"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 120.0, f"Error recovery test should complete in <120s, took {execution_time:.2f}s"
        
        logger.info(f"Tool error propagation and recovery test completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_parallel_tool_execution_result_aggregation(self, real_services_fixture):
        """
        Test parallel tool execution with sophisticated result aggregation.
        
        PERFORMANCE SCENARIO: Validates parallel execution capabilities
        and intelligent result combination for comprehensive analysis.
        """
        logger.info("Starting parallel tool execution and result aggregation test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_parallel_user")
        user_id = auth_context.user_id  # Use the same user_id from auth_context
        
        # Initialize components with SSOT patterns
        llm_manager = LLMManager()  # SSOT: Create LLM manager for agent registry
        agent_registry = AgentRegistry(llm_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        enhanced_tool_engine = EnhancedToolExecutionEngine()
        
        # Track parallel execution metrics
        parallel_executions = []
        aggregation_results = []
        websocket_events = []
        
        def capture_websocket_event(event):
            websocket_events.append({
                **event,
                "captured_at": datetime.now(timezone.utc)
            })
        
        websocket_manager.add_event_listener(capture_websocket_event)
        
        # Start agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            user_id=str(user_id),
            thread_id=str(thread_id),
            run_id=str(run_id),
            agent_name="supervisor_agent",
            request_id=str(uuid.uuid4()),
            metadata={
                "message": "Perform parallel analysis across multiple domains with intelligent result aggregation"
            }
        )
        
        # Execute agent with user context
        agent_execution = await execution_engine.execute_agent(agent_context, auth_context)
        
        # Phase 1: Define parallel tool execution groups
        parallel_tool_groups = {
            "infrastructure_analysis": [
                {"tool": "compute_analyzer", "inputs": {"resource_type": "compute", "depth": "detailed"}},
                {"tool": "storage_analyzer", "inputs": {"resource_type": "storage", "depth": "detailed"}},
                {"tool": "network_analyzer", "inputs": {"resource_type": "network", "depth": "detailed"}}
            ],
            "cost_optimization": [
                {"tool": "cost_calculator", "inputs": {"calculation_type": "current_spend"}},
                {"tool": "savings_identifier", "inputs": {"analysis_type": "opportunities"}},
                {"tool": "roi_calculator", "inputs": {"projection_period": "12_months"}}
            ],
            "performance_metrics": [
                {"tool": "latency_analyzer", "inputs": {"metric_type": "response_time"}},
                {"tool": "throughput_analyzer", "inputs": {"metric_type": "requests_per_second"}},
                {"tool": "availability_analyzer", "inputs": {"metric_type": "uptime_stats"}}
            ],
            "security_assessment": [
                {"tool": "vulnerability_scanner", "inputs": {"scan_type": "comprehensive"}},
                {"tool": "compliance_checker", "inputs": {"standards": ["SOC2", "ISO27001"]}},
                {"tool": "access_auditor", "inputs": {"audit_type": "permissions"}}
            ]
        }
        
        # Phase 2: Execute tool groups in parallel
        async def execute_parallel_group(group_name: str, tools: List[Dict]) -> Dict[str, Any]:
            """Execute a group of tools in parallel."""
            group_start_time = time.time()
            
            async def execute_single_tool(tool_config: Dict) -> Dict[str, Any]:
                tool_start = time.time()
                try:
                    result = await enhanced_tool_engine.execute_tool(
                        tool_name=tool_config["tool"],
                        tool_inputs=tool_config["inputs"],
                        user_id=user_id,
                        execution_context=auth_context,
                        agent_execution_id=str(agent_execution.id)
                    )
                    
                    tool_duration = time.time() - tool_start
                    
                    return {
                        "tool": tool_config["tool"],
                        "success": result.get("success", False),
                        "duration_ms": tool_duration * 1000,
                        "output": result.get("outputs", {}),
                        "error": result.get("error") if not result.get("success", False) else None
                    }
                    
                except Exception as e:
                    return {
                        "tool": tool_config["tool"],
                        "success": False,
                        "duration_ms": (time.time() - tool_start) * 1000,
                        "output": {},
                        "error": str(e)
                    }
            
            # Execute all tools in the group concurrently
            tool_tasks = [execute_single_tool(tool_config) for tool_config in tools]
            tool_results = await asyncio.gather(*tool_tasks)
            
            group_duration = time.time() - group_start_time
            successful_tools = [r for r in tool_results if r["success"]]
            failed_tools = [r for r in tool_results if not r["success"]]
            
            group_result = {
                "group_name": group_name,
                "total_tools": len(tools),
                "successful_tools": len(successful_tools),
                "failed_tools": len(failed_tools),
                "group_duration_ms": group_duration * 1000,
                "tool_results": tool_results,
                "success_rate": len(successful_tools) / len(tools)
            }
            
            parallel_executions.append(group_result)
            logger.info(f"Group {group_name}: {len(successful_tools)}/{len(tools)} tools succeeded in {group_duration:.2f}s")
            
            return group_result
        
        # Execute all groups in parallel
        group_tasks = [execute_parallel_group(group_name, tools) 
                      for group_name, tools in parallel_tool_groups.items()]
        
        group_results = await asyncio.gather(*group_tasks)
        
        # Phase 3: Intelligent result aggregation
        logger.info("Starting intelligent result aggregation")
        aggregation_start = time.time()
        
        # Aggregate results by domain
        aggregated_analysis = {}
        
        for group_result in group_results:
            group_name = group_result["group_name"]
            successful_results = [r["output"] for r in group_result["tool_results"] if r["success"]]
            
            if successful_results:
                # Perform domain-specific aggregation
                if group_name == "infrastructure_analysis":
                    # Combine infrastructure metrics
                    aggregated_analysis["infrastructure"] = {
                        "compute_metrics": {},
                        "storage_metrics": {},
                        "network_metrics": {},
                        "total_resources": 0
                    }
                    
                    for result in successful_results:
                        for key, value in result.items():
                            if "compute" in key.lower():
                                aggregated_analysis["infrastructure"]["compute_metrics"].update({key: value})
                            elif "storage" in key.lower():
                                aggregated_analysis["infrastructure"]["storage_metrics"].update({key: value})
                            elif "network" in key.lower():
                                aggregated_analysis["infrastructure"]["network_metrics"].update({key: value})
                
                elif group_name == "cost_optimization":
                    # Aggregate cost and savings data
                    total_current_cost = 0
                    total_potential_savings = 0
                    projected_roi = 0
                    
                    for result in successful_results:
                        total_current_cost += result.get("current_cost", 0)
                        total_potential_savings += result.get("potential_savings", 0)
                        if "roi" in result:
                            projected_roi = max(projected_roi, result.get("roi", 0))
                    
                    aggregated_analysis["cost_optimization"] = {
                        "current_monthly_cost": total_current_cost,
                        "potential_monthly_savings": total_potential_savings,
                        "savings_percentage": (total_potential_savings / total_current_cost * 100) if total_current_cost > 0 else 0,
                        "projected_12_month_roi": projected_roi
                    }
                
                elif group_name == "performance_metrics":
                    # Aggregate performance data
                    aggregated_analysis["performance"] = {
                        "avg_latency_ms": 0,
                        "avg_throughput_rps": 0,
                        "availability_percentage": 0,
                        "performance_score": 0
                    }
                    
                    latency_values = []
                    throughput_values = []
                    availability_values = []
                    
                    for result in successful_results:
                        if "latency" in result:
                            latency_values.extend(result["latency"] if isinstance(result["latency"], list) else [result["latency"]])
                        if "throughput" in result:
                            throughput_values.extend(result["throughput"] if isinstance(result["throughput"], list) else [result["throughput"]])
                        if "availability" in result:
                            availability_values.extend(result["availability"] if isinstance(result["availability"], list) else [result["availability"]])
                    
                    if latency_values:
                        aggregated_analysis["performance"]["avg_latency_ms"] = sum(latency_values) / len(latency_values)
                    if throughput_values:
                        aggregated_analysis["performance"]["avg_throughput_rps"] = sum(throughput_values) / len(throughput_values)
                    if availability_values:
                        aggregated_analysis["performance"]["availability_percentage"] = sum(availability_values) / len(availability_values)
                
                elif group_name == "security_assessment":
                    # Aggregate security findings
                    total_vulnerabilities = 0
                    compliance_status = {}
                    access_issues = 0
                    
                    for result in successful_results:
                        total_vulnerabilities += result.get("vulnerability_count", 0)
                        if "compliance" in result:
                            compliance_status.update(result["compliance"])
                        access_issues += result.get("access_violations", 0)
                    
                    compliance_score = sum(1 for status in compliance_status.values() if status) / len(compliance_status) if compliance_status else 0
                    
                    aggregated_analysis["security"] = {
                        "total_vulnerabilities": total_vulnerabilities,
                        "compliance_score": compliance_score * 100,
                        "access_violations": access_issues,
                        "security_score": max(0, 100 - total_vulnerabilities * 5 - access_issues * 10)
                    }
        
        # Phase 4: Generate comprehensive summary
        comprehensive_summary = {
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "parallel_execution_summary": {
                "total_groups": len(group_results),
                "total_tools_executed": sum(gr["total_tools"] for gr in group_results),
                "total_successful_tools": sum(gr["successful_tools"] for gr in group_results),
                "overall_success_rate": sum(gr["successful_tools"] for gr in group_results) / sum(gr["total_tools"] for gr in group_results),
                "total_execution_time_ms": max(gr["group_duration_ms"] for gr in group_results)  # Max since they ran in parallel
            },
            "aggregated_insights": aggregated_analysis,
            "recommendations": []
        }
        
        # Generate intelligent recommendations based on aggregated data
        if "cost_optimization" in aggregated_analysis:
            cost_data = aggregated_analysis["cost_optimization"]
            if cost_data["savings_percentage"] > 20:
                comprehensive_summary["recommendations"].append({
                    "type": "cost_optimization",
                    "priority": "high",
                    "message": f"Significant cost savings opportunity: {cost_data['savings_percentage']:.1f}% reduction possible"
                })
        
        if "security" in aggregated_analysis:
            security_data = aggregated_analysis["security"]
            if security_data["total_vulnerabilities"] > 10:
                comprehensive_summary["recommendations"].append({
                    "type": "security",
                    "priority": "critical",
                    "message": f"Critical security issues detected: {security_data['total_vulnerabilities']} vulnerabilities found"
                })
        
        if "performance" in aggregated_analysis:
            perf_data = aggregated_analysis["performance"]
            if perf_data["availability_percentage"] < 99.0:
                comprehensive_summary["recommendations"].append({
                    "type": "performance",
                    "priority": "medium",
                    "message": f"Availability improvement needed: current {perf_data['availability_percentage']:.2f}%"
                })
        
        aggregation_duration = time.time() - aggregation_start
        aggregation_results.append({
            "aggregation_duration_ms": aggregation_duration * 1000,
            "domains_aggregated": len(aggregated_analysis),
            "recommendations_generated": len(comprehensive_summary["recommendations"]),
            "summary": comprehensive_summary
        })
        
        # Complete agent execution with comprehensive results
        await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result=comprehensive_summary
        )
        
        # Phase 5: Validate parallel execution and aggregation
        
        # Validate parallel execution efficiency
        total_sequential_time = sum(sum(tr["duration_ms"] for tr in gr["tool_results"]) for gr in group_results)
        actual_parallel_time = max(gr["group_duration_ms"] for gr in group_results)
        parallelization_efficiency = (total_sequential_time - actual_parallel_time) / total_sequential_time
        
        logger.info(f"Parallelization Efficiency: {parallelization_efficiency:.2%}")
        logger.info(f"Sequential time would be: {total_sequential_time:.1f}ms, Parallel time: {actual_parallel_time:.1f}ms")
        
        # Parallel execution should provide significant speedup
        assert parallelization_efficiency >= 0.5, f"Parallelization efficiency too low: {parallelization_efficiency:.2%} (expected  >= 50%)"
        
        # Validate overall success rate
        overall_success_rate = comprehensive_summary["parallel_execution_summary"]["overall_success_rate"]
        assert overall_success_rate >= 0.8, f"Overall tool success rate too low: {overall_success_rate:.2%} (expected  >= 80%)"
        
        # Validate aggregation quality
        domains_with_data = len(aggregated_analysis)
        expected_domains = len(parallel_tool_groups)
        aggregation_coverage = domains_with_data / expected_domains
        
        assert aggregation_coverage >= 0.75, f"Aggregation coverage too low: {aggregation_coverage:.2%} (expected  >= 75%)"
        
        # Validate intelligent recommendations
        recommendations_count = len(comprehensive_summary["recommendations"])
        assert recommendations_count > 0, "Should generate at least one intelligent recommendation"
        
        # Validate WebSocket events for parallel execution
        parallel_tool_events = [e for e in websocket_events if e.get("type") in [
            WebSocketEventType.TOOL_EXECUTING.value,
            WebSocketEventType.TOOL_COMPLETED.value
        ]]
        
        total_tools = comprehensive_summary["parallel_execution_summary"]["total_tools_executed"]
        expected_events = total_tools * 2  # executing + completed
        
        assert len(parallel_tool_events) >= expected_events * 0.7, f"Insufficient parallel tool WebSocket events: {len(parallel_tool_events)}/{expected_events}"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 90.0, f"Parallel execution test should complete in <90s, took {execution_time:.2f}s"
        
        # Parallel execution should be faster than sequential execution would be
        estimated_sequential_time = total_sequential_time / 1000  # Convert to seconds
        speedup_factor = estimated_sequential_time / execution_time if execution_time > 0 else 0
        
        assert speedup_factor >= 2.0, f"Parallel speedup too low: {speedup_factor:.1f}x (expected  >= 2.0x)"
        
        logger.info(f"Parallel tool execution test completed in {execution_time:.2f}s with {parallelization_efficiency:.2%} efficiency and {speedup_factor:.1f}x speedup")

    @pytest.mark.asyncio  
    async def test_dynamic_tool_selection_execution_path_optimization(self, real_services_fixture):
        """
        Test dynamic tool selection and execution path optimization.
        
        INTELLIGENCE SCENARIO: Validates system can intelligently select
        optimal tool execution paths based on context and previous results.
        """
        logger.info("Starting dynamic tool selection and execution path optimization test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_dynamic_user")
        user_id = auth_context.user_id  # Use the same user_id from auth_context
        
        # Initialize components with SSOT patterns
        llm_manager = LLMManager()  # SSOT: Create LLM manager for agent registry
        agent_registry = AgentRegistry(llm_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        enhanced_tool_engine = EnhancedToolExecutionEngine()
        
        # Track dynamic selection decisions
        selection_decisions = []
        path_optimizations = []
        execution_paths = []
        websocket_events = []
        
        def capture_websocket_event(event):
            websocket_events.append({
                **event,
                "captured_at": datetime.now(timezone.utc)
            })
        
        websocket_manager.add_event_listener(capture_websocket_event)
        
        # Start agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            user_id=str(user_id),
            thread_id=str(thread_id),
            run_id=str(run_id),
            agent_name="supervisor_agent",
            request_id=str(uuid.uuid4()),
            metadata={
                "message": "Perform intelligent analysis with dynamic tool selection based on data characteristics and optimization opportunities"
            }
        )
        
        # Execute agent with user context
        agent_execution = await execution_engine.execute_agent(agent_context, auth_context)
        
        # Phase 1: Define adaptive analysis scenarios
        analysis_scenarios = [
            {
                "scenario": "cost_focused_analysis",
                "context": {"priority": "cost_optimization", "budget_constraint": "high", "timeline": "urgent"},
                "available_tools": ["quick_cost_analyzer", "detailed_cost_analyzer", "cost_forecaster"],
                "selection_criteria": ["speed", "cost_focus", "accuracy"]
            },
            {
                "scenario": "security_focused_analysis", 
                "context": {"priority": "security_compliance", "risk_tolerance": "low", "audit_deadline": "approaching"},
                "available_tools": ["vulnerability_scanner", "compliance_checker", "penetration_tester", "security_auditor"],
                "selection_criteria": ["thoroughness", "compliance_coverage", "risk_identification"]
            },
            {
                "scenario": "performance_optimization",
                "context": {"priority": "performance", "current_issues": "latency", "scale": "enterprise"},
                "available_tools": ["latency_analyzer", "bottleneck_identifier", "capacity_planner", "optimization_engine"],
                "selection_criteria": ["performance_impact", "scalability", "implementation_ease"]
            }
        ]
        
        # Phase 2: Implement intelligent tool selection logic
        async def select_optimal_tools(scenario: Dict[str, Any]) -> List[str]:
            """Select optimal tools based on scenario context."""
            selection_start = time.time()
            context = scenario["context"]
            available_tools = scenario["available_tools"]
            criteria = scenario["selection_criteria"]
            
            # Tool scoring based on context
            tool_scores = {}
            
            for tool in available_tools:
                score = 0.0
                
                # Score based on priority alignment
                if context["priority"] == "cost_optimization" and "cost" in tool:
                    score += 30
                elif context["priority"] == "security_compliance" and ("security" in tool or "compliance" in tool):
                    score += 30
                elif context["priority"] == "performance" and ("performance" in tool or "latency" in tool or "capacity" in tool):
                    score += 30
                
                # Score based on constraints
                if context.get("timeline") == "urgent" and "quick" in tool:
                    score += 20
                elif context.get("timeline") != "urgent" and "detailed" in tool:
                    score += 15
                
                # Score based on risk tolerance
                if context.get("risk_tolerance") == "low" and ("audit" in tool or "compliance" in tool):
                    score += 15
                
                # Score based on scale requirements
                if context.get("scale") == "enterprise" and ("capacity" in tool or "optimization" in tool):
                    score += 10
                
                tool_scores[tool] = score
            
            # Select top scoring tools (limit to 3 for efficiency)
            selected_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            selected_tool_names = [tool for tool, score in selected_tools]
            
            selection_decision = {
                "scenario": scenario["scenario"],
                "context": context,
                "tool_scores": tool_scores,
                "selected_tools": selected_tool_names,
                "selection_duration_ms": (time.time() - selection_start) * 1000,
                "selection_rationale": f"Selected based on {', '.join(criteria)}"
            }
            
            selection_decisions.append(selection_decision)
            logger.info(f"Selected tools for {scenario['scenario']}: {selected_tool_names}")
            
            return selected_tool_names
        
        # Phase 3: Execute scenarios with dynamic tool selection
        for scenario in analysis_scenarios:
            scenario_start = time.time()
            
            # Select optimal tools for this scenario
            selected_tools = await select_optimal_tools(scenario)
            
            # Execute selected tools and adapt based on results
            tool_results = []
            execution_path = {
                "scenario": scenario["scenario"],
                "planned_tools": selected_tools,
                "executed_tools": [],
                "adaptations": [],
                "final_results": {}
            }
            
            for i, tool_name in enumerate(selected_tools):
                tool_start = time.time()
                
                try:
                    # Prepare inputs based on previous results
                    tool_inputs = {"scenario_context": scenario["context"]}
                    
                    # Add previous tool outputs as context
                    if tool_results:
                        tool_inputs["previous_results"] = [r.get("outputs", {}) for r in tool_results if r.get("success")]
                    
                    # Execute tool
                    result = await enhanced_tool_engine.execute_tool(
                        tool_name=tool_name,
                        tool_inputs=tool_inputs,
                        user_id=user_id,
                        execution_context=auth_context,
                        agent_execution_id=str(agent_execution.id)
                    )
                    
                    tool_duration = time.time() - tool_start
                    result["execution_duration_ms"] = tool_duration * 1000
                    tool_results.append(result)
                    
                    execution_path["executed_tools"].append({
                        "tool": tool_name,
                        "success": result.get("success", False),
                        "duration_ms": tool_duration * 1000
                    })
                    
                    # Adaptive logic: modify remaining execution based on results
                    if result.get("success") and i < len(selected_tools) - 1:
                        outputs = result.get("outputs", {})
                        
                        # Example adaptation: If security issues found, prioritize security tools
                        if "vulnerabilities" in outputs and outputs.get("vulnerability_count", 0) > 10:
                            remaining_tools = selected_tools[i+1:]
                            if "security_auditor" not in remaining_tools and "security_auditor" in scenario["available_tools"]:
                                remaining_tools.append("security_auditor")
                                selected_tools = selected_tools[:i+1] + remaining_tools
                                
                                execution_path["adaptations"].append({
                                    "trigger": "high_vulnerability_count",
                                    "action": "added_security_auditor",
                                    "at_step": i
                                })
                        
                        # Example adaptation: If cost savings opportunities are low, try different approach
                        elif "cost_savings" in outputs and outputs.get("potential_savings_percent", 0) < 5:
                            remaining_tools = selected_tools[i+1:]
                            if "detailed_cost_analyzer" not in remaining_tools and "detailed_cost_analyzer" in scenario["available_tools"]:
                                remaining_tools = ["detailed_cost_analyzer"] + remaining_tools
                                selected_tools = selected_tools[:i+1] + remaining_tools
                                
                                execution_path["adaptations"].append({
                                    "trigger": "low_cost_savings",
                                    "action": "switched_to_detailed_analysis",
                                    "at_step": i
                                })
                
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {e}")
                    execution_path["executed_tools"].append({
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                        "duration_ms": (time.time() - tool_start) * 1000
                    })
                
                # Brief pause between tools
                await asyncio.sleep(0.2)
            
            # Aggregate results for this scenario
            successful_results = [r for r in tool_results if r.get("success")]
            execution_path["final_results"] = {
                "total_tools_executed": len(execution_path["executed_tools"]),
                "successful_tools": len(successful_results),
                "adaptations_made": len(execution_path["adaptations"]),
                "scenario_duration_ms": (time.time() - scenario_start) * 1000
            }
            
            execution_paths.append(execution_path)
        
        # Phase 4: Analyze path optimization effectiveness
        
        # Calculate adaptation effectiveness
        total_adaptations = sum(len(path["adaptations"]) for path in execution_paths)
        total_scenarios = len(analysis_scenarios)
        adaptation_rate = total_adaptations / total_scenarios
        
        # Calculate execution efficiency
        avg_tools_per_scenario = sum(path["final_results"]["total_tools_executed"] for path in execution_paths) / len(execution_paths)
        avg_success_rate = sum(path["final_results"]["successful_tools"] / path["final_results"]["total_tools_executed"] 
                             for path in execution_paths if path["final_results"]["total_tools_executed"] > 0) / len(execution_paths)
        
        # Calculate selection accuracy (tools chosen were appropriate for context)
        selection_accuracy_scores = []
        for decision in selection_decisions:
            score = 0.0
            scenario_name = decision["scenario"] 
            selected_tools = decision["selected_tools"]
            
            # Check if selections align with scenario priorities
            if scenario_name == "cost_focused_analysis":
                score += sum(1 for tool in selected_tools if "cost" in tool) / len(selected_tools)
            elif scenario_name == "security_focused_analysis":
                score += sum(1 for tool in selected_tools if ("security" in tool or "compliance" in tool or "audit" in tool)) / len(selected_tools)
            elif scenario_name == "performance_optimization":
                score += sum(1 for tool in selected_tools if ("performance" in tool or "latency" in tool or "capacity" in tool or "optimization" in tool)) / len(selected_tools)
            
            selection_accuracy_scores.append(score)
        
        avg_selection_accuracy = sum(selection_accuracy_scores) / len(selection_accuracy_scores) if selection_accuracy_scores else 0.0
        
        path_optimization_summary = {
            "total_scenarios": total_scenarios,
            "adaptations_per_scenario": adaptation_rate,
            "avg_tools_per_scenario": avg_tools_per_scenario,
            "avg_success_rate": avg_success_rate,
            "selection_accuracy": avg_selection_accuracy,
            "optimization_effectiveness": (adaptation_rate + avg_success_rate + avg_selection_accuracy) / 3
        }
        
        path_optimizations.append(path_optimization_summary)
        
        logger.info(f"Path Optimization Results:")
        logger.info(f"  Adaptations per scenario: {adaptation_rate:.2f}")
        logger.info(f"  Average success rate: {avg_success_rate:.2%}")
        logger.info(f"  Selection accuracy: {avg_selection_accuracy:.2%}")
        logger.info(f"  Overall optimization effectiveness: {path_optimization_summary['optimization_effectiveness']:.2%}")
        
        # Complete agent execution
        await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result={
                "dynamic_tool_selection": "completed",
                "scenarios_analyzed": total_scenarios,
                "path_optimization_summary": path_optimization_summary,
                "execution_paths": execution_paths
            }
        )
        
        # Phase 5: Validate dynamic selection and optimization
        
        # Validate selection accuracy
        assert avg_selection_accuracy >= 0.7, f"Tool selection accuracy too low: {avg_selection_accuracy:.2%} (expected  >= 70%)"
        
        # Validate adaptation capability
        assert adaptation_rate >= 0.5, f"Adaptation rate too low: {adaptation_rate:.2f} (expected  >= 0.5 adaptations per scenario)"
        
        # Validate execution success rate
        assert avg_success_rate >= 0.8, f"Tool execution success rate too low: {avg_success_rate:.2%} (expected  >= 80%)"
        
        # Validate overall optimization effectiveness
        assert path_optimization_summary["optimization_effectiveness"] >= 0.75, f"Optimization effectiveness too low: {path_optimization_summary['optimization_effectiveness']:.2%} (expected  >= 75%)"
        
        # Validate WebSocket events for dynamic selection
        selection_events = [e for e in websocket_events if "selection" in e.get("type", "").lower()]
        adaptation_events = [e for e in websocket_events if "adaptation" in e.get("type", "").lower()]
        
        # Should have events for major selection and adaptation decisions
        total_expected_events = len(selection_decisions) + total_adaptations
        actual_events = len(selection_events) + len(adaptation_events)
        
        logger.info(f"Dynamic selection WebSocket events: {actual_events}/{total_expected_events} expected events")
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 150.0, f"Dynamic tool selection test should complete in <150s, took {execution_time:.2f}s"
        
        # Validate that dynamic selection was more efficient than static approaches
        estimated_static_time = total_scenarios * len(scenario["available_tools"][0] if scenario else []) * 5  # Assume 5s per tool
        efficiency_gain = (estimated_static_time - execution_time) / estimated_static_time if estimated_static_time > 0 else 0
        
        assert efficiency_gain >= 0.3, f"Dynamic selection efficiency gain too low: {efficiency_gain:.2%} (expected  >= 30%)"
        
        logger.info(f"Dynamic tool selection test completed in {execution_time:.2f}s with {path_optimization_summary['optimization_effectiveness']:.2%} optimization effectiveness")

    @pytest.mark.asyncio
    async def test_tool_timeout_circuit_breaker_patterns(self, real_services_fixture):
        """
        Test tool timeout handling and circuit breaker patterns.
        
        RESILIENCE SCENARIO: Validates system handles tool timeouts gracefully
        and implements circuit breaker patterns to prevent cascading failures.
        """
        logger.info("Starting tool timeout and circuit breaker patterns test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_timeout_user")
        user_id = auth_context.user_id  # Use the same user_id from auth_context
        
        # Initialize components with SSOT patterns
        llm_manager = LLMManager()  # SSOT: Create LLM manager for agent registry
        agent_registry = AgentRegistry(llm_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        enhanced_tool_engine = EnhancedToolExecutionEngine()
        
        # Track timeout and circuit breaker events
        timeout_events = []
        circuit_breaker_events = []
        tool_execution_attempts = []
        websocket_events = []
        
        def capture_websocket_event(event):
            websocket_events.append({
                **event,
                "captured_at": datetime.now(timezone.utc)
            })
        
        websocket_manager.add_event_listener(capture_websocket_event)
        
        # Start agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            user_id=str(user_id),
            thread_id=str(thread_id),
            run_id=str(run_id),
            agent_name="supervisor_agent",
            request_id=str(uuid.uuid4()),
            metadata={
                "message": "Test tool timeout and circuit breaker resilience patterns"
            }
        )
        
        # Execute agent with user context
        agent_execution = await execution_engine.execute_agent(agent_context, auth_context)
        
        # Phase 1: Test various timeout scenarios
        timeout_test_cases = [
            {
                "tool": "quick_response_tool",
                "timeout_seconds": 5.0,
                "expected_duration": 1.0,
                "should_timeout": False,
                "scenario": "normal_execution"
            },
            {
                "tool": "slow_tool",
                "timeout_seconds": 2.0,
                "expected_duration": 5.0,  # Will timeout
                "should_timeout": True,
                "scenario": "timeout_expected"
            },
            {
                "tool": "variable_speed_tool",
                "timeout_seconds": 3.0,
                "expected_duration": 2.5,  # Close to timeout
                "should_timeout": False,
                "scenario": "near_timeout_success"
            },
            {
                "tool": "unreliable_tool",
                "timeout_seconds": 1.0,
                "expected_duration": 10.0,  # Will definitely timeout
                "should_timeout": True,
                "scenario": "definite_timeout"
            }
        ]
        
        async def test_tool_timeout(test_case: Dict[str, Any]) -> Dict[str, Any]:
            """Test individual tool timeout scenario."""
            attempt_start = time.time()
            
            try:
                result = await enhanced_tool_engine.execute_tool(
                    tool_name=test_case["tool"],
                    tool_inputs={
                        "simulate_duration": test_case["expected_duration"],
                        "timeout_test": True
                    },
                    user_id=user_id,
                    execution_context=auth_context,
                    agent_execution_id=str(agent_execution.id),
                    timeout_seconds=test_case["timeout_seconds"]
                )
                
                actual_duration = time.time() - attempt_start
                success = result.get("success", False)
                timed_out = actual_duration >= test_case["timeout_seconds"] * 0.95  # Allow 5% tolerance
                
                attempt_result = {
                    "tool": test_case["tool"],
                    "scenario": test_case["scenario"],
                    "success": success,
                    "timed_out": timed_out,
                    "expected_timeout": test_case["should_timeout"],
                    "timeout_handled_correctly": timed_out == test_case["should_timeout"],
                    "actual_duration": actual_duration,
                    "timeout_limit": test_case["timeout_seconds"]
                }
                
                if timed_out:
                    timeout_events.append({
                        "tool": test_case["tool"],
                        "timeout_seconds": test_case["timeout_seconds"],
                        "actual_duration": actual_duration,
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                tool_execution_attempts.append(attempt_result)
                return attempt_result
                
            except Exception as e:
                actual_duration = time.time() - attempt_start
                
                attempt_result = {
                    "tool": test_case["tool"],
                    "scenario": test_case["scenario"],
                    "success": False,
                    "timed_out": "timeout" in str(e).lower(),
                    "expected_timeout": test_case["should_timeout"],
                    "timeout_handled_correctly": "timeout" in str(e).lower() and test_case["should_timeout"],
                    "actual_duration": actual_duration,
                    "timeout_limit": test_case["timeout_seconds"],
                    "error": str(e)
                }
                
                tool_execution_attempts.append(attempt_result)
                return attempt_result
        
        # Execute timeout test cases
        for test_case in timeout_test_cases:
            result = await test_tool_timeout(test_case)
            logger.info(f"Timeout test {test_case['scenario']}: {'PASS' if result['timeout_handled_correctly'] else 'FAIL'}")
            await asyncio.sleep(0.5)
        
        # Phase 2: Test circuit breaker patterns
        logger.info("Testing circuit breaker patterns")
        
        # Simulate repeated failures to trigger circuit breaker
        failing_tool = "consistently_failing_tool"
        circuit_breaker_threshold = 3  # Open circuit after 3 failures
        
        circuit_breaker_state = {
            "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
            "failure_count": 0,
            "last_failure_time": None,
            "half_open_timeout": 5.0  # seconds
        }
        
        async def execute_with_circuit_breaker(tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Execute tool with circuit breaker pattern."""
            
            # Check circuit breaker state
            if circuit_breaker_state["state"] == "OPEN":
                time_since_failure = time.time() - (circuit_breaker_state["last_failure_time"] or 0)
                if time_since_failure < circuit_breaker_state["half_open_timeout"]:
                    # Circuit is open, fail fast
                    circuit_breaker_events.append({
                        "event": "circuit_open_fail_fast",
                        "tool": tool_name,
                        "timestamp": datetime.now(timezone.utc)
                    })
                    return {
                        "success": False,
                        "error": "Circuit breaker OPEN - failing fast",
                        "circuit_breaker_triggered": True
                    }
                else:
                    # Try half-open state
                    circuit_breaker_state["state"] = "HALF_OPEN"
                    circuit_breaker_events.append({
                        "event": "circuit_half_open",
                        "tool": tool_name,
                        "timestamp": datetime.now(timezone.utc)
                    })
            
            try:
                # Attempt tool execution
                result = await enhanced_tool_engine.execute_tool(
                    tool_name=tool_name,
                    tool_inputs=inputs,
                    user_id=user_id,
                    execution_context=auth_context,
                    agent_execution_id=str(agent_execution.id),
                    timeout_seconds=2.0
                )
                
                if result.get("success", False):
                    # Success - reset circuit breaker
                    if circuit_breaker_state["state"] == "HALF_OPEN":
                        circuit_breaker_state["state"] = "CLOSED"
                        circuit_breaker_state["failure_count"] = 0
                        circuit_breaker_events.append({
                            "event": "circuit_closed_after_success",
                            "tool": tool_name,
                            "timestamp": datetime.now(timezone.utc)
                        })
                    return result
                else:
                    # Failure - increment failure count
                    circuit_breaker_state["failure_count"] += 1
                    circuit_breaker_state["last_failure_time"] = time.time()
                    
                    if circuit_breaker_state["failure_count"] >= circuit_breaker_threshold:
                        circuit_breaker_state["state"] = "OPEN"
                        circuit_breaker_events.append({
                            "event": "circuit_opened",
                            "tool": tool_name,
                            "failure_count": circuit_breaker_state["failure_count"],
                            "timestamp": datetime.now(timezone.utc)
                        })
                    
                    return result
                    
            except Exception as e:
                # Exception - treat as failure
                circuit_breaker_state["failure_count"] += 1
                circuit_breaker_state["last_failure_time"] = time.time()
                
                if circuit_breaker_state["failure_count"] >= circuit_breaker_threshold:
                    circuit_breaker_state["state"] = "OPEN"
                    circuit_breaker_events.append({
                        "event": "circuit_opened",
                        "tool": tool_name,
                        "failure_count": circuit_breaker_state["failure_count"],
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                return {
                    "success": False,
                    "error": str(e),
                    "circuit_breaker_failure": True
                }
        
        # Execute multiple attempts to trigger circuit breaker
        circuit_breaker_results = []
        
        for attempt in range(8):  # More attempts than threshold to test circuit breaker
            result = await execute_with_circuit_breaker(
                failing_tool,
                {"force_failure": True, "attempt": attempt}
            )
            
            circuit_breaker_results.append({
                "attempt": attempt,
                "success": result.get("success", False),
                "circuit_breaker_triggered": result.get("circuit_breaker_triggered", False),
                "circuit_state": circuit_breaker_state["state"],
                "failure_count": circuit_breaker_state["failure_count"]
            })
            
            logger.info(f"Circuit breaker attempt {attempt}: State={circuit_breaker_state['state']}, Failures={circuit_breaker_state['failure_count']}")
            await asyncio.sleep(0.5)
        
        # Phase 3: Test circuit breaker recovery
        logger.info("Testing circuit breaker recovery")
        
        # Wait for half-open timeout
        await asyncio.sleep(circuit_breaker_state["half_open_timeout"] + 1)
        
        # Try with a successful tool to test recovery
        recovery_result = await execute_with_circuit_breaker(
            "reliable_recovery_tool",
            {"ensure_success": True}
        )
        
        circuit_breaker_results.append({
            "attempt": "recovery",
            "success": recovery_result.get("success", False),
            "circuit_state": circuit_breaker_state["state"],
            "recovery_test": True
        })
        
        # Complete agent execution
        await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result={
                "timeout_circuit_breaker_test": "completed",
                "timeout_tests": len(timeout_test_cases),
                "circuit_breaker_events": len(circuit_breaker_events),
                "timeout_events": len(timeout_events)
            }
        )
        
        # Phase 4: Validate timeout and circuit breaker behavior
        
        # Validate timeout handling
        timeout_accuracy = sum(1 for attempt in tool_execution_attempts if attempt["timeout_handled_correctly"]) / len(tool_execution_attempts)
        
        logger.info(f"Timeout Handling Results:")
        logger.info(f"  Timeout accuracy: {timeout_accuracy:.2%}")
        logger.info(f"  Timeout events: {len(timeout_events)}")
        
        assert timeout_accuracy >= 0.8, f"Timeout handling accuracy too low: {timeout_accuracy:.2%} (expected  >= 80%)"
        
        # Validate circuit breaker behavior
        circuit_opened = any(event["event"] == "circuit_opened" for event in circuit_breaker_events)
        fail_fast_triggered = any(event["event"] == "circuit_open_fail_fast" for event in circuit_breaker_events)
        circuit_recovery = any(event["event"] == "circuit_closed_after_success" for event in circuit_breaker_events)
        
        assert circuit_opened, "Circuit breaker should have opened after repeated failures"
        assert fail_fast_triggered, "Circuit breaker should have triggered fail-fast behavior"
        
        logger.info(f"Circuit Breaker Results:")
        logger.info(f"  Circuit opened: {circuit_opened}")
        logger.info(f"  Fail-fast triggered: {fail_fast_triggered}")
        logger.info(f"  Recovery attempted: {circuit_recovery}")
        
        # Validate circuit breaker reduced unnecessary attempts
        attempts_after_opening = [r for r in circuit_breaker_results 
                                if r.get("circuit_breaker_triggered", False)]
        
        assert len(attempts_after_opening) >= 2, f"Circuit breaker should have prevented multiple attempts: {len(attempts_after_opening)}"
        
        # Validate WebSocket events for timeout and circuit breaker
        timeout_websocket_events = [e for e in websocket_events if "timeout" in e.get("type", "").lower()]
        circuit_websocket_events = [e for e in websocket_events if "circuit" in e.get("type", "").lower()]
        
        logger.info(f"WebSocket Events: {len(timeout_websocket_events)} timeout events, {len(circuit_websocket_events)} circuit events")
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 90.0, f"Timeout/circuit breaker test should complete in <90s, took {execution_time:.2f}s"
        
        # Validate that circuit breaker prevented excessive execution time
        total_attempts = len(circuit_breaker_results)
        if total_attempts > circuit_breaker_threshold:
            # With circuit breaker, we should have saved time by failing fast
            estimated_time_without_circuit_breaker = total_attempts * 2.0  # 2s timeout per attempt
            time_saved_ratio = (estimated_time_without_circuit_breaker - execution_time) / estimated_time_without_circuit_breaker
            
            assert time_saved_ratio >= 0.2, f"Circuit breaker should have saved time: {time_saved_ratio:.2%} time saved (expected  >= 20%)"
        
        logger.info(f"Tool timeout and circuit breaker test completed in {execution_time:.2f}s with {timeout_accuracy:.2%} timeout accuracy")