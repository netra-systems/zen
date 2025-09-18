"""Empty docstring."""
WebSocket JWT Authentication Regression Test
Tests for the JWT authentication issues identified in staging.

This test reproduces and verifies fixes for:
    1. JWT secret mismatch between auth service and backend
2. Misleading error messages when JWT validation fails
3. Dangerous fallback to singleton pattern
"""Empty docstring."""
import pytest
import jwt
import asyncio
import websockets
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
from fastapi import WebSocket
from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor

@pytest.mark.e2e
class JWTSecretMismatchTests:
    "Test JWT secret mismatch scenarios and error reporting."""

    @pytest.mark.asyncio
    async def test_jwt_extraction_vs_validation_error_messages(self):
    """"

        Test that error messages correctly differentiate between:
        - JWT not found in headers/subprotocols (extraction failure)
        - JWT found but invalid (validation failure)
        
        extractor = UserContextExtractor()
        websocket_no_jwt = Mock(spec=WebSocket)
        websocket_no_jwt.headers = {}
        token = extractor.extract_jwt_from_websocket(websocket_no_jwt)
        assert token is None, "'Should return None when no JWT present'"
        signing_secret = 'auth_service_secret'
        validation_secret = 'backend_service_secret'
        payload = {'sub': 'test_user_123', 'exp': datetime.now(UTC) + timedelta(hours=1), 'iat': datetime.now(UTC), 'permissions': ['read', 'write'], 'roles': ['user']}
        token = jwt.encode(payload, signing_secret, algorithm='HS256')
        websocket_with_jwt = Mock(spec=WebSocket)
        websocket_with_jwt.headers = {'authorization': f'Bearer {token}'}
        extracted_token = extractor.extract_jwt_from_websocket(websocket_with_jwt)
        assert extracted_token == token, "'Should extract JWT from Authorization header'"
        extractor.jwt_secret_key = validation_secret
        decoded = await extractor.validate_and_decode_jwt(extracted_token)
        assert decoded is None, "'Should fail validation with wrong secret'"

    @pytest.mark.asyncio
    async def test_environment_specific_jwt_secret_loading(self):
        ""Test that environment-specific JWT secrets are loaded correctly.""

        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'JWT_SECRET_STAGING': 'staging_specific_secret_123', 'JWT_SECRET_KEY': 'generic_secret_456'}.get(key, default)
            extractor = UserContextExtractor()
            assert extractor.jwt_secret_key == 'staging_specific_secret_123'
            mock_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'production', 'JWT_SECRET_PRODUCTION': 'prod_specific_secret_789', 'JWT_SECRET_KEY': 'generic_secret_456'}.get(key, default)
            extractor = UserContextExtractor()
            assert extractor.jwt_secret_key == 'prod_specific_secret_789'

    @pytest.mark.asyncio
    async def test_jwt_validation_with_correct_secret(self):
        Test that JWT validation succeeds when secrets match.""
        secret = 'shared_secret_123'
        payload = {'sub': 'user_456', 'exp': datetime.now(UTC) + timedelta(hours=1), 'iat': datetime.now(UTC), 'permissions': ['chat', 'read'], 'roles': ['user'], 'session_id': 'session_789'}
        token = jwt.encode(payload, secret, algorithm='HS256')
        extractor = UserContextExtractor()
        extractor.jwt_secret_key = secret
        decoded = await extractor.validate_and_decode_jwt(token)
        assert decoded is not None, "'Should validate successfully with correct secret'"
        assert decoded['sub'] == 'user_456'
        assert decoded['session_id'] == 'session_789'

    @pytest.mark.asyncio
    async def test_websocket_auth_full_flow(self):
        Test the complete WebSocket authentication flow.""
        secret = 'test_secret'
        user_id = 'test_user_123'
        payload = {'sub': user_id, 'exp': datetime.now(UTC) + timedelta(hours=1), 'iat': datetime.now(UTC), 'permissions': ['chat'], 'roles': ['user']}
        token = jwt.encode(payload, secret, algorithm='HS256')
        websocket = Mock(spec=WebSocket)
        websocket.headers = {'authorization': f'Bearer {token}', 'user-agent': 'TestClient/1.0', 'origin': 'http://localhost:3000', 'host': 'localhost:8000'}
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'testing', 'JWT_SECRET_KEY': secret}.get(key, default)
            extractor = UserContextExtractor()
            try:
                user_context, auth_info = await extractor.extract_user_context_from_websocket(websocket)
                assert user_context.user_id == user_id
                assert user_context.websocket_connection_id.startswith(f'ws_{user_id[:8]}')
                assert auth_info['user_id'] == user_id
                assert 'chat' in auth_info['permissions']
                assert 'user' in auth_info['roles']
                assert auth_info['client_info']['user_agent'] == 'TestClient/1.0'
            except Exception as e:
                pytest.fail(f'Should not raise exception with valid JWT: {e}')

    @pytest.mark.asyncio
    async def test_websocket_auth_with_subprotocol_jwt(self):
        Test JWT extraction from WebSocket subprotocol.""
        import base64
        secret = 'test_secret'
        user_id = 'subprotocol_user'
        payload = {'sub': user_id, 'exp': datetime.now(UTC) + timedelta(hours=1), 'iat': datetime.now(UTC)}
        token = jwt.encode(payload, secret, algorithm='HS256')
        encoded_token = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
        websocket = Mock(spec=WebSocket)
        websocket.headers = {'sec-websocket-protocol': f'jwt.{encoded_token}, other-protocol'}
        extractor = UserContextExtractor()
        extracted = extractor.extract_jwt_from_websocket(websocket)
        assert extracted == token, "'Should extract JWT from subprotocol'"

    @pytest.mark.asyncio
    async def test_error_message_clarity(self):
    """Empty docstring."""
        Test that error messages clearly indicate the actual problem.
        This is the key issue - the error says No JWT found when it's actually Invalid JWT.'
""
        from fastapi import HTTPException
        secret_auth = 'auth_secret'
        secret_backend = 'backend_secret'
        payload = {'sub': 'user_123', 'exp': datetime.now(UTC) + timedelta(hours=1), 'iat': datetime.now(UTC)}
        token = jwt.encode(payload, secret_auth, algorithm='HS256')
        websocket = Mock(spec=WebSocket)
        websocket.headers = {'authorization': f'Bearer {token}'}
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'JWT_SECRET_KEY': secret_backend}.get(key, default)
            extractor = UserContextExtractor()
            with pytest.raises(HTTPException) as exc_info:
                await extractor.extract_user_context_from_websocket(websocket)
            assert exc_info.value.status_code == 401

@pytest.mark.e2e
class SingletonFallbackTests:
    Test that dangerous singleton fallback is removed.""

    @pytest.mark.asyncio
    async def test_no_singleton_fallback_on_auth_failure(self):
        Verify that auth failure doesn't fall back to insecure singleton pattern.""'
        pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
"""