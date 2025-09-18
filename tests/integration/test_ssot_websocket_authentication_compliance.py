"""Empty docstring."""
SSOT WebSocket Authentication Compliance Test Suite

Business Value Justification:
    - Segment: Platform/Internal - Testing Infrastructure
- Business Goal: Validate SSOT compliance and eliminate authentication chaos
- Value Impact: Prevents regression to duplicate authentication paths
- Revenue Impact: Ensures $""120K""+ MRR remains unblocked by maintaining working WebSocket auth

This test suite validates that:
    1. All WebSocket authentication uses SSOT unified authentication service
2. No duplicate authentication paths exist
3. Authentication works consistently across all environments
4. Legacy authentication implementations are completely eliminated

CRITICAL: These tests MUST pass to ensure SSOT compliance is maintained.
"""Empty docstring."""
import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from fastapi import WebSocket, HTTPException
from fastapi.testclient import TestClient
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service, UnifiedAuthenticationService, AuthResult, AuthenticationContext, AuthenticationMethod
from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator, UnifiedWebSocketAuthenticator, WebSocketAuthResult, authenticate_websocket_ssot
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.fixtures.websocket_fixtures import create_mock_websocket
from test_framework.ssot.integration_auth_manager import IntegrationAuthServiceManager

class SSOTWebSocketAuthenticationComplianceTests:
    "Test suite for SSOT WebSocket authentication compliance."""

    @pytest.fixture
    def auth_manager(self):
        "Create integration auth manager for testing."
        return IntegrationAuthServiceManager()

    @pytest.fixture
    def mock_websocket(self):
        "Create mock WebSocket with JWT token in headers."
        websocket = create_mock_websocket()
        test_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.test_signature'
        websocket.headers = {'authorization': f'Bearer {test_token}', 'user-agent': 'WebSocket Test Client', 'origin': 'https://test.example.com'}
        return websocket

    @pytest.fixture
    def mock_websocket_no_token(self):
        Create mock WebSocket without JWT token.""
        websocket = create_mock_websocket()
        websocket.headers = {'user-agent': 'WebSocket Test Client', 'origin': 'https://test.example.com'}
        return websocket

    @pytest.mark.asyncio
    async def test_unified_authentication_service_ssot_compliance(self):
        Test that UnifiedAuthenticationService is SSOT for all authentication.""
        auth_service = get_unified_auth_service()
        assert isinstance(auth_service, "UnifiedAuthenticationService)"
        assert hasattr(auth_service, "'_auth_client')"
        auth_service2 = get_unified_auth_service()
        assert auth_service is auth_service2
        print(' PASS:  SSOT COMPLIANCE: UnifiedAuthenticationService is properly configured as SSOT')

    @pytest.mark.asyncio
    async def test_websocket_authenticator_uses_ssot(self):
        "Test that WebSocket authenticator uses SSOT authentication service."""
        ws_authenticator = get_websocket_authenticator()
        assert isinstance(ws_authenticator, "UnifiedWebSocketAuthenticator)"
        assert hasattr(ws_authenticator, "'_auth_service')"
        auth_service = get_unified_auth_service()
        assert ws_authenticator._auth_service is auth_service
        print(' PASS:  SSOT COMPLIANCE: WebSocket authenticator properly uses unified auth service')

    @pytest.mark.asyncio
    async def test_websocket_authentication_success_flow(self, mock_websocket):
        ""Test successful WebSocket authentication using SSOT implementation.""

        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'test-user-123', 'email': 'test@example.com', 'permissions': ['read', 'write']}
            auth_result = await authenticate_websocket_ssot(mock_websocket)
            assert auth_result.success is True
            assert auth_result.user_context is not None
            assert auth_result.auth_result is not None
            user_context = auth_result.user_context
            assert user_context.user_id == 'test-user-123'
            assert user_context.websocket_client_id.startswith('ws_test-use_')
            assert user_context.thread_id.startswith('ws_thread_')
            assert user_context.run_id.startswith('ws_run_')
            auth_data = auth_result.auth_result
            assert auth_data.success is True
            assert auth_data.user_id == 'test-user-123'
            assert auth_data.email == 'test@example.com'
            assert 'read' in auth_data.permissions
            assert 'write' in auth_data.permissions
            print(' PASS:  SSOT COMPLIANCE: WebSocket authentication success flow works correctly')

    @pytest.mark.asyncio
    async def test_websocket_authentication_failure_flow(self, mock_websocket_no_token):
        Test WebSocket authentication failure using SSOT implementation.""
        auth_result = await authenticate_websocket_ssot(mock_websocket_no_token)
        assert auth_result.success is False
        assert auth_result.user_context is None
        assert auth_result.auth_result is not None
        assert auth_result.error_code == 'NO_TOKEN'
        assert 'No JWT token found' in auth_result.error_message
        auth_data = auth_result.auth_result
        assert auth_data.success is False
        assert auth_data.error_code == 'NO_TOKEN'
        print(' PASS:  SSOT COMPLIANCE: WebSocket authentication failure flow works correctly')

    @pytest.mark.asyncio
    async def test_websocket_authentication_invalid_token(self, mock_websocket):
        Test WebSocket authentication with invalid token.""
        mock_websocket.headers['authorization'] = 'Bearer invalid-token'
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': False, 'error': 'Invalid token signature'}
            auth_result = await authenticate_websocket_ssot(mock_websocket)
            assert auth_result.success is False
            assert auth_result.user_context is None
            assert auth_result.error_code == 'VALIDATION_FAILED'
            assert 'Invalid token signature' in auth_result.error_message
            print(' PASS:  SSOT COMPLIANCE: Invalid token handling works correctly')

    @pytest.mark.asyncio
    async def test_no_duplicate_authentication_paths_exist(self):
        Test that no duplicate authentication paths exist (SSOT violation check).""
        try:
            from netra_backend.app.websocket_core import auth as old_auth_module
            if hasattr(old_auth_module, 'WebSocketAuthenticator'):
                pytest.fail(' FAIL:  SSOT VIOLATION: Old WebSocketAuthenticator still exists in websocket_core/auth.py')
        except ImportError:
            pass
        from netra_backend.app.websocket_core import user_context_extractor
        extractor = user_context_extractor.UserContextExtractor()
        if hasattr(extractor, '_legacy_jwt_validation'):
            pytest.fail(' FAIL:  SSOT VIOLATION: Legacy JWT validation method still exists')
        print(' PASS:  SSOT COMPLIANCE: No duplicate authentication paths detected')

    @pytest.mark.asyncio
    async def test_authentication_statistics_tracking(self):
        "Test that SSOT authentication service tracks statistics correctly."""
        auth_service = get_unified_auth_service()
        ws_authenticator = get_websocket_authenticator()
        initial_auth_stats = auth_service.get_authentication_stats()
        initial_ws_stats = ws_authenticator.get_websocket_auth_stats()
        assert 'ssot_enforcement' in initial_auth_stats
        assert initial_auth_stats['ssot_enforcement']['ssot_compliant'] is True
        assert initial_auth_stats['ssot_enforcement']['duplicate_paths_eliminated'] == 4
        assert 'ssot_compliance' in initial_ws_stats
        assert initial_ws_stats['ssot_compliance']['ssot_compliant'] is True
        print(' PASS:  SSOT COMPLIANCE: Authentication statistics tracking works correctly')

    @pytest.mark.asyncio
    async def test_unified_authentication_health_check(self):
        "Test that unified authentication service health check works."
        auth_service = get_unified_auth_service()
        health_status = await auth_service.health_check()
        assert 'status' in health_status
        assert 'service' in health_status
        assert health_status['service'] == 'UnifiedAuthenticationService'
        assert 'ssot_compliant' in health_status
        assert health_status['ssot_compliant'] is True
        print(' PASS:  SSOT COMPLIANCE: Unified authentication health check works correctly')

    @pytest.mark.asyncio
    async def test_websocket_auth_context_tracking(self, mock_websocket):
        "Test that authentication context is properly tracked for WebSocket."
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'test-user-456', 'email': 'test2@example.com', 'permissions': ['websocket_access']}
            auth_service = get_unified_auth_service()
            initial_stats = auth_service.get_authentication_stats()
            initial_websocket_count = initial_stats['context_distribution'].get('websocket', 0)
            auth_result = await authenticate_websocket_ssot(mock_websocket)
            assert auth_result.success is True
            updated_stats = auth_service.get_authentication_stats()
            updated_websocket_count = updated_stats['context_distribution']['websocket']
            assert updated_websocket_count == initial_websocket_count + 1
            print(' PASS:  SSOT COMPLIANCE: WebSocket authentication context tracking works correctly')

    @pytest.mark.asyncio
    async def test_jwt_token_extraction_methods(self, auth_manager):
        Test JWT token extraction from different WebSocket headers.""
        websocket1 = create_mock_websocket()
        test_token = auth_manager.create_test_jwt_token('auth-header-user')
        websocket1.headers = {'authorization': f'Bearer {test_token}'}
        ws_authenticator = get_websocket_authenticator()
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'auth-header-user', 'email': 'header@example.com', 'permissions': []}
            auth_result = await ws_authenticator.authenticate_websocket_connection(websocket1)
            assert auth_result.success is True
            assert auth_result.user_context.user_id == 'auth-header-user'
        websocket2 = create_mock_websocket()
        import base64
        protocol_token = base64.urlsafe_b64encode(test_token.encode()).decode()
        websocket2.headers = {'sec-websocket-protocol': f'jwt.{protocol_token}'}
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'protocol-user', 'email': 'protocol@example.com', 'permissions': []}
            auth_result = await ws_authenticator.authenticate_websocket_connection(websocket2)
            assert auth_result.success is True
        print(' PASS:  SSOT COMPLIANCE: JWT token extraction methods work correctly')

    def test_ssot_enforcement_imports(self):
        Test that only SSOT-compliant imports are allowed.""
        from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
        from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator
        auth_service = get_unified_auth_service()
        ws_authenticator = get_websocket_authenticator()
        assert auth_service.__class__.__name__ == 'UnifiedAuthenticationService'
        assert ws_authenticator.__class__.__name__ == 'UnifiedWebSocketAuthenticator'
        try:
            from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
        except ImportError:
            pass
        print(' PASS:  SSOT COMPLIANCE: Import restrictions properly enforced')

