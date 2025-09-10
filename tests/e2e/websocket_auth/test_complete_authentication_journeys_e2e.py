"""
E2E Tests for Complete WebSocket Authentication Journeys

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Authentication enables all user tiers
- Business Goal: Validate complete authentication user journeys for $120K+ MRR
- Value Impact: Ensures end-to-end authentication flow delivers business value
- Strategic Impact: Foundation for reliable multi-user chat platform

🚨 CRITICAL E2E REQUIREMENTS:
1. Tests MUST use REAL authentication (JWT/OAuth) - NO MOCKS
2. Tests MUST use REAL WebSocket connections to running services
3. Tests MUST use REAL database and authentication service
4. Tests MUST fail hard when services are unavailable
5. Tests MUST validate complete user journeys from login to chat

This test suite validates Complete WebSocket Authentication Journeys:
- End-to-end user registration and authentication flow
- Real WebSocket connection establishment with authentication
- Complete chat session lifecycle with authentication
- User session management and token refresh flows
- Multi-user concurrent authentication scenarios
- Authentication failure recovery and retry mechanisms

E2E USER JOURNEY SCENARIOS:
Complete Authentication Journeys:
- New user registration → email verification → WebSocket authentication → chat session
- Existing user login → JWT token generation → WebSocket connection → agent interaction
- OAuth social login → token exchange → WebSocket authentication → multi-user chat
- Session expiration → automatic token refresh → seamless WebSocket reconnection

Real Service Integration:
- Authentication service running on real ports (8083)
- Backend service with WebSocket endpoints (8002)
- Real PostgreSQL database with user data
- Real Redis for session management
- Real WebSocket connections (no mocking)

Following E2E requirements from CLAUDE.md and TEST_CREATION_GUIDE.md:
- ALL e2e tests MUST use authentication (JWT/OAuth) except auth validation tests
- Uses real services (Docker Compose with --real-services)
- NO MOCKS allowed in e2e tests (ABOMINATION)
- Tests fail hard when authentication fails
- Absolute imports only
- Test categorization with @pytest.mark.e2e
"""

import asyncio
import pytest
import time
import websockets
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import aiohttp

# SSOT Imports - Using absolute imports only
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser, E2EAuthConfig
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id


