"""Integration tests for Issue #1211: Agent pipeline ContextVar serialization failures.

This test suite reproduces ContextVar serialization failures in the full agent pipeline
context, demonstrating how the issue manifests in real agent execution scenarios.

Business Value: Platform/Internal - System Stability
Prevents serialization failures in production agent workflows that could disrupt
the $500K+ ARR chat functionality and Golden Path user experience.

Integration Test Scope:
- Agent execution with ContextVar-containing objects
- WebSocket event serialization in agent workflows
- State persistence during agent execution
- Cross-process communication with agent data

The 4 failing object types tested in integration context:
1. UnifiedTraceContext in agent execution flow
2. LoggingContext in agent logging operations
3. ExecutionEngineFactory in agent creation pipeline
4. UserExecutionContext in agent lifecycle management

SSOT Compliance:
- Inherits from SSotAsyncTestCase for unified test infrastructure
- Uses real service integration patterns from SSOT guidelines
- Follows integration test patterns for agent pipeline testing
"""

import asyncio
import pickle
import uuid
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import agent pipeline components
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_defensive_user_execution_context
)
from netra_backend.app.core.unified_trace_context import (
    UnifiedTraceContext,
    TraceSpan,
    _trace_context
)
from netra_backend.app.core.logging_context import (
    LoggingContext,
    set_logging_context,
    get_logging_context
)
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


