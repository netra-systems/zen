"""
Critical Database Session Safety Tests for Thread Handlers

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data integrity and prevent data corruption in thread operations
- Value Impact: Prevents database corruption, data loss, and transaction leaks
- Strategic Impact: Core platform reliability and user data protection

CRITICAL: These tests are designed to INITIALLY FAIL to demonstrate database session safety issues.
They prove that the current implementation has dangerous database session handling that could
lead to data corruption, session leaks, and system instability.

ISSUES BEING TESTED:
1. handle_update_thread_request() calls db.commit() without rollback (line 109)
2. Missing rollback handling in most functions
3. Session cleanup in error scenarios
4. Repository pattern inconsistency
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError
from fastapi import HTTPException

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

# ABSOLUTE IMPORTS per CLAUDE.md requirements
from netra_backend.app.routes.utils.thread_handlers import (
    handle_update_thread_request,
    handle_create_thread_request, 
    handle_get_thread_request,
    handle_delete_thread_request,
    handle_send_message_request,
    handle_auto_rename_request,
    handle_list_threads_request,
    handle_get_messages_request
)


class TestThreadHandlersDatabaseSessionSafety(BaseIntegrationTest):
    """
    CRITICAL DATABASE SESSION SAFETY TESTS
    
    These tests are designed to FAIL initially to prove that the current
    database session handling in thread_handlers.py has dangerous issues.
    """

    @pytest.mark.unit
    async def test_handle_update_thread_request_commit_without_rollback_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: handle_update_thread_request() commits without rollback
        
        Line 109: await db.commit() - no rollback handling for database errors
        This test SHOULD FAIL initially because the function has unsafe db session handling.
        """
        # Mock database session that will raise error after commit
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Setup - make thread validation pass, but make commit fail
        mock_thread = Mock()
        mock_thread.id = "test-thread-123"
        mock_thread.metadata_ = {"user_id": "user-123"}
        
        mock_thread_update = Mock()
        mock_thread_update.title = "Updated Title"
        mock_thread_update.metadata = {"some": "data"}

        # Make the database commit fail with a database error
        mock_db.commit = AsyncMock(side_effect=DatabaseError("Connection lost", None, None))
        
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation', 
                  return_value=mock_thread):
            with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository'):
                
                # This should raise DatabaseError but NOT call rollback
                with pytest.raises(DatabaseError):
                    await handle_update_thread_request(
                        db=mock_db, 
                        thread_id="test-thread-123", 
                        thread_update=mock_thread_update,
                        user_id="user-123"
                    )
                
                # CRITICAL ASSERTION: Function should have called rollback but didn't
                # This test will FAIL because the current implementation doesn't rollback
                mock_db.rollback.assert_called_once()  # THIS WILL FAIL - proving the bug!

    @pytest.mark.unit  
    async def test_handle_create_thread_request_missing_rollback_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: handle_create_thread_request() has no rollback handling
        
        The function lacks database error handling and rollback capability.
        This test SHOULD FAIL initially because there's no rollback mechanism.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        thread_data = {"title": "Test Thread", "metadata": {"user_id": "user-123"}}
        user_id = "user-123"
        
        # Make thread creation fail after some processing
        with patch('netra_backend.app.routes.utils.thread_handlers.generate_thread_id', 
                  return_value="thread-123"):
            with patch('netra_backend.app.routes.utils.thread_handlers.prepare_thread_metadata',
                      return_value={"title": "Test", "user_id": "user-123"}):
                with patch('netra_backend.app.routes.utils.thread_handlers.create_thread_record',
                          side_effect=IntegrityError("Constraint violation", None, None)):
                    
                    # This should raise IntegrityError
                    with pytest.raises(IntegrityError):
                        await handle_create_thread_request(
                            db=mock_db,
                            thread_data=thread_data,
                            user_id=user_id
                        )
                    
                    # CRITICAL ASSERTION: Function should have called rollback but didn't
                    # This test will FAIL because there's no rollback handling
                    mock_db.rollback.assert_called_once()  # THIS WILL FAIL - proving the bug!

    @pytest.mark.unit
    async def test_session_leak_detection_in_get_thread_request_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Session leak detection in error scenarios
        
        When database operations fail, the session should be properly cleaned up.
        This test SHOULD FAIL because current implementation doesn't track or clean sessions.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Track session state
        session_active = True
        mock_db.in_transaction = Mock(return_value=session_active)
        mock_db.is_active = True
        
        # Make thread validation fail with database error
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                  side_effect=OperationalError("Connection timeout", None, None)):
            
            with pytest.raises(OperationalError):
                await handle_get_thread_request(
                    db=mock_db,
                    thread_id="test-thread-123", 
                    user_id="user-123"
                )
            
            # CRITICAL ASSERTION: Session should be cleaned up after error
            # This test will FAIL because there's no session cleanup mechanism
            mock_db.rollback.assert_called_once()  # THIS WILL FAIL - no cleanup!
            
            # Verify session is no longer in active transaction state
            # This assertion will also FAIL - proving session leak
            assert not mock_db.in_transaction(), "Session should be cleaned up after error"

    @pytest.mark.unit
    async def test_repository_pattern_inconsistency_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Repository pattern inconsistency
        
        Some functions use MessageRepository() while others don't follow consistent patterns.
        This creates inconsistent database session handling.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Test handle_get_thread_request - uses MessageRepository directly
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation') as mock_get_thread:
            with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository') as mock_repo_class:
                
                mock_thread = Mock()
                mock_get_thread.return_value = mock_thread
                
                # Mock repository instance
                mock_repo = AsyncMock()
                mock_repo_class.return_value = mock_repo
                mock_repo.count_by_thread.return_value = 5
                
                with patch('netra_backend.app.routes.utils.thread_handlers.build_thread_response'):
                    await handle_get_thread_request(
                        db=mock_db,
                        thread_id="test-thread-123",
                        user_id="user-123"
                    )
                
                # CRITICAL ASSERTION: Repository should receive the db session for consistency
                # This test will FAIL because MessageRepository() is instantiated without session context
                mock_repo.count_by_thread.assert_called_with(mock_db, "test-thread-123")
                
                # Verify that the repository instance was properly session-scoped
                # This will FAIL because current pattern creates repository without session scope
                assert mock_repo_class.call_count == 1, "Repository should be instantiated once per request"

    @pytest.mark.unit
    async def test_handle_delete_thread_missing_transaction_management_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: handle_delete_thread_request lacks transaction management
        
        The function calls archive_thread_safely but doesn't handle transaction rollback
        if the archival process fails.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Make thread validation pass but archival fail
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation'):
            with patch('netra_backend.app.routes.utils.thread_handlers.archive_thread_safely',
                      side_effect=DatabaseError("Archive failed", None, None)):
                
                with pytest.raises(DatabaseError):
                    await handle_delete_thread_request(
                        db=mock_db,
                        thread_id="test-thread-123",
                        user_id="user-123"
                    )
                
                # CRITICAL ASSERTION: Should rollback when archive fails
                # This test will FAIL because there's no rollback handling
                mock_db.rollback.assert_called_once()  # THIS WILL FAIL - proving the bug!

    @pytest.mark.unit
    async def test_handle_auto_rename_transaction_isolation_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: handle_auto_rename_request lacks transaction isolation
        
        The function performs multiple database operations but doesn't ensure
        they're wrapped in a proper transaction with rollback capability.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Setup mocks for successful validation and message retrieval
        mock_thread = Mock()
        mock_message = Mock()
        mock_message.content = "Test message for title generation"
        
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                  return_value=mock_thread):
            with patch('netra_backend.app.routes.utils.thread_handlers.get_first_user_message_safely',
                      return_value=mock_message):
                with patch('netra_backend.app.routes.utils.thread_handlers.generate_title_with_llm',
                          return_value="Generated Title"):
                    # Make thread update fail
                    with patch('netra_backend.app.routes.utils.thread_handlers.update_thread_with_title',
                              side_effect=DatabaseError("Update failed", None, None)):
                        
                        with pytest.raises(DatabaseError):
                            await handle_auto_rename_request(
                                db=mock_db,
                                thread_id="test-thread-123", 
                                user_id="user-123"
                            )
                        
                        # CRITICAL ASSERTION: Should rollback the entire transaction
                        # This test will FAIL because there's no transaction management
                        mock_db.rollback.assert_called_once()  # THIS WILL FAIL!

    @pytest.mark.unit
    async def test_handle_list_threads_no_error_handling_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: handle_list_threads_request has no error handling
        
        If database operations fail during thread listing, there's no rollback mechanism.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Make get_user_threads fail
        with patch('netra_backend.app.routes.utils.thread_handlers.get_user_threads',
                  side_effect=OperationalError("Query timeout", None, None)):
            
            with pytest.raises(OperationalError):
                await handle_list_threads_request(
                    db=mock_db,
                    user_id="user-123",
                    offset=0,
                    limit=10
                )
            
            # CRITICAL ASSERTION: Should attempt rollback on database error
            # This test will FAIL because there's no error handling
            mock_db.rollback.assert_called_once()  # THIS WILL FAIL!

    @pytest.mark.unit
    async def test_database_session_state_consistency_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Database session state consistency across operations
        
        Verifies that database sessions maintain consistent state across function calls
        and properly handle connection state changes.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock a partially successful operation that leaves session in bad state
        mock_thread = Mock()
        mock_thread.metadata_ = {"user_id": "user-123"}
        
        # Simulate session state corruption during update
        def corrupt_session(*args, **kwargs):
            mock_db.is_active = False
            mock_db.in_transaction.return_value = True  # Inconsistent state!
            raise DatabaseError("Session corrupted", None, None)
        
        mock_db.commit = AsyncMock(side_effect=corrupt_session)
        
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                  return_value=mock_thread):
            with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository'):
                
                mock_thread_update = Mock()
                mock_thread_update.title = "Test"
                mock_thread_update.metadata = {}
                
                with pytest.raises(DatabaseError):
                    await handle_update_thread_request(
                        db=mock_db,
                        thread_id="test-thread-123",
                        thread_update=mock_thread_update,
                        user_id="user-123"
                    )
                
                # CRITICAL ASSERTION: Session state should be restored/cleaned
                # This test will FAIL because there's no session state management
                assert mock_db.is_active or not mock_db.in_transaction(), \
                    "Session should be in consistent state after error"

    @pytest.mark.unit
    async def test_concurrent_session_safety_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Concurrent database session safety
        
        Tests that concurrent calls to thread handlers don't interfere with
        each other's database session state.
        """
        # Create multiple mock sessions to simulate concurrent requests
        mock_db1 = AsyncMock(spec=AsyncSession)
        mock_db2 = AsyncMock(spec=AsyncSession)
        
        # Make one session fail while other succeeds
        mock_db1.commit = AsyncMock(side_effect=DatabaseError("Connection lost", None, None))
        mock_db2.commit = AsyncMock()  # This should succeed
        
        mock_thread1 = Mock()
        mock_thread1.metadata_ = {"user_id": "user-123"}
        mock_thread2 = Mock() 
        mock_thread2.metadata_ = {"user_id": "user-456"}
        
        async def failing_update():
            with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                      return_value=mock_thread1):
                with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository'):
                    mock_update = Mock()
                    mock_update.title = "Failing Update"
                    mock_update.metadata = {}
                    
                    try:
                        await handle_update_thread_request(
                            db=mock_db1,
                            thread_id="thread-1", 
                            thread_update=mock_update,
                            user_id="user-123"
                        )
                    except DatabaseError:
                        pass  # Expected

        async def successful_update():
            with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                      return_value=mock_thread2):
                with patch('netra_backend.app.routes.utils.thread_handlers.MessageRepository'):
                    mock_update = Mock()
                    mock_update.title = "Successful Update"
                    mock_update.metadata = {}
                    
                    await handle_update_thread_request(
                        db=mock_db2,
                        thread_id="thread-2",
                        thread_update=mock_update, 
                        user_id="user-456"
                    )
        
        # Run both operations concurrently
        await asyncio.gather(failing_update(), successful_update())
        
        # CRITICAL ASSERTION: Failed session should have called rollback
        # This test will FAIL because there's no rollback handling for concurrent failures
        mock_db1.rollback.assert_called_once()  # THIS WILL FAIL!
        
        # Successful session should have committed successfully
        mock_db2.commit.assert_called_once()


class TestSessionLeakDetection(BaseIntegrationTest):
    """
    Additional tests specifically for database session leak detection.
    These tests are designed to FAIL and prove session management issues.
    """

    @pytest.mark.unit
    async def test_detect_unclosed_database_connections_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Detect unclosed database connections
        
        Verifies that database connections are properly closed after operations,
        even when errors occur.
        """
        connection_count_before = 0  # Simulate connection tracking
        
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.close = AsyncMock()
        
        # Make operation fail
        with patch('netra_backend.app.routes.utils.thread_handlers.get_thread_with_validation',
                  side_effect=DatabaseError("Connection error", None, None)):
            
            try:
                await handle_get_thread_request(
                    db=mock_db,
                    thread_id="test-thread-123",
                    user_id="user-123" 
                )
            except DatabaseError:
                pass  # Expected
        
        # CRITICAL ASSERTION: Database connection should be properly closed
        # This test will FAIL because current implementation doesn't ensure cleanup
        mock_db.close.assert_called_once()  # THIS WILL FAIL - no cleanup!

    @pytest.mark.unit
    async def test_detect_hanging_transactions_SHOULD_FAIL(self):
        """
        CRITICAL FAILING TEST: Detect hanging transactions
        
        Verifies that database transactions are properly completed (committed or rolled back)
        and not left hanging after operations.
        """
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.in_transaction = Mock(return_value=True)
        
        # Simulate operation that starts transaction but fails to complete it
        with patch('netra_backend.app.routes.utils.thread_handlers.get_user_threads',
                  side_effect=DatabaseError("Query failed", None, None)):
            
            try:
                await handle_list_threads_request(
                    db=mock_db,
                    user_id="user-123",
                    offset=0,
                    limit=10
                )
            except DatabaseError:
                pass  # Expected
        
        # CRITICAL ASSERTION: Transaction should be rolled back, not left hanging
        # This test will FAIL because there's no transaction cleanup
        assert not mock_db.in_transaction(), \
            "Transaction should be completed (committed or rolled back), not left hanging"


# Pytest configuration for these specific failing tests
@pytest.fixture(autouse=True) 
def setup_failing_test_environment():
    """
    Setup fixture that configures environment for intentionally failing tests.
    
    These tests are DESIGNED to fail initially to prove database session issues exist.
    After fixing the thread_handlers.py implementation, these tests should pass.
    """
    import os
    os.environ["EXPECT_DATABASE_SESSION_SAFETY_TESTS_TO_FAIL"] = "true"
    yield
    if "EXPECT_DATABASE_SESSION_SAFETY_TESTS_TO_FAIL" in os.environ:
        del os.environ["EXPECT_DATABASE_SESSION_SAFETY_TESTS_TO_FAIL"]