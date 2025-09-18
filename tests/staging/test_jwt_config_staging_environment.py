"""
Staging Environment Tests for JWT Configuration Crisis (Issue #681)

Tests validate JWT configuration in actual staging environment.
These tests run against the real staging deployment to verify JWT secret resolution.

Business Value: Validates $50K MRR WebSocket functionality in staging environment
Architecture: Staging environment validation (no mocks, real environment)
"""
import pytest
import asyncio
import logging
import os
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
logger = logging.getLogger(__name__)

class StagingJWTConfigurationEnvironmentTests(SSotAsyncTestCase):
    """Staging environment tests for JWT configuration validation."""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Set up staging environment validation."""
        env = get_env()
        environment = env.get('ENVIRONMENT', '').lower()
        if environment != 'staging':
            pytest.skip('This test suite only runs in staging environment')

    async def asyncSetUp(self):
        """Set up async test fixtures."""
        await super().asyncSetUp()
        self.env = get_env()

    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        try:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            get_jwt_secret_manager().clear_cache()
        except Exception:
            pass
        await super().asyncTearDown()

    async def test_staging_environment_jwt_secret_resolution(self):
        """
        CRITICAL STAGING TEST: Validate JWT secret resolution in actual staging.
        
        This test validates Issue #681 fix by checking JWT secret resolution
        in the real staging environment where the failure occurs.
        
        Expected After Fix:
        - JWT_SECRET_STAGING or JWT_SECRET_KEY should be configured
        - JWT secret resolution should succeed
        - No ValueError about missing staging configuration
        """
        from shared.jwt_secret_manager import get_unified_jwt_secret
        try:
            secret = get_unified_jwt_secret()
            assert secret is not None
            assert isinstance(secret, str)
            assert len(secret) >= 32, f'JWT secret too short: {len(secret)} characters'
            logger.info(f'SUCCESS: JWT secret resolved in staging (length: {len(secret)})')
        except ValueError as e:
            error_message = str(e)
            if 'JWT secret not configured for staging environment' in error_message:
                pytest.fail(f'ISSUE #681 CONFIRMED: JWT secret not configured in staging environment. Error: {error_message}')
            else:
                pytest.fail(f'Unexpected JWT configuration error: {error_message}')

    async def test_staging_environment_variable_presence(self):
        """
        Test presence of expected JWT environment variables in staging.
        
        This diagnostic test checks what JWT-related environment variables
        are actually available in the staging environment.
        """
        env = get_env()
        jwt_env_vars = ['JWT_SECRET_STAGING', 'JWT_SECRET_KEY', 'JWT_SECRET', 'JWT_ALGORITHM']
        available_vars = {}
        for var_name in jwt_env_vars:
            value = env.get(var_name)
            if value:
                available_vars[var_name] = f'present (length: {len(value)})'
            else:
                available_vars[var_name] = 'NOT SET'
        logger.info(f'Staging JWT environment variables: {available_vars}')
        jwt_secret_vars = ['JWT_SECRET_STAGING', 'JWT_SECRET_KEY', 'JWT_SECRET']
        has_jwt_secret = any((env.get(var) for var in jwt_secret_vars))
        if not has_jwt_secret:
            pytest.fail(f'No JWT secret environment variables configured in staging. Available: {available_vars}. This confirms Issue #681: missing JWT configuration in staging.')
        logger.info('SUCCESS: At least one JWT secret variable is configured in staging')

    async def test_staging_unified_secrets_manager_integration(self):
        """
        Test UnifiedSecretsManager integration in staging environment.
        
        This tests the exact path used by fastapi_auth_middleware.py:696
        that fails with the JWT configuration error.
        """
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        try:
            secret = get_jwt_secret()
            assert secret is not None
            assert len(secret) >= 32
            logger.info('SUCCESS: UnifiedSecretsManager resolved JWT secret in staging')
        except ValueError as e:
            error_message = str(e)
            if 'JWT secret not configured' in error_message:
                pytest.fail(f'ISSUE #681 CONFIRMED: UnifiedSecretsManager cannot resolve JWT secret. Error: {error_message}')
            else:
                pytest.fail(f'Unexpected JWT secrets manager error: {error_message}')

    async def test_staging_websocket_auth_middleware_initialization(self):
        """
        Test WebSocket auth middleware initialization in staging.
        
        This tests whether the WebSocket authentication middleware can
        initialize successfully with the current JWT configuration.
        """
        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
        from unittest.mock import Mock
        try:
            middleware = FastAPIAuthMiddleware(Mock())
            secret = await middleware.configure_jwt_secret()
            assert secret is not None
            assert len(secret) >= 32
            logger.info('SUCCESS: WebSocket auth middleware initialized in staging')
        except ValueError as e:
            error_message = str(e)
            if 'JWT secret not configured' in error_message:
                pytest.fail(f'ISSUE #681 CONFIRMED: WebSocket auth middleware cannot initialize. This blocks $50K MRR WebSocket functionality. Error: {error_message}')
            else:
                pytest.fail(f'Unexpected middleware initialization error: {error_message}')

    async def test_staging_jwt_secret_validation_comprehensive(self):
        """
        Comprehensive JWT secret validation in staging environment.
        
        This test validates all aspects of JWT configuration that could
        cause the Issue #681 failure.
        """
        from shared.jwt_secret_manager import get_jwt_secret_manager
        manager = get_jwt_secret_manager()
        try:
            secret = manager.get_jwt_secret()
            logger.info(f'JWT secret resolved: length {len(secret)}')
        except Exception as e:
            pytest.fail(f'JWT secret resolution failed: {str(e)}')
        try:
            algorithm = manager.get_jwt_algorithm()
            assert algorithm in ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
            logger.info(f'JWT algorithm resolved: {algorithm}')
        except Exception as e:
            pytest.fail(f'JWT algorithm resolution failed: {str(e)}')
        validation_result = manager.validate_jwt_configuration()
        if not validation_result['valid']:
            pytest.fail(f"JWT configuration validation failed in staging. Issues: {validation_result['issues']}. This confirms Issue #681.")
        debug_info = manager.get_debug_info()
        logger.info(f'JWT debug info: {debug_info}')
        environment = self.env.get('ENVIRONMENT', 'staging')
        is_valid, context = manager.validate_jwt_secret_for_environment(secret, environment)
        if not is_valid:
            pytest.fail(f'JWT secret validation failed for staging environment. Context: {context}. This confirms Issue #681.')
        logger.info('SUCCESS: Comprehensive JWT configuration validation passed in staging')

class StagingWebSocketJWTIntegrationTests(SSotAsyncTestCase):
    """Test WebSocket JWT integration in staging environment."""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Set up staging environment validation."""
        env = get_env()
        environment = env.get('ENVIRONMENT', '').lower()
        if environment != 'staging':
            pytest.skip('This test suite only runs in staging environment')

    async def test_staging_websocket_manager_jwt_integration(self):
        """
        Test WebSocket manager JWT integration in staging.
        
        This validates that WebSocket functionality works with JWT configuration
        after Issue #681 is resolved.
        """
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            manager = WebSocketManager()
            logger.info('WebSocket manager created successfully in staging')
        except Exception as e:
            error_message = str(e)
            if any((term in error_message.lower() for term in ['jwt', 'secret', 'configuration'])):
                pytest.fail(f'ISSUE #681 CONFIRMED: WebSocket manager initialization failed due to JWT config. Error: {error_message}')
            else:
                logger.warning(f'WebSocket manager initialization failed (non-JWT issue): {error_message}')

    async def test_staging_golden_path_jwt_validation(self):
        """
        Test Golden Path JWT validation in staging environment.
        
        Golden Path: User login -> WebSocket authentication -> Agent events -> AI response
        Critical Point: WebSocket authentication requires JWT configuration
        """
        from shared.jwt_secret_manager import get_unified_jwt_secret
        try:
            secret = get_unified_jwt_secret()
            assert secret is not None
            logger.info('Golden Path Step 1: JWT secret available for WebSocket authentication')
            from netra_backend.app.websocket_core.auth import WebSocketAuth
            auth = WebSocketAuth()
            logger.info('Golden Path Step 2: WebSocket authentication components available')
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            manager = WebSocketManager()
            logger.info('Golden Path Step 3: WebSocket manager available for agent events')
            logger.info('SUCCESS: Golden Path JWT dependencies validated in staging')
        except ValueError as e:
            error_message = str(e)
            if 'JWT secret not configured' in error_message:
                pytest.fail(f'ISSUE #681 CONFIRMED: Golden Path blocked by JWT configuration. This prevents users from getting AI responses via WebSocket. Error: {error_message}')
            else:
                pytest.fail(f'Unexpected Golden Path JWT validation error: {error_message}')

