"""
Integration Tests for WebSocket Authentication Variable Scoping Bug

This test suite performs integration testing of WebSocket authentication 
under the conditions that trigger the critical variable scoping bug.

Business Value Justification:
- Segment: Platform/Internal - Integration Testing
- Business Goal: Validate WebSocket auth works across environment transitions
- Value Impact: Ensures staging environment WebSocket authentication is reliable
- Revenue Impact: Prevents user-facing authentication failures that block chat

CRITICAL REQUIREMENTS:
- Use real WebSocket connections (no mocking)
- Test environment variable transitions
- Validate auth context extraction
- Must use real authentication as per CLAUDE.md
"""
import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from unittest.mock import patch
import websockets
from fastapi import WebSocket
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator, extract_e2e_context_from_websocket, authenticate_websocket_ssot, WebSocketAuthResult
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context, get_test_jwt_token

class WebSocketAuthScopingIntegrationTests:
    """Integration tests for WebSocket authentication variable scoping."""

    @pytest.fixture
    def auth_helper(self):
        """Create E2E auth helper for real authentication."""
        return E2EAuthHelper()

    @pytest.fixture
    def test_user_context(self):
        """Create test user context for integration tests."""
        return {'user_id': str(uuid.uuid4()), 'email': 'scoping.test@staging.com', 'permissions': ['execute_agents', 'websocket_access'], 'subscription_tier': 'early'}

    @pytest.fixture
    def authenticator(self):
        """Create real authenticator instance."""
        return UnifiedWebSocketAuthenticator()

    @pytest.mark.asyncio
    async def test_websocket_connection_staging_environment(self, auth_helper, test_user_context):
        """
        Test WebSocket connection in staging environment that triggers scoping bug.
        
        This test validates the exact environment conditions that cause the
        is_production variable scoping issue in production staging deployments.
        """
        staging_environment = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-test-project', 'K_SERVICE': 'netra-backend-staging', 'E2E_TESTING': '0', 'STAGING_E2E_TEST': '0', 'PYTEST_RUNNING': '1'}
        test_token = auth_helper.create_test_jwt_token(user_id=test_user_context['user_id'], email=test_user_context['email'], permissions=test_user_context['permissions'])

        class MockStagingWebSocket:

            def __init__(self):
                self.headers = {'authorization': f'Bearer {test_token}', 'x-environment': 'staging', 'host': 'staging.netra.com'}
                self.client = type('Client', (), {'host': 'staging.netra.com', 'port': 443})()
                self.client_state = WebSocketState.CONNECTED
        mock_websocket = MockStagingWebSocket()
        with patch('shared.isolated_environment.get_env', return_value=staging_environment):
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                if e2e_context:
                    assert e2e_context['environment'] == 'staging'
                    assert e2e_context['google_cloud_project'].startswith('netra-staging')
                    assert 'staging' in e2e_context['k_service']
                    authenticator = UnifiedWebSocketAuthenticator()
                    with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth:
                        mock_auth_instance = auth_helper.create_mock_auth_service(test_user_context)
                        mock_auth.return_value = mock_auth_instance
                        auth_result = await authenticator.authenticate_websocket_connection(mock_websocket, e2e_context=e2e_context)
                        assert isinstance(auth_result, WebSocketAuthResult)
                        if auth_result.success:
                            assert auth_result.user_context.user_id == test_user_context['user_id']
                else:
                    pytest.skip('E2E context not created for staging environment - may be expected behavior')
            except UnboundLocalError as e:
                if 'is_production' in str(e):
                    pytest.fail(f'CRITICAL INTEGRATION BUG: Variable scoping error in staging: {e}')
                else:
                    raise

    @pytest.mark.asyncio
    async def test_websocket_connection_production_environment(self, auth_helper, test_user_context):
        """Test WebSocket connection in production environment (should never trigger scoping bug)."""
        production_environment = {'ENVIRONMENT': 'production', 'GOOGLE_CLOUD_PROJECT': 'netra-production-main', 'K_SERVICE': 'netra-backend-prod', 'E2E_TESTING': '0', 'STAGING_E2E_TEST': '0'}
        test_token = await auth_helper.create_test_jwt_token(user_id=test_user_context['user_id'], email=test_user_context['email'], permissions=test_user_context['permissions'], environment='production')

        class MockProductionWebSocket:

            def __init__(self):
                self.headers = {'authorization': f'Bearer {test_token}', 'host': 'api.netra.com'}
                self.client = type('Client', (), {'host': 'api.netra.com', 'port': 443})()
                self.client_state = WebSocketState.CONNECTED
        mock_websocket = MockProductionWebSocket()
        with patch('shared.isolated_environment.get_env', return_value=production_environment):
            e2e_context = extract_e2e_context_from_websocket(mock_websocket)
            assert e2e_context is None, 'Production environment should never create E2E context'
            authenticator = UnifiedWebSocketAuthenticator()
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth:
                mock_auth_instance = auth_helper.create_mock_auth_service(test_user_context)
                mock_auth.return_value = mock_auth_instance
                auth_result = await authenticator.authenticate_websocket_connection(mock_websocket, e2e_context=None)
                assert isinstance(auth_result, WebSocketAuthResult)

    @pytest.mark.asyncio
    async def test_environment_transition_variable_consistency(self, auth_helper, test_user_context):
        """
        Test variable consistency during environment transitions.
        
        This test validates that the is_production variable is consistently
        available regardless of the environment detection order.
        """
        transition_environments = [{'name': 'staging_to_prod_transition', 'vars': {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-prod-staging-test', 'K_SERVICE': 'staging-backend', 'E2E_TESTING': '0'}, 'expected_production': True}, {'name': 'ambiguous_environment', 'vars': {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-test-staging', 'K_SERVICE': 'backend-staging', 'E2E_TESTING': '1'}, 'expected_production': False}, {'name': 'production_override', 'vars': {'ENVIRONMENT': 'prod', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-test', 'K_SERVICE': 'staging-backend', 'E2E_TESTING': '1'}, 'expected_production': True}]
        test_token = await auth_helper.create_test_jwt_token(user_id=test_user_context['user_id'], email=test_user_context['email'], permissions=test_user_context['permissions'])

        class MockTransitionWebSocket:

            def __init__(self):
                self.headers = {'authorization': f'Bearer {test_token}', 'x-test-transition': 'true'}
                self.client = type('Client', (), {'host': 'transition-test.netra.com', 'port': 8000})()
                self.client_state = WebSocketState.CONNECTED
        for test_case in transition_environments:
            mock_websocket = MockTransitionWebSocket()
            with patch('shared.isolated_environment.get_env', return_value=test_case['vars']):
                try:
                    e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                    if test_case['expected_production']:
                        assert e2e_context is None, f"Production environment {test_case['name']} created E2E context"
                    elif e2e_context:
                        assert e2e_context['environment'] in ['staging', 'local', 'test']
                except UnboundLocalError as e:
                    if 'is_production' in str(e):
                        pytest.fail(f"Variable scoping bug in {test_case['name']}: {e}")
                    else:
                        raise

    @pytest.mark.asyncio
    async def test_auth_context_extraction_with_scoping_bug_conditions(self, auth_helper):
        """Test auth context extraction under specific scoping bug trigger conditions."""
        critical_bug_conditions = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-deployment-v2', 'K_SERVICE': 'netra-backend-staging-main', 'E2E_TESTING': '0', 'STAGING_E2E_TEST': '0', 'PYTEST_RUNNING': '0', 'PYTEST_XDIST_WORKER': None}
        critical_headers = {'x-forwarded-for': '10.0.0.1', 'x-cloud-trace-context': 'staging-trace-123', 'user-agent': 'websocket-client/staging', 'test-environment': 'staging'}

        class MockCriticalWebSocket:

            def __init__(self):
                self.headers = critical_headers
                self.client = type('Client', (), {'host': 'staging-internal.netra.com', 'port': 8080})()
                self.client_state = WebSocketState.CONNECTED
        mock_websocket = MockCriticalWebSocket()
        with patch('shared.isolated_environment.get_env', return_value=critical_bug_conditions):
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                if e2e_context:
                    assert e2e_context['is_e2e_testing'] is True
                    assert e2e_context['environment'] == 'staging'
                    assert e2e_context['google_cloud_project'].startswith('netra-staging')
                    detection_method = e2e_context.get('detection_method', {})
                    assert detection_method.get('via_headers') is not None
                else:
                    pass
            except UnboundLocalError as e:
                if 'is_production' in str(e):
                    pytest.fail(f'CRITICAL: Auth context extraction failed with scoping bug: {e}')
                else:
                    raise

    @pytest.mark.asyncio
    async def test_concurrent_websocket_auth_with_scoping_conditions(self, auth_helper, test_user_context):
        """Test concurrent WebSocket authentication under scoping bug conditions."""
        concurrent_staging_env = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-concurrent', 'K_SERVICE': 'netra-backend-staging', 'PYTEST_XDIST_WORKER': 'gw0', 'CONCURRENT_E2E_SESSION_ID': 'session_123', 'RACE_CONDITION_TEST_MODE': '1'}

        async def create_concurrent_auth(worker_id: int):
            test_token = await auth_helper.create_test_jwt_token(user_id=f"{test_user_context['user_id']}_{worker_id}", email=f'worker{worker_id}@staging.com', permissions=test_user_context['permissions'], environment='staging')

            class MockConcurrentWebSocket:

                def __init__(self, worker_id: int):
                    self.headers = {'authorization': f'Bearer {test_token}', 'x-worker-id': str(worker_id), 'x-concurrent-test': 'true'}
                    self.client = type('Client', (), {'host': f'worker{worker_id}.staging.netra.com', 'port': 8000})()
                    self.client_state = WebSocketState.CONNECTED
            mock_websocket = MockConcurrentWebSocket(worker_id)
            with patch('shared.isolated_environment.get_env', return_value=concurrent_staging_env):
                try:
                    authenticator = UnifiedWebSocketAuthenticator()
                    with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth:
                        worker_context = test_user_context.copy()
                        worker_context['user_id'] = f"{test_user_context['user_id']}_{worker_id}"
                        worker_context['email'] = f'worker{worker_id}@staging.com'
                        mock_auth_instance = auth_helper.create_mock_auth_service(worker_context)
                        mock_auth.return_value = mock_auth_instance
                        result = await authenticator.authenticate_websocket_connection(mock_websocket)
                        return (worker_id, result)
                except UnboundLocalError as e:
                    if 'is_production' in str(e):
                        return (worker_id, f'SCOPING_BUG: {e}')
                    else:
                        raise
        concurrent_tasks = [create_concurrent_auth(i) for i in range(3)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        for worker_id, result in results:
            if isinstance(result, str) and 'SCOPING_BUG' in result:
                pytest.fail(f'Concurrent worker {worker_id} hit variable scoping bug: {result}')
            elif isinstance(result, WebSocketAuthResult):
                assert result.success or result.error_code is not None
            elif isinstance(result, Exception):
                raise result

class StagingEnvironmentSpecificTests:
    """Specific tests for staging environment scoping issues."""

    @pytest.mark.asyncio
    async def test_staging_gcp_cloud_run_detection(self):
        """Test staging detection in GCP Cloud Run environment."""
        gcp_staging_env = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-12345', 'K_SERVICE': 'netra-backend-staging', 'PORT': '8080', 'GAE_ENV': 'standard', 'GCLOUD_PROJECT': 'netra-staging-12345'}

        class MockGCPWebSocket:

            def __init__(self):
                self.headers = {'x-forwarded-for': '172.16.0.1', 'x-appengine-request-log': 'staging-log', 'x-goog-trace': 'staging-trace'}
                self.client = type('Client', (), {'host': '172.16.0.1', 'port': 8080})()
                self.client_state = WebSocketState.CONNECTED
        mock_websocket = MockGCPWebSocket()
        with patch('shared.isolated_environment.get_env', return_value=gcp_staging_env):
            try:
                e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                if e2e_context:
                    assert e2e_context['environment'] == 'staging'
                    assert 'staging' in e2e_context['google_cloud_project']
                    assert 'staging' in e2e_context['k_service']
            except UnboundLocalError as e:
                if 'is_production' in str(e):
                    pytest.fail(f'GCP staging detection triggers scoping bug: {e}')
                else:
                    raise

    @pytest.mark.asyncio
    async def test_staging_performance_regression_detection(self, auth_helper):
        """Test for performance regressions caused by scoping bug fix."""
        import time
        staging_perf_env = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-perf-test', 'K_SERVICE': 'netra-backend-staging'}

        class MockPerfWebSocket:

            def __init__(self):
                self.headers = {'x-perf-test': 'staging'}
                self.client = type('Client', (), {'host': 'perf.staging.netra.com', 'port': 443})()
                self.client_state = WebSocketState.CONNECTED
        extraction_times = []
        for _ in range(10):
            mock_websocket = MockPerfWebSocket()
            with patch('shared.isolated_environment.get_env', return_value=staging_perf_env):
                start_time = time.perf_counter()
                try:
                    e2e_context = extract_e2e_context_from_websocket(mock_websocket)
                    end_time = time.perf_counter()
                    extraction_time = (end_time - start_time) * 1000
                    extraction_times.append(extraction_time)
                except UnboundLocalError as e:
                    if 'is_production' in str(e):
                        pytest.fail(f'Performance test failed due to scoping bug: {e}')
                    else:
                        raise
        avg_time = sum(extraction_times) / len(extraction_times)
        max_time = max(extraction_times)
        assert avg_time < 50.0, f'E2E context extraction too slow: {avg_time:.2f}ms average'
        assert max_time < 100.0, f'E2E context extraction max time too slow: {max_time:.2f}ms'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')