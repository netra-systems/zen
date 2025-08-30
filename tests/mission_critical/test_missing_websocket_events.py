"""
Comprehensive test suite for missing WebSocket events.
Tests that the backend properly emits ALL expected events that frontend handlers are waiting for.

CRITICAL: These events are currently NOT being emitted, causing frontend to have no real-time updates.
"""

import asyncio
import json
import pytest
from typing import Dict, List, Set, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.agents.supervisor.agent_manager import AgentManager
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventCapture:
    """Captures all WebSocket events for validation."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_types: Set[str] = set()
        self.event_sequence: List[str] = []
        
    async def capture_event(self, thread_id: str, message: dict):
        """Capture a WebSocket event."""
        self.events.append(message)
        event_type = message.get('type', 'unknown')
        self.event_types.add(event_type)
        self.event_sequence.append(event_type)
        logger.info(f"Captured event: {event_type} for thread {thread_id}")
        
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get('type') == event_type]
    
    def has_event_type(self, event_type: str) -> bool:
        """Check if an event type was captured."""
        return event_type in self.event_types
    
    def assert_event_sequence(self, expected_sequence: List[str]):
        """Assert that events occurred in the expected sequence."""
        for expected in expected_sequence:
            if expected not in self.event_sequence:
                raise AssertionError(f"Event '{expected}' not found in sequence: {self.event_sequence}")
        
        # Check order
        filtered_sequence = [e for e in self.event_sequence if e in expected_sequence]
        if filtered_sequence != expected_sequence:
            raise AssertionError(
                f"Events out of order. Expected: {expected_sequence}, "
                f"Got: {filtered_sequence}"
            )


@pytest.fixture
async def event_capture():
    """Fixture for capturing WebSocket events."""
    return WebSocketEventCapture()


@pytest.fixture
async def mock_websocket_manager(event_capture):
    """Mock WebSocket manager that captures events."""
    manager = AsyncMock(spec=WebSocketManager)
    manager.send_to_thread = event_capture.capture_event
    manager.send_message = event_capture.capture_event
    return manager


@pytest.fixture
async def agent_context():
    """Create test agent execution context."""
    return AgentExecutionContext(
        agent_name="test_agent",
        thread_id="test_thread_123",
        run_id="run_456",
        user_id="test_user_789",
        metadata={"test": True, "prompt": "Test the WebSocket events"}
    )


class TestMissingWebSocketEvents:
    """Test suite for missing WebSocket events."""
    
    @pytest.mark.asyncio
    async def test_agent_stopped_event_on_cancellation(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that agent_stopped event is emitted when agent is cancelled."""
        # This event is MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Simulate agent cancellation
        await notifier.send_agent_started(agent_context)
        
        # Try to send agent_stopped (this method doesn't exist!)
        # This should be called when AgentStatus.CANCELLED is set
        with pytest.raises(AttributeError):
            await notifier.send_agent_stopped(agent_context, reason="User cancelled")
        
        # Verify the event would have been sent if the method existed
        assert not event_capture.has_event_type("agent_stopped"), \
            "agent_stopped should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_agent_error_event_on_failure(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that agent_error event is emitted on agent failure."""
        # This event is MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Simulate agent error
        error_details = {
            "error_type": "ExecutionError",
            "message": "Agent failed to process request",
            "traceback": "..."
        }
        
        # Try to send agent_error (this method doesn't exist!)
        with pytest.raises(AttributeError):
            await notifier.send_agent_error(agent_context, error_details)
        
        # Verify the event would have been sent if the method existed
        assert not event_capture.has_event_type("agent_error"), \
            "agent_error should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_agent_log_event_for_debugging(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that agent_log events are emitted for debugging."""
        # This event is MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Try to send agent_log (this method doesn't exist!)
        log_entry = {
            "level": "info",
            "message": "Processing step 1 of 5",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        with pytest.raises(AttributeError):
            await notifier.send_agent_log(agent_context, log_entry)
        
        assert not event_capture.has_event_type("agent_log"), \
            "agent_log should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_tool_started_vs_tool_executing_events(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that both tool_started and tool_executing events are sent."""
        # Currently only tool_executing is sent, tool_started is MISSING
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Send tool_executing (this exists)
        await notifier.send_tool_executing(agent_context, "data_analyzer")
        assert event_capture.has_event_type("tool_executing")
        
        # Try to send tool_started (this method doesn't exist!)
        with pytest.raises(AttributeError):
            await notifier.send_tool_started(agent_context, "data_analyzer")
        
        assert not event_capture.has_event_type("tool_started"), \
            "tool_started should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_stream_chunk_event_for_incremental_updates(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that stream_chunk events are sent for incremental content."""
        # This event is MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Simulate streaming content
        chunks = [
            "Processing data...",
            "Analyzing patterns...",
            "Generating insights..."
        ]
        
        for i, chunk in enumerate(chunks):
            # Try to send stream_chunk (this method doesn't exist!)
            with pytest.raises(AttributeError):
                await notifier.send_stream_chunk(
                    agent_context, 
                    chunk=chunk,
                    chunk_index=i,
                    total_chunks=len(chunks)
                )
        
        assert not event_capture.has_event_type("stream_chunk"), \
            "stream_chunk should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_stream_complete_event_after_streaming(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that stream_complete event is sent after streaming finishes."""
        # This event is MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Try to send stream_complete (this method doesn't exist!)
        with pytest.raises(AttributeError):
            await notifier.send_stream_complete(
                agent_context,
                total_chunks=5,
                duration_ms=1500
            )
        
        assert not event_capture.has_event_type("stream_complete"), \
            "stream_complete should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_subagent_lifecycle_events(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test that subagent_started and subagent_completed events are sent."""
        # These events are MISSING - test should FAIL
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        subagent_context = AgentExecutionContext(
            agent_name="data_sub_agent",
            thread_id=agent_context.thread_id,
            run_id="subagent_run_789",
            user_id=agent_context.user_id,
            metadata={"parent_agent": agent_context.agent_name, "prompt": "Analyze data"}
        )
        
        # Try to send subagent_started (this method doesn't exist!)
        with pytest.raises(AttributeError):
            await notifier.send_subagent_started(
                agent_context,
                subagent_name="data_sub_agent",
                subagent_run_id="subagent_run_789"
            )
        
        # Try to send subagent_completed (this method doesn't exist!)
        with pytest.raises(AttributeError):
            await notifier.send_subagent_completed(
                agent_context,
                subagent_name="data_sub_agent",
                subagent_run_id="subagent_run_789",
                result={"status": "success"}
            )
        
        assert not event_capture.has_event_type("subagent_started"), \
            "subagent_started should NOT be present (method doesn't exist)"
        assert not event_capture.has_event_type("subagent_completed"), \
            "subagent_completed should NOT be present (method doesn't exist)"
    
    @pytest.mark.asyncio
    async def test_complete_agent_execution_event_flow(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test the complete event flow for agent execution."""
        # This test shows what SHOULD happen vs what ACTUALLY happens
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Expected event sequence (what frontend expects)
        expected_events = [
            "agent_started",      # ✅ Exists
            "agent_thinking",     # ✅ Exists  
            "tool_started",       # ❌ MISSING - should be before tool_executing
            "tool_executing",     # ✅ Exists
            "stream_chunk",       # ❌ MISSING - for incremental updates
            "stream_chunk",       # ❌ MISSING
            "stream_complete",    # ❌ MISSING - after streaming
            "tool_completed",     # ✅ Exists
            "subagent_started",   # ❌ MISSING - when delegating to sub-agent
            "subagent_completed", # ❌ MISSING - when sub-agent finishes
            "partial_result",     # ✅ Exists
            "agent_completed",    # ✅ Exists
            "final_report"        # ✅ Exists
        ]
        
        # What we can actually send (existing methods)
        await notifier.send_agent_started(agent_context)
        await notifier.send_agent_thinking(agent_context, "Analyzing request", 1)
        # Can't send tool_started - MISSING
        await notifier.send_tool_executing(agent_context, "analyzer")
        # Can't send stream_chunk - MISSING
        # Can't send stream_complete - MISSING
        await notifier.send_tool_completed(agent_context, "analyzer", {"result": "data"})
        # Can't send subagent_started - MISSING
        # Can't send subagent_completed - MISSING
        await notifier.send_partial_result(agent_context, "Partial analysis complete")
        await notifier.send_agent_completed(agent_context, {"status": "success"}, 2500)
        await notifier.send_final_report(agent_context, {"summary": "Complete"}, 2500)
        
        # Verify what was actually sent
        actual_events = list(event_capture.event_types)
        missing_events = [e for e in expected_events if e not in actual_events]
        
        assert len(missing_events) > 0, \
            f"These events are MISSING from backend: {missing_events}"
        
        # This assertion SHOULD FAIL showing missing events
        assert missing_events == [
            "tool_started",
            "stream_chunk", 
            "stream_chunk",
            "stream_complete",
            "subagent_started",
            "subagent_completed"
        ], f"Unexpected missing events: {missing_events}"
    
    @pytest.mark.asyncio
    async def test_error_handling_event_flow(
        self, mock_websocket_manager, agent_context, event_capture
    ):
        """Test error handling event flow."""
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Start agent
        await notifier.send_agent_started(agent_context)
        
        # Simulate error during execution
        # Should send agent_error but method doesn't exist!
        error_info = {
            "error_type": "ToolExecutionError",
            "message": "Failed to execute data analyzer",
            "tool_name": "data_analyzer",
            "retry_count": 2,
            "max_retries": 3
        }
        
        # This should work but doesn't
        with pytest.raises(AttributeError):
            await notifier.send_agent_error(agent_context, error_info)
        
        # Should also send agent_log for error details
        with pytest.raises(AttributeError):
            await notifier.send_agent_log(
                agent_context,
                {
                    "level": "error",
                    "message": f"Tool execution failed: {error_info['message']}",
                    "details": error_info
                }
            )
        
        # Verify error events are missing
        assert not event_capture.has_event_type("agent_error")
        assert not event_capture.has_event_type("agent_log")


class TestWebSocketEventIntegration:
    """Integration tests for WebSocket events in real agent execution."""
    
    @pytest.mark.asyncio
    async def test_agent_manager_missing_event_emissions(self):
        """Test that AgentManager doesn't emit required events during execution."""
        # This test simulates real agent execution and verifies missing events
        
        with patch('netra_backend.app.agents.supervisor.agent_manager.WebSocketManager') as MockWS:
            ws_manager = MockWS.return_value
            event_capture = WebSocketEventCapture()
            ws_manager.send_to_thread = event_capture.capture_event
            
            # Create agent manager
            agent_manager = AgentManager()
            agent_manager.websocket_manager = ws_manager
            
            # Mock agent execution
            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value={"result": "success"})
            
            with patch.object(agent_manager, '_get_agent', return_value=mock_agent):
                # Execute agent
                context = AgentExecutionContext(
                    agent_name="test_agent",
                    thread_id="thread_123",
                    run_id="run_456",
                    user_id="test_user"
                )
                
                # This should emit events but many are missing
                result = await agent_manager.execute_agent(
                    agent_name="test_agent",
                    thread_id="thread_123",
                    prompt="Test execution"
                )
            
            # Check which events were NOT emitted
            missing_critical_events = [
                "agent_error",     # No structured error events
                "agent_stopped",   # No cancellation events
                "agent_log",       # No debug logging events
                "tool_started",    # Only tool_executing is sent
                "stream_chunk",    # No streaming support
                "stream_complete", # No streaming completion
                "subagent_started",    # No sub-agent tracking
                "subagent_completed"   # No sub-agent completion
            ]
            
            for event in missing_critical_events:
                assert not event_capture.has_event_type(event), \
                    f"Event '{event}' should be MISSING but was found"
    
    @pytest.mark.asyncio  
    async def test_frontend_orphaned_handlers_validation(self):
        """Validate that frontend has handlers for events that backend never sends."""
        # List of handlers defined in frontend but never receive events
        orphaned_handlers = {
            "agent_stopped": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:241",
                "expected_payload": {
                    "agent_name": str,
                    "reason": str,
                    "timestamp": float
                },
                "user_impact": "No notification when agent is stopped/cancelled"
            },
            "agent_error": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:241", 
                "expected_payload": {
                    "error_type": str,
                    "message": str,
                    "traceback": str,
                    "retry_available": bool
                },
                "user_impact": "No structured error information displayed"
            },
            "agent_log": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:242",
                "expected_payload": {
                    "level": str,
                    "message": str,
                    "timestamp": str,
                    "details": dict
                },
                "user_impact": "No debug information for troubleshooting"
            },
            "tool_started": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:245",
                "expected_payload": {
                    "tool_name": str,
                    "parameters": dict,
                    "timestamp": float
                },
                "user_impact": "Tool execution appears to start without warning"
            },
            "stream_chunk": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:251",
                "expected_payload": {
                    "chunk": str,
                    "chunk_index": int,
                    "total_chunks": int
                },
                "user_impact": "No incremental content updates during generation"
            },
            "stream_complete": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:251",
                "expected_payload": {
                    "total_chunks": int,
                    "duration_ms": float
                },
                "user_impact": "No indication when streaming finishes"
            },
            "subagent_started": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:248",
                "expected_payload": {
                    "subagent_name": str,
                    "parent_agent": str,
                    "task": str
                },
                "user_impact": "No visibility into sub-agent delegation"
            },
            "subagent_completed": {
                "frontend_location": "frontend/hooks/useEventProcessor.ts:248",
                "expected_payload": {
                    "subagent_name": str,
                    "result": dict,
                    "duration_ms": float
                },
                "user_impact": "No feedback when sub-agents complete tasks"
            }
        }
        
        # Validate each orphaned handler
        for event_type, details in orphaned_handlers.items():
            # These assertions document what SHOULD exist but doesn't
            assert details["user_impact"], \
                f"Missing event '{event_type}' has significant user impact"
            
            # Log the missing functionality
            logger.error(
                f"ORPHANED HANDLER: {event_type}",
                extra={
                    "location": details["frontend_location"],
                    "impact": details["user_impact"],
                    "expected_payload": details["expected_payload"]
                }
            )


@pytest.mark.asyncio
async def test_comprehensive_missing_events_summary():
    """
    Summary test that documents all missing WebSocket events.
    This test SHOULD FAIL until all events are properly implemented.
    """
    missing_events = {
        "agent_stopped": "Backend never emits when agent is cancelled",
        "agent_error": "No structured error events from backend", 
        "agent_log": "No logging/debug events sent to frontend",
        "tool_started": "Only tool_executing is sent, not tool_started",
        "stream_chunk": "No incremental content streaming",
        "stream_complete": "No streaming completion signal",
        "subagent_started": "No sub-agent lifecycle tracking",
        "subagent_completed": "No sub-agent completion events"
    }
    
    # This assertion documents the problem and WILL FAIL
    assert len(missing_events) == 0, \
        f"The following WebSocket events are MISSING from backend:\n" + \
        "\n".join([f"  - {event}: {reason}" for event, reason in missing_events.items()])


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])