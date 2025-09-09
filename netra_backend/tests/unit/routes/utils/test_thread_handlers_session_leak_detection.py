"""
Unit Tests: Thread Handlers Session Leak Detection

These tests are designed to FAIL initially to expose session leak issues
in the 8 thread handler functions. Each test validates that database sessions
are properly managed with commit/rollback and closure.

CRITICAL: Following CLAUDE.md principle "CHEATING ON TESTS = ABOMINATION"
These tests use real PostgreSQL and fail hard when leaks are detected.

Business Value:
- Prevents database connection pool exhaustion
- Ensures thread handler reliability under load
- Validates proper session lifecycle management
- Identifies session leaks before deployment
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Any, Dict

from test_framework.session_leak_detection import SessionLeakTestBase
from netra_backend.app.routes.utils.thread_handlers import (
    handle_list_threads_request,
    handle_create_thread_request, 
    handle_get_thread_request,
    handle_update_thread_request,
    handle_delete_thread_request,
    handle_get_messages_request,
    handle_auto_rename_request,
    handle_send_message_request
)


class TestThreadHandlersSessionLeakDetection(SessionLeakTestBase):
    """
    Session leak detection tests for all thread handler functions.
    
    CRITICAL: These tests are designed to FAIL initially because the current
    thread handlers do not have centralized session lifecycle management.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_leak_detection(self):
        """Set up session leak detection for each test."""
        await self.setup_session_leak_testing(
            max_session_age_seconds=5.0,  # Short timeout to catch leaks quickly
            monitoring_interval=0.1  # Fast monitoring for unit tests
        )
        yield
        await self.teardown_session_leak_testing()
    
    async def test_session_leak_scenario(self):
        """Required abstract method - not used in this test class."""
        pass
    
    @pytest.mark.asyncio
    async def test_handle_list_threads_request_session_leak(self):
        """
        Test: handle_list_threads_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        user_id = "test-user-123"
        offset = 0
        limit = 10
        
        # Mock dependencies to isolate session management testing
        with patch('netra_backend.app.routes.utils.thread_handlers.get_user_threads') as mock_get_threads, \
             patch('netra_backend.app.routes.utils.thread_handlers.convert_threads_to_responses') as mock_convert:
            
            mock_get_threads.return_value = []
            mock_convert.return_value = {'threads': [], 'total': 0}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_list_threads_request,
                user_id, offset, limit
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Current thread handlers don't have centralized session lifecycle management
        await self.assert_no_session_leaks(
            "handle_list_threads_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio  
    async def test_handle_create_thread_request_session_leak(self):
        """
        Test: handle_create_thread_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_data = {"title": "Test Thread", "metadata": {}}
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.generate_thread_id') as mock_gen_id, \
             patch('netra_backend.app.routes.utils.thread_handlers.prepare_thread_metadata') as mock_prepare, \
             patch('netra_backend.app.routes.utils.thread_handlers.create_thread_record') as mock_create, \
             patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
            
            mock_gen_id.return_value = "thread-123"
            mock_prepare.return_value = {"title": "Test Thread", "user_id": user_id}
            mock_create.return_value = Mock(id="thread-123")
            mock_build.return_value = {"id": "thread-123", "title": "Test Thread"}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_create_thread_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_handle_get_thread_request_session_leak(self):
        """
        Test: handle_get_thread_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo_class, \
             patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
            
            mock_thread = Mock(id=thread_id, metadata_={"title": "Test Thread"})
            mock_get.return_value = mock_thread
            
            mock_repo = Mock()
            mock_repo.count_by_thread.return_value = 5
            mock_repo_class.return_value = mock_repo
            
            mock_build.return_value = {"id": thread_id, "message_count": 5}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_get_thread_request,
                thread_id, user_id
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_get_thread_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_handle_update_thread_request_session_leak(self):
        """
        Test: handle_update_thread_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        thread_update = Mock(title="Updated Title", metadata={"new_field": "value"})
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.update_thread_metadata_fields') as mock_update, \
             patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo_class, \
             patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
            
            mock_thread = Mock(id=thread_id, metadata_={"title": "Original"})
            mock_get.return_value = mock_thread
            
            mock_repo = Mock()
            mock_repo.count_by_thread.return_value = 3
            mock_repo_class.return_value = mock_repo
            
            mock_build.return_value = {"id": thread_id, "title": "Updated Title"}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_update_thread_request,
                thread_id, thread_update, user_id
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_update_thread_request must properly manage database sessions and commit changes"
        )
    
    @pytest.mark.asyncio
    async def test_handle_delete_thread_request_session_leak(self):
        """
        Test: handle_delete_thread_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.archive_thread_safely') as mock_archive:
            
            mock_thread = Mock(id=thread_id)
            mock_get.return_value = mock_thread
            mock_archive.return_value = None
            
            # Execute handler with session tracking
            result = await self.execute_thread_handler_with_tracking(
                handle_delete_thread_request,
                thread_id, user_id
            )
            
            assert result == {"message": "Thread archived successfully"}
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_delete_thread_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_handle_get_messages_request_session_leak(self):
        """
        Test: handle_get_messages_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        user_id = "test-user-123"
        limit = 20
        offset = 0
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.build_thread_messages_response') as mock_build:
            
            mock_thread = Mock(id=thread_id)
            mock_get.return_value = mock_thread
            mock_build.return_value = {"messages": [], "total": 0}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_get_messages_request,
                thread_id, user_id, limit, offset
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_get_messages_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_handle_auto_rename_request_session_leak(self):
        """
        Test: handle_auto_rename_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.get_first_user_message_safely') as mock_get_msg, \
             patch('netra_backend.app.routes.utils.thread_handlers.generate_title_with_llm') as mock_gen_title, \
             patch('netra_backend.app.routes.utils.thread_handlers.update_thread_with_title') as mock_update, \
             patch('netra_backend.app.routes.utils.thread_handlers.send_thread_rename_notification') as mock_notify, \
             patch('netra_backend.app.routes.utils.thread_handlers.create_final_thread_response') as mock_response:
            
            mock_thread = Mock(id=thread_id)
            mock_get.return_value = mock_thread
            
            mock_message = Mock(content="Hello, I need help with...")
            mock_get_msg.return_value = mock_message
            
            mock_gen_title.return_value = "Help Request"
            mock_update.return_value = None
            mock_notify.return_value = None
            mock_response.return_value = {"id": thread_id, "title": "Help Request"}
            
            # Execute handler with session tracking
            await self.execute_thread_handler_with_tracking(
                handle_auto_rename_request,
                thread_id, user_id
            )
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_auto_rename_request must properly manage database sessions"
        )
    
    @pytest.mark.asyncio
    async def test_handle_send_message_request_session_leak(self):
        """
        Test: handle_send_message_request session management
        
        EXPECTED TO FAIL: Current implementation lacks centralized session tracking
        """
        thread_id = "thread-123"
        request = Mock(message="Test message", metadata={"type": "user"})
        user_id = "test-user-123"
        
        # Mock dependencies
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get, \
             patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo_class, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_thread = Mock(id=thread_id)
            mock_get.return_value = mock_thread
            
            mock_repo = Mock()
            mock_repo.create.return_value = None
            mock_repo_class.return_value = mock_repo
            
            mock_uuid.return_value = Mock(hex="message123")
            
            # Execute handler with session tracking
            result = await self.execute_thread_handler_with_tracking(
                handle_send_message_request,
                thread_id, request, user_id
            )
            
            # Verify result structure
            assert "id" in result
            assert result["thread_id"] == thread_id
            assert result["content"] == "Test message"
            assert result["role"] == "user"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "handle_send_message_request must properly manage database sessions and commit message"
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_handlers_session_leak(self):
        """
        Test: Concurrent execution of multiple thread handlers
        
        EXPECTED TO FAIL: Session leaks become more apparent under concurrent load
        """
        user_id = "test-user-123"
        
        # Mock all dependencies for all handlers
        with patch('netra_backend.app.routes.utils.thread_handlers.get_user_threads') as mock_get_threads, \
             patch('netra_backend.app.routes.utils.thread_handlers.convert_threads_to_responses') as mock_convert, \
             patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get_thread, \
             patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo_class, \
             patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response') as mock_build:
            
            # Set up mocks
            mock_get_threads.return_value = []
            mock_convert.return_value = {'threads': [], 'total': 0}
            mock_get_thread.return_value = Mock(id="thread-123", metadata_={"title": "Test"})
            
            mock_repo = Mock()
            mock_repo.count_by_thread.return_value = 2
            mock_repo_class.return_value = mock_repo
            
            mock_build.return_value = {"id": "thread-123", "message_count": 2}
            
            # Execute concurrent requests
            results = await self.simulate_concurrent_requests(
                handle_list_threads_request,
                request_count=10,
                concurrent_limit=5,
                args=(user_id, 0, 10)  # handler arguments
            )
            
            # Check that all requests completed
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) > 0, "At least some concurrent requests should succeed"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Concurrent execution amplifies session leak issues
        await self.assert_no_session_leaks(
            "Concurrent thread handler execution must not cause session leaks"
        )
    
    @pytest.mark.asyncio
    async def test_exception_handling_session_leak(self):
        """
        Test: Session management when exceptions occur in thread handlers
        
        EXPECTED TO FAIL: Current handlers may not properly rollback sessions on exceptions
        """
        user_id = "test-user-123"
        
        # Mock to cause an exception
        with patch('netra_backend.app.routes.utils.thread_handlers.get_user_threads') as mock_get_threads:
            mock_get_threads.side_effect = Exception("Database error")
            
            # Execute handler that should fail
            try:
                await self.execute_thread_handler_with_tracking(
                    handle_list_threads_request,
                    user_id, 0, 10
                )
                pytest.fail("Handler should have raised an exception")
            except Exception as e:
                assert "Database error" in str(e)
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Sessions must be properly rolled back even when exceptions occur
        await self.assert_no_session_leaks(
            "Exception handling must properly rollback database sessions"
        )