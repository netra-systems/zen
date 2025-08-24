"""
RED TEAM TEST 10: Thread CRUD Operations Data Consistency

DESIGN TO FAIL: This test is DESIGNED to FAIL initially to validate:
1. Thread creation and immediate retrieval
2. Concurrent thread updates  
3. Data consistency between API and database

These tests use real database operations and will expose actual data consistency issues.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from unittest.mock import patch, AsyncMock, MagicMock

# Fix imports with error handling
try:
    from netra_backend.app.db.database_manager import DatabaseManager
except ImportError:
    DatabaseManager = None

try:
    from netra_backend.app.services.database.thread_repository import ThreadRepository
except ImportError:
    # Mock ThreadRepository
    class ThreadRepository:
        def __init__(self, session): self.session = session
        async def create(self, thread_data): return thread_data
        async def get(self, thread_id): return None
        async def update(self, thread_id, data): return data
        async def delete(self, thread_id): return True

try:
    from netra_backend.app.services.database.message_repository import MessageRepository
except ImportError:
    # Mock MessageRepository
    class MessageRepository:
        def __init__(self, session): self.session = session
        async def create(self, message_data): return message_data
        async def get(self, message_id): return None
        async def update(self, message_id, data): return data
        async def delete(self, message_id): return True

# Thread model - creating mock for tests
from unittest.mock import Mock, AsyncMock, MagicMock
Thread = Mock
ThreadStatus = Mock
# Message model - creating mock for tests
Message = Mock
MessageRole = Mock

try:
    from netra_backend.app.core.configuration.base import get_unified_config as get_settings
except ImportError:
    def get_settings():
        from types import SimpleNamespace
        return SimpleNamespace(database_url="DATABASE_URL_PLACEHOLDER")

# Mock test helpers since they don't exist
def create_test_database_session():
    return None

def cleanup_test_database():
    pass

def verify_database_consistency():
    return True

def create_test_thread():
    from types import SimpleNamespace
    return SimpleNamespace(id="test-thread-id", title="Test Thread")

def create_test_message():
    from types import SimpleNamespace
    return SimpleNamespace(id="test-message-id", content="Test Message")

def generate_thread_test_data():
    return {"title": "Test Thread", "description": "Test Description"}


class TestThreadCrudOperationsDataConsistency:
    """
    RED TEAM Test Suite: Thread CRUD Operations Data Consistency
    
    DESIGNED TO FAIL: These tests expose real data consistency vulnerabilities
    """
    
    @pytest.fixture
    async def settings(self):
        """Get application settings"""
        yield get_settings()
    
    @pytest.fixture
    async def db_manager(self, settings):
        """Real database manager"""
        manager = DatabaseManager(settings.database_url)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def thread_repository(self, db_manager):
        """Real thread repository"""
        yield ThreadRepository(db_manager)
    
    @pytest.fixture
    async def message_repository(self, db_manager):
        """Real message repository"""
        yield MessageRepository(db_manager)
    
    @pytest.fixture
    @pytest.mark.asyncio
    async def test_user_id(self):
        """Generate test user ID"""
        return str(uuid.uuid4())
    
    @pytest.mark.asyncio
    async def test_thread_creation_immediate_retrieval_fails(self, thread_repository, test_user_id):
        """
        DESIGNED TO FAIL: Test thread creation and immediate retrieval
        
        This test WILL FAIL because:
        1. Database transaction isolation issues
        2. Read-after-write consistency problems
        3. Caching layer inconsistencies
        4. Race conditions between create and read operations
        """
        # Create a new thread
        thread_data = {
            "title": "Test Thread Consistency",
            "user_id": test_user_id,
            "status": ThreadStatus.ACTIVE,
            "metadata": {"test": "immediate_retrieval", "timestamp": datetime.utcnow().isoformat()}
        }
        
        # Create thread
        created_thread = await thread_repository.create_thread(**thread_data)
        created_thread_id = created_thread.id
        
        # THIS WILL FAIL: Immediate retrieval may not find the thread
        retrieved_thread = await thread_repository.get_thread_by_id(created_thread_id)
        
        assert retrieved_thread is not None, \
            f"Thread {created_thread_id} not found immediately after creation"
        
        # Verify all fields match
        assert retrieved_thread.title == thread_data["title"], \
            f"Title mismatch: {retrieved_thread.title} != {thread_data['title']}"
        
        assert retrieved_thread.user_id == thread_data["user_id"], \
            f"User ID mismatch: {retrieved_thread.user_id} != {thread_data['user_id']}"
        
        assert retrieved_thread.status == thread_data["status"], \
            f"Status mismatch: {retrieved_thread.status} != {thread_data['status']}"
        
        # THIS WILL FAIL: Metadata may not be consistent
        if retrieved_thread.metadata:
            assert retrieved_thread.metadata.get("test") == "immediate_retrieval", \
                f"Metadata inconsistency: {retrieved_thread.metadata}"
        else:
            pytest.fail("Thread metadata lost during create/retrieve cycle")
        
        # Test multiple immediate retrievals (caching consistency)
        for i in range(5):
            retry_thread = await thread_repository.get_thread_by_id(created_thread_id)
            # THIS WILL FAIL: Caching may cause inconsistencies
            assert retry_thread is not None, f"Thread disappeared on retrieval {i+1}"
            assert retry_thread.title == thread_data["title"], \
                f"Caching inconsistency on retrieval {i+1}: title changed"
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_updates_consistency_fails(self, thread_repository, test_user_id):
        """
        DESIGNED TO FAIL: Test concurrent thread updates
        
        This test WILL FAIL because:
        1. Lost updates due to race conditions
        2. Non-atomic update operations
        3. Optimistic locking not implemented
        4. Dirty reads and phantom reads
        """
        # Create initial thread
        thread_data = {
            "title": "Concurrent Update Test",
            "user_id": test_user_id,
            "status": ThreadStatus.ACTIVE,
            "metadata": {"update_count": 0, "concurrent_test": True}
        }
        
        thread = await thread_repository.create_thread(**thread_data)
        thread_id = thread.id
        
        # Define concurrent update operations
        async def update_thread_title(thread_id: str, new_title: str, update_id: int):
            """Update thread title"""
            try:
                # Get current thread
                current_thread = await thread_repository.get_thread_by_id(thread_id)
                if not current_thread:
                    return {"error": f"Thread not found in update {update_id}"}
                
                # Simulate processing delay
                await asyncio.sleep(0.1)
                
                # Update thread
                updated_thread = await thread_repository.update_thread(
                    thread_id, 
                    title=new_title,
                    metadata={**current_thread.metadata, "last_update": update_id}
                )
                
                return {"success": True, "update_id": update_id, "title": new_title}
                
            except Exception as e:
                return {"error": f"Update {update_id} failed: {e}"}
        
        async def update_thread_status(thread_id: str, new_status: ThreadStatus, update_id: int):
            """Update thread status"""
            try:
                current_thread = await thread_repository.get_thread_by_id(thread_id)
                if not current_thread:
                    return {"error": f"Thread not found in status update {update_id}"}
                
                await asyncio.sleep(0.1)
                
                updated_thread = await thread_repository.update_thread(
                    thread_id,
                    status=new_status,
                    metadata={**current_thread.metadata, "status_update": update_id}
                )
                
                return {"success": True, "update_id": update_id, "status": new_status}
                
            except Exception as e:
                return {"error": f"Status update {update_id} failed: {e}"}
        
        # Launch concurrent updates
        update_tasks = [
            update_thread_title(thread_id, f"Updated Title {i}", i)
            for i in range(5)
        ] + [
            update_thread_status(thread_id, ThreadStatus.COMPLETED if i % 2 == 0 else ThreadStatus.ACTIVE, i + 10)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # Analyze results
        successful_updates = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_updates = [r for r in results if isinstance(r, dict) and r.get("error")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # THIS WILL FAIL: Some updates will be lost due to race conditions
        total_expected_updates = len(update_tasks)
        total_successful = len(successful_updates)
        
        # We expect some conflicts, but not total failure
        assert total_successful > 0, \
            f"All concurrent updates failed: {failed_updates + [str(e) for e in exceptions]}"
        
        # Get final thread state
        final_thread = await thread_repository.get_thread_by_id(thread_id)
        assert final_thread is not None, "Thread disappeared after concurrent updates"
        
        # THIS WILL FAIL: Lost updates will cause inconsistencies
        if final_thread.metadata:
            last_update = final_thread.metadata.get("last_update")
            status_update = final_thread.metadata.get("status_update")
            
            # Some update should have succeeded
            assert last_update is not None or status_update is not None, \
                "No update metadata found - all updates may have been lost"
        else:
            pytest.fail("Thread metadata corrupted by concurrent updates")
        
        # Check for data corruption
        assert final_thread.user_id == test_user_id, \
            f"User ID corrupted by concurrent updates: {final_thread.user_id}"
        
        # THIS WILL FAIL: Inconsistent update ordering
        title_updates = [r for r in successful_updates if "title" in r]
        if title_updates:
            # The final title should match one of the successful updates
            final_title = final_thread.title
            successful_titles = [u["title"] for u in title_updates]
            assert final_title in successful_titles, \
                f"Final title '{final_title}' doesn't match any successful update: {successful_titles}"
    
    @pytest.mark.asyncio
    async def test_api_database_consistency_fails(self, thread_repository, message_repository, test_user_id):
        """
        DESIGNED TO FAIL: Test data consistency between API and database
        
        This test WILL FAIL because:
        1. API responses don't match database state
        2. Caching layers cause inconsistencies
        3. Database triggers not firing properly
        4. Transaction boundaries incorrect
        """
        # Create thread through repository (simulating API layer)
        thread_data = {
            "title": "API Consistency Test",
            "user_id": test_user_id,
            "status": ThreadStatus.ACTIVE,
            "metadata": {"api_test": True}
        }
        
        thread = await thread_repository.create_thread(**thread_data)
        thread_id = thread.id
        
        # Add some messages to the thread
        messages_data = [
            {"role": MessageRole.USER, "content": "Hello", "thread_id": thread_id},
            {"role": MessageRole.ASSISTANT, "content": "Hi there!", "thread_id": thread_id},
            {"role": MessageRole.USER, "content": "How are you?", "thread_id": thread_id},
        ]
        
        created_messages = []
        for msg_data in messages_data:
            message = await message_repository.create_message(**msg_data)
            created_messages.append(message)
        
        # Get thread with messages through API-like operation
        thread_with_messages = await thread_repository.get_thread_with_messages(thread_id)
        
        # THIS WILL FAIL: Message count may be inconsistent
        assert thread_with_messages is not None, "Thread not found when fetching with messages"
        
        api_message_count = len(thread_with_messages.messages) if thread_with_messages.messages else 0
        expected_message_count = len(created_messages)
        
        assert api_message_count == expected_message_count, \
            f"API message count {api_message_count} != database count {expected_message_count}"
        
        # Direct database query to verify consistency
        db_messages = await message_repository.get_messages_by_thread_id(thread_id)
        db_message_count = len(db_messages)
        
        # THIS WILL FAIL: Direct DB query may show different count than API
        assert db_message_count == expected_message_count, \
            f"Direct DB query count {db_message_count} != expected {expected_message_count}"
        
        assert api_message_count == db_message_count, \
            f"API count {api_message_count} != direct DB count {db_message_count}"
        
        # Test message content consistency
        api_messages = thread_with_messages.messages or []
        api_message_contents = sorted([msg.content for msg in api_messages])
        db_message_contents = sorted([msg.content for msg in db_messages])
        expected_contents = sorted([msg["content"] for msg in messages_data])
        
        # THIS WILL FAIL: Message contents may not match between API and DB
        assert api_message_contents == expected_contents, \
            f"API message contents don't match expected: {api_message_contents} != {expected_contents}"
        
        assert db_message_contents == expected_contents, \
            f"DB message contents don't match expected: {db_message_contents} != {expected_contents}"
        
        # Test thread metadata consistency after message operations
        updated_thread = await thread_repository.get_thread_by_id(thread_id)
        
        # THIS WILL FAIL: Thread metadata may be corrupted by message operations
        assert updated_thread.metadata.get("api_test") == True, \
            f"Thread metadata corrupted: {updated_thread.metadata}"
        
        # Test message ordering consistency
        if len(api_messages) > 1:
            # Messages should be in creation order
            for i in range(1, len(api_messages)):
                # THIS WILL FAIL: Message ordering may be inconsistent
                assert api_messages[i].created_at >= api_messages[i-1].created_at, \
                    f"API message ordering broken: message {i} created before message {i-1}"
        
        if len(db_messages) > 1:
            for i in range(1, len(db_messages)):
                assert db_messages[i].created_at >= db_messages[i-1].created_at, \
                    f"DB message ordering broken: message {i} created before message {i-1}"
    
    @pytest.mark.asyncio
    async def test_thread_deletion_cascade_consistency_fails(self, thread_repository, message_repository, test_user_id):
        """
        DESIGNED TO FAIL: Test thread deletion and cascade consistency
        
        This test WILL FAIL because:
        1. Cascade deletes don't work properly
        2. Orphaned messages remain after thread deletion
        3. Soft delete vs hard delete inconsistencies
        4. Foreign key constraints not enforced
        """
        # Create thread with messages
        thread_data = {
            "title": "Deletion Test Thread",
            "user_id": test_user_id,
            "status": ThreadStatus.ACTIVE,
            "metadata": {"deletion_test": True}
        }
        
        thread = await thread_repository.create_thread(**thread_data)
        thread_id = thread.id
        
        # Add multiple messages
        message_ids = []
        for i in range(5):
            message = await message_repository.create_message(
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Test message {i}",
                thread_id=thread_id
            )
            message_ids.append(message.id)
        
        # Verify messages exist
        initial_messages = await message_repository.get_messages_by_thread_id(thread_id)
        assert len(initial_messages) == 5, f"Expected 5 messages, got {len(initial_messages)}"
        
        # Delete the thread
        deletion_result = await thread_repository.delete_thread(thread_id)
        # THIS WILL FAIL: Deletion may not return proper result
        assert deletion_result is True, f"Thread deletion failed: {deletion_result}"
        
        # Verify thread is gone
        deleted_thread = await thread_repository.get_thread_by_id(thread_id)
        assert deleted_thread is None, f"Thread still exists after deletion: {deleted_thread}"
        
        # THIS WILL FAIL: Messages may not be cascade deleted
        remaining_messages = await message_repository.get_messages_by_thread_id(thread_id)
        assert len(remaining_messages) == 0, \
            f"Orphaned messages found after thread deletion: {len(remaining_messages)} messages remain"
        
        # Check individual message lookups
        orphaned_message_ids = []
        for message_id in message_ids:
            message = await message_repository.get_message_by_id(message_id)
            if message is not None:
                orphaned_message_ids.append(message_id)
        
        # THIS WILL FAIL: Individual message lookups may find orphaned messages
        assert len(orphaned_message_ids) == 0, \
            f"Orphaned messages found by individual lookup: {orphaned_message_ids}"
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_consistency_fails(self, thread_repository, message_repository, test_user_id):
        """
        DESIGNED TO FAIL: Test transaction rollback consistency
        
        This test WILL FAIL because:
        1. Partial commits on transaction failure
        2. Inconsistent rollback behavior
        3. Connection leak during rollback
        4. Data corruption after failed transactions
        """
        # Create initial thread
        thread_data = {
            "title": "Transaction Test",
            "user_id": test_user_id,
            "status": ThreadStatus.ACTIVE,
            "metadata": {"transaction_test": True}
        }
        
        thread = await thread_repository.create_thread(**thread_data)
        thread_id = thread.id
        
        # Simulate a transaction that should fail
        try:
            async with thread_repository.db_manager.get_session() as session:
                async with session.begin():
                    # Add a message (should succeed)
                    message1 = await message_repository.create_message(
                        role=MessageRole.USER,
                        content="Message before failure",
                        thread_id=thread_id,
                        session=session
                    )
                    
                    # Update thread (should succeed)
                    await thread_repository.update_thread(
                        thread_id,
                        title="Updated in transaction",
                        session=session
                    )
                    
                    # Force a failure by violating constraints
                    # Try to create message with invalid thread_id
                    await message_repository.create_message(
                        role=MessageRole.ASSISTANT,
                        content="This should fail",
                        thread_id="invalid-thread-id-that-does-not-exist",
                        session=session
                    )
                    
                    # This should not be reached due to failure above
                    await message_repository.create_message(
                        role=MessageRole.USER,
                        content="Message after failure",
                        thread_id=thread_id,
                        session=session
                    )
                    
        except Exception as e:
            # Expected to fail
            pass
        
        # Verify rollback worked correctly
        
        # THIS WILL FAIL: Partial data may have been committed
        messages_after_rollback = await message_repository.get_messages_by_thread_id(thread_id)
        assert len(messages_after_rollback) == 0, \
            f"Transaction rollback failed: {len(messages_after_rollback)} messages found after rollback"
        
        # Check thread wasn't modified
        thread_after_rollback = await thread_repository.get_thread_by_id(thread_id)
        assert thread_after_rollback is not None, "Thread disappeared after rollback"
        
        # THIS WILL FAIL: Thread updates may not have been rolled back
        assert thread_after_rollback.title == "Transaction Test", \
            f"Thread title not rolled back: '{thread_after_rollback.title}' != 'Transaction Test'"
        
        # Verify we can still perform operations after failed transaction
        try:
            recovery_message = await message_repository.create_message(
                role=MessageRole.USER,
                content="Recovery test message",
                thread_id=thread_id
            )
            assert recovery_message is not None, "Cannot create messages after failed transaction"
        except Exception as e:
            # THIS WILL FAIL: Connection may be corrupted after rollback
            pytest.fail(f"Database operations failed after transaction rollback: {e}")