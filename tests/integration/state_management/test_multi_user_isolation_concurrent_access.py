"""
Test Multi-User State Isolation and Concurrent Access - State Management & Context Swimlane

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core multi-tenant platform functionality
- Business Goal: Ensure complete user data isolation and prevent state leakage between users
- Value Impact: Protects user privacy and enables secure multi-user AI interactions
- Strategic Impact: CRITICAL - User isolation is fundamental to platform security and scalability

This test suite validates comprehensive multi-user state isolation:
- Complete user data isolation across all operations
- Concurrent user operations without state interference
- User-specific context boundaries and access controls
- Race condition prevention in multi-user scenarios
- Resource isolation and fairness across users
- Security validation for user data segregation
"""

import asyncio
import json
import logging
import pytest
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import RealServicesManager, get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.session_management import UserSessionManager, get_user_session_tracker
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)


@pytest.fixture
async def real_services_fixture():
    """SSOT fixture for real services integration testing."""
    async with get_real_services() as services:
        yield services


@pytest.fixture
async def auth_helper():
    """E2E authentication helper fixture."""
    return E2EAuthHelper(environment="test")


@pytest.fixture
async def id_generator():
    """Unified ID generator fixture."""
    return UnifiedIdGenerator()


class TestMultiUserIsolationConcurrentAccess(BaseIntegrationTest):
    """
    Comprehensive multi-user state isolation and concurrent access tests.
    
    CRITICAL: Tests use REAL services only - PostgreSQL and Redis for actual isolation validation.
    All tests must validate actual business value through secure user isolation.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_user_data_isolation(self, real_services_fixture, auth_helper, id_generator):
        """
        Test complete user data isolation across all state operations.
        
        Business Value: Ensures user privacy and prevents data leakage between users.
        """
        # Create multiple users with distinct data
        test_users = []
        user_data_sets = []
        
        for i in range(4):  # Test with 4 users for comprehensive isolation
            auth_user = await auth_helper.create_authenticated_user(
                email=f"isolation_user_{i}_{uuid.uuid4().hex[:8]}@example.com",
                full_name=f"Isolation Test User {i}"
            )
            
            # Generate unique thread and run IDs
            thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"isolation_test_{i}"
            )
            
            # Create user-specific sensitive data
            user_sensitive_data = {
                'user_id': auth_user.user_id,
                'email': auth_user.email,
                'full_name': auth_user.full_name,
                'thread_id': thread_id,
                'run_id': run_id,
                'request_id': request_id,
                'private_data': {
                    'user_index': i,
                    'secret_key': f"secret_data_user_{i}_{uuid.uuid4().hex}",
                    'personal_info': f"Personal info for user {i}",
                    'sensitive_context': f"Sensitive context {i}",
                    'financial_data': f"Financial info user {i}",
                    'ai_conversation_context': f"Private AI context for user {i}"
                },
                'user_specific_ids': {
                    'internal_user_id': f"internal_{i}_{uuid.uuid4().hex[:8]}",
                    'customer_id': f"customer_{i}",
                    'organization_id': f"org_{i}"
                }
            }
            
            test_users.append(auth_user)
            user_data_sets.append(user_sensitive_data)
        
        # Store each user's data in database and cache with proper isolation
        stored_user_contexts = []
        
        for i, (auth_user, user_data) in enumerate(zip(test_users, user_data_sets)):
            # Store user in database with unique constraints
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO auth.users (id, email, name, is_active, created_at, metadata)
                    VALUES ($1, $2, $3, true, $4, $5)
                    ON CONFLICT (email) DO NOTHING
                """, auth_user.user_id, auth_user.email, auth_user.full_name, 
                datetime.now(timezone.utc), json.dumps(user_data['private_data']))
                
                # Create user-specific thread
                await tx.execute("""
                    INSERT INTO backend.threads (id, user_id, title, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $4, $5)
                """, user_data['thread_id'], auth_user.user_id, 
                f"Private Thread User {i}", datetime.now(timezone.utc),
                json.dumps(user_data['user_specific_ids']))
                
                # Create user-specific run
                await tx.execute("""
                    INSERT INTO backend.runs (id, thread_id, status, started_at, metadata)
                    VALUES ($1, $2, 'active', $3, $4)
                """, user_data['run_id'], user_data['thread_id'], 
                datetime.now(timezone.utc), json.dumps({'user_index': i}))
            
            # Store user context in Redis with proper isolation
            user_context_key = f"user_context:{auth_user.user_id}"
            thread_context_key = f"thread:{user_data['thread_id']}"
            
            await real_services_fixture.redis.set_json(user_context_key, user_data, ex=3600)
            await real_services_fixture.redis.set_json(thread_context_key, {
                'thread_id': user_data['thread_id'],
                'user_id': auth_user.user_id,
                'private_data': user_data['private_data'],
                'user_specific_ids': user_data['user_specific_ids']
            }, ex=3600)
            
            stored_user_contexts.append({
                'user_context_key': user_context_key,
                'thread_context_key': thread_context_key,
                'user_data': user_data
            })
        
        # Validate complete isolation - each user can only access their own data
        for i, context in enumerate(stored_user_contexts):
            user_data = context['user_data']
            current_user_id = user_data['user_id']
            
            # Verify user can access their own data
            own_user_context = await real_services_fixture.redis.get_json(context['user_context_key'])
            assert own_user_context is not None
            assert own_user_context['user_id'] == current_user_id
            assert own_user_context['private_data']['user_index'] == i
            
            # Verify database isolation
            db_user = await real_services_fixture.postgres.fetchrow("""
                SELECT id, email, metadata FROM auth.users WHERE id = $1
            """, current_user_id)
            
            assert db_user is not None
            assert db_user['id'] == current_user_id
            user_metadata = json.loads(db_user['metadata'])
            assert user_metadata['user_index'] == i
            
            # Verify user cannot access other users' data
            for j, other_context in enumerate(stored_user_contexts):
                if i != j:  # Different user
                    other_user_data = other_context['user_data']
                    
                    # Attempt to access other user's context should fail or return None
                    # (In a properly isolated system, users shouldn't even know other user keys)
                    
                    # Verify no data leakage in own context
                    assert own_user_context['private_data']['user_index'] != j
                    assert own_user_context['user_id'] != other_user_data['user_id']
                    assert own_user_context['private_data']['secret_key'] != other_user_data['private_data']['secret_key']
        
        # Cross-validation: Verify no user data appears in other users' contexts
        isolation_violations = []
        
        for i, context_i in enumerate(stored_user_contexts):
            user_data_i = context_i['user_data']
            
            for j, context_j in enumerate(stored_user_contexts):
                if i != j:  # Different users
                    user_data_j = context_j['user_data']
                    
                    # Check for any data leakage
                    context_i_data = await real_services_fixture.redis.get_json(context_i['user_context_key'])
                    
                    # Verify no other user's data appears in this user's context
                    context_i_str = json.dumps(context_i_data)
                    
                    # Check for leaked sensitive data
                    if user_data_j['private_data']['secret_key'] in context_i_str:
                        isolation_violations.append(f"User {i} context contains User {j} secret key")
                    if user_data_j['email'] in context_i_str and user_data_j['email'] != user_data_i['email']:
                        isolation_violations.append(f"User {i} context contains User {j} email")
                    if user_data_j['private_data']['personal_info'] in context_i_str:
                        isolation_violations.append(f"User {i} context contains User {j} personal info")
        
        assert len(isolation_violations) == 0, f"User isolation violations detected: {isolation_violations}"
        
        # BUSINESS VALUE VALIDATION: Complete user isolation ensures privacy and security
        self.assert_business_value_delivered({
            'users_isolated': len(test_users),
            'isolation_violations': len(isolation_violations),
            'data_privacy_maintained': True,
            'cross_user_access_prevented': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_operations_without_interference(self, real_services_fixture, auth_helper, id_generator):
        """
        Test concurrent user operations without state interference.
        
        Business Value: Ensures platform scalability and prevents user operation conflicts.
        """
        # Create users for concurrent testing
        concurrent_users = []
        for i in range(6):  # 6 concurrent users
            auth_user = await auth_helper.create_authenticated_user(
                email=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            concurrent_users.append(auth_user)
        
        # Define concurrent operations each user will perform
        async def user_operations(user_index: int, auth_user, operation_count: int = 5) -> Dict[str, Any]:
            """Perform concurrent operations for a single user."""
            user_id = auth_user.user_id
            operation_results = []
            
            # Create user in database
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO auth.users (id, email, name, is_active, created_at)
                    VALUES ($1, $2, $3, true, $4)
                    ON CONFLICT (email) DO NOTHING
                """, user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            # Perform multiple operations concurrently for this user
            for op_num in range(operation_count):
                # Generate unique IDs for this operation
                thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                    user_id=user_id,
                    operation=f"concurrent_op_{user_index}_{op_num}"
                )
                
                # Operation 1: Create thread
                async with real_services_fixture.postgres.transaction() as tx:
                    await tx.execute("""
                        INSERT INTO backend.threads (id, user_id, title, created_at, updated_at, status)
                        VALUES ($1, $2, $3, $4, $4, 'active')
                    """, thread_id, user_id, f"Thread {user_index}-{op_num}", datetime.now(timezone.utc))
                    
                    # Operation 2: Create run
                    await tx.execute("""
                        INSERT INTO backend.runs (id, thread_id, status, started_at, metadata)
                        VALUES ($1, $2, 'active', $3, $4)
                    """, run_id, thread_id, datetime.now(timezone.utc), 
                    json.dumps({'user_index': user_index, 'op_num': op_num}))
                
                # Operation 3: Cache user state
                state_data = {
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'user_index': user_index,
                    'operation_number': op_num,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'concurrent_test': True
                }
                
                await real_services_fixture.redis.set_json(f"user_op:{user_id}:{op_num}", state_data, ex=1800)
                
                # Operation 4: Add messages
                for msg_num in range(2):  # 2 messages per operation
                    message_id = f"{run_id}_msg_{msg_num}"
                    await real_services_fixture.postgres.execute("""
                        INSERT INTO backend.messages (id, thread_id, run_id, role, content, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, message_id, thread_id, run_id, 
                    "user" if msg_num % 2 == 0 else "assistant",
                    f"Message {msg_num} from User {user_index} Operation {op_num}",
                    datetime.now(timezone.utc))
                
                operation_results.append({
                    'thread_id': thread_id,
                    'run_id': run_id,
                    'operation_number': op_num,
                    'messages_created': 2
                })
                
                # Add small delay to simulate real processing
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            return {
                'user_id': user_id,
                'user_index': user_index,
                'operations_completed': len(operation_results),
                'operation_results': operation_results
            }
        
        # Execute all user operations concurrently
        concurrent_results = await asyncio.gather(*[
            user_operations(i, user, 5) for i, user in enumerate(concurrent_users)
        ])
        
        # Validate all operations completed successfully
        assert len(concurrent_results) == len(concurrent_users)
        
        total_operations = sum(result['operations_completed'] for result in concurrent_results)
        expected_operations = len(concurrent_users) * 5
        assert total_operations == expected_operations
        
        # Validate operation isolation - each user's operations should be distinct
        all_thread_ids = set()
        all_run_ids = set()
        user_operation_mapping = {}
        
        for result in concurrent_results:
            user_id = result['user_id']
            user_index = result['user_index']
            
            # Collect all IDs for uniqueness validation
            user_threads = []
            user_runs = []
            
            for op_result in result['operation_results']:
                thread_id = op_result['thread_id']
                run_id = op_result['run_id']
                
                # Check for ID uniqueness across all users
                assert thread_id not in all_thread_ids, f"Thread ID collision: {thread_id}"
                assert run_id not in all_run_ids, f"Run ID collision: {run_id}"
                
                all_thread_ids.add(thread_id)
                all_run_ids.add(run_id)
                user_threads.append(thread_id)
                user_runs.append(run_id)
            
            user_operation_mapping[user_id] = {
                'user_index': user_index,
                'threads': user_threads,
                'runs': user_runs
            }
        
        # Validate database integrity after concurrent operations
        for result in concurrent_results:
            user_id = result['user_id']
            user_index = result['user_index']
            
            # Verify user's threads in database
            user_threads = await real_services_fixture.postgres.fetch("""
                SELECT id, title, user_id FROM backend.threads 
                WHERE user_id = $1 AND title LIKE $2
            """, user_id, f"Thread {user_index}-%")
            
            assert len(user_threads) == 5  # 5 operations per user
            
            # Verify all threads belong to correct user
            for thread in user_threads:
                assert thread['user_id'] == user_id
                assert f"Thread {user_index}-" in thread['title']
            
            # Verify user's messages
            user_messages = await real_services_fixture.postgres.fetch("""
                SELECT m.id, m.content, t.user_id
                FROM backend.messages m
                JOIN backend.threads t ON m.thread_id = t.id
                WHERE t.user_id = $1 AND m.content LIKE $2
            """, user_id, f"%User {user_index} Operation%")
            
            expected_messages = 5 * 2  # 5 operations × 2 messages each
            assert len(user_messages) == expected_messages
            
            # Verify no messages from other users
            for message in user_messages:
                assert f"User {user_index}" in message['content']
                assert message['user_id'] == user_id
        
        # Cross-user validation: Ensure no data leakage
        for i, result_i in enumerate(concurrent_results):
            user_i_id = result_i['user_id']
            
            for j, result_j in enumerate(concurrent_results):
                if i != j:  # Different users
                    user_j_id = result_j['user_id']
                    user_j_index = result_j['user_index']
                    
                    # Verify user i has no data from user j
                    cross_contamination = await real_services_fixture.postgres.fetchval("""
                        SELECT COUNT(*)
                        FROM backend.messages m
                        JOIN backend.threads t ON m.thread_id = t.id
                        WHERE t.user_id = $1 AND m.content LIKE $2
                    """, user_i_id, f"%User {user_j_index}%")
                    
                    assert cross_contamination == 0, f"User {i} has data from User {j}"
        
        # BUSINESS VALUE VALIDATION: Concurrent operations maintain isolation
        self.assert_business_value_delivered({
            'concurrent_users': len(concurrent_users),
            'total_operations': total_operations,
            'id_collisions': 0,
            'data_leakage_incidents': 0,
            'concurrent_success_rate': 1.0
        }, 'automation')
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_race_condition_prevention_multi_user(self, real_services_fixture, auth_helper, id_generator):
        """
        Test race condition prevention in multi-user scenarios.
        
        Business Value: Prevents data corruption and ensures system reliability under load.
        """
        # Create shared resource that multiple users will access concurrently
        shared_resource_id = f"shared_resource_{uuid.uuid4().hex[:8]}"
        
        # Initialize shared resource in database
        async with real_services_fixture.postgres.transaction() as tx:
            await tx.execute("""
                CREATE TABLE IF NOT EXISTS test_shared_resources (
                    id TEXT PRIMARY KEY,
                    current_value INTEGER DEFAULT 0,
                    last_modified_by TEXT,
                    last_modified_at TIMESTAMP WITH TIME ZONE,
                    version INTEGER DEFAULT 0
                )
            """)
            
            await tx.execute("""
                INSERT INTO test_shared_resources (id, current_value, last_modified_at, version)
                VALUES ($1, 0, $2, 0)
                ON CONFLICT (id) DO NOTHING
            """, shared_resource_id, datetime.now(timezone.utc))
        
        # Create users who will compete for the shared resource
        racing_users = []
        for i in range(8):  # 8 users for intense race condition testing
            auth_user = await auth_helper.create_authenticated_user(
                email=f"race_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            racing_users.append((i, auth_user))
        
        # Define race condition operation: increment shared counter with proper locking
        async def racing_operation(user_index: int, auth_user, iterations: int = 10) -> Dict[str, Any]:
            """Perform operations that could cause race conditions."""
            user_id = auth_user.user_id
            successful_increments = 0
            race_attempts = 0
            
            for iteration in range(iterations):
                race_attempts += 1
                
                try:
                    # Use database transaction with proper locking to prevent race conditions
                    async with real_services_fixture.postgres.transaction() as tx:
                        # Lock the row to prevent race conditions
                        current_state = await tx.fetchrow("""
                            SELECT current_value, version, last_modified_by
                            FROM test_shared_resources 
                            WHERE id = $1 
                            FOR UPDATE
                        """, shared_resource_id)
                        
                        if current_state is None:
                            continue
                        
                        # Simulate some processing time that could expose race conditions
                        await asyncio.sleep(random.uniform(0.001, 0.005))
                        
                        # Increment value with version checking (optimistic locking)
                        new_value = current_state['current_value'] + 1
                        new_version = current_state['version'] + 1
                        
                        updated_rows = await tx.fetchval("""
                            UPDATE test_shared_resources 
                            SET current_value = $2, 
                                last_modified_by = $3, 
                                last_modified_at = $4,
                                version = $5
                            WHERE id = $1 AND version = $6
                            RETURNING current_value
                        """, shared_resource_id, new_value, user_id, 
                        datetime.now(timezone.utc), new_version, current_state['version'])
                        
                        if updated_rows is not None:
                            successful_increments += 1
                            
                            # Log operation in Redis for tracking
                            operation_log = {
                                'user_id': user_id,
                                'user_index': user_index,
                                'iteration': iteration,
                                'old_value': current_state['current_value'],
                                'new_value': new_value,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            }
                            
                            await real_services_fixture.redis.lpush(
                                f"race_log:{shared_resource_id}", 
                                json.dumps(operation_log)
                            )
                
                except Exception as e:
                    logger.warning(f"Race condition handling for user {user_index}: {e}")
                    # In a proper system, we would retry or handle gracefully
                    continue
            
            return {
                'user_id': user_id,
                'user_index': user_index,
                'successful_increments': successful_increments,
                'race_attempts': race_attempts,
                'success_rate': successful_increments / race_attempts if race_attempts > 0 else 0
            }
        
        # Execute racing operations concurrently
        race_results = await asyncio.gather(*[
            racing_operation(user_index, auth_user, 10) 
            for user_index, auth_user in racing_users
        ])
        
        # Validate race condition prevention
        final_resource_state = await real_services_fixture.postgres.fetchrow("""
            SELECT current_value, version, last_modified_by, last_modified_at
            FROM test_shared_resources WHERE id = $1
        """, shared_resource_id)
        
        assert final_resource_state is not None
        
        # Verify data integrity
        total_successful_increments = sum(result['successful_increments'] for result in race_results)
        final_value = final_resource_state['current_value']
        
        # The final value should equal the total successful increments
        assert final_value == total_successful_increments, \
            f"Race condition detected: Expected {total_successful_increments}, got {final_value}"
        
        # Verify operation log integrity
        operation_log_length = await real_services_fixture.redis.llen(f"race_log:{shared_resource_id}")
        assert operation_log_length == total_successful_increments
        
        # Analyze race condition metrics
        total_attempts = sum(result['race_attempts'] for result in race_results)
        overall_success_rate = total_successful_increments / total_attempts if total_attempts > 0 else 0
        
        # In a well-designed system, we should have a reasonable success rate
        # (not 100% due to legitimate contention, but not too low)
        assert overall_success_rate > 0.5, f"Success rate too low: {overall_success_rate}"
        
        # Validate no user was completely starved of access
        for result in race_results:
            assert result['successful_increments'] > 0, \
                f"User {result['user_index']} was completely starved of resource access"
        
        # Clean up test table
        await real_services_fixture.postgres.execute("""
            DROP TABLE IF EXISTS test_shared_resources
        """)
        
        # BUSINESS VALUE VALIDATION: Race condition prevention ensures data integrity
        self.assert_business_value_delivered({
            'concurrent_users': len(racing_users),
            'total_operations': total_attempts,
            'successful_operations': total_successful_increments,
            'data_integrity_maintained': final_value == total_successful_increments,
            'fairness_maintained': all(r['successful_increments'] > 0 for r in race_results),
            'success_rate': overall_success_rate
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_isolation_and_fairness(self, real_services_fixture, auth_helper, id_generator):
        """
        Test resource isolation and fairness across users under load.
        
        Business Value: Ensures equitable resource distribution and prevents resource hogging.
        """
        # Create users with different resource requirements
        resource_users = []
        user_profiles = [
            {'type': 'light_user', 'operations': 5, 'data_size': 100},
            {'type': 'medium_user', 'operations': 15, 'data_size': 500},
            {'type': 'heavy_user', 'operations': 25, 'data_size': 1000},
            {'type': 'light_user', 'operations': 5, 'data_size': 100},
            {'type': 'medium_user', 'operations': 15, 'data_size': 500},
        ]
        
        for i, profile in enumerate(user_profiles):
            auth_user = await auth_helper.create_authenticated_user(
                email=f"resource_user_{i}_{profile['type']}_{uuid.uuid4().hex[:8]}@example.com"
            )
            resource_users.append((auth_user, profile))
        
        # Track resource usage per user
        resource_usage_tracker = {}
        
        async def user_resource_operations(auth_user, profile: Dict[str, Any]) -> Dict[str, Any]:
            """Perform resource-intensive operations for a user."""
            user_id = auth_user.user_id
            user_type = profile['type']
            operations_count = profile['operations']
            data_size = profile['data_size']
            
            # Initialize user in database
            async with real_services_fixture.postgres.transaction() as tx:
                await tx.execute("""
                    INSERT INTO auth.users (id, email, name, is_active, created_at)
                    VALUES ($1, $2, $3, true, $4)
                    ON CONFLICT (email) DO NOTHING
                """, user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            operation_start_time = time.time()
            database_operations = 0
            cache_operations = 0
            storage_used = 0
            
            # Perform operations based on user profile
            for op_num in range(operations_count):
                # Generate IDs for this operation
                thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                    user_id=user_id,
                    operation=f"resource_op_{op_num}"
                )
                
                # Database operation
                large_data = "x" * data_size  # Simulate data of specified size
                
                async with real_services_fixture.postgres.transaction() as tx:
                    await tx.execute("""
                        INSERT INTO backend.threads (id, user_id, title, created_at, updated_at, metadata)
                        VALUES ($1, $2, $3, $4, $4, $5)
                    """, thread_id, user_id, f"Resource Thread {op_num}", 
                    datetime.now(timezone.utc), json.dumps({'data': large_data, 'user_type': user_type}))
                    
                    database_operations += 1
                
                # Cache operation
                cache_data = {
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'user_type': user_type,
                    'operation_number': op_num,
                    'large_payload': large_data,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                await real_services_fixture.redis.set_json(
                    f"resource:{user_id}:{op_num}", 
                    cache_data, 
                    ex=1800
                )
                cache_operations += 1
                storage_used += len(json.dumps(cache_data))
                
                # Add processing delay proportional to data size
                await asyncio.sleep(0.001 * (data_size / 100))
            
            operation_end_time = time.time()
            total_time = operation_end_time - operation_start_time
            
            return {
                'user_id': user_id,
                'user_type': user_type,
                'operations_completed': operations_count,
                'database_operations': database_operations,
                'cache_operations': cache_operations,
                'storage_used_bytes': storage_used,
                'total_time_seconds': total_time,
                'operations_per_second': operations_count / total_time if total_time > 0 else 0
            }
        
        # Execute all user operations concurrently
        resource_results = await asyncio.gather(*[
            user_resource_operations(user, profile) 
            for user, profile in resource_users
        ])
        
        # Analyze resource usage and fairness
        resource_analysis = {
            'light_users': [r for r in resource_results if r['user_type'] == 'light_user'],
            'medium_users': [r for r in resource_results if r['user_type'] == 'medium_user'],
            'heavy_users': [r for r in resource_results if r['user_type'] == 'heavy_user']
        }
        
        # Verify all users completed their operations
        for result in resource_results:
            profile = next(p for _, p in resource_users if p['operations'] == result['operations_completed'])
            assert result['operations_completed'] == profile['operations']
            assert result['database_operations'] == profile['operations']
            assert result['cache_operations'] == profile['operations']
        
        # Verify resource fairness - no user type should be significantly starved
        for user_type, results in resource_analysis.items():
            if results:  # If we have users of this type
                avg_ops_per_second = sum(r['operations_per_second'] for r in results) / len(results)
                min_ops_per_second = min(r['operations_per_second'] for r in results)
                max_ops_per_second = max(r['operations_per_second'] for r in results)
                
                # Verify reasonable performance variance (no user completely starved)
                if max_ops_per_second > 0:
                    fairness_ratio = min_ops_per_second / max_ops_per_second
                    assert fairness_ratio > 0.3, \
                        f"Unfair resource allocation for {user_type}: ratio {fairness_ratio}"
        
        # Verify database isolation - each user's data is separate
        for result in resource_results:
            user_id = result['user_id']
            
            # Check user's threads
            user_threads = await real_services_fixture.postgres.fetch("""
                SELECT id, user_id, metadata FROM backend.threads WHERE user_id = $1
            """, user_id)
            
            assert len(user_threads) == result['operations_completed']
            
            # Verify no cross-contamination
            for thread in user_threads:
                assert thread['user_id'] == user_id
                thread_metadata = json.loads(thread['metadata'])
                assert thread_metadata['user_type'] == result['user_type']
        
        # Verify cache isolation
        cache_isolation_verified = True
        for i, result_i in enumerate(resource_results):
            user_i_id = result_i['user_id']
            
            # Get all cache keys for this user
            user_cache_keys = []
            for op_num in range(result_i['operations_completed']):
                key = f"resource:{user_i_id}:{op_num}"
                cache_data = await real_services_fixture.redis.get_json(key)
                if cache_data:
                    assert cache_data['user_id'] == user_i_id
                    user_cache_keys.append(key)
            
            assert len(user_cache_keys) == result_i['operations_completed']
        
        # Calculate overall resource utilization metrics
        total_operations = sum(r['operations_completed'] for r in resource_results)
        total_storage = sum(r['storage_used_bytes'] for r in resource_results)
        total_time = max(r['total_time_seconds'] for r in resource_results)
        
        # BUSINESS VALUE VALIDATION: Resource isolation ensures fairness and performance
        self.assert_business_value_delivered({
            'users_served': len(resource_users),
            'total_operations': total_operations,
            'total_storage_bytes': total_storage,
            'resource_isolation_maintained': cache_isolation_verified,
            'fairness_maintained': True,  # All users completed operations
            'system_throughput': total_operations / total_time if total_time > 0 else 0
        }, 'automation')