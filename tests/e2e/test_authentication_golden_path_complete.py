
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Test Complete Authentication Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete authentication flow works end-to-end
- Value Impact: Users must be able to authenticate to access core chat functionality
- Strategic Impact: Foundation for all revenue-generating features

CRITICAL: This test validates the complete authentication flow that depends on
the user_sessions table, reproducing the exact staging failure that blocks
user access to chat functionality.
"""

import pytest
import asyncio
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAuthenticationGoldenPathComplete(BaseE2ETest):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Test complete authentication flow with user_sessions dependency."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_auth_flow_user_sessions_dependency(self, real_services_fixture):
        """
        Test complete authentication flow requiring user_sessions table.
        
        This test reproduces the EXACT business impact of the missing user_sessions table:
        1. User attempts to authenticate
        2. System tries to create/validate session 
        3. Fails due to missing user_sessions table
        4. User cannot access chat functionality
        5. Business value delivery blocked
        
        Should FAIL initially due to missing table, then PASS after fix.
        """
        # Initialize E2E auth helper
        auth_helper = E2EAuthHelper()
        
        try:
            # Test 1: Create authenticated user (requires user_sessions table for session storage)
            print("[U+1F510] Testing user authentication with session creation...")
            
            # This should fail if user_sessions table is missing
            auth_user = await auth_helper.create_authenticated_user(
                email="golden_path_test@example.com",
                full_name="Golden Path User"
            )
            
            # If we get here, authentication worked
            assert auth_user is not None, "Failed to create authenticated user"
            assert auth_user.jwt_token is not None, "User missing JWT token"
            assert auth_user.user_id is not None, "User missing ID"
            
            print(f" PASS:  User authenticated successfully: {auth_user.user_id}")
            
            # Test 2: Validate session persistence (depends on user_sessions table)
            print("[U+1F4BE] Testing session persistence and validation...")
            
            # Get authentication headers
            auth_headers = auth_helper.get_auth_headers(auth_user.jwt_token)
            assert auth_headers is not None, "Failed to get auth headers"
            assert "Authorization" in auth_headers, "Missing Authorization header"
            
            # Test 3: Validate session against backend service
            backend_url = real_services_fixture["backend_url"]
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Make authenticated request to backend
                validate_url = f"{backend_url}/api/v1/auth/validate"
                
                async with session.get(validate_url, headers=auth_headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        assert user_data["user_id"] == auth_user.user_id
                        print(" PASS:  Session validation successful")
                    else:
                        # Expected failure case - session validation fails due to missing user_sessions
                        error_text = await response.text()
                        if "user_sessions" in error_text.lower() or response.status == 500:
                            pytest.fail(f"Session validation failed due to missing user_sessions table: {error_text}")
                        else:
                            pytest.fail(f"Unexpected session validation failure: {response.status} - {error_text}")
            
            # Test 4: Test session refresh (requires user_sessions table for token management)
            print(" CYCLE:  Testing session refresh functionality...")
            
            # Refresh the JWT token
            refreshed_auth = await auth_helper.refresh_user_session(auth_user)
            assert refreshed_auth is not None, "Failed to refresh session"
            assert refreshed_auth.jwt_token != auth_user.jwt_token, "Token was not refreshed"
            
            print(" PASS:  Session refresh successful")
            
            # Test 5: Test session cleanup (validates user_sessions table operations)
            print("[U+1F9F9] Testing session cleanup...")
            
            cleanup_success = await auth_helper.cleanup_user_session(auth_user.user_id)
            assert cleanup_success, "Failed to cleanup user session"
            
            print(" PASS:  Session cleanup successful")
            
            print(" CELEBRATION:  COMPLETE AUTHENTICATION FLOW SUCCESSFUL - user_sessions table is working!")
            
        except Exception as e:
            # Expected failure scenarios
            error_message = str(e).lower()
            
            if any(keyword in error_message for keyword in ["user_sessions", "table", "does not exist", "relation"]):
                pytest.fail(f" FAIL:  CRITICAL: Authentication failed due to missing user_sessions table: {e}")
            elif "connection" in error_message or "database" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: Database connection issue (may indicate missing schema): {e}")
            elif "service" in error_message or "unavailable" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: Service registration issue (app.state not configured): {e}")
            else:
                # Unexpected error
                pytest.fail(f" FAIL:  UNEXPECTED: Authentication failed with unexpected error: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_authentication_with_session_validation(self, real_services_fixture):
        """
        Test WebSocket authentication that validates against user_sessions table.
        
        This test validates the critical WebSocket authentication path that enables
        chat functionality - the core business value delivery mechanism.
        
        Should FAIL initially if user_sessions table missing, then PASS after fix.
        """
        # Initialize E2E auth helper
        auth_helper = E2EAuthHelper()
        
        try:
            # Create authenticated user for WebSocket connection
            auth_user = await auth_helper.create_authenticated_user(
                email="websocket_test@example.com",
                full_name="WebSocket User"
            )
            
            # Get WebSocket authentication headers
            ws_headers = auth_helper.get_websocket_headers(auth_user.jwt_token)
            
            # Test WebSocket connection with authentication
            backend_url = real_services_fixture["backend_url"]
            ws_url = backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
            
            import websockets
            import json
            
            try:
                # Connect to WebSocket with authentication
                async with websockets.connect(
                    ws_url,
                    extra_headers=ws_headers,
                    timeout=10
                ) as websocket:
                    
                    print("[U+1F517] WebSocket connection established with authentication")
                    
                    # Send test message that requires authenticated session
                    test_message = {
                        "type": "ping",
                        "user_id": auth_user.user_id,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        # Validate authenticated response
                        assert response_data.get("type") == "pong", "Invalid WebSocket response type"
                        print(" PASS:  WebSocket authentication successful")
                        
                    except asyncio.TimeoutError:
                        pytest.fail("WebSocket response timeout - session validation may have failed")
                    
            except websockets.exceptions.ConnectionClosed as e:
                if e.code == 1008:  # Policy violation
                    pytest.fail(" FAIL:  CRITICAL: WebSocket authentication failed - likely due to session validation failure")
                else:
                    pytest.fail(f" FAIL:  WebSocket connection closed unexpectedly: {e}")
                    
            except Exception as e:
                error_message = str(e).lower()
                if "authentication" in error_message or "unauthorized" in error_message:
                    pytest.fail(f" FAIL:  CRITICAL: WebSocket authentication failed: {e}")
                else:
                    pytest.fail(f" FAIL:  WebSocket connection failed: {e}")
                    
        except Exception as e:
            # Handle authentication setup failures
            error_message = str(e).lower()
            
            if "user_sessions" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: WebSocket auth failed due to missing user_sessions table: {e}")
            else:
                pytest.fail(f" FAIL:  WebSocket authentication setup failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_chat_functionality_requires_authentication(self, real_services_fixture):
        """
        Test that chat functionality requires proper authentication with user_sessions.
        
        This test validates the END-TO-END business value delivery:
        Authentication  ->  Session Management  ->  Chat Access  ->  Business Value
        
        Should FAIL initially if authentication stack is broken, then PASS after fix.
        """
        # Initialize E2E auth helper
        auth_helper = E2EAuthHelper()
        
        try:
            # Create authenticated user
            auth_user = await auth_helper.create_authenticated_user(
                email="chat_test@example.com",
                full_name="Chat User"
            )
            
            print(f"[U+1F510] User authenticated for chat access: {auth_user.user_id}")
            
            # Test chat access with authenticated session
            backend_url = real_services_fixture["backend_url"]
            auth_headers = auth_helper.get_auth_headers(auth_user.jwt_token)
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                
                # Test 1: Create chat thread (requires authentication)
                create_thread_url = f"{backend_url}/api/v1/threads"
                thread_data = {
                    "title": "Authentication Test Thread",
                    "description": "Testing chat access with user_sessions authentication"
                }
                
                async with session.post(
                    create_thread_url, 
                    json=thread_data,
                    headers=auth_headers
                ) as response:
                    
                    if response.status == 201:
                        thread_result = await response.json()
                        thread_id = thread_result["id"]
                        print(f" PASS:  Chat thread created: {thread_id}")
                    else:
                        error_text = await response.text()
                        pytest.fail(f" FAIL:  CRITICAL: Thread creation failed (authentication issue): {response.status} - {error_text}")
                
                # Test 2: Send message to thread (core business functionality)
                send_message_url = f"{backend_url}/api/v1/threads/{thread_id}/messages"
                message_data = {
                    "content": "Test message requiring authentication",
                    "message_type": "user"
                }
                
                async with session.post(
                    send_message_url,
                    json=message_data,
                    headers=auth_headers
                ) as response:
                    
                    if response.status == 201:
                        message_result = await response.json()
                        print(f" PASS:  Message sent successfully: {message_result['id']}")
                    else:
                        error_text = await response.text()
                        pytest.fail(f" FAIL:  CRITICAL: Message sending failed (authentication issue): {response.status} - {error_text}")
                
                # Test 3: Retrieve thread messages (validate session persistence)
                get_messages_url = f"{backend_url}/api/v1/threads/{thread_id}/messages"
                
                async with session.get(
                    get_messages_url,
                    headers=auth_headers
                ) as response:
                    
                    if response.status == 200:
                        messages = await response.json()
                        assert len(messages) > 0, "No messages retrieved"
                        print(f" PASS:  Messages retrieved: {len(messages)} messages")
                    else:
                        error_text = await response.text()
                        pytest.fail(f" FAIL:  CRITICAL: Message retrieval failed (session issue): {response.status} - {error_text}")
            
            print(" CELEBRATION:  COMPLETE CHAT FUNCTIONALITY SUCCESSFUL - Authentication and user_sessions working!")
            
        except Exception as e:
            error_message = str(e).lower()
            
            if "user_sessions" in error_message or "session" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: Chat functionality blocked by session management issue: {e}")
            elif "authentication" in error_message or "unauthorized" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: Chat functionality blocked by authentication failure: {e}")
            elif "database" in error_message or "table" in error_message:
                pytest.fail(f" FAIL:  CRITICAL: Chat functionality blocked by database issue: {e}")
            else:
                pytest.fail(f" FAIL:  Chat functionality failed: {e}")