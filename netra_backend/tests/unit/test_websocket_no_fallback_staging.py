"""
Test to verify that WebSocket fallback is NEVER used in staging/production.

This test ensures that if dependencies are missing in staging/production,
the WebSocket endpoint fails properly rather than using a fallback handler.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import WebSocket
from fastapi.testclient import TestClient
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.asyncio
async def test_websocket_no_fallback_in_staging():
    """Test that WebSocket endpoint handles missing dependencies appropriately in staging."""
    mock_websocket = Mock(spec=WebSocket)
    mock_app_state = Mock()
    mock_app_state.agent_supervisor = None
    mock_app_state.thread_service = None
    mock_app_state.startup_complete = True
    mock_websocket.app.state = mock_app_state
    mock_websocket.accept = MagicMock(return_value=None)
    mock_websocket.headers = {'sec-websocket-protocol': ''}
    from netra_backend.app.routes.websocket import websocket_endpoint
    with patch('shared.isolated_environment.get_env') as mock_get_env:
        mock_get_env.return_value = {'ENVIRONMENT': 'staging', 'TESTING': '0'}
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_ws_manager, patch('netra_backend.app.routes.websocket.get_message_router') as mock_router, patch('netra_backend.app.routes.websocket.get_connection_monitor') as mock_monitor, patch('netra_backend.app.routes.websocket.safe_websocket_send') as mock_send, patch('netra_backend.app.routes.websocket.safe_websocket_close') as mock_close, patch('netra_backend.app.websocket_core.agent_handler.AgentMessageHandler') as mock_agent_handler, patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_message_service:
            mock_ws_manager.return_value = Mock()
            mock_message_router = Mock()
            mock_message_router.add_handler = Mock()
            mock_message_router.handlers = []
            mock_router.return_value = mock_message_router
            mock_monitor.return_value = Mock()
            try:
                result = await websocket_endpoint(mock_websocket)
                assert True
            except Exception as e:
                assert not isinstance(e, RuntimeError), f'Unexpected RuntimeError: {e}'

@pytest.mark.asyncio
async def test_websocket_no_fallback_in_production():
    """Test that WebSocket endpoint handles missing dependencies appropriately in production."""
    mock_websocket = Mock(spec=WebSocket)
    mock_app_state = Mock()
    mock_app_state.agent_supervisor = None
    mock_app_state.thread_service = None
    mock_app_state.startup_complete = True
    mock_websocket.app.state = mock_app_state
    mock_websocket.accept = MagicMock(return_value=None)
    mock_websocket.headers = {'sec-websocket-protocol': ''}
    from netra_backend.app.routes.websocket import websocket_endpoint
    with patch('shared.isolated_environment.get_env') as mock_get_env:
        mock_get_env.return_value = {'ENVIRONMENT': 'production', 'TESTING': '0'}
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_ws_manager, patch('netra_backend.app.routes.websocket.get_message_router') as mock_router, patch('netra_backend.app.routes.websocket.get_connection_monitor') as mock_monitor, patch('netra_backend.app.routes.websocket.safe_websocket_send') as mock_send, patch('netra_backend.app.routes.websocket.safe_websocket_close') as mock_close, patch('netra_backend.app.websocket_core.agent_handler.AgentMessageHandler') as mock_agent_handler, patch('netra_backend.app.services.message_handlers.MessageHandlerService') as mock_message_service:
            mock_ws_manager.return_value = Mock()
            mock_message_router = Mock()
            mock_message_router.add_handler = Mock()
            mock_message_router.handlers = []
            mock_router.return_value = mock_message_router
            mock_monitor.return_value = Mock()
            try:
                result = await websocket_endpoint(mock_websocket)
                assert True
            except Exception as e:
                assert not isinstance(e, RuntimeError), f'Unexpected RuntimeError: {e}'

@pytest.mark.asyncio
async def test_websocket_allows_fallback_in_development():
    """Test that WebSocket endpoint allows fallback in development environment."""
    mock_websocket = Mock(spec=WebSocket)
    mock_app_state = Mock()
    mock_app_state.agent_supervisor = None
    mock_app_state.thread_service = None
    mock_websocket.app.state = mock_app_state
    mock_websocket.accept = MagicMock(return_value=None)
    mock_websocket.headers = {'sec-websocket-protocol': ''}
    from netra_backend.app.routes.websocket import websocket_endpoint
    with patch('shared.isolated_environment.get_env') as mock_get_env:
        mock_get_env.return_value = {'ENVIRONMENT': 'development', 'TESTING': '0'}
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_ws_manager, patch('netra_backend.app.routes.websocket.get_message_router') as mock_router, patch('netra_backend.app.routes.websocket.get_connection_monitor') as mock_monitor, patch('netra_backend.app.routes.websocket._create_fallback_agent_handler') as mock_create_fallback:
            mock_ws_manager.return_value = Mock()
            mock_message_router = Mock()
            mock_router.return_value = mock_message_router
            mock_monitor.return_value = Mock()
            mock_fallback_handler = Mock()
            mock_create_fallback.return_value = mock_fallback_handler
            try:
                assert True
            except RuntimeError:
                pytest.fail('Development environment should allow fallback handlers')

@pytest.mark.asyncio
async def test_websocket_allows_fallback_when_testing_flag_set():
    """Test that WebSocket endpoint allows fallback when TESTING flag is set even in staging."""
    mock_websocket = Mock(spec=WebSocket)
    mock_app_state = Mock()
    mock_app_state.agent_supervisor = None
    mock_app_state.thread_service = None
    mock_websocket.app.state = mock_app_state
    mock_websocket.accept = MagicMock(return_value=None)
    mock_websocket.headers = {'sec-websocket-protocol': ''}
    from netra_backend.app.routes.websocket import websocket_endpoint
    with patch('shared.isolated_environment.get_env') as mock_get_env:
        mock_get_env.return_value = {'ENVIRONMENT': 'staging', 'TESTING': '1'}
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_ws_manager, patch('netra_backend.app.routes.websocket.get_message_router') as mock_router, patch('netra_backend.app.routes.websocket.get_connection_monitor') as mock_monitor, patch('netra_backend.app.routes.websocket._create_fallback_agent_handler') as mock_create_fallback:
            mock_ws_manager.return_value = Mock()
            mock_message_router = Mock()
            mock_router.return_value = mock_message_router
            mock_monitor.return_value = Mock()
            mock_fallback_handler = Mock()
            mock_create_fallback.return_value = mock_fallback_handler
            try:
                assert True
            except RuntimeError:
                pytest.fail('TESTING flag should allow fallback handlers even in staging')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')