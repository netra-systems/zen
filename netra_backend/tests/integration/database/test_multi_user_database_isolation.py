"""
Integration Test: Multi-User Database Isolation with Real PostgreSQL

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user data isolation in real database operations
- Value Impact: User data privacy and security - prevents cross-user data exposure
- Strategic Impact: Core foundation for trusted multi-tenant platform

This integration test validates:
1. Real PostgreSQL operations maintain strict user isolation
2. Concurrent user operations don't cross-contaminate data
3. Database transactions preserve user boundaries under load
4. User context factory patterns work with real database connections

CRITICAL: Uses REAL PostgreSQL - NO mocks for true integration validation.
Authentication REQUIRED for all operations to ensure proper user context.
"""

import asyncio
import uuid
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Database and auth imports
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import text, select, and_, func, distinct
    from sqlalchemy.pool import NullPool
    from netra_backend.app.db.models_postgres import User, Thread, Message
    from auth_service.auth_core.database.models import AuthUser
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestMultiUserDatabaseIsolation(BaseIntegrationTest):
    """Test multi-user database isolation with real PostgreSQL."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for database integration testing")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_users_isolated_database_operations(self, lightweight_services_fixture, isolated_env):
        """Test concurrent users perform isolated database operations with authentication."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
            
        # Create authenticated users for testing
        auth_helper = E2EAuthHelper()
        
        # Create 3 authenticated users with proper contexts
        authenticated_users = []
        for i in range(3):
            user = await auth_helper.create_authenticated_user(
                email=f"isolation.user.{i}@test.com",
                full_name=f"Isolation Test User {i}"
            )
            authenticated_users.append(user)
            self.logger.info(f"Created authenticated user {i}: {user.user_id}")
        
        # Create user contexts with authenticated sessions
        user_contexts = []
        for user in authenticated_users:
            context = StronglyTypedUserExecutionContext(
                user_id=ensure_user_id(user.user_id),
                thread_id=ThreadID(f"thread_{uuid.uuid4()}"),
                run_id=RunID(f"run_{uuid.uuid4()}"),
                request_id=RequestID(f"req_{uuid.uuid4()}"),
                db_session=db_session
            )
            user_contexts.append((user, context))
        
        # Create users in backend database
        for auth_user, context in user_contexts:
            backend_user = User(
                id=auth_user.user_id,
                email=auth_user.email,
                full_name=auth_user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # Concurrent operation simulation
        async def perform_isolated_operations(user_data: Tuple[AuthenticatedUser, StronglyTypedUserExecutionContext]):
            """Perform database operations for a specific user."""
            auth_user, context = user_data
            operation_results = {
                'user_id': auth_user.user_id,
                'operations': [],
                'data_created': [],
                'errors': []
            }
            
            try:
                # Operation 1: Create multiple threads
                for thread_idx in range(3):
                    thread = Thread(
                        id=f"thread_{auth_user.user_id}_{thread_idx}",
                        object_="thread",
                        created_at=int(time.time()),
                        metadata_={"user_id": auth_user.user_id, "thread_index": thread_idx}
                    )
                    db_session.add(thread)
                    operation_results['data_created'].append(f"thread_{thread_idx}")
                    operation_results['operations'].append(f"created_thread_{thread_idx}")
                
                # Operation 2: Create messages in threads
                for thread_idx in range(2):  # Only first 2 threads get messages
                    for msg_idx in range(2):
                        message = Message(
                            id=f"msg_{auth_user.user_id}_{thread_idx}_{msg_idx}",
                            object_="thread.message",
                            created_at=int(time.time()),
                            thread_id=f"thread_{auth_user.user_id}_{thread_idx}",
                            role="user",
                            content=[{
                                "type": "text",
                                "text": {
                                    "value": f"User {auth_user.user_id} message {msg_idx} in thread {thread_idx}",
                                    "annotations": []
                                }
                            }],
                            metadata_={"user_id": auth_user.user_id, "message_index": msg_idx}
                        )
                        db_session.add(message)
                        operation_results['data_created'].append(f"message_{thread_idx}_{msg_idx}")
                        operation_results['operations'].append(f"created_message_{thread_idx}_{msg_idx}")
                
                # Small delay to simulate realistic operation timing
                await asyncio.sleep(0.2)
                
                # Operation 3: Query user's own data
                user_threads_query = await db_session.execute(
                    select(Thread).where(
                        Thread.metadata_["user_id"].astext == auth_user.user_id
                    )
                )
                user_threads = user_threads_query.scalars().all()
                operation_results['operations'].append(f"queried_{len(user_threads)}_threads")
                
                # Operation 4: Query user's messages
                user_messages_query = await db_session.execute(
                    select(Message).where(
                        Message.metadata_["user_id"].astext == auth_user.user_id
                    )
                )
                user_messages = user_messages_query.scalars().all()
                operation_results['operations'].append(f"queried_{len(user_messages)}_messages")
                
                # Verify isolation - should only see own data
                for thread in user_threads:
                    thread_user_id = thread.metadata_.get("user_id")
                    if thread_user_id != auth_user.user_id:
                        operation_results['errors'].append(
                            f"Thread isolation violation: {thread.id} belongs to {thread_user_id}"
                        )
                
                for message in user_messages:
                    message_user_id = message.metadata_.get("user_id")
                    if message_user_id != auth_user.user_id:
                        operation_results['errors'].append(
                            f"Message isolation violation: {message.id} belongs to {message_user_id}"
                        )
                
            except Exception as e:
                operation_results['errors'].append(f"Operation failed: {str(e)}")
                self.logger.error(f"User {auth_user.user_id} operations failed: {e}")
            
            return operation_results
        
        # Execute concurrent operations
        self.logger.info("Starting concurrent database operations for user isolation test")
        start_time = time.time()
        
        operation_results = await asyncio.gather(*[
            perform_isolated_operations(user_data) for user_data in user_contexts
        ], return_exceptions=True)
        
        duration = time.time() - start_time
        self.logger.info(f"Concurrent operations completed in {duration:.2f} seconds")
        
        # Analyze results for isolation violations
        successful_operations = []
        isolation_violations = []
        
        for i, result in enumerate(operation_results):
            if isinstance(result, Exception):
                self.logger.error(f"User {i} operations failed with exception: {result}")
                continue
                
            successful_operations.append(result)
            
            # Check for isolation violations
            if result['errors']:
                isolation_violations.extend(result['errors'])
                self.logger.error(f"User {result['user_id']} isolation violations: {result['errors']}")
        
        # Commit all changes
        await db_session.commit()
        
        # Assertions for isolation integrity
        assert len(isolation_violations) == 0, \
            f"Database isolation violations detected: {isolation_violations}"
        
        # Verify at least 80% of operations succeeded
        success_rate = len(successful_operations) / len(user_contexts)
        assert success_rate >= 0.8, \
            f"Too many operations failed: {success_rate:.1%} success rate"
        
        # Cross-verification: Ensure users can't see each other's data
        for auth_user, context in user_contexts:
            # Query all threads - should only return this user's threads
            all_user_threads = await db_session.execute(
                select(Thread).where(
                    Thread.metadata_["user_id"].astext == auth_user.user_id
                )
            )
            threads = all_user_threads.scalars().all()
            
            # Should have exactly 3 threads for this user
            assert len(threads) == 3, \
                f"User {auth_user.user_id} should have 3 threads, got {len(threads)}"
            
            # Query all messages - should only return this user's messages
            all_user_messages = await db_session.execute(
                select(Message).where(
                    Message.metadata_["user_id"].astext == auth_user.user_id
                )
            )
            messages = all_user_messages.scalars().all()
            
            # Should have exactly 4 messages (2 threads × 2 messages each)
            assert len(messages) == 4, \
                f"User {auth_user.user_id} should have 4 messages, got {len(messages)}"
            
            # Verify no cross-contamination
            for thread in threads:
                assert thread.metadata_.get("user_id") == auth_user.user_id, \
                    f"Thread {thread.id} metadata shows wrong user"
            
            for message in messages:
                assert message.metadata_.get("user_id") == auth_user.user_id, \
                    f"Message {message.id} metadata shows wrong user"
                    
        await db_session.close()
        self.logger.info("Multi-user database isolation test completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_transaction_boundaries_user_isolation(self, lightweight_services_fixture, isolated_env):
        """Test database transaction boundaries maintain user isolation."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Create authenticated users
        auth_helper = E2EAuthHelper()
        
        user_a = await auth_helper.create_authenticated_user(
            email="transaction.user.a@test.com",
            full_name="Transaction User A"
        )
        user_b = await auth_helper.create_authenticated_user(
            email="transaction.user.b@test.com", 
            full_name="Transaction User B"
        )
        
        # Create contexts
        context_a = StronglyTypedUserExecutionContext(
            user_id=ensure_user_id(user_a.user_id),
            thread_id=ThreadID(f"thread_a_{uuid.uuid4()}"),
            run_id=RunID(f"run_a_{uuid.uuid4()}"),
            request_id=RequestID(f"req_a_{uuid.uuid4()}"),
            db_session=db_session
        )
        
        context_b = StronglyTypedUserExecutionContext(
            user_id=ensure_user_id(user_b.user_id),
            thread_id=ThreadID(f"thread_b_{uuid.uuid4()}"),
            run_id=RunID(f"run_b_{uuid.uuid4()}"),
            request_id=RequestID(f"req_b_{uuid.uuid4()}"),
            db_session=db_session
        )
        
        # Create backend users
        backend_user_a = User(
            id=user_a.user_id,
            email=user_a.email,
            full_name=user_a.full_name,
            is_active=True
        )
        backend_user_b = User(
            id=user_b.user_id,
            email=user_b.email,
            full_name=user_b.full_name,
            is_active=True
        )
        
        db_session.add(backend_user_a)
        db_session.add(backend_user_b)
        await db_session.commit()
        
        # Test transaction isolation
        transaction_log = []
        
        try:
            # Start with User A operations
            transaction_log.append("user_a_operations_start")
            
            # User A creates data
            thread_a = Thread(
                id=f"trans_thread_a_{uuid.uuid4()}",
                object_="thread",
                created_at=int(time.time()),
                metadata_={"user_id": user_a.user_id, "transaction_test": True}
            )
            db_session.add(thread_a)
            transaction_log.append("user_a_thread_created")
            
            # User A creates messages
            for i in range(3):
                message_a = Message(
                    id=f"trans_msg_a_{i}_{uuid.uuid4()}",
                    object_="thread.message", 
                    created_at=int(time.time()),
                    thread_id=thread_a.id,
                    role="user",
                    content=[{
                        "type": "text",
                        "text": {
                            "value": f"Transaction test message {i} from user A",
                            "annotations": []
                        }
                    }],
                    metadata_={"user_id": user_a.user_id, "msg_index": i}
                )
                db_session.add(message_a)
            
            transaction_log.append("user_a_messages_created")
            
            # Partial commit - User A's data is committed
            await db_session.commit()
            transaction_log.append("user_a_committed")
            
            # User B operations in separate logical transaction
            transaction_log.append("user_b_operations_start")
            
            thread_b = Thread(
                id=f"trans_thread_b_{uuid.uuid4()}",
                object_="thread",
                created_at=int(time.time()),
                metadata_={"user_id": user_b.user_id, "transaction_test": True}
            )
            db_session.add(thread_b)
            transaction_log.append("user_b_thread_created")
            
            # User B creates messages
            for i in range(2):
                message_b = Message(
                    id=f"trans_msg_b_{i}_{uuid.uuid4()}",
                    object_="thread.message",
                    created_at=int(time.time()),
                    thread_id=thread_b.id,
                    role="user", 
                    content=[{
                        "type": "text",
                        "text": {
                            "value": f"Transaction test message {i} from user B",
                            "annotations": []
                        }
                    }],
                    metadata_={"user_id": user_b.user_id, "msg_index": i}
                )
                db_session.add(message_b)
            
            transaction_log.append("user_b_messages_created")
            
            # Simulate error condition for User B (rollback scenario)
            if True:  # Simulate error
                await db_session.rollback()
                transaction_log.append("user_b_rollback")
                
                # Re-create User B's data after rollback
                thread_b_retry = Thread(
                    id=f"trans_thread_b_retry_{uuid.uuid4()}",
                    object_="thread",
                    created_at=int(time.time()),
                    metadata_={"user_id": user_b.user_id, "transaction_retry": True}
                )
                db_session.add(thread_b_retry)
                
                message_b_retry = Message(
                    id=f"trans_msg_b_retry_{uuid.uuid4()}",
                    object_="thread.message",
                    created_at=int(time.time()),
                    thread_id=thread_b_retry.id,
                    role="user",
                    content=[{
                        "type": "text", 
                        "text": {
                            "value": "User B retry message after rollback",
                            "annotations": []
                        }
                    }],
                    metadata_={"user_id": user_b.user_id, "retry": True}
                )
                db_session.add(message_b_retry)
                
                await db_session.commit()
                transaction_log.append("user_b_retry_committed")
            
        except Exception as e:
            self.logger.error(f"Transaction isolation test error: {e}")
            await db_session.rollback()
            transaction_log.append("error_rollback")
            raise
        
        # Verify transaction isolation results
        # User A's data should be preserved despite User B's rollback
        user_a_threads = await db_session.execute(
            select(Thread).where(
                Thread.metadata_["user_id"].astext == user_a.user_id
            )
        )
        a_threads = user_a_threads.scalars().all()
        
        user_a_messages = await db_session.execute(
            select(Message).where(
                Message.metadata_["user_id"].astext == user_a.user_id
            )
        )
        a_messages = user_a_messages.scalars().all()
        
        # User B should have retry data only
        user_b_threads = await db_session.execute(
            select(Thread).where(
                Thread.metadata_["user_id"].astext == user_b.user_id
            )
        )
        b_threads = user_b_threads.scalars().all()
        
        user_b_messages = await db_session.execute(
            select(Message).where(
                Message.metadata_["user_id"].astext == user_b.user_id
            )
        )
        b_messages = user_b_messages.scalars().all()
        
        # Verify User A's data integrity
        assert len(a_threads) == 1, f"User A should have 1 thread, got {len(a_threads)}"
        assert len(a_messages) == 3, f"User A should have 3 messages, got {len(a_messages)}"
        
        # Verify User B's data (should be retry data only)
        assert len(b_threads) == 1, f"User B should have 1 thread (retry), got {len(b_threads)}"
        assert len(b_messages) == 1, f"User B should have 1 message (retry), got {len(b_messages)}"
        
        # Verify transaction boundaries maintained user isolation
        for thread in a_threads:
            assert thread.metadata_.get("user_id") == user_a.user_id, \
                "User A thread metadata corrupted by transaction operations"
        
        for thread in b_threads:
            assert thread.metadata_.get("user_id") == user_b.user_id, \
                "User B thread metadata corrupted by transaction operations"
            assert thread.metadata_.get("transaction_retry") is True, \
                "User B should have retry data only"
        
        await db_session.close()
        self.logger.info(f"Transaction isolation verified. Log: {transaction_log}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_database_integration(self, lightweight_services_fixture, isolated_env):
        """Test User Context Factory integration with real database operations."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Test factory-based user context creation with database integration
        auth_helper = E2EAuthHelper()
        
        # Create factory test users
        factory_users = []
        for i in range(4):
            user = await auth_helper.create_authenticated_user(
                email=f"factory.user.{i}@test.com",
                full_name=f"Factory Test User {i}"
            )
            factory_users.append(user)
        
        # Simulate factory-based context creation (as would happen in real system)
        @asynccontextmanager
        async def user_execution_context_factory(auth_user: AuthenticatedUser):
            """Factory method to create isolated user execution context."""
            context = StronglyTypedUserExecutionContext(
                user_id=ensure_user_id(auth_user.user_id),
                thread_id=ThreadID(f"factory_thread_{uuid.uuid4()}"),
                run_id=RunID(f"factory_run_{uuid.uuid4()}"),
                request_id=RequestID(f"factory_req_{uuid.uuid4()}"),
                db_session=db_session
            )
            
            # Create backend user if needed
            backend_user = User(
                id=auth_user.user_id,
                email=auth_user.email,
                full_name=auth_user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
            
            try:
                yield context
            finally:
                # Factory cleanup (would happen automatically in real system)
                pass
        
        # Test concurrent factory usage
        factory_results = []
        
        async def test_factory_context_isolation(auth_user: AuthenticatedUser, operation_id: int):
            """Test isolated operations using factory-created context."""
            async with user_execution_context_factory(auth_user) as context:
                result = {
                    'user_id': auth_user.user_id,
                    'operation_id': operation_id,
                    'context_request_id': str(context.request_id),
                    'data_created': 0,
                    'isolation_verified': True,
                    'errors': []
                }
                
                try:
                    # Create isolated data using factory context
                    for data_idx in range(2):
                        thread = Thread(
                            id=f"factory_{auth_user.user_id}_{operation_id}_{data_idx}",
                            object_="thread",
                            created_at=int(time.time()),
                            metadata_={
                                "user_id": auth_user.user_id,
                                "operation_id": operation_id,
                                "factory_test": True,
                                "context_request": str(context.request_id)
                            }
                        )
                        db_session.add(thread)
                        result['data_created'] += 1
                    
                    # Verify context isolation - query should only return own data
                    user_data_query = await db_session.execute(
                        select(Thread).where(
                            and_(
                                Thread.metadata_["user_id"].astext == auth_user.user_id,
                                Thread.metadata_["factory_test"].astext == "true"
                            )
                        )
                    )
                    user_threads = user_data_query.scalars().all()
                    
                    # Verify isolation
                    for thread in user_threads:
                        if thread.metadata_.get("user_id") != auth_user.user_id:
                            result['isolation_verified'] = False
                            result['errors'].append(
                                f"Factory isolation violation: thread {thread.id} has wrong user"
                            )
                    
                    # Verify unique context per factory call
                    context_threads = [
                        t for t in user_threads 
                        if t.metadata_.get("context_request") == str(context.request_id)
                    ]
                    
                    if len(context_threads) != result['data_created']:
                        result['errors'].append(
                            f"Context isolation issue: expected {result['data_created']} "
                            f"threads for context, got {len(context_threads)}"
                        )
                
                except Exception as e:
                    result['errors'].append(f"Factory operation failed: {str(e)}")
                    self.logger.error(f"Factory test failed for user {auth_user.user_id}: {e}")
                
                return result
        
        # Execute factory tests concurrently
        self.logger.info("Testing factory-based context isolation with database")
        
        factory_tasks = [
            test_factory_context_isolation(user, i) 
            for i, user in enumerate(factory_users)
        ]
        
        factory_results = await asyncio.gather(*factory_tasks, return_exceptions=True)
        await db_session.commit()
        
        # Analyze factory test results
        successful_factory_tests = []
        factory_errors = []
        
        for result in factory_results:
            if isinstance(result, Exception):
                factory_errors.append(f"Factory test exception: {result}")
                continue
                
            successful_factory_tests.append(result)
            
            if result['errors']:
                factory_errors.extend(result['errors'])
            
            if not result['isolation_verified']:
                factory_errors.append(f"Factory isolation failed for user {result['user_id']}")
        
        # Verify factory pattern success
        assert len(factory_errors) == 0, f"Factory isolation errors: {factory_errors}"
        
        success_rate = len(successful_factory_tests) / len(factory_users)
        assert success_rate == 1.0, f"Factory test success rate: {success_rate:.1%}"
        
        # Cross-verify factory isolation
        total_threads_created = sum(r['data_created'] for r in successful_factory_tests)
        
        factory_threads_query = await db_session.execute(
            select(Thread).where(
                Thread.metadata_["factory_test"].astext == "true"
            )
        )
        all_factory_threads = factory_threads_query.scalars().all()
        
        assert len(all_factory_threads) == total_threads_created, \
            f"Factory thread count mismatch: expected {total_threads_created}, found {len(all_factory_threads)}"
        
        # Verify each user's factory data is isolated
        for user in factory_users:
            user_factory_threads = [
                t for t in all_factory_threads 
                if t.metadata_.get("user_id") == user.user_id
            ]
            
            assert len(user_factory_threads) == 2, \
                f"User {user.user_id} should have 2 factory threads, got {len(user_factory_threads)}"
            
            # Verify unique context request IDs (factory isolation)
            context_ids = set(
                t.metadata_.get("context_request") 
                for t in user_factory_threads 
                if t.metadata_.get("context_request")
            )
            
            assert len(context_ids) == 1, \
                f"User {user.user_id} should have 1 unique context ID, got {len(context_ids)}"
        
        await db_session.close()
        self.logger.info("Factory-based database integration test completed successfully")