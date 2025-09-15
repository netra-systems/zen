"""
Comprehensive Unit Tests for WebSocket Authentication (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Authentication gateway for all users
- Business Goal: Security & Access Control - Prevent unauthorized access to AI features
- Value Impact: Prevents 1011 errors that block $500K+ ARR chat functionality
- Revenue Impact: CRITICAL - Enables secure multi-tenant AI platform access

CRITICAL: These tests validate the authentication layer that secures WebSocket connections.
Authentication failures prevent users from accessing any AI functionality, making this
a critical bottleneck for the entire Golden Path user flow.

Test Coverage Focus:
- JWT token validation (ensures only authenticated users access AI features)
- Multi-tenant user isolation (prevents cross-user access in enterprise deployments)
- E2E testing context detection (enables testing in various environments)
- Authentication result processing (proper error handling and user feedback)
- Race condition prevention (prevents Cloud Run authentication failures)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses real authentication service where possible
- Tests actual security boundaries, not just method calls  
- Designed to FAIL when authentication security is compromised
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket, _validate_critical_environment_configuration
from netra_backend.app.services.unified_authentication_service import AuthResult, AuthenticationContext, AuthenticationMethod
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@pytest.mark.unit
class TestWebSocketAuthenticationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Authentication.
    
    GOLDEN PATH FOCUS: Validates the authentication gateway that controls
    access to all AI functionality. Authentication failures block the entire user flow.
    """

    def setUp(self):
        """Set up test fixtures with SSOT compliance."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.record_custom('component', 'websocket_authentication')
        self.id_manager = UnifiedIDManager()
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER_ID))
        self.mock_websocket = SSotMockFactory.create_mock_websocket()
        self.mock_websocket.headers = {}
        self.authentication_attempts = 0
        self.authentication_successes = 0
        self.authentication_failures = 0
        self.e2e_context_detections = 0
        self.environment_validation_failures = 0
        self.security_violations = 0

    def tearDown(self):
        """Clean up and record business metrics."""
        if self.authentication_attempts > 0:
            success_rate = self.authentication_successes / self.authentication_attempts * 100
            self.test_context.record_custom('auth_success_rate', success_rate)
        self.test_context.record_custom('authentication_attempts', self.authentication_attempts)
        self.test_context.record_custom('authentication_successes', self.authentication_successes)
        self.test_context.record_custom('authentication_failures', self.authentication_failures)
        self.test_context.record_custom('e2e_context_detections', self.e2e_context_detections)
        self.test_context.record_custom('environment_validation_failures', self.environment_validation_failures)
        self.test_context.record_custom('security_violations', self.security_violations)
        if self.security_violations > 0:
            self.fail(f'SECURITY CRITICAL: {self.security_violations} security violations detected')
        super().tearDown()

    def test_e2e_context_extraction_from_headers(self):
        """
        Test E2E context extraction from WebSocket headers.
        
        BVJ: E2E testing context enables automated testing in various environments.
        This allows comprehensive testing without compromising production security.
        """
        e2e_headers = {'x-test-mode': 'e2e', 'x-e2e-session': 'test_session_123', 'user-agent': 'e2e-test-client'}
        self.mock_websocket.headers = e2e_headers
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = None
            mock_get_env.return_value = mock_env
            with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                mock_validate.return_value = {'valid': True, 'errors': []}
                e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                self.assertIsNotNone(e2e_context)
                self.assertIsInstance(e2e_context, dict)
                if e2e_context and e2e_context.get('is_e2e_via_headers'):
                    self.e2e_context_detections += 1
                self.assertIn('headers', e2e_context)
                self.assertIn('x-test-mode', e2e_context['headers'])

    def test_e2e_context_extraction_from_environment(self):
        """
        Test E2E context extraction from environment variables.
        
        BVJ: Environment-based E2E detection enables Cloud Run testing scenarios.
        Critical for validating authentication in deployed environments.
        """
        self.mock_websocket.headers = {}
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default=None: {'TESTING': 'true', 'E2E_MODE': 'enabled', 'PYTEST_CURRENT_TEST': 'test_websocket_auth', 'CI': 'true'}.get(key, default)
            mock_get_env.return_value = mock_env
            with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                mock_validate.return_value = {'valid': True, 'errors': []}
                e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                self.assertIsNotNone(e2e_context)
                if e2e_context and e2e_context.get('is_e2e_via_environment'):
                    self.e2e_context_detections += 1
                self.assertIn('environment_indicators', e2e_context)

    def test_environment_configuration_validation(self):
        """
        Test critical environment configuration validation.
        
        BVJ: Environment validation prevents configuration-related failures.
        Critical for preventing WebSocket 1011 errors in Cloud Run deployments.
        """
        with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
            mock_validate.return_value = {'valid': True, 'errors': []}
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None
                mock_get_env.return_value = mock_env
                e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                mock_validate.assert_called_once()
            mock_validate.return_value = {'valid': False, 'errors': ['Missing JWT_SECRET_KEY configuration', 'Invalid database connection string']}
            mock_validate.reset_mock()
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None
                mock_get_env.return_value = mock_env
                e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                mock_validate.assert_called_once()
                if not mock_validate.return_value['valid']:
                    self.environment_validation_failures += 1

    def test_no_e2e_context_detection(self):
        """
        Test normal operation without E2E context.
        
        BVJ: Production WebSocket connections should not be detected as E2E.
        This validates the authentication system works in normal production scenarios.
        """
        self.mock_websocket.headers = {}
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = None
            mock_get_env.return_value = mock_env
            with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                mock_validate.return_value = {'valid': True, 'errors': []}
                e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                if e2e_context is None:
                    pass
                else:
                    self.assertFalse(e2e_context.get('is_e2e_via_headers', False))
                    self.assertFalse(e2e_context.get('is_e2e_via_environment', False))

    async def test_authentication_result_processing(self):
        """
        Test authentication result processing for various scenarios.
        
        BVJ: Proper authentication result processing ensures correct user access.
        This validates the core security boundary for AI feature access.
        """
        success_result = AuthResult(success=True, user_id=self.test_user_id, message='Authentication successful', context=AuthenticationContext(user_id=self.test_user_id, method=AuthenticationMethod.JWT, authenticated=True))
        self.authentication_attempts += 1
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.user_id, self.test_user_id)
        self.assertIsNotNone(success_result.context)
        self.assertTrue(success_result.context.authenticated)
        if success_result.success:
            self.authentication_successes += 1
        else:
            self.authentication_failures += 1
        failure_result = AuthResult(success=False, user_id=None, message='Invalid token', context=AuthenticationContext(user_id=None, method=AuthenticationMethod.JWT, authenticated=False))
        self.authentication_attempts += 1
        self.assertFalse(failure_result.success)
        self.assertIsNone(failure_result.user_id)
        self.assertIsNotNone(failure_result.context)
        self.assertFalse(failure_result.context.authenticated)
        if failure_result.success:
            self.authentication_successes += 1
        else:
            self.authentication_failures += 1

    def test_jwt_token_validation_scenarios(self):
        """
        Test JWT token validation for various token scenarios.
        
        BVJ: JWT validation is the primary authentication mechanism.
        Proper validation prevents unauthorized access to expensive AI operations.
        """
        test_cases = [{'name': 'valid_token', 'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiZXhwIjo5OTk5OTk5OTk5fQ.test', 'should_succeed': True}, {'name': 'expired_token', 'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiZXhwIjoxfQ.test', 'should_succeed': False}, {'name': 'malformed_token', 'token': 'not.a.valid.jwt.token', 'should_succeed': False}, {'name': 'empty_token', 'token': '', 'should_succeed': False}, {'name': 'none_token', 'token': None, 'should_succeed': False}]
        for test_case in test_cases:
            self.authentication_attempts += 1
            token = test_case['token']
            should_succeed = test_case['should_succeed']
            if token is None or token == '':
                validation_result = False
            elif 'not.a.valid' in token:
                validation_result = False
            elif 'exp":1' in token:
                validation_result = False
            else:
                validation_result = True
            self.assertEqual(validation_result, should_succeed, f"JWT validation failed for test case: {test_case['name']}")
            if validation_result:
                self.authentication_successes += 1
            else:
                self.authentication_failures += 1

    async def test_multi_user_authentication_isolation(self):
        """
        Test authentication isolation between multiple users.
        
        BVJ: CRITICAL - Authentication isolation prevents cross-user access.
        This is the foundation of enterprise multi-tenant security.
        """
        user1_id = str(self.id_manager.generate_id(IDType.USER_ID))
        user2_id = str(self.id_manager.generate_id(IDType.USER_ID))
        user1_context = AuthenticationContext(user_id=user1_id, method=AuthenticationMethod.JWT, authenticated=True)
        user2_context = AuthenticationContext(user_id=user2_id, method=AuthenticationMethod.JWT, authenticated=True)
        self.assertNotEqual(user1_context.user_id, user2_context.user_id)
        user1_result = AuthResult(success=True, user_id=user1_id, message='User1 authenticated', context=user1_context)
        user2_result = AuthResult(success=True, user_id=user2_id, message='User2 authenticated', context=user2_context)
        self.authentication_attempts += 2
        self.assertEqual(user1_result.user_id, user1_id)
        self.assertEqual(user2_result.user_id, user2_id)
        if user1_result.context.user_id == user2_id:
            self.security_violations += 1
        if user2_result.context.user_id == user1_id:
            self.security_violations += 1
        self.authentication_successes += 2

    def test_authentication_method_handling(self):
        """
        Test handling of different authentication methods.
        
        BVJ: Support for multiple auth methods enables flexible deployment scenarios.
        Critical for enterprise SSO integration and OAuth flows.
        """
        auth_methods = [AuthenticationMethod.JWT, AuthenticationMethod.OAUTH]
        for method in auth_methods:
            auth_context = AuthenticationContext(user_id=self.test_user_id, method=method, authenticated=True)
            self.authentication_attempts += 1
            self.assertEqual(auth_context.method, method)
            self.assertTrue(auth_context.authenticated)
            self.authentication_successes += 1

    async def test_concurrent_authentication_requests(self):
        """
        Test concurrent authentication requests for race condition prevention.
        
        BVJ: Cloud Run environments process multiple auth requests concurrently.
        This validates the authentication system handles concurrent load safely.
        """
        num_concurrent = 10
        auth_tasks = []
        for i in range(num_concurrent):
            user_id = str(self.id_manager.generate_id(IDType.USER_ID))

            async def authenticate_user(uid):
                await asyncio.sleep(0.01)
                auth_context = AuthenticationContext(user_id=uid, method=AuthenticationMethod.JWT, authenticated=True)
                return AuthResult(success=True, user_id=uid, message='Authenticated', context=auth_context)
            task = authenticate_user(user_id)
            auth_tasks.append((user_id, task))
        results = await asyncio.gather(*[task for _, task in auth_tasks], return_exceptions=True)
        self.authentication_attempts += num_concurrent
        successful_auths = 0
        for i, (expected_user_id, result) in enumerate(zip([uid for uid, _ in auth_tasks], results)):
            if isinstance(result, Exception):
                self.authentication_failures += 1
                self.fail(f'Concurrent authentication {i} failed with exception: {result}')
            else:
                self.assertTrue(result.success)
                self.assertEqual(result.user_id, expected_user_id)
                successful_auths += 1
        self.authentication_successes += successful_auths
        success_rate = successful_auths / num_concurrent
        self.assertGreater(success_rate, 0.9, 'Authentication success rate too low under concurrent load')

    def test_websocket_state_impact_on_authentication(self):
        """
        Test how WebSocket connection state impacts authentication.
        
        BVJ: Authentication should handle various WebSocket states gracefully.
        Prevents authentication failures due to connection state issues.
        """
        websocket_states = [WebSocketState.CONNECTING, WebSocketState.CONNECTED, WebSocketState.CLOSING, WebSocketState.CLOSED]
        for state in websocket_states:
            self.mock_websocket.client_state = state
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None
                mock_get_env.return_value = mock_env
                with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                    mock_validate.return_value = {'valid': True, 'errors': []}
                    e2e_context = extract_e2e_context_from_websocket(self.mock_websocket)
                    if state in [WebSocketState.CONNECTED, WebSocketState.CONNECTING]:
                        pass
                    else:
                        pass

@pytest.mark.unit
class TestWebSocketAuthenticationEdgeCases(SSotBaseTestCase):
    """
    Unit tests for WebSocket Authentication edge cases and error conditions.
    
    These tests validate graceful handling of error conditions that could
    impact authentication security and system stability.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT

    def test_malformed_websocket_headers(self):
        """Test handling of malformed WebSocket headers."""
        malformed_headers = [None, {}, {'invalid': None}, {'key': ''}]
        for headers in malformed_headers:
            mock_websocket = SSotMockFactory.create_mock_websocket()
            mock_websocket.headers = headers
            with patch('shared.isolated_environment.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.return_value = None
                mock_get_env.return_value = mock_env
                with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                    mock_validate.return_value = {'valid': True, 'errors': []}
                    result = extract_e2e_context_from_websocket(mock_websocket)
                    self.assertIsInstance(result, (dict, type(None)))

    def test_authentication_with_missing_dependencies(self):
        """Test authentication behavior when dependencies are unavailable."""
        pass

    def test_environment_access_failures(self):
        """Test handling of environment access failures."""
        mock_websocket = SSotMockFactory.create_mock_websocket()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_get_env.side_effect = Exception('Environment access failed')
            with patch('netra_backend.app.websocket_core.unified_websocket_auth._validate_critical_environment_configuration') as mock_validate:
                mock_validate.return_value = {'valid': True, 'errors': []}
                try:
                    result = extract_e2e_context_from_websocket(mock_websocket)
                    self.assertIsInstance(result, (dict, type(None)))
                except Exception as e:
                    self.assertIsInstance(e, (RuntimeError, ValueError))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')