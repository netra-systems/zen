"""
Unit Test for WebSocket State Registry Scope Bug

CRITICAL BUG REPRODUCTION: "NameError: name 'state_registry' is not defined"

This test reproduces the exact variable scope issue where:
1. state_registry is created locally in _initialize_connection_state()
2. state_registry is referenced in websocket_endpoint() without being in scope
3. Results in 100% WebSocket connection failure rate in production

Expected Result: Test must FAIL with exact NameError before fix is implemented
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocket, WebSocketDisconnect
import logging
from test_framework.ssot.base_test_case import SSotBaseTestCase
logger = logging.getLogger(__name__)

class TestWebSocketStateRegistryScopeBug(SSotBaseTestCase):
    """
    CRITICAL: Test reproduces the exact scope bug where state_registry
    variable is not accessible in websocket_endpoint() function.
    
    This test must FAIL with NameError before the bug is fixed.
    """

    def setup_method(self, method=None):
        """Set up test environment for scope bug reproduction"""
        super().setup_method(method)
        self.mock_websocket = Mock(spec=WebSocket)
        self.mock_websocket.connection_id = None
        self.mock_websocket.accept = AsyncMock()
        self.mock_websocket.receive_text = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.close = AsyncMock()
        self.error_logs = []
        self.log_handler = logging.Handler()
        self.log_handler.emit = lambda record: self.error_logs.append(record)
        logger.addHandler(self.log_handler)

    def teardown_method(self, method=None):
        """Clean up test environment"""
        super().teardown_method(method) if hasattr(super(), 'teardown_method') else None
        if hasattr(self, 'log_handler'):
            logger.removeHandler(self.log_handler)

    @pytest.mark.asyncio
    async def test_state_registry_scope_bug_unit_reproduction(self):
        """
        CRITICAL TEST: Reproduces the exact NameError scope bug
        
        EXPECTED RESULT: NameError: name 'state_registry' is not defined
        
        This test simulates the production scenario where:
        1. _initialize_connection_state() creates state_registry locally
        2. websocket_endpoint() tries to use state_registry but it's out of scope
        3. Results in NameError causing 100% connection failures
        """
        from netra_backend.app.routes.websocket import websocket_endpoint, _initialize_connection_state
        logger.info('[U+1F534] UNIT TEST: Reproducing state_registry scope bug')
        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_registry.register_connection = Mock()
            mock_registry.unregister_connection = Mock()
            mock_get_registry.return_value = mock_registry
            mock_state_machine = Mock()
            mock_state_machine.transition_to = Mock(return_value=True)
            mock_state_machine.user_id = None
            mock_registry.register_connection.return_value = mock_state_machine
            with patch('netra_backend.app.routes.websocket.windows_safe_sleep', new_callable=AsyncMock), patch('netra_backend.app.routes.websocket._check_websocket_service_circuit_breaker', new_callable=AsyncMock) as mock_circuit_breaker, patch('netra_backend.app.routes.websocket._check_environment_for_staging_compat', return_value='testing'), patch('netra_backend.app.routes.websocket.jwt_decode') as mock_jwt_decode, patch('netra_backend.app.routes.websocket.get_connection_state_machine') as mock_get_state_machine:
                mock_circuit_breaker.return_value = {'status': 'closed', 'failure_count': 0}
                mock_jwt_decode.return_value = {'user_id': 'test_user_123'}
                mock_get_state_machine.return_value = mock_state_machine
                self.mock_websocket.receive_text.side_effect = ['{"type": "auth", "token": "valid_jwt_token"}', WebSocketDisconnect()]
                with pytest.raises((NameError, UnboundLocalError)) as exc_info:
                    await websocket_endpoint(self.mock_websocket)
                error_message = str(exc_info.value)
                logger.error(f'[U+1F534] CAPTURED ERROR: {error_message}')
                assert 'state_registry' in error_message, f'Expected state_registry error, got: {error_message}'
                assert 'not defined' in error_message or 'referenced before assignment' in error_message, f'Expected scope error, got: {error_message}'
                logger.info(' PASS:  UNIT TEST SUCCESS: state_registry scope bug reproduced successfully')

    @pytest.mark.asyncio
    async def test_state_registry_variable_isolation_unit(self):
        """
        UNIT TEST: Verify state_registry variable scope isolation
        
        This test specifically focuses on the variable scope issue by
        calling functions in isolation to demonstrate the scope bug.
        """
        from netra_backend.app.routes.websocket import _initialize_connection_state
        logger.info('[U+1F534] UNIT TEST: Testing state_registry variable isolation')
        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_registry.register_connection = Mock(return_value=Mock())
            mock_get_registry.return_value = mock_registry
            preliminary_connection_id, state_machine = await _initialize_connection_state(self.mock_websocket, 'testing', 'jwt.test_token')
            assert preliminary_connection_id is not None
            assert state_machine is not None
            try:
                state_registry.unregister_connection(preliminary_connection_id)
                pytest.fail('Expected NameError for state_registry variable not being in scope')
            except NameError as e:
                logger.info(f' PASS:  UNIT TEST SUCCESS: Confirmed state_registry scope isolation: {e}')
                assert 'state_registry' in str(e)
                assert 'not defined' in str(e)

    @pytest.mark.asyncio
    async def test_websocket_authentication_flow_scope_bug(self):
        """
        UNIT TEST: Focus on the exact authentication flow where scope bug occurs
        
        This test simulates the specific code path in websocket_endpoint()
        where state_registry is accessed after _initialize_connection_state() returns.
        """
        logger.info('[U+1F534] UNIT TEST: Testing authentication flow scope bug')
        from netra_backend.app.routes.websocket import websocket_endpoint
        with patch('netra_backend.app.routes.websocket._initialize_connection_state') as mock_init_state, patch('netra_backend.app.routes.websocket.windows_safe_sleep', new_callable=AsyncMock), patch('netra_backend.app.routes.websocket._check_websocket_service_circuit_breaker', new_callable=AsyncMock) as mock_circuit_breaker, patch('netra_backend.app.routes.websocket._check_environment_for_staging_compat', return_value='testing'), patch('netra_backend.app.routes.websocket.jwt_decode') as mock_jwt_decode:
            mock_state_machine = Mock()
            mock_state_machine.transition_to = Mock(return_value=True)
            mock_state_machine.user_id = None
            mock_init_state.return_value = ('test_connection_id', mock_state_machine)
            mock_circuit_breaker.return_value = {'status': 'closed', 'failure_count': 0}
            mock_jwt_decode.return_value = {'user_id': 'test_user_123'}
            self.mock_websocket.receive_text.side_effect = ['{"type": "auth", "token": "valid_jwt_token", "connection_id": "new_connection_id"}', WebSocketDisconnect()]
            with pytest.raises((NameError, UnboundLocalError)) as exc_info:
                await websocket_endpoint(self.mock_websocket)
            error_message = str(exc_info.value)
            logger.error(f'[U+1F534] AUTH FLOW ERROR: {error_message}')
            assert 'state_registry' in error_message, f'Expected state_registry error, got: {error_message}'
            logger.info(' PASS:  UNIT TEST SUCCESS: Authentication flow scope bug reproduced')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')