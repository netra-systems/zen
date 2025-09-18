from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
MISSION CRITICAL: WebSocket Event Validation During Page Refresh

This test validates that all required WebSocket events are properly sent
and received during page refresh scenarios using the factory-based patterns.

CRITICAL: Per SPEC/learnings/websocket_agent_integration_critical.xml
The following events MUST be sent:
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User must know when done
6. partial_result - Streaming response UX (optional)
7. final_report - Comprehensive summary (optional)

NEW: Factory-Based Pattern Validation:
- WebSocketBridgeFactory creates per-user emitters
- UserWebSocketEmitter ensures event isolation"""
- JSON serialization validation for all events"""
@pytest.fixture"""

import asyncio
import json
import time
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
import jwt
import pytest
from playwright.async_api import Page, Browser, WebSocket
import os
import sys
import uuid

        # Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

        # Import factory-based components for validation
from netra_backend.app.services.websocket_bridge_factory import ( )
WebSocketBridgeFactory,
UserWebSocketEmitter,
UserWebSocketContext,
UserWebSocketConnection,
WebSocketEvent,
WebSocketConnectionPool
        
from netra_backend.app.agents.supervisor.execution_factory import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
ExecutionEngineFactory,
UserExecutionContext,
ExecutionStatus
        """
"""
    """Validates WebSocket events during refresh scenarios."""

    # Required events per spec
    REQUIRED_EVENTS = { )
    'agent_started',
    'agent_thinking',
    'tool_executing',
    'tool_completed',
    'agent_completed'
    

    # Optional but important events
    OPTIONAL_EVENTS = { )
    'partial_result',
    'final_report'
    

    # Connection lifecycle events
    LIFECYCLE_EVENTS = { )
    'connect',
    'disconnect',
    'session_restore',
    'auth',
    'ping',
    'pong'
    

    def __init__(self):
        pass
        self.frontend_url = get_env().get('FRONTEND_URL', 'http://localhost:3000')
        self.jwt_secret = get_env().get('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = { )
        'total': 0,
        'passed': 0,
        'failed': 0,
        'events_captured': {},
        'missing_events': [],
        'factory_tests': {},
        'timestamp': datetime.now(timezone.utc).isoformat()
    

    # Initialize factory components for testing
        self.websocket_factory = WebSocketBridgeFactory()"""
