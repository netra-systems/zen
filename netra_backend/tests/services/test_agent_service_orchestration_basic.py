"""
Basic agent service orchestration tests.

Tests core AgentService functionality including initialization,
execution, and WebSocket message handling.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.agent_service import AgentService
from tests.helpers.test_agent_orchestration_pytest_fixtures import (
    mock_supervisor, agent_service, mock_message_handler
)
from tests.helpers.test_agent_orchestration_assertions import (
    assert_agent_service_initialized, assert_agent_run_completed,
    assert_supervisor_called_correctly, assert_message_handler_called,
    assert_websocket_message_parsed, assert_concurrent_execution_successful,
    setup_mock_request_model, setup_mock_request_model_with_dump,
    setup_websocket_message, setup_concurrent_tasks
)
from starlette.websockets import WebSocketDisconnect


class TestAgentServiceOrchestration:
    """Test agent service orchestration functionality."""
    async def test_agent_service_initialization(self, mock_supervisor):
        """Test agent service initialization."""
        service = AgentService(mock_supervisor)
        assert_agent_service_initialized(service, mock_supervisor)
    async def test_agent_run_execution(self, agent_service, mock_supervisor):
        """Test agent run execution."""
        request_model = setup_mock_request_model("Test user request", "test_run_123", "test_user")
        run_id = "test_run_123"
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        result = await agent_service.run(request_model, run_id, stream_updates=True)
        
        assert_agent_run_completed(result)
        assert_supervisor_called_correctly(mock_supervisor, "Test user request", "test_run_123", "test_user", run_id)
    async def test_agent_run_with_model_dump_fallback(self, agent_service, mock_supervisor):
        """Test agent run with model dump fallback."""
        request_model = setup_mock_request_model_with_dump({'query': 'test query'}, "test_run_456", "test_user2")
        run_id = "test_run_456"
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        result = await agent_service.run(request_model, run_id)
        
        assert_agent_run_completed(result)
        assert_supervisor_called_correctly(mock_supervisor, "{'query': 'test query'}", "test_run_456", "test_user2", run_id)
    async def test_websocket_message_handling_start_agent(self, agent_service):
        """Test WebSocket message handling for start_agent."""
        user_id = "user123"
        message = setup_websocket_message("start_agent", {"query": "start analysis"})
        agent_service.message_handler.handle_start_agent = AsyncMock()
        
        await agent_service.handle_websocket_message(user_id, message)
        
        assert_message_handler_called(
            agent_service.message_handler, "handle_start_agent",
            (user_id, {"query": "start analysis"}, None)
        )
    async def test_websocket_message_handling_user_message(self, agent_service):
        """Test WebSocket message handling for user_message."""
        user_id = "user456"
        message = setup_websocket_message("user_message", {"content": "Hello agent"})
        agent_service.message_handler.handle_user_message = AsyncMock()
        
        await agent_service.handle_websocket_message(user_id, message)
        
        assert_message_handler_called(
            agent_service.message_handler, "handle_user_message",
            (user_id, {"content": "Hello agent"}, None)
        )
    async def test_websocket_message_handling_stop_agent(self, agent_service):
        """Test WebSocket message handling for stop_agent."""
        user_id = "user999"
        message = setup_websocket_message("stop_agent", {})
        agent_service.message_handler.handle_stop_agent = AsyncMock()
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_stop_agent.assert_called_once_with(user_id)
    async def test_websocket_message_handling_unknown_type(self, agent_service):
        """Test WebSocket message handling for unknown message type."""
        user_id = "user_unknown"
        message = setup_websocket_message("unknown_message_type", {})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle gracefully without calling any specific handler
    async def test_websocket_disconnect_handling(self, agent_service):
        """Test handling of WebSocket disconnect."""
        user_id = "user_disconnect"
        message = setup_websocket_message("start_agent", {})
        
        agent_service.message_handler.handle_start_agent = AsyncMock(
            side_effect=WebSocketDisconnect()
        )
        
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle disconnect gracefully
    async def test_concurrent_agent_execution(self, agent_service, mock_supervisor):
        """Test concurrent agent execution."""
        num_concurrent = 5
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        tasks = setup_concurrent_tasks(agent_service, num_concurrent)
        results = await asyncio.gather(*tasks)
        
        assert_concurrent_execution_successful(results, num_concurrent)
        assert mock_supervisor.run.call_count == num_concurrent
    async def test_message_parsing_string_input(self, agent_service):
        """Test message parsing with string input."""
        json_string = '{"type": "start_agent", "payload": {"query": "test"}}'
        parsed = agent_service._parse_message(json_string)
        
        assert_websocket_message_parsed(parsed, "start_agent", {"query": "test"})
    async def test_message_parsing_dict_input(self, agent_service):
        """Test message parsing with dict input."""
        dict_message = {"type": "user_message", "payload": {"content": "hello"}}
        parsed = agent_service._parse_message(dict_message)
        
        assert_websocket_message_parsed(parsed, "user_message", {"content": "hello"})


class TestAgentServiceBasic:
    """Basic agent service tests with complex RequestModel."""
    async def test_run_agent_with_request_model(self):
        """Test basic run method with RequestModel."""
        mock_supervisor = MagicMock()
        mock_supervisor.run = AsyncMock(return_value={"status": "started"})
        agent_service = AgentService(mock_supervisor)
        
        request_model = self._create_complex_request_model()
        result = await agent_service.run(request_model, "test_run", False)
        
        assert result == {"status": "started"}
        expected_user_request = str(request_model.model_dump())
        assert_supervisor_called_correctly(mock_supervisor, expected_user_request, "test_req", "test_user", "test_run")
    
    def _create_complex_request_model(self):
        """Create complex RequestModel for testing."""
        from app.schemas import Settings, Workload, DataSource, TimeRange, RequestModel
        
        settings = Settings(debug_mode=True)
        workload = self._create_test_workload()
        
        return RequestModel(
            id="test_req",
            user_id="test_user", 
            query="test query",
            workloads=[workload]
        )
    
    def _create_test_workload(self):
        """Create test workload for RequestModel."""
        from app.schemas import Workload, DataSource, TimeRange
        
        return Workload(
            run_id="test_run",
            query="test_query",
            data_source=DataSource(source_table="test_table").model_dump(),
            time_range=TimeRange(
                start_time="2024-01-01T00:00:00Z", 
                end_time="2024-01-02T00:00:00Z"
            ).model_dump()
        )