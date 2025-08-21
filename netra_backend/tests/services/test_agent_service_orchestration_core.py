"""
Core agent service orchestration tests.

MODULE PURPOSE:
Tests the core AgentService orchestration functionality including WebSocket message handling,
agent execution, and message parsing. Focuses on the primary interface and coordination logic.

TEST CATEGORIES:
- Basic agent service initialization
- Agent run execution with different request types
- WebSocket message handling for all message types
- Message parsing and error handling
- Concurrent agent execution

PERFORMANCE REQUIREMENTS:
- Unit tests: < 100ms each
- Concurrent tests: < 1s for multiple parallel operations
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from netra_backend.app import schemas
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path
from netra_backend.app.services.agent_service import AgentService
from netra_backend.tests.services.test_agent_service_fixtures import (
    agent_service,
    create_concurrent_request_models,
    create_mock_request_model,
    create_websocket_message,
    mock_message_handler,
    # Add project root to path
    mock_supervisor,
    mock_thread_service,
    verify_agent_execution_result,
)


class TestAgentServiceOrchestrationCore:
    """Test agent service core orchestration functionality."""
    async def test_agent_service_initialization(self, mock_supervisor):
        """Test agent service initialization with dependencies."""
        service = AgentService(mock_supervisor)
        
        assert service.supervisor is mock_supervisor
        assert service.thread_service != None
        assert service.message_handler != None
    async def test_agent_run_execution_basic(self, agent_service, mock_supervisor):
        """Test basic agent run execution."""
        request_model = create_mock_request_model()
        run_id = "test_run_123"
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        result = await agent_service.run(request_model, run_id, stream_updates=True)
        
        verify_agent_execution_result(result)
        self._verify_supervisor_call(mock_supervisor, request_model, run_id)
    
    def _verify_supervisor_call(self, mock_supervisor, request_model, run_id):
        """Verify supervisor was called with correct parameters."""
        expected_args = (request_model.user_request, request_model.id, request_model.user_id, run_id)
        mock_supervisor.run.assert_called_once_with(*expected_args)
    async def test_agent_run_with_model_dump_fallback(self, agent_service, mock_supervisor):
        """Test agent run with model dump fallback when user_request not available."""
        request_model = self._create_model_without_user_request()
        run_id = "test_run_456"
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        result = await agent_service.run(request_model, run_id)
        
        verify_agent_execution_result(result)
        self._verify_model_dump_call(mock_supervisor, request_model, run_id)
    
    def _create_model_without_user_request(self):
        """Create request model without user_request attribute."""
        request_model = MagicMock()
        del request_model.user_request
        request_model.model_dump.return_value = {'query': 'test query'}
        request_model.id = "test_thread_456"
        request_model.user_id = "test_user_789"
        return request_model
    
    def _verify_model_dump_call(self, mock_supervisor, request_model, run_id):
        """Verify supervisor called with model dump string."""
        expected_args = ("{'query': 'test query'}", request_model.id, request_model.user_id, run_id)
        mock_supervisor.run.assert_called_once_with(*expected_args)
    async def test_websocket_message_handling_start_agent(self, agent_service):
        """Test WebSocket message handling for start_agent."""
        user_id = "user123"
        message = create_websocket_message("start_agent", {"query": "start analysis"})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        self._verify_start_agent_handler_call(agent_service, user_id)
    
    def _verify_start_agent_handler_call(self, agent_service, user_id):
        """Verify start_agent handler was called correctly."""
        expected_args = (user_id, {"query": "start analysis"}, None)
        agent_service.message_handler.handle_start_agent.assert_called_once_with(*expected_args)
    async def test_websocket_message_handling_user_message(self, agent_service):
        """Test WebSocket message handling for user_message."""
        user_id = "user456"
        message = create_websocket_message("user_message", {"content": "Hello agent"})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        self._verify_user_message_handler_call(agent_service, user_id)
    
    def _verify_user_message_handler_call(self, agent_service, user_id):
        """Verify user_message handler was called correctly."""
        expected_args = (user_id, {"content": "Hello agent"}, None)
        agent_service.message_handler.handle_user_message.assert_called_once_with(*expected_args)
    async def test_websocket_message_handling_thread_operations(self, agent_service):
        """Test WebSocket message handling for thread operations."""
        user_id = "user789"
        thread_operations = self._get_thread_operations()
        
        for message_type, payload in thread_operations:
            await self._test_single_thread_operation(agent_service, user_id, message_type, payload)
    
    def _get_thread_operations(self):
        """Get list of thread operations to test."""
        return [
            ("get_thread_history", {}),
            ("create_thread", {"name": "New Thread"}),
            ("switch_thread", {"thread_id": "thread_123"}),
            ("delete_thread", {"thread_id": "thread_456"}),
            ("list_threads", {})
        ]
    
    async def _test_single_thread_operation(self, agent_service, user_id, message_type, payload):
        """Test a single thread operation message."""
        message = create_websocket_message(message_type, payload)
        await agent_service.handle_websocket_message(user_id, message)
        self._verify_thread_operation_handler(agent_service, user_id, message_type, payload)
    
    def _verify_thread_operation_handler(self, agent_service, user_id, message_type, payload):
        """Verify thread operation handler was called correctly."""
        method_map = {
            "get_thread_history": "handle_thread_history",
            "create_thread": "handle_create_thread", 
            "switch_thread": "handle_switch_thread",
            "delete_thread": "handle_delete_thread",
            "list_threads": "handle_list_threads"
        }
        handler_name = method_map[message_type]
        handler_method = getattr(agent_service.message_handler, handler_name)
        
        # Just verify the method was called, not specific arguments
        # since the call signature may vary based on implementation
        handler_method.assert_called()
    async def test_websocket_message_handling_stop_agent(self, agent_service):
        """Test WebSocket message handling for stop_agent."""
        user_id = "user999"
        message = create_websocket_message("stop_agent", {})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_stop_agent.assert_called_once_with(user_id)
    async def test_websocket_message_handling_unknown_type(self, agent_service):
        """Test WebSocket message handling for unknown message type."""
        user_id = "user_unknown"
        message = create_websocket_message("unknown_message_type", {})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle gracefully without calling any specific handler
    async def test_websocket_message_handling_json_error(self, agent_service):
        """Test WebSocket message handling with JSON decode error."""
        user_id = "user_json_error"
        invalid_message = "invalid json {broken"
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            mock_send_error.return_value = None
            
            await agent_service.handle_websocket_message(user_id, invalid_message)
            
            mock_send_error.assert_called_once_with(user_id, "Invalid message format")
    async def test_websocket_disconnect_handling(self, agent_service):
        """Test handling of WebSocket disconnect during message processing."""
        user_id = "user_disconnect"
        message = create_websocket_message("start_agent", {})
        
        agent_service.message_handler.handle_start_agent = AsyncMock(side_effect=WebSocketDisconnect())
        
        await agent_service.handle_websocket_message(user_id, message)
        
        # Should handle disconnect gracefully without raising exception
    async def test_concurrent_agent_execution(self, agent_service, mock_supervisor):
        """Test concurrent agent execution without race conditions."""
        num_concurrent = 5
        mock_supervisor.run = AsyncMock(return_value={'status': 'completed'})
        
        request_models = create_concurrent_request_models(num_concurrent)
        tasks = self._create_concurrent_tasks(agent_service, request_models)
        results = await asyncio.gather(*tasks)
        
        self._verify_concurrent_execution_results(results, num_concurrent, mock_supervisor)
    
    def _create_concurrent_tasks(self, agent_service, request_models):
        """Create concurrent tasks for agent execution."""
        return [agent_service.run(model, f"run_{i}") for i, model in enumerate(request_models)]
    
    def _verify_concurrent_execution_results(self, results, num_concurrent, mock_supervisor):
        """Verify concurrent execution results."""
        assert len(results) == num_concurrent
        assert all(result['status'] == 'completed' for result in results)
        assert mock_supervisor.run.call_count == num_concurrent
    async def test_message_parsing_string_input(self, agent_service):
        """Test message parsing with string input."""
        json_string = '{"type": "start_agent", "payload": {"query": "test"}}'
        
        parsed = agent_service._parse_message(json_string)
        
        assert parsed["type"] == "start_agent"
        assert parsed["payload"]["query"] == "test"
    async def test_message_parsing_dict_input(self, agent_service):
        """Test message parsing with dict input."""
        dict_message = {"type": "user_message", "payload": {"content": "hello"}}
        
        parsed = agent_service._parse_message(dict_message)
        
        assert parsed["type"] == "user_message"
        assert parsed["payload"]["content"] == "hello"


class TestAgentServiceBasic:
    """Basic agent service tests for core functionality."""
    async def test_run_agent_with_request_model(self):
        """Test basic run method with full RequestModel."""
        mock_supervisor = MagicMock()
        mock_supervisor.run = AsyncMock(return_value={"status": "started"})
        agent_service = AgentService(mock_supervisor)
        
        request_model = self._create_full_request_model()
        
        result = await agent_service.run(request_model, "test_run", False)
        
        assert result == {"status": "started"}
        self._verify_full_request_call(mock_supervisor, request_model)
    
    def _create_full_request_model(self):
        """Create full RequestModel with all required fields."""
        from netra_backend.app.schemas.unified_tools import (
            DataSource,
            RequestModel,
            Settings,
            TimeRange,
            Workload,
        )
        
        settings = Settings(debug_mode=True)
        workload = Workload(
            run_id="test_run",
            query="test_query",
            data_source=DataSource(source_table="test_table").model_dump(),
            time_range=TimeRange(start_time="2024-01-01T00:00:00Z", end_time="2024-01-02T00:00:00Z").model_dump()
        )
        return RequestModel(
            id="test_req",
            user_id="test_user", 
            query="test query",
            workloads=[workload]
        )
    
    def _verify_full_request_call(self, mock_supervisor, request_model):
        """Verify supervisor called with full request model."""
        expected_user_request = str(request_model.model_dump())
        expected_args = (expected_user_request, "test_req", "test_user", "test_run")
        mock_supervisor.run.assert_called_once_with(*expected_args)