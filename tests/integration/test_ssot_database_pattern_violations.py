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

# SSOT Imports - Absolute imports only
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestUtility
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
        self.db_helper = DatabaseTestUtility(service="netra_backend")
        self.message_repository = MessageRepository()
        self.thread_repository = ThreadRepository()
        
    async def asyncSetUp(self):
        """Setup with real database connection."""
        # Generate unique test identifiers
        self.test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
        logger.info(f"Integration Test Setup - User: {self.test_user_id}, Thread: {self.test_thread_id}")
        
    async def asyncTearDown(self):
        """Clean up test data."""
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Remove all test data from database."""
        async with self.db_helper.get_async_session() as session:
            # Clean messages first (foreign key dependency)
            await session.execute(
                text("DELETE FROM message WHERE thread_id LIKE :pattern"),
                {"pattern": f"{self.test_thread_id}%"}
            )
            # Clean threads
            await session.execute(
                text("DELETE FROM thread WHERE id LIKE :pattern"),
                {"pattern": f"{self.test_thread_id}%"}
            )
            await session.commit()
            
    @pytest.mark.asyncio
    async def test_ssot_cross_repository_integration(self):
        """
        CRITICAL INTEGRATION TEST: Validate SSOT patterns across multiple repositories.
        
        This test creates a complete thread + messages workflow using proper SSOT
        repositories, then compares with test framework violation patterns.
        
        EXPECTED: Test should FAIL due to inconsistencies between SSOT and violation paths.
        """
        logger.info("=== SSOT Cross-Repository Integration Test ===")
        
        async with self.db_helper.get_async_session() as session:
            # 1. Create thread using SSOT repository (proper pattern)
            thread_metadata = {
                "user_id": self.test_user_id,
                "source": "integration_test",
                "created_by": "ssot_repository"
            }
            
            ssot_thread = await self.thread_repository.create_thread(
                db=session,
                user_id=self.test_user_id,
                metadata=thread_metadata
            )
            await session.commit()
            
            # 2. Create messages using SSOT repository (proper pattern)
            ssot_messages = []
            for i in range(3):
                message = await self.message_repository.create_message(
                    db=session,
                    thread_id=ssot_thread.id,
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"SSOT integration test message {i + 1}",
                    metadata={"message_index": i, "created_by": "ssot_repository"}
                )
                ssot_messages.append(message)
            await session.commit()
            
            # 3. Create messages using TEST FRAMEWORK (VIOLATION pattern)
            # This exposes the violation by using direct session.add()
            violation_messages = []
            for i in range(3):
                message = await self.db_helper.create_message(
                    thread_id=ssot_thread.id,
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Test framework violation message {i + 1}",
                    metadata={"message_index": i + 10, "created_by": "test_framework"}
                )
                violation_messages.append(message)
                
            # 4. CRITICAL COMPARISON: Validate integration consistency
            
            # Get all messages for the thread
            all_messages_result = await session.execute(
                select(Message)
                .where(Message.thread_id == ssot_thread.id)
                .order_by(Message.created_at)
            )
            all_messages = all_messages_result.scalars().all()
            
            # Should have 6 messages total (3 SSOT + 3 violation)
            assert len(all_messages) == 6, f"Expected 6 messages, got {len(all_messages)}"
            
            # Separate SSOT vs violation messages
            ssot_db_messages = [msg for msg in all_messages if msg.id in [m.id for m in ssot_messages]]
            violation_db_messages = [msg for msg in all_messages if msg.id not in [m.id for m in ssot_messages]]
            
            assert len(ssot_db_messages) == 3, "Should have 3 SSOT messages"
            assert len(violation_db_messages) == 3, "Should have 3 violation messages"
            
            # CRITICAL ASSERTION: Structure consistency (will FAIL due to violation)
            for ssot_msg, violation_msg in zip(ssot_db_messages, violation_db_messages):
                # Object type consistency
                assert ssot_msg.object == violation_msg.object, \
                    f"SSOT VIOLATION: object type differs - SSOT: {ssot_msg.object}, Violation: {violation_msg.object}"
                
                # Content structure consistency
                assert type(ssot_msg.content) == type(violation_msg.content), \
                    f"SSOT VIOLATION: content type differs - SSOT: {type(ssot_msg.content)}, Violation: {type(violation_msg.content)}"
                
                # Metadata handling consistency
                assert type(ssot_msg.metadata_) == type(violation_msg.metadata_), \
                    f"SSOT VIOLATION: metadata type differs - SSOT: {type(ssot_msg.metadata_)}, Violation: {type(violation_msg.metadata_)}"
                    
        logger.info("SSOT Cross-Repository Integration Test Completed")
        
    @pytest.mark.asyncio  
    async def test_ssot_database_transaction_integration(self):
        """
        CRITICAL INTEGRATION TEST: Validate transaction handling consistency.
        
        This test ensures SSOT repositories and test framework handle
        database transactions consistently in integration scenarios.
        """
        logger.info("=== SSOT Database Transaction Integration Test ===")
        
        async with self.db_helper.get_async_session() as session:
            try:
                # Start transaction - create thread
                ssot_thread = await self.thread_repository.create_thread(
                    db=session,
                    user_id=self.test_user_id,
                    metadata={"test": "transaction_integration"}
                )
                
                # Within same transaction - create messages via both methods
                ssot_message = await self.message_repository.create_message(
                    db=session,
                    thread_id=ssot_thread.id,
                    role="user",
                    content="Transaction test SSOT"
                )
                
                # This should participate in same transaction (violation check)
                violation_message = await self.db_helper.create_message(
                    thread_id=ssot_thread.id,
                    role="assistant", 
                    content="Transaction test violation"
                )
                
                # Check transaction state BEFORE commit
                transaction_count = await session.execute(
                    select(func.count()).select_from(
                        select(Message).where(Message.thread_id == ssot_thread.id).subquery()
                    )
                )
                uncommitted_count = transaction_count.scalar()
                
                # CRITICAL: Both should be visible in same transaction
                assert uncommitted_count >= 2, \
                    "SSOT VIOLATION: Transaction isolation differs between SSOT and test framework"
                
                # Now rollback to test transaction consistency
                await session.rollback()
                
                # Verify both were rolled back
                final_count_result = await session.execute(
                    select(func.count()).select_from(
                        select(Message).where(Message.thread_id == ssot_thread.id).subquery()
                    )
                )
                final_count = final_count_result.scalar()
                
                # CRITICAL: Both should be rolled back consistently  
                assert final_count == 0, \
                    "SSOT VIOLATION: Transaction rollback handling differs between SSOT and test framework"
                    
            except Exception as e:
                await session.rollback()
                raise e
                
        logger.info("SSOT Database Transaction Integration Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_database_performance_consistency(self):
        """
        INTEGRATION TEST: Validate performance characteristics consistency.
        
        This test ensures SSOT repository patterns and test framework
        violation patterns have consistent performance characteristics.
        """
        logger.info("=== SSOT Database Performance Integration Test ===")
        
        async with self.db_helper.get_async_session() as session:
            # Create test thread
            test_thread = await self.thread_repository.create_thread(
                db=session,
                user_id=self.test_user_id,
                metadata={"test": "performance_integration"}
            )
            await session.commit()
            
            # Measure SSOT repository performance
            ssot_start_time = time.time()
            ssot_messages = []
            
            for i in range(10):
                message = await self.message_repository.create_message(
                    db=session,
                    thread_id=test_thread.id,
                    role="user",
                    content=f"SSOT performance test {i}",
                    metadata={"batch": "ssot", "index": i}
                )
                ssot_messages.append(message)
                
            await session.commit()
            ssot_duration = time.time() - ssot_start_time
            
            # Measure test framework violation performance  
            violation_start_time = time.time()
            violation_messages = []
            
            for i in range(10):
                message = await self.db_helper.create_message(
                    thread_id=test_thread.id,
                    role="user",
                    content=f"Violation performance test {i}",
                    metadata={"batch": "violation", "index": i}
                )
                violation_messages.append(message)
                
            violation_duration = time.time() - violation_start_time
            
            # Performance should be comparable (within reasonable bounds)
            performance_ratio = max(ssot_duration, violation_duration) / min(ssot_duration, violation_duration)
            
            # CRITICAL: Performance characteristics should be similar
            assert performance_ratio < 3.0, \
                f"SSOT VIOLATION: Significant performance difference - SSOT: {ssot_duration:.3f}s, Violation: {violation_duration:.3f}s"
            
            logger.info(f"Performance Comparison - SSOT: {ssot_duration:.3f}s, Violation: {violation_duration:.3f}s")
            
        logger.info("SSOT Database Performance Integration Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_database_error_handling_integration(self):
        """
        INTEGRATION TEST: Validate error handling consistency.
        
        This test ensures both SSOT repository and test framework violation
        handle database errors consistently in integration scenarios.
        """
        logger.info("=== SSOT Database Error Handling Integration Test ===")
        
        async with self.db_helper.get_async_session() as session:
            # Test constraint violation handling
            
            # 1. Try to create message with invalid thread_id (should fail)
            invalid_thread_id = "invalid_thread_999"
            
            # Test SSOT repository error handling
            ssot_error = None
            try:
                await self.message_repository.create_message(
                    db=session,
                    thread_id=invalid_thread_id,
                    role="user",
                    content="SSOT error test"
                )
                await session.commit()
            except Exception as e:
                ssot_error = e
                await session.rollback()
                
            # Test framework violation error handling
            violation_error = None
            try:
                await self.db_helper.create_message(
                    thread_id=invalid_thread_id,
                    role="user",
                    content="Violation error test"
                )
            except Exception as e:
                violation_error = e
                
            # CRITICAL: Error handling should be consistent
            assert ssot_error is not None, "SSOT repository should raise error for invalid thread"
            assert violation_error is not None, "Test framework should raise error for invalid thread"
            
            # Error types should be related (both database constraint errors)
            assert type(ssot_error).__name__ == type(violation_error).__name__, \
                f"SSOT VIOLATION: Error types differ - SSOT: {type(ssot_error)}, Violation: {type(violation_error)}"
                
        logger.info("SSOT Database Error Handling Integration Test Completed")


@pytest.mark.integration
class TestSSotDatabaseConcurrencyIntegration:
    """
    Integration Tests for SSOT Database Concurrency Patterns
    
    These tests validate SSOT patterns work correctly under concurrent
    access scenarios and expose any concurrency handling violations.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.db_helper = DatabaseTestUtility(service="netra_backend")
        self.message_repository = MessageRepository()
        self.thread_repository = ThreadRepository()
        
    @pytest.mark.asyncio
    async def test_ssot_concurrent_message_creation(self):
        """
        CONCURRENCY INTEGRATION TEST: Validate concurrent message creation.
        
        This test ensures SSOT repository and test framework violation
        handle concurrent operations consistently.
        """
        logger.info("=== SSOT Concurrent Message Creation Test ===")
        
        test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        try:
            async with self.db_helper.get_async_session() as session:
                # Create test thread
                test_thread = await self.thread_repository.create_thread(
                    db=session,
                    user_id=test_user_id,
                    metadata={"test": "concurrency"}
                )
                await session.commit()
                
                # Define concurrent operations
                async def create_ssot_messages():
                    """Create messages via SSOT repository."""
                    messages = []
                    async with self.db_helper.get_async_session() as session:
                        for i in range(5):
                            message = await self.message_repository.create_message(
                                db=session,
                                thread_id=test_thread.id,
                                role="user",
                                content=f"SSOT concurrent {i}",
                                metadata={"source": "ssot", "batch": i}
                            )
                            messages.append(message)
                        await session.commit()
                    return messages
                    
                async def create_violation_messages():
                    """Create messages via test framework violation."""
                    messages = []
                    for i in range(5):
                        message = await self.db_helper.create_message(
                            thread_id=test_thread.id,
                            role="assistant",
                            content=f"Violation concurrent {i}",
                            metadata={"source": "violation", "batch": i}
                        )
                        messages.append(message)
                    return messages
                
                # Run concurrent operations
                ssot_task = asyncio.create_task(create_ssot_messages())
                violation_task = asyncio.create_task(create_violation_messages())
                
                ssot_results, violation_results = await asyncio.gather(
                    ssot_task, violation_task, return_exceptions=True
                )
                
                # Validate both completed successfully
                assert not isinstance(ssot_results, Exception), f"SSOT concurrent creation failed: {ssot_results}"
                assert not isinstance(violation_results, Exception), f"Violation concurrent creation failed: {violation_results}"
                
                # Verify final database state
                async with self.db_helper.get_async_session() as session:
                    final_count_result = await session.execute(
                        select(func.count()).select_from(
                            select(Message).where(Message.thread_id == test_thread.id).subquery()
                        )
                    )
                    final_count = final_count_result.scalar()
                    
                    # Should have 10 messages total (5 SSOT + 5 violation)
                    assert final_count == 10, f"Expected 10 messages, got {final_count}"
                    
        finally:
            # Cleanup
            async with self.db_helper.get_async_session() as session:
                await session.execute(
                    text("DELETE FROM message WHERE thread_id = :thread_id"),
                    {"thread_id": test_thread_id}
                )
                await session.execute(
                    text("DELETE FROM thread WHERE id = :thread_id"),
                    {"thread_id": test_thread_id}
                )
                await session.commit()
                
        logger.info("SSOT Concurrent Message Creation Test Completed")


if __name__ == "__main__":
    # Run the integration test suite
    import sys
    import os
    
    # Add project root to path for imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, project_root)
    
    # Configure logging for test execution
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run tests with real services
    pytest.main([__file__, "-v", "-s", "--tb=short"])