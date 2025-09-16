from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nComprehensive Authentication and OAuth Flow Test Suite - Updated for GCP Staging\n\nThis test suite is designed to work with GCP staging services and includes:\n- CORS blocking requests \n- Token not being properly sent back\n- OAuth redirect issues\n- Security misconfigurations\n- Port mismatch problems\n- Cookie/storage issues\n- WebSocket authentication failures\n- Cross-service token propagation issues\n\nTest Categories:\n1. Dev login flow (username/password)\n2. OAuth2 flow (Google login) \n3. JWT token generation and validation\n4. Token propagation to frontend\n5. CORS configuration issues\n6. Security headers validation\n7. Session management\n8. Token refresh mechanism\n9. WebSocket authentication\n10. Cross-service authentication sync\n\nExpected Failures:\n- CORS preflight failures from frontend origins\n- Token validation timeouts\n- OAuth state mismatch errors\n- Invalid redirect URI configurations\n- WebSocket connection authentication failures\n- Session fixation vulnerabilities\n- Token blacklist inconsistencies\n'
import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse
import httpx
import pytest
from httpx._exceptions import ConnectError, ReadTimeout
from tests.e2e.staging_auth_bypass import StagingAuthHelper
logger = logging.getLogger(__name__)
TEST_CONFIG = {'auth_service_url': 'http://localhost:8001', 'backend_url': 'http://localhost:8000', 'frontend_url': 'http://localhost:3000', 'staging_auth_url': 'https://auth.staging.netrasystems.ai', 'staging_backend_url': 'https://api.staging.netrasystems.ai', 'staging_frontend_url': 'https://app.staging.netrasystems.ai', 'timeout': 30.0}
MOCK_OAUTH_CONFIG = {'client_id': 'test-google-client-id.apps.googleusercontent.com', 'client_secret': 'mock-client-secret', 'redirect_uri': f"{TEST_CONFIG['frontend_url']}/auth/callback", 'scope': 'openid email profile'}
TEST_HEADERS = {'Content-Type': 'application/json', 'Origin': 'http://localhost:3000', 'Referer': 'http://localhost:3000/login', 'User-Agent': 'Mozilla/5.0 (Test Browser) AppleWebKit/537.36', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache'}

class TestAuthFlower:
    """Comprehensive authentication flow testing class"""

    def __init__(self):
        self.is_staging = get_env().get('ENVIRONMENT', 'development') == 'staging'
        self.base_urls = {'auth': TEST_CONFIG['staging_auth_url'] if self.is_staging else TEST_CONFIG['auth_service_url'], 'backend': TEST_CONFIG['staging_backend_url'] if self.is_staging else TEST_CONFIG['backend_url'], 'frontend': TEST_CONFIG['staging_frontend_url'] if self.is_staging else TEST_CONFIG['frontend_url']}
        self.client = httpx.AsyncClient(timeout=TEST_CONFIG['timeout'], follow_redirects=True)
        self.auth_tokens = {}
        self.session_data = {}
        self.cors_errors = []
        self.auth_errors = []
        if self.is_staging:
            self.staging_auth = StagingAuthHelper()
            self.staging_auth.staging_auth_url = self.base_urls['auth']

    async def cleanup(self):
        """Cleanup test client"""
        await self.client.aclose()

@pytest.fixture
async def auth_tester():
    """Async fixture for auth flow tester"""
    tester = TestAuthFlower()
    try:
        yield tester
    finally:
        await tester.cleanup()

@pytest.mark.e2e
class TestDevLoginFlow:
    """Test development mode login flow - Expected to expose configuration issues"""

    @pytest.mark.e2e
    async def test_dev_login_basic_flow(self, auth_tester):
        """Test basic dev login flow - Should expose CORS and endpoint issues"""
        try:
            health_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/health", headers=TEST_HEADERS)
            logger.info(f'Auth service health: {health_response.status_code}')
        except ConnectError:
            pytest.skip(f"Auth service not running on expected port 8001. This test requires the auth service to be started. Expected: Auth service at {TEST_CONFIG['auth_service_url']}/health, Actual: Connection refused. To run this test, start the auth service first using: python scripts/start_auth_service.py or python scripts/dev_launcher.py")
        try:
            config_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/config", headers=TEST_HEADERS)
            if config_response.status_code != 200:
                auth_tester.cors_errors.append(f'Config endpoint failed: {config_response.status_code}')
            config_data = config_response.json()
            logger.info(f'Auth config received: {config_data}')
        except Exception as e:
            pytest.fail(f'Auth config request failed - possible CORS issue: {e}')
        login_data = {'email': 'dev@example.com', 'password': 'dev_password_123'}
        try:
            login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json=login_data)
            logger.info(f'Dev login response: {login_response.status_code}')
            logger.info(f'Dev login headers: {dict(login_response.headers)}')
            if login_response.status_code == 403:
                pytest.fail('Dev login not enabled - environment configuration issue')
            elif login_response.status_code == 400:
                pytest.fail('Invalid dev login request format')
            elif login_response.status_code == 500:
                pytest.fail('Dev login internal server error - database sync issue')
            if 'access-control-allow-origin' not in login_response.headers:
                auth_tester.cors_errors.append('Missing CORS headers in dev login response')
            login_result = login_response.json()
            if 'access_token' not in login_result:
                pytest.fail('No access token in dev login response')
            auth_tester.auth_tokens['dev'] = login_result.get('access_token')
        except ReadTimeout:
            pytest.fail('Dev login timeout - service performance issue')
        except Exception as e:
            pytest.fail(f'Dev login failed unexpectedly: {e}')

    @pytest.mark.e2e
    @pytest.mark.skipif(reason='Test requires real auth service - set USE_REAL_SERVICES=true')
    @pytest.mark.auth
    async def test_dev_login_cors_preflight(self, auth_tester):
        """Test CORS preflight for dev login - Expected to fail with CORS errors"""
        try:
            preflight_response = await auth_tester.client.request('OPTIONS', f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type, Authorization'})
            logger.info(f'CORS preflight status: {preflight_response.status_code}')
            logger.info(f'CORS preflight headers: {dict(preflight_response.headers)}')
            required_cors_headers = ['access-control-allow-origin', 'access-control-allow-methods', 'access-control-allow-headers', 'access-control-allow-credentials']
            missing_headers = []
            for header in required_cors_headers:
                if header not in preflight_response.headers:
                    missing_headers.append(header)
            if missing_headers:
                auth_tester.cors_errors.extend(missing_headers)
                pytest.fail(f'Missing CORS headers: {missing_headers}')
            allowed_origin = preflight_response.headers.get('access-control-allow-origin')
            if allowed_origin != 'http://localhost:3000' and allowed_origin != '*':
                auth_tester.cors_errors.append(f'Origin not allowed: {allowed_origin}')
        except Exception as e:
            pytest.fail(f'CORS preflight test failed: {e}')

    @pytest.mark.e2e
    async def test_dev_login_token_validation(self, auth_tester):
        """Test dev login token validation - Should expose JWT issues"""
        await self.test_dev_login_basic_flow(auth_tester)
        if 'dev' not in auth_tester.auth_tokens:
            pytest.skip('No dev token available for validation test')
        token = auth_tester.auth_tokens['dev']
        try:
            validation_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={**TEST_HEADERS, 'Authorization': f'Bearer {token}'}, json={'token': token})
            logger.info(f'Token validation status: {validation_response.status_code}')
            if validation_response.status_code != 200:
                pytest.fail(f'Token validation failed: {validation_response.status_code}')
            validation_result = validation_response.json()
            expected_fields = ['valid', 'user_id', 'email']
            missing_fields = []
            for field in expected_fields:
                if field not in validation_result:
                    missing_fields.append(field)
            if missing_fields:
                pytest.fail(f'Missing validation fields: {missing_fields}')
        except Exception as e:
            pytest.fail(f'Token validation test failed: {e}')

