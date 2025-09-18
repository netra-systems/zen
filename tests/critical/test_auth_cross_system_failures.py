from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

env = get_env()
"""
Authentication Cross-System Critical Failure Tests

These tests are designed to FAIL initially to expose real authentication integration
issues between auth_service and netra_backend. Each test targets a specific cross-system
vulnerability that commonly exists in distributed authentication architectures.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Security, Retention, Platform Stability
- Value Impact: Auth failures cause immediate user churn and security breaches
- Strategic Impact: Critical for platform reliability - auth issues destroy trust

Test Philosophy: Expose Real Failure Modes
- Tests MUST fail initially against current system
- Each test designed to expose specific integration gaps
- Focus on race conditions, state sync, and cross-service consistency
- Target real-world attack vectors and edge cases
"""

import asyncio
import os
import sys
import time
import uuid
import json
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
import httpx
import jwt as pyjwt
from fastapi.testclient import TestClient

    # Set test environment before any imports
env.set("TESTING", "true", "test")
env.set("ENVIRONMENT", "test", "test")
env.set("SKIP_STARTUP_CHECKS", "true", "test")
env.set("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only", "test")

    # Force enable auth service for cross-system testing
env.set("AUTH_SERVICE_ENABLED", "true", "test")
env.set("AUTH_FAST_TEST_MODE", "false", "test")
env.set("AUTH_SERVICE_URL", "http://127.0.0.1:8001", "test")

    # Add project root to path for imports
import sys
from pathlib import Path
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

    # Import modules but defer app creation until test execution
try:
    pass
import netra_backend.app.main
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.db.models_postgres import User
backend_available = True
except ImportError as e:
    print("")
backend_available = False

try:
    pass
import auth_service.main
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.services.auth_service import AuthService
auth_service_available = True
except ImportError as e:
    print("")
auth_app = None
auth_service_available = False


class TestAuthCrossSystemFailures:
    '''
    '''
    Authentication Cross-System Critical Failure Test Suite

    These tests are designed to FAIL to expose real integration issues
    between the auth service and main backend service.
    '''
    '''
    pass

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture
    async def test_concurrent_login_race_condition(self):
'''Test 1: Concurrent Login Race Condition

This test WILL FAIL because the auth service and main backend
don"t properly handle concurrent login attempts for the same user."
The race condition occurs when:
1. Multiple login requests hit different service instances
2. Token generation and session creation aren"t atomic"
3. Database updates can overwrite each other
'''
'''
pass
user_email = ""
password = "testpass123"

            # Create test user first
auth_client_test = TestClient(auth_app)
response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
            
assert response.status_code == 201

            # Simulate concurrent login attempts (this will expose the race condition)
async def login_attempt():
pass
async with httpx.AsyncClient() as client:
response = await client.post( )
"http://localhost:8001/auth/login,"
json={"email": user_email, "password: password}"
        
await asyncio.sleep(0)
return response

        # Launch 5 concurrent login attempts
tasks = [login_attempt() for _ in range(5)]
results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract successful tokens
successful_tokens = []
for result in results:
if hasattr(result, 'status_code') and result.status_code == 200:
    pass
token_data = result.json()
if 'access_token' in token_data:
    pass
successful_tokens.append(token_data['access_token'])

                    # THIS ASSERTION WILL FAIL - multiple valid tokens should not exist
                    # The system should ensure only one valid session per user
assert len(successful_tokens) <= 1, "( )"
""
f"This indicates the auth system doesnt properly handle concurrent logins.""
f"This indicates the auth system doesnt properly handle concurrent logins.""
                    

                    # Additional check: Verify all tokens are actually different
                    # (This will also fail, exposing the duplicate token issue)
unique_tokens = set(successful_tokens)
assert len(unique_tokens) == len(successful_tokens), "( )"
"DUPLICATE TOKENS DETECTED: Auth service issued identical tokens concurrently"
                    

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_token_invalidation_propagation(self):
        """Test 2: Token Invalidation Propagation

        This test WILL FAIL because token invalidation in auth_service
        doesn't properly propagate to netra_backend, causing stale tokens
        to remain valid in the backend service.
        """
        pass
user_email = ""
password = "testpass123"

                        # Create user and get token
auth_client_test = TestClient(auth_app)

                        # Register user
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
                        
assert register_response.status_code == 201

                        # Login to get token
login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                        
assert login_response.status_code == 200
token = login_response.json()["access_token]"

                        # Verify token works in backend - use authenticated demo endpoint
backend_client_test = TestClient(backend_app)
health_response = backend_client_test.get( )
"/api/demo/,"
headers={"Authorization": "}"
                        
assert health_response.status_code == 200

                        # Invalidate token in auth service (logout)
logout_response = auth_client_test.post( )
"/auth/logout,"
headers={"Authorization": "}"
                        
assert logout_response.status_code == 200

                        # Wait a moment for propagation (this won't help - the bug is systemic)'
await asyncio.sleep(0.1)

                        # THIS ASSERTION WILL FAIL - invalidated token should be rejected by backend
                        # But the backend service doesn't know the token was invalidated'
backend_health_response = backend_client_test.get( )
"/api/demo/,"
headers={"Authorization": "}"
                        
assert backend_health_response.status_code == 401, "( )"
f"TOKEN INVALIDATION FAILURE: Invalidated token still accepted by backend. "
""
f"This indicates token blacklisting isnt synchronized across services.""
f"This indicates token blacklisting isnt synchronized across services.""
                        

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_session_state_desync(self):
'''Test 3: Session State Desync

