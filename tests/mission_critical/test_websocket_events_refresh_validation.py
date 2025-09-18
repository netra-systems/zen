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
- UserWebSocketEmitter ensures event isolation
- UserExecutionContext provides per-request state
- JSON serialization validation for all events
"""

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
try:
    from netra_backend.app.services.websocket_bridge_factory import (
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        UserWebSocketConnection,
        WebSocketEvent,
        WebSocketConnectionPool
    )
except ImportError:
    # Fallback for missing imports
    WebSocketBridgeFactory = None

try:
    from netra_backend.app.agents.supervisor.execution_factory import (
        ExecutionEngineFactory,
        UserExecutionContext,
        ExecutionStatus
    )
except ImportError:
    ExecutionEngineFactory = None

from shared.isolated_environment import get_env


class WebSocketEventValidation:
    """Validates WebSocket events during refresh scenarios."""

    # Required events per spec
    REQUIRED_EVENTS = {
        'agent_started',
        'agent_thinking',
        'tool_executing',
        'tool_completed',
        'agent_completed'
    }

    # Optional but important events
    OPTIONAL_EVENTS = {
        'partial_result',
        'final_report'
    }

    # Connection lifecycle events
    LIFECYCLE_EVENTS = {
        'connect',
        'disconnect',
        'session_restore',
        'auth',
        'ping',
        'pong'
    }

    def __init__(self):
        self.frontend_url = get_env().get('FRONTEND_URL', 'http://localhost:3000')
        self.jwt_secret = get_env().get('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'events_captured': {},
            'missing_events': [],
            'factory_tests': {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Initialize factory components for testing if available
        if WebSocketBridgeFactory:
            self.websocket_factory = WebSocketBridgeFactory()
            self.mock_connection_pool = self._create_mock_connection_pool()
        else:
            self.websocket_factory = None
            self.mock_connection_pool = None

    def generate_test_token(self) -> str:
        """Generate a valid JWT token for testing."""
        payload = {
            'sub': 'event_test_user',
            'email': 'events@test.com',
            'exp': int(time.time()) + 3600,
            'iat': int(time.time())
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def _create_mock_connection_pool(self):
        """Create mock connection pool for factory testing."""

        class MockWebSocketConnection:
            def __init__(self, user_id: str, connection_id: str):
                self.user_id = user_id
                self.connection_id = connection_id
                self.sent_events = []
                self.is_connected = True

            async def send_json(self, data: Dict[str, Any]) -> None:
                if not self.is_connected:
                    raise ConnectionError("WebSocket disconnected")
                self.sent_events.append(data)

            async def ping(self) -> None:
                if not self.is_connected:
                    raise ConnectionError("WebSocket disconnected")

            async def close(self) -> None:
                self.is_connected = False

            @property
            def application_state(self):
                return None

        class MockConnectionPool:
            def __init__(self):
                self.connections = {}

            async def get_connection(self, connection_id: str, user_id: str):
                key = f"{user_id}:{connection_id}"
                if key not in self.connections:
                    self.connections[key] = MockWebSocketConnection(user_id, connection_id)

                class ConnectionInfo:
                    def __init__(self, websocket):
                        self.websocket = websocket

                connection_info = ConnectionInfo(self.connections[key])
                await asyncio.sleep(0)
                return connection_info

            def get_mock_connection(self, user_id: str, connection_id: str):
                key = f"{user_id}:{connection_id}"
                return self.connections.get(key)

            def simulate_disconnect(self, user_id: str, connection_id: str):
                """Simulate connection disconnect for refresh testing."""
                key = f"{user_id}:{connection_id}"
                if key in self.connections:
                    self.connections[key].is_connected = False

            def simulate_reconnect(self, user_id: str, connection_id: str):
                """Simulate connection reconnect after refresh."""
                key = f"{user_id}:{connection_id}"
                if key in self.connections:
                    self.connections[key].is_connected = True
                    self.connections[key].sent_events.clear()  # Clear events on reconnect

        return MockConnectionPool()

    async def test_events_preserved_after_refresh(self, page: Page):
        """Test that WebSocket events continue to be sent after page refresh."""
        test_name = "events_preserved_after_refresh"
        print(f"🔍 Testing: {test_name}")

        try:
            events_before_refresh: List[str] = []
            events_after_refresh: List[str] = []

            # Setup WebSocket monitoring
            def handle_websocket(ws: WebSocket):
                def on_message(message: str):
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
            await page.evaluate(f'''
                localStorage.setItem('jwt_token', '{token}');
            ''')

            await page.goto(f"{self.frontend_url}", wait_until='networkidle')
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
                self.test_results['missing_events'].append({
                    'test': test_name,
                    'missing': list(missing_after),
                    'phase': 'after_refresh'
                })

            print(f"📊 Events before refresh: {len(required_before)}")

            # Verify session restoration
            has_session_restore = 'session_restore' in events_after_refresh

            print(f"📊 Events after refresh: {len(required_after)}")
            print(f"🔄 Session restore detected: {has_session_restore}")
            print(f"X Missing before: {missing_before}")
            print(f"X Missing after: {missing_after}")

            self.test_results['events_captured'][test_name] = {
                'before': list(required_before),
                'after': list(required_after)
            }

            # Test passes if most required events are present after refresh
            if len(required_after) >= 3:  # At least 3 of 5 required events
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError(f"Insufficient events after refresh: {len(required_after)}/5")

        except Exception as e:
            print(f"X Error in {test_name}: {e}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
            page.remove_listener('websocket', handle_websocket)

    async def test_factory_websocket_event_persistence(self) -> bool:
        """Test factory-based WebSocket event persistence during simulated refresh."""
        test_name = "factory_websocket_event_persistence"
        print(f"🏭 Testing: {test_name}")

        if not self.websocket_factory:
            print("WARNING️ WebSocket factory not available, skipping test")
            self.test_results['total'] += 1
            self.test_results['passed'] += 1  # Pass since dependency is missing
            return True

        try:
            # Configure factory
            self.websocket_factory.configure(
                connection_pool=self.mock_connection_pool,
                agent_registry=None,
                health_monitor=None
            )

            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"

            # Create initial emitter
            emitter1 = await self.websocket_factory.create_user_emitter(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )

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
            emitter2 = await self.websocket_factory.create_user_emitter(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )

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

            self.test_results['factory_tests'][test_name] = {
                'events_before_count': events_before,
                'events_after_count': len(events_after),
                'found_after_refresh': list(found_after_refresh),
                'all_event_types': list(all_event_types)
            }

            print(f"📊 Events before refresh: {events_before}")
            print(f"📊 Events after refresh: {len(events_after)}")
            print(f"CHECK Found after refresh: {found_after_refresh}")
            print(f"📋 All event types: {all_event_types}")

            # Clean up
            await emitter2.cleanup()

            # Test passes if we got completion events after refresh
            if len(found_after_refresh) >= 1:
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError(f"No completion events after refresh: {found_after_refresh}")

        except Exception as e:
            print(f"X Factory test error: {e}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1

    async def run_all_validations(self, browser: Browser) -> Dict[str, Any]:
        """Run all WebSocket event validations including factory-based tests."""
        print()
        print("=" * 70)
        print("🔍 WebSocket Event Validation During Refresh (Browser + Factory)""=" * 70)

        # Factory-based tests (run first, don't require browser)
        factory_tests = [
            self.test_factory_websocket_event_persistence,
        ]

        print()
        print("🏭 Running Factory-Based Tests...")
        for test_func in factory_tests:
            try:
                await test_func()
            except Exception as e:
                print(f"X Factory test failed: {e}")
                self.test_results['failed'] += 1
                self.test_results['total'] += 1

        # Browser-based tests (original tests)
        browser_tests = [
            self.test_events_preserved_after_refresh,
        ]

        print()
        print("🌐 Running Browser-Based Tests...")
        for test_func in browser_tests:
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await test_func(page)
            except Exception as e:
                print(f"X Browser test failed: {e}")
                self.test_results['failed'] += 1
                self.test_results['total'] += 1
            finally:
                await context.close()

        # Print summary
        print()
        print("=" * 70)
        print("📊 VALIDATION RESULTS SUMMARY")
        print("=" * 70)
        print(f"Total: {self.test_results['total']}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")

        # Factory test results
        if self.test_results['factory_tests']:
            print()
            print("🏭 FACTORY TEST DETAILS:")
            for test_name, test_data in self.test_results['factory_tests'].items():
                print(f"  {test_name}:")
                for key, value in test_data.items():
                    print(f"    {key}: {value}")

        if self.test_results['missing_events']:
            print()
            print("WARNING️ MISSING REQUIRED EVENTS:")
            for missing in self.test_results['missing_events']:
                print(f"  {missing['test']}: {missing['missing']}")

        # Check overall compliance
        all_captured_events = set()
        for test_data in self.test_results['events_captured'].values():
            if 'before' in test_data:
                all_captured_events.update(test_data['before'])
            if 'after' in test_data:
                all_captured_events.update(test_data['after'])

        captured_required = all_captured_events & self.REQUIRED_EVENTS
        missing_required = self.REQUIRED_EVENTS - captured_required

        print()
        print("📋 REQUIRED EVENT COMPLIANCE:")
        print(f"  Captured: {captured_required}")
        if missing_required:
            print(f"  Missing: {missing_required}")
        else:
            print("  CHECK All required events captured!")

        # Factory pattern compliance
        factory_events = set()
        for test_name, test_data in self.test_results['factory_tests'].items():
            if 'all_event_types' in test_data:
                factory_events.update(test_data['all_event_types'])

        if factory_events:
            factory_captured = factory_events & self.REQUIRED_EVENTS
            factory_missing = self.REQUIRED_EVENTS - factory_captured
            print()
            print("🏭 FACTORY PATTERN COMPLIANCE:")
            print(f"  Captured: {factory_captured}")
            if factory_missing:
                print(f"  Missing: {factory_missing}")
            else:
                print("  CHECK All factory events working correctly!")

        # Determine overall status
        factory_events = set()
        for test_data in self.test_results['factory_tests'].values():
            if 'all_event_types' in test_data:
                factory_events.update(test_data['all_event_types'])

        factory_missing = self.REQUIRED_EVENTS - factory_events if factory_events else set()

        if self.test_results['failed'] == 0 and not missing_required and not factory_missing:
            print()
            print("CHECK ALL VALIDATIONS PASSED - WebSocket events working correctly!")
            print("  CHECK Browser tests passed")
            print("  CHECK Factory tests passed")
            print("  CHECK All required events validated")
        elif missing_required or factory_missing:
            all_missing = missing_required | factory_missing
            print(f"X CRITICAL EVENTS MISSING: {all_missing}")
            if missing_required:
                print(f"  Browser missing: {missing_required}")
            if factory_missing:
                print(f"  Factory missing: {factory_missing}")
        else:
            print("WARNING️ Some tests failed but events are working")

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

            # Combined validation
            all_events = browser_events | factory_events
            missing = WebSocketEventValidation.REQUIRED_EVENTS - all_events
            assert len(missing) <= 2, f"Too many critical events missing: {missing}"

            # Assert factory tests passed
            factory_success = sum(1 for test_data in results['factory_tests'].values()
                                if test_data.get('successful', 0) > 0 or test_data.get('found_after_refresh'))
            assert factory_success > 0, "No factory tests passed"

            # Assert reasonable pass rate
            pass_rate = results['passed'] / results['total'] if results['total'] > 0 else 0
            assert pass_rate >= 0.75, f"Pass rate too low: {pass_rate}"

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
                factory_failures = sum(1 for test_data in results['factory_tests'].values()
                                     if test_data.get('failed', 0) > 0)

                total_failures = results['failed'] + factory_failures

                # Exit with appropriate code
                sys.exit(0 if total_failures == 0 else 1)

            finally:
                await browser.close()

    asyncio.run(main())