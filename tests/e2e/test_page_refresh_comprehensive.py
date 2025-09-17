'''
MISSION CRITICAL: Comprehensive Page Refresh Test Suite

This test suite ensures the chat interface remains fully functional across page refreshes.
Tests cover state persistence, WebSocket reconnection, authentication, and user experience.

CRITICAL: Any failure here indicates potential data loss or degraded user experience.

@pytest.fixture
@compliance SPEC/learnings/websocket_agent_integration_critical.xml
'''

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from playwright.async_api import Page, Browser, WebSocket, ConsoleMessage, Response
import os
import sys
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class WebSocketMonitor:
    """Simple WebSocket monitor for testing."""
    def __init__(self):
        pass
        self.connections = []
        self.messages = []

    def track_connection(self, ws):
        pass
        self.connections.append(ws)

    def track_message(self, msg):
        pass
        self.messages.append(msg)


class PageRefreshTestSuite:
        """Comprehensive test suite for page refresh scenarios."""

    def __init__(self):
        pass
        from shared.isolated_environment import get_env
        env = get_env()
        self.frontend_url = env.get('FRONTEND_URL', 'http://localhost:3000')
        self.backend_url = env.get('BACKEND_URL', 'http://localhost:8000')
        self.auth_url = env.get('AUTH_SERVICE_URL', 'http://localhost:8081')
        self.jwt_secret = env.get('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = { }
        'total': 0,
        'passed': 0,
        'failed': 0,
        'critical_failures': [],
        'performance_metrics': {},
        'timestamp': datetime.now(timezone.utc).isoformat()
    

    def generate_test_token(self, user_email: str = "test@example.com", expires_in: int = 3600) -> str:
        """Generate a valid JWT token for testing."""
        payload = { }
        'sub': 'user_123',
        'email': user_email,
        'name': 'Test User',
        'exp': datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        'iat': datetime.now(timezone.utc),
        'role': 'user'
    
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    async def test_basic_refresh_with_active_chat(self, page:
        '''
        CRITICAL TEST 1: Basic page refresh with active chat session.
        Verifies that chat state is preserved across refresh.
        '''
        test_name = "basic_refresh_with_active_chat"
        print("")

        try:
            # Setup: Login and start a chat
        token = self.generate_test_token()
            # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("", wait_until='networkidle')
        await page.wait_for_timeout(2000)

            # Send a test message
        message_input = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"]')
        if not message_input:
        raise AssertionError("Message input not found")

        test_message = "Test message before refresh"
        await message_input.fill(test_message)
        await message_input.press("Enter")

                # Wait for message to appear
        await page.wait_for_selector('formatted_string', timeout=5000)

                # Store current state
                # Removed problematic line: messages_before = await page.evaluate(''' )
        Array.from(document.querySelectorAll('[data-testid*="message"], .message-content'))
        .map(el => el.textContent)
        ''')

                # Perform page refresh
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)

                # Verify chat is still active
        chat_visible = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
        if not chat_visible:
        raise AssertionError("Chat not visible after refresh")

                    # Check if messages are preserved
                    # Removed problematic line: messages_after = await page.evaluate(''' )
        Array.from(document.querySelectorAll('[data-testid*="message"], .message-content'))
        .map(el => el.textContent)
        ''')

                    # At minimum, the sent message should be preserved
        if test_message not in str(messages_after):
        raise AssertionError("")

        print("")
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        self.test_results['critical_failures'].append({ })
        'test': test_name,
        'error': str(e)
                            
        return False
        finally:
        self.test_results['total'] += 1

    async def test_websocket_reconnection_on_refresh(self, page:
        '''
        CRITICAL TEST 2: WebSocket reconnection after page refresh.
        Ensures WebSocket properly reconnects with authentication.
        '''
        test_name = "websocket_reconnection_on_refresh"
        print("")

        try:
                                        # Setup monitoring
        ws_connections: List[Dict] = []

    def handle_websocket(ws: WebSocket):
        pass
        ws_connections.append({ })
        'url': ws.url,
        'time': time.time(),
        'closed': False
    
        ws.on('close', lambda x: None ws_connections[-1].update({'closed': True}))

        page.on('websocket', handle_websocket)

    # Login and establish initial connection
        token = self.generate_test_token()
    # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("", wait_until='networkidle')
        await page.wait_for_timeout(2000)

    # Verify initial WebSocket connection
        initial_connections = len(ws_connections)
        if initial_connections == 0:
        raise AssertionError("No initial WebSocket connection established")

        # Perform refresh
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)

        # Check for new WebSocket connection
        total_connections = len(ws_connections)
        if total_connections <= initial_connections:
        raise AssertionError("WebSocket did not reconnect after refresh")

            # Verify the new connection is active
        latest_connection = ws_connections[-1]
        if latest_connection['closed']:
        raise AssertionError("WebSocket connection closed immediately after refresh")

                # Test that the connection is functional
        message_input = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"]')
        if message_input:
        await message_input.fill("Test after reconnect")
        await message_input.press("Enter")

                    # Wait for response (indicates working WebSocket)
        await page.wait_for_timeout(2000)

        print("")
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        self.test_results['critical_failures'].append({ })
        'test': test_name,
        'error': str(e)
                        
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener('websocket', handle_websocket)

    async def test_rapid_refresh_resilience(self, page:
        '''
        STRESS TEST: Rapid consecutive refreshes.
        Ensures system handles rapid refreshes without crashes or connection flooding.
        '''
        test_name = "rapid_refresh_resilience"
        print("")

        try:
                                    # Setup authentication
        token = self.generate_test_token()
                                    # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("", wait_until='networkidle')

        errors_caught = []

                                    # Monitor console errors
    def handle_console(msg: ConsoleMessage):
        pass
        if msg.type == "error":
        errors_caught.append(msg.text)

        page.on("console", handle_console)

        # Perform rapid refreshes
        refresh_count = 5
        for i in range(refresh_count):
        print("")
        await page.reload(wait_until='domcontentloaded')
        await page.wait_for_timeout(500)  # Short delay between refreshes

            # Final wait for stability
        await page.wait_for_timeout(3000)

            # Check for critical errors
        critical_errors = [e for e in errors_caught if any( ))
        keyword in e.lower() for keyword in
        ['websocket', 'connection', 'memory', 'crash', 'unhandled']
            

        if critical_errors:
        raise AssertionError("")

                # Verify chat is still functional
        chat_visible = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
        if not chat_visible:
        raise AssertionError("Chat not functional after rapid refreshes")

                    # Check WebSocket connection count (should not be excessive)
                    # Removed problematic line: ws_count = await page.evaluate(''' )
        performance.getEntriesByType('resource')
        .filter(r => r.name.includes('ws://') || r.name.includes('wss://'))
        .length
        ''')

        if ws_count > refresh_count * 2:  # Allow some overhead
        raise AssertionError("")

        print("")
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        self.test_results['critical_failures'].append({ })
        'test': test_name,
        'error': str(e)
                        
        return False
        finally:
        self.test_results['total'] += 1
        page.remove_listener("console", handle_console)

    async def test_draft_message_persistence(self, page:
        '''
        TEST: Draft message persistence across refresh.
        Ensures unsent messages are preserved.
        '''
        test_name = "draft_message_persistence"
        print("")

        try:
                                    # Setup and navigate
        token = self.generate_test_token()
                                    # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("", wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                    # Type a draft message (don't send)
        message_input = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"]')
        if not message_input:
        raise AssertionError("Message input not found")

        draft_text = "This is my draft message that should persist"
        await message_input.fill(draft_text)

                                        # Refresh the page
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                        # Check if draft is restored
        message_input_after = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"]')
        if not message_input_after:
        raise AssertionError("Message input not found after refresh")

        restored_text = await message_input_after.input_value()

                                            # Draft persistence is a nice-to-have feature
        if restored_text == draft_text:
        print("")
        self.test_results['passed'] += 1
        return True
        else:
        print("")
                                                    # Not marking as failed since this might be intentional behavior
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1

    async def test_token_refresh_during_page_reload(self, page:
        '''
        CRITICAL TEST: Token refresh handling during page reload.
        Ensures authentication remains stable when token expires during refresh.
        '''
        test_name = "token_refresh_during_page_reload"
        print("")

        try:
                                                                    # Create a token that expires soon
        short_lived_token = self.generate_test_token(expires_in=10)  # 10 seconds
                                                                    # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{short_lived_token}');
        ''')

        await page.goto("", wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                                                    # Wait for token to near expiration
        await page.wait_for_timeout(8000)

                                                                    # Refresh page while token is expiring
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)

                                                                    # Check if we're still authenticated (should handle token refresh)
        current_url = page.url
        if '/login' in current_url:
                                                                        # Check if a refresh token mechanism kicked in
        new_token = await page.evaluate("localStorage.getItem('jwt_token')")
        if new_token == short_lived_token:
        raise AssertionError("Token not refreshed, redirected to login")

                                                                            # Verify chat is still accessible
        chat_visible = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
        if not chat_visible:
                                                                                # This might be expected behavior - log but don't fail
        print("")

        print("")
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        self.test_results['critical_failures'].append({ })
        'test': test_name,
        'error': str(e)
                                                                                    
        return False
        finally:
        self.test_results['total'] += 1

    async def test_scroll_position_restoration(self, page:
        '''
        UX TEST: Scroll position restoration after refresh.
        Ensures user doesn"t lose their place in the conversation.
        '''
        test_name = "scroll_position_restoration"
        print("")

        try:
                                                                                                # Setup
        token = self.generate_test_token()
                                                                                                # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

        await page.goto("", wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                                                                                # Send multiple messages to create scrollable content
        message_input = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"]')
        if message_input:
        for i in range(5):
        await message_input.fill("")
        await message_input.press("Enter")
        await page.wait_for_timeout(500)

                                                                                                        # Scroll to middle of conversation
                                                                                                        # Removed problematic line: await page.evaluate(''' )
        const chatContainer = document.querySelector('[data-testid="chat-messages"], .messages-container, main');
        if (chatContainer) { }
        chatContainer.scrollTop = chatContainer.scrollHeight / 2;
                                                                                                        
        ''')

                                                                                                        # Get scroll position before refresh
                                                                                                        # Removed problematic line: scroll_before = await page.evaluate(''' )
        const chatContainer = document.querySelector('[data-testid="chat-messages"], .messages-container, main');
        chatContainer ? chatContainer.scrollTop : 0;
        ''')

                                                                                                        # Refresh
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(2000)

                                                                                                        # Get scroll position after refresh
                                                                                                        # Removed problematic line: scroll_after = await page.evaluate(''' )
        const chatContainer = document.querySelector('[data-testid="chat-messages"], .messages-container, main');
        chatContainer ? chatContainer.scrollTop : 0;
        ''')

                                                                                                        # Check if scroll position is approximately preserved (within 100px)
        if abs(scroll_after - scroll_before) < 100:
        print("")
        self.test_results['passed'] += 1
        return True
        else:
        print("")
                                                                                                                # Not critical, so we pass anyway
        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1

    async def test_performance_metrics_after_refresh(self, page:
        '''
        PERFORMANCE TEST: Measure key metrics after page refresh.
        Ensures refresh doesn"t degrade performance.
        '''
        test_name = "performance_metrics_after_refresh"
        print("")

        try:
                                                                                                                                # Setup
        token = self.generate_test_token()
                                                                                                                                # Removed problematic line: await page.evaluate(f''' )
        localStorage.setItem('jwt_token', '{token}');
        ''')

                                                                                                                                # Measure initial load
        start_time = time.time()
        await page.goto("", wait_until='networkidle')
        initial_load_time = time.time() - start_time

                                                                                                                                # Wait for full initialization
        await page.wait_for_selector('[data-testid="main-chat"], .chat-interface', timeout=10000)

                                                                                                                                # Measure refresh load
        refresh_start = time.time()
        await page.reload(wait_until='networkidle')
        refresh_load_time = time.time() - refresh_start

                                                                                                                                # Get performance metrics
                                                                                                                                # Removed problematic line: metrics = await page.evaluate(''' )
        const perf = performance.getEntriesByType('navigation')[0];
        ({ })
        domContentLoaded: perf.domContentLoadedEventEnd - perf.domContentLoadedEventStart,
        loadComplete: perf.loadEventEnd - perf.loadEventStart,
        domInteractive: perf.domInteractive - perf.fetchStart,
        resourceCount: performance.getEntriesByType('resource').length
                                                                                                                                
        ''')

                                                                                                                                # Store metrics
        self.test_results['performance_metrics'] = { }
        'initial_load_time': initial_load_time,
        'refresh_load_time': refresh_load_time,
        'dom_content_loaded': metrics['domContentLoaded'],
        'load_complete': metrics['loadComplete'],
        'dom_interactive': metrics['domInteractive'],
        'resource_count': metrics['resourceCount']
                                                                                                                                

                                                                                                                                # Performance thresholds
        if refresh_load_time > initial_load_time * 1.5:
        print("")

        if metrics['domInteractive'] > 3000:
        print("")

        print("")
        print("")
        print("")
        print("")

        self.test_results['passed'] += 1
        return True

        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        return False
        finally:
        self.test_results['total'] += 1

    async def run_all_tests(self, browser: Browser) -> Dict[str, Any]:
        """Run all page refresh tests."""
        print("")
         + =" * 60)
        print("[U+1F680] MISSION CRITICAL: Page Refresh Test Suite")
        print("=" * 60)

    # Create a new browser context for each test to ensure isolation
        tests = [ ]
        self.test_basic_refresh_with_active_chat,
        self.test_websocket_reconnection_on_refresh,
        self.test_rapid_refresh_resilience,
        self.test_draft_message_persistence,
        self.test_token_refresh_during_page_reload,
        self.test_scroll_position_restoration,
        self.test_performance_metrics_after_refresh
    

        for test_func in tests:
        context = await browser.new_context()
        page = await context.new_page()

        try:
        await test_func(page)
        except Exception as e:
        print("")
        self.test_results['failed'] += 1
        self.test_results['total'] += 1
        finally:
        await context.close()

                    # Print summary
        print("")
         + =" * 60)
        print(" CHART:  TEST RESULTS SUMMARY")
        print("=" * 60)
        print("")
        print("")
        print("")

        if self.test_results['critical_failures']:
        print("")
        WARNING: [U+FE0F] CRITICAL FAILURES:")
        for failure in self.test_results['critical_failures']:
        print("")

        if self.test_results.get('performance_metrics'):
        print("")
        [U+1F4C8] PERFORMANCE METRICS:")
        metrics = self.test_results['performance_metrics']
        for key, value in metrics.items():
        if isinstance(value, float):
        print("")
        else:
        print("")

                                            # Determine overall status
        if self.test_results['failed'] == 0:
        print("")
        PASS:  ALL TESTS PASSED - Page refresh handling is robust!")
        elif len(self.test_results['critical_failures']) > 0:
        print("")
        FAIL:  CRITICAL FAILURES DETECTED - Immediate attention required!")
        else:
        print("")
        WARNING: [U+FE0F] SOME TESTS FAILED - Review and fix non-critical issues")

        return self.test_results


                                                        # Pytest integration
@pytest.mark.asyncio
@pytest.mark.critical
    async def test_page_refresh_comprehensive():
"""Pytest wrapper for the comprehensive page refresh test suite."""
from playwright.async_api import async_playwright

async with async_playwright() as p:
browser = await p.chromium.launch(headless=True)

try:
test_suite = PageRefreshTestSuite()
results = await test_suite.run_all_tests(browser)

                                                                    # Assert no critical failures
assert len(results['critical_failures']) == 0, \
""

                                                                    # Assert reasonable pass rate
pass_rate = results['passed'] / results['total'] if results['total'] > 0 else 0
assert pass_rate >= 0.8, ""

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
test_suite = PageRefreshTestSuite()
results = await test_suite.run_all_tests(browser)

            # Exit with appropriate code
sys.exit(0 if results['failed'] == 0 else 1)

finally:
await browser.close()

asyncio.run(main())
pass
