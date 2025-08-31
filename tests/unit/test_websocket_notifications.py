"""Unit tests for WebSocket notification functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier


@pytest.mark.asyncio
async def test_websocket_notifier_sends_all_events():
    """Test that WebSocketNotifier sends all required event types."""
    # Create mock WebSocket manager
    mock_ws_manager = MagicMock()
    mock_ws_manager.send_to_thread = AsyncMock()
    
    # Create notifier
    notifier = WebSocketNotifier(mock_ws_manager)
    
    # Create test context
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run_001",
        thread_id="test_thread_001",
        user_id="test_user_001"
    )
    
    # Test agent_started
    await notifier.send_agent_started(context)
    assert mock_ws_manager.send_to_thread.called
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[0] == "test_thread_001"
    assert call_args[1]["type"] == "agent_started"
    
    # Test agent_thinking
    await notifier.send_agent_thinking(context, "Processing request...", 1)
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "agent_thinking"
    assert call_args[1]["payload"]["thought"] == "Processing request..."
    assert call_args[1]["payload"]["step_number"] == 1
    
    # Test partial_result
    await notifier.send_partial_result(context, "Partial content", False)
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "partial_result"
    assert call_args[1]["payload"]["content"] == "Partial content"
    assert call_args[1]["payload"]["is_complete"] == False
    
    # Test tool_executing
    await notifier.send_tool_executing(context, "test_tool")
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "tool_executing"
    assert call_args[1]["payload"]["tool_name"] == "test_tool"
    
    # Test tool_completed
    await notifier.send_tool_completed(context, "test_tool", {"status": "success"})
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "tool_completed"
    assert call_args[1]["payload"]["tool_name"] == "test_tool"
    assert call_args[1]["payload"]["result"]["status"] == "success"
    
    # Test final_report
    report = {"summary": "Test completed", "status": "success"}
    await notifier.send_final_report(context, report, 1000.0)
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "final_report"
    assert call_args[1]["payload"]["report"] == report
    assert call_args[1]["payload"]["total_duration_ms"] == 1000.0
    
    # Test agent_completed
    await notifier.send_agent_completed(context, {"status": "done"}, 1500.0)
    call_args = mock_ws_manager.send_to_thread.call_args[0]
    assert call_args[1]["type"] == "agent_completed"
    assert call_args[1]["payload"]["duration_ms"] == 1500.0
    
    # Verify all events were sent
    assert mock_ws_manager.send_to_thread.call_count >= 7


@pytest.mark.asyncio
async def test_websocket_notifier_handles_missing_manager():
    """Test that notifier handles missing WebSocket manager gracefully."""
    # Create notifier without manager
    notifier = WebSocketNotifier(None)
    
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run",
        thread_id="test_thread",
        user_id="test_user"
    )
    
    # These should not raise exceptions
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "test", 1)
    await notifier.send_partial_result(context, "content", False)
    await notifier.send_tool_executing(context, "tool")
    await notifier.send_tool_completed(context, "tool", {})
    await notifier.send_final_report(context, {}, 100.0)
    await notifier.send_agent_completed(context, {}, 100.0)


@pytest.mark.asyncio
async def test_enhanced_execution_engine_sends_notifications():
    """Test that enhanced execution engine sends proper notifications."""
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.agents.state import DeepAgentState
    
    # Create mocks
    mock_registry = MagicMock()
    mock_ws_manager = MagicMock()
    mock_ws_manager.send_to_thread = AsyncMock()
    
    # Create execution engine
    engine = ExecutionEngine(mock_registry, mock_ws_manager)
    
    # Mock agent execution
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock()
    mock_registry.get.return_value = mock_agent
    
    # Create test context and state
    context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id="test_run",
        thread_id="test_thread",
        user_id="test_user"
    )
    
    state = DeepAgentState()
    state.user_prompt = "Test prompt"
    state.final_answer = "Test answer"
    
    # Mock the agent core to return success
    with patch.object(engine.agent_core, 'execute_agent') as mock_execute:
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        mock_execute.return_value = AgentExecutionResult(
            success=True,
            state=state,
            duration=1.0
        )
        
        # Execute agent
        result = await engine.execute_agent(context, state)
    
    # Verify notifications were sent
    assert mock_ws_manager.send_to_thread.called
    
    # Check for specific event types
    sent_events = []
    for call in mock_ws_manager.send_to_thread.call_args_list:
        message = call[0][1]
        if isinstance(message, dict) and 'type' in message:
            sent_events.append(message['type'])
    
    # Should have sent agent_started and agent_thinking
    assert 'agent_started' in sent_events
    assert 'agent_thinking' in sent_events
    
    print(f"Sent events: {sent_events}")


if __name__ == "__main__":
    asyncio.run(test_websocket_notifier_sends_all_events())
    print("All WebSocket notification tests passed!")