This test WILL FAIL because session state between auth_service
and netra_backend can become desynchronized, leading to
inconsistent user states across services.
'''
'''
pass
user_email = ""
password = "testpass123"

                            # Create user and establish session
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
                            
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                            
assert login_response.status_code == 200
token = login_response.json()["access_token]"

                            Get user info from both services
auth_user_response = auth_client_test.get( )
"/auth/me,"
headers={"Authorization": "}"
                            
assert auth_user_response.status_code == 200
auth_user_data = auth_user_response.json()

backend_client_test = TestClient(backend_app)
backend_user_response = backend_client_test.get( )
"/auth/me,"
headers={"Authorization": "}"
                            
assert backend_user_response.status_code == 200
backend_user_data = backend_user_response.json()

                            # Modify user state in auth service (e.g., update profile)
update_response = auth_client_test.put( )
"/auth/profile,"
headers={"Authorization": "},"
json={"display_name": "Updated Name}"
                            
assert update_response.status_code == 200

                            # Wait for sync (this won't work - there's no sync mechanism)
await asyncio.sleep(0.1)

                            Get updated user info from both services
auth_updated_response = auth_client_test.get( )
"/auth/me,"
headers={"Authorization": "}"
                            
backend_updated_response = backend_client_test.get( )
"/auth/me,"
headers={"Authorization": "}"
                            

auth_updated_data = auth_updated_response.json()
backend_updated_data = backend_updated_response.json()

                            # THIS ASSERTION WILL FAIL - user data should be consistent across services
assert auth_updated_data == backend_updated_data, "( )"
f"SESSION STATE DESYNC: User data inconsistent across services. "
""
f"This indicates session state is not synchronized between services."
                            

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_jwt_secret_rotation_during_request(self):
'''Test 4: JWT Secret Rotation During Request

This test WILL FAIL because the system doesn"t handle JWT secret"
rotation gracefully. Active requests fail when secrets rotate,
and there"s no grace period for old tokens."
'''
'''
pass
user_email = ""
password = "testpass123"

                                # Create user and get token with current secret
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
                                
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                                
assert login_response.status_code == 200
token = login_response.json()["access_token]"

                                # Verify token works
backend_client_test = TestClient(backend_app)
initial_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
                                
assert initial_response.status_code == 200

                                # Simulate JWT secret rotation (this is the critical test)
                                # In production, this happens during security incidents or scheduled rotation
new_secret = "new-jwt-secret-key-after-rotation"

                                # Patch JWT secret in auth service
with patch.object(JWTHandler, '_get_secret_key', return_value=new_secret):
                                    # Try to use old token after secret rotation
                                    # THIS WILL FAIL - old tokens should be handled gracefully
post_rotation_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
                                    

                                    # The token should either:
                                        # 1. Continue working (grace period), OR
                                        # 2. Fail with specific "token expired due to rotation error"
                                        # But it will likely fail with generic "invalid token error"
assert ( )
post_rotation_response.status_code == 200 or
(post_rotation_response.status_code == 401 and )
"rotation" in post_rotation_response.json().get("detail", ").lower())"
), (
f"JWT SECRET ROTATION FAILURE: Token handling after rotation failed. "
""
""
f"System should handle secret rotation gracefully."
                                        

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_cross_service_permission_escalation(self):
'''Test 5: Cross-Service Permission Escalation

This test WILL FAIL because permissions granted in auth_service
may not be properly validated in netra_backend, allowing
privilege escalation through service boundary manipulation.
'''
'''
pass
                                            # Create low-privilege user
user_email = ""
password = "testpass123"

auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password,"
"role": "user  # Low privilege role"
                                            
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                                            
assert login_response.status_code == 200
token = login_response.json()["access_token]"

                                            # Decode token to inspect claims
decoded_token = pyjwt.decode(token, verify=False)
original_role = decoded_token.get("role", "user)"

                                            # Create malicious token with elevated privileges
                                            # This simulates an attacker tampering with token claims
malicious_payload = decoded_token.copy()
malicious_payload["role"] = "admin"
malicious_payload["permissions"] = ["admin:read", "admin:write", "admin:delete]"
malicious_payload["iat] = int(time.time())"
malicious_payload["exp] = int(time.time()) + 3600"

                                            # Create token with same secret (simulating secret leak or weak secret)
malicious_token = pyjwt.encode( )
malicious_payload,
env.get("JWT_SECRET_KEY),"
algorithm="HS256"
                                            

                                            # Try to access admin endpoint with escalated token
backend_client_test = TestClient(backend_app)

                                            # THIS ASSERTION WILL FAIL - backend should reject tampered tokens
                                            # But if token validation is weak, it might accept the malicious token
admin_response = backend_client_test.get( )
"/admin/users,  # Admin-only endpoint"
headers={"Authorization": "}"
                                            

assert admin_response.status_code == 401, "( )"
f"PRIVILEGE ESCALATION VULNERABILITY: Tampered token accepted. "
""
""
f"Backend should validate token integrity and reject tampering."
                                            

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture
    async def test_oauth_state_replay_attack(self):
'''Test 6: OAuth State Replay Attack

This test WILL FAIL because OAuth state parameters aren"t properly"
validated against replay attacks, allowing attackers to reuse
state tokens for unauthorized access.
'''
'''
pass
                                                # Simulate OAuth flow initiation
auth_client_test = TestClient(auth_app)

                                                # Start OAuth flow - this should generate a unique state parameter
oauth_start_response = auth_client_test.get("/auth/oauth/google/login)"
assert oauth_start_response.status_code in [200, "302]"

                                                Extract state parameter from response/redirect
                                                # In real implementation, this would be in the redirect URL
state_value = ""

                                                # Simulate successful OAuth callback with valid state
callback_data = { }
"code": "valid_oauth_code_123,"
"state: state_value"
                                                

first_callback_response = auth_client_test.post("/auth/oauth/google/callback, json=callback_data)"

                                                # First use should succeed (if OAuth is implemented)
if first_callback_response.status_code == 200:
    pass
first_token = first_callback_response.json().get("access_token)"

                                                    # Wait a moment
await asyncio.sleep(0.1)

                                                    # THIS ASSERTION WILL FAIL - replay attack should be prevented
                                                    # Attempt to replay the same OAuth state/code combination
replay_response = auth_client_test.post("/auth/oauth/google/callback, json=callback_data)"

assert replay_response.status_code == 400, "( )"
f"OAUTH REPLAY ATTACK VULNERABILITY: State parameter reused successfully. "
""
f"OAuth implementation should prevent state parameter replay attacks."
                                                    

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_refresh_token_cross_service_leak(self):
'''Test 7: Refresh Token Cross-Service Leak

This test WILL FAIL because refresh tokens may leak between
services or be accessible from unintended endpoints,
creating security vulnerabilities.
'''
'''
pass
user_email = ""
password = "testpass123"

                                                        # Create user and get tokens
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
                                                        
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                                                        
assert login_response.status_code == 200

login_data = login_response.json()
access_token = login_data["access_token]"
refresh_token = login_data.get("refresh_token)"

if refresh_token:
                                                            Try to access refresh token from backend service
                                                            THIS SHOULD FAIL - refresh tokens should only be accessible from auth service
backend_client_test = TestClient(backend_app)

                                                            # Attempt to use refresh token with backend
backend_refresh_response = backend_client_test.post( )
"/auth/refresh,"
headers={"Authorization": "}"
                                                            

                                                            # Also try to extract refresh token through backend API
user_profile_response = backend_client_test.get( )
"/auth/me,"
headers={"Authorization": "}"
                                                            

if user_profile_response.status_code == 200:
    pass
profile_data = user_profile_response.json()

                                                                # THIS ASSERTION WILL FAIL - refresh tokens should not be exposed
assert "refresh_token" not in profile_data, "( )"
f"REFRESH TOKEN LEAK: Refresh token exposed in user profile. "
""
f"Refresh tokens should never be accessible from backend service."
                                                                

                                                                # Backend should not accept refresh tokens for any operations
assert backend_refresh_response.status_code == 401, "( )"
f"REFRESH TOKEN CROSS-SERVICE VULNERABILITY: Backend accepted refresh token. "
""
f"Only auth service should handle refresh tokens."
                                                                

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_multi_tab_session_collision(self):
'''Test 8: Multi-Tab Session Collision

This test WILL FAIL because the system doesn"t properly handle"
multiple browser tabs with different sessions for the same user,
leading to session collision and state corruption.
'''
'''
pass
user_email = ""
password = "testpass123"

                                                                    # Create user
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
                                                                    
assert register_response.status_code == 201

                                                                    # Simulate multiple tab logins (should create separate sessions)
login_responses = []
for i in range(3):
response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
                                                                        
assert response.status_code == 200
login_responses.append(response.json())
await asyncio.sleep(0.5)  # Small delay between logins

                                                                        Extract tokens from different "tabs"
tokens = [resp["access_token] for resp in login_responses]"

                                                                        # Verify all tokens are different (each tab should have unique session)
unique_tokens = set(tokens)
assert len(unique_tokens) == len(tokens), "( )"
f"SESSION COLLISION: Multiple tabs received identical tokens. "
""
f"Each browser tab should have an independent session."
                                                                        

                                                                        Test concurrent operations from different tabs
backend_client_test = TestClient(backend_app)

async def tab_operation(token, tab_id):
"""Simulate user action from specific tab"""
response = backend_client_test.get( )
"",
headers={"Authorization": "}"
    
await asyncio.sleep(0)
return response.status_code, tab_id

    Execute concurrent operations from all tabs
tasks = [tab_operation(token, i) for i, token in enumerate(tokens)]
results = await asyncio.gather(*tasks, return_exceptions=True)

successful_operations = [item for item in []] == 200]

    # THIS ASSERTION WILL FAIL - all tabs should work independently
assert len(successful_operations) == len(tokens), "( )"
""
""
f"Multi-tab sessions are interfering with each other."
    

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_service_restart_auth_persistence(self):
'''Test 9: Service Restart Auth Persistence

This test WILL FAIL because authentication state doesn"t persist"
properly across service restarts, causing all users to be logged out
when services restart.
'''
'''
pass
user_email = ""
password = "testpass123"

        # Create user and establish session
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
        
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
        
assert login_response.status_code == 200
token = login_response.json()["access_token]"

        # Verify token works before restart
backend_client_test = TestClient(backend_app)
pre_restart_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
        
assert pre_restart_response.status_code == 200

        # Simulate service restart by clearing in-memory caches/state
        # This simulates what happens during a real service restart
        # Mock: Component isolation for testing without external dependencies
        # Mock: Component isolation for testing without external dependencies
        # Wait for caches to clear
await asyncio.sleep(0.1)

        # THIS ASSERTION WILL FAIL - valid tokens should survive restart
        # If auth depends on in-memory state, this will fail
post_restart_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
        

assert post_restart_response.status_code == 200, "( )"
f"SERVICE RESTART AUTH FAILURE: Valid token rejected after restart. "
""
f"Authentication should persist across service restarts."
        

@pytest.mark.asyncio
@pytest.mark.critical
# @pytest.fixture, reason="Auth service or backend not available)"
    async def test_cross_origin_token_injection(self):
'''Test 10: Cross-Origin Token Injection

This test WILL FAIL because the system doesn"t properly validate"
token origins, allowing tokens from unauthorized domains to be
accepted by the backend service.
'''
'''
pass
user_email = ""
password = "testpass123"

            # Create legitimate user and token
auth_client_test = TestClient(auth_app)
register_response = auth_client_test.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
            
assert register_response.status_code == 201

login_response = auth_client_test.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
            
assert login_response.status_code == 200
legitimate_token = login_response.json()["access_token]"

            # Create malicious token with different issuer/audience
            This simulates an attack where tokens from different systems are used
malicious_payload = { }
"sub: user_email,"
"iss": "malicious-issuer.com,  # Wrong issuer"
"aud": "evil-audience,         # Wrong audience"
"exp: int(time.time()) + 3600,"
"iat: int(time.time()),"
"role": "admin"
            

malicious_token = pyjwt.encode( )
malicious_payload,
env.get("JWT_SECRET_KEY),  # Same secret (simulating leak)"
algorithm="HS256"
            

            # Try to use malicious token with backend
backend_client_test = TestClient(backend_app)

            # THIS ASSERTION WILL FAIL - backend should validate token origin
malicious_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
            

assert malicious_response.status_code == 401, "( )"
f"CROSS-ORIGIN TOKEN INJECTION: Malicious token accepted. "
""
f"Backend should validate token issuer and audience claims."
            

            # Verify legitimate token still works
legitimate_response = backend_client_test.get( )
"/health,"
headers={"Authorization": "}"
            

assert legitimate_response.status_code == 200, "( )"
"Legitimate token should continue working while malicious tokens are rejected"
            

@pytest.fixture
def auth_service_client(self):
    pass
"""Fixture to provide auth service test client"""
if not auth_service_available:
    pass
pytest.skip("Auth service not available)"
        # Create auth app at test execution time to avoid hanging
await asyncio.sleep(0)
return TestClient(auth_service.main.app)

@pytest.fixture
def backend_service_client(self):
    pass
"""Fixture to provide backend service test client"""
pass
if not backend_available:
    pass
pytest.skip("Backend service not available)"
        # Create backend app at test execution time to avoid hanging
return TestClient(netra_backend.app.main.app)

# @pytest.fixture
    async def test_user_credentials(self, auth_service_client):
            # Removed problematic line: Fixture to create test user and await asyncio.sleep(0)
return credentials'''
return credentials'''
user_email = ""
password = "testpass123"

            # Register user
register_response = auth_service_client.post("/auth/register, json={ })"
"email: user_email,"
"password: password,"
"confirm_password: password"
            
assert register_response.status_code == 201

            # Login to get token
login_response = auth_service_client.post("/auth/login, json={ })"
"email: user_email,"
"password: password"
            
assert login_response.status_code == 200

return { }
"email: user_email,"
"password: password,"
"token": login_response.json()["access_token]"
            

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
        raise RuntimeError("WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure):"
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

'''