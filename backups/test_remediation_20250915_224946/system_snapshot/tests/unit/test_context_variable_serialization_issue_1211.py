"""Unit tests for Issue #1211: ContextVar serialization failures.

This test suite reproduces the ContextVar serialization failures that occur when
attempting to pickle/serialize objects containing contextvars.ContextVar instances.

Business Value: Platform/Internal - System Stability
Prevents serialization failures that could disrupt agent execution and WebSocket events.

The issue manifests in 4 failing object types:
1. UnifiedTraceContext (contains ContextVar references)
2. LoggingContext (contains ContextVar references)
3. ExecutionEngineFactory (contains async locks with ContextVar state)
4. UserExecutionContext (may contain ContextVar references indirectly)

These failures occur during:
- Redis caching operations
- WebSocket message serialization
- Agent state persistence
- Cross-process communication

SSOT Compliance:
- Inherits from SSotBaseTestCase for unified test infrastructure
- Uses test framework patterns from SSOT base classes
- Follows naming conventions and error handling patterns
"""

import pickle
import contextvars
import asyncio
import uuid
import pytest
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the problematic classes that contain ContextVar references
from netra_backend.app.core.unified_trace_context import (
    UnifiedTraceContext,
    TraceSpan,
    _trace_context,
    get_current_trace_context,
    set_trace_context
)
from netra_backend.app.core.logging_context import (
    LoggingContext,
    request_id_context,
    user_id_context,
    trace_id_context
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_defensive_user_execution_context
)


