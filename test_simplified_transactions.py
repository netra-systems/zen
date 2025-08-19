"""
Simplified Transaction Boundary Tests

CRITICAL: These tests validate transaction boundaries across all operations to prevent data corruption.
All tests use real databases and verify actual state to ensure transaction integrity.

SUCCESS CRITERIA:
- Transactions properly isolated
- Rollbacks work correctly  
- No partial commits
- Concurrent operations safe
"""

import asyncio
import pytest
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DisconnectionError
from sqlalchemy import select, text, func

from app.db.postgres import get_postgres_session
from app.db.transaction_core import (
    TransactionManager, TransactionConfig, TransactionIsolationLevel,
    transactional, with_deadlock_retry, with_serializable_retry
)
from app.services.transaction_manager import transaction_manager as distributed_tx_manager
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
from app.db.models_postgres import User, Thread, Message
from app.core.exceptions import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestTransactionBoundaries:
    """Test transaction boundaries for data integrity."""
    
    @pytest.fixture
    async def db_session(self):
        """Create isolated database session for testing."""
        async with get_postgres_session() as session:
            # Start with clean transaction
            await session.rollback()
            yield session
            # Cleanup after test
            await session.rollback()
    
    @pytest.fixture
    def message_repository(self):
        """Create message repository instance."""
        return MessageRepository()
    
    @pytest.fixture
    def thread_repository(self):
        """Create thread repository instance.""" 
        return ThreadRepository()
    
    @pytest.fixture
    def transaction_manager(self):
        """Create transaction manager instance."""
        return TransactionManager()

    async def _create_test_user_data(self) -> Dict[str, Any]:
        """Create test user data."""
        return {
            'id': str(uuid.uuid4()),
            'email': f'test_{uuid.uuid4()}@example.com',
            'name': 'Test User',
            'full_name': 'Test User',
            'is_active': True,
            'role': 'user'
        }
    
    async def _create_test_user(self, session: AsyncSession, user_data: Dict[str, Any]) -> User:
        """Create test user directly."""
        user = User(**user_data)
        session.add(user)
        await session.flush()  # Flush but don't commit
        return user
    
    async def _verify_user_exists(self, session: AsyncSession, user_id: str) -> bool:
        """Verify user exists in database."""
        result = await session.execute(
            select(func.count(User.id)).where(User.id == user_id)
        )
        return result.scalar() > 0
    
    async def _verify_user_not_exists(self, session: AsyncSession, user_id: str) -> bool:
        """Verify user does not exist in database."""
        return not await self._verify_user_exists(session, user_id)


