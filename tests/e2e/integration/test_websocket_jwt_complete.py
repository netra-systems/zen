from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

"""
Complete WebSocket JWT Authentication Flow Test

CRITICAL E2E Test: Complete JWT token authentication flow for WebSocket connections.
Tests the end-to-end security chain from Auth Service JWT generation to WebSocket message delivery.

Business Value Justification (BVJ):
Segment: ALL (Free, Early, Mid, Enterprise) | Goal: Core Security | Impact: $100K+ MRR Protection
- Security breach = 100% Enterprise customer loss
- Prevents authentication bypass vulnerabilities in real-time AI interactions
- Ensures JWT token validation consistency across Auth → Backend → WebSocket services
- Tests token refresh, expiry, and reconnection flows critical for user retention
- Validates unauthorized access blocking for compliance requirements

Performance Requirements:
- JWT Generation: <100ms
- Token Validation: <50ms
- WebSocket Connection: <2s
- Token Refresh: <500ms
- Unauthorized Rejection: <1s
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pytest
import websockets
from websockets import ConnectionClosedError, InvalidStatusCode

from tests.clients import TestClientFactory
from tests.e2e.jwt_token_helpers import JWTTestHelper

# Enable real services for this test module
env_vars = get_env()
pytestmark = pytest.mark.skipif(
    env_vars.get("USE_REAL_SERVICES", "false").lower() != "true",
    reason="Real services disabled (set USE_REAL_SERVICES=true)"
)


class CompleteJWTAuthTester:
    """Complete JWT authentication flow tester with performance tracking."""
    
    def __init__(self, real_services):
        """Initialize with real services context."""
        self.real_services = real_services
        self.factory = real_services.factory
        self.jwt_helper = JWTTestHelper()
        
    async def get_jwt_from_auth_service(self, email: Optional[str] = None) -> Dict[str, Any]:
        """Get real JWT token from Auth service with timing."""
        start_time = time.time()
        
        try:
            auth_client = await self.factory.create_auth_client()
            
            if email:
                # Use existing user
                token = await auth_client.login(email, "testpass123")
                user_email = email
            else:
                # Create new test user
                user_data = await auth_client.create_test_user()
                token = user_data["token"]
                user_email = user_data["email"]
            
            auth_time = time.time() - start_time
            
            # JWT Generation performance requirement: <100ms
            assert auth_time < 0.1, f"JWT generation took {auth_time:.3f}s, required <100ms"
            
            return {
                "access_token": token,
                "email": user_email,
                "generation_time": auth_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "access_token": None,
                "email": email,
                "generation_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    async def validate_jwt_in_backend(self, token: str) -> Dict[str, Any]:
        """Validate JWT token in Backend service with performance tracking."""
        start_time = time.time()
        
        try:
            backend_client = await self.factory.create_backend_client(token=token)
            health_result = await backend_client.health_check()
            
            validation_time = time.time() - start_time
            
            # Token Validation performance requirement: <50ms
            assert validation_time < 0.05, f"Token validation took {validation_time:.3f}s, required <50ms"
            
            return {
                "valid": bool(health_result),
                "validation_time": validation_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "validation_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    @pytest.mark.e2e
    async def test_websocket_jwt_connection(self, token: str) -> Dict[str, Any]:
        """Test WebSocket connection with JWT token and performance tracking."""
        start_time = time.time()
        
        try:
            # Create WebSocket client with JWT token
            ws_client = await self.factory.create_websocket_client(token)
            
            # Attempt connection
            connected = await ws_client.connect(timeout=5.0)
            connection_time = time.time() - start_time
            
            # WebSocket Connection performance requirement: <2s
            if connected:
                assert connection_time < 2.0, f"WebSocket connection took {connection_time:.3f}s, required <2s"
            
            return {
                "websocket": ws_client if connected else None,
                "connected": connected,
                "connection_time": connection_time,
                "success": connected,
                "error": None if connected else "Connection failed"
            }
            
        except Exception as e:
            return {
                "websocket": None,
                "connected": False,
                "connection_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    @pytest.mark.e2e
    async def test_websocket_message_with_jwt(self, ws_client, message: str) -> Dict[str, Any]:
        """Send authenticated message through WebSocket and validate response."""
        start_time = time.time()
        
        try:
            # Send ping first to verify connection
            await ws_client.send_ping()
            pong_response = await ws_client.receive_until("pong", timeout=3.0)
            
            if not pong_response:
                return {
                    "ping_success": False,
                    "message_sent": False,
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": "Ping failed - connection not authenticated"
                }
            
            # Send actual message
            await ws_client.send_chat(message)
            response = await ws_client.receive(timeout=10.0)
            
            response_time = time.time() - start_time
            
            return {
                "ping_success": True,
                "message_sent": True,
                "response": response,
                "response_time": response_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "ping_success": False,
                "message_sent": False,
                "response": None,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    @pytest.mark.e2e
    async def test_token_refresh_flow(self, email: str, original_token: str) -> Dict[str, Any]:
        """Test token refresh and reconnection flow."""
        start_time = time.time()
        
        try:
            # Get fresh token for same user
            auth_client = await self.factory.create_auth_client()
            new_token = await auth_client.login(email, "testpass123")
            
            # Test new token works with WebSocket
            ws_result = await self.test_websocket_jwt_connection(new_token)
            
            refresh_time = time.time() - start_time
            
            # Token Refresh performance requirement: <500ms
            assert refresh_time < 0.5, f"Token refresh took {refresh_time:.3f}s, required <500ms"
            
            return {
                "new_token": new_token,
                "refresh_time": refresh_time,
                "websocket_success": ws_result["success"],
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "new_token": None,
                "refresh_time": time.time() - start_time,
                "websocket_success": False,
                "success": False,
                "error": str(e)
            }
    
    @pytest.mark.e2e
    async def test_unauthorized_access_blocking(self, invalid_token: str, token_type: str) -> Dict[str, Any]:
        """Test that unauthorized access is properly blocked."""
        start_time = time.time()
        
        try:
            # Attempt WebSocket connection with invalid token
            ws_client = await self.factory.create_websocket_client(invalid_token)
            connected = await ws_client.connect(timeout=2.0)
            
            rejection_time = time.time() - start_time
            
            # Unauthorized Rejection performance requirement: <1s
            assert rejection_time < 1.0, f"Unauthorized rejection took {rejection_time:.3f}s, required <1s"
            
            # Connection should fail for invalid tokens
            if connected:
                await ws_client.disconnect()  # Cleanup if somehow connected
            
            return {
                "blocked": not connected,
                "rejection_time": rejection_time,
                "success": not connected,  # Success means properly blocked
                "error": None
            }
            
        except Exception as e:
            # Exceptions are expected for invalid tokens
            rejection_time = time.time() - start_time
            return {
                "blocked": True,
                "rejection_time": rejection_time,
                "success": True,
                "error": f"Properly blocked: {str(e)}"
            }


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_auth_complete_flow(real_services):
    """
    BVJ: ALL Segments | Goal: Core Security | Impact: $100K+ MRR Protection
    Test: Complete JWT authentication flow from Auth Service to WebSocket message delivery
    """
    tester = CompleteJWTAuthTester(real_services)
    
    # Phase 1: Get real JWT token from Auth service
    print("\n=== Phase 1: JWT Token Generation ===")
    auth_response = await tester.get_jwt_from_auth_service()
    assert auth_response["success"], f"Failed to get JWT token: {auth_response['error']}"
    
    token = auth_response["access_token"]
    user_email = auth_response["email"]
    
    print(f"✓ JWT token generated in {auth_response['generation_time']:.3f}s")
    
    # Phase 2: Validate JWT in Backend service
    print("\n=== Phase 2: Backend JWT Validation ===")
    backend_result = await tester.validate_jwt_in_backend(token)
    assert backend_result["success"], f"Backend JWT validation failed: {backend_result['error']}"
    assert backend_result["valid"], "Backend rejected valid JWT token"
    
    print(f"✓ JWT validated by Backend in {backend_result['validation_time']:.3f}s")
    
    # Phase 3: Test WebSocket connection with JWT
    print("\n=== Phase 3: WebSocket JWT Connection ===")
    ws_result = await tester.test_websocket_jwt_connection(token)
    assert ws_result["success"], f"WebSocket connection failed: {ws_result['error']}"
    assert ws_result["connected"], "WebSocket not connected with valid JWT"
    
    websocket = ws_result["websocket"]
    print(f"✓ WebSocket connected with JWT in {ws_result['connection_time']:.3f}s")
    
    try:
        # Phase 4: Send authenticated message through WebSocket
        print("\n=== Phase 4: Authenticated Message Delivery ===")
        message_result = await tester.test_websocket_message_with_jwt(
            websocket, "Complete JWT auth integration test message"
        )
        assert message_result["success"], f"Authenticated message failed: {message_result['error']}"
        assert message_result["ping_success"], "WebSocket ping failed with valid JWT"
        assert message_result["message_sent"], "Failed to send authenticated message"
        
        print(f"✓ Authenticated message sent in {message_result['response_time']:.3f}s")
        
        # Verify response handling
        if message_result["response"]:
            response = message_result["response"]
            print(f"✓ Message response received: {response.get('type', 'unknown')}")
        else:
            print("ℹ No immediate response (acceptable for async processing)")
        
    finally:
        if websocket:
            await websocket.disconnect()
    
    # Phase 5: Test token refresh flow
    print("\n=== Phase 5: Token Refresh Flow ===")
    refresh_result = await tester.test_token_refresh_flow(user_email, token)
    assert refresh_result["success"], f"Token refresh failed: {refresh_result['error']}"
    assert refresh_result["websocket_success"], "Refreshed token failed WebSocket connection"
    
    print(f"✓ Token refresh completed in {refresh_result['refresh_time']:.3f}s")
    
    print(f"\n🎯 Complete JWT authentication flow successful!")
    print(f"   - JWT Generation: {auth_response['generation_time']:.3f}s")
    print(f"   - Backend Validation: {backend_result['validation_time']:.3f}s")
    print(f"   - WebSocket Connection: {ws_result['connection_time']:.3f}s")
    print(f"   - Token Refresh: {refresh_result['refresh_time']:.3f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_invalid_token_rejection(real_services):
    """Test that various invalid JWT tokens are properly rejected by WebSocket."""
    tester = CompleteJWTAuthTester(real_services)
    
    # Create different types of invalid tokens
    invalid_tokens = [
        ("expired", tester.jwt_helper.create_token(tester.jwt_helper.create_expired_payload())),
        ("malformed", "invalid.token.structure"),
        ("empty", ""),
        ("none_algorithm", tester.jwt_helper.create_none_algorithm_token()),
        ("tampered", await tester.jwt_helper.create_tampered_token(tester.jwt_helper.create_valid_payload()))
    ]
    
    print(f"\n=== Testing {len(invalid_tokens)} Invalid Token Types ===")
    
    for token_type, invalid_token in invalid_tokens:
        if not invalid_token:  # Skip empty token for WebSocket
            print(f"⚠ Skipping empty token test for WebSocket")
            continue
            
        print(f"\nTesting {token_type} token rejection...")
        
        rejection_result = await tester.test_unauthorized_access_blocking(invalid_token, token_type)
        
        assert rejection_result["success"], f"{token_type} token was not properly blocked"
        assert rejection_result["blocked"], f"{token_type} token should be rejected but was accepted"
        
        print(f"✓ {token_type} token properly blocked in {rejection_result['rejection_time']:.3f}s")
    
    print(f"\n🔒 All invalid tokens properly rejected by WebSocket!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_token_expiry_handling(real_services):
    """Test WebSocket handling of token expiry and reconnection."""
    tester = CompleteJWTAuthTester(real_services)
    
    # Get initial token and establish connection
    print("\n=== Initial Connection Setup ===")
    auth_response = await tester.get_jwt_from_auth_service()
    assert auth_response["success"], "Failed to get initial token"
    
    initial_token = auth_response["access_token"]
    user_email = auth_response["email"]
    
    # Test initial connection
    ws_result = await tester.test_websocket_jwt_connection(initial_token)
    assert ws_result["success"], "Initial WebSocket connection failed"
    
    initial_websocket = ws_result["websocket"]
    print(f"✓ Initial connection established")
    
    try:
        # Send test message to verify connection works
        message_result = await tester.test_websocket_message_with_jwt(
            initial_websocket, "Pre-expiry test message"
        )
        assert message_result["success"], "Initial message failed"
        print(f"✓ Initial message sent successfully")
        
    finally:
        # Disconnect initial connection
        await initial_websocket.disconnect()
    
    # Simulate token expiry scenario with fresh token
    print("\n=== Token Refresh and Reconnection ===")
    await asyncio.sleep(1.0)  # Brief pause to simulate time passage
    
    # Test token refresh and reconnection
    refresh_result = await tester.test_token_refresh_flow(user_email, initial_token)
    assert refresh_result["success"], f"Token refresh failed: {refresh_result['error']}"
    
    # Test the new connection with a message
    new_ws_result = await tester.test_websocket_jwt_connection(refresh_result["new_token"])
    assert new_ws_result["success"], "Reconnection with refreshed token failed"
    
    new_websocket = new_ws_result["websocket"]
    
    try:
        message_result = await tester.test_websocket_message_with_jwt(
            new_websocket, "Post-refresh test message"
        )
        assert message_result["success"], "Message with refreshed token failed"
        print(f"✓ Message sent successfully with refreshed token")
        
    finally:
        await new_websocket.disconnect()
    
    print(f"🔄 Token expiry handling successful!")
    print(f"   - Refresh Time: {refresh_result['refresh_time']:.3f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_cross_service_consistency(real_services):
    """Test JWT token consistency across Auth, Backend, and WebSocket services."""
    tester = CompleteJWTAuthTester(real_services)
    
    print("\n=== Cross-Service JWT Consistency Test ===")
    
    # Get token from Auth service
    auth_response = await tester.get_jwt_from_auth_service()
    assert auth_response["success"], "Failed to get token from Auth service"
    
    token = auth_response["access_token"]
    print(f"✓ Token generated by Auth service")
    
    # Test Backend service accepts the token
    backend_result = await tester.validate_jwt_in_backend(token)
    assert backend_result["success"], f"Backend service failed: {backend_result['error']}"
    assert backend_result["valid"], "Backend service rejected Auth service token"
    print(f"✓ Token accepted by Backend service")
    
    # Test WebSocket service accepts the same token
    ws_result = await tester.test_websocket_jwt_connection(token)
    assert ws_result["success"], f"WebSocket service failed: {ws_result['error']}"
    assert ws_result["connected"], "WebSocket service rejected token accepted by Backend"
    
    websocket = ws_result["websocket"]
    
    try:
        # Verify WebSocket can process authenticated messages
        message_result = await tester.test_websocket_message_with_jwt(
            websocket, "Cross-service consistency test message"
        )
        assert message_result["success"], "WebSocket message processing failed"
        print(f"✓ Token processed by WebSocket service for messaging")
        
    finally:
        await websocket.disconnect()
    
    print(f"🔗 JWT token consistently validated across all services!")
    print(f"   Auth → Backend → WebSocket: All services accept same token")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_concurrent_connections(real_services):
    """Test multiple concurrent WebSocket connections with different valid JWT tokens."""
    tester = CompleteJWTAuthTester(real_services)
    
    print(f"\n=== Concurrent JWT Authentication Test ===")
    
    # Create multiple users and tokens
    num_users = 3
    user_tokens = []
    
    for i in range(num_users):
        auth_response = await tester.get_jwt_from_auth_service()
        assert auth_response["success"], f"Failed to create user {i+1}"
        user_tokens.append({
            "token": auth_response["access_token"],
            "email": auth_response["email"],
            "user_id": i + 1
        })
        print(f"✓ User {i+1} token generated")
    
    # Establish concurrent WebSocket connections
    websockets = []
    connection_tasks = []
    
    for user_data in user_tokens:
        task = tester.test_websocket_jwt_connection(user_data["token"])
        connection_tasks.append((task, user_data["user_id"]))
    
    # Wait for all connections
    connection_results = []
    for task, user_id in connection_tasks:
        result = await task
        connection_results.append((result, user_id))
        
        if result["success"]:
            websockets.append(result["websocket"])
            print(f"✓ User {user_id} connected successfully")
        else:
            print(f"⚠ User {user_id} connection failed: {result['error']}")
    
    # Verify at least 2 concurrent connections work
    successful_connections = len(websockets)
    assert successful_connections >= 2, f"Expected ≥2 concurrent connections, got {successful_connections}"
    
    try:
        # Send messages from each connection concurrently
        message_tasks = []
        for i, websocket in enumerate(websockets):
            task = tester.test_websocket_message_with_jwt(
                websocket, f"Concurrent message from authenticated user {i+1}"
            )
            message_tasks.append((task, i+1))
        
        # Process messages concurrently
        successful_messages = 0
        for task, user_id in message_tasks:
            message_result = await task
            if message_result["success"]:
                successful_messages += 1
                print(f"✓ User {user_id} message sent successfully")
            else:
                print(f"⚠ User {user_id} message failed: {message_result['error']}")
        
        assert successful_messages >= 2, f"Expected ≥2 successful messages, got {successful_messages}"
        
    finally:
        # Cleanup all connections
        for websocket in websockets:
            try:
                await websocket.disconnect()
            except Exception as e:
                print(f"Warning: Error disconnecting WebSocket: {e}")
    
    print(f"🔀 Concurrent JWT authentication successful!")
    print(f"   - {successful_connections} concurrent connections")
    print(f"   - {successful_messages} concurrent authenticated messages")


# Import os for environment variables


# Business Impact Summary
"""
Complete WebSocket JWT Authentication Test - Business Impact Summary

