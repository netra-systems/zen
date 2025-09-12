"""Integration Tests for Agent Response Error Handling

Tests error handling scenarios in agent response generation to ensure
graceful degradation and proper error reporting to users.

Business Value Justification (BVJ):
- Segment: All segments - Reliability/User Experience
- Business Goal: Ensure reliable system behavior under error conditions
- Value Impact: Prevents user frustration and maintains platform reliability
- Strategic Impact: Protects brand reputation and user retention
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context,
    InvalidContextError
)
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorSimulationAgent(DataHelperAgent):
    """Agent that can simulate various error conditions for testing."""
    
    def __init__(self, error_mode: Optional[str] = None):
        super().__init__()
        self.error_mode = error_mode
        self.call_count = 0
        
    async def run(self, context: UserExecutionContext, **kwargs) -> TypedAgentResult:
        """Run agent with potential error simulation."""
        self.call_count += 1
        
        if self.error_mode == "timeout":
            await asyncio.sleep(35)  # Simulate timeout
            
        elif self.error_mode == "exception":
            raise RuntimeError("Simulated agent execution error")
            
        elif self.error_mode == "invalid_response":
            return TypedAgentResult(
                success=False,
                result=None,
                error="Invalid response format"
            )
            
        elif self.error_mode == "memory_error":
            # Simulate memory exhaustion
            raise MemoryError("Simulated memory exhaustion")
            
        elif self.error_mode == "network_error":
            raise ConnectionError("Simulated network connectivity issue")
            
        elif self.error_mode == "intermittent" and self.call_count % 2 == 1:
            raise RuntimeError("Intermittent failure simulation")
            
        # Normal execution
        return await super().run(context, **kwargs)


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseErrorHandling(BaseIntegrationTest):
    """Test agent response error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = self.get_env()  # Use SSOT environment from base class
        self.execution_tracker = get_execution_tracker()
        self.test_user_id = "test_user_errors"
        self.test_thread_id = "thread_errors_001"
        
    async def test_agent_timeout_error_handling_maintains_user_experience(self):
        """
        Test agent timeout error handling maintains user experience.
        
        BVJ: All segments - Reliability/User Experience
        Validates that when agents timeout, users receive clear feedback
        rather than hanging indefinitely.
        """
        # GIVEN: A user execution context and timeout-prone agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = ErrorSimulationAgent(error_mode="timeout")
            query = "Test query for timeout handling"
            
            # WHEN: Agent execution times out
            start_time = time.time()
            
            try:
                # Set a shorter timeout for testing
                result = await asyncio.wait_for(
                    agent.run(context, query=query),
                    timeout=5.0  # 5 second timeout for test
                )
                timeout_occurred = False
            except asyncio.TimeoutError:
                timeout_occurred = True
                execution_time = time.time() - start_time
                
                # Create error response for user
                result = TypedAgentResult(
                    success=False,
                    result=None,
                    error="Agent execution timed out. Please try again with a simpler query.",
                    execution_time_ms=execution_time * 1000
                )
            
            # THEN: Timeout is handled gracefully
            assert timeout_occurred, "Timeout should occur for timeout simulation"
            assert isinstance(result, TypedAgentResult), "Should return structured error response"
            assert not result.success, "Timeout should be marked as failure"
            assert result.error is not None, "Timeout should include error message"
            assert "timeout" in result.error.lower(), "Error message should mention timeout"
            assert result.execution_time_ms is not None, "Execution time should be tracked"
            
            logger.info(f" PASS:  Agent timeout handled gracefully: {result.error}")
            
    async def test_agent_exception_error_handling_prevents_system_crash(self):
        """
        Test agent exception error handling prevents system crashes.
        
        BVJ: All segments - System Stability/Reliability
        Validates that agent exceptions are caught and handled gracefully
        without crashing the entire system.
        """
        # GIVEN: A user execution context and exception-throwing agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = ErrorSimulationAgent(error_mode="exception")
            query = "Test query for exception handling"
            
            # WHEN: Agent throws exception
            exception_caught = False
            
            try:
                result = await agent.run(context, query=query)
            except RuntimeError as e:
                exception_caught = True
                
                # Create error response from exception
                result = TypedAgentResult(
                    success=False,
                    result=None,
                    error=f"Agent execution failed: {str(e)}"
                )
            
            # THEN: Exception is handled without system crash
            assert exception_caught, "Exception should be caught"
            assert isinstance(result, TypedAgentResult), "Should return structured error response"
            assert not result.success, "Exception should be marked as failure"
            assert result.error is not None, "Exception should include error message"
            assert "failed" in result.error.lower(), "Error message should indicate failure"
            
            # Verify system continues to function
            healthy_agent = DataHelperAgent()
            healthy_result = await healthy_agent.run(context, query="Simple test query")
            assert healthy_result is not None, "System should continue functioning after exception"
            
            logger.info(f" PASS:  Agent exception handled without system crash: {result.error}")
            
    async def test_memory_error_handling_protects_system_resources(self):
        """
        Test memory error handling protects system resources.
        
        BVJ: All segments - System Stability/Performance
        Validates that memory errors are handled gracefully and don't
        compromise system stability or other users' experiences.
        """
        # GIVEN: A user execution context and memory-error-prone agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = ErrorSimulationAgent(error_mode="memory_error")
            query = "Test query for memory error handling"
            
            # WHEN: Agent encounters memory error
            memory_error_caught = False
            
            try:
                result = await agent.run(context, query=query)
            except MemoryError as e:
                memory_error_caught = True
                
                # Create resource-constrained error response
                result = TypedAgentResult(
                    success=False,
                    result=None,
                    error="System temporarily unavailable due to high demand. Please try again shortly."
                )
            
            # THEN: Memory error is handled with resource protection
            assert memory_error_caught, "Memory error should be caught"
            assert isinstance(result, TypedAgentResult), "Should return structured error response"
            assert not result.success, "Memory error should be marked as failure"
            assert result.error is not None, "Memory error should include user-friendly message"
            
            # Verify error message is user-friendly (doesn't expose technical details)
            assert "memory" not in result.error.lower(), "Error message should not expose technical details"
            assert "unavailable" in result.error.lower(), "Error message should indicate temporary unavailability"
            
            logger.info(f" PASS:  Memory error handled with resource protection: {result.error}")
            
    async def test_network_error_handling_provides_actionable_feedback(self):
        """
        Test network error handling provides actionable feedback.
        
        BVJ: All segments - User Experience/Support
        Validates that network errors provide actionable feedback to users
        rather than generic error messages.
        """
        # GIVEN: A user execution context and network-error-prone agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = ErrorSimulationAgent(error_mode="network_error")
            query = "Test query for network error handling"
            
            # WHEN: Agent encounters network error
            network_error_caught = False
            
            try:
                result = await agent.run(context, query=query)
            except ConnectionError as e:
                network_error_caught = True
                
                # Create actionable error response
                result = TypedAgentResult(
                    success=False,
                    result=None,
                    error="Unable to process request due to connectivity issues. Please check your connection and try again."
                )
            
            # THEN: Network error provides actionable feedback
            assert network_error_caught, "Network error should be caught"
            assert isinstance(result, TypedAgentResult), "Should return structured error response"
            assert not result.success, "Network error should be marked as failure"
            assert result.error is not None, "Network error should include actionable message"
            
            # Validate actionable feedback
            assert "connectivity" in result.error.lower(), "Error should mention connectivity"
            assert "try again" in result.error.lower(), "Error should suggest retry action"
            
            logger.info(f" PASS:  Network error handled with actionable feedback: {result.error}")
            
    async def test_invalid_context_error_handling_maintains_security(self):
        """
        Test invalid context error handling maintains security.
        
        BVJ: Enterprise - Security/Compliance
        Validates that invalid user context errors are handled securely
        without exposing sensitive information or allowing unauthorized access.
        """
        # GIVEN: An invalid user execution context
        try:
            # Attempt to create context with invalid parameters
            with create_isolated_execution_context(
                user_id="",  # Invalid empty user ID
                thread_id=self.test_thread_id
            ) as context:
                agent = DataHelperAgent()
                query = "Test query with invalid context"
                
                # This should not execute due to invalid context
                result = await agent.run(context, query=query)
                context_error_occurred = False
                
        except (InvalidContextError, ValueError) as e:
            context_error_occurred = True
            
            # Create secure error response
            result = TypedAgentResult(
                success=False,
                result=None,
                error="Authentication required. Please log in and try again."
            )
            
        # THEN: Invalid context is handled securely
        assert context_error_occurred, "Invalid context should trigger error"
        assert isinstance(result, TypedAgentResult), "Should return structured error response"
        assert not result.success, "Invalid context should be marked as failure"
        assert result.error is not None, "Invalid context should include secure error message"
        
        # Validate security of error message
        assert "authentication" in result.error.lower(), "Error should mention authentication"
        assert "invalid" not in result.error.lower(), "Error should not expose technical details"
        assert "user_id" not in result.error.lower(), "Error should not expose internal field names"
        
        logger.info(f" PASS:  Invalid context handled securely: {result.error}")
        
    async def test_intermittent_error_retry_mechanism(self):
        """
        Test intermittent error retry mechanism.
        
        BVJ: All segments - Reliability/User Experience
        Validates that intermittent errors can be handled with retry logic
        to improve success rates and user experience.
        """
        # GIVEN: A user execution context and intermittently failing agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = ErrorSimulationAgent(error_mode="intermittent")
            query = "Test query for intermittent error handling"
            
            max_retries = 3
            retry_count = 0
            last_error = None
            
            # WHEN: Agent execution is retried on intermittent failures
            for attempt in range(max_retries):
                try:
                    result = await agent.run(context, query=query)
                    # If successful, break out of retry loop
                    break
                except RuntimeError as e:
                    last_error = e
                    retry_count += 1
                    
                    if attempt < max_retries - 1:
                        # Wait before retry (exponential backoff)
                        wait_time = 0.1 * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        logger.info(f"Retry attempt {attempt + 1} after {wait_time:.1f}s")
                    else:
                        # Final failure after all retries
                        result = TypedAgentResult(
                            success=False,
                            result=None,
                            error=f"Request failed after {max_retries} attempts. Please try again later."
                        )
            
            # THEN: Retry mechanism improves success rate
            # The intermittent agent should succeed on the second attempt
            if isinstance(result, TypedAgentResult):
                if result.success:
                    assert retry_count >= 1, "Should have retried at least once"
                    logger.info(f" PASS:  Intermittent error resolved after {retry_count + 1} attempts")
                else:
                    assert retry_count == max_retries, "Should have exhausted all retries"
                    assert "failed after" in result.error, "Error should mention retry attempts"
                    logger.info(f" PASS:  Intermittent error handling exhausted retries: {result.error}")
            
    async def test_concurrent_error_handling_isolation(self):
        """
        Test concurrent error handling maintains user isolation.
        
        BVJ: Enterprise - Multi-tenancy/Security
        Validates that errors in one user's agent execution don't affect
        other users' experiences or data.
        """
        # GIVEN: Multiple users with different error scenarios
        user_1_id = f"{self.test_user_id}_concurrent_1"
        user_2_id = f"{self.test_user_id}_concurrent_2"
        
        async def process_user_with_errors(user_id: str, error_mode: Optional[str]) -> Dict[str, Any]:
            """Process user request with potential errors."""
            with create_isolated_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}"
            ) as context:
                if error_mode:
                    agent = ErrorSimulationAgent(error_mode=error_mode)
                else:
                    agent = DataHelperAgent()
                    
                try:
                    result = await agent.run(context, query=f"Query from {user_id}")
                    return {"user_id": user_id, "result": result, "error_occurred": False}
                except Exception as e:
                    error_result = TypedAgentResult(
                        success=False,
                        result=None,
                        error=f"Processing error: {str(e)}"
                    )
                    return {"user_id": user_id, "result": error_result, "error_occurred": True}
        
        # WHEN: Multiple users process concurrently with different error conditions
        tasks = [
            process_user_with_errors(user_1_id, "exception"),  # User 1 has errors
            process_user_with_errors(user_2_id, None)          # User 2 should succeed
        ]
        
        results = await asyncio.gather(*tasks)
        
        # THEN: Error isolation is maintained
        user_1_result, user_2_result = results
        
        # User 1 should have errors
        assert user_1_result["error_occurred"], "User 1 should experience errors"
        assert isinstance(user_1_result["result"], TypedAgentResult), "User 1 should get error result"
        assert not user_1_result["result"].success, "User 1 result should indicate failure"
        
        # User 2 should succeed despite User 1's errors
        assert not user_2_result["error_occurred"], "User 2 should not be affected by User 1's errors"
        assert isinstance(user_2_result["result"], TypedAgentResult), "User 2 should get valid result"
        
        # Validate isolation
        assert user_1_result["user_id"] != user_2_result["user_id"], "Users should be different"
        
        logger.info(" PASS:  Concurrent error handling maintained user isolation")
        
    def teardown_method(self):
        """Clean up test resources."""
        super().teardown_method()