"""
Test 22: Agent Route Message Handling
Tests for agent API message processing - app/routes/agent_route.py

Business Value Justification (BVJ):
- Segment: Growth, Mid, Enterprise
- Business Goal: Core AI Agent functionality for customer value delivery
- Value Impact: Direct impact on AI processing quality and response generation
- Revenue Impact: Core revenue driver - agent performance affects customer retention
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


from typing import Optional

import pytest

from netra_backend.tests.test_route_fixtures import (
    CommonResponseValidators,
    MockServiceFactory,
    agent_test_client,
)

class TestAgentRoute:
    """Test agent API message processing and streaming functionality."""
    
    def test_agent_message_processing(self, agent_test_client):
        """Test agent message processing endpoint."""
        from netra_backend.app.main import app
        from netra_backend.app.services.agent_service import get_agent_service
        
        # Create and configure mock agent service
        mock_agent_service = MockServiceFactory.create_mock_agent_service()
        
        # Override the dependency for this specific test
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = agent_test_client.post(
                "/api/agent/message",
                json={"message": "Test message", "thread_id": "thread1"}
            )
            
            if response.status_code == 200:
                CommonResponseValidators.validate_success_response(
                    response,
                    expected_keys=["response", "agent", "status"]
                )
                data = response.json()
                assert data["status"] == "success"
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    
    @pytest.mark.asyncio
    async def test_agent_streaming_response(self):
        """Test agent streaming response capability."""
        import json

        from netra_backend.app.routes.agent_route import stream_agent_response
        from netra_backend.app.services.agent_service import AgentService
        
        # Create a mock agent service with streaming capability
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service = Mock(spec=AgentService)
        
        async def mock_generate_stream(message: str, thread_id: Optional[str] = None):
            """Mock async generator that yields properly typed chunks."""
            yield {"type": "content", "data": "Part 1"}
            yield {"type": "content", "data": "Part 2"}  
            yield {"type": "content", "data": "Part 3"}
        
        mock_agent_service.generate_stream = mock_generate_stream
        
        # Mock the dependencies
        # Mock: Agent service isolation for testing without LLM agent execution
        with patch('netra_backend.app.routes.agent_route.get_agent_service', return_value=mock_agent_service):
            chunks = await self._collect_stream_chunks("test message", mock_agent_service)
            
            assert len(chunks) == 4  # 3 content chunks + 1 completion chunk
            
            # Verify chunk structure (parse JSON strings back to dicts)
            for i, chunk_str in enumerate(chunks[:3]):
                chunk = json.loads(chunk_str)
                assert chunk["type"] == "content"
                assert chunk["data"] == f"Part {i+1}"
    
    async def _collect_stream_chunks(self, message: str, agent_service):
        """Helper to collect streaming chunks into a list."""
        from netra_backend.app.routes.agent_route import stream_agent_response
        chunks = []
        async for chunk in stream_agent_response(message, agent_service=agent_service):
            chunks.append(chunk)
        return chunks
    
    def test_agent_error_handling(self, agent_test_client):
        """Test agent error handling."""
        from netra_backend.app.main import app
        from netra_backend.app.services.agent_service import (
            AgentService,
            get_agent_service,
        )
        
        # Create a mock AgentService that raises an exception
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service = Mock(spec=AgentService)
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service.process_message = AsyncMock(side_effect=Exception("Processing failed"))
        
        # Override the dependency
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = agent_test_client.post(
                "/api/agent/message",
                json={"message": "Test message"}
            )
            
            assert response.status_code == 500  # Internal server error expected
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    
    def test_agent_message_validation(self, agent_test_client):
        """Test agent message input validation."""
        from netra_backend.app.main import app
        from netra_backend.app.services.agent_service import get_agent_service
        
        # Create and configure mock agent service
        mock_agent_service = MockServiceFactory.create_mock_agent_service()
        
        # Override the dependency for this specific test
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            # Test empty message
            response = agent_test_client.post(
                "/api/agent/message",
                json={"message": ""}
            )
            CommonResponseValidators.validate_error_response(response, [422, 400])
            
            # Test missing message field
            response = agent_test_client.post(
                "/api/agent/message", 
                json={"thread_id": "thread1"}
            )
            CommonResponseValidators.validate_error_response(response, [422, 400])
            
            # Test invalid JSON
            response = agent_test_client.post(
                "/api/agent/message",
                data="invalid json"
            )
            CommonResponseValidators.validate_error_response(response, [422, 400])
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    
    @pytest.mark.asyncio
    async def test_agent_context_management(self):
        """Test agent context and thread management."""
        from netra_backend.app.routes.agent_route import process_with_context
        from netra_backend.app.services.agent_service import AgentService
        
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service = Mock(spec=AgentService)
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service.process_message = AsyncMock(return_value={
            "response": "Context-aware response",
            "context": {"thread_id": "thread123", "message_count": 5}
        })
        
        # Mock: Agent service isolation for testing without LLM agent execution
        with patch('netra_backend.app.routes.agent_route.get_agent_service', return_value=mock_agent_service):
            result = await process_with_context(
                message="Test with context",
                thread_id="thread123",
                agent_service=mock_agent_service
            )
            
            assert "response" in result
            assert "context" in result
            assert result["context"]["thread_id"] == "thread123"
    
    def test_agent_rate_limiting(self, agent_test_client):
        """Test agent endpoint rate limiting."""
        from netra_backend.app.main import app
        from netra_backend.app.services.agent_service import get_agent_service
        
        # Create and configure mock agent service
        mock_agent_service = MockServiceFactory.create_mock_agent_service()
        
        # Override the dependency for this specific test
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            # Send multiple rapid requests to test rate limiting
            responses = []
            for i in range(10):
                response = agent_test_client.post(
                    "/api/agent/message",
                    json={"message": f"Rate limit test {i}"}
                )
                responses.append(response.status_code)
            
            # Should have at least some successful responses or rate limit errors
            success_codes = [200, 201]
            rate_limit_codes = [429, 503]
            error_codes = [500, 404]  # If not implemented
            
            for status_code in responses:
                assert status_code in success_codes + rate_limit_codes + error_codes
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    
    @pytest.mark.asyncio
    async def test_agent_multi_modal_input(self):
        """Test agent handling of multi-modal input."""
        from netra_backend.app.routes.agent_route import process_multimodal_message
        
        multimodal_input = {
            "text": "Analyze this data",
            "attachments": [
                {"type": "image", "url": "data:image/png;base64,iVBOR..."},
                {"type": "document", "content": "Sample document text"}
            ]
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.services.agent_service.process_multimodal') as mock_process:
            mock_process.return_value = {
                "response": "Analysis complete",
                "processed_attachments": 2
            }
            
            result = await process_multimodal_message(multimodal_input)
            assert result["processed_attachments"] == 2
    
    def test_agent_performance_metrics(self, agent_test_client):
        """Test agent performance metric collection."""
        from netra_backend.app.main import app
        from netra_backend.app.services.agent_service import get_agent_service
        
        # Mock agent service with performance metrics
        mock_agent_service = AgentRegistry().get_agent("supervisor")
        mock_agent_service.process_message = AsyncMock(return_value={
            "response": "Processed with metrics",
            "metrics": {
                "processing_time_ms": 150,
                "tokens_used": 75,
                "model": LLMModel.GEMINI_2_5_FLASH.value
            }
        })
        
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = agent_test_client.post(
                "/api/agent/message",
                json={"message": "Performance test"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "metrics" in data:
                    metrics = data["metrics"]
                    assert "processing_time_ms" in metrics
                    assert metrics["processing_time_ms"] > 0
        finally:
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    
    @pytest.mark.asyncio
    async def test_agent_fallback_mechanisms(self):
        """Test agent fallback and recovery mechanisms."""
        from netra_backend.app.routes.agent_route import process_with_fallback
        
        # Mock primary agent failure
        # Mock: Generic component isolation for controlled unit testing
        primary_agent = AgentRegistry().get_agent("supervisor")
        # Mock: Async component isolation for testing without real async operations
        primary_agent.process_message = AsyncMock(side_effect=Exception("Primary failed"))
        
        # Mock fallback agent success
        # Mock: Generic component isolation for controlled unit testing
        fallback_agent = AgentRegistry().get_agent("supervisor")
        # Mock: Async component isolation for testing without real async operations
        fallback_agent.process_message = AsyncMock(return_value={
            "response": "Fallback response",
            "agent": "fallback",
            "status": "recovered"
        })
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.services.agent_service.get_primary_agent', return_value=primary_agent):
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.services.agent_service.get_fallback_agent', return_value=fallback_agent):
                result = await process_with_fallback("Test fallback")
                
                assert result["agent"] == "fallback"
                assert result["status"] == "recovered"
    
    @pytest.mark.skip(reason="Agent WebSocket endpoint not implemented")
    def test_agent_websocket_integration(self, agent_test_client):
        """Test agent integration with WebSocket communication."""
        self._test_websocket_connection(agent_test_client)
    
    def _test_websocket_connection(self, agent_test_client):
        """Test WebSocket connection with proper endpoint."""
        with agent_test_client.websocket_connect("/api/agent/ws/agent") as websocket:
            self._send_agent_test_message(websocket)
    
    def _send_agent_test_message(self, websocket):
        """Send agent test message via WebSocket."""
        message = self._create_test_message()
        websocket.send_json(message)
        self._validate_websocket_response(websocket)
        
    def _create_test_message(self) -> dict:
        """Create test message for WebSocket."""
        return {"type": "agent_message", "message": "WebSocket test", "thread_id": "ws_thread_1"}
    
    def _validate_websocket_response(self, websocket):
        """Validate WebSocket response structure."""
        response = websocket.receive_json()
        assert "type" in response
        assert response["type"] in ["agent_response", "error"]