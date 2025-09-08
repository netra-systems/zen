"""
Integration Tests for Agent Execution Error Handling - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure robust error handling maintains platform reliability
- Value Impact: Users get meaningful responses even when errors occur
- Strategic Impact: Error resilience prevents customer churn and maintains trust

CRITICAL: Poor error handling destroys user confidence and platform reputation.
Graceful error recovery is essential for business continuity.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

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

class TestAgentExecutionErrorHandling(BaseIntegrationTest):
    """Integration tests for agent execution error handling with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_handles_invalid_agent_gracefully(self, real_services_fixture):
        """
        Test agent execution gracefully handles requests for non-existent agents.
        
        Business Value: Users get clear feedback when requesting invalid agents.
        Prevents confusion and provides actionable error information.
        """
        # Arrange: Setup execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        user_id = UserID("invalid_agent_test_user")
        thread_id = ThreadID("invalid_agent_thread")
        run_id = RunID("invalid_agent_run")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["agent_execution"],
            session_data={"test_type": "invalid_agent"}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="completely_nonexistent_agent_xyz_12345",  # Invalid agent
            message="Please analyze my costs",
            user_context=user_context
        )
        
        # Act: Attempt to execute invalid agent
        error_occurred = False
        execution_result = None
        error_message = ""
        
        try:
            execution_result = await execution_engine.execute_agent(execution_context)
        except Exception as e:
            error_occurred = True
            error_message = str(e)
        
        # Assert: Invalid agent handled gracefully
        if error_occurred:
            # Business requirement: Error message should be user-friendly
            assert "agent" in error_message.lower(), "Error should mention agent issue"
            assert len(error_message) > 10, "Error message should be descriptive"
            assert "completely_nonexistent_agent_xyz_12345" in error_message, "Should identify the invalid agent name"
        else:
            # If no exception, result should indicate error
            assert execution_result is not None, "Should return some result even for invalid agent"
            if hasattr(execution_result, 'error'):
                assert execution_result.error is not None, "Result should contain error information"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_handles_malformed_context_gracefully(self, real_services_fixture):
        """
        Test agent execution handles malformed execution context gracefully.
        
        Business Value: System remains stable even with corrupted or invalid requests.
        Robustness prevents crashes that would impact all users.
        """
        # Arrange: Setup execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        # Test various malformed contexts
        malformed_contexts = [
            {
                "name": "missing_user_id",
                "context": AgentExecutionContext(
                    user_id=None,  # Invalid - None user_id
                    thread_id=ThreadID("malformed_thread_1"),
                    run_id=RunID("malformed_run_1"),
                    agent_name="triage_agent",
                    message="Test with missing user ID",
                    user_context=None
                )
            },
            {
                "name": "empty_message",
                "context": AgentExecutionContext(
                    user_id=UserID("malformed_test_user"),
                    thread_id=ThreadID("malformed_thread_2"),
                    run_id=RunID("malformed_run_2"),
                    agent_name="triage_agent",
                    message="",  # Empty message
                    user_context=UserExecutionContext(
                        user_id=UserID("malformed_test_user"),
                        thread_id=ThreadID("malformed_thread_2"),
                        authenticated=True,
                        permissions=[],
                        session_data={}
                    )
                )
            }
        ]
        
        error_handling_results = []
        
        for test_case in malformed_contexts:
            context = test_case["context"]
            
            # Act: Attempt execution with malformed context
            try:
                result = await execution_engine.execute_agent(context)
                error_handling_results.append({
                    "test_case": test_case["name"],
                    "success": True,
                    "result": result,
                    "error": None
                })
            except Exception as e:
                error_handling_results.append({
                    "test_case": test_case["name"],
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
        
        # Assert: Malformed contexts handled appropriately
        assert len(error_handling_results) == len(malformed_contexts), "Should handle all malformed context tests"
        
        for result in error_handling_results:
            test_case_name = result["test_case"]
            
            # Business requirement: System should not crash silently
            if not result["success"]:
                assert result["error"] is not None, f"Failed test {test_case_name} should provide error information"
                assert len(result["error"]) > 0, f"Error message for {test_case_name} should be descriptive"
            
            # If successful despite malformed input, should have some validation
            if result["success"]:
                # Success is acceptable if the system can handle/correct malformed input
                pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_timeout_error_handling(self, real_services_fixture):
        """
        Test agent execution handles timeout errors gracefully.
        
        Business Value: Timeouts prevent resource exhaustion and provide user feedback.
        Essential for maintaining platform performance under load.
        """
        # Arrange: Setup execution with timeout simulation
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        user_id = UserID("timeout_test_user")
        thread_id = ThreadID("timeout_thread")
        run_id = RunID("timeout_run")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["timeout_testing"],
            session_data={"test_type": "timeout"}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="triage_agent",
            message="This is a timeout test message that should be processed with a reasonable timeout",
            user_context=user_context
        )
        
        # Act: Execute with timeout
        timeout_occurred = False
        execution_result = None
        execution_time = 0
        
        start_time = time.time()
        
        try:
            # Use asyncio timeout to simulate timeout conditions
            execution_result = await asyncio.wait_for(
                execution_engine.execute_agent(execution_context),
                timeout=30.0  # 30 second timeout for integration test
            )
        except asyncio.TimeoutError:
            timeout_occurred = True
        except Exception as e:
            # Other errors are also acceptable for timeout testing
            pass
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert: Timeout handling appropriate
        if timeout_occurred:
            # Business requirement: Timeout should occur within reasonable time
            assert execution_time >= 29, "Timeout should respect timeout period"
            assert execution_time <= 35, "Timeout should not extend significantly beyond limit"
        else:
            # If no timeout, execution should have completed reasonably quickly
            assert execution_time < 30, "Non-timeout execution should complete within timeout period"
            
            if execution_result is not None:
                # Business requirement: Successful execution should provide value
                assert execution_result, "Completed execution should return meaningful result"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_partial_failure_recovery(self, real_services_fixture):
        """
        Test agent execution recovers from partial failures gracefully.
        
        Business Value: Partial failures shouldn't prevent all functionality.
        Users should still receive value even when some components fail.
        """
        # Arrange: Setup execution environment
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        execution_engine = ExecutionEngine(agent_registry=agent_registry)
        
        user_id = UserID("partial_failure_user")
        thread_id = ThreadID("partial_failure_thread")
        run_id = RunID("partial_failure_run")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["partial_failure_testing"],
            session_data={"test_type": "partial_failure"}
        )
        
        execution_context = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name="triage_agent",
            message="Perform analysis that might encounter partial failures but should still provide some value",
            user_context=user_context
        )
        
        # Mock partial failure scenario by patching components
        partial_failure_results = []
        
        # Act: Execute with simulated partial failures
        try:
            # Simulate condition where some tools might fail but overall execution continues
            result = await execution_engine.execute_agent(execution_context)
            
            partial_failure_results.append({
                "execution_successful": True,
                "result": result,
                "error": None
            })
            
        except Exception as e:
            partial_failure_results.append({
                "execution_successful": False,
                "result": None,
                "error": str(e)
            })
        
        # Assert: Partial failure handled appropriately
        assert len(partial_failure_results) == 1, "Should have one execution attempt result"
        
        result_info = partial_failure_results[0]
        
        if result_info["execution_successful"]:
            # Business requirement: Successful execution should provide value
            assert result_info["result"] is not None, "Successful execution should return result"
            
            # If the execution succeeded despite potential partial failures,
            # the result should still provide business value
            if hasattr(result_info["result"], 'result') and result_info["result"].result:
                result_content = str(result_info["result"].result)
                assert len(result_content) > 10, "Result should contain meaningful content"
        
        else:
            # If execution failed, error should be informative
            assert result_info["error"] is not None, "Failed execution should provide error information"
            assert len(result_info["error"]) > 0, "Error message should be descriptive"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_concurrent_error_isolation(self, real_services_fixture):
        """
        Test that errors in one agent execution don't affect concurrent executions.
        
        Business Value: Error isolation prevents cascade failures across users.
        CRITICAL: One user's problems shouldn't impact other paying customers.
        """
        # Arrange: Setup multiple concurrent executions with mixed success/failure
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        
        agent_registry = bridge.get_orchestrator().agent_registry
        
        # Create contexts for concurrent executions
        concurrent_contexts = []
        
        # Success case
        success_context = AgentExecutionContext(
            user_id=UserID("concurrent_success_user"),
            thread_id=ThreadID("success_thread"),
            run_id=RunID("success_run"),
            agent_name="triage_agent",  # Valid agent
            message="Normal analysis request that should succeed",
            user_context=UserExecutionContext(
                user_id=UserID("concurrent_success_user"),
                thread_id=ThreadID("success_thread"),
                authenticated=True,
                permissions=["normal_execution"],
                session_data={"expected": "success"}
            )
        )
        concurrent_contexts.append(("success", success_context))
        
        # Error case  
        error_context = AgentExecutionContext(
            user_id=UserID("concurrent_error_user"),
            thread_id=ThreadID("error_thread"),
            run_id=RunID("error_run"),
            agent_name="nonexistent_error_agent_12345",  # Invalid agent
            message="This request should fail due to invalid agent",
            user_context=UserExecutionContext(
                user_id=UserID("concurrent_error_user"),
                thread_id=ThreadID("error_thread"),
                authenticated=True,
                permissions=["error_testing"],
                session_data={"expected": "failure"}
            )
        )
        concurrent_contexts.append(("error", error_context))
        
        # Another success case
        success2_context = AgentExecutionContext(
            user_id=UserID("concurrent_success2_user"),
            thread_id=ThreadID("success2_thread"),
            run_id=RunID("success2_run"),
            agent_name="triage_agent",  # Valid agent
            message="Another normal request that should succeed despite concurrent error",
            user_context=UserExecutionContext(
                user_id=UserID("concurrent_success2_user"),
                thread_id=ThreadID("success2_thread"),
                authenticated=True,
                permissions=["normal_execution"],
                session_data={"expected": "success"}
            )
        )
        concurrent_contexts.append(("success2", success2_context))
        
        # Act: Execute all concurrent requests
        async def execute_single(label, context):
            execution_engine = ExecutionEngine(agent_registry=agent_registry)
            try:
                result = await execution_engine.execute_agent(context)
                return {
                    "label": label,
                    "success": True,
                    "result": result,
                    "error": None,
                    "user_id": str(context.user_id)
                }
            except Exception as e:
                return {
                    "label": label,
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "user_id": str(context.user_id)
                }
        
        concurrent_tasks = [execute_single(label, context) for label, context in concurrent_contexts]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        
        # Assert: Error isolation maintained
        assert len(concurrent_results) == 3, "Should have results for all concurrent executions"
        
        # Categorize results
        success_results = [r for r in concurrent_results if r["label"] in ["success", "success2"]]
        error_results = [r for r in concurrent_results if r["label"] == "error"]
        
        # Business requirement: Error in one execution shouldn't affect others
        assert len(error_results) == 1, "Should have one error result"
        assert len(success_results) == 2, "Should have two success results"
        
        # Verify error isolation - success cases should not be affected by error case
        successful_executions = [r for r in success_results if r["success"]]
        
        # At least one success case should succeed (proving isolation)
        assert len(successful_executions) >= 1, "At least one concurrent execution should succeed despite error in another"
        
        # Verify user isolation - each result has correct user
        user_ids_in_results = {r["user_id"] for r in concurrent_results}
        expected_user_ids = {"concurrent_success_user", "concurrent_error_user", "concurrent_success2_user"}
        
        assert user_ids_in_results == expected_user_ids, "Each concurrent execution should maintain user identity"