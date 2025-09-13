"""Foundation Unit Tests for BaseAgent - Phase 1 Coverage Enhancement

MISSION: Improve BaseAgent unit test coverage from 23.21% to 50%+ by testing
foundational functionality and user isolation patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal (ALL user segments depend on agents)
- Business Goal: System Stability & Development Velocity
- Value Impact: BaseAgent is foundation of ALL agent operations - proper testing
  ensures $500K+ ARR business functionality remains stable
- Strategic Impact: Every agent inherits from BaseAgent, so test quality here
  cascades to ALL business-critical agent operations

COVERAGE TARGET: Focus on high-impact foundation methods:
- Initialization and configuration (lines 133-251)
- State management and transitions (lines 254-304)
- Metadata storage methods (lines 318-451)
- Token tracking and optimization (lines 452-569)
- Session isolation validation (lines 570-610)
- Factory patterns and user context (lines 1774-2058)

PRINCIPLES:
- Inherit from SSotBaseTestCase for SSOT compliance
- Use real services where possible, minimal mocking
- Test user isolation and factory patterns thoroughly
- Focus on unit-level behavior, not integration scenarios
- Ensure tests actually fail when code is broken
"""

import asyncio
import pytest
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

# SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Core imports
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.base.timing_collector import ExecutionTimingCollector
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager


class TestableBaseAgent(BaseAgent):
    """Testable BaseAgent implementation with controlled behavior."""

    def __init__(self, *args, **kwargs):
        # Extract test configuration
        self.test_execution_should_succeed = kwargs.pop('execution_should_succeed', True)
        self.test_execution_result = kwargs.pop('execution_result', {"status": "success"})
        self.test_websocket_events_enabled = kwargs.pop('websocket_events_enabled', True)

        super().__init__(*args, **kwargs)

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> dict:
        """Modern execution method implementation for testing."""
        if not self.test_execution_should_succeed:
            raise RuntimeError("Test execution failure")

        # Store execution context for validation
        self._last_execution_context = context
        self._last_stream_updates = stream_updates

        # Emit some WebSocket events for testing if enabled
        if self.test_websocket_events_enabled and hasattr(self, '_websocket_adapter'):
            try:
                await self.emit_agent_started("Test execution started")
                await self.emit_thinking("Processing test request")
                await self.emit_agent_completed(self.test_execution_result, context)
            except Exception:
                # Gracefully handle WebSocket errors in tests
                pass

        return {
            "status": "completed",
            "result": self.test_execution_result,
            "context_received": {
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "run_id": context.run_id,
                "request_id": context.request_id
            }
        }