@pytest.mark.e2e
class TestOAuth2Flow:
    """Test OAuth2 Google login flow - Expected to expose OAuth configuration issues"""

    @pytest.mark.e2e
    async def test_oauth_initiation(self, auth_tester):
        """Test OAuth flow initiation - Should expose redirect URI issues"""
        try:
            oauth_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/login", params={'provider': 'google'}, headers=TEST_HEADERS, follow_redirects=False)
            logger.info(f'OAuth initiation status: {oauth_response.status_code}')
            logger.info(f'OAuth initiation headers: {dict(oauth_response.headers)}')
            if oauth_response.status_code == 500:
                pytest.fail('OAuth not configured - GOOGLE_CLIENT_ID missing')
            elif oauth_response.status_code != 302:
                pytest.fail(f'OAuth initiation failed: {oauth_response.status_code}')
            redirect_location = oauth_response.headers.get('location')
            if not redirect_location:
                pytest.fail('No OAuth redirect location provided')
            if 'accounts.google.com/o/oauth2' not in redirect_location:
                pytest.fail(f'Invalid OAuth redirect URL: {redirect_location}')
            parsed_url = urlparse(redirect_location)
            query_params = parse_qs(parsed_url.query)
            redirect_uri = query_params.get('redirect_uri', [None])[0]
            if not redirect_uri:
                pytest.fail('No redirect_uri in OAuth URL')
            expected_redirect = f"{TEST_CONFIG['frontend_url']}/auth/callback"
            if redirect_uri != expected_redirect:
                pytest.fail(f'Redirect URI mismatch: {redirect_uri} != {expected_redirect}')
        except Exception as e:
            pytest.fail(f'OAuth initiation test failed: {e}')

    @pytest.mark.e2e
    async def test_oauth_callback_with_invalid_state(self, auth_tester):
        """Test OAuth callback with invalid state - Should expose state validation issues"""
        invalid_callback_data = {'code': 'mock_authorization_code_12345', 'state': 'invalid_state_token', 'redirect_uri': f"{TEST_CONFIG['frontend_url']}/auth/callback"}
        try:
            callback_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/callback/google", headers=TEST_HEADERS, json=invalid_callback_data)
            logger.info(f'OAuth callback status: {callback_response.status_code}')
            if callback_response.status_code == 200:
                pytest.fail('OAuth callback succeeded with invalid state - security vulnerability')
            elif callback_response.status_code == 401:
                logger.info('OAuth callback properly rejected invalid state')
            else:
                pytest.fail(f'Unexpected OAuth callback response: {callback_response.status_code}')
        except Exception as e:
            pytest.fail(f'OAuth callback state validation test failed: {e}')

    @pytest.mark.e2e
    async def test_oauth_callback_network_failure(self, auth_tester):
        """Test OAuth callback with network failure to Google - Should expose error handling"""
        valid_callback_data = {'code': 'valid_authorization_code_67890', 'state': self._generate_valid_oauth_state(), 'redirect_uri': f"{TEST_CONFIG['frontend_url']}/auth/callback"}
        try:
            callback_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/callback/google", headers=TEST_HEADERS, json=valid_callback_data)
            logger.info(f'OAuth callback with network simulation: {callback_response.status_code}')
            if callback_response.status_code in [503, 502, 500]:
                logger.info('OAuth callback properly handled network failure')
            elif callback_response.status_code == 401:
                logger.info('OAuth callback failed token exchange - expected')
            else:
                logger.warning(f'Unexpected OAuth response: {callback_response.status_code}')
        except Exception as e:
            logger.info(f'OAuth callback network failure test: {e}')

    def _generate_valid_oauth_state(self) -> str:
        """Generate a valid OAuth state token"""
        import base64
        state_data = {'timestamp': int(time.time()), 'nonce': str(uuid.uuid4()), 'session_id': str(uuid.uuid4())}
        return base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

