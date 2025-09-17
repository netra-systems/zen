"""
SSOT WebSocket Authentication Bypass Detection Test - ISSUE #814

PURPOSE: Test that FAILS when WebSocket authentication bypasses auth service SSOT
EXPECTED: FAIL - Demonstrates WebSocket auth bypass violations
TARGET: WebSocket authentication must delegate to auth service, not handle JWT directly

CRITICAL: This test is designed to FAIL until Issue #814 SSOT remediation is complete.
"""
import logging
import pytest
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
logger = logging.getLogger(__name__)

@pytest.mark.integration
class WebSocketAuthBypassDetectionTests(SSotAsyncTestCase):
    """
    Integration test detecting WebSocket authentication SSOT violations.
    EXPECTED TO FAIL until WebSocket auth properly delegates to auth service.
    """

    async def asyncSetUp(self):
        """Setup WebSocket and auth service components"""
        await super().asyncSetUp()
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            self.auth_service = JWTHandler()
        except ImportError as e:
            self.skipTest(f'Auth service not available: {e}')

    async def test_websocket_core_has_no_direct_jwt_decode(self):
        """
        EXPECTED: FAIL - WebSocket core likely has direct jwt.decode() usage

        Scans WebSocket core modules for direct JWT handling that bypasses auth service.
        """
        websocket_core_path = Path(__file__).parents[2] / 'netra_backend' / 'app' / 'websocket_core'
        violations = []
        if websocket_core_path.exists():
            for py_file in websocket_core_path.rglob('*.py'):
                if py_file.is_file():
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        if re.search('jwt\\.decode\\s*\\(', content):
                            violations.append(str(py_file.relative_to(websocket_core_path)))
                            logger.error(f'SSOT violation in WebSocket: {py_file}')
                    except Exception as e:
                        logger.warning(f'Could not scan {py_file}: {e}')
        assert len(violations) == 0, f'WebSocket SSOT violation: {len(violations)} files use direct jwt.decode(): {violations}. WebSocket authentication must delegate to auth service, not handle JWT directly.'

    async def test_websocket_routes_delegate_to_auth_service(self):
        """
        EXPECTED: FAIL - WebSocket routes likely implement direct auth

        Tests that WebSocket route handlers delegate authentication to auth service.
        """
        violations = []
        routes_path = Path(__file__).parents[2] / 'netra_backend' / 'app' / 'routes'
        for py_file in routes_path.rglob('*websocket*.py'):
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding='utf-8')
                    jwt_operations = ['jwt\\.decode\\s*\\(', 'jwt\\.encode\\s*\\(', 'PyJWT', 'from jwt import']
                    for operation in jwt_operations:
                        if re.search(operation, content):
                            violations.append(f'{py_file}: {operation}')
                            logger.error(f'WebSocket route SSOT violation: {py_file} - {operation}')
                except Exception as e:
                    logger.warning(f'Could not scan {py_file}: {e}')
        assert len(violations) == 0, f'WebSocket route SSOT violations: {violations}. WebSocket routes must delegate authentication to auth service.'

    async def test_websocket_authentication_flow_uses_auth_service(self):
        """
        EXPECTED: FAIL - WebSocket auth flow likely bypasses auth service

        Tests WebSocket authentication flow for proper auth service delegation.
        """
        try:
            test_token = self.auth_service.create_access_token(user_id='websocket-flow-test', user_data={'email': 'wsflow@example.com', 'tier': 'free'})
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
            authenticator = WebSocketAuthenticator()
            auth_result = await authenticator.authenticate_token(test_token)
            assert auth_result is not None, 'WebSocket authentication failed'
            assert auth_result.get('user_id') == 'websocket-flow-test', 'User ID mismatch'
        except (ImportError, AttributeError) as e:
            pytest.fail(f'WebSocket auth service delegation not implemented: {e}. SSOT violation - WebSocket must use auth service for authentication.')
        except Exception as e:
            pytest.fail(f'WebSocket authentication flow error: {e}. Likely bypassing auth service SSOT pattern.')

    async def test_websocket_user_context_extraction_delegates(self):
        """
        EXPECTED: FAIL - WebSocket user context likely extracts JWT directly

        Tests WebSocket user context extraction for SSOT compliance.
        User context should come from auth service, not direct JWT decode.
        """
        try:
            test_token = self.auth_service.create_access_token(user_id='context-test-user', user_data={'email': 'context@example.com', 'tier': 'enterprise', 'permissions': ['chat', 'api']})
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.websocket_core.auth import extract_user_context
            user_context = await extract_user_context(test_token)
            assert user_context is not None, 'User context extraction failed'
            assert user_context.get('user_id') == 'context-test-user', 'User context ID mismatch'
            assert user_context.get('tier') == 'enterprise', 'User context tier mismatch'
        except (ImportError, AttributeError) as e:
            pytest.fail(f'WebSocket user context extraction missing: {e}. SSOT violation - must delegate to auth service for user context.')
        except Exception as e:
            pytest.fail(f'WebSocket user context extraction error: {e}. Likely using direct JWT decode instead of auth service delegation.')

    async def test_websocket_events_preserve_auth_context(self):
        """
        EXPECTED: FAIL - WebSocket events likely don't preserve auth context properly

        Tests that WebSocket events maintain authentication context from auth service.
        Event handling should use auth service context, not recreate from JWT.
        """
        try:
            test_token = self.auth_service.create_access_token(user_id='event-test-user', user_data={'email': 'events@example.com', 'tier': 'mid'})
        except Exception as e:
            self.skipTest(f'Auth service token creation failed: {e}')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            ws_manager = WebSocketManager()
            event_result = await ws_manager.handle_authenticated_event(token=test_token, event_type='agent_started', event_data={'message': 'Test event'})
            assert event_result is not None, 'WebSocket event handling failed'
        except (ImportError, AttributeError) as e:
            pytest.fail(f'WebSocket event auth context handling missing: {e}. SSOT violation - events must preserve auth service context.')
        except Exception as e:
            pytest.fail(f'WebSocket event auth context error: {e}. Likely implementing custom auth instead of using auth service.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')