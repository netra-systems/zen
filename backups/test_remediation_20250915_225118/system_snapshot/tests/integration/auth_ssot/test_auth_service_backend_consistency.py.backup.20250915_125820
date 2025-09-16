"""
SSOT Authentication Service-Backend Consistency Test - ISSUE #814

PURPOSE: Integration test that FAILS when auth service and backend have inconsistent JWT handling
EXPECTED: FAIL - Demonstrates current inconsistencies between auth service and backend
TARGET: Identify authentication flow inconsistencies that break SSOT patterns

CRITICAL: This test is designed to FAIL until Issue #814 SSOT remediation is complete.
"""
import logging
import pytest
import asyncio
import json
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestAuthServiceBackendConsistency(SSotAsyncTestCase):
    """
    Integration test validating consistency between auth service and backend JWT handling.
    EXPECTED TO FAIL until SSOT remediation ensures single source of truth.
    """

    async def asyncSetUp(self):
        """Setup auth service and backend clients for consistency testing"""
        await super().asyncSetUp()
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            self.auth_service_jwt = JWTHandler()
        except ImportError as e:
            self.skipTest(f'Auth service not available: {e}')
        try:
            from netra_backend.app.auth_integration.auth import get_current_user_dependency
            self.backend_auth = get_current_user_dependency
        except ImportError as e:
            self.skipTest(f'Backend auth integration not available: {e}')

    async def test_jwt_secret_consistency_between_services(self):
        """
        EXPECTED: FAIL - JWT secrets likely inconsistent between services

        Validates that auth service and backend use the same JWT secret.
        Inconsistency breaks Golden Path authentication flow.
        """
        auth_service_secret = self.auth_service_jwt.secret
        try:
            from netra_backend.app.config import get_config
            backend_config = get_config()
            backend_secret = getattr(backend_config, 'JWT_SECRET_KEY', None)
            if backend_secret is None:
                import os
                backend_secret = os.getenv('JWT_SECRET_KEY')
        except Exception as e:
            pytest.fail(f'Backend JWT secret access inconsistent: {e}. SSOT violation - auth service is authoritative source.')
        assert auth_service_secret == backend_secret, f'JWT secret inconsistency detected. Auth service secret exists: {auth_service_secret is not None}, Backend secret exists: {backend_secret is not None}. SSOT violation - only auth service should manage JWT secrets.'

    async def test_token_validation_consistency(self):
        """
        EXPECTED: FAIL - Token validation likely inconsistent between services

        Creates token with auth service, validates with backend.
        Inconsistency indicates SSOT violations.
        """
        test_user_data = {'user_id': 'test-user-123', 'email': 'test@example.com', 'tier': 'free'}
        try:
            auth_service_token = self.auth_service_jwt.create_access_token(user_id=test_user_data['user_id'], user_data=test_user_data)
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.auth_integration.auth import validate_token_with_auth_service
            backend_validation = await validate_token_with_auth_service(auth_service_token)
            assert backend_validation is not None, 'Backend validation returned None'
            assert backend_validation.get('user_id') == test_user_data['user_id'], 'User ID mismatch between auth service and backend'
        except (ImportError, AttributeError, NameError) as e:
            pytest.fail(f'Backend auth service delegation missing: {e}. SSOT violation - backend should delegate to auth service.')
        except Exception as e:
            pytest.fail(f'Token validation inconsistency: {e}. Auth service created token, backend failed validation. SSOT violation.')

    async def test_websocket_auth_delegates_to_auth_service(self):
        """
        EXPECTED: FAIL - WebSocket auth likely bypasses auth service

        Tests WebSocket authentication delegation to auth service.
        Direct JWT handling in WebSocket breaks SSOT pattern.
        """
        try:
            test_token = self.auth_service_jwt.create_access_token(user_id='websocket-test-user', user_data={'email': 'ws@example.com'})
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.websocket_core.auth import validate_websocket_auth
            ws_validation = await validate_websocket_auth(test_token)
            assert ws_validation is not None, 'WebSocket validation returned None'
        except (ImportError, AttributeError) as e:
            pytest.fail(f'WebSocket auth service delegation missing: {e}. SSOT violation - WebSocket must delegate to auth service.')
        except Exception as e:
            pytest.fail(f'WebSocket authentication failed: {e}. Likely bypassing auth service SSOT pattern.')

    async def test_message_route_auth_consistency(self):
        """
        EXPECTED: FAIL - Message routes likely bypass auth service

        Tests message/chat route authentication consistency with auth service.
        Route-level JWT handling breaks SSOT pattern.
        """
        try:
            test_token = self.auth_service_jwt.create_access_token(user_id='message-test-user', user_data={'email': 'msg@example.com', 'tier': 'enterprise'})
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.routes.threads_messages import authenticate_request
            route_auth = await authenticate_request(test_token)
            assert route_auth is not None, 'Message route auth returned None'
        except (ImportError, AttributeError) as e:
            pytest.fail(f'Message route auth service delegation missing: {e}. SSOT violation - routes must delegate to auth service.')
        except Exception as e:
            pytest.fail(f'Message route authentication failed: {e}. Likely implementing direct JWT handling instead of auth service delegation.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')