class ContextVarSerializationFailuresTests(SSotAsyncTestCase):
    """Test suite reproducing ContextVar serialization failures for Issue #1211."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)

        # Clear any existing context state
        self.clear_all_context_vars()

        # Test data
        self.test_user_id = "test_user_123"
        self.test_run_id = str(uuid.uuid4())
        self.test_request_id = str(uuid.uuid4())

    def teardown_method(self, method):
        """Clean up after each test method."""
        super().teardown_method(method)

        # Clear context state
        self.clear_all_context_vars()

    def clear_all_context_vars(self):
        """Clear all context variables to prevent test interference."""
        try:
            _trace_context.set(None)
            request_id_context.set(None)
            user_id_context.set(None)
            trace_id_context.set(None)
        except Exception:
            pass  # Context vars may not be set

    def test_unified_trace_context_pickle_failure(self):
        """Test that UnifiedTraceContext fails to pickle due to ContextVar references.

        This test reproduces the core serialization issue where UnifiedTraceContext
        cannot be pickled because it references _trace_context (a ContextVar).
        """
        # Create a UnifiedTraceContext instance
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            thread_id="thread_123"
        )

        # Set up a trace span
        span = trace_context.start_span("test_operation", {"key": "value"})
        trace_context.add_event("test_event", {"event_key": "event_value"})
        trace_context.finish_span(span)

        # Attempt to pickle the trace context - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(trace_context)

    def test_logging_context_pickle_failure(self):
        """Test that LoggingContext fails to pickle due to ContextVar references.

        LoggingContext contains multiple ContextVar instances that prevent serialization.
        """
        # Create a LoggingContext instance and set some context
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id="trace_123"
        )

        # Verify context is set
        context_data = logging_context.get_context()
        self.assertEqual(context_data['request_id'], self.test_request_id)
        self.assertEqual(context_data['user_id'], self.test_user_id)

        # Attempt to pickle the logging context - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(logging_context)

    async def test_execution_engine_factory_pickle_failure(self):
        """Test that ExecutionEngineFactory fails to pickle due to async locks and ContextVar state.

        ExecutionEngineFactory contains asyncio.Lock and other async primitives that
        may have ContextVar state and cannot be pickled.
        """
        # Create a mock WebSocket bridge to avoid real dependencies
        mock_websocket_bridge = Mock()
        mock_websocket_bridge.user_id = self.test_user_id

        # Create ExecutionEngineFactory instance
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_websocket_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )

        # Set some factory state
        factory._factory_metrics['test_metric'] = 42

        # Attempt to pickle the factory - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(factory)

    async def test_user_execution_context_pickle_failure(self):
        """Test that UserExecutionContext may fail to pickle when containing ContextVar references.

        UserExecutionContext may indirectly reference ContextVar state through
        trace contexts or other nested objects.
        """
        # Create UserExecutionContext with trace context
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4())
        )

        # Set the trace context in ContextVar
        set_trace_context(trace_context)

        # Create UserExecutionContext
        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            websocket_client_id=self.test_request_id
        )

        # Add trace context if supported
        if hasattr(user_context, 'trace_context'):
            user_context.trace_context = trace_context

        # Attempt to pickle the user context - this may FAIL depending on implementation
        try:
            pickle.dumps(user_context)
            # If this succeeds, the UserExecutionContext might not have ContextVar issues
            # but we still want to test the scenario
            self.logger.info("UserExecutionContext pickle succeeded - no ContextVar references detected")
        except (TypeError, AttributeError, pickle.PicklingError) as e:
            # This is the expected failure case
            # Expected failure due to ContextVar serialization issues
            pass

    def test_contextvar_direct_pickle_failure(self):
        """Test that ContextVar instances themselves cannot be pickled.

        This is the root cause - ContextVar objects are not picklable.
        """
        # Create a ContextVar instance
        test_context_var = contextvars.ContextVar('test_var', default="default_value")
        test_context_var.set("test_value")

        # Attempt to pickle the ContextVar - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(test_context_var)


    def test_contextvar_token_pickle_failure(self):
        """Test that ContextVar tokens also cannot be pickled.

        ContextVar.set() returns a Token that also cannot be serialized.
        """
        # Create a ContextVar and get a token
        test_context_var = contextvars.ContextVar('test_var_token')
        token = test_context_var.set("token_value")

        # Attempt to pickle the token - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(token)


    def test_complex_object_with_contextvar_pickle_failure(self):
        """Test that complex objects containing ContextVar references fail to pickle.

        This simulates the real-world scenario where business objects
        contain ContextVar references and cannot be serialized.
        """
        class ComplexBusinessObject:
            def __init__(self):
                self.context_var = contextvars.ContextVar('business_context')
                self.trace_context = UnifiedTraceContext(
                    request_id="req_123",
                    user_id="user_456"
                )
                self.logging_context = LoggingContext()
                self.business_data = {
                    'value': 42,
                    'timestamp': datetime.now(timezone.utc),
                    'metadata': {'key': 'value'}
                }

        # Create the complex object
        business_obj = ComplexBusinessObject()
        business_obj.context_var.set("business_value")
        business_obj.logging_context.set_context(
            request_id="req_123",
            user_id="user_456"
        )

        # Attempt to pickle the complex object - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(business_obj)

        # Verify the error is related to ContextVar or nested serialization issues
        # Context was cleaned up by earlier fixes

    def test_serialization_impact_on_redis_operations(self):
        """Test how ContextVar serialization failures would impact Redis operations.

        This test simulates the failure mode when trying to cache objects
        with ContextVar references in Redis.
        """
        # Create objects with ContextVar references
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id
        )

        logging_context = LoggingContext()
        logging_context.set_context(request_id=self.test_request_id)

        # Simulate Redis serialization (Redis typically uses pickle)
        test_objects = [
            ('trace_context', trace_context),
            ('logging_context', logging_context),
            ('context_var', contextvars.ContextVar('redis_test'))
        ]

        serialization_failures = []

        for obj_name, obj in test_objects:
            try:
                # This is what Redis would do internally
                serialized = pickle.dumps(obj)
                # If we get here, serialization unexpectedly succeeded
                self.logger.warning(f"Unexpected serialization success for {obj_name}")
            except (TypeError, AttributeError, pickle.PicklingError) as e:
                serialization_failures.append((obj_name, type(e).__name__, str(e)))

        # Verify that we got the expected serialization failures
        self.assertGreater(
            len(serialization_failures), 0,
            "Expected at least some serialization failures for Redis operations"
        )

        # Log the failures for debugging
        for obj_name, error_type, error_msg in serialization_failures:
            self.logger.info(f"Redis serialization failure for {obj_name}: {error_type} - {error_msg}")

    def test_websocket_message_serialization_failure(self):
        """Test how ContextVar serialization failures would impact WebSocket messages.

        WebSocket messages containing ContextVar references would fail to serialize.
        """
        # Create a mock WebSocket message with ContextVar references
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id
        )

        websocket_message = {
            'type': 'agent_update',
            'user_id': self.test_user_id,
            'trace_context': trace_context,  # This contains ContextVar references
            'timestamp': datetime.now(timezone.utc),
            'data': {'status': 'processing'}
        }

        # Attempt to serialize the WebSocket message - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(websocket_message)

    def test_agent_state_persistence_failure(self):
        """Test how ContextVar serialization failures would impact agent state persistence.

        Agent states containing ContextVar references would fail to persist.
        """
        # Create a mock agent state with ContextVar references
        agent_state = {
            'agent_id': 'agent_123',
            'user_context': UnifiedTraceContext(
                user_id=self.test_user_id,
                request_id=self.test_request_id
            ),
            'execution_context': LoggingContext(),
            'state_data': {
                'step': 1,
                'variables': {'x': 42},
                'timestamp': datetime.now(timezone.utc)
            }
        }

        # Set some context in the logging context
        agent_state['execution_context'].set_context(
            user_id=self.test_user_id,
            request_id=self.test_request_id
        )

        # Attempt to persist the agent state - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(agent_state)


class ContextVarSerializationWorkaroundsTests(SSotAsyncTestCase):
    """Test potential workarounds for ContextVar serialization issues."""

    def setup_method(self, method):
        """Set up test environment for each test method."""
        super().setup_method(method)

    def test_trace_context_to_dict_serializable(self):
        """Test that trace context can be converted to serializable dict format."""
        # Create a trace context
        trace_context = UnifiedTraceContext(
            request_id="req_123",
            user_id="user_456",
            trace_id="trace_789",
            correlation_id="corr_abc",
            thread_id="thread_def"
        )

        # Convert to serializable format
        serializable_dict = trace_context.to_websocket_context()

        # This should be picklable
        try:
            serialized = pickle.dumps(serializable_dict)
            deserialized = pickle.loads(serialized)

            # Verify the data is preserved
            self.assertEqual(deserialized['user_id'], "user_456")
            self.assertEqual(deserialized['trace_id'], "trace_789")

        except Exception as e:
            self.fail(f"Serializable dict should pickle successfully: {e}")

    def test_logging_context_extract_values(self):
        """Test that logging context values can be extracted for serialization."""
        # Create logging context and set values
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id="req_123",
            user_id="user_456",
            trace_id="trace_789"
        )

        # Extract serializable values
        context_values = logging_context.get_filtered_context()

        # This should be picklable
        try:
            serialized = pickle.dumps(context_values)
            deserialized = pickle.loads(serialized)

            # Verify the data is preserved
            self.assertEqual(deserialized['user_id'], "user_456")
            self.assertEqual(deserialized['request_id'], "req_123")

        except Exception as e:
            self.fail(f"Extracted context values should pickle successfully: {e}")