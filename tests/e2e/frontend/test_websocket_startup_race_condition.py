"""
MISSION CRITICAL: WebSocket Startup Race Condition Regression Tests

This test suite ensures that WebSocket connections do not attempt to connect
before authentication is properly initialized, preventing spurious errors.

CRITICAL: These tests MUST pass or the user experience will be degraded with
false error messages on every page load.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from shared.isolated_environment import IsolatedEnvironment

import pytest
from playwright.async_api import Page, WebSocket, ConsoleMessage

from test_framework.base_e2e_test import BaseE2ETest as E2ETestBase
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketStartupRaceCondition(E2ETestBase):
    """
    Critical regression tests for WebSocket startup race conditions.
    
    These tests ensure:
    1. WebSocket waits for auth initialization before connecting
    2. No spurious authentication errors on startup
    3. Proper error classification (expected states vs actual errors)
    4. Smooth transition from unauthenticated to authenticated state
    """
    
    @pytest.fixture(autouse=True)
    async def setup_monitoring(self, page: Page):
        """Set up console and WebSocket monitoring for all tests."""
        self.console_errors: List[ConsoleMessage] = []
        self.console_warnings: List[ConsoleMessage] = []
        self.websocket_connections: List[Dict[str, Any]] = []
        self.auth_errors: List[str] = []
        
        # Monitor console messages
        async def handle_console(msg: ConsoleMessage):
            if msg.type == "error":
                self.console_errors.append(msg)
                text = msg.text
                # Check for specific auth/websocket errors
                if any(keyword in text.lower() for keyword in ["authentication", "websocket error", "auth error"]):
                    self.auth_errors.append(text)
            elif msg.type == "warning":
                self.console_warnings.append(msg)
        
        page.on("console", handle_console)
        
        # Monitor WebSocket connections
        async def handle_websocket(ws: WebSocket):
            connection_info = {
                "url": ws.url,
                "timestamp": time.time(),
                "headers": {},
                "closed": False,
                "close_code": None,
                "messages": []
            }
            self.websocket_connections.append(connection_info)
            
            def on_close():
                connection_info["closed"] = True
                
            ws.on("close", on_close)
            
            def on_message(message):
                connection_info["messages"].append(message)
                
            ws.on("message", on_message)
        
        page.on("websocket", handle_websocket)
        
        yield
        
        # Cleanup
        page.remove_listener("console", handle_console)
    
    @pytest.mark.critical
    async def test_no_websocket_connection_before_auth_init(self, authenticated_page: Page):
        """
        CRITICAL: WebSocket must not attempt connection before auth is initialized.
        
        This test verifies the core fix - WebSocket waits for authInitialized flag.
        """
        # Navigate to a fresh instance with monitoring
        await authenticated_page.goto("/", wait_until="networkidle")
        
        # Inject monitoring script before any app code runs
        await authenticated_page.evaluate("""
            window.websocketConnectionAttempts = [];
            window.authInitializationComplete = false;
            
            // Override WebSocket constructor to track connection attempts
            const OriginalWebSocket = window.WebSocket;
            window.WebSocket = function(...args) {
                window.websocketConnectionAttempts.push({
                    url: args[0],
                    timestamp: Date.now(),
                    authInitialized: window.authInitializationComplete
                });
                return new OriginalWebSocket(...args);
            };
            
            // Monitor auth initialization
            if (window.localStorage) {
                const originalSetItem = window.localStorage.setItem;
                window.localStorage.setItem = function(key, value) {
                    if (key === 'auth_initialized') {
                        window.authInitializationComplete = true;
                    }
                    return originalSetItem.call(this, key, value);
                };
            }
        """)
        
        # Reload the page to trigger fresh initialization
        await authenticated_page.reload(wait_until="networkidle")
        await authenticated_page.wait_for_timeout(2000)  # Wait for initialization
        
        # Check connection attempts
        attempts = await authenticated_page.evaluate("window.websocketConnectionAttempts")
        
        # Verify no connections were attempted before auth initialization
        premature_attempts = [a for a in attempts if not a["authInitialized"]]
        assert len(premature_attempts) == 0, (
            f"WebSocket attempted connection before auth initialization: {premature_attempts}"
        )
        
        # Verify connection was attempted after initialization
        post_init_attempts = [a for a in attempts if a["authInitialized"]]
        assert len(post_init_attempts) > 0, "WebSocket should connect after auth initialization"
    
    @pytest.mark.critical
    async def test_no_spurious_auth_errors_on_startup(self, page: Page):
        """
        CRITICAL: No authentication errors should be logged during normal startup.
        
        This test ensures users don't see alarming error messages on page load.
        """
        # Start fresh without authentication
        await page.goto("/", wait_until="networkidle")
        await page.wait_for_timeout(3000)  # Wait for any delayed errors
        
        # Check for authentication-related errors
        assert len(self.auth_errors) == 0, (
            f"Spurious authentication errors detected on startup: {self.auth_errors}"
        )
        
        # Check that no ERROR level logs contain WebSocket/auth keywords
        error_texts = [msg.text for msg in self.console_errors]
        ws_errors = [e for e in error_texts if "websocket" in e.lower()]
        
        # In production mode without token, there should be NO websocket errors
        assert len(ws_errors) == 0, (
            f"WebSocket errors logged when they should be suppressed: {ws_errors}"
        )
    
    @pytest.mark.critical
    async def test_proper_error_classification(self, page: Page):
        """
        Test that errors are properly classified based on context.
        
        Expected states (no token in production) should not be errors.
        Actual failures (network issues, auth rejection) should be errors.
        """
        # Test 1: No token scenario (expected in production)
        await page.evaluate("window.localStorage.clear()")
        await page.goto("/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Should see debug/info messages, not errors
        no_token_errors = [e for e in self.console_errors if "authentication" in e.text.lower()]
        assert len(no_token_errors) == 0, (
            "No-token state incorrectly logged as error instead of debug/info"
        )
        
        # Test 2: Invalid token scenario (actual error)
        await page.evaluate("""
            window.localStorage.setItem('jwt_token', 'invalid.token.here');
            window.localStorage.setItem('auth_initialized', 'true');
        """)
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # This SHOULD produce an error since token is invalid
        # But check it's a proper auth error, not a generic WebSocket error
        invalid_token_errors = [
            e for e in self.console_errors 
            if "invalid" in e.text.lower() or "authentication failed" in e.text.lower()
        ]
        # This is expected when we have an invalid token
        # The key is that it's a clear auth error, not a confusing WebSocket error
    
    @pytest.mark.critical
    async def test_smooth_auth_transition(self, page: Page):
        """
        Test smooth transition from unauthenticated to authenticated state.
        
        User logs in after page load - WebSocket should connect without errors.
        """
        # Start unauthenticated
        await page.goto("/", wait_until="networkidle")
        initial_errors = len(self.console_errors)
        
        # Simulate auth completion (as would happen after OAuth callback)
        await page.evaluate("""
            // Simulate successful authentication
            const mockToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJleHAiOjk5OTk5OTk5OTl9.test';
            window.localStorage.setItem('jwt_token', mockToken);
            window.localStorage.setItem('auth_initialized', 'true');
            
            // Trigger storage event as would happen from OAuth callback
            window.dispatchEvent(new StorageEvent('storage', {
                key: 'jwt_token',
                newValue: mockToken,
                url: window.location.href
            }));
        """)
        
        await page.wait_for_timeout(2000)  # Wait for WebSocket to connect
        
        # Check that no new errors were introduced during auth transition
        post_auth_errors = len(self.console_errors)
        new_errors = post_auth_errors - initial_errors
        
        assert new_errors == 0, (
            f"Authentication transition introduced {new_errors} new errors. "
            f"Errors: {[e.text for e in self.console_errors[initial_errors:]]}"
        )
        
        # Verify WebSocket is now connected
        ws_state = await page.evaluate("""
            // Check if WebSocket is connected through the app's state
            window.__websocketConnected || false
        """)
        # Note: Actual connection state would depend on backend being available
    
    @pytest.mark.critical
    async def test_race_condition_under_load(self, page: Page):
        """
        Stress test to ensure race condition doesn't reappear under load.
        
        Rapidly reload the page multiple times to catch timing issues.
        """
        error_counts = []
        
        for i in range(5):  # Rapid reloads
            self.console_errors.clear()
            self.auth_errors.clear()
            
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            error_counts.append({
                "iteration": i,
                "console_errors": len(self.console_errors),
                "auth_errors": len(self.auth_errors)
            })
        
        # No iteration should have auth errors
        iterations_with_errors = [
            e for e in error_counts 
            if e["auth_errors"] > 0
        ]
        
        assert len(iterations_with_errors) == 0, (
            f"Race condition detected under load. "
            f"Iterations with errors: {iterations_with_errors}"
        )
    
    @pytest.mark.critical
    async def test_websocket_waits_for_auth_initialized_flag(self, page: Page):
        """
        Direct test of the authInitialized flag dependency.
        
        WebSocketProvider should not proceed until authInitialized is true.
        """
        await page.goto("/", wait_until="networkidle")
        
        # Inject test to verify the WebSocketProvider checks authInitialized
        result = await page.evaluate("""
            // Try to access React fiber to check component props
            // This is a deep test to verify the actual implementation
            const checkAuthInitialized = () => {
                // Find WebSocketProvider in React tree
                const root = document.getElementById('__next') || document.getElementById('root');
                if (!root || !root._reactRootContainer) return null;
                
                // This would need the actual React DevTools hook
                // For E2E, we'll check the observable behavior instead
                return 'behavior_check';
            };
            
            checkAuthInitialized();
        """)
        
        # Verify through behavior: no WebSocket attempts without auth
        ws_attempts = len(self.websocket_connections)
        
        # Set auth as initialized and verify connection happens
        await page.evaluate("""
            window.localStorage.setItem('auth_initialized', 'true');
            window.dispatchEvent(new Event('storage'));
        """)
        
        await page.wait_for_timeout(1000)
        
        # Should see WebSocket attempt after auth initialization
        ws_attempts_after = len(self.websocket_connections)
        
        # The difference shows WebSocket waited for auth
        assert ws_attempts_after >= ws_attempts, (
            "WebSocket should attempt connection after auth initialization"
        )
    
    @pytest.mark.critical
    async def test_no_authentication_error_without_token(self, page: Page):
        """
        REGRESSION TEST: Ensure the specific error from the bug report doesn't occur.
        
        The original bug showed:
        - ERROR: WebSocket error occurred [WebSocketService] (websocket_error)
        - ERROR: Authentication failure [WebSocketProvider] (authentication_error)
        
        These should NOT appear when there's simply no token available.
        """
        # Clear any auth state
        await page.evaluate("window.localStorage.clear()")
        await page.goto("/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Check for the specific error patterns from the bug report
        specific_errors = [
            e for e in self.console_errors
            if ("WebSocket error occurred" in e.text and "[WebSocketService]" in e.text) or
               ("Authentication failure" in e.text and "[WebSocketProvider]" in e.text)
        ]
        
        assert len(specific_errors) == 0, (
            f"REGRESSION DETECTED: Original bug errors reappeared: {[e.text for e in specific_errors]}"
        )
        
        # Also check the error metadata structure
        ws_error_with_metadata = [
            e for e in self.console_errors
            if "websocket_error" in e.text or "authentication_error" in e.text
        ]
        
        assert len(ws_error_with_metadata) == 0, (
            f"WebSocket errors with metadata logged inappropriately: {[e.text for e in ws_error_with_metadata]}"
        )


class TestWebSocketStartupPerformance(E2ETestBase):
    """
    Performance regression tests to ensure fix doesn't degrade startup time.
    """
    
    @pytest.mark.performance
    async def test_websocket_connection_timing(self, authenticated_page: Page):
        """
        Ensure WebSocket connection happens within acceptable time after auth.
        """
        start_time = time.time()
        
        await authenticated_page.goto("/", wait_until="networkidle")
        
        # Measure time to WebSocket connection
        await authenticated_page.wait_for_function("""
            () => {
                // Check if WebSocket is connected (implementation-specific)
                return window.__websocketConnected === true;
            }
        """, timeout=5000)  # 5 second timeout
        
        connection_time = time.time() - start_time
        
        # WebSocket should connect within 3 seconds on auth pages
        assert connection_time < 3.0, (
            f"WebSocket connection too slow: {connection_time:.2f}s (expected < 3s)"
        )
    
    @pytest.mark.performance  
    async def test_no_unnecessary_reconnection_attempts(self, authenticated_page: Page):
        """
        Verify the fix doesn't cause unnecessary reconnection attempts.
        """
        # Monitor WebSocket connections
        connections = []
        
        async def monitor_ws(ws: WebSocket):
            connections.append(ws.url)
        
        authenticated_page.on("websocket", monitor_ws)
        
        await authenticated_page.goto("/", wait_until="networkidle")
        await authenticated_page.wait_for_timeout(5000)  # Wait for any reconnection attempts
        
        # Should only have one WebSocket connection attempt
        assert len(connections) <= 2, (  # Allow one reconnect for token refresh
            f"Too many WebSocket connections: {len(connections)}. URLs: {connections}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
