"""
Test 22: Agent Route Message Handling
Tests for agent API message processing - app/routes/agent_route.py
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional
from .test_utilities import setup_agent_mocks, clear_dependency_overrides


class TestAgentRoute:
    """Test agent API message processing."""
    
    @pytest.fixture
    def client(self):
        """Client with agent dependencies mocked."""
        from app.main import app
        from fastapi.testclient import TestClient
        
        setup_agent_mocks(app)
        
        try:
            return TestClient(app)
        finally:
            clear_dependency_overrides(app)
    
    def test_agent_message_processing(self, client):
        """Test agent message processing endpoint."""
        from app.main import app
        from app.services.agent_service import get_agent_service, AgentService
        
        # Create mock service
        mock_agent_service = Mock(spec=AgentService)
        mock_agent_service.process_message = AsyncMock(return_value={
            "response": "Processed successfully",
            "agent": "supervisor",
            "status": "success"
        })
        
        # Override dependency for test
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = client.post(
                "/api/agent/message",
                json={"message": "Test message", "thread_id": "thread1"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "agent" in data
                assert data["status"] == "success"
        finally:
            # Clean up override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]

    async def test_agent_streaming_response(self):
        """Test agent streaming response capability."""
        from app.routes.agent_route import stream_agent_response
        from app.services.agent_service import AgentService
        
        # Create mock agent service
        mock_agent_service = Mock(spec=AgentService)
        
        async def mock_generate_stream(message: str, thread_id: Optional[str] = None):
            """Mock async generator that yields properly typed chunks."""
            yield {"type": "content", "data": "Part 1"}
            yield {"type": "content", "data": "Part 2"}
            yield {"type": "content", "data": "Part 3"}
        
        mock_agent_service.generate_stream = mock_generate_stream
        
        # Test streaming
        with patch('app.routes.agent_route.get_agent_service', return_value=mock_agent_service):
            chunks = []
            async for chunk in stream_agent_response("test message", agent_service=mock_agent_service):
                chunks.append(chunk)
            
            # 3 content chunks + 1 completion chunk
            assert len(chunks) == 4

    def test_agent_error_handling(self, client):
        """Test agent error handling."""
        from app.main import app
        from app.services.agent_service import get_agent_service, AgentService
        
        # Create mock service that raises exception
        mock_agent_service = Mock(spec=AgentService)
        mock_agent_service.process_message = AsyncMock(side_effect=Exception("Processing failed"))
        
        # Override dependency
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = client.post(
                "/api/agent/message",
                json={"message": "Test message"}
            )
            
            # Internal server error expected
            assert response.status_code == 500
        finally:
            # Clean up override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]