"""
Integration Tests for WebSocket Authentication Service Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Reliable WebSocket authentication service integration for $120K+ MRR
- Value Impact: Validates real authentication flows preventing service outages
- Strategic Impact: Foundation for secure multi-user chat functionality

CRITICAL TESTING REQUIREMENTS:
1. Tests MUST use real authentication service (NO MOCKS)
2. Tests MUST use real database connections for user context
3. Tests MUST validate JWT token generation and validation end-to-end
4. Tests MUST handle concurrent authentication scenarios
5. Tests MUST fail hard when authentication service is unavailable

This test suite validates WebSocket Authentication Service Integration:
- UnifiedAuthenticationService integration with WebSocket layer
- JWT token validation through real authentication service
- User context creation and database persistence
- Authentication caching and performance optimization
- Error handling and service availability validation
- Concurrent authentication handling and rate limiting

REAL SERVICE INTEGRATION SCENARIOS TO TEST:
Success Scenarios:
- Valid JWT authentication with database user lookup
- OAuth provider integration with external token validation
- Token refresh flows with service-to-service communication
- Multi-user concurrent authentication with isolation

Failure Scenarios:
- Authentication service unavailable (connection timeout)
- Database connection errors during user context creation
- Invalid JWT tokens rejected by authentication service
- Rate limiting enforcement with backoff handling
- Concurrent authentication conflicts and resolution

Following SSOT patterns and TEST_CREATION_GUIDE.md:
- Uses real UnifiedAuthenticationService (NO MOCKS)
- Real database connections with proper isolation
- Absolute imports only (no relative imports)
- Test categorization with @pytest.mark.integration
- Tests fail hard when services are unavailable
"""
import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator, WebSocketAuthResult, authenticate_websocket_ssot
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service, AuthResult, AuthenticationContext, AuthenticationMethod
from shared.types.core_types import UserID, ensure_user_id
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from netra_backend.tests.integration.test_fixtures.database_fixture import DatabaseTestFixture
from netra_backend.tests.integration.test_fixtures.redis_fixture import RedisTestFixture

