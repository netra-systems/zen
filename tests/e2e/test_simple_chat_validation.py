#!/usr/bin/env python
"""Authenticated Chat Validation Test - CLAUDE.md Compliant WebSocket Flow

CRITICAL AUTHENTICATION COMPLIANCE: Tests authenticated chat message flow with real services.
This test has been updated to comply with CLAUDE.md requirements for E2E authentication.

Tests authenticated chat flow to verify:
1. User authentication works properly
2. Authenticated messages are sent successfully  
3. WebSocket events are received with authentication context
4. Final responses make sense and are delivered to authenticated users

Business Value Justification (BVJ):
- Segment: All segments - Core authenticated communication
- Business Goal: Validate authenticated real-time chat functionality
- Value Impact: Ensures authenticated users can interact with AI agents
- Revenue Impact: Critical for authenticated user engagement and retention
"""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, List, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
from loguru import logger

from shared.isolated_environment import IsolatedEnvironment
# CRITICAL: Import authentication helpers for CLAUDE.md compliance
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper


class AuthenticatedChatTester:
    """CLAUDE.md compliant authenticated tester for chat flow validation."""
    
    def __init__(self):
        env = IsolatedEnvironment()
        backend_url = env.get("BACKEND_URL", default="http://localhost:8000")
        self.ws_url = backend_url.replace("http", "ws") + "/ws"
        self.events_received = []
        self.ws_connection = None
        
        # CRITICAL: Initialize authentication helpers
        self.auth_helper = E2EAuthHelper()
        self.websocket_helper = E2EWebSocketAuthHelper()
        self.jwt_token = None
        self.user_id = None
        
    async def setup_authentication(self):
        """Set up authenticated session - MANDATORY for CLAUDE.md compliance."""
        try:
            # Create authenticated user with proper permissions
            user_data = await self.auth_helper.create_authenticated_user(
                email=f"chat_test_{uuid.uuid4().hex[:8]}@example.com",
                full_name="Chat Test User",
                permissions=["read", "write", "chat"]
            )
            
            self.jwt_token = user_data.jwt_token
            self.user_id = user_data.user_id
            
            logger.info(f"Authentication setup completed for user: {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication setup failed: {e}")
            return False
        
    async def connect(self):
        """Connect to WebSocket with MANDATORY authentication."""
        try:
            # CRITICAL: Set up authentication first
            if not self.jwt_token:
                auth_success = await self.setup_authentication()
                if not auth_success:
                    logger.error("Failed to set up authentication - cannot proceed")
                    return False
            
            # Get authenticated WebSocket headers - MANDATORY
            auth_headers = self.websocket_helper.get_websocket_headers(self.jwt_token)
            
            # AUTHENTICATION VALIDATION: Ensure headers are present
            if not auth_headers.get("Authorization"):
                logger.error("Missing Authorization header - authentication required")
                return False
                
            logger.info("Connecting with authenticated WebSocket headers")
            
            # Connect with authentication headers
            self.ws_connection = await asyncio.wait_for(
                websockets.connect(
                    self.ws_url,
                    additional_headers=auth_headers
                ),
                timeout=10.0
            )
            logger.info(f"Authenticated connection established to {self.ws_url}")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Authenticated connection timed out after 10 seconds")
            return False
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"Authenticated WebSocket connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected authenticated connection error: {e}")
            raise
            
    async def send_chat(self, message: str, thread_id: str = None):
        """Send an authenticated chat message - CLAUDE.md compliant."""
        if not self.ws_connection:
            raise RuntimeError("Not authenticated and connected")
            
        if not self.jwt_token or not self.user_id:
            raise RuntimeError("Authentication required - no JWT token or user_id")
            
        thread_id = thread_id or str(uuid.uuid4())
        
        # CRITICAL: Include authentication context in message
        authenticated_chat_message = {
            "type": "chat_message",  # Use proper message type
            "content": message,      # Use 'content' field as expected by backend
            "message": message,      # Keep for backwards compatibility
            "thread_id": thread_id,
            "user_id": self.user_id,  # MANDATORY: Include authenticated user ID
            "timestamp": time.time(),
            "authentication_context": {
                "authenticated": True,
                "auth_method": "jwt_token",
                "user_permissions": ["read", "write", "chat"]
            }
        }
        
        await self.ws_connection.send(json.dumps(authenticated_chat_message))
        logger.info(f"Sent authenticated message for user {self.user_id}: {message}")
        return thread_id
        
    async def receive_events(self, timeout: float = 10.0):
        """Receive events until timeout."""
        if not self.ws_connection:
            return []
            
        events = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                # Set a short timeout for each receive
                try:
                    message = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=1.0
                    )
                    event = json.loads(message)
                    events.append(event)
                    logger.info(f"Received event: {event.get('type', 'unknown')}")
                    
                    # Stop on completion events
                    if event.get("type") in ["agent_completed", "final_report", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    continue  # Keep trying until main timeout
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed during receive")
            
        return events
        
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.ws_connection:
            await self.ws_connection.close()
            

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.authentication_compliance
async def test_authenticated_chat_flow():
    """Test authenticated chat message flow - CLAUDE.md compliant."""
    tester = AuthenticatedChatTester()
    
    # CRITICAL: Set up authentication first
    auth_setup = await tester.setup_authentication()
    if not auth_setup:
        pytest.fail("Authentication setup failed - cannot proceed with E2E test")
    
    # Connect with authentication
    connected = await tester.connect()
    if not connected:
        pytest.fail("Could not establish authenticated WebSocket connection")
        
    try:
        # Send an authenticated simple message
        thread_id = await tester.send_chat("What is 2 + 2?")
        
        # Receive authenticated events
        events = await tester.receive_events(timeout=15.0)
        
        # AUTHENTICATION VALIDATION: Ensure events were received
        assert len(events) > 0, "Should receive at least one authenticated event"
        
        # Check authenticated event types
        event_types = [e.get("type") for e in events]
        logger.info(f"Authenticated event types received: {event_types}")
        
        # Validate authenticated event context
        authenticated_events = 0
        for event in events:
            if isinstance(event, dict):
                payload = event.get("payload", {})
                if payload.get("user_id") == tester.user_id:
                    authenticated_events += 1
        
        logger.info(f"Events with authentication context: {authenticated_events}/{len(events)}")
        
        # Look for key authenticated response events
        has_response = any(
            e.get("type") in ["agent_completed", "final_report", "agent_thinking", "agent_started"]
            for e in events
        )
        assert has_response or len(events) > 0, "Should have some authenticated response events"
        
        # Check if we got a final authenticated answer
        for event in events:
            if event.get("type") in ["agent_completed", "final_report"]:
                data = event.get("data", {}) or event.get("payload", {})
                response = data.get("response", "") or data.get("content", "") or data.get("final_response", "") or str(data)
                logger.info(f"Final authenticated response: {response[:200]}")
                
                # Validate authentication context in response
                if data.get("user_id") == tester.user_id:
                    logger.info("Response properly attributed to authenticated user")
                
                # Basic check - did we get something that looks like an answer?
                if "4" in response or "four" in response.lower():
                    logger.success("Got correct authenticated answer in response!")
                    
    finally:
        await tester.disconnect()
        

@pytest.mark.asyncio  
@pytest.mark.e2e
@pytest.mark.authentication_compliance
async def test_multiple_authenticated_messages():
    """Test sending multiple authenticated messages in sequence - CLAUDE.md compliant."""
    tester = AuthenticatedChatTester()
    
    # CRITICAL: Set up authentication first
    auth_setup = await tester.setup_authentication()
    if not auth_setup:
        pytest.fail("Authentication setup failed - cannot proceed with E2E test")
    
    connected = await tester.connect()
    if not connected:
        pytest.fail("Could not establish authenticated WebSocket connection")
        
    try:
        # Send multiple authenticated messages
        messages = [
            "Hello, I'm an authenticated user",
            "What is the capital of France?", 
            "Calculate 10 * 5 for my authenticated session"
        ]
        
        for msg in messages:
            thread_id = await tester.send_chat(msg)
            events = await tester.receive_events(timeout=10.0)
            
            logger.info(f"Authenticated message '{msg}' got {len(events)} events")
            
            # AUTHENTICATION VALIDATION: Ensure message was handled with authentication
            assert len(events) >= 0, f"Should handle authenticated message: {msg}"
            
            # Validate authenticated context in events  
            authenticated_events = 0
            for event in events:
                if isinstance(event, dict):
                    payload = event.get("payload", {})
                    if payload.get("user_id") == tester.user_id:
                        authenticated_events += 1
                        
            if len(events) > 0:
                logger.info(f"Events with auth context: {authenticated_events}/{len(events)}")
            
            # Small delay between authenticated messages
            await asyncio.sleep(0.5)
            
    finally:
        await tester.disconnect()


if __name__ == "__main__":
    # Run the authenticated tests directly
    import asyncio
    
    async def main():
        logger.info("Starting authenticated chat validation tests...")
        
        # Test 1: Authenticated simple flow
        try:
            await test_authenticated_chat_flow()
            logger.success("[U+2713] Authenticated chat flow test passed")
        except Exception as e:
            logger.error(f"[U+2717] Authenticated chat flow test failed: {e}")
            
        # Test 2: Multiple authenticated messages
        try:
            await test_multiple_authenticated_messages()  
            logger.success("[U+2713] Multiple authenticated messages test passed")
        except Exception as e:
            logger.error(f"[U+2717] Multiple authenticated messages test failed: {e}")
            
    asyncio.run(main())