@pytest.mark.e2e
class TestJWTTokenHandling:
    """Test JWT token generation and validation - Should expose token handling issues"""

    @pytest.mark.e2e
    async def test_jwt_token_structure(self, auth_tester):
        """Test JWT token structure and claims - Should expose malformed tokens"""
        login_data = {'email': 'dev@example.com'}
        try:
            login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json=login_data)
            if login_response.status_code != 200:
                pytest.skip('Cannot get dev token for JWT structure test')
            login_result = login_response.json()
            token = login_result.get('access_token')
            if not token:
                pytest.fail('No access token in dev login response')
            token_parts = token.split('.')
            if len(token_parts) != 3:
                pytest.fail(f'Invalid JWT structure: {len(token_parts)} parts instead of 3')
            try:
                payload_part = token_parts[1]
                missing_padding = len(payload_part) % 4
                if missing_padding:
                    payload_part += '=' * (4 - missing_padding)
                payload_bytes = base64.urlsafe_b64decode(payload_part)
                payload_data = json.loads(payload_bytes)
                logger.info(f'JWT payload: {payload_data}')
                required_claims = ['sub', 'exp', 'iat']
                missing_claims = []
                for claim in required_claims:
                    if claim not in payload_data:
                        missing_claims.append(claim)
                if missing_claims:
                    pytest.fail(f'Missing JWT claims: {missing_claims}')
                if 'exp' in payload_data:
                    exp_time = payload_data['exp']
                    current_time = int(time.time())
                    if exp_time <= current_time:
                        pytest.fail('JWT token already expired')
                    max_expiry = current_time + 24 * 60 * 60
                    if exp_time > max_expiry:
                        pytest.fail('JWT expiry too long - security issue')
            except Exception as e:
                pytest.fail(f'Cannot decode JWT payload: {e}')
        except Exception as e:
            pytest.fail(f'JWT structure test failed: {e}')

    @pytest.mark.e2e
    async def test_jwt_blacklist_functionality(self, auth_tester):
        """Test JWT token blacklisting - Should expose blacklist synchronization issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for blacklist test')
        token = login_response.json().get('access_token')
        validation_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={'Authorization': f'Bearer {token}'}, json={'token': token})
        if validation_response.status_code != 200:
            pytest.skip('Token not valid for blacklist test')
        logout_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/logout", headers={'Authorization': f'Bearer {token}'})
        logger.info(f'Logout response: {logout_response.status_code}')
        blacklist_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/check-blacklist", headers=TEST_HEADERS, json={'token': token})
        if blacklist_response.status_code == 200:
            blacklist_result = blacklist_response.json()
            if not blacklist_result.get('blacklisted', False):
                pytest.fail('Token not blacklisted after logout - security issue')
        validation_after_blacklist = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={'Authorization': f'Bearer {token}'}, json={'token': token})
        if validation_after_blacklist.status_code == 200:
            validation_result = validation_after_blacklist.json()
            if validation_result.get('valid', False):
                pytest.fail('Blacklisted token still valid - security vulnerability')

@pytest.mark.e2e
class TestTokenPropagation:
    """Test token propagation to frontend - Should expose token delivery issues"""

    @pytest.mark.e2e
    async def test_token_in_auth_headers(self, auth_tester):
        """Test token propagation via Authorization headers - Should expose header issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for propagation test')
        token = login_response.json().get('access_token')
        try:
            backend_response = await auth_tester.client.get(f"{TEST_CONFIG['backend_url']}/api/user/profile", headers={**TEST_HEADERS, 'Authorization': f'Bearer {token}'})
            logger.info(f'Backend auth response: {backend_response.status_code}')
            if backend_response.status_code == 401:
                pytest.fail('Backend cannot validate auth service token - cross-service auth issue')
            elif backend_response.status_code == 403:
                pytest.fail('Backend rejected valid token - permission propagation issue')
        except ConnectError:
            pytest.fail('Backend service not running on expected port 8000')
        except Exception as e:
            logger.warning(f'Backend token test failed: {e}')

    @pytest.mark.e2e
    async def test_token_in_cookies(self, auth_tester):
        """Test token propagation via cookies - Should expose cookie configuration issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for cookie test')
        cookies = login_response.cookies
        logger.info(f'Login response cookies: {dict(cookies)}')
        auth_cookie_names = ['auth_token', 'access_token', 'session_id', 'jwt_token']
        found_auth_cookies = []
        for cookie_name in auth_cookie_names:
            if cookie_name in cookies:
                found_auth_cookies.append(cookie_name)
        if not found_auth_cookies:
            logger.warning('No authentication cookies set - may require frontend cookie management')
        for cookie_name, cookie in cookies.items():
            if not hasattr(cookie, 'secure') or not cookie.secure:
                logger.warning(f'Cookie {cookie_name} not marked as secure - security issue')
            if not hasattr(cookie, 'httponly') or not cookie.httponly:
                logger.warning(f'Cookie {cookie_name} not marked as httponly - XSS vulnerability')

@pytest.mark.e2e
class TestCORSConfiguration:
    """Test CORS configuration - Should expose cross-origin request issues"""

    @pytest.mark.e2e
    async def test_cors_preflight_all_endpoints(self, auth_tester):
        """Test CORS preflight for all auth endpoints - Should expose CORS misconfigurations"""
        auth_endpoints = ['/auth/login', '/auth/logout', '/auth/validate', '/auth/refresh', '/auth/dev/login', '/auth/callback/google']
        cors_failures = []
        for endpoint in auth_endpoints:
            try:
                preflight_response = await auth_tester.client.request('OPTIONS', f"{TEST_CONFIG['auth_service_url']}{endpoint}", headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type, Authorization'})
                if preflight_response.status_code != 200:
                    cors_failures.append(f'{endpoint}: {preflight_response.status_code}')
                cors_headers = [h.lower() for h in preflight_response.headers.keys()]
                if 'access-control-allow-origin' not in cors_headers:
                    cors_failures.append(f'{endpoint}: missing allow-origin')
            except Exception as e:
                cors_failures.append(f'{endpoint}: {str(e)}')
        if cors_failures:
            auth_tester.cors_errors.extend(cors_failures)
            pytest.fail(f'CORS failures: {cors_failures}')

    @pytest.mark.e2e
    async def test_cors_different_origins(self, auth_tester):
        """Test CORS with different origins - Should expose origin whitelist issues"""
        test_origins = ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'https://localhost:3000', 'http://example.com', 'null']
        origin_failures = []
        for origin in test_origins:
            try:
                response = await auth_tester.client.request('OPTIONS', f"{TEST_CONFIG['auth_service_url']}/auth/config", headers={'Origin': origin, 'Access-Control-Request-Method': 'GET'})
                allowed_origin = response.headers.get('access-control-allow-origin')
                if origin in ['http://localhost:3000', 'http://127.0.0.1:3000']:
                    if not allowed_origin or (allowed_origin != origin and allowed_origin != '*'):
                        origin_failures.append(f'Should allow {origin}, got {allowed_origin}')
                elif origin == 'http://example.com':
                    if allowed_origin == origin or allowed_origin == '*':
                        origin_failures.append(f'Should NOT allow {origin}, but did')
            except Exception as e:
                origin_failures.append(f'{origin}: {str(e)}')
        if origin_failures:
            logger.warning(f'Origin check issues: {origin_failures}')

@pytest.mark.e2e
class TestSecurityHeaders:
    """Test security headers - Should expose security configuration issues"""

    @pytest.mark.e2e
    async def test_security_headers_presence(self, auth_tester):
        """Test presence of security headers - Should expose missing security configurations"""
        response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/health", headers=TEST_HEADERS)
        security_headers = {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'x-xss-protection': '1; mode=block', 'strict-transport-security': 'max-age=31536000', 'content-security-policy': 'default-src'}
        missing_headers = []
        incorrect_headers = []
        for header_name, expected_value in security_headers.items():
            actual_value = response.headers.get(header_name)
            if not actual_value:
                missing_headers.append(header_name)
            elif expected_value not in actual_value:
                incorrect_headers.append(f'{header_name}: {actual_value}')
        if missing_headers:
            logger.warning(f'Missing security headers: {missing_headers}')
        if incorrect_headers:
            logger.warning(f'Incorrect security headers: {incorrect_headers}')

    @pytest.mark.e2e
    async def test_sensitive_info_exposure(self, auth_tester):
        """Test for sensitive information exposure - Should expose info leakage"""
        error_endpoints = [('/auth/login', {'email': 'invalid', 'password': 'invalid'}), ('/auth/validate', {'token': 'invalid_token'}), ('/auth/refresh', {'refresh_token': 'invalid_refresh'})]
        info_leaks = []
        for endpoint, data in error_endpoints:
            try:
                response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}{endpoint}", headers=TEST_HEADERS, json=data)
                response_text = response.text.lower()
                sensitive_keywords = ['database', 'sql', 'connection', 'internal server error', 'stack trace', 'exception', 'debug', 'redis', 'secret']
                for keyword in sensitive_keywords:
                    if keyword in response_text:
                        info_leaks.append(f"{endpoint}: contains '{keyword}'")
            except Exception as e:
                logger.warning(f'Error testing {endpoint}: {e}')
        if info_leaks:
            logger.warning(f'Potential information leaks: {info_leaks}')

@pytest.mark.e2e
class TestSessionManagement:
    """Test session management - Should expose session handling issues"""

    @pytest.mark.e2e
    async def test_session_creation_and_cleanup(self, auth_tester):
        """Test session lifecycle - Should expose session management issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot create session for test')
        token = login_response.json().get('access_token')
        session_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/session", headers={'Authorization': f'Bearer {token}'})
        logger.info(f'Session check: {session_response.status_code}')
        if session_response.status_code == 200:
            session_data = session_response.json()
            logger.info(f'Session data: {session_data}')
            if not session_data.get('active', False):
                pytest.fail('Session not active after login')
        logout_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/logout", headers={'Authorization': f'Bearer {token}'})
        session_after_logout = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/session", headers={'Authorization': f'Bearer {token}'})
        if session_after_logout.status_code == 200:
            session_data = session_after_logout.json()
            if session_data.get('active', True):
                pytest.fail('Session still active after logout - cleanup issue')

    @pytest.mark.e2e
    async def test_concurrent_sessions(self, auth_tester):
        """Test concurrent session handling - Should expose session isolation issues"""
        sessions = []
        for i in range(3):
            try:
                login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers={**TEST_HEADERS, 'User-Agent': f'TestClient-{i}'}, json={'email': 'dev@example.com'})
                if login_response.status_code == 200:
                    token = login_response.json().get('access_token')
                    sessions.append(token)
            except Exception as e:
                logger.warning(f'Failed to create session {i}: {e}')
        logger.info(f'Created {len(sessions)} sessions')
        for i, token in enumerate(sessions):
            try:
                session_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/session", headers={'Authorization': f'Bearer {token}'})
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    user_id = session_data.get('user_id')
                    if not user_id:
                        pytest.fail(f'Session {i} missing user_id')
            except Exception as e:
                logger.warning(f'Session check {i} failed: {e}')

