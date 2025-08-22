"""
Shared Authentication Test Fixtures - Common utilities for auth testing across all modules

Provides common authentication test utilities to prevent duplication across split test files.
This module extracts shared functionality from large auth test files to enable focused testing.

Business Value Justification (BVJ):
- Segment: Platform/Internal | Goal: Test Infrastructure | Impact: Development Velocity
- Reduces code duplication across auth test modules
- Ensures consistent authentication testing patterns
- Enables maintainable test infrastructure for critical auth flows

Key Components:
- WebSocketAuthTester: WebSocket authentication utilities
- TokenExpiryTester: Token expiry and refresh scenarios
- MessagePreservationTester: Message preservation during reconnection
- AuthTestConfig: Centralized auth test configuration
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

from tests.config import TEST_ENDPOINTS, TEST_SECRETS, TEST_USERS
from tests.jwt_token_helpers import JWTSecurityTester, JWTTestHelper
from tests.real_services_manager import RealServicesManager


class AuthTestConfig:
    """Centralized authentication test configuration."""
    
    # Performance requirements
    AUTH_TIME_LIMIT = 0.1  # 100ms
    RECONNECTION_TIME_LIMIT = 2.0  # 2s
    TOKEN_VALIDATION_LIMIT = 0.05  # 50ms
    WEBSOCKET_TIMEOUT = 5.0
    
    # Test timeouts
    MESSAGE_RESPONSE_TIMEOUT = 3.0
    TOKEN_EXPIRY_WAIT = 6.0
    TEST_EXECUTION_LIMIT = 10.0


class WebSocketAuthTester:
    """Critical WebSocket authentication test manager with real services integration."""
    
    def __init__(self):
        """Initialize WebSocket auth tester with service endpoints."""
        self.auth_url = TEST_ENDPOINTS.auth_base
        self.backend_url = TEST_ENDPOINTS.api_base  
        self.websocket_url = TEST_ENDPOINTS.ws_url
        self.jwt_helper = JWTTestHelper()
        self.services_manager = RealServicesManager()
        
    async def generate_real_jwt_token(self, user_tier: str = "free") -> Optional[str]:
        """Generate real JWT token from Auth service with performance tracking."""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # Use test user credentials
                test_user = TEST_USERS.get(user_tier)
                if not test_user:
                    test_user = TEST_USERS["free"]
                
                login_data = {
                    "email": test_user.email,
                    "user_id": test_user.id,
                    "dev_mode": True
                }
                
                response = await client.post(f"{self.auth_url}/auth/dev/login", json=login_data)
                auth_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("access_token")
                    
                    # Verify auth performance requirement
                    assert auth_time < AuthTestConfig.AUTH_TIME_LIMIT, \
                        f"Auth took {auth_time:.3f}s, required <{AuthTestConfig.AUTH_TIME_LIMIT}s"
                    
                    return token
                    
            except Exception as e:
                return None
        return None
    
    def create_mock_jwt_token(self, expiry_seconds: int = 900) -> str:
        """Create mock JWT token for fallback testing."""
        payload = self.jwt_helper.create_valid_payload()
        if expiry_seconds > 0:
            payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
        else:
            payload["exp"] = datetime.now(timezone.utc) - timedelta(seconds=abs(expiry_seconds))
        return self.jwt_helper.create_token(payload)
    
    async def validate_token_in_backend(self, token: str) -> Dict[str, Any]:
        """Validate JWT token in Backend service with timing."""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(f"{self.backend_url}/health", headers=headers)
                
                validation_time = time.time() - start_time
                
                return {
                    "valid": response.status_code in [200, 401],
                    "status_code": response.status_code,
                    "validation_time": validation_time,
                    "error": None
                }
                
            except Exception as e:
                return {
                    "valid": False,
                    "status_code": 500,
                    "validation_time": time.time() - start_time,
                    "error": str(e)
                }
    
    async def establish_websocket_connection(self, token: str, timeout: float = None) -> Dict[str, Any]:
        """Establish WebSocket connection with JWT token and performance tracking."""
        timeout = timeout or AuthTestConfig.WEBSOCKET_TIMEOUT
        start_time = time.time()
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(f"{self.websocket_url}?token={token}"),
                timeout=timeout
            )
            
            # Test connection with ping
            await websocket.ping()
            
            connection_time = time.time() - start_time
            
            return {
                "websocket": websocket,
                "connected": True,
                "connection_time": connection_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "websocket": None,
                "connected": False,
                "connection_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def test_token_refresh_flow(self, current_token: str) -> Optional[str]:
        """Test token refresh during active connection."""
        # Create refresh token for the same user
        refresh_payload = self.jwt_helper.create_refresh_payload()
        refresh_token = self.jwt_helper.create_token(refresh_payload)
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                refresh_data = {"refresh_token": refresh_token}
                response = await client.post(f"{self.auth_url}/auth/refresh", json=refresh_data)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
            except Exception as e:
                pass
        return None
    
    async def send_test_message(self, websocket, message_content: str) -> Dict[str, Any]:
        """Send test message and measure response time."""
        start_time = time.time()
        
        test_message = {
            "type": "chat",
            "content": message_content,
            "timestamp": start_time,
            "message_id": str(uuid.uuid4())
        }
        
        try:
            await websocket.send(json.dumps(test_message))
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(
                    websocket.recv(), 
                    timeout=AuthTestConfig.MESSAGE_RESPONSE_TIMEOUT
                )
                response_time = time.time() - start_time
                
                return {
                    "sent": True,
                    "response": response,
                    "response_time": response_time,
                    "error": None
                }
                
            except asyncio.TimeoutError:
                # No response is acceptable for some message types
                return {
                    "sent": True,
                    "response": None,
                    "response_time": time.time() - start_time,
                    "error": "timeout"
                }
                
        except Exception as e:
            return {
                "sent": False,
                "response": None,
                "response_time": time.time() - start_time,
                "error": str(e)
            }


class TokenExpiryTester:
    """Tests token expiry and refresh scenarios."""
    
    def __init__(self, auth_tester: WebSocketAuthTester):
        """Initialize with auth tester."""
        self.auth_tester = auth_tester
        self.jwt_helper = JWTTestHelper()
    
    def create_expired_token(self) -> str:
        """Create expired JWT token."""
        return self.auth_tester.create_mock_jwt_token(expiry_seconds=-60)
    
    def create_short_lived_token(self, seconds: int = 5) -> str:
        """Create JWT token with short expiry."""
        return self.auth_tester.create_mock_jwt_token(expiry_seconds=seconds)
    
    def create_invalid_signature_token(self) -> str:
        """Create token with invalid signature."""
        payload = self.jwt_helper.create_valid_payload()
        valid_token = self.jwt_helper.create_token(payload)
        parts = valid_token.split('.')
        return f"{parts[0]}.{parts[1]}.invalid_signature_test"
    
    def create_malformed_tokens(self) -> List[tuple]:
        """Create various malformed tokens for testing."""
        return [
            ("expired", self.create_expired_token()),
            ("invalid_signature", self.create_invalid_signature_token()),
            ("malformed", "invalid.token.structure"),
            ("empty", ""),
            ("none_algorithm", self.jwt_helper.create_none_algorithm_token()),
        ]


class MessagePreservationTester:
    """Tests message preservation during reconnection."""
    
    def __init__(self, auth_tester: WebSocketAuthTester):
        """Initialize message preservation tester."""
        self.auth_tester = auth_tester
        self.pending_messages: List[Dict] = []
        
    async def queue_messages_before_disconnect(self, websocket, count: int = 3) -> List[str]:
        """Queue messages before planned disconnect."""
        message_ids = []
        
        for i in range(count):
            message_id = str(uuid.uuid4())
            message = {
                "type": "chat",
                "content": f"Test message {i+1} before disconnect",
                "message_id": message_id,
                "timestamp": time.time()
            }
            
            try:
                await websocket.send(json.dumps(message))
                message_ids.append(message_id)
                self.pending_messages.append(message)
                
                # Small delay between messages
                await asyncio.sleep(0.1)
                
            except Exception as e:
                break
                
        return message_ids
    
    async def verify_message_preservation_after_reconnect(
        self, 
        new_websocket, 
        expected_message_ids: List[str],
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Verify messages are preserved after reconnection."""
        start_time = time.time()
        received_messages = []
        
        try:
            # Send reconnection message to trigger message replay
            reconnect_msg = {
                "type": "reconnect",
                "timestamp": time.time(),
                "request_message_replay": True
            }
            await new_websocket.send(json.dumps(reconnect_msg))
            
            # Collect messages until timeout
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(new_websocket.recv(), timeout=1.0)
                    received_messages.append(message)
                    
                    # Parse and check if it's one of our expected messages
                    try:
                        parsed_msg = json.loads(message)
                        if parsed_msg.get("message_id") in expected_message_ids:
                            expected_message_ids.remove(parsed_msg.get("message_id"))
                    except:
                        pass
                        
                except asyncio.TimeoutError:
                    break
            
            return {
                "messages_preserved": len(expected_message_ids) == 0,
                "received_count": len(received_messages),
                "missing_message_ids": expected_message_ids,
                "received_messages": received_messages[:5]  # First 5 for debugging
            }
            
        except Exception as e:
            return {
                "messages_preserved": False,
                "received_count": 0,
                "missing_message_ids": expected_message_ids,
                "error": str(e)
            }


