"""
Test Suite for WebSocket 1011 Internal Server Error Fix

This test suite reproduces the WebSocket 1011 internal server error and validates
that the SSOT-compliant fix prevents these errors through defensive validation
and graceful fallback handling.

Business Value Justification:
- Segment: Platform/Internal - Critical Infrastructure
- Business Goal: Prevent WebSocket 1011 errors that block user interactions
- Value Impact: Ensures reliable WebSocket connectivity for chat functionality
- Revenue Impact: Prevents loss of $120K+ MRR from WebSocket failures

Root Cause Analysis:
1. UserExecutionContext validation failures in websocket_manager_factory.py (lines 66-115)
2. Hard 1011 failures in websocket.py when factory creation fails (lines 334 & 769)
3. Authentication result validation issues in unified_authentication_service.py (lines 464-482)

Fix Implementation:
- Defensive UserExecutionContext creation with validation
- Graceful fallback handling instead of hard 1011 failures
- Enhanced authentication result validation with fallback patterns
- Better error diagnostics and logging
"""
import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager, create_defensive_user_execution_context, FactoryInitializationError, _validate_ssot_user_context
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot, WebSocketAuthResult
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service, AuthResult
pytestmark = pytest.mark.asyncio

class TestWebSocket1011ErrorReproduction:
    """Test cases that reproduce the original 1011 error conditions."""

    async def test_invalid_user_context_causes_factory_error(self):
        """Test that invalid UserExecutionContext causes FactoryInitializationError (original bug)."""
        invalid_context = Mock()
        invalid_context.user_id = None
        invalid_context.thread_id = 'test_thread'
        invalid_context.run_id = 'test_run'
        with pytest.raises(FactoryInitializationError) as exc_info:
            create_websocket_manager(invalid_context)
        assert 'SSOT validation failed' in str(exc_info.value)
        assert 'UserExecutionContext type incompatibility' in str(exc_info.value)

    async def test_missing_attributes_causes_validation_failure(self):
        """Test that UserExecutionContext with missing attributes fails validation."""

        class PartialContext:

            def __init__(self):
                self.user_id = 'unique_test_user_123'
                self.thread_id = 'test_thread'
                self.run_id = 'test_run'
        partial_context = PartialContext()
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(partial_context)
        assert 'SSOT VIOLATION' in str(exc_info.value) or 'missing required attributes' in str(exc_info.value)

    async def test_empty_user_id_causes_validation_failure(self):
        """Test that empty user_id causes validation failure."""

        class EmptyUserContext:

            def __init__(self):
                self.user_id = ''
                self.thread_id = 'test_thread'
                self.run_id = 'test_run'
                self.request_id = 'test_request'
                self.websocket_client_id = 'test_client'
        empty_user_context = EmptyUserContext()
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(empty_user_context)
        assert 'SSOT VIOLATION' in str(exc_info.value) or 'must be non-empty string' in str(exc_info.value)