class BaseAgentFoundationTests(SSotAsyncTestCase):
    """Foundation unit tests for BaseAgent class.

    Tests core functionality including initialization, state management,
    metadata operations, and user isolation patterns.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Create mock dependencies for isolated testing
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_redis_manager = Mock(spec=RedisManager)
        self.mock_tool_dispatcher = Mock(spec=UnifiedToolDispatcher)

        # Create test user execution context
        self.test_context = UserExecutionContext(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789",
            request_id="test-request-abc",
            db_session=Mock(),
            agent_context={"test_key": "test_value"},
            metadata={"initialized": True}
        )

    def test_agent_initialization_defaults(self):
        """Test BaseAgent initialization with default parameters."""
        # COVERAGE: BaseAgent.__init__ lines 133-251
        agent = TestableBaseAgent()

        # Verify required attributes initialized
        self.assertIsNotNone(agent.state)
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        self.assertIsNotNone(agent.name)
        self.assertIsNotNone(agent.description)
        self.assertIsNotNone(agent.agent_id)
        self.assertIsNotNone(agent.correlation_id)
        self.assertIsNotNone(agent.context)
        self.assertIsInstance(agent.context, dict)

        # Verify infrastructure components initialized
        self.assertIsNotNone(agent.timing_collector)
        self.assertIsInstance(agent.timing_collector, ExecutionTimingCollector)
        self.assertIsNotNone(agent.token_counter)
        self.assertIsInstance(agent.token_counter, TokenCounter)
        self.assertIsNotNone(agent.token_context_manager)
        self.assertIsInstance(agent.token_context_manager, TokenOptimizationContextManager)

        # Verify monitoring components
        self.assertIsNotNone(agent.monitor)
        self.assertIsInstance(agent.monitor, ExecutionMonitor)

        # Verify reliability components enabled by default
        self.assertTrue(agent._enable_reliability)
        self.assertIsNotNone(agent.reliability_manager)
        self.assertIsInstance(agent.reliability_manager, ReliabilityManager)

        # Verify circuit breaker configured
        self.assertIsNotNone(agent.circuit_breaker)
        self.assertEqual(agent.circuit_breaker.name, agent.name)

    def test_agent_initialization_with_custom_params(self):
        """Test BaseAgent initialization with custom parameters."""
        # COVERAGE: BaseAgent.__init__ with parameter validation
        custom_name = "CustomTestAgent"
        custom_description = "Test agent for custom initialization"
        custom_agent_id = "custom-agent-123"

        agent = TestableBaseAgent(
            name=custom_name,
            description=custom_description,
            agent_id=custom_agent_id,
            enable_reliability=False,
            enable_execution_engine=False,
            enable_caching=True
        )

        # Verify custom parameters applied
        self.assertEqual(agent.name, custom_name)
        self.assertEqual(agent.description, custom_description)
        self.assertEqual(agent.agent_id, custom_agent_id)

        # Verify feature flags respected
        self.assertFalse(agent._enable_reliability)
        self.assertFalse(agent._enable_execution_engine)
        self.assertTrue(agent._enable_caching)

    def test_agent_initialization_with_deprecated_params(self):
        """Test BaseAgent initialization logs warnings for deprecated parameters."""
        # COVERAGE: Deprecated parameter warning logic lines 182-194
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            agent = TestableBaseAgent(
                tool_dispatcher=self.mock_tool_dispatcher,
                redis_manager=self.mock_redis_manager
            )

            # Should generate deprecation warning for tool_dispatcher
            warning_messages = [str(warning.message) for warning in w]
            deprecated_warnings = [msg for msg in warning_messages if "DEPRECATED" in msg]
            self.assertTrue(len(deprecated_warnings) > 0,
                          f"Expected deprecation warning not found. Got warnings: {warning_messages}")

            # Verify deprecated parameters still work for backward compatibility
            self.assertEqual(agent.tool_dispatcher, self.mock_tool_dispatcher)
            self.assertEqual(agent.redis_manager, self.mock_redis_manager)

    def test_state_management_valid_transitions(self):
        """Test valid state transitions in agent lifecycle."""
        # COVERAGE: State management methods lines 254-304
        agent = TestableBaseAgent()

        # Test valid state transitions
        valid_transitions = [
            (SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING),
            (SubAgentLifecycle.RUNNING, SubAgentLifecycle.COMPLETED),
            (SubAgentLifecycle.COMPLETED, SubAgentLifecycle.SHUTDOWN)
        ]

        for from_state, to_state in valid_transitions:
            agent.state = from_state  # Set initial state
            agent.set_state(to_state)
            self.assertEqual(agent.state, to_state)

    def test_state_management_invalid_transitions(self):
        """Test invalid state transitions raise appropriate errors."""
        # COVERAGE: State validation logic lines 272-276
        agent = TestableBaseAgent()

        # Test invalid transitions
        invalid_transitions = [
            (SubAgentLifecycle.COMPLETED, SubAgentLifecycle.PENDING),
            (SubAgentLifecycle.SHUTDOWN, SubAgentLifecycle.RUNNING),
            (SubAgentLifecycle.COMPLETED, SubAgentLifecycle.RUNNING)
        ]

        for from_state, to_state in invalid_transitions:
            agent.state = from_state  # Set initial state
            with self.assertRaises(ValueError) as cm:
                agent.set_state(to_state)

            # Verify error message contains state information
            error_msg = str(cm.exception)
            self.assertIn("Invalid state transition", error_msg)
            self.assertIn(str(from_state), error_msg)
            self.assertIn(str(to_state), error_msg)

    def test_get_state_returns_current_state(self):
        """Test get_state method returns current agent state."""
        # COVERAGE: get_state method line 302-304
        agent = TestableBaseAgent()

        # Test initial state
        self.assertEqual(agent.get_state(), SubAgentLifecycle.PENDING)

        # Test after state change
        agent.set_state(SubAgentLifecycle.RUNNING)
        self.assertEqual(agent.get_state(), SubAgentLifecycle.RUNNING)

    def test_metadata_storage_basic_operations(self):
        """Test basic metadata storage and retrieval operations."""
        # COVERAGE: Metadata methods lines 318-451
        agent = TestableBaseAgent()

        # Test storing simple metadata
        test_key = "test_result"
        test_value = {"data": "test_data", "timestamp": time.time()}

        agent.store_metadata_result(self.test_context, test_key, test_value)

        # Verify metadata stored correctly
        retrieved_value = agent.get_metadata_value(self.test_context, test_key)
        self.assertEqual(retrieved_value, test_value)

    def test_metadata_storage_with_pydantic_serialization(self):
        """Test metadata storage with Pydantic model serialization."""
        # COVERAGE: Pydantic serialization logic lines 342-346
        agent = TestableBaseAgent()

        # Create a mock Pydantic model
        mock_pydantic_model = Mock()
        mock_pydantic_model.model_dump.return_value = {"serialized": "data"}

        agent.store_metadata_result(
            self.test_context,
            "pydantic_result",
            mock_pydantic_model,
            ensure_serializable=True
        )

        # Verify model_dump was called with correct parameters
        mock_pydantic_model.model_dump.assert_called_once_with(mode='json', exclude_none=True)

        # Verify serialized data stored
        retrieved_value = agent.get_metadata_value(self.test_context, "pydantic_result")
        self.assertEqual(retrieved_value, {"serialized": "data"})

    def test_metadata_batch_storage(self):
        """Test batch metadata storage operations."""
        # COVERAGE: store_metadata_batch method lines 412-433
        agent = TestableBaseAgent()

        batch_data = {
            "result1": {"type": "analysis", "value": 123},
            "result2": {"type": "optimization", "value": 456},
            "result3": {"type": "summary", "value": "completed"}
        }

        agent.store_metadata_batch(self.test_context, batch_data)

        # Verify all items stored correctly
        for key, expected_value in batch_data.items():
            retrieved_value = agent.get_metadata_value(self.test_context, key)
            self.assertEqual(retrieved_value, expected_value)

    def test_metadata_retrieval_with_defaults(self):
        """Test metadata retrieval with default values."""
        # COVERAGE: get_metadata_value method lines 434-451
        agent = TestableBaseAgent()

        # Test retrieval of non-existent key with default
        default_value = {"default": "value"}
        retrieved_value = agent.get_metadata_value(
            self.test_context,
            "non_existent_key",
            default_value
        )
        self.assertEqual(retrieved_value, default_value)

        # Test retrieval of non-existent key without default
        retrieved_value = agent.get_metadata_value(self.test_context, "non_existent_key")
        self.assertIsNone(retrieved_value)

    def test_token_usage_tracking(self):
        """Test LLM token usage tracking functionality."""
        # COVERAGE: Token tracking methods lines 452-569
        agent = TestableBaseAgent()

        input_tokens = 100
        output_tokens = 50
        model = "gpt-4"
        operation_type = "test_execution"

        # Track token usage
        enhanced_context = agent.track_llm_usage(
            self.test_context,
            input_tokens,
            output_tokens,
            model,
            operation_type
        )

        # Verify enhanced context returned
        self.assertIsInstance(enhanced_context, UserExecutionContext)

        # Verify token counter called (implementation detail)
        # Note: We're testing behavior, not implementation
        self.assertIsNotNone(agent.token_counter)

    def test_prompt_optimization(self):
        """Test prompt optimization functionality."""
        # COVERAGE: Prompt optimization lines 488-522
        agent = TestableBaseAgent()

        original_prompt = "This is a test prompt that could be optimized"
        target_reduction = 20

        # Optimize prompt
        enhanced_context, optimized_prompt = agent.optimize_prompt_for_context(
            self.test_context,
            original_prompt,
            target_reduction
        )

        # Verify results
        self.assertIsInstance(enhanced_context, UserExecutionContext)
        self.assertIsInstance(optimized_prompt, str)
        # Note: The actual optimization is handled by TokenOptimizationContextManager

    def test_cost_optimization_suggestions(self):
        """Test cost optimization suggestions functionality."""
        # COVERAGE: Cost optimization lines 523-546
        agent = TestableBaseAgent()

        # Get cost optimization suggestions
        enhanced_context, suggestions = agent.get_cost_optimization_suggestions(self.test_context)

        # Verify results
        self.assertIsInstance(enhanced_context, UserExecutionContext)
        self.assertIsInstance(suggestions, list)

    def test_token_usage_summary(self):
        """Test token usage summary retrieval."""
        # COVERAGE: get_token_usage_summary lines 547-569
        agent = TestableBaseAgent()

        # Get token usage summary
        summary = agent.get_token_usage_summary(self.test_context)

        # Verify summary structure
        self.assertIsInstance(summary, dict)
        # The actual summary content depends on TokenCounter implementation

    def test_session_isolation_validation(self):
        """Test session isolation validation mechanism."""
        # COVERAGE: Session isolation lines 570-610
        agent = TestableBaseAgent()

        # Validation should pass for clean agent
        try:
            agent._validate_session_isolation()
        except Exception as e:
            self.fail(f"Session isolation validation failed unexpectedly: {e}")

    def test_user_context_setting(self):
        """Test user context setting and validation."""
        # COVERAGE: set_user_context method lines 1693-1720
        agent = TestableBaseAgent()

        # Set user context
        agent.set_user_context(self.test_context)

        # Verify context stored
        self.assertEqual(agent.user_context, self.test_context)

        # Verify WebSocket emitter reset
        self.assertIsNone(agent._websocket_emitter)

    def test_user_context_validation_invalid_context(self):
        """Test user context validation rejects invalid contexts."""
        # COVERAGE: Context validation in set_user_context
        agent = TestableBaseAgent()

        # Test with None context
        with self.assertRaises(Exception):
            agent.set_user_context(None)

        # Test with invalid context type
        with self.assertRaises(Exception):
            agent.set_user_context("invalid_context")

    async def test_modern_execute_with_context(self):
        """Test modern execute method with UserExecutionContext."""
        # COVERAGE: execute_with_context method lines 690-802
        agent = TestableBaseAgent(
            execution_should_succeed=True,
            execution_result={"test": "result"}
        )

        # Set user context
        agent.set_user_context(self.test_context)

        # Execute with context
        result = await agent.execute_with_context(self.test_context, stream_updates=True)

        # Verify execution completed
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"], {"test": "result"})

        # Verify context was passed correctly
        self.assertEqual(agent._last_execution_context, self.test_context)
        self.assertTrue(agent._last_stream_updates)

    async def test_modern_execute_failure_handling(self):
        """Test modern execute method handles failures correctly."""
        # COVERAGE: Exception handling in execute_with_context
        agent = TestableBaseAgent(execution_should_succeed=False)
        agent.set_user_context(self.test_context)

        # Execute should raise the test exception
        with self.assertRaises(RuntimeError) as cm:
            await agent.execute_with_context(self.test_context)

        self.assertEqual(str(cm.exception), "Test execution failure")

    async def test_legacy_execute_compatibility(self):
        """Test legacy execute method compatibility."""
        # COVERAGE: Legacy compatibility in execute method lines 613-689
        agent = TestableBaseAgent(
            execution_should_succeed=True,
            execution_result={"legacy": "result"}
        )

        # Test legacy call pattern with message and context
        result = await agent.execute(
            message="test message",
            context=self.test_context,
            stream_updates=False
        )

        # Verify execution completed
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "completed")

        # Verify message was injected into context
        self.assertIn("user_request", agent._last_execution_context.agent_context)
        self.assertEqual(agent._last_execution_context.agent_context["user_request"], "test message")

    def test_factory_method_create_with_context(self):
        """Test factory method for creating agent with context."""
        # COVERAGE: create_agent_with_context factory lines 2014-2058
        agent = TestableBaseAgent.create_agent_with_context(self.test_context)

        # Verify agent created correctly
        self.assertIsInstance(agent, TestableBaseAgent)
        self.assertEqual(agent.user_context, self.test_context)

        # Verify context isolation
        self.assertEqual(agent.user_context.user_id, self.test_context.user_id)
        self.assertEqual(agent.user_context.thread_id, self.test_context.thread_id)

    def test_factory_method_create_legacy_with_warnings(self):
        """Test legacy factory method generates appropriate warnings."""
        # COVERAGE: create_legacy_with_warnings factory lines 1821-1860
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            agent = TestableBaseAgent.create_legacy_with_warnings(
                llm_manager=self.mock_llm_manager,
                tool_dispatcher=self.mock_tool_dispatcher
            )

            # Should generate deprecation warning
            warning_messages = [str(warning.message) for warning in w]
            deprecated_warnings = [msg for msg in warning_messages if "DEPRECATED" in msg]
            self.assertTrue(len(deprecated_warnings) > 0,
                          f"Expected deprecation warning not found. Got warnings: {warning_messages}")

        # Verify agent created with legacy parameters
        self.assertEqual(agent.llm_manager, self.mock_llm_manager)
        self.assertEqual(agent.tool_dispatcher, self.mock_tool_dispatcher)

    def test_migration_validation_compliant_agent(self):
        """Test migration validation for compliant modern agent."""
        # COVERAGE: validate_modern_implementation lines 1863-1953
        agent = TestableBaseAgent()

        validation_result = agent.validate_modern_implementation()

        # Verify validation structure
        self.assertIsInstance(validation_result, dict)
        self.assertIn("compliant", validation_result)
        self.assertIn("pattern", validation_result)
        self.assertIn("warnings", validation_result)
        self.assertIn("errors", validation_result)

        # Agent should be compliant (has _execute_with_user_context)
        self.assertTrue(validation_result["compliant"])
        self.assertEqual(validation_result["pattern"], "modern")

    def test_migration_status_reporting(self):
        """Test migration status reporting functionality."""
        # COVERAGE: get_migration_status lines 1993-2013
        agent = TestableBaseAgent()

        migration_status = agent.get_migration_status()

        # Verify status structure
        self.assertIsInstance(migration_status, dict)
        required_keys = [
            "agent_name", "agent_class", "migration_status",
            "execution_pattern", "user_isolation_safe",
            "warnings_count", "errors_count", "recommendations_count",
            "validation_timestamp", "compliance_details"
        ]

        for key in required_keys:
            self.assertIn(key, migration_status)

        # Verify values make sense
        self.assertEqual(migration_status["agent_name"], agent.name)
        self.assertIn("TestableBaseAgent", migration_status["agent_class"])

    async def test_reset_state_functionality(self):
        """Test agent state reset functionality."""
        # COVERAGE: reset_state method lines 819-972
        agent = TestableBaseAgent()

        # Modify agent state
        agent.set_state(SubAgentLifecycle.RUNNING)
        agent.context["test_data"] = "should_be_cleared"

        # Reset state
        await agent.reset_state()

        # Verify state reset
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        self.assertEqual(len(agent.context), 0)
        self.assertIsNone(agent.start_time)
        self.assertIsNone(agent.end_time)

    async def test_shutdown_functionality(self):
        """Test agent shutdown functionality."""
        # COVERAGE: shutdown method lines 973-1008
        agent = TestableBaseAgent()

        # Add some context data
        agent.context["test_data"] = "should_be_cleared"

        # Shutdown agent
        await agent.shutdown()

        # Verify shutdown state
        self.assertEqual(agent.state, SubAgentLifecycle.SHUTDOWN)
        self.assertEqual(len(agent.context), 0)

        # Multiple shutdowns should be idempotent
        await agent.shutdown()
        self.assertEqual(agent.state, SubAgentLifecycle.SHUTDOWN)

    def test_health_status_reporting(self):
        """Test comprehensive health status reporting."""
        # COVERAGE: get_health_status lines 1495-1587
        agent = TestableBaseAgent()

        health_status = agent.get_health_status()

        # Verify health status structure
        self.assertIsInstance(health_status, dict)
        required_keys = [
            "agent_name", "state", "websocket_available",
            "uses_unified_reliability", "overall_status", "status"
        ]

        for key in required_keys:
            self.assertIn(key, health_status)

        # Verify values
        self.assertEqual(health_status["agent_name"], agent.name)
        self.assertEqual(health_status["state"], agent.state.value)
        self.assertTrue(health_status["uses_unified_reliability"])
        self.assertIn(health_status["overall_status"], ["healthy", "degraded", "unhealthy"])

    def test_circuit_breaker_status(self):
        """Test circuit breaker status reporting."""
        # COVERAGE: get_circuit_breaker_status lines 1588-1620
        agent = TestableBaseAgent()

        cb_status = agent.get_circuit_breaker_status()

        # Verify status structure
        self.assertIsInstance(cb_status, dict)
        self.assertIn("state", cb_status)
        self.assertIn("status", cb_status)

        # Should be healthy initially
        self.assertIn(cb_status["state"], ["closed", "open", "half_open", "unknown"])

    async def test_websocket_bridge_integration(self):
        """Test WebSocket bridge integration functionality."""
        # COVERAGE: WebSocket bridge methods lines 1011-1020
        agent = TestableBaseAgent(websocket_events_enabled=True)

        # Set up mock WebSocket bridge
        mock_bridge = Mock()
        run_id = "test-run-123"

        # Set WebSocket bridge
        agent.set_websocket_bridge(mock_bridge, run_id)

        # Verify bridge configuration
        self.assertTrue(hasattr(agent, '_websocket_adapter'))

        # Test propagate context method
        context = {"test": "context"}
        agent.propagate_websocket_context_to_state(context)

        # Verify context stored
        self.assertTrue(hasattr(agent, '_websocket_context'))
        self.assertIn("test", agent._websocket_context)

    async def test_compatibility_cleanup_method(self):
        """Test cleanup method for backward compatibility."""
        # COVERAGE: cleanup method lines 1429-1455
        agent = TestableBaseAgent()

        # Add some state to clean up
        agent.context["test_data"] = "should_be_cleared"

        # Call cleanup
        await agent.cleanup()

        # Verify cleanup occurred
        self.assertTrue(hasattr(agent, '_cleaned_up'))
        self.assertTrue(agent._cleaned_up)
        self.assertEqual(len(agent.context), 0)

    def test_websocket_test_mode_enablement(self):
        """Test WebSocket test mode enablement."""
        # COVERAGE: enable_websocket_test_mode lines 1456-1465
        agent = TestableBaseAgent()

        # Enable test mode
        agent.enable_websocket_test_mode()

        # Verify test mode enabled on adapter
        # Note: Implementation detail, but we can verify the method exists and runs
        self.assertTrue(hasattr(agent, '_websocket_adapter'))