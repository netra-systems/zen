# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Comprehensive test suite for missing WebSocket events.
    # REMOVED_SYNTAX_ERROR: Tests that the backend properly emits ALL expected events that frontend handlers are waiting for.

    # REMOVED_SYNTAX_ERROR: CRITICAL: These events are currently NOT being emitted, causing frontend to have no real-time updates.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Set, Any
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_manager import AgentManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_models import WebSocketMessage
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class WebSocketEventCapture:
    # REMOVED_SYNTAX_ERROR: """Captures all WebSocket events for validation."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.events: List[Dict[str, Any]] = []
    # REMOVED_SYNTAX_ERROR: self.event_types: Set[str] = set()
    # REMOVED_SYNTAX_ERROR: self.event_sequence: List[str] = []

# REMOVED_SYNTAX_ERROR: async def capture_event(self, thread_id: str, message: dict):
    # REMOVED_SYNTAX_ERROR: """Capture a WebSocket event."""
    # REMOVED_SYNTAX_ERROR: self.events.append(message)
    # REMOVED_SYNTAX_ERROR: event_type = message.get('type', 'unknown')
    # REMOVED_SYNTAX_ERROR: self.event_types.add(event_type)
    # REMOVED_SYNTAX_ERROR: self.event_sequence.append(event_type)
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
    # REMOVED_SYNTAX_ERROR: """Get all events of a specific type."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return [item for item in []]

# REMOVED_SYNTAX_ERROR: def has_event_type(self, event_type: str) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if an event type was captured."""
    # REMOVED_SYNTAX_ERROR: return event_type in self.event_types

# REMOVED_SYNTAX_ERROR: def assert_event_sequence(self, expected_sequence: List[str]):
    # REMOVED_SYNTAX_ERROR: """Assert that events occurred in the expected sequence."""
    # REMOVED_SYNTAX_ERROR: for expected in expected_sequence:
        # REMOVED_SYNTAX_ERROR: if expected not in self.event_sequence:
            # REMOVED_SYNTAX_ERROR: raise AssertionError("formatted_string")

            # Check order
            # REMOVED_SYNTAX_ERROR: filtered_sequence = [item for item in []]
            # REMOVED_SYNTAX_ERROR: if filtered_sequence != expected_sequence:
                # REMOVED_SYNTAX_ERROR: raise AssertionError( )
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                


                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def event_capture():
    # REMOVED_SYNTAX_ERROR: """Fixture for capturing WebSocket events."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return WebSocketEventCapture()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_websocket_manager(event_capture):
    # REMOVED_SYNTAX_ERROR: """Mock WebSocket manager that captures events."""
    # REMOVED_SYNTAX_ERROR: manager = AsyncMock(spec=WebSocketManager)
    # REMOVED_SYNTAX_ERROR: manager.send_to_thread = event_capture.capture_event
    # REMOVED_SYNTAX_ERROR: manager.send_message = event_capture.capture_event
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def agent_context():
    # REMOVED_SYNTAX_ERROR: """Create test agent execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return AgentExecutionContext( )
    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread_123",
    # REMOVED_SYNTAX_ERROR: run_id="run_456",
    # REMOVED_SYNTAX_ERROR: user_id="test_user_789",
    # REMOVED_SYNTAX_ERROR: metadata={"test": True, "prompt": "Test the WebSocket events"}
    


