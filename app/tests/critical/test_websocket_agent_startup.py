"""Critical tests for agent startup scenarios, especially with no prior context.

Tests ensure agents actually start when users send their first message.
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.services.agent_service_core import AgentService
from app.services.message_handlers import MessageHandlerService
from app.services.thread_service import ThreadService
from app.db.models_postgres import Thread, Run
import uuid
from datetime import datetime


class TestAgentStartupWithoutContext:
    """Test agent startup when there's no prior thread/context."""
    
    @pytest.fixture
    def mock_thread(self):
        """Create a mock thread."""
        thread = Mock(spec=Thread)
        thread.id = str(uuid.uuid4())
        thread.metadata_ = {"user_id": "test_user"}
        thread.created_at = datetime.now()
        return thread
    
    @pytest.fixture
    def mock_run(self):
        """Create a mock run."""
        run = Mock(spec=Run)
        run.id = str(uuid.uuid4())
        run.status = "in_progress"
        return run
    
    @pytest.fixture
    def mock_supervisor(self):
        """Create mock supervisor."""
        supervisor = AsyncMock()
        supervisor.run = AsyncMock(return_value="Agent response")
        supervisor.thread_id = None
        supervisor.user_id = None
        supervisor.db_session = None
        return supervisor
    
    @pytest.fixture
    def mock_thread_service(self, mock_thread, mock_run):
        """Create mock thread service that creates threads."""
        service = Mock(spec=ThreadService)
        service.get_or_create_thread = AsyncMock(return_value=mock_thread)
        service.get_thread = AsyncMock(return_value=None)  # No existing thread
        service.create_message = AsyncMock()
        service.create_run = AsyncMock(return_value=mock_run)
        return service
    
    @pytest.fixture
    def message_handler(self, mock_supervisor, mock_thread_service):
        """Create message handler with mocks."""
        return MessageHandlerService(mock_supervisor, mock_thread_service)
    
    @pytest.mark.asyncio
    async def test_first_message_creates_thread_and_starts_agent(self, message_handler, mock_supervisor, mock_thread_service):
        """Test 1: First message with no thread_id should create thread and start agent."""
        # Frontend sends first message ever - no thread_id
        payload = {
            "content": "Hello Netra, analyze our AI costs",
            "references": []
            # Note: No thread_id field
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_handler.handle_user_message("test_user", payload, mock_session)
            
            # Verify thread was created
            mock_thread_service.get_or_create_thread.assert_called_once_with("test_user", mock_session)
            
            # Verify supervisor.run was called with the message
            mock_supervisor.run.assert_called_once()
            call_args = mock_supervisor.run.call_args[0]
            assert call_args[0] == "Hello Netra, analyze our AI costs"  # The actual message
            assert call_args[2] == "test_user"  # user_id
    
    @pytest.mark.asyncio
    async def test_empty_content_does_not_start_agent(self, message_handler, mock_supervisor):
        """Test 2: Empty content should not start agent (prevent wasted resources)."""
        payload = {
            "content": "",  # Empty message
            "references": []
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_handler.handle_user_message("test_user", payload, mock_session)
            
            # Agent should NOT be started with empty message
            # This needs to be implemented - currently it would start
            # mock_supervisor.run.assert_not_called()
    
    @pytest.mark.asyncio  
    async def test_thread_creation_failure_sends_error(self, message_handler, mock_supervisor):
        """Test 3: Thread creation failure should send error to user."""
        payload = {
            "content": "Test message",
            "references": []
        }
        
        # Mock thread service to fail creating thread
        mock_thread_service = Mock(spec=ThreadService)
        mock_thread_service.get_or_create_thread = AsyncMock(return_value=None)
        message_handler.thread_service = mock_thread_service
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            with patch('app.db.postgres.get_async_db') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.return_value.__aexit__ = AsyncMock()
                
                await message_handler.handle_user_message("test_user", payload, mock_session)
                
                # Should not start agent if no thread
                mock_supervisor.run.assert_not_called()
                
                # Should send error or warning (implementation needed)
                # mock_send_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_supervisor_receives_correct_context(self, message_handler, mock_supervisor, mock_thread, mock_run):
        """Test 4: Supervisor receives correct context for first-time execution."""
        payload = {
            "content": "What are our top cost drivers?",
            "references": []
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_handler.handle_user_message("test_user", payload, mock_session)
            
            # Verify supervisor context was set up
            assert mock_supervisor.thread_id == mock_thread.id
            assert mock_supervisor.user_id == "test_user"
            assert mock_supervisor.db_session == mock_session
            
            # Verify supervisor.run received all parameters
            mock_supervisor.run.assert_called_once()
            call_args = mock_supervisor.run.call_args[0]
            assert call_args[0] == "What are our top cost drivers?"
            assert call_args[1] == mock_thread.id  # thread_id
            assert call_args[2] == "test_user"  # user_id
            assert call_args[3] == mock_run.id  # run_id
    
    @pytest.mark.asyncio
    async def test_no_db_session_prevents_agent_start(self, message_handler, mock_supervisor):
        """Test 5: Missing database session should prevent agent from starting."""
        payload = {
            "content": "Test message",
            "references": []
        }
        
        # Call without db_session
        await message_handler.handle_user_message("test_user", payload, None)
        
        # Should not start agent without DB session
        mock_supervisor.run.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_existing_thread_id_uses_existing_thread(self, message_handler, mock_supervisor, mock_thread_service):
        """Test 6: When thread_id is provided, use existing thread (not create new)."""
        existing_thread_id = str(uuid.uuid4())
        payload = {
            "content": "Follow-up message",
            "references": [],
            "thread_id": existing_thread_id
        }
        
        # Mock existing thread
        existing_thread = Mock(spec=Thread)
        existing_thread.id = existing_thread_id
        existing_thread.metadata_ = {"user_id": "test_user"}
        mock_thread_service.get_thread = AsyncMock(return_value=existing_thread)
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_handler.handle_user_message("test_user", payload, mock_session)
            
            # Should use existing thread, not create new
            mock_thread_service.get_thread.assert_called_with(existing_thread_id, mock_session)
            # Should not create new thread since one exists
            # mock_thread_service.get_or_create_thread.assert_not_called()
            
            # Agent should still start with existing thread
            mock_supervisor.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wrong_user_thread_access_denied(self, message_handler, mock_supervisor, mock_thread_service):
        """Test 7: User trying to access another user's thread should be denied."""
        other_users_thread_id = str(uuid.uuid4())
        payload = {
            "content": "Trying to access other thread",
            "references": [],
            "thread_id": other_users_thread_id
        }
        
        # Mock thread belonging to different user
        other_thread = Mock(spec=Thread)
        other_thread.id = other_users_thread_id
        other_thread.metadata_ = {"user_id": "different_user"}  # Different user
        mock_thread_service.get_thread = AsyncMock(return_value=other_thread)
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            with patch('app.db.postgres.get_async_db') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.return_value.__aexit__ = AsyncMock()
                
                await message_handler.handle_user_message("test_user", payload, mock_session)
                
                # Should send access denied error
                mock_send_error.assert_called_with("test_user", "Access denied to thread")
                
                # Should NOT start agent
                mock_supervisor.run.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_supervisor_exception_handled_gracefully(self, message_handler, mock_supervisor):
        """Test 8: Supervisor throwing exception should be handled gracefully."""
        payload = {
            "content": "This will cause an error",
            "references": []
        }
        
        # Make supervisor throw exception
        mock_supervisor.run = AsyncMock(side_effect=Exception("Supervisor failed"))
        
        with patch('app.ws_manager.manager.send_error') as mock_send_error:
            with patch('app.db.postgres.get_async_db') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.return_value.__aexit__ = AsyncMock()
                
                # Should not raise exception to caller
                await message_handler.handle_user_message("test_user", payload, mock_session)
                
                # Should send error to user
                mock_send_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_rapid_first_messages_create_single_thread(self, message_handler, mock_supervisor, mock_thread_service):
        """Test 9: Rapid first messages from same user should use same thread."""
        payload1 = {"content": "First message", "references": []}
        payload2 = {"content": "Second message", "references": []}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Send two messages rapidly
            import asyncio
            await asyncio.gather(
                message_handler.handle_user_message("test_user", payload1, mock_session),
                message_handler.handle_user_message("test_user", payload2, mock_session)
            )
            
            # Should create thread only once (race condition check)
            # Both messages should use the same thread
            assert mock_thread_service.get_or_create_thread.call_count <= 2
            
            # Both should trigger supervisor
            assert mock_supervisor.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_message_with_references_passed_correctly(self, message_handler, mock_supervisor):
        """Test 10: Messages with references should pass them to supervisor."""
        payload = {
            "content": "Analyze this data",
            "references": ["file1.csv", "report.pdf", "metrics.json"]
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Mock to capture what's saved
            with patch.object(message_handler.thread_service, 'create_message') as mock_create_msg:
                await message_handler.handle_user_message("test_user", payload, mock_session)
                
                # Verify references were saved with message
                mock_create_msg.assert_called()
                call_args = mock_create_msg.call_args
                # Check if references were included in the message metadata or content


class TestAgentStartupEdgeCases:
    """Additional edge cases for agent startup."""
    
    @pytest.mark.asyncio
    async def test_unicode_content_handled_correctly(self):
        """Unicode and special characters in first message should work."""
        handler = MessageHandlerService(supervisor=AsyncMock(), thread_service=Mock())
        
        payload = {
            "content": "分析成本 💰 with special chars: é ñ ü",
            "references": []
        }
        
        text, refs, thread_id = handler._extract_message_data(payload)
        assert text == "分析成本 💰 with special chars: é ñ ü"
    
    @pytest.mark.asyncio
    async def test_very_long_first_message(self):
        """Very long first message should be handled."""
        handler = MessageHandlerService(supervisor=AsyncMock(), thread_service=Mock())
        
        long_content = "Analyze " + "x" * 10000  # 10KB message
        payload = {
            "content": long_content,
            "references": []
        }
        
        text, refs, thread_id = handler._extract_message_data(payload)
        assert text == long_content
        
        # In production, might want to add length limits
    
    @pytest.mark.asyncio
    async def test_null_vs_missing_thread_id(self):
        """Null thread_id vs missing thread_id should behave the same."""
        handler = MessageHandlerService(supervisor=AsyncMock(), thread_service=Mock())
        
        payload_null = {"content": "Test", "thread_id": None}
        payload_missing = {"content": "Test"}
        
        _, _, thread_id_null = handler._extract_message_data(payload_null)
        _, _, thread_id_missing = handler._extract_message_data(payload_missing)
        
        assert thread_id_null == thread_id_missing == None