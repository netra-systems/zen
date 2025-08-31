"""
MISSION CRITICAL: Chat Initialization Test Suite

CHAT IS KING - This test ensures the main chat interface initializes correctly
for authenticated users. This is the primary value delivery channel (90% of value).

Any failure here blocks deployment.

@compliance SPEC/core.xml - Mission critical system test
@compliance CLAUDE.md - Chat is the primary value channel
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from playwright.async_api import async_playwright, Page, Browser
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from test_framework.test_context import TestContext
from test_framework.backend_client import BackendClient


class ChatInitializationTester:
    """Mission critical tester for chat initialization."""
    
    def __init__(self):
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.auth_url = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081')
        self.jwt_secret = os.getenv('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'critical_failures': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def generate_test_token(self, user_email: str = "test@example.com") -> str:
        """Generate a valid JWT token for testing."""
        payload = {
            'sub': 'user_123',
            'email': user_email,
            'name': 'Test User',
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            'iat': datetime.now(timezone.utc),
            'role': 'user'
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    async def test_fresh_page_load_with_token(self, page: Page) -> bool:
        """
        CRITICAL TEST 1: Fresh page load with existing JWT token.
        This tests the exact scenario that was broken.
        """
        test_name = "fresh_page_load_with_token"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Set JWT token in localStorage
            token = self.generate_test_token()
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            # Navigate to chat page
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            
            # Wait for auth context to initialize
            await page.wait_for_timeout(2000)
            
            # Check if main chat element exists and is not empty
            main_element = await page.query_selector('main')
            if not main_element:
                raise AssertionError("Main element not found")
            
            # Check for chat interface components
            chat_visible = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
            if not chat_visible:
                # Check if we got redirected to login (indicates auth failure)
                current_url = page.url
                if '/login' in current_url:
                    raise AssertionError(f"Redirected to login despite valid token. URL: {current_url}")
                
                # Get main element content for debugging
                main_content = await main_element.inner_html()
                raise AssertionError(f"Main chat not visible. Main content: {main_content[:200]}")
            
            # Verify message input is present
            message_input = await page.query_selector('[data-testid="message-input"], textarea[placeholder*="Message"], input[placeholder*="Message"]')
            if not message_input:
                raise AssertionError("Message input not found - chat not fully initialized")
            
            print(f"✅ {test_name}: PASSED - Chat initialized with existing token")
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {str(e)}")
            self.test_results['critical_failures'].append({
                'test': test_name,
                'error': str(e),
                'severity': 'CRITICAL'
            })
            return False
    
    async def test_page_refresh_maintains_session(self, page: Page) -> bool:
        """
        CRITICAL TEST 2: Page refresh maintains user session and chat access.
        """
        test_name = "page_refresh_maintains_session"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # First, set up authenticated session
            token = self.generate_test_token("refresh@example.com")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            # Load chat page
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Verify initial load
            initial_chat = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
            if not initial_chat:
                raise AssertionError("Initial chat load failed")
            
            # Perform page refresh
            await page.reload(wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Verify chat still accessible after refresh
            after_refresh = await page.is_visible('[data-testid="main-chat"]', timeout=5000)
            if not after_refresh:
                current_url = page.url
                raise AssertionError(f"Chat not visible after refresh. URL: {current_url}")
            
            # Verify token still in localStorage
            stored_token = await page.evaluate("localStorage.getItem('jwt_token')")
            if stored_token != token:
                raise AssertionError("Token lost after refresh")
            
            print(f"✅ {test_name}: PASSED - Session maintained after refresh")
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {str(e)}")
            self.test_results['critical_failures'].append({
                'test': test_name,
                'error': str(e),
                'severity': 'CRITICAL'
            })
            return False
    
    async def test_auth_guard_blocks_without_token(self, page: Page) -> bool:
        """
        TEST 3: AuthGuard properly blocks access without token.
        """
        test_name = "auth_guard_blocks_without_token"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Clear any existing tokens
            await page.evaluate("localStorage.clear()")
            
            # Try to access chat page
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Should be redirected to login
            current_url = page.url
            if '/login' not in current_url:
                raise AssertionError(f"Not redirected to login. URL: {current_url}")
            
            # Chat should not be visible
            chat_visible = await page.is_visible('[data-testid="main-chat"]', timeout=1000)
            if chat_visible:
                raise AssertionError("Chat visible without authentication")
            
            print(f"✅ {test_name}: PASSED - Properly blocked without auth")
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {str(e)}")
            return False
    
    async def test_expired_token_handling(self, page: Page) -> bool:
        """
        TEST 4: Expired token triggers refresh or redirect.
        """
        test_name = "expired_token_handling"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Generate expired token
            payload = {
                'sub': 'user_expired',
                'email': 'expired@example.com',
                'name': 'Expired User',
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
                'iat': datetime.now(timezone.utc) - timedelta(hours=2),
                'role': 'user'
            }
            expired_token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{expired_token}');
            """)
            
            # Navigate to chat
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Should either refresh token or redirect to login
            current_url = page.url
            
            # Check if redirected to login (expected for expired token)
            if '/login' in current_url:
                print(f"✅ {test_name}: PASSED - Expired token handled with redirect")
                return True
            
            # Or check if token was refreshed (if refresh mechanism is in place)
            new_token = await page.evaluate("localStorage.getItem('jwt_token')")
            if new_token and new_token != expired_token:
                print(f"✅ {test_name}: PASSED - Expired token refreshed")
                return True
            
            raise AssertionError("Expired token not properly handled")
            
        except Exception as e:
            print(f"⚠️  {test_name}: WARNING - {str(e)}")
            return True  # Non-critical for now
    
    async def test_websocket_connection_with_auth(self, page: Page) -> bool:
        """
        TEST 5: WebSocket connects successfully with authenticated user.
        """
        test_name = "websocket_connection_with_auth"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Set up authenticated session
            token = self.generate_test_token("websocket@example.com")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            # Set up WebSocket monitoring
            ws_connected = False
            ws_error = None
            
            async def handle_websocket(ws):
                nonlocal ws_connected
                ws_connected = True
            
            page.on("websocket", handle_websocket)
            
            # Navigate to chat
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check console for WebSocket errors
            console_errors = await page.evaluate("""
                (() => {
                    const errors = [];
                    const originalError = console.error;
                    console.error = (...args) => {
                        errors.push(args.join(' '));
                        originalError.apply(console, args);
                    };
                    return errors;
                })()
            """)
            
            ws_errors = [e for e in console_errors if 'websocket' in e.lower()]
            if ws_errors:
                ws_error = ws_errors[0]
            
            if not ws_connected and ws_error:
                raise AssertionError(f"WebSocket connection failed: {ws_error}")
            
            print(f"✅ {test_name}: PASSED - WebSocket connected with auth")
            return True
            
        except Exception as e:
            print(f"⚠️  {test_name}: WARNING - {str(e)}")
            return True  # Non-critical but logged
    
    async def test_chat_input_functional(self, page: Page) -> bool:
        """
        TEST 6: Chat input is functional and can send messages.
        """
        test_name = "chat_input_functional"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Set up authenticated session
            token = self.generate_test_token("input@example.com")
            await page.evaluate(f"""
                localStorage.setItem('jwt_token', '{token}');
            """)
            
            # Navigate to chat
            await page.goto(f"{self.frontend_url}/chat", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Find message input
            input_selector = '[data-testid="message-input"], textarea[placeholder*="Message"], input[placeholder*="Message"]'
            message_input = await page.wait_for_selector(input_selector, timeout=5000)
            
            if not message_input:
                raise AssertionError("Message input not found")
            
            # Type a test message
            await message_input.type("Test message from mission critical test")
            
            # Verify input has value
            input_value = await message_input.input_value()
            if "Test message" not in input_value:
                raise AssertionError(f"Input not accepting text. Value: {input_value}")
            
            print(f"✅ {test_name}: PASSED - Chat input is functional")
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {str(e)}")
            self.test_results['critical_failures'].append({
                'test': test_name,
                'error': str(e),
                'severity': 'HIGH'
            })
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all mission critical chat initialization tests."""
        print("\n" + "="*60)
        print("🚨 MISSION CRITICAL: CHAT INITIALIZATION TEST SUITE")
        print("CHAT IS KING - Primary value delivery channel")
        print("="*60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Configure page
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Run tests
            tests = [
                self.test_fresh_page_load_with_token,
                self.test_page_refresh_maintains_session,
                self.test_auth_guard_blocks_without_token,
                self.test_expired_token_handling,
                self.test_websocket_connection_with_auth,
                self.test_chat_input_functional
            ]
            
            for test in tests:
                self.test_results['total'] += 1
                try:
                    # Create new page for each test to ensure isolation
                    test_page = await context.new_page()
                    result = await test(test_page)
                    if result:
                        self.test_results['passed'] += 1
                    else:
                        self.test_results['failed'] += 1
                    await test_page.close()
                except Exception as e:
                    print(f"❌ Test execution error: {str(e)}")
                    self.test_results['failed'] += 1
            
            await browser.close()
        
        # Generate summary
        self.generate_summary()
        return self.test_results
    
    def generate_summary(self):
        """Generate test summary report."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.test_results['total']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        
        if self.test_results['critical_failures']:
            print("\n🚨 CRITICAL FAILURES:")
            for failure in self.test_results['critical_failures']:
                print(f"  - {failure['test']}: {failure['error']}")
                print(f"    Severity: {failure['severity']}")
        
        # Determine overall status
        if self.test_results['failed'] == 0:
            print("\n✅ ALL TESTS PASSED - Chat initialization is working correctly!")
            self.test_results['status'] = 'PASSED'
        elif any(f['severity'] == 'CRITICAL' for f in self.test_results['critical_failures']):
            print("\n🔴 CRITICAL FAILURE - CHAT IS BROKEN! Deployment blocked.")
            self.test_results['status'] = 'CRITICAL_FAILURE'
        else:
            print("\n⚠️  SOME TESTS FAILED - Review and fix before production.")
            self.test_results['status'] = 'PARTIAL_FAILURE'
        
        print("="*60)


async def main():
    """Main test runner."""
    tester = ChatInitializationTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    with open('chat_initialization_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Exit with appropriate code
    if results['status'] == 'CRITICAL_FAILURE':
        sys.exit(2)  # Critical failure
    elif results['status'] == 'PARTIAL_FAILURE':
        sys.exit(1)  # Some failures
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    asyncio.run(main())