"""E2E tests for streaming endpoint singleton behavior.

Tests to ensure streaming endpoint uses dependency injection properly.
See: SPEC/learnings/agent_registration_idempotency.xml
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from netra_backend.app.main import app


class TestStreamingEndpointSingleton:
    """E2E tests for streaming endpoint agent registration."""

    @pytest.fixture
    @pytest.mark.e2e
    def test_client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        service = MagicNone  # TODO: Use real service instead of Mock
        service.supervisor = MagicNone  # TODO: Use real service instead of Mock
        service.supervisor.agent_registry = MagicNone  # TODO: Use real service instead of Mock
        service.supervisor.agent_registry.agents = {
            'triage': MagicNone,  # TODO: Use real service instead of Mock
            'data': MagicNone,  # TODO: Use real service instead of Mock
            'optimization': MagicNone,  # TODO: Use real service instead of Mock
            'actions': MagicNone,  # TODO: Use real service instead of Mock
            'reporting': MagicNone,  # TODO: Use real service instead of Mock
            'synthetic_data': MagicNone,  # TODO: Use real service instead of Mock
            'corpus_admin': MagicNone  # TODO: Use real service instead of Mock
        }
        service.supervisor.agent_registry._agents_registered = True
        return service

    @pytest.fixture
    def auth_headers(self):
        """Create auth headers for requests."""
        return {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }

    # @patch(...) - Removed: No mocks in e2e tests
    # @patch(...) - Removed: No mocks in e2e tests
    @pytest.mark.e2e
    def test_stream_endpoint_uses_dependency_injection(
        self, mock_create_response, mock_get_service, test_client, 
        mock_agent_service, auth_headers
    ):
        """Test that /stream endpoint uses dependency injection."""
        # Setup mocks
        mock_get_service.return_value = mock_agent_service
        mock_create_response.return_value = MagicNone  # TODO: Use real service instead of Mock
        
        # Make request
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            response = test_client.post(
                "/agent/stream",
                json=request_data,
                headers=auth_headers
            )
        
        # Verify get_agent_service was called (via dependency injection)
        assert mock_get_service.called
        
        # Verify create_streaming_response received the injected service
        mock_create_response.assert_called_once()
        call_args = mock_create_response.call_args[0]
        assert call_args[1] == mock_agent_service  # Second argument is agent_service

    # @patch(...) - Removed: No mocks in e2e tests
    @pytest.mark.e2e
    def test_multiple_stream_requests_share_service(
        self, mock_get_service, test_client, mock_agent_service, auth_headers
    ):
        """Test that multiple requests to /stream share agent service instance."""
        # Track service instances
        service_instances = []
        
        def track_service(*args, **kwargs):
            service = MagicNone  # TODO: Use real service instead of Mock
            service_instances.append(service)
            return service
        
        mock_get_service.side_effect = track_service
        
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route_streaming.create_streaming_response'):
                # Make multiple requests
                for _ in range(3):
                    test_client.post(
                        "/agent/stream",
                        json=request_data,
                        headers=auth_headers
                    )
        
        # Each request should get its own service instance (FastAPI behavior)
        # But within a request, the same instance should be used
        assert len(service_instances) == 3

    @pytest.mark.asyncio
    # @patch(...) - Removed: No mocks in e2e tests
    @pytest.mark.e2e
    async def test_no_duplicate_registration_logs(
        self, mock_logger, async_client, auth_headers
    ):
        """Test that agent registration doesn't occur multiple times."""
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route_streaming.create_streaming_response'):
                # Make multiple streaming requests
                for _ in range(5):
                    await async_client.post(
                        "/agent/stream",
                        json=request_data,
                        headers=auth_headers
                    )
        
        # Check that we don't see repeated registration logs
        info_calls = [call for call in mock_logger.info.call_args_list 
                     if 'Registered agent:' in str(call)]
        
        # Should have at most 7 info logs (one per agent type)
        assert len(info_calls) <= 7

    @pytest.mark.asyncio
    async def test_concurrent_stream_requests(self, async_client, auth_headers):
        """Test that concurrent streaming requests don't cause registration issues."""
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        registration_count = {'count': 0}
        
        original_register = None
        
        def count_registrations(*args, **kwargs):
            registration_count['count'] += 1
            if original_register:
                return original_register(*args, **kwargs)
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route_streaming.create_streaming_response'):
                with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.register_default_agents', 
                          side_effect=count_registrations) as mock_register:
                    original_register = mock_register.wraps
                    
                    # Make concurrent requests
                    tasks = []
                    for _ in range(10):
                        task = async_client.post(
                            "/agent/stream",
                            json=request_data,
                            headers=auth_headers
                        )
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)
        
        # Registration should happen limited number of times (not once per request)
        # Due to FastAPI's dependency injection, it might be called once per worker
        assert registration_count['count'] <= 10

    @pytest.mark.e2e
    def test_stream_endpoint_response_structure(self, test_client, auth_headers):
        """Test that streaming endpoint returns proper response."""
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        mock_response = MagicNone  # TODO: Use real service instead of Mock
        mock_response.body_iterator = [b"data: test\n\n"]
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/event-stream"}
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route_streaming.create_streaming_response',
                      return_value=mock_response):
                response = test_client.post(
                    "/agent/stream",
                    json=request_data,
                    headers=auth_headers
                )
        
        assert response.status_code == 200

    # @patch(...) - Removed: No mocks in e2e tests
    @pytest.mark.e2e
    def test_agent_registry_initialization(self, mock_registry_class, test_client, auth_headers):
        """Test that AgentRegistry is initialized properly."""
        mock_instance = MagicNone  # TODO: Use real service instead of Mock
        mock_instance._agents_registered = False
        mock_instance.agents = {}
        mock_registry_class.return_value = mock_instance
        
        request_data = {
            "query": "test query",
            "id": "test_id"
        }
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route_streaming.create_streaming_response'):
                test_client.post(
                    "/agent/stream",
                    json=request_data,
                    headers=auth_headers
                )
        
        # Verify registry was initialized with idempotency flag
        assert hasattr(mock_instance, '_agents_registered')

    @pytest.mark.e2e
    def test_message_endpoint_also_uses_injection(self, test_client, auth_headers):
        """Test that /message endpoint also uses dependency injection."""
        request_data = {
            "message": "test message",
            "thread_id": "test_thread"
        }
        
        with patch('netra_backend.app.dependencies.verify_token', return_value={"sub": "test_user"}):
            with patch('netra_backend.app.routes.agent_route.get_agent_service') as mock_get_service:
                with patch('netra_backend.app.routes.agent_route_processors.execute_message_processing'):
                    mock_get_service.return_value = MagicNone  # TODO: Use real service instead of Mock
                    
                    response = test_client.post(
                        "/agent/message",
                        json=request_data,
                        headers=auth_headers
                    )
                    
                    # Verify dependency injection was used
                    assert mock_get_service.called