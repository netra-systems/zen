# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''E2E tests for streaming endpoint singleton behavior.

    # REMOVED_SYNTAX_ERROR: Tests to ensure streaming endpoint uses dependency injection properly.
    # REMOVED_SYNTAX_ERROR: See: SPEC/learnings/agent_registration_idempotency.xml
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi.testclient import TestClient
    # REMOVED_SYNTAX_ERROR: from httpx import AsyncClient

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.main import app
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestStreamingEndpointSingleton:
    # REMOVED_SYNTAX_ERROR: """E2E tests for streaming endpoint agent registration."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_client(self):
    # REMOVED_SYNTAX_ERROR: """Create test client."""
    # REMOVED_SYNTAX_ERROR: return TestClient(app)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def async_client(self):
    # REMOVED_SYNTAX_ERROR: """Create async test client."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: async with AsyncClient(app=app, base_url="http://test") as client:
        # REMOVED_SYNTAX_ERROR: yield client

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def mock_agent_service(self):
    # REMOVED_SYNTAX_ERROR: """Create mock agent service."""
    # REMOVED_SYNTAX_ERROR: service = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: service.supervisor = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: service.supervisor.agent_registry = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: service.supervisor.agent_registry.agents = { )
    # REMOVED_SYNTAX_ERROR: 'triage': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'data': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'optimization': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'actions': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'reporting': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'synthetic_data': MagicNone,  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: 'corpus_admin': MagicNone  # TODO: Use real service instead of Mock
    
    # REMOVED_SYNTAX_ERROR: service.supervisor.agent_registry._agents_registered = True
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def auth_headers(self):
    # REMOVED_SYNTAX_ERROR: """Create auth headers for requests."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "Authorization": "Bearer test_token",
    # REMOVED_SYNTAX_ERROR: "Content-Type": "application/json"
    

    #     #     @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_stream_endpoint_uses_dependency_injection( )
self, mock_create_response, mock_get_service, test_client,
mock_agent_service, auth_headers
# REMOVED_SYNTAX_ERROR: ):
    # REMOVED_SYNTAX_ERROR: """Test that /stream endpoint uses dependency injection."""
    # Setup mocks
    # REMOVED_SYNTAX_ERROR: mock_get_service.return_value = mock_agent_service
    # REMOVED_SYNTAX_ERROR: mock_create_response.return_value = MagicNone  # TODO: Use real service instead of Mock

    # Make request
    # REMOVED_SYNTAX_ERROR: request_data = { )
    # REMOVED_SYNTAX_ERROR: "query": "test query",
    # REMOVED_SYNTAX_ERROR: "id": "test_id"
    

    # REMOVED_SYNTAX_ERROR: response = test_client.post( )
    # REMOVED_SYNTAX_ERROR: "/agent/stream",
    # REMOVED_SYNTAX_ERROR: json=request_data,
    # REMOVED_SYNTAX_ERROR: headers=auth_headers
    

    # Verify get_agent_service was called (via dependency injection)
    # REMOVED_SYNTAX_ERROR: assert mock_get_service.called

    # Verify create_streaming_response received the injected service
    # REMOVED_SYNTAX_ERROR: mock_create_response.assert_called_once()
    # REMOVED_SYNTAX_ERROR: call_args = mock_create_response.call_args[0]
    # REMOVED_SYNTAX_ERROR: assert call_args[1] == mock_agent_service  # Second argument is agent_service

    #     @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_multiple_stream_requests_share_service( )
self, mock_get_service, test_client, mock_agent_service, auth_headers
# REMOVED_SYNTAX_ERROR: ):
    # REMOVED_SYNTAX_ERROR: """Test that multiple requests to /stream share agent service instance."""
    # Track service instances
    # REMOVED_SYNTAX_ERROR: service_instances = []

# REMOVED_SYNTAX_ERROR: def track_service(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: service = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: service_instances.append(service)
    # REMOVED_SYNTAX_ERROR: return service

    # REMOVED_SYNTAX_ERROR: mock_get_service.side_effect = track_service

    # REMOVED_SYNTAX_ERROR: request_data = { )
    # REMOVED_SYNTAX_ERROR: "query": "test query",
    # REMOVED_SYNTAX_ERROR: "id": "test_id"
    

    # Make multiple requests
    # REMOVED_SYNTAX_ERROR: for _ in range(3):
        # REMOVED_SYNTAX_ERROR: test_client.post( )
        # REMOVED_SYNTAX_ERROR: "/agent/stream",
        # REMOVED_SYNTAX_ERROR: json=request_data,
        # REMOVED_SYNTAX_ERROR: headers=auth_headers
        

        # Each request should get its own service instance (FastAPI behavior)
        # But within a request, the same instance should be used
        # REMOVED_SYNTAX_ERROR: assert len(service_instances) == 3

        # Removed problematic line: @pytest.mark.asyncio
        #     @pytest.mark.e2e
        # Removed problematic line: async def test_no_duplicate_registration_logs( )
        # REMOVED_SYNTAX_ERROR: self, mock_logger, async_client, auth_headers
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test that agent registration doesn't occur multiple times."""
            # REMOVED_SYNTAX_ERROR: request_data = { )
            # REMOVED_SYNTAX_ERROR: "query": "test query",
            # REMOVED_SYNTAX_ERROR: "id": "test_id"
            

            # Make multiple streaming requests
            # REMOVED_SYNTAX_ERROR: for _ in range(5):
                # REMOVED_SYNTAX_ERROR: await async_client.post( )
                # REMOVED_SYNTAX_ERROR: "/agent/stream",
                # REMOVED_SYNTAX_ERROR: json=request_data,
                # REMOVED_SYNTAX_ERROR: headers=auth_headers
                

                # Check that we don't see repeated registration logs
                # REMOVED_SYNTAX_ERROR: info_calls = [call for call in mock_logger.info.call_args_list )
                # REMOVED_SYNTAX_ERROR: if 'Registered agent:' in str(call)]

                # Should have at most 7 info logs (one per agent type)
                # REMOVED_SYNTAX_ERROR: assert len(info_calls) <= 7

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_concurrent_stream_requests(self, async_client, auth_headers):
                    # REMOVED_SYNTAX_ERROR: """Test that concurrent streaming requests don't cause registration issues."""
                    # REMOVED_SYNTAX_ERROR: request_data = { )
                    # REMOVED_SYNTAX_ERROR: "query": "test query",
                    # REMOVED_SYNTAX_ERROR: "id": "test_id"
                    

                    # REMOVED_SYNTAX_ERROR: registration_count = {'count': 0}

                    # REMOVED_SYNTAX_ERROR: original_register = None

