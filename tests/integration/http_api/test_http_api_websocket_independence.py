"""
Test Issue #362: HTTP API should work without WebSocket dependency.

This test validates that HTTP API endpoints can execute agents successfully
even when WebSocket connections are unavailable, providing system resilience.
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from netra_backend.app.main import app
from netra_backend.app.dependencies import RequestScopedContext
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestHttpApiWebSocketIndependence(SSotAsyncTestCase):
    """Test HTTP API independence from WebSocket connections."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = TestClient(app)

    def test_request_scoped_context_websocket_property_alias(self):
        """Test that RequestScopedContext has websocket_connection_id property alias."""
        context = RequestScopedContext(user_id='test_user', thread_id='test_thread', run_id='test_run', websocket_client_id='test_websocket_id')
        self.assertEqual(context.websocket_connection_id, 'test_websocket_id')
        self.assertEqual(context.websocket_connection_id, context.websocket_client_id)
        context_none = RequestScopedContext(user_id='test_user', thread_id='test_thread', run_id='test_run', websocket_client_id=None)
        self.assertIsNone(context_none.websocket_connection_id)

    @patch('netra_backend.app.dependencies.get_agent_service_optional')
    def test_http_api_agent_execute_without_service(self, mock_get_service):
        """Test HTTP API agent execution when AgentService unavailable."""
        mock_get_service.return_value = None
        response = self.client.post('/api/agents/execute', json={'type': 'triage', 'message': 'Test message without WebSocket'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'service_unavailable')
        self.assertEqual(data['agent'], 'triage')
        self.assertIn('Service unavailable', data['response'])
        self.assertIn('request acknowledged', data['response'])

    @patch('netra_backend.app.dependencies.get_agent_service_optional')
    def test_http_api_specific_agents_fallback(self, mock_get_service):
        """Test specific agent endpoints work without WebSocket."""
        mock_get_service.return_value = None
        agent_types = ['triage', 'data', 'optimization']
        for agent_type in agent_types:
            with self.subTest(agent_type=agent_type):
                response = self.client.post(f'/api/agents/{agent_type}', json={'message': f'Test {agent_type} without WebSocket'})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data['status'], 'service_unavailable')
                self.assertEqual(data['agent'], agent_type)

    @patch('netra_backend.app.dependencies.get_agent_service_optional')
    def test_http_api_control_endpoints_fallback(self, mock_get_service):
        """Test agent control endpoints work without WebSocket."""
        mock_get_service.return_value = None
        response = self.client.post('/api/agents/start', json={'agent_type': 'triage', 'message': 'Test start without WebSocket'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'start')
        self.assertIn('Mock start response', data['message'])
        response = self.client.post('/api/agents/stop', json={'agent_id': 'test-agent-123', 'reason': 'Test stop'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'stop')
        response = self.client.post('/api/agents/cancel', json={'agent_id': 'test-agent-123'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'cancel')

    @patch('netra_backend.app.dependencies.get_agent_service_optional')
    def test_http_api_status_endpoint_fallback(self, mock_get_service):
        """Test agent status endpoint works without WebSocket."""
        mock_get_service.return_value = None
        response = self.client.get('/api/agents/status')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        agent_status = data[0]
        self.assertIn('agent_id', agent_status)
        self.assertIn('status', agent_status)
        self.assertIn('agent_type', agent_status)
        response = self.client.get('/api/agents/status?agent_id=test-agent-123')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['agent_id'], 'test-agent-123')

    @patch('netra_backend.app.dependencies.get_agent_service_optional')
    def test_http_api_streaming_fallback(self, mock_get_service):
        """Test streaming endpoint provides fallback without WebSocket."""
        mock_get_service.return_value = None
        response = self.client.post('/api/agents/stream', json={'agent_type': 'triage', 'message': 'Test streaming without WebSocket'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=utf-8')
        content = response.text
        self.assertIn('data:', content)
        self.assertIn('agent_started', content)
        self.assertIn('agent_thinking', content)
        self.assertIn('agent_completed', content)
        self.assertIn('stream_end', content)

    @patch('netra_backend.app.services.agent_service_core.AgentService')
    async def test_agent_service_fallback_execution(self, mock_agent_service_class):
        """Test AgentService fallback execution without WebSocket coordination."""
        from netra_backend.app.services.agent_service_core import AgentService
        mock_supervisor = AsyncMock()
        mock_supervisor.run.return_value = 'Fallback execution result'
        service = AgentService(mock_supervisor)
        service._bridge_initialized = False
        service._bridge = None
        result = await service._execute_agent_fallback(agent_type='triage', message='Test fallback execution', context={'test': 'context'}, user_id='test_user')
        mock_supervisor.run.assert_called_once()
        call_args = mock_supervisor.run.call_args[0]
        self.assertIn('triage', call_args[0])
        self.assertIn('Test fallback execution', call_args[0])
        self.assertEqual(call_args[1], 'thread_test_user')
        self.assertEqual(call_args[2], 'test_user')
        self.assertIn('status', result)
        self.assertIn('response', result)
        self.assertIn('user_id', result)

    def test_get_request_scoped_user_context_websocket_parameter_mapping(self):
        """Test parameter mapping in get_request_scoped_user_context_http_api."""
        from netra_backend.app.dependencies import get_request_scoped_user_context_http_api
        context = get_request_scoped_user_context_http_api(user_id='test_user', thread_id='test_thread', run_id='test_run', websocket_connection_id='test_connection_id')
        self.assertEqual(context.websocket_client_id, 'test_connection_id')
        self.assertEqual(context.websocket_connection_id, 'test_connection_id')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')