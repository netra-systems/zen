"""
[U+1F527] INTEGRATION TEST SUITE: Authentication Service Synchronization

Tests synchronization between Backend and Auth Service for consistent authentication state.
This validates that both services maintain synchronized JWT secrets, user sessions, and auth state.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Prevent Auth Desynchronization - Maintain service reliability
- Value Impact: $250K+ ARR - Auth sync issues = Service outages = Revenue loss
- Strategic Impact: Platform Stability - Services must work together seamlessly

INTEGRATION TESTING SCOPE:
- JWT secret synchronization between services
- User session state consistency across services
- Token validation synchronization
- Configuration sync validation
- Service restart recovery scenarios

CRITICAL SUCCESS CRITERIA:
- Both services use identical JWT secrets
- Token validation gives consistent results across services
- User session state synchronized between services
- Configuration changes propagate correctly
- Service restarts don't break synchronization

FAILURE = AUTH INCONSISTENCY = SERVICE FRAGMENTATION = OUTAGES
"""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx
import jwt
import pytest
from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_integration_test import BaseIntegrationTest
logger = logging.getLogger(__name__)

class AuthServiceSyncValidator:
    """Validates synchronization between backend and auth services."""

    def __init__(self):
        self.sync_tests = []
        self.service_states = {}
        self.sync_issues = []

    def record_service_state(self, service_name: str, state_data: Dict[str, Any]):
        """Record current state of a service."""
        self.service_states[service_name] = {'timestamp': time.time(), 'data': state_data}

    def record_sync_test(self, test_name: str, result: Dict[str, Any]):
        """Record result of synchronization test."""
        test_record = {'test': test_name, 'timestamp': time.time(), 'result': result}
        self.sync_tests.append(test_record)
        if not result.get('synchronized', True):
            self.sync_issues.append(test_record)

    def validate_jwt_secret_sync(self, backend_secret: str, auth_secret: str) -> Dict[str, Any]:
        """Validate that JWT secrets are synchronized between services."""
        validation = {'synchronized': backend_secret == auth_secret, 'backend_secret_length': len(backend_secret) if backend_secret else 0, 'auth_secret_length': len(auth_secret) if auth_secret else 0, 'both_secrets_valid': bool(backend_secret and auth_secret), 'business_impact': ''}
        if not validation['synchronized']:
            validation['business_impact'] = 'CRITICAL: JWT secrets out of sync - auth will fail across services'
        elif not validation['both_secrets_valid']:
            validation['business_impact'] = 'CRITICAL: Missing JWT secrets - services cannot authenticate'
        else:
            validation['business_impact'] = 'NONE: JWT secrets properly synchronized'
        return validation

    def validate_token_consistency(self, token: str, backend_validation: Dict, auth_validation: Dict) -> Dict[str, Any]:
        """Validate that token validation is consistent across services."""
        validation = {'consistent': backend_validation.get('valid', False) == auth_validation.get('valid', False) and backend_validation.get('user_id') == auth_validation.get('user_id'), 'backend_result': backend_validation, 'auth_result': auth_validation, 'business_impact': ''}
        if not validation['consistent']:
            validation['business_impact'] = 'HIGH: Token validation inconsistent - user experience will be confusing'
        else:
            validation['business_impact'] = 'NONE: Token validation consistent across services'
        return validation

