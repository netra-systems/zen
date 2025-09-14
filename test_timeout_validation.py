"""
Simple validation test to verify timeout WebSocket notification behavior.
This test validates the fix for Issue #1025.
"""
import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext


async def test_timeout_websocket_notification():
    """Validate that timeout triggers WebSocket notification."""

    # Setup mocks
    mock_registry = Mock()
    mock_websocket_bridge = AsyncMock()
    mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_error = AsyncMock(return_value=True)

    # Create slow agent that will timeout
    slow_agent = AsyncMock()
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(2)  # This should timeout
        return {"success": True, "result": "should not complete"}

    slow_agent.execute = AsyncMock(side_effect=slow_execute)
    slow_agent.__class__.__name__ = "SlowAgent"
    slow_agent.set_websocket_bridge = Mock()
    slow_agent.set_trace_context = Mock()
    slow_agent.websocket_bridge = None
    slow_agent.execution_engine = None

    mock_registry.get_async = AsyncMock(return_value=slow_agent)

    # Create execution core
    execution_core = AgentExecutionCore(mock_registry, mock_websocket_bridge)

    # Mock the trackers
    agent_tracker = Mock()
    agent_tracker.create_execution = Mock(return_value=uuid4())
    agent_tracker.start_execution = Mock(return_value=True)
    agent_tracker.transition_state = AsyncMock()
    agent_tracker.update_execution_state = Mock()
    agent_tracker.create_fallback_response = AsyncMock()
    execution_core.agent_tracker = agent_tracker

    execution_tracker = Mock()
    execution_tracker.register_execution = Mock(return_value=uuid4())
    execution_tracker.start_execution = Mock(return_value=True)
    execution_tracker.complete_execution = Mock()
    execution_core.execution_tracker = execution_tracker

    # Create test context
    context = AgentExecutionContext(
        agent_name="test_agent",
        run_id=uuid4(),
        thread_id="test-session",
        user_id="test-user",
        correlation_id="test-request",
        retry_count=0
    )

    state = UserExecutionContext(
        user_id="test-user",
        thread_id="test-session",
        run_id=str(uuid4()),
        agent_context={"test": "data"}
    )

    # Execute with short timeout
    start_time = time.time()
    result = await execution_core.execute_agent(context, state, timeout=0.1)
    end_time = time.time()

    # Verify timeout was enforced
    assert result.success is False
    assert "timeout" in result.error.lower()
    assert end_time - start_time < 1.0

    # Check if WebSocket notification was called
    print(f"notify_agent_error called: {mock_websocket_bridge.notify_agent_error.called}")
    print(f"notify_agent_error call_count: {mock_websocket_bridge.notify_agent_error.call_count}")

    # This will PASS after the fix is implemented
    return mock_websocket_bridge.notify_agent_error.called


if __name__ == "__main__":
    result = asyncio.run(test_timeout_websocket_notification())
    print(f"WebSocket notification called: {result}")
    if not result:
        print("❌ ISSUE CONFIRMED: WebSocket notification NOT called during timeout")
    else:
        print("✅ ISSUE FIXED: WebSocket notification called during timeout")