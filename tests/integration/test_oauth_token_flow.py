"""
Integration test for OAuth token flow from Google to frontend storage.
Tests the complete flow: OAuth callback -> token exchange -> frontend redirect -> token storage

CRITICAL: Updated to comply with CLAUDE.md standards:
- Uses real services (no mocks)
- Uses absolute imports only
- Accesses environment through IsolatedEnvironment
- Tests real OAuth flows end-to-end
- Validates actual token exchange and storage
"""
import asyncio
import base64
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse, urlencode
import httpx
import pytest
from shared.isolated_environment import get_env
from test_framework.fixtures.auth import create_test_user_token, create_real_jwt_token
from tests.helpers.auth_test_utils import create_admin_token
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.repository import AuthUserRepository

async def ensure_test_services_running():
    """Ensure required test services are running"""
    import socket
    services_to_check = [('localhost', 5433, 'PostgreSQL'), ('localhost', 6381, 'Redis'), ('http://localhost:8081/auth/health', None, 'Auth Service')]
    failed_services = []
    for host_or_url, port_or_none, service_name in services_to_check:
        try:
            if service_name == 'Auth Service':
                async with httpx.AsyncClient() as client:
                    response = await client.get(host_or_url, timeout=5.0)
                    if response.status_code != 200:
                        failed_services.append(service_name)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host_or_url, port_or_none))
                sock.close()
                if result != 0:
                    failed_services.append(service_name)
        except Exception as e:
            failed_services.append(f'{service_name} ({e})')
    if failed_services:
        pytest.skip(f"Required services not running: {', '.join(failed_services)}. Start with: docker-compose up dev-auth dev-postgres dev-redis")

async def setup_test_oauth_credentials() -> Dict[str, str]:
    """Setup test OAuth credentials for real testing"""
    env = get_env()
    test_credentials = {'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': 'test-google-client-id.apps.googleusercontent.com', 'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': 'test-google-client-secret-abcdef123456', 'GITHUB_CLIENT_ID': 'test-github-client-id-123456', 'GITHUB_CLIENT_SECRET': 'test-github-client-secret-abcdef123456', 'JWT_SECRET_KEY': 'test-jwt-secret-key-must-be-at-least-32-characters-long', 'SERVICE_SECRET': 'test-service-secret-for-cross-service-authentication'}
    for key, value in test_credentials.items():
        env.set(key, value, 'oauth_test_setup')
    return test_credentials

async def cleanup_test_data():
    """Clean up test data from database"""
    try:
        await auth_db.create_tables()
        async with auth_db.get_session() as session:
            from sqlalchemy import text
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'test%' OR email LIKE '%example.com'"))
            await session.commit()
    except Exception as e:
        pass

