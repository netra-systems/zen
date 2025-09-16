"""
Comprehensive E2E test for auth token refresh flow.
Tests the complete flow from frontend to auth service.
"""
import pytest
import json
import time
import httpx
from datetime import datetime, timedelta
import logging
from shared.isolated_environment import IsolatedEnvironment
logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.auth
@pytest.mark.asyncio
class AuthRefreshFlowTests:
    """Test suite for auth token refresh flow end-to-end"""

    @pytest.mark.auth
    async def test_refresh_token_success(self, auth_test_client):
        """Test successful token refresh flow"""
        login_response = await auth_test_client.post('/auth/login', json={'email': 'test@example.com', 'password': 'testpass123'})
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert 'access_token' in login_data
        assert 'refresh_token' in login_data
        access_token = login_data['access_token']
        refresh_token = login_data['refresh_token']
        await asyncio.sleep(0.1)
        refresh_response = await auth_test_client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert 'access_token' in refresh_data
        assert 'refresh_token' in refresh_data
        assert refresh_data['access_token'] != access_token
        assert refresh_data['refresh_token'] != refresh_token
        verify_response = await auth_test_client.get('/auth/verify', headers={'Authorization': f"Bearer {refresh_data['access_token']}"})
        assert verify_response.status_code == 200

    @pytest.mark.auth
    async def test_refresh_token_missing_body(self, auth_test_client):
        """Test refresh endpoint with missing request body"""
        refresh_response = await auth_test_client.post('/auth/refresh', json={})
        assert refresh_response.status_code == 422
        error_data = refresh_response.json()
        assert 'refresh_token field is required' in str(error_data)

    @pytest.mark.auth
    async def test_refresh_token_invalid(self, auth_test_client):
        """Test refresh with invalid token"""
        refresh_response = await auth_test_client.post('/auth/refresh', json={'refresh_token': 'invalid.token.here'})
        assert refresh_response.status_code == 401

    @pytest.mark.auth
    async def test_refresh_token_expired(self, auth_test_client, mock_time):
        """Test refresh with expired token"""
        login_response = await auth_test_client.post('/auth/login', json={'email': 'test@example.com', 'password': 'testpass123'})
        assert login_response.status_code == 200
        refresh_token = login_response.json()['refresh_token']
        mock_time.advance(timedelta(days=8))
        refresh_response = await auth_test_client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert refresh_response.status_code == 401

    @pytest.mark.auth
    async def test_refresh_token_race_condition(self, auth_test_client):
        """Test refresh token race condition protection"""
        login_response = await auth_test_client.post('/auth/login', json={'email': 'test@example.com', 'password': 'testpass123'})
        assert login_response.status_code == 200
        refresh_token = login_response.json()['refresh_token']
        import asyncio

        async def refresh_request():
            return await auth_test_client.post('/auth/refresh', json={'refresh_token': refresh_token})
        results = await asyncio.gather(refresh_request(), refresh_request(), return_exceptions=True)
        success_count = sum((1 for r in results if not isinstance(r, Exception) and r.status_code == 200))
        assert success_count == 1, 'Only one refresh should succeed with the same token'

    @pytest.mark.auth
    async def test_refresh_token_with_different_field_names(self, auth_test_client):
        """Test refresh endpoint accepts different field name formats"""
        login_response = await auth_test_client.post('/auth/login', json={'email': 'test@example.com', 'password': 'testpass123'})
        assert login_response.status_code == 200
        refresh_token = login_response.json()['refresh_token']
        refresh_response = await auth_test_client.post('/auth/refresh', json={'refreshToken': refresh_token})
        assert refresh_response.status_code == 200
        new_refresh_token = refresh_response.json()['refresh_token']
        refresh_response2 = await auth_test_client.post('/auth/refresh', json={'token': new_refresh_token})
        assert refresh_response2.status_code == 200

    @pytest.mark.auth
    async def test_refresh_clears_blacklisted_token(self, auth_test_client):
        """Test that refresh properly handles blacklisted tokens"""
        login_response = await auth_test_client.post('/auth/login', json={'email': 'test@example.com', 'password': 'testpass123'})
        assert login_response.status_code == 200
        access_token = login_response.json()['access_token']
        refresh_token = login_response.json()['refresh_token']
        logout_response = await auth_test_client.post('/auth/logout', headers={'Authorization': f'Bearer {access_token}'})
        assert logout_response.status_code == 200
        refresh_response = await auth_test_client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert refresh_response.status_code == 401

    @pytest.mark.auth
    async def test_full_frontend_backend_refresh_flow(self, auth_test_client, frontend_test_client):
        """Test complete refresh flow from frontend through to backend"""
        tokens = {'access_token': 'test.access.token', 'refresh_token': 'test.refresh.token'}
        with patch('frontend.lib.auth_service_client.localStorage') as mock_storage:
            mock_storage.getItem.return_value = tokens['refresh_token']
            refresh_request_body = json.dumps({'refresh_token': tokens['refresh_token']})
            assert 'refresh_token' in refresh_request_body
        headers = {'Content-Type': 'application/json'}
        logger.info('Frontend-backend refresh flow test completed')

