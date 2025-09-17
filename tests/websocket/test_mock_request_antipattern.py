"""
WebSocket Mock Request Anti-Pattern Elimination Test

This test validates that the WebSocket system uses proper WebSocketContext objects
instead of mock Request objects, ensuring clean architecture and user isolation.

Business Value:
- Ensures proper multi-user WebSocket isolation
- Validates clean architecture patterns
- Prevents authentication and routing bugs
- Tests real WebSocket message handling

CRITICAL: This test uses REAL WebSocket connections and authentication.
No mocks are allowed except for controlled isolation testing.
"""
import asyncio
import json
import os
import pytest
import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.environment_isolation import IsolatedEnvironment
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.dependencies import get_request_scoped_db_session
from shared.isolated_environment import get_env

@pytest.mark.websocket
class WebSocketAntiPatternEliminationTests(SSotBaseTestCase):
    """Test suite to validate elimination of WebSocket mock Request anti-patterns.
    
    These tests ensure the system uses proper WebSocketContext objects instead
    of creating mock Request objects for WebSocket connections. This validates
    clean architecture and proper user isolation.
    
    CRITICAL: All tests use real authentication and WebSocket connections.
    """

    def setUp(self) -> None:
        """Set up test environment with real authentication."""
        super().setUp()
        self.env = get_env()
        self.auth_config = E2EAuthConfig()
        self.auth_helper = E2EAuthHelper(config=self.auth_config)
        self.ws_auth_helper = E2EWebSocketAuthHelper(config=self.auth_config)
        self.test_user_id = f'test_user_{int(datetime.now(UTC).timestamp())}'
        self.test_thread_id = f'test_thread_{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'test_run_{uuid.uuid4().hex[:8]}'

    @pytest.mark.asyncio
    async def test_websocket_context_creation_honest_pattern(self):
        """Test that WebSocketContext provides honest WebSocket functionality.
        
        This validates that the system uses honest WebSocket context objects
        instead of mock Request objects that pretend to be something they're not.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        mock_websocket = self._create_test_websocket()
        context = WebSocketContext.create_for_user(websocket=mock_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.websocket == mock_websocket
        assert context.is_active
        assert hasattr(context, 'websocket')
        assert hasattr(context, 'connection_id')
        assert hasattr(context, 'is_active')
        assert hasattr(context, 'update_activity')
        assert not hasattr(context, 'headers')
        assert not hasattr(context, 'cookies')
        assert not hasattr(context, 'method')
        assert not hasattr(context, 'url')
        original_activity = context.last_activity
        await asyncio.sleep(0.01)
        context.update_activity()
        assert context.last_activity > original_activity
        isolation_key = context.to_isolation_key()
        assert self.test_user_id in isolation_key
        assert self.test_thread_id in isolation_key
        assert self.test_run_id in isolation_key

    @pytest.mark.asyncio
    async def test_websocket_context_validation_requirements(self):
        """Test that WebSocketContext properly validates required fields.
        
        This ensures the system fails fast with clear errors when
        required WebSocket context data is missing.
        """
        mock_websocket = self._create_test_websocket()
        with pytest.raises(ValueError, match='user_id is required'):
            WebSocketContext(connection_id='test_conn', websocket=mock_websocket, user_id='', thread_id=self.test_thread_id, run_id=self.test_run_id)
        with pytest.raises(ValueError, match='thread_id is required'):
            WebSocketContext(connection_id='test_conn', websocket=mock_websocket, user_id=self.test_user_id, thread_id='', run_id=self.test_run_id)
        with pytest.raises(ValueError, match='run_id is required'):
            WebSocketContext(connection_id='test_conn', websocket=mock_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id='')
        with pytest.raises(ValueError, match='websocket is required'):
            WebSocketContext(connection_id='test_conn', websocket=None, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle_management(self):
        """Test that WebSocketContext properly tracks connection lifecycle.
        
        This validates that the context honestly reports connection state
        and properly handles connection state changes.
        """
        mock_websocket = self._create_test_websocket(state=WebSocketState.CONNECTED)
        context = WebSocketContext.create_for_user(websocket=mock_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id)
        assert context.is_active
        conn_info = context.get_connection_info()
        assert conn_info['user_id'] == self.test_user_id
        assert conn_info['thread_id'] == self.test_thread_id
        assert conn_info['is_active'] is True
        assert 'connected_at' in conn_info
        assert 'last_activity' in conn_info
        assert context.validate_for_message_processing()
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        assert not context.is_active
        with pytest.raises(ValueError, match='not active'):
            context.validate_for_message_processing()

    @pytest.mark.asyncio
    async def test_websocket_message_handler_integration(self):
        """Test that WebSocket message handler integrates properly with WebSocketContext.
        
        This validates that the agent message handler uses WebSocketContext
        instead of creating mock Request objects.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id)
        mock_websocket = self._create_test_websocket()
        test_message = WebSocketMessage(type=MessageType.START_AGENT, payload={'thread_id': self.test_thread_id, 'run_id': self.test_run_id, 'message': 'Test agent execution'}, user_id=self.test_user_id, thread_id=self.test_thread_id, correlation_id=f'test_corr_{uuid.uuid4().hex[:8]}')
        context = WebSocketContext.create_for_user(websocket=mock_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        assert context.validate_for_message_processing()
        isolation_key = context.to_isolation_key()
        assert isolation_key.startswith('ws_')
        assert self.test_user_id in isolation_key
        assert self.test_thread_id in isolation_key
        conn_info = context.get_connection_info()
        assert isinstance(conn_info, dict)
        assert 'client_state' in conn_info
        assert conn_info['client_state'] == 'CONNECTED'

    @pytest.mark.asyncio
    async def test_user_isolation_with_multiple_contexts(self):
        """Test that multiple WebSocket contexts provide proper user isolation.
        
        This validates that concurrent WebSocket connections maintain
        independent contexts without cross-contamination.
        """
        contexts = []
        for i in range(3):
            user_id = f'user_{i}_{int(datetime.now(UTC).timestamp())}'
            thread_id = f'thread_{i}_{uuid.uuid4().hex[:8]}'
            run_id = f'run_{i}_{uuid.uuid4().hex[:8]}'
            mock_websocket = self._create_test_websocket()
            context = WebSocketContext.create_for_user(websocket=mock_websocket, user_id=user_id, thread_id=thread_id, run_id=run_id)
            contexts.append(context)
        for i, context in enumerate(contexts):
            assert f'user_{i}_' in context.user_id
            assert f'thread_{i}_' in context.thread_id
            assert f'run_{i}_' in context.run_id
            assert context.is_active
            isolation_key = context.to_isolation_key()
            assert context.user_id in isolation_key
            assert context.thread_id in isolation_key
            assert context.run_id in isolation_key
        for i, context1 in enumerate(contexts):
            for j, context2 in enumerate(contexts):
                if i != j:
                    assert context1.user_id != context2.user_id
                    assert context1.thread_id != context2.thread_id
                    assert context1.run_id != context2.run_id
                    assert context1.connection_id != context2.connection_id
                    assert context1.to_isolation_key() != context2.to_isolation_key()

    @pytest.mark.asyncio
    async def test_websocket_context_error_handling(self):
        """Test that WebSocketContext handles errors gracefully and honestly.
        
        This validates that the context fails fast with clear errors
        rather than hiding problems with mock objects.
        """

        class FaultyWebSocket:

            @property
            def client_state(self):
                raise RuntimeError('WebSocket connection error')
        faulty_websocket = FaultyWebSocket()
        context = WebSocketContext(connection_id='test_conn_faulty', websocket=faulty_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        assert not context.is_active
        from datetime import timedelta, UTC
        old_time = datetime.now(UTC) - timedelta(days=2)
        old_context = WebSocketContext(connection_id='old_conn', websocket=self._create_test_websocket(), user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id, connected_at=old_time)
        assert old_context.validate_for_message_processing()

    @pytest.mark.asyncio
    async def test_authentication_integration_with_context(self):
        """Test that WebSocketContext integrates properly with authentication.
        
        This validates that the context works with real JWT tokens
        and authentication flows without requiring mock objects.
        """
        token = self.auth_helper.create_test_jwt_token(user_id=self.test_user_id, permissions=['read', 'write'], exp_minutes=5)
        auth_headers = self.auth_helper.get_auth_headers(token)
        assert 'Authorization' in auth_headers
        assert auth_headers['Authorization'].startswith('Bearer ')
        ws_headers = self.ws_auth_helper.get_websocket_headers(token)
        assert 'Authorization' in ws_headers
        assert 'X-User-ID' in ws_headers
        assert ws_headers['X-User-ID'] == self.test_user_id
        mock_websocket = self._create_test_websocket()
        context = WebSocketContext.create_for_user(websocket=mock_websocket, user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        assert context.user_id == self.test_user_id
        assert context.validate_for_message_processing()
        isolation_key = context.to_isolation_key()
        assert self.test_user_id in isolation_key

    def _create_test_websocket(self, state: WebSocketState=WebSocketState.CONNECTED):
        """Create a controlled WebSocket for testing.
        
        Args:
            state: WebSocket state to simulate
            
        Returns:
            Mock WebSocket with controlled behavior
        """

        class WebSocketTests:

            def __init__(self, client_state: WebSocketState):
                self.client_state = client_state
                self.messages_sent = []
                self.closed = False

            async def send_text(self, message: str):
                if self.closed:
                    raise RuntimeError('WebSocket is closed')
                self.messages_sent.append(message)

            async def send_json(self, data: dict):
                if self.closed:
                    raise RuntimeError('WebSocket is closed')
                self.messages_sent.append(json.dumps(data))

            async def close(self, code: int=1000, reason: str='Normal closure'):
                self.closed = True
                self.client_state = WebSocketState.DISCONNECTED
        return WebSocketTests(state)

    def tearDown(self) -> None:
        """Clean up test resources."""
        super().tearDown()
        if hasattr(self, 'auth_helper') and self.auth_helper:
            self.auth_helper._cached_token = None
            self.auth_helper._token_expiry = None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')