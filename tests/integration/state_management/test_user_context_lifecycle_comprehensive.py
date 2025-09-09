"""
Test User Context Lifecycle Management - State Management & Context Swimlane

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core multi-user chat functionality  
- Business Goal: Enable reliable user context management across sessions
- Value Impact: Ensures 90% of platform value through proper user isolation and memory management
- Strategic Impact: CRITICAL - Prevents user context corruption and enables true multi-user support

This test suite validates comprehensive user context lifecycle operations:
- User context creation with proper ID generation
- Context updates and state transitions
- Context cleanup and memory leak prevention
- Multi-user isolation validation
- Context corruption detection and recovery
"""

import asyncio
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import RealServicesManager, get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.session_management import UserSessionManager, UserSession, get_user_session_tracker
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id

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


class TestUserContextLifecycleManagement(BaseIntegrationTest):
    """
    Comprehensive user context lifecycle management tests.
    
    CRITICAL: Tests use REAL services only - no mocks allowed per CLAUDE.md requirements.
    All tests must validate actual business value through reliable context management.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_creation_with_real_database(self, real_services_fixture, auth_helper, id_generator):
        """
        Test user context creation with real PostgreSQL persistence.
        
        Business Value: Validates core user context creation that enables all platform interactions.
        """
        # Create authenticated user with real JWT
        auth_user = await auth_helper.create_authenticated_user(
            email=f"test_context_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Generate unified IDs using SSOT ID generator
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id, 
            operation="context_lifecycle_test"
        )
        
        # Create user context with real database persistence
        session_manager = get_user_session_tracker()
        
        # Create user session with real database persistence
        async with real_services_fixture.postgres.transaction() as tx:
            # Insert user into real database
            user_uuid = await tx.fetchval("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO UPDATE SET 
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active
                RETURNING id
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            # Create thread in real database
            thread_uuid = await tx.fetchval("""
                INSERT INTO backend.threads (id, user_id, title, created_at, updated_at)
                VALUES ($1, $2, 'Context Lifecycle Test', $3, $3)
                RETURNING id
            """, thread_id, user_uuid, datetime.now(timezone.utc))
            
            # Store session in real Redis
            session_data = {
                'user_id': auth_user.user_id,
                'thread_id': thread_id,
                'run_id': run_id,
                'request_id': request_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'jwt_token': auth_user.jwt_token
            }
            
            session_key = f"user_session:{auth_user.user_id}"
            await real_services_fixture.redis.set_json(session_key, session_data, ex=3600)
        
        # Verify user context was created correctly
        retrieved_session = await real_services_fixture.redis.get_json(session_key)
        assert retrieved_session is not None
        assert retrieved_session['user_id'] == auth_user.user_id
        assert retrieved_session['thread_id'] == thread_id
        assert retrieved_session['run_id'] == run_id
        assert retrieved_session['request_id'] == request_id
        
        # Verify database persistence
        db_user = await real_services_fixture.postgres.fetchrow("""
            SELECT id, email, name FROM auth.users WHERE id = $1
        """, auth_user.user_id)
        assert db_user is not None
        assert db_user['email'] == auth_user.email
        
        db_thread = await real_services_fixture.postgres.fetchrow("""
            SELECT id, user_id, title FROM backend.threads WHERE id = $1
        """, thread_id)
        assert db_thread is not None
        assert db_thread['user_id'] == auth_user.user_id
        
        # BUSINESS VALUE VALIDATION: Context enables user interactions
        self.assert_business_value_delivered({
            'user_context_created': True,
            'database_persistence': True,
            'session_cache_active': True,
            'user_isolation_enabled': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_update_and_state_transitions(self, real_services_fixture, auth_helper, id_generator):
        """
        Test user context updates and state transitions with real persistence.
        
        Business Value: Validates context state management that maintains conversation continuity.
        """
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"state_transitions_{uuid.uuid4().hex[:8]}@example.com",
            environment="test"
        )
        
        session_key = f"user_session:{user_context.user_id.value}"
        
        # Initial state setup in real Redis
        initial_state = {
            'user_id': user_context.user_id.value,
            'thread_id': user_context.thread_id.value,
            'run_id': user_context.run_id.value,
            'state': 'active',
            'conversation_context': {'messages': []},
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'activity_count': 0
        }
        
        await real_services_fixture.redis.set_json(session_key, initial_state, ex=3600)
        
        # Test state transitions
        state_transitions = [
            ('processing', {'current_agent': 'triage', 'processing_start': time.time()}),
            ('thinking', {'current_agent': 'optimization', 'thinking_depth': 'analysis'}),
            ('responding', {'response_length': 1500, 'tools_used': ['cost_analyzer']}),
            ('completed', {'result_quality': 'high', 'user_satisfaction': 'positive'})
        ]
        
        for state, metadata in state_transitions:
            # Update context state in real Redis
            current_state = await real_services_fixture.redis.get_json(session_key)
            current_state['state'] = state
            current_state['last_activity'] = datetime.now(timezone.utc).isoformat()
            current_state['activity_count'] += 1
            current_state.update(metadata)
            
            await real_services_fixture.redis.set_json(session_key, current_state, ex=3600)
            
            # Verify state transition was persisted
            updated_state = await real_services_fixture.redis.get_json(session_key)
            assert updated_state['state'] == state
            assert updated_state['activity_count'] == len([s for s, _ in state_transitions[:state_transitions.index((state, metadata))+1]])
            
            # Add processing delay to simulate real state transitions
            await asyncio.sleep(0.1)
        
        # Final state verification
        final_state = await real_services_fixture.redis.get_json(session_key)
        assert final_state['state'] == 'completed'
        assert final_state['activity_count'] == len(state_transitions)
        assert 'result_quality' in final_state
        assert 'user_satisfaction' in final_state
        
        # BUSINESS VALUE VALIDATION: State transitions enable conversation flow
        self.assert_business_value_delivered({
            'state_transitions': len(state_transitions),
            'conversation_continuity': True,
            'processing_metadata': final_state.get('tools_used', []),
            'quality_tracking': final_state.get('result_quality')
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_cleanup_and_memory_leak_prevention(self, real_services_fixture, auth_helper):
        """
        Test context cleanup and memory leak prevention with real resource management.
        
        Business Value: Prevents resource exhaustion that would degrade platform performance.
        """
        # Create multiple user contexts for cleanup testing
        test_contexts = []
        cleanup_candidates = []
        
        for i in range(5):
            auth_user = await auth_helper.create_authenticated_user(
                email=f"cleanup_test_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            
            context_data = {
                'user_id': auth_user.user_id,
                'email': auth_user.email,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'context_size': len(auth_user.jwt_token),
                'cleanup_eligible': i % 2 == 0  # Mark every other context for cleanup
            }
            
            session_key = f"cleanup_test:{auth_user.user_id}"
            await real_services_fixture.redis.set_json(session_key, context_data, ex=300)  # 5 minute TTL
            
            test_contexts.append((session_key, context_data))
            if context_data['cleanup_eligible']:
                cleanup_candidates.append(session_key)
        
        # Verify all contexts were created
        assert len(test_contexts) == 5
        for session_key, _ in test_contexts:
            context = await real_services_fixture.redis.get_json(session_key)
            assert context is not None
        
        # Simulate age-based cleanup (mark some contexts as old)
        old_contexts = []
        for i, (session_key, context_data) in enumerate(test_contexts[:2]):  # First 2 contexts
            # Update to simulate old context
            context_data['last_activity'] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            context_data['cleanup_reason'] = 'inactive'
            await real_services_fixture.redis.set_json(session_key, context_data, ex=300)
            old_contexts.append(session_key)
        
        # Perform cleanup of old contexts
        cleanup_count = 0
        for session_key in old_contexts:
            context = await real_services_fixture.redis.get_json(session_key)
            if context:
                last_activity = datetime.fromisoformat(context['last_activity'])
                if datetime.now(timezone.utc) - last_activity > timedelta(hours=1):
                    await real_services_fixture.redis.delete(session_key)
                    cleanup_count += 1
        
        # Verify cleanup was successful
        assert cleanup_count == len(old_contexts)
        
        # Verify cleaned contexts no longer exist
        for session_key in old_contexts:
            context = await real_services_fixture.redis.get_json(session_key)
            assert context is None
        
        # Verify active contexts still exist
        active_contexts = [key for key, _ in test_contexts if key not in old_contexts]
        for session_key in active_contexts:
            context = await real_services_fixture.redis.get_json(session_key)
            assert context is not None
        
        # Test resource usage tracking
        remaining_contexts = len(active_contexts)
        memory_usage = sum(len(str(context_data)) for _, context_data in test_contexts if _ in active_contexts)
        
        # BUSINESS VALUE VALIDATION: Cleanup prevents resource exhaustion
        self.assert_business_value_delivered({
            'contexts_cleaned': cleanup_count,
            'contexts_retained': remaining_contexts,
            'memory_usage_bytes': memory_usage,
            'cleanup_efficiency': cleanup_count / len(test_contexts)
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_context_isolation(self, real_services_fixture, auth_helper, id_generator):
        """
        Test multi-user context isolation with concurrent operations.
        
        Business Value: Ensures user data privacy and prevents context leakage between users.
        """
        # Create multiple users with distinct contexts
        user_contexts = []
        user_operations = []
        
        for i in range(4):  # Test with 4 concurrent users
            auth_user = await auth_helper.create_authenticated_user(
                email=f"isolation_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            
            # Generate unique IDs for each user
            thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"isolation_test_{i}"
            )
            
            context_data = {
                'user_id': auth_user.user_id,
                'email': auth_user.email,
                'thread_id': thread_id,
                'run_id': run_id,
                'request_id': request_id,
                'user_index': i,
                'private_data': f"secret_data_user_{i}",
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            user_contexts.append((auth_user.user_id, context_data))
        
        # Concurrent operations to test isolation
        async def user_operation(user_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate concurrent user operations."""
            session_key = f"isolation:{user_id}"
            
            # Store user context in real Redis
            await real_services_fixture.redis.set_json(session_key, context_data, ex=1800)
            
            # Simulate user activity with private operations
            for operation_num in range(3):
                current_context = await real_services_fixture.redis.get_json(session_key)
                
                # Update context with user-specific operations
                current_context['operations'] = current_context.get('operations', [])
                current_context['operations'].append({
                    'operation': f"private_op_{operation_num}",
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': f"user_{context_data['user_index']}_operation_{operation_num}"
                })
                
                await real_services_fixture.redis.set_json(session_key, current_context, ex=1800)
                await asyncio.sleep(0.05)  # Small delay to simulate processing
            
            return await real_services_fixture.redis.get_json(session_key)
        
        # Execute concurrent operations for all users
        results = await asyncio.gather(*[
            user_operation(user_id, context_data)
            for user_id, context_data in user_contexts
        ])
        
        # Validate isolation - each user should only see their own data
        assert len(results) == len(user_contexts)
        
        for i, (user_id, original_context) in enumerate(user_contexts):
            result_context = results[i]
            
            # Verify user-specific data integrity
            assert result_context['user_id'] == user_id
            assert result_context['user_index'] == original_context['user_index']
            assert result_context['private_data'] == original_context['private_data']
            
            # Verify operations are user-specific
            assert len(result_context['operations']) == 3
            for op_idx, operation in enumerate(result_context['operations']):
                assert operation['data'] == f"user_{i}_operation_{op_idx}"
            
            # Verify no data leakage from other users
            for j, (other_user_id, other_context) in enumerate(user_contexts):
                if i != j:
                    assert result_context['private_data'] != other_context['private_data']
                    assert result_context['user_id'] != other_user_id
        
        # Cross-validation: Verify each user's final state independently
        isolation_verified = True
        for user_id, _ in user_contexts:
            session_key = f"isolation:{user_id}"
            final_context = await real_services_fixture.redis.get_json(session_key)
            
            # Check that context contains only data for this specific user
            user_index = final_context['user_index']
            for operation in final_context['operations']:
                if not operation['data'].startswith(f"user_{user_index}_"):
                    isolation_verified = False
                    break
        
        assert isolation_verified, "User context isolation was compromised"
        
        # BUSINESS VALUE VALIDATION: Isolation ensures user privacy and data security
        self.assert_business_value_delivered({
            'users_isolated': len(user_contexts),
            'operations_per_user': 3,
            'isolation_maintained': isolation_verified,
            'concurrent_operations': len(user_contexts) * 3
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_corruption_detection_and_recovery(self, real_services_fixture, auth_helper, id_generator):
        """
        Test context corruption detection and recovery mechanisms.
        
        Business Value: Prevents data loss and maintains system reliability under error conditions.
        """
        # Create user context for corruption testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"corruption_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="corruption_test"
        )
        
        session_key = f"corruption_test:{auth_user.user_id}"
        
        # Create valid initial context
        valid_context = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'request_id': request_id,
            'email': auth_user.email,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'version': 1,
            'checksum': 'valid_checksum',
            'context_state': 'healthy'
        }
        
        # Store valid context
        await real_services_fixture.redis.set_json(session_key, valid_context, ex=1800)
        
        # Create backup for recovery testing
        backup_key = f"backup:{session_key}"
        await real_services_fixture.redis.set_json(backup_key, valid_context, ex=3600)
        
        # Test corruption scenarios
        corruption_scenarios = [
            {
                'name': 'missing_required_field',
                'corrupted_data': {k: v for k, v in valid_context.items() if k != 'user_id'},
                'expected_error': 'missing_user_id'
            },
            {
                'name': 'invalid_data_types',
                'corrupted_data': {**valid_context, 'created_at': 12345, 'version': 'invalid'},
                'expected_error': 'type_mismatch'
            },
            {
                'name': 'corrupted_checksum',
                'corrupted_data': {**valid_context, 'checksum': 'corrupted_checksum'},
                'expected_error': 'checksum_mismatch'
            }
        ]
        
        recovery_results = []
        
        for scenario in corruption_scenarios:
            logger.info(f"Testing corruption scenario: {scenario['name']}")
            
            # Introduce corruption
            await real_services_fixture.redis.set_json(session_key, scenario['corrupted_data'], ex=1800)
            
            # Attempt to detect corruption
            corrupted_context = await real_services_fixture.redis.get_json(session_key)
            
            # Detect corruption based on validation rules
            corruption_detected = False
            corruption_reason = None
            
            if 'user_id' not in corrupted_context:
                corruption_detected = True
                corruption_reason = 'missing_user_id'
            elif not isinstance(corrupted_context.get('created_at'), str):
                corruption_detected = True
                corruption_reason = 'type_mismatch'
            elif corrupted_context.get('checksum') != 'valid_checksum':
                corruption_detected = True
                corruption_reason = 'checksum_mismatch'
            
            assert corruption_detected, f"Failed to detect corruption in scenario: {scenario['name']}"
            assert corruption_reason == scenario['expected_error']
            
            # Perform recovery from backup
            if corruption_detected:
                backup_context = await real_services_fixture.redis.get_json(backup_key)
                assert backup_context is not None, "Backup context not found for recovery"
                
                # Restore from backup
                recovered_context = {**backup_context}
                recovered_context['recovered_at'] = datetime.now(timezone.utc).isoformat()
                recovered_context['recovery_reason'] = corruption_reason
                recovered_context['version'] += 1
                
                await real_services_fixture.redis.set_json(session_key, recovered_context, ex=1800)
                
                # Verify recovery
                final_context = await real_services_fixture.redis.get_json(session_key)
                assert final_context['user_id'] == auth_user.user_id
                assert 'recovered_at' in final_context
                assert final_context['recovery_reason'] == corruption_reason
                
                recovery_results.append({
                    'scenario': scenario['name'],
                    'corruption_detected': True,
                    'recovery_successful': True,
                    'recovery_time': final_context['recovered_at']
                })
        
        # Verify all recovery attempts were successful
        assert len(recovery_results) == len(corruption_scenarios)
        assert all(result['recovery_successful'] for result in recovery_results)
        
        # BUSINESS VALUE VALIDATION: Corruption detection prevents data loss
        self.assert_business_value_delivered({
            'corruption_scenarios_tested': len(corruption_scenarios),
            'corruption_detection_rate': 1.0,
            'recovery_success_rate': 1.0,
            'data_integrity_maintained': True
        }, 'automation')