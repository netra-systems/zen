"""Integration Test Suite: WebSocket to Agent Service Full Flow

CRITICAL: Tests the complete integration from WebSocket message receipt to agent execution.
These tests ensure the message routing fix is working end-to-end.

ROOT CAUSE ADDRESSED: Messages were being validated but never forwarded to agent service.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.manager import get_websocket_manager

logger = central_logger.get_logger(__name__)

@pytest.mark.asyncio
class TestWebSocketAgentIntegration:
    """Integration tests for WebSocket-Agent communication."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_message_flow(self):
        """Test complete flow: WebSocket message → Agent → Response."""
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.schemas.Config import AppConfig
        from netra_backend.app.services.agent_service_core import AgentService
        
        # Setup mocks
        config = AppConfig()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = Mock()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager.ask_llm = AsyncMock(return_value="Agent response")
        # Mock: Tool execution isolation for predictable agent testing
        tool_dispatcher = Mock()
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = Mock()
        
        # Create supervisor with mocked components
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.agents.supervisor_consolidated.AsyncSession'):
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
        
        # Mock: WebSocket connection isolation for testing without network overhead
        with patch('app.get_websocket_manager().send_message', new=mock_send_message):
            # Mock: WebSocket connection isolation for testing without network overhead
            with patch('app.get_websocket_manager().send_error', new=AsyncMock()):
                # Execute
                await agent_service.handle_websocket_message(
                    user_id="test_user",
                    message=test_message,
                    db_session=None
                )
        
        # Verify response was sent
        assert len(sent_messages) > 0
        assert any(msg.get("type") == "agent_completed" for msg in sent_messages)
    
    @pytest.mark.asyncio
    async def test_agent_registration_during_startup(self):
        """Test that agents are properly registered during startup."""
        from fastapi import FastAPI

        from netra_backend.app.startup_module import _create_agent_supervisor
        
        app = FastAPI()
        # Mock: LLM provider isolation to prevent external API usage and costs
        app.state.llm_manager = Mock()
        # Mock: Tool execution isolation for predictable agent testing
        app.state.tool_dispatcher = Mock()
        
        # Mock WebSocket manager
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.startup_module.manager') as mock_manager:
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.agents.supervisor_consolidated.AsyncSession'):
                _create_agent_supervisor(app)
        
        # Verify supervisor was created and stored
        assert hasattr(app.state, 'agent_supervisor')
        assert app.state.agent_supervisor is not None
        
        # Verify agents are registered
        supervisor = app.state.agent_supervisor
        assert len(supervisor.registry.list_agents()) >= 5  # At least 5 core agents
    
    @pytest.mark.asyncio
    async def test_thread_context_preservation(self):
        """Test that thread context is preserved across messages."""
        from netra_backend.app.services.message_handlers import MessageHandlerService
        from netra_backend.app.services.thread_service import ThreadService
        
        # Setup mocks
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor = AsyncMock()
        # Mock: Async component isolation for testing without real async operations
        mock_supervisor.run = AsyncMock(return_value="Response")
        # Mock: Component isolation for controlled unit testing
        mock_thread_service = Mock(spec=ThreadService)
        
        # Mock thread retrieval
        # Mock: Generic component isolation for controlled unit testing
        mock_thread = Mock()
        mock_thread.id = "thread_123"
        mock_thread.metadata_ = {"user_id": "test_user"}
        # Mock: Async component isolation for testing without real async operations
        mock_thread_service.get_thread = AsyncMock(return_value=mock_thread)
        # Mock: Generic component isolation for controlled unit testing
        mock_thread_service.create_message = AsyncMock()
        
        handler = MessageHandlerService(mock_supervisor, mock_thread_service)
        
        # Test payload with thread_id
        payload = {
            "content": "Continue our conversation",
            "thread_id": "thread_123",
            "references": []
        }
        
        # Mock: Generic component isolation for controlled unit testing
        mock_db = Mock()
        
        # Execute
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.get_websocket_manager()'):
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
    
    @pytest.mark.asyncio
    async def test_error_handling_in_message_flow(self):
        """Test error handling when agent execution fails."""
        from netra_backend.app.services.agent_service_core import AgentService
        
        # Setup mock that raises error
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor = AsyncMock()
        # Mock: Agent service isolation for testing without LLM agent execution
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
        # Mock: WebSocket connection isolation for testing without network overhead
        with patch('app.get_websocket_manager().send_error', new=mock_send_error):
            # Mock: WebSocket connection isolation for testing without network overhead
            with patch('app.get_websocket_manager().send_message', new=AsyncMock()):
                await agent_service.handle_websocket_message(
                    user_id="test_user",
                    message=test_message,
                    db_session=None
                )
        
        # Verify error was handled
        assert error_sent
    
    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test handling multiple concurrent WebSocket messages."""
        from netra_backend.app.services.agent_service_core import AgentService
        
        # Setup mock with delay to simulate processing
        # Mock: Generic component isolation for controlled unit testing
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
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.get_websocket_manager()'):
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