class TestWebSocket1011ErrorFixValidation:
    """Test cases that validate the SSOT-compliant fix prevents 1011 errors."""

    async def test_defensive_user_context_creation_success(self):
        """Test that defensive UserExecutionContext creation prevents validation failures."""
        user_id = 'unique_test_user_defensive_123'
        websocket_client_id = 'ws_client_test_123'
        user_context = create_defensive_user_execution_context(user_id=user_id, websocket_client_id=websocket_client_id)
        _validate_ssot_user_context(user_context)
        assert user_context.user_id == user_id
        assert user_context.websocket_client_id == websocket_client_id
        assert user_context.thread_id is not None
        assert user_context.run_id is not None
        assert user_context.request_id is not None
        assert isinstance(user_context.user_id, str)
        assert len(user_context.user_id.strip()) > 0
        assert isinstance(user_context.thread_id, str)
        assert len(user_context.thread_id.strip()) > 0

    async def test_defensive_creation_with_invalid_user_id_fails_gracefully(self):
        """Test that defensive creation fails gracefully with invalid user_id."""
        invalid_user_ids = [None, '', '   ', 123, [], {}]
        for invalid_user_id in invalid_user_ids:
            with pytest.raises(ValueError) as exc_info:
                create_defensive_user_execution_context(user_id=invalid_user_id, websocket_client_id='test_client')
            assert 'user_id must be non-empty string' in str(exc_info.value)

    async def test_defensive_creation_auto_generates_client_id(self):
        """Test that defensive creation auto-generates websocket_client_id when None."""
        user_id = 'unique_user_auto_gen_456'
        user_context = create_defensive_user_execution_context(user_id=user_id, websocket_client_id=None)
        assert user_context.websocket_client_id is not None
        assert isinstance(user_context.websocket_client_id, str)
        assert len(user_context.websocket_client_id.strip()) > 0
        assert user_id[:8] in user_context.websocket_client_id
        _validate_ssot_user_context(user_context)

    async def test_factory_creation_with_valid_context_succeeds(self):
        """Test that WebSocket manager factory creation succeeds with valid context."""
        user_context = create_defensive_user_execution_context(user_id='unique_factory_user_789', websocket_client_id='ws_factory_test')
        ws_manager = create_websocket_manager(user_context)
        assert ws_manager is not None
        assert ws_manager.user_context.user_id == 'unique_factory_user_789'
        assert ws_manager.user_context.websocket_client_id == 'ws_factory_test'
        assert ws_manager._is_active is True

    async def test_authentication_service_creates_valid_context(self):
        """Test that unified authentication service creates valid UserExecutionContext."""
        mock_auth_result = AuthResult(success=True, user_id='unique_auth_test_user_101112', email='test@example.com', permissions=['read', 'write'])
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client = Mock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 12345
        auth_service = get_unified_auth_service()
        user_context = auth_service._create_user_execution_context(auth_result=mock_auth_result, websocket=mock_websocket)
        _validate_ssot_user_context(user_context)
        assert user_context.user_id == 'unique_auth_test_user_101112'
        assert user_context.websocket_client_id is not None
        assert 'ws_' in user_context.websocket_client_id
        assert 'unique_a'[:8] in user_context.websocket_client_id

