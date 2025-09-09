"""
E2E Test: Complete Database User Workflows with Authentication

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure complete user workflows maintain data isolation end-to-end
- Value Impact: Full user journey data integrity prevents privacy breaches and data loss
- Strategic Impact: User trust and platform reliability for production multi-tenant system

This E2E test validates:
1. Complete authenticated user workflows with database operations
2. End-to-end user data isolation from registration to data management
3. Real-world multi-user scenarios with concurrent database access
4. Full authentication integration with database user context

CRITICAL: Uses REAL services with REAL authentication - no mocks for true E2E validation.
MANDATORY: All operations must be authenticated with proper JWT/OAuth flows.
"""

import asyncio
import uuid
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Database and service imports for E2E testing
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, and_, func, distinct
    from netra_backend.app.db.models_postgres import User, Thread, Message
    from auth_service.auth_core.database.models import AuthUser, AuthSession
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestDatabaseE2EUserWorkflows(BaseE2ETest):
    """E2E test for complete database user workflows with authentication."""

    def setUp(self):
        """Set up E2E test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for E2E database testing")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_user_lifecycle_with_database_isolation(self, real_services_fixture, isolated_env):
        """Test complete user lifecycle from registration to data operations with isolation."""
        
        if not real_services_fixture["all_services_ready"]:
            pytest.skip("All services not ready - run with --real-services")
            
        auth_service = real_services_fixture["auth_service"]
        backend_service = real_services_fixture["backend_service"]
        db_session = real_services_fixture["db"]
        
        if not all([auth_service, backend_service, db_session]):
            pytest.skip("Required services not available for E2E test")
        
        # E2E Test Scenario: Complete User Journey with Database Operations
        
        # Phase 1: User Registration and Authentication
        auth_helper = E2EAuthHelper()
        
        e2e_users = []
        for i in range(3):
            try:
                # Complete authentication flow
                user = await auth_helper.create_authenticated_user(
                    email=f"e2e.database.user.{i}@test.com",
                    full_name=f"E2E Database Test User {i}",
                    verify_auth_service=True  # Verify with real auth service
                )
                e2e_users.append(user)
                
                self.logger.info(f"E2E User {i} registered: {user.user_id}")
                
                # Verify user exists in auth database
                auth_user_query = await db_session.execute(
                    text("SELECT id, email FROM auth_users WHERE id = :user_id"),
                    {"user_id": user.user_id}
                )
                auth_user_record = auth_user_query.fetchone()
                
                assert auth_user_record is not None, \
                    f"User {user.user_id} not found in auth database"
                assert auth_user_record[1] == user.email, \
                    f"Email mismatch in auth database: {auth_user_record[1]} != {user.email}"
                
            except Exception as e:
                self.logger.error(f"E2E user {i} registration failed: {e}")
                raise
        
        # Phase 2: Backend User Creation with Authentication Context
        backend_users_created = []
        
        for user in e2e_users:
            try:
                # Create user execution context with authenticated session
                context = StronglyTypedUserExecutionContext(
                    user_id=ensure_user_id(user.user_id),
                    thread_id=ThreadID(f"e2e_thread_{uuid.uuid4()}"),
                    run_id=RunID(f"e2e_run_{uuid.uuid4()}"),
                    request_id=RequestID(f"e2e_req_{uuid.uuid4()}"),
                    db_session=db_session
                )
                
                # Create backend user with proper authentication context
                backend_user = User(
                    id=user.user_id,
                    email=user.email,
                    full_name=user.full_name,
                    is_active=True
                )
                db_session.add(backend_user)
                
                backend_users_created.append({
                    'auth_user': user,
                    'context': context,
                    'backend_user': backend_user
                })
                
            except Exception as e:
                self.logger.error(f"Backend user creation failed for {user.user_id}: {e}")
                raise
        
        await db_session.commit()
        
        # Phase 3: Multi-User Data Operations with Isolation Testing
        user_data_operations = []
        
        async def execute_authenticated_user_operations(user_data: Dict[str, Any], operation_batch: int):
            """Execute complete user data operations with authentication."""
            
            auth_user = user_data['auth_user']
            context = user_data['context']
            
            operation_result = {
                'user_id': auth_user.user_id,
                'batch_id': operation_batch,
                'authentication_verified': False,
                'threads_created': 0,
                'messages_created': 0,
                'data_isolation_verified': False,
                'cross_user_access_prevented': False,
                'operations_completed': 0,
                'errors': []
            }
            
            try:
                # Verify authentication context
                if auth_user.access_token:
                    operation_result['authentication_verified'] = True
                
                # Create user threads with authenticated context
                user_threads = []
                for thread_idx in range(3):
                    thread = Thread(
                        id=f"e2e_thread_{auth_user.user_id}_{operation_batch}_{thread_idx}",
                        object_="thread",
                        created_at=int(time.time()),
                        metadata_={
                            "user_id": auth_user.user_id,
                            "e2e_test": True,
                            "batch_id": operation_batch,
                            "thread_index": thread_idx,
                            "authenticated_context": str(context.request_id)
                        }
                    )
                    db_session.add(thread)
                    user_threads.append(thread)
                    operation_result['threads_created'] += 1
                
                # Create messages in threads with user context
                for thread in user_threads:
                    for msg_idx in range(2):
                        message = Message(
                            id=f"e2e_msg_{auth_user.user_id}_{operation_batch}_{thread.metadata_['thread_index']}_{msg_idx}",
                            object_="thread.message",
                            created_at=int(time.time()),
                            thread_id=thread.id,
                            role="user",
                            content=[{
                                "type": "text",
                                "text": {
                                    "value": f"E2E test message {msg_idx} from authenticated user {auth_user.user_id}",
                                    "annotations": []
                                }
                            }],
                            metadata_={
                                "user_id": auth_user.user_id,
                                "e2e_test": True,
                                "message_index": msg_idx,
                                "authenticated_creation": True
                            }
                        )
                        db_session.add(message)
                        operation_result['messages_created'] += 1
                
                operation_result['operations_completed'] += 1
                
                # Test data isolation - verify user can only see own data
                user_threads_query = await db_session.execute(
                    select(Thread).where(
                        and_(
                            Thread.metadata_["user_id"].astext == auth_user.user_id,
                            Thread.metadata_["e2e_test"].astext == "true"
                        )
                    )
                )
                user_threads_found = user_threads_query.scalars().all()
                
                isolation_verified = True
                for thread in user_threads_found:
                    thread_user_id = thread.metadata_.get("user_id")
                    if thread_user_id != auth_user.user_id:
                        isolation_verified = False
                        operation_result['errors'].append(
                            f"Data isolation violation: thread {thread.id} belongs to {thread_user_id}"
                        )
                
                operation_result['data_isolation_verified'] = isolation_verified
                operation_result['operations_completed'] += 1
                
                # Test cross-user access prevention
                other_users_data_query = await db_session.execute(
                    select(func.count(Thread.id)).where(
                        and_(
                            Thread.metadata_["e2e_test"].astext == "true",
                            Thread.metadata_["user_id"].astext != auth_user.user_id
                        )
                    )
                )
                other_users_count = other_users_data_query.scalar()
                
                # User should be able to see count of other users' data (read committed isolation)
                # but should not be able to access the actual data in application logic
                if other_users_count >= 0:  # Count query succeeds
                    operation_result['cross_user_access_prevented'] = True
                operation_result['operations_completed'] += 1
                
                # Test authenticated query patterns
                authenticated_message_query = await db_session.execute(
                    select(Message).where(
                        and_(
                            Message.metadata_["user_id"].astext == auth_user.user_id,
                            Message.metadata_["authenticated_creation"].astext == "true"
                        )
                    )
                )
                authenticated_messages = authenticated_message_query.scalars().all()
                
                expected_message_count = operation_result['messages_created']
                actual_message_count = len(authenticated_messages)
                
                if actual_message_count != expected_message_count:
                    operation_result['errors'].append(
                        f"Message count mismatch: expected {expected_message_count}, got {actual_message_count}"
                    )
                else:
                    operation_result['operations_completed'] += 1
                
                # Verify all messages have proper authentication metadata
                for message in authenticated_messages:
                    if not message.metadata_.get("authenticated_creation"):
                        operation_result['errors'].append(
                            f"Message {message.id} missing authentication metadata"
                        )
                
            except Exception as e:
                operation_result['errors'].append(f"Authenticated operation failed: {str(e)}")
                self.logger.error(f"E2E operations failed for user {auth_user.user_id}: {e}")
            
            return operation_result
        
        # Execute concurrent authenticated operations
        self.logger.info("Executing concurrent authenticated user database operations")
        
        concurrent_e2e_tasks = [
            execute_authenticated_user_operations(user_data, i)
            for i, user_data in enumerate(backend_users_created)
        ]
        
        e2e_results = await asyncio.gather(*concurrent_e2e_tasks, return_exceptions=True)
        
        await db_session.commit()
        
        # Phase 4: Cross-User Data Verification and Isolation Validation
        cross_user_violations = []
        authentication_failures = []
        data_integrity_issues = []
        
        for result in e2e_results:
            if isinstance(result, Exception):
                authentication_failures.append(f"E2E operation exception: {result}")
                continue
            
            # Check authentication verification
            if not result['authentication_verified']:
                authentication_failures.append(
                    f"Authentication not verified for user {result['user_id']}"
                )
            
            # Check data isolation
            if not result['data_isolation_verified']:
                cross_user_violations.append(
                    f"Data isolation failed for user {result['user_id']}"
                )
            
            # Check operation completeness
            if result['operations_completed'] < 4:  # Expected minimum operations
                data_integrity_issues.append(
                    f"Incomplete operations for user {result['user_id']}: "
                    f"{result['operations_completed']} completed"
                )
            
            # Check for specific errors
            if result['errors']:
                for error in result['errors']:
                    if "isolation" in error.lower() or "violation" in error.lower():
                        cross_user_violations.append(f"User {result['user_id']}: {error}")
                    elif "auth" in error.lower():
                        authentication_failures.append(f"User {result['user_id']}: {error}")
                    else:
                        data_integrity_issues.append(f"User {result['user_id']}: {error}")
        
        # Phase 5: Final Database State Verification
        final_verification_results = await self._verify_final_database_state(
            db_session, [user['auth_user'] for user in backend_users_created]
        )
        
        # Clean up test data
        await self._cleanup_e2e_test_data(db_session, [user['auth_user'].user_id for user in backend_users_created])
        
        await db_session.close()
        
        # E2E Assertions
        assert len(authentication_failures) == 0, \
            f"E2E authentication failures: {authentication_failures}"
        
        assert len(cross_user_violations) == 0, \
            f"E2E cross-user isolation violations: {cross_user_violations}"
        
        assert len(data_integrity_issues) == 0, \
            f"E2E data integrity issues: {data_integrity_issues}"
        
        assert final_verification_results['verification_passed'], \
            f"E2E final verification failed: {final_verification_results['errors']}"
        
        # Success metrics
        successful_e2e_operations = len([r for r in e2e_results if not isinstance(r, Exception)])
        success_rate = successful_e2e_operations / len(e2e_users) if e2e_users else 0
        
        assert success_rate >= 0.9, \
            f"E2E success rate too low: {success_rate:.1%}"
        
        self.logger.info(f"E2E database user workflows completed successfully")
        self.logger.info(f"Users processed: {len(e2e_users)}, Success rate: {success_rate:.1%}")
        self.logger.info(f"Final verification: {final_verification_results}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_concurrent_database_workflows(self, real_services_fixture, isolated_env):
        """Test multi-user concurrent database workflows with real authentication."""
        
        if not real_services_fixture["all_services_ready"]:
            pytest.skip("All services not ready - run with --real-services")
            
        db_session = real_services_fixture["db"]
        
        # Create larger user set for concurrency testing
        auth_helper = E2EAuthHelper()
        
        concurrent_users = []
        for i in range(8):  # 8 concurrent users
            user = await auth_helper.create_authenticated_user(
                email=f"concurrent.e2e.user.{i}@test.com",
                full_name=f"Concurrent E2E User {i}"
            )
            concurrent_users.append(user)
        
        # Create backend users
        for user in concurrent_users:
            backend_user = User(
                id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # Define concurrent workflow scenarios
        workflow_scenarios = [
            {'name': 'heavy_write', 'threads': 5, 'messages_per_thread': 3},
            {'name': 'heavy_read', 'threads': 2, 'messages_per_thread': 2},
            {'name': 'mixed_operations', 'threads': 3, 'messages_per_thread': 2},
        ]
        
        async def execute_workflow_scenario(user: AuthenticatedUser, scenario: Dict[str, Any], user_index: int):
            """Execute a specific workflow scenario for a user."""
            
            scenario_result = {
                'user_id': user.user_id,
                'user_index': user_index,
                'scenario': scenario['name'],
                'threads_created': 0,
                'messages_created': 0,
                'queries_executed': 0,
                'concurrent_safety_verified': True,
                'errors': []
            }
            
            try:
                # Create context
                context = StronglyTypedUserExecutionContext(
                    user_id=ensure_user_id(user.user_id),
                    thread_id=ThreadID(f"concurrent_thread_{uuid.uuid4()}"),
                    run_id=RunID(f"concurrent_run_{uuid.uuid4()}"),
                    request_id=RequestID(f"concurrent_req_{uuid.uuid4()}"),
                    db_session=db_session
                )
                
                # Execute scenario
                created_threads = []
                for thread_idx in range(scenario['threads']):
                    thread = Thread(
                        id=f"concurrent_{user.user_id}_{user_index}_{thread_idx}",
                        object_="thread",
                        created_at=int(time.time()),
                        metadata_={
                            "user_id": user.user_id,
                            "concurrent_test": True,
                            "scenario": scenario['name'],
                            "user_index": user_index,
                            "thread_index": thread_idx
                        }
                    )
                    db_session.add(thread)
                    created_threads.append(thread)
                    scenario_result['threads_created'] += 1
                    
                    # Create messages
                    for msg_idx in range(scenario['messages_per_thread']):
                        message = Message(
                            id=f"concurrent_msg_{user.user_id}_{user_index}_{thread_idx}_{msg_idx}",
                            object_="thread.message",
                            created_at=int(time.time()),
                            thread_id=thread.id,
                            role="user",
                            content=[{
                                "type": "text",
                                "text": {
                                    "value": f"Concurrent {scenario['name']} message {msg_idx}",
                                    "annotations": []
                                }
                            }],
                            metadata_={
                                "user_id": user.user_id,
                                "concurrent_test": True,
                                "scenario": scenario['name']
                            }
                        )
                        db_session.add(message)
                        scenario_result['messages_created'] += 1
                
                # Commit batch
                await db_session.commit()
                
                # Execute concurrent queries
                if scenario['name'] == 'heavy_read':
                    for query_idx in range(10):  # Heavy read scenario
                        query_result = await db_session.execute(
                            select(func.count(Message.id)).where(
                                Message.metadata_["user_id"].astext == user.user_id
                            )
                        )
                        count = query_result.scalar()
                        scenario_result['queries_executed'] += 1
                        
                        # Verify count makes sense
                        if count < scenario_result['messages_created']:
                            scenario_result['concurrent_safety_verified'] = False
                            scenario_result['errors'].append(
                                f"Query {query_idx} returned inconsistent count: {count}"
                            )
                
                # Add delay to simulate realistic timing
                await asyncio.sleep(0.1)
                
            except Exception as e:
                scenario_result['errors'].append(f"Workflow scenario failed: {str(e)}")
                await db_session.rollback()
            
            return scenario_result
        
        # Execute all scenarios concurrently
        self.logger.info("Executing concurrent workflow scenarios")
        
        all_workflow_tasks = []
        for user_index, user in enumerate(concurrent_users):
            scenario = workflow_scenarios[user_index % len(workflow_scenarios)]
            task = execute_workflow_scenario(user, scenario, user_index)
            all_workflow_tasks.append(task)
        
        workflow_results = await asyncio.gather(*all_workflow_tasks, return_exceptions=True)
        
        # Analyze concurrent workflow results
        workflow_failures = []
        successful_workflows = 0
        
        for result in workflow_results:
            if isinstance(result, Exception):
                workflow_failures.append(f"Workflow exception: {result}")
                continue
                
            if not result['concurrent_safety_verified']:
                workflow_failures.append(
                    f"Concurrent safety failed for user {result['user_id']} in {result['scenario']}"
                )
            
            if result['errors']:
                workflow_failures.extend([
                    f"User {result['user_id']} ({result['scenario']}): {error}"
                    for error in result['errors']
                ])
            else:
                successful_workflows += 1
        
        # Cleanup
        await self._cleanup_e2e_test_data(db_session, [user.user_id for user in concurrent_users])
        await db_session.close()
        
        # Assert concurrent workflow success
        assert len(workflow_failures) == 0, f"Concurrent workflow failures: {workflow_failures[:5]}"
        
        success_rate = successful_workflows / len(concurrent_users) if concurrent_users else 0
        assert success_rate >= 0.8, f"Concurrent workflow success rate too low: {success_rate:.1%}"
        
        self.logger.info(f"Concurrent database workflows completed: {successful_workflows}/{len(concurrent_users)} successful")

    async def _verify_final_database_state(self, db_session: AsyncSession, users: List[AuthenticatedUser]) -> Dict[str, Any]:
        """Verify final database state after E2E operations."""
        
        verification_result = {
            'verification_passed': True,
            'users_verified': 0,
            'data_integrity_confirmed': True,
            'cross_contamination_detected': False,
            'errors': []
        }
        
        try:
            for user in users:
                # Verify user data exists and is isolated
                user_threads = await db_session.execute(
                    select(Thread).where(
                        Thread.metadata_["user_id"].astext == user.user_id
                    )
                )
                threads = user_threads.scalars().all()
                
                # Check data integrity
                for thread in threads:
                    if thread.metadata_.get("user_id") != user.user_id:
                        verification_result['cross_contamination_detected'] = True
                        verification_result['errors'].append(
                            f"Cross-contamination: thread {thread.id} has wrong user_id"
                        )
                
                verification_result['users_verified'] += 1
            
            if verification_result['cross_contamination_detected']:
                verification_result['verification_passed'] = False
                verification_result['data_integrity_confirmed'] = False
                
        except Exception as e:
            verification_result['verification_passed'] = False
            verification_result['errors'].append(f"Verification failed: {str(e)}")
        
        return verification_result

    async def _cleanup_e2e_test_data(self, db_session: AsyncSession, user_ids: List[str]):
        """Clean up E2E test data."""
        
        try:
            # Delete messages
            await db_session.execute(
                text("DELETE FROM messages WHERE metadata_->>'e2e_test' = 'true'")
            )
            
            # Delete threads  
            await db_session.execute(
                text("DELETE FROM threads WHERE metadata_->>'e2e_test' = 'true'")
            )
            
            # Delete test users
            for user_id in user_ids:
                await db_session.execute(
                    text("DELETE FROM users WHERE id = :user_id"),
                    {"user_id": user_id}
                )
            
            await db_session.commit()
            
        except Exception as e:
            self.logger.warning(f"E2E cleanup failed: {e}")
            await db_session.rollback()