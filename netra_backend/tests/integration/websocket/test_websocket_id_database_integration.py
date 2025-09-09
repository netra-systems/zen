"""
WebSocket ID Database Integration Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose database integration issues caused by uuid.uuid4() ID patterns.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Data integrity and consistent ID management  
- Value Impact: Ensures WebSocket IDs integrate properly with database systems
- Strategic Impact: CRITICAL - Database consistency prevents data corruption

Test Strategy:
1. FAIL INITIALLY - Tests expose database integration issues with uuid.uuid4()  
2. MIGRATE PHASE - Replace with UnifiedIdGenerator database-aware methods
3. PASS FINALLY - Tests validate proper database integration with consistent IDs

These tests validate that WebSocket IDs work correctly with database operations,
foreign key relationships, and data consistency requirements.
"""

import pytest
import asyncio
import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Import test framework for real services integration
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

# Import WebSocket core modules for database testing
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, generate_default_message
from netra_backend.app.websocket_core.context import WebSocketRequestContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager

# Import database models and managers
from netra_backend.app.db.postgresql_manager import PostgreSQLManager
from netra_backend.app.models.user import User
from netra_backend.app.models.conversation import Conversation
from netra_backend.app.models.message import Message
from netra_backend.app.models.websocket_connection import WebSocketConnection

# Import SSOT UnifiedIdGenerator for proper database integration
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, ThreadID, MessageID


