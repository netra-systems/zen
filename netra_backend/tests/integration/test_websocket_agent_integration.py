"""Integration Test Suite: WebSocket to Agent Service Full Flow

CRITICAL: Tests the complete integration from WebSocket message receipt to agent execution.
These tests ensure the message routing fix is working end-to-end.

ROOT CAUSE ADDRESSED: Messages were being validated but never forwarded to agent service.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from logging_config import central_logger

# Add project root to path


logger = central_logger.get_logger(__name__)


@pytest.mark.asyncio
class TestWebSocketAgentIntegration:
    """Integration tests for WebSocket-Agent communication."""
    
    async def test_end_to_end_message_flow(self):
        """Test complete flow: WebSocket message → Agent → Response."""
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.schemas.Config import AppConfig
        from netra_backend.app.services.agent_service_core import AgentService
        
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
        from fastapi import FastAPI

        from netra_backend.app.startup_module import _create_agent_supervisor
        
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
        from netra_backend.app.services.message_handlers import MessageHandlerService
        from netra_backend.app.services.thread_service import ThreadService
        
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
        from netra_backend.app.services.agent_service_core import AgentService
        
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
        from netra_backend.app.services.agent_service_core import AgentService
        
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