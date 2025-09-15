"""
Test Complete OAuth Login Flow - E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure user authentication enables platform access
- Value Impact: Users can reliably authenticate and access Netra platform capabilities
- Strategic Impact: Core security foundation enabling all business operations

This E2E test validates the complete Google OAuth flow from start to finish:
1. OAuth authorization URL generation
2. User authentication with Google (simulated)
3. Authorization code callback handling
4. JWT token generation and validation
5. Cross-service authentication validation
6. Session persistence and refresh token handling
7. Complete user journey testing with real services

CRITICAL E2E REQUIREMENTS:
- Uses REAL Docker services (PostgreSQL, Redis, Auth Service)
- NO MOCKS allowed - all services must be real
- Tests complete end-to-end business journeys
- Validates actual authentication flows that enable business value
- Uses proper timing validation (no 0-second executions)
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from urllib.parse import urlparse, parse_qs
import pytest
import httpx
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import get_env
logger = logging.getLogger(__name__)

class TestCompleteOAuthLoginFlow(BaseE2ETest):
    """Test complete OAuth login flow with real services."""

    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.docker_manager = None
        self.auth_service_url = None
        self.test_start_time = None

    async def setup_real_services(self):
        """Set up real Docker services for E2E testing."""
        self.logger.info('[U+1F527] Setting up real Docker services for OAuth E2E testing')
        self.docker_manager = UnifiedDockerManager()
        success = await self.docker_manager.start_services_smart(services=['postgres', 'redis', 'auth'], wait_healthy=True)
        if not success:
            raise RuntimeError('Failed to start real services')
        auth_port = self.docker_manager.allocated_ports.get('auth', 8081)
        self.auth_service_url = f'http://localhost:{auth_port}'
        self.postgres_port = self.docker_manager.allocated_ports.get('postgres', 5434)
        self.redis_port = self.docker_manager.allocated_ports.get('redis', 6381)
        self.logger.info(f' PASS:  Real services started - Auth: {self.auth_service_url}')
        await self.wait_for_service_ready(self.auth_service_url + '/health', timeout=60)
        self.register_cleanup_task(self._cleanup_docker_services)

    async def _cleanup_docker_services(self):
        """Clean up Docker services after testing."""
        if self.docker_manager:
            try:
                await self.docker_manager.stop_services_smart(['postgres', 'redis', 'auth'])
                self.logger.info(' PASS:  Docker services cleaned up successfully')
            except Exception as e:
                self.logger.error(f' FAIL:  Error cleaning up Docker services: {e}')

    async def wait_for_service_ready(self, health_url: str, timeout: float=30.0):
        """Wait for service to be ready with health check."""

        async def check_health():
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        health_data = response.json()
                        return health_data.get('status') == 'healthy'
            except Exception:
                pass
            return False
        if not await self.wait_for_condition(check_health, timeout=timeout, description=f'service at {health_url}'):
            raise RuntimeError(f'Service not ready at {health_url} within {timeout}s')
        self.logger.info(f' PASS:  Service ready: {health_url}')

    async def create_test_user_session(self) -> Dict[str, Any]:
        """Create a test user session for authentication testing."""
        user_data = {'email': f'test.user.{int(time.time())}@netratest.com', 'name': 'OAuth Test User', 'google_id': f'oauth_test_{int(time.time())}', 'picture': 'https://lh3.googleusercontent.com/a/test-picture', 'locale': 'en', 'verified_email': True}
        return user_data

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_oauth_authorization_flow(self):
        """Test complete OAuth authorization URL generation and validation."""
        self.test_start_time = time.time()
        await self.setup_real_services()
        self.logger.info('[U+1F510] Testing OAuth authorization flow with real auth service')
        async with httpx.AsyncClient(timeout=30.0) as client:
            oauth_status_response = await client.get(f'{self.auth_service_url}/oauth/status')
            assert oauth_status_response.status_code == 200, f'OAuth status check failed: {oauth_status_response.text}'
            oauth_status = oauth_status_response.json()
            assert 'available_providers' in oauth_status
            assert 'google' in oauth_status['available_providers'], 'Google OAuth provider not available'
            auth_url_response = await client.post(f'{self.auth_service_url}/oauth/google/authorize', json={'redirect_uri': 'http://localhost:3000/auth/callback'})
            assert auth_url_response.status_code == 200, f'OAuth authorization failed: {auth_url_response.text}'
            auth_data = auth_url_response.json()
            assert 'authorization_url' in auth_data
            assert 'state' in auth_data
            authorization_url = auth_data['authorization_url']
            oauth_state = auth_data['state']
            assert 'accounts.google.com' in authorization_url
            assert 'oauth2/v2/auth' in authorization_url
            assert 'client_id' in authorization_url
            assert 'redirect_uri' in authorization_url
            assert f'state={oauth_state}' in authorization_url
            assert len(oauth_state) >= 32, 'OAuth state should be sufficiently random'
            self.logger.info(f' PASS:  OAuth authorization URL generated successfully: {authorization_url[:100]}...')
            self.logger.info(f' PASS:  OAuth state parameter: {oauth_state}')
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f'E2E test executed too fast: {execution_time}s (likely mocked)'
        self.logger.info(f' PASS:  OAuth authorization flow test completed in {execution_time:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_oauth_callback_processing(self):
        """Test complete OAuth callback processing with token generation."""
        self.test_start_time = time.time()
        await self.setup_real_services()
        self.logger.info('[U+1F510] Testing OAuth callback processing with real services')
        user_data = await self.create_test_user_session()
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_url_response = await client.post(f'{self.auth_service_url}/oauth/google/authorize', json={'redirect_uri': 'http://localhost:3000/auth/callback'})
            assert auth_url_response.status_code == 200
            auth_data = auth_url_response.json()
            oauth_state = auth_data['state']
            callback_response = await client.post(f'{self.auth_service_url}/oauth/google/callback', json={'code': f'test_auth_code_{int(time.time())}', 'state': oauth_state, 'user_info': user_data})
            assert callback_response.status_code == 200, f'OAuth callback failed: {callback_response.text}'
            callback_data = callback_response.json()
            assert 'access_token' in callback_data
            assert 'refresh_token' in callback_data
            assert 'token_type' in callback_data
            assert callback_data['token_type'] == 'Bearer'
            access_token = callback_data['access_token']
            refresh_token = callback_data['refresh_token']
            token_parts = access_token.split('.')
            assert len(token_parts) == 3, 'Access token should be valid JWT format'
            validation_response = await client.post(f'{self.auth_service_url}/auth/validate', headers={'Authorization': f'Bearer {access_token}'})
            assert validation_response.status_code == 200, f'Token validation failed: {validation_response.text}'
            validation_data = validation_response.json()
            assert 'user' in validation_data
            assert validation_data['user']['email'] == user_data['email']
            assert 'user_id' in validation_data['user']
            refresh_response = await client.post(f'{self.auth_service_url}/auth/refresh', json={'refresh_token': refresh_token})
            assert refresh_response.status_code == 200, f'Token refresh failed: {refresh_response.text}'
            refresh_data = refresh_response.json()
            assert 'access_token' in refresh_data
            new_access_token = refresh_data['access_token']
            assert new_access_token != access_token, 'Refreshed token should be different'
            self.logger.info(' PASS:  OAuth callback processing completed with valid tokens')
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f'E2E test executed too fast: {execution_time}s (likely mocked)'
        self.logger.info(f' PASS:  OAuth callback test completed in {execution_time:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_oauth_session_persistence_and_security(self):
        """Test OAuth session persistence with real database and security validation."""
        self.test_start_time = time.time()
        await self.setup_real_services()
        self.logger.info('[U+1F510] Testing OAuth session persistence with real database')
        user_data = await self.create_test_user_session()
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_url_response = await client.post(f'{self.auth_service_url}/oauth/google/authorize', json={'redirect_uri': 'http://localhost:3000/auth/callback'})
            auth_data = auth_url_response.json()
            oauth_state = auth_data['state']
            callback_response = await client.post(f'{self.auth_service_url}/oauth/google/callback', json={'code': f'test_auth_code_{int(time.time())}', 'state': oauth_state, 'user_info': user_data})
            assert callback_response.status_code == 200
            callback_data = callback_response.json()
            access_token = callback_data['access_token']
            for i in range(3):
                validation_response = await client.post(f'{self.auth_service_url}/auth/validate', headers={'Authorization': f'Bearer {access_token}'})
                assert validation_response.status_code == 200
                validation_data = validation_response.json()
                assert validation_data['user']['email'] == user_data['email']
                await asyncio.sleep(0.1)
            user_lookup_response = await client.get(f'{self.auth_service_url}/auth/user', headers={'Authorization': f'Bearer {access_token}'})
            assert user_lookup_response.status_code == 200
            user_info = user_lookup_response.json()
            assert user_info['email'] == user_data['email']
            assert user_info['name'] == user_data['name']
            invalid_token_response = await client.post(f'{self.auth_service_url}/auth/validate', headers={'Authorization': 'Bearer invalid.token.here'})
            assert invalid_token_response.status_code == 401, 'Invalid token should be rejected'
            no_auth_response = await client.post(f'{self.auth_service_url}/auth/validate')
            assert no_auth_response.status_code == 401, 'Missing authorization should be rejected'
            self.logger.info(' PASS:  OAuth session persistence and security validation completed')
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f'E2E test executed too fast: {execution_time}s (likely mocked)'
        self.logger.info(f' PASS:  OAuth session persistence test completed in {execution_time:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_oauth_error_handling_and_recovery(self):
        """Test OAuth error handling and recovery scenarios with real services."""
        self.test_start_time = time.time()
        await self.setup_real_services()
        self.logger.info('[U+1F510] Testing OAuth error handling and recovery')
        async with httpx.AsyncClient(timeout=30.0) as client:
            invalid_redirect_response = await client.post(f'{self.auth_service_url}/oauth/google/authorize', json={'redirect_uri': 'http://malicious-site.com/callback'})
            assert invalid_redirect_response.status_code == 400, 'Invalid redirect URI should be rejected'
            callback_invalid_state = await client.post(f'{self.auth_service_url}/oauth/google/callback', json={'code': 'test_code', 'state': 'invalid_state_12345', 'user_info': {'email': 'test@example.com'}})
            assert callback_invalid_state.status_code == 400, 'Invalid OAuth state should be rejected'
            callback_missing_fields = await client.post(f'{self.auth_service_url}/oauth/google/callback', json={'code': 'test_code'})
            assert callback_missing_fields.status_code == 400, 'Missing required fields should be rejected'
            refresh_invalid_response = await client.post(f'{self.auth_service_url}/auth/refresh', json={'refresh_token': 'invalid.refresh.token'})
            assert refresh_invalid_response.status_code == 401, 'Invalid refresh token should be rejected'
            oauth_status_response = await client.get(f'{self.auth_service_url}/oauth/status')
            assert oauth_status_response.status_code == 200
            oauth_status = oauth_status_response.json()
            assert 'oauth_healthy' in oauth_status
            self.logger.info(' PASS:  OAuth error handling and recovery validation completed')
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.1, f'E2E test executed too fast: {execution_time}s (likely mocked)'
        self.logger.info(f' PASS:  OAuth error handling test completed in {execution_time:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_oauth_user_journey_complete_flow(self):
        """Test complete OAuth user journey from start to authenticated platform access."""
        self.test_start_time = time.time()
        await self.setup_real_services()
        self.logger.info('[U+1F510] Testing complete OAuth user journey with business value validation')
        user_data = await self.create_test_user_session()
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.logger.info('[U+1F464] Step 1: User initiates OAuth login')
            auth_url_response = await client.post(f'{self.auth_service_url}/oauth/google/authorize', json={'redirect_uri': 'http://localhost:3000/auth/callback'})
            assert auth_url_response.status_code == 200
            auth_data = auth_url_response.json()
            authorization_url = auth_data['authorization_url']
            oauth_state = auth_data['state']
            self.logger.info(f' PASS:  Step 1 Complete: OAuth URL generated for user journey')
            self.logger.info('[U+1F464] Step 2: User completes Google OAuth authentication')
            callback_response = await client.post(f'{self.auth_service_url}/oauth/google/callback', json={'code': f'journey_auth_code_{int(time.time())}', 'state': oauth_state, 'user_info': user_data})
            assert callback_response.status_code == 200
            callback_data = callback_response.json()
            access_token = callback_data['access_token']
            refresh_token = callback_data['refresh_token']
            self.logger.info(' PASS:  Step 2 Complete: User authenticated, tokens generated')
            self.logger.info('[U+1F464] Step 3: User accesses protected platform resources')
            user_profile_response = await client.get(f'{self.auth_service_url}/auth/user', headers={'Authorization': f'Bearer {access_token}'})
            assert user_profile_response.status_code == 200
            user_profile = user_profile_response.json()
            assert user_profile['email'] == user_data['email']
            for endpoint in ['/auth/validate', '/auth/user']:
                protected_response = await client.get(f'{self.auth_service_url}{endpoint}', headers={'Authorization': f'Bearer {access_token}'})
                assert protected_response.status_code in [200, 405]
            self.logger.info(' PASS:  Step 3 Complete: User successfully accessing protected resources')
            self.logger.info('[U+1F464] Step 4: Session renewal for continued platform access')
            await asyncio.sleep(0.1)
            refresh_response = await client.post(f'{self.auth_service_url}/auth/refresh', json={'refresh_token': refresh_token})
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            new_access_token = refresh_data['access_token']
            renewed_validation = await client.post(f'{self.auth_service_url}/auth/validate', headers={'Authorization': f'Bearer {new_access_token}'})
            assert renewed_validation.status_code == 200
            renewed_user_data = renewed_validation.json()
            assert renewed_user_data['user']['email'] == user_data['email']
            self.logger.info(' PASS:  Step 4 Complete: Session renewed, continued access enabled')
            self.logger.info('[U+1F4BC] Validating business value delivery')
            assert access_token != new_access_token, 'Token renewal provides new credentials'
            assert user_profile['email'] == user_data['email']
            assert user_profile['name'] == user_data['name']
            validation_check = await client.post(f'{self.auth_service_url}/auth/validate', headers={'Authorization': f'Bearer {new_access_token}'})
            assert validation_check.status_code == 200
            self.logger.info(' PASS:  BUSINESS VALUE DELIVERED: Complete OAuth user journey successful')
            self.logger.info(f"   - User authenticated: {user_data['email']}")
            self.logger.info(f'   - Platform access enabled via JWT tokens')
            self.logger.info(f'   - Session persistence and renewal working')
            self.logger.info(f'   - Security validation passed')
        execution_time = time.time() - self.test_start_time
        assert execution_time > 0.2, f'E2E test executed too fast: {execution_time}s (likely mocked)'
        self.logger.info(f' PASS:  Complete OAuth user journey test completed in {execution_time:.2f}s')

@pytest.fixture(scope='session')
async def oauth_test_environment():
    """Set up OAuth test environment with real services."""
    logger.info('Setting up OAuth test environment')
    env = get_env()
    env.set('NETRA_TEST_MODE', 'true', source='test')
    env.set('ENVIRONMENT', 'test', source='test')
    env.set('AUTH_FAST_TEST_MODE', 'false', source='test')
    yield {'environment': 'test', 'oauth_enabled': True}
    logger.info('OAuth test environment cleaned up')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')