class TestUserCreationTransactions(TestTransactionBoundaries):
    """Test user creation transaction boundaries - all or nothing behavior."""
    
    @pytest.mark.asyncio
    async def test_user_creation_success_commits_all(self, db_session):
        """Test successful user creation commits all related data."""
        user_data = await self._create_test_user_data()
        
        async with transactional(db_session) as tx_metrics:
            user = await self._create_test_user(db_session, user_data)
            
            # Verify user created in transaction
            assert user is not None
            assert user.id == user_data['id']
            assert user.email == user_data['email']
            
            # Verify transaction metrics
            assert tx_metrics.transaction_id is not None
            assert tx_metrics.start_time > 0
        
        # Verify user persisted after transaction commit
        await db_session.commit()
        assert await self._verify_user_exists(db_session, user_data['id'])
    
    @pytest.mark.asyncio
    async def test_user_creation_integrity_error_rolls_back_all(self, db_session):
        """Test user creation with integrity error rolls back all changes."""
        user_data = await self._create_test_user_data()
        
        # First create user successfully
        async with transactional(db_session) as tx_metrics:
            await self._create_test_user(db_session, user_data)
        await db_session.commit()
        
        # Attempt to create duplicate user - should fail
        with pytest.raises((IntegrityError, SQLAlchemyError)):
            async with transactional(db_session) as tx_metrics:
                await self._create_test_user(db_session, user_data)
        
        # Verify only one user exists
        result = await db_session.execute(
            select(func.count(User.id)).where(User.email == user_data['email'])
        )
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_user_creation_with_related_data_transaction(self, db_session, thread_repository):
        """Test user creation with related thread data maintains transaction boundary."""
        user_data = await self._create_test_user_data()
        
        async with transactional(db_session) as tx_metrics:
            # Create user
            user = await self._create_test_user(db_session, user_data)
            assert user is not None
            
            # Create related thread
            thread = await thread_repository.create(
                db_session,
                title='Test Thread',
                metadata_={'user_id': user.id}
            )
            assert thread is not None
            assert thread.metadata_.get('user_id') == user.id
        
        # Verify both user and thread committed
        await db_session.commit()
        assert await self._verify_user_exists(db_session, user.id)
        
        result = await db_session.execute(
            select(func.count(Thread.id)).where(
                Thread.metadata_.op('->>')('user_id') == user.id
            )
        )
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_user_creation_partial_failure_rolls_back_all(self, db_session, thread_repository):
        """Test that partial failure in user creation process rolls back everything."""
        user_data = await self._create_test_user_data()
        
        with pytest.raises(Exception):
            async with transactional(db_session) as tx_metrics:
                # Create user successfully
                user = await self._create_test_user(db_session, user_data)
                assert user is not None
                
                # Force thread creation to fail
                with patch.object(thread_repository, 'create', side_effect=SQLAlchemyError("Forced failure")):
                    await thread_repository.create(
                        db_session,
                        title='Test Thread', 
                        metadata_={'user_id': user.id}
                    )
        
        # Verify nothing was committed
        await db_session.rollback()
        assert await self._verify_user_not_exists(db_session, user_data['id'])


class TestMessageSaveTransactions(TestTransactionBoundaries):
    """Test message save transaction isolation and rollback scenarios."""
    
    async def _create_test_thread(self, db_session, user_id: str) -> Thread:
        """Create test thread for message tests."""
        thread_repo = ThreadRepository()
        return await thread_repo.create(
            db_session,
            title='Test Thread',
            metadata_={'user_id': user_id}
        )
    
    @pytest.mark.asyncio
    async def test_message_save_transaction_integrity(self, db_session, message_repository):
        """Test message save maintains transaction integrity."""
        # Setup test data
        user_data = await self._create_test_user_data()
        
        async with transactional(db_session) as tx_metrics:
            user = await self._create_test_user(db_session, user_data)
            thread = await self._create_test_thread(db_session, user.id)
            
            # Create message
            message = await message_repository.create_message(
                db_session,
                thread_id=thread.id,
                role='user',
                content='Test message content'
            )
            
            assert message is not None
            assert message.thread_id == thread.id
            assert message.role == 'user'
            assert 'Test message content' in str(message.content)
        
        # Verify all committed together
        await db_session.commit()
        result = await db_session.execute(
            select(func.count(Message.id)).where(Message.thread_id == thread.id)
        )
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_message_save_rollback_on_error(self, db_session, message_repository):
        """Test message save rollback when error occurs."""
        user_data = await self._create_test_user_data()
        
        # Setup user and thread
        async with transactional(db_session):
            user = await self._create_test_user(db_session, user_data)
            thread = await self._create_test_thread(db_session, user.id)
        await db_session.commit()
        
        # Attempt message creation with forced failure
        with pytest.raises(Exception):
            async with transactional(db_session) as tx_metrics:
                # Create first message successfully  
                message1 = await message_repository.create_message(
                    db_session,
                    thread_id=thread.id,
                    role='user',
                    content='First message'
                )
                assert message1 is not None
                
                # Force second message to fail
                with patch.object(message_repository, 'create_message', side_effect=SQLAlchemyError("Forced failure")):
                    await message_repository.create_message(
                        db_session,
                        thread_id=thread.id,
                        role='assistant', 
                        content='Second message'
                    )
        
        # Verify no messages were committed
        await db_session.rollback()
        result = await db_session.execute(
            select(func.count(Message.id)).where(Message.thread_id == thread.id)
        )
        assert result.scalar() == 0

    @pytest.mark.asyncio
    async def test_message_batch_transaction_atomicity(self, db_session, message_repository):
        """Test batch message operations are atomic."""
        user_data = await self._create_test_user_data()
        
        # Setup user and thread
        async with transactional(db_session):
            user = await self._create_test_user(db_session, user_data)
            thread = await self._create_test_thread(db_session, user.id)
        await db_session.commit()
        
        # Test batch message creation
        messages_data = [
            {'role': 'user', 'content': 'Message 1'},
            {'role': 'assistant', 'content': 'Message 2'}, 
            {'role': 'user', 'content': 'Message 3'}
        ]
        
        async with transactional(db_session) as tx_metrics:
            created_messages = []
            for msg_data in messages_data:
                message = await message_repository.create_message(
                    db_session,
                    thread_id=thread.id,
                    role=msg_data['role'],
                    content=msg_data['content']
                )
                created_messages.append(message)
                assert message is not None
        
        # Verify all messages committed together
        await db_session.commit()
        result = await db_session.execute(
            select(func.count(Message.id)).where(Message.thread_id == thread.id)
        )
        assert result.scalar() == len(messages_data)


