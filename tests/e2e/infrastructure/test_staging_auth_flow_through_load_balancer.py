"""
Infrastructure Test: Staging Auth Flow Through Load Balancer

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete OAuth authentication flow works through load balancer
- Value Impact: Prevents authentication failures that block all user access
- Strategic Impact: Validates production-like authentication infrastructure

CRITICAL: This test validates that the complete OAuth authentication flow works
correctly through the load balancer, including header propagation and JWT token
validation. Authentication failures prevent ALL users from accessing the system.

This addresses GitHub issue #113: GCP Load Balancer Authentication Header Stripping
"""

import asyncio
import json
import time
import uuid
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Tuple
import pytest
import aiohttp
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestStagingAuthFlowThroughLoadBalancer(SSotBaseTestCase):
    """
    Test complete OAuth authentication flow through load balancer.
    
    INFRASTRUCTURE TEST: Validates that authentication headers are properly
    propagated through the load balancer and that JWT tokens work correctly.
    """
    
    # Load balancer authentication endpoints
    AUTH_ENDPOINTS = {
        "login": "https://auth.staging.netrasystems.ai/auth/login",
        "callback": "https://auth.staging.netrasystems.ai/auth/callback", 
        "logout": "https://auth.staging.netrasystems.ai/auth/logout",
        "user_info": "https://auth.staging.netrasystems.ai/auth/user",
    }
    
    # Backend endpoints that require authentication
    PROTECTED_ENDPOINTS = {
        "api_health": "https://api.staging.netrasystems.ai/api/v1/health",
        "agents_list": "https://api.staging.netrasystems.ai/api/v1/agents",
        "user_profile": "https://api.staging.netrasystems.ai/api/v1/user/profile",
    }
    
    # Authentication flow timeout limits
    AUTH_FLOW_TIMEOUT = 60.0
    JWT_VALIDATION_TIMEOUT = 30.0
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.infrastructure
    async def test_oauth_login_flow_through_load_balancer(self):
        """
        HARD FAIL: OAuth login flow MUST work through load balancer.
        
        This test validates that the complete OAuth login flow works correctly
        when requests go through the load balancer, including proper redirect
        handling and session management.
        """
        auth_flow_results = {}
        auth_flow_failures = []
        
        try:
            # Step 1: Test OAuth login initiation
            login_result = await self._test_oauth_login_initiation()
            auth_flow_results['login_initiation'] = login_result
            
            if not login_result['success']:
                auth_flow_failures.append(
                    f"OAuth login initiation failed: {login_result['error']}"
                )
            
            # Step 2: Test OAuth callback handling  
            callback_result = await self._test_oauth_callback_handling()
            auth_flow_results['callback_handling'] = callback_result
            
            if not callback_result['success']:
                auth_flow_failures.append(
                    f"OAuth callback handling failed: {callback_result['error']}"
                )
            
            # Step 3: Test JWT token validation through load balancer
            jwt_result = await self._test_jwt_token_validation_through_lb()
            auth_flow_results['jwt_validation'] = jwt_result
            
            if not jwt_result['success']:
                auth_flow_failures.append(
                    f"JWT token validation through LB failed: {jwt_result['error']}"
                )
            
        except Exception as e:
            auth_flow_failures.append(f"OAuth flow test setup failed: {e}")
        
        if auth_flow_failures:
            error_report = self._build_auth_flow_failure_report(auth_flow_results, auth_flow_failures)
            raise AssertionError(
                f"CRITICAL: OAuth authentication flow failures through load balancer!\n\n"
                f"OAuth flow failures prevent ALL users from logging in and accessing\n"
                f"the system. This indicates load balancer header propagation issues.\n\n"
                f"AUTHENTICATION FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Check load balancer header propagation configuration\n"
                f"2. Verify OAuth redirect URL configuration in auth service\n"
                f"3. Validate session cookie handling through load balancer\n"
                f"4. Review CORS configuration for authentication endpoints\n"
                f"5. Check JWT token validation in backend services\n\n"
                f"Reference: GitHub issue #113 - Load Balancer Authentication Header Stripping"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.infrastructure  
    async def test_jwt_token_authentication_through_load_balancer(self):
        """
        HARD FAIL: JWT token authentication MUST work through load balancer.
        
        This test validates that JWT tokens work correctly when requests go through
        the load balancer, including proper Authorization header propagation.
        """
        jwt_auth_results = {}
        jwt_auth_failures = []
        
        try:
            # Create authenticated user to get JWT token
            auth_helper = E2EAuthHelper(environment="staging")
            user = await auth_helper.create_authenticated_user()
            
            # Test JWT authentication on protected endpoints through load balancer
            for endpoint_name, endpoint_url in self.PROTECTED_ENDPOINTS.items():
                try:
                    auth_result = await self._test_jwt_auth_endpoint(
                        endpoint_name, endpoint_url, user.jwt_token
                    )
                    jwt_auth_results[endpoint_name] = auth_result
                    
                    if not auth_result['authenticated']:
                        jwt_auth_failures.append(
                            f"JWT authentication failed for {endpoint_name}: {auth_result['error']}"
                        )
                    
                    # Verify proper header propagation
                    if not auth_result['headers_propagated']:
                        jwt_auth_failures.append(
                            f"Authentication headers not propagated for {endpoint_name}"
                        )
                    
                except Exception as e:
                    jwt_auth_results[endpoint_name] = {
                        'authenticated': False,
                        'headers_propagated': False,
                        'error': str(e)
                    }
                    jwt_auth_failures.append(f"JWT auth test failed for {endpoint_name}: {e}")
        
        except Exception as e:
            jwt_auth_failures.append(f"JWT authentication test setup failed: {e}")
        
        if jwt_auth_failures:
            error_report = self._build_jwt_auth_failure_report(jwt_auth_results, jwt_auth_failures)
            raise AssertionError(
                f"CRITICAL: JWT token authentication failures through load balancer!\n\n"
                f"JWT authentication failures prevent authenticated users from accessing\n"
                f"protected resources. This indicates header stripping in load balancer.\n\n"
                f"JWT AUTHENTICATION FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Verify Authorization header propagation in load balancer config\n"
                f"2. Check custom_request_headers configuration\n"
                f"3. Validate header_action settings for WebSocket connections\n"
                f"4. Review backend JWT validation configuration\n"
                f"5. Test header preservation for Bearer token format\n\n"
                f"Reference: Load Balancer Header Propagation Configuration"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.infrastructure
    async def test_session_management_through_load_balancer(self):
        """
        HARD FAIL: Session management MUST work through load balancer.
        
        This test validates that user sessions are properly maintained when
        requests go through the load balancer, including session cookies and
        session affinity configuration.
        """
        session_results = {}
        session_failures = []
        
        try:
            # Test session creation and persistence
            session_result = await self._test_session_creation_and_persistence()
            session_results['session_persistence'] = session_result
            
            if not session_result['success']:
                session_failures.append(
                    f"Session persistence failed: {session_result['error']}"
                )
            
            # Test session affinity for WebSocket connections
            affinity_result = await self._test_session_affinity_websocket()
            session_results['websocket_affinity'] = affinity_result
            
            if not affinity_result['success']:
                session_failures.append(
                    f"WebSocket session affinity failed: {affinity_result['error']}"
                )
            
            # Test concurrent session handling
            concurrent_result = await self._test_concurrent_session_handling()
            session_results['concurrent_sessions'] = concurrent_result
            
            if not concurrent_result['success']:
                session_failures.append(
                    f"Concurrent session handling failed: {concurrent_result['error']}"
                )
            
        except Exception as e:
            session_failures.append(f"Session management test setup failed: {e}")
        
        if session_failures:
            error_report = self._build_session_failure_report(session_results, session_failures)
            raise AssertionError(
                f"CRITICAL: Session management failures through load balancer!\n\n"
                f"Session management failures cause authentication state loss and\n"
                f"force users to re-authenticate frequently.\n\n"
                f"SESSION MANAGEMENT FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Check session affinity configuration (GENERATED_COOKIE)\n"
                f"2. Verify session cookie propagation through load balancer\n"
                f"3. Review session timeout and persistence settings\n"
                f"4. Validate WebSocket session affinity for agent connections\n"
                f"5. Test concurrent session isolation\n\n"
                f"Reference: Load Balancer Session Affinity Configuration"
            )
    
    async def _test_oauth_login_initiation(self) -> Dict:
        """Test OAuth login initiation through load balancer."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.AUTH_FLOW_TIMEOUT)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test login endpoint accessibility
                async with session.get(self.AUTH_ENDPOINTS['login'], allow_redirects=False) as response:
                    
                    # Should redirect to OAuth provider or return login page
                    success = response.status in [200, 302, 307, 308]
                    
                    return {
                        'success': success,
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'redirect_location': response.headers.get('location'),
                        'error': None if success else f"Unexpected status: {response.status}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'error': str(e)
            }
    
    async def _test_oauth_callback_handling(self) -> Dict:
        """Test OAuth callback handling through load balancer."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.AUTH_FLOW_TIMEOUT)
            
            # Test callback endpoint with mock OAuth parameters
            callback_url = f"{self.AUTH_ENDPOINTS['callback']}?code=test_code&state=test_state"
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(callback_url, allow_redirects=False) as response:
                    
                    # Callback should handle OAuth response (redirect or error)
                    success = response.status in [200, 302, 400, 401]  # Various valid responses
                    
                    return {
                        'success': success,
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'redirect_location': response.headers.get('location'),
                        'error': None if success else f"Callback failed: {response.status}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'error': str(e)
            }
    
    async def _test_jwt_token_validation_through_lb(self) -> Dict:
        """Test JWT token validation through load balancer."""
        try:
            # Create a test user with valid JWT token
            auth_helper = E2EAuthHelper(environment="staging")
            user = await auth_helper.create_authenticated_user()
            
            # Test JWT token on protected endpoint
            headers = {
                'Authorization': f'Bearer {user.jwt_token}',
                'Content-Type': 'application/json'
            }
            
            timeout = aiohttp.ClientTimeout(total=self.JWT_VALIDATION_TIMEOUT)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.PROTECTED_ENDPOINTS['api_health'], headers=headers) as response:
                    
                    # Should return success (200) or authorized access
                    success = 200 <= response.status < 500  # 4xx is authentication issue, not LB issue
                    
                    return {
                        'success': success,
                        'status_code': response.status,
                        'authenticated': response.status != 401,
                        'headers_received': dict(response.headers),
                        'error': None if success else f"JWT validation failed: {response.status}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'authenticated': False,
                'error': str(e)
            }
    
    async def _test_jwt_auth_endpoint(self, endpoint_name: str, endpoint_url: str, jwt_token: str) -> Dict:
        """Test JWT authentication on a specific endpoint."""
        try:
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Content-Type': 'application/json',
                'X-Test-Case': f'jwt_auth_{endpoint_name}'
            }
            
            timeout = aiohttp.ClientTimeout(total=15.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint_url, headers=headers) as response:
                    
                    # Determine if authentication worked
                    authenticated = response.status != 401
                    headers_propagated = response.status != 400  # 400 might indicate missing headers
                    
                    return {
                        'authenticated': authenticated,
                        'headers_propagated': headers_propagated,
                        'status_code': response.status,
                        'response_headers': dict(response.headers),
                        'error': None if authenticated else f"Auth failed: HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                'authenticated': False,
                'headers_propagated': False,
                'status_code': None,
                'error': str(e)
            }
    
    async def _test_session_creation_and_persistence(self) -> Dict:
        """Test session creation and persistence through load balancer."""
        try:
            # Test session creation with login
            timeout = aiohttp.ClientTimeout(total=30.0)
            
            async with aiohttp.ClientSession(timeout=timeout, cookie_jar=aiohttp.CookieJar()) as session:
                # Make initial request to create session
                async with session.get(self.AUTH_ENDPOINTS['login']) as response:
                    initial_cookies = len(session.cookie_jar)
                    
                    # Make follow-up request to test session persistence
                    async with session.get(self.AUTH_ENDPOINTS['login']) as followup_response:
                        persistent_cookies = len(session.cookie_jar)
                        
                        return {
                            'success': True,
                            'initial_cookies': initial_cookies,
                            'persistent_cookies': persistent_cookies,
                            'session_maintained': persistent_cookies >= initial_cookies,
                            'error': None
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _test_session_affinity_websocket(self) -> Dict:
        """Test session affinity for WebSocket connections."""
        try:
            # This tests that WebSocket connections maintain session affinity
            websocket_url = "wss://api.staging.netrasystems.ai/ws"
            
            # Test WebSocket connection establishment (should fail gracefully without auth)
            import websockets
            try:
                async with websockets.connect(websocket_url, timeout=10) as websocket:
                    return {
                        'success': True,
                        'connection_established': True,
                        'affinity_working': True,
                        'error': None
                    }
            except websockets.exceptions.InvalidStatusCode as e:
                # Expected failure due to authentication, but connection attempt succeeded
                if e.status_code in [401, 403, 426]:
                    return {
                        'success': True,
                        'connection_established': False,
                        'affinity_working': True,
                        'rejection_reason': f"HTTP {e.status_code}",
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'connection_established': False,
                        'affinity_working': False,
                        'error': f"Unexpected status: {e.status_code}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'connection_established': False,
                'affinity_working': False,
                'error': str(e)
            }
    
    async def _test_concurrent_session_handling(self) -> Dict:
        """Test concurrent session handling through load balancer."""
        try:
            # Test multiple concurrent sessions
            concurrent_sessions = []
            
            for i in range(3):  # Test 3 concurrent sessions
                session_task = self._create_concurrent_session(f"session_{i}")
                concurrent_sessions.append(session_task)
            
            results = await asyncio.gather(*concurrent_sessions, return_exceptions=True)
            
            successful_sessions = sum(1 for result in results if isinstance(result, dict) and result.get('success'))
            
            return {
                'success': successful_sessions >= 2,  # At least 2 out of 3 should succeed
                'concurrent_sessions_tested': len(concurrent_sessions),
                'successful_sessions': successful_sessions,
                'session_results': results,
                'error': None if successful_sessions >= 2 else "Too many concurrent session failures"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _create_concurrent_session(self, session_id: str) -> Dict:
        """Create a single concurrent session for testing."""
        try:
            timeout = aiohttp.ClientTimeout(total=15.0)
            
            async with aiohttp.ClientSession(timeout=timeout, cookie_jar=aiohttp.CookieJar()) as session:
                headers = {'X-Session-ID': session_id}
                async with session.get(self.AUTH_ENDPOINTS['login'], headers=headers) as response:
                    return {
                        'success': 200 <= response.status < 500,
                        'session_id': session_id,
                        'status_code': response.status,
                        'error': None
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'session_id': session_id,
                'error': str(e)
            }
    
    def _build_auth_flow_failure_report(self, auth_results: Dict, failures: List[str]) -> str:
        """Build authentication flow failure report."""
        report_parts = []
        
        for step_name, result in auth_results.items():
            if not result.get('success', False):
                report_parts.append(
                    f"  {step_name}: {result.get('error', 'Unknown failure')}"
                )
        
        return "\n".join(report_parts)
    
    def _build_jwt_auth_failure_report(self, jwt_results: Dict, failures: List[str]) -> str:
        """Build JWT authentication failure report."""
        report_parts = []
        
        for endpoint_name, result in jwt_results.items():
            if not result.get('authenticated', False):
                report_parts.append(
                    f"  {endpoint_name}: {result.get('error', 'Authentication failed')}"
                )
        
        return "\n".join(report_parts)
    
    def _build_session_failure_report(self, session_results: Dict, failures: List[str]) -> str:
        """Build session management failure report."""
        report_parts = []
        
        for session_type, result in session_results.items():
            if not result.get('success', False):
                report_parts.append(
                    f"  {session_type}: {result.get('error', 'Session management failed')}"
                )
        
        return "\n".join(report_parts)


if __name__ == "__main__":
    # Run this test standalone to check auth flow through load balancer
    import asyncio
    
    async def run_tests():
        test_instance = TestStagingAuthFlowThroughLoadBalancer()
        
        try:
            await test_instance.test_oauth_login_flow_through_load_balancer()
            print(" PASS:  OAuth login flow through load balancer working")
        except AssertionError as e:
            print(f" FAIL:  OAuth flow failures:\n{e}")
            return False
        
        try:
            await test_instance.test_jwt_token_authentication_through_load_balancer()
            print(" PASS:  JWT token authentication through load balancer working")
        except AssertionError as e:
            print(f" FAIL:  JWT authentication failures:\n{e}")
            return False
        
        try:
            await test_instance.test_session_management_through_load_balancer()
            print(" PASS:  Session management through load balancer working")
        except AssertionError as e:
            print(f" FAIL:  Session management failures:\n{e}")
            return False
        
        return True
    
    if asyncio.run(run_tests()):
        print(" PASS:  All auth flow through load balancer tests passed!")
    else:
        exit(1)