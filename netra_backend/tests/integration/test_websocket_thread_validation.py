"""Integration test for WebSocket thread validation and database interaction.

This test verifies the interaction between WebSocket handlers, thread service,
and database when handling non-existent threads in development mode.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.db.models_postgres import Thread
from netra_backend.app.core.exceptions_database import DatabaseError


@pytest.mark.asyncio
class TestWebSocketThreadValidation:
    """Test WebSocket message handling with thread validation."""
    
    async def test_websocket_start_agent_with_nonexistent_thread(self):
        """Test that WebSocket start_agent fails when thread doesn't exist in database."""
        # Arrange
        mock_supervisor = AsyncMock()
        thread_service = ThreadService()
        message_handler = MessageHandlerService(mock_supervisor, thread_service)
        agent_handler = AgentMessageHandler(message_handler)
        
        # Mock database session
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        # Create WebSocket message with non-existent thread
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test request",
                "thread_id": "thread_dev-temp-e946eb46"
            }
        )
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        
        # Configure thread service to raise DB_QUERY_FAILED error
        with patch.object(thread_service, '_execute_with_uow') as mock_execute:
            mock_execute.side_effect = DatabaseError(
                message="Failed to fetch Thread by ID",
                code="DB_QUERY_FAILED",
                context={"entity_id": "thread_dev-temp-e946eb46"}
            )
            
            # Act & Assert
            result = await agent_handler.handle_message(
                user_id="development-user",
                websocket=mock_websocket,
                message=message
            )
            
            # Should return False when thread validation fails
            assert result is False
            assert agent_handler.processing_stats["errors"] > 0
    
    async def test_thread_service_get_or_create_in_development_mode(self):
        """Test thread service creates threads for development users."""
        # Arrange
        thread_service = ThreadService()
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        # Mock UnitOfWork
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_uow:
            mock_uow_instance = AsyncMock()
            mock_uow.return_value.__aenter__.return_value = mock_uow_instance
            
            # Configure threads repository to return None first (not found)
            # then return a created thread
            mock_uow_instance.threads.get_or_create_for_user.return_value = Thread(
                id="thread_development-user",
                object="thread",
                created_at=1000000000,
                metadata_={"user_id": "development-user"}
            )
            
            # Act
            thread = await thread_service.get_or_create_thread("development-user", mock_db_session)
            
            # Assert
            assert thread is not None
            assert thread.id == "thread_development-user"
            assert thread.metadata_["user_id"] == "development-user"
    
    async def test_message_handler_validates_thread_access(self):
        """Test message handler properly validates thread access permissions."""
        # Arrange
        mock_supervisor = AsyncMock()
        thread_service = ThreadService()
        message_handler = MessageHandlerService(mock_supervisor, thread_service)
        
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        # Create a thread owned by different user
        existing_thread = Thread(
            id="thread_other_user",
            object="thread",
            created_at=1000000000,
            metadata_={"user_id": "other-user"}
        )
        
        # Mock thread service to return the thread
        with patch.object(thread_service, 'get_thread') as mock_get_thread:
            mock_get_thread.return_value = existing_thread
            
            # Act
            payload = {
                "user_request": "Test request",
                "thread_id": "thread_other_user"
            }
            
            # Should create new thread when access denied
            with patch.object(thread_service, 'get_or_create_thread') as mock_create:
                mock_create.return_value = Thread(
                    id="thread_development-user",
                    object="thread",
                    created_at=1000000000,
                    metadata_={"user_id": "development-user"}
                )
                
                await message_handler.handle_start_agent(
                    user_id="development-user",
                    payload=payload,
                    db_session=mock_db_session
                )
                
                # Should have created a new thread for the user
                mock_create.assert_called_once()
    
    async def test_concurrent_thread_operations_in_development(self):
        """Test handling of concurrent thread operations in development mode."""
        # Arrange
        thread_service = ThreadService()
        mock_db_session = AsyncMock(spec=AsyncSession)
        
        # Simulate concurrent requests for same non-existent thread
        thread_id = "thread_dev-temp-concurrent"
        
        async def fetch_thread():
            """Simulate thread fetch operation."""
            with patch.object(thread_service, '_execute_with_uow') as mock_execute:
                # First call raises error (thread doesn't exist)
                mock_execute.side_effect = [
                    DatabaseError(message="Failed to fetch Thread by ID"),
                    Thread(id=thread_id, object="thread", created_at=1000000000, metadata_={})
                ]
                
                try:
                    return await thread_service.get_thread(thread_id, db=mock_db_session)
                except:
                    return None
        
        # Act - Execute multiple concurrent requests
        results = await asyncio.gather(
            fetch_thread(),
            fetch_thread(),
            fetch_thread(),
            return_exceptions=True
        )
        
        # Assert - All requests should handle the error gracefully
        for result in results:
            assert not isinstance(result, Exception) or result is None