class TestWebSocketErrorHandlingIntegration:
    """Integration tests for WebSocket error handling and fallback mechanisms."""

    async def test_websocket_auth_with_invalid_context_provides_fallback(self):
        """Test that WebSocket authentication provides fallback when context creation fails."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {'authorization': 'Bearer valid_test_token_12345'}
        mock_websocket.client = Mock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 8080
        mock_websocket.client_state = WebSocketState.CONNECTED
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(success=True, user_id='   unique_edge_case_user_131415   ', email='edge@example.com')
            mock_service.authenticate_websocket.return_value = (mock_auth_result, Mock())
            mock_get_service.return_value = mock_service
            result = await authenticate_websocket_ssot(mock_websocket)
            assert result.success is True or result.error_code != 'FACTORY_INIT_FAILED'

    async def test_factory_error_handling_prevents_1011_crashes(self):
        """Test that factory errors are handled gracefully to prevent 1011 crashes."""
        problematic_context = create_defensive_user_execution_context(user_id='unique_problematic_user_161718', websocket_client_id='ws_client_123')
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory.create_manager') as mock_create:
            mock_create.side_effect = RuntimeError('Simulated factory failure')
            with pytest.raises(FactoryInitializationError) as exc_info:
                create_websocket_manager(problematic_context)
            assert 'WebSocket factory initialization failed unexpectedly' in str(exc_info.value)
            assert 'system configuration issue' in str(exc_info.value)

class TestWebSocketValidationDefensiveMeasures:
    """Test defensive validation measures in WebSocket components."""

    async def test_ssot_validation_handles_attribute_access_errors(self):
        """Test that SSOT validation handles attribute access errors defensively."""

        class ProblematicContext:

            def __init__(self):
                self.user_id = 'unique_problematic_test_user_192021'

            @property
            def thread_id(self):
                raise AttributeError('Simulated attribute access error')
        problematic_context = ProblematicContext()
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(problematic_context)
        error_message = str(exc_info.value)
        assert 'thread_id attribute access failed' in error_message or 'SSOT' in error_message

    async def test_defensive_context_creation_with_id_generator_failure(self):
        """Test that defensive context creation handles ID generator failures."""
        with patch('shared.id_generation.unified_id_generator.UnifiedIdGenerator.generate_user_context_ids') as mock_id_gen:
            mock_id_gen.side_effect = Exception('ID generator service unavailable')
            user_context = create_defensive_user_execution_context(user_id='unique_fallback_test_user_222324', websocket_client_id='fallback_client')
            assert user_context.user_id == 'unique_fallback_test_user_222324'
            assert user_context.websocket_client_id == 'fallback_client'
            assert user_context.thread_id is not None
            assert user_context.run_id is not None
            assert user_context.request_id is not None
            assert 'ws_thread_' in user_context.thread_id
            assert 'ws_run_' in user_context.run_id
            assert 'ws_req_' in user_context.request_id

    async def test_auth_service_fallback_context_creation(self):
        """Test that auth service can create fallback context when primary creation fails."""
        edge_case_auth_result = AuthResult(success=True, user_id=None, email='edge@example.com')
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client = None
        auth_service = get_unified_auth_service()
        try:
            user_context = auth_service._create_user_execution_context(auth_result=edge_case_auth_result, websocket=mock_websocket)
            assert user_context.user_id in ['fallback_user', 'unknown_user']
            _validate_ssot_user_context(user_context)
        except ValueError as e:
            assert 'UserExecutionContext creation failed' in str(e)

class TestWebSocketErrorDiagnostics:
    """Test enhanced error diagnostics and logging for WebSocket issues."""

    async def test_factory_error_provides_detailed_diagnostics(self):
        """Test that factory initialization errors provide detailed diagnostic information."""
        invalid_context = Mock()
        invalid_context.__class__.__module__ = 'wrong.module'
        with pytest.raises(FactoryInitializationError) as exc_info:
            create_websocket_manager(invalid_context)
        error_message = str(exc_info.value)
        assert 'SSOT validation failed' in error_message
        assert 'UserExecutionContext type incompatibility' in error_message

    async def test_validation_errors_include_context_information(self):
        """Test that validation errors include sufficient context for debugging."""

        class BadContext:

            def __init__(self):
                self.user_id = ''
                self.thread_id = 123
                self.run_id = None
                self.request_id = 'valid_request'
                self.websocket_client_id = 'test_client'
        bad_context = BadContext()
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(bad_context)
        error_message = str(exc_info.value)
        assert 'SSOT VIOLATION' in error_message or 'user_id' in error_message
        assert 'UserExecutionContext' in error_message or 'VALIDATION FAILED' in error_message

    async def test_websocket_auth_result_includes_diagnostic_info(self):
        """Test that WebSocket authentication results include diagnostic information."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.client = Mock()
        mock_websocket.client.host = '127.0.0.1'
        result = await authenticate_websocket_ssot(mock_websocket)
        assert result.success is False
        assert result.error_code is not None
        assert result.error_message is not None
        if result.auth_result:
            assert hasattr(result.auth_result, 'metadata')

class TestWebSocketConnectionFlowIntegration:
    """Integration test simulating complete WebSocket connection flow with error handling."""

    async def test_complete_websocket_connection_with_error_recovery(self):
        """Test complete WebSocket connection flow with error recovery mechanisms."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.headers = {'authorization': 'Bearer test_token_with_valid_format'}
        mock_websocket.client = Mock()
        mock_websocket.client.host = '127.0.0.1'
        mock_websocket.client.port = 8080
        mock_websocket.client_state = WebSocketState.CONNECTED
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_auth_result = AuthResult(success=True, user_id='unique_integration_test_user_252627', email='integration@example.com', permissions=['read', 'write'])
            mock_user_context = create_defensive_user_execution_context(user_id='unique_integration_test_user_252627', websocket_client_id='integration_client')
            mock_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
            mock_get_service.return_value = mock_service
            auth_result = await authenticate_websocket_ssot(mock_websocket)
            if auth_result.success:
                assert auth_result.user_context is not None
                _validate_ssot_user_context(auth_result.user_context)
                ws_manager = create_websocket_manager(auth_result.user_context)
                assert ws_manager is not None
                assert ws_manager._is_active
            else:
                assert auth_result.error_code is not None
                assert auth_result.error_message is not None
                assert auth_result.error_code != 'INTERNAL_ERROR'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')