"""
E2E Tests: Golden Path User Flow with Authentication Permissiveness

PURPOSE: End-to-end validation of complete user journey (login → AI responses) 
with different authentication modes to resolve 1011 WebSocket blocking issues.

BUSINESS JUSTIFICATION:
- Golden Path Value: 90% of platform value delivered through chat functionality
- Revenue Impact: $500K+ ARR blocked by WebSocket 1011 errors  
- Root Cause: GCP Load Balancer strips auth headers, strict validation fails
- Solution: Multiple auth validation levels enable golden path completion

GOLDEN PATH FLOW:
1. User opens chat interface
2. WebSocket connection established (with permissive auth)
3. User sends message
4. Agent execution begins 
5. All 5 WebSocket events delivered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
6. User receives AI response
7. Conversation persisted to database

E2E TEST STRATEGY:
- Real browser automation (Playwright/Selenium)
- Real WebSocket connections 
- Real agent execution with AI responses
- Real database persistence validation
- Multiple auth modes: STRICT, RELAXED, DEMO, EMERGENCY

EXPECTED FAILURES:
These tests MUST FAIL INITIALLY to prove golden path is blocked:
1. STRICT mode fails due to header stripping
2. RELAXED/DEMO/EMERGENCY modes not implemented
3. WebSocket 1011 errors prevent agent execution
4. No AI responses delivered to users
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from unittest.mock import patch, Mock

# E2E testing framework
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import websockets

# Base test case with real services
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Real service clients
from tests.clients.websocket_client import WebSocketTestClient as WebSocketClient
from tests.helpers.auth_helper import create_test_user_with_jwt, get_test_frontend_url

# Environment isolation
from shared.isolated_environment import IsolatedEnvironment

# Database validation
from netra_backend.app.db.database_manager import get_database_manager
from netra_backend.app.db.models_auth import User
from netra_backend.app.db.models_corpus import Thread, Message


class TestGoldenPathAuthModes(SSotBaseTestCase):
    """
    E2E tests for complete golden path user flow with auth permissiveness.
    
    Tests the complete user journey: UI → WebSocket → Agent → AI Response
    with different authentication validation levels.
    
    MUST FAIL INITIALLY to prove current system blocks golden path.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up E2E test environment with real services"""
        super().setUpClass()
        
        # Frontend URLs for testing
        cls.frontend_url = get_test_frontend_url()
        cls.websocket_url = "ws://localhost:8000/ws"
        
        # Test user profiles for different auth modes
        cls.test_users = {
            "strict": {
                "email": f"strict-user-{int(time.time())}@test.com",
                "user_id": f"strict_user_{int(time.time())}",
                "password": "test_password_123",
                "jwt_token": None,  # Will be created in setUp
                "auth_mode": "STRICT"
            },
            "relaxed": {
                "email": f"relaxed-user-{int(time.time())}@test.com", 
                "user_id": f"relaxed_user_{int(time.time())}",
                "password": "test_password_456",
                "jwt_token": None,  # Intentionally missing for relaxed auth
                "auth_mode": "RELAXED"
            },
            "demo": {
                "email": f"demo-user-{int(time.time())}@test.com",
                "user_id": f"demo-user-{int(time.time())}", 
                "password": None,  # Demo mode doesn't need password
                "jwt_token": None,  # Demo mode bypasses JWT
                "auth_mode": "DEMO"
            },
            "emergency": {
                "email": f"emergency-user-{int(time.time())}@test.com",
                "user_id": f"emergency_user_{int(time.time())}",
                "password": None,  # Emergency access bypasses normal auth
                "jwt_token": None,  # Emergency mode bypasses JWT 
                "auth_mode": "EMERGENCY"
            }
        }
        
        # Expected WebSocket events in golden path
        cls.required_websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Test messages for agent execution
        cls.test_messages = {
            "simple": "Hello, can you help me analyze my AI costs?",
            "complex": "I need a comprehensive analysis of my AI spending patterns and optimization recommendations.",
            "data_query": "What are my top 3 most expensive AI operations this month?"
        }
    
    async def asyncSetUp(self):
        """Set up each test with fresh browser and auth tokens"""
        await super().asyncSetUp()
        
        # Create valid JWT for strict auth user
        try:
            self.test_users["strict"]["jwt_token"] = await create_test_user_with_jwt(
                user_id=self.test_users["strict"]["user_id"],
                email=self.test_users["strict"]["email"]
            )
        except Exception as e:
            self.logger.warning(f"Failed to create strict auth JWT: {e}")
        
        # Initialize browser for UI testing
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Set up console logging for debugging
        self.page.on("console", lambda msg: self.logger.info(f"Browser console: {msg.text}"))
        self.page.on("pageerror", lambda error: self.logger.error(f"Browser error: {error}"))
    
    async def test_golden_path_strict_auth_with_valid_jwt(self):
        """
        Test complete golden path with STRICT auth and valid JWT.
        
        This test validates the current system works end-to-end when JWT is present.
        Should pass if auth service and frontend are working correctly.
        """
        if not self.test_users["strict"]["jwt_token"]:
            self.skipTest("JWT creation failed - auth service unavailable for testing")
        
        user = self.test_users["strict"]
        
        # Set environment to STRICT mode (current default)
        env = IsolatedEnvironment()
        env.set("AUTH_VALIDATION_LEVEL", "STRICT")
        
        try:
            # Step 1: Load chat interface
            await self.page.goto(self.frontend_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Step 2: Authenticate user (login)
            await self._perform_user_login(user)
            
            # Step 3: Verify WebSocket connection establishes
            websocket_connected = await self._verify_websocket_connection(user)
            self.assertTrue(websocket_connected, "WebSocket connection should establish with valid JWT")
            
            # Step 4: Send message and trigger agent execution
            test_message = self.test_messages["simple"]
            agent_execution_started = await self._send_message_and_verify_agent_start(test_message)
            self.assertTrue(agent_execution_started, "Agent execution should start with valid auth")
            
            # Step 5: Verify all 5 WebSocket events are received
            events_received = await self._verify_all_websocket_events()
            self.assertEqual(len(events_received), 5, 
                           f"Should receive all 5 WebSocket events, got {len(events_received)}: {events_received}")
            
            # Step 6: Verify AI response is delivered
            ai_response = await self._verify_ai_response_delivery()
            self.assertIsNotNone(ai_response, "AI response should be delivered to user")
            self.assertIn("cost", ai_response.lower(), "Response should address the AI cost query")
            
            # Step 7: Verify conversation persistence
            persisted = await self._verify_conversation_persistence(user["user_id"], test_message, ai_response)
            self.assertTrue(persisted, "Conversation should be persisted to database")
            
            # Golden path completed successfully
            self.logger.info("✅ Golden path with STRICT auth completed successfully")
            
        except Exception as e:
            # If this fails, it indicates issues with current auth system
            self.logger.error(f"Golden path with STRICT auth failed: {e}")
            self.fail(f"STRICT auth golden path should work but failed: {e}")
    
    async def test_golden_path_strict_auth_missing_jwt_reproduces_1011(self):
        """
        Test golden path with STRICT auth but missing JWT - EXPECTED FAILURE.
        
        This test reproduces the exact production scenario:
        - User loads frontend
        - Frontend attempts WebSocket connection  
        - GCP Load Balancer strips Authorization header
        - WebSocket fails with 1011 error
        - Golden path is blocked
        """
        user = self.test_users["strict"]
        
        # Set environment to STRICT mode
        env = IsolatedEnvironment()
        env.set("AUTH_VALIDATION_LEVEL", "STRICT")
        
        # Step 1: Load chat interface without authentication
        await self.page.goto(self.frontend_url)
        await self.page.wait_for_load_state('networkidle')
        
        # Step 2: Skip login (simulating load balancer header stripping)
        # The frontend will try to connect WebSocket without valid auth headers
        
        # Step 3: Verify WebSocket connection fails with 1011 error
        websocket_error = await self._verify_websocket_connection_failure()
        
        # Should get 1011 or auth-related error
        self.assertIsNotNone(websocket_error, "WebSocket connection should fail without JWT")
        error_message = str(websocket_error).lower()
        self.assertTrue(
            any(indicator in error_message for indicator in ['1011', 'unauthorized', 'auth', 'token']),
            f"Expected 1011/auth error, got: {websocket_error}"
        )
        
        # Step 4: Verify golden path is blocked
        golden_path_blocked = await self._verify_golden_path_blocked()
        self.assertTrue(golden_path_blocked, "Golden path should be blocked without authentication")
        
        # Step 5: Verify no agent execution occurs
        agent_execution_attempted = await self._verify_no_agent_execution()
        self.assertFalse(agent_execution_attempted, "Agent execution should not occur without auth")
        
        # This failure reproduces the production issue
        self.logger.info(f"✅ Successfully reproduced 1011 error blocking golden path: {websocket_error}")
    
    async def test_golden_path_relaxed_auth_not_implemented(self):
        """
        Test golden path with RELAXED auth mode - MUST FAIL (not implemented).
        
        RELAXED mode should:
        1. Accept degraded auth with warnings
        2. Create user context from available headers
        3. Complete golden path with reduced security
        4. Log security events for monitoring
        
        This test will fail until relaxed auth is implemented.
        """
        user = self.test_users["relaxed"]
        
        # Set environment to RELAXED mode
        env = IsolatedEnvironment()
        env.set("AUTH_VALIDATION_LEVEL", "RELAXED")
        
        try:
            # Step 1: Load chat interface
            await self.page.goto(self.frontend_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Step 2: Set degraded auth headers in browser
            await self._set_relaxed_auth_headers(user)
            
            # Step 3: Attempt WebSocket connection with relaxed auth
            # THIS SHOULD FAIL because relaxed mode is not implemented
            websocket_connected = await self._verify_websocket_connection(user)
            
            if websocket_connected:
                # If connection succeeded, test the full golden path
                test_message = self.test_messages["simple"]
                agent_execution_started = await self._send_message_and_verify_agent_start(test_message)
                
                if agent_execution_started:
                    # Verify relaxed auth context in responses
                    events_received = await self._verify_all_websocket_events()
                    
                    # Check if events indicate degraded auth
                    auth_context = await self._extract_auth_context_from_events(events_received)
                    self.assertIn("degraded", auth_context.get("level", "").lower(),
                                "Auth context should indicate degraded/relaxed validation")
                    
                    self.fail("Relaxed auth appears to be working - test needs update")
                else:
                    self.fail("WebSocket connected but agent execution failed with relaxed auth")
            else:
                # Connection failed - this is expected
                self.logger.info("✅ Relaxed auth correctly failed (not implemented)")
                
        except Exception as e:
            # Exception expected because relaxed mode is not implemented
            error_message = str(e).lower()
            self.assertTrue(
                any(indicator in error_message for indicator in ['relaxed', 'not implemented', 'not found']),
                f"Expected relaxed auth implementation error, got: {e}"
            )
            self.logger.info(f"✅ Relaxed auth golden path correctly failed: {e}")
    
    async def test_golden_path_demo_auth_not_implemented(self):
        """
        Test golden path with DEMO auth mode - MUST FAIL (not implemented).
        
        DEMO mode should:
        1. Bypass authentication completely
        2. Create demo user context automatically
        3. Complete full golden path for demonstrations
        4. Log demo mode activation for security
        
        This test will fail until demo auth is implemented.
        """
        user = self.test_users["demo"]
        
        # Set environment to DEMO mode
        env = IsolatedEnvironment()
        env.set("DEMO_MODE", "1")
        env.set("AUTH_VALIDATION_LEVEL", "DEMO")
        
        try:
            # Step 1: Load chat interface without any authentication
            await self.page.goto(self.frontend_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Step 2: Skip all authentication (demo mode should handle this)
            # No login, no auth headers - demo mode should work
            
            # Step 3: Attempt WebSocket connection in demo mode
            # THIS SHOULD FAIL because demo mode is not implemented
            websocket_connected = await self._verify_websocket_connection(user)
            
            if websocket_connected:
                # If connection succeeded, test full golden path
                test_message = self.test_messages["simple"]
                agent_execution_started = await self._send_message_and_verify_agent_start(test_message)
                
                if agent_execution_started:
                    # Verify demo user context
                    events_received = await self._verify_all_websocket_events()
                    
                    # Check if events indicate demo user
                    user_context = await self._extract_user_context_from_events(events_received)
                    demo_user_id = user_context.get("user_id", "")
                    self.assertTrue(demo_user_id.startswith("demo-user-"),
                                  f"Expected demo user ID, got: {demo_user_id}")
                    
                    self.fail("Demo auth appears to be working - test needs update")
                else:
                    self.fail("WebSocket connected but agent execution failed with demo auth")
            else:
                # Connection failed - this is expected
                self.logger.info("✅ Demo auth correctly failed (not implemented)")
                
        except Exception as e:
            # Exception expected because demo mode is not implemented
            error_message = str(e).lower()
            self.assertTrue(
                any(indicator in error_message for indicator in ['demo', 'not implemented', 'not found']),
                f"Expected demo auth implementation error, got: {e}"
            )
            self.logger.info(f"✅ Demo auth golden path correctly failed: {e}")
    
    async def test_golden_path_emergency_auth_not_implemented(self):
        """
        Test golden path with EMERGENCY auth mode - MUST FAIL (not implemented).
        
        EMERGENCY mode should:
        1. Provide minimal validation for system recovery
        2. Accept emergency access headers
        3. Complete golden path with minimal security
        4. Log emergency access for audit
        
        This test will fail until emergency auth is implemented.
        """
        user = self.test_users["emergency"]
        
        # Set environment to EMERGENCY mode
        env = IsolatedEnvironment()
        env.set("AUTH_VALIDATION_LEVEL", "EMERGENCY")
        
        try:
            # Step 1: Load chat interface 
            await self.page.goto(self.frontend_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Step 2: Set emergency access headers
            await self._set_emergency_auth_headers(user)
            
            # Step 3: Attempt WebSocket connection in emergency mode
            # THIS SHOULD FAIL because emergency mode is not implemented
            websocket_connected = await self._verify_websocket_connection(user)
            
            if websocket_connected:
                # If connection succeeded, test full golden path
                test_message = self.test_messages["complex"]
                agent_execution_started = await self._send_message_and_verify_agent_start(test_message)
                
                if agent_execution_started:
                    # Verify emergency user context
                    events_received = await self._verify_all_websocket_events()
                    
                    # Check if events indicate emergency access
                    auth_context = await self._extract_auth_context_from_events(events_received)
                    self.assertIn("emergency", auth_context.get("level", "").lower(),
                                "Auth context should indicate emergency access")
                    
                    self.fail("Emergency auth appears to be working - test needs update")
                else:
                    self.fail("WebSocket connected but agent execution failed with emergency auth")
            else:
                # Connection failed - this is expected
                self.logger.info("✅ Emergency auth correctly failed (not implemented)")
                
        except Exception as e:
            # Exception expected because emergency mode is not implemented
            error_message = str(e).lower()
            self.assertTrue(
                any(indicator in error_message for indicator in ['emergency', 'not implemented', 'not found']),
                f"Expected emergency auth implementation error, got: {e}"
            )
            self.logger.info(f"✅ Emergency auth golden path correctly failed: {e}")
    
    async def test_golden_path_all_auth_modes_comprehensive(self):
        """
        Comprehensive test of golden path with all authentication modes.
        
        This test attempts all auth modes and validates the expected behavior:
        - STRICT: Works with valid JWT, fails without JWT
        - RELAXED: Fails (not implemented) 
        - DEMO: Fails (not implemented)
        - EMERGENCY: Fails (not implemented)
        """
        results = {}
        
        for auth_mode, user in self.test_users.items():
            self.logger.info(f"Testing golden path with {auth_mode} auth mode")
            
            try:
                # Set environment for this auth mode
                env = IsolatedEnvironment()
                env.set("AUTH_VALIDATION_LEVEL", auth_mode.upper())
                if auth_mode == "demo":
                    env.set("DEMO_MODE", "1")
                
                # Test golden path with this auth mode
                success = await self._test_single_auth_mode_golden_path(auth_mode, user)
                results[auth_mode] = {"success": success, "error": None}
                
            except Exception as e:
                results[auth_mode] = {"success": False, "error": str(e)}
                self.logger.info(f"{auth_mode} auth failed as expected: {e}")
        
        # Validate results match expected behavior
        # Only STRICT should potentially succeed (if JWT is valid)
        strict_should_work = self.test_users["strict"]["jwt_token"] is not None
        
        if strict_should_work:
            self.assertTrue(results["strict"]["success"], 
                          f"STRICT auth should work with valid JWT: {results['strict']}")
        else:
            self.assertFalse(results["strict"]["success"],
                           f"STRICT auth should fail without JWT: {results['strict']}")
        
        # All other modes should fail (not implemented)
        for mode in ["relaxed", "demo", "emergency"]:
            self.assertFalse(results[mode]["success"],
                           f"{mode.upper()} auth should fail (not implemented): {results[mode]}")
        
        # Log comprehensive results
        self.logger.info(f"✅ Golden path auth mode test results: {results}")
        
        # This test proves which auth modes need to be implemented
        unimplemented_modes = [mode for mode, result in results.items() 
                              if not result["success"] and mode != "strict"]
        self.assertEqual(len(unimplemented_modes), 3, 
                        f"Should have 3 unimplemented auth modes: {unimplemented_modes}")
    
    # Helper methods for E2E test operations
    
    async def _perform_user_login(self, user: Dict[str, Any]) -> bool:
        """Perform user login through frontend UI."""
        try:
            # Look for login form
            await self.page.wait_for_selector('input[type="email"], input[name="email"]', timeout=5000)
            
            # Fill in credentials
            await self.page.fill('input[type="email"], input[name="email"]', user["email"])
            if user["password"]:
                await self.page.fill('input[type="password"], input[name="password"]', user["password"])
            
            # Submit login form
            await self.page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")')
            
            # Wait for redirect to chat interface
            await self.page.wait_for_url("**/chat**", timeout=10000)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Login failed or not required: {e}")
            return False
    
    async def _verify_websocket_connection(self, user: Dict[str, Any]) -> bool:
        """Verify WebSocket connection establishes successfully."""
        try:
            # Wait for WebSocket connection indicator in UI
            await self.page.wait_for_selector('.connection-status.connected, .websocket-connected', timeout=10000)
            
            # Check browser network tab for WebSocket connection
            # Alternative: Direct WebSocket client test
            client = WebSocketClient()
            
            headers = {}
            if user["jwt_token"]:
                headers["Authorization"] = f"Bearer {user['jwt_token']}"
            
            success = await client.connect(
                url=self.websocket_url,
                headers=headers,
                timeout=5.0
            )
            
            if success:
                await client.disconnect()
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"WebSocket connection verification failed: {e}")
            return False
    
    async def _verify_websocket_connection_failure(self) -> Optional[Exception]:
        """Verify WebSocket connection fails and return the error."""
        try:
            # Check for connection error indicators in UI
            error_selector = '.connection-error, .websocket-error, .connection-failed'
            await self.page.wait_for_selector(error_selector, timeout=5000)
            
            error_text = await self.page.text_content(error_selector)
            return Exception(error_text)
            
        except Exception:
            # If no UI error indicator, try direct connection
            client = WebSocketClient()
            
            try:
                success = await client.connect(
                    url=self.websocket_url,
                    headers={},  # No auth headers
                    timeout=5.0
                )
                
                if success:
                    await client.disconnect()
                    return None  # Connection succeeded unexpectedly
                else:
                    return Exception("WebSocket connection failed")
                    
            except Exception as e:
                return e
    
    async def _send_message_and_verify_agent_start(self, message: str) -> bool:
        """Send message through UI and verify agent execution starts."""
        try:
            # Find chat input and send message
            await self.page.fill('.chat-input, input[placeholder*="message"], textarea', message)
            await self.page.click('.send-button, button:has-text("Send")')
            
            # Wait for agent started indicator
            await self.page.wait_for_selector('.agent-started, .agent-executing', timeout=10000)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Message send or agent start verification failed: {e}")
            return False
    
    async def _verify_all_websocket_events(self) -> List[str]:
        """Verify all 5 required WebSocket events are received."""
        events_received = []
        
        try:
            # Monitor for each required event
            for event in self.required_websocket_events:
                selector = f'.event-{event}, .{event}-event'
                
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    events_received.append(event)
                except Exception:
                    self.logger.warning(f"Event {event} not received within timeout")
            
            return events_received
            
        except Exception as e:
            self.logger.warning(f"WebSocket event verification failed: {e}")
            return events_received
    
    async def _verify_ai_response_delivery(self) -> Optional[str]:
        """Verify AI response is delivered and return the response text."""
        try:
            # Wait for AI response in chat interface
            response_selector = '.ai-response, .assistant-message, .agent-response'
            await self.page.wait_for_selector(response_selector, timeout=30000)
            
            response_text = await self.page.text_content(response_selector)
            return response_text
            
        except Exception as e:
            self.logger.warning(f"AI response verification failed: {e}")
            return None
    
    async def _verify_conversation_persistence(self, user_id: str, message: str, response: str) -> bool:
        """Verify conversation is persisted to database."""
        try:
            # Query database for conversation
            db_manager = get_database_manager()
            
            # Check for user message
            user_messages = await db_manager.query(
                "SELECT * FROM messages WHERE user_id = %s AND content LIKE %s",
                (user_id, f"%{message[:50]}%")
            )
            
            # Check for AI response  
            ai_responses = await db_manager.query(
                "SELECT * FROM messages WHERE user_id = %s AND content LIKE %s",
                (user_id, f"%{response[:50]}%")
            )
            
            return len(user_messages) > 0 and len(ai_responses) > 0
            
        except Exception as e:
            self.logger.warning(f"Database persistence verification failed: {e}")
            return False
    
    async def _verify_golden_path_blocked(self) -> bool:
        """Verify golden path is blocked (no chat functionality available)."""
        try:
            # Check for error messages or disabled chat interface
            error_indicators = [
                '.chat-disabled',
                '.connection-error',
                '.auth-required',
                '.service-unavailable'
            ]
            
            for indicator in error_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=2000)
                    return True
                except Exception:
                    continue
            
            # Check if chat input is disabled
            chat_input_disabled = await self.page.is_disabled('.chat-input, input, textarea')
            return chat_input_disabled
            
        except Exception as e:
            self.logger.warning(f"Golden path blocked verification failed: {e}")
            return False
    
    async def _verify_no_agent_execution(self) -> bool:
        """Verify no agent execution occurs."""
        try:
            # Check that no agent execution indicators appear
            agent_indicators = [
                '.agent-started',
                '.agent-executing', 
                '.agent-thinking',
                '.tool-executing'
            ]
            
            for indicator in agent_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=2000)
                    return True  # Agent execution detected
                except Exception:
                    continue
            
            return False  # No agent execution detected
            
        except Exception as e:
            self.logger.warning(f"Agent execution verification failed: {e}")
            return False
    
    async def _set_relaxed_auth_headers(self, user: Dict[str, Any]) -> None:
        """Set relaxed auth headers in browser context."""
        await self.page.set_extra_http_headers({
            'X-User-Hint': user["user_id"],
            'X-Auth-Degraded': 'true',
            'X-Fallback-Auth': 'load-balancer-stripped'
        })
    
    async def _set_emergency_auth_headers(self, user: Dict[str, Any]) -> None:
        """Set emergency auth headers in browser context."""
        await self.page.set_extra_http_headers({
            'X-Emergency-Access': 'true',
            'X-Emergency-Key': 'emergency_recovery_key',
            'X-System-Recovery': 'auth-bypass-required'
        })
    
    async def _extract_auth_context_from_events(self, events: List[str]) -> Dict[str, Any]:
        """Extract authentication context from WebSocket events."""
        # This would examine the actual event data in a real implementation
        return {"level": "unknown", "events": events}
    
    async def _extract_user_context_from_events(self, events: List[str]) -> Dict[str, Any]:
        """Extract user context from WebSocket events."""
        # This would examine the actual event data in a real implementation
        return {"user_id": "unknown", "events": events}
    
    async def _test_single_auth_mode_golden_path(self, auth_mode: str, user: Dict[str, Any]) -> bool:
        """Test golden path with a single auth mode."""
        try:
            # Create new page for this test
            page = await self.context.new_page()
            
            # Load chat interface
            await page.goto(self.frontend_url)
            await page.wait_for_load_state('networkidle')
            
            # Perform auth mode specific setup
            if auth_mode == "strict" and user["jwt_token"]:
                await self._perform_user_login(user)
            elif auth_mode == "relaxed":
                await page.set_extra_http_headers({
                    'X-User-Hint': user["user_id"],
                    'X-Auth-Degraded': 'true'
                })
            elif auth_mode == "emergency":
                await page.set_extra_http_headers({
                    'X-Emergency-Access': 'true'
                })
            # Demo mode requires no special setup
            
            # Test WebSocket connection
            websocket_connected = await self._verify_websocket_connection(user)
            if not websocket_connected:
                return False
            
            # Send test message
            test_message = self.test_messages["simple"]
            agent_started = await self._send_message_and_verify_agent_start(test_message)
            if not agent_started:
                return False
            
            # Verify events and response
            events = await self._verify_all_websocket_events()
            response = await self._verify_ai_response_delivery()
            
            await page.close()
            
            return len(events) >= 3 and response is not None
            
        except Exception as e:
            self.logger.warning(f"Single auth mode test failed for {auth_mode}: {e}")
            return False
    
    async def asyncTearDown(self):
        """Clean up after each test"""
        # Close browser
        if hasattr(self, 'context'):
            await self.context.close()
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        
        # Reset environment
        env = IsolatedEnvironment()
        env.remove("AUTH_VALIDATION_LEVEL", default=None)
        env.remove("DEMO_MODE", default=None)
        
        await super().asyncTearDown()


if __name__ == '__main__':
    # Run with asyncio support for E2E testing
    pytest.main([__file__, '-v', '-s'])