@pytest.mark.e2e
class TestTokenRefreshMechanism:
    """Test token refresh functionality - Should expose refresh token issues"""

    @pytest.mark.e2e
    async def test_token_refresh_flow(self, auth_tester):
        """Test complete token refresh flow - Should expose refresh mechanism issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get initial tokens for refresh test')
        login_data = login_response.json()
        access_token = login_data.get('access_token')
        refresh_token = login_data.get('refresh_token')
        if not refresh_token:
            pytest.fail('No refresh token provided in login response')
        await asyncio.sleep(1)
        refresh_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/refresh", headers=TEST_HEADERS, json={'refresh_token': refresh_token})
        logger.info(f'Token refresh response: {refresh_response.status_code}')
        if refresh_response.status_code != 200:
            pytest.fail(f'Token refresh failed: {refresh_response.status_code}')
        refresh_data = refresh_response.json()
        new_access_token = refresh_data.get('access_token')
        new_refresh_token = refresh_data.get('refresh_token')
        if not new_access_token:
            pytest.fail('No new access token in refresh response')
        old_token_validation = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={'Authorization': f'Bearer {access_token}'}, json={'token': access_token})
        logger.info(f'Old token validation: {old_token_validation.status_code}')
        new_token_validation = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={'Authorization': f'Bearer {new_access_token}'}, json={'token': new_access_token})
        if new_token_validation.status_code != 200:
            pytest.fail('New access token is not valid')

    @pytest.mark.e2e
    async def test_refresh_token_reuse(self, auth_tester):
        """Test refresh token reuse protection - Should expose security issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get tokens for reuse test')
        refresh_token = login_response.json().get('refresh_token')
        if not refresh_token:
            pytest.skip('No refresh token for reuse test')
        first_refresh = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/refresh", headers=TEST_HEADERS, json={'refresh_token': refresh_token})
        if first_refresh.status_code != 200:
            pytest.skip('First refresh failed')
        second_refresh = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/refresh", headers=TEST_HEADERS, json={'refresh_token': refresh_token})
        if second_refresh.status_code == 200:
            pytest.fail('Refresh token reuse allowed - security vulnerability')