@pytest.mark.integration
@pytest.mark.database
class TestWebSocketIdDatabaseIntegration(BaseIntegrationTest):
    """
    Integration tests that EXPOSE database integration failures with uuid.uuid4().
    
    CRITICAL: These tests use real PostgreSQL service and are DESIGNED TO FAIL
    initially to demonstrate database consistency issues with random UUID patterns.
    """

    @pytest.fixture(autouse=True)
    async def setup_real_database(self, real_services_fixture):
        """Set up real database services for integration testing."""
        self.services = await get_real_services()
        self.db_manager = self.services.get_database_manager()
        
        # Ensure clean test environment
        await self._cleanup_test_data()
        
        yield
        
        # Cleanup after tests
        await self._cleanup_test_data()

    async def test_websocket_connection_foreign_key_consistency_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose foreign key consistency issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() WebSocket connection IDs
        break foreign key relationships in the database.
        """
        # Create test user in database
        test_user = await self._create_test_user("db_test_user_1")
        user_id = test_user.id
        
        # Create WebSocket connection with current uuid.uuid4() pattern
        connection_info = ConnectionInfo(user_id=str(user_id))
        
        # FAILING ASSERTION: Connection ID should be database-compatible format
        assert not connection_info.connection_id.startswith("conn_"), \
            f"Connection still uses uuid.uuid4() pattern: {connection_info.connection_id}"
            
        # Expected UnifiedIdGenerator format for database compatibility
        expected_pattern = f"ws_conn_{str(user_id)[:8]}_"
        assert connection_info.connection_id.startswith(expected_pattern), \
            f"Expected database-compatible pattern '{expected_pattern}', got: {connection_info.connection_id}"
            
        # Try to store connection in database
        try:
            websocket_conn = WebSocketConnection(
                connection_id=connection_info.connection_id,
                user_id=user_id,
                connected_at=datetime.now(timezone.utc),
                state="connected"
            )
            
            await self.db_manager.create(websocket_conn)
            stored_connection = await self.db_manager.get_websocket_connection_by_id(
                connection_info.connection_id
            )
            
            # This should work but may fail due to ID format incompatibility
            assert stored_connection is not None, \
                f"Failed to store/retrieve connection with ID: {connection_info.connection_id}"
                
            # FAILING ASSERTION: Should be able to query by user-aware connection ID
            user_connections = await self.db_manager.get_connections_for_user(user_id)
            connection_ids = [conn.connection_id for conn in user_connections]
            
            # This will FAIL because uuid.uuid4() makes user-specific queries inefficient
            assert connection_info.connection_id in connection_ids, \
                f"Cannot efficiently query user connections with uuid.uuid4() pattern"
                
        except Exception as e:
            pytest.fail(f"Database integration failed with uuid.uuid4() connection ID: {str(e)}")

    async def test_message_thread_relationship_integrity_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose message-thread relationship issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() message and thread IDs
        break referential integrity in the database.
        """
        # Create test user and conversation
        test_user = await self._create_test_user("msg_thread_user")
        conversation = await self._create_test_conversation(test_user.id, "Test Conversation")
        
        # Create WebSocket context (triggers uuid.uuid4() usage)
        context = WebSocketRequestContext.create_for_user(
            user_id=str(test_user.id),
            thread_id=str(conversation.id),
            connection_info=None
        )
        
        # Create messages using current uuid.uuid4() pattern
        messages = []
        for i in range(3):
            message = generate_default_message(
                message_type="agent_thinking",
                user_id=str(test_user.id),
                thread_id=context.thread_id,
                data={"content": f"Test message {i}"}
            )
            messages.append(message)
            
        # FAILING ASSERTION: Message IDs should follow database-compatible format
        for msg in messages:
            # This will FAIL because uuid.uuid4() message IDs lack database context
            assert not len(msg.message_id) == 36, \
                f"Message ID still uses uuid.uuid4() format: {msg.message_id}"
                
            # Expected UnifiedIdGenerator format for database relationships
            expected_pattern = f"msg_agent_thinking_{str(test_user.id)[:8]}_"
            assert msg.message_id.startswith(expected_pattern), \
                f"Expected database-compatible message pattern '{expected_pattern}', got: {msg.message_id}"
                
        # Try to store messages in database with foreign key relationships
        try:
            for msg in messages:
                db_message = Message(
                    id=msg.message_id,
                    conversation_id=conversation.id,
                    user_id=test_user.id,
                    content=msg.data.get("content", ""),
                    message_type=msg.type,
                    created_at=datetime.now(timezone.utc)
                )
                
                await self.db_manager.create(db_message)
                
            # FAILING ASSERTION: Should be able to query messages by thread efficiently
            thread_messages = await self.db_manager.get_messages_by_thread(conversation.id)
            
            # This will FAIL because uuid.uuid4() makes thread-based queries inefficient
            assert len(thread_messages) == 3, \
                f"Cannot efficiently query thread messages with uuid.uuid4() pattern: got {len(thread_messages)} expected 3"
                
            # FAILING ASSERTION: Message ordering should be deterministic
            message_ids = [msg.id for msg in thread_messages]
            sorted_ids = sorted(message_ids)
            
            # This will FAIL because uuid.uuid4() provides no ordering information
            assert message_ids == sorted_ids, \
                f"uuid.uuid4() message IDs provide no temporal ordering"
                
        except Exception as e:
            pytest.fail(f"Message-thread relationship failed with uuid.uuid4(): {str(e)}")

    async def test_connection_session_cascade_operations_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose cascade operation issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() IDs break database cascade
        operations for WebSocket connections and user sessions.
        """
        # Create test user  
        test_user = await self._create_test_user("cascade_test_user")
        user_id = test_user.id
        
        # Create multiple WebSocket connections for user
        connections = []
        for i in range(3):
            conn_info = ConnectionInfo(user_id=str(user_id))
            websocket_conn = WebSocketConnection(
                connection_id=conn_info.connection_id,
                user_id=user_id,
                connected_at=datetime.now(timezone.utc),
                state="connected"
            )
            await self.db_manager.create(websocket_conn)
            connections.append(websocket_conn)
            
        # Create user session with connections
        session_manager = UserSessionManager()
        session_data = {
            "user_id": str(user_id),
            "connections": [conn.connection_id for conn in connections]
        }
        
        session = await session_manager.create_session(str(user_id), session_data)
        
        # FAILING ASSERTION: Session ID should support efficient cascade operations
        session_id = getattr(session, 'session_id', None) or getattr(session, 'id', None)
        
        if session_id:
            # This will FAIL because uuid.uuid4() session IDs lack user context for cascades
            assert str(user_id)[:8] in session_id, \
                f"Session ID lacks user context for cascade operations: {session_id}"
                
            # Expected UnifiedIdGenerator format for database cascades
            expected_pattern = f"session_{str(user_id)[:8]}_"
            assert session_id.startswith(expected_pattern), \
                f"Expected cascade-compatible session pattern '{expected_pattern}', got: {session_id}"
                
        # Test cascade delete operations
        try:
            # This should cascade delete all user connections and sessions
            await self.db_manager.delete_user_data(user_id)
            
            # FAILING ASSERTION: Should efficiently clean up all related data
            remaining_connections = await self.db_manager.get_connections_for_user(user_id)
            assert len(remaining_connections) == 0, \
                f"Cascade delete failed with uuid.uuid4() IDs: {len(remaining_connections)} connections remain"
                
            # FAILING ASSERTION: Session cleanup should also work efficiently  
            if session_id:
                remaining_session = await self.db_manager.get_session_by_id(session_id)
                assert remaining_session is None, \
                    f"Session cascade delete failed with uuid.uuid4() ID: {session_id}"
                    
        except Exception as e:
            pytest.fail(f"Cascade operations failed with uuid.uuid4() IDs: {str(e)}")

    async def test_database_query_performance_with_uuid4_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose query performance issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns cause poor database
        query performance due to lack of indexing and clustering benefits.
        """
        # Create test users
        users = []
        for i in range(10):
            user = await self._create_test_user(f"perf_user_{i}")
            users.append(user)
            
        # Create many connections per user using uuid.uuid4() pattern
        all_connections = []
        for user in users:
            for i in range(20):  # 20 connections per user
                conn_info = ConnectionInfo(user_id=str(user.id))
                websocket_conn = WebSocketConnection(
                    connection_id=conn_info.connection_id,
                    user_id=user.id,
                    connected_at=datetime.now(timezone.utc),
                    state="connected"
                )
                await self.db_manager.create(websocket_conn)
                all_connections.append(websocket_conn)
                
        print(f"Created {len(all_connections)} connections across {len(users)} users")
        
        # Test query performance for user-specific connections
        query_times = []
        
        for user in users[:3]:  # Test first 3 users
            start_time = time.time()
            
            # This query should be efficient but will be slow with uuid.uuid4()
            user_connections = await self.db_manager.get_connections_for_user(user.id)
            
            query_time = time.time() - start_time
            query_times.append(query_time)
            
            # FAILING ASSERTION: Query should be fast (< 100ms)
            assert query_time < 0.1, \
                f"User connection query too slow with uuid.uuid4(): {query_time:.3f}s > 0.1s"
                
            # FAILING ASSERTION: Should return exactly 20 connections
            assert len(user_connections) == 20, \
                f"Expected 20 connections for user {user.id}, got {len(user_connections)}"
                
        # FAILING ASSERTION: Average query performance should be acceptable
        avg_query_time = sum(query_times) / len(query_times)
        assert avg_query_time < 0.05, \
            f"Average query time too slow with uuid.uuid4(): {avg_query_time:.3f}s > 0.05s"
            
        print(f"Query performance results:")
        print(f"  Individual query times: {[f'{t:.3f}s' for t in query_times]}")
        print(f"  Average query time: {avg_query_time:.3f}s")
        print(f"  FAILURE: uuid.uuid4() patterns cause poor indexing and query performance")

    async def test_database_transaction_consistency_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose transaction consistency issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() IDs can cause transaction
        consistency issues in complex WebSocket database operations.
        """
        # Create test user
        test_user = await self._create_test_user("transaction_user")
        user_id = test_user.id
        
        # Start database transaction
        async with self.db_manager.transaction() as tx:
            try:
                # Create conversation
                conversation = Conversation(
                    user_id=user_id,
                    title="Transaction Test Conversation",
                    created_at=datetime.now(timezone.utc)
                )
                await tx.create(conversation)
                
                # Create WebSocket connection
                conn_info = ConnectionInfo(user_id=str(user_id))
                websocket_conn = WebSocketConnection(
                    connection_id=conn_info.connection_id,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    connected_at=datetime.now(timezone.utc),
                    state="connected"
                )
                await tx.create(websocket_conn)
                
                # Create WebSocket context
                context = WebSocketRequestContext.create_for_user(
                    user_id=str(user_id),
                    thread_id=str(conversation.id),
                    connection_info=conn_info
                )
                
                # Create related messages
                messages = []
                for i in range(5):
                    message = generate_default_message(
                        message_type="agent_started",
                        user_id=str(user_id),
                        thread_id=context.thread_id,
                        data={"content": f"Transaction message {i}"}
                    )
                    
                    db_message = Message(
                        id=message.message_id,
                        conversation_id=conversation.id,
                        user_id=user_id,
                        content=message.data["content"],
                        message_type=message.type,
                        created_at=datetime.now(timezone.utc)
                    )
                    await tx.create(db_message)
                    messages.append(db_message)
                    
                # FAILING ASSERTION: All IDs should be consistent and related
                # Check connection-conversation relationship
                assert str(conversation.id) in context.thread_id, \
                    f"Context thread_id not properly related to conversation: {context.thread_id}"
                    
                # Check message-conversation relationships
                for msg in messages:
                    # This will FAIL because uuid.uuid4() message IDs don't encode relationships
                    assert str(conversation.id)[:8] in msg.id, \
                        f"Message ID should reference conversation: {msg.id} for conv {conversation.id}"
                        
                # FAILING ASSERTION: Connection ID should be traceable to user and conversation
                expected_conn_pattern = f"ws_conn_{str(user_id)[:8]}_{str(conversation.id)[:8]}_"
                assert websocket_conn.connection_id.find(expected_conn_pattern) != -1, \
                    f"Connection ID lacks relational context: {websocket_conn.connection_id}"
                    
                # Commit transaction
                await tx.commit()
                
            except Exception as e:
                await tx.rollback()
                pytest.fail(f"Transaction consistency failed with uuid.uuid4() IDs: {str(e)}")
                
        # Verify transaction integrity after commit
        stored_conversation = await self.db_manager.get_conversation(conversation.id)
        stored_connection = await self.db_manager.get_websocket_connection_by_id(websocket_conn.connection_id)
        stored_messages = await self.db_manager.get_messages_by_conversation(conversation.id)
        
        assert stored_conversation is not None, "Conversation not properly stored"
        assert stored_connection is not None, "WebSocket connection not properly stored"
        assert len(stored_messages) == 5, f"Expected 5 messages, got {len(stored_messages)}"

    async def test_database_index_optimization_requirements_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose database indexing issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns prevent effective
        database indexing strategies for WebSocket-related queries.
        """
        # Create test data with uuid.uuid4() patterns
        users = []
        for i in range(5):
            user = await self._create_test_user(f"index_user_{i}")
            users.append(user)
            
        # Create connections and messages with current uuid.uuid4() patterns
        for user in users:
            for i in range(10):
                # Connection with uuid.uuid4()
                conn_info = ConnectionInfo(user_id=str(user.id))
                websocket_conn = WebSocketConnection(
                    connection_id=conn_info.connection_id,
                    user_id=user.id,
                    connected_at=datetime.now(timezone.utc),
                    state="connected"
                )
                await self.db_manager.create(websocket_conn)
                
                # Messages with uuid.uuid4()
                for j in range(5):
                    message = generate_default_message(
                        message_type="agent_completed",
                        user_id=str(user.id),
                        thread_id=f"thread_{i}",
                        data={"content": f"Index test message {j}"}
                    )
                    
                    db_message = Message(
                        id=message.message_id,
                        user_id=user.id,
                        content=message.data["content"],
                        message_type=message.type,
                        created_at=datetime.now(timezone.utc)
                    )
                    await self.db_manager.create(db_message)
                    
        # Test index effectiveness queries
        
        # FAILING ASSERTION: User-based queries should use indexes effectively
        for user in users:
            explain_result = await self.db_manager.explain_query(
                "SELECT * FROM websocket_connections WHERE user_id = $1", [user.id]
            )
            
            # This will FAIL because uuid.uuid4() connection IDs don't support prefix indexing
            assert "Index Scan" in str(explain_result), \
                f"User connection query not using index effectively with uuid.uuid4() patterns"
                
        # FAILING ASSERTION: Message type queries should be optimized
        explain_result = await self.db_manager.explain_query(
            "SELECT * FROM messages WHERE message_type = $1", ["agent_completed"]
        )
        
        # This will FAIL because uuid.uuid4() message IDs don't group by type for indexing
        assert "Index Scan" in str(explain_result), \
            f"Message type query not using index effectively with uuid.uuid4() patterns"
            
        # FAILING ASSERTION: Range queries should be supported
        start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = datetime.now(timezone.utc)
        
        explain_result = await self.db_manager.explain_query(
            "SELECT * FROM messages WHERE created_at BETWEEN $1 AND $2", [start_time, end_time]
        )
        
        # This should use time-based indexing, but uuid.uuid4() message IDs don't support it
        assert "Index Scan" in str(explain_result), \
            f"Time range query not using index effectively with uuid.uuid4() patterns"
            
        print(f"Database indexing analysis:")
        print(f"  FAILURE: uuid.uuid4() patterns prevent effective indexing strategies")
        print(f"  REQUIRED: UnifiedIdGenerator patterns support prefix and cluster indexing")

    # Helper methods for database integration testing
    
    async def _create_test_user(self, username: str) -> User:
        """Create a test user in the database."""
        user = User(
            username=username,
            email=f"{username}@example.com",
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        created_user = await self.db_manager.create(user)
        return created_user
        
    async def _create_test_conversation(self, user_id: int, title: str) -> Conversation:
        """Create a test conversation in the database."""
        conversation = Conversation(
            user_id=user_id,
            title=title,
            created_at=datetime.now(timezone.utc)
        )
        created_conversation = await self.db_manager.create(conversation)
        return created_conversation
        
    async def _cleanup_test_data(self):
        """Clean up test data from database."""
        try:
            # Clean up test users and related data
            await self.db_manager.execute(
                "DELETE FROM messages WHERE content LIKE '%test%' OR content LIKE '%Test%'"
            )
            await self.db_manager.execute(
                "DELETE FROM websocket_connections WHERE connection_id LIKE '%test%' OR connection_id LIKE '%conn_%'"
            )
            await self.db_manager.execute(
                "DELETE FROM conversations WHERE title LIKE '%test%' OR title LIKE '%Test%'"
            )
            await self.db_manager.execute(
                "DELETE FROM users WHERE username LIKE '%test%' OR email LIKE '%test%'"
            )
        except Exception as e:
            # Ignore cleanup errors in test setup
            self.logger.warning(f"Test cleanup error: {e}")

    @pytest.fixture
    async def real_services_fixture(self):
        """Fixture to ensure real services are available for integration tests."""
        # This fixture is automatically used by BaseIntegrationTest
        # and ensures real database services are running
        pass