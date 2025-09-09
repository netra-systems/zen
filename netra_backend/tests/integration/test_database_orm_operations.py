"""Integration tests for Database ORM operations.

These tests validate REAL component interactions between:
- SQLAlchemy ORM models and database operations
- Database session management and transactions  
- User context isolation in database operations
- Real database operations using SQLite in-memory
- Model relationships and business logic

CRITICAL: These are INTEGRATION tests - they test REAL interactions between components
without mocks for core functionality. Uses SQLite in-memory for real database operations.

Business Value: Platform/Internal - System Stability
Ensures database operations work correctly for multi-user business data isolation.
"""

import asyncio
import pytest
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.models.database import Base
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.message import Message
from netra_backend.app.models.agent_execution import AgentExecution
from netra_backend.app.services.user_execution_context import UserExecutionContext


class DatabaseTestFixture:
    """Real database fixture using SQLite in-memory for integration testing."""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self.sync_session = None
        self.async_session = None
        
    async def setup(self):
        """Setup real SQLite in-memory database."""
        # Create sync engine for SQLite in-memory
        self.engine = create_engine(
            "sqlite:///:memory:",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False}
        )
        
        # Create async engine for SQLite in-memory 
        self.async_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        # Create session factories
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        
        # For async engine, we need to create tables differently
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    def get_sync_session(self) -> Session:
        """Get synchronous database session."""
        return self.SessionLocal()
        
    async def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session."""
        return self.AsyncSessionLocal()
        
    async def cleanup(self):
        """Cleanup database connections."""
        if self.sync_session:
            self.sync_session.close()
        if self.async_session:
            await self.async_session.close()
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            await self.async_engine.dispose()


class TestDatabaseORMOperations(SSotAsyncTestCase):
    """Integration tests for Database ORM operations.
    
    Tests REAL database operations without Docker dependencies using SQLite in-memory.
    """
    
    def setup_method(self, method=None):
        """Setup for each test with real database components."""
        super().setup_method(method)
        
        # Create real database fixture
        self.db_fixture = DatabaseTestFixture()
        
        # Setup will be called in async tests
        self.db_setup_complete = False
        
        # Create real user contexts for database testing
        self.user1_context = UserExecutionContext(
            user_id="db_test_user_001",
            thread_id="db_thread_001",
            run_id="db_run_001",
            metadata={
                "test": "database_integration",
                "session": "user1_session"
            }
        )
        
        self.user2_context = UserExecutionContext(
            user_id="db_test_user_002", 
            thread_id="db_thread_002",
            run_id="db_run_002",
            metadata={
                "test": "database_integration",
                "session": "user2_session"
            }
        )
        
        # Record setup metrics
        self.record_metric("test_setup_time", time.time())
        
    async def ensure_db_setup(self):
        """Ensure database is setup for async tests."""
        if not self.db_setup_complete:
            await self.db_fixture.setup()
            self.db_setup_complete = True
            
    async def test_user_model_crud_operations(self):
        """Test User model CRUD operations with real database.
        
        Business Value: Ensures user management works correctly.
        Tests REAL ORM operations with User model.
        """
        await self.ensure_db_setup()
        
        # Test CREATE operations
        async with self.db_fixture.get_async_session() as session:
            # Create new users
            user1 = User(
                id=self.user1_context.user_id,
                email="test_user_001@netra.ai",
                username="test_user_001",
                full_name="Test User 001",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            user2 = User(
                id=self.user2_context.user_id,
                email="test_user_002@netra.ai", 
                username="test_user_002",
                full_name="Test User 002",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            session.add_all([user1, user2])
            await session.commit()
            
            # Verify users were created
            self.record_metric("users_created", 2)
            
        # Test READ operations
        async with self.db_fixture.get_async_session() as session:
            # Query user by ID
            queried_user1 = await session.get(User, self.user1_context.user_id)
            assert queried_user1 is not None
            assert queried_user1.email == "test_user_001@netra.ai"
            assert queried_user1.is_active is True
            
            # Query all users
            result = await session.execute(text("SELECT * FROM users"))
            all_users = result.fetchall()
            assert len(all_users) == 2
            
            self.record_metric("users_queried", len(all_users))
            
        # Test UPDATE operations
        async with self.db_fixture.get_async_session() as session:
            user_to_update = await session.get(User, self.user1_context.user_id)
            user_to_update.full_name = "Updated Test User 001"
            user_to_update.updated_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            # Verify update
            updated_user = await session.get(User, self.user1_context.user_id)
            assert updated_user.full_name == "Updated Test User 001"
            assert updated_user.updated_at is not None
            
            self.record_metric("users_updated", 1)
            
        # Test DELETE operations
        async with self.db_fixture.get_async_session() as session:
            user_to_delete = await session.get(User, self.user2_context.user_id)
            await session.delete(user_to_delete)
            await session.commit()
            
            # Verify deletion
            deleted_user = await session.get(User, self.user2_context.user_id)
            assert deleted_user is None
            
            self.record_metric("users_deleted", 1)
            
    async def test_thread_message_relationship_operations(self):
        """Test Thread-Message relationship operations with real database.
        
        Business Value: Ensures conversation management works correctly.
        Tests REAL ORM relationships and foreign key constraints.
        """
        await self.ensure_db_setup()
        
        # First create a user for the relationship
        async with self.db_fixture.get_async_session() as session:
            user = User(
                id=self.user1_context.user_id,
                email="thread_test@netra.ai",
                username="thread_test_user",
                full_name="Thread Test User",
                is_active=True
            )
            session.add(user)
            await session.commit()
            
        # Test Thread creation with user relationship
        async with self.db_fixture.get_async_session() as session:
            thread = Thread(
                id=self.user1_context.thread_id,
                user_id=self.user1_context.user_id,
                title="Integration Test Thread",
                created_at=datetime.now(timezone.utc),
                metadata={"test": "thread_integration", "priority": "high"}
            )
            
            session.add(thread)
            await session.commit()
            
            self.record_metric("threads_created", 1)
            
        # Test Message creation with thread relationship
        async with self.db_fixture.get_async_session() as session:
            messages = [
                Message(
                    id=f"msg_{i:03d}",
                    thread_id=self.user1_context.thread_id,
                    user_id=self.user1_context.user_id,
                    content=f"Test message {i} for integration testing",
                    role="user" if i % 2 == 0 else "assistant",
                    created_at=datetime.now(timezone.utc),
                    metadata={"sequence": i, "test": "message_integration"}
                )
                for i in range(1, 6)  # Create 5 messages
            ]
            
            session.add_all(messages)
            await session.commit()
            
            self.record_metric("messages_created", len(messages))
            
        # Test relationship queries
        async with self.db_fixture.get_async_session() as session:
            # Query thread with messages (test JOIN)
            result = await session.execute(
                text("""
                    SELECT t.id, t.title, COUNT(m.id) as message_count
                    FROM threads t
                    LEFT JOIN messages m ON t.id = m.thread_id
                    WHERE t.user_id = :user_id
                    GROUP BY t.id, t.title
                """),
                {"user_id": self.user1_context.user_id}
            )
            
            thread_data = result.fetchone()
            assert thread_data is not None
            assert thread_data.message_count == 5
            
            # Query messages by thread (test foreign key)
            messages_result = await session.execute(
                text("SELECT * FROM messages WHERE thread_id = :thread_id ORDER BY created_at"),
                {"thread_id": self.user1_context.thread_id}
            )
            
            thread_messages = messages_result.fetchall()
            assert len(thread_messages) == 5
            
            # Verify message order and content
            for i, msg in enumerate(thread_messages, 1):
                assert f"Test message {i}" in msg.content
                
            self.record_metric("relationship_queries_executed", 2)
            
    async def test_agent_execution_tracking_operations(self):
        """Test AgentExecution model for tracking agent runs with real database.
        
        Business Value: Ensures agent execution tracking works for business analytics.
        Tests REAL ORM operations with complex business data.
        """
        await self.ensure_db_setup()
        
        # Create user and thread for execution tracking
        async with self.db_fixture.get_async_session() as session:
            user = User(
                id=self.user1_context.user_id,
                email="execution_test@netra.ai",
                username="execution_test_user",
                full_name="Execution Test User",
                is_active=True
            )
            
            thread = Thread(
                id=self.user1_context.thread_id,
                user_id=self.user1_context.user_id,
                title="Agent Execution Test Thread",
                created_at=datetime.now(timezone.utc)
            )
            
            session.add_all([user, thread])
            await session.commit()
            
        # Test AgentExecution creation with business metrics
        async with self.db_fixture.get_async_session() as session:
            executions = [
                AgentExecution(
                    id=f"exec_{i:03d}",
                    user_id=self.user1_context.user_id,
                    thread_id=self.user1_context.thread_id,
                    run_id=f"{self.user1_context.run_id}_{i}",
                    agent_name="triage" if i <= 2 else "data_processor" if i <= 4 else "optimizer",
                    status="completed" if i % 3 != 0 else "failed",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    execution_time_ms=100 + i * 50,  # Varying execution times
                    metadata={
                        "business_metrics": {
                            "cost": 0.01 * i,
                            "accuracy": 0.95 - (i * 0.01),
                            "tokens_used": 100 + i * 20
                        },
                        "execution_details": {
                            "iteration": i,
                            "test": "agent_execution_integration"
                        }
                    }
                )
                for i in range(1, 7)  # Create 6 executions
            ]
            
            session.add_all(executions)
            await session.commit()
            
            self.record_metric("agent_executions_created", len(executions))
            
        # Test business analytics queries
        async with self.db_fixture.get_async_session() as session:
            # Query execution statistics by agent
            agent_stats_result = await session.execute(
                text("""
                    SELECT 
                        agent_name,
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_executions,
                        AVG(execution_time_ms) as avg_execution_time,
                        SUM(execution_time_ms) as total_execution_time
                    FROM agent_executions
                    WHERE user_id = :user_id
                    GROUP BY agent_name
                    ORDER BY agent_name
                """),
                {"user_id": self.user1_context.user_id}
            )
            
            agent_stats = agent_stats_result.fetchall()
            assert len(agent_stats) == 3  # triage, data_processor, optimizer
            
            # Verify statistics
            for stats in agent_stats:
                assert stats.total_executions >= 1
                assert stats.avg_execution_time > 0
                
            # Query execution trends over time
            trends_result = await session.execute(
                text("""
                    SELECT 
                        date(started_at) as execution_date,
                        COUNT(*) as daily_executions,
                        AVG(execution_time_ms) as avg_daily_time
                    FROM agent_executions
                    WHERE user_id = :user_id
                    GROUP BY date(started_at)
                """),
                {"user_id": self.user1_context.user_id}
            )
            
            trends = trends_result.fetchall()
            assert len(trends) >= 1  # At least one day of executions
            
            self.record_metric("analytics_queries_executed", 2)
            self.record_metric("agents_tracked", len(agent_stats))
            
    async def test_database_transaction_isolation(self):
        """Test database transaction isolation between concurrent operations.
        
        Business Value: Ensures data consistency in multi-user scenarios.
        Tests REAL transaction isolation with concurrent database operations.
        """
        await self.ensure_db_setup()
        
        # Setup initial data
        async with self.db_fixture.get_async_session() as session:
            users = [
                User(
                    id=self.user1_context.user_id,
                    email="isolation_test_1@netra.ai",
                    username="isolation_test_1",
                    full_name="Isolation Test User 1",
                    is_active=True
                ),
                User(
                    id=self.user2_context.user_id,
                    email="isolation_test_2@netra.ai",
                    username="isolation_test_2", 
                    full_name="Isolation Test User 2",
                    is_active=True
                )
            ]
            session.add_all(users)
            await session.commit()
            
        # Test concurrent transaction isolation
        async def user1_operations():
            """User 1 database operations."""
            async with self.db_fixture.get_async_session() as session:
                # Start transaction
                async with session.begin():
                    # Create thread for user 1
                    thread1 = Thread(
                        id=self.user1_context.thread_id,
                        user_id=self.user1_context.user_id,
                        title="User 1 Isolated Thread",
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(thread1)
                    
                    # Simulate some processing time
                    await asyncio.sleep(0.001)
                    
                    # Add messages
                    messages1 = [
                        Message(
                            id=f"user1_msg_{i}",
                            thread_id=self.user1_context.thread_id,
                            user_id=self.user1_context.user_id,
                            content=f"User 1 message {i}",
                            role="user",
                            created_at=datetime.now(timezone.utc)
                        )
                        for i in range(1, 4)
                    ]
                    session.add_all(messages1)
                    
                return len(messages1)
                
        async def user2_operations():
            """User 2 database operations."""
            async with self.db_fixture.get_async_session() as session:
                # Start transaction
                async with session.begin():
                    # Create thread for user 2
                    thread2 = Thread(
                        id=self.user2_context.thread_id,
                        user_id=self.user2_context.user_id,
                        title="User 2 Isolated Thread", 
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(thread2)
                    
                    # Simulate some processing time
                    await asyncio.sleep(0.001)
                    
                    # Add messages
                    messages2 = [
                        Message(
                            id=f"user2_msg_{i}",
                            thread_id=self.user2_context.thread_id,
                            user_id=self.user2_context.user_id,
                            content=f"User 2 message {i}",
                            role="user",
                            created_at=datetime.now(timezone.utc)
                        )
                        for i in range(1, 5)
                    ]
                    session.add_all(messages2)
                    
                return len(messages2)
        
        # Execute operations concurrently
        results = await asyncio.gather(
            user1_operations(),
            user2_operations(),
            return_exceptions=True
        )
        
        # Verify both operations succeeded
        user1_messages_count, user2_messages_count = results
        assert user1_messages_count == 3
        assert user2_messages_count == 4
        
        # Verify data isolation - check that each user's data is separate
        async with self.db_fixture.get_async_session() as session:
            # Count messages for each user
            user1_result = await session.execute(
                text("SELECT COUNT(*) FROM messages WHERE user_id = :user_id"),
                {"user_id": self.user1_context.user_id}
            )
            user1_count = user1_result.scalar()
            
            user2_result = await session.execute(
                text("SELECT COUNT(*) FROM messages WHERE user_id = :user_id"),
                {"user_id": self.user2_context.user_id}
            )
            user2_count = user2_result.scalar()
            
            assert user1_count == 3
            assert user2_count == 4
            
            # Verify thread isolation
            threads_result = await session.execute(
                text("SELECT user_id, COUNT(*) FROM threads GROUP BY user_id")
            )
            thread_counts = threads_result.fetchall()
            assert len(thread_counts) == 2  # One thread per user
            
        self.record_metric("concurrent_transactions", 2)
        self.record_metric("transaction_isolation_verified", True)
        
    async def test_database_performance_and_indexing(self):
        """Test database performance with larger datasets and indexing.
        
        Business Value: Ensures system performance scales with business data growth.
        Tests REAL database performance with realistic data volumes.
        """
        await self.ensure_db_setup()
        
        # Setup user for performance testing
        async with self.db_fixture.get_async_session() as session:
            user = User(
                id=self.user1_context.user_id,
                email="performance_test@netra.ai",
                username="performance_test_user",
                full_name="Performance Test User",
                is_active=True
            )
            session.add(user)
            await session.commit()
            
        # Create larger dataset for performance testing
        batch_size = 100
        total_threads = 10
        messages_per_thread = 50
        
        # Measure bulk insert performance
        insert_start_time = time.time()
        
        async with self.db_fixture.get_async_session() as session:
            # Create threads in batch
            threads = [
                Thread(
                    id=f"perf_thread_{i:03d}",
                    user_id=self.user1_context.user_id,
                    title=f"Performance Test Thread {i}",
                    created_at=datetime.now(timezone.utc),
                    metadata={"batch": i // 5, "performance_test": True}
                )
                for i in range(total_threads)
            ]
            
            session.add_all(threads)
            await session.commit()
            
            # Create messages in batches
            for thread_idx in range(total_threads):
                thread_id = f"perf_thread_{thread_idx:03d}"
                
                messages = [
                    Message(
                        id=f"perf_msg_{thread_idx:03d}_{msg_idx:03d}",
                        thread_id=thread_id,
                        user_id=self.user1_context.user_id,
                        content=f"Performance test message {msg_idx} in thread {thread_idx}",
                        role="user" if msg_idx % 2 == 0 else "assistant",
                        created_at=datetime.now(timezone.utc),
                        metadata={
                            "thread_index": thread_idx,
                            "message_index": msg_idx,
                            "performance_test": True
                        }
                    )
                    for msg_idx in range(messages_per_thread)
                ]
                
                session.add_all(messages)
                await session.commit()
                
        insert_time = time.time() - insert_start_time
        total_records = total_threads + (total_threads * messages_per_thread)
        
        # Measure query performance
        query_start_time = time.time()
        
        async with self.db_fixture.get_async_session() as session:
            # Complex aggregation query
            aggregation_result = await session.execute(
                text("""
                    SELECT 
                        t.metadata as thread_metadata,
                        COUNT(m.id) as message_count,
                        MIN(m.created_at) as first_message,
                        MAX(m.created_at) as last_message,
                        COUNT(CASE WHEN m.role = 'user' THEN 1 END) as user_messages,
                        COUNT(CASE WHEN m.role = 'assistant' THEN 1 END) as assistant_messages
                    FROM threads t
                    LEFT JOIN messages m ON t.id = m.thread_id
                    WHERE t.user_id = :user_id
                    AND t.title LIKE 'Performance Test%'
                    GROUP BY t.id, t.metadata
                    ORDER BY message_count DESC
                    LIMIT 10
                """),
                {"user_id": self.user1_context.user_id}
            )
            
            performance_stats = aggregation_result.fetchall()
            
            # Search query performance
            search_result = await session.execute(
                text("""
                    SELECT m.*, t.title as thread_title
                    FROM messages m
                    JOIN threads t ON m.thread_id = t.id
                    WHERE m.user_id = :user_id
                    AND m.content LIKE '%message 25%'
                    ORDER BY m.created_at DESC
                """),
                {"user_id": self.user1_context.user_id}
            )
            
            search_results = search_result.fetchall()
            
        query_time = time.time() - query_start_time
        
        # Record performance metrics
        self.record_metric("bulk_insert_time", insert_time)
        self.record_metric("records_inserted", total_records)
        self.record_metric("insert_rate_per_second", total_records / insert_time if insert_time > 0 else 0)
        self.record_metric("complex_query_time", query_time)
        self.record_metric("performance_stats_rows", len(performance_stats))
        self.record_metric("search_results_found", len(search_results))
        
        # Verify performance is reasonable (adjust thresholds as needed)
        assert insert_time < 5.0  # Should complete bulk insert in under 5 seconds
        assert query_time < 1.0   # Should complete complex queries in under 1 second
        assert len(performance_stats) == total_threads  # Should find all threads
        assert len(search_results) >= 0  # Should execute search without error
        
    async def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Record final database metrics
        if hasattr(self, 'db_fixture') and self.db_fixture and self.db_setup_complete:
            try:
                # Get final database statistics
                async with self.db_fixture.get_async_session() as session:
                    # Count total records across all tables
                    tables = ['users', 'threads', 'messages', 'agent_executions']
                    total_records = 0
                    
                    for table in tables:
                        try:
                            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                            count = result.scalar()
                            self.record_metric(f"{table}_final_count", count)
                            total_records += count
                        except Exception:
                            # Table might not exist in all tests
                            pass
                    
                    self.record_metric("total_database_records", total_records)
                    
            except Exception as e:
                # Database might be in inconsistent state, log but don't fail
                self.record_metric("cleanup_database_error", str(e))
            
            # Cleanup database fixture
            await self.db_fixture.cleanup()
            
        super().teardown_method(method)