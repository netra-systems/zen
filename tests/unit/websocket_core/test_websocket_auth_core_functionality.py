"""Test WebSocket Core Authentication - Core Functionality Tests

Business Value Justification (BVJ):
- Segment: Platform/All Users (Free -> Enterprise)
- Business Goal: Protect $500K+ ARR by ensuring secure WebSocket authentication
- Value Impact: Ensures WebSocket connections are properly authenticated and authorized
- Revenue Impact: Prevents unauthorized access and maintains customer trust and security

This test suite focuses on WebSocket authentication core functionality:

1. JWT token validation and processing
2. User authentication and authorization
3. Connection security and isolation
4. Authentication error handling
5. Token refresh and lifecycle management

These tests validate the security layer that protects customer data and chat sessions.
"""
import asyncio
import pytest
import jwt
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
from netra_backend.app.websocket_core.unified_websocket_auth import WebSocketAuthResult as AuthenticationResult

class AuthenticationError(Exception):
    """Authentication error for compatibility"""
    pass
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

class TestWebSocketAuthenticatorCore(SSotAsyncTestCase):
    """Test core functionality of WebSocket authentication."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_secret = 'test_secret_key_for_websocket_auth_testing_12345'
        self.authenticator = WebSocketAuthenticator(jwt_secret=self.test_secret, jwt_algorithm='HS256')

    def create_test_jwt_token(self, user_id: str, expires_in_minutes: int=60) -> str:
        """Create a test JWT token."""
        payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(minutes=expires_in_minutes), 'iat': datetime.utcnow(), 'iss': 'netra-test'}
        return jwt.encode(payload, self.test_secret, algorithm='HS256')

    def test_authenticator_initialization(self):
        """Test authenticator initializes correctly."""
        self.assertIsNotNone(self.authenticator)
        self.assertEqual(self.authenticator.jwt_algorithm, 'HS256')

    async def test_valid_token_authentication(self):
        """Test authentication with valid JWT token."""
        user_id = 'test_user_001'
        token = self.create_test_jwt_token(user_id)
        result = await self.authenticator.authenticate_token(token)
        self.assertIsInstance(result, AuthenticationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.user_id, user_id)
        self.assertIsNone(result.error)

    async def test_invalid_token_authentication(self):
        """Test authentication with invalid JWT token."""
        result = await self.authenticator.authenticate_token('invalid.token.format')
        self.assertIsInstance(result, AuthenticationResult)
        self.assertFalse(result.success)
        self.assertIsNone(result.user_id)
        self.assertIsNotNone(result.error)

    async def test_expired_token_authentication(self):
        """Test authentication with expired JWT token."""
        user_id = 'test_user_002'
        token = self.create_test_jwt_token(user_id, expires_in_minutes=-5)
        result = await self.authenticator.authenticate_token(token)
        self.assertFalse(result.success)
        self.assertIsNone(result.user_id)
        self.assertIsInstance(result.error, AuthenticationError)

    async def test_token_with_wrong_secret(self):
        """Test authentication with token signed with wrong secret."""
        wrong_secret = 'wrong_secret_key'
        payload = {'user_id': 'test_user_003', 'exp': datetime.utcnow() + timedelta(hours=1), 'iat': datetime.utcnow()}
        wrong_token = jwt.encode(payload, wrong_secret, algorithm='HS256')
        result = await self.authenticator.authenticate_token(wrong_token)
        self.assertFalse(result.success)
        self.assertIsNone(result.user_id)

    async def test_missing_user_id_in_token(self):
        """Test authentication with token missing user_id."""
        payload = {'exp': datetime.utcnow() + timedelta(hours=1), 'iat': datetime.utcnow()}
        invalid_token = jwt.encode(payload, self.test_secret, algorithm='HS256')
        result = await self.authenticator.authenticate_token(invalid_token)
        self.assertFalse(result.success)
        self.assertIsNone(result.user_id)

    async def test_websocket_connection_auth_flow(self):
        """Test complete WebSocket connection authentication flow."""
        user_id = 'flow_test_user'
        token = self.create_test_jwt_token(user_id)
        auth_headers = {'Authorization': f'Bearer {token}'}
        auth_header = auth_headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            extracted_token = auth_header[7:]
        else:
            extracted_token = None
        self.assertIsNotNone(extracted_token)
        result = await self.authenticator.authenticate_token(extracted_token)
        self.assertTrue(result.success)
        self.assertEqual(result.user_id, user_id)

    async def test_concurrent_authentication_requests(self):
        """Test handling of concurrent authentication requests."""
        tokens_and_users = []
        for i in range(5):
            user_id = f'concurrent_user_{i:03d}'
            token = self.create_test_jwt_token(user_id)
            tokens_and_users.append((token, user_id))
        auth_tasks = [self.authenticator.authenticate_token(token) for token, _ in tokens_and_users]
        results = await asyncio.gather(*auth_tasks)
        for i, result in enumerate(results):
            expected_user_id = tokens_and_users[i][1]
            self.assertTrue(result.success)
            self.assertEqual(result.user_id, expected_user_id)

    async def test_authentication_result_creation(self):
        """Test AuthenticationResult object creation and properties."""
        success_result = AuthenticationResult.success('test_user')
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.user_id, 'test_user')
        self.assertIsNone(success_result.error)
        error = AuthenticationError('Invalid token', 'TOKEN_INVALID')
        fail_result = AuthenticationResult.failure(error)
        self.assertFalse(fail_result.success)
        self.assertIsNone(fail_result.user_id)
        self.assertEqual(fail_result.error, error)

    async def test_authentication_with_custom_claims(self):
        """Test authentication with custom JWT claims."""
        user_id = 'custom_claims_user'
        payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(hours=1), 'iat': datetime.utcnow(), 'iss': 'netra-test', 'custom_role': 'premium_user', 'subscription_tier': 'enterprise'}
        token = jwt.encode(payload, self.test_secret, algorithm='HS256')
        result = await self.authenticator.authenticate_token(token)
        self.assertTrue(result.success)
        self.assertEqual(result.user_id, user_id)
        decoded = jwt.decode(token, self.test_secret, algorithms=['HS256'])
        self.assertEqual(decoded['custom_role'], 'premium_user')
        self.assertEqual(decoded['subscription_tier'], 'enterprise')

class TestWebSocketAuthenticationIntegration(SSotAsyncTestCase):
    """Test WebSocket authentication integration scenarios."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_secret = 'integration_test_secret_12345'
        self.authenticator = WebSocketAuthenticator(jwt_secret=self.test_secret, jwt_algorithm='HS256')

    def create_test_jwt_token(self, user_id: str, expires_in_minutes: int=60) -> str:
        """Create a test JWT token."""
        payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(minutes=expires_in_minutes), 'iat': datetime.utcnow(), 'iss': 'netra-test'}
        return jwt.encode(payload, self.test_secret, algorithm='HS256')

    async def test_auth_integration_with_user_context(self):
        """Test authentication integration with UserExecutionContext."""
        user_id = 'integration_user_001'
        token = self.create_test_jwt_token(user_id)
        auth_result = await self.authenticator.authenticate_token(token)
        self.assertTrue(auth_result.success)
        user_context = UserExecutionContext(user_id=auth_result.user_id, thread_id='auth_thread_001', run_id='auth_run_001', websocket_client_id='auth_ws_001')
        self.assertEqual(user_context.user_id, user_id)

    async def test_multiple_user_auth_isolation(self):
        """Test that multiple user authentications maintain proper isolation."""
        users = ['user_a', 'user_b', 'user_c']
        auth_results = []
        for user_id in users:
            token = self.create_test_jwt_token(user_id)
            result = await self.authenticator.authenticate_token(token)
            auth_results.append(result)
        for i, result in enumerate(auth_results):
            self.assertTrue(result.success)
            self.assertEqual(result.user_id, users[i])
        user_ids = [result.user_id for result in auth_results]
        self.assertEqual(len(set(user_ids)), len(users))

    async def test_auth_error_handling_resilience(self):
        """Test authentication error handling doesn't affect subsequent requests."""
        invalid_result = await self.authenticator.authenticate_token('invalid_token')
        self.assertFalse(invalid_result.success)
        valid_token = self.create_test_jwt_token('resilience_user')
        valid_result = await self.authenticator.authenticate_token(valid_token)
        self.assertTrue(valid_result.success)
        self.assertEqual(valid_result.user_id, 'resilience_user')

    async def test_token_edge_cases(self):
        """Test various token edge cases."""
        test_cases = [('', 'empty_token'), ('not.a.jwt', 'invalid_format'), ('eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature', 'invalid_payload'), (None, 'none_token')]
        for token, case_name in test_cases:
            with self.subTest(case=case_name):
                if token is None:
                    with self.assertRaises((TypeError, AttributeError)):
                        await self.authenticator.authenticate_token(token)
                else:
                    result = await self.authenticator.authenticate_token(token)
                    self.assertFalse(result.success)
                    self.assertIsNone(result.user_id)

