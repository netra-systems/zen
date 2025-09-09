"""
Integration Tests: Database Session Leak Detection

These integration tests validate session lifecycle management across
real database operations with thread handlers. Tests are designed to FAIL
initially to expose session management issues.

CRITICAL: Uses real PostgreSQL database as per CLAUDE.md:
"Real Everything (LLM, Services) E2E > E2E > Integration > Unit"
No mocks allowed in integration tests.

Business Value:
- Validates database session safety under realistic conditions
- Exposes session leaks in actual database transaction flows
- Ensures proper connection pool management
- Tests session handling with real SQL operations
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from unittest.mock import patch

from test_framework.session_leak_detection import SessionLeakTestBase
from netra_backend.app.routes.utils.thread_handlers import (
    handle_list_threads_request,
    handle_create_thread_request,
    handle_get_thread_request,
    handle_update_thread_request,
    handle_delete_thread_request,
    handle_get_messages_request,
    handle_send_message_request
)
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository


class TestSessionLeakDetectionIntegration(SessionLeakTestBase):
    """
    Integration tests for session leak detection with real database operations.
    
    CRITICAL: These tests are designed to FAIL initially because current
    thread handlers lack centralized session lifecycle management.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_integration_leak_detection(self):
        """Set up integration test environment with real database."""
        await self.setup_session_leak_testing(
            max_session_age_seconds=15.0,  # Longer timeout for integration tests
            monitoring_interval=0.5
        )
        
        # Initialize repositories for real database operations
        self.message_repo = MessageRepository()
        self.thread_repo = ThreadRepository()
        
        yield
        await self.teardown_session_leak_testing()
    
    async def test_session_leak_scenario(self):
        """Required abstract method implementation."""
        pass
    
    @pytest.mark.asyncio
    async def test_real_database_thread_creation_session_leak(self):
        """
        Test: Real database thread creation with session tracking
        
        EXPECTED TO FAIL: Real database operations will expose session management issues
        """
        user_id = "integration-test-user-123"
        thread_data = {
            "title": "Integration Test Thread",
            "metadata": {
                "test_type": "integration",
                "created_by": "session_leak_test"
            }
        }
        
        # Execute real thread creation
        result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        # Verify thread was created
        assert result is not None
        assert "id" in result
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Real database operations will expose session lifecycle issues
        await self.assert_no_session_leaks(
            "Real database thread creation must properly manage sessions"
        )
    
    @pytest.mark.asyncio
    async def test_real_database_thread_retrieval_session_leak(self):
        """
        Test: Real database thread retrieval with session tracking
        
        EXPECTED TO FAIL: Database query operations expose session management gaps
        """
        user_id = "integration-test-user-456"
        
        # First create a thread to retrieve
        thread_data = {"title": "Test Thread for Retrieval", "metadata": {}}
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Now retrieve the thread
        retrieve_result = await self.execute_thread_handler_with_tracking(
            handle_get_thread_request,
            thread_id, user_id
        )
        
        # Verify retrieval worked
        assert retrieve_result is not None
        assert retrieve_result["id"] == thread_id
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "Real database thread retrieval must properly manage sessions"
        )
    
    @pytest.mark.asyncio
    async def test_real_database_thread_update_transaction_leak(self):
        """
        Test: Real database thread update with transaction management
        
        EXPECTED TO FAIL: Transaction commits/rollbacks are not centrally managed
        """
        user_id = "integration-test-user-789"
        
        # Create thread
        thread_data = {"title": "Original Title", "metadata": {"version": 1}}
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Update thread with new data
        from unittest.mock import Mock
        thread_update = Mock()
        thread_update.title = "Updated Title"
        thread_update.metadata = {"version": 2, "updated": True}
        
        update_result = await self.execute_thread_handler_with_tracking(
            handle_update_thread_request,
            thread_id, thread_update, user_id
        )
        
        # Verify update worked
        assert update_result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Update operations require proper transaction commit/rollback
        await self.assert_no_session_leaks(
            "Real database thread updates must properly commit transactions"
        )
    
    @pytest.mark.asyncio
    async def test_real_database_message_operations_session_leak(self):
        """
        Test: Real database message operations with session tracking
        
        EXPECTED TO FAIL: Message creation and retrieval lack centralized session management
        """
        user_id = "integration-test-user-msg"
        
        # Create thread for messages
        thread_data = {"title": "Message Test Thread", "metadata": {}}
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Send multiple messages
        from unittest.mock import Mock
        for i in range(3):
            message_request = Mock()
            message_request.message = f"Test message {i+1}"
            message_request.metadata = {"message_number": i+1}
            
            send_result = await self.execute_thread_handler_with_tracking(
                handle_send_message_request,
                thread_id, message_request, user_id
            )
            
            assert send_result is not None
            assert send_result["content"] == f"Test message {i+1}"
        
        # Retrieve messages
        messages_result = await self.execute_thread_handler_with_tracking(
            handle_get_messages_request,
            thread_id, user_id, 10, 0
        )
        
        assert messages_result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "Real database message operations must properly manage sessions"
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_database_operations_session_leak(self):
        """
        Test: Concurrent real database operations under load
        
        EXPECTED TO FAIL: Concurrent database access amplifies session management issues
        """
        base_user_id = "concurrent-test-user"
        
        async def create_thread_and_messages(user_index: int):
            """Create a thread and add messages for concurrent testing."""
            user_id = f"{base_user_id}-{user_index}"
            
            # Create thread
            thread_data = {
                "title": f"Concurrent Thread {user_index}",
                "metadata": {"user_index": user_index}
            }
            
            create_result = await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
            
            thread_id = create_result["id"]
            
            # Add messages to thread
            from unittest.mock import Mock
            for msg_i in range(2):
                message_request = Mock()
                message_request.message = f"Message {msg_i} from user {user_index}"
                message_request.metadata = {"user_index": user_index, "message_index": msg_i}
                
                await self.execute_thread_handler_with_tracking(
                    handle_send_message_request,
                    thread_id, message_request, user_id
                )
            
            return {"user_id": user_id, "thread_id": thread_id}
        
        # Execute concurrent database operations
        concurrent_tasks = [
            create_thread_and_messages(i) 
            for i in range(8)  # 8 concurrent users
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 6, "Most concurrent operations should succeed"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Concurrent database operations will expose session pool issues
        await self.assert_no_session_leaks(
            "Concurrent database operations must not cause session leaks or pool exhaustion"
        )
    
    @pytest.mark.asyncio
    async def test_database_exception_rollback_session_leak(self):
        """
        Test: Database session rollback when exceptions occur
        
        EXPECTED TO FAIL: Exception handling doesn't properly rollback transactions
        """
        user_id = "exception-test-user"
        
        # Create valid thread first
        thread_data = {"title": "Exception Test Thread", "metadata": {}}
        create_result = await self.execute_thread_handler_with_tracking(
            handle_create_thread_request,
            thread_data, user_id
        )
        
        thread_id = create_result["id"]
        
        # Now cause database exception during update
        with patch('netra_backend.app.services.database.thread_repository.ThreadRepository.update') as mock_update:
            mock_update.side_effect = Exception("Simulated database error")
            
            from unittest.mock import Mock
            thread_update = Mock()
            thread_update.title = "This should fail"
            thread_update.metadata = {}
            
            # Execute update that should fail
            try:
                await self.execute_thread_handler_with_tracking(
                    handle_update_thread_request,
                    thread_id, thread_update, user_id
                )
                pytest.fail("Update should have raised an exception")
            except Exception as e:
                assert "database error" in str(e).lower()
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Sessions must be properly rolled back when exceptions occur
        await self.assert_no_session_leaks(
            "Database exceptions must trigger proper session rollback"
        )
    
    @pytest.mark.asyncio
    async def test_long_running_database_operations_session_leak(self):
        """
        Test: Long-running database operations and session timeout
        
        EXPECTED TO FAIL: Long operations may not properly manage session lifecycle
        """
        user_id = "long-running-test-user"
        
        # Simulate long-running operation by creating many threads
        thread_ids = []
        
        for i in range(15):  # Create many threads to simulate load
            thread_data = {
                "title": f"Long Running Test Thread {i}",
                "metadata": {"batch_index": i}
            }
            
            create_result = await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
            
            thread_ids.append(create_result["id"])
            
            # Add small delay to simulate processing time
            await asyncio.sleep(0.1)
        
        # Now retrieve all threads (simulates list operation)
        list_result = await self.execute_thread_handler_with_tracking(
            handle_list_threads_request,
            user_id, 0, 20
        )
        
        assert list_result is not None
        
        # CRITICAL: This assertion SHOULD FAIL initially
        await self.assert_no_session_leaks(
            "Long-running database operations must maintain proper session lifecycle"
        )
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self):
        """
        Test: Database connection pool behavior under stress
        
        EXPECTED TO FAIL: Session leaks will cause pool exhaustion
        """
        base_user_id = "pool-stress-user"
        
        # Create many concurrent operations to stress pool
        async def stress_operation(operation_id: int):
            user_id = f"{base_user_id}-{operation_id}"
            
            # Create thread
            thread_data = {"title": f"Pool Stress Thread {operation_id}", "metadata": {}}
            create_result = await self.execute_thread_handler_with_tracking(
                handle_create_thread_request,
                thread_data, user_id
            )
            
            # Get thread
            thread_id = create_result["id"]
            await self.execute_thread_handler_with_tracking(
                handle_get_thread_request,
                thread_id, user_id
            )
            
            return operation_id
        
        # Execute many operations concurrently to stress connection pool
        stress_tasks = [stress_operation(i) for i in range(20)]
        
        start_time = time.time()
        results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Check pool monitoring results
        pool_analysis = await self.session_monitor.detect_session_leaks(
            baseline_duration=end_time - start_time
        )
        
        # Verify some operations completed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 10, "Most operations should complete despite stress"
        
        # CRITICAL: This assertion SHOULD FAIL initially
        # Pool stress will expose session management weaknesses
        await self.assert_no_session_leaks(
            "Database connection pool stress must not cause session leaks"
        )
        
        # Additional pool health assertion
        self.session_monitor.assert_healthy_pool_state(max_utilization=95.0)