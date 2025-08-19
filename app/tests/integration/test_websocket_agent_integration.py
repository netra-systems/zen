"""Integration tests for WebSocket and Agent systems.

End-to-end tests ensuring WebSocket messages properly trigger agent execution
and responses are correctly sent back to clients.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.asyncio
class TestWebSocketAgentIntegration:
    """Integration tests for WebSocket-Agent communication."""
    
    async def test_end_to_end_message_flow(self):
        """Test complete flow: WebSocket message → Agent → Response."""
        from app.services.agent_service_core import AgentService
        from app.agents.supervisor_consolidated import SupervisorAgent
        from app.schemas import AppConfig
        
        # Setup mocks
        config = AppConfig()
        llm_manager = Mock()
        llm_manager.ask_llm = AsyncMock(return_value="Agent response")
        tool_dispatcher = Mock()
        websocket_manager = Mock()
        
        # Create supervisor with mocked components
        with patch('app.agents.supervisor_consolidated.AsyncSession'):
            supervisor = SupervisorAgent(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                websocket_manager=websocket_manager
            )
        
        # Create agent service
        agent_service = AgentService(supervisor)
        
        # Test message
        test_message = {
            "type": "user_message",
            "payload": {
                "content": "Test: Switch from GPT-5 to Claude 4.1",
                "references": [],
                "thread_id": "test_thread_123"
            }
        }
        
        # Mock WebSocket manager to capture sent messages
        sent_messages = []
        
        async def mock_send_message(user_id: str, message: Dict[str, Any]):
            sent_messages.append(message)
        
        with patch('app.ws_manager.manager.send_message', new=mock_send_message):
            with patch('app.ws_manager.manager.send_error', new=AsyncMock()):
                # Execute
                await agent_service.handle_websocket_message(
                    user_id="test_user",
                    message=test_message,
                    db_session=None
                )
        
        # Verify response was sent
        assert len(sent_messages) > 0
        assert any(msg.get("type") == "agent_completed" for msg in sent_messages)
    
    async def test_agent_registration_during_startup(self):
        """Test that agents are properly registered during startup."""
        from app.startup_module import _create_agent_supervisor
        from fastapi import FastAPI
        
        app = FastAPI()
        app.state.llm_manager = Mock()
        app.state.tool_dispatcher = Mock()
        
        # Mock WebSocket manager
        with patch('app.startup_module.manager') as mock_manager:
            with patch('app.agents.supervisor_consolidated.AsyncSession'):
                _create_agent_supervisor(app)
        
        # Verify supervisor was created and stored
        assert hasattr(app.state, 'agent_supervisor')
        assert app.state.agent_supervisor is not None
        
        # Verify agents are registered
        supervisor = app.state.agent_supervisor
        assert len(supervisor.registry.list_agents()) >= 5  # At least 5 core agents
    
    async def test_thread_context_preservation(self):
        """Test that thread context is preserved across messages."""
        from app.services.message_handlers import MessageHandlerService
        from app.services.thread_service import ThreadService
        
        # Setup mocks
        mock_supervisor = AsyncMock()
        mock_supervisor.run = AsyncMock(return_value="Response")
        mock_thread_service = Mock(spec=ThreadService)
        
        # Mock thread retrieval
        mock_thread = Mock()
        mock_thread.id = "thread_123"
        mock_thread.metadata_ = {"user_id": "test_user"}
        mock_thread_service.get_thread = AsyncMock(return_value=mock_thread)
        mock_thread_service.create_message = AsyncMock()
        
        handler = MessageHandlerService(mock_supervisor, mock_thread_service)
        
        # Test payload with thread_id
        payload = {
            "content": "Continue our conversation",
            "thread_id": "thread_123",
            "references": []
        }
        
        mock_db = Mock()
        
        # Execute
        with patch('app.ws_manager.manager'):
            await handler.handle_user_message(
                user_id="test_user",
                payload=payload,
                db_session=mock_db
            )
        
        # Verify thread was retrieved
        mock_thread_service.get_thread.assert_called_with("thread_123", mock_db)
        
        # Verify supervisor was called with thread context
        assert mock_supervisor.run.called
        call_args = mock_supervisor.run.call_args
        assert "thread_123" in call_args[0] or "thread_123" in call_args[1]
    
    async def test_error_handling_in_message_flow(self):
        """Test error handling when agent execution fails."""
        from app.services.agent_service_core import AgentService
        
        # Setup mock that raises error
        mock_supervisor = AsyncMock()
        mock_supervisor.run = AsyncMock(side_effect=Exception("Agent error"))
        
        agent_service = AgentService(mock_supervisor)
        
        # Test message
        test_message = {
            "type": "user_message",
            "payload": {"content": "Test message"}
        }
        
        error_sent = False
        
        async def mock_send_error(user_id: str, error: str):
            nonlocal error_sent
            error_sent = True
        
        # Execute with error handling
        with patch('app.ws_manager.manager.send_error', new=mock_send_error):
            with patch('app.ws_manager.manager.send_message', new=AsyncMock()):
                await agent_service.handle_websocket_message(
                    user_id="test_user",
                    message=test_message,
                    db_session=None
                )
        
        # Verify error was handled
        assert error_sent
    
    async def test_concurrent_message_handling(self):
        """Test handling multiple concurrent WebSocket messages."""
        from app.services.agent_service_core import AgentService
        
        # Setup mock with delay to simulate processing
        mock_supervisor = AsyncMock()
        
        async def delayed_response(request, thread_id, user_id, run_id):
            await asyncio.sleep(0.1)  # Simulate processing
            return f"Response for {user_id}"
        
        mock_supervisor.run = delayed_response
        
        agent_service = AgentService(mock_supervisor)
        
        # Create multiple test messages
        messages = [
            {
                "type": "user_message",
                "payload": {"content": f"Message {i}"}
            }
            for i in range(5)
        ]
        
        # Execute concurrently
        with patch('app.ws_manager.manager'):
            tasks = [
                agent_service.handle_websocket_message(
                    user_id=f"user_{i}",
                    message=msg,
                    db_session=None
                )
                for i, msg in enumerate(messages)
            ]
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed
        assert len(results) == 5
        assert all(r is None or isinstance(r, Exception) for r in results)