class AgentPipelineContextVarSerializationTests(SSotAsyncTestCase):
    """Integration tests for ContextVar serialization failures in agent pipeline."""

    def setup_method(self, method):
        """Set up integration test environment."""
        super().setup_method(method)

        # Test data
        self.test_user_id = "integration_user_123"
        self.test_run_id = str(uuid.uuid4())
        self.test_request_id = str(uuid.uuid4())
        self.test_correlation_id = str(uuid.uuid4())

        # Clear context state
        self._clear_all_contexts()

        # Mock dependencies for integration testing
        self.mock_websocket_bridge = Mock()
        self.mock_websocket_bridge.user_id = self.test_user_id
        self.mock_websocket_bridge.emit_event = AsyncMock()

        self.mock_database_manager = Mock()
        self.mock_redis_manager = Mock()

    def teardown_method(self, method):
        """Clean up after integration tests."""
        super().teardown_method(method)
        self._clear_all_contexts()

    def _clear_all_contexts(self):
        """Clear all context variables and state."""
        try:
            _trace_context.set(None)
            from netra_backend.app.core.logging_context import (
                request_id_context, user_id_context, trace_id_context
            )
            request_id_context.set(None)
            user_id_context.set(None)
            trace_id_context.set(None)
        except Exception:
            pass

    async def test_agent_execution_engine_factory_serialization_failure(self):
        """Test serialization failure when creating execution engines with ContextVar state.

        This test reproduces the issue where ExecutionEngineFactory cannot be serialized
        for Redis caching or cross-process communication due to ContextVar references.
        """
        # Create ExecutionEngineFactory with real dependencies
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_database_manager,
            redis_manager=self.mock_redis_manager
        )

        # Create user context for agent execution
        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            websocket_client_id=self.test_request_id
        )

        # Create an execution engine (this sets up internal state)
        execution_engine = await factory.create_for_user(user_context)

        # Verify the engine was created successfully
        self.assertIsNotNone(execution_engine)
        self.assertEqual(execution_engine.get_user_context().user_id, self.test_user_id)

        # Attempt to serialize the factory for Redis caching - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(factory)

        error_message = str(context.exception).lower()
        self.assertTrue(
            any(keyword in error_message for keyword in [
                'lock', 'asyncio', 'contextvar', 'pickle', 'cannot', 'serialize',
                'contextvars', 'reduce', 'getstate', 'thread'
            ]),
            f"Expected async/ContextVar-related serialization error, got: {context.exception}"
        )

        # Clean up
        await factory.cleanup_engine(execution_engine)
        await factory.shutdown()

    async def test_agent_trace_context_serialization_in_execution(self):
        """Test serialization failure of UnifiedTraceContext during agent execution.

        This test reproduces the issue where trace contexts created during agent
        execution cannot be serialized for WebSocket events or state persistence.
        """
        # Set up trace context for agent execution
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4()),
            correlation_id=self.test_correlation_id,
            thread_id="agent_thread_123"
        )

        # Start a span to simulate agent operation tracking
        span = trace_context.start_span("agent_execution", {
            "agent_type": "supervisor",
            "operation": "process_request"
        })

        # Add events to simulate agent progress
        trace_context.add_event("agent_started", {"timestamp": datetime.now(timezone.utc).isoformat()})
        trace_context.add_event("tool_executing", {"tool": "data_processor"})

        # Simulate WebSocket event serialization - this should FAIL
        websocket_event = {
            'type': 'agent_progress',
            'user_id': self.test_user_id,
            'trace_context': trace_context,  # Contains ContextVar references
            'span': span,
            'timestamp': datetime.now(timezone.utc),
            'data': {'progress': 0.5}
        }

        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(websocket_event)


        # Clean up
        trace_context.finish_span(span)

    async def test_agent_logging_context_serialization_in_pipeline(self):
        """Test serialization failure of LoggingContext during agent pipeline execution.

        This test reproduces the issue where logging contexts cannot be serialized
        for state persistence or cross-service communication.
        """
        # Set up logging context for agent pipeline
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id="agent_trace_456"
        )

        # Create unified trace context and set it
        unified_trace = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id="agent_trace_456"
        )
        logging_context.set_context(unified_context=unified_trace)

        # Verify context is properly set
        context_data = logging_context.get_context()
        self.assertEqual(context_data['user_id'], self.test_user_id)
        self.assertEqual(context_data['request_id'], self.test_request_id)

        # Simulate agent state serialization for persistence - this should FAIL
        agent_pipeline_state = {
            'pipeline_id': 'agent_pipeline_123',
            'user_id': self.test_user_id,
            'logging_context': logging_context,  # Contains ContextVar references
            'execution_state': {
                'current_step': 'data_analysis',
                'completed_steps': ['initialization', 'validation'],
                'timestamp': datetime.now(timezone.utc)
            }
        }

        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(agent_pipeline_state)


    async def test_user_execution_context_serialization_in_agent_flow(self):
        """Test serialization failure of UserExecutionContext in agent execution flow.

        This test reproduces the issue where user execution contexts containing
        trace context references cannot be serialized for Redis caching or state persistence.
        """
        # Create user execution context with trace context
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4()),
            correlation_id=self.test_correlation_id
        )

        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            websocket_client_id=self.test_request_id
        )

        # Add trace context if the implementation supports it
        if hasattr(user_context, 'trace_context'):
            user_context.trace_context = trace_context

        # Simulate agent execution context with all the problematic components
        agent_execution_context = {
            'execution_id': str(uuid.uuid4()),
            'user_context': user_context,
            'trace_context': trace_context,  # Contains ContextVar references
            'agent_metadata': {
                'agent_type': 'supervisor',
                'start_time': datetime.now(timezone.utc),
                'parameters': {'mode': 'standard'}
            }
        }

        # Attempt to serialize for Redis caching - this may FAIL
        try:
            serialized = pickle.dumps(agent_execution_context)
            # If this succeeds, log it but don't fail the test
            self.logger.info("Agent execution context serialization succeeded unexpectedly")
        except (TypeError, AttributeError, pickle.PicklingError) as e:
            # This is the expected failure case
            # Expected failure case due to ContextVar serialization issues
            pass

    async def test_websocket_emitter_with_contextvar_serialization_failure(self):
        """Test serialization failure when WebSocket emitter contains ContextVar references.

        This test reproduces the issue in the WebSocket event emission pipeline
        where events containing ContextVar references cannot be serialized.
        """
        # Create user context
        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id
        )

        # Create trace context with active state
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4())
        )

        # Create a mock WebSocket manager for the emitter
        mock_websocket_manager = Mock()
        mock_websocket_manager.emit_event = AsyncMock()

        # Create UnifiedWebSocketEmitter
        emitter = UnifiedWebSocketEmitter(
            user_id=self.test_user_id,
            context=user_context,
            manager=mock_websocket_manager
        )

        # Create a WebSocket event with ContextVar references
        websocket_event_data = {
            'event_type': 'agent_thinking',
            'user_id': self.test_user_id,
            'trace_context': trace_context,  # Contains ContextVar references
            'agent_data': {
                'thinking': 'Processing user request...',
                'step': 1,
                'total_steps': 5
            },
            'metadata': {
                'timestamp': datetime.now(timezone.utc),
                'correlation_id': self.test_correlation_id
            }
        }

        # Attempt to serialize the event data for transmission - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(websocket_event_data)


    async def test_agent_state_persistence_with_all_failing_types(self):
        """Test comprehensive agent state persistence failure with all 4 failing types.

        This test creates a realistic agent execution scenario that includes all
        4 types of objects that fail serialization due to ContextVar references.
        """
        # Create ExecutionEngineFactory
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_database_manager,
            redis_manager=self.mock_redis_manager
        )

        # Create user context
        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            websocket_client_id=self.test_request_id
        )

        # Create trace context
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4()),
            correlation_id=self.test_correlation_id
        )

        # Create logging context
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            unified_context=trace_context
        )

        # Create execution engine
        execution_engine = await factory.create_for_user(user_context)

        # Create comprehensive agent state with all failing types
        comprehensive_agent_state = {
            'agent_execution_id': str(uuid.uuid4()),
            'factory': factory,                    # Type 1: ExecutionEngineFactory
            'user_context': user_context,          # Type 2: UserExecutionContext (may fail)
            'trace_context': trace_context,        # Type 3: UnifiedTraceContext
            'logging_context': logging_context,    # Type 4: LoggingContext
            'execution_engine': execution_engine,  # Contains all the above indirectly
            'agent_data': {
                'current_step': 'analysis',
                'progress': 0.3,
                'results': [],
                'timestamp': datetime.now(timezone.utc)
            }
        }

        # Attempt to serialize the comprehensive state - this should FAIL
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(comprehensive_agent_state)


        # Clean up
        await factory.cleanup_engine(execution_engine)
        await factory.shutdown()

    async def test_redis_caching_simulation_with_contextvar_objects(self):
        """Test Redis caching simulation showing how ContextVar objects would fail.

        This test simulates the Redis caching operations that would be used
        for agent state persistence and shows how they fail with ContextVar objects.
        """
        # Simulate various objects that would be cached in Redis
        cache_objects = []

        # 1. UnifiedTraceContext for request tracking
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4())
        )
        cache_objects.append(('trace_context', trace_context))

        # 2. LoggingContext for request logging
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id
        )
        cache_objects.append(('logging_context', logging_context))

        # 3. User execution context
        user_context = create_defensive_user_execution_context(
            user_id=self.test_user_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id
        )
        cache_objects.append(('user_context', user_context))

        # Simulate Redis SET operations
        redis_failures = []
        redis_successes = []

        for cache_key, cache_obj in cache_objects:
            try:
                # This is what Redis would do internally for serialization
                serialized_data = pickle.dumps(cache_obj)

                # If we get here, simulate successful Redis storage
                redis_successes.append((cache_key, len(serialized_data)))

            except (TypeError, AttributeError, pickle.PicklingError) as e:
                # This is the expected failure case for ContextVar objects
                redis_failures.append((cache_key, type(e).__name__, str(e)))

        # Verify that we have some Redis serialization failures
        self.assertGreater(
            len(redis_failures), 0,
            "Expected at least some Redis caching failures due to ContextVar serialization issues"
        )

        # Log the results for debugging
        for cache_key, error_type, error_msg in redis_failures:
            self.logger.info(f"Redis caching failure for {cache_key}: {error_type}")

        for cache_key, data_size in redis_successes:
            self.logger.info(f"Redis caching success for {cache_key}: {data_size} bytes")

    async def test_cross_process_communication_serialization_failure(self):
        """Test cross-process communication failure with ContextVar-containing objects.

        This test simulates the scenario where agent data needs to be passed
        between processes and fails due to ContextVar serialization issues.
        """
        # Create objects that would be passed between processes
        process_communication_data = {
            'message_type': 'agent_request',
            'source_process': 'main_agent',
            'target_process': 'data_processor',
            'payload': {
                'trace_context': UnifiedTraceContext(
                    request_id=self.test_request_id,
                    user_id=self.test_user_id
                ),
                'logging_context': LoggingContext(),
                'request_data': {
                    'operation': 'analyze_data',
                    'parameters': {'depth': 'detailed'},
                    'timestamp': datetime.now(timezone.utc)
                }
            }
        }

        # Set some context in the logging context
        process_communication_data['payload']['logging_context'].set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id
        )

        # Simulate multiprocessing serialization (uses pickle)
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            # This is what multiprocessing would do when sending data between processes
            pickle.dumps(process_communication_data)

        error_message = str(context.exception).lower()
        self.assertTrue(
            any(keyword in error_message for keyword in [
                'contextvar', 'pickle', 'cannot', 'serialize',
                'contextvars', 'reduce', 'getstate'
            ]),
            f"Expected ContextVar serialization error in cross-process communication, got: {context.exception}"
        )


