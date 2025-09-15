"""
Targeted test for timeout configuration bug reproduction (FIXED VERSION).

PURPOSE: Reproduce the specific timeout configuration issue with empty error messages identified in issue #276.

EXPECTED BEHAVIOR:
- Test should FAIL when timeout configuration produces empty or invalid error messages
- Demonstrates the issue where timeout handling doesn't provide meaningful error context
- Shows the exact scenarios where timeout error messages are missing or unclear

BUG TO REPRODUCE:
- Timeout configuration not properly setting error messages
- Empty error messages when timeout occurs
- Timeout configuration not being applied consistently across different execution paths
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker,
    ExecutionState,
    TimeoutConfig,
    CircuitBreakerOpenError
)
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore


class TestTimeoutConfigurationIssues(SSotAsyncTestCase):
    """Test to reproduce timeout configuration bugs."""
    
    def setup_method(self, method=None):
        """Setup test with timeout configurations."""
        super().setup_method(method)
        self.tracker = AgentExecutionTracker()
        self.execution_id = None
        
        # Mock registry and websocket bridge for AgentExecutionCore
        self.mock_registry = Mock()
        self.mock_websocket_bridge = Mock()
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    def test_timeout_config_empty_error_message_bug(self):
        """
        Test that reproduces the empty error message bug in timeout configuration.
        
        EXPECTED RESULT: This test should FAIL when timeout produces empty error message.
        This demonstrates the bug where timeout handling doesn't provide meaningful error context.
        """
        # Create a timeout configuration with very short timeout
        timeout_config = TimeoutConfig(
            agent_execution_timeout=0.1,  # 100ms timeout
            llm_api_timeout=0.05,  # 50ms API timeout
            failure_threshold=1,
            recovery_timeout=1.0
        )
        
        # Create execution with timeout config
        self.execution_id = self.tracker.create_execution_with_full_context(
            agent_name="test_agent",
            user_context={
                "user_id": "test_user",
                "thread_id": "test_thread"
            },
            timeout_config={
                "timeout_seconds": 0.1,
                "llm_timeout": 0.05
            }
        )
        
        # Start execution
        self.tracker.start_execution(self.execution_id)
        
        # Wait for timeout to occur
        time.sleep(0.2)  # Wait longer than timeout
        
        # Check for timeout detection
        dead_executions = self.tracker.detect_dead_executions()
        
        if dead_executions:
            execution = dead_executions[0]
            error_message = execution.error
            
            # BUG REPRODUCTION: Check if error message is empty or meaningless
            if not error_message or error_message.strip() == "":
                assert False, (
                    "BUG REPRODUCED: Timeout occurred but error message is empty. "
                    f"Execution ID: {execution.execution_id}, State: {execution.state}, "
                    f"Error: '{error_message}'. Timeout handling should provide meaningful error messages."
                )
            
            # Check if error message is too generic or unhelpful
            generic_messages = ["error", "timeout", "failed", "unknown"]
            if error_message and error_message.lower().strip() in generic_messages:
                assert False, (
                    f"BUG REPRODUCED: Timeout error message is too generic: '{error_message}'. "
                    "Timeout handling should provide specific context about what timed out and why."
                )
        else:
            # Timeout should have been detected
            record = self.tracker.get_execution(self.execution_id)
            if record and not record.is_timed_out():
                assert False, (
                    "BUG REPRODUCED: Timeout detection failed. "
                    f"Execution should have timed out after 0.1s but is still active. "
                    f"State: {record.state}, Duration: {record.duration}"
                )
    
    def test_timeout_config_inconsistent_application_bug(self):
        """
        Test that reproduces inconsistent timeout configuration application.
        
        This tests if timeout configs are properly applied across different execution paths.
        """
        # Create multiple executions with different timeout configs
        configs = [
            {"timeout_seconds": 0.1, "name": "fast_timeout"},
            {"timeout_seconds": 0.5, "name": "medium_timeout"},
            {"timeout_seconds": 1.0, "name": "slow_timeout"}
        ]
        
        execution_ids = []
        for config in configs:
            exec_id = self.tracker.create_execution_with_full_context(
                agent_name=f"agent_{config['name']}",
                user_context={
                    "user_id": "test_user",
                    "thread_id": f"thread_{config['name']}"
                },
                timeout_config=config
            )
            execution_ids.append((exec_id, config))
            self.tracker.start_execution(exec_id)
        
        # Wait for timeouts to occur
        time.sleep(1.2)  # Wait longer than all timeouts
        
        # Check timeout consistency
        timeout_results = []
        for exec_id, config in execution_ids:
            record = self.tracker.get_execution(exec_id)
            timeout_status = self.tracker.check_timeout(exec_id)
            
            expected_timeout = config["timeout_seconds"]
            actual_timeout = record.timeout_seconds if record else None
            
            timeout_results.append({
                "execution_id": exec_id,
                "config_name": config["name"],
                "expected_timeout": expected_timeout,
                "actual_timeout": actual_timeout,
                "is_timed_out": timeout_status["is_timed_out"] if timeout_status else None,
                "state": record.state.value if record else None,
                "error": record.error if record else None
            })
        
        # Validate timeout configuration consistency
        inconsistencies = []
        for result in timeout_results:
            if result["expected_timeout"] != result["actual_timeout"]:
                inconsistencies.append(
                    f"Execution {result['execution_id']}: expected timeout {result['expected_timeout']}s "
                    f"but got {result['actual_timeout']}s"
                )
            
            # Fast timeout should have timed out
            if result["config_name"] == "fast_timeout" and not result["is_timed_out"]:
                inconsistencies.append(
                    f"Fast timeout execution {result['execution_id']} should have timed out but didn't"
                )
            
            # Check error message quality for timed out executions
            if result["is_timed_out"] and result["error"]:
                if not str(result["expected_timeout"]) in result["error"]:
                    inconsistencies.append(
                        f"Timeout error for {result['execution_id']} doesn't mention expected timeout {result['expected_timeout']}s: '{result['error']}'"
                    )
        
        self.record_metric("timeout_results", timeout_results)
        
        if inconsistencies:
            assert False, (
                f"BUG REPRODUCED: Timeout configuration inconsistencies detected: {inconsistencies}. "
                "Timeout configurations should be applied consistently and produce meaningful error messages."
            )
    
    async def test_circuit_breaker_timeout_error_message_bug(self):
        """
        Test that reproduces circuit breaker timeout error message issues.
        
        This tests if circuit breaker timeouts produce meaningful error messages.
        """
        # Create execution with circuit breaker
        self.execution_id = self.tracker.create_execution_with_full_context(
            agent_name="circuit_breaker_test",
            user_context={
                "user_id": "test_user", 
                "thread_id": "test_thread"
            },
            timeout_config={
                "timeout_seconds": 0.1,
                "failure_threshold": 1,
                "recovery_timeout": 5.0
            }
        )
        
        # Register circuit breaker
        self.tracker.register_circuit_breaker(self.execution_id)
        
        # Simulate a function that will timeout
        async def timeout_function():
            await asyncio.sleep(0.2)  # Sleep longer than timeout
            return "should not reach here"
        
        # Execute with circuit breaker - this should timeout and open the circuit
        try:
            result = await self.tracker.execute_with_circuit_breaker(
                self.execution_id,
                timeout_function,
                "test_operation"
            )
            assert False, "Expected TimeoutError but function completed successfully"
        except TimeoutError as e:
            error_message = str(e)
            
            # BUG REPRODUCTION: Check circuit breaker timeout error message quality
            if not error_message or error_message.strip() == "":
                assert False, "BUG REPRODUCED: Circuit breaker timeout produced empty error message"
            
            # Check if error message has meaningful context
            required_elements = ["timeout", "test_operation"]
            missing_elements = []
            for element in required_elements:
                if element not in error_message.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                assert False, (
                    f"BUG REPRODUCED: Circuit breaker timeout error message lacks context: {missing_elements}. "
                    f"Error message: '{error_message}'. "
                    "Circuit breaker timeouts should include operation name and timeout information."
                )
        
        # Now try to call again - should get CircuitBreakerOpenError
        try:
            await self.tracker.execute_with_circuit_breaker(
                self.execution_id,
                timeout_function,
                "test_operation"
            )
            assert False, "Expected CircuitBreakerOpenError but function was allowed"
        except CircuitBreakerOpenError as e:
            error_message = str(e)
            
            # BUG REPRODUCTION: Check circuit breaker open error message
            if not error_message or error_message.strip() == "":
                assert False, "BUG REPRODUCED: Circuit breaker open error produced empty error message"
            
            # Check for circuit breaker specific context
            required_elements = ["circuit breaker", "open", "test_operation"]
            missing_elements = []
            for element in required_elements:
                if element.lower() not in error_message.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                assert False, (
                    f"BUG REPRODUCED: Circuit breaker open error message lacks context: {missing_elements}. "
                    f"Error message: '{error_message}'. "
                    "Circuit breaker open errors should clearly indicate the breaker is open and which operation is blocked."
                )
    
    def test_timeout_config_default_values_bug(self):
        """
        Test that reproduces issues with timeout configuration default values.
        
        This tests if default timeout values are reasonable and properly documented.
        """
        # Create execution without explicit timeout config
        self.execution_id = self.tracker.create_execution(
            agent_name="default_timeout_test",
            thread_id="test_thread",
            user_id="test_user"
        )
        
        record = self.tracker.get_execution(self.execution_id)
        default_timeout = record.timeout_seconds
        
        # Check if default timeout is reasonable
        if default_timeout <= 0:
            assert False, (
                f"BUG REPRODUCED: Default timeout is invalid: {default_timeout}s. "
                "Default timeout should be a positive value."
            )
        
        if default_timeout < 5:
            assert False, (
                f"BUG REPRODUCED: Default timeout is too short: {default_timeout}s. "
                "Default timeout should allow sufficient time for normal agent execution."
            )
        
        if default_timeout > 300:  # 5 minutes
            assert False, (
                f"BUG REPRODUCED: Default timeout is too long: {default_timeout}s. "
                "Default timeout should prevent runaway executions without being excessive."
            )
        
        # Test timeout config object defaults
        timeout_config = TimeoutConfig()
        
        config_issues = []
        if timeout_config.agent_execution_timeout <= 0:
            config_issues.append(f"agent_execution_timeout: {timeout_config.agent_execution_timeout}")
        if timeout_config.llm_api_timeout <= 0:
            config_issues.append(f"llm_api_timeout: {timeout_config.llm_api_timeout}")
        if timeout_config.failure_threshold <= 0:
            config_issues.append(f"failure_threshold: {timeout_config.failure_threshold}")
        if timeout_config.recovery_timeout <= 0:
            config_issues.append(f"recovery_timeout: {timeout_config.recovery_timeout}")
        
        if config_issues:
            assert False, (
                f"BUG REPRODUCED: TimeoutConfig has invalid default values: {config_issues}. "
                "All timeout configuration values should be positive."
            )
        
        # Test consistency between execution record and timeout config
        record = self.tracker.get_execution(self.execution_id)
        if record.timeout_config:
            config_timeout = record.timeout_config.agent_execution_timeout
            record_timeout = record.timeout_seconds
            
            if abs(config_timeout - record_timeout) > 0.1:  # Allow small floating point differences
                assert False, (
                    f"BUG REPRODUCED: Timeout configuration inconsistency. "
                    f"TimeoutConfig.agent_execution_timeout: {config_timeout}s, "
                    f"ExecutionRecord.timeout_seconds: {record_timeout}s. "
                    "These values should be consistent."
                )
    
    def teardown_method(self, method=None):
        """Clean up test execution."""
        if self.execution_id and hasattr(self, 'tracker'):
            try:
                record = self.tracker.get_execution(self.execution_id)
                if record and not record.is_terminal:
                    self.tracker.update_execution_state(
                        self.execution_id,
                        ExecutionState.CANCELLED,
                        error="Test cleanup"
                    )
            except Exception:
                pass  # Ignore cleanup errors
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test to reproduce the timeout configuration bug
    pytest.main([__file__, "-v", "-s"])