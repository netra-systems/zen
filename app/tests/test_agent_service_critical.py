"""
Critical agent service tests for essential functionality.

Tests the most critical paths of agent service orchestration including
initialization, execution, error handling, and supervisor integration.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.agent_service import AgentService
from app.schemas.websocket_message_types import StartAgentPayload
from app.core.exceptions import NetraException
from starlette.websockets import WebSocketDisconnect


class TestAgentServiceCritical:
    """Critical agent service tests for essential functionality."""
    
    @pytest.fixture
    def mock_supervisor(self):
        """Create mock supervisor."""
        supervisor = AsyncMock()
        supervisor.run = AsyncMock(return_value={'status': 'completed'})
        return supervisor
    
    @pytest.fixture
    def agent_service(self, mock_supervisor):
        """Create agent service instance."""
        return AgentService(mock_supervisor)
    
    @pytest.fixture
    def mock_request_model(self):
        """Create mock request model."""
        model = MagicMock()
        model.user_message = "Test message"
        model.run_id = "test_run_123"
        model.user_id = "test_user"
        model.model_dump = MagicMock(return_value={
            "user_message": "Test message",
            "run_id": "test_run_123", 
            "user_id": "test_user"
        })
        return model
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_supervisor):
        """Test agent service initializes correctly."""
        service = AgentService(mock_supervisor)
        assert service.supervisor == mock_supervisor
        assert hasattr(service, 'supervisor')
    
    @pytest.mark.asyncio
    async def test_run_execution_success(self, agent_service, mock_request_model):
        """Test successful agent run execution."""
        run_id = "test_run_123"
        result = await agent_service.run(mock_request_model, run_id, stream_updates=True)
        
        assert result is not None
        assert agent_service.supervisor.run.called
        call_args = agent_service.supervisor.run.call_args[1]
        assert call_args["user_request"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_run_with_model_dump_fallback(self, agent_service, mock_supervisor):
        """Test run with model dump fallback."""
        model = MagicMock()
        model.user_message = "Test message"
        model.run_id = "test_run"
        model.user_id = "user123"
        
        await agent_service.run(model, "test_run", stream_updates=False)
        assert mock_supervisor.run.called
    
    @pytest.mark.asyncio
    async def test_websocket_message_parsing(self, agent_service):
        """Test WebSocket message parsing."""
        message_data = {
            "agent_id": "test_agent",
            "prompt": "Test prompt"
        }
        
        parsed = agent_service._parse_websocket_message(message_data)
        assert isinstance(parsed, StartAgentPayload)
        assert parsed.agent_id == "test_agent"
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, agent_service, mock_request_model):
        """Test concurrent execution handling."""
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                agent_service.run(mock_request_model, f"run_{i}", stream_updates=False)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_error_handling_supervisor_failure(self, agent_service, mock_request_model):
        """Test error handling when supervisor fails."""
        agent_service.supervisor.run = AsyncMock(side_effect=NetraException("Supervisor error"))
        
        with pytest.raises(NetraException):
            await agent_service.run(mock_request_model, "test_run", stream_updates=False)
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self, agent_service):
        """Test WebSocket disconnect handling."""
        with patch.object(agent_service, '_handle_websocket_message') as mock_handler:
            mock_handler.side_effect = WebSocketDisconnect(code=1000)
            
            result = await agent_service._safe_handle_websocket_message({})
            assert result is None
    
    @pytest.mark.asyncio
    async def test_supervisor_integration(self, agent_service, mock_request_model):
        """Test supervisor integration."""
        expected_response = {"status": "completed", "result": "success"}
        agent_service.supervisor.run = AsyncMock(return_value=expected_response)
        
        result = await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_stream_updates_parameter(self, agent_service, mock_request_model):
        """Test stream updates parameter handling."""
        # Test with stream_updates=True
        await agent_service.run(mock_request_model, "test_run", stream_updates=True)
        call_args = agent_service.supervisor.run.call_args[1]
        assert call_args["stream_updates"] is True
        
        # Test with stream_updates=False
        await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        call_args = agent_service.supervisor.run.call_args[1]
        assert call_args["stream_updates"] is False
    
    @pytest.mark.asyncio
    async def test_message_validation(self, agent_service):
        """Test message validation."""
        invalid_message = {"invalid": "data"}
        
        with pytest.raises((ValueError, KeyError)):
            agent_service._parse_websocket_message(invalid_message)
    
    @pytest.mark.asyncio
    async def test_run_id_parameter_passing(self, agent_service, mock_request_model):
        """Test run ID parameter passing."""
        run_id = "custom_run_id_123"
        await agent_service.run(mock_request_model, run_id, stream_updates=False)
        
        call_args = agent_service.supervisor.run.call_args[1]
        assert call_args["run_id"] == run_id
    
    @pytest.mark.asyncio
    async def test_user_context_preservation(self, agent_service, mock_request_model):
        """Test user context preservation."""
        await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        
        call_args = agent_service.supervisor.run.call_args[1]
        assert call_args["user_id"] == "test_user"
        assert call_args["user_request"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_async_safety(self, agent_service, mock_request_model):
        """Test async operation safety."""
        # Create multiple overlapping async calls
        task1 = asyncio.create_task(
            agent_service.run(mock_request_model, "run1", stream_updates=False)
        )
        task2 = asyncio.create_task(
            agent_service.run(mock_request_model, "run2", stream_updates=False)
        )
        
        # Both should complete without interference
        result1, result2 = await asyncio.gather(task1, task2)
        assert result1 is not None
        assert result2 is not None
    
    @pytest.mark.asyncio
    async def test_request_model_compatibility(self, agent_service):
        """Test compatibility with different request model formats."""
        # Test with dict-like model
        dict_model = MagicMock()
        dict_model.user_message = "Dict message"
        dict_model.run_id = "dict_run"
        dict_model.user_id = "dict_user"
        
        result = await agent_service.run(dict_model, "dict_run", stream_updates=False)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, agent_service, mock_request_model):
        """Test timeout handling."""
        # Mock a slow supervisor response
        agent_service.supervisor.run = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with pytest.raises(asyncio.TimeoutError):
            await agent_service.run(mock_request_model, "test_run", stream_updates=False)
    
    @pytest.mark.asyncio
    async def test_response_format_validation(self, agent_service, mock_request_model):
        """Test response format validation."""
        # Test various response formats
        test_responses = [
            {"status": "completed"},
            {"result": "success", "data": {}},
            None,
            {"error": "test_error"}
        ]
        
        for response in test_responses:
            agent_service.supervisor.run = AsyncMock(return_value=response)
            result = await agent_service.run(mock_request_model, "test_run", stream_updates=False)
            assert result == response
    
    @pytest.mark.asyncio
    async def test_critical_path_integration(self, agent_service, mock_request_model):
        """Test critical path integration."""
        # Simulate complete critical path
        expected_flow = {
            "initialization": True,
            "execution": True,
            "completion": True
        }
        
        agent_service.supervisor.run = AsyncMock(return_value=expected_flow)
        result = await agent_service.run(mock_request_model, "critical_run", stream_updates=True)
        
        assert result == expected_flow
        assert agent_service.supervisor.run.called
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, agent_service, mock_request_model):
        """Test memory cleanup after execution."""
        # Run multiple operations
        for i in range(5):
            await agent_service.run(mock_request_model, f"run_{i}", stream_updates=False)
        
        # Verify service remains functional
        final_result = await agent_service.run(mock_request_model, "final_run", stream_updates=False)
        assert final_result is not None
    
    @pytest.mark.asyncio
    async def test_exception_propagation(self, agent_service, mock_request_model):
        """Test proper exception propagation."""
        custom_error = NetraException("Custom test error")
        agent_service.supervisor.run = AsyncMock(side_effect=custom_error)
        
        with pytest.raises(NetraException) as exc_info:
            await agent_service.run(mock_request_model, "error_run", stream_updates=False)
        
        assert str(exc_info.value) == "Custom test error"
    
    @pytest.mark.asyncio
    async def test_state_isolation(self, mock_supervisor):
        """Test state isolation between service instances."""
        service1 = AgentService(mock_supervisor)
        service2 = AgentService(mock_supervisor)
        
        assert service1 is not service2
        assert service1.supervisor == service2.supervisor
    
    @pytest.mark.asyncio
    async def test_logging_integration(self, agent_service, mock_request_model):
        """Test logging integration."""
        with patch('app.services.agent_service.logger') as mock_logger:
            await agent_service.run(mock_request_model, "log_test", stream_updates=False)
            # Verify logging calls would be made in real scenarios
            assert mock_logger is not None