"""
Integration Tests: SSOT Database Pattern Violations

This test suite validates SSOT database patterns across the entire system
and exposes violations where components bypass repository patterns.

PRIMARY TARGET: test_framework/ssot/database.py:596 - Direct session.add() violation
SSOT REFERENCE: netra_backend/app/services/database/message_repository.py

Business Value:
- Ensures consistent data access patterns across all services
- Validates proper repository usage in integration scenarios  
- Prevents data corruption from bypassing business logic
- Maintains database consistency and integrity

CRITICAL: These tests use REAL services (PostgreSQL, Redis) to validate
actual integration behavior. NO MOCKS in integration testing.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Message, Thread
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.integration
class TestSSotDatabasePatternIntegration:
    """
    Integration Tests for SSOT Database Pattern Compliance
    
    These tests validate SSOT patterns work correctly with real database
    and expose violations in cross-service integration scenarios.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.db_helper = DatabaseTestUtilities(service='netra_backend')
        self.message_repository = MessageRepository()
        self.thread_repository = ThreadRepository()

    async def asyncSetUp(self):
        """Setup with real database connection."""
        self.test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'run_{uuid.uuid4().hex[:8]}'
        await self._cleanup_test_data()
        logger.info(f'Integration Test Setup - User: {self.test_user_id}, Thread: {self.test_thread_id}')

    async def asyncTearDown(self):
        """Clean up test data."""
        await self._cleanup_test_data()

    async def _cleanup_test_data(self):
        """Remove all test data from database."""
        async with self.db_helper.get_async_session() as session:
            await session.execute(text('DELETE FROM message WHERE thread_id LIKE :pattern'), {'pattern': f'{self.test_thread_id}%'})
            await session.execute(text('DELETE FROM thread WHERE id LIKE :pattern'), {'pattern': f'{self.test_thread_id}%'})
            await session.commit()

    @pytest.mark.asyncio
    async def test_ssot_cross_repository_integration(self):
        """
        CRITICAL INTEGRATION TEST: Validate SSOT patterns across multiple repositories.
        
        This test creates a complete thread + messages workflow using proper SSOT
        repositories, then compares with test framework violation patterns.
        
        EXPECTED: Test should FAIL due to inconsistencies between SSOT and violation paths.
        """
        logger.info('=== SSOT Cross-Repository Integration Test ===')
        async with self.db_helper.get_async_session() as session:
            thread_metadata = {'user_id': self.test_user_id, 'source': 'integration_test', 'created_by': 'ssot_repository'}
            ssot_thread = await self.thread_repository.create_thread(db=session, user_id=self.test_user_id, metadata=thread_metadata)
            await session.commit()
            ssot_messages = []
            for i in range(3):
                message = await self.message_repository.create_message(db=session, thread_id=ssot_thread.id, role='user' if i % 2 == 0 else 'assistant', content=f'SSOT integration test message {i + 1}', metadata={'message_index': i, 'created_by': 'ssot_repository'})
                ssot_messages.append(message)
            await session.commit()
            violation_messages = []
            for i in range(3):
                message = await self.db_helper.create_message(thread_id=ssot_thread.id, role='user' if i % 2 == 0 else 'assistant', content=f'Test framework violation message {i + 1}', metadata={'message_index': i + 10, 'created_by': 'test_framework'})
                violation_messages.append(message)
            all_messages_result = await session.execute(select(Message).where(Message.thread_id == ssot_thread.id).order_by(Message.created_at))
            all_messages = all_messages_result.scalars().all()
            assert len(all_messages) == 6, f'Expected 6 messages, got {len(all_messages)}'
            ssot_db_messages = [msg for msg in all_messages if msg.id in [m.id for m in ssot_messages]]
            violation_db_messages = [msg for msg in all_messages if msg.id not in [m.id for m in ssot_messages]]
            assert len(ssot_db_messages) == 3, 'Should have 3 SSOT messages'
            assert len(violation_db_messages) == 3, 'Should have 3 violation messages'
            for ssot_msg, violation_msg in zip(ssot_db_messages, violation_db_messages):
                assert ssot_msg.object == violation_msg.object, f'SSOT VIOLATION: object type differs - SSOT: {ssot_msg.object}, Violation: {violation_msg.object}'
                assert type(ssot_msg.content) == type(violation_msg.content), f'SSOT VIOLATION: content type differs - SSOT: {type(ssot_msg.content)}, Violation: {type(violation_msg.content)}'
                assert type(ssot_msg.metadata_) == type(violation_msg.metadata_), f'SSOT VIOLATION: metadata type differs - SSOT: {type(ssot_msg.metadata_)}, Violation: {type(violation_msg.metadata_)}'
        logger.info('SSOT Cross-Repository Integration Test Completed')

    @pytest.mark.asyncio
    async def test_ssot_database_transaction_integration(self):
        """
        CRITICAL INTEGRATION TEST: Validate transaction handling consistency.
        
        This test ensures SSOT repositories and test framework handle
        database transactions consistently in integration scenarios.
        """
        logger.info('=== SSOT Database Transaction Integration Test ===')
        async with self.db_helper.get_async_session() as session:
            try:
                ssot_thread = await self.thread_repository.create_thread(db=session, user_id=self.test_user_id, metadata={'test': 'transaction_integration'})
                ssot_message = await self.message_repository.create_message(db=session, thread_id=ssot_thread.id, role='user', content='Transaction test SSOT')
                violation_message = await self.db_helper.create_message(thread_id=ssot_thread.id, role='assistant', content='Transaction test violation')
                transaction_count = await session.execute(select(func.count()).select_from(select(Message).where(Message.thread_id == ssot_thread.id).subquery()))
                uncommitted_count = transaction_count.scalar()
                assert uncommitted_count >= 2, 'SSOT VIOLATION: Transaction isolation differs between SSOT and test framework'
                await session.rollback()
                final_count_result = await session.execute(select(func.count()).select_from(select(Message).where(Message.thread_id == ssot_thread.id).subquery()))
                final_count = final_count_result.scalar()
                assert final_count == 0, 'SSOT VIOLATION: Transaction rollback handling differs between SSOT and test framework'
            except Exception as e:
                await session.rollback()
                raise e
        logger.info('SSOT Database Transaction Integration Test Completed')

    @pytest.mark.asyncio
    async def test_ssot_database_performance_consistency(self):
        """
        INTEGRATION TEST: Validate performance characteristics consistency.
        
        This test ensures SSOT repository patterns and test framework
        violation patterns have consistent performance characteristics.
        """
        logger.info('=== SSOT Database Performance Integration Test ===')
        async with self.db_helper.get_async_session() as session:
            test_thread = await self.thread_repository.create_thread(db=session, user_id=self.test_user_id, metadata={'test': 'performance_integration'})
            await session.commit()
            ssot_start_time = time.time()
            ssot_messages = []
            for i in range(10):
                message = await self.message_repository.create_message(db=session, thread_id=test_thread.id, role='user', content=f'SSOT performance test {i}', metadata={'batch': 'ssot', 'index': i})
                ssot_messages.append(message)
            await session.commit()
            ssot_duration = time.time() - ssot_start_time
            violation_start_time = time.time()
            violation_messages = []
            for i in range(10):
                message = await self.db_helper.create_message(thread_id=test_thread.id, role='user', content=f'Violation performance test {i}', metadata={'batch': 'violation', 'index': i})
                violation_messages.append(message)
            violation_duration = time.time() - violation_start_time
            performance_ratio = max(ssot_duration, violation_duration) / min(ssot_duration, violation_duration)
            assert performance_ratio < 3.0, f'SSOT VIOLATION: Significant performance difference - SSOT: {ssot_duration:.3f}s, Violation: {violation_duration:.3f}s'
            logger.info(f'Performance Comparison - SSOT: {ssot_duration:.3f}s, Violation: {violation_duration:.3f}s')
        logger.info('SSOT Database Performance Integration Test Completed')

    @pytest.mark.asyncio
    async def test_ssot_database_error_handling_integration(self):
        """
        INTEGRATION TEST: Validate error handling consistency.
        
        This test ensures both SSOT repository and test framework violation
        handle database errors consistently in integration scenarios.
        """
        logger.info('=== SSOT Database Error Handling Integration Test ===')
        async with self.db_helper.get_async_session() as session:
            invalid_thread_id = 'invalid_thread_999'
            ssot_error = None
            try:
                await self.message_repository.create_message(db=session, thread_id=invalid_thread_id, role='user', content='SSOT error test')
                await session.commit()
            except Exception as e:
                ssot_error = e
                await session.rollback()
            violation_error = None
            try:
                await self.db_helper.create_message(thread_id=invalid_thread_id, role='user', content='Violation error test')
            except Exception as e:
                violation_error = e
            assert ssot_error is not None, 'SSOT repository should raise error for invalid thread'
            assert violation_error is not None, 'Test framework should raise error for invalid thread'
            assert type(ssot_error).__name__ == type(violation_error).__name__, f'SSOT VIOLATION: Error types differ - SSOT: {type(ssot_error)}, Violation: {type(violation_error)}'
        logger.info('SSOT Database Error Handling Integration Test Completed')