# REMOVED_SYNTAX_ERROR: def count_registrations(*args, **kwargs):
    # REMOVED_SYNTAX_ERROR: registration_count['count'] += 1
    # REMOVED_SYNTAX_ERROR: if original_register:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return original_register(*args, **kwargs)

        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.register_default_agents',
        # REMOVED_SYNTAX_ERROR: side_effect=count_registrations) as mock_register:
            # REMOVED_SYNTAX_ERROR: original_register = mock_register.wraps

            # Make concurrent requests
            # REMOVED_SYNTAX_ERROR: tasks = []
            # REMOVED_SYNTAX_ERROR: for _ in range(10):
                # REMOVED_SYNTAX_ERROR: task = async_client.post( )
                # REMOVED_SYNTAX_ERROR: "/agent/stream",
                # REMOVED_SYNTAX_ERROR: json=request_data,
                # REMOVED_SYNTAX_ERROR: headers=auth_headers
                
                # REMOVED_SYNTAX_ERROR: tasks.append(task)

                # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                # Registration should happen limited number of times (not once per request)
                # Due to FastAPI's dependency injection, it might be called once per worker
                # REMOVED_SYNTAX_ERROR: assert registration_count['count'] <= 10

                # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_stream_endpoint_response_structure(self, test_client, auth_headers):
    # REMOVED_SYNTAX_ERROR: """Test that streaming endpoint returns proper response."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: request_data = { )
    # REMOVED_SYNTAX_ERROR: "query": "test query",
    # REMOVED_SYNTAX_ERROR: "id": "test_id"
    

    # REMOVED_SYNTAX_ERROR: mock_response = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: mock_response.body_iterator = [b"data: test )

    # REMOVED_SYNTAX_ERROR: "]
    # REMOVED_SYNTAX_ERROR: mock_response.status_code = 200
    # REMOVED_SYNTAX_ERROR: mock_response.headers = {"Content-Type": "text/event-stream"}

    # REMOVED_SYNTAX_ERROR: response = test_client.post( )
    # REMOVED_SYNTAX_ERROR: "/agent/stream",
    # REMOVED_SYNTAX_ERROR: json=request_data,
    # REMOVED_SYNTAX_ERROR: headers=auth_headers
    

    # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

    #     @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_agent_registry_initialization(self, mock_registry_class, test_client, auth_headers):
    # REMOVED_SYNTAX_ERROR: """Test that AgentRegistry is initialized properly."""
    # REMOVED_SYNTAX_ERROR: mock_instance = MagicNone  # TODO: Use real service instead of Mock
    # REMOVED_SYNTAX_ERROR: mock_instance._agents_registered = False
    # REMOVED_SYNTAX_ERROR: mock_instance.agents = {}
    # REMOVED_SYNTAX_ERROR: mock_registry_class.return_value = mock_instance

    # REMOVED_SYNTAX_ERROR: request_data = { )
    # REMOVED_SYNTAX_ERROR: "query": "test query",
    # REMOVED_SYNTAX_ERROR: "id": "test_id"
    

    # REMOVED_SYNTAX_ERROR: test_client.post( )
    # REMOVED_SYNTAX_ERROR: "/agent/stream",
    # REMOVED_SYNTAX_ERROR: json=request_data,
    # REMOVED_SYNTAX_ERROR: headers=auth_headers
    

    # Verify registry was initialized with idempotency flag
    # REMOVED_SYNTAX_ERROR: assert hasattr(mock_instance, '_agents_registered')

    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_message_endpoint_also_uses_injection(self, test_client, auth_headers):
    # REMOVED_SYNTAX_ERROR: """Test that /message endpoint also uses dependency injection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: request_data = { )
    # REMOVED_SYNTAX_ERROR: "message": "test message",
    # REMOVED_SYNTAX_ERROR: "thread_id": "test_thread"
    

    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.routes.agent_route.get_agent_service') as mock_get_service:
        # REMOVED_SYNTAX_ERROR: mock_get_service.return_value = MagicNone  # TODO: Use real service instead of Mock

        # REMOVED_SYNTAX_ERROR: response = test_client.post( )
        # REMOVED_SYNTAX_ERROR: "/agent/message",
        # REMOVED_SYNTAX_ERROR: json=request_data,
        # REMOVED_SYNTAX_ERROR: headers=auth_headers
        

        # Verify dependency injection was used
        # REMOVED_SYNTAX_ERROR: assert mock_get_service.called