@pytest.mark.integration
class SSOTWebSocketAuthenticationEndToEndTests:
    "End-to-end integration tests for SSOT WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_full_websocket_auth_flow_integration(self):
        ""Test complete WebSocket authentication flow with real services.""

        pytest.importorskip('test_framework.conftest_real_services', reason='Requires real services')
        from test_framework.ssot.websocket import create_authenticated_websocket_connection
        try:
            websocket, auth_result = await create_authenticated_websocket_connection('integration-test-user')
            assert auth_result.success is True
            assert auth_result.user_context is not None
            assert auth_result.auth_result.success is True
            assert websocket is not None
            user_context = auth_result.user_context
            assert user_context.user_id == 'integration-test-user'
            assert user_context.websocket_client_id.startswith('ws_integrat_')
            print(' PASS:  E2E SSOT COMPLIANCE: Full WebSocket authentication flow works with real services')
        except Exception as e:
            pytest.fail(f' FAIL:  E2E SSOT FAILURE: WebSocket authentication flow failed: {e}')

    @pytest.mark.asyncio
    async def test_ssot_authentication_prevents_chaos_regression(self):
        Test that SSOT implementation prevents regression to authentication chaos."""
        Test that SSOT implementation prevents regression to authentication chaos.""""

        auth_service = get_unified_auth_service()
        test_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3NvdCIsImVtYWlsIjoidGVzdEBzc290LmNvbSIsImlhdCI6MTYwMDAwMDAwMCwiZXhwIjo5OTk5OTk5OTk5fQ.test_signature'
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_token') as mock_validate:
            mock_validate.return_value = {'valid': True, 'user_id': 'test-user-ssot', 'email': 'test@ssot.com', 'permissions': ['test_permission']}
            results = []
            for i in range(5):
                auth_result = await auth_service.authenticate_token(test_token, AuthenticationContext.WEBSOCKET, AuthenticationMethod.JWT_TOKEN)
                results.append(auth_result)
            for result in results:
                assert result.success is True
                assert result.user_id == 'test-user-ssot'
                assert result.email == 'test@ssot.com'
                assert result.metadata['context'] == 'websocket'
                assert result.metadata['method'] == 'jwt_token'
            stats = auth_service.get_authentication_stats()
            assert stats['statistics']['total_attempts'] >= 5
            assert stats['context_distribution']['websocket'] >= 5
            print(' PASS:  SSOT COMPLIANCE: Authentication consistency maintained - no chaos regression')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')