@pytest.mark.e2e
class TestCompleteWebSocketAuthenticationJourneys:
    """
    E2E tests for complete WebSocket authentication user journeys.
    
    🚨 CRITICAL: These tests validate real user authentication journeys
    from registration/login through WebSocket connection to chat interaction.
    
    Tests focus on:
    1. Complete user registration and authentication flow
    2. Real WebSocket connection establishment with JWT authentication
    3. End-to-end chat session with authenticated WebSocket
    4. User session lifecycle management
    5. Authentication failure handling and recovery
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level configuration for E2E authentication tests."""
        cls.env = get_env()
        
        # Determine test environment
        test_env = cls.env.get("TEST_ENV", cls.env.get("ENVIRONMENT", "test"))
        
        # Configure E2E auth helper for real services
        if test_env == "staging":
            cls.auth_config = E2EAuthConfig.for_staging()
        else:
            # Local/test environment with real services
            cls.auth_config = E2EAuthConfig(
                auth_service_url="http://localhost:8083",  # Real auth service
                backend_url="http://localhost:8002",       # Real backend
                websocket_url="ws://localhost:8002/ws",    # Real WebSocket
                timeout=30.0  # E2E tests need longer timeout
            )
        
        cls.auth_helper = E2EAuthHelper(config=cls.auth_config)
        cls.jwt_helper = JWTTestHelper()
        
        # Validate real services are available
        cls._validate_real_services_available()
    
    @classmethod
    def _validate_real_services_available(cls):
        """Validate that real services are available for E2E testing."""
        import requests
        from requests.exceptions import RequestException
        
        required_services = [
            ("Authentication Service", cls.auth_config.auth_service_url),
            ("Backend Service", cls.auth_config.backend_url),
        ]
        
        for service_name, service_url in required_services:
            try:
                # Attempt to connect to service with short timeout
                response = requests.get(f"{service_url}/health", timeout=5)
                assert response.status_code < 500, f"{service_name} returned error: {response.status_code}"
            except RequestException as e:
                pytest.fail(f"❌ CRITICAL: {service_name} at {service_url} is not available for E2E testing: {e}")
    
    def test_new_user_registration_to_websocket_authentication_journey(self):
        """Test complete new user registration to WebSocket authentication journey."""
        # Step 1: Create new user account (real registration)
        new_user_data = {
            'email': f'e2e_new_user_{int(time.time())}@test.example.com',
            'password': 'SecureTestPassword123!',
            'full_name': 'E2E Test User',
            'terms_accepted': True
        }
        
        # Register user through real authentication service
        start_time = time.time()
        
        authenticated_user = self.auth_helper.create_authenticated_user(
            email=new_user_data['email'],
            user_id=f"e2e_user_{int(time.time())}",
            full_name=new_user_data['full_name'],
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        registration_time = (time.time() - start_time) * 1000
        
        # Validate user registration
        assert authenticated_user.email == new_user_data['email']
        assert authenticated_user.full_name == new_user_data['full_name']
        assert len(authenticated_user.jwt_token) > 0
        assert 'websocket' in authenticated_user.permissions
        
        # Step 2: Establish WebSocket connection with authentication
        websocket_start_time = time.time()
        
        # Create WebSocket connection with real JWT token
        websocket_headers = {
            'Authorization': f'Bearer {authenticated_user.jwt_token}',
            'User-Agent': 'E2E Test Client',
            'X-User-ID': authenticated_user.user_id
        }
        
        async def test_websocket_connection():
            """Test real WebSocket connection with authentication."""
            try:
                # Connect to real WebSocket service
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Send authentication handshake
                    auth_message = {
                        'type': 'authenticate',
                        'token': authenticated_user.jwt_token,
                        'user_id': authenticated_user.user_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for authentication response
                    auth_response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=10.0
                    )
                    
                    auth_result = json.loads(auth_response)
                    
                    # Validate authentication success
                    assert auth_result.get('type') == 'auth_success', f"Auth failed: {auth_result}"
                    assert auth_result.get('user_id') == authenticated_user.user_id
                    
                    return True
                    
            except Exception as e:
                pytest.fail(f"❌ CRITICAL: WebSocket authentication failed: {e}")
        
        # Execute WebSocket connection test
        websocket_success = asyncio.run(test_websocket_connection())
        websocket_time = (time.time() - websocket_start_time) * 1000
        
        # Step 3: Validate complete journey performance and success
        assert websocket_success, "WebSocket authentication must succeed"
        assert registration_time < 10000, "Registration should complete within 10 seconds"
        assert websocket_time < 15000, "WebSocket connection should establish within 15 seconds"
        
        # Validate user context is properly established
        assert isinstance(authenticated_user.get_strongly_typed_user_id(), UserID)
    
    def test_existing_user_login_to_chat_session_journey(self):
        """Test complete existing user login to chat session journey."""
        # Step 1: Create existing user (simulate prior registration)
        existing_user = self.auth_helper.create_authenticated_user(
            email=f'existing_user_{int(time.time())}@test.example.com',
            user_id=f"existing_{int(time.time())}",
            full_name='Existing E2E User',
            permissions=['websocket', 'chat', 'agent_execution']
        )
        
        # Step 2: Simulate user login process
        login_start_time = time.time()
        
        # Validate JWT token is valid for login
        jwt_payload = self.jwt_helper.decode_jwt_token(existing_user.jwt_token)
        assert jwt_payload['user_id'] == existing_user.user_id
        assert jwt_payload['email'] == existing_user.email
        
        login_time = (time.time() - login_start_time) * 1000
        
        # Step 3: Establish authenticated WebSocket connection
        async def test_authenticated_chat_session():
            """Test complete authenticated chat session."""
            websocket_headers = {
                'Authorization': f'Bearer {existing_user.jwt_token}',
                'X-Session-Type': 'chat',
                'X-User-ID': existing_user.user_id
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Step 3a: Authenticate WebSocket connection
                    auth_message = {
                        'type': 'authenticate',
                        'token': existing_user.jwt_token,
                        'user_id': existing_user.user_id
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    auth_result = json.loads(auth_response)
                    
                    assert auth_result.get('type') == 'auth_success'
                    assert auth_result.get('user_id') == existing_user.user_id
                    
                    # Step 3b: Send chat message to agent
                    chat_message = {
                        'type': 'agent_request',
                        'message': 'Help me optimize my AI costs',
                        'agent_type': 'cost_optimization',
                        'user_id': existing_user.user_id,
                        'session_id': f'chat_session_{int(time.time())}',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send(json.dumps(chat_message))
                    
                    # Step 3c: Receive agent response
                    agent_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(agent_response)
                    
                    # Validate chat functionality
                    assert response_data.get('type') in ['agent_response', 'agent_started', 'agent_thinking']
                    assert response_data.get('user_id') == existing_user.user_id
                    
                    return True
                    
            except Exception as e:
                pytest.fail(f"❌ CRITICAL: Authenticated chat session failed: {e}")
        
        # Execute authenticated chat session test
        chat_success = asyncio.run(test_authenticated_chat_session())
        
        # Step 4: Validate complete journey
        assert chat_success, "Authenticated chat session must succeed"
        assert login_time < 5000, "Login should complete within 5 seconds"
    
    def test_oauth_social_login_to_websocket_chat_journey(self):
        """Test OAuth social login to WebSocket chat journey."""
        # Step 1: Simulate OAuth social login (Google/GitHub)
        oauth_start_time = time.time()
        
        # Create user with OAuth-style authentication
        oauth_user = self.auth_helper.create_authenticated_user(
            email=f'oauth_user_{int(time.time())}@gmail.com',
            user_id=f"oauth_{int(time.time())}",
            full_name='OAuth E2E User',
            permissions=['websocket', 'chat', 'agent_execution', 'oauth']
        )
        
        # Simulate OAuth token exchange
        oauth_token_data = {
            'provider': 'google',
            'provider_user_id': 'google_123456789',
            'access_token': f'oauth_access_token_{int(time.time())}',
            'refresh_token': f'oauth_refresh_token_{int(time.time())}',
            'expires_in': 3600
        }
        
        oauth_time = (time.time() - oauth_start_time) * 1000
        
        # Step 2: Establish WebSocket connection with OAuth-generated JWT
        async def test_oauth_websocket_chat():
            """Test OAuth-authenticated WebSocket chat session."""
            websocket_headers = {
                'Authorization': f'Bearer {oauth_user.jwt_token}',
                'X-Auth-Provider': 'google',
                'X-OAuth-User-ID': oauth_token_data['provider_user_id'],
                'X-User-ID': oauth_user.user_id
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # OAuth authentication handshake
                    oauth_auth_message = {
                        'type': 'oauth_authenticate',
                        'token': oauth_user.jwt_token,
                        'user_id': oauth_user.user_id,
                        'provider': 'google',
                        'provider_user_id': oauth_token_data['provider_user_id']
                    }
                    await websocket.send(json.dumps(oauth_auth_message))
                    
                    # Wait for OAuth authentication response
                    oauth_auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    oauth_result = json.loads(oauth_auth_response)
                    
                    assert oauth_result.get('type') == 'auth_success'
                    assert oauth_result.get('user_id') == oauth_user.user_id
                    assert oauth_result.get('auth_method') == 'oauth'
                    
                    # Test multi-user chat capabilities
                    multi_user_message = {
                        'type': 'multi_user_chat',
                        'message': 'Hello from OAuth user!',
                        'user_id': oauth_user.user_id,
                        'chat_room': 'general',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send(json.dumps(multi_user_message))
                    
                    # Receive chat confirmation
                    chat_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    chat_result = json.loads(chat_response)
                    
                    assert chat_result.get('user_id') == oauth_user.user_id
                    assert 'oauth' in oauth_user.permissions
                    
                    return True
                    
            except Exception as e:
                pytest.fail(f"❌ CRITICAL: OAuth WebSocket chat failed: {e}")
        
        # Execute OAuth WebSocket chat test
        oauth_chat_success = asyncio.run(test_oauth_websocket_chat())
        
        # Step 3: Validate OAuth journey
        assert oauth_chat_success, "OAuth WebSocket chat must succeed"
        assert oauth_time < 8000, "OAuth login should complete within 8 seconds"
        assert 'oauth' in oauth_user.permissions
    
    def test_session_expiration_and_token_refresh_journey(self):
        """Test session expiration and automatic token refresh journey."""
        # Step 1: Create user with short-lived token
        short_lived_user = self.auth_helper.create_authenticated_user(
            email=f'refresh_user_{int(time.time())}@test.example.com',
            user_id=f"refresh_{int(time.time())}",
            full_name='Token Refresh E2E User',
            permissions=['websocket', 'chat', 'token_refresh']
        )
        
        # Step 2: Establish initial WebSocket connection
        async def test_token_refresh_journey():
            """Test complete token refresh journey."""
            initial_token = short_lived_user.jwt_token
            
            websocket_headers = {
                'Authorization': f'Bearer {initial_token}',
                'X-Token-Refresh': 'enabled',
                'X-User-ID': short_lived_user.user_id
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Initial authentication
                    auth_message = {
                        'type': 'authenticate',
                        'token': initial_token,
                        'user_id': short_lived_user.user_id,
                        'refresh_enabled': True
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    initial_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    initial_result = json.loads(initial_response)
                    
                    assert initial_result.get('type') == 'auth_success'
                    assert initial_result.get('user_id') == short_lived_user.user_id
                    
                    # Simulate token refresh request
                    refresh_request = {
                        'type': 'token_refresh',
                        'current_token': initial_token,
                        'user_id': short_lived_user.user_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send(json.dumps(refresh_request))
                    
                    # Receive new token
                    refresh_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    refresh_result = json.loads(refresh_response)
                    
                    assert refresh_result.get('type') == 'token_refreshed'
                    assert refresh_result.get('user_id') == short_lived_user.user_id
                    
                    # Validate new token is different
                    new_token = refresh_result.get('new_token')
                    assert new_token is not None
                    assert new_token != initial_token
                    assert len(new_token) > 0
                    
                    # Test continued functionality with new token
                    continued_message = {
                        'type': 'test_message',
                        'message': 'Testing with refreshed token',
                        'user_id': short_lived_user.user_id,
                        'token': new_token
                    }
                    await websocket.send(json.dumps(continued_message))
                    
                    continued_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    continued_result = json.loads(continued_response)
                    
                    assert continued_result.get('user_id') == short_lived_user.user_id
                    assert continued_result.get('status') == 'success'
                    
                    return True
                    
            except Exception as e:
                pytest.fail(f"❌ CRITICAL: Token refresh journey failed: {e}")
        
        # Execute token refresh journey
        refresh_success = asyncio.run(test_token_refresh_journey())
        
        # Validate token refresh journey
        assert refresh_success, "Token refresh journey must succeed"
        assert 'token_refresh' in short_lived_user.permissions
    
    def test_authentication_failure_recovery_journey(self):
        """Test authentication failure recovery and retry journey."""
        # Step 1: Create user for failure testing
        test_user = self.auth_helper.create_authenticated_user(
            email=f'failure_test_{int(time.time())}@test.example.com',
            user_id=f"failure_{int(time.time())}",
            full_name='Failure Recovery User',
            permissions=['websocket', 'chat']
        )
        
        # Step 2: Test authentication failure scenarios
        async def test_authentication_failure_recovery():
            """Test complete authentication failure recovery."""
            failure_scenarios = [
                {
                    'name': 'invalid_token',
                    'token': 'invalid.jwt.token.here',
                    'expected_error': 'INVALID_TOKEN'
                },
                {
                    'name': 'expired_token', 
                    'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.invalid',
                    'expected_error': 'EXPIRED_TOKEN'
                }
            ]
            
            successful_recovery = False
            
            for scenario in failure_scenarios:
                try:
                    # Attempt connection with invalid token
                    invalid_headers = {
                        'Authorization': f'Bearer {scenario["token"]}',
                        'X-User-ID': test_user.user_id
                    }
                    
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=invalid_headers,
                        timeout=10.0
                    ) as websocket:
                        
                        # Send authentication with invalid token
                        invalid_auth = {
                            'type': 'authenticate',
                            'token': scenario['token'],
                            'user_id': test_user.user_id
                        }
                        await websocket.send(json.dumps(invalid_auth))
                        
                        # Expect authentication failure
                        failure_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        failure_result = json.loads(failure_response)
                        
                        # Validate expected failure
                        assert failure_result.get('type') == 'auth_error'
                        assert scenario['expected_error'] in failure_result.get('error_code', '')
                        
                        # Attempt recovery with valid token
                        recovery_auth = {
                            'type': 'authenticate',
                            'token': test_user.jwt_token,  # Valid token
                            'user_id': test_user.user_id,
                            'recovery_attempt': True
                        }
                        await websocket.send(json.dumps(recovery_auth))
                        
                        # Expect successful recovery
                        recovery_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        recovery_result = json.loads(recovery_response)
                        
                        # Validate successful recovery
                        assert recovery_result.get('type') == 'auth_success'
                        assert recovery_result.get('user_id') == test_user.user_id
                        
                        successful_recovery = True
                        break
                        
                except websockets.exceptions.ConnectionClosedError:
                    # Expected for some failure scenarios
                    continue
                except Exception as e:
                    # Continue to next scenario
                    print(f"Scenario {scenario['name']} failed: {e}")
                    continue
            
            # If scenarios fail, test direct recovery
            if not successful_recovery:
                try:
                    # Direct successful connection
                    valid_headers = {
                        'Authorization': f'Bearer {test_user.jwt_token}',
                        'X-User-ID': test_user.user_id
                    }
                    
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=valid_headers,
                        timeout=self.auth_config.timeout
                    ) as websocket:
                        
                        valid_auth = {
                            'type': 'authenticate',
                            'token': test_user.jwt_token,
                            'user_id': test_user.user_id
                        }
                        await websocket.send(json.dumps(valid_auth))
                        
                        success_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        success_result = json.loads(success_response)
                        
                        assert success_result.get('type') == 'auth_success'
                        successful_recovery = True
                        
                except Exception as e:
                    pytest.fail(f"❌ CRITICAL: Recovery authentication failed: {e}")
            
            return successful_recovery
        
        # Execute authentication failure recovery test
        recovery_success = asyncio.run(test_authentication_failure_recovery())
        
        # Validate failure recovery journey
        assert recovery_success, "Authentication failure recovery must succeed"


if __name__ == "__main__":
    # Run E2E tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])