"""
Test Database Persistence and Transaction Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data integrity and ACID compliance for all user operations
- Value Impact: Data persistence failures would cause user data loss and platform unreliability
- Strategic Impact: Database integrity is foundation of platform trust and reliability

This test suite validates database persistence and transaction handling:
1. ACID transaction compliance with rollback scenarios
2. Concurrent user data operations with proper isolation
3. Database session management and connection pooling
4. Data consistency across user context boundaries
"""

import asyncio
import uuid
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, SessionID,
    ensure_user_id, ensure_thread_id, ensure_run_id
)

# Database and persistence components
from netra_backend.app.database import get_db, DatabaseManager
from netra_backend.app.dependencies import validate_session_is_request_scoped
from netra_backend.app.services.database_service import DatabaseTransactionManager
from netra_backend.app.factories.data_access_factory import DataAccessFactory

# Models for testing
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread, Message
from netra_backend.app.models.session import Session
from netra_backend.app.models.agent_execution import AgentExecution


class TestDatabaseTransactionIntegration(BaseIntegrationTest):
    """Test database transactions and persistence with real PostgreSQL."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_acid_transaction_rollback_on_error(self, real_services_fixture, isolated_env):
        """Test ACID compliance with automatic rollback on transaction errors."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        validate_session_is_request_scoped(db, "acid_test")
        
        # Setup initial data
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        initial_user = User(
            id=str(user_id),
            email="acid.test@example.com",
            name="ACID Test User",
            created_at=datetime.utcnow()
        )
        
        db.add(initial_user)
        await db.commit()
        
        # Verify user was created
        db_user = await db.get(User, str(user_id))
        assert db_user is not None
        assert db_user.email == "acid.test@example.com"
        
        # Test transaction rollback scenario
        transaction_manager = DatabaseTransactionManager(db)
        
        try:
            async with transaction_manager.atomic_transaction():
                # Add a thread within transaction
                test_thread = Thread(
                    id=str(thread_id),
                    user_id=str(user_id),
                    title="ACID Test Thread",
                    created_at=datetime.utcnow()
                )
                db.add(test_thread)
                
                # Add a message within the same transaction
                message_id = str(uuid.uuid4())
                test_message = Message(
                    id=message_id,
                    thread_id=str(thread_id),
                    user_id=str(user_id),
                    content="Test message content",
                    created_at=datetime.utcnow()
                )
                db.add(test_message)
                
                # Force an error to trigger rollback
                # Create duplicate user with same ID (should fail)
                duplicate_user = User(
                    id=str(user_id),  # Same ID - should cause integrity error
                    email="duplicate@example.com",
                    name="Duplicate User"
                )
                db.add(duplicate_user)
                
                await db.flush()  # This should raise IntegrityError
                
        except IntegrityError:
            # Expected error - transaction should rollback
            pass
        
        # Verify rollback occurred - thread and message should not exist
        db_thread = await db.get(Thread, str(thread_id))
        assert db_thread is None, "Transaction rollback failed - thread still exists"
        
        # Verify original user still exists and unchanged
        db_user = await db.get(User, str(user_id))
        assert db_user is not None
        assert db_user.email == "acid.test@example.com"  # Original data intact
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_database_operations_isolation(self, real_services_fixture, isolated_env):
        """Test concurrent database operations maintain proper isolation."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create multiple users for concurrent testing
        user_count = 5
        user_ids = [ensure_user_id(str(uuid.uuid4())) for _ in range(user_count)]
        
        async def create_user_with_data(user_id: UserID, user_index: int):
            """Create user with associated threads and messages."""
            
            # Each concurrent operation gets its own transaction scope
            async with db.begin():
                user = User(
                    id=str(user_id),
                    email=f"concurrent.{user_index}@test.com",
                    name=f"Concurrent User {user_index}",
                    created_at=datetime.utcnow()
                )
                db.add(user)
                
                # Create multiple threads per user
                for thread_index in range(3):
                    thread_id = ensure_thread_id(str(uuid.uuid4()))
                    thread = Thread(
                        id=str(thread_id),
                        user_id=str(user_id),
                        title=f"Thread {thread_index} for User {user_index}",
                        created_at=datetime.utcnow()
                    )
                    db.add(thread)
                    
                    # Create messages in each thread
                    for msg_index in range(2):
                        message = Message(
                            id=str(uuid.uuid4()),
                            thread_id=str(thread_id),
                            user_id=str(user_id),
                            content=f"Message {msg_index} in Thread {thread_index}",
                            created_at=datetime.utcnow()
                        )
                        db.add(message)
                
                await db.flush()
                return user_id
        
        # Execute concurrent database operations
        tasks = [
            create_user_with_data(user_ids[i], i) 
            for i in range(user_count)
        ]
        
        completed_user_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        for result in completed_user_ids:
            assert not isinstance(result, Exception), f"Concurrent operation failed: {result}"
        
        # Verify data isolation - each user should have exactly their own data
        for i, user_id in enumerate(user_ids):
            # Check user exists
            db_user = await db.get(User, str(user_id))
            assert db_user is not None
            assert db_user.email == f"concurrent.{i}@test.com"
            
            # Check user has exactly 3 threads
            user_threads = await db.execute(
                select(Thread).where(Thread.user_id == str(user_id))
            )
            threads = user_threads.scalars().all()
            assert len(threads) == 3, f"User {i} should have 3 threads, got {len(threads)}"
            
            # Check each thread has exactly 2 messages
            for thread in threads:
                thread_messages = await db.execute(
                    select(Message).where(Message.thread_id == thread.id)
                )
                messages = thread_messages.scalars().all()
                assert len(messages) == 2, f"Thread should have 2 messages, got {len(messages)}"
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_pooling_and_session_management(self, real_services_fixture, isolated_env):
        """Test database connection pooling and proper session lifecycle management."""
        
        # Create multiple database sessions to test pooling
        session_count = 10
        sessions = []
        
        # Create sessions concurrently
        for i in range(session_count):
            db_session = real_services_fixture.get("db") or self._create_test_db_session()
            validate_session_is_request_scoped(db_session, f"pooling_test_{i}")
            sessions.append(db_session)
        
        # Test operations across all sessions concurrently
        async def perform_database_operations(session: AsyncSession, session_index: int):
            """Perform database operations using a specific session."""
            
            user_id = ensure_user_id(str(uuid.uuid4()))
            
            # Create user
            user = User(
                id=str(user_id),
                email=f"session.{session_index}@pool.test",
                name=f"Pool Test User {session_index}",
                created_at=datetime.utcnow()
            )
            
            session.add(user)
            await session.commit()
            
            # Verify user creation
            db_user = await session.get(User, str(user_id))
            assert db_user is not None
            
            # Perform additional operations
            thread_id = ensure_thread_id(str(uuid.uuid4()))
            thread = Thread(
                id=str(thread_id),
                user_id=str(user_id),
                title=f"Pool Test Thread {session_index}",
                created_at=datetime.utcnow()
            )
            
            session.add(thread)
            await session.commit()
            
            return user_id, thread_id
        
        # Execute operations across all sessions concurrently
        operation_tasks = [
            perform_database_operations(sessions[i], i) 
            for i in range(session_count)
        ]
        
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        assert len(results) == session_count
        for result in results:
            assert not isinstance(result, Exception), f"Session operation failed: {result}"
            user_id, thread_id = result
            assert user_id is not None
            assert thread_id is not None
        
        # Cleanup all sessions
        cleanup_tasks = [session.close() for session in sessions]
        await asyncio.gather(*cleanup_tasks)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_consistency_across_user_boundaries(self, real_services_fixture, isolated_env):
        """Test data consistency enforcement across user context boundaries."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create users with overlapping data scenarios
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        # Create users
        user1 = User(id=str(user1_id), email="boundary1@test.com", name="Boundary User 1")
        user2 = User(id=str(user2_id), email="boundary2@test.com", name="Boundary User 2")
        
        db.add_all([user1, user2])
        await db.commit()
        
        # Create threads with potential for cross-contamination
        thread1_id = ensure_thread_id(str(uuid.uuid4()))
        thread2_id = ensure_thread_id(str(uuid.uuid4()))
        
        thread1 = Thread(
            id=str(thread1_id),
            user_id=str(user1_id),
            title="User 1 Private Thread",
            created_at=datetime.utcnow()
        )
        
        thread2 = Thread(
            id=str(thread2_id),
            user_id=str(user2_id),
            title="User 2 Private Thread", 
            created_at=datetime.utcnow()
        )
        
        db.add_all([thread1, thread2])
        await db.commit()
        
        # Test data access factory with user isolation
        data_factory1 = DataAccessFactory(user_id=user1_id, database_session=db)
        data_factory2 = DataAccessFactory(user_id=user2_id, database_session=db)
        
        # Each factory should only access its user's data
        user1_threads = await data_factory1.get_user_threads()
        user2_threads = await data_factory2.get_user_threads()
        
        user1_thread_ids = [thread.id for thread in user1_threads]
        user2_thread_ids = [thread.id for thread in user2_threads]
        
        # Verify boundary enforcement
        assert str(thread1_id) in user1_thread_ids
        assert str(thread2_id) not in user1_thread_ids, "User 1 can access User 2's thread - boundary violation!"
        
        assert str(thread2_id) in user2_thread_ids
        assert str(thread1_id) not in user2_thread_ids, "User 2 can access User 1's thread - boundary violation!"
        
        # Test cross-user operation prevention
        with pytest.raises(PermissionError):
            # User1 factory should not be able to modify User2's data
            await data_factory1.update_thread(
                thread_id=thread2_id,
                updates={"title": "Unauthorized modification attempt"}
            )
        
        # Verify original data remains intact
        db_thread2 = await db.get(Thread, str(thread2_id))
        assert db_thread2.title == "User 2 Private Thread", "Unauthorized modification succeeded!"
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_data_persistence(self, real_services_fixture, isolated_env):
        """Test agent execution data is properly persisted with transaction integrity."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Setup user and thread
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        run_id = ensure_run_id(str(uuid.uuid4()))
        
        user = User(id=str(user_id), email="execution@test.com", name="Execution Test User")
        thread = Thread(id=str(thread_id), user_id=str(user_id), title="Execution Test Thread")
        
        db.add_all([user, thread])
        await db.commit()
        
        # Test agent execution persistence with transaction
        transaction_manager = DatabaseTransactionManager(db)
        
        execution_id = str(uuid.uuid4())
        
        async with transaction_manager.atomic_transaction():
            # Create agent execution record
            agent_execution = AgentExecution(
                id=execution_id,
                user_id=str(user_id),
                thread_id=str(thread_id),
                run_id=str(run_id),
                agent_type="test_agent",
                status="running",
                started_at=datetime.utcnow(),
                input_data={"query": "test execution query"},
                metadata={"test_source": "integration_test"}
            )
            
            db.add(agent_execution)
            await db.flush()
            
            # Create associated message during execution
            message = Message(
                id=str(uuid.uuid4()),
                thread_id=str(thread_id),
                user_id=str(user_id),
                content="Agent execution in progress",
                message_type="system",
                created_at=datetime.utcnow(),
                agent_execution_id=execution_id
            )
            
            db.add(message)
            await db.flush()
            
            # Update execution status
            agent_execution.status = "completed"
            agent_execution.completed_at = datetime.utcnow()
            agent_execution.output_data = {
                "result": "execution completed successfully",
                "metrics": {
                    "duration_seconds": 5.2,
                    "tool_calls": 3,
                    "tokens_used": 150
                }
            }
            
            await db.flush()
        
        # Verify all data was persisted correctly
        db_execution = await db.get(AgentExecution, execution_id)
        assert db_execution is not None
        assert db_execution.status == "completed"
        assert db_execution.output_data["result"] == "execution completed successfully"
        assert db_execution.output_data["metrics"]["duration_seconds"] == 5.2
        
        # Verify message was linked to execution
        execution_message = await db.execute(
            select(Message).where(Message.agent_execution_id == execution_id)
        )
        message = execution_message.scalar_one()
        assert message.content == "Agent execution in progress"
        assert message.thread_id == str(thread_id)
        
        await db.close()

    def _create_test_db_session(self) -> AsyncSession:
        """Create test database session with transaction support."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.begin = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session