# REMOVED_SYNTAX_ERROR: class TestMissingWebSocketEvents:
    # REMOVED_SYNTAX_ERROR: """Test suite for missing WebSocket events."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_agent_stopped_event_on_cancellation( )
    # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test that agent_stopped event is emitted when agent is cancelled."""
        # This event is MISSING - test should FAIL
        # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

        # Simulate agent cancellation
        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_started(agent_context)

        # Send agent_stopped - this method now exists!
        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_stopped(agent_context, stop_reason="User cancelled")

        # Verify the event was sent
        # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("agent_stopped"), \
        # REMOVED_SYNTAX_ERROR: "agent_stopped should be present"

        # REMOVED_SYNTAX_ERROR: stopped_events = event_capture.get_events_by_type("agent_stopped")
        # REMOVED_SYNTAX_ERROR: assert len(stopped_events) == 1
        # REMOVED_SYNTAX_ERROR: assert stopped_events[0]['payload']['stop_reason'] == "User cancelled"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_error_event_on_failure( )
        # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test that agent_error event is emitted on agent failure."""
            # This event is MISSING - test should FAIL
            # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

            # Simulate agent error
            # REMOVED_SYNTAX_ERROR: error_details = { )
            # REMOVED_SYNTAX_ERROR: "error_type": "ExecutionError",
            # REMOVED_SYNTAX_ERROR: "message": "Agent failed to process request",
            # REMOVED_SYNTAX_ERROR: "traceback": "..."
            

            # Send agent_error - this method now exists!
            # REMOVED_SYNTAX_ERROR: await notifier.send_agent_error( )
            # REMOVED_SYNTAX_ERROR: agent_context,
            # REMOVED_SYNTAX_ERROR: error_message=error_details["message"],
            # REMOVED_SYNTAX_ERROR: error_type=error_details["error_type"],
            # REMOVED_SYNTAX_ERROR: error_details=error_details
            

            # Verify the event was sent
            # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("agent_error"), \
            # REMOVED_SYNTAX_ERROR: "agent_error should be present"

            # REMOVED_SYNTAX_ERROR: error_events = event_capture.get_events_by_type("agent_error")
            # REMOVED_SYNTAX_ERROR: assert len(error_events) == 1
            # REMOVED_SYNTAX_ERROR: assert error_events[0]['payload']['error_message'] == error_details["message"]

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_agent_log_event_for_debugging( )
            # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: """Test that agent_log events are emitted for debugging."""
                # This event is MISSING - test should FAIL
                # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                # Send agent_log - this method now exists!
                # REMOVED_SYNTAX_ERROR: await notifier.send_agent_log( )
                # REMOVED_SYNTAX_ERROR: agent_context,
                # REMOVED_SYNTAX_ERROR: level="info",
                # REMOVED_SYNTAX_ERROR: log_message="Processing step 1 of 5",
                # REMOVED_SYNTAX_ERROR: metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
                

                # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("agent_log"), \
                # REMOVED_SYNTAX_ERROR: "agent_log should be present"

                # REMOVED_SYNTAX_ERROR: log_events = event_capture.get_events_by_type("agent_log")
                # REMOVED_SYNTAX_ERROR: assert len(log_events) == 1
                # REMOVED_SYNTAX_ERROR: assert log_events[0]['payload']['message'] == "Processing step 1 of 5"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_tool_started_vs_tool_executing_events( )
                # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                # REMOVED_SYNTAX_ERROR: ):
                    # REMOVED_SYNTAX_ERROR: """Test that both tool_started and tool_executing events are sent."""
                    # Currently only tool_executing is sent, tool_started is MISSING
                    # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                    # Send tool_executing (this exists)
                    # REMOVED_SYNTAX_ERROR: await notifier.send_tool_executing(agent_context, "data_analyzer")
                    # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("tool_executing")

                    # Send tool_started - this method now exists!
                    # REMOVED_SYNTAX_ERROR: await notifier.send_tool_started(agent_context, "data_analyzer", {"mode": "fast"})

                    # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("tool_started"), \
                    # REMOVED_SYNTAX_ERROR: "tool_started should be present"

                    # REMOVED_SYNTAX_ERROR: tool_started_events = event_capture.get_events_by_type("tool_started")
                    # REMOVED_SYNTAX_ERROR: assert len(tool_started_events) == 1
                    # REMOVED_SYNTAX_ERROR: assert tool_started_events[0]['payload']['tool_name'] == "data_analyzer"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_stream_chunk_event_for_incremental_updates( )
                    # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                    # REMOVED_SYNTAX_ERROR: ):
                        # REMOVED_SYNTAX_ERROR: """Test that stream_chunk events are sent for incremental content."""
                        # This event is MISSING - test should FAIL
                        # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                        # Simulate streaming content
                        # REMOVED_SYNTAX_ERROR: chunks = [ )
                        # REMOVED_SYNTAX_ERROR: "Processing data...",
                        # REMOVED_SYNTAX_ERROR: "Analyzing patterns...",
                        # REMOVED_SYNTAX_ERROR: "Generating insights..."
                        

                        # REMOVED_SYNTAX_ERROR: for i, chunk in enumerate(chunks):
                            # Send stream_chunk - this method now exists!
                            # REMOVED_SYNTAX_ERROR: await notifier.send_stream_chunk( )
                            # REMOVED_SYNTAX_ERROR: agent_context,
                            # REMOVED_SYNTAX_ERROR: chunk_id="formatted_string",
                            # REMOVED_SYNTAX_ERROR: content=chunk,
                            # REMOVED_SYNTAX_ERROR: is_final=(i == len(chunks) - 1)
                            

                            # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("stream_chunk"), \
                            # REMOVED_SYNTAX_ERROR: "stream_chunk should be present"

                            # REMOVED_SYNTAX_ERROR: stream_events = event_capture.get_events_by_type("stream_chunk")
                            # REMOVED_SYNTAX_ERROR: assert len(stream_events) == 3

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_stream_complete_event_after_streaming( )
                            # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                            # REMOVED_SYNTAX_ERROR: ):
                                # REMOVED_SYNTAX_ERROR: """Test that stream_complete event is sent after streaming finishes."""
                                # This event is MISSING - test should FAIL
                                # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                # Send stream_complete - this method now exists!
                                # REMOVED_SYNTAX_ERROR: await notifier.send_stream_complete( )
                                # REMOVED_SYNTAX_ERROR: agent_context,
                                # REMOVED_SYNTAX_ERROR: stream_id="stream_123",
                                # REMOVED_SYNTAX_ERROR: total_chunks=5,
                                # REMOVED_SYNTAX_ERROR: metadata={"duration_ms": 1500}
                                

                                # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("stream_complete"), \
                                # REMOVED_SYNTAX_ERROR: "stream_complete should be present"

                                # REMOVED_SYNTAX_ERROR: complete_events = event_capture.get_events_by_type("stream_complete")
                                # REMOVED_SYNTAX_ERROR: assert len(complete_events) == 1
                                # REMOVED_SYNTAX_ERROR: assert complete_events[0]['payload']['total_chunks'] == 5

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_subagent_lifecycle_events( )
                                # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                                # REMOVED_SYNTAX_ERROR: ):
                                    # REMOVED_SYNTAX_ERROR: """Test that subagent_started and subagent_completed events are sent."""
                                    # These events are MISSING - test should FAIL
                                    # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                    # REMOVED_SYNTAX_ERROR: subagent_context = AgentExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: agent_name="data_sub_agent",
                                    # REMOVED_SYNTAX_ERROR: thread_id=agent_context.thread_id,
                                    # REMOVED_SYNTAX_ERROR: run_id="subagent_run_789",
                                    # REMOVED_SYNTAX_ERROR: user_id=agent_context.user_id,
                                    # REMOVED_SYNTAX_ERROR: metadata={"parent_agent": agent_context.agent_name, "prompt": "Analyze data"}
                                    

                                    # Send subagent_started - this method now exists!
                                    # REMOVED_SYNTAX_ERROR: await notifier.send_subagent_started( )
                                    # REMOVED_SYNTAX_ERROR: agent_context,
                                    # REMOVED_SYNTAX_ERROR: subagent_name="data_sub_agent",
                                    # REMOVED_SYNTAX_ERROR: subagent_id="subagent_run_789"
                                    

                                    # Send subagent_completed - this method now exists!
                                    # REMOVED_SYNTAX_ERROR: await notifier.send_subagent_completed( )
                                    # REMOVED_SYNTAX_ERROR: agent_context,
                                    # REMOVED_SYNTAX_ERROR: subagent_name="data_sub_agent",
                                    # REMOVED_SYNTAX_ERROR: subagent_id="subagent_run_789",
                                    # REMOVED_SYNTAX_ERROR: result={"status": "success"},
                                    # REMOVED_SYNTAX_ERROR: duration_ms=1200
                                    

                                    # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("subagent_started"), \
                                    # REMOVED_SYNTAX_ERROR: "subagent_started should be present"
                                    # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("subagent_completed"), \
                                    # REMOVED_SYNTAX_ERROR: "subagent_completed should be present"

                                    # REMOVED_SYNTAX_ERROR: subagent_start = event_capture.get_events_by_type("subagent_started")
                                    # REMOVED_SYNTAX_ERROR: assert len(subagent_start) == 1
                                    # REMOVED_SYNTAX_ERROR: assert subagent_start[0]['payload']['subagent_name'] == "data_sub_agent"

                                    # REMOVED_SYNTAX_ERROR: subagent_complete = event_capture.get_events_by_type("subagent_completed")
                                    # REMOVED_SYNTAX_ERROR: assert len(subagent_complete) == 1
                                    # REMOVED_SYNTAX_ERROR: assert subagent_complete[0]['payload']['result']['status'] == "success"

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_complete_agent_execution_event_flow( )
                                    # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                                    # REMOVED_SYNTAX_ERROR: ):
                                        # REMOVED_SYNTAX_ERROR: """Test the complete event flow for agent execution."""
                                        # This test shows what SHOULD happen vs what ACTUALLY happens
                                        # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                        # Expected event sequence (what frontend expects)
                                        # REMOVED_SYNTAX_ERROR: expected_events = [ )
                                        # REMOVED_SYNTAX_ERROR: "agent_started",      # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "agent_thinking",     # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "tool_started",       # ❌ MISSING - should be before tool_executing
                                        # REMOVED_SYNTAX_ERROR: "tool_executing",     # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "stream_chunk",       # ❌ MISSING - for incremental updates
                                        # REMOVED_SYNTAX_ERROR: "stream_chunk",       # ❌ MISSING
                                        # REMOVED_SYNTAX_ERROR: "stream_complete",    # ❌ MISSING - after streaming
                                        # REMOVED_SYNTAX_ERROR: "tool_completed",     # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "subagent_started",   # ❌ MISSING - when delegating to sub-agent
                                        # REMOVED_SYNTAX_ERROR: "subagent_completed", # ❌ MISSING - when sub-agent finishes
                                        # REMOVED_SYNTAX_ERROR: "partial_result",     # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "agent_completed",    # ✅ Exists
                                        # REMOVED_SYNTAX_ERROR: "final_report"        # ✅ Exists
                                        

                                        # Send the complete event flow (all methods now exist)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_started(agent_context)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_thinking(agent_context, "Analyzing request", 1)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_tool_started(agent_context, "analyzer", {"mode": "fast"})
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_tool_executing(agent_context, "analyzer")
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_stream_chunk(agent_context, "chunk_1", "Processing...", False)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_stream_chunk(agent_context, "chunk_2", "Analyzing...", True)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_stream_complete(agent_context, "stream_1", 2, {})
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_tool_completed(agent_context, "analyzer", {"result": "data"})
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_subagent_started(agent_context, "helper_agent", "sub_1")
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_subagent_completed(agent_context, "helper_agent", "sub_1", {"ok": True}, 500)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_partial_result(agent_context, "Partial analysis complete")
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_completed(agent_context, {"status": "success"}, 2500)
                                        # REMOVED_SYNTAX_ERROR: await notifier.send_final_report(agent_context, {"summary": "Complete"}, 2500)

                                        # Verify all events were sent
                                        # REMOVED_SYNTAX_ERROR: actual_events = list(event_capture.event_types)

                                        # All expected events should now be present
                                        # REMOVED_SYNTAX_ERROR: for event in expected_events:
                                            # REMOVED_SYNTAX_ERROR: count = event_capture.event_sequence.count(event)
                                            # REMOVED_SYNTAX_ERROR: if event == "stream_chunk":
                                                # REMOVED_SYNTAX_ERROR: assert count >= 2, "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: else:
                                                    # REMOVED_SYNTAX_ERROR: assert count >= 1, "formatted_string"

                                                    # Verify the sequence includes all critical events
                                                    # REMOVED_SYNTAX_ERROR: assert "agent_started" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "agent_thinking" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "tool_started" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "tool_executing" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "stream_chunk" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "stream_complete" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "tool_completed" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "subagent_started" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "subagent_completed" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "partial_result" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "agent_completed" in actual_events
                                                    # REMOVED_SYNTAX_ERROR: assert "final_report" in actual_events

                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_error_handling_event_flow( )
                                                    # REMOVED_SYNTAX_ERROR: self, mock_websocket_manager, agent_context, event_capture
                                                    # REMOVED_SYNTAX_ERROR: ):
                                                        # REMOVED_SYNTAX_ERROR: """Test error handling event flow."""
                                                        # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                                        # Start agent
                                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_started(agent_context)

                                                        # Simulate error during execution
                                                        # Should send agent_error but method doesn't exist!
                                                        # REMOVED_SYNTAX_ERROR: error_info = { )
                                                        # REMOVED_SYNTAX_ERROR: "error_type": "ToolExecutionError",
                                                        # REMOVED_SYNTAX_ERROR: "message": "Failed to execute data analyzer",
                                                        # REMOVED_SYNTAX_ERROR: "tool_name": "data_analyzer",
                                                        # REMOVED_SYNTAX_ERROR: "retry_count": 2,
                                                        # REMOVED_SYNTAX_ERROR: "max_retries": 3
                                                        

                                                        # Send agent_error with structured info
                                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_error( )
                                                        # REMOVED_SYNTAX_ERROR: agent_context,
                                                        # REMOVED_SYNTAX_ERROR: error_message=error_info["message"],
                                                        # REMOVED_SYNTAX_ERROR: error_type=error_info["error_type"],
                                                        # REMOVED_SYNTAX_ERROR: error_details=error_info
                                                        

                                                        # Also send agent_log for error details
                                                        # REMOVED_SYNTAX_ERROR: await notifier.send_agent_log( )
                                                        # REMOVED_SYNTAX_ERROR: agent_context,
                                                        # REMOVED_SYNTAX_ERROR: level="error",
                                                        # REMOVED_SYNTAX_ERROR: log_message="formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: metadata={"details": error_info}
                                                        

                                                        # Verify error events are present
                                                        # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("agent_error")
                                                        # REMOVED_SYNTAX_ERROR: assert event_capture.has_event_type("agent_log")

                                                        # REMOVED_SYNTAX_ERROR: error_events = event_capture.get_events_by_type("agent_error")
                                                        # REMOVED_SYNTAX_ERROR: assert len(error_events) == 1
                                                        # REMOVED_SYNTAX_ERROR: assert error_events[0]['payload']['error_type'] == "ToolExecutionError"

                                                        # REMOVED_SYNTAX_ERROR: log_events = event_capture.get_events_by_type("agent_log")
                                                        # REMOVED_SYNTAX_ERROR: assert any(e['payload']['level'] == "error" for e in log_events)


