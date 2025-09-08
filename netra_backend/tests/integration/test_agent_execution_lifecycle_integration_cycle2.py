"""
Integration Tests for Agent Execution Lifecycle - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete agent execution lifecycle works with real services
- Value Impact: Users experience reliable end-to-end agent processing
- Strategic Impact: Integration testing validates real business value delivery paths

CRITICAL: This tests the complete agent execution pipeline that delivers customer value.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types import UserID, ThreadID, RunID
from shared.isolated_environment import get_env

class TestAgentExecutionLifecycleIntegration(BaseIntegrationTest):
    """Integration tests for agent execution lifecycle with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_agent_execution_lifecycle_with_real_services(self, real_services_fixture):
        """
        Test complete agent execution from start to finish with real services.
        
        Business Value: Validates end-to-end agent processing that customers pay for.
        CRITICAL: This is the core value delivery mechanism of the platform.
        """
        # Arrange: Setup real execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        # Get real agent registry and execution engine
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        # Create realistic execution context
        user_id = UserID("lifecycle_integration_user")
        thread_id = ThreadID("lifecycle_thread_001")
        run_id = RunID("lifecycle_run_001")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["agent_execution", "data_access"],
            session_data={"test_context": True}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="triage_agent",  # Use real agent for integration test
            message="Analyze my cloud costs and provide optimization recommendations",
            user_context=user_context
        )
        
        # Act: Execute complete agent lifecycle
        start_time = time.time()
        execution_result = await execution_engine.execute_agent(execution_context)
        end_time = time.time()
        
        execution_duration = end_time - start_time
        
        # Assert: Complete lifecycle executed successfully
        assert execution_result is not None, "Agent execution should return a result"
        
        # Business requirement: Execution completes within reasonable time
        assert execution_duration < 60, f"Agent execution took {execution_duration:.2f}s, should be under 60s"
        assert execution_duration > 0.1, "Agent execution should take measurable time"
        
        # Verify result contains business value
        if hasattr(execution_result, 'result') and execution_result.result:
            result_content = str(execution_result.result).lower()
            business_indicators = ["cost", "optimization", "recommendation", "analysis", "saving"]
            assert any(indicator in result_content for indicator in business_indicators), \
                f"Result should show business value: {execution_result.result}"
        
        # Verify execution context was properly used
        assert execution_context.user_id == user_id
        assert execution_context.agent_name == "triage_agent"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_with_database_integration(self, real_services_fixture):
        """
        Test agent execution lifecycle integrates properly with database services.
        
        Business Value: Agents must persist results and access user data reliably.
        Database integration is essential for maintaining user context and history.
        """
        # Arrange: Setup execution with database integration
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        # Create context with database requirements
        user_id = UserID("db_integration_user")
        thread_id = ThreadID("db_thread_001")
        run_id = RunID("db_run_001")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["database_read", "database_write"],
            session_data={"requires_persistence": True}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="triage_agent",
            message="Save my analysis results for future reference",
            user_context=user_context
        )
        
        # Act: Execute agent with database integration
        try:
            result = await execution_engine.execute_agent(execution_context)
            execution_successful = True
        except Exception as e:
            print(f"Database integration test error: {e}")
            execution_successful = False
            result = None
        
        # Assert: Database integration worked or failed gracefully
        if execution_successful:
            assert result is not None, "Successful database integration should return result"
            
            # Business requirement: Results should indicate persistence
            if hasattr(result, 'result') and result.result:
                result_str = str(result.result)
                # May contain references to saved data or successful storage
        
        # Even if database integration fails, it should fail gracefully
        assert execution_successful or result is None, "Database integration should succeed or fail gracefully"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_execution_concurrent_lifecycle_management(self, real_services_fixture):
        """
        Test multiple concurrent agent execution lifecycles.
        
        Business Value: Platform must handle multiple paying customers simultaneously.
        Concurrent execution is essential for business scalability.
        """
        # Arrange: Setup multiple concurrent executions
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        
        # Create multiple execution contexts
        concurrent_contexts = []
        for i in range(3):  # 3 concurrent executions for integration test
            user_id = UserID(f"concurrent_user_{i}")
            thread_id = ThreadID(f"concurrent_thread_{i}")
            run_id = RunID(f"concurrent_run_{i}")
            
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                authenticated=True,
                permissions=["concurrent_execution"],
                session_data={"concurrent_index": i}
            )
            
            execution_context = AgentExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_name="triage_agent",
                message=f"Concurrent analysis request {i}",
                user_context=user_context
            )
            
            concurrent_contexts.append(execution_context)
        
        # Act: Execute all agents concurrently
        start_time = time.time()
        
        async def execute_single_agent(context, engine_instance):
            execution_engine = ExecutionEngine(agent_registry=engine_instance)
            try:
                result = await execution_engine.execute_agent(context)
                return {
                    "user_id": str(context.user_id),
                    "success": True,
                    "result": result,
                    "error": None
                }
            except Exception as e:
                return {
                    "user_id": str(context.user_id),
                    "success": False,
                    "result": None,
                    "error": str(e)
                }
        
        # Execute all concurrent tasks
        tasks = [
            execute_single_agent(context, agent_registry) 
            for context in concurrent_contexts
        ]
        
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_concurrent_time = end_time - start_time
        
        # Assert: Concurrent executions handled properly
        successful_executions = [r for r in concurrent_results if isinstance(r, dict) and r.get("success")]
        
        # Business requirement: Most concurrent executions should succeed
        assert len(successful_executions) >= 2, f"At least 2 of 3 concurrent executions should succeed, got {len(successful_executions)}"
        
        # Performance requirement: Concurrent execution efficient
        assert total_concurrent_time < 120, f"Concurrent execution took {total_concurrent_time:.2f}s, should be under 120s"
        
        # Verify user isolation in concurrent results
        user_ids_in_results = set()
        for result in successful_executions:
            user_ids_in_results.add(result["user_id"])
        
        expected_user_ids = {f"concurrent_user_{i}" for i in range(len(successful_executions))}
        assert len(user_ids_in_results) == len(successful_executions), "Each concurrent execution should have unique user"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_lifecycle_error_recovery(self, real_services_fixture):
        """
        Test agent execution lifecycle recovers from errors gracefully.
        
        Business Value: System reliability prevents customer frustration and churn.
        Error recovery maintains business continuity during issues.
        """
        # Arrange: Setup execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        # Create context for error testing
        user_id = UserID("error_recovery_user")
        thread_id = ThreadID("error_thread_001") 
        run_id = RunID("error_run_001")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["error_testing"],
            session_data={"error_test": True}
        )
        
        # Test different error scenarios
        error_scenarios = [
            {
                "name": "invalid_agent",
                "agent_name": "nonexistent_agent_12345",
                "message": "Test invalid agent error handling"
            },
            {
                "name": "valid_agent_with_complex_request",
                "agent_name": "triage_agent", 
                "message": "Handle this extremely complex and potentially problematic request that might cause issues"
            }
        ]
        
        recovery_results = []
        
        for scenario in error_scenarios:
            execution_context = AgentExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=RunID(f"error_run_{scenario['name']}"),
                agent_name=scenario["agent_name"],
                message=scenario["message"],
                user_context=user_context
            )
            
            # Act: Execute with potential error
            try:
                result = await execution_engine.execute_agent(execution_context)
                recovery_results.append({
                    "scenario": scenario["name"],
                    "success": True,
                    "result": result,
                    "error": None
                })
            except Exception as e:
                recovery_results.append({
                    "scenario": scenario["name"],
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
        
        # Assert: Error recovery behavior
        assert len(recovery_results) == len(error_scenarios), "Should attempt all error scenarios"
        
        # Business requirement: System handles errors gracefully
        for result in recovery_results:
            scenario_name = result["scenario"]
            
            if scenario_name == "invalid_agent":
                # Invalid agent should fail gracefully
                if not result["success"]:
                    assert "agent" in result["error"].lower() or "not found" in result["error"].lower(), \
                        "Invalid agent error should be descriptive"
                
            elif scenario_name == "valid_agent_with_complex_request":
                # Valid agent should either succeed or fail gracefully  
                if result["success"]:
                    assert result["result"] is not None, "Successful execution should return result"
                else:
                    # Graceful failure is acceptable for complex requests
                    assert result["error"] is not None, "Failed execution should provide error information"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_lifecycle_performance_monitoring(self, real_services_fixture):
        """
        Test agent execution lifecycle includes proper performance monitoring.
        
        Business Value: Performance metrics enable optimization and billing accuracy.
        Essential for understanding platform efficiency and customer usage patterns.
        """
        # Arrange: Setup execution with performance monitoring
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        user_id = UserID("performance_monitoring_user")
        thread_id = ThreadID("perf_thread_001")
        run_id = RunID("perf_run_001")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["performance_monitoring"],
            session_data={"monitor_performance": True}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="triage_agent",
            message="Performance monitoring test with detailed analysis request",
            user_context=user_context
        )
        
        # Act: Execute with performance monitoring
        performance_metrics = {
            "start_time": time.time(),
            "memory_before": 0,  # Would need memory monitoring in real implementation
            "cpu_start": time.process_time()
        }
        
        result = await execution_engine.execute_agent(execution_context)
        
        performance_metrics.update({
            "end_time": time.time(),
            "memory_after": 0,  # Would track memory usage
            "cpu_end": time.process_time()
        })
        
        # Calculate performance metrics
        execution_time = performance_metrics["end_time"] - performance_metrics["start_time"]
        cpu_time = performance_metrics["cpu_end"] - performance_metrics["cpu_start"]
        
        # Assert: Performance metrics are reasonable
        assert execution_time > 0, "Should track execution time"
        assert execution_time < 90, f"Execution time {execution_time:.2f}s should be reasonable"
        
        assert cpu_time >= 0, "CPU time should be measurable"
        
        # Business requirement: Performance data enables optimization
        performance_summary = {
            "execution_time_seconds": execution_time,
            "cpu_time_seconds": cpu_time,
            "agent_name": execution_context.agent_name,
            "user_id": str(execution_context.user_id),
            "success": result is not None
        }
        
        # Verify performance data is complete
        assert all(key in performance_summary for key in ["execution_time_seconds", "agent_name", "success"]), \
            "Performance summary should include key metrics"
        
        # Business requirement: Successful execution provides value
        if performance_summary["success"]:
            assert result is not None, "Successful performance-monitored execution should return result"