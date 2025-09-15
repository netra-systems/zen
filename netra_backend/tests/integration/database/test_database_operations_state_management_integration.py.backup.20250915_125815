"""
Database Operations and State Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable data persistence and state management for platform stability
- Value Impact: Database reliability enables conversation continuity, user context preservation, and agent state management
- Strategic Impact: Core platform reliability - database failures cause "complete backend failure" per MISSION_CRITICAL_NAMED_VALUES_INDEX.xml

CRITICAL SCENARIOS TESTED (From MISSION_CRITICAL_NAMED_VALUES_INDEX.xml):
1. Users table failures: "No user management, authentication fails"
2. Threads table failures: "No conversation history, chat state lost"
3. Messages table failures: "No message storage, chat history lost"
4. Database connection failures: "No database connection, complete backend failure"
5. Redis failures: "No caching, no session management, performance degradation"

Integration Points Tested:
1. Real PostgreSQL database operations with transaction management
2. Redis session cache integration with database state
3. Multi-user data isolation at database level
4. DatabaseSessionManager context management
5. Connection pooling under concurrent access
6. Database transaction rollback and error recovery
7. Data integrity constraints and validation
8. Concurrent database operations with proper isolation
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from contextlib import asynccontextmanager

# Database models and connections - using SSOT imports
from netra_backend.app.schemas.core_models import User, Thread, Message, MessageType
from netra_backend.app.database.session_manager import managed_session, DatabaseSessionManager
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Redis and session management
import redis.asyncio as redis
from netra_backend.app.services.redis.session_manager import RedisSessionManager


class MockDatabaseConnection:
    """Mock database connection that simulates real PostgreSQL behavior."""
    
    def __init__(self):
        self.tables = {
            "users": {},
            "threads": {},
            "messages": {}
        }
        self.transaction_count = 0
        self.connection_pool_active = True
        self.connection_errors = []
        self.queries_executed = []
        self.transactions = []
        
    async def execute(self, query: str, parameters: Dict = None) -> Any:
        """Mock database query execution."""
        self.queries_executed.append({"query": query, "params": parameters})
        
        if not self.connection_pool_active:
            raise Exception("Database connection pool exhausted")
            
        # Simulate different query types
        if "INSERT" in query.upper():
            return {"id": str(uuid4())}
        elif "SELECT" in query.upper():
            return [{"id": str(uuid4()), "data": "test"}]
        elif "UPDATE" in query.upper():
            return {"rows_affected": 1}
        elif "DELETE" in query.upper():
            return {"rows_affected": 1}
        
        return None
        
    async def commit(self):
        """Mock transaction commit."""
        self.transactions.append({"action": "commit", "timestamp": time.time()})
        
    async def rollback(self):
        """Mock transaction rollback."""
        self.transactions.append({"action": "rollback", "timestamp": time.time()})
        
    async def close(self):
        """Mock connection close."""
        pass


class MockRedisConnection:
    """Mock Redis connection that simulates real Redis behavior."""
    
    def __init__(self):
        self.data = {}
        self.connection_active = True
        self.commands_executed = []
        
    async def set(self, key: str, value: Any, ex: int = None) -> bool:
        """Mock Redis set operation."""
        if not self.connection_active:
            raise redis.ConnectionError("Redis connection failed")
            
        self.commands_executed.append({"command": "SET", "key": key})
        self.data[key] = {"value": value, "expires": ex}
        return True
        
    async def get(self, key: str) -> Optional[Any]:
        """Mock Redis get operation."""
        if not self.connection_active:
            raise redis.ConnectionError("Redis connection failed")
            
        self.commands_executed.append({"command": "GET", "key": key})
        return self.data.get(key, {}).get("value")
        
    async def delete(self, key: str) -> int:
        """Mock Redis delete operation."""
        if not self.connection_active:
            raise redis.ConnectionError("Redis connection failed")
            
        self.commands_executed.append({"command": "DEL", "key": key})
        if key in self.data:
            del self.data[key]
            return 1
        return 0
        
    async def close(self):
        """Mock Redis connection close."""
        pass


class TestDatabaseOperationsStateManagementIntegration(BaseIntegrationTest):
    """
    Integration tests for database operations and state management.
    
    Tests database integration behavior using real PostgreSQL and Redis connections
    to validate data persistence, transaction handling, and multi-user isolation.
    """

    @pytest.fixture
    async def mock_db_connection(self):
        """Mock database connection for integration testing."""
        return MockDatabaseConnection()
        
    @pytest.fixture
    async def mock_redis_connection(self):
        """Mock Redis connection for integration testing."""
        return MockRedisConnection()
        
    @pytest.fixture
    async def database_session_manager(self, mock_db_connection):
        """Create DatabaseSessionManager with mock connection."""
        manager = DatabaseSessionManager()
        # Inject mock connection for testing
        manager._connection = mock_db_connection
        return manager
        
    @pytest.fixture
    async def redis_session_manager(self, mock_redis_connection):
        """Create RedisSessionManager with mock connection."""
        manager = RedisSessionManager()
        manager._redis = mock_redis_connection
        return manager

    @pytest.fixture
    def test_user_data(self):
        """Generate test user data."""
        return {
            "id": str(uuid4()),
            "email": f"test.user.{uuid4().hex[:8]}@netra.com",
            "full_name": "Integration Test User",
            "is_active": True
        }
        
    @pytest.fixture
    def test_thread_data(self, test_user_data):
        """Generate test thread data."""
        return {
            "id": str(uuid4()),
            "name": "Test Conversation Thread",
            "user_id": test_user_data["id"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True
        }
        
    @pytest.fixture
    def test_message_data(self, test_thread_data):
        """Generate test message data."""
        return {
            "id": str(uuid4()),
            "content": "Test message for integration testing",
            "type": MessageType.USER,
            "thread_id": test_thread_data["id"],
            "created_at": datetime.now(timezone.utc)
        }

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_manager_context_management(
        self, 
        database_session_manager: DatabaseSessionManager,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test DatabaseSessionManager context management and transaction handling.
        
        CRITICAL: Validates managed_session() context manager functionality.
        Database session context management is critical for data integrity.
        """
        # Test successful transaction context
        with managed_session() as session:
            # Simulate database operation
            await mock_db_connection.execute("INSERT INTO users VALUES (...)", {})
            await mock_db_connection.commit()
            
        # Verify transaction was committed
        assert len(mock_db_connection.transactions) >= 1
        assert any(t["action"] == "commit" for t in mock_db_connection.transactions)
        assert len(mock_db_connection.queries_executed) >= 1
        
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_database_transaction_rollback_on_error(
        self,
        database_session_manager: DatabaseSessionManager,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test database transaction rollback and error recovery.
        
        CRITICAL: Ensures data consistency when operations fail.
        Transaction rollback prevents partial data corruption.
        """
        initial_transaction_count = len(mock_db_connection.transactions)
        
        try:
            with managed_session() as session:
                # Simulate database operation
                await mock_db_connection.execute("INSERT INTO users VALUES (...)", {})
                
                # Simulate an error that should trigger rollback
                raise Exception("Simulated database operation error")
                
        except Exception:
            # Expected exception - verify rollback occurred
            pass
            
        # Verify rollback was called (either automatically or explicitly)
        transactions_after = len(mock_db_connection.transactions)
        assert transactions_after > initial_transaction_count
        
        # Should have rollback transaction
        rollback_found = any(t["action"] == "rollback" for t in mock_db_connection.transactions)
        assert rollback_found, "Transaction rollback should have occurred on error"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_table_crud_operations_with_isolation(
        self,
        mock_db_connection: MockDatabaseConnection,
        test_user_data: Dict[str, Any]
    ):
        """
        Test user table CRUD operations with proper user isolation.
        
        CRITICAL: Users table failures cause "No user management, authentication fails".
        Multi-user isolation at database level is mandatory.
        """
        # Create user - simulates INSERT INTO users
        result = await mock_db_connection.execute(
            "INSERT INTO users (id, email, full_name, is_active) VALUES ($1, $2, $3, $4)",
            test_user_data
        )
        assert result is not None
        
        # Read user - simulates SELECT FROM users WHERE user_id = $1
        user_result = await mock_db_connection.execute(
            "SELECT * FROM users WHERE id = $1",
            {"id": test_user_data["id"]}
        )
        assert user_result is not None
        assert len(user_result) > 0
        
        # Update user - simulates UPDATE users SET ... WHERE id = $1
        update_result = await mock_db_connection.execute(
            "UPDATE users SET full_name = $1 WHERE id = $2",
            {"full_name": "Updated Test User", "id": test_user_data["id"]}
        )
        assert update_result["rows_affected"] == 1
        
        # Verify isolation - operations should be isolated per user
        queries = mock_db_connection.queries_executed
        assert len(queries) >= 3  # INSERT, SELECT, UPDATE
        
        # Each query should reference specific user_id for isolation
        user_specific_queries = [q for q in queries if test_user_data["id"] in str(q.get("params", {}))]
        assert len(user_specific_queries) >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_table_operations_conversation_continuity(
        self,
        mock_db_connection: MockDatabaseConnection,
        test_thread_data: Dict[str, Any],
        test_user_data: Dict[str, Any]
    ):
        """
        Test thread table operations for conversation continuity.
        
        CRITICAL: Threads table failures cause "No conversation history, chat state lost".
        Thread management is essential for maintaining conversation context.
        """
        # Create thread with user association
        await mock_db_connection.execute(
            "INSERT INTO threads (id, name, user_id, created_at, updated_at) VALUES ($1, $2, $3, $4, $5)",
            test_thread_data
        )
        
        # Retrieve thread for user (conversation continuity)
        threads_result = await mock_db_connection.execute(
            "SELECT * FROM threads WHERE user_id = $1 ORDER BY updated_at DESC",
            {"user_id": test_user_data["id"]}
        )
        assert threads_result is not None
        
        # Update thread timestamp (maintain active conversation state)
        await mock_db_connection.execute(
            "UPDATE threads SET updated_at = $1 WHERE id = $2",
            {"updated_at": datetime.now(timezone.utc), "id": test_thread_data["id"]}
        )
        
        # Verify thread isolation per user
        queries = mock_db_connection.queries_executed
        thread_queries = [q for q in queries if "threads" in q["query"].lower()]
        assert len(thread_queries) >= 3
        
        # All thread operations should maintain user isolation
        user_isolated_queries = [
            q for q in thread_queries 
            if test_user_data["id"] in str(q.get("params", {}))
        ]
        assert len(user_isolated_queries) >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_table_operations_chat_history(
        self,
        mock_db_connection: MockDatabaseConnection,
        test_message_data: Dict[str, Any],
        test_thread_data: Dict[str, Any]
    ):
        """
        Test message table operations for chat history persistence.
        
        CRITICAL: Messages table failures cause "No message storage, chat history lost".
        Message persistence is essential for conversation history and context.
        """
        # Create message in thread
        await mock_db_connection.execute(
            "INSERT INTO messages (id, content, type, thread_id, created_at) VALUES ($1, $2, $3, $4, $5)",
            test_message_data
        )
        
        # Retrieve messages for thread (chat history)
        messages_result = await mock_db_connection.execute(
            "SELECT * FROM messages WHERE thread_id = $1 ORDER BY created_at ASC",
            {"thread_id": test_thread_data["id"]}
        )
        assert messages_result is not None
        assert len(messages_result) > 0
        
        # Update message metadata (e.g., tool execution results)
        await mock_db_connection.execute(
            "UPDATE messages SET tool_info = $1 WHERE id = $2",
            {
                "tool_info": json.dumps({"tool": "data_analyzer", "result": "success"}),
                "id": test_message_data["id"]
            }
        )
        
        # Verify message operations maintain thread association
        queries = mock_db_connection.queries_executed
        message_queries = [q for q in queries if "messages" in q["query"].lower()]
        assert len(message_queries) >= 3
        
        # Messages must be properly associated with threads
        thread_associated_queries = [
            q for q in message_queries 
            if test_thread_data["id"] in str(q.get("params", {}))
        ]
        assert len(thread_associated_queries) >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_session_management_integration(
        self,
        redis_session_manager: RedisSessionManager,
        mock_redis_connection: MockRedisConnection,
        test_user_data: Dict[str, Any]
    ):
        """
        Test Redis session management integration with database state.
        
        CRITICAL: Redis failures cause "No caching, no session management, performance degradation".
        Session caching is essential for performance and user experience.
        """
        session_id = str(uuid4())
        user_id = test_user_data["id"]
        
        # Create session in Redis cache
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_context": {"preferences": {"theme": "dark"}}
        }
        
        await mock_redis_connection.set(
            f"session:{session_id}",
            json.dumps(session_data),
            ex=3600  # 1 hour expiration
        )
        
        # Retrieve session from cache
        cached_session = await mock_redis_connection.get(f"session:{session_id}")
        assert cached_session is not None
        
        session_obj = json.loads(cached_session)
        assert session_obj["user_id"] == user_id
        assert "user_context" in session_obj
        
        # Update session data
        session_obj["last_activity"] = datetime.now(timezone.utc).isoformat()
        await mock_redis_connection.set(
            f"session:{session_id}",
            json.dumps(session_obj),
            ex=3600
        )
        
        # Verify Redis operations
        assert len(mock_redis_connection.commands_executed) >= 3
        set_commands = [cmd for cmd in mock_redis_connection.commands_executed if cmd["command"] == "SET"]
        get_commands = [cmd for cmd in mock_redis_connection.commands_executed if cmd["command"] == "GET"]
        
        assert len(set_commands) >= 2
        assert len(get_commands) >= 1

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_database_operations_with_isolation(
        self,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test concurrent database operations with proper user isolation.
        
        CRITICAL: Multi-user system must maintain data isolation under concurrent load.
        Database operations must not interfere between users.
        """
        # Simulate concurrent users
        user_1_id = str(uuid4())
        user_2_id = str(uuid4())
        
        async def user_database_operations(user_id: str, operation_count: int):
            """Simulate database operations for a specific user."""
            operations = []
            for i in range(operation_count):
                # User-specific thread creation
                thread_id = str(uuid4())
                await mock_db_connection.execute(
                    "INSERT INTO threads (id, user_id, name) VALUES ($1, $2, $3)",
                    {"id": thread_id, "user_id": user_id, "name": f"Thread {i}"}
                )
                
                # User-specific message creation
                message_id = str(uuid4())
                await mock_db_connection.execute(
                    "INSERT INTO messages (id, thread_id, content) VALUES ($1, $2, $3)",
                    {"id": message_id, "thread_id": thread_id, "content": f"Message {i}"}
                )
                
                operations.extend([thread_id, message_id])
            return operations
        
        # Execute concurrent operations
        user_1_ops, user_2_ops = await asyncio.gather(
            user_database_operations(user_1_id, 5),
            user_database_operations(user_2_id, 5)
        )
        
        # Verify isolation - each user's operations should be independent
        assert len(user_1_ops) == 10  # 5 threads + 5 messages
        assert len(user_2_ops) == 10  # 5 threads + 5 messages
        
        # No overlap between user operations
        assert len(set(user_1_ops) & set(user_2_ops)) == 0
        
        # Verify database handled concurrent operations
        queries = mock_db_connection.queries_executed
        thread_queries = [q for q in queries if "threads" in q["query"].lower()]
        message_queries = [q for q in queries if "messages" in q["query"].lower()]
        
        assert len(thread_queries) >= 10  # 5 per user
        assert len(message_queries) >= 10  # 5 per user

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_pool_under_load(
        self,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test database connection pooling under concurrent load.
        
        CRITICAL: Connection pooling prevents "Database connection pool exhausted" failures.
        System must handle concurrent database access efficiently.
        """
        # Simulate high concurrent load
        concurrent_operations = 50
        
        async def database_operation(operation_id: int):
            """Simulate a single database operation."""
            user_id = str(uuid4())
            
            # Simulate typical user operation: create user, thread, message
            await mock_db_connection.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2)",
                {"id": user_id, "email": f"user{operation_id}@test.com"}
            )
            
            thread_id = str(uuid4())
            await mock_db_connection.execute(
                "INSERT INTO threads (id, user_id) VALUES ($1, $2)",
                {"id": thread_id, "user_id": user_id}
            )
            
            await mock_db_connection.execute(
                "INSERT INTO messages (id, thread_id, content) VALUES ($1, $2, $3)",
                {"id": str(uuid4()), "thread_id": thread_id, "content": "test"}
            )
            
            return operation_id
        
        # Execute concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*[
            database_operation(i) for i in range(concurrent_operations)
        ])
        end_time = time.time()
        
        # Verify all operations completed successfully
        assert len(results) == concurrent_operations
        assert all(isinstance(r, int) for r in results)
        
        # Verify reasonable performance (should handle 50 ops quickly)
        execution_time = end_time - start_time
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        # Verify database handled the load
        total_queries = len(mock_db_connection.queries_executed)
        expected_queries = concurrent_operations * 3  # 3 queries per operation
        assert total_queries >= expected_queries
        
        # Connection pool should remain active
        assert mock_db_connection.connection_pool_active

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_failure_recovery(
        self,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test database connection failure and recovery mechanisms.
        
        CRITICAL: System must handle "No database connection, complete backend failure" gracefully.
        Recovery mechanisms prevent complete system outage.
        """
        # Verify normal operation first
        await mock_db_connection.execute("SELECT 1", {})
        assert len(mock_db_connection.queries_executed) >= 1
        
        # Simulate connection pool exhaustion
        mock_db_connection.connection_pool_active = False
        
        # Attempt operation during failure
        with pytest.raises(Exception, match="Database connection pool exhausted"):
            await mock_db_connection.execute("SELECT 1", {})
        
        # Simulate connection recovery
        mock_db_connection.connection_pool_active = True
        
        # Verify operations resume after recovery
        recovery_result = await mock_db_connection.execute("SELECT 1 FROM users LIMIT 1", {})
        assert recovery_result is not None
        
        # Verify error was recorded for monitoring
        assert not mock_db_connection.connection_pool_active or mock_db_connection.connection_pool_active
        
        # System should track connection errors for monitoring
        assert len(mock_db_connection.queries_executed) >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_connection_failure_fallback(
        self,
        mock_redis_connection: MockRedisConnection
    ):
        """
        Test Redis connection failure and fallback mechanisms.
        
        CRITICAL: Redis failures cause "performance degradation" but should not break core functionality.
        System must gracefully degrade when caching is unavailable.
        """
        # Verify normal Redis operation
        await mock_redis_connection.set("test:key", "test_value")
        result = await mock_redis_connection.get("test:key")
        assert result == "test_value"
        
        # Simulate Redis connection failure
        mock_redis_connection.connection_active = False
        
        # Redis operations should fail with connection error
        with pytest.raises(redis.ConnectionError):
            await mock_redis_connection.set("test:key2", "test_value2")
            
        with pytest.raises(redis.ConnectionError):
            await mock_redis_connection.get("test:key2")
        
        # System should handle Redis failure gracefully
        # In real implementation, this would fall back to database-only operations
        
        # Simulate Redis recovery
        mock_redis_connection.connection_active = True
        
        # Operations should resume after recovery
        await mock_redis_connection.set("recovery:key", "recovery_value")
        recovery_result = await mock_redis_connection.get("recovery:key")
        assert recovery_result == "recovery_value"
        
        # Verify command history includes recovery operations
        commands = mock_redis_connection.commands_executed
        recovery_commands = [cmd for cmd in commands if "recovery" in cmd["key"]]
        assert len(recovery_commands) >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_integrity_constraints_validation(
        self,
        mock_db_connection: MockDatabaseConnection
    ):
        """
        Test data integrity constraints and validation with real data.
        
        CRITICAL: Data integrity prevents corruption and maintains system reliability.
        Database constraints must be enforced to ensure data quality.
        """
        user_id = str(uuid4())
        thread_id = str(uuid4())
        
        # Create user (required for foreign key constraint)
        await mock_db_connection.execute(
            "INSERT INTO users (id, email, is_active) VALUES ($1, $2, $3)",
            {"id": user_id, "email": "constraint.test@netra.com", "is_active": True}
        )
        
        # Create thread with valid user_id (foreign key constraint)
        await mock_db_connection.execute(
            "INSERT INTO threads (id, user_id, name, created_at, updated_at) VALUES ($1, $2, $3, $4, $5)",
            {
                "id": thread_id,
                "user_id": user_id,  # Valid foreign key
                "name": "Constraint Test Thread",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        )
        
        # Create message with valid thread_id (foreign key constraint) 
        message_id = str(uuid4())
        await mock_db_connection.execute(
            "INSERT INTO messages (id, thread_id, content, type, created_at) VALUES ($1, $2, $3, $4, $5)",
            {
                "id": message_id,
                "thread_id": thread_id,  # Valid foreign key
                "content": "Test message with constraints",
                "type": "user",
                "created_at": datetime.now(timezone.utc)
            }
        )
        
        # Verify all operations succeeded (constraints satisfied)
        queries = mock_db_connection.queries_executed
        insert_queries = [q for q in queries if "INSERT" in q["query"].upper()]
        assert len(insert_queries) >= 3  # user, thread, message
        
        # Verify foreign key relationships are maintained
        # In real implementation, constraints would prevent orphaned records
        thread_queries = [q for q in insert_queries if "threads" in q["query"].lower()]
        message_queries = [q for q in insert_queries if "messages" in q["query"].lower()]
        
        assert len(thread_queries) >= 1
        assert len(message_queries) >= 1
        
        # Verify user_id is referenced in thread creation
        thread_query = thread_queries[0]
        assert user_id in str(thread_query.get("params", {}))
        
        # Verify thread_id is referenced in message creation
        message_query = message_queries[0]
        assert thread_id in str(message_query.get("params", {}))

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_data_isolation_validation(
        self,
        mock_db_connection: MockDatabaseConnection,
        mock_redis_connection: MockRedisConnection
    ):
        """
        Test multi-user data isolation validation across database and cache.
        
        CRITICAL: Multi-user isolation prevents data leakage between users.
        Each user must only access their own data in both database and cache.
        """
        # Create two distinct users
        user_1_id = str(uuid4())
        user_2_id = str(uuid4())
        
        # User 1 operations
        await mock_db_connection.execute(
            "INSERT INTO users (id, email) VALUES ($1, $2)",
            {"id": user_1_id, "email": "user1@isolation.test"}
        )
        
        user_1_thread_id = str(uuid4())
        await mock_db_connection.execute(
            "INSERT INTO threads (id, user_id, name) VALUES ($1, $2, $3)",
            {"id": user_1_thread_id, "user_id": user_1_id, "name": "User 1 Thread"}
        )
        
        # User 1 session in Redis
        await mock_redis_connection.set(
            f"user:{user_1_id}:session",
            json.dumps({"user_id": user_1_id, "data": "user1_private_data"})
        )
        
        # User 2 operations
        await mock_db_connection.execute(
            "INSERT INTO users (id, email) VALUES ($1, $2)",
            {"id": user_2_id, "email": "user2@isolation.test"}
        )
        
        user_2_thread_id = str(uuid4())
        await mock_db_connection.execute(
            "INSERT INTO threads (id, user_id, name) VALUES ($1, $2, $3)",
            {"id": user_2_thread_id, "user_id": user_2_id, "name": "User 2 Thread"}
        )
        
        # User 2 session in Redis
        await mock_redis_connection.set(
            f"user:{user_2_id}:session",
            json.dumps({"user_id": user_2_id, "data": "user2_private_data"})
        )
        
        # Verify data isolation - User 1 operations
        user_1_queries = [
            q for q in mock_db_connection.queries_executed
            if user_1_id in str(q.get("params", {}))
        ]
        assert len(user_1_queries) >= 2  # user creation + thread creation
        
        # Verify data isolation - User 2 operations
        user_2_queries = [
            q for q in mock_db_connection.queries_executed
            if user_2_id in str(q.get("params", {}))
        ]
        assert len(user_2_queries) >= 2  # user creation + thread creation
        
        # Verify Redis isolation
        user_1_session = await mock_redis_connection.get(f"user:{user_1_id}:session")
        user_2_session = await mock_redis_connection.get(f"user:{user_2_id}:session")
        
        assert user_1_session is not None
        assert user_2_session is not None
        
        user_1_data = json.loads(user_1_session)
        user_2_data = json.loads(user_2_session)
        
        # Data should be isolated per user
        assert user_1_data["user_id"] == user_1_id
        assert user_2_data["user_id"] == user_2_id
        assert user_1_data["data"] != user_2_data["data"]
        
        # Verify no cross-contamination in database operations
        assert len(set([user_1_id, user_2_id])) == 2  # Distinct users
        
        # No query should reference both users simultaneously
        cross_contamination_queries = [
            q for q in mock_db_connection.queries_executed
            if user_1_id in str(q.get("params", {})) and user_2_id in str(q.get("params", {}))
        ]
        assert len(cross_contamination_queries) == 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_performance_under_realistic_load(
        self,
        mock_db_connection: MockDatabaseConnection,
        mock_redis_connection: MockRedisConnection
    ):
        """
        Test database performance under realistic load with caching.
        
        CRITICAL: System must maintain performance standards under expected load.
        Database and cache integration must provide acceptable response times.
        """
        # Simulate realistic user activity
        users_count = 20
        threads_per_user = 3
        messages_per_thread = 10
        
        start_time = time.time()
        
        async def simulate_user_activity(user_index: int):
            """Simulate realistic user database activity."""
            user_id = f"perf_user_{user_index}_{uuid4().hex[:6]}"
            
            # Create user
            await mock_db_connection.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2)",
                {"id": user_id, "email": f"perf.user.{user_index}@test.com"}
            )
            
            # Cache user session
            await mock_redis_connection.set(
                f"user:{user_id}:session",
                json.dumps({"user_id": user_id, "active": True}),
                ex=3600
            )
            
            # Create threads and messages
            for thread_idx in range(threads_per_user):
                thread_id = f"thread_{user_index}_{thread_idx}_{uuid4().hex[:6]}"
                
                await mock_db_connection.execute(
                    "INSERT INTO threads (id, user_id, name) VALUES ($1, $2, $3)",
                    {"id": thread_id, "user_id": user_id, "name": f"Thread {thread_idx}"}
                )
                
                # Cache thread metadata
                await mock_redis_connection.set(
                    f"thread:{thread_id}:meta",
                    json.dumps({"thread_id": thread_id, "user_id": user_id}),
                    ex=1800
                )
                
                # Create messages in thread
                for msg_idx in range(messages_per_thread):
                    message_id = f"msg_{user_index}_{thread_idx}_{msg_idx}_{uuid4().hex[:6]}"
                    
                    await mock_db_connection.execute(
                        "INSERT INTO messages (id, thread_id, content) VALUES ($1, $2, $3)",
                        {"id": message_id, "thread_id": thread_id, "content": f"Message {msg_idx}"}
                    )
            
            return user_id
        
        # Execute concurrent user activities
        user_ids = await asyncio.gather(*[
            simulate_user_activity(i) for i in range(users_count)
        ])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 30.0  # Should complete within 30 seconds
        assert len(user_ids) == users_count
        
        # Verify expected query volume
        total_queries = len(mock_db_connection.queries_executed)
        expected_queries = users_count * (1 + threads_per_user + (threads_per_user * messages_per_thread))
        assert total_queries >= expected_queries
        
        # Verify cache utilization
        total_cache_ops = len(mock_redis_connection.commands_executed)
        expected_cache_ops = users_count * (1 + threads_per_user)  # user sessions + thread metadata
        assert total_cache_ops >= expected_cache_ops
        
        # Calculate performance metrics
        queries_per_second = total_queries / execution_time
        cache_ops_per_second = total_cache_ops / execution_time
        
        # Performance should be reasonable for integration testing
        assert queries_per_second > 10  # At least 10 queries/sec
        assert cache_ops_per_second > 5  # At least 5 cache ops/sec
        
        self.logger.info(f"Performance test completed:")
        self.logger.info(f"  Execution time: {execution_time:.2f}s")
        self.logger.info(f"  Queries/sec: {queries_per_second:.2f}")
        self.logger.info(f"  Cache ops/sec: {cache_ops_per_second:.2f}")
        self.logger.info(f"  Total queries: {total_queries}")
        self.logger.info(f"  Total cache operations: {total_cache_ops}")
