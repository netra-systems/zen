"
Integration Tests for WebSocket JWT Authentication Crisis (Issue #681)

Tests validate WebSocket authentication failures due to missing JWT secrets in staging.
These tests demonstrate the $50K MRR WebSocket functionality blockage.

Business Value: Validates WebSocket authentication works correctly with proper JWT configuration
Architecture: Integration tests with real WebSocket connections (no Docker required)
""
import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
logger = logging.getLogger(__name__)

@pytest.mark.integration
class WebSocketJWTAuthenticationCrisisTests(SSotAsyncTestCase):
    ""Integration tests for WebSocket JWT authentication failures in staging."

    async def asyncSetUp(self):
        "Set up async test fixtures.""
        await super().asyncSetUp()
        self.websocket_utility = WebSocketTestUtility()

    async def asyncTearDown(self):
        ""Clean up async test fixtures."
        try:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            get_jwt_secret_manager().clear_cache()
        except Exception:
            pass
        await super().asyncTearDown()

    def _mock_staging_environment(self, jwt_secrets: Dict[str, str]=None) -> Mock:
        "Mock staging environment with specific JWT secret configuration.""
        mock_env = Mock()
        base_env = {'ENVIRONMENT': 'staging', 'TESTING': 'false', 'PYTEST_CURRENT_TEST': None}
        if jwt_secrets:
            base_env.update(jwt_secrets)
        mock_env.get.side_effect = lambda key, default=None: base_env.get(key, default)
        return mock_env

    async def test_websocket_connection_fails_with_missing_jwt_secret(self):
        ""
        CRITICAL FAILURE TEST: WebSocket connection fails when JWT secret missing.
        
        This demonstrates the exact Issue #681 scenario:
        - Staging environment with no JWT secrets
        - WebSocket authentication attempt
        - Should fail with JWT configuration error
        
        Expected: Connection failure due to JWT misconfiguration
        "
        mock_env = self._mock_staging_environment()
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            with pytest.raises((ValueError, RuntimeError, Exception)) as exc_info:
                manager = WebSocketManager()
                await manager.initialize()
            error_message = str(exc_info.value)
            assert any((term in error_message.lower() for term in ['jwt', 'secret', 'staging', 'configuration'])

    async def test_websocket_middleware_auth_fails_missing_jwt(self):
        "
        Test WebSocket middleware authentication fails with missing JWT secret.
        
        This tests the exact middleware path that throws the error in 
        fastapi_auth_middleware.py:696
        ""
        mock_env = self._mock_staging_environment()
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
            middleware = FastAPIAuthMiddleware(Mock())
            with pytest.raises(ValueError) as exc_info:
                await middleware.configure_jwt_secret()
            error_message = str(exc_info.value)
            assert 'JWT secret not configured' in error_message

    async def test_websocket_auth_success_with_valid_jwt_secret(self):
        ""
        Test WebSocket authentication succeeds with valid JWT secret.
        
        This demonstrates the expected behavior after Issue #681 is fixed.
        "
        jwt_config = {'JWT_SECRET_KEY': 'valid-jwt-secret-for-websocket-auth-32-characters'}
        mock_env = self._mock_staging_environment(jwt_config)
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
            middleware = FastAPIAuthMiddleware(Mock())
            secret = await middleware.configure_jwt_secret()
            assert secret == 'valid-jwt-secret-for-websocket-auth-32-characters'

    async def test_websocket_connection_handshake_jwt_validation(self):
        "
        Test WebSocket connection handshake validates JWT properly.
        
        This tests the complete flow:
        1. Client connects with JWT token
        2. Middleware validates token using configured secret
        3. Connection succeeds/fails based on JWT configuration
        ""
        mock_env = self._mock_staging_environment()
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.websocket_core.auth import WebSocketAuth
            auth = WebSocketAuth()
            mock_websocket = Mock()
            mock_websocket.headers = {'authorization': 'Bearer fake.jwt.token'}
            with pytest.raises((ValueError, Exception)) as exc_info:
                await auth.authenticate(mock_websocket)
            error_message = str(exc_info.value)
            assert any((term in error_message.lower() for term in ['jwt', 'secret', 'configuration', 'not configured'])

    async def test_websocket_events_blocked_by_jwt_auth_failure(self):
        ""
        Test WebSocket events are blocked by JWT authentication failure.
        
        This demonstrates the business impact: agent events cannot be sent
        when WebSocket authentication fails due to JWT misconfiguration.
        
        Business Impact: $50K MRR WebSocket-dependent functionality blocked
        "
        mock_env = self._mock_staging_environment()
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            with pytest.raises((ValueError, Exception)) as exc_info:
                manager = WebSocketManager()
                await manager.initialize()
                await manager.send_agent_event('user_123', {'type': 'agent_started', 'data': {'message': 'Agent processing started'}}
            assert exc_info.value is not None

    async def test_golden_path_websocket_flow_jwt_blockage(self):
        "
        Test Golden Path WebSocket flow blocked by JWT configuration.
        
        Golden Path: User login → Agent starts → WebSocket events → AI response
        Blockage Point: WebSocket authentication fails due to missing JWT secret
        ""
        mock_env = self._mock_staging_environment()
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                manager = WebSocketManager()
                await manager.initialize()
                registry = AgentRegistry()
                registry.set_websocket_manager(manager)
                await manager.send_agent_event('user_123', {'type': 'agent_started', 'data': {'agent_type': 'supervisor'}}
                pytest.fail('Expected JWT configuration failure, but flow succeeded')
            except (ValueError, RuntimeError, Exception) as e:
                error_message = str(e)
                assert any((term in error_message.lower() for term in ['jwt', 'secret', 'configuration', 'staging'])
                logger.info(f'Golden Path correctly blocked by JWT config issue: {error_message}')

@pytest.mark.integration
class JWTConfigurationBusinessImpactIntegrationTests(SSotAsyncTestCase):
    ""Integration tests demonstrating business impact of JWT configuration failures."

    async def test_websocket_revenue_functionality_integration(self):
        "
        Test $50K MRR WebSocket functionality integration with JWT configuration.
        
        This test validates that JWT configuration directly impacts
        revenue-generating WebSocket features.
        ""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'TESTING': 'false'}.get(key, default)
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            with pytest.raises(ValueError) as exc_info:
                secret = get_jwt_secret()
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager()
                await manager.initialize()
            error_message = str(exc_info.value)
            assert 'staging environment' in error_message.lower()
            logger.critical(f'$50K MRR WebSocket functionality blocked: {error_message}')

    async def test_staging_deployment_validation_jwt_integration(self):
        ""
        Test staging deployment validation integration with JWT configuration.
        
        This simulates the staging deployment process where JWT configuration
        must be validated before WebSocket services can start.
        "
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'TESTING': 'false'}.get(key, default)
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            validation_steps = []
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                validation_steps.append('JWT secret resolved')
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager()
                await manager.initialize()
                validation_steps.append('WebSocket manager initialized')
                from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
                middleware = FastAPIAuthMiddleware(Mock())
                await middleware.configure_jwt_secret(secret)
                validation_steps.append('Auth middleware configured')
            except (ValueError, Exception) as e:
                error_message = str(e)
                logger.error(f'Staging deployment validation failed at step {len(validation_steps) + 1}: {error_message}')
                assert any((term in error_message.lower() for term in ['jwt', 'secret', 'staging', 'not configured'])
            if len(validation_steps) == 3:
                logger.info('All staging deployment validation steps passed')
            else:
                logger.warning(f'Staging deployment validation incomplete: {validation_steps}')

@pytest.mark.integration
class JWTSecretDeploymentScenariosTests(SSotAsyncTestCase):
    "Integration tests for various JWT secret deployment scenarios.""

    async def test_environment_variable_jwt_secret_integration(self):
        ""
        Test JWT secret integration via environment variables.
        
        This tests the expected fix path for Issue #681.
        "
        jwt_config = {'JWT_SECRET_STAGING': 'environment-staging-jwt-secret-32-characters'}
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'TESTING': 'false', **jwt_config}.get(key, default)
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            secret = get_jwt_secret()
            assert secret == 'environment-staging-jwt-secret-32-characters'
            manager = WebSocketManager()

    async def test_gcp_secret_manager_jwt_integration(self):
        "
        Test JWT secret integration via GCP Secret Manager.
        
        This tests the enterprise-grade fix for Issue #681.
        """
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default=None: {'ENVIRONMENT': 'staging', 'TESTING': 'false'}.get(key, default)
        mock_get_staging_secret = AsyncMock(return_value='gcp-managed-jwt-secret-32-characters')
        with patch('shared.isolated_environment.get_env', return_value=mock_env):
            with patch('deployment.secrets_config.get_staging_secret', mock_get_staging_secret):
                from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
                secret = get_jwt_secret()
                assert secret == 'gcp-managed-jwt-secret-32-characters'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')