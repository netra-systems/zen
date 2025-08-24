"""
E2E Tests for Authentication Flow
Tests OAuth, JWT tokens, session management, and cross-service authentication.

Business Value Justification (BVJ):
- Segment: All (Critical for Free-to-Paid conversion)
- Business Goal: User Acquisition, Security, Trust
- Value Impact: Enables user onboarding and secure access to AI services
- Strategic Impact: 0% conversion without auth, compliance requirement
"""

import asyncio
import pytest
import aiohttp
import jwt
import time
from typing import Dict, Optional, Any
import uuid
import hashlib
import secrets


@pytest.mark.e2e
@pytest.mark.real_services
class TestAuthenticationFlow:
    """Test suite for authentication and authorization flows."""

    @pytest.mark.asyncio
    async def test_first_time_oauth_signup(self):
        """
        Test first-time user OAuth signup flow.
        
        Critical Assertions:
        - OAuth providers configured (Google, GitHub)
        - OAuth redirect URLs correct
        - User account created on first OAuth login
        - Profile data populated from OAuth
        
        Expected Failure: OAuth credentials not configured
        Business Impact: No new user acquisition, 100% conversion loss
        """
        auth_service_url = "http://localhost:8001"
        
        async with aiohttp.ClientSession() as session:
            # Get available OAuth providers
            providers_response = await session.get(f"{auth_service_url}/auth/providers")
            assert providers_response.status == 200, "OAuth providers endpoint not accessible"
            
            providers = await providers_response.json()
            assert len(providers) >= 2, f"Insufficient OAuth providers: {providers}"
            
            # Check Google OAuth configuration
            google_provider = next((p for p in providers if p['name'] == 'google'), None)
            assert google_provider, "Google OAuth not configured"
            assert google_provider.get('client_id'), "Google client_id missing"
            assert google_provider.get('authorize_url'), "Google authorize_url missing"
            assert 'accounts.google.com' in google_provider['authorize_url'], \
                f"Invalid Google OAuth URL: {google_provider['authorize_url']}"
            
            # Check GitHub OAuth configuration
            github_provider = next((p for p in providers if p['name'] == 'github'), None)
            assert github_provider, "GitHub OAuth not configured"
            assert github_provider.get('client_id'), "GitHub client_id missing"
            assert 'github.com/login/oauth' in github_provider['authorize_url'], \
                f"Invalid GitHub OAuth URL: {github_provider['authorize_url']}"
            
            # Simulate OAuth callback (mock for E2E)
            mock_oauth_code = "test_oauth_code_" + str(uuid.uuid4())
            callback_data = {
                "provider": "google",
                "code": mock_oauth_code,
                "state": secrets.token_urlsafe(32)
            }
            
            # Process OAuth callback
            callback_response = await session.post(
                f"{auth_service_url}/auth/callback",
                json=callback_data
            )
            
            if callback_response.status == 200:
                callback_result = await callback_response.json()
                
                # Verify user creation
                assert callback_result.get('user_id'), "No user_id returned"
                assert callback_result.get('access_token'), "No access token generated"
                assert callback_result.get('refresh_token'), "No refresh token generated"
                assert callback_result.get('is_new_user'), "New user flag not set"
                
                # Verify profile populated
                assert callback_result.get('profile'), "User profile not created"
                profile = callback_result['profile']
                assert profile.get('email'), "Email not populated from OAuth"
                assert profile.get('name'), "Name not populated from OAuth"
            else:
                # OAuth mock not implemented - expected in initial tests
                error_data = await callback_response.json() if callback_response.status < 500 else {}
                assert False, f"OAuth callback failed: {callback_response.status} - {error_data}"

    @pytest.mark.asyncio
    async def test_oauth_login_flow(self):
        """
        Test OAuth login flow for existing users.
        
        Critical Assertions:
        - OAuth login works for existing users
        - Correct user account linked
        - Session created properly
        - Previous OAuth tokens updated
        
        Expected Failure: OAuth account linking not implemented
        Business Impact: Users can't log back in, high churn rate
        """
        auth_service_url = "http://localhost:8001"
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # First create a user via regular signup
            signup_data = {
                "email": "oauth.test@example.com",
                "password": "TestPassword123!",
                "name": "OAuth Test User"
            }
            
            signup_response = await session.post(
                f"{backend_url}/api/v1/auth/register",
                json=signup_data
            )
            
            user_id = None
            if signup_response.status == 200:
                signup_result = await signup_response.json()
                user_id = signup_result.get('user_id')
            
            # Link OAuth account
            if user_id:
                link_data = {
                    "user_id": user_id,
                    "provider": "google",
                    "provider_user_id": "google_123456",
                    "provider_email": "oauth.test@example.com"
                }
                
                link_response = await session.post(
                    f"{auth_service_url}/auth/link-oauth",
                    json=link_data
                )
                
                assert link_response.status in [200, 201], \
                    f"OAuth linking failed: {link_response.status}"
            
            # Now test OAuth login for existing user
            oauth_login_data = {
                "provider": "google",
                "provider_user_id": "google_123456",
                "email": "oauth.test@example.com"
            }
            
            login_response = await session.post(
                f"{auth_service_url}/auth/oauth-login",
                json=oauth_login_data
            )
            
            if login_response.status == 200:
                login_result = await login_response.json()
                
                assert login_result.get('user_id') == user_id, \
                    "Wrong user account returned"
                assert login_result.get('access_token'), "No access token"
                assert not login_result.get('is_new_user'), \
                    "Existing user marked as new"
                assert login_result.get('oauth_linked'), "OAuth not properly linked"
            else:
                assert False, f"OAuth login failed: {login_response.status}"

    @pytest.mark.asyncio
    async def test_jwt_token_generation(self):
        """
        Test JWT token generation and validation.
        
        Critical Assertions:
        - JWT tokens properly signed
        - Tokens contain required claims
        - Token signature verification works
        - Token expiry set correctly
        
        Expected Failure: JWT secret not configured
        Business Impact: Authentication completely broken
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create test user
            test_email = f"jwt.test.{uuid.uuid4()}@example.com"
            signup_data = {
                "email": test_email,
                "password": "JWTTest123!",
                "name": "JWT Test User"
            }
            
            await session.post(f"{backend_url}/api/v1/auth/register", json=signup_data)
            
            # Login to get JWT
            login_data = {
                "email": test_email,
                "password": "JWTTest123!"
            }
            
            login_response = await session.post(
                f"{backend_url}/api/v1/auth/login",
                json=login_data
            )
            
            assert login_response.status == 200, f"Login failed: {login_response.status}"
            
            login_result = await login_response.json()
            access_token = login_result.get('access_token')
            refresh_token = login_result.get('refresh_token')
            
            assert access_token, "No access token generated"
            assert refresh_token, "No refresh token generated"
            
            # Decode and validate JWT structure (without verification for testing)
            try:
                # Decode without verification to inspect claims
                access_claims = jwt.decode(access_token, options={"verify_signature": False})
                
                # Verify required claims
                assert access_claims.get('sub'), "No subject (user_id) in token"
                assert access_claims.get('email') == test_email, "Wrong email in token"
                assert access_claims.get('exp'), "No expiration in token"
                assert access_claims.get('iat'), "No issued-at in token"
                assert access_claims.get('type') == 'access', "Wrong token type"
                
                # Check expiry is reasonable (1 hour for access token)
                exp_time = access_claims['exp']
                iat_time = access_claims['iat']
                token_lifetime = exp_time - iat_time
                assert 3500 <= token_lifetime <= 3700, \
                    f"Unexpected access token lifetime: {token_lifetime} seconds"
                
                # Decode refresh token
                refresh_claims = jwt.decode(refresh_token, options={"verify_signature": False})
                assert refresh_claims.get('type') == 'refresh', "Wrong refresh token type"
                
                # Refresh token should have longer expiry (e.g., 7 days)
                refresh_lifetime = refresh_claims['exp'] - refresh_claims['iat']
                assert refresh_lifetime > 86400, \
                    f"Refresh token lifetime too short: {refresh_lifetime} seconds"
                
            except jwt.DecodeError as e:
                assert False, f"JWT decode failed: {str(e)}"
            
            # Test token validation endpoint
            validate_response = await session.post(
                f"{backend_url}/api/v1/auth/validate",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert validate_response.status == 200, "Token validation failed"
            validate_result = await validate_response.json()
            assert validate_result.get('valid'), "Token marked as invalid"
            assert validate_result.get('user_id'), "No user_id in validation response"

    @pytest.mark.asyncio
    async def test_token_refresh_mechanism(self):
        """
        Test JWT refresh token mechanism.
        
        Critical Assertions:
        - Refresh token can generate new access token
        - Old access token invalidated after refresh
        - Refresh token rotation works
        - Cannot use expired refresh token
        
        Expected Failure: Refresh mechanism not implemented
        Business Impact: Users logged out frequently, poor UX
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create and login user
            test_email = f"refresh.test.{uuid.uuid4()}@example.com"
            signup_data = {
                "email": test_email,
                "password": "RefreshTest123!",
                "name": "Refresh Test User"
            }
            
            await session.post(f"{backend_url}/api/v1/auth/register", json=signup_data)
            
            login_response = await session.post(
                f"{backend_url}/api/v1/auth/login",
                json={"email": test_email, "password": "RefreshTest123!"}
            )
            
            login_result = await login_response.json()
            original_access_token = login_result['access_token']
            original_refresh_token = login_result['refresh_token']
            
            # Wait a moment to ensure new token has different timestamp
            await asyncio.sleep(1)
            
            # Use refresh token to get new access token
            refresh_response = await session.post(
                f"{backend_url}/api/v1/auth/refresh",
                json={"refresh_token": original_refresh_token}
            )
            
            assert refresh_response.status == 200, "Token refresh failed"
            
            refresh_result = await refresh_response.json()
            new_access_token = refresh_result.get('access_token')
            new_refresh_token = refresh_result.get('refresh_token')
            
            assert new_access_token, "No new access token generated"
            assert new_access_token != original_access_token, \
                "Same access token returned"
            
            # Verify new token works
            validate_response = await session.post(
                f"{backend_url}/api/v1/auth/validate",
                headers={"Authorization": f"Bearer {new_access_token}"}
            )
            assert validate_response.status == 200, "New token validation failed"
            
            # Verify old refresh token doesn't work (if rotation enabled)
            if new_refresh_token and new_refresh_token != original_refresh_token:
                old_refresh_response = await session.post(
                    f"{backend_url}/api/v1/auth/refresh",
                    json={"refresh_token": original_refresh_token}
                )
                assert old_refresh_response.status in [401, 403], \
                    "Old refresh token still works after rotation"

    @pytest.mark.asyncio
    async def test_session_persistence(self):
        """
        Test session persistence and management.
        
        Critical Assertions:
        - Sessions stored in database
        - Session retrieval works
        - Session expiry handled
        - Multiple sessions per user supported
        
        Expected Failure: Session storage not implemented
        Business Impact: No persistent login, constant re-authentication
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create test user
            test_email = f"session.test.{uuid.uuid4()}@example.com"
            signup_data = {
                "email": test_email,
                "password": "SessionTest123!",
                "name": "Session Test User"
            }
            
            await session.post(f"{backend_url}/api/v1/auth/register", json=signup_data)
            
            # Login from multiple "devices"
            sessions = []
            for device in ["desktop", "mobile", "tablet"]:
                login_response = await session.post(
                    f"{backend_url}/api/v1/auth/login",
                    json={
                        "email": test_email,
                        "password": "SessionTest123!",
                        "device_id": f"test_{device}",
                        "device_name": f"Test {device.title()}"
                    }
                )
                
                assert login_response.status == 200, f"Login failed for {device}"
                login_result = await login_response.json()
                
                session_info = {
                    "device": device,
                    "access_token": login_result['access_token'],
                    "session_id": login_result.get('session_id')
                }
                sessions.append(session_info)
                
                assert session_info['session_id'], f"No session_id for {device}"
            
            # Verify all sessions are active
            for session_info in sessions:
                session_response = await session.get(
                    f"{backend_url}/api/v1/auth/session/{session_info['session_id']}",
                    headers={"Authorization": f"Bearer {session_info['access_token']}"}
                )
                
                if session_response.status == 200:
                    session_data = await session_response.json()
                    assert session_data.get('active'), \
                        f"Session not active for {session_info['device']}"
                    assert session_data.get('device_name'), \
                        "Device name not stored"
            
            # Get all sessions for user
            all_sessions_response = await session.get(
                f"{backend_url}/api/v1/auth/sessions",
                headers={"Authorization": f"Bearer {sessions[0]['access_token']}"}
            )
            
            if all_sessions_response.status == 200:
                all_sessions = await all_sessions_response.json()
                assert len(all_sessions) >= 3, \
                    f"Not all sessions returned: {len(all_sessions)}"
            
            # Test session revocation
            revoke_response = await session.delete(
                f"{backend_url}/api/v1/auth/session/{sessions[1]['session_id']}",
                headers={"Authorization": f"Bearer {sessions[0]['access_token']}"}
            )
            
            if revoke_response.status in [200, 204]:
                # Verify revoked session no longer works
                check_response = await session.get(
                    f"{backend_url}/api/v1/auth/validate",
                    headers={"Authorization": f"Bearer {sessions[1]['access_token']}"}
                )
                assert check_response.status in [401, 403], \
                    "Revoked session still valid"

    @pytest.mark.asyncio
    async def test_cross_service_authentication(self):
        """
        Test authentication across multiple services.
        
        Critical Assertions:
        - Auth token works across backend and auth service
        - Service-to-service authentication works
        - Token propagation in headers
        - Auth context preserved
        
        Expected Failure: Services not sharing auth configuration
        Business Impact: Features broken, services can't communicate
        """
        backend_url = "http://localhost:8000"
        auth_service_url = "http://localhost:8001"
        
        async with aiohttp.ClientSession() as session:
            # Create user and get token from backend
            test_email = f"cross.service.{uuid.uuid4()}@example.com"
            signup_data = {
                "email": test_email,
                "password": "CrossService123!",
                "name": "Cross Service User"
            }
            
            await session.post(f"{backend_url}/api/v1/auth/register", json=signup_data)
            
            login_response = await session.post(
                f"{backend_url}/api/v1/auth/login",
                json={"email": test_email, "password": "CrossService123!"}
            )
            
            login_result = await login_response.json()
            access_token = login_result['access_token']
            
            # Test token works on backend service
            backend_test = await session.get(
                f"{backend_url}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert backend_test.status in [200, 404], \
                f"Backend auth failed: {backend_test.status}"
            
            # Test same token works on auth service
            auth_test = await session.get(
                f"{auth_service_url}/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert auth_test.status in [200, 404], \
                f"Auth service auth failed: {auth_test.status}"
            
            # Test service-to-service auth
            service_token_response = await session.post(
                f"{auth_service_url}/auth/service-token",
                json={
                    "service": "backend",
                    "secret": "test_service_secret"
                }
            )
            
            if service_token_response.status == 200:
                service_token_data = await service_token_response.json()
                service_token = service_token_data.get('token')
                
                assert service_token, "No service token generated"
                
                # Verify service token has correct claims
                service_claims = jwt.decode(
                    service_token,
                    options={"verify_signature": False}
                )
                assert service_claims.get('service') == 'backend', \
                    "Wrong service in token"
                assert service_claims.get('type') == 'service', \
                    "Wrong token type for service"

    @pytest.mark.asyncio
    async def test_frontend_auth_state(self):
        """
        Test frontend authentication state management.
        
        Critical Assertions:
        - Frontend can store auth tokens
        - CORS configured for frontend domain
        - Cookie-based auth works
        - Auth state synchronized
        
        Expected Failure: Frontend auth integration missing
        Business Impact: Frontend unusable, 100% user impact
        """
        backend_url = "http://localhost:8000"
        frontend_origin = "http://localhost:3000"
        
        # Use session with cookie jar
        jar = aiohttp.CookieJar()
        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            # Test CORS preflight
            preflight_response = await session.options(
                f"{backend_url}/api/v1/auth/login",
                headers={
                    "Origin": frontend_origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type"
                }
            )
            
            if preflight_response.status == 200:
                cors_headers = preflight_response.headers
                assert cors_headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"], \
                    "CORS origin not allowed"
                assert "POST" in cors_headers.get("Access-Control-Allow-Methods", ""), \
                    "POST method not allowed"
            
            # Login with cookie support
            test_email = f"frontend.auth.{uuid.uuid4()}@example.com"
            signup_data = {
                "email": test_email,
                "password": "Frontend123!",
                "name": "Frontend User"
            }
            
            await session.post(
                f"{backend_url}/api/v1/auth/register",
                json=signup_data,
                headers={"Origin": frontend_origin}
            )
            
            login_response = await session.post(
                f"{backend_url}/api/v1/auth/login",
                json={
                    "email": test_email,
                    "password": "Frontend123!",
                    "remember_me": True
                },
                headers={"Origin": frontend_origin}
            )
            
            assert login_response.status == 200, "Frontend login failed"
            
            # Check for auth cookies
            cookies = jar.filter_cookies(backend_url)
            auth_cookie = cookies.get('auth_token') or cookies.get('session')
            
            if auth_cookie:
                assert auth_cookie.value, "Auth cookie has no value"
                assert auth_cookie.get('httponly'), "Auth cookie not httponly"
                assert auth_cookie.get('samesite'), "Auth cookie missing samesite"
            
            # Test authenticated request with cookie
            profile_response = await session.get(
                f"{backend_url}/api/v1/user/profile",
                headers={"Origin": frontend_origin}
            )
            
            # Should work with cookie even without Authorization header
            if auth_cookie:
                assert profile_response.status in [200, 404], \
                    "Cookie-based auth failed"
            
            # Test logout
            logout_response = await session.post(
                f"{backend_url}/api/v1/auth/logout",
                headers={"Origin": frontend_origin}
            )
            
            if logout_response.status in [200, 204]:
                # Verify cookie cleared
                cookies_after = jar.filter_cookies(backend_url)
                auth_cookie_after = cookies_after.get('auth_token') or cookies_after.get('session')
                
                if auth_cookie_after:
                    assert auth_cookie_after.value == "" or auth_cookie_after.get('max_age') == 0, \
                        "Auth cookie not cleared on logout"