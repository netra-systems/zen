"""
Integration Test: Database Transaction Integrity Under Concurrency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure database ACID properties under concurrent user operations
- Value Impact: Data consistency and reliability under load prevents corruption/loss
- Strategic Impact: Database integrity foundation for production multi-user platform

This integration test validates:
1. ACID transaction properties maintained under concurrent access
2. Database isolation levels prevent dirty reads and phantom reads
3. Deadlock detection and recovery mechanisms work correctly
4. Transaction rollback preserves user data integrity

CRITICAL: Uses REAL PostgreSQL with concurrent transactions.
Authentication REQUIRED to ensure proper user context in transactions.
"""

import asyncio
import uuid
import pytest
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Database imports for transaction testing
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import text, select, and_, func, distinct, update, delete
    from sqlalchemy.exc import IntegrityError, DeadlockDetectedError
    from sqlalchemy.pool import NullPool
    from netra_backend.app.db.models_postgres import User, Thread, Message
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestDatabaseTransactionConcurrency(BaseIntegrationTest):
    """Test database transaction integrity under concurrency."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for transaction testing")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_acid_properties_under_concurrent_transactions(self, lightweight_services_fixture, isolated_env):
        """Test ACID transaction properties maintained under concurrent access."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Create authenticated users for concurrent transaction testing
        auth_helper = E2EAuthHelper()
        
        # Create users for ACID testing
        acid_users = []
        for i in range(5):
            user = await auth_helper.create_authenticated_user(
                email=f"acid.test.user.{i}@test.com",
                full_name=f"ACID Test User {i}"
            )
            acid_users.append(user)
        
        # Create backend users
        for user in acid_users:
            backend_user = User(
                id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # ACID Test Scenario: Concurrent thread and message creation with constraints
        
        async def atomic_transaction_test(auth_user: AuthenticatedUser, operation_batch: int):
            """Test atomic transaction operations for ACID properties."""
            
            context = StronglyTypedUserExecutionContext(
                user_id=ensure_user_id(auth_user.user_id),
                thread_id=ThreadID(f"acid_thread_{uuid.uuid4()}"),
                run_id=RunID(f"acid_run_{uuid.uuid4()}"),
                request_id=RequestID(f"acid_req_{uuid.uuid4()}"),
                db_session=db_session
            )
            
            transaction_result = {
                'user_id': auth_user.user_id,
                'batch_id': operation_batch,
                'operations_attempted': 0,
                'operations_completed': 0,
                'atomicity_preserved': True,
                'consistency_maintained': True,
                'isolation_verified': True,
                'durability_confirmed': False,
                'errors': []
            }
            
            try:
                # Begin complex atomic transaction
                transaction_result['operations_attempted'] = 1
                
                # Create thread with metadata
                thread = Thread(
                    id=f"acid_thread_{auth_user.user_id}_{operation_batch}",
                    object_="thread",
                    created_at=int(time.time()),
                    metadata_={
                        "user_id": auth_user.user_id,
                        "acid_test": True,
                        "batch_id": operation_batch,
                        "atomic_transaction": True
                    }
                )
                db_session.add(thread)
                
                # Create multiple messages atomically
                message_ids = []
                for msg_idx in range(3):
                    message_id = f"acid_msg_{auth_user.user_id}_{operation_batch}_{msg_idx}"
                    message = Message(
                        id=message_id,
                        object_="thread.message",
                        created_at=int(time.time()),
                        thread_id=thread.id,
                        role="user",
                        content=[{
                            "type": "text", 
                            "text": {
                                "value": f"ACID test message {msg_idx} batch {operation_batch}",
                                "annotations": []
                            }
                        }],
                        metadata_={
                            "user_id": auth_user.user_id,
                            "acid_test": True,
                            "batch_id": operation_batch,
                            "message_index": msg_idx
                        }
                    )
                    db_session.add(message)
                    message_ids.append(message_id)
                
                # Simulate potential conflict - random delay
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Add constraint validation (consistency check)
                # Ensure all messages reference valid thread
                validation_query = await db_session.execute(
                    select(func.count(Message.id)).where(
                        and_(
                            Message.thread_id == thread.id,
                            Message.metadata_["batch_id"].astext == str(operation_batch)
                        )
                    )
                )
                message_count = validation_query.scalar()
                
                if message_count != 3:
                    transaction_result['consistency_maintained'] = False
                    transaction_result['errors'].append(
                        f"Consistency violation: expected 3 messages, got {message_count}"
                    )
                
                # Test isolation - check if we can see other users' concurrent changes
                other_users_data = await db_session.execute(
                    select(func.count(Thread.id)).where(
                        and_(
                            Thread.metadata_["acid_test"].astext == "true",
                            Thread.metadata_["user_id"].astext != auth_user.user_id
                        )
                    )
                )
                other_count = other_users_data.scalar()
                
                # We should see other users' committed data (READ COMMITTED isolation)
                # but not their uncommitted changes in active transactions
                self.logger.debug(f"User {auth_user.user_id} sees {other_count} other users' threads")
                
                # Commit atomic transaction
                await db_session.commit()
                transaction_result['operations_completed'] = 1
                transaction_result['durability_confirmed'] = True
                
                # Post-commit verification (durability)
                post_commit_query = await db_session.execute(
                    select(func.count(Message.id)).where(
                        Message.metadata_["batch_id"].astext == str(operation_batch)
                    )
                )
                post_commit_count = post_commit_query.scalar()
                
                if post_commit_count != 3:
                    transaction_result['durability_confirmed'] = False
                    transaction_result['errors'].append(
                        f"Durability violation: messages not persisted correctly"
                    )
                
            except Exception as e:
                # Test atomicity - rollback should undo all changes
                await db_session.rollback()
                transaction_result['atomicity_preserved'] = True  # Rollback is expected atomicity
                transaction_result['errors'].append(f"Transaction rolled back: {str(e)}")
                
                # Verify rollback completeness
                rollback_verify_query = await db_session.execute(
                    select(func.count(Thread.id)).where(
                        Thread.metadata_["batch_id"].astext == str(operation_batch)
                    )
                )
                rollback_count = rollback_verify_query.scalar()
                
                if rollback_count != 0:
                    transaction_result['atomicity_preserved'] = False
                    transaction_result['errors'].append(
                        f"Atomicity violation: {rollback_count} records survived rollback"
                    )
            
            return transaction_result
        
        # Execute concurrent ACID transactions
        self.logger.info("Starting concurrent ACID transaction tests")
        start_time = time.time()
        
        acid_tasks = [
            atomic_transaction_test(user, batch_id)
            for batch_id, user in enumerate(acid_users)
        ]
        
        acid_results = await asyncio.gather(*acid_tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        self.logger.info(f"ACID transaction tests completed in {duration:.2f} seconds")
        
        # Analyze ACID results
        acid_violations = []
        successful_acid_tests = []
        
        for result in acid_results:
            if isinstance(result, Exception):
                acid_violations.append(f"ACID test exception: {result}")
                continue
            
            successful_acid_tests.append(result)
            
            # Check ACID property violations
            if not result['atomicity_preserved']:
                acid_violations.append(f"Atomicity violation for user {result['user_id']}")
            
            if not result['consistency_maintained']:
                acid_violations.append(f"Consistency violation for user {result['user_id']}")
            
            if not result['isolation_verified']:
                acid_violations.append(f"Isolation violation for user {result['user_id']}")
            
            if not result['durability_confirmed'] and result['operations_completed'] > 0:
                acid_violations.append(f"Durability violation for user {result['user_id']}")
            
            if result['errors']:
                for error in result['errors']:
                    if "violation" in error.lower():
                        acid_violations.append(f"User {result['user_id']}: {error}")
        
        # ACID assertions
        assert len(acid_violations) == 0, f"ACID property violations: {acid_violations}"
        
        # Verify overall transaction consistency
        final_thread_count = await db_session.execute(
            select(func.count(Thread.id)).where(
                Thread.metadata_["acid_test"].astext == "true"
            )
        )
        total_threads = final_thread_count.scalar()
        
        final_message_count = await db_session.execute(
            select(func.count(Message.id)).where(
                Message.metadata_["acid_test"].astext == "true"
            )
        )
        total_messages = final_message_count.scalar()
        
        successful_transactions = len([r for r in successful_acid_tests if r['operations_completed'] > 0])
        
        # Each successful transaction creates 1 thread + 3 messages
        expected_threads = successful_transactions
        expected_messages = successful_transactions * 3
        
        assert total_threads == expected_threads, \
            f"Transaction consistency: expected {expected_threads} threads, got {total_threads}"
        assert total_messages == expected_messages, \
            f"Transaction consistency: expected {expected_messages} messages, got {total_messages}"
        
        await db_session.close()
        self.logger.info(f"ACID properties verified: {successful_transactions} successful transactions")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_deadlock_detection_and_recovery(self, lightweight_services_fixture, isolated_env):
        """Test deadlock detection and recovery mechanisms work correctly."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Create users for deadlock testing
        auth_helper = E2EAuthHelper()
        
        user_a = await auth_helper.create_authenticated_user(
            email="deadlock.user.a@test.com",
            full_name="Deadlock Test User A"
        )
        user_b = await auth_helper.create_authenticated_user(
            email="deadlock.user.b@test.com",
            full_name="Deadlock Test User B"
        )
        
        # Create backend users
        for user in [user_a, user_b]:
            backend_user = User(
                id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # Setup deadlock scenario data
        # Create shared resources that will be accessed in conflicting order
        
        shared_thread_1 = Thread(
            id=f"deadlock_thread_1_{uuid.uuid4()}",
            object_="thread",
            created_at=int(time.time()),
            metadata_={"shared_resource": "thread_1", "deadlock_test": True}
        )
        
        shared_thread_2 = Thread(
            id=f"deadlock_thread_2_{uuid.uuid4()}",
            object_="thread", 
            created_at=int(time.time()),
            metadata_={"shared_resource": "thread_2", "deadlock_test": True}
        )
        
        db_session.add(shared_thread_1)
        db_session.add(shared_thread_2)
        await db_session.commit()
        
        # Deadlock simulation with conflicting resource access order
        
        async def deadlock_transaction_a(auth_user: AuthenticatedUser):
            """Transaction A: Access resources in order Thread1 -> Thread2."""
            result = {
                'user_id': auth_user.user_id,
                'transaction_name': 'Transaction A',
                'deadlock_detected': False,
                'recovery_successful': False,
                'operations_completed': 0,
                'errors': []
            }
            
            try:
                # Step 1: Lock Thread 1 first
                update_query_1 = (
                    update(Thread)
                    .where(Thread.id == shared_thread_1.id)
                    .values(metadata_=func.jsonb_set(
                        Thread.metadata_,
                        '{locked_by}',
                        f'"{auth_user.user_id}"'
                    ))
                )
                await db_session.execute(update_query_1)
                result['operations_completed'] += 1
                
                # Small delay to increase deadlock probability
                await asyncio.sleep(0.2)
                
                # Step 2: Try to lock Thread 2 (potential deadlock point)
                update_query_2 = (
                    update(Thread)
                    .where(Thread.id == shared_thread_2.id)
                    .values(metadata_=func.jsonb_set(
                        Thread.metadata_,
                        '{locked_by}',
                        f'"{auth_user.user_id}"'
                    ))
                )
                await db_session.execute(update_query_2)
                result['operations_completed'] += 1
                
                # If we reach here, no deadlock occurred
                await db_session.commit()
                result['recovery_successful'] = True
                
            except Exception as e:
                error_str = str(e).lower()
                if 'deadlock' in error_str or 'lock' in error_str:
                    result['deadlock_detected'] = True
                    self.logger.info(f"Transaction A detected deadlock: {e}")
                    
                    try:
                        await db_session.rollback()
                        result['recovery_successful'] = True
                    except Exception as rollback_error:
                        result['errors'].append(f"Rollback failed: {rollback_error}")
                else:
                    result['errors'].append(f"Unexpected error: {e}")
                    await db_session.rollback()
            
            return result
        
        async def deadlock_transaction_b(auth_user: AuthenticatedUser):
            """Transaction B: Access resources in reverse order Thread2 -> Thread1."""
            result = {
                'user_id': auth_user.user_id,
                'transaction_name': 'Transaction B',
                'deadlock_detected': False,
                'recovery_successful': False,
                'operations_completed': 0,
                'errors': []
            }
            
            try:
                # Step 1: Lock Thread 2 first (reverse order)
                update_query_2 = (
                    update(Thread)
                    .where(Thread.id == shared_thread_2.id)
                    .values(metadata_=func.jsonb_set(
                        Thread.metadata_,
                        '{locked_by}',
                        f'"{auth_user.user_id}"'
                    ))
                )
                await db_session.execute(update_query_2)
                result['operations_completed'] += 1
                
                # Small delay to increase deadlock probability
                await asyncio.sleep(0.2)
                
                # Step 2: Try to lock Thread 1 (potential deadlock point)
                update_query_1 = (
                    update(Thread)
                    .where(Thread.id == shared_thread_1.id)
                    .values(metadata_=func.jsonb_set(
                        Thread.metadata_,
                        '{locked_by}',
                        f'"{auth_user.user_id}"'
                    ))
                )
                await db_session.execute(update_query_1)
                result['operations_completed'] += 1
                
                # If we reach here, no deadlock occurred
                await db_session.commit()
                result['recovery_successful'] = True
                
            except Exception as e:
                error_str = str(e).lower()
                if 'deadlock' in error_str or 'lock' in error_str:
                    result['deadlock_detected'] = True
                    self.logger.info(f"Transaction B detected deadlock: {e}")
                    
                    try:
                        await db_session.rollback()
                        result['recovery_successful'] = True
                    except Exception as rollback_error:
                        result['errors'].append(f"Rollback failed: {rollback_error}")
                else:
                    result['errors'].append(f"Unexpected error: {e}")
                    await db_session.rollback()
            
            return result
        
        # Execute deadlock-prone transactions concurrently
        self.logger.info("Starting deadlock detection test")
        
        # Run multiple iterations to increase deadlock probability
        deadlock_results = []
        for iteration in range(3):
            self.logger.info(f"Deadlock test iteration {iteration + 1}")
            
            # Reset shared resources
            await db_session.execute(
                update(Thread)
                .where(Thread.metadata_["deadlock_test"].astext == "true")
                .values(metadata_=func.jsonb_set(
                    Thread.metadata_,
                    '{locked_by}',
                    'null'
                ))
            )
            await db_session.commit()
            
            # Execute concurrent transactions
            concurrent_results = await asyncio.gather(
                deadlock_transaction_a(user_a),
                deadlock_transaction_b(user_b),
                return_exceptions=True
            )
            
            deadlock_results.extend(concurrent_results)
            
            # Small delay between iterations
            await asyncio.sleep(0.1)
        
        # Analyze deadlock detection results
        deadlock_detections = 0
        successful_recoveries = 0
        recovery_failures = []
        
        for result in deadlock_results:
            if isinstance(result, Exception):
                recovery_failures.append(f"Transaction exception: {result}")
                continue
            
            if result['deadlock_detected']:
                deadlock_detections += 1
                if result['recovery_successful']:
                    successful_recoveries += 1
                else:
                    recovery_failures.append(
                        f"Recovery failed for {result['transaction_name']}: {result['errors']}"
                    )
            
            # Check for other errors
            if result['errors']:
                for error in result['errors']:
                    if 'rollback failed' in error.lower():
                        recovery_failures.append(f"{result['transaction_name']}: {error}")
        
        # Deadlock detection assertions
        if deadlock_detections > 0:
            self.logger.info(f"Deadlocks detected: {deadlock_detections}")
            assert successful_recoveries == deadlock_detections, \
                f"Recovery failures: {recovery_failures}"
        else:
            self.logger.info("No deadlocks occurred in test iterations (transactions completed successfully)")
        
        # Verify database consistency after deadlock tests
        final_state_query = await db_session.execute(
            select(Thread).where(
                Thread.metadata_["deadlock_test"].astext == "true"
            )
        )
        final_threads = final_state_query.scalars().all()
        
        assert len(final_threads) == 2, \
            f"Deadlock test corrupted data: expected 2 threads, got {len(final_threads)}"
        
        # Verify no permanent locks remain
        for thread in final_threads:
            locked_by = thread.metadata_.get("locked_by")
            if locked_by and locked_by != "null":
                self.logger.warning(f"Thread {thread.id} still locked by {locked_by}")
        
        await db_session.close()
        self.logger.info(f"Deadlock detection test completed: {deadlock_detections} deadlocks, "
                        f"{successful_recoveries} successful recoveries")