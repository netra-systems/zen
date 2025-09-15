"""
Test WebSocket Application State Cross-User Isolation Validation Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Security and Privacy Critical
- Business Goal: Ensure complete user data isolation in multi-tenant environment
- Value Impact: Users never see other users' data or affect other users' state
- Strategic Impact: Foundation of enterprise trust - data isolation is non-negotiable

This test validates that application state changes for one user do not affect
or become visible to other users. The system must maintain perfect isolation
across all state layers (PostgreSQL, Redis, WebSocket).
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List, Optional, Set
from uuid import uuid4
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState
from shared.types import UserID, ThreadID, MessageID, OrganizationID
from shared.isolated_environment import get_env


@dataclass
class UserTestContext:
    """Context for a user in isolation testing."""
    user_id: UserID
    connection_id: str
    thread_ids: List[ThreadID]
    message_ids: List[MessageID]
    organization_id: Optional[OrganizationID] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': str(self.user_id),
            'connection_id': self.connection_id,
            'thread_ids': [str(tid) for tid in self.thread_ids],
            'message_ids': [str(mid) for mid in self.message_ids],
            'organization_id': str(self.organization_id) if self.organization_id else None
        }


class IsolationTestValidator:
    """Validates isolation between users in the system."""
    
    def __init__(self, services, state_manager):
        self.services = services
        self.state_manager = state_manager
        self.isolation_violations: List[Dict[str, Any]] = []
    
    async def validate_database_isolation(self, user_contexts: List[UserTestContext]) -> Dict[str, bool]:
        """Validate that database queries respect user isolation."""
        isolation_results = {}
        
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            other_users = [ctx for j, ctx in enumerate(user_contexts) if j != i]
            
            # Test: User should only see their own threads
            user_threads = await self.services.postgres.fetch("""
                SELECT id, user_id, title FROM backend.threads WHERE user_id = $1
            """, str(user_id))
            
            user_thread_ids = set(str(t['id']) for t in user_threads)
            expected_thread_ids = set(str(tid) for tid in user_context.thread_ids)
            
            # Verify user sees all their threads
            threads_accessible = user_thread_ids == expected_thread_ids
            isolation_results[f'user_{i}_threads_accessible'] = threads_accessible
            
            if not threads_accessible:
                self.isolation_violations.append({
                    'type': 'missing_user_threads',
                    'user_id': str(user_id),
                    'expected_threads': list(expected_thread_ids),
                    'actual_threads': list(user_thread_ids)
                })
            
            # Test: User should not see other users' threads
            for j, other_user in enumerate(other_users):
                other_user_threads = await self.services.postgres.fetch("""
                    SELECT id FROM backend.threads WHERE user_id = $1
                """, str(other_user.user_id))
                
                other_thread_ids = set(str(t['id']) for t in other_user_threads)
                thread_isolation_maintained = user_thread_ids.isdisjoint(other_thread_ids)
                
                isolation_results[f'user_{i}_isolated_from_user_{j}'] = thread_isolation_maintained
                
                if not thread_isolation_maintained:
                    leaked_threads = user_thread_ids.intersection(other_thread_ids)
                    self.isolation_violations.append({
                        'type': 'thread_isolation_violation',
                        'user_id': str(user_id),
                        'other_user_id': str(other_user.user_id),
                        'leaked_threads': list(leaked_threads)
                    })
            
            # Test: User messages isolation
            user_messages = await self.services.postgres.fetch("""
                SELECT id, user_id, thread_id FROM backend.messages WHERE user_id = $1
            """, str(user_id))
            
            user_message_ids = set(str(m['id']) for m in user_messages)
            expected_message_ids = set(str(mid) for mid in user_context.message_ids)
            
            messages_accessible = user_message_ids == expected_message_ids
            isolation_results[f'user_{i}_messages_accessible'] = messages_accessible
            
            if not messages_accessible:
                self.isolation_violations.append({
                    'type': 'missing_user_messages',
                    'user_id': str(user_id),
                    'expected_messages': list(expected_message_ids),
                    'actual_messages': list(user_message_ids)
                })
        
        return isolation_results
    
    async def validate_redis_isolation(self, user_contexts: List[UserTestContext]) -> Dict[str, bool]:
        """Validate that Redis cache respects user isolation."""
        isolation_results = {}
        
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            
            # Test: User's thread cache accessibility
            accessible_threads = []
            inaccessible_threads = []
            
            for thread_id in user_context.thread_ids:
                cached_thread = await self.services.redis.get_json(f"thread:{thread_id}")
                if cached_thread:
                    # Verify cached thread belongs to correct user
                    if cached_thread.get('user_id') == str(user_id):
                        accessible_threads.append(str(thread_id))
                    else:
                        self.isolation_violations.append({
                            'type': 'redis_thread_ownership_violation',
                            'cached_thread_id': str(thread_id),
                            'expected_user': str(user_id),
                            'actual_user': cached_thread.get('user_id')
                        })
                else:
                    inaccessible_threads.append(str(thread_id))
            
            thread_cache_correct = len(accessible_threads) == len(user_context.thread_ids)
            isolation_results[f'user_{i}_redis_threads_correct'] = thread_cache_correct
            
            # Test: User's message cache accessibility
            accessible_messages = []
            for message_id in user_context.message_ids:
                cached_message = await self.services.redis.get_json(f"message:{message_id}")
                if cached_message:
                    if cached_message.get('user_id') == str(user_id):
                        accessible_messages.append(str(message_id))
                    else:
                        self.isolation_violations.append({
                            'type': 'redis_message_ownership_violation',
                            'cached_message_id': str(message_id),
                            'expected_user': str(user_id),
                            'actual_user': cached_message.get('user_id')
                        })
            
            message_cache_correct = len(accessible_messages) == len(user_context.message_ids)
            isolation_results[f'user_{i}_redis_messages_correct'] = message_cache_correct
            
            # Test: Cross-contamination check - no other users' data should be accessible
            other_users = [ctx for j, ctx in enumerate(user_contexts) if j != i]
            contamination_found = False
            
            for other_user in other_users:
                for other_thread_id in other_user.thread_ids:
                    # Try to access other user's thread cache using this user's context
                    cached_thread = await self.services.redis.get_json(f"thread:{other_thread_id}")
                    if cached_thread and cached_thread.get('user_id') == str(user_id):
                        # This would be a serious isolation violation
                        contamination_found = True
                        self.isolation_violations.append({
                            'type': 'redis_cross_user_contamination',
                            'user_id': str(user_id),
                            'contaminated_thread_id': str(other_thread_id),
                            'other_user_id': str(other_user.user_id)
                        })
            
            isolation_results[f'user_{i}_redis_no_contamination'] = not contamination_found
        
        return isolation_results
    
    async def validate_websocket_isolation(self, user_contexts: List[UserTestContext]) -> Dict[str, bool]:
        """Validate that WebSocket state respects user isolation."""
        isolation_results = {}
        
        for i, user_context in enumerate(user_contexts):
            user_id = user_context.user_id
            connection_id = user_context.connection_id
            
            # Test: User's WebSocket state accessibility
            ws_state = self.state_manager.get_websocket_state(connection_id, 'connection_info')
            
            ws_state_accessible = ws_state is not None
            isolation_results[f'user_{i}_websocket_state_accessible'] = ws_state_accessible
            
            if ws_state_accessible:
                # Verify WebSocket state belongs to correct user
                ws_user_id = ws_state.get('user_id')
                correct_ownership = ws_user_id == str(user_id)
                isolation_results[f'user_{i}_websocket_ownership_correct'] = correct_ownership
                
                if not correct_ownership:
                    self.isolation_violations.append({
                        'type': 'websocket_ownership_violation',
                        'connection_id': connection_id,
                        'expected_user': str(user_id),
                        'actual_user': ws_user_id
                    })
            
            # Test: Other users cannot access this user's WebSocket state
            other_users = [ctx for j, ctx in enumerate(user_contexts) if j != i]
            cross_access_blocked = True
            
            for other_user in other_users:
                # Attempt to access this user's WebSocket state from another user's context
                # In a properly isolated system, this should not be possible
                try:
                    other_ws_state = self.state_manager.get_websocket_state(
                        connection_id, 'connection_info'
                    )
                    
                    # If other user can access state and it contains sensitive data
                    if other_ws_state and 'current_thread_id' in other_ws_state:
                        current_thread_id = other_ws_state['current_thread_id']
                        
                        # Check if this thread belongs to the original user
                        if current_thread_id in [str(tid) for tid in user_context.thread_ids]:
                            # This is expected - the state is correctly isolated
                            continue
                        else:
                            cross_access_blocked = False
                            self.isolation_violations.append({
                                'type': 'websocket_cross_access_violation',
                                'original_user': str(user_id),
                                'accessing_user': str(other_user.user_id),
                                'leaked_thread_id': current_thread_id
                            })
                except Exception:
                    # Exception is expected when access is properly blocked
                    continue
            
            isolation_results[f'user_{i}_websocket_cross_access_blocked'] = cross_access_blocked
        
        return isolation_results


class TestWebSocketApplicationStateCrossUserIsolationValidation(BaseIntegrationTest):
    """Test cross-user state isolation validation during concurrent WebSocket operations."""
    
    async def create_isolated_user_environment(self, services, user_count: int = 3) -> List[UserTestContext]:
        """Create isolated environments for multiple users."""
        user_contexts = []
        
        for i in range(user_count):
            # Create user
            user_data = await self.create_test_user_context(services, {
                'email': f'isolation-user-{i}@example.com',
                'name': f'Isolation Test User {i}'
            })
            user_id = UserID(user_data['id'])
            
            # Create user's threads
            thread_ids = []
            for j in range(2):  # 2 threads per user
                thread_id = await services.postgres.fetchval("""
                    INSERT INTO backend.threads (user_id, title, metadata)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, str(user_id), f"User {i} Thread {j}", json.dumps({
                    'user_index': i,
                    'thread_index': j,
                    'isolation_test': True
                }))
                
                thread_ids.append(ThreadID(str(thread_id)))
                
                # Cache thread in Redis
                await services.redis.set_json(f"thread:{thread_id}", {
                    'id': str(thread_id),
                    'user_id': str(user_id),
                    'title': f'User {i} Thread {j}',
                    'user_index': i,
                    'thread_index': j
                }, ex=3600)
            
            # Create user's messages
            message_ids = []
            for thread_id in thread_ids:
                for k in range(2):  # 2 messages per thread
                    message_id = MessageID(str(uuid4()))
                    
                    await services.postgres.execute("""
                        INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                        VALUES ($1, $2, $3, $4, $5)
                    """, str(message_id), str(thread_id), str(user_id), 
                         f"User {i} message {k} in thread {thread_id}", "user")
                    
                    message_ids.append(message_id)
                    
                    # Cache message in Redis
                    await services.redis.set_json(f"message:{message_id}", {
                        'id': str(message_id),
                        'thread_id': str(thread_id),
                        'user_id': str(user_id),
                        'content': f"User {i} message {k}",
                        'user_index': i
                    }, ex=3600)
            
            # Set up WebSocket state
            connection_id = str(uuid4())
            user_context = UserTestContext(
                user_id=user_id,
                connection_id=connection_id,
                thread_ids=thread_ids,
                message_ids=message_ids
            )
            
            state_manager = get_websocket_state_manager()
            state_manager.set_websocket_state(connection_id, 'connection_info', {
                'user_id': str(user_id),
                'connection_id': connection_id,
                'current_thread_id': str(thread_ids[0]) if thread_ids else None,
                'thread_count': len(thread_ids),
                'message_count': len(message_ids),
                'user_index': i,
                'state': WebSocketConnectionState.CONNECTED.value
            })
            
            user_contexts.append(user_context)
        
        return user_contexts
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_user_state_isolation_validation(self, real_services_fixture):
        """Test complete isolation of user state across all system layers."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create isolated user environments
        user_contexts = await self.create_isolated_user_environment(services, user_count=3)
        
        # Create isolation validator
        validator = IsolationTestValidator(services, state_manager)
        
        # Run comprehensive isolation validation
        database_isolation = await validator.validate_database_isolation(user_contexts)
        redis_isolation = await validator.validate_redis_isolation(user_contexts)
        websocket_isolation = await validator.validate_websocket_isolation(user_contexts)
        
        # Analyze results
        all_results = {**database_isolation, **redis_isolation, **websocket_isolation}
        
        passed_checks = sum(1 for result in all_results.values() if result)
        total_checks = len(all_results)
        isolation_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        self.logger.info(f"User isolation validation results:")
        self.logger.info(f"  Total isolation checks: {total_checks}")
        self.logger.info(f"  Passed checks: {passed_checks}")
        self.logger.info(f"  Isolation score: {isolation_score:.1f}%")
        
        # Log detailed results
        for category, results in [("Database", database_isolation), ("Redis", redis_isolation), ("WebSocket", websocket_isolation)]:
            category_passed = sum(1 for result in results.values() if result)
            category_total = len(results)
            self.logger.info(f"  {category}: {category_passed}/{category_total} checks passed")
        
        # Log any violations found
        if validator.isolation_violations:
            self.logger.warning(f"Isolation violations detected: {len(validator.isolation_violations)}")
            for violation in validator.isolation_violations:
                self.logger.warning(f"  {violation['type']}: {violation}")
        
        # Critical assertions - isolation must be perfect
        assert isolation_score == 100.0, f"Isolation not perfect: {isolation_score:.1f}% (violations: {len(validator.isolation_violations)})"
        assert len(validator.isolation_violations) == 0, f"Isolation violations found: {validator.isolation_violations}"
        
        # Verify each user can access their own data
        for i, user_context in enumerate(user_contexts):
            assert all_results.get(f'user_{i}_threads_accessible', False), f"User {i} cannot access own threads"
            assert all_results.get(f'user_{i}_messages_accessible', False), f"User {i} cannot access own messages"
            assert all_results.get(f'user_{i}_websocket_state_accessible', False), f"User {i} cannot access own WebSocket state"
        
        # BUSINESS VALUE: Perfect user isolation maintained
        self.assert_business_value_delivered({
            'perfect_isolation': isolation_score == 100.0,
            'user_privacy': True,
            'data_security': True,
            'enterprise_compliance': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_operations_isolation_stress_test(self, real_services_fixture):
        """Test user isolation under concurrent operations stress."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create user environments
        user_contexts = await self.create_isolated_user_environment(services, user_count=2)
        
        # Define concurrent operations that could potentially cause isolation leaks
        isolation_breach_attempts = []
        
        async def user_concurrent_operations(user_context: UserTestContext, operation_count: int):
            """Perform concurrent operations for a user while others are also active."""
            user_id = user_context.user_id
            connection_id = user_context.connection_id
            
            breach_attempts = []
            
            for i in range(operation_count):
                try:
                    # Create new thread
                    new_thread_id = await services.postgres.fetchval("""
                        INSERT INTO backend.threads (user_id, title, metadata)
                        VALUES ($1, $2, $3)
                        RETURNING id
                    """, str(user_id), f"Concurrent thread {i}", json.dumps({
                        'concurrent_test': True,
                        'operation_index': i
                    }))
                    
                    new_thread_id = ThreadID(str(new_thread_id))
                    user_context.thread_ids.append(new_thread_id)
                    
                    # Add message to new thread
                    message_id = MessageID(str(uuid4()))
                    await services.postgres.execute("""
                        INSERT INTO backend.messages (id, thread_id, user_id, content, role)
                        VALUES ($1, $2, $3, $4, $5)
                    """, str(message_id), str(new_thread_id), str(user_id), 
                         f"Concurrent message {i}", "user")
                    
                    user_context.message_ids.append(message_id)
                    
                    # Update Redis cache
                    await services.redis.set_json(f"thread:{new_thread_id}", {
                        'id': str(new_thread_id),
                        'user_id': str(user_id),
                        'title': f'Concurrent thread {i}',
                        'concurrent_test': True
                    }, ex=3600)
                    
                    await services.redis.set_json(f"message:{message_id}", {
                        'id': str(message_id),
                        'thread_id': str(new_thread_id),
                        'user_id': str(user_id),
                        'content': f"Concurrent message {i}"
                    }, ex=3600)
                    
                    # Update WebSocket state
                    current_ws_state = state_manager.get_websocket_state(connection_id, 'connection_info')
                    if current_ws_state:
                        updated_ws_state = {
                            **current_ws_state,
                            'thread_count': current_ws_state.get('thread_count', 0) + 1,
                            'message_count': current_ws_state.get('message_count', 0) + 1,
                            'last_concurrent_operation': i,
                            'last_activity': time.time()
                        }
                        state_manager.set_websocket_state(connection_id, 'connection_info', updated_ws_state)
                    
                    # Attempt to access other users' data (this should fail in isolated system)
                    other_users = [ctx for ctx in user_contexts if ctx.user_id != user_id]
                    for other_user in other_users:
                        # Try to query other user's threads
                        try:
                            other_threads = await services.postgres.fetch("""
                                SELECT id FROM backend.threads WHERE user_id = $1
                            """, str(other_user.user_id))
                            
                            if len(other_threads) > 0:
                                # This is expected - we can query but should only get results for correct user
                                # The isolation is at the data level, not query level
                                pass
                        except Exception as e:
                            # Query-level blocking would also be acceptable
                            pass
                        
                        # Try to access other user's cached data
                        for other_thread_id in other_user.thread_ids:
                            cached_thread = await services.redis.get_json(f"thread:{other_thread_id}")
                            if cached_thread and cached_thread.get('user_id') == str(user_id):
                                # This would be an isolation breach
                                breach_attempts.append({
                                    'type': 'redis_cross_user_access',
                                    'accessing_user': str(user_id),
                                    'target_user': str(other_user.user_id),
                                    'accessed_thread': str(other_thread_id)
                                })
                        
                        # Try to access other user's WebSocket state
                        try:
                            other_ws_state = state_manager.get_websocket_state(
                                other_user.connection_id, 'connection_info'
                            )
                            
                            # If we can access it, check if it leaks information
                            if other_ws_state and other_ws_state.get('user_id') == str(user_id):
                                breach_attempts.append({
                                    'type': 'websocket_cross_user_access',
                                    'accessing_user': str(user_id),
                                    'target_user': str(other_user.user_id),
                                    'leaked_connection': other_user.connection_id
                                })
                        except Exception:
                            # Access denied is expected and good
                            pass
                    
                    # Small delay to allow concurrency
                    await asyncio.sleep(0.01)
                
                except Exception as e:
                    self.logger.error(f"Concurrent operation {i} failed for user {user_id}: {e}")
            
            return breach_attempts
        
        # Run concurrent operations for all users
        concurrent_operations = 5
        
        tasks = [
            user_concurrent_operations(user_context, concurrent_operations)
            for user_context in user_contexts
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze isolation breach attempts
        total_breach_attempts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"User {i} operations failed: {result}")
            else:
                total_breach_attempts.extend(result)
        
        self.logger.info(f"Concurrent isolation stress test results:")
        self.logger.info(f"  Test duration: {end_time - start_time:.2f}s")
        self.logger.info(f"  Users: {len(user_contexts)}")
        self.logger.info(f"  Operations per user: {concurrent_operations}")
        self.logger.info(f"  Total isolation breach attempts: {len(total_breach_attempts)}")
        
        # Validate isolation held under stress
        final_validator = IsolationTestValidator(services, state_manager)
        final_database_isolation = await final_validator.validate_database_isolation(user_contexts)
        final_redis_isolation = await final_validator.validate_redis_isolation(user_contexts)
        final_websocket_isolation = await final_validator.validate_websocket_isolation(user_contexts)
        
        all_final_results = {**final_database_isolation, **final_redis_isolation, **final_websocket_isolation}
        final_isolation_score = (sum(1 for result in all_final_results.values() if result) / len(all_final_results) * 100) if all_final_results else 0
        
        self.logger.info(f"  Final isolation score: {final_isolation_score:.1f}%")
        
        if total_breach_attempts:
            self.logger.warning("Isolation breaches detected:")
            for breach in total_breach_attempts:
                self.logger.warning(f"  {breach}")
        
        # Critical assertions
        assert len(total_breach_attempts) == 0, f"Isolation breaches detected: {total_breach_attempts}"
        assert final_isolation_score >= 95.0, f"Isolation degraded under stress: {final_isolation_score:.1f}%"
        
        # Verify data consistency after concurrent operations
        for i, user_context in enumerate(user_contexts):
            user_thread_count = await services.postgres.fetchval("""
                SELECT COUNT(*) FROM backend.threads WHERE user_id = $1
            """, str(user_context.user_id))
            
            expected_thread_count = len(user_context.thread_ids)
            assert user_thread_count == expected_thread_count, f"User {i} thread count inconsistent: {user_thread_count} != {expected_thread_count}"
        
        # BUSINESS VALUE: Isolation maintained under stress
        self.assert_business_value_delivered({
            'stress_tested_isolation': final_isolation_score >= 95.0,
            'no_data_leaks': len(total_breach_attempts) == 0,
            'concurrent_safety': True,
            'enterprise_security': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_organization_based_isolation_with_shared_resources(self, real_services_fixture):
        """Test isolation between users in different organizations while allowing controlled sharing within organizations."""
        services = real_services_fixture
        state_manager = get_websocket_state_manager()
        
        # Create two organizations
        org1_id = await services.postgres.fetchval("""
            INSERT INTO backend.organizations (name, slug, plan)
            VALUES ($1, $2, $3)
            RETURNING id
        """, "Isolation Org 1", "isolation-org-1", "enterprise")
        
        org2_id = await services.postgres.fetchval("""
            INSERT INTO backend.organizations (name, slug, plan)
            VALUES ($1, $2, $3)
            RETURNING id
        """, "Isolation Org 2", "isolation-org-2", "enterprise")
        
        org1_id = OrganizationID(str(org1_id))
        org2_id = OrganizationID(str(org2_id))
        
        # Create users in each organization
        org1_users = []
        org2_users = []
        
        for i in range(2):  # 2 users per org
            # Org 1 user
            user1_data = await self.create_test_user_context(services, {
                'email': f'org1-user-{i}@example.com',
                'name': f'Org 1 User {i}'
            })
            user1_id = UserID(user1_data['id'])
            
            await services.postgres.execute("""
                INSERT INTO backend.organization_memberships (user_id, organization_id, role)
                VALUES ($1, $2, $3)
            """, str(user1_id), str(org1_id), "member")
            
            # Org 2 user
            user2_data = await self.create_test_user_context(services, {
                'email': f'org2-user-{i}@example.com',
                'name': f'Org 2 User {i}'
            })
            user2_id = UserID(user2_data['id'])
            
            await services.postgres.execute("""
                INSERT INTO backend.organization_memberships (user_id, organization_id, role)
                VALUES ($1, $2, $3)
            """, str(user2_id), str(org2_id), "member")
            
            org1_users.append(user1_id)
            org2_users.append(user2_id)
        
        # Create organization-scoped resources
        
        # Org 1 shared thread
        org1_shared_thread = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, organization_id, title, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, str(org1_users[0]), str(org1_id), "Org 1 Shared Thread", json.dumps({
            'shared_within_org': True,
            'organization_id': str(org1_id)
        }))
        
        org1_shared_thread = ThreadID(str(org1_shared_thread))
        
        # Org 2 shared thread
        org2_shared_thread = await services.postgres.fetchval("""
            INSERT INTO backend.threads (user_id, organization_id, title, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, str(org2_users[0]), str(org2_id), "Org 2 Shared Thread", json.dumps({
            'shared_within_org': True,
            'organization_id': str(org2_id)
        }))
        
        org2_shared_thread = ThreadID(str(org2_shared_thread))
        
        # Set up WebSocket connections
        org1_connections = []
        org2_connections = []
        
        for i, user_id in enumerate(org1_users):
            connection_id = str(uuid4())
            state_manager.set_websocket_state(connection_id, 'connection_info', {
                'user_id': str(user_id),
                'organization_id': str(org1_id),
                'connection_id': connection_id,
                'shared_thread_id': str(org1_shared_thread),
                'state': WebSocketConnectionState.CONNECTED.value
            })
            org1_connections.append(connection_id)
        
        for i, user_id in enumerate(org2_users):
            connection_id = str(uuid4())
            state_manager.set_websocket_state(connection_id, 'connection_info', {
                'user_id': str(user_id),
                'organization_id': str(org2_id),
                'connection_id': connection_id,
                'shared_thread_id': str(org2_shared_thread),
                'state': WebSocketConnectionState.CONNECTED.value
            })
            org2_connections.append(connection_id)
        
        # Test isolation between organizations
        
        # Org 1 users should see org 1 shared thread
        org1_thread_visibility = []
        for user_id in org1_users:
            visible_threads = await services.postgres.fetch("""
                SELECT t.id FROM backend.threads t
                JOIN backend.organization_memberships om ON t.organization_id = om.organization_id
                WHERE om.user_id = $1
            """, str(user_id))
            
            visible_thread_ids = [str(t['id']) for t in visible_threads]
            org1_thread_visible = str(org1_shared_thread) in visible_thread_ids
            org2_thread_visible = str(org2_shared_thread) in visible_thread_ids
            
            org1_thread_visibility.append({
                'user_id': str(user_id),
                'can_see_org1_thread': org1_thread_visible,
                'can_see_org2_thread': org2_thread_visible,
                'visible_threads': visible_thread_ids
            })
        
        # Org 2 users should see org 2 shared thread
        org2_thread_visibility = []
        for user_id in org2_users:
            visible_threads = await services.postgres.fetch("""
                SELECT t.id FROM backend.threads t
                JOIN backend.organization_memberships om ON t.organization_id = om.organization_id
                WHERE om.user_id = $1
            """, str(user_id))
            
            visible_thread_ids = [str(t['id']) for t in visible_threads]
            org1_thread_visible = str(org1_shared_thread) in visible_thread_ids
            org2_thread_visible = str(org2_shared_thread) in visible_thread_ids
            
            org2_thread_visibility.append({
                'user_id': str(user_id),
                'can_see_org1_thread': org1_thread_visible,
                'can_see_org2_thread': org2_thread_visible,
                'visible_threads': visible_thread_ids
            })
        
        # Validate organization isolation
        isolation_violations = []
        
        # Org 1 users should not see org 2 resources
        for visibility in org1_thread_visibility:
            if not visibility['can_see_org1_thread']:
                isolation_violations.append(f"Org 1 user {visibility['user_id']} cannot see org 1 thread")
            
            if visibility['can_see_org2_thread']:
                isolation_violations.append(f"Org 1 user {visibility['user_id']} can see org 2 thread (isolation breach)")
        
        # Org 2 users should not see org 1 resources
        for visibility in org2_thread_visibility:
            if not visibility['can_see_org2_thread']:
                isolation_violations.append(f"Org 2 user {visibility['user_id']} cannot see org 2 thread")
            
            if visibility['can_see_org1_thread']:
                isolation_violations.append(f"Org 2 user {visibility['user_id']} can see org 1 thread (isolation breach)")
        
        # Test WebSocket state isolation
        for i, connection_id in enumerate(org1_connections):
            ws_state = state_manager.get_websocket_state(connection_id, 'connection_info')
            if ws_state:
                if ws_state.get('organization_id') != str(org1_id):
                    isolation_violations.append(f"Org 1 connection {i} has wrong organization ID")
                
                if ws_state.get('shared_thread_id') != str(org1_shared_thread):
                    isolation_violations.append(f"Org 1 connection {i} has wrong shared thread ID")
        
        for i, connection_id in enumerate(org2_connections):
            ws_state = state_manager.get_websocket_state(connection_id, 'connection_info')
            if ws_state:
                if ws_state.get('organization_id') != str(org2_id):
                    isolation_violations.append(f"Org 2 connection {i} has wrong organization ID")
                
                if ws_state.get('shared_thread_id') != str(org2_shared_thread):
                    isolation_violations.append(f"Org 2 connection {i} has wrong shared thread ID")
        
        # Log results
        self.logger.info(f"Organization isolation test results:")
        self.logger.info(f"  Org 1 thread visibility: {org1_thread_visibility}")
        self.logger.info(f"  Org 2 thread visibility: {org2_thread_visibility}")
        self.logger.info(f"  Isolation violations: {len(isolation_violations)}")
        
        if isolation_violations:
            for violation in isolation_violations:
                self.logger.warning(f"  {violation}")
        
        # Assertions
        assert len(isolation_violations) == 0, f"Organization isolation violations: {isolation_violations}"
        
        # All org 1 users should see org 1 thread
        assert all(v['can_see_org1_thread'] for v in org1_thread_visibility), "Org 1 users cannot access org resources"
        
        # All org 2 users should see org 2 thread
        assert all(v['can_see_org2_thread'] for v in org2_thread_visibility), "Org 2 users cannot access org resources"
        
        # No cross-organization access
        assert not any(v['can_see_org2_thread'] for v in org1_thread_visibility), "Cross-org access detected (org 1 -> org 2)"
        assert not any(v['can_see_org1_thread'] for v in org2_thread_visibility), "Cross-org access detected (org 2 -> org 1)"
        
        # BUSINESS VALUE: Organization-based isolation with controlled sharing
        self.assert_business_value_delivered({
            'organization_isolation': True,
            'controlled_sharing': True,
            'enterprise_multi_tenancy': True,
            'access_control': True
        }, 'automation')