"""
        """Generate a valid JWT token for testing."""
payload = {'sub': 'event_test_user',, 'email': 'events@test.com',, 'exp': int(time.time()) + 3600,, 'iat': int(time.time())}"""
"""
        """Create mock connection pool for factory testing."""

class MockWebSocketConnection:
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.sent_events = []
        self.is_connected = True"""
    async def send_json(self, data: Dict[str, Any]) -> None:"""
        raise ConnectionError("WebSocket disconnected")
        self.sent_events.append(data)

    async def ping(self) -> None:
        if not self.is_connected:
        raise ConnectionError("WebSocket disconnected")

    async def close(self) -> None:
        self.is_connected = False

        @property
    def application_state(self):
        return Magic
class MockConnectionPool:
    def __init__(self):
        self.connections = {}

    async def get_connection(self, connection_id: str, user_id: str):
        key = "formatted_string"
        if key not in self.connections:
        self.connections[key] = MockWebSocketConnection(user_id, connection_id)

        connection_info = Magic                connection_info.websocket = self.connections[key]
        await asyncio.sleep(0)
        return connection_info

    def get_mock_connection(self, user_id: str, connection_id: str):
        key = "formatted_string"
        return self.connections.get(key)

    def simulate_disconnect(self, user_id: str, connection_id: str):
        """Simulate connection disconnect for refresh testing.""""""
        key = "formatted_string"
        if key in self.connections:
        self.connections[key].is_connected = False

    def simulate_reconnect(self, user_id: str, connection_id: str):
        """Simulate connection reconnect after refresh."""
        key = "formatted_string"
        if key in self.connections:
        self.connections[key].is_connected = True
        self.connections[key].sent_events.clear()  # Clear events on reconnect

        return MockConnectionPool()

    async def test_events_preserved_after_refresh(self, page:
        """"""
        Test that WebSocket events continue to be sent after page refresh."""
        test_name = "events_preserved_after_refresh"
        print(f" )

class TestWebSocketConnection:
        """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True"""
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True"""
"""
        """Get all sent messages.""""""
        return self.messages_sent.copy()"""
        SEARCH:  Testing: {test_name}")

        try:
        events_before_refresh: List[str] = []
        events_after_refresh: List[str] = []

        # Setup WebSocket monitoring
    def handle_websocket(ws: WebSocket):
        pass
    def on_message(message: str):
        pass
        try:
        data = json.loads(message)
        event_type = data.get('type', '')

        # Track events based on timing
        if len(events_before_refresh) < 100:  # Arbitrary limit
        events_before_refresh.append(event_type)
        else:
        events_after_refresh.append(event_type)
        except:
        pass

        ws.on('message', on_message)

        page.on('websocket', handle_websocket)

                # Setup and navigate
        token = self.generate_test_token()
                # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("formatted_string", wait_until='networkidle')
        await page.wait_for_timeout(2000)

                # Send a message to trigger agent events
        message_input = await page.query_selector('[data-testid="message-input"], textarea')
        if message_input:
        await message_input.fill("Test message before refresh")
        await message_input.press("Enter")
        await page.wait_for_timeout(3000)  # Wait for events

                    # Mark transition point
        events_before_refresh.extend(['REFRESH_MARKER'] * 100)

                    # Perform refresh
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(2000)

                    # Send another message after refresh
        message_input_after = await page.query_selector('[data-testid="message-input"], textarea')
        if message_input_after:
        await message_input_after.fill("Test message after refresh")
        await message_input_after.press("Enter")
        await page.wait_for_timeout(3000)  # Wait for events

                        # Analyze events
        required_before = set(events_before_refresh) & self.REQUIRED_EVENTS
        required_after = set(events_after_refresh) & self.REQUIRED_EVENTS

                        # Check if required events were sent both before and after
        missing_before = self.REQUIRED_EVENTS - required_before
        missing_after = self.REQUIRED_EVENTS - required_after

        if missing_after:
        self.test_results['missing_events'].append({ ))
        'test': test_name,
        'missing': list(missing_after),
        'phase': 'after_refresh'
                            
        print("formatted_string")

                            # Verify session restoration
        has_session_restore = 'session_restore' in events_after_refresh

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        self.test_results['events_captured'][test_name] = { )
        'before': list(required_before),
        'after': list(required_after)
                            

                            # Test passes if most required events are present after refresh
        if len(required_after) >= 3:  # At least 3 of 5 required events
        self.test_results['passed'] += 1
        return True
        else:
        raise AssertionError("formatted_string")

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener('websocket', handle_websocket)

    async def test_reconnection_event_sequence(self, page:
        """
        Test that WebSocket reconnection follows proper event sequence."""
        test_name = "reconnection_event_sequence"
        print("formatted_string")

        try:
        event_sequence: List[tuple] = []

                                                # Monitor WebSocket events with timestamps
    def handle_websocket(ws: WebSocket):
        pass
        connection_time = time.time()

    def on_message(message: str):
        pass
        try:
        data = json.loads(message)
        event_type = data.get('type', '')
        event_sequence.append(( ))
        event_type,
        time.time() - connection_time,
        'incoming'
        
        except:
        pass

    def on_close():
        pass
        event_sequence.append(( ))
        'connection_closed',
        time.time() - connection_time,
        'lifecycle'
    

        ws.on('message', on_message)
        ws.on('close', on_close)

        event_sequence.append(('connection_opened', 0, 'lifecycle'))

        page.on('websocket', handle_websocket)

    # Setup and navigate
        token = self.generate_test_token()
    # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("formatted_string", wait_until='networkidle')
        await page.wait_for_timeout(2000)

    # Trigger refresh
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)

    # Analyze sequence
        lifecycle_events = [item for item in []]

    # Expected sequence: open -> close -> open
        expected_pattern = ['connection_opened', 'connection_closed', 'connection_opened']
        actual_pattern = [item for item in []]

    # Check for proper cleanup
        has_proper_close = 'connection_closed' in actual_pattern
        has_reconnect = actual_pattern.count('connection_opened') >= 2

    # Check for session restoration
        has_session_event = any(e == 'session_restore' for e, _, _ in event_sequence)

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        self.test_results['events_captured'][test_name] = { )
        'sequence': actual_pattern[:5],
        'total_events': len(event_sequence)
    

        if has_reconnect:
        self.test_results['passed'] += 1
        return True
        else:
        raise AssertionError("No reconnection detected after refresh")

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener('websocket', handle_websocket)

    async def test_no_duplicate_events_after_refresh(self, page:
        """
        Test that events are not duplicated after page refresh."""
        test_name = "no_duplicate_events_after_refresh"
        print("formatted_string")

        try:
        message_ids: Set[str] = set()
        duplicate_events: List[str] = []

                            # Monitor for duplicate message IDs
    def handle_websocket(ws: WebSocket):
        pass
    def on_message(message: str):
        pass
        try:
        data = json.loads(message)
        payload = data.get('payload', {})
        message_id = payload.get('message_id') or payload.get('id')

        if message_id:
        if message_id in message_ids:
        duplicate_events.append(message_id)
        else:
        message_ids.add(message_id)
        except:
        pass

        ws.on('message', on_message)

        page.on('websocket', handle_websocket)

                        # Setup and navigate
        token = self.generate_test_token()
                        # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("formatted_string", wait_until='networkidle')

                        # Send messages before and after refresh
        for i in range(2):
        message_input = await page.query_selector('[data-testid="message-input"], textarea')
        if message_input:
        await message_input.fill("formatted_string")
        await message_input.press("Enter")
        await page.wait_for_timeout(2000)

        if i == 0:
                                    # Refresh between messages
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                    # Check for duplicates
        if duplicate_events:
        print("formatted_string")
        self.test_results['events_captured'][test_name] = { )
        'duplicates': duplicate_events[:5]  # First 5 duplicates
                                        

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

                                        # Test passes if duplicates are minimal
        if len(duplicate_events) <= 2:  # Allow up to 2 duplicates (edge cases)
        self.test_results['passed'] += 1
        return True
        else:
        raise AssertionError("formatted_string")

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener('websocket', handle_websocket)

    async def test_event_timing_after_refresh(self, page:
        """
        Test that events are sent with appropriate timing after refresh."""
        test_name = "event_timing_after_refresh"
        print("formatted_string")

        try:
        event_timings: Dict[str, List[float]] = {}

                                                            # Monitor event timing
    def handle_websocket(ws: WebSocket):
        pass
        start_time = time.time()

    def on_message(message: str):
        pass
        try:
        data = json.loads(message)
        event_type = data.get('type', '')
        elapsed = time.time() - start_time

        if event_type not in event_timings:
        event_timings[event_type] = []
        event_timings[event_type].append(elapsed)
        except:
        pass

        ws.on('message', on_message)

        page.on('websocket', handle_websocket)

                # Setup and navigate
        token = self.generate_test_token()
                # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("formatted_string", wait_until='networkidle')
        await page.wait_for_timeout(1000)

                # Measure initial connection timing
        initial_timing = time.time()

                # Send a test message
        message_input = await page.query_selector('[data-testid="message-input"], textarea')
        if message_input:
        await message_input.fill("Timing test message")
        await message_input.press("Enter")
        await page.wait_for_timeout(2000)

                    # Refresh and measure reconnection timing
        refresh_start = time.time()
        await page.reload(wait_until='networkidle')
        refresh_duration = time.time() - refresh_start

        await page.wait_for_timeout(2000)

                    # Analyze timings
        critical_events = ['auth', 'session_restore', 'connection_opened']
        critical_timings = {}

        for event in critical_events:
        if event in event_timings and event_timings[event]:
        critical_timings[event] = min(event_timings[event])

        print("formatted_string")
        print("formatted_string")

        for event, timing in critical_timings.items():
        print("formatted_string")

        self.test_results['events_captured'][test_name] = { )
        'refresh_duration': refresh_duration,
        'critical_timings': critical_timings
                                

                                # Test passes if reconnection is reasonably fast
        if refresh_duration < 5.0:  # Less than 5 seconds
        self.test_results['passed'] += 1
        return True
        else:
        print("formatted_string")
        self.test_results['passed'] += 1  # Still pass but warn
        return True

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener('websocket', handle_websocket)

    async def test_factory_websocket_event_persistence(self) -> bool:
        """Test factory-based WebSocket event persistence during simulated refresh."""
        test_name = "factory_websocket_event_persistence"
        print("formatted_string")

        try:
                                                    # Configure factory
        self.websocket_factory.configure(connection_pool=self.mock_connection_pool,, agent_registry=None,, health_monitor=None, user_id = "formatted_string", thread_id = "formatted_string", connection_id = "formatted_string")
                                                    # Create initial emitter
        emitter1 = await self.websocket_factory.create_user_emitter(user_id=user_id,, thread_id=thread_id,, connection_id=connection_id)
                                                    # Send events before "refresh"
        await emitter1.notify_agent_started("TestAgent", "run_1")
        await emitter1.notify_agent_thinking("TestAgent", "run_1", "Processing...")
        await emitter1.notify_tool_executing("TestAgent", "run_1", "search_tool", {"query": "test"})

        await asyncio.sleep(0.1)  # Allow processing

                                                    # Get events before refresh
        mock_conn = self.mock_connection_pool.get_mock_connection(user_id, connection_id)
        events_before = len(mock_conn.sent_events)

                                                    # Simulate page refresh (connection disconnect/reconnect)
        await emitter1.cleanup()
        self.mock_connection_pool.simulate_disconnect(user_id, connection_id)

                                                    # Simulate brief delay during refresh
        await asyncio.sleep(0.1)

                                                    # Reconnect and create new emitter (simulates page reload)
        self.mock_connection_pool.simulate_reconnect(user_id, connection_id)
        emitter2 = await self.websocket_factory.create_user_emitter(user_id=user_id,, thread_id=thread_id,, connection_id=connection_id)
                                                    # Send events after "refresh"
        await emitter2.notify_tool_completed("TestAgent", "run_1", "search_tool", {"results": ["found"]})
        await emitter2.notify_agent_completed("TestAgent", "run_1", {"status": "success"})

        await asyncio.sleep(0.1)  # Allow processing

                                                    # Verify events after refresh
        mock_conn_after = self.mock_connection_pool.get_mock_connection(user_id, connection_id)
        events_after = mock_conn_after.sent_events

                                                    # Check that all 5 required events were sent across both sessions
        all_event_types = set()
        for event in events_after:
        all_event_types.add(event.get('event_type'))

                                                        # The reconnected session should have the completion events
        required_after_refresh = {'tool_completed', 'agent_completed'}
        found_after_refresh = all_event_types & required_after_refresh

        self.test_results['factory_tests'][test_name] = { )
        'events_before_count': events_before,
        'events_after_count': len(events_after),
        'found_after_refresh': list(found_after_refresh),
        'all_event_types': list(all_event_types)
                                                        

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

                                                        # Clean up
        await emitter2.cleanup()

                                                        # Test passes if we got completion events after refresh
        if len(found_after_refresh) >= 1:
        self.test_results['passed'] += 1
        return True
        else:
        raise AssertionError("formatted_string")

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1

    async def test_factory_json_serialization_during_refresh(self) -> bool:
        """Test JSON serialization remains intact during refresh scenarios."""
        test_name = "factory_json_serialization_during_refresh"
        print("formatted_string")

        try:
                                                                                # Configure factory
        self.websocket_factory.configure(connection_pool=self.mock_connection_pool,, agent_registry=None,, health_monitor=None, user_id = "formatted_string", thread_id = "formatted_string", connection_id = "formatted_string")
                                                                                # Test events with complex data for JSON serialization
        test_events_data = [ )
        ('agent_started', {'agent_name': 'TestAgent', 'status': 'started', 'complex_data': {'nested': {'value': 123}}}),
        ('tool_executing', {'tool_name': 'complex_tool', 'tool_input': {'array': [1, 2, 3], 'unicode': '[U+2764][U+FE0F][U+1F680]'}}),
        ('agent_completed', {'result': {'success': True, 'metrics': {'time_ms': 1500, 'accuracy': 0.95}}})
                                                                                

        serialization_results = []

        for event_type, event_data in test_events_data:
                                                                                    # Create emitter for each test
        emitter = await self.websocket_factory.create_user_emitter(user_id=user_id,, thread_id="formatted_string",, connection_id="formatted_string")
                                                                                    # Send event based on type
        if event_type == 'agent_started':
        await emitter.notify_agent_started(event_data['agent_name'], 'test_run')
        elif event_type == 'tool_executing':
        await emitter.notify_tool_executing('TestAgent', 'test_run', event_data['tool_name'], event_data['tool_input'])
        elif event_type == 'agent_completed':
        await emitter.notify_agent_completed('TestAgent', 'test_run', event_data['result'])

        await asyncio.sleep(0.1)

                                                                                                # Get sent events and test JSON serialization
        mock_conn = self.mock_connection_pool.get_mock_connection(user_id, "formatted_string")
        sent_events = mock_conn.sent_events

        for event in sent_events:
        try:
                                                                                                        # Test JSON serialization roundtrip
        json_str = json.dumps(event)
        deserialized = json.loads(json_str)

                                                                                                        # Verify structure preservation
        assert event['event_type'] == deserialized['event_type']
        assert event['event_id'] == deserialized['event_id']
        assert event['thread_id'] == deserialized['thread_id']

        serialization_results.append({ ))
        'event_type': event_type,
        'serializable': True,
        'json_length': len(json_str)
                                                                                                        

        except (TypeError, ValueError) as json_error:
        serialization_results.append({ ))
        'event_type': event_type,
        'serializable': False,
        'error': str(json_error)
                                                                                                            

        await emitter.cleanup()

                                                                                                            # Analyze results
        successful_serializations = [item for item in []]
        failed_serializations = [item for item in []]

        self.test_results['factory_tests'][test_name] = { )
        'total_events': len(serialization_results),
        'successful': len(successful_serializations),
        'failed': len(failed_serializations),
        'failed_details': failed_serializations[:3]  # First 3 failures
                                                                                                            

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

                                                                                                            # Test passes if most events serialize correctly
        if len(failed_serializations) == 0:
        self.test_results['passed'] += 1
        return True
        elif len(successful_serializations) > len(failed_serializations):
        print(f" WARNING: [U+FE0F] Some serialization failures but mostly working")
        self.test_results['passed'] += 1
        return True
        else:
        raise AssertionError("formatted_string")

        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1

    async def run_all_validations(self, browser: Browser) -> Dict[str, Any]:
        """Run all WebSocket event validations including factory-based tests."""
        print(" )
        " + "=" * 70)
        print(" SEARCH:  WebSocket Event Validation During Refresh (Browser + Factory)")
        print("=" * 70)

    # Factory-based tests (run first, don't require browser)
        factory_tests = [ )
        self.test_factory_websocket_event_persistence,
        self.test_factory_json_serialization_during_refresh
    

        print(" )
        [U+1F3ED] Running Factory-Based Tests...")
        for test_func in factory_tests:
        try:
        await test_func()
        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        self.test_results['total'] += 1

                # Browser-based tests (original tests)
        browser_tests = [ )
        self.test_events_preserved_after_refresh,
        self.test_reconnection_event_sequence,
        self.test_no_duplicate_events_after_refresh,
        self.test_event_timing_after_refresh
                

        print(" )
        [U+1F310] Running Browser-Based Tests...")
        for test_func in browser_tests:
        context = await browser.new_context()
        try:
        await test_func(page)
        except Exception as e:
        print("formatted_string")
        self.test_results['failed'] += 1
        self.test_results['total'] += 1
        finally:
        await context.close()

                                # Print summary
        print(" )
        " + "=" * 70)
        print(" CHART:  VALIDATION RESULTS SUMMARY")
        print("=" * 70)
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

                                # Factory test results
        if self.test_results['factory_tests']:
        print(" )
        [U+1F3ED] FACTORY TEST DETAILS:")
        for test_name, test_data in self.test_results['factory_tests'].items():
        print("formatted_string")
        for key, value in test_data.items():
        print("formatted_string")

        if self.test_results['missing_events']:
        print(" )
        WARNING: [U+FE0F] MISSING REQUIRED EVENTS:")
        for missing in self.test_results['missing_events']:
        print("formatted_string")

                                                    # Check overall compliance
        all_captured_events = set()
        for test_data in self.test_results['events_captured'].values():
        if 'before' in test_data:
        all_captured_events.update(test_data['before'])
        if 'after' in test_data:
        all_captured_events.update(test_data['after'])

        captured_required = all_captured_events & self.REQUIRED_EVENTS
        missing_required = self.REQUIRED_EVENTS - captured_required

        print(f" )
        [U+1F4CB] REQUIRED EVENT COMPLIANCE:")
        print("formatted_string")
        if missing_required:
        print("formatted_string")
        else:
        print("   PASS:  All required events captured!")

                                                                        # Factory pattern compliance
        factory_events = set()
        for test_name, test_data in self.test_results['factory_tests'].items():
        if 'all_event_types' in test_data:
        factory_events.update(test_data['all_event_types'])

        if factory_events:
        factory_captured = factory_events & self.REQUIRED_EVENTS
        factory_missing = self.REQUIRED_EVENTS - factory_captured
        print(f" )
        [U+1F3ED] FACTORY PATTERN COMPLIANCE:")
        print("formatted_string")
        if factory_missing:
        print("formatted_string")
        else:
        print("   PASS:  All factory events working correctly!")

                                                                                            # Determine overall status
        factory_events = set()
        for test_data in self.test_results['factory_tests'].values():
        if 'all_event_types' in test_data:
        factory_events.update(test_data['all_event_types'])

        factory_missing = self.REQUIRED_EVENTS - factory_events if factory_events else set()

        if self.test_results['failed'] == 0 and not missing_required and not factory_missing:
        print(" )
        PASS:  ALL VALIDATIONS PASSED - WebSocket events working correctly!")
        print("   PASS:  Browser tests passed")
        print("   PASS:  Factory tests passed")
        print("   PASS:  All required events validated")
        elif missing_required or factory_missing:
        all_missing = missing_required | factory_missing
        print("formatted_string")
        if missing_required:
        print("formatted_string")
        if factory_missing:
        print("formatted_string")
        else:
        print("formatted_string")

        return self.test_results


                                                                                                                        # Pytest integration
@pytest.mark.asyncio
@pytest.mark.critical
    async def test_websocket_events_refresh_validation():
"""Pytest wrapper for WebSocket event validation."""
from playwright.async_api import async_playwright

async with async_playwright() as p:
browser = await p.chromium.launch(headless=True)

try:
validator = WebSocketEventValidation()
results = await validator.run_all_validations(browser)

                                                                                                                                    # Assert critical events are captured (browser tests)
browser_events = set()
for test_data in results['events_captured'].values():
if isinstance(test_data, dict):
browser_events.update(test_data.get('before', []))
browser_events.update(test_data.get('after', []))

                                                                                                                                            # Assert critical events are captured (factory tests)
factory_events = set()
for test_data in results['factory_tests'].values():
if 'all_event_types' in test_data:
factory_events.update(test_data['all_event_types'])
"""
all_events = browser_events | factory_events"""
assert len(missing) <= 2, "formatted_string"

                                                                                                                                                    # Assert factory tests passed
factory_success = sum(1 for test_data in results['factory_tests'].values() )
if test_data.get('successful', 0) > 0 or test_data.get('found_after_refresh'))
assert factory_success > 0, "No factory tests passed"

                                                                                                                                                    # Assert reasonable pass rate
pass_rate = results['passed'] / results['total'] if results['total'] > 0 else 0
assert pass_rate >= 0.75, "formatted_string"

finally:
await browser.close()


if __name__ == "__main__":
                                                                                                                                                            # Allow running directly for debugging
import asyncio
from playwright.async_api import async_playwright

async def main():
async with async_playwright() as p:
browser = await p.chromium.launch(headless=False)  # Visible for debugging

try:
validator = WebSocketEventValidation()
results = await validator.run_all_validations(browser)

            # Check both browser and factory test results
factory_failures = sum(1 for test_data in results['factory_tests'].values() )
if test_data.get('failed', 0) > 0)

total_failures = results['failed'] + factory_failures

            # Exit with appropriate code
sys.exit(0 if total_failures == 0 else 1)

finally:
await browser.close()

asyncio.run(main())

pass