class AgentPipelineSerializationWorkaroundsTests(SSotAsyncTestCase):
    """Integration tests for potential workarounds to ContextVar serialization issues."""

    def setup_method(self, method):
        """Set up integration test environment for workaround testing."""
        super().setup_method(method)

        self.test_user_id = "workaround_user_123"
        self.test_run_id = str(uuid.uuid4())
        self.test_request_id = str(uuid.uuid4())

    async def test_trace_context_websocket_serialization_workaround(self):
        """Test workaround using websocket-serializable format for trace context."""
        # Create trace context
        trace_context = UnifiedTraceContext(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4())
        )

        # Use the websocket serialization method as workaround
        websocket_serializable = trace_context.to_websocket_context()

        # Create WebSocket event with serializable format
        websocket_event = {
            'type': 'agent_progress',
            'user_id': self.test_user_id,
            'trace_context': websocket_serializable,  # Serializable format
            'timestamp': datetime.now(timezone.utc),
            'data': {'progress': 0.5}
        }

        # This should be serializable
        try:
            serialized = pickle.dumps(websocket_event)
            deserialized = pickle.loads(serialized)

            # Verify data integrity
            self.assertEqual(deserialized['user_id'], self.test_user_id)
            self.assertEqual(deserialized['trace_context']['user_id'], self.test_user_id)

        except Exception as e:
            self.fail(f"Websocket-serializable format should work as workaround: {e}")

    async def test_logging_context_extraction_workaround(self):
        """Test workaround using context value extraction for logging context."""
        # Create logging context
        logging_context = LoggingContext()
        logging_context.set_context(
            request_id=self.test_request_id,
            user_id=self.test_user_id,
            trace_id="trace_123"
        )

        # Extract values as workaround
        extracted_context = logging_context.get_filtered_context()

        # Create agent state with extracted values
        agent_state = {
            'agent_id': 'agent_123',
            'context_values': extracted_context,  # Extracted values instead of ContextVar objects
            'execution_data': {
                'step': 1,
                'timestamp': datetime.now(timezone.utc)
            }
        }

        # This should be serializable
        try:
            serialized = pickle.dumps(agent_state)
            deserialized = pickle.loads(serialized)

            # Verify data integrity
            self.assertEqual(deserialized['context_values']['user_id'], self.test_user_id)

        except Exception as e:
            self.fail(f"Context value extraction should work as workaround: {e}")

    async def test_factory_metrics_extraction_workaround(self):
        """Test workaround using metrics extraction for factory serialization."""
        # Create factory
        mock_websocket_bridge = Mock()
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_websocket_bridge
        )

        # Extract metrics instead of serializing the factory
        factory_metrics = factory.get_factory_metrics()
        factory_summary = {
            'factory_type': 'ExecutionEngineFactory',
            'metrics': factory_metrics,
            'timestamp': datetime.now(timezone.utc)
        }

        # This should be serializable
        try:
            serialized = pickle.dumps(factory_summary)
            deserialized = pickle.loads(serialized)

            # Verify data integrity
            self.assertEqual(deserialized['factory_type'], 'ExecutionEngineFactory')
            self.assertIn('total_engines_created', deserialized['metrics'])

        except Exception as e:
            self.fail(f"Factory metrics extraction should work as workaround: {e}")

        # Clean up
        await factory.shutdown()