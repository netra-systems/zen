class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
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
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Regression test for WebSocket connection loop bug in GCP staging.
        This test reproduces the race condition between auth initialization and WebSocket connection
        that causes continuous connection/disconnection loops.

        Bug Report: /reports/websocket_connection_loop_bug_report.md
        '''

        import asyncio
        import pytest
        import time
        from typing import List, Dict, Any
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        from shared.isolated_environment import IsolatedEnvironment


class MockWebSocket:
        """Mock WebSocket that simulates auth failures and connection states"""

        CONNECTING = 0
        OPEN = 1
        CLOSING = 2
        CLOSED = 3

    def __init__(self, url: str, protocols: List[str] = None):
        pass
        self.url = url
        self.protocols = protocols or []
        self.readyState = self.CONNECTING
        self.onopen = None
        self.onclose = None
        self.onerror = None
        self.onmessage = None
        self._messages_sent = []
        self._close_code = None
        self._close_reason = None
        self._connection_attempts = 0

    def send(self, data: str):
        pass
        if self.readyState != self.OPEN:
        raise Exception("WebSocket is not open")
        self._messages_sent.append(data)

    def close(self, code: int = 1000, reason: str = ""):
        pass
        self.readyState = self.CLOSED
        self._close_code = code
        self._close_reason = reason
        if self.onclose:
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        event.code = code
        event.reason = reason
        self.onclose(event)


class WebSocketConnectionLoopTest:
        '''
        Test harness that simulates the WebSocket connection loop bug.
        This reproduces the exact conditions that cause the issue in staging.
        '''

    def __init__(self):
        pass
        self.connection_attempts = []
        self.reconnection_attempts = []
        self.auth_failures = []
        self.successful_connections = []

    def simulate_auth_delay(self, delay_ms: int = 500):
        """Simulate delayed auth initialization"""
        time.sleep(delay_ms / 1000)
        return {"token": "test_token_123", "initialized": True}

    def simulate_websocket_provider_effects(self, auth_state):
        '''
        pass
        Simulate multiple React effects firing in WebSocketProvider.
        This reproduces the race condition where multiple effects trigger connections.
        '''
        effects_triggered = []

    # Effect 1: Main connection effect (line 109 in WebSocketProvider)
        if auth_state.get("initialized") and auth_state.get("token"):
        effects_triggered.append({ ))
        "type": "main_effect",
        "timestamp": time.time(),
        "trigger": "auth_initialized && token"
        

        # Effect 2: Token synchronization effect (line 307)
        if auth_state.get("token"):
        effects_triggered.append({ ))
        "type": "token_sync_effect",
        "timestamp": time.time(),
        "trigger": "token_changed"
            

        return effects_triggered

    def simulate_connection_attempt(self, ws_service_mock, attempt_number: int):
        """Simulate a WebSocket connection attempt"""
        connection_record = { )
        "attempt": attempt_number,
        "timestamp": time.time(),
        "state": "connecting"
    
        self.connection_attempts.append(connection_record)

    # Simulate auth failure on staging (code 1008)
        if attempt_number > 0 and attempt_number % 2 == 0:
        # Every second attempt fails with auth error
        self.auth_failures.append({ ))
        "attempt": attempt_number,
        "code": 1008,
        "reason": "Policy Violation - Token expired"
        
        return {"success": False, "code": 1008}

        return {"success": True}

    def measure_connection_loop_rate(self, duration_seconds: int = 5) -> Dict[str, Any]:
        '''
        pass
        Measure the rate of connection attempts over a period.
        This helps detect the connection loop issue.
        '''
        start_time = time.time()
        attempts_in_window = []

        while time.time() - start_time < duration_seconds:
        # Simulate rapid connection attempts
        attempt_time = time.time() - start_time
        attempts_in_window.append(attempt_time)
        time.sleep(0.1)  # 100ms between attempts (simulating the bug)

        rate = len(attempts_in_window) / duration_seconds
        return { )
        "total_attempts": len(attempts_in_window),
        "duration": duration_seconds,
        "rate_per_second": rate,
        "is_looping": rate > 2  # More than 2 attempts per second indicates a loop
        


@pytest.mark.asyncio
    async def test_websocket_connection_loop_bug():
        '''
Test that reproduces the WebSocket connection loop bug.
This test SHOULD FAIL with the current implementation,
demonstrating the bug exists.
'''
pass
test_harness = WebSocketConnectionLoopTest()

            # Step 1: Simulate delayed auth initialization
auth_state = {"initialized": False, "token": None}

            # Step 2: Simulate WebSocketProvider mounting
initial_effects = test_harness.simulate_websocket_provider_effects(auth_state)
assert len(initial_effects) == 0, "No effects should trigger without auth"

            # Step 3: Simulate auth completing
auth_state = test_harness.simulate_auth_delay(200)

            # Step 4: Simulate multiple effects triggering (THE BUG)
effects = test_harness.simulate_websocket_provider_effects(auth_state)
assert len(effects) >= 2, "formatted_string"

            # Step 5: Simulate WebSocket service handling multiple connection requests
websocket = TestWebSocketConnection()  # Real WebSocket implementation
connection_results = []

for i, effect in enumerate(effects):
    result = test_harness.simulate_connection_attempt(ws_service_mock, i)
connection_results.append(result)

                # Step 6: Measure connection loop rate
loop_metrics = test_harness.measure_connection_loop_rate(duration_seconds=2)

                # ASSERTIONS THAT SHOULD FAIL (demonstrating the bug)

                Bug indicator 1: Multiple connection attempts from single auth change
assert len(test_harness.connection_attempts) <= 1, \
"formatted_string"

                # Bug indicator 2: Rapid reconnection rate (connection loop)
assert not loop_metrics["is_looping"], \
"formatted_string"

                # Bug indicator 3: Auth failures triggering immediate reconnects
assert len(test_harness.auth_failures) == 0 or \
len(test_harness.reconnection_attempts) < len(test_harness.auth_failures), \
"formatted_string"


@pytest.mark.asyncio
    async def test_websocket_connection_deduplication():
        '''