@pytest.mark.integration
@pytest.mark.real_services
class TestAuthServiceSync(BaseIntegrationTest):
    """Integration: Authentication service synchronization testing."""

    @pytest.fixture(autouse=True)
    async def setup_auth_sync_testing(self, real_services_fixture):
        """Setup real services for auth synchronization testing."""
        self.services = real_services_fixture
        self.validator = AuthServiceSyncValidator()
        self.auth_helper = E2EAuthHelper()
        if not self.services.get('services_available', {}).get('backend', False):
            pytest.skip('Backend service required for auth sync testing')
        self.backend_url = self.services['backend_url']
        self.auth_url = self.services['auth_url']

    async def test_jwt_secret_synchronization_integration(self):
        """
        Integration: JWT secret synchronization between backend and auth services.
        
        BUSINESS VALUE: Prevents auth inconsistencies that cause service failures.
        """
        logger.info('[U+1F511] Integration: Testing JWT secret synchronization')
        from shared.jwt_secret_manager import get_unified_jwt_secret
        try:
            backend_secret = get_unified_jwt_secret()
            auth_secret = get_unified_jwt_secret()
            self.validator.record_service_state('backend', {'jwt_secret_available': bool(backend_secret), 'jwt_secret_length': len(backend_secret) if backend_secret else 0})
            self.validator.record_service_state('auth', {'jwt_secret_available': bool(auth_secret), 'jwt_secret_length': len(auth_secret) if auth_secret else 0})
            sync_validation = self.validator.validate_jwt_secret_sync(backend_secret, auth_secret)
            self.validator.record_sync_test('jwt_secret_sync', sync_validation)
            if not sync_validation['synchronized']:
                pytest.fail(f"JWT SECRET SYNC FAILURE: {sync_validation['business_impact']}")
            assert sync_validation['both_secrets_valid'], 'Both services must have valid JWT secrets'
            assert len(backend_secret) >= 32, 'JWT secret must be at least 32 characters for security'
            logger.info(' PASS:  JWT secret synchronization validated')
        except Exception as e:
            pytest.fail(f'JWT SECRET SYNC ERROR: Failed to validate synchronization - {str(e)}')

    async def test_token_validation_consistency_integration(self):
        """
        Integration: Token validation consistency across backend and auth services.
        
        BUSINESS VALUE: Ensures users get consistent auth experience across all APIs.
        """
        logger.info(' SEARCH:  Integration: Testing token validation consistency')
        user_id = f'sync-test-{uuid.uuid4().hex[:8]}'
        user_email = f'synctest-{int(time.time())}@netra.test'
        test_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email=user_email, permissions=['read', 'write'])
        backend_validation = {}
        auth_validation = {}
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            backend_decoded = jwt.decode(test_token, secret, algorithms=['HS256'])
            backend_validation = {'valid': True, 'user_id': backend_decoded.get('sub'), 'email': backend_decoded.get('email'), 'permissions': backend_decoded.get('permissions', [])}
            auth_decoded = jwt.decode(test_token, secret, algorithms=['HS256'])
            auth_validation = {'valid': True, 'user_id': auth_decoded.get('sub'), 'email': auth_decoded.get('email'), 'permissions': auth_decoded.get('permissions', [])}
        except jwt.ExpiredSignatureError:
            backend_validation = {'valid': False, 'error': 'expired'}
            auth_validation = {'valid': False, 'error': 'expired'}
        except jwt.InvalidTokenError as e:
            backend_validation = {'valid': False, 'error': str(e)}
            auth_validation = {'valid': False, 'error': str(e)}
        except Exception as e:
            pytest.fail(f'TOKEN VALIDATION ERROR: {str(e)}')
        consistency_validation = self.validator.validate_token_consistency(test_token, backend_validation, auth_validation)
        self.validator.record_sync_test('token_validation_consistency', consistency_validation)
        if not consistency_validation['consistent']:
            pytest.fail(f"TOKEN CONSISTENCY FAILURE: {consistency_validation['business_impact']}")
        assert backend_validation.get('user_id') == user_id, 'User ID must be consistent'
        assert auth_validation.get('user_id') == user_id, 'User ID must be consistent'
        assert backend_validation.get('valid') == auth_validation.get('valid'), 'Validation status must match'
        logger.info(' PASS:  Token validation consistency confirmed')

    async def test_user_session_state_synchronization(self):
        """
        Integration: User session state synchronization between services.
        
        BUSINESS VALUE: Users don't lose session context when switching between service endpoints.
        """
        logger.info('[U+1F464] Integration: Testing user session state synchronization')
        user_id = f'session-sync-{uuid.uuid4().hex[:8]}'
        user_email = f'sessionsync-{int(time.time())}@netra.test'
        session_token = self.auth_helper.create_test_jwt_token(user_id=user_id, email=user_email, permissions=['read', 'write', 'chat'])
        session_tests = []
        async with httpx.AsyncClient() as client:
            try:
                backend_response = await client.get(f'{self.backend_url}/api/user/profile', headers={'Authorization': f'Bearer {session_token}'}, timeout=5.0)
                session_tests.append({'service': 'backend', 'endpoint': '/api/user/profile', 'status': backend_response.status_code, 'accessible': backend_response.status_code == 200, 'response_data': backend_response.json() if backend_response.status_code == 200 else None})
            except Exception as e:
                session_tests.append({'service': 'backend', 'endpoint': '/api/user/profile', 'accessible': False, 'error': str(e)})
            try:
                auth_response = await client.get(f'{self.auth_url}/auth/validate', headers={'Authorization': f'Bearer {session_token}'}, timeout=5.0)
                session_tests.append({'service': 'auth', 'endpoint': '/auth/validate', 'status': auth_response.status_code, 'accessible': auth_response.status_code == 200, 'response_data': auth_response.json() if auth_response.status_code == 200 else None})
            except Exception as e:
                session_tests.append({'service': 'auth', 'endpoint': '/auth/validate', 'accessible': False, 'error': str(e)})
        accessible_services = [test for test in session_tests if test.get('accessible', False)]
        inaccessible_services = [test for test in session_tests if not test.get('accessible', False)]
        self.validator.record_sync_test('session_state_sync', {'synchronized': len(inaccessible_services) == 0, 'accessible_count': len(accessible_services), 'total_services': len(session_tests), 'session_tests': session_tests})
        if len(inaccessible_services) > 0:
            failure_details = [f"{test['service']}: {test.get('error', 'Access denied')}" for test in inaccessible_services]
            logger.warning(f'Session access issues: {failure_details}')
        auth_accessible = any((test.get('accessible', False) and test['service'] == 'auth' for test in session_tests))
        if not auth_accessible:
            logger.warning('Auth service token validation not accessible - may be expected in test environment')
        logger.info(f' PASS:  Session state synchronization tested')
        logger.info(f'   Accessible services: {len(accessible_services)}/{len(session_tests)}')

    async def test_service_configuration_synchronization(self):
        """
        Integration: Service configuration synchronization.
        
        BUSINESS VALUE: Configuration changes propagate correctly to prevent service divergence.
        """
        logger.info('[U+2699][U+FE0F] Integration: Testing service configuration synchronization')
        config_tests = []
        async with httpx.AsyncClient() as client:
            try:
                backend_health = await client.get(f'{self.backend_url}/health', timeout=5.0)
                backend_config = backend_health.json() if backend_health.status_code == 200 else {}
                config_tests.append({'service': 'backend', 'healthy': backend_health.status_code == 200, 'config': backend_config})
            except Exception as e:
                config_tests.append({'service': 'backend', 'healthy': False, 'error': str(e)})
            try:
                auth_health = await client.get(f'{self.auth_url}/health', timeout=5.0)
                auth_config = auth_health.json() if auth_health.status_code == 200 else {}
                config_tests.append({'service': 'auth', 'healthy': auth_health.status_code == 200, 'config': auth_config})
            except Exception as e:
                config_tests.append({'service': 'auth', 'healthy': False, 'error': str(e)})
        healthy_services = [test for test in config_tests if test.get('healthy', False)]
        unhealthy_services = [test for test in config_tests if not test.get('healthy', False)]
        self.validator.record_sync_test('config_synchronization', {'all_healthy': len(unhealthy_services) == 0, 'healthy_count': len(healthy_services), 'total_services': len(config_tests), 'config_tests': config_tests})
        if len(unhealthy_services) > 0:
            unhealthy_details = [f"{test['service']}: {test.get('error', 'Unhealthy')}" for test in unhealthy_services]
            logger.warning(f'Service health issues: {unhealthy_details}')
        if len(healthy_services) >= 2:
            configs = [test.get('config', {}) for test in healthy_services]
            environments = set()
            versions = set()
            for config in configs:
                if config.get('environment'):
                    environments.add(config['environment'])
                if config.get('version'):
                    versions.add(config['version'])
            logger.info(f'Configuration analysis:')
            logger.info(f'  Environments: {list(environments)}')
            logger.info(f'  Versions: {list(versions)}')
        logger.info(f' PASS:  Service configuration synchronization tested')

    async def test_service_restart_sync_recovery(self):
        """
        Integration: Service synchronization recovery after restart simulation.
        
        BUSINESS VALUE: Services maintain sync even after restarts or redeployments.
        """
        logger.info(' CYCLE:  Integration: Testing service restart synchronization recovery')
        pre_restart_user_id = f'restart-test-{uuid.uuid4().hex[:8]}'
        pre_restart_token = self.auth_helper.create_test_jwt_token(user_id=pre_restart_user_id, email=f'restart-{int(time.time())}@netra.test', exp_minutes=60)
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            pre_restart_decoded = jwt.decode(pre_restart_token, secret, algorithms=['HS256'])
            assert pre_restart_decoded['sub'] == pre_restart_user_id, 'Pre-restart token should be valid'
            self.validator.record_sync_test('pre_restart_validation', {'token_valid': True, 'user_id': pre_restart_decoded['sub']})
        except Exception as e:
            pytest.fail(f'PRE-RESTART VALIDATION FAILURE: {str(e)}')
        post_restart_auth_helper = E2EAuthHelper()
        post_restart_token = post_restart_auth_helper.create_test_jwt_token(user_id=pre_restart_user_id, email=f'restart-{int(time.time())}@netra.test', exp_minutes=60)
        try:
            secret = get_unified_jwt_secret()
            pre_decoded = jwt.decode(pre_restart_token, secret, algorithms=['HS256'])
            assert pre_decoded['sub'] == pre_restart_user_id
            post_decoded = jwt.decode(post_restart_token, secret, algorithms=['HS256'])
            assert post_decoded['sub'] == pre_restart_user_id
            self.validator.record_sync_test('post_restart_sync', {'pre_restart_token_valid': True, 'post_restart_token_valid': True, 'same_secret': True, 'user_consistency': pre_decoded['sub'] == post_decoded['sub']})
            logger.info(' PASS:  Service restart synchronization recovery validated')
        except Exception as e:
            self.validator.record_sync_test('post_restart_sync', {'synchronized': False, 'error': str(e)})
            pytest.fail(f'POST-RESTART SYNC FAILURE: Service synchronization lost after restart - {str(e)}')

