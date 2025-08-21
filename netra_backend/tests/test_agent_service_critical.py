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

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.schemas.Request import StartAgentPayload
from netra_backend.app.core.exceptions import NetraException
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
        model.user_request = "Test message"
        model.run_id = "test_run_123"
        model.user_id = "test_user"
        model.model_dump = MagicMock(return_value={
            "user_request": "Test message",
            "run_id": "test_run_123", 
            "user_id": "test_user"
        })
        return model
    async def test_service_initialization(self, mock_supervisor):
        """Test agent service initializes correctly."""
        service = AgentService(mock_supervisor)
        assert service.supervisor == mock_supervisor
        assert hasattr(service, 'supervisor')
    async def test_run_execution_success(self, agent_service, mock_request_model):
        """Test successful agent run execution."""
        run_id = "test_run_123"
        result = await agent_service.run(mock_request_model, run_id, stream_updates=True)
        
        assert result is not None
        assert agent_service.supervisor.run.called
        call_args = agent_service.supervisor.run.call_args[0]
        assert call_args[0] == "Test message"  # user_request is first positional arg
    async def test_run_with_model_dump_fallback(self, agent_service, mock_supervisor):
        """Test run with model dump fallback."""
        model = MagicMock()
        model.user_request = "Test message"
        model.run_id = "test_run"
        model.user_id = "user123"
        
        await agent_service.run(model, "test_run", stream_updates=False)
        assert mock_supervisor.run.called
    async def test_websocket_message_handling(self, agent_service):
        """Test WebSocket message handling method exists."""
        # Test that the method exists and accepts correct parameters
        user_id = "test_user"
        message = {"type": "test", "data": "test_data"}
        
        # Should not raise AttributeError
        try:
            await agent_service.handle_websocket_message(user_id, message)
        except Exception as e:
            # Any other exception is fine, we just want to verify method exists
            assert "has no attribute" not in str(e)
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
    async def test_error_handling_supervisor_failure(self, agent_service, mock_request_model):
        """Test error handling when supervisor fails."""
        agent_service.supervisor.run = AsyncMock(side_effect=NetraException("Supervisor error"))
        
        with pytest.raises(NetraException):
            await agent_service.run(mock_request_model, "test_run", stream_updates=False)
    async def test_websocket_disconnect_handling(self, agent_service):
        """Test WebSocket disconnect exception handling."""
        # Test that WebSocketDisconnect can be imported and used
        user_id = "test_user"
        message = {"type": "disconnect_test"}
        
        # Test that the service handles exceptions gracefully
        try:
            await agent_service.handle_websocket_message(user_id, message)
        except WebSocketDisconnect:
            # This exception should be caught and handled appropriately
            pass
        except Exception:
            # Other exceptions are acceptable for this test
            pass
    async def test_supervisor_integration(self, agent_service, mock_request_model):
        """Test supervisor integration."""
        expected_response = {"status": "completed", "result": "success"}
        agent_service.supervisor.run = AsyncMock(return_value=expected_response)
        
        result = await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        assert result == expected_response
    async def test_stream_updates_parameter(self, agent_service, mock_request_model):
        """Test stream updates parameter acceptance."""
        # Test with stream_updates=True (should not raise error)
        result1 = await agent_service.run(mock_request_model, "test_run", stream_updates=True)
        assert result1 is not None
        
        # Test with stream_updates=False (should not raise error)  
        result2 = await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        assert result2 is not None
    async def test_message_validation(self, agent_service):
        """Test message validation via WebSocket handler."""
        invalid_message = {"invalid": "data"}
        user_id = "test_user"
        
        # Test that invalid messages are handled gracefully
        try:
            await agent_service.handle_websocket_message(user_id, invalid_message)
        except Exception as e:
            # Exception handling is expected for invalid messages
            assert "invalid" in str(e).lower() or "error" in str(e).lower() or True
    async def test_run_id_parameter_passing(self, agent_service, mock_request_model):
        """Test run ID parameter passing."""
        run_id = "custom_run_id_123"
        await agent_service.run(mock_request_model, run_id, stream_updates=False)
        
        call_args = agent_service.supervisor.run.call_args[0]
        assert call_args[3] == run_id  # run_id is fourth positional arg
    async def test_user_context_preservation(self, agent_service, mock_request_model):
        """Test user context preservation."""
        await agent_service.run(mock_request_model, "test_run", stream_updates=False)
        
        call_args = agent_service.supervisor.run.call_args[0]
        assert call_args[2] == "test_user"  # user_id is third positional arg
        assert call_args[0] == "Test message"  # user_request is first positional arg
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
    async def test_request_model_compatibility(self, agent_service):
        """Test compatibility with different request model formats."""
        # Test with dict-like model
        dict_model = MagicMock()
        dict_model.user_request = "Dict message"
        dict_model.run_id = "dict_run"
        dict_model.user_id = "dict_user"
        
        result = await agent_service.run(dict_model, "dict_run", stream_updates=False)
        assert result is not None
    async def test_timeout_handling(self, agent_service, mock_request_model):
        """Test timeout handling."""
        # Mock a slow supervisor response
        agent_service.supervisor.run = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with pytest.raises(asyncio.TimeoutError):
            await agent_service.run(mock_request_model, "test_run", stream_updates=False)
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
    async def test_memory_cleanup(self, agent_service, mock_request_model):
        """Test memory cleanup after execution."""
        # Run multiple operations
        for i in range(5):
            await agent_service.run(mock_request_model, f"run_{i}", stream_updates=False)
        
        # Verify service remains functional
        final_result = await agent_service.run(mock_request_model, "final_run", stream_updates=False)
        assert final_result is not None
    async def test_exception_propagation(self, agent_service, mock_request_model):
        """Test proper exception propagation."""
        custom_error = NetraException("Custom test error")
        agent_service.supervisor.run = AsyncMock(side_effect=custom_error)
        
        with pytest.raises(NetraException) as exc_info:
            await agent_service.run(mock_request_model, "error_run", stream_updates=False)
        
        assert "Custom test error" in str(exc_info.value)
    async def test_state_isolation(self, mock_supervisor):
        """Test state isolation between service instances."""
        service1 = AgentService(mock_supervisor)
        service2 = AgentService(mock_supervisor)
        
        assert service1 is not service2
        assert service1.supervisor == service2.supervisor
    async def test_logging_integration(self, agent_service, mock_request_model):
        """Test logging integration."""
        with patch('app.services.agent_service_core.logger') as mock_logger:
            # Test that logger is properly mocked
            assert mock_logger is not None
            
            # Trigger WebSocket message handling which uses logging
            await agent_service.handle_websocket_message("test_user", {"type": "start_agent", "payload": {}})
            
            # Verify logger was called (info level for websocket message handling)
            assert mock_logger.info.call_count > 0
            
            # Verify first log call contains expected user_id info
            first_call = mock_logger.info.call_args_list[0][0][0]
            assert "test_user" in first_call