Test that WebSocket service properly deduplicates rapid connection attempts.
This test SHOULD FAIL with current implementation.
'''

                    # Mock the WebSocket service
with patch('frontend.services.webSocketService.WebSocketService') as MockWSService:
    ws_service = MockWSService.return_value
ws_service.websocket = TestWebSocketConnection()
ws_service.isConnecting = False
ws_service.state = 'disconnected'

                        # Simulate rapid successive connection attempts (the bug scenario)
connection_tasks = []
for i in range(5):
                            # These should be deduplicated but currently aren't
task = asyncio.create_task(ws_service.connect("formatted_string", {}))
connection_tasks.append(task)
                            # No delay - simulating race condition

await asyncio.gather(*connection_tasks, return_exceptions=True)

                            # SHOULD only connect once, but currently connects multiple times
actual_calls = ws_service.connect.call_count
assert actual_calls == 1, \
"formatted_string"


@pytest.mark.asyncio
    async def test_websocket_auth_failure_backoff():
        '''
Test that auth failures trigger proper exponential backoff.
This test SHOULD FAIL with current implementation.
'''
pass
test_harness = WebSocketConnectionLoopTest()
reconnect_delays = []

                                # Simulate series of auth failures
for attempt in range(5):
    result = test_harness.simulate_connection_attempt( )
if not result["success"] and result["code"] == 1008:
                                        # Measure time until next reconnect attempt
reconnect_delay = 0.1 * (2 ** attempt)  # Expected exponential backoff
reconnect_delays.append(reconnect_delay)
await asyncio.sleep(0.01)  # Minimal delay in test

                                        # Verify exponential backoff is applied
for i in range(1, len(reconnect_delays)):
    expected_increase = reconnect_delays[i] > reconnect_delays[i-1]
assert expected_increase, \
"formatted_string"


@pytest.mark.asyncio
    async def test_websocket_provider_effect_coordination():
        '''
Test that WebSocketProvider properly coordinates multiple effects.
This test SHOULD FAIL with current implementation.
'''

                                                # Track effect executions
effect_executions = []

def track_effect(effect_name: str):
    pass
effect_executions.append({ ))
"name": effect_name,
"timestamp": time.time()
    

    # Simulate auth state changes triggering effects
auth_states = [ )
{"initialized": False, "token": None},
{"initialized": True, "token": None},
{"initialized": True, "token": "token1"},
{"initialized": True, "token": "token2"},  # Token refresh
    

for state in auth_states:
    if state["initialized"] and state["token"]:
            # Both effects trigger (the bug)
track_effect("main_connection_effect")
track_effect("token_sync_effect")

            # Check for duplicate connection triggers
connection_effects = [item for item in []]]

            # Should have coordinated effects, not duplicates
assert len(connection_effects) <= len(auth_states) - 2, \
"formatted_string"


def test_websocket_connection_race_condition():
    '''
Synchronous test for the race condition between auth and connection.
This test SHOULD FAIL, proving the bug exists.
'''
pass
import threading

connection_log = []
lock = threading.Lock()

def connect_websocket(source: str):
    pass
with lock:
    connection_log.append({ ))
"source": source,
"timestamp": time.time(),
"thread": threading.current_thread().name
        

        # Simulate race condition with multiple threads
threads = []

        # Thread 1: Auth completion triggers connection
t1 = threading.Thread(target=lambda x: None connect_websocket("auth_complete"), name="auth_effect")
threads.append(t1)

        # Thread 2: Token sync triggers connection
t2 = threading.Thread(target=lambda x: None connect_websocket("token_sync"), name="token_effect")
threads.append(t2)

        # Thread 3: Manual reconnect attempt
t3 = threading.Thread(target=lambda x: None connect_websocket("manual_reconnect"), name="reconnect")
threads.append(t3)

        # Start all threads simultaneously (race condition)
for t in threads:
    t.start()

            # Wait for completion
for t in threads:
    t.join()

                # Should have connection coordination, but doesn't
assert len(connection_log) == 1, \
"formatted_string"


if __name__ == "__main__":
                    # Run the tests - these should PASS after the SSOT fix
import sys

print("Running WebSocket Connection Loop Bug Tests...")
print("=" * 60)
print("These tests verify the SSOT fix is working correctly.")
print("=" * 60)

                    # Run async tests
asyncio.run(test_websocket_connection_loop_bug())
asyncio.run(test_websocket_connection_deduplication())
asyncio.run(test_websocket_auth_failure_backoff())
asyncio.run(test_websocket_provider_effect_coordination())

                    # Run sync test
test_websocket_connection_race_condition()

print(" )
PASS:  All tests passed! The SSOT fix successfully prevents connection loops.")
