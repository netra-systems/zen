"""
Unit test to validate UnifiedWebSocketEmitter field name fixes.
This test validates the local changes to ensure correct field names in events.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


@pytest.mark.asyncio
async def test_agent_thinking_uses_reasoning_field():
    """Test that notify_agent_thinking uses 'reasoning' field instead of 'thought'."""
    # Mock WebSocket manager
    mock_manager = Mock()
    mock_manager.emit_critical_event = AsyncMock()
    mock_manager.is_connection_active = Mock(return_value=True)
    
    # Mock context with run_id
    mock_context = Mock()
    mock_context.run_id = "test_run_id"
    mock_context.user_id = "test_user"
    
    # Create emitter
    emitter = UnifiedWebSocketEmitter(
        manager=mock_manager,
        user_id="test_user",
        context=mock_context
    )
    
    # Call notify_agent_thinking
    await emitter.notify_agent_thinking(
        agent_name="test_agent",
        reasoning="This is my reasoning process"
    )
    
    # Verify emit_critical_event was called with correct field
    mock_manager.emit_critical_event.assert_called_once()
    call_args = mock_manager.emit_critical_event.call_args
    
    # Extract the data parameter
    data = call_args[1]['data']  # keyword argument 'data'
    
    # Verify the correct field name is used
    assert 'reasoning' in data, "Expected 'reasoning' field in agent_thinking event"
    assert data['reasoning'] == "This is my reasoning process"
    assert 'thought' not in data, "Should not have legacy 'thought' field"


@pytest.mark.asyncio
async def test_tool_executing_uses_tool_name_field():
    """Test that notify_tool_executing uses 'tool_name' field instead of 'tool'."""
    # Mock WebSocket manager
    mock_manager = Mock()
    mock_manager.emit_critical_event = AsyncMock()
    mock_manager.is_connection_active = Mock(return_value=True)
    
    # Mock context with run_id
    mock_context = Mock()
    mock_context.run_id = "test_run_id"
    mock_context.user_id = "test_user"
    
    # Create emitter
    emitter = UnifiedWebSocketEmitter(
        manager=mock_manager,
        user_id="test_user",
        context=mock_context
    )
    
    # Call notify_tool_executing
    await emitter.notify_tool_executing(
        tool_name="search_tool",
        metadata={"query": "test query"}
    )
    
    # Verify emit_critical_event was called with correct field
    mock_manager.emit_critical_event.assert_called_once()
    call_args = mock_manager.emit_critical_event.call_args
    
    # Extract the data parameter
    data = call_args[1]['data']  # keyword argument 'data'
    
    # Verify the correct field name is used
    assert 'tool_name' in data, "Expected 'tool_name' field in tool_executing event"
    assert data['tool_name'] == "search_tool"
    assert 'tool' not in data, "Should not have legacy 'tool' field"


@pytest.mark.asyncio
async def test_tool_completed_uses_tool_name_field():
    """Test that notify_tool_completed uses 'tool_name' field instead of 'tool'."""
    # Mock WebSocket manager
    mock_manager = Mock()
    mock_manager.emit_critical_event = AsyncMock()
    mock_manager.is_connection_active = Mock(return_value=True)
    
    # Mock context with run_id
    mock_context = Mock()
    mock_context.run_id = "test_run_id"
    mock_context.user_id = "test_user"
    
    # Create emitter
    emitter = UnifiedWebSocketEmitter(
        manager=mock_manager,
        user_id="test_user",
        context=mock_context
    )
    
    # Call notify_tool_completed
    await emitter.notify_tool_completed(
        tool_name="search_tool",
        metadata={"result": "search completed"}
    )
    
    # Verify emit_critical_event was called with correct field
    mock_manager.emit_critical_event.assert_called_once()
    call_args = mock_manager.emit_critical_event.call_args
    
    # Extract the data parameter
    data = call_args[1]['data']  # keyword argument 'data'
    
    # Verify the correct field name is used
    assert 'tool_name' in data, "Expected 'tool_name' field in tool_completed event"
    assert data['tool_name'] == "search_tool"
    assert 'tool' not in data, "Should not have legacy 'tool' field"


@pytest.mark.asyncio
async def test_backward_compatibility_reasoning_fallback():
    """Test backward compatibility: reasoning parameter takes precedence over thought."""
    # Mock WebSocket manager
    mock_manager = Mock()
    mock_manager.emit_critical_event = AsyncMock()
    mock_manager.is_connection_active = Mock(return_value=True)
    
    # Create emitter
    emitter = UnifiedWebSocketEmitter(
        manager=mock_manager,
        user_id="test_user"
    )
    
    # Call with both reasoning and thought (reasoning should win)
    await emitter.notify_agent_thinking(
        reasoning="New reasoning",
        thought="Old thought"
    )
    
    # Verify reasoning is used
    call_args = mock_manager.emit_critical_event.call_args
    data = call_args[1]['data']
    assert data['reasoning'] == "New reasoning"
    
    # Reset mock
    mock_manager.emit_critical_event.reset_mock()
    
    # Call with only thought parameter
    await emitter.notify_agent_thinking(
        thought="Only thought provided"
    )
    
    # Verify thought is mapped to reasoning field
    call_args = mock_manager.emit_critical_event.call_args
    data = call_args[1]['data']
    assert data['reasoning'] == "Only thought provided"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])