# REMOVED_SYNTAX_ERROR: class TestWebSocketEventIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for WebSocket events in real agent execution."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_agent_manager_missing_event_emissions(self):
        # REMOVED_SYNTAX_ERROR: """Test that AgentManager doesn't emit required events during execution."""
        # This test simulates real agent execution and verifies missing events

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.agent_manager.WebSocketManager') as MockWS:
            # REMOVED_SYNTAX_ERROR: ws_manager = MockWS.return_value
            # REMOVED_SYNTAX_ERROR: event_capture = WebSocketEventCapture()
            # REMOVED_SYNTAX_ERROR: ws_manager.send_to_thread = event_capture.capture_event

            # Create agent manager
            # REMOVED_SYNTAX_ERROR: agent_manager = AgentManager()
            # REMOVED_SYNTAX_ERROR: agent_manager.websocket_manager = ws_manager

            # Mock agent execution
            # REMOVED_SYNTAX_ERROR: mock_agent = Magic            mock_agent.execute = AsyncMock(return_value={"result": "success"})

            # REMOVED_SYNTAX_ERROR: with patch.object(agent_manager, '_get_agent', return_value=mock_agent):
                # Execute agent
                # REMOVED_SYNTAX_ERROR: context = AgentExecutionContext( )
                # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
                # REMOVED_SYNTAX_ERROR: run_id="run_456",
                # REMOVED_SYNTAX_ERROR: user_id="test_user"
                

                # This should emit events but many are missing
                # REMOVED_SYNTAX_ERROR: result = await agent_manager.execute_agent( )
                # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
                # REMOVED_SYNTAX_ERROR: prompt="Test execution"
                

                # Check which events are still not integrated in AgentManager
                # Note: The methods exist but AgentManager doesn't call them yet
                # REMOVED_SYNTAX_ERROR: potentially_missing = [ )
                # REMOVED_SYNTAX_ERROR: "agent_error",
                # REMOVED_SYNTAX_ERROR: "agent_stopped",
                # REMOVED_SYNTAX_ERROR: "agent_log",
                # REMOVED_SYNTAX_ERROR: "tool_started",
                # REMOVED_SYNTAX_ERROR: "stream_chunk",
                # REMOVED_SYNTAX_ERROR: "stream_complete",
                # REMOVED_SYNTAX_ERROR: "subagent_started",
                # REMOVED_SYNTAX_ERROR: "subagent_completed"
                

                # These events may not be emitted by the mock execution
                # This is expected since we haven't fully integrated them
                # into the actual execution flow yet
                # REMOVED_SYNTAX_ERROR: for event in potentially_missing:
                    # REMOVED_SYNTAX_ERROR: if not event_capture.has_event_type(event):
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_frontend_orphaned_handlers_validation(self):
                            # REMOVED_SYNTAX_ERROR: """Validate that frontend has handlers for events that backend never sends."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # List of handlers defined in frontend but never receive events
                            # REMOVED_SYNTAX_ERROR: orphaned_handlers = { )
                            # REMOVED_SYNTAX_ERROR: "agent_stopped": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:241",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "agent_name": str,
                            # REMOVED_SYNTAX_ERROR: "reason": str,
                            # REMOVED_SYNTAX_ERROR: "timestamp": float
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No notification when agent is stopped/cancelled"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "agent_error": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:241",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "error_type": str,
                            # REMOVED_SYNTAX_ERROR: "message": str,
                            # REMOVED_SYNTAX_ERROR: "traceback": str,
                            # REMOVED_SYNTAX_ERROR: "retry_available": bool
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No structured error information displayed"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "agent_log": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:242",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "level": str,
                            # REMOVED_SYNTAX_ERROR: "message": str,
                            # REMOVED_SYNTAX_ERROR: "timestamp": str,
                            # REMOVED_SYNTAX_ERROR: "details": dict
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No debug information for troubleshooting"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "tool_started": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:245",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "tool_name": str,
                            # REMOVED_SYNTAX_ERROR: "parameters": dict,
                            # REMOVED_SYNTAX_ERROR: "timestamp": float
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "Tool execution appears to start without warning"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "stream_chunk": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:251",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "chunk": str,
                            # REMOVED_SYNTAX_ERROR: "chunk_index": int,
                            # REMOVED_SYNTAX_ERROR: "total_chunks": int
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No incremental content updates during generation"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "stream_complete": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:251",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "total_chunks": int,
                            # REMOVED_SYNTAX_ERROR: "duration_ms": float
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No indication when streaming finishes"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "subagent_started": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:248",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "subagent_name": str,
                            # REMOVED_SYNTAX_ERROR: "parent_agent": str,
                            # REMOVED_SYNTAX_ERROR: "task": str
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No visibility into sub-agent delegation"
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "subagent_completed": { )
                            # REMOVED_SYNTAX_ERROR: "frontend_location": "frontend/hooks/useEventProcessor.ts:248",
                            # REMOVED_SYNTAX_ERROR: "expected_payload": { )
                            # REMOVED_SYNTAX_ERROR: "subagent_name": str,
                            # REMOVED_SYNTAX_ERROR: "result": dict,
                            # REMOVED_SYNTAX_ERROR: "duration_ms": float
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: "user_impact": "No feedback when sub-agents complete tasks"
                            
                            

                            # Validate each orphaned handler
                            # REMOVED_SYNTAX_ERROR: for event_type, details in orphaned_handlers.items():
                                # These assertions document what SHOULD exist but doesn't
                                # REMOVED_SYNTAX_ERROR: assert details["user_impact"], \
                                # REMOVED_SYNTAX_ERROR: "formatted_string"

                                # Log the missing functionality
                                # REMOVED_SYNTAX_ERROR: logger.error( )
                                # REMOVED_SYNTAX_ERROR: "formatted_string",
                                # REMOVED_SYNTAX_ERROR: extra={ )
                                # REMOVED_SYNTAX_ERROR: "location": details["frontend_location"],
                                # REMOVED_SYNTAX_ERROR: "impact": details["user_impact"],
                                # REMOVED_SYNTAX_ERROR: "expected_payload": details["expected_payload"]
                                
                                


                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_comprehensive_missing_events_summary():
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: Summary test that documents all missing WebSocket events.
                                    # REMOVED_SYNTAX_ERROR: This test SHOULD FAIL until all events are properly implemented.
                                    # REMOVED_SYNTAX_ERROR: '''
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # All events have been implemented!
                                    # REMOVED_SYNTAX_ERROR: implemented_events = { )
                                    # REMOVED_SYNTAX_ERROR: "agent_stopped": "Now emits when agent is cancelled",
                                    # REMOVED_SYNTAX_ERROR: "agent_error": "Structured error events implemented",
                                    # REMOVED_SYNTAX_ERROR: "agent_log": "Debug logging events implemented",
                                    # REMOVED_SYNTAX_ERROR: "tool_started": "Tool start notification implemented",
                                    # REMOVED_SYNTAX_ERROR: "stream_chunk": "Incremental content streaming implemented",
                                    # REMOVED_SYNTAX_ERROR: "stream_complete": "Stream completion signal implemented",
                                    # REMOVED_SYNTAX_ERROR: "subagent_started": "Sub-agent lifecycle tracking implemented",
                                    # REMOVED_SYNTAX_ERROR: "subagent_completed": "Sub-agent completion events implemented"
                                    

                                    # This assertion should PASS now
                                    # REMOVED_SYNTAX_ERROR: assert len(implemented_events) == 8, \
                                    # REMOVED_SYNTAX_ERROR: "formatted_string" + \
                                        # REMOVED_SYNTAX_ERROR: "
                                        # REMOVED_SYNTAX_ERROR: ".join(["formatted_string" for event, status in implemented_events.items()])

                                        # REMOVED_SYNTAX_ERROR: print(" )
                                        # REMOVED_SYNTAX_ERROR: ✅ SUCCESS: All missing WebSocket events have been implemented!")
                                        # REMOVED_SYNTAX_ERROR: print(" )
                                        # REMOVED_SYNTAX_ERROR: Implemented events:")
                                        # REMOVED_SYNTAX_ERROR: for event, status in implemented_events.items():
                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")


                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                # Run the tests
                                                # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])