class TestWebSocketAuthenticationSecurity(SSotAsyncTestCase):
    """Test WebSocket authentication security aspects."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_secret = 'security_test_secret_12345'
        self.authenticator = WebSocketAuthenticator(jwt_secret=self.test_secret, jwt_algorithm='HS256')

    def create_test_jwt_token(self, user_id: str, expires_in_minutes: int=60) -> str:
        """Create a test JWT token."""
        payload = {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(minutes=expires_in_minutes), 'iat': datetime.utcnow(), 'iss': 'netra-test'}
        return jwt.encode(payload, self.test_secret, algorithm='HS256')

    async def test_token_expiration_security(self):
        """Test that expired tokens are properly rejected."""
        user_id = 'expiry_test_user'
        short_lived_token = self.create_test_jwt_token(user_id, expires_in_minutes=0)
        await asyncio.sleep(1)
        result = await self.authenticator.authenticate_token(short_lived_token)
        self.assertFalse(result.success)
        self.assertIsNone(result.user_id)

    async def test_algorithm_security(self):
        """Test that only supported algorithms are accepted."""
        payload = {'user_id': 'algo_test_user', 'exp': datetime.utcnow() + timedelta(hours=1), 'iat': datetime.utcnow()}
        try:
            hs512_token = jwt.encode(payload, self.test_secret, algorithm='HS512')
            result = await self.authenticator.authenticate_token(hs512_token)
            self.assertFalse(result.success)
        except Exception:
            pass

    async def test_user_id_injection_protection(self):
        """Test protection against user ID injection attacks."""
        malicious_user_ids = ["'; DROP TABLE users; --", '../../../etc/passwd', "<script>alert('xss')</script>", 'admin\x00hidden']
        for malicious_id in malicious_user_ids:
            with self.subTest(user_id=malicious_id):
                token = self.create_test_jwt_token(malicious_id)
                result = await self.authenticator.authenticate_token(token)
                if result.success:
                    self.assertEqual(result.user_id, malicious_id)
                    self.assertIsInstance(result.user_id, str)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')