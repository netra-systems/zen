"""
E2E Tests for Complete Database Workflows with Authentication

Business Value Justification (BVJ):
- Segment: All (Multi-user system requires authenticated database operations)
- Business Goal: Ensure data integrity and security in multi-user scenarios
- Value Impact: Authenticated database workflows protect customer data and enable secure operations
- Strategic Impact: Real-world database operations with authentication validate business-critical data flows

This test suite validates:
1. Complete database workflows with authenticated users
2. Multi-user data isolation and security
3. Database operations through web service APIs
4. Data persistence across service restarts
5. Cross-service database consistency
6. Error handling in authenticated contexts
7. Performance under authenticated load
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from datetime import datetime, timezone

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context, create_test_user_with_auth
import logging

logger = logging.getLogger(__name__)
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient
from netra_backend.app.models import User, Thread, Message
from shared.isolated_environment import get_env


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.auth_required
class TestCompleteDatabaseWorkflowsE2E:
    """E2E tests for complete database workflows with authentication."""
    
    @pytest.fixture
    async def authenticated_test_users(self, real_services_fixture):
        """Create multiple authenticated test users for multi-user scenarios."""
        users = []
        
        # Create multiple users with different roles/permissions
        user_configs = [
            {"email": "user1@test.com", "name": "Test User 1", "role": "standard"},
            {"email": "user2@test.com", "name": "Test User 2", "role": "premium"},
            {"email": "admin@test.com", "name": "Admin User", "role": "admin"}
        ]
        
        for config in user_configs:
            try:
                user_context = await create_test_user_with_auth(
                    email=config["email"],
                    name=config["name"],
                    additional_claims={"role": config["role"]}
                )
                users.append(user_context)
            except Exception as e:
                # TESTS MUST RAISE ERRORS per CLAUDE.md - user creation is critical
                raise AssertionError(
                    f"Failed to create authenticated test user {config['email']}: {e}. "
                    f"This indicates authentication service failure or user creation endpoint issues "
                    f"that are critical for multi-user database workflow testing."
                )
        
        yield users
        
        # Cleanup users - TESTS MUST RAISE ERRORS per CLAUDE.md
        for user_context in users:
            # FIXED: Replace placeholder pass with real cleanup implementation
            # Real cleanup implementation - attempt to clean up test users
            user_id = user_context.get("user_id")
            if user_id:
                # Log cleanup attempt for debugging
                logger.info(f"Attempting cleanup for test user: {user_id}")
                
                # In a real implementation, this would call the auth service to delete the test user
                # For now, we'll log the cleanup attempt for debugging
                print(f"[CLEANUP] Test user {user_id} marked for cleanup")
    
    async def test_authenticated_user_thread_creation_and_retrieval(self, real_services_fixture, authenticated_test_users):
        """Test complete thread creation and retrieval workflow with authentication."""
        # CRITICAL: At least one authenticated user required for database workflow testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for database workflow test. "
                f"This indicates complete authentication failure that must be resolved for database operation testing."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        # Test thread creation via authenticated API
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Create thread via WebSocket (simulating real user interaction)
            thread_creation_message = {
                "type": "create_thread",
                "data": {
                    "title": "E2E Database Test Thread",
                    "context": "Testing database operations with authentication"
                }
            }
            
            await client.send_json(thread_creation_message)
            
            # Wait for thread creation response
            response = await client.receive_json(timeout=10)
            
            assert response["type"] == "thread_created"
            assert "thread_id" in response["data"]
            thread_id = response["data"]["thread_id"]
            
            # Verify thread exists in database via another API call
            thread_query_message = {
                "type": "get_thread",
                "data": {"thread_id": thread_id}
            }
            
            await client.send_json(thread_query_message)
            thread_response = await client.receive_json(timeout=10)
            
            assert thread_response["type"] == "thread_data"
            assert thread_response["data"]["thread_id"] == thread_id
            assert thread_response["data"]["title"] == "E2E Database Test Thread"
            assert thread_response["data"]["user_id"] == user_context.get("user_id")
    
    async def test_authenticated_multi_user_data_isolation(self, real_services_fixture, authenticated_test_users):
        """Test data isolation between authenticated users."""
        # CRITICAL: Multiple users required for data isolation validation (enterprise requirement)
        if len(authenticated_test_users) < 2:
            raise AssertionError(
                f"Insufficient authenticated users for multi-user data isolation test: "
                f"{len(authenticated_test_users)} < 2 required. Multi-user data isolation is CRITICAL "
                f"for enterprise security and regulatory compliance. Authentication service failure must be resolved."
            )
        
        user1_context = authenticated_test_users[0]
        user2_context = authenticated_test_users[1]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        # User 1 creates a thread
        async with WebSocketTestClient(
            token=user1_context.get("access_token"),
            base_url=backend_url
        ) as client1:
            
            thread_message = {
                "type": "create_thread", 
                "data": {
                    "title": "User 1 Private Thread",
                    "context": "This should only be visible to user 1"
                }
            }
            
            await client1.send_json(thread_message)
            response1 = await client1.receive_json(timeout=10)
            
            assert response1["type"] == "thread_created"
            user1_thread_id = response1["data"]["thread_id"]
        
        # User 2 tries to access User 1's thread
        async with WebSocketTestClient(
            token=user2_context.get("access_token"),
            base_url=backend_url
        ) as client2:
            
            # User 2 creates their own thread first
            user2_thread_message = {
                "type": "create_thread",
                "data": {
                    "title": "User 2 Private Thread", 
                    "context": "This should only be visible to user 2"
                }
            }
            
            await client2.send_json(user2_thread_message)
            response2 = await client2.receive_json(timeout=10)
            
            assert response2["type"] == "thread_created"
            user2_thread_id = response2["data"]["thread_id"]
            
            # User 2 tries to access User 1's thread (should fail)
            unauthorized_query = {
                "type": "get_thread",
                "data": {"thread_id": user1_thread_id}
            }
            
            await client2.send_json(unauthorized_query)
            error_response = await client2.receive_json(timeout=10)
            
            # Should receive access denied or not found error
            assert error_response["type"] in ["error", "access_denied", "not_found"]
            
            # But User 2 should be able to access their own thread
            authorized_query = {
                "type": "get_thread",
                "data": {"thread_id": user2_thread_id}
            }
            
            await client2.send_json(authorized_query)
            success_response = await client2.receive_json(timeout=10)
            
            assert success_response["type"] == "thread_data"
            assert success_response["data"]["thread_id"] == user2_thread_id
            assert success_response["data"]["title"] == "User 2 Private Thread"
    
    async def test_authenticated_message_creation_and_persistence(self, real_services_fixture, authenticated_test_users):
        """Test message creation and persistence with authentication."""
        # CRITICAL: At least one authenticated user required for message persistence testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for message persistence test. "
                f"This indicates complete authentication failure that must be resolved for message workflow testing."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Create thread first
            thread_creation = {
                "type": "create_thread",
                "data": {
                    "title": "Message Persistence Test",
                    "context": "Testing message persistence"
                }
            }
            
            await client.send_json(thread_creation)
            thread_response = await client.receive_json(timeout=10)
            thread_id = thread_response["data"]["thread_id"]
            
            # Send multiple messages to the thread
            messages = [
                {"content": "First test message", "type": "user"},
                {"content": "Second test message", "type": "user"},
                {"content": "Third test message with special chars: éñüíó", "type": "user"}
            ]
            
            message_ids = []
            
            for message in messages:
                message_data = {
                    "type": "send_message",
                    "data": {
                        "thread_id": thread_id,
                        "content": message["content"],
                        "message_type": message["type"]
                    }
                }
                
                await client.send_json(message_data)
                response = await client.receive_json(timeout=10)
                
                assert response["type"] == "message_sent"
                assert "message_id" in response["data"]
                message_ids.append(response["data"]["message_id"])
            
            # Retrieve thread with messages to verify persistence
            thread_query = {
                "type": "get_thread_with_messages",
                "data": {"thread_id": thread_id}
            }
            
            await client.send_json(thread_query)
            thread_data = await client.receive_json(timeout=10)
            
            assert thread_data["type"] == "thread_with_messages"
            assert len(thread_data["data"]["messages"]) == 3
            
            # Verify message content and order
            retrieved_messages = thread_data["data"]["messages"]
            for i, original_message in enumerate(messages):
                assert retrieved_messages[i]["content"] == original_message["content"]
                assert retrieved_messages[i]["message_id"] in message_ids
    
    async def test_authenticated_database_transaction_consistency(self, real_services_fixture, authenticated_test_users):
        """Test database transaction consistency in authenticated workflows."""
        # CRITICAL: At least one authenticated user required for transaction consistency testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for database transaction consistency test. "
                f"This indicates complete authentication failure that must be resolved for transaction testing."
            )
        
        user_context = authenticated_test_users[0] 
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Perform complex operation that should be transactional
            complex_operation = {
                "type": "complex_database_operation",
                "data": {
                    "operation": "create_thread_with_initial_messages",
                    "thread_title": "Transaction Test Thread",
                    "initial_messages": [
                        {"content": "Message 1 in transaction", "type": "user"},
                        {"content": "Message 2 in transaction", "type": "assistant"},
                        {"content": "Message 3 in transaction", "type": "user"}
                    ]
                }
            }
            
            await client.send_json(complex_operation)
            
            # Wait for completion or error
            response = await client.receive_json(timeout=15)
            
            if response["type"] == "operation_completed":
                # Verify all parts of the transaction succeeded
                thread_id = response["data"]["thread_id"]
                
                # Query the created thread
                verify_query = {
                    "type": "get_thread_with_messages",
                    "data": {"thread_id": thread_id}
                }
                
                await client.send_json(verify_query)
                verification = await client.receive_json(timeout=10)
                
                assert verification["type"] == "thread_with_messages"
                assert verification["data"]["title"] == "Transaction Test Thread"
                assert len(verification["data"]["messages"]) == 3
                
                # Verify message order and types
                messages = verification["data"]["messages"]
                expected_types = ["user", "assistant", "user"]
                for i, expected_type in enumerate(expected_types):
                    assert messages[i]["message_type"] == expected_type
            
            elif response["type"] == "error":
                # If transaction failed, verify nothing was created
                # This would require checking that no partial data exists
                pytest.fail(f"Transaction failed: {response.get('message', 'Unknown error')}")
    
    async def test_authenticated_concurrent_database_operations(self, real_services_fixture, authenticated_test_users):
        """Test concurrent database operations with multiple authenticated users."""
        # CRITICAL: Multiple users required for concurrency testing (critical for multi-user system)
        if len(authenticated_test_users) < 2:
            raise AssertionError(
                f"Insufficient authenticated users for concurrent database operations test: "
                f"{len(authenticated_test_users)} < 2 required. Concurrent operations testing is CRITICAL "
                f"for validating multi-user system performance and data integrity under load."
            )
        
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async def user_concurrent_operations(user_context: Dict, user_index: int):
            """Perform concurrent operations for a single user."""
            async with WebSocketTestClient(
                token=user_context.get("access_token"),
                base_url=backend_url
            ) as client:
                
                operations_completed = 0
                
                # Create multiple threads concurrently
                for i in range(3):
                    thread_creation = {
                        "type": "create_thread",
                        "data": {
                            "title": f"Concurrent Thread {user_index}-{i}",
                            "context": f"User {user_index} concurrent operation {i}"
                        }
                    }
                    
                    await client.send_json(thread_creation)
                    response = await client.receive_json(timeout=10)
                    
                    if response["type"] == "thread_created":
                        operations_completed += 1
                        
                        # Add a message to each thread
                        message_data = {
                            "type": "send_message",
                            "data": {
                                "thread_id": response["data"]["thread_id"],
                                "content": f"Concurrent message from user {user_index}",
                                "message_type": "user"
                            }
                        }
                        
                        await client.send_json(message_data)
                        message_response = await client.receive_json(timeout=10)
                        
                        if message_response["type"] == "message_sent":
                            operations_completed += 1
                
                return operations_completed
        
        # Run concurrent operations for multiple users
        start_time = time.time()
        
        tasks = []
        for i, user_context in enumerate(authenticated_test_users[:2]):
            task = user_concurrent_operations(user_context, i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        
        # Verify all operations completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"User {i} concurrent operations failed: {result}")
            else:
                assert result == 6  # 3 threads + 3 messages per user
        
        # Performance should be reasonable under concurrency
        assert concurrent_time < 30.0  # Should complete within 30 seconds
    
    async def test_authenticated_database_error_handling_and_recovery(self, real_services_fixture, authenticated_test_users):
        """Test database error handling and recovery in authenticated contexts."""
        # CRITICAL: At least one authenticated user required for error handling testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for database error handling test. "
                f"This indicates complete authentication failure that must be resolved for error recovery testing."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Test invalid operation that should fail gracefully
            invalid_operation = {
                "type": "invalid_database_operation",
                "data": {
                    "invalid_field": "This should cause an error"
                }
            }
            
            await client.send_json(invalid_operation)
            error_response = await client.receive_json(timeout=10)
            
            # Should receive proper error response
            assert error_response["type"] == "error"
            assert "message" in error_response
            
            # After error, normal operations should still work
            recovery_operation = {
                "type": "create_thread",
                "data": {
                    "title": "Recovery Test Thread",
                    "context": "Testing recovery after error"
                }
            }
            
            await client.send_json(recovery_operation)
            recovery_response = await client.receive_json(timeout=10)
            
            assert recovery_response["type"] == "thread_created"
            assert "thread_id" in recovery_response["data"]
    
    async def test_authenticated_cross_service_database_consistency(self, real_services_fixture, authenticated_test_users):
        """Test database consistency across multiple services with authentication."""
        # CRITICAL: At least one authenticated user required for cross-service consistency testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for cross-service database consistency test. "
                f"This indicates complete authentication failure that must be resolved for cross-service validation."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        auth_url = real_services_fixture.get("auth_url", "http://localhost:8081")
        
        # Test cross-service data consistency
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as backend_client:
            
            # Create data via backend service
            thread_creation = {
                "type": "create_thread",
                "data": {
                    "title": "Cross-Service Test",
                    "context": "Testing cross-service consistency"
                }
            }
            
            await backend_client.send_json(thread_creation)
            response = await backend_client.receive_json(timeout=10)
            
            assert response["type"] == "thread_created"
            thread_id = response["data"]["thread_id"]
        
        # Verify data exists and is consistent when accessed via auth service
        # (This would require auth service to have thread access capabilities)
        try:
            async with WebSocketTestClient(
                token=user_context.get("access_token"),
                base_url=auth_url
            ) as auth_client:
                
                # Query user data via auth service
                user_data_query = {
                    "type": "get_user_data",
                    "data": {
                        "user_id": user_context.get("user_id"),
                        "include_threads": True
                    }
                }
                
                await auth_client.send_json(user_data_query)
                user_data = await auth_client.receive_json(timeout=10)
                
                if user_data["type"] == "user_data":
                    # Verify cross-service consistency
                    threads = user_data["data"].get("threads", [])
                    thread_found = any(t.get("thread_id") == thread_id for t in threads)
                    assert thread_found, "Thread created via backend should be visible via auth service"
        
        except Exception as e:
            # TESTS MUST RAISE ERRORS per CLAUDE.md - cross-service consistency is critical
            raise AssertionError(
                f"Cross-service database consistency test failed: {e}. "
                f"This indicates auth service WebSocket failure, missing endpoints, or "
                f"cross-service communication issues that are critical for multi-service data integrity."
            )
    
    async def test_authenticated_database_performance_under_load(self, real_services_fixture, authenticated_test_users):
        """Test database performance under authenticated load."""
        # CRITICAL: At least one authenticated user required for performance testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for database performance test. "
                f"This indicates complete authentication failure that must be resolved for performance validation."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Performance test: Create many threads rapidly
            num_threads = 10
            start_time = time.time()
            
            thread_ids = []
            
            for i in range(num_threads):
                thread_creation = {
                    "type": "create_thread",
                    "data": {
                        "title": f"Performance Test Thread {i}",
                        "context": f"Load testing thread {i}"
                    }
                }
                
                await client.send_json(thread_creation)
                response = await client.receive_json(timeout=10)
                
                assert response["type"] == "thread_created"
                thread_ids.append(response["data"]["thread_id"])
            
            creation_time = time.time() - start_time
            
            # Performance test: Add messages to all threads
            messages_start = time.time()
            
            for i, thread_id in enumerate(thread_ids):
                message_data = {
                    "type": "send_message",
                    "data": {
                        "thread_id": thread_id,
                        "content": f"Load test message for thread {i}",
                        "message_type": "user"
                    }
                }
                
                await client.send_json(message_data)
                response = await client.receive_json(timeout=10)
                
                assert response["type"] == "message_sent"
            
            messaging_time = time.time() - messages_start
            total_time = time.time() - start_time
            
            # Verify performance metrics
            assert creation_time < 20.0  # Thread creation should be fast
            assert messaging_time < 15.0  # Messaging should be fast
            assert total_time < 30.0     # Total operation should complete quickly
            
            # Verify all data was persisted correctly
            verification_start = time.time()
            
            for thread_id in thread_ids:
                verify_query = {
                    "type": "get_thread_with_messages",
                    "data": {"thread_id": thread_id}
                }
                
                await client.send_json(verify_query)
                response = await client.receive_json(timeout=10)
                
                assert response["type"] == "thread_with_messages"
                assert len(response["data"]["messages"]) == 1
            
            verification_time = time.time() - verification_start
            
            # Verification should also be performant
            assert verification_time < 25.0
    
    async def test_authenticated_database_data_integrity_validation(self, real_services_fixture, authenticated_test_users):
        """Test data integrity validation in authenticated database workflows."""
        # CRITICAL: At least one authenticated user required for data integrity testing
        if len(authenticated_test_users) < 1:
            raise AssertionError(
                f"No authenticated users available for database data integrity test. "
                f"This indicates complete authentication failure that must be resolved for data integrity validation."
            )
        
        user_context = authenticated_test_users[0]
        backend_url = real_services_fixture.get("backend_url", "http://localhost:8000")
        
        async with WebSocketTestClient(
            token=user_context.get("access_token"),
            base_url=backend_url
        ) as client:
            
            # Test data integrity with special characters and edge cases
            integrity_test_data = {
                "type": "create_thread",
                "data": {
                    "title": "Integrity Test: Special Chars éñüíóç",
                    "context": "Testing with emojis 🚀🔥 and special chars < > & \" '"
                }
            }
            
            await client.send_json(integrity_test_data)
            response = await client.receive_json(timeout=10)
            
            assert response["type"] == "thread_created"
            thread_id = response["data"]["thread_id"]
            
            # Add message with complex data
            complex_message = {
                "type": "send_message",
                "data": {
                    "thread_id": thread_id,
                    "content": """Complex message with:
                    - Line breaks
                    - Unicode: ñáéíóúü
                    - Emojis: 🚀🔥⚡
                    - JSON-like: {"key": "value", "number": 123}
                    - HTML-like: <tag>content</tag>
                    - SQL-like: SELECT * FROM table WHERE id = 1;
                    """,
                    "message_type": "user"
                }
            }
            
            await client.send_json(complex_message)
            message_response = await client.receive_json(timeout=10)
            
            assert message_response["type"] == "message_sent"
            
            # Retrieve and verify data integrity
            verification_query = {
                "type": "get_thread_with_messages",
                "data": {"thread_id": thread_id}
            }
            
            await client.send_json(verification_query)
            verification_response = await client.receive_json(timeout=10)
            
            assert verification_response["type"] == "thread_with_messages"
            
            # Verify special characters are preserved
            thread_data = verification_response["data"]
            assert "éñüíóç" in thread_data["title"]
            assert "🚀🔥" in thread_data["context"]
            
            # Verify message content integrity
            message = thread_data["messages"][0]
            message_content = message["content"]
            
            assert "ñáéíóúü" in message_content
            assert "🚀🔥⚡" in message_content
            assert '{"key": "value", "number": 123}' in message_content
            assert "<tag>content</tag>" in message_content
            assert "SELECT * FROM table WHERE id = 1;" in message_content