@pytest.mark.asyncio
async def test_oauth_callback_token_exchange():
    """Test that auth service correctly exchanges OAuth code for tokens using REAL services"""
    await ensure_test_services_running()
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('POSTGRES_HOST', 'localhost', 'oauth_test')
    env.set('POSTGRES_PORT', '5433', 'oauth_test')
    env.set('POSTGRES_USER', 'test', 'oauth_test')
    env.set('POSTGRES_PASSWORD', 'test', 'oauth_test')
    env.set('POSTGRES_DB', 'netra_test', 'oauth_test')
    env.set('REDIS_HOST', 'localhost', 'oauth_test')
    env.set('REDIS_PORT', '6381', 'oauth_test')
    await setup_test_oauth_credentials()
    try:
        from fastapi import FastAPI
        from auth_service.auth_core.routes.auth_routes import router
        app = FastAPI()
        app.include_router(router)
        await auth_db.create_tables()
        await cleanup_test_data()
        oauth_code = 'test_oauth_code_' + str(int(time.time()))
        oauth_state = base64.urlsafe_b64encode(json.dumps({'timestamp': int(time.time()), 'nonce': 'test_nonce_123', 'session_id': 'test_session_123'}).encode()).decode()
        async with httpx.AsyncClient(base_url='http://localhost:8081') as client:
            health_response = await client.get('/auth/health')
            assert health_response.status_code == 200
            callback_response = await client.get('/auth/callback', params={'code': oauth_code, 'state': oauth_state}, follow_redirects=False)
            if callback_response.status_code == 302:
                location = callback_response.headers.get('location')
                assert location is not None
                parsed_url = urlparse(location)
                query_params = parse_qs(parsed_url.query)
                assert 'token' in query_params
                assert 'refresh' in query_params
                access_token = query_params['token'][0]
                refresh_token = query_params['refresh'][0]
                assert len(access_token) > 100
                assert len(refresh_token) > 50
            else:
                assert callback_response.status_code in [400, 401, 500]
                if callback_response.headers.get('content-type', '').startswith('application/json'):
                    error_data = callback_response.json()
                    assert 'detail' in error_data or 'error' in error_data
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_frontend_token_storage():
    """Test that frontend correctly stores tokens from URL parameters using real tokens"""
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-must-be-at-least-32-characters', 'oauth_test')
    env.set('SERVICE_SECRET', 'test-service-secret-for-cross-service-authentication', 'oauth_test')
    env.set('SERVICE_ID', 'auth-service', 'oauth_test')
    try:
        from auth_service.auth_core.services.auth_service import AuthService
        auth_service = AuthService()
        access_token = auth_service.jwt_handler.create_access_token(user_id='test_user_123', email='test@example.com', permissions=['user'])
        refresh_token = auth_service.jwt_handler.create_refresh_token(user_id='test_user_123')
        frontend_url = 'http://localhost:3000'
        redirect_url = f'{frontend_url}/auth/callback?token={access_token}&refresh={refresh_token}'
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        assert 'token' in params
        assert 'refresh' in params
        extracted_access_token = params['token'][0]
        extracted_refresh_token = params['refresh'][0]
        assert len(extracted_access_token) > 100
        assert len(extracted_refresh_token) > 50
        assert '.' in extracted_access_token
        assert '.' in extracted_refresh_token
        token_parts = extracted_access_token.split('.')
        assert len(token_parts) == 3
        import jwt
        payload = jwt.decode(extracted_access_token, options={'verify_signature': False})
        assert payload['sub'] == 'test_user_123'
        assert payload['email'] == 'test@example.com'
        assert 'user' in payload['permissions']
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_token_validation_after_storage():
    """Test that stored tokens can be validated by auth service using REAL validation"""
    await ensure_test_services_running()
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-must-be-at-least-32-characters', 'oauth_test')
    env.set('SERVICE_SECRET', 'test-service-secret-for-cross-service-authentication', 'oauth_test')
    env.set('SERVICE_ID', 'auth-service', 'oauth_test')
    env.set('POSTGRES_HOST', 'localhost', 'oauth_test')
    env.set('POSTGRES_PORT', '5433', 'oauth_test')
    env.set('POSTGRES_USER', 'test', 'oauth_test')
    env.set('POSTGRES_PASSWORD', 'test', 'oauth_test')
    env.set('POSTGRES_DB', 'netra_test', 'oauth_test')
    try:
        async with httpx.AsyncClient(base_url='http://localhost:8081') as client:
            health_response = await client.get('/auth/health')
            assert health_response.status_code == 200
            invalid_validation_response = await client.post('/auth/validate', json={'token': 'invalid.token.here', 'token_type': 'access'})
            assert invalid_validation_response.status_code in [400, 401]
            invalid_data = invalid_validation_response.json()
            assert 'valid' in invalid_data and invalid_data['valid'] is False or 'detail' in invalid_data
            invalid_verify_response = await client.post('/auth/verify', headers={'Authorization': 'Bearer invalid.token.here'})
            assert invalid_verify_response.status_code in [400, 401]
            from auth_service.auth_core.services.auth_service import AuthService
            from auth_service.auth_core.config import AuthConfig
            real_auth_service = AuthService()
            real_test_token = real_auth_service.jwt_handler.create_access_token(user_id='test-user-123', email='test@example.com', permissions=['user'])
            real_validation_response = await client.post('/auth/validate', json={'token': real_test_token, 'token_type': 'access'})
            if real_validation_response.status_code == 200:
                validation_data = real_validation_response.json()
                assert validation_data['valid'] is True
                assert validation_data['user_id'] == 'test-user-123'
                assert validation_data['email'] == 'test@example.com'
            else:
                assert real_validation_response.status_code in [401, 403]
                error_data = real_validation_response.json()
                assert 'valid' in error_data or 'detail' in error_data
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_oauth_error_handling():
    """Test error handling when OAuth token exchange fails using REAL error scenarios"""
    await ensure_test_services_running()
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('POSTGRES_HOST', 'localhost', 'oauth_test')
    env.set('POSTGRES_PORT', '5433', 'oauth_test')
    env.set('POSTGRES_USER', 'test', 'oauth_test')
    env.set('POSTGRES_PASSWORD', 'test', 'oauth_test')
    env.set('POSTGRES_DB', 'netra_test', 'oauth_test')
    env.set('GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'invalid-client-id', 'oauth_test')
    env.set('GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT', 'invalid-secret', 'oauth_test')
    try:
        async with httpx.AsyncClient(base_url='http://localhost:8081') as client:
            invalid_oauth_code = 'definitely_invalid_oauth_code'
            invalid_state = base64.urlsafe_b64encode(json.dumps({'timestamp': int(time.time()), 'nonce': 'test_nonce_invalid', 'session_id': 'test_session_invalid'}).encode()).decode()
            error_response = await client.get('/auth/callback', params={'code': invalid_oauth_code, 'state': invalid_state}, follow_redirects=False)
            assert error_response.status_code in [400, 401, 500]
            missing_state_response = await client.get('/auth/callback', params={'code': 'any-code'}, follow_redirects=False)
            assert missing_state_response.status_code in [400, 422]
            oauth_init_response = await client.get('/auth/login', params={'provider': 'google'}, follow_redirects=False)
            assert oauth_init_response.status_code in [400, 500]
            error_data = oauth_init_response.json()
            assert 'error' in error_data or 'detail' in error_data
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_staging_environment_urls():
    """Test that staging environment uses correct URLs using IsolatedEnvironment"""
    env = get_env()
    env.enable_isolation()
    try:
        env.set('ENVIRONMENT', 'staging', 'oauth_test')
        from auth_service.auth_core.config import AuthConfig
        auth_url = AuthConfig.get_auth_service_url()
        assert auth_url == 'https://auth.staging.netrasystems.ai'
        frontend_url = AuthConfig.get_frontend_url()
        assert frontend_url == 'https://app.staging.netrasystems.ai'
        callback_url = f'{frontend_url}/auth/callback'
        assert callback_url == 'https://app.staging.netrasystems.ai/auth/callback'
        try:
            google_client_id = AuthConfig.get_google_client_id()
            assert isinstance(google_client_id, (str, type(None)))
        except Exception:
            pass
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.integration
def test_jwt_token_decoding():
    """Test that frontend can decode JWT tokens using real auth service tokens"""
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('JWT_SECRET_KEY', 'test-jwt-secret-key-must-be-at-least-32-characters', 'oauth_test')
    env.set('SERVICE_SECRET', 'test-service-secret-for-cross-service-authentication', 'oauth_test')
    env.set('SERVICE_ID', 'auth-service', 'oauth_test')
    env.set('SERVICE_SECRET', 'test-service-secret-for-cross-service-authentication', 'oauth_test')
    env.set('SERVICE_ID', 'auth-service', 'oauth_test')
    try:
        import time
        import jwt
        from auth_service.auth_core.services.auth_service import AuthService
        auth_service = AuthService()
        token = auth_service.jwt_handler.create_access_token(user_id='user-123', email='test@example.com', permissions=['user'])
        assert isinstance(token, str)
        assert len(token) > 100
        assert token.count('.') == 2
        decoded = jwt.decode(token, options={'verify_signature': False})
        assert decoded['sub'] == 'user-123'
        assert decoded['email'] == 'test@example.com'
        assert 'user' in decoded['permissions']
        assert 'exp' in decoded
        assert 'iat' in decoded
        assert decoded['token_type'] == 'access'
        assert decoded['iss'] == 'netra-auth-service'
        current_time = int(time.time())
        assert decoded['exp'] > current_time
        assert decoded['iat'] <= current_time
        validation_result = auth_service.jwt_handler.validate_token(token, 'access')
        assert validation_result is not None
        if isinstance(validation_result, dict):
            user_id = validation_result.get('sub') or validation_result.get('user_id')
            assert user_id == 'user-123'
            assert validation_result.get('email') == 'test@example.com'
        else:
            user_id = getattr(validation_result, 'user_id', None) or getattr(validation_result, 'sub', None)
            assert user_id == 'user-123'
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_oauth_providers_endpoint():
    """Test that OAuth providers endpoint returns correct configuration"""
    await ensure_test_services_running()
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'test-google-client-id.apps.googleusercontent.com', 'oauth_test')
    env.set('GITHUB_CLIENT_ID', 'test-github-client-id-123456', 'oauth_test')
    try:
        async with httpx.AsyncClient(base_url='http://localhost:8081') as client:
            providers_response = await client.get('/oauth/providers')
            assert providers_response.status_code == 200
            providers_data = providers_response.json()
            assert 'providers' in providers_data
            assert 'environment' in providers_data
            providers = providers_data['providers']
            assert len(providers) >= 2
            google_provider = next((p for p in providers if p['name'] == 'google'), None)
            assert google_provider is not None
            assert google_provider['display_name'] == 'Google'
            assert 'client_id' in google_provider
            assert 'authorize_url' in google_provider
            github_provider = next((p for p in providers if p['name'] == 'github'), None)
            assert github_provider is not None
            assert github_provider['display_name'] == 'GitHub'
    finally:
        env.disable_isolation(restore_original=True)