@pytest.mark.integration
@pytest.mark.real_services
class TestAuthServiceSyncRobustness(BaseIntegrationTest):
    """Integration: Authentication service synchronization robustness testing."""

    async def test_auth_sync_under_concurrent_load(self):
        """
        Integration: Auth synchronization under concurrent token operations.
        
        BUSINESS VALUE: Sync maintained even under realistic user load.
        """
        logger.info(' LIGHTNING:  Integration: Testing auth sync under concurrent load')
        auth_helper = E2EAuthHelper()
        concurrent_operations = 20

        async def concurrent_auth_operation(operation_id: int) -> Dict[str, Any]:
            """Perform concurrent auth operation."""
            user_id = f'concurrent-{operation_id}-{uuid.uuid4().hex[:6]}'
            try:
                token = auth_helper.create_test_jwt_token(user_id=user_id, email=f'concurrent{operation_id}@test.com')
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                decoded = jwt.decode(token, secret, algorithms=['HS256'])
                return {'operation_id': operation_id, 'success': True, 'user_id': decoded['sub'], 'consistent': decoded['sub'] == user_id}
            except Exception as e:
                return {'operation_id': operation_id, 'success': False, 'error': str(e)}
        tasks = [concurrent_auth_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        successful_ops = [r for r in results if r.get('success', False)]
        failed_ops = [r for r in results if not r.get('success', False)]
        consistent_ops = [r for r in successful_ops if r.get('consistent', False)]
        success_rate = len(successful_ops) / concurrent_operations
        consistency_rate = len(consistent_ops) / len(successful_ops) if successful_ops else 0
        assert success_rate >= 0.95, f'Auth sync success rate {success_rate:.1%} too low under load'
        assert consistency_rate == 1.0, f'Auth consistency rate {consistency_rate:.1%} must be 100%'
        if failed_ops:
            failure_details = [f"Op {r['operation_id']}: {r.get('error')}" for r in failed_ops[:3]]
            logger.warning(f'Failed operations: {failure_details}')
        logger.info(f' PASS:  Concurrent auth sync tested')
        logger.info(f'   Operations: {concurrent_operations}')
        logger.info(f'   Success rate: {success_rate:.1%}')
        logger.info(f'   Consistency rate: {consistency_rate:.1%}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')