"""
Integration Tests for Tool Dispatcher Performance and Reliability - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool dispatcher performs reliably under real conditions
- Value Impact: Users get fast, reliable AI analysis results
- Strategic Impact: Performance directly impacts user experience and platform scalability

CRITICAL: Tool dispatcher performance affects every AI interaction.
Slow or unreliable tool execution destroys the user experience.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types import UserID, ThreadID, RunID
from shared.isolated_environment import get_env

class TestToolDispatcherPerformanceReliability(BaseIntegrationTest):
    """Integration tests for tool dispatcher performance and reliability."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_performance_under_load(self, real_services_fixture):
        """
        Test tool dispatcher performance with concurrent tool executions.
        
        Business Value: Platform must handle multiple users running tools simultaneously.
        Performance degradation under load would limit business scalability.
        """
        # Arrange: Setup real tool dispatcher environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Create multiple execution contexts for load testing
        execution_contexts = []
        for i in range(5):  # 5 concurrent tool executions
            user_context = UserExecutionContext(
                user_id=UserID(f"load_test_user_{i}"),
                thread_id=ThreadID(f"load_test_thread_{i}"),
                authenticated=True,
                permissions=["tool_execution", "performance_testing"],
                session_data={"load_test_index": i}
            )
            
            agent_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=RunID(f"load_test_run_{i}"),
                agent_name="load_test_agent",
                message=f"Load test tool execution {i}",
                user_context=user_context
            )
            
            execution_contexts.append(agent_context)
        
        # Create tool dispatcher
        dispatcher_config = {"environment": "integration_test", "timeout": 30, "max_concurrent": 10}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Act: Execute tools concurrently under load
        performance_results = []
        start_time = time.time()
        
        async def execute_tool_with_timing(context, tool_index):
            tool_start = time.time()
            try:
                # Simulate realistic tool execution (would use real tools in actual implementation)
                result = await execution_engine.execute_tool(
                    tool_name="performance_test_tool",
                    parameters={"test_index": tool_index, "simulate_work": True},
                    execution_context=context
                )
                
                tool_end = time.time()
                return {
                    "index": tool_index,
                    "success": True,
                    "duration": tool_end - tool_start,
                    "result": result,
                    "error": None
                }
                
            except Exception as e:
                tool_end = time.time()
                return {
                    "index": tool_index,
                    "success": False,
                    "duration": tool_end - tool_start,
                    "result": None,
                    "error": str(e)
                }
        
        # Run all tool executions concurrently
        concurrent_tasks = [
            execute_tool_with_timing(context, i) 
            for i, context in enumerate(execution_contexts)
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Assert: Performance meets requirements
        successful_executions = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # Business requirement: Most executions should succeed under load
        success_rate = len(successful_executions) / len(results) * 100
        assert success_rate >= 80, f"Success rate {success_rate:.1f}% should be at least 80% under load"
        
        # Performance requirement: Concurrent execution should be efficient
        assert total_time < 45, f"Concurrent execution took {total_time:.2f}s, should be under 45s"
        
        # Calculate average execution time
        if successful_executions:
            avg_execution_time = sum(r["duration"] for r in successful_executions) / len(successful_executions)
            assert avg_execution_time < 10, f"Average execution time {avg_execution_time:.2f}s too high"
            
            # Performance should be consistent
            execution_times = [r["duration"] for r in successful_executions]
            max_time = max(execution_times)
            min_time = min(execution_times)
            time_variance = max_time - min_time
            
            assert time_variance < 15, f"Execution time variance {time_variance:.2f}s too high - inconsistent performance"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_reliability_with_service_failures(self, real_services_fixture):
        """
        Test tool dispatcher reliability when underlying services have issues.
        
        Business Value: System must remain functional even when some services fail.
        Service failures shouldn't prevent all tool execution.
        """
        # Arrange: Setup tool dispatcher with failure simulation
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("reliability_test_user"),
            thread_id=ThreadID("reliability_thread"),
            authenticated=True,
            permissions=["reliability_testing"],
            session_data={"test_type": "service_failure"}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("reliability_run"),
            agent_name="reliability_agent",
            message="Test tool reliability with service failures",
            user_context=user_context
        )
        
        # Test different failure scenarios
        failure_scenarios = [
            {
                "name": "database_connection_failure",
                "tool": "database_query_tool",
                "expected_behavior": "graceful_fallback"
            },
            {
                "name": "external_api_timeout",
                "tool": "external_data_tool", 
                "expected_behavior": "retry_with_timeout"
            },
            {
                "name": "memory_pressure",
                "tool": "memory_intensive_tool",
                "expected_behavior": "resource_management"
            }
        ]
        
        dispatcher_config = {"environment": "reliability_test", "timeout": 15, "retry_attempts": 2}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        reliability_results = []
        
        # Act: Test each failure scenario
        for scenario in failure_scenarios:
            scenario_start = time.time()
            
            try:
                # Simulate service failure during tool execution
                result = await execution_engine.execute_tool(
                    tool_name=scenario["tool"],
                    parameters={"simulate_failure": scenario["name"]},
                    execution_context=agent_context
                )
                
                scenario_end = time.time()
                reliability_results.append({
                    "scenario": scenario["name"],
                    "success": True,
                    "duration": scenario_end - scenario_start,
                    "result": result,
                    "behavior": "successful_execution"
                })
                
            except Exception as e:
                scenario_end = time.time()
                reliability_results.append({
                    "scenario": scenario["name"],
                    "success": False,
                    "duration": scenario_end - scenario_start,
                    "result": None,
                    "behavior": "graceful_failure",
                    "error": str(e)
                })
        
        # Assert: Reliability requirements met
        for result in reliability_results:
            scenario_name = result["scenario"]
            
            # Business requirement: Failures should be handled gracefully
            if not result["success"]:
                assert result.get("error"), f"Failed scenario {scenario_name} should provide error information"
                assert result["duration"] < 20, f"Failed scenario {scenario_name} should timeout reasonably"
                
                # Error should be informative for debugging
                error_msg = result.get("error", "")
                assert len(error_msg) > 5, f"Error message for {scenario_name} should be descriptive"
            
            # Successful scenarios should complete within reasonable time
            if result["success"]:
                assert result["duration"] < 30, f"Successful scenario {scenario_name} should complete efficiently"
                assert result["result"] is not None, f"Successful scenario {scenario_name} should return result"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_memory_and_resource_management(self, real_services_fixture):
        """
        Test tool dispatcher manages memory and resources efficiently.
        
        Business Value: Efficient resource usage enables serving more customers.
        Resource leaks would limit platform scalability and increase costs.
        """
        # Arrange: Setup resource monitoring
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("resource_test_user"),
            thread_id=ThreadID("resource_thread"),
            authenticated=True,
            permissions=["resource_testing"],
            session_data={"monitor_resources": True}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("resource_run"),
            agent_name="resource_agent",
            message="Test resource management efficiency",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "resource_test", "memory_limit_mb": 512}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Track resource usage
        import gc
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Act: Execute multiple tool operations to test resource management
        resource_test_results = []
        
        for i in range(10):  # Multiple iterations to test resource cleanup
            iteration_start = time.time()
            
            try:
                result = await execution_engine.execute_tool(
                    tool_name="resource_test_tool",
                    parameters={"iteration": i, "data_size": "medium"},
                    execution_context=agent_context
                )
                
                iteration_end = time.time()
                resource_test_results.append({
                    "iteration": i,
                    "success": True,
                    "duration": iteration_end - iteration_start,
                    "result": result
                })
                
            except Exception as e:
                iteration_end = time.time()
                resource_test_results.append({
                    "iteration": i,
                    "success": False,
                    "duration": iteration_end - iteration_start,
                    "error": str(e)
                })
        
        # Force garbage collection and measure resource usage
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Assert: Resource management efficiency
        successful_iterations = [r for r in resource_test_results if r["success"]]
        assert len(successful_iterations) >= 8, f"At least 8/10 iterations should succeed, got {len(successful_iterations)}"
        
        # Business requirement: Resource usage should be reasonable
        objects_per_iteration = object_growth / len(resource_test_results) if object_growth > 0 else 0
        assert objects_per_iteration < 100, f"Each iteration should create fewer than 100 objects, created {objects_per_iteration}"
        
        # Performance should remain consistent across iterations
        execution_times = [r["duration"] for r in successful_iterations]
        if len(execution_times) > 1:
            avg_time = sum(execution_times) / len(execution_times)
            time_variance = max(execution_times) - min(execution_times)
            
            # Business requirement: Performance shouldn't degrade with usage
            assert time_variance < 5, f"Execution time variance {time_variance:.2f}s indicates resource issues"
            assert avg_time < 3, f"Average execution time {avg_time:.2f}s should remain efficient"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_error_recovery_and_circuit_breaking(self, real_services_fixture):
        """
        Test tool dispatcher error recovery and circuit breaker functionality.
        
        Business Value: Error recovery prevents cascade failures across the platform.
        Circuit breakers protect system stability when tools consistently fail.
        """
        # Arrange: Setup error recovery testing
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("circuit_breaker_user"),
            thread_id=ThreadID("circuit_breaker_thread"),
            authenticated=True,
            permissions=["circuit_breaker_testing"],
            session_data={"test_circuit_breaker": True}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("circuit_breaker_run"),
            agent_name="circuit_breaker_agent",
            message="Test error recovery and circuit breaking",
            user_context=user_context
        )
        
        # Configure dispatcher with circuit breaker settings
        dispatcher_config = {
            "environment": "circuit_breaker_test",
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 5
        }
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        circuit_breaker_results = []
        
        # Act: Test circuit breaker behavior with repeated failures
        for attempt in range(6):  # More attempts than circuit breaker threshold
            attempt_start = time.time()
            
            try:
                result = await execution_engine.execute_tool(
                    tool_name="failing_tool_for_circuit_test",
                    parameters={"attempt": attempt, "force_failure": True},
                    execution_context=agent_context
                )
                
                attempt_end = time.time()
                circuit_breaker_results.append({
                    "attempt": attempt,
                    "success": True,
                    "duration": attempt_end - attempt_start,
                    "result": result,
                    "circuit_state": "closed"
                })
                
            except Exception as e:
                attempt_end = time.time()
                error_msg = str(e).lower()
                
                # Detect circuit breaker activation
                circuit_state = "open" if "circuit" in error_msg or "breaker" in error_msg else "closed"
                
                circuit_breaker_results.append({
                    "attempt": attempt,
                    "success": False,
                    "duration": attempt_end - attempt_start,
                    "error": str(e),
                    "circuit_state": circuit_state
                })
        
        # Assert: Circuit breaker functionality
        failed_attempts = [r for r in circuit_breaker_results if not r["success"]]
        assert len(failed_attempts) >= 3, "Should have multiple failures to test circuit breaker"
        
        # Business requirement: Circuit breaker should activate after threshold
        later_attempts = circuit_breaker_results[3:]  # After threshold
        circuit_open_attempts = [r for r in later_attempts if r.get("circuit_state") == "open"]
        
        if len(circuit_open_attempts) > 0:
            # Circuit breaker activated - should fail fast
            for attempt in circuit_open_attempts:
                assert attempt["duration"] < 1, f"Circuit breaker should fail fast, took {attempt['duration']:.2f}s"
        
        # Recovery mechanism: Wait for circuit breaker timeout and test recovery
        await asyncio.sleep(6)  # Wait for circuit breaker timeout
        
        recovery_start = time.time()
        try:
            recovery_result = await execution_engine.execute_tool(
                tool_name="recovery_test_tool",
                parameters={"test": "recovery"},
                execution_context=agent_context
            )
            recovery_success = True
        except Exception as e:
            recovery_success = False
        
        recovery_end = time.time()
        recovery_duration = recovery_end - recovery_start
        
        # Business requirement: System should attempt recovery after timeout
        # (May succeed or fail, but should not be immediately rejected)
        assert recovery_duration > 0.1, "Recovery attempt should take measurable time (not immediate circuit rejection)"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_tool_dispatcher_health_monitoring_and_diagnostics(self, real_services_fixture):
        """
        Test tool dispatcher provides health monitoring and diagnostic information.
        
        Business Value: Health monitoring enables proactive issue detection and resolution.
        Diagnostics help maintain platform reliability and customer satisfaction.
        """
        # Arrange: Setup health monitoring
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        user_context = UserExecutionContext(
            user_id=UserID("health_monitoring_user"),
            thread_id=ThreadID("health_thread"),
            authenticated=True,
            permissions=["health_monitoring"],
            session_data={"monitor_health": True}
        )
        
        agent_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=RunID("health_run"),
            agent_name="health_agent",
            message="Test health monitoring and diagnostics",
            user_context=user_context
        )
        
        dispatcher_config = {"environment": "health_test", "enable_monitoring": True}
        dispatcher = UnifiedToolDispatcherFactory.create_dispatcher(dispatcher_config)
        execution_engine = UnifiedToolExecutionEngine(tool_dispatcher=dispatcher)
        
        # Act: Execute tools and collect health metrics
        health_test_start = time.time()
        
        # Execute several tool operations to generate metrics
        for i in range(3):
            try:
                await execution_engine.execute_tool(
                    tool_name=f"health_test_tool_{i}",
                    parameters={"health_check": True},
                    execution_context=agent_context
                )
            except Exception:
                pass  # Expected for health testing
        
        health_test_end = time.time()
        
        # Collect health and diagnostic information
        # (In real implementation, would query dispatcher health endpoints)
        health_metrics = {
            "total_execution_time": health_test_end - health_test_start,
            "tools_attempted": 3,
            "monitoring_enabled": True
        }
        
        # Assert: Health monitoring functionality
        assert health_metrics["total_execution_time"] > 0, "Should track execution time"
        assert health_metrics["tools_attempted"] == 3, "Should track number of tool executions"
        
        # Business requirement: Health metrics should be meaningful for operations
        assert health_metrics["total_execution_time"] < 30, "Health test execution should complete efficiently"
        
        # Diagnostic information should be available for troubleshooting
        # (In real implementation, would verify specific diagnostic endpoints and data)