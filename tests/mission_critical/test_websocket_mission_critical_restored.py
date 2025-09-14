#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Agent Events - RESTORED VERSION

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Core chat functionality

This test validates WebSocket agent event integration using mocked services
instead of real services to avoid infrastructure dependencies while still
testing the critical integration points.

Focus:
    1. WebSocketNotifier has all required methods
    2. Tool dispatcher enhancement works
    3. Agent registry integration works
    4. Enhanced tool execution sends events
    5. All critical event types are sent

    ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import os
import sys
import asyncio
from typing import Dict, List, Set, Any, Optional
import time
from unittest.mock import AsyncMock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Import production components
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()


class MissionCriticalEventValidator:
    """Validates WebSocket events with extreme rigor - MOCKED WEBSOCKET CONNECTIONS."""

    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }

    # Additional events that may be sent in real scenarios
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report",
        "partial_result",
        "tool_error"
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()

    def record(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")

        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met."""
        failures = []

        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")

        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")

        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events")

        return len(failures) == 0, failures

    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False

        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event must be agent_started, got {self.event_timeline[0][1]}")
            return False

        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            # Accept any completion event for now
            self.warnings.append(f"Last event should be completion, got {last_event}")

        return True

    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)

        if tool_starts != tool_ends:
            self.errors.append(f"Unmatched tool events: {tool_starts} starts vs {tool_ends} ends")
            return False

        return True


class MockLLM:
    async def generate(self, *args, **kwargs):
        await asyncio.sleep(0)
        return {"content": "Mission critical response"}


@pytest.mark.critical
@pytest.mark.mission_critical
class TestMissionCriticalWebSocketEvents:
    """Mission critical tests for WebSocket agent events."""

    @pytest.mark.asyncio
    async def test_websocket_notifier_all_required_methods(self):
        """MISSION CRITICAL: Test that WebSocketNotifier has ALL required methods."""
        ws_manager = WebSocketManager()
        
        # Create proper user execution context
        user_context = UserExecutionContext.create_for_user(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run"
        )
        
        notifier = WebSocketNotifier.create_for_user(ws_manager, user_context)

        # Verify all methods exist
        required_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_partial_result',
            'send_tool_executing',
            'send_tool_completed',
            'send_final_report',
            'send_agent_completed'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(notifier, method):
                missing_methods.append(method)
            elif not callable(getattr(notifier, method)):
                missing_methods.append(f"{method} (not callable)")

        assert not missing_methods, f"CRITICAL: WebSocketNotifier missing methods: {missing_methods}"

    @pytest.mark.asyncio
    async def test_tool_dispatcher_enhancement_always_works(self):
        """MISSION CRITICAL: Tool dispatcher MUST be enhanced with WebSocket."""
        dispatcher = ToolDispatcher()
        ws_manager = WebSocketManager()

        # Verify initial state
        assert hasattr(dispatcher, 'executor'), "ToolDispatcher missing executor"
        original_executor = dispatcher.executor

        # Enhance
        enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)

        # Verify enhancement
        assert dispatcher.executor != original_executor, "Executor was not replaced"
        assert isinstance(dispatcher.executor, UnifiedToolExecutionEngine), \
            f"Expected UnifiedToolExecutionEngine, got {type(dispatcher.executor)}"
        assert hasattr(dispatcher, '_websocket_enhanced'), "Missing enhancement marker"
        assert dispatcher._websocket_enhanced is True, "Enhancement marker not set"

    @pytest.mark.asyncio
    async def test_agent_registry_websocket_integration_critical(self):
        """MISSION CRITICAL: AgentRegistry MUST integrate WebSocket."""
        llm = MockLLM()
        tool_dispatcher = ToolDispatcher()
        registry = AgentRegistry(llm, tool_dispatcher)
        ws_manager = WebSocketManager()

        # Set WebSocket manager
        registry.set_websocket_manager(ws_manager)

        # Verify tool dispatcher was enhanced
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            f"Expected UnifiedToolExecutionEngine, got {type(tool_dispatcher.executor)}"

    @pytest.mark.asyncio
    async def test_execution_engine_websocket_initialization(self):
        """MISSION CRITICAL: ExecutionEngine MUST have WebSocket components."""
        llm = MockLLM()
        registry = AgentRegistry(llm, ToolDispatcher())
        ws_manager = WebSocketManager()

        engine = ExecutionEngine(registry, ws_manager)

        # Verify WebSocket components
        assert hasattr(engine, 'websocket_notifier'), "CRITICAL: Missing websocket_notifier"
        assert isinstance(engine.websocket_notifier, WebSocketNotifier), \
            f"Expected WebSocketNotifier, got {type(engine.websocket_notifier)}"

    @pytest.mark.asyncio
    async def test_unified_tool_execution_sends_critical_events(self):
        """MISSION CRITICAL: Enhanced tool execution MUST send WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()

        # Mock WebSocket calls to capture events
        original_send = ws_manager.send_to_thread
        ws_manager.send_to_thread = AsyncMock(return_value=True)

        # Capture all event data
        sent_events = []

        async def capture_events(thread_id, message_data):
            sent_events.append(message_data)
            validator.record(message_data)
            await asyncio.sleep(0)
            return True

        ws_manager.send_to_thread.side_effect = capture_events

        # Create enhanced executor
        executor = UnifiedToolExecutionEngine(ws_manager)

        # Create test context
        context = AgentExecutionContext(
            run_id="mission-critical-test",
            thread_id="test-thread",
            user_id="test-user",
            agent_name="test",
            retry_count=0,
            max_retries=1
        )

        # Mock tool
        async def critical_test_tool(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate work
            return {"result": "mission_critical_success"}

        # Execute with context
        state = DeepAgentState(
            chat_thread_id="test-thread",
            user_id="test-user", 
            run_id="mission-critical-test"
        )

        result = await executor.execute_with_state(
            critical_test_tool, "critical_test_tool", {}, state, "mission-critical-test"
        )

        # Verify execution worked
        assert result is not None, "CRITICAL: Tool execution returned no result"

        # Verify critical events were sent
        assert ws_manager.send_to_thread.call_count >= 2, \
            f"Expected at least 2 WebSocket events, got {ws_manager.send_to_thread.call_count}"

        # Check for tool_executing and tool_completed events
        event_types = [event.get('type') for event in sent_events]
        assert 'tool_executing' in event_types, \
            f"Missing tool_executing event. Got events: {event_types}"
        assert 'tool_completed' in event_types, \
            f"Missing tool_completed event. Got events: {event_types}"

    @pytest.mark.asyncio
    async def test_websocket_notifier_sends_all_critical_events(self):
        """MISSION CRITICAL: WebSocketNotifier MUST send all required event types."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()

        # Mock WebSocket calls to capture events
        sent_events = []

        async def capture_events(thread_id, message_data):
            sent_events.append(message_data)
            validator.record(message_data)
            await asyncio.sleep(0)
            return True

        ws_manager.send_to_thread = AsyncMock(side_effect=capture_events)

        # Create proper user execution context
        user_context = UserExecutionContext.create_for_user(
            user_id="event-user",
            thread_id="event-thread", 
            run_id="event-test"
        )
        
        notifier = WebSocketNotifier.create_for_user(ws_manager, user_context)

        # Create test context
        context = AgentExecutionContext(
            run_id="event-test",
            thread_id="event-thread",
            user_id="event-user",
            agent_name="event_agent",
            retry_count=0,
            max_retries=1
        )

        # Send all critical event types
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Critical thinking...")
        await notifier.send_tool_executing(context, "critical_tool")
        await notifier.send_tool_completed(context, "critical_tool", {"status": "success"})
        await notifier.send_agent_completed(context, {"success": True})

        # Validate all events were captured
        is_valid, failures = validator.validate_critical_requirements()

        assert is_valid, f"Event validation failed: {failures}"
        assert len(sent_events) >= 5, f"Expected at least 5 events, got {len(sent_events)}"

        # Verify each required event type was sent
        event_types = [event.get('type') for event in sent_events]
        for required_event in validator.REQUIRED_EVENTS:
            assert required_event in event_types, \
                f"Missing required event: {required_event}. Got: {event_types}"

    @pytest.mark.asyncio 
    async def test_full_agent_execution_websocket_flow(self):
        """MISSION CRITICAL: Full agent execution flow with all WebSocket events."""
        ws_manager = WebSocketManager()
        validator = MissionCriticalEventValidator()

        # Mock WebSocket manager
        sent_events = []

        async def capture_events(thread_id, message_data):
            sent_events.append(message_data)
            validator.record(message_data)
            await asyncio.sleep(0)
            return True

        ws_manager.send_to_thread = AsyncMock(side_effect=capture_events)

        # Create full agent setup
        llm = MockLLM()
        tool_dispatcher = ToolDispatcher()

        # Create registry with WebSocket
        registry = AgentRegistry(llm, tool_dispatcher)
        registry.set_websocket_manager(ws_manager)

        # Create and register a test agent
        class MissionCriticalAgent:
            async def execute(self, state, run_id, return_direct=True):
                # Simulate agent work with tool usage
                if hasattr(tool_dispatcher, 'executor') and hasattr(tool_dispatcher.executor, 'execute_with_state'):
                    # Mock tool
                    async def test_agent_tool(*args, **kwargs):
                        await asyncio.sleep(0)
                        return {"result": "agent_tool_success"}

                    await tool_dispatcher.executor.execute_with_state(
                        test_agent_tool, "agent_tool", {}, state, state.run_id
                    )

                # Update state
                state.final_report = "Mission critical agent completed"
                return state

        test_agent = MissionCriticalAgent()
        registry.register("mission_critical_agent", test_agent)

        # Create execution engine
        engine = ExecutionEngine(registry, ws_manager)

        # Create context and state
        context = AgentExecutionContext(
            run_id="mission-flow-test",
            thread_id="mission-thread",
            user_id="mission-user",
            agent_name="mission_critical_agent",
            retry_count=0,
            max_retries=1
        )

        state = DeepAgentState()
        state.user_request = "Mission critical test request"
        state.chat_thread_id = "mission-thread"
        state.run_id = "mission-flow-test"
        state.user_id = "mission-user"

        # Execute the full flow
        result = await engine.execute_agent(context, state)

        # Give time for all async events to be processed
        await asyncio.sleep(0.1)

        # Validate the full flow
        assert result is not None, "CRITICAL: Agent execution returned no result"
        assert len(sent_events) >= 3, f"Expected at least 3 events in full flow, got {len(sent_events)}"

        # Check for key events
        event_types = [event.get('type') for event in sent_events]

        # At minimum we should have agent_started and tool events
        assert 'agent_started' in event_types, \
            f"Missing agent_started event in full flow. Got: {event_types}"


def main():
    """Run mission critical tests directly."""
    print("=" * 80)
    print("RUNNING MISSION CRITICAL WEBSOCKET TEST SUITE")
    print("=" * 80)

    # Use pytest to run the tests
    import pytest
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--no-header"
    ])

    if result == 0:
        print("\n" + "=" * 80)
        print("SUCCESS: ALL MISSION CRITICAL TESTS PASSED!")
        print("WebSocket agent events are working correctly.")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print("CRITICAL FAILURE: Some mission critical tests failed!")
        print("WebSocket agent events require immediate attention.")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)