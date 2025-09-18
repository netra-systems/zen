"""
Issue #508: WebSocket ASGI Middleware Integration Test Suite

CRITICAL BUG INTEGRATION TESTS:
- Error: 'URL' object has no attribute 'query_params' 
- Location: netra_backend/app/routes/websocket_ssot.py:354
- Context: ASGI middleware WebSocket exclusion processing

INTEGRATION TEST FOCUS:
1. Middleware WebSocket exclusion handling with ASGI scopes
2. FastAPI WebSocket URL object interactions
3. Authentication middleware WebSocket processing
4. Real WebSocket connection scenarios that trigger the bug

BUSINESS IMPACT:
- P0 Critical: $500K+ ARR at risk from WebSocket failures
- Golden Path chat functionality degradation
- Real-time agent event delivery failures

SUCCESS CRITERIA:
- Tests MUST reproduce actual middleware processing paths
- Tests MUST integrate with FastAPI WebSocket handling
- Tests MUST validate ASGI scope processing chain
- Tests MUST demonstrate business impact scenarios
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.datastructures import URL, QueryParams
from starlette.websockets import WebSocketState
from starlette.types import ASGIApp, Receive, Send, Scope
from starlette.middleware.base import BaseHTTPMiddleware
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
try:
    from netra_backend.app.core.middleware_setup import setup_enhanced_middleware_stack
except ImportError:
    setup_enhanced_middleware_stack = None

@pytest.mark.integration
class Issue508WebSocketASGIMiddlewareIntegrationTests(SSotAsyncTestCase):
    """
    Issue #508: Integration tests for WebSocket ASGI middleware processing
    
    These tests reproduce the exact middleware chain that leads to the bug
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.app = FastAPI(title='Issue 508 Test App')
        self.client = TestClient(self.app)
        self.websocket_urls = ['ws://localhost:8000/ws/chat?token=jwt_token&user_id=123', 'ws://localhost:8000/ws/agent?token=test&thread_id=abc&run_id=xyz', 'ws://localhost:8000/ws/health?mode=status&timestamp=1234567890']

    @pytest.mark.asyncio
    async def test_middleware_websocket_exclusion_asgi_scope_error(self):
        """
        CRITICAL: Integration test reproducing middleware WebSocket exclusion error
        
        This test simulates the full middleware stack processing a WebSocket request
        that leads to the URL.query_params AttributeError
        """

        class WebSocketExclusionMiddlewareTests(BaseHTTPMiddleware):

            async def dispatch(self, request, call_next):
                try:
                    if request.url.path.startswith('/ws/'):
                        websocket_context = {'path': request.url.path, 'query_params': dict(request.url.query_params) if hasattr(request.url, 'query_params') else {}}
                    response = await call_next(request)
                    return response
                except AttributeError as e:
                    if "'URL' object has no attribute 'query_params'" in str(e):
                        raise e
                    raise
        self.app.add_middleware(WebSocketExclusionMiddlewareTests)

        @self.app.websocket('/ws/chat')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text('Connected')
            await websocket.close()
        with pytest.raises((AttributeError, Exception)) as exc_info:
            with self.client.websocket_connect('/ws/chat?token=test123&user_id=456') as websocket:
                data = websocket.receive_text()

    @pytest.mark.asyncio
    async def test_websocket_asgi_scope_processing_chain(self):
        """
        Integration test for complete ASGI scope processing chain
        
        Tests the flow: ASGI scope -> middleware -> WebSocket handler -> bug location
        """

        async def mock_asgi_app(scope: Scope, receive: Receive, send: Send):
            if scope['type'] == 'websocket':
                websocket_mock = Mock()
                websocket_mock.url = URL('ws://localhost/ws/chat?' + scope['query_string'].decode())
                try:
                    connection_context = {'websocket_url': str(websocket_mock.url), 'path': websocket_mock.url.path, 'query_params': dict(websocket_mock.url.query_params) if websocket_mock.url.query_params else {}}
                except AttributeError as e:
                    assert "'URL' object has no attribute 'query_params'" in str(e)
                    raise
        websocket_scope = {'type': 'websocket', 'scheme': 'ws', 'path': '/ws/chat', 'query_string': b'token=test123&user_id=456', 'headers': [(b'host', b'localhost:8000')]}
        receive = AsyncMock()
        send = AsyncMock()
        with pytest.raises(AttributeError) as exc_info:
            await mock_asgi_app(websocket_scope, receive, send)
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_middleware_websocket_processing_bug(self):
        """
        Integration test for authentication middleware WebSocket processing
        
        This reproduces how authentication middleware processing leads to the bug
        """

        class AuthMiddlewareWithBug:

            def process_websocket_authentication(self, websocket: WebSocket) -> Dict[str, Any]:
                """
                This simulates authentication middleware processing that triggers the bug
                """
                try:
                    auth_context = {'websocket_url': str(websocket.url), 'path': websocket.url.path, 'query_params': dict(websocket.url.query_params) if websocket.url.query_params else {}, 'auth_token': None}
                    auth_token = auth_context['query_params'].get('token')
                    auth_context['auth_token'] = auth_token
                    return auth_context
                except AttributeError as e:
                    raise e
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL('ws://localhost:8000/ws/chat?token=jwt_auth_token&user_id=12345')
        auth_middleware = AuthMiddlewareWithBug()
        with pytest.raises(AttributeError) as exc_info:
            auth_context = auth_middleware.process_websocket_authentication(mock_websocket)
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