class StagingJWTConfigurationBusinessImpactTests(SSotAsyncTestCase):
    """Test business impact validation in staging environment."""

    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Set up staging environment validation."""
        env = get_env()
        environment = env.get('ENVIRONMENT', '').lower()
        if environment != 'staging':
            pytest.skip('This test suite only runs in staging environment')

    async def test_staging_websocket_revenue_functionality_validation(self):
        """
        Test $50K MRR WebSocket functionality validation in staging.
        
        This test validates that the revenue-critical WebSocket features
        can function properly after Issue #681 JWT configuration is fixed.
        """
        from shared.jwt_secret_manager import get_unified_jwt_secret
        try:
            secret = get_unified_jwt_secret()
            assert secret is not None
            logger.info('SUCCESS: JWT secret available for $50K MRR WebSocket functionality')
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            unified_secret = get_jwt_secret()
            assert unified_secret == secret
            logger.info('SUCCESS: Unified secrets integration validated for revenue functionality')
        except ValueError as e:
            error_message = str(e)
            pytest.fail(f'CRITICAL BUSINESS IMPACT: $50K MRR WebSocket functionality blocked in staging. Issue #681 JWT configuration prevents revenue-generating features. Error: {error_message}')

    async def test_staging_deployment_confidence_validation(self):
        """
        Test deployment confidence validation in staging.
        
        This test ensures staging environment can validate Golden Path
        before production deployment, which is blocked by Issue #681.
        """
        validation_steps = []
        try:
            from shared.jwt_secret_manager import validate_unified_jwt_config
            config_result = validate_unified_jwt_config()
            if config_result['valid']:
                validation_steps.append('JWT configuration valid')
            else:
                raise ValueError(f"JWT configuration invalid: {config_result['issues']}")
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            secret = get_jwt_secret()
            validation_steps.append('WebSocket authentication ready')
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            manager = WebSocketManager()
            validation_steps.append('Golden Path components available')
            logger.info(f'SUCCESS: Staging deployment validation complete: {validation_steps}')
        except Exception as e:
            error_message = str(e)
            pytest.fail(f'DEPLOYMENT CONFIDENCE BLOCKED: Issue #681 prevents staging validation. Cannot validate Golden Path before production deployment. Failed at step {len(validation_steps) + 1}. Completed steps: {validation_steps}. Error: {error_message}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')