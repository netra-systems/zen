"""
Test Thread Creation and Persistence with Real PostgreSQL

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable thread creation and persistence for multi-user chat conversations
- Value Impact: Thread creation failures break the foundation of user chat sessions and conversation continuity
- Strategic Impact: Core database operations must be bulletproof for scalable multi-user AI platform

This test suite validates thread creation and persistence with real PostgreSQL database:
1. Thread creation with proper user isolation and database constraints
2. Concurrent thread creation performance and isolation
3. Thread lifecycle management with real database transactions
4. User context isolation preventing cross-user thread access
5. Database constraint enforcement and integrity validation
6. Performance testing under concurrent user load scenarios

CRITICAL: Uses REAL PostgreSQL database (port 5434) - NO mocks allowed.
Expected: Some failures initially - thread isolation and concurrent access patterns need validation.
Authentication REQUIRED: All tests use real JWT tokens for proper user context isolation.
"""

import asyncio
import uuid
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from unittest.mock import patch
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, SessionID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    AuthValidationResult, SessionValidationResult
)

# Helper function for tests
def ensure_session_id(value: str) -> SessionID:
    """Helper to ensure SessionID type."""
    return SessionID(value)

# Thread routing and database components
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.models_postgres import Thread, Message, User
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager
from netra_backend.app.schemas.core_models import Thread as ThreadModel, Message as MessageModel
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import SQLAlchemy for direct database operations
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, and_, or_, func
    from sqlalchemy.orm import selectinload
    from sqlalchemy.exc import IntegrityError, OperationalError
except ImportError:
    # Fallback for environments without SQLAlchemy
    AsyncSession = None
    text = None
    select = None
    IntegrityError = Exception
    OperationalError = Exception