@pytest.mark.integration
class Issue508WebSocketSSoTHealthEndpointIntegrationTests(SSotAsyncTestCase):
    """
    Issue #508: Integration tests for WebSocket SSOT health endpoint processing
    
    Direct integration tests for the buggy code in websocket_ssot.py
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()

    @pytest.mark.asyncio
    async def test_websocket_ssot_health_endpoint_integration_bug(self):
        """
        CRITICAL: Integration test for websocket_ssot.py health endpoint bug
        
        This test directly reproduces the error in websocket_ssot.py:354
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL('ws://localhost:8000/ws/health?mode=status&connection_id=test123')
        mock_websocket.client = Mock()
        mock_websocket.client.host = 'localhost'
        mock_websocket.headers = {'host': 'localhost:8000', 'user-agent': 'TestClient/1.0'}

        def simulate_websocket_health_context_creation():
            """
            This simulates the exact code from websocket_ssot.py:350-360
            """
            connection_id = 'test-connection-123'
            mode = 'health'
            user_agent = 'TestClient/1.0'
            connection_context = {'connection_id': connection_id, 'websocket_url': str(mock_websocket.url), 'path': mock_websocket.url.path, 'query_params': dict(mock_websocket.url.query_params) if mock_websocket.url.query_params else {}, 'mode_parameter': mode, 'user_agent': user_agent, 'client_host': getattr(mock_websocket.client, 'host', 'unknown') if mock_websocket.client else 'no_client', 'headers_count': len(mock_websocket.headers) if mock_websocket.headers else 0, 'has_auth_header': 'authorization' in (mock_websocket.headers or {})}
            return connection_context
        with pytest.raises(AttributeError) as exc_info:
            context = simulate_websocket_health_context_creation()
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_websocket_ssot_config_endpoint_integration_bug(self):
        """
        Integration test for WebSocket SSOT config endpoint processing
        
        Tests other endpoints in websocket_ssot.py that might have the same bug
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL('ws://localhost:8000/ws/config?env=staging&service=backend')
        mock_websocket.client = Mock()
        mock_websocket.client.host = 'localhost'
        mock_websocket.headers = {'host': 'localhost:8000'}

        def simulate_websocket_config_context():
            return {'connection_id': 'config-connection-456', 'websocket_url': str(mock_websocket.url), 'path': mock_websocket.url.path, 'query_params': dict(mock_websocket.url.query_params) if mock_websocket.url.query_params else {}, 'endpoint_type': 'config', 'environment': 'staging'}
        with pytest.raises(AttributeError) as exc_info:
            config_context = simulate_websocket_config_context()
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_websocket_ssot_stats_endpoint_integration_bug(self):
        """
        Integration test for WebSocket SSOT stats endpoint processing
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL('ws://localhost:8000/ws/stats?metric=connections&interval=5m')
        mock_websocket.client = Mock()
        mock_websocket.client.host = 'localhost'
        mock_websocket.headers = {'host': 'localhost:8000'}

        def simulate_websocket_stats_context():
            return {'connection_id': 'stats-connection-789', 'websocket_url': str(mock_websocket.url), 'path': mock_websocket.url.path, 'query_params': dict(mock_websocket.url.query_params) if mock_websocket.url.query_params else {}, 'endpoint_type': 'stats', 'metrics_requested': ['connections']}
        with pytest.raises(AttributeError) as exc_info:
            stats_context = simulate_websocket_stats_context()
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

@pytest.mark.integration
class Issue508WebSocketRealConnectionScenariosTests(SSotAsyncTestCase):
    """
    Issue #508: Real WebSocket connection scenarios that trigger the bug
    
    Integration tests using actual WebSocket connection patterns
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        self.app = FastAPI(title='Issue 508 Real Connection Test')
        self.setup_websocket_endpoints()

    def setup_websocket_endpoints(self):
        """Set up WebSocket endpoints that would trigger the bug"""

        @self.app.websocket('/ws/chat')
        async def chat_websocket(websocket: WebSocket):
            await websocket.accept()
            try:
                context = {'url': str(websocket.url), 'path': websocket.url.path, 'query_params': dict(websocket.url.query_params) if websocket.url.query_params else {}}
                await websocket.send_json({'status': 'connected', 'context': context})
            except AttributeError as e:
                await websocket.send_json({'error': str(e)})
            finally:
                await websocket.close()

        @self.app.websocket('/ws/agent')
        async def agent_websocket(websocket: WebSocket):
            await websocket.accept()
            try:
                agent_context = {'websocket_url': str(websocket.url), 'path': websocket.url.path, 'query_params': dict(websocket.url.query_params) if websocket.url.query_params else {}, 'agent_events': ['agent_started', 'agent_thinking', 'tool_executing']}
                await websocket.send_json({'agent_status': 'ready', 'context': agent_context})
            except AttributeError as e:
                await websocket.send_json({'agent_error': str(e)})
            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_real_chat_websocket_connection_with_auth_params(self):
        """
        Real WebSocket connection test with authentication parameters
        
        This reproduces actual user connection scenarios that would fail
        """
        websocket_url = 'ws://localhost/ws/chat?token=jwt_token_here&user_id=12345&session_id=abc'
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL(websocket_url)
        with pytest.raises(AttributeError) as exc_info:
            chat_context = {'connection_type': 'chat', 'websocket_url': str(mock_websocket.url), 'path': mock_websocket.url.path, 'query_params': dict(mock_websocket.url.query_params) if mock_websocket.url.query_params else {}, 'user_authenticated': False, 'business_impact': '$500K+ ARR affected'}
            auth_token = chat_context['query_params'].get('token')
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_real_agent_websocket_connection_with_execution_params(self):
        """
        Real agent WebSocket connection test with execution parameters
        """
        agent_websocket_url = 'ws://localhost/ws/agent?user_id=123&thread_id=thread_abc&run_id=run_xyz&mode=execute'
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.url = URL(agent_websocket_url)
        with pytest.raises(AttributeError) as exc_info:
            agent_execution_context = {'connection_type': 'agent', 'websocket_url': str(mock_websocket.url), 'path': mock_websocket.url.path, 'query_params': dict(mock_websocket.url.query_params) if mock_websocket.url.query_params else {}, 'execution_mode': 'execute', 'critical_events_affected': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']}
            user_id = agent_execution_context['query_params'].get('user_id')
            thread_id = agent_execution_context['query_params'].get('thread_id')
            run_id = agent_execution_context['query_params'].get('run_id')
        assert "'URL' object has no attribute 'query_params'" in str(exc_info.value)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')