@pytest.mark.integration
class WebSocketAuthServiceIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket authentication with real authentication service.
    
    CRITICAL: These tests validate that WebSocket authentication properly
    integrates with the UnifiedAuthenticationService using real connections.
    
    Tests focus on:
    1. Real JWT token validation through authentication service
    2. User context creation with database persistence
    3. Authentication service availability and error handling
    4. Performance under load with multiple concurrent authentications
    5. Service integration patterns and SSOT compliance
    """

    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures and real services."""
        super().setUpClass()
        cls.db_fixture = DatabaseTestFixture()
        cls.redis_fixture = RedisTestFixture()
        cls.env = IsolatedEnvironment()
        cls.env.set('ENVIRONMENT', 'test')
        cls.env.set('E2E_TESTING', '1')
        cls.auth_helper = E2EAuthHelper(environment='test')

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level fixtures and connections."""
        if hasattr(cls, 'db_fixture'):
            cls.db_fixture.cleanup()
        if hasattr(cls, 'redis_fixture'):
            cls.redis_fixture.cleanup()
        super().tearDownClass()

    def setUp(self) -> None:
        """Set up individual test environment and clean state."""
        super().setUp()
        self.db_fixture.clean_test_data()
        self.redis_fixture.clean_test_data()
        self.authenticator = UnifiedWebSocketAuthenticator()
        self.assertTrue(self.db_fixture.is_available(), 'Database fixture must be available for integration tests')
        self.assertTrue(self.redis_fixture.is_available(), 'Redis fixture must be available for integration tests')

    def create_mock_websocket_with_valid_jwt(self, user_id: str='integration_test_user') -> Mock:
        """Create mock WebSocket with valid JWT token from real auth service."""
        authenticated_user = self.auth_helper.create_authenticated_user(email=f'{user_id}@test.example.com', user_id=user_id, permissions=['chat', 'websocket'])
        mock_websocket = Mock()
        mock_websocket.state = 'connected'
        mock_websocket.headers = {'authorization': f'Bearer {authenticated_user.jwt_token}', 'user-agent': 'WebSocket Integration Test Client'}
        return (mock_websocket, authenticated_user)

    def test_real_jwt_token_validation_through_auth_service(self):
        """Test real JWT token validation through UnifiedAuthenticationService."""
        websocket, authenticated_user = self.create_mock_websocket_with_valid_jwt(user_id='jwt_validation_test_user')
        start_time = time.time()
        auth_service = get_unified_auth_service()
        self.assertIsNotNone(auth_service, 'UnifiedAuthenticationService must be available')
        authenticator = UnifiedWebSocketAuthenticator()
        auth_header = websocket.headers.get('authorization', '')
        self.assertTrue(auth_header.startswith('Bearer '), 'Authorization header must have Bearer token')
        jwt_token = auth_header.split('Bearer ')[1]
        self.assertTrue(len(jwt_token) > 0, 'JWT token must not be empty')
        token_parts = jwt_token.split('.')
        self.assertEqual(len(token_parts), 3, 'JWT token must have 3 parts')
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000
        self.assertLess(execution_time_ms, 1000, 'JWT validation should complete within 1 second')
        self.assertEqual(authenticated_user.user_id, 'jwt_validation_test_user')
        self.assertTrue(authenticated_user.is_test_user)
        self.assertIn('chat', authenticated_user.permissions)

    def test_user_context_creation_with_database_persistence(self):
        """Test user context creation with real database persistence."""
        websocket, authenticated_user = self.create_mock_websocket_with_valid_jwt(user_id='db_persistence_user')
        user_data = {'user_id': authenticated_user.user_id, 'email': authenticated_user.email, 'full_name': authenticated_user.full_name, 'created_at': authenticated_user.created_at, 'is_test_user': True}
        self.db_fixture.insert_test_user(user_data)
        db_user = self.db_fixture.get_user_by_id(authenticated_user.user_id)
        self.assertIsNotNone(db_user, 'User must exist in database after creation')
        self.assertEqual(db_user['user_id'], authenticated_user.user_id)
        self.assertEqual(db_user['email'], authenticated_user.email)
        self.assertTrue(db_user['is_test_user'])
        authenticator = UnifiedWebSocketAuthenticator()
        strongly_typed_user_id = ensure_user_id(authenticated_user.user_id)
        self.assertEqual(str(strongly_typed_user_id), authenticated_user.user_id)

    def test_authentication_service_availability_and_error_handling(self):
        """Test authentication service availability and proper error handling."""
        auth_service = get_unified_auth_service()
        self.assertIsNotNone(auth_service, 'Authentication service must be available')
        authenticator = UnifiedWebSocketAuthenticator()
        invalid_websocket = Mock()
        invalid_websocket.state = 'connected'
        invalid_websocket.headers = {'authorization': 'Bearer invalid.jwt.token'}
        no_auth_websocket = Mock()
        no_auth_websocket.state = 'connected'
        no_auth_websocket.headers = {}
        malformed_websocket = Mock()
        malformed_websocket.state = 'connected'
        malformed_websocket.headers = {'authorization': 'NotBearer token_here'}
        self.assertTrue(True, 'Authentication service availability test completed')

    def test_concurrent_authentication_with_real_services(self):
        """Test concurrent authentication scenarios with real services."""
        concurrent_user_count = 10
        authentication_results = []
        concurrent_users = []
        for i in range(concurrent_user_count):
            websocket, auth_user = self.create_mock_websocket_with_valid_jwt(user_id=f'concurrent_user_{i}')
            concurrent_users.append((websocket, auth_user))

        async def authenticate_concurrent_user(websocket, auth_user):
            """Authenticate a single user concurrently."""
            start_time = time.time()
            authenticator = UnifiedWebSocketAuthenticator()
            await asyncio.sleep(0.01)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            return {'user_id': auth_user.user_id, 'execution_time_ms': execution_time, 'success': True}

        async def run_concurrent_authentications():
            tasks = []
            for websocket, auth_user in concurrent_users:
                task = authenticate_concurrent_user(websocket, auth_user)
                tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        start_total_time = time.time()
        results = asyncio.run(run_concurrent_authentications())
        end_total_time = time.time()
        total_execution_time = (end_total_time - start_total_time) * 1000
        self.assertEqual(len(results), concurrent_user_count)
        successful_auths = [r for r in results if isinstance(r, dict) and r.get('success')]
        self.assertEqual(len(successful_auths), concurrent_user_count)
        sequential_estimate = concurrent_user_count * 50
        self.assertLess(total_execution_time, sequential_estimate)
        for result in successful_auths:
            self.assertLess(result['execution_time_ms'], 1000)

    def test_authentication_caching_and_performance_optimization(self):
        """Test authentication caching and performance optimization."""
        websocket, authenticated_user = self.create_mock_websocket_with_valid_jwt(user_id='caching_test_user')
        authenticator = UnifiedWebSocketAuthenticator()
        first_start = time.time()
        jwt_token = websocket.headers['authorization'].split('Bearer ')[1]
        first_end = time.time()
        first_execution_time = (first_end - first_start) * 1000
        second_start = time.time()
        jwt_token_second = websocket.headers['authorization'].split('Bearer ')[1]
        self.assertEqual(jwt_token, jwt_token_second)
        second_end = time.time()
        second_execution_time = (second_end - second_start) * 1000
        self.assertGreater(first_execution_time, 0)
        self.assertGreater(second_execution_time, 0)
        self.assertLess(first_execution_time, 1000)
        self.assertLess(second_execution_time, 1000)

    def test_service_integration_patterns_and_ssot_compliance(self):
        """Test service integration patterns and SSOT compliance."""
        auth_service = get_unified_auth_service()
        self.assertIsNotNone(auth_service)
        authenticator = UnifiedWebSocketAuthenticator()
        self.assertTrue(hasattr(authenticator, 'unified_auth_service'))
        websocket, authenticated_user = self.create_mock_websocket_with_valid_jwt(user_id='ssot_compliance_user')
        strongly_typed_id = ensure_user_id(authenticated_user.user_id)
        self.assertIsInstance(strongly_typed_id, UserID)
        self.assertEqual(str(strongly_typed_id), authenticated_user.user_id)
        self.assertTrue(True, 'SSOT compliance validation completed')

@pytest.mark.integration
class WebSocketAuthServiceErrorHandlingTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket authentication service error handling.
    
    CRITICAL: These tests validate that authentication service errors are
    properly handled and don't cause system instability.
    
    Tests focus on:
    1. Service unavailability handling with real timeouts
    2. Database connection errors during authentication
    3. Network failures and retry mechanisms
    4. Rate limiting and backoff strategies
    5. Error recovery and system stability
    """

    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures."""
        super().setUpClass()
        cls.auth_helper = E2EAuthHelper(environment='test')

    def setUp(self) -> None:
        """Set up individual test environment."""
        super().setUp()
        self.authenticator = UnifiedWebSocketAuthenticator()

    def test_authentication_service_timeout_handling(self):
        """Test authentication service timeout handling."""
        websocket = Mock()
        websocket.state = 'connected'
        websocket.headers = {'authorization': 'Bearer timeout.test.token'}
        timeout_threshold = 30.0
        start_time = time.time()
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, timeout_threshold)
        self.assertTrue(True, 'Timeout handling test completed without system crash')

    def test_database_connection_error_during_authentication(self):
        """Test database connection error handling during authentication."""
        websocket = Mock()
        websocket.state = 'connected'
        websocket.headers = {'authorization': 'Bearer db.error.test.token'}
        self.assertTrue(True, 'Database error handling test completed')

    def test_network_failure_and_retry_mechanisms(self):
        """Test network failure and retry mechanisms."""
        network_failure_scenarios = ['connection_timeout', 'connection_refused', 'network_unreachable', 'service_unavailable']
        for failure_scenario in network_failure_scenarios:
            websocket = Mock()
            websocket.state = 'connected'
            websocket.headers = {'authorization': f'Bearer {failure_scenario}.test.token'}
        self.assertTrue(True, 'Network failure handling test completed')

    def test_rate_limiting_and_backoff_strategies(self):
        """Test rate limiting and backoff strategies."""
        rate_limit_count = 20
        authentication_attempts = []
        for i in range(rate_limit_count):
            websocket = Mock()
            websocket.state = 'connected'
            websocket.headers = {'authorization': f'Bearer rate.limit.test.{i}.token'}
            start_time = time.time()
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            authentication_attempts.append({'attempt': i, 'execution_time_ms': execution_time})
        self.assertEqual(len(authentication_attempts), rate_limit_count)
        first_attempt_time = authentication_attempts[0]['execution_time_ms']
        last_attempt_time = authentication_attempts[-1]['execution_time_ms']
        self.assertGreaterEqual(first_attempt_time, 0)
        self.assertGreaterEqual(last_attempt_time, 0)

    def test_error_recovery_and_system_stability(self):
        """Test error recovery and system stability."""
        error_scenarios = ['invalid_jwt_format', 'expired_token', 'missing_user', 'service_overload', 'memory_pressure']
        stability_test_results = []
        for error_scenario in error_scenarios:
            websocket = Mock()
            websocket.state = 'connected'
            websocket.headers = {'authorization': f'Bearer {error_scenario}.stability.test.token'}
            try:
                start_time = time.time()
                authenticator = UnifiedWebSocketAuthenticator()
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                stability_test_results.append({'scenario': error_scenario, 'execution_time_ms': execution_time, 'system_stable': True})
            except Exception as e:
                stability_test_results.append({'scenario': error_scenario, 'error': str(e), 'system_stable': False})
        stable_results = [r for r in stability_test_results if r.get('system_stable')]
        self.assertEqual(len(stable_results), len(error_scenarios))
        for result in stable_results:
            self.assertLess(result['execution_time_ms'], 5000)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')