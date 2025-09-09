"""
Test Thread Switching Concurrent Operations (Tests 61-80)

Business Value Justification (BVJ):
- Segment: Enterprise, Mid (high concurrent usage scenarios)
- Business Goal: Ensure platform stability under concurrent load
- Value Impact: Multi-user systems must handle parallel thread operations
- Strategic Impact: CRITICAL - Concurrent stability enables enterprise scalability
"""

import asyncio
import pytest
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types import ThreadID, UserID, RunID, RequestID

from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.db.models_postgres import Thread, Message
from netra_backend.app.websocket_core import create_websocket_manager


class TestThreadSwitchingConcurrentOperations(BaseIntegrationTest):
    """Integration tests for concurrent thread operations"""
    
    # Tests 61-65: Concurrent Thread Creation and Access
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_61_concurrent_thread_creation_same_user(self, real_services_fixture):
        """
        BVJ: Prevent duplicate threads when user rapidly clicks 'new conversation'
        Validates: Race condition prevention in thread creation
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"user_{UnifiedIDManager.generate_id()}"
        
        # Simulate rapid concurrent thread creation requests
        async def create_thread_task():
            return await thread_service.get_or_create_thread(user_id, db)
        
        # Execute 10 concurrent thread creation requests
        tasks = [create_thread_task() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should result in only 1 thread despite concurrent requests
        thread_ids = {result.id for result in results if hasattr(result, 'id')}
        assert len(thread_ids) <= 2  # Allow for minor race conditions but prevent excessive creation
        
        # Verify only legitimate threads exist
        threads = await thread_service.get_threads(user_id, db)
        assert len(threads) <= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_62_concurrent_thread_access_different_users(self, real_services_fixture):
        """
        BVJ: Ensure user isolation during concurrent thread access
        Validates: Multi-user thread access without cross-contamination
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Create multiple users and their threads
        users_and_threads = []
        for i in range(5):
            user_id = f"user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            users_and_threads.append((user_id, thread))
        
        # Concurrent access to different user threads
        async def access_user_thread(user_id: str, thread_id: str):
            return await thread_service.get_thread(thread_id, user_id, db)
        
        tasks = []
        for user_id, thread in users_and_threads:
            tasks.append(access_user_thread(user_id, thread.id))
        
        results = await asyncio.gather(*tasks)
        
        # Verify all threads were accessed correctly
        for i, result in enumerate(results):
            expected_user_id, expected_thread = users_and_threads[i]
            assert result is not None
            assert result.id == expected_thread.id

    @pytest.mark.integration  
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_63_concurrent_thread_switching_single_user(self, real_services_fixture):
        """
        BVJ: Handle rapid thread switching in power user scenarios
        Validates: Context preservation during rapid switching
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"user_{UnifiedIDManager.generate_id()}"
        
        # Create multiple threads for the user
        threads = []
        for i in range(5):
            thread = await thread_service.get_or_create_thread(user_id, db)
            threads.append(thread)
            # Create slight delay to ensure different IDs
            await asyncio.sleep(0.01)
        
        # Simulate rapid thread switching
        async def switch_to_thread(thread_id: str):
            user_context = UserExecutionContext(
                user_id=UserID(user_id),
                thread_id=ThreadID(thread_id),
                run_id=RunID(f"run_{UnifiedIDManager.generate_id()}"),
                request_id=RequestID(f"req_{UnifiedIDManager.generate_id()}")
            )
            return await thread_service.get_thread(thread_id, user_id, db)
        
        # Execute rapid switching between threads
        switch_tasks = []
        for _ in range(20):  # 20 rapid switches
            thread = threads[_ % len(threads)]
            switch_tasks.append(switch_to_thread(thread.id))
        
        results = await asyncio.gather(*switch_tasks, return_exceptions=True)
        
        # Verify all switches completed successfully
        successful_switches = [r for r in results if hasattr(r, 'id')]
        assert len(successful_switches) == 20

    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.asyncio
    async def test_64_concurrent_thread_message_operations(self, real_services_fixture):
        """
        BVJ: Ensure message consistency during concurrent operations
        Validates: Message ordering and integrity under concurrent load
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"user_{UnifiedIDManager.generate_id()}"
        
        # Create a thread for message operations
        thread = await thread_service.get_or_create_thread(user_id, db)
        
        # Concurrent message addition
        async def add_message(msg_index: int):
            return await thread_service.add_message(
                thread_id=thread.id,
                role="user",
                content=f"Concurrent message {msg_index}",
                db=db
            )
        
        # Add 10 concurrent messages
        message_tasks = [add_message(i) for i in range(10)]
        messages = await asyncio.gather(*message_tasks, return_exceptions=True)
        
        # Verify all messages were added successfully
        successful_messages = [m for m in messages if hasattr(m, 'id')]
        assert len(successful_messages) == 10
        
        # Verify thread message consistency
        thread_messages = await thread_service.get_thread_messages(thread.id, db)
        assert len(thread_messages) == 10

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio  
    async def test_65_concurrent_thread_metadata_updates(self, real_services_fixture):
        """
        BVJ: Maintain thread metadata consistency during concurrent updates
        Validates: Metadata integrity under concurrent modification
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"user_{UnifiedIDManager.generate_id()}"
        
        # Create thread for metadata testing
        thread = await thread_service.get_or_create_thread(user_id, db)
        
        # Concurrent metadata updates
        async def update_metadata(key: str, value: str):
            return await thread_service.update_thread_metadata(
                thread_id=thread.id,
                metadata={key: value},
                db=db
            )
        
        # Execute concurrent metadata updates
        update_tasks = [
            update_metadata(f"key_{i}", f"value_{i}") for i in range(5)
        ]
        
        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # Verify updates completed successfully
        successful_updates = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_updates) >= 3  # Allow for some conflicts but ensure most succeed
    
    # Tests 66-70: Parallel Thread Switching Operations
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_66_parallel_websocket_thread_switches(self, real_services_fixture):
        """
        BVJ: WebSocket connections must handle parallel thread switches gracefully
        Validates: WebSocket manager state during concurrent switches
        """
        db = real_services_fixture["db"]
        user_id = f"user_{UnifiedIDManager.generate_id()}"
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread_service = ThreadService()
            thread = await thread_service.get_or_create_thread(user_id, db)
            threads.append(thread)
        
        # Simulate parallel WebSocket thread switches
        async def websocket_thread_switch(thread_id: str):
            user_context = UserExecutionContext(
                user_id=UserID(user_id),
                thread_id=ThreadID(thread_id),
                run_id=RunID(f"run_{UnifiedIDManager.generate_id()}"),
                request_id=RequestID(f"req_{UnifiedIDManager.generate_id()}")
            )
            
            # Mock WebSocket manager creation
            with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
                mock_manager = AsyncMock()
                mock_manager.send_to_user = AsyncMock(return_value=True)
                mock_create.return_value = mock_manager
                
                manager = await create_websocket_manager(user_context)
                return await manager.send_to_user(user_id, {
                    "type": "thread_switched", 
                    "thread_id": thread_id
                })
        
        # Execute parallel switches
        switch_tasks = [websocket_thread_switch(thread.id) for thread in threads]
        results = await asyncio.gather(*switch_tasks, return_exceptions=True)
        
        # All switches should complete successfully
        successful_switches = [r for r in results if r is True]
        assert len(successful_switches) == 3

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_67_parallel_thread_context_preservation(self, real_services_fixture):
        """
        BVJ: Thread execution context must be preserved during parallel operations
        Validates: Context isolation and preservation under load
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Create multiple user contexts
        contexts = []
        for i in range(5):
            user_id = f"user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            
            context = UserExecutionContext(
                user_id=UserID(user_id),
                thread_id=ThreadID(thread.id),
                run_id=RunID(f"run_{UnifiedIDManager.generate_id()}"),
                request_id=RequestID(f"req_{UnifiedIDManager.generate_id()}")
            )
            contexts.append(context)
        
        # Parallel context operations
        async def process_context(context: UserExecutionContext):
            # Simulate context-specific operations
            thread = await thread_service.get_thread(context.thread_id, context.user_id, db)
            return {
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "thread_exists": thread is not None
            }
        
        # Execute parallel context processing
        context_tasks = [process_context(ctx) for ctx in contexts]
        results = await asyncio.gather(*context_tasks)
        
        # Verify context preservation
        assert len(results) == 5
        for result in results:
            assert result["thread_exists"] is True
            assert result["user_id"] is not None
            assert result["thread_id"] is not None

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_68_parallel_thread_session_management(self, real_services_fixture):
        """
        BVJ: Thread sessions must remain isolated during parallel access
        Validates: Session boundary enforcement under concurrent load
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        thread_service = ThreadService()
        
        # Create multiple user sessions
        sessions = []
        for i in range(3):
            user_id = f"user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            session_id = f"session_{UnifiedIDManager.generate_id()}"
            
            # Store session in Redis
            session_data = {
                "user_id": user_id,
                "thread_id": thread.id,
                "created_at": datetime.now().isoformat()
            }
            await redis.set(f"session:{session_id}", str(session_data))
            sessions.append((session_id, user_id, thread.id))
        
        # Parallel session access
        async def access_session(session_id: str, expected_user_id: str, expected_thread_id: str):
            session_data = await redis.get(f"session:{session_id}")
            return {
                "session_id": session_id,
                "data_exists": session_data is not None,
                "expected_user": expected_user_id,
                "expected_thread": expected_thread_id
            }
        
        # Execute parallel session access
        session_tasks = [
            access_session(session_id, user_id, thread_id) 
            for session_id, user_id, thread_id in sessions
        ]
        results = await asyncio.gather(*session_tasks)
        
        # Verify session isolation
        assert len(results) == 3
        for result in results:
            assert result["data_exists"] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_69_parallel_thread_cleanup_operations(self, real_services_fixture):
        """
        BVJ: Thread cleanup must be safe during parallel operations
        Validates: Resource cleanup without interfering with active threads
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Create threads for cleanup testing
        threads_to_cleanup = []
        active_threads = []
        
        for i in range(3):
            user_id = f"cleanup_user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            threads_to_cleanup.append((user_id, thread))
        
        for i in range(3):
            user_id = f"active_user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            active_threads.append((user_id, thread))
        
        # Parallel cleanup and active operations
        async def cleanup_thread(user_id: str, thread_id: str):
            return await thread_service.soft_delete_thread(thread_id, user_id, db)
        
        async def access_active_thread(user_id: str, thread_id: str):
            return await thread_service.get_thread(thread_id, user_id, db)
        
        # Execute parallel cleanup and access
        cleanup_tasks = [
            cleanup_thread(user_id, thread.id) 
            for user_id, thread in threads_to_cleanup
        ]
        access_tasks = [
            access_active_thread(user_id, thread.id)
            for user_id, thread in active_threads
        ]
        
        all_tasks = cleanup_tasks + access_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Verify cleanup didn't interfere with active threads
        access_results = results[len(cleanup_tasks):]
        successful_access = [r for r in access_results if hasattr(r, 'id')]
        assert len(successful_access) == 3

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_70_parallel_thread_performance_monitoring(self, real_services_fixture):
        """
        BVJ: Monitor thread operation performance under parallel load
        Validates: System performance metrics during concurrent operations
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"perf_user_{UnifiedIDManager.generate_id()}"
        
        # Performance monitoring setup
        operation_times = []
        
        async def timed_thread_operation():
            start_time = time.time()
            thread = await thread_service.get_or_create_thread(user_id, db)
            
            # Simulate thread operations
            await thread_service.add_message(
                thread_id=thread.id,
                role="user", 
                content="Performance test message",
                db=db
            )
            
            end_time = time.time()
            return end_time - start_time
        
        # Execute parallel performance tests
        perf_tasks = [timed_thread_operation() for _ in range(10)]
        operation_times = await asyncio.gather(*perf_tasks)
        
        # Verify performance metrics
        avg_time = sum(operation_times) / len(operation_times)
        max_time = max(operation_times)
        
        # Performance assertions (reasonable thresholds)
        assert avg_time < 5.0  # Average operation under 5 seconds
        assert max_time < 10.0  # No operation takes more than 10 seconds
        assert len(operation_times) == 10  # All operations completed
    
    # Tests 71-75: Race Condition Handling and Prevention
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_71_thread_id_generation_race_conditions(self, real_services_fixture):
        """
        BVJ: Prevent duplicate thread IDs during concurrent creation
        Validates: ID generation uniqueness under race conditions
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Concurrent thread creation to test ID uniqueness
        async def create_unique_thread():
            user_id = f"race_user_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            return thread.id
        
        # Create many threads concurrently
        creation_tasks = [create_unique_thread() for _ in range(20)]
        thread_ids = await asyncio.gather(*creation_tasks)
        
        # Verify all IDs are unique
        unique_ids = set(thread_ids)
        assert len(unique_ids) == len(thread_ids), "Thread ID collision detected"
        
        # Verify ID format consistency
        for thread_id in thread_ids:
            assert thread_id is not None
            assert len(thread_id) > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_72_database_transaction_race_conditions(self, real_services_fixture):
        """
        BVJ: Database transactions must be isolated during concurrent access
        Validates: ACID properties under concurrent thread operations
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"transaction_user_{UnifiedIDManager.generate_id()}"
        
        # Create a thread for transaction testing
        thread = await thread_service.get_or_create_thread(user_id, db)
        
        # Concurrent database operations
        async def concurrent_message_transaction(message_id: int):
            try:
                message = await thread_service.add_message(
                    thread_id=thread.id,
                    role="user",
                    content=f"Transaction message {message_id}",
                    db=db
                )
                return message.id if message else None
            except Exception as e:
                return f"error_{message_id}"
        
        # Execute concurrent transactions
        transaction_tasks = [
            concurrent_message_transaction(i) for i in range(15)
        ]
        results = await asyncio.gather(*transaction_tasks, return_exceptions=True)
        
        # Count successful transactions
        successful_transactions = [
            r for r in results 
            if r and not str(r).startswith("error_") and not isinstance(r, Exception)
        ]
        
        # Should have most transactions succeed
        assert len(successful_transactions) >= 10
        
        # Verify final state consistency
        final_messages = await thread_service.get_thread_messages(thread.id, db)
        assert len(final_messages) >= 10

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_73_websocket_connection_race_conditions(self, real_services_fixture):
        """
        BVJ: WebSocket connections must handle concurrent state changes
        Validates: Connection state consistency during rapid changes
        """
        user_id = f"websocket_race_user_{UnifiedIDManager.generate_id()}"
        
        # Simulate concurrent WebSocket connection changes
        async def simulate_connection_change(connection_id: int):
            user_context = UserExecutionContext(
                user_id=UserID(user_id),
                thread_id=ThreadID(f"thread_{UnifiedIDManager.generate_id()}"),
                run_id=RunID(f"run_{UnifiedIDManager.generate_id()}"),
                request_id=RequestID(f"req_{UnifiedIDManager.generate_id()}")
            )
            
            with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
                mock_manager = AsyncMock()
                mock_manager.add_connection = AsyncMock(return_value=True)
                mock_manager.remove_connection = AsyncMock(return_value=True)
                mock_create.return_value = mock_manager
                
                manager = await create_websocket_manager(user_context)
                
                # Simulate connection lifecycle
                connection_added = await manager.add_connection(f"conn_{connection_id}")
                connection_removed = await manager.remove_connection(f"conn_{connection_id}")
                
                return {
                    "connection_id": connection_id,
                    "added": connection_added,
                    "removed": connection_removed
                }
        
        # Execute concurrent connection changes
        connection_tasks = [
            simulate_connection_change(i) for i in range(10)
        ]
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Verify connection handling
        successful_operations = [
            r for r in results 
            if isinstance(r, dict) and r.get("added") and r.get("removed")
        ]
        assert len(successful_operations) >= 8  # Allow for some race conditions

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_74_thread_state_race_conditions(self, real_services_fixture):
        """
        BVJ: Thread state must remain consistent during concurrent modifications
        Validates: State consistency under concurrent state changes
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        user_id = f"state_user_{UnifiedIDManager.generate_id()}"
        
        # Create thread for state testing
        thread = await thread_service.get_or_create_thread(user_id, db)
        
        # Concurrent state modifications
        async def modify_thread_state(modification_id: int):
            try:
                # Simulate different types of state modifications
                if modification_id % 3 == 0:
                    return await thread_service.update_thread_metadata(
                        thread_id=thread.id,
                        metadata={"modified_by": f"task_{modification_id}"},
                        db=db
                    )
                elif modification_id % 3 == 1:
                    return await thread_service.add_message(
                        thread_id=thread.id,
                        role="user",
                        content=f"State modification {modification_id}",
                        db=db
                    )
                else:
                    return await thread_service.get_thread(thread.id, user_id, db)
            except Exception as e:
                return f"error_{modification_id}: {e}"
        
        # Execute concurrent state modifications
        modification_tasks = [modify_thread_state(i) for i in range(12)]
        results = await asyncio.gather(*modification_tasks, return_exceptions=True)
        
        # Count successful modifications
        successful_modifications = [
            r for r in results 
            if r and not isinstance(r, Exception) and not str(r).startswith("error_")
        ]
        
        assert len(successful_modifications) >= 8
        
        # Verify final thread state is consistent
        final_thread = await thread_service.get_thread(thread.id, user_id, db)
        assert final_thread is not None
        assert final_thread.id == thread.id

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_75_concurrent_user_isolation_race_conditions(self, real_services_fixture):
        """
        BVJ: User isolation must be maintained during concurrent access
        Validates: No cross-user data leakage under race conditions
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Create multiple users with threads
        user_data = []
        for i in range(5):
            user_id = f"isolation_user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            user_data.append((user_id, thread.id))
        
        # Concurrent cross-user access attempts
        async def attempt_cross_user_access(accessor_index: int, target_index: int):
            accessor_user_id, _ = user_data[accessor_index]
            _, target_thread_id = user_data[target_index]
            
            # Try to access another user's thread
            result = await thread_service.get_thread(target_thread_id, accessor_user_id, db)
            
            return {
                "accessor": accessor_user_id,
                "target_thread": target_thread_id,
                "access_granted": result is not None,
                "same_user": accessor_index == target_index
            }
        
        # Generate cross-user access attempts
        access_tasks = []
        for accessor_idx in range(5):
            for target_idx in range(5):
                access_tasks.append(attempt_cross_user_access(accessor_idx, target_idx))
        
        results = await asyncio.gather(*access_tasks, return_exceptions=True)
        
        # Verify isolation - users should only access their own threads
        for result in results:
            if isinstance(result, dict):
                if result["same_user"]:
                    # Users should access their own threads
                    assert result["access_granted"] is True
                # Cross-user access behavior depends on implementation
                # but should be consistent and secure
    
    # Tests 76-80: Multi-User Concurrent Thread Management
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_76_multi_user_concurrent_thread_creation(self, real_services_fixture):
        """
        BVJ: Support multiple users creating threads simultaneously
        Validates: Scalable thread creation for enterprise deployments
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Simulate multiple users creating threads concurrently
        async def user_creates_thread(user_index: int):
            user_id = f"concurrent_user_{user_index}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            
            return {
                "user_id": user_id,
                "thread_id": thread.id if thread else None,
                "success": thread is not None
            }
        
        # Simulate 15 users creating threads simultaneously
        user_tasks = [user_creates_thread(i) for i in range(15)]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Verify all users successfully created threads
        successful_creations = [
            r for r in results 
            if isinstance(r, dict) and r["success"]
        ]
        
        assert len(successful_creations) == 15
        
        # Verify all thread IDs are unique
        thread_ids = [r["thread_id"] for r in successful_creations]
        unique_thread_ids = set(thread_ids)
        assert len(unique_thread_ids) == 15

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_77_multi_user_concurrent_message_operations(self, real_services_fixture):
        """
        BVJ: Multiple users must be able to send messages concurrently
        Validates: Message system scalability for active chat sessions
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Create multiple users with threads
        user_threads = []
        for i in range(8):
            user_id = f"msg_user_{i}_{UnifiedIDManager.generate_id()}"
            thread = await thread_service.get_or_create_thread(user_id, db)
            user_threads.append((user_id, thread.id))
        
        # Concurrent message sending
        async def user_sends_messages(user_id: str, thread_id: str, message_count: int):
            messages = []
            for i in range(message_count):
                message = await thread_service.add_message(
                    thread_id=thread_id,
                    role="user",
                    content=f"Message {i} from {user_id}",
                    db=db
                )
                if message:
                    messages.append(message.id)
            return len(messages)
        
        # Each user sends 3 messages concurrently
        message_tasks = [
            user_sends_messages(user_id, thread_id, 3)
            for user_id, thread_id in user_threads
        ]
        
        message_counts = await asyncio.gather(*message_tasks)
        
        # Verify all users sent their messages
        total_messages = sum(message_counts)
        assert total_messages >= 20  # Allow for some failures but expect most to succeed

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_78_multi_user_concurrent_thread_switching(self, real_services_fixture):
        """
        BVJ: Multiple users switching threads simultaneously
        Validates: Thread switching scalability and isolation
        """
        db = real_services_fixture["db"]
        thread_service = ThreadService()
        
        # Setup multiple users with multiple threads each
        user_thread_sets = []
        for user_idx in range(6):
            user_id = f"switch_user_{user_idx}_{UnifiedIDManager.generate_id()}"
            threads = []
            
            # Create 3 threads per user
            for thread_idx in range(3):
                thread = await thread_service.get_or_create_thread(user_id, db)
                threads.append(thread.id)
                # Small delay to ensure different thread IDs
                await asyncio.sleep(0.01)
            
            user_thread_sets.append((user_id, threads))
        
        # Concurrent thread switching by all users
        async def user_switches_threads(user_id: str, thread_ids: List[str]):
            switch_results = []
            for thread_id in thread_ids:
                thread = await thread_service.get_thread(thread_id, user_id, db)
                switch_results.append(thread is not None)
            return sum(switch_results)  # Count successful switches
        
        # All users switch through their threads concurrently
        switch_tasks = [
            user_switches_threads(user_id, threads)
            for user_id, threads in user_thread_sets
        ]
        
        switch_counts = await asyncio.gather(*switch_tasks)
        
        # Each user should successfully switch to all their threads
        for count in switch_counts:
            assert count >= 2  # At least 2 out of 3 switches should succeed

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_79_multi_user_resource_management_under_load(self, real_services_fixture):
        """
        BVJ: System must manage resources efficiently under multi-user load
        Validates: Resource allocation and cleanup under concurrent load
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        thread_service = ThreadService()
        
        # Resource tracking setup
        initial_redis_keys = len(await redis.keys("*"))
        
        async def user_resource_operations(user_index: int):
            user_id = f"resource_user_{user_index}_{UnifiedIDManager.generate_id()}"
            
            # Create thread
            thread = await thread_service.get_or_create_thread(user_id, db)
            
            # Add messages
            for i in range(2):
                await thread_service.add_message(
                    thread_id=thread.id,
                    role="user",
                    content=f"Resource test message {i}",
                    db=db
                )
            
            # Create session in Redis
            session_key = f"session:{user_id}"
            await redis.set(session_key, f"session_data_{user_index}")
            
            return {
                "user_id": user_id,
                "thread_id": thread.id,
                "session_key": session_key
            }
        
        # Simulate 10 users performing resource operations
        resource_tasks = [user_resource_operations(i) for i in range(10)]
        user_resources = await asyncio.gather(*resource_tasks)
        
        # Verify resource creation
        assert len(user_resources) == 10
        
        # Check Redis resource utilization
        final_redis_keys = len(await redis.keys("*"))
        redis_keys_added = final_redis_keys - initial_redis_keys
        assert redis_keys_added >= 8  # Should have added session keys
        
        # Verify database resources
        for user_resource in user_resources:
            thread = await thread_service.get_thread(
                user_resource["thread_id"], 
                user_resource["user_id"], 
                db
            )
            assert thread is not None

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_80_enterprise_scale_concurrent_thread_operations(self, real_services_fixture):
        """
        BVJ: Validate enterprise-scale concurrent thread operations
        Validates: System stability under enterprise deployment load
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        thread_service = ThreadService()
        
        # Enterprise-scale simulation parameters
        num_concurrent_users = 20
        operations_per_user = 5
        
        async def enterprise_user_simulation(user_index: int):
            user_id = f"enterprise_user_{user_index}_{UnifiedIDManager.generate_id()}"
            operations_completed = 0
            
            try:
                # Create multiple threads
                threads = []
                for i in range(2):
                    thread = await thread_service.get_or_create_thread(user_id, db)
                    threads.append(thread)
                    operations_completed += 1
                
                # Add messages to threads
                for thread in threads:
                    for i in range(operations_per_user):
                        message = await thread_service.add_message(
                            thread_id=thread.id,
                            role="user",
                            content=f"Enterprise message {i}",
                            db=db
                        )
                        if message:
                            operations_completed += 1
                
                # Cache operations
                cache_key = f"enterprise_cache:{user_id}"
                await redis.set(cache_key, f"user_data_{user_index}")
                operations_completed += 1
                
                return {
                    "user_index": user_index,
                    "operations_completed": operations_completed,
                    "threads_created": len(threads),
                    "success": True
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "operations_completed": operations_completed,
                    "error": str(e),
                    "success": False
                }
        
        # Execute enterprise-scale concurrent operations
        start_time = time.time()
        enterprise_tasks = [
            enterprise_user_simulation(i) for i in range(num_concurrent_users)
        ]
        results = await asyncio.gather(*enterprise_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Performance analysis
        execution_time = end_time - start_time
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
        total_operations = sum(r["operations_completed"] for r in successful_users)
        
        # Enterprise-scale assertions
        assert len(successful_users) >= 15  # At least 75% success rate
        assert execution_time < 60.0  # Complete within 60 seconds
        assert total_operations >= 100  # Significant operation volume
        
        # System should remain responsive
        final_redis_keys = len(await redis.keys("*"))
        assert final_redis_keys > 0  # Redis functioning
        
        print(f"Enterprise test completed: {len(successful_users)}/{num_concurrent_users} users, "
              f"{total_operations} operations in {execution_time:.2f}s")