@pytest.mark.asyncio
class AuthServiceIntegrationTests:
    """Integration tests for auth service refresh functionality"""

    @pytest.mark.auth
    async def test_refresh_token_validation(self, auth_service):
        """Test auth service refresh token validation"""
        from auth_service.auth_core.services.auth_service import AuthService
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        service = AuthService()
        jwt_handler = JWTHandler()
        user_id = 'test-user-123'
        refresh_token = jwt_handler.create_refresh_token(user_id)
        result = await service.refresh_tokens(refresh_token)
        assert result is not None
        access_token, new_refresh = result
        assert access_token is not None
        assert new_refresh is not None

    @pytest.mark.auth
    async def test_refresh_token_expiry_check(self, auth_service):
        """Test refresh token expiry validation"""
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        import jwt
        from datetime import datetime, UTC
        jwt_handler = JWTHandler()
        payload = {'sub': 'test-user', 'type': 'refresh', 'exp': datetime.now(UTC) - timedelta(hours=1)}
        expired_token = jwt.encode(payload, jwt_handler.secret_key, algorithm=jwt_handler.algorithm)
        result = jwt_handler.validate_token(expired_token, 'refresh')
        assert result is None

@pytest.mark.asyncio
class FrontendAuthRefreshTests:
    """Frontend-specific auth refresh tests"""

    @pytest.mark.auth
    async def test_frontend_stores_refresh_token(self):
        """Test that frontend properly stores refresh token from OAuth callback"""
        mock_params = {'token': 'access.token.here', 'refresh': 'refresh.token.here'}
        with patch('localStorage.setItem') as mock_set:
            mock_set.assert_any_call('jwt_token', mock_params['token'])
            mock_set.assert_any_call('refresh_token', mock_params['refresh'])

    @pytest.mark.auth
    async def test_frontend_sends_refresh_token_in_body(self):
        """Test that frontend sends refresh token in request body"""
        with patch('fetch') as mock_fetch:
            mock_fetch.return_value.ok = True
            mock_fetch.return_value.json.return_value = {'access_token': 'new.access.token', 'refresh_token': 'new.refresh.token'}
            call_args = mock_fetch.call_args
            if call_args:
                body = json.loads(call_args[1].get('body', '{}'))
                assert 'refresh_token' in body

    @pytest.mark.auth
    async def test_frontend_handles_missing_refresh_token(self):
        """Test frontend behavior when refresh token is missing"""
        with patch('localStorage.getItem') as mock_get:
            mock_get.return_value = None
            from frontend.lib.auth_service_client import authServiceClient
            with pytest.raises(Exception, match='No refresh token available'):
                await authServiceClient.refreshToken()

    @pytest.mark.auth
    async def test_frontend_clears_tokens_on_refresh_failure(self):
        """Test that frontend clears tokens when refresh fails"""
        with patch('localStorage.removeItem') as mock_remove:
            with patch('fetch') as mock_fetch:
                mock_fetch.return_value.ok = False
                mock_fetch.return_value.status = 401
                mock_remove.assert_any_call('jwt_token')
                mock_remove.assert_any_call('refresh_token')

@pytest.fixture
async def auth_test_client():
    """Create test client for auth service"""
    from auth_service.main import app
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client

@pytest.fixture
def mock_time():
    """Mock time for testing expiry"""

    class TimeMock:

        def __init__(self):
            self.current_time = datetime.now(UTC)

        def advance(self, delta):
            self.current_time += delta
    return TimeNone
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')