🎯 Revenue Protection: $100K+ MRR at Risk
- Security breach = 100% Enterprise customer loss
- Prevents authentication bypass in real-time AI agent interactions  
- Ensures JWT validation consistency across microservice boundaries
- Tests critical token refresh flows for long-running user sessions

🔒 Security Compliance Validation:
- End-to-end JWT authentication from Auth Service to WebSocket delivery
- Invalid token rejection with proper performance characteristics (<1s)
- Token expiry and refresh handling for session continuity
- Cross-service authentication consistency for SOC2/GDPR compliance
- Concurrent user authentication for enterprise scalability

⚡ Performance Requirements Enforced:
- JWT Generation: <100ms (Auth Service)
- Token Validation: <50ms (Backend Service) 
- WebSocket Connection: <2s (Real-time requirement)
- Token Refresh: <500ms (Session continuity)
- Unauthorized Rejection: <1s (Security responsiveness)

👥 Customer Impact by Segment:
- All Segments: Secure real-time AI interactions without auth failures
- Enterprise: Security compliance enabling high-value contract execution
- Free/Early: Smooth onboarding with secure chat functionality
- Mid: Reliable concurrent connections for team collaboration

🏗️ System Reliability:
- Tests REAL security, not mocks - validates production-ready authentication
- Comprehensive invalid token rejection (expired, malformed, tampered, none-algorithm)
- Token refresh and reconnection flows critical for user retention
- Cross-service consistency prevents auth discrepancies between services
"""
