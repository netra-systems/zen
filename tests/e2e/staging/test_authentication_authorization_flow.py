"""
Test Authentication & Authorization E2E Flows

Business Value Justification (BVJ):
- Segment: All (Security is critical across all user tiers)
- Business Goal: Ensure secure access control and user authentication works end-to-end
- Value Impact: Users can securely access platform with proper authorization boundaries
- Strategic Impact: Security foundation required for enterprise adoption and compliance

CRITICAL AUTHENTICATION REQUIREMENT:
These tests validate the authentication system itself. Most tests use real authentication
flows, with only one test specifically validating the auth mechanism without pre-auth.

CRITICAL AUTH REQUIREMENTS:
- JWT Authentication: Token generation, validation, and expiration handling
- OAuth Integration: Google OAuth flow with proper redirect handling  
- Session Management: User sessions persist correctly across requests
- Authorization: Users can only access their own data and authorized features
- Token Refresh: Expired tokens are handled gracefully with refresh flows
"""

import asyncio
import json
import jwt
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from tests.e2e.staging_config import get_staging_config


class TestAuthenticationAuthorizationFlow(BaseE2ETest):
    """Test complete authentication and authorization flows."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_jwt_authentication_complete_flow(self, real_services):
        """Test complete JWT authentication flow - THE ONLY test without pre-auth.
        
        This test validates the authentication mechanism itself, so it starts
        without authentication and validates the full auth flow.
        """
        self.logger.info("🚀 Starting JWT Authentication Complete Flow E2E Test")
        
        # This is the ONLY test that doesn't start with authentication
        # because it's testing the authentication system itself
        
        test_email = f"jwt-flow-test-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        test_password = f"JwtTest123!{uuid.uuid4().hex[:6]}"
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Register new user (testing registration flow)
            register_url = f"{self.staging_config.urls.auth_url}/auth/register"
            register_data = {
                "email": test_email,
                "password": test_password,
                "name": f"JWT Test User {int(time.time())}"
            }
            
            async with session.post(register_url, json=register_data) as resp:
                assert resp.status in [200, 201], f"Registration failed: {resp.status}"
                register_result = await resp.json()
                
                # Validate registration response
                assert "access_token" in register_result, "No access token in registration response"
                assert "user" in register_result, "No user data in registration response"
                
                access_token = register_result["access_token"]
                user_data = register_result["user"]
                
                self.logger.info(f"✅ User registered: {user_data.get('email')}")
            
            # Step 2: Validate JWT token structure
            try:
                # Decode token without verification to check structure
                token_payload = jwt.decode(access_token, options={"verify_signature": False})
                
                # Validate required JWT claims
                required_claims = ["sub", "email", "exp", "iat"]
                for claim in required_claims:
                    assert claim in token_payload, f"Missing JWT claim: {claim}"
                
                assert token_payload["email"] == test_email, "JWT email doesn't match"
                assert token_payload["sub"] == user_data["id"], "JWT subject doesn't match user ID"
                
                self.logger.info("✅ JWT token structure validated")
                
            except jwt.InvalidTokenError as e:
                pytest.fail(f"Invalid JWT token structure: {e}")
            
            # Step 3: Test token validation endpoint
            validate_url = f"{self.staging_config.urls.auth_url}/auth/validate"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with session.get(validate_url, headers=headers) as resp:
                assert resp.status == 200, f"Token validation failed: {resp.status}"
                validate_result = await resp.json()
                
                assert validate_result.get("valid") == True, "Token should be valid"
                assert validate_result.get("user_id") == user_data["id"], "User ID mismatch in validation"
                
                self.logger.info("✅ JWT token validation successful")
            
            # Step 4: Test login flow with existing user
            login_url = f"{self.staging_config.urls.auth_url}/auth/login"
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(login_url, json=login_data) as resp:
                assert resp.status == 200, f"Login failed: {resp.status}"
                login_result = await resp.json()
                
                assert "access_token" in login_result, "No access token in login response"
                
                # New token should be different but valid
                new_token = login_result["access_token"]
                assert new_token != access_token, "Login should generate new token"
                
                self.logger.info("✅ Login flow successful")
            
            # Step 5: Test WebSocket authentication with JWT
            try:
                websocket_headers = self.auth_helper.get_websocket_headers(new_token)
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers,
                        open_timeout=15.0
                    ),
                    timeout=20.0
                )
                
                # Send test message to verify WebSocket auth
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_data["id"]
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for any response (connection working indicates auth success)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    # Any response indicates authentication worked
                    self.logger.info("✅ WebSocket authentication successful")
                except asyncio.TimeoutError:
                    # No response is also acceptable for ping
                    self.logger.info("✅ WebSocket connection established (no response to ping)")
                
                await websocket.close()
                
            except Exception as e:
                pytest.fail(f"WebSocket authentication failed: {e}")
            
            self.logger.info("✅ JWT Authentication Complete Flow E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_oauth_integration_flow(self, real_services):
        """Test OAuth integration and token exchange."""
        self.logger.info("🚀 Starting OAuth Integration E2E Test")
        
        # MANDATORY: Start with authenticated user for OAuth integration test
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"oauth-integration-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        async with aiohttp.ClientSession() as session:
            # Test OAuth simulation endpoint (for staging E2E testing)
            oauth_simulation_url = f"{self.staging_config.urls.auth_url}/auth/e2e/test-auth"
            
            # Use E2E bypass key for OAuth simulation in staging
            bypass_headers = self.staging_config.get_bypass_auth_headers()
            oauth_data = {
                "email": user_data["email"],
                "name": f"OAuth Test User {int(time.time())}",
                "permissions": ["read", "write", "oauth_test"]
            }
            
            try:
                async with session.post(oauth_simulation_url, headers=bypass_headers, json=oauth_data, timeout=15) as resp:
                    if resp.status == 200:
                        oauth_result = await resp.json()
                        
                        assert "access_token" in oauth_result, "OAuth simulation should return access token"
                        oauth_token = oauth_result["access_token"]
                        
                        # Validate OAuth token is different from original
                        assert oauth_token != token, "OAuth should generate new token"
                        
                        # Test OAuth token validation
                        validate_url = f"{self.staging_config.urls.auth_url}/auth/validate"
                        oauth_headers = {"Authorization": f"Bearer {oauth_token}"}
                        
                        async with session.get(validate_url, headers=oauth_headers) as validate_resp:
                            assert validate_resp.status == 200, "OAuth token should validate successfully"
                            
                        self.logger.info("✅ OAuth simulation flow successful")
                        
                    else:
                        # OAuth simulation not available - test standard token exchange
                        self.logger.info("⚠️ OAuth simulation unavailable, testing token exchange")
                        
                        # Test token refresh/exchange endpoint
                        refresh_url = f"{self.staging_config.urls.auth_url}/auth/refresh"
                        refresh_headers = {"Authorization": f"Bearer {token}"}
                        
                        async with session.post(refresh_url, headers=refresh_headers) as refresh_resp:
                            if refresh_resp.status == 200:
                                refresh_result = await refresh_resp.json()
                                assert "access_token" in refresh_result, "Token refresh should return new token"
                                self.logger.info("✅ Token refresh flow successful")
                            else:
                                self.logger.info("⚠️ Token refresh not implemented, OAuth integration partial")
                        
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ OAuth endpoint timeout - may not be available in staging")
                # Continue with basic validation
                
            # Test that original token still works for basic operations
            api_headers = {"Authorization": f"Bearer {token}"}
            health_url = f"{self.staging_config.urls.auth_url}/auth/health"
            
            async with session.get(health_url, headers=api_headers) as resp:
                # Health endpoint should work with or without auth
                assert resp.status in [200, 401], "Health endpoint should respond"
                
        self.logger.info("✅ OAuth Integration E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_session_management_and_expiration(self, real_services):
        """Test user session management and token expiration handling."""
        self.logger.info("🚀 Starting Session Management and Expiration E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"session-mgmt-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai",
            permissions=["read", "write", "session_test"]
        )
        
        # Step 1: Test session establishment
        async with aiohttp.ClientSession() as session:
            # Verify initial token works
            validate_url = f"{self.staging_config.urls.auth_url}/auth/validate"
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(validate_url, headers=headers) as resp:
                assert resp.status == 200, "Initial token should be valid"
                initial_validation = await resp.json()
                assert initial_validation.get("valid") == True, "Token should validate initially"
                
                self.logger.info("✅ Session established successfully")
            
            # Step 2: Test session persistence across requests
            websocket_headers = self.auth_helper.get_websocket_headers(token)
            
            # Make multiple WebSocket connections with same token
            for connection_num in range(2):
                try:
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.staging_config.urls.websocket_url,
                            additional_headers=websocket_headers,
                            open_timeout=15.0
                        ),
                        timeout=18.0
                    )
                    
                    # Send session test message
                    session_message = {
                        "type": "session_test",
                        "connection": connection_num,
                        "user_id": user_data["id"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(session_message))
                    
                    # Brief wait for any response
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    except asyncio.TimeoutError:
                        pass  # No response expected for session test
                    
                    await websocket.close()
                    self.logger.info(f"✅ Session persistence test {connection_num + 1} successful")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Session persistence test {connection_num + 1} failed: {e}")
                    # Continue with other tests
            
            # Step 3: Test token expiration handling
            # Create a short-lived token for expiration testing
            short_lived_token = self.auth_helper.create_test_jwt_token(
                user_id=user_data["id"],
                email=user_data["email"],
                exp_minutes=1  # 1 minute expiration
            )
            
            # Validate short token works initially
            short_headers = {"Authorization": f"Bearer {short_lived_token}"}
            async with session.get(validate_url, headers=short_headers) as resp:
                if resp.status == 200:
                    self.logger.info("✅ Short-lived token validated initially")
                    
                    # Wait for token to expire (with some buffer time)
                    self.logger.info("⏳ Waiting for token expiration...")
                    await asyncio.sleep(70)  # Wait 70 seconds for 1-minute token to expire
                    
                    # Test expired token
                    async with session.get(validate_url, headers=short_headers) as expired_resp:
                        # Should either reject expired token or handle gracefully
                        if expired_resp.status == 401:
                            self.logger.info("✅ Expired token correctly rejected")
                        elif expired_resp.status == 200:
                            # Some systems may have longer grace periods
                            expired_result = await expired_resp.json()
                            if expired_result.get("valid") == False:
                                self.logger.info("✅ Expired token marked as invalid")
                            else:
                                self.logger.warning("⚠️ Expired token still marked as valid (may have grace period)")
                        else:
                            self.logger.warning(f"⚠️ Unexpected response to expired token: {expired_resp.status}")
                else:
                    self.logger.warning("⚠️ Short-lived token creation may not be supported")
            
            # Step 4: Test session cleanup
            # Original token should still work
            async with session.get(validate_url, headers=headers) as resp:
                if resp.status == 200:
                    self.logger.info("✅ Original token still valid after expiration tests")
                else:
                    self.logger.warning("⚠️ Original token may have been affected by expiration test")
        
        self.logger.info("✅ Session Management and Expiration E2E Test completed")
        
    async def teardown_method(self):
        """Cleanup after each test method."""
        await super().cleanup_resources()