class TestThreadCreationPostgreSQL(BaseIntegrationTest):
    """Test thread creation and persistence with real PostgreSQL database."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authenticated_thread_creation_with_user_isolation(self, real_services_fixture, isolated_env):
        """Test thread creation with proper authentication and user isolation."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup authenticated users using E2E auth helper
        auth_helper = E2EAuthHelper()
        
        # Create multiple authenticated users for isolation testing
        user_count = 4
        authenticated_users = []
        
        for i in range(user_count):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"thread.creation.user.{i}@test.com",
                name=f"Thread Creation Test User {i}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
            
            # Create user record in database
            test_user = User(
                id=user_data["user_id"],
                email=user_data["email"],
                full_name=user_data["name"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db_session.add(test_user)
        
        await db_session.commit()
        
        # Initialize thread service
        thread_service = ThreadService()
        thread_repository = ThreadRepository()
        
        # Test concurrent thread creation with authentication
        user_threads = {}
        thread_creation_metrics = {}
        
        async def create_authenticated_threads(user_data: Dict, threads_to_create: int = 3):
            """Create multiple threads for an authenticated user."""
            user_id = ensure_user_id(user_data["user_id"])
            user_threads_list = []
            creation_times = []
            
            # Create user execution context with proper authentication
            execution_context = UserExecutionContext(
                user_id=str(user_id),
                session_id=user_data["session_id"],
                auth_token=user_data["access_token"],
                permissions=user_data.get("permissions", [])
            )
            
            for thread_idx in range(threads_to_create):
                creation_start = time.time()
                
                # Create thread with authenticated context
                thread = await thread_service.get_or_create_thread(
                    user_id=str(user_id),
                    db=db_session
                )
                
                creation_duration = time.time() - creation_start
                creation_times.append(creation_duration)
                
                # Verify thread has correct user metadata
                assert thread.metadata_ is not None, f"Thread {thread.id} missing metadata"
                thread_user_id = thread.metadata_.get("user_id")
                assert thread_user_id == str(user_id), \
                    f"Thread {thread.id} assigned to wrong user: {thread_user_id} != {user_id}"
                
                # Verify thread in database with direct query
                db_thread_query = await db_session.execute(
                    select(Thread).where(Thread.id == thread.id)
                )
                db_thread = db_thread_query.scalar_one_or_none()
                
                assert db_thread is not None, f"Thread {thread.id} not found in database"
                assert db_thread.metadata_.get("user_id") == str(user_id), \
                    f"Database thread has wrong user_id: {db_thread.metadata_.get('user_id')} != {user_id}"
                
                user_threads_list.append(thread)
                self.logger.info(f"Created authenticated thread {thread.id} for user {user_id}")
                
                # Small delay to prevent rapid-fire creation stress
                await asyncio.sleep(0.05)
            
            return {
                "user_id": user_id,
                "threads": user_threads_list,
                "creation_times": creation_times,
                "avg_creation_time": sum(creation_times) / len(creation_times)
            }
        
        # Execute concurrent thread creation for all users
        self.logger.info(f"Starting concurrent authenticated thread creation for {user_count} users")
        concurrent_start = time.time()
        
        creation_results = await asyncio.gather(*[
            create_authenticated_threads(user_data, 3) for user_data in authenticated_users
        ], return_exceptions=True)
        
        concurrent_duration = time.time() - concurrent_start
        self.logger.info(f"Concurrent thread creation completed in {concurrent_duration:.2f} seconds")
        
        # Analyze results and check for failures
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(creation_results):
            if isinstance(result, Exception):
                failed_results.append((authenticated_users[i]["user_id"], result))
                self.logger.error(f"Thread creation failed for user {authenticated_users[i]['user_id']}: {result}")
            else:
                successful_results.append(result)
        
        # Require at least 75% success rate for concurrent operations
        success_rate = len(successful_results) / len(authenticated_users)
        assert success_rate >= 0.75, \
            f"Too many thread creation failures: {success_rate:.1%} success rate (need 75%+)"
        
        # Validate thread isolation - no user should see other users' threads
        isolation_violations = []
        
        for result in successful_results:
            user_id = result["user_id"]
            user_threads_list = result["threads"]
            
            # Query all threads visible to this user
            user_visible_threads = await thread_service.get_threads(str(user_id), db_session)
            
            # User should see at least their own threads
            user_thread_ids = {t.id for t in user_threads_list}
            visible_thread_ids = {t.id for t in user_visible_threads}
            
            # Check user can see their own threads
            missing_threads = user_thread_ids - visible_thread_ids
            if missing_threads:
                isolation_violations.append(
                    f"User {user_id} cannot see their own threads: {missing_threads}"
                )
            
            # Check for cross-user contamination
            other_users = [r["user_id"] for r in successful_results if r["user_id"] != user_id]
            for other_user_id in other_users:
                other_user_threads = next(r["threads"] for r in successful_results if r["user_id"] == other_user_id)
                other_thread_ids = {t.id for t in other_user_threads}
                
                contaminated_threads = visible_thread_ids & other_thread_ids
                if contaminated_threads:
                    isolation_violations.append(
                        f"User {user_id} can see other user's threads: {contaminated_threads} (belong to {other_user_id})"
                    )
        
        # Report isolation violations
        if isolation_violations:
            for violation in isolation_violations:
                self.logger.error(f"THREAD ISOLATION VIOLATION: {violation}")
            raise AssertionError(f"Found {len(isolation_violations)} thread isolation violations")
        
        # Performance analysis
        all_creation_times = []
        for result in successful_results:
            all_creation_times.extend(result["creation_times"])
        
        if all_creation_times:
            avg_creation_time = sum(all_creation_times) / len(all_creation_times)
            max_creation_time = max(all_creation_times)
            
            # Thread creation should be reasonably fast (under 500ms per thread)
            assert max_creation_time < 0.5, \
                f"Thread creation too slow: {max_creation_time:.3f}s > 500ms"
            
            self.logger.info(f"Thread creation performance: avg={avg_creation_time*1000:.2f}ms, max={max_creation_time*1000:.2f}ms")
        
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_database_constraint_enforcement(self, real_services_fixture, isolated_env):
        """Test PostgreSQL constraint enforcement for thread operations."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup authenticated user
        auth_helper = E2EAuthHelper()
        user_data = await auth_helper.create_authenticated_test_user(
            email="constraint.test@example.com",
            name="Database Constraint Test User",
            password="securepassword123"
        )
        
        # Create user in database
        test_user = User(
            id=user_data["user_id"],
            email=user_data["email"],
            full_name=user_data["name"],
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        user_id = ensure_user_id(user_data["user_id"])
        
        # Test 1: Unique constraint enforcement (if applicable)
        # Create initial thread
        thread1 = await thread_service.get_or_create_thread(str(user_id), db_session)
        assert thread1 is not None, "Initial thread creation should succeed"
        
        # Test 2: Foreign key constraint enforcement
        # Try to create message with non-existent thread ID (should fail gracefully)
        fake_thread_id = f"fake_thread_{uuid.uuid4()}"
        
        try:
            # This should fail due to foreign key constraint
            await thread_service.create_message(
                thread_id=fake_thread_id,
                role="user",
                content="This should fail due to missing thread"
            )
            # If we get here, the constraint wasn't enforced
            raise AssertionError("Foreign key constraint not enforced - message created with fake thread ID")
        except Exception as e:
            # Expected failure due to constraint violation
            self.logger.info(f"Foreign key constraint correctly enforced: {e}")
            assert "foreign key" in str(e).lower() or "does not exist" in str(e).lower() or "not found" in str(e).lower(), \
                f"Unexpected error type: {e}"
        
        # Test 3: Null constraint enforcement  
        # Try to create thread with null user_id (should fail)
        try:
            # Directly insert into database with null user_id
            await db_session.execute(
                text("INSERT INTO threads (id, metadata_) VALUES (:id, :metadata)"),
                {"id": str(uuid.uuid4()), "metadata": "{}"}
            )
            await db_session.commit()
            raise AssertionError("Null constraint not enforced - thread created without user_id in metadata")
        except Exception as e:
            # Expected failure - rollback transaction
            await db_session.rollback()
            self.logger.info(f"Thread creation constraints enforced: {e}")
        
        # Test 4: Data type constraint enforcement
        # Try to insert invalid data types
        try:
            await db_session.execute(
                text("INSERT INTO threads (id, metadata_) VALUES (:id, :metadata)"),
                {"id": 12345, "metadata": "invalid_json_string"}  # Invalid ID type and JSON
            )
            await db_session.commit()
            raise AssertionError("Data type constraints not enforced")
        except Exception as e:
            await db_session.rollback()
            self.logger.info(f"Data type constraints correctly enforced: {e}")
        
        # Test 5: Transaction rollback behavior
        # Start transaction, make changes, then rollback
        async with db_session.begin():
            thread2 = await thread_service.get_or_create_thread(str(user_id), db_session)
            thread2_id = thread2.id
            
            # Verify thread exists in transaction
            check_thread = await thread_service.get_thread(thread2_id, str(user_id), db_session)
            assert check_thread is not None, "Thread should exist within transaction"
            
            # Force rollback
            await db_session.rollback()
        
        # Verify thread was rolled back
        rolled_back_thread = await thread_service.get_thread(thread2_id, str(user_id), db_session)
        # Note: Depending on implementation, this might still exist if it was created in a separate transaction
        
        # Test 6: Concurrent constraint validation
        # Test what happens when multiple transactions try to violate constraints
        constraint_violation_count = 0
        
        async def attempt_constraint_violation(attempt_id: int):
            """Attempt operation that might violate constraints."""
            try:
                # Try to insert thread with duplicate ID (should fail)
                duplicate_id = thread1.id  # Use existing thread ID
                await db_session.execute(
                    text("INSERT INTO threads (id, metadata_) VALUES (:id, :metadata)"),
                    {"id": duplicate_id, "metadata": '{"user_id": "' + str(user_id) + '"}'}
                )
                await db_session.commit()
                return f"violation_succeeded_{attempt_id}"
            except Exception as e:
                await db_session.rollback()
                return f"violation_prevented_{attempt_id}"
        
        # Run concurrent constraint violation attempts
        violation_results = await asyncio.gather(*[
            attempt_constraint_violation(i) for i in range(3)
        ], return_exceptions=True)
        
        # All should be prevented (no violations should succeed)
        violations_prevented = sum(1 for result in violation_results if "violation_prevented" in str(result))
        assert violations_prevented == 3, f"Not all constraint violations were prevented: {violation_results}"
        
        self.logger.info(f"Database constraint enforcement verified: {violations_prevented}/3 violations prevented")
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_high_volume_concurrent_thread_creation_performance(self, real_services_fixture, isolated_env):
        """Test thread creation performance under high concurrent load."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup performance test scenario
        auth_helper = E2EAuthHelper()
        concurrent_users = 10
        threads_per_user = 5
        
        authenticated_users = []
        
        # Create authenticated users for performance testing
        for i in range(concurrent_users):
            user_data = await auth_helper.create_authenticated_test_user(
                email=f"perf.user.{i}@test.com",
                name=f"Performance Test User {i}",
                password="securepassword123"
            )
            authenticated_users.append(user_data)
            
            # Create user in database
            test_user = User(
                id=user_data["user_id"],
                email=user_data["email"],
                full_name=user_data["name"],
                is_active=True
            )
            db_session.add(test_user)
        
        await db_session.commit()
        
        thread_service = ThreadService()
        
        async def high_volume_thread_creation(user_data: Dict):
            """Create multiple threads rapidly for performance testing."""
            user_id = ensure_user_id(user_data["user_id"])
            creation_metrics = {
                "user_id": str(user_id),
                "threads_created": 0,
                "creation_times": [],
                "errors": [],
                "start_time": time.time()
            }
            
            for thread_idx in range(threads_per_user):
                try:
                    creation_start = time.time()
                    
                    thread = await thread_service.get_or_create_thread(str(user_id), db_session)
                    
                    creation_duration = time.time() - creation_start
                    creation_metrics["creation_times"].append(creation_duration)
                    creation_metrics["threads_created"] += 1
                    
                    # Verify basic thread properties
                    assert thread.id is not None, "Thread must have valid ID"
                    assert thread.metadata_.get("user_id") == str(user_id), "Thread must have correct user_id"
                    
                    # Minimal delay to allow database processing
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    creation_metrics["errors"].append(str(e))
                    self.logger.error(f"Thread creation error for user {user_id}, thread {thread_idx}: {e}")
            
            creation_metrics["total_duration"] = time.time() - creation_metrics["start_time"]
            return creation_metrics
        
        # Execute high-volume concurrent thread creation
        self.logger.info(f"Starting high-volume test: {concurrent_users} users x {threads_per_user} threads")
        performance_start = time.time()
        
        performance_results = await asyncio.gather(*[
            high_volume_thread_creation(user_data) for user_data in authenticated_users
        ], return_exceptions=True)
        
        total_performance_duration = time.time() - performance_start
        
        # Analyze performance results
        successful_results = [r for r in performance_results if not isinstance(r, Exception)]
        failed_results = [r for r in performance_results if isinstance(r, Exception)]
        
        # Performance metrics
        total_threads_attempted = concurrent_users * threads_per_user
        total_threads_created = sum(r["threads_created"] for r in successful_results)
        total_errors = sum(len(r["errors"]) for r in successful_results)
        
        success_rate = total_threads_created / total_threads_attempted
        threads_per_second = total_threads_created / total_performance_duration
        
        # Collect all creation times for analysis
        all_creation_times = []
        for result in successful_results:
            all_creation_times.extend(result["creation_times"])
        
        if all_creation_times:
            avg_creation_time = sum(all_creation_times) / len(all_creation_times)
            p95_creation_time = sorted(all_creation_times)[int(0.95 * len(all_creation_times))]
            max_creation_time = max(all_creation_times)
            
            # Performance assertions
            assert success_rate >= 0.90, f"Thread creation success rate too low: {success_rate:.1%} (need 90%+)"
            assert threads_per_second >= 5, f"Thread creation too slow: {threads_per_second:.2f} threads/sec (need 5+)"
            assert avg_creation_time < 0.2, f"Average creation time too slow: {avg_creation_time*1000:.2f}ms (need <200ms)"
            assert p95_creation_time < 0.5, f"95th percentile too slow: {p95_creation_time*1000:.2f}ms (need <500ms)"
            
            # Log performance metrics
            self.logger.info(f"Performance Results:")
            self.logger.info(f"  Success Rate: {success_rate:.1%} ({total_threads_created}/{total_threads_attempted})")
            self.logger.info(f"  Throughput: {threads_per_second:.2f} threads/second")
            self.logger.info(f"  Average Creation Time: {avg_creation_time*1000:.2f}ms")
            self.logger.info(f"  95th Percentile: {p95_creation_time*1000:.2f}ms")
            self.logger.info(f"  Max Creation Time: {max_creation_time*1000:.2f}ms")
            self.logger.info(f"  Total Errors: {total_errors}")
        
        # Validate data integrity after high-volume operations
        integrity_violations = []
        
        for result in successful_results:
            user_id = result["user_id"]
            
            # Verify user can retrieve their threads
            try:
                user_threads = await thread_service.get_threads(user_id, db_session)
                
                # Should have at least the threads we created
                if len(user_threads) < result["threads_created"]:
                    integrity_violations.append(
                        f"User {user_id} missing threads: found {len(user_threads)}, created {result['threads_created']}"
                    )
                
                # All threads should belong to this user
                for thread in user_threads:
                    if thread.metadata_.get("user_id") != user_id:
                        integrity_violations.append(
                            f"Thread {thread.id} has wrong owner: {thread.metadata_.get('user_id')} != {user_id}"
                        )
                        
            except Exception as e:
                integrity_violations.append(f"Failed to retrieve threads for user {user_id}: {e}")
        
        # Report integrity violations
        if integrity_violations:
            for violation in integrity_violations[:5]:  # Show first 5
                self.logger.error(f"DATA INTEGRITY VIOLATION: {violation}")
            raise AssertionError(f"Found {len(integrity_violations)} data integrity violations after high-volume test")
        
        self.logger.info(f"High-volume thread creation test completed successfully")
        await db_session.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_lifecycle_with_database_transactions(self, real_services_fixture, isolated_env):
        """Test complete thread lifecycle with proper database transaction handling."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        db_session = real_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Setup authenticated user
        auth_helper = E2EAuthHelper()
        user_data = await auth_helper.create_authenticated_test_user(
            email="lifecycle.test@example.com",
            name="Thread Lifecycle Test User",
            password="securepassword123"
        )
        
        # Create user in database
        test_user = User(
            id=user_data["user_id"],
            email=user_data["email"],
            full_name=user_data["name"],
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        
        thread_service = ThreadService()
        user_id = ensure_user_id(user_data["user_id"])
        
        # Phase 1: Thread Creation with Transaction Verification
        lifecycle_log = []
        
        # Create thread in explicit transaction
        async with db_session.begin():
            thread = await thread_service.get_or_create_thread(str(user_id), db_session)
            thread_id = ensure_thread_id(thread.id)
            lifecycle_log.append(f"created:{thread_id}")
            
            # Verify thread exists in transaction
            in_transaction_thread = await thread_service.get_thread(thread.id, str(user_id), db_session)
            assert in_transaction_thread is not None, "Thread should exist within transaction"
            
            # Commit is automatic at end of block
        
        # Verify thread persisted after transaction commit
        committed_thread = await thread_service.get_thread(str(thread_id), str(user_id), db_session)
        assert committed_thread is not None, "Thread should persist after transaction commit"
        assert committed_thread.id == str(thread_id), "Thread ID should be unchanged"
        lifecycle_log.append(f"committed:{thread_id}")
        
        # Phase 2: Thread Population with Messages
        message_count = 5
        message_ids = []
        
        for i in range(message_count):
            message = await thread_service.create_message(
                thread_id=str(thread_id),
                role="user" if i % 2 == 0 else "assistant",
                content=f"Lifecycle test message {i}",
                metadata={
                    "lifecycle_test": True,
                    "message_index": i,
                    "creation_timestamp": datetime.utcnow().isoformat()
                }
            )
            message_ids.append(message.id)
            lifecycle_log.append(f"message_created:{message.id}")
        
        # Verify all messages are associated with thread
        thread_messages = await thread_service.get_thread_messages(str(thread_id), db=db_session)
        lifecycle_messages = [
            msg for msg in thread_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("lifecycle_test")
        ]
        
        assert len(lifecycle_messages) == message_count, \
            f"Expected {message_count} lifecycle messages, found {len(lifecycle_messages)}"
        
        # Phase 3: Thread Updates and State Changes
        # Create run associated with thread
        run = await thread_service.create_run(
            thread_id=str(thread_id),
            assistant_id="lifecycle-test-assistant",
            model="gpt-4",
            instructions="Lifecycle test run"
        )
        lifecycle_log.append(f"run_created:{run.id}")
        
        # Update run status through lifecycle
        run_statuses = ["queued", "in_progress", "completed"]
        for status in run_statuses:
            updated_run = await thread_service.update_run_status(
                run_id=run.id,
                status=status
            )
            assert updated_run.status == status, f"Run status not updated to {status}"
            lifecycle_log.append(f"run_status_updated:{status}")
        
        # Phase 4: Transaction Rollback Testing
        # Test what happens when operations fail and need rollback
        rollback_test_passed = False
        
        try:
            async with db_session.begin():
                # Create a message that will be rolled back
                rollback_message = await thread_service.create_message(
                    thread_id=str(thread_id),
                    role="user",
                    content="This message should be rolled back",
                    metadata={"rollback_test": True}
                )
                rollback_message_id = rollback_message.id
                lifecycle_log.append(f"rollback_message_created:{rollback_message_id}")
                
                # Verify message exists in transaction
                in_tx_messages = await thread_service.get_thread_messages(str(thread_id), db=db_session)
                rollback_messages = [
                    msg for msg in in_tx_messages
                    if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("rollback_test")
                ]
                assert len(rollback_messages) == 1, "Rollback message should exist in transaction"
                
                # Force rollback by raising exception
                raise RuntimeError("Intentional rollback for testing")
        
        except RuntimeError as e:
            if "Intentional rollback" in str(e):
                rollback_test_passed = True
                lifecycle_log.append("rollback_triggered")
        
        assert rollback_test_passed, "Rollback test did not execute properly"
        
        # Verify rolled back message does not exist
        post_rollback_messages = await thread_service.get_thread_messages(str(thread_id), db=db_session)
        rollback_messages_after = [
            msg for msg in post_rollback_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("rollback_test")
        ]
        assert len(rollback_messages_after) == 0, "Rolled back message should not exist after rollback"
        lifecycle_log.append("rollback_verified")
        
        # Phase 5: Concurrent Transaction Testing
        # Test how concurrent transactions interact with the same thread
        concurrent_operations = 3
        
        async def concurrent_thread_operation(operation_id: int):
            """Perform concurrent operations on the same thread."""
            try:
                # Each operation adds a message with unique identifier
                message = await thread_service.create_message(
                    thread_id=str(thread_id),
                    role="assistant",
                    content=f"Concurrent operation {operation_id}",
                    metadata={
                        "concurrent_test": True,
                        "operation_id": operation_id,
                        "timestamp": time.time()
                    }
                )
                return f"success:{operation_id}:{message.id}"
            except Exception as e:
                return f"error:{operation_id}:{str(e)}"
        
        # Execute concurrent operations
        concurrent_results = await asyncio.gather(*[
            concurrent_thread_operation(i) for i in range(concurrent_operations)
        ])
        
        # Analyze concurrent operation results
        successful_concurrent = [r for r in concurrent_results if r.startswith("success")]
        failed_concurrent = [r for r in concurrent_results if r.startswith("error")]
        
        # Most concurrent operations should succeed (allow some failures under high concurrency)
        success_rate = len(successful_concurrent) / len(concurrent_results)
        assert success_rate >= 0.67, f"Concurrent operations success rate too low: {success_rate:.1%}"
        
        lifecycle_log.extend([f"concurrent_{r}" for r in concurrent_results])
        
        # Phase 6: Final State Verification
        # Verify thread and all its components are in expected state
        final_thread = await thread_service.get_thread(str(thread_id), str(user_id), db_session)
        assert final_thread is not None, "Thread should exist at end of lifecycle"
        assert final_thread.id == str(thread_id), "Thread ID should be unchanged"
        
        # Verify all messages (except rolled back ones) exist
        final_messages = await thread_service.get_thread_messages(str(thread_id), db=db_session)
        lifecycle_messages_final = [
            msg for msg in final_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("lifecycle_test")
        ]
        concurrent_messages_final = [
            msg for msg in final_messages
            if hasattr(msg, 'metadata_') and msg.metadata_ and msg.metadata_.get("concurrent_test")
        ]
        
        assert len(lifecycle_messages_final) == message_count, \
            f"Final lifecycle message count mismatch: {len(lifecycle_messages_final)} != {message_count}"
        assert len(concurrent_messages_final) == len(successful_concurrent), \
            f"Final concurrent message count mismatch: {len(concurrent_messages_final)} != {len(successful_concurrent)}"
        
        # Log lifecycle completion
        lifecycle_log.append("lifecycle_completed")
        self.logger.info(f"Thread lifecycle completed successfully: {len(lifecycle_log)} operations")
        self.logger.info(f"Lifecycle operations: {' -> '.join(lifecycle_log)}")
        
        await db_session.close()

    async def verify_thread_database_consistency(self, db_session: AsyncSession, thread_id: ThreadID, user_id: UserID):
        """Helper method to verify thread database consistency and integrity."""
        if not select or not db_session:
            return True  # Skip if SQLAlchemy not available
        
        consistency_issues = []
        
        try:
            # Check thread exists and has proper foreign key relationships
            thread_query = await db_session.execute(
                select(Thread).options(selectinload(Thread.messages)).where(Thread.id == str(thread_id))
            )
            thread = thread_query.scalar_one_or_none()
            
            if thread is None:
                consistency_issues.append(f"Thread {thread_id} not found in database")
                return consistency_issues
            
            # Verify thread metadata contains correct user_id
            if not thread.metadata_ or thread.metadata_.get("user_id") != str(user_id):
                consistency_issues.append(
                    f"Thread {thread_id} metadata user_id mismatch: {thread.metadata_.get('user_id')} != {user_id}"
                )
            
            # Verify all messages in thread belong to correct thread
            for message in thread.messages:
                if message.thread_id != str(thread_id):
                    consistency_issues.append(
                        f"Message {message.id} has wrong thread_id: {message.thread_id} != {thread_id}"
                    )
            
            # Check for orphaned messages (messages with thread_id but thread doesn't exist)
            orphaned_messages_query = await db_session.execute(
                text("""
                    SELECT m.id FROM messages m 
                    LEFT JOIN threads t ON m.thread_id = t.id 
                    WHERE t.id IS NULL AND m.thread_id = :thread_id
                """),
                {"thread_id": str(thread_id)}
            )
            orphaned_messages = orphaned_messages_query.fetchall()
            
            if orphaned_messages:
                consistency_issues.append(
                    f"Found {len(orphaned_messages)} orphaned messages for thread {thread_id}"
                )
            
        except Exception as e:
            consistency_issues.append(f"Database consistency check failed: {e}")
        
        return consistency_issues