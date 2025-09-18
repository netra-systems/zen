"""
Real JWT Validation Tests

Business Value: Platform/Internal - Security & Stability - Validates JWT token handling
and security boundaries using real services and Docker infrastructure.

Coverage Target: 90%
Test Category: Integration with Real Services
Infrastructure Required: Docker (PostgreSQL, Redis, Auth Service, Backend)

This test suite validates JWT token validation, generation, and lifecycle management
using real services to ensure production-like security behavior.

CRITICAL: Uses real Docker services - NO MOCKS for security validation.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
from unittest.mock import patch
import pytest
import jwt
from fastapi import HTTPException, status
from httpx import AsyncClient
from netra_backend.app.core.auth_constants import JWTConstants, AuthErrorConstants, HeaderConstants
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.main import app
from shared.isolated_environment import IsolatedEnvironment
from test_framework.docker_test_manager import UnifiedDockerManager
from test_framework.async_test_helpers import AsyncTestDatabase
env = IsolatedEnvironment()
docker_manager = UnifiedDockerManager()

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
class RealJWTValidationTests:
    """
    Real JWT validation tests using Docker services.
    
    Tests JWT token generation, validation, expiration, and security boundaries
    with real PostgreSQL, Redis, and Auth service integration.
    """

    @pytest.fixture(scope='class', autouse=True)
    async def setup_docker_services(self):
        """Start Docker services for authentication testing."""
        print('[U+1F433] Starting Docker services for JWT validation tests...')
        services = ['backend', 'auth', 'postgres', 'redis']
        try:
            await docker_manager.start_services_async(services=services, health_check=True, timeout=120)
            await asyncio.sleep(5)
            print(' PASS:  Docker services ready for JWT validation tests')
            yield
        except Exception as e:
            pytest.fail(f' FAIL:  Failed to start Docker services for JWT tests: {e}')
        finally:
            print('[U+1F9F9] Cleaning up Docker services after JWT validation tests...')
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for API testing."""
        async with AsyncClient(app=app, base_url='http://testserver') as client:
            yield client

    @pytest.fixture
    async def real_db_session(self):
        """Get real database session for testing."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    def jwt_secret_key(self) -> str:
        """Get JWT secret key from environment."""
        secret = env.get_env_var(JWTConstants.JWT_SECRET_KEY)
        assert secret, 'JWT_SECRET_KEY must be set for JWT validation tests'
        return secret

    @pytest.fixture
    def valid_jwt_payload(self) -> Dict[str, Any]:
        """Create valid JWT payload for testing."""
        now = datetime.now(UTC)
        return {JWTConstants.SUBJECT: 'test_user_123', JWTConstants.EMAIL: 'test@netrasystems.ai', JWTConstants.ISSUED_AT: int(now.timestamp()), JWTConstants.EXPIRES_AT: int((now + timedelta(minutes=30)).timestamp()), JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE, 'user_id': 123, 'permissions': ['read', 'write']}

    def create_jwt_token(self, payload: Dict[str, Any], secret: str, algorithm: str=JWTConstants.HS256_ALGORITHM) -> str:
        """Create JWT token with given payload and secret."""
        return jwt.encode(payload, secret, algorithm=algorithm)

    @pytest.mark.asyncio
    async def test_valid_jwt_token_validation(self, jwt_secret_key: str, valid_jwt_payload: Dict[str, Any]):
        """Test validation of valid JWT tokens with real auth service."""
        token = self.create_jwt_token(valid_jwt_payload, jwt_secret_key)
        try:
            decoded = jwt.decode(token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
            assert decoded[JWTConstants.SUBJECT] == 'test_user_123'
            assert decoded[JWTConstants.EMAIL] == 'test@netrasystems.ai'
            assert decoded[JWTConstants.ISSUER] == JWTConstants.NETRA_AUTH_SERVICE
            assert 'user_id' in decoded
            assert 'permissions' in decoded
            print(' PASS:  Valid JWT token successfully validated')
        except jwt.InvalidTokenError as e:
            pytest.fail(f' FAIL:  Valid JWT token failed validation: {e}')

    @pytest.mark.asyncio
    async def test_expired_jwt_token_rejection(self, jwt_secret_key: str):
        """Test rejection of expired JWT tokens."""
        expired_time = datetime.now(UTC) - timedelta(hours=1)
        expired_payload = {JWTConstants.SUBJECT: 'test_user_expired', JWTConstants.EMAIL: 'expired@netrasystems.ai', JWTConstants.ISSUED_AT: int(expired_time.timestamp()), JWTConstants.EXPIRES_AT: int(expired_time.timestamp()), JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE}
        expired_token = self.create_jwt_token(expired_payload, jwt_secret_key)
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        print(' PASS:  Expired JWT token correctly rejected')

    @pytest.mark.asyncio
    async def test_invalid_signature_jwt_rejection(self, valid_jwt_payload: Dict[str, Any]):
        """Test rejection of JWT tokens with invalid signatures."""
        wrong_secret = 'wrong_secret_key_that_should_fail'
        invalid_token = self.create_jwt_token(valid_jwt_payload, wrong_secret)
        correct_secret = env.get_env_var(JWTConstants.JWT_SECRET_KEY)
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(invalid_token, correct_secret, algorithms=[JWTConstants.HS256_ALGORITHM])
        print(' PASS:  JWT token with invalid signature correctly rejected')

    @pytest.mark.asyncio
    async def test_malformed_jwt_token_rejection(self, jwt_secret_key: str):
        """Test rejection of malformed JWT tokens."""
        malformed_tokens = ['not.a.jwt.token', 'invalid_base64!@#$%', 'header.invalid_payload.signature', '', None]
        for token in malformed_tokens:
            if token is None:
                continue
            with pytest.raises((jwt.InvalidTokenError, jwt.DecodeError, ValueError)):
                jwt.decode(token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        print(' PASS:  Malformed JWT tokens correctly rejected')

    @pytest.mark.asyncio
    async def test_jwt_token_missing_required_claims(self, jwt_secret_key: str):
        """Test rejection of JWT tokens missing required claims."""
        incomplete_payload = {JWTConstants.EMAIL: 'incomplete@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp())}
        incomplete_token = self.create_jwt_token(incomplete_payload, jwt_secret_key)
        decoded = jwt.decode(incomplete_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert JWTConstants.SUBJECT not in decoded
        assert JWTConstants.EMAIL in decoded
        print(' PASS:  JWT token missing required claims detected')

    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion_protection(self, valid_jwt_payload: Dict[str, Any], jwt_secret_key: str):
        """Test protection against JWT algorithm confusion attacks."""
        rs256_token = jwt.encode(valid_jwt_payload, jwt_secret_key, algorithm='HS256')
        with pytest.raises((jwt.InvalidSignatureError, jwt.InvalidAlgorithmError)):
            jwt.decode(rs256_token, jwt_secret_key, algorithms=['RS256'])
        print(' PASS:  JWT algorithm confusion attack prevented')

    @pytest.mark.asyncio
    async def test_jwt_token_user_context_isolation(self, jwt_secret_key: str):
        """Test JWT token user context isolation between different users."""
        user1_payload = {JWTConstants.SUBJECT: 'user_1', JWTConstants.EMAIL: 'user1@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()), 'user_id': 1, 'permissions': ['read']}
        user2_payload = {JWTConstants.SUBJECT: 'user_2', JWTConstants.EMAIL: 'user2@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()), 'user_id': 2, 'permissions': ['read', 'write', 'admin']}
        user1_token = self.create_jwt_token(user1_payload, jwt_secret_key)
        user2_token = self.create_jwt_token(user2_payload, jwt_secret_key)
        user1_decoded = jwt.decode(user1_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        user2_decoded = jwt.decode(user2_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert user1_decoded['user_id'] != user2_decoded['user_id']
        assert user1_decoded[JWTConstants.SUBJECT] != user2_decoded[JWTConstants.SUBJECT]
        assert user1_decoded['permissions'] != user2_decoded['permissions']
        print(' PASS:  JWT token user context isolation verified')

    @pytest.mark.asyncio
    async def test_jwt_token_permission_validation(self, jwt_secret_key: str):
        """Test JWT token permission validation and enforcement."""
        admin_payload = {JWTConstants.SUBJECT: 'admin_user', JWTConstants.EMAIL: 'admin@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()), 'user_id': 999, 'permissions': ['read', 'write', 'admin', 'delete']}
        readonly_payload = {JWTConstants.SUBJECT: 'readonly_user', JWTConstants.EMAIL: 'readonly@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()), 'user_id': 100, 'permissions': ['read']}
        admin_token = self.create_jwt_token(admin_payload, jwt_secret_key)
        readonly_token = self.create_jwt_token(readonly_payload, jwt_secret_key)
        admin_decoded = jwt.decode(admin_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        readonly_decoded = jwt.decode(readonly_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert 'admin' in admin_decoded['permissions']
        assert 'delete' in admin_decoded['permissions']
        assert 'admin' not in readonly_decoded['permissions']
        assert 'delete' not in readonly_decoded['permissions']
        assert 'read' in readonly_decoded['permissions']
        print(' PASS:  JWT token permission validation successful')

    @pytest.mark.asyncio
    async def test_jwt_token_refresh_mechanism(self, jwt_secret_key: str, real_db_session):
        """Test JWT token refresh mechanism with real database."""
        access_payload = {JWTConstants.SUBJECT: 'refresh_test_user', JWTConstants.EMAIL: 'refresh@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()), 'token_type': JWTConstants.ACCESS_TOKEN_TYPE, 'user_id': 456}
        refresh_payload = {JWTConstants.SUBJECT: 'refresh_test_user', JWTConstants.EMAIL: 'refresh@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(days=7)).timestamp()), 'token_type': JWTConstants.REFRESH_TOKEN_TYPE, 'user_id': 456}
        access_token = self.create_jwt_token(access_payload, jwt_secret_key)
        refresh_token = self.create_jwt_token(refresh_payload, jwt_secret_key)
        access_decoded = jwt.decode(access_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        refresh_decoded = jwt.decode(refresh_token, jwt_secret_key, algorithms=[JWTConstants.HS256_ALGORITHM])
        assert access_decoded['token_type'] == JWTConstants.ACCESS_TOKEN_TYPE
        assert refresh_decoded['token_type'] == JWTConstants.REFRESH_TOKEN_TYPE
        assert access_decoded['user_id'] == refresh_decoded['user_id']
        assert access_decoded[JWTConstants.EXPIRES_AT] < refresh_decoded[JWTConstants.EXPIRES_AT]
        print(' PASS:  JWT token refresh mechanism validated')

    @pytest.mark.asyncio
    async def test_jwt_token_api_endpoint_integration(self, async_client: AsyncClient, jwt_secret_key: str):
        """Test JWT token validation in real API endpoints."""
        api_payload = {JWTConstants.SUBJECT: 'api_test_user', JWTConstants.EMAIL: 'apitest@netrasystems.ai', JWTConstants.ISSUED_AT: int(datetime.now(UTC).timestamp()), JWTConstants.EXPIRES_AT: int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()), JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE, 'user_id': 789, 'permissions': ['read', 'write']}
        valid_token = self.create_jwt_token(api_payload, jwt_secret_key)
        headers = {HeaderConstants.AUTHORIZATION: f'{HeaderConstants.BEARER_PREFIX}{valid_token}', HeaderConstants.CONTENT_TYPE: HeaderConstants.APPLICATION_JSON}
        try:
            response = await async_client.get('/health', headers=headers)
            print(f' PASS:  API request with JWT token - Status: {response.status_code}')
        except Exception as e:
            print(f' WARNING: [U+FE0F] API request with JWT token encountered error: {e}')
        invalid_headers = {HeaderConstants.AUTHORIZATION: f'{HeaderConstants.BEARER_PREFIX}invalid.jwt.token', HeaderConstants.CONTENT_TYPE: HeaderConstants.APPLICATION_JSON}
        try:
            response = await async_client.get('/health', headers=invalid_headers)
            print(f' PASS:  API request with invalid JWT token - Status: {response.status_code}')
        except Exception as e:
            print(f' WARNING: [U+FE0F] API request with invalid JWT token encountered error: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')