@pytest.mark.integration
class TestSSotDatabaseConcurrencyIntegration:
    """
    Integration Tests for SSOT Database Concurrency Patterns
    
    These tests validate SSOT patterns work correctly under concurrent
    access scenarios and expose any concurrency handling violations.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.db_helper = DatabaseTestUtilities(service='netra_backend')
        self.message_repository = MessageRepository()
        self.thread_repository = ThreadRepository()

    @pytest.mark.asyncio
    async def test_ssot_concurrent_message_creation(self):
        """
        CONCURRENCY INTEGRATION TEST: Validate concurrent message creation.
        
        This test ensures SSOT repository and test framework violation
        handle concurrent operations consistently.
        """
        logger.info('=== SSOT Concurrent Message Creation Test ===')
        test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        test_user_id = f'user_{uuid.uuid4().hex[:8]}'
        try:
            async with self.db_helper.get_async_session() as session:
                test_thread = await self.thread_repository.create_thread(db=session, user_id=test_user_id, metadata={'test': 'concurrency'})
                await session.commit()

                async def create_ssot_messages():
                    """Create messages via SSOT repository."""
                    messages = []
                    async with self.db_helper.get_async_session() as session:
                        for i in range(5):
                            message = await self.message_repository.create_message(db=session, thread_id=test_thread.id, role='user', content=f'SSOT concurrent {i}', metadata={'source': 'ssot', 'batch': i})
                            messages.append(message)
                        await session.commit()
                    return messages

                async def create_violation_messages():
                    """Create messages via test framework violation."""
                    messages = []
                    for i in range(5):
                        message = await self.db_helper.create_message(thread_id=test_thread.id, role='assistant', content=f'Violation concurrent {i}', metadata={'source': 'violation', 'batch': i})
                        messages.append(message)
                    return messages
                ssot_task = asyncio.create_task(create_ssot_messages())
                violation_task = asyncio.create_task(create_violation_messages())
                ssot_results, violation_results = await asyncio.gather(ssot_task, violation_task, return_exceptions=True)
                assert not isinstance(ssot_results, Exception), f'SSOT concurrent creation failed: {ssot_results}'
                assert not isinstance(violation_results, Exception), f'Violation concurrent creation failed: {violation_results}'
                async with self.db_helper.get_async_session() as session:
                    final_count_result = await session.execute(select(func.count()).select_from(select(Message).where(Message.thread_id == test_thread.id).subquery()))
                    final_count = final_count_result.scalar()
                    assert final_count == 10, f'Expected 10 messages, got {final_count}'
        finally:
            async with self.db_helper.get_async_session() as session:
                await session.execute(text('DELETE FROM message WHERE thread_id = :thread_id'), {'thread_id': test_thread_id})
                await session.execute(text('DELETE FROM thread WHERE id = :thread_id'), {'thread_id': test_thread_id})
                await session.commit()
        logger.info('SSOT Concurrent Message Creation Test Completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')