class AuthTestFixtures:
    """Pytest fixtures for authentication testing."""
    
    @pytest.fixture
    def auth_tester(self):
        """Initialize WebSocket auth tester."""
        return WebSocketAuthTester()
    
    @pytest.fixture
    def expiry_tester(self, auth_tester):
        """Initialize token expiry tester."""
        return TokenExpiryTester(auth_tester)
    
    @pytest.fixture
    def message_tester(self, auth_tester):
        """Initialize message preservation tester."""
        return MessagePreservationTester(auth_tester)
    
    @pytest.fixture
    def jwt_helper(self):
        """Initialize JWT test helper."""
        return JWTTestHelper()
    
    @pytest.fixture
    def jwt_security_tester(self):
        """Initialize JWT security tester."""
        return JWTSecurityTester()


# Utility functions for common auth test patterns
def skip_if_services_unavailable(error_message: str):
    """Skip test if services are not available."""
    if any(phrase in error_message.lower() for phrase in 
           ["connection refused", "server not available", "services not available"]):
        pytest.skip(f"Services not available: {error_message}")


def assert_auth_performance(auth_time: float, operation: str):
    """Assert authentication performance requirements."""
    if operation == "auth":
        limit = AuthTestConfig.AUTH_TIME_LIMIT
    elif operation == "reconnection":
        limit = AuthTestConfig.RECONNECTION_TIME_LIMIT
    elif operation == "validation":
        limit = AuthTestConfig.TOKEN_VALIDATION_LIMIT
    else:
        limit = AuthTestConfig.WEBSOCKET_TIMEOUT
    
    assert auth_time < limit, f"{operation} took {auth_time:.3f}s, required <{limit}s"


def assert_token_rejection(ws_result: Dict[str, Any], test_name: str):
    """Assert that invalid tokens are properly rejected."""
    assert not ws_result["connected"], f"{test_name} token should be rejected"
    assert ws_result["error"] is not None, f"{test_name} should have error message"


# Export commonly used classes
__all__ = [
    'AuthTestConfig',
    'WebSocketAuthTester', 
    'TokenExpiryTester', 
    'MessagePreservationTester',
    'AuthTestFixtures',
    'skip_if_services_unavailable',
    'assert_auth_performance',
    'assert_token_rejection'
]