class TestConcurrentTransactionHandling(TestTransactionBoundaries):
    """Test concurrent transaction handling and isolation levels."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_creation_isolation(self):
        """Test concurrent user creation maintains proper isolation."""
        # Create multiple concurrent user creation tasks
        user_tasks = []
        for i in range(3):
            user_data = await self._create_test_user_data()
            task = asyncio.create_task(
                self._create_user_with_transaction(user_data)
            )
            user_tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Verify all succeeded without interference
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        assert success_count == 3
    
    async def _create_user_with_transaction(self, user_data):
        """Helper to create user within transaction."""
        try:
            async with get_postgres_session() as session:
                async with transactional(session):
                    user = await self._create_test_user(session, user_data)
                    # Simulate processing time
                    await asyncio.sleep(0.1)
                await session.commit()
                return {'success': True, 'user_id': user.id}
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @pytest.mark.asyncio
    async def test_concurrent_message_creation_isolation(self, message_repository):
        """Test concurrent message creation maintains isolation."""
        # Setup shared thread
        async with get_postgres_session() as session:
            user_data = await self._create_test_user_data()
            async with transactional(session):
                user = await self._create_test_user(session, user_data)
                thread = await self._create_test_thread(session, user.id)
            await session.commit()
            
            # Create concurrent message tasks
            message_tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    self._create_message_with_transaction(
                        message_repository, thread.id, f"Message {i}"
                    )
                )
                message_tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Verify all messages created without conflicts
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            assert success_count == 5
            
            # Verify final message count
            result = await session.execute(
                select(func.count(Message.id)).where(Message.thread_id == thread.id)
            )
            assert result.scalar() == 5
    
    async def _create_message_with_transaction(self, message_repository, thread_id, content):
        """Helper to create message within transaction."""
        try:
            async with get_postgres_session() as session:
                async with transactional(session):
                    message = await message_repository.create_message(
                        session,
                        thread_id=thread_id,
                        role='user',
                        content=content
                    )
                await session.commit()
                return {'success': True, 'message_id': message.id}
        except Exception as e:
            logger.error(f"Message creation failed: {e}")
            return {'success': False, 'error': str(e)}


class TestDistributedTransactions(TestTransactionBoundaries):
    """Test distributed transaction scenarios across multiple services."""
    
    @pytest.mark.asyncio
    async def test_distributed_transaction_commit(self):
        """Test distributed transaction commits across services."""
        async with distributed_tx_manager.transaction() as tx_id:
            # Add operations to transaction
            from app.core.error_recovery import OperationType
            op1_id = await distributed_tx_manager.add_operation(
                tx_id, 
                OperationType.DATABASE_WRITE,
                {'entity': 'User', 'operation': 'create'}
            )
            
            op2_id = await distributed_tx_manager.add_operation(
                tx_id,
                OperationType.DATABASE_WRITE, 
                {'entity': 'Thread', 'operation': 'create'}
            )
            
            # Mark operations as completed
            await distributed_tx_manager.complete_operation(tx_id, op1_id)
            await distributed_tx_manager.complete_operation(tx_id, op2_id)
        
        # Transaction should auto-commit
        # Verify transaction no longer active
        assert tx_id not in distributed_tx_manager.active_transactions
    
    @pytest.mark.asyncio
    async def test_distributed_transaction_rollback(self):
        """Test distributed transaction rollback on failure."""
        with pytest.raises(Exception):
            async with distributed_tx_manager.transaction() as tx_id:
                # Add operations
                from app.core.error_recovery import OperationType
                op1_id = await distributed_tx_manager.add_operation(
                    tx_id,
                    OperationType.DATABASE_WRITE,
                    {'entity': 'User', 'operation': 'create'}
                )
                
                await distributed_tx_manager.complete_operation(tx_id, op1_id)
                
                # Force failure
                raise RuntimeError("Simulated failure")
        
        # Verify transaction was rolled back
        assert tx_id not in distributed_tx_manager.active_transactions
    
    @pytest.mark.asyncio
    async def test_distributed_transaction_partial_failure_compensation(self):
        """Test distributed transaction compensation on partial failure."""
        tx_id = await distributed_tx_manager.begin_transaction()
        
        try:
            # Complete first operation
            from app.core.error_recovery import OperationType
            op1_id = await distributed_tx_manager.add_operation(
                tx_id,
                OperationType.DATABASE_WRITE,
                {'entity': 'User', 'operation': 'create'}
            )
            await distributed_tx_manager.complete_operation(tx_id, op1_id)
            
            # Fail second operation
            op2_id = await distributed_tx_manager.add_operation(
                tx_id,
                OperationType.DATABASE_WRITE,
                {'entity': 'Thread', 'operation': 'create'}
            )
            await distributed_tx_manager.fail_operation(
                tx_id, op2_id, "Operation failed"
            )
            
            # Attempt commit should fail
            success = await distributed_tx_manager.commit_transaction(tx_id)
            assert not success
            
        finally:
            # Verify rollback occurred
            if tx_id in distributed_tx_manager.active_transactions:
                await distributed_tx_manager.rollback_transaction(tx_id)


class TestTransactionRollbackMechanisms(TestTransactionBoundaries):
    """Test transaction rollback mechanisms across PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_postgresql_transaction_rollback(self, db_session):
        """Test PostgreSQL transaction rollback mechanics."""
        user_data = await self._create_test_user_data()
        
        # Test explicit rollback
        async with transactional(db_session) as tx_metrics:
            user = await self._create_test_user(db_session, user_data)
            assert user is not None
            
            # Explicit rollback
            await db_session.rollback()
        
        # Verify user not persisted
        assert await self._verify_user_not_exists(db_session, user_data['id'])
    
    @pytest.mark.asyncio
    async def test_serializable_transaction_conflict_retry(self):
        """Test serializable transaction retry on conflict."""
        user_data = await self._create_test_user_data()
        
        async def create_user_serializable():
            async with get_postgres_session() as session:
                return await with_serializable_retry(
                    session,
                    lambda: self._create_test_user(session, user_data),
                    max_attempts=3
                )
        
        # Execute operation with serializable retry
        user = await create_user_serializable()
        assert user is not None
        assert user.email == user_data['email']
    
    @pytest.mark.asyncio
    async def test_deadlock_retry_mechanism(self):
        """Test deadlock retry mechanism."""
        user_data = await self._create_test_user_data()
        
        async def create_user_with_deadlock_retry():
            async with get_postgres_session() as session:
                return await with_deadlock_retry(
                    session,
                    lambda: self._create_test_user(session, user_data),
                    max_attempts=3
                )
        
        # Execute with deadlock retry
        user = await create_user_with_deadlock_retry()
        assert user is not None
        assert user.id == user_data['id']


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])