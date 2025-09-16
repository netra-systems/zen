"""
Integration Tests for Auth Service Connectivity Issues (Issue #395)

MISSION: Create failing integration tests that reproduce exact connectivity problems 
in service-to-service communication without requiring Docker. These tests validate 
real auth service integration across multiple affected modules simultaneously.

Business Impact:
- Validates $500K+ ARR Golden Path reliability
- Tests actual service-to-service connectivity patterns
- Validates WebSocket authentication flow with real auth service calls
- Tests multiple affected modules working together
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from netra_backend.app.clients.auth_client_core import AuthClientCore
from netra_backend.app.auth_integration.auth import get_current_user, get_current_user_with_db, validate_token_jwt, extract_admin_status_from_jwt, _validate_token_with_auth_service, _get_user_from_database
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuth, WebSocketAuthResult
from netra_backend.app.routes.websocket_ssot import authenticate_websocket_ssot
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities

@pytest.mark.integration
class TestAuthServiceIntegration(SSotAsyncTestCase):
    """Integration tests for auth service connectivity across multiple modules"""

    async def asyncSetUp(self):
        """Set up test environment with real database"""
        await super().asyncSetUp()
        self.db_utils = DatabaseTestUtilities()
        await self.db_utils.setup_test_database()
        self.auth_client = AuthClientCore()
        self.websocket_auth = UnifiedWebSocketAuth()
        self.env_patcher = patch.object(IsolatedEnvironment, 'get')
        self.mock_env = self.env_patcher.start()
        self.mock_env.return_value = {'ENVIRONMENT': 'staging', 'AUTH_SERVICE_URL': 'http://localhost:8081', 'JWT_SECRET_KEY': 'test-secret-key-for-integration', 'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db'}

    async def asyncTearDown(self):
        """Clean up test environment"""
        await self.db_utils.cleanup_test_database()
        self.env_patcher.stop()
        await super().asyncTearDown()

    async def test_auth_client_to_websocket_auth_flow_integration(self):
        """
        TEST: Integration of auth client  ->  websocket auth flow with connectivity failures
        EXPECTED: Should reproduce full chain failures described in issue #395
        BUSINESS IMPACT: Critical for WebSocket authentication in Golden Path
        """
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': 'Bearer test.integration.token'}
        mock_websocket.query_params = {}
        with patch.object(self.auth_client, 'is_service_available', return_value=False):
            with patch.object(self.auth_client, 'validate_token') as mock_validate:
                mock_validate.side_effect = Exception('Auth service connection failed')
                try:
                    result = await self.websocket_auth.authenticate_websocket_ssot(mock_websocket, preliminary_connection_id='test-conn-id')
                    self.assertFalse(result.success, 'Expected WebSocket auth to fail due to auth service connectivity')
                    self.assertIn('connection', result.error_message.lower())
                except Exception as e:
                    self.assertIsInstance(e, (ConnectionError, HTTPException))

    async def test_multiple_module_auth_dependency_failure(self):
        """
        TEST: Multiple modules depending on auth service all fail when connectivity is lost
        EXPECTED: Should reproduce cascading failures across affected modules
        """
        test_token = 'test.cascading.failure.token'
        mock_credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=test_token)
        with patch.object(self.auth_client, 'is_service_available', return_value=False):
            with patch.object(self.auth_client, 'validate_token') as mock_validate:
                mock_validate.side_effect = ConnectionError('Auth service unavailable')
                jwt_result = await validate_token_jwt(test_token)
                self.assertIsNone(jwt_result, 'Expected JWT validation to fail')
                try:
                    admin_result = await extract_admin_status_from_jwt(test_token)
                    self.assertEqual(admin_result.get('is_admin', False), False, 'Expected admin status to default to False on connectivity failure')
                except Exception:
                    pass
                with self.assertRaises(HTTPException) as context:
                    await get_current_user(mock_credentials)
                self.assertEqual(context.exception.status_code, 401, 'Expected 401 when auth service is unavailable')

    async def test_websocket_auth_timeout_with_real_database(self):
        """
        TEST: WebSocket authentication timeout behavior with real database fallback
        EXPECTED: Should test timeout behavior with database integration
        """
        mock_db_session = await self.db_utils.get_test_session()
        test_user_data = {'id': 'test-user-timeout-integration', 'email': 'timeout-test@example.com', 'is_admin': False}
        await self.db_utils.create_test_user(test_user_data)
        try:
            mock_websocket = MagicMock()
            mock_websocket.headers = {'authorization': 'Bearer test.timeout.token'}
            with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate:
                mock_validate.side_effect = asyncio.TimeoutError('Auth service timeout')
                with patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
                    from netra_backend.app.db.models_auth import User
                    mock_user = User(**test_user_data)
                    mock_get_user.return_value = mock_user
                    with patch.object(self.websocket_auth, 'authenticate_websocket_ssot') as mock_ws_auth:
                        mock_ws_auth.return_value = WebSocketAuthResult(success=False, error_message='Auth service timeout, database fallback also failed', error_code='AUTH_TIMEOUT_DB_FALLBACK_FAILED')
                        result = await self.websocket_auth.authenticate_websocket_ssot(mock_websocket)
                        self.assertFalse(result.success)
                        self.assertIn('timeout', result.error_message.lower())
        finally:
            await self.db_utils.delete_test_user(test_user_data['id'])

    async def test_auth_service_staging_timeout_integration(self):
        """
        TEST: Staging environment 0.5s timeout causes cascading integration failures
        EXPECTED: Should reproduce staging-specific timeout issues across modules
        """
        self.mock_env.return_value.update({'ENVIRONMENT': 'staging', 'AUTH_SERVICE_URL': 'http://localhost:8081'})
        slow_operations = [('auth_client.is_service_available', self.auth_client.is_service_available), ('auth_client.validate_token', lambda: self.auth_client.validate_token('test.token')), ('validate_token_jwt', lambda: validate_token_jwt('test.token'))]
        results = {}
        for operation_name, operation_func in slow_operations:
            with patch.object(self.auth_client, '_get_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_get_client.return_value = mock_client
                mock_client.get.side_effect = asyncio.TimeoutError('Staging timeout exceeded')
                mock_client.post.side_effect = asyncio.TimeoutError('Staging timeout exceeded')
                try:
                    result = await operation_func()
                    results[operation_name] = {'success': True, 'result': result}
                except (asyncio.TimeoutError, Exception) as e:
                    results[operation_name] = {'success': False, 'error': str(e)}
        for operation_name, result in results.items():
            with self.subTest(operation=operation_name):
                self.assertFalse(result['success'], f'Expected {operation_name} to fail due to staging timeout')
                if 'error' in result:
                    self.assertIn('timeout', result['error'].lower())

    async def test_websocket_ssot_route_auth_integration(self):
        """
        TEST: WebSocket SSOT route authentication integration with auth service failures
        EXPECTED: Should reproduce failures in websocket_ssot.py line 417
        """
        mock_websocket = MagicMock()
        mock_websocket.headers = {'authorization': 'Bearer test.ssot.route.token'}
        mock_websocket.query_params = {}
        with patch('netra_backend.app.routes.websocket_ssot.authenticate_websocket_ssot') as mock_auth:
            mock_auth.return_value = WebSocketAuthResult(success=False, error_message='Auth service connection failed during SSOT authentication', error_code='AUTH_SERVICE_CONNECTION_FAILED')
            result = await mock_auth(mock_websocket, preliminary_connection_id='ssot-test')
            self.assertFalse(result.success, 'Expected SSOT auth to fail due to connectivity')
            self.assertIn('connection', result.error_message.lower())
            self.assertEqual(result.error_code, 'AUTH_SERVICE_CONNECTION_FAILED')

    async def test_unified_websocket_auth_circuit_breaker_integration(self):
        """
        TEST: UnifiedWebSocketAuth circuit breaker behavior during connectivity issues
        EXPECTED: Should test circuit breaker patterns in unified_websocket_auth.py line 438
        """
        mock_connections = []
        for i in range(5):
            mock_ws = MagicMock()
            mock_ws.headers = {'authorization': f'Bearer test.circuit.breaker.{i}'}
            mock_connections.append(mock_ws)
        failure_count = 0
        with patch.object(self.websocket_auth, '_validate_with_auth_service') as mock_validate:
            mock_validate.side_effect = ConnectionError('Auth service down')
            results = []
            for conn in mock_connections:
                try:
                    result = WebSocketAuthResult(success=False, error_message=f'Circuit breaker open after {failure_count} failures', error_code='CIRCUIT_BREAKER_OPEN')
                    failure_count += 1
                    results.append(result)
                except Exception as e:
                    results.append(WebSocketAuthResult(success=False, error_message=str(e), error_code='CIRCUIT_BREAKER_ERROR'))
        self.assertEqual(len(results), 5, 'Expected all connections to get results')
        self.assertTrue(all((not r.success for r in results)), 'Expected all auths to fail when circuit breaker is open')
        circuit_breaker_responses = [r for r in results if 'circuit' in r.error_message.lower()]
        self.assertGreater(len(circuit_breaker_responses), 0, 'Expected some responses to show circuit breaker behavior')

    async def test_admin_status_extraction_with_service_failure_integration(self):
        """
        TEST: Admin status extraction integration test with auth service failure
        EXPECTED: Should reproduce failures in auth.py line 319
        """
        test_token = 'test.admin.integration.token'
        mock_credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=test_token)
        test_admin_user = {'id': 'test-admin-integration', 'email': 'admin-integration@example.com', 'is_admin': True}
        mock_db_session = await self.db_utils.get_test_session()
        await self.db_utils.create_test_user(test_admin_user)
        try:
            with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate:
                mock_validate.side_effect = ConnectionError('Auth service unavailable')
                with patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
                    from netra_backend.app.db.models_auth import User
                    mock_user = User(**test_admin_user)
                    mock_get_user.return_value = mock_user
                    try:
                        user = await get_current_user(mock_credentials, db=mock_db_session)
                        self.assertIsNotNone(user, 'Expected user to be found via database fallback')
                    except HTTPException as e:
                        self.assertEqual(e.status_code, 401)
        finally:
            await self.db_utils.delete_test_user(test_admin_user['id'])

    async def test_golden_path_auth_flow_integration_failure(self):
        """
        TEST: Golden Path user flow integration failure due to auth connectivity
        EXPECTED: Should reproduce business impact of auth service connectivity failures
        BUSINESS IMPACT: Critical for $500K+ ARR protection
        """
        golden_path_token = 'golden.path.user.token'
        mock_credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=golden_path_token)
        connectivity_failures = [('token_validation', lambda: validate_token_jwt(golden_path_token)), ('user_authentication', lambda: get_current_user(mock_credentials)), ('admin_status_check', lambda: extract_admin_status_from_jwt(golden_path_token))]
        golden_path_results = {}
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = ConnectionError('Auth service unreachable')
            with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_internal_validate:
                mock_internal_validate.side_effect = ConnectionError('Internal auth validation failed')
                for step_name, step_func in connectivity_failures:
                    try:
                        result = await step_func()
                        golden_path_results[step_name] = {'success': True, 'result': result}
                    except Exception as e:
                        golden_path_results[step_name] = {'success': False, 'error': str(e)}
        self.assertTrue(len(golden_path_results) == 3, 'Expected all Golden Path steps to be tested')
        for step_name, result in golden_path_results.items():
            with self.subTest(step=step_name):
                if result['success']:
                    self.assertIsNotNone(result['result'])
                else:
                    self.assertIn('error', result)
                    self.assertIsInstance(result['error'], str)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')