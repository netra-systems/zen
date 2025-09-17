class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
        raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

    #!/usr/bin/env python
        '''ADVANCED WEBSOCKET EVENT TESTS - Extended Coverage

        These tests provide deep validation of WebSocket event handling under
        extreme conditions, edge cases, and failure scenarios.

        CRITICAL: These tests ensure the chat UI remains functional under ALL conditions.
        '''

        import asyncio
        import json
        import time
        import random
        import uuid
        from collections import defaultdict, deque
        from concurrent.futures import ThreadPoolExecutor
        from datetime import datetime, timedelta
        from typing import Dict, List, Set, Any, Optional, Tuple
        import threading
        import weakref
        import gc
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        import pytest
        from loguru import logger

        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import ( )
        UnifiedToolExecutionEngine,
        enhance_tool_dispatcher_with_notifications
    
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
        from netra_backend.app.schemas.agent_models import DeepAgentState

    # Import test helpers
        from tests.mission_critical.test_helpers import SimpleWebSocketNotifier
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


    # ============================================================================
    # ADVANCED EVENT VALIDATORS
    # ============================================================================

class EventOrderValidator:
        "Validates complex event ordering requirements.""

    # Define valid state transitions
        STATE_TRANSITIONS = {
        None: [agent_started"],
        "agent_started: [agent_thinking", "tool_executing, agent_completed", "agent_fallback],
        agent_thinking": ["agent_thinking, tool_executing", "partial_result, agent_completed"],
        "tool_executing: [tool_completed"],
        "tool_completed: [tool_executing", "agent_thinking, partial_result", "agent_completed],
        partial_result": ["partial_result, tool_executing", "agent_thinking, agent_completed"],
        "agent_completed: [],  # Terminal state
        agent_fallback": ["agent_completed],  # Error recovery
        final_report": ["agent_completed]
    

    def __init__(self):
        pass
        self.state_history: List[Tuple[float, str, str]] = []  # (timestamp, event_type, request_id)
        self.current_states: Dict[str, str] = {}  # request_id -> current_state
        self.violations: List[str] = []
        self.start_time = time.time()

    def record_event(self, event: Dict) -> bool:
        ""Record event and validate state transition."
        timestamp = time.time() - self.start_time
        event_type = event.get("type, unknown")
        request_id = event.get("request_id, event.get(data", {}.get("request_id, unknown"))

        self.state_history.append((timestamp, event_type, request_id))

    # Get current state for this request
        current_state = self.current_states.get(request_id)

    # Validate transition
        valid_transitions = self.STATE_TRANSITIONS.get(current_state, []

        if event_type not in valid_transitions:
        violation = "formatted_string
        self.violations.append(violation)
        logger.error(violation)
        return False

        # Update state
        self.current_states[request_id] = event_type
        return True

    def validate_complete_flow(self, request_id: str) -> Tuple[bool, List[str]]:
        ""Validate that a request had a complete, valid flow."
        events = [item for item in []] == request_id]

        if not events:
        return False, ["No events found for request]

        errors = []

        # Must start with agent_started
        if events[0][1] != agent_started":
        errors.append(f"Flow didnt start with agent_started: {events[0][1]})

            # Must end with completion
        last_event = events[-1][1]
        if last_event not in ["agent_completed", final_report]:
        errors.append(f"Flow didn"t end with completion: {last_event})

                # Check for orphaned tool executions
        tool_starts = sum(1 for e in events if e[1] == tool_executing")
        tool_ends = sum(1 for e in events if e[1] == "tool_completed)
        if tool_starts != tool_ends:
        errors.append(formatted_string")

        return len(errors) == 0, errors


class EventTimingAnalyzer:
        "Analyzes timing patterns and detects anomalies.""

    def __init__(self, max_latency_ms: float = 100):
        pass
        self.max_latency_ms = max_latency_ms
        self.event_times: Dict[str, List[float]] = defaultdict(list)
        self.event_intervals: Dict[str, deque] = defaultdict(lambda x: None deque(maxlen=100))
        self.anomalies: List[Dict] = []

    def record_event(self, event: Dict) -> None:
        ""Record event timing."
        event_type = event.get("type, unknown")
        timestamp = time.time()

        self.event_times[event_type].append(timestamp)

    # Calculate interval since last event of same type
        if len(self.event_times[event_type] > 1:
        interval = (timestamp - self.event_times[event_type][-2] * 1000  # ms
        self.event_intervals[event_type].append(interval)

        # Detect timing anomalies
        if interval > self.max_latency_ms:
        self.anomalies.append({}
        "event_type: event_type,
        interval_ms": interval,
        "timestamp: timestamp,
        severity": "high if interval > self.max_latency_ms * 10 else medium"
            

    def get_statistics(self) -> Dict[str, Any]:
        "Get timing statistics.""
        stats = {}

        for event_type, intervals in self.event_intervals.items():
        if intervals:
        stats[event_type] = {
        count": len(self.event_times[event_type],
        "avg_interval_ms: sum(intervals) / len(intervals),
        max_interval_ms": max(intervals),
        "min_interval_ms: min(intervals),
        p95_interval_ms": sorted(intervals)[int(len(intervals) * 0.95)] if len(intervals) > 1 else 0
            

        stats["anomalies] = len(self.anomalies)
        stats[item for item in []] == high")

        return stats


class EventContentValidator:
        "Validates event content and data integrity.""

        REQUIRED_FIELDS = {
        agent_started": ["type, timestamp", "data],
        agent_thinking": ["type, timestamp", "data, data.message"],
        "tool_executing: [type", "timestamp, data", "data.tool_name],
        tool_completed": ["type, timestamp", "data, data.tool_name", "data.result],
        partial_result": ["type, timestamp", "data, data.content"],
        "agent_completed: [type", "timestamp, data"]
    

    def __init__(self):
        pass
        self.validation_errors: List[Dict] = []
        self.event_sizes: Dict[str, List[int]] = defaultdict(list)

    def validate_event(self, event: Dict) -> bool:
        "Validate event has required fields and proper structure.""
        event_type = event.get(type", "unknown)

    # Track event size
        event_size = len(json.dumps(event))
        self.event_sizes[event_type].append(event_size)

    # Check size limits (WebSocket frame limit)
        if event_size > 65536:  # 64KB limit
        self.validation_errors.append({}
        event_type": event_type,
        "error: formatted_string",
        "severity: critical"
    
        return False

    # Validate required fields
        required = self.REQUIRED_FIELDS.get(event_type, ["type, timestamp"]

        for field_path in required:
        if not self._check_field_path(event, field_path):
        self.validation_errors.append({}
        "event_type: event_type,
        error": "formatted_string,
        severity": "high
            
        return False

        return True

    def _check_field_path(self, obj: Dict, path: str) -> bool:
        ""Check if a nested field path exists."
        parts = path.split(".)
        current = obj

        for part in parts:
        if not isinstance(current, dict) or part not in current:
        return False
        current = current[part]

        return True


            # ============================================================================
            # ADVANCED TEST SCENARIOS
            # ============================================================================

class TestAdvancedEventOrdering:
        ""Tests for complex event ordering scenarios."

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_parallel_tool_execution_ordering(self):
"Test that parallel tool executions maintain proper event pairing.""
ws_manager = WebSocketManager()
order_validator = EventOrderValidator()

conn_id = parallel-tools"
mock_ws = Magic
async def capture(message):
data = json.loads(message) if isinstance(message, str) else message
order_validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

    # Create enhanced tool dispatcher
dispatcher = ToolDispatcher()
enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)

    # Register multiple tools using the registry
from langchain_core.tools import Tool

async def tool_a(data):
await asyncio.sleep(random.uniform(0.01, 0.05))
await asyncio.sleep(0)
return {"tool_a_result: data}

async def tool_b(data):
await asyncio.sleep(random.uniform(0.01, 0.05))
await asyncio.sleep(0)
return {tool_b_result": data}

async def tool_c(data):
await asyncio.sleep(random.uniform(0.01, 0.05))
await asyncio.sleep(0)
return {"tool_c_result: data}

    # Create tool objects and register them
tool_a_obj = Tool(name=tool_a", func=tool_a, description="Tool A)
tool_b_obj = Tool(name=tool_b", func=tool_b, description="Tool B)
tool_c_obj = Tool(name=tool_c", func=tool_c, description="Tool C)

dispatcher.registry.register_tool(tool_a_obj)
dispatcher.registry.register_tool(tool_b_obj)
dispatcher.registry.register_tool(tool_c_obj)

    # Execute tools in parallel
state = DeepAgentState()
state.thread_id = conn_id

tasks = [
dispatcher.executor.execute_with_state(tool_a, tool_a", {"data: a"}, state, "run-a),
dispatcher.executor.execute_with_state(tool_b, tool_b", {"data: b"}, state, "run-b),
dispatcher.executor.execute_with_state(tool_c, tool_c", {"data: c"}, state, "run-c)
    

await asyncio.gather(*tasks)
await asyncio.sleep(0.2)

    # Validate ordering
assert len(order_validator.violations) == 0, \
formatted_string"

    # Verify each tool had proper pairing
tool_events = [item for item in []]]
tool_starts = [item for item in []] == "tool_executing]
tool_ends = [item for item in []] == tool_completed"]

assert len(tool_starts) == 3, "formatted_string
assert len(tool_ends) == 3, formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_nested_agent_execution_events(self):
"Test event ordering with nested agent executions.""
pass
ws_manager = WebSocketManager()
order_validator = EventOrderValidator()

conn_id = nested-agents"
mock_ws = Magic
async def capture(message):
pass
data = json.loads(message) if isinstance(message, str) else message
order_validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Simulate nested agent execution
async def execute_nested_agents():
pass
    # Parent agent starts
await notifier.send_agent_started(conn_id, "parent-req, parent_agent")
await notifier.send_agent_thinking(conn_id, "parent-req, Starting sub-agents...")

    # Execute child agents in parallel
child_tasks = []
for i in range(3):
    async def execute_child(child_id=i):
pass
req_id = "formatted_string
await notifier.send_agent_started(conn_id, req_id, formatted_string")
await asyncio.sleep(random.uniform(0.01, 0.03))
await notifier.send_agent_thinking(conn_id, req_id, "formatted_string)
await asyncio.sleep(random.uniform(0.01, 0.03))
await notifier.send_agent_completed(conn_id, req_id, {child_result": child_id}

child_tasks.append(execute_child())

await asyncio.gather(*child_tasks)

    # Parent completes
await notifier.send_agent_completed(conn_id, "parent-req, {all_children_done": True}

await execute_nested_agents()
await asyncio.sleep(0.2)

    # Validate each request flow
for req_id in ["parent-req, child-0", "child-1, child-2"]:
    is_valid, errors = order_validator.validate_complete_flow(req_id)
assert is_valid, "formatted_string


class TestFailureInjection:
        ""Tests with injected failures and recovery scenarios."

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_websocket_disconnection_during_execution(self):
"Test that execution handles WebSocket disconnection gracefully.""
ws_manager = WebSocketManager()
events_before = []
events_after = []

conn_id = disconnect-test"

        # First connection
mock_ws1 = Magic
async def capture1(message):
data = json.loads(message) if isinstance(message, str) else message
events_before.append(data)

mock_ws1.send_json = AsyncMock(side_effect=capture1)
await ws_manager.connect_user(conn_id, mock_ws1, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Start execution
request_id = "disconnect-req
await notifier.send_agent_started(conn_id, request_id, agent")
await notifier.send_agent_thinking(conn_id, request_id, "Processing...)

    # Disconnect during execution
await ws_manager.disconnect_user(conn_id, mock_ws1, conn_id)

    # Continue sending events (should handle gracefully)
await notifier.send_tool_executing(conn_id, request_id, tool", {}
await notifier.send_tool_completed(conn_id, request_id, "tool, {result": "done}

    # Reconnect
mock_ws2 = Magic
async def capture2(message):
data = json.loads(message) if isinstance(message, str) else message
events_after.append(data)

mock_ws2.send_json = AsyncMock(side_effect=capture2)
await ws_manager.connect_user(conn_id, mock_ws2, conn_id)

    # Complete execution
await notifier.send_agent_completed(conn_id, request_id, {success": True}

await asyncio.sleep(0.2)

    # Verify events were captured appropriately
assert len(events_before) >= 2, "Should have events before disconnect
assert len(events_after) >= 1, Should have completion after reconnect"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_random_failure_injection(self):
"Test system resilience with random failures injected.""
pass
ws_manager = WebSocketManager()
timing_analyzer = EventTimingAnalyzer(max_latency_ms=500)

conn_id = chaos-test"
mock_ws = Magic
failure_count = 0

async def capture_with_failures(message):
pass
nonlocal failure_count

    # Randomly inject failures (10% chance)
if random.random() < 0.1:
    failure_count += 1
raise Exception("Simulated send failure)

data = json.loads(message) if isinstance(message, str) else message
timing_analyzer.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture_with_failures)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

        # Send many events with potential failures
for i in range(50):
    request_id = formatted_string"

try:
    await notifier.send_agent_started(conn_id, request_id, "agent)
await asyncio.sleep(random.uniform(0.001, 0.01))

await notifier.send_agent_thinking(conn_id, request_id, formatted_string")
await asyncio.sleep(random.uniform(0.001, 0.01))

if random.random() > 0.5:
    await notifier.send_tool_executing(conn_id, request_id, "tool, {}
await asyncio.sleep(random.uniform(0.001, 0.01))
await notifier.send_tool_completed(conn_id, request_id, tool", {"ok: True}

await notifier.send_agent_completed(conn_id, request_id, {iteration": i}
except Exception:
                        # Should handle failures gracefully
pass

await asyncio.sleep(0.5)

                        # Get statistics
stats = timing_analyzer.get_statistics()

logger.info("formatted_string)
logger.info(formatted_string")

                        # System should have handled failures
assert stats.get("agent_completed, {}.get(count", 0) > 0, \
"System should complete some executions despite failures


class TestPerformanceBenchmarks:
        ""Performance and throughput benchmarks."

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.fixture
    async def test_high_frequency_event_throughput(self):
"Test WebSocket can handle high-frequency event streams.""
ws_manager = WebSocketManager()

        # Track metrics
events_sent = 0
events_received = 0
latencies = []

conn_id = throughput-test"
mock_ws = Magic
async def capture(message):
nonlocal events_received
events_received += 1

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Send events at maximum rate
start_time = time.time()
target_events = 1000

async def send_burst():
nonlocal events_sent
for i in range(100):
    await notifier.send_agent_thinking(conn_id, "formatted_string, formatted_string")
events_sent += 1
        # No delay - maximum throughput

        # Send 10 bursts in parallel
tasks = [send_burst() for _ in range(10)]
await asyncio.gather(*tasks)

duration = time.time() - start_time

        # Allow processing
await asyncio.sleep(0.5)

        # Calculate metrics
throughput = events_received / duration
success_rate = (events_received / events_sent) * 100 if events_sent > 0 else 0

logger.info(f"Throughput test results:)
logger.info(formatted_string")
logger.info("formatted_string)
logger.info(formatted_string")
logger.info("formatted_string)
logger.info(formatted_string")

        # Performance requirements
assert throughput > 500, "formatted_string
assert success_rate > 95, formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_memory_leak_prevention(self):
"Test that WebSocket events don't cause memory leaks.""
pass
ws_manager = WebSocketManager()

            # Track object references
initial_objects = len(gc.get_objects())

            # Create and destroy many connections
for i in range(10):
    conn_id = formatted_string"
mock_ws = Magic            mock_ws.websocket = TestWebSocketConnection()

await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

                # Send many events
for j in range(100):
    await notifier.send_agent_thinking(conn_id, "formatted_string, formatted_string")

                    # Disconnect and cleanup
await ws_manager.disconnect_user(conn_id, mock_ws, conn_id)

                    # Force garbage collection
gc.collect()

                    # Final garbage collection
gc.collect()
await asyncio.sleep(0.5)
gc.collect()

                    # Check for memory leaks
final_objects = len(gc.get_objects())
object_growth = final_objects - initial_objects

logger.info("formatted_string)

                    # Allow some growth but not excessive
assert object_growth < 1000, formatted_string"


class TestEdgeCasesAndBoundaries:
    "Tests for edge cases and boundary conditions.""

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_extremely_large_event_payload(self):
""Test handling of very large event payloads."
ws_manager = WebSocketManager()
content_validator = EventContentValidator()

conn_id = "large-payload
mock_ws = Magic
async def capture(message):
data = json.loads(message) if isinstance(message, str) else message
content_validator.validate_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Create large payload (just under 64KB limit)
large_content = x" * 60000  # 60KB of data

await notifier.send_partial_result(conn_id, "large-req, large_content)

await asyncio.sleep(0.1)

    # Should handle large payload
assert len(content_validator.validation_errors) == 0, \
formatted_string"

    # Test oversized payload (should fail gracefully)
oversized_content = "x * 70000  # 70KB - too large

try:
    await notifier.send_partial_result(conn_id, oversized-req", oversized_content)
except Exception:
    pass  # Expected to fail

await asyncio.sleep(0.1)

            # Should have recorded the error
assert any(e["error].startswith(Event too large") for e in content_validator.validation_errors), \
"Should detect oversized events

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_rapid_connection_cycling(self):
""Test rapid connect/disconnect cycles."
pass
ws_manager = WebSocketManager()

events_by_connection = defaultdict(list)

                # Rapidly cycle connections
for cycle in range(10):
    conn_id = "formatted_string
mock_ws = Magic
async def capture(message, conn=conn_id):
pass
data = json.loads(message) if isinstance(message, str) else message
events_by_connection[conn].append(data)

mock_ws.send_json = AsyncMock(side_effect=capture)

    # Connect
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

    # Send event immediately
notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)
await notifier.send_agent_started(conn_id, formatted_string", "agent)

    # Disconnect immediately
await ws_manager.disconnect_user(conn_id, mock_ws, conn_id)

    # No delay between cycles - stress test

await asyncio.sleep(0.5)

    # Each connection should have received its event
successful_cycles = sum(1 for events in events_by_connection.values() if len(events) > 0)

assert successful_cycles >= 8, \
formatted_string"

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_unicode_and_special_characters(self):
"Test handling of Unicode and special characters in events.""
ws_manager = WebSocketManager()
received_events = []

conn_id = unicode-test"
mock_ws = Magic
async def capture(message):
data = json.loads(message) if isinstance(message, str) else message
received_events.append(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Test various Unicode and special characters
test_strings = [
"Hello [U+4E16][U+754C] [U+1F30D], # Emoji and Chinese
[U+041F]p[U+0438]vet m[U+0438]p",  # Cyrillic
"[U+0645][U+0631][U+062D][U+0628][U+0627] [U+0628][U+0627][U+0644][U+0639][U+0627][U+0644][U+0645],  # Arabic (RTL)

\t\r",  # Control characters
"null\x00byte,  # Null byte
'{nested": "json}',  # JSON in string
<script>alert('xss')</script>",  # HTML/XSS attempt
"; DROP TABLE users; --,  # SQL injection attempt
    

for i, test_str in enumerate(test_strings):
    await notifier.send_agent_thinking(conn_id, "formatted_string", test_str)

await asyncio.sleep(0.2)

        # All events should be received and properly encoded
assert len(received_events) == len(test_strings), \
formatted_string

        # Verify content integrity
for i, event in enumerate(received_events):
    content = event.get("data", {}.get(message, "")
            # Content should be preserved (possibly sanitized)
assert content, formatted_string


class TestSecurityAndIsolation:
        ""Security and isolation tests for WebSocket events.""

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_user_event_isolation(self):
"Test that events for one user don't leak to another."
ws_manager = WebSocketManager()

user1_events = []
user2_events = []

        # Create two user connections
user1_id = "user-1"
user2_id = user-2

mock_ws1 = Magic        async def capture1(message):
data = json.loads(message) if isinstance(message, str) else message
user1_events.append(data)
mock_ws1.send_json = AsyncMock(side_effect=capture1)

mock_ws2 = Magic        async def capture2(message):
data = json.loads(message) if isinstance(message, str) else message
user2_events.append(data)
mock_ws2.send_json = AsyncMock(side_effect=capture2)

await ws_manager.connect_user(user1_id, mock_ws1, user1_id)
await ws_manager.connect_user(user2_id, mock_ws2, user2_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

                # Send events to different users
await notifier.send_agent_started(user1_id, "req-1", agent)
await notifier.send_agent_thinking(user1_id, "req-1", User 1 data)

await notifier.send_agent_started(user2_id, "req-2", agent)
await notifier.send_agent_thinking(user2_id, "req-2", User 2 data)

await asyncio.sleep(0.2)

                # Verify isolation
assert len(user1_events) > 0, "User 1 should have events"
assert len(user2_events) > 0, User 2 should have events

                # Check no cross-contamination
for event in user1_events:
    data_str = json.dumps(event)
assert "User 2" not in data_str, User 1 received User 2 data!

for event in user2_events:
    data_str = json.dumps(event)
assert "User 1" not in data_str, User 2 received User 1 data!

@pytest.mark.asyncio
@pytest.mark.critical
    async def test_request_id_isolation(self):
""Test that events are properly isolated by request ID.""
pass
ws_manager = WebSocketManager()
events_by_request = defaultdict(list)

conn_id = request-isolation
mock_ws = Magic
async def capture(message):
pass
data = json.loads(message) if isinstance(message, str) else message
req_id = data.get("request_id", data.get(data, {}.get("request_id", unknown))
events_by_request[req_id].append(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

notifier = SimpleWebSocketNotifier.create_for_user(ws_manager)

    # Execute multiple requests in parallel
async def execute_request(req_id):
pass
await notifier.send_agent_started(conn_id, req_id, "formatted_string")
await asyncio.sleep(random.uniform(0.01, 0.03))
await notifier.send_agent_thinking(conn_id, req_id, formatted_string)
await asyncio.sleep(random.uniform(0.01, 0.03))
await notifier.send_agent_completed(conn_id, req_id, {"request": req_id}

    # Run 10 parallel requests
tasks = [execute_request(formatted_string) for i in range(10)]
await asyncio.gather(*tasks)

await asyncio.sleep(0.2)

    # Verify each request has its own events
for req_id in ["formatted_string" for i in range(10)]:
    events = events_by_request.get(req_id, []
assert len(events) >= 3, formatted_string

        # Verify all events belong to this request
for event in events:
    event_req_id = event.get("request_id", event.get(data, {}.get("request_id"))
assert event_req_id == req_id, formatted_string


            # ============================================================================
            # MULTI-AGENT COORDINATION TESTS
            # ============================================================================

class TestMultiAgentCoordination:
        ""Tests for multi-agent coordination and event flow.""

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.fixture
    async def test_supervisor_with_multiple_subagents(self):
"Test supervisor coordinating multiple sub-agents."
ws_manager = WebSocketManager()
order_validator = EventOrderValidator()

conn_id = "multi-agent"
mock_ws = Magic
async def capture(message):
data = json.loads(message) if isinstance(message, str) else message
order_validator.record_event(data)

mock_ws.send_json = AsyncMock(side_effect=capture)
await ws_manager.connect_user(conn_id, mock_ws, conn_id)

    # Create mock LLM and tools
class MockLLM:
    async def generate(self, *args, **kwargs):
        await asyncio.sleep(0)
        return {content: "Response", reasoning: "Reasoning"}

    # Setup components
        tool_dispatcher = ToolDispatcher()
        registry = AgentRegistry(), tool_dispatcher)
        registry.set_websocket_manager(ws_manager)

        engine = UserExecutionEngine(registry, ws_manager)

    # Simulate supervisor with sub-agents
    async def run_multi_agent_flow():
        supervisor_ctx = AgentExecutionContext( )
        agent_name=supervisor,
        request_id="supervisor-main",
        connection_id=conn_id,
        start_time=time.time(),
        retry_count=0,
        max_retries=1
    

    # Supervisor starts
        await engine.websocket_notifier.send_agent_started(supervisor_ctx)
        await engine.send_agent_thinking(supervisor_ctx, Delegating to sub-agents..., 1)

    # Execute sub-agents in parallel
        sub_agent_tasks = []

        for i in range(3):
    async def execute_subagent(agent_id=i):
        sub_ctx = AgentExecutionContext( )
        agent_name="formatted_string",
        request_id=formatted_string,
        connection_id=conn_id,
        start_time=time.time(),
        retry_count=0,
        max_retries=1
    

        await engine.websocket_notifier.send_agent_started(sub_ctx)
        await asyncio.sleep(random.uniform(0.01, 0.05))
        await engine.send_agent_thinking(sub_ctx, "formatted_string", 1)
        await asyncio.sleep(random.uniform(0.01, 0.05))
        await engine.websocket_notifier.send_agent_completed(sub_ctx)

        await asyncio.sleep(0)
        return formatted_string

        sub_agent_tasks.append(execute_subagent())

        results = await asyncio.gather(*sub_agent_tasks)

    # Supervisor completes
        await engine.send_partial_result(supervisor_ctx, "formatted_string", True)
        await engine.websocket_notifier.send_agent_completed(supervisor_ctx)

        await run_multi_agent_flow()
        await asyncio.sleep(0.5)

    # Validate flows
        for req_id in [supervisor-main, "sub-0", sub-1, "sub-2"]:
        is_valid, errors = order_validator.validate_complete_flow(req_id)
        assert is_valid, formatted_string

        # Verify no ordering violations
        assert len(order_validator.violations) == 0, \
        "formatted_string"


        if __name__ == "__main__":
        pass