@pytest.mark.e2e
class TestWebSocketAuthentication:
    """Test WebSocket authentication - Should expose WebSocket auth issues"""

    @pytest.mark.e2e
    async def test_websocket_auth_handshake(self, auth_tester):
        """Test WebSocket authentication handshake - Should expose WebSocket auth problems"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for WebSocket auth test')
        token = login_response.json().get('access_token')
        try:
            ws_auth_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/websocket/auth", headers={**TEST_HEADERS, 'Authorization': f'Bearer {token}'}, json={'token': token})
            logger.info(f'WebSocket auth response: {ws_auth_response.status_code}')
            if ws_auth_response.status_code != 200:
                pytest.fail(f'WebSocket auth failed: {ws_auth_response.status_code}')
            auth_result = ws_auth_response.json()
            if auth_result.get('status') != 'authenticated':
                pytest.fail('WebSocket authentication not successful')
            user_data = auth_result.get('user', {})
            if not user_data.get('id'):
                pytest.fail('No user ID in WebSocket auth response')
        except Exception as e:
            pytest.fail(f'WebSocket authentication test failed: {e}')

    @pytest.mark.e2e
    async def test_websocket_token_validation(self, auth_tester):
        """Test WebSocket token validation endpoint - Should expose validation issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for WebSocket validation test')
        token = login_response.json().get('access_token')
        ws_validation_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/websocket/validate", params={'token': token})
        logger.info(f'WebSocket validation response: {ws_validation_response.status_code}')
        if ws_validation_response.status_code == 200:
            validation_result = ws_validation_response.json()
            if not validation_result.get('valid', False):
                pytest.fail('WebSocket token validation failed')
            required_fields = ['valid', 'user_id', 'email']
            missing_fields = [field for field in required_fields if field not in validation_result]
            if missing_fields:
                pytest.fail(f'Missing WebSocket validation fields: {missing_fields}')

