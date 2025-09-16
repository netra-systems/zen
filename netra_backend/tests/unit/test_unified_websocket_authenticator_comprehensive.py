"""
Comprehensive Unit Tests for UnifiedWebSocketAuthenticator - SSOT WebSocket Auth Business Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal - WebSocket Security Infrastructure  
- Business Goal: Restore WebSocket functionality and eliminate authentication failures
- Value Impact: Ensures WebSocket auth works correctly to restore $120K+ MRR chat functionality
- Strategic Impact: Critical WebSocket security that enables real-time AI chat interactions

This test suite validates the SSOT WebSocket authenticator business logic that replaced
4 duplicate WebSocket authentication implementations and fixes 1011 WebSocket errors.

CRITICAL: This authenticator is MISSION CRITICAL for chat revenue.
WebSocket auth failures directly block users from AI chat interactions.

Tests follow CLAUDE.md principles:
- Focus on business logic validation (NOT infrastructure)  
- Use IsolatedEnvironment for all env access
- Test security-critical scenarios: JWT validation, user isolation, session expiry
- Test E2E context detection and bypass logic
- Validate WebSocket state handling and error responses
- Test authentication statistics and monitoring
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from enum import Enum
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator, WebSocketAuthResult, get_websocket_authenticator, authenticate_websocket_ssot, extract_e2e_context_from_websocket, _safe_websocket_state_for_logging
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService, AuthResult, AuthenticationMethod, AuthenticationContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.clients.auth_client_core import AuthServiceError, AuthServiceConnectionError, AuthServiceValidationError
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics
from shared.isolated_environment import get_env

class MockWebSocketState(Enum):
    """Mock WebSocketState for testing without FastAPI dependency."""
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 3

class MockWebSocket:
    """Mock WebSocket for unit testing business logic."""

    def __init__(self, headers: Dict[str, str]=None, client_info: Dict[str, str]=None, state: MockWebSocketState=MockWebSocketState.CONNECTED):
        self.headers = headers or {}
        self.client_state = state
        self.client = Mock()
        if client_info:
            self.client.host = client_info.get('host', 'localhost')
            self.client.port = client_info.get('port', 8080)
        else:
            self.client.host = 'localhost'
            self.client.port = 8080
        self.send_json = AsyncMock()
        self.close = AsyncMock()

@pytest.mark.unit
class UnifiedWebSocketAuthenticatorBusinessLogicTests(SSotAsyncTestCase):
    """Test UnifiedWebSocketAuthenticator business logic."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.authenticator = UnifiedWebSocketAuthenticator()
        self.mock_auth_service = AsyncMock(spec=UnifiedAuthenticationService)
        self.authenticator._auth_service = self.mock_auth_service

    async def test_init_creates_proper_ssot_authenticator(self):
        """Test that authenticator initializes with SSOT compliance."""
        auth = UnifiedWebSocketAuthenticator()
        assert auth._auth_service is not None
        assert hasattr(auth, '_websocket_auth_attempts')
        assert hasattr(auth, '_websocket_auth_successes')
        assert hasattr(auth, '_websocket_auth_failures')
        assert auth._websocket_auth_attempts == 0
        assert auth._websocket_auth_successes == 0
        assert auth._websocket_auth_failures == 0

    async def test_successful_websocket_authentication_flow(self):
        """Test successful WebSocket authentication business logic."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer valid-jwt-token'})
        expected_auth_result = AuthResult(success=True, user_id='user_12345', email='test@example.com', permissions=['read', 'write'])
        expected_user_context = UserExecutionContext(user_id='user_12345', websocket_client_id='ws_client_abc123', thread_id='thread_789', run_id='run_xyz456')
        self.mock_auth_service.authenticate_websocket.return_value = (expected_auth_result, expected_user_context)
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        assert result.success is True
        assert result.user_context is not None
        assert result.user_context.user_id == 'user_12345'
        assert result.auth_result is not None
        assert result.auth_result.success is True
        assert result.error_message is None
        assert result.error_code is None
        assert self.authenticator._websocket_auth_attempts == 1
        assert self.authenticator._websocket_auth_successes == 1
        assert self.authenticator._websocket_auth_failures == 0
        self.mock_auth_service.authenticate_websocket.assert_called_once_with(websocket, e2e_context=None)

    async def test_websocket_authentication_failure_handling(self):
        """Test WebSocket authentication failure handling business logic."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer invalid-token'})
        failed_auth_result = AuthResult(success=False, error='Invalid JWT token format', error_code='INVALID_FORMAT')
        self.mock_auth_service.authenticate_websocket.return_value = (failed_auth_result, None)
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        assert result.success is False
        assert result.user_context is None
        assert result.auth_result is not None
        assert result.auth_result.success is False
        assert result.error_message == 'Invalid JWT token format'
        assert result.error_code == 'INVALID_FORMAT'
        assert self.authenticator._websocket_auth_attempts == 1
        assert self.authenticator._websocket_auth_successes == 0
        assert self.authenticator._websocket_auth_failures == 1

    async def test_websocket_authentication_with_e2e_context(self):
        """Test WebSocket authentication with E2E testing context."""
        websocket = MockWebSocket(headers={'x-e2e-test': 'staging-test'})
        e2e_context = {'is_e2e_testing': True, 'environment': 'staging', 'bypass_enabled': True}
        expected_auth_result = AuthResult(success=True, user_id='e2e_user_123', email='e2e@staging.com', permissions=['e2e_test'])
        expected_user_context = UserExecutionContext(user_id='e2e_user_123', websocket_client_id='e2e_ws_client', thread_id='e2e_thread', run_id='e2e_run')
        self.mock_auth_service.authenticate_websocket.return_value = (expected_auth_result, expected_user_context)
        result = await self.authenticator.authenticate_websocket_connection(websocket, e2e_context=e2e_context)
        assert result.success is True
        assert result.user_context.user_id == 'e2e_user_123'
        self.mock_auth_service.authenticate_websocket.assert_called_once_with(websocket, e2e_context=e2e_context)

    async def test_websocket_invalid_state_rejection(self):
        """Test rejection of WebSocket in invalid state."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer valid-token'}, state=MockWebSocketState.DISCONNECTED)
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        assert result.success is False
        assert result.error_code == 'INVALID_WEBSOCKET_STATE'
        assert 'invalid state' in result.error_message.lower()
        self.mock_auth_service.authenticate_websocket.assert_not_called()
        assert self.authenticator._websocket_auth_failures == 1

    async def test_websocket_authentication_exception_handling(self):
        """Test exception handling during WebSocket authentication."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer token'})
        self.mock_auth_service.authenticate_websocket.side_effect = Exception('Unexpected auth service error')
        result = await self.authenticator.authenticate_websocket_connection(websocket)
        assert result.success is False
        assert result.error_code == 'WEBSOCKET_AUTH_EXCEPTION'
        assert 'WebSocket authentication error' in result.error_message
        assert self.authenticator._websocket_auth_failures == 1

    def test_websocket_auth_result_to_dict_conversion(self):
        """Test WebSocketAuthResult to dictionary conversion."""
        user_context = UserExecutionContext(user_id='user_123', websocket_client_id='ws_456', thread_id='thread_789', run_id='run_abc')
        auth_result = AuthResult(success=True, user_id='user_123', email='test@example.com', permissions=['read', 'write'])
        ws_auth_result = WebSocketAuthResult(success=True, user_context=user_context, auth_result=auth_result)
        result_dict = ws_auth_result.to_dict()
        assert result_dict['success'] is True
        assert result_dict['user_id'] == 'user_123'
        assert result_dict['websocket_client_id'] == 'ws_456'
        assert result_dict['thread_id'] == 'thread_789'
        assert result_dict['run_id'] == 'run_abc'
        assert result_dict['email'] == 'test@example.com'
        assert result_dict['permissions'] == ['read', 'write']
        assert result_dict['error_message'] is None
        assert result_dict['error_code'] is None

    def test_websocket_auth_result_to_dict_failure(self):
        """Test WebSocketAuthResult to dictionary conversion for failures."""
        ws_auth_result = WebSocketAuthResult(success=False, error_message='Token validation failed', error_code='VALIDATION_FAILED')
        result_dict = ws_auth_result.to_dict()
        assert result_dict['success'] is False
        assert result_dict['error_message'] == 'Token validation failed'
        assert result_dict['error_code'] == 'VALIDATION_FAILED'
        assert result_dict['user_id'] is None
        assert result_dict['websocket_client_id'] is None

    def test_get_websocket_auth_stats_business_metrics(self):
        """Test authentication statistics for business monitoring."""
        self.authenticator._websocket_auth_attempts = 10
        self.authenticator._websocket_auth_successes = 8
        self.authenticator._websocket_auth_failures = 2
        self.authenticator._connection_states_seen = {'connected': 8, 'connecting': 2}
        stats = self.authenticator.get_websocket_auth_stats()
        assert stats['ssot_compliance']['ssot_compliant'] is True
        assert stats['ssot_compliance']['service'] == 'UnifiedWebSocketAuthenticator'
        assert stats['ssot_compliance']['authentication_service'] == 'UnifiedAuthenticationService'
        assert stats['ssot_compliance']['duplicate_paths_eliminated'] == 4
        assert stats['websocket_auth_statistics']['total_attempts'] == 10
        assert stats['websocket_auth_statistics']['successful_authentications'] == 8
        assert stats['websocket_auth_statistics']['failed_authentications'] == 2
        assert stats['websocket_auth_statistics']['success_rate_percent'] == 80.0
        assert stats['connection_states_seen'] == {'connected': 8, 'connecting': 2}
        assert 'timestamp' in stats

    def test_websocket_close_code_mapping_security(self):
        """Test WebSocket close code mapping for security scenarios."""
        test_cases = [('NO_TOKEN', 1008), ('INVALID_FORMAT', 1008), ('VALIDATION_FAILED', 1008), ('TOKEN_EXPIRED', 1008), ('AUTH_SERVICE_ERROR', 1011), ('WEBSOCKET_AUTH_ERROR', 1011), ('INVALID_WEBSOCKET_STATE', 1002), ('UNKNOWN_ERROR', 1008)]
        for error_code, expected_close_code in test_cases:
            close_code = self.authenticator._get_close_code_for_error(error_code)
            assert close_code == expected_close_code, f'Error {error_code} should map to {expected_close_code}'

