"""Test to expose ExecutionContext missing timestamp attribute issue."""

import pytest
from datetime import datetime, timezone
import time

from netra_backend.app.agents.base.execution_context import (
    ExecutionContext,
    ExecutionMetadata,
    AgentExecutionContext
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


class TestExecutionContextTimestamp:
    """Tests to verify ExecutionContext has timestamp attribute."""

    def test_execution_context_has_timestamp_attribute(self):
        """Test that ExecutionContext has a timestamp attribute."""
        # Create execution context
        context_id = "test-context-123"
        metadata = ExecutionMetadata(
            agent_id="test-agent",
            operation="test-operation"
        )

        # Create context
        context = ExecutionContext(context_id, metadata)

        # This should not raise AttributeError
        # Currently fails with: AttributeError: 'ExecutionContext' object has no attribute 'timestamp'
        assert hasattr(context, 'timestamp'), "ExecutionContext should have timestamp attribute"
        assert context.timestamp is not None, "timestamp should be initialized"
        assert isinstance(context.timestamp, (float, datetime)), "timestamp should be float or datetime"

    def test_agent_execution_context_has_timestamp(self):
        """Test that AgentExecutionContext has a timestamp attribute."""
        context = AgentExecutionContext(
            context_id="agent-context-123",
            agent_id="test-agent",
            operation="data-analysis"
        )

        # This should not raise AttributeError
        assert hasattr(context, 'timestamp'), "AgentExecutionContext should have timestamp attribute"
        assert context.timestamp is not None, "timestamp should be initialized"

    def test_execution_context_timestamp_in_unified_error_handler_scenario(self):
        """Simulate the scenario from unified_error_handler.py line 678."""
        # Create a mock agent error with context
        from unittest.mock import Mock

        # Mock AgentError
        error = Mock()
        error.message = "Data analysis failed"
        error.recoverable = False

        # Create actual ExecutionContext as it would be in the error
        context = ExecutionContext("error-context", ExecutionMetadata(
            agent_id="data-analyzer",
            operation="analyze"
        ))
        error.context = context

        # This simulates what unified_error_handler.py line 678 does
        # Currently fails with: AttributeError: 'ExecutionContext' object has no attribute 'timestamp'
        try:
            timestamp = error.context.timestamp if error.context else datetime.now(timezone.utc)
            assert timestamp is not None
        except AttributeError as e:
            pytest.fail(f"ExecutionContext missing timestamp attribute: {e}")

    def test_execution_metadata_has_timestamp_compatibility(self):
        """Test ExecutionMetadata provides timestamp through start_time."""
        metadata = ExecutionMetadata(
            agent_id="test",
            operation="test-op"
        )

        # Metadata has start_time which is effectively a timestamp
        assert hasattr(metadata, 'start_time')
        assert metadata.start_time is not None
        assert isinstance(metadata.start_time, float)

        # Verify it's a recent timestamp
        now = time.time()
        assert abs(now - metadata.start_time) < 1.0  # Within 1 second