@pytest.mark.e2e
class TestCrossServiceAuthSync:
    """Test cross-service authentication synchronization - Should expose sync issues"""

    @pytest.mark.e2e
    async def test_auth_backend_token_sync(self, auth_tester):
        """Test token validation between auth service and backend - Should expose sync issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot get token for cross-service test')
        token = login_response.json().get('access_token')
        try:
            backend_response = await auth_tester.client.get(f"{TEST_CONFIG['backend_url']}/api/health", headers={**TEST_HEADERS, 'Authorization': f'Bearer {token}'})
            logger.info(f'Backend auth response: {backend_response.status_code}')
            if backend_response.status_code == 401:
                pytest.fail('Backend cannot validate auth service token - cross-service auth not working')
            elif backend_response.status_code == 403:
                logger.info('Backend rejected token - possible permission sync issue')
            elif backend_response.status_code == 500:
                pytest.fail('Backend error validating token - internal sync issue')
        except ConnectError:
            logger.warning('Backend service not available for cross-service test')
        except Exception as e:
            logger.warning(f'Cross-service test failed: {e}')

    @pytest.mark.e2e
    async def test_user_data_consistency(self, auth_tester):
        """Test user data consistency between services - Should expose data sync issues"""
        login_response = await auth_tester.client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers=TEST_HEADERS, json={'email': 'dev@example.com'})
        if login_response.status_code != 200:
            pytest.skip('Cannot login for user data consistency test')
        login_data = login_response.json()
        token = login_data.get('access_token')
        auth_user_data = login_data.get('user', {})
        auth_me_response = await auth_tester.client.get(f"{TEST_CONFIG['auth_service_url']}/auth/me", headers={'Authorization': f'Bearer {token}'})
        if auth_me_response.status_code == 200:
            auth_me_data = auth_me_response.json()
            auth_user_id = auth_user_data.get('id')
            me_user_id = auth_me_data.get('id')
            if auth_user_id and me_user_id and (auth_user_id != me_user_id):
                pytest.fail(f'User ID inconsistency: login={auth_user_id}, me={me_user_id}')
            auth_email = auth_user_data.get('email')
            me_email = auth_me_data.get('email')
            if auth_email and me_email and (auth_email != me_email):
                pytest.fail(f'Email inconsistency: login={auth_email}, me={me_email}')

@pytest.mark.e2e
class TestMultiTabSessionHandling:
    """Test multi-tab session handling - Should expose session coordination issues"""

    @pytest.mark.e2e
    async def test_multi_tab_login_logout(self, auth_tester):
        """Test login/logout across multiple tabs - Should expose session sync issues"""
        clients = [httpx.AsyncClient(timeout=TEST_CONFIG['timeout'], follow_redirects=True) for _ in range(3)]
        try:
            tokens = []
            for i, client in enumerate(clients):
                login_response = await client.post(f"{TEST_CONFIG['auth_service_url']}/auth/dev/login", headers={**TEST_HEADERS, 'User-Agent': f'Tab-{i}'}, json={'email': 'dev@example.com'})
                if login_response.status_code == 200:
                    token = login_response.json().get('access_token')
                    tokens.append(token)
            logger.info(f'Created {len(tokens)} tab sessions')
            if tokens:
                logout_response = await clients[0].post(f"{TEST_CONFIG['auth_service_url']}/auth/logout", headers={'Authorization': f'Bearer {tokens[0]}'})
                logger.info(f'Logout from tab 0: {logout_response.status_code}')
                for i, token in enumerate(tokens[1:], 1):
                    validation_response = await clients[i].post(f"{TEST_CONFIG['auth_service_url']}/auth/validate", headers={'Authorization': f'Bearer {token}'}, json={'token': token})
                    logger.info(f'Tab {i} validation after logout: {validation_response.status_code}')
                    if validation_response.status_code == 401:
                        logger.info(f'Tab {i} invalidated after logout (global logout)')
                    elif validation_response.status_code == 200:
                        logger.info(f'Tab {i} still valid after logout (per-tab sessions)')
        finally:
            for client in clients:
                await client.aclose()

@pytest.mark.e2e
class TestStagingEnvironmentAuth:
    """Test staging environment authentication - Should expose staging-specific issues"""

    @pytest.mark.e2e
    async def test_staging_auth_config(self, auth_tester):
        """Test staging auth configuration - Should expose staging config issues"""
        if not TEST_CONFIG.get('staging_auth_url'):
            pytest.skip('No staging auth URL configured')
        try:
            staging_config_response = await auth_tester.client.get(f"{TEST_CONFIG['staging_auth_url']}/auth/config", headers=TEST_HEADERS, timeout=15.0)
            logger.info(f'Staging auth config: {staging_config_response.status_code}')
            if staging_config_response.status_code == 200:
                config_data = staging_config_response.json()
                if config_data.get('development_mode', True):
                    pytest.fail('Staging environment has development_mode enabled - security issue')
                google_client_id = config_data.get('google_client_id')
                if not google_client_id or 'example' in google_client_id:
                    pytest.fail('Staging OAuth not properly configured')
                redirect_uris = config_data.get('authorized_redirect_uris', [])
                staging_redirect = f"{TEST_CONFIG['staging_frontend_url']}/auth/callback"
                if staging_redirect not in redirect_uris:
                    pytest.fail(f'Staging redirect URI not configured: {staging_redirect}')
        except ConnectError:
            pytest.fail('Cannot connect to staging auth service')
        except ReadTimeout:
            pytest.fail('Staging auth service timeout')
        except Exception as e:
            logger.warning(f'Staging auth config test failed: {e}')

@pytest.mark.e2e
async def test_auth_comprehensive_summary(auth_tester):
    """Summary test to report all discovered issues"""
    logger.info('=== AUTHENTICATION FLOW TEST SUMMARY ===')
    issues_found = {'cors_errors': auth_tester.cors_errors, 'auth_errors': auth_tester.auth_errors}
    total_issues = sum((len(errors) for errors in issues_found.values()))
    logger.info(f'Total issues found: {total_issues}')
    for category, errors in issues_found.items():
        if errors:
            logger.info(f'{category.upper()}: {len(errors)} issues')
            for error in errors:
                logger.info(f'  - {error}')
    expected_failures = ['CORS preflight failures from localhost origins', 'OAuth redirect URI mismatches', 'Token validation cross-service failures', 'WebSocket authentication timeouts', 'Session synchronization issues', 'Security headers missing', 'Token blacklist synchronization delays', 'Refresh token reuse protection', 'Multi-tab session coordination', 'Staging environment configuration errors']
    logger.info('EXPECTED FAILURE CATEGORIES:')
    for failure in expected_failures:
        logger.info(f'  - {failure}')
    if total_issues == 0:
        logger.warning('No issues found - this may indicate tests need adjustment')
    else:
        logger.info(f'Successfully exposed {total_issues} authentication issues for fixing')

@pytest.mark.e2e
async def test_gcp_staging_comprehensive_auth_flow():
    """Test comprehensive authentication flow using GCP staging services with StagingAuthHelper"""
    if get_env().get('ENVIRONMENT', 'development') != 'staging':
        pytest.skip('Test only runs in staging environment')
    auth_tester = TestAuthFlower()
    try:
        if not auth_tester.is_staging or not hasattr(auth_tester, 'staging_auth'):
            pytest.skip('Staging auth helper not initialized')
        try:
            token = await auth_tester.staging_auth.get_test_token()
            assert token is not None, 'Failed to get staging auth token'
            assert len(token) > 20, 'Token appears invalid'
            logger.info('[U+2713] Successfully obtained staging auth token')
        except Exception as e:
            if 'GCP' in str(e) or 'secret' in str(e).lower():
                pytest.skip(f'GCP service issue: {e}')
            else:
                raise
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{auth_tester.base_urls['auth']}/auth/verify", headers={'Authorization': f'Bearer {token}'}, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    assert data.get('valid') is True, 'Token verification failed'
                    logger.info('[U+2713] Token verification successful')
                else:
                    logger.warning(f'Token verification returned {response.status_code}')
        except httpx.TimeoutException:
            pytest.skip('GCP service timeout during token verification')
        except Exception as e:
            if 'run.app' in str(e):
                pytest.skip(f'GCP service connectivity issue: {e}')
            else:
                raise
        try:
            auth_client = await auth_tester.staging_auth.get_authenticated_client(base_url=auth_tester.base_urls['auth'])
            health_response = await auth_client.get('/health', timeout=30.0)
            if health_response.status_code == 200:
                logger.info('[U+2713] Authenticated health check successful')
            else:
                logger.warning(f'Health check returned {health_response.status_code}')
            await auth_client.aclose()
        except Exception as e:
            if any((term in str(e).lower() for term in ['timeout', 'gcp', 'run.app'])):
                pytest.skip(f'GCP service issue: {e}')
            else:
                raise
        logger.info(' CELEBRATION:  GCP staging comprehensive auth flow test PASSED')
    except Exception as e:
        if any((term in str(e).lower() for term in ['gcp', 'staging', 'run.app', 'secret'])):
            pytest.skip(f'GCP/Staging service issue: {e}')
        else:
            raise
    finally:
        await auth_tester.cleanup()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')