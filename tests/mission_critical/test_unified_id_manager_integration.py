"""
Integration tests for UnifiedIDManager in WebSocket agent flow.

Tests the complete flow from WebSocket message to agent response with ID extraction.
Ensures UnifiedIDManager works correctly in production scenarios.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestUnifiedIDManagerIntegration:
    """Test UnifiedIDManager integration in WebSocket agent flow."""
    
    @pytest.fixture
    async def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = AsyncMock()
        manager.send_error = AsyncMock()
        manager.send_message = AsyncMock()
        manager.get_connection_id_by_websocket = MagicMock(return_value="conn_123")
        manager.update_connection_thread = MagicMock(return_value=True)
        return manager
    
    @pytest.fixture
    async def mock_supervisor(self):
        """Create mock supervisor agent."""
        supervisor = AsyncMock(spec=SupervisorAgent)
        supervisor.execute = AsyncMock(return_value="Test response")
        supervisor.agent_registry = MagicMock()
        supervisor.agent_registry.set_websocket_manager = MagicMock()
        return supervisor
    
    @pytest.fixture
    async def mock_thread_service(self):
        """Create mock thread service."""
        service = AsyncMock()
        thread = MagicMock()
        thread.id = "thread_test123"
        thread.user_id = "user_456"
        service.get_or_create_thread = AsyncMock(return_value=thread)
        service.create_message = AsyncMock()
        service.create_run = AsyncMock(return_value=MagicMock(id="run_789"))
        return service
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_unified_id_manager_extraction_in_flow(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_db_session
    ):
        """Test that UnifiedIDManager correctly extracts thread IDs in WebSocket flow."""
        
        # Test both canonical and legacy ID formats
        test_cases = [
            {
                "run_id": "thread_abc123_run_1234567890_12345678",
                "expected_thread": "abc123",
                "format": "canonical"
            },
            {
                "run_id": "run_xyz789_abcd1234",
                "expected_thread": "xyz789", 
                "format": "legacy"
            }
        ]
        
        for test_case in test_cases:
            # Test ID extraction directly
            extracted_thread_id = UnifiedIDManager.extract_thread_id(test_case["run_id"])
            assert extracted_thread_id == test_case["expected_thread"], \
                f"Failed to extract thread ID from {test_case['format']} format"
            
            # Test format info
            format_info = UnifiedIDManager.get_format_info(test_case["run_id"])
            assert format_info["thread_id"] == test_case["expected_thread"]
            assert "format_version" in format_info
    
    @pytest.mark.asyncio
    async def test_websocket_agent_handler_with_supervisor_import(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_db_session
    ):
        """Test that AgentMessageHandler can properly import and use SupervisorAgent."""
        
        # Create message handler service with mocked dependencies
        message_handler_service = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=mock_websocket_manager
        )
        
        # Create agent message handler
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=None
        )
        
        # Create test message
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test request",
                "thread_id": "thread_test123"
            }
        )
        
        # Test handling start_agent message
        result = await agent_handler._handle_start_agent(
            user_id="user_456",
            message=message,
            db_session=mock_db_session
        )
        
        # Verify supervisor was called
        assert mock_supervisor.execute.called or mock_supervisor.run.called, \
            "Supervisor should be executed during agent start"
    
    @pytest.mark.asyncio
    async def test_agent_websocket_bridge_thread_resolution(self):
        """Test AgentWebSocketBridge thread resolution with UnifiedIDManager."""
        
        # Create bridge instance
        bridge = AgentWebSocketBridge()
        
        # Test thread extraction for various ID formats
        test_ids = [
            ("thread_user123_run_1234567890_abcd1234", "user123"),
            ("run_session456_12345678", "session456"),
            ("thread_already_prefixed_run_1234567890_abcd1234", "already_prefixed"),
        ]
        
        for run_id, expected_thread in test_ids:
            # Use private method that calls UnifiedIDManager
            extracted = bridge._extract_thread_from_standardized_run_id(run_id)
            
            # Verify extraction (bridge adds "thread_" prefix)
            assert extracted is not None, f"Failed to extract from {run_id}"
            assert expected_thread in extracted, \
                f"Expected thread {expected_thread} not found in {extracted}"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_import_issues(
        self,
        mock_websocket_manager,
        mock_supervisor,
        mock_thread_service,
        mock_db_session
    ):
        """Test that import errors are properly raised and logged."""
        
        # Create message handler service
        message_handler_service = MessageHandlerService(
            supervisor=mock_supervisor,
            thread_service=mock_thread_service,
            websocket_manager=mock_websocket_manager
        )
        
        # Create agent handler
        agent_handler = AgentMessageHandler(
            message_handler_service=message_handler_service,
            websocket=None
        )
        
        # Mock an import error scenario
        with patch.object(
            message_handler_service, 
            'handle_start_agent',
            side_effect=NameError("name 'UnifiedIDManager' is not defined")
        ):
            message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={"user_request": "Test"}
            )
            
            # The error should be caught but critical errors re-raised
            with pytest.raises(NameError) as exc_info:
                await agent_handler._handle_start_agent(
                    user_id="user_456",
                    message=message,
                    db_session=mock_db_session
                )
            
            assert "UnifiedIDManager" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unified_id_generation(self):
        """Test UnifiedIDManager ID generation."""
        
        # Test normal thread ID
        run_id = UnifiedIDManager.generate_run_id("test_thread")
        assert run_id.startswith("thread_test_thread_run_")
        
        # Test already prefixed thread ID (shouldn't double prefix)
        run_id = UnifiedIDManager.generate_run_id("thread_already_prefixed")
        assert not run_id.startswith("thread_thread_")
        assert run_id.startswith("thread_already_prefixed_run_")
        
        # Verify generated ID can be parsed back
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted in ["test_thread", "already_prefixed"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])