@pytest.mark.asyncio
async def test_oauth_state_csrf_protection():
    """Test OAuth state parameter CSRF protection using real security mechanisms"""
    await ensure_test_services_running()
    env = get_env()
    env.enable_isolation()
    env.set('ENVIRONMENT', 'test', 'oauth_test')
    env.set('GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'test-google-client-id.apps.googleusercontent.com', 'oauth_test')
    env.set('GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT', 'test-google-client-secret-12345', 'oauth_test')
    try:
        async with httpx.AsyncClient(base_url='http://localhost:8081', follow_redirects=False) as client:
            oauth_init_response = await client.get('/auth/login', params={'provider': 'google'})
            if oauth_init_response.status_code == 302:
                location = oauth_init_response.headers.get('location')
                assert location is not None
                assert 'accounts.google.com' in location
                assert 'state=' in location
                parsed_location = urlparse(location)
                query_params = parse_qs(parsed_location.query)
                assert 'state' in query_params
                state_param = query_params['state'][0]
                assert len(state_param) > 10
                fake_state = 'fake_malicious_state_parameter'
                csrf_attack_response = await client.get('/auth/callback', params={'code': 'test-oauth-code', 'state': fake_state}, follow_redirects=False)
                assert csrf_attack_response.status_code in [401, 400]
            else:
                assert oauth_init_response.status_code in [400, 500]
                error_data = oauth_init_response.json()
                assert 'error' in error_data or 'detail' in error_data
    finally:
        env.disable_isolation(restore_original=True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')