@pytest.mark.unit
class E2EContextExtractionBusinessLogicTests(SSotAsyncTestCase):
    """Test E2E context extraction business logic."""

    def test_extract_e2e_context_from_headers(self):
        """Test E2E context extraction from WebSocket headers."""
        websocket = MockWebSocket(headers={'x-e2e-test': 'true', 'x-test-environment': 'staging'})
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging-123', 'K_SERVICE': 'backend-staging'}
            context = extract_e2e_context_from_websocket(websocket)
            assert context is not None
            assert context['is_e2e_testing'] is True
            assert context['detection_method']['via_headers'] is True
            assert context['bypass_enabled'] is True
            assert context['enhanced_detection'] is True

    def test_extract_e2e_context_from_environment_staging(self):
        """Test E2E context extraction from staging environment."""
        websocket = MockWebSocket()
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value = {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_SERVICE': 'backend-staging', 'E2E_TESTING': '0'}
            context = extract_e2e_context_from_websocket(websocket)
            assert context is not None
            assert context['is_e2e_testing'] is True
            assert context['detection_method']['via_staging_auto_detection'] is True
            assert context['environment'] == 'staging'

    def test_extract_e2e_context_no_detection(self):
        """Test E2E context extraction when no E2E indicators present."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer token'})
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value = {'ENVIRONMENT': 'production', 'GOOGLE_CLOUD_PROJECT': 'netra-prod', 'K_SERVICE': 'backend-prod'}
            context = extract_e2e_context_from_websocket(websocket)
            assert context is None

    def test_safe_websocket_state_logging(self):
        """Test safe WebSocket state serialization for logging."""
        mock_state = MockWebSocketState.CONNECTED
        safe_state = _safe_websocket_state_for_logging(mock_state)
        assert safe_state == 'connected'
        non_enum = 'some_string'
        safe_non_enum = _safe_websocket_state_for_logging(non_enum)
        assert safe_non_enum == 'some_string'

@pytest.mark.unit
class WebSocketAuthenticatorSSotComplianceTests(SSotAsyncTestCase):
    """Test SSOT compliance and global instance management."""

    def test_get_websocket_authenticator_singleton_pattern(self):
        """Test that get_websocket_authenticator returns singleton instance."""
        auth1 = get_websocket_authenticator()
        auth2 = get_websocket_authenticator()
        assert auth1 is auth2
        assert isinstance(auth1, UnifiedWebSocketAuthenticator)

    async def test_authenticate_websocket_ssot_function(self):
        """Test SSOT WebSocket authentication function."""
        websocket = MockWebSocket(headers={'authorization': 'Bearer token'})
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_websocket_authenticator') as mock_get_auth:
            mock_authenticator = AsyncMock()
            mock_auth_result = WebSocketAuthResult(success=True)
            mock_authenticator.authenticate_websocket_connection.return_value = mock_auth_result
            mock_get_auth.return_value = mock_authenticator
            result = await authenticate_websocket_ssot(websocket)
            assert result is mock_auth_result
            mock_authenticator.authenticate_websocket_connection.assert_called_once_with(websocket, e2e_context=None)

    async def test_authenticate_websocket_ssot_with_e2e_context(self):
        """Test SSOT WebSocket authentication function with E2E context."""
        websocket = MockWebSocket()
        e2e_context = {'is_e2e_testing': True, 'environment': 'staging'}
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_websocket_authenticator') as mock_get_auth:
            mock_authenticator = AsyncMock()
            mock_auth_result = WebSocketAuthResult(success=True)
            mock_authenticator.authenticate_websocket_connection.return_value = mock_auth_result
            mock_get_auth.return_value = mock_authenticator
            result = await authenticate_websocket_ssot(websocket, e2e_context=e2e_context)
            mock_authenticator.authenticate_websocket_connection.assert_called_once_with(websocket, e2e_context=e2e_context)

@pytest.mark.unit
class WebSocketAuthenticatorErrorHandlingTests(SSotAsyncTestCase):
    """Test WebSocket authenticator error handling business logic."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.authenticator = UnifiedWebSocketAuthenticator()

    async def test_create_auth_error_response(self):
        """Test creation of authentication error response."""
        websocket = MockWebSocket()
        auth_result = WebSocketAuthResult(success=False, error_message='Token validation failed', error_code='VALIDATION_FAILED')
        await self.authenticator.create_auth_error_response(websocket, auth_result)
        websocket.send_json.assert_called_once()
        sent_message = websocket.send_json.call_args[0][0]
        assert sent_message['type'] == 'authentication_error'
        assert sent_message['event'] == 'auth_failed'
        assert sent_message['error'] == 'Token validation failed'
        assert sent_message['error_code'] == 'VALIDATION_FAILED'
        assert sent_message['retry_allowed'] is True
        assert sent_message['ssot_authenticated'] is False
        assert 'timestamp' in sent_message

    async def test_create_auth_success_response(self):
        """Test creation of authentication success response."""
        websocket = MockWebSocket()
        user_context = UserExecutionContext(user_id='user_123', websocket_client_id='ws_456', thread_id='thread_789', run_id='run_abc')
        auth_result = AuthResult(success=True, user_id='user_123', permissions=['read', 'write'])
        ws_auth_result = WebSocketAuthResult(success=True, user_context=user_context, auth_result=auth_result)
        await self.authenticator.create_auth_success_response(websocket, ws_auth_result)
        websocket.send_json.assert_called_once()
        sent_message = websocket.send_json.call_args[0][0]
        assert sent_message['type'] == 'authentication_success'
        assert sent_message['event'] == 'auth_success'
        assert sent_message['user_id'] == 'user_123'
        assert sent_message['websocket_client_id'] == 'ws_456'
        assert sent_message['permissions'] == ['read', 'write']
        assert sent_message['ssot_authenticated'] is True
        assert 'timestamp' in sent_message

    async def test_handle_authentication_failure_with_close(self):
        """Test handling authentication failure with connection close."""
        websocket = MockWebSocket()
        auth_result = WebSocketAuthResult(success=False, error_message='Invalid token', error_code='INVALID_FORMAT')
        await self.authenticator.handle_authentication_failure(websocket, auth_result, close_connection=True)
        websocket.send_json.assert_called_once()
        websocket.close.assert_called_once()
        close_args = websocket.close.call_args
        assert close_args[1]['code'] == 1008
        assert 'Invalid token' in close_args[1]['reason']

    async def test_handle_authentication_failure_without_close(self):
        """Test handling authentication failure without closing connection."""
        websocket = MockWebSocket()
        auth_result = WebSocketAuthResult(success=False, error_message='Rate limited', error_code='RATE_LIMITED')
        await self.authenticator.handle_authentication_failure(websocket, auth_result, close_connection=False)
        websocket.send_json.assert_called_once()
        websocket.close.assert_not_called()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')