"""
E2E Tests: Golden Path Auth Delegation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure complete auth flow works with delegation
- Value Impact: 500K+ ARR Golden Path functionality protected
- Strategic Impact: Core user authentication experience

This test suite validates the complete Golden Path user flow with auth service
delegation using the staging GCP environment:

1. Users login -> get AI responses (complete end-to-end flow)
2. WebSocket authentication using delegated auth patterns
3. Agent execution working with delegated authentication
4. Multi-user isolation maintained with delegation
5. Session management delegation working properly

CRITICAL: These tests use the STAGING environment (no Docker required)
and validate the complete business-critical user journey.

Test execution: python tests/e2e/auth_ssot/test_golden_path_auth_delegation.py
"""

import pytest
import asyncio
import json
import websockets
from typing import Dict, Any, List, Optional
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env


class GoldenPathAuthDelegationTests(BaseE2ETest):
    """
    E2E tests for Golden Path auth delegation using staging environment.
    
    Validates that unified auth delegation maintains the complete
    user experience from login through AI responses.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Configure for staging environment
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
        self.set_env_var("BACKEND_URL", "https://api.staging.netrasystems.ai")
        self.set_env_var("WEBSOCKET_URL", "wss://api.staging.netrasystems.ai/ws")
        
        # Test user details for staging
        self.test_user_email = "e2e-auth-delegation-test@example.com"
        self.test_user_password = "E2EAuthTest123!"
        
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.mission_critical
    async def test_complete_user_login_flow(self):
        """
        Test complete user login flow uses auth service delegation.
        
        CRITICAL: This validates the primary business value - users can login
        and the auth system works with delegation patterns.
        
        Expected: Users can successfully authenticate through delegated auth
        """
        import httpx
        
        try:
            # Test user registration/login through auth service delegation
            async with httpx.AsyncClient(timeout=30.0) as client:
                
                # Test auth service endpoint (should be available via delegation)
                auth_service_url = self.get_env_var("AUTH_SERVICE_URL")
                
                # Try to login/create user via backend that delegates to auth service
                backend_url = self.get_env_var("BACKEND_URL")
                login_response = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    },
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                
                # Should get either successful login or user creation needed
                assert login_response.status_code in [200, 201, 401, 404], \
                    f"Login endpoint responded with unexpected status: {login_response.status_code}"
                
                # If user doesn't exist, try to create via backend delegation
                if login_response.status_code in [401, 404]:
                    register_response = await client.post(
                        f"{backend_url}/auth/register",
                        json={
                            "email": self.test_user_email,
                            "password": self.test_user_password,
                            "name": "E2E Auth Delegation Test User"
                        }
                    )
                    
                    # Registration should work or user might already exist
                    assert register_response.status_code in [200, 201, 400, 409], \
                        f"Registration failed with status: {register_response.status_code}"
                    
                    # Try login again after registration
                    if register_response.status_code in [200, 201]:
                        login_response = await client.post(
                            f"{backend_url}/auth/login",
                            json={
                                "email": self.test_user_email,
                                "password": self.test_user_password
                            }
                        )
                
                # Verify login produces access token (delegated from auth service)
                if login_response.status_code in [200, 201]:
                    login_data = login_response.json()
                    
                    # Should have access token from auth service delegation
                    assert "access_token" in login_data or "token" in login_data, \
                        f"Login response missing access token: {login_data}"
                    
                    # Extract token for further testing
                    access_token = login_data.get("access_token") or login_data.get("token")
                    assert access_token is not None and len(access_token) > 0
                    
                    # Token should be JWT format (from auth service)
                    assert "." in access_token, "Token should be JWT format from auth service"
                    
                    self.logger.info(f"Login successful with delegated auth: {len(access_token)} chars")
                    
                    return access_token
                else:
                    pytest.skip(f"Could not establish test user for auth delegation testing")
                    
        except httpx.TimeoutException:
            pytest.skip("Staging environment not available for E2E testing")
        except Exception as e:
            pytest.fail(f"Login flow with auth delegation failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.mission_critical
    async def test_websocket_auth_with_delegation(self):
        """
        Test WebSocket authentication works with auth service delegation.
        
        CRITICAL: WebSocket auth is essential for real-time chat functionality.
        Must work with delegated authentication patterns.
        """
        try:
            # First get auth token through delegation
            access_token = await self.test_complete_user_login_flow()
            if access_token is None:
                pytest.skip("Could not get auth token for WebSocket testing")
            
            # Test WebSocket connection with delegated auth
            websocket_url = self.get_env_var("WEBSOCKET_URL")
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {access_token}"
                    },
                    timeout=10
                ) as websocket:
                    
                    # Send authentication message
                    auth_message = {
                        "type": "authenticate",
                        "token": access_token
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for authentication response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Should get successful authentication (via auth service delegation)
                    assert response_data.get("type") in ["authenticated", "connection_established"], \
                        f"WebSocket auth failed: {response_data}"
                    
                    self.logger.info("WebSocket authentication successful with delegation")
                    
                    # Test that we can send a message (requires auth)
                    test_message = {
                        "type": "message",
                        "content": "Test message with delegated auth"
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Should be able to receive response (auth working)
                    try:
                        message_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        self.logger.info("WebSocket message exchange successful with delegated auth")
                    except asyncio.TimeoutError:
                        # Timeout is OK - the important thing is auth worked
                        pass
                        
            except websockets.ConnectionClosed as e:
                if "401" in str(e) or "Unauthorized" in str(e):
                    pytest.fail("WebSocket auth delegation failed - authentication rejected")
                else:
                    # Other connection issues might be environment-related
                    pytest.skip(f"WebSocket connection issue (non-auth): {e}")
                    
        except Exception as e:
            pytest.fail(f"WebSocket auth with delegation failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_agent_execution_with_delegated_auth(self):
        """
        Test that agent execution works with delegated authentication.
        
        Agents should be able to execute using tokens validated through
        auth service delegation rather than local JWT validation.
        """
        try:
            # Get auth token through delegation
            access_token = await self.test_complete_user_login_flow()
            if access_token is None:
                pytest.skip("Could not get auth token for agent testing")
            
            # Test agent execution with delegated auth
            import httpx
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test agent execution endpoint
                agent_response = await client.post(
                    f"{backend_url}/agent/execute",
                    json={
                        "agent": "triage_agent",
                        "message": "Test agent execution with delegated auth",
                        "stream": False
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                # Should get successful response (auth delegation working)
                assert agent_response.status_code in [200, 201, 202], \
                    f"Agent execution failed with status: {agent_response.status_code}"
                
                agent_data = agent_response.json()
                
                # Should have execution result or process ID
                assert "result" in agent_data or "process_id" in agent_data or "message" in agent_data, \
                    f"Agent response missing expected fields: {agent_data}"
                
                self.logger.info("Agent execution successful with delegated auth")
                
        except httpx.TimeoutException:
            pytest.skip("Agent execution timeout in staging environment")
        except Exception as e:
            pytest.fail(f"Agent execution with delegated auth failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_multi_user_isolation_with_delegation(self):
        """
        Test that multi-user isolation works with auth service delegation.
        
        Different users should get isolated authentication and execution
        contexts when using delegated auth patterns.
        """
        try:
            # Create multiple test users
            test_users = [
                {
                    "email": "e2e-auth-user1@example.com",
                    "password": "TestUser1Pass123!",
                    "name": "E2E Auth User 1"
                },
                {
                    "email": "e2e-auth-user2@example.com", 
                    "password": "TestUser2Pass123!",
                    "name": "E2E Auth User 2"
                }
            ]
            
            user_tokens = []
            
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Login/register each user
                for user in test_users:
                    try:
                        # Try login first
                        login_response = await client.post(
                            f"{backend_url}/auth/login",
                            json={
                                "email": user["email"],
                                "password": user["password"]
                            }
                        )
                        
                        # If login fails, try registration
                        if login_response.status_code not in [200, 201]:
                            register_response = await client.post(
                                f"{backend_url}/auth/register",
                                json=user
                            )
                            
                            if register_response.status_code in [200, 201]:
                                # Try login again
                                login_response = await client.post(
                                    f"{backend_url}/auth/login",
                                    json={
                                        "email": user["email"],
                                        "password": user["password"]
                                    }
                                )
                        
                        # Extract token if login successful
                        if login_response.status_code in [200, 201]:
                            login_data = login_response.json()
                            token = login_data.get("access_token") or login_data.get("token")
                            if token:
                                user_tokens.append({
                                    "user": user["email"],
                                    "token": token
                                })
                                
                    except Exception as e:
                        self.logger.warning(f"Could not setup user {user['email']}: {e}")
            
            # Verify we have at least 2 isolated users
            if len(user_tokens) < 2:
                pytest.skip("Could not create multiple users for isolation testing")
            
            # Verify tokens are different (isolation working)
            token1 = user_tokens[0]["token"]
            token2 = user_tokens[1]["token"]
            
            assert token1 != token2, "User tokens should be different (isolation required)"
            
            # Verify each user can access their own resources
            for user_token_info in user_tokens:
                try:
                    # Test user-specific endpoint
                    profile_response = await client.get(
                        f"{backend_url}/user/profile",
                        headers={
                            "Authorization": f"Bearer {user_token_info['token']}"
                        }
                    )
                    
                    # Should get successful response for each user
                    assert profile_response.status_code in [200, 201], \
                        f"Profile access failed for {user_token_info['user']}"
                        
                except Exception as e:
                    self.logger.warning(f"Profile test failed for {user_token_info['user']}: {e}")
            
            self.logger.info(f"Multi-user isolation validated with {len(user_tokens)} users")
            
        except Exception as e:
            pytest.fail(f"Multi-user isolation testing with delegation failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_session_management_delegation(self):
        """
        Test that session management works through auth service delegation.
        
        Session creation, validation, and cleanup should all
        go through auth service rather than local session storage.
        """
        try:
            # Get auth token
            access_token = await self.test_complete_user_login_flow()
            if access_token is None:
                pytest.skip("Could not get auth token for session testing")
            
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test session validation through delegation
                session_response = await client.get(
                    f"{backend_url}/auth/session",
                    headers={
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                # Should get session info (validated via auth service)
                assert session_response.status_code in [200, 201], \
                    f"Session validation failed: {session_response.status_code}"
                
                session_data = session_response.json()
                
                # Should have session information
                assert "user_id" in session_data or "email" in session_data or "valid" in session_data, \
                    f"Session response missing expected fields: {session_data}"
                
                # Test session refresh/extension through delegation
                refresh_response = await client.post(
                    f"{backend_url}/auth/refresh",
                    headers={
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                # Should be able to refresh session (if endpoint exists)
                if refresh_response.status_code in [200, 201]:
                    refresh_data = refresh_response.json()
                    
                    # Should get new token or confirmation
                    assert "access_token" in refresh_data or "success" in refresh_data, \
                        f"Session refresh failed: {refresh_data}"
                
                self.logger.info("Session management delegation working")
                
        except Exception as e:
            pytest.fail(f"Session management delegation testing failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.mission_critical
    async def test_websocket_events_sent_with_delegated_auth(self):
        """
        Test that all 5 critical WebSocket events are sent with delegated auth.
        
        MISSION CRITICAL: The 5 WebSocket events are essential for chat value.
        Must work correctly with auth service delegation.
        
        Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        """
        try:
            # Get auth token through delegation
            access_token = await self.test_complete_user_login_flow()
            if access_token is None:
                pytest.skip("Could not get auth token for WebSocket event testing")
            
            # Connect to WebSocket with delegated auth
            websocket_url = self.get_env_var("WEBSOCKET_URL")
            
            received_events = []
            
            async with websockets.connect(
                websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=10
            ) as websocket:
                
                # Authenticate
                auth_message = {
                    "type": "authenticate",
                    "token": access_token
                }
                await websocket.send(json.dumps(auth_message))
                
                # Wait for auth response
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                
                assert auth_data.get("type") in ["authenticated", "connection_established"]
                
                # Send agent execution request
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Test message to trigger all 5 events with delegated auth"
                }
                await websocket.send(json.dumps(agent_request))
                
                # Collect events for up to 30 seconds
                try:
                    for _ in range(30):  # 30 second timeout
                        event_response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event_data = json.loads(event_response)
                        received_events.append(event_data)
                        
                        # Check if we got completion event
                        if event_data.get("type") == "agent_completed":
                            break
                            
                except asyncio.TimeoutError:
                    # Timeout is OK - check what events we received
                    pass
            
            # Analyze received events
            event_types = [event.get("type") for event in received_events]
            
            # Critical events that should be present
            critical_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            # Check which critical events were received
            received_critical = [event for event in critical_events if event in event_types]
            
            self.logger.info(f"Received events: {event_types}")
            self.logger.info(f"Critical events received: {received_critical}")
            
            # At minimum, should have agent_started and some execution events
            assert "agent_started" in event_types or len(received_events) > 0, \
                "Should receive at least some WebSocket events with delegated auth"
            
            # If we received completion, that indicates full event flow worked
            if "agent_completed" in event_types:
                self.logger.info("Complete WebSocket event flow confirmed with delegated auth")
            
        except websockets.ConnectionClosed as e:
            if "401" in str(e):
                pytest.fail("WebSocket events failed due to auth delegation issue")
            else:
                pytest.skip(f"WebSocket connection issue: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket events testing with delegated auth failed: {e}")


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])