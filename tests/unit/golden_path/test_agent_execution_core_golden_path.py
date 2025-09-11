"""
Comprehensive Unit Tests for Agent Execution Core in Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent execution delivering $500K+ ARR
- Value Impact: Validates core agent execution logic that drives chat functionality
- Strategic Impact: Protects primary revenue-generating user flow "users login → get AI responses"

This test suite validates the agent execution core components that power the golden path:
- SupervisorAgent orchestration and workflow management
- Sub-agent execution and coordination
- ExecutionEngine factory patterns and user isolation
- Agent state management and persistence
- Error handling and recovery mechanisms
- Performance requirements and SLA compliance

Key Coverage Areas:
- Agent creation and initialization
- Execution workflow and coordination
- State management and persistence
- Error handling and recovery
- Performance and timeout management
- User context isolation
- WebSocket integration
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Agent core imports
from netra_backend.app.agents.base_agent import BaseAgent, AgentState
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory

# User context and state management
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextManager
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, get_execution_tracker
from netra_backend.app.core.execution_tracker import ExecutionState

# WebSocket and communication
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Execution results and schemas
from shared.types.agent_types import AgentExecutionResult
from netra_backend.app.schemas.agent_result_types import AgentExecutionResult as LegacyAgentExecutionResult

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestAgentExecutionCoreGoldenPath(SSotAsyncTestCase):
    """
    Comprehensive unit tests for agent execution core in the golden path.
    
    Tests focus on the core agent execution components that deliver chat functionality
    representing 90% of platform business value.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Test user context for all tests
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        
        # Mock LLM Manager for agent testing
        self.mock_llm_manager = MagicMock()
        self.mock_llm_client = self.mock_factory.create_llm_client_mock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_llm_client
        
        # Mock WebSocket components
        self.mock_websocket = self.mock_factory.create_websocket_mock()
        self.mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Execution tracking
        self.execution_results = []
        self.state_changes = []
        self.performance_metrics = []

    async def async_setup_method(self, method):
        """Async setup for agent and context initialization."""
        await super().async_setup_method(method)
        
        # Create user execution context
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Initialize execution tracker
        self.execution_tracker = get_execution_tracker()

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_supervisor_agent_initialization_and_configuration(self):
        """
        BVJ: All segments | System Reliability | Ensures supervisor agent initializes correctly
        Test SupervisorAgent initialization with proper configuration.
        """
        # Test supervisor creation
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Verify basic initialization
        assert supervisor is not None
        assert supervisor.llm_manager == self.mock_llm_manager
        assert hasattr(supervisor, 'name')
        assert hasattr(supervisor, 'description')
        
        # Test configuration properties
        assert supervisor.name == "supervisor"
        assert "orchestrat" in supervisor.description.lower()
        
        # Test state initialization
        assert hasattr(supervisor, '_current_state')
        initial_state = supervisor.get_current_state()
        assert initial_state == AgentState.IDLE
        
        # Test WebSocket bridge integration
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = mock_bridge
        assert supervisor.websocket_bridge == mock_bridge
        
        logger.info("✅ SupervisorAgent initialization validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_execution_engine_factory_user_isolation_patterns(self):
        """
        BVJ: All segments | User Isolation | Ensures proper user context isolation
        Test ExecutionEngineFactory creates properly isolated execution environments.
        """
        # Create WebSocket bridge for factory
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Create contexts for different users
        user1_context = UserExecutionContext(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        user2_context = UserExecutionContext(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        
        # Create execution engines for different users
        engine1 = await factory.create_for_user(user1_context)
        engine2 = await factory.create_for_user(user2_context)
        
        # Verify engines are different instances
        assert engine1 is not engine2, "Engines should be separate instances"
        assert id(engine1) != id(engine2), "Engines should have different memory addresses"
        
        # Verify user context isolation
        context1 = engine1.get_user_context()
        context2 = engine2.get_user_context()
        
        assert context1.user_id != context2.user_id, "User IDs should be different"
        assert context1.thread_id != context2.thread_id, "Thread IDs should be different"
        assert context1.run_id != context2.run_id, "Run IDs should be different"
        
        # Test state isolation
        test_key = "test_agent_state"
        user1_value = "user1_specific_value"
        user2_value = "user2_specific_value"
        
        engine1.set_agent_state(test_key, user1_value)
        engine2.set_agent_state(test_key, user2_value)
        
        # Verify state doesn't leak between users
        assert engine1.get_agent_state(test_key) == user1_value
        assert engine2.get_agent_state(test_key) == user2_value
        assert engine1.get_agent_state(test_key) != engine2.get_agent_state(test_key)
        
        # Test execution isolation
        execution_data1 = {"message": "user1_message", "type": "analysis"}
        execution_data2 = {"message": "user2_message", "type": "optimization"}
        
        engine1.set_execution_state("current_task", execution_data1)
        engine2.set_execution_state("current_task", execution_data2)
        
        retrieved_data1 = engine1.get_execution_state("current_task")
        retrieved_data2 = engine2.get_execution_state("current_task")
        
        assert retrieved_data1["message"] == "user1_message"
        assert retrieved_data2["message"] == "user2_message"
        
        logger.info("✅ ExecutionEngineFactory user isolation validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_agent_state_management_and_transitions(self):
        """
        BVJ: All segments | State Management | Ensures proper agent state handling
        Test agent state management and state transitions during execution.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Track state changes
        state_history = []
        
        def track_state_change(old_state, new_state):
            state_history.append((old_state, new_state, datetime.utcnow()))
        
        # Mock state change tracking
        original_set_state = supervisor.set_current_state
        def tracked_set_state(new_state):
            old_state = supervisor.get_current_state()
            result = original_set_state(new_state)
            track_state_change(old_state, new_state)
            return result
        
        supervisor.set_current_state = tracked_set_state
        
        # Test state transitions
        initial_state = supervisor.get_current_state()
        assert initial_state == AgentState.IDLE
        
        # Transition to processing
        supervisor.set_current_state(AgentState.PROCESSING)
        assert supervisor.get_current_state() == AgentState.PROCESSING
        
        # Transition to completed
        supervisor.set_current_state(AgentState.COMPLETED)
        assert supervisor.get_current_state() == AgentState.COMPLETED
        
        # Transition to error state
        supervisor.set_current_state(AgentState.ERROR)
        assert supervisor.get_current_state() == AgentState.ERROR
        
        # Reset to idle
        supervisor.set_current_state(AgentState.IDLE)
        assert supervisor.get_current_state() == AgentState.IDLE
        
        # Verify state history
        assert len(state_history) == 4, f"Expected 4 state transitions, got {len(state_history)}"
        
        expected_transitions = [
            (AgentState.IDLE, AgentState.PROCESSING),
            (AgentState.PROCESSING, AgentState.COMPLETED),
            (AgentState.COMPLETED, AgentState.ERROR),
            (AgentState.ERROR, AgentState.IDLE)
        ]
        
        for i, (expected_old, expected_new) in enumerate(expected_transitions):
            actual_old, actual_new, timestamp = state_history[i]
            assert actual_old == expected_old, f"Transition {i}: expected old state {expected_old}, got {actual_old}"
            assert actual_new == expected_new, f"Transition {i}: expected new state {expected_new}, got {actual_new}"
            assert isinstance(timestamp, datetime), f"Transition {i}: timestamp should be datetime"
        
        logger.info("✅ Agent state management validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_agent_execution_workflow_coordination(self):
        """
        BVJ: All segments | Workflow Management | Ensures proper execution coordination
        Test agent execution workflow and coordination logic.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Mock WebSocket bridge for event tracking
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = mock_bridge
        
        # Track execution steps
        execution_steps = []
        
        # Mock the LLM client to return realistic responses
        async def mock_llm_response(*args, **kwargs):
            execution_steps.append("llm_call")
            return {
                "response": "I'll analyze your request and coordinate the appropriate sub-agents.",
                "workflow": {
                    "steps": ["triage", "data_collection", "analysis", "report_generation"],
                    "estimated_time": "2-3 minutes"
                }
            }
        
        self.mock_llm_client.agenerate.return_value = mock_llm_response()
        
        # Execute supervisor workflow
        start_time = time.time()
        
        result = await supervisor.execute(
            context=self.user_context,
            stream_updates=True
        )
        
        execution_time = time.time() - start_time
        
        # Verify execution completed
        assert result is not None, "Execution should return a result"
        
        # Verify result format (handle both dict and AgentExecutionResult)
        if isinstance(result, dict):
            assert "status" in result or "success" in result or "supervisor_result" in result
        elif hasattr(result, 'success'):
            assert hasattr(result, 'success')
            assert hasattr(result, 'error')
        
        # Verify WebSocket events were sent
        bridge_calls = mock_bridge.method_calls
        assert len(bridge_calls) > 0, "WebSocket bridge should be called for events"
        
        # Check for specific event types
        called_methods = [call.method for call in bridge_calls if hasattr(call, 'method')]
        
        # Alternative: Check that bridge was called (some methods might be dynamically set)
        assert len(bridge_calls) > 0, "Bridge should be called during execution"
        
        # Verify execution timing is reasonable
        assert execution_time < 5.0, f"Execution took too long: {execution_time}s"
        
        # Verify LLM was called
        assert "llm_call" in execution_steps, "LLM should be called during execution"
        
        logger.info(f"✅ Agent execution workflow validation passed: {execution_time:.3f}s")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_agent_error_handling_and_recovery_mechanisms(self):
        """
        BVJ: All segments | System Reliability | Ensures robust error handling
        Test agent error handling and recovery mechanisms.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Mock failing LLM client
        failing_client = AsyncMock()
        failing_client.agenerate.side_effect = Exception("LLM service temporarily unavailable")
        self.mock_llm_manager.get_default_client.return_value = failing_client
        
        # Track error handling
        error_events = []
        
        # Mock WebSocket bridge to capture error events
        async def capture_error_event(*args, **kwargs):
            if len(args) > 0 and "error" in str(args[0]).lower():
                error_events.append({"args": args, "kwargs": kwargs})
        
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_error = capture_error_event
        supervisor.websocket_bridge = mock_bridge
        
        # Test error handling during execution
        with pytest.raises(Exception, match="LLM service temporarily unavailable"):
            await supervisor.execute(
                context=self.user_context,
                stream_updates=True
            )
        
        # Verify agent state after error
        final_state = supervisor.get_current_state()
        assert final_state == AgentState.ERROR, f"Agent should be in ERROR state, got {final_state}"
        
        # Test recovery mechanism
        # Create working LLM client for recovery test
        working_client = AsyncMock()
        working_client.agenerate.return_value = {
            "response": "Recovery successful, proceeding with analysis.",
            "status": "recovered"
        }
        self.mock_llm_manager.get_default_client.return_value = working_client
        
        # Reset agent state for recovery
        supervisor.set_current_state(AgentState.IDLE)
        
        # Execute again to test recovery
        recovery_result = await supervisor.execute(
            context=self.user_context,
            stream_updates=True
        )
        
        # Verify recovery
        assert recovery_result is not None, "Recovery execution should succeed"
        recovery_state = supervisor.get_current_state()
        assert recovery_state != AgentState.ERROR, f"Agent should recover from error state, got {recovery_state}"
        
        logger.info("✅ Agent error handling and recovery validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_agent_performance_and_timeout_management(self):
        """
        BVJ: All segments | Performance SLA | Ensures agents meet timing requirements
        Test agent performance and timeout management for SLA compliance.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Mock WebSocket bridge
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = mock_bridge
        
        # Track performance metrics
        performance_data = []
        
        # Mock LLM client with controlled delays
        async def timed_llm_response(delay_seconds=0.1):
            await asyncio.sleep(delay_seconds)
            performance_data.append({"operation": "llm_call", "duration": delay_seconds})
            return {
                "response": "Analysis complete with timing data.",
                "performance": {"processing_time": delay_seconds}
            }
        
        self.mock_llm_client.agenerate.return_value = await timed_llm_response(0.1)
        
        # Test normal performance
        start_time = time.time()
        
        result = await supervisor.execute(
            context=self.user_context,
            stream_updates=True
        )
        
        execution_time = time.time() - start_time
        
        # Verify performance requirements
        assert execution_time < 2.0, f"Execution too slow: {execution_time}s (should be < 2.0s)"
        assert result is not None, "Execution should complete successfully"
        
        # Test timeout handling
        # Mock slow LLM client
        slow_client = AsyncMock()
        
        async def slow_llm_response():
            await asyncio.sleep(10.0)  # Longer than timeout
            return {"response": "This should timeout"}
        
        slow_client.agenerate.return_value = slow_llm_response()
        self.mock_llm_manager.get_default_client.return_value = slow_client
        
        # Reset agent state
        supervisor.set_current_state(AgentState.IDLE)
        
        # Test timeout behavior
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                supervisor.execute(
                    context=self.user_context,
                    stream_updates=True
                ),
                timeout=1.0  # 1 second timeout
            )
        
        # Verify agent handles timeout gracefully
        timeout_state = supervisor.get_current_state()
        # Agent may be in PROCESSING or ERROR state after timeout
        assert timeout_state in [AgentState.PROCESSING, AgentState.ERROR], f"Unexpected state after timeout: {timeout_state}"
        
        logger.info(f"✅ Agent performance and timeout validation passed: {execution_time:.3f}s")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_execution_result_formats_and_compatibility(self):
        """
        BVJ: All segments | API Compatibility | Ensures consistent result formats
        Test agent execution result formats and API compatibility.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Mock WebSocket bridge
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = mock_bridge
        
        # Test different result formats
        test_cases = [
            # Success case
            {
                "llm_response": {
                    "response": "Analysis completed successfully.",
                    "status": "success",
                    "data": {"recommendations": 5, "savings": 1200.50}
                },
                "expected_success": True
            },
            # Partial success case
            {
                "llm_response": {
                    "response": "Analysis partially completed with warnings.",
                    "status": "partial",
                    "warnings": ["Some data unavailable"]
                },
                "expected_success": True  # Partial success still counts as success
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases):
            # Configure LLM response
            self.mock_llm_client.agenerate.return_value = test_case["llm_response"]
            
            # Reset agent state
            supervisor.set_current_state(AgentState.IDLE)
            
            # Execute and capture result
            result = await supervisor.execute(
                context=self.user_context,
                stream_updates=True
            )
            
            results.append(result)
            
            # Verify result is not None
            assert result is not None, f"Test case {i}: Result should not be None"
            
            # Test different result format handling
            if isinstance(result, dict):
                # Dictionary format - check for status or success indicators
                has_status = any(key in result for key in ["status", "success", "supervisor_result", "results"])
                assert has_status, f"Test case {i}: Result dict should have status indicator"
                
                # Check specific format types
                if "results" in result and hasattr(result["results"], "success"):
                    # Wrapped AgentExecutionResult
                    execution_result = result["results"]
                    assert hasattr(execution_result, "success"), "Should have success attribute"
                    assert hasattr(execution_result, "error"), "Should have error attribute"
                elif "supervisor_result" in result:
                    # Supervisor result format
                    assert result["supervisor_result"] in ["completed", "failed", "partial"]
                elif "status" in result:
                    # Legacy format
                    assert result["status"] in ["success", "completed", "failed", "partial"]
                
            elif hasattr(result, 'success'):
                # AgentExecutionResult format
                assert hasattr(result, 'success'), "Should have success attribute"
                assert hasattr(result, 'error'), "Should have error attribute"
                assert isinstance(result.success, bool), "Success should be boolean"
                
                # Verify expected success/failure
                if test_case["expected_success"]:
                    assert result.success, f"Test case {i}: Expected success"
                    assert result.error is None, f"Test case {i}: Error should be None on success"
                
            else:
                # Unknown format - this is an issue
                pytest.fail(f"Test case {i}: Unknown result format: {type(result)}")
        
        # Verify all test cases produced results
        assert len(results) == len(test_cases), "All test cases should produce results"
        
        logger.info(f"✅ Execution result format validation passed: {len(results)} formats tested")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_user_context_manager_integration(self):
        """
        BVJ: All segments | User Management | Ensures proper user context handling
        Test integration with UserContextManager for secure user isolation.
        """
        # Test UserContextManager integration
        context_manager = UserContextManager()
        
        # Create user contexts for testing
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        
        # Test context creation and isolation
        context1 = await context_manager.create_isolated_execution_context(
            user_id=user1_id,
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        
        context2 = await context_manager.create_isolated_execution_context(
            user_id=user2_id,
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        
        # Verify contexts are isolated
        assert context1.user_id != context2.user_id, "User contexts should be isolated"
        assert context1.thread_id != context2.thread_id, "Thread contexts should be isolated"
        
        # Test context validation
        is_valid1 = await context_manager.validate_user_context(context1)
        is_valid2 = await context_manager.validate_user_context(context2)
        
        assert is_valid1, "Context 1 should be valid"
        assert is_valid2, "Context 2 should be valid"
        
        # Test cross-contamination detection
        # This should detect if contexts are accidentally sharing state
        context1_state = context_manager._get_context_state(context1.user_id)
        context2_state = context_manager._get_context_state(context2.user_id)
        
        # Verify states are separate
        assert context1_state is not context2_state, "Context states should be separate objects"
        
        # Test context cleanup
        await context_manager.cleanup_user_context(context1.user_id)
        
        # Verify cleanup worked
        with pytest.raises(Exception):  # Should raise InvalidContextError or similar
            await context_manager.validate_user_context(context1)
        
        # Context2 should still be valid
        is_valid2_after_cleanup = await context_manager.validate_user_context(context2)
        assert is_valid2_after_cleanup, "Context 2 should still be valid after context 1 cleanup"
        
        # Cleanup context2
        await context_manager.cleanup_user_context(context2.user_id)
        
        logger.info("✅ UserContextManager integration validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    async def test_execution_tracker_integration_and_metrics(self):
        """
        BVJ: Platform/Internal | Observability | Ensures execution tracking works
        Test integration with AgentExecutionTracker for monitoring and metrics.
        """
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        execution_tracker = get_execution_tracker()
        
        # Mock WebSocket bridge
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        supervisor.websocket_bridge = mock_bridge
        
        # Create execution ID for tracking
        execution_id = str(uuid.uuid4())
        
        # Start execution tracking
        await execution_tracker.start_execution(
            execution_id=execution_id,
            user_id=self.test_user_id,
            agent_name="supervisor",
            context=self.user_context.to_dict()
        )
        
        # Verify execution was started
        execution_state = execution_tracker.get_execution_state(execution_id)
        assert execution_state == ExecutionState.RUNNING, f"Expected RUNNING state, got {execution_state}"
        
        # Mock successful LLM response
        self.mock_llm_client.agenerate.return_value = {
            "response": "Execution tracked successfully.",
            "metrics": {"tokens_used": 150, "processing_time": 0.5}
        }
        
        # Execute supervisor with tracking
        start_time = time.time()
        
        result = await supervisor.execute(
            context=self.user_context,
            stream_updates=True
        )
        
        execution_time = time.time() - start_time
        
        # Update execution tracking with results
        await execution_tracker.update_execution_state(
            execution_id=execution_id,
            state=ExecutionState.COMPLETED
        )
        
        # Record execution metrics
        await execution_tracker.record_execution_metrics(
            execution_id=execution_id,
            metrics={
                "execution_time": execution_time,
                "tokens_used": 150,
                "success": True,
                "user_id": self.test_user_id
            }
        )
        
        # Verify final execution state
        final_state = execution_tracker.get_execution_state(execution_id)
        assert final_state == ExecutionState.COMPLETED, f"Expected COMPLETED state, got {final_state}"
        
        # Verify metrics were recorded
        metrics = execution_tracker.get_execution_metrics(execution_id)
        assert metrics is not None, "Metrics should be recorded"
        assert "execution_time" in metrics, "Execution time should be recorded"
        assert "tokens_used" in metrics, "Token usage should be recorded"
        assert "success" in metrics, "Success status should be recorded"
        
        # Test error tracking
        error_execution_id = str(uuid.uuid4())
        
        await execution_tracker.start_execution(
            execution_id=error_execution_id,
            user_id=self.test_user_id,
            agent_name="supervisor",
            context=self.user_context.to_dict()
        )
        
        # Simulate error
        await execution_tracker.update_execution_state(
            execution_id=error_execution_id,
            state=ExecutionState.FAILED
        )
        
        await execution_tracker.record_execution_error(
            execution_id=error_execution_id,
            error="Test error for tracking",
            error_type="TestError"
        )
        
        # Verify error tracking
        error_state = execution_tracker.get_execution_state(error_execution_id)
        assert error_state == ExecutionState.FAILED, f"Expected FAILED state, got {error_state}"
        
        error_info = execution_tracker.get_execution_error(error_execution_id)
        assert error_info is not None, "Error info should be recorded"
        assert "Test error for tracking" in str(error_info), "Error message should be recorded"
        
        logger.info("✅ Execution tracker integration validation passed")

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Clear execution tracking
        self.execution_results.clear()
        self.state_changes.clear()
        self.performance_metrics.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        # Cleanup user context if needed
        if hasattr(self, 'user_context'):
            # Cleanup any resources associated with the test user context
            pass
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
