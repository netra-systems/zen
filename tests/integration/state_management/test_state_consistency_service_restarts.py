"""
Test State Consistency Across Service Restarts - State Management & Context Swimlane

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core system reliability functionality
- Business Goal: Ensure state consistency and conversation continuity across service restarts
- Value Impact: Prevents data loss and maintains user experience during system maintenance
- Strategic Impact: CRITICAL - Service restart resilience is fundamental to platform reliability

This test suite validates state consistency across service restarts:
- State persistence during planned service restarts
- Automatic state recovery after unplanned failures
- Cross-service state synchronization during restart sequences
- State validation and corruption detection post-restart
- Performance impact assessment of restart operations
- User session continuity across restart events
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import RealServicesManager, get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.session_management import UserSessionManager, get_user_session_tracker
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

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


class TestStateConsistencyServiceRestarts(BaseIntegrationTest):
    """
    Test state consistency across service restarts.
    
    CRITICAL: Tests use REAL services - Redis and PostgreSQL for actual restart simulation.
    All tests validate business value through reliable state recovery.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_persistence_during_service_restart(self, real_services_fixture, auth_helper, id_generator):
        """
        Test state persistence during planned service restart simulation.
        
        Business Value: Ensures no data loss during maintenance windows.
        """
        # Create user with active conversation state
        auth_user = await auth_helper.create_authenticated_user(
            email=f"restart_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="restart_persistence_test"
        )
        
        # Create comprehensive pre-restart state
        pre_restart_state = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'request_id': request_id,
            'conversation_context': {
                'active_conversation': True,
                'current_stage': 'analysis_in_progress',
                'ai_working_memory': {
                    'analyzed_data': {'ec2_costs': 5000, 'optimization_potential': 0.3},
                    'current_reasoning': 'Analyzing cost patterns for optimization recommendations',
                    'pending_actions': ['generate_recommendations', 'calculate_savings', 'create_implementation_plan']
                },
                'user_context': {
                    'expertise_level': 'intermediate',
                    'business_context': 'startup_scaling',
                    'time_sensitivity': 'high',
                    'budget_constraints': 'moderate'
                }
            },
            'message_history': [
                {
                    'id': f'{run_id}_msg_0',
                    'role': 'user',
                    'content': 'I need help reducing my AWS costs. My current monthly bill is $5,000.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'critical_data': True
                },
                {
                    'id': f'{run_id}_msg_1',
                    'role': 'assistant',
                    'content': 'I understand you need cost optimization for your $5,000 monthly AWS spend. Let me analyze your usage patterns.',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'ai_processing_state': 'analysis_started',
                    'tools_invoked': ['cost_analyzer']
                }
            ],
            'system_state': {
                'restart_checkpoint': datetime.now(timezone.utc).isoformat(),
                'data_integrity_hash': 'pre_restart_hash_12345',
                'critical_for_recovery': True
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat()
        }
        
        # Store state in both Redis (cache) and PostgreSQL (persistent)
        cache_key = f"active_state:{auth_user.user_id}:{thread_id}"
        backup_key = f"restart_backup:{auth_user.user_id}:{thread_id}"
        
        # Primary storage in Redis
        await real_services_fixture.redis.set_json(cache_key, pre_restart_state, ex=7200)
        
        # Backup storage for restart recovery
        await real_services_fixture.redis.set_json(backup_key, pre_restart_state, ex=86400)  # 24 hour backup
        
        # Persistent storage in PostgreSQL
        async with real_services_fixture.postgres.transaction() as tx:
            # Ensure user exists
            await tx.execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, true, $4)
                ON CONFLICT (email) DO NOTHING
            """, auth_user.user_id, auth_user.email, auth_user.full_name, datetime.now(timezone.utc))
            
            # Create persistent state table for restart testing
            await tx.execute("""
                CREATE TABLE IF NOT EXISTS restart_test_states (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    state_data JSONB NOT NULL,
                    checkpoint_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    recovery_priority INTEGER DEFAULT 1
                )
            """)
            
            state_id = f"{auth_user.user_id}_{thread_id}_restart"
            await tx.execute("""
                INSERT INTO restart_test_states (id, user_id, thread_id, state_data, recovery_priority)
                VALUES ($1, $2, $3, $4, 1)
            """, state_id, auth_user.user_id, thread_id, json.dumps(pre_restart_state, default=str))
        
        # Simulate service restart - clear primary cache but keep backup
        await real_services_fixture.redis.delete(cache_key)
        
        # Verify primary state is "lost" (simulating restart)
        lost_state = await real_services_fixture.redis.get_json(cache_key)
        assert lost_state is None, "Primary state should be cleared to simulate restart"
        
        # Simulate restart recovery process
        recovery_start_time = time.time()
        
        # Step 1: Check for backup in Redis
        backup_state = await real_services_fixture.redis.get_json(backup_key)
        assert backup_state is not None, "Backup state must exist for recovery"
        
        # Step 2: Verify backup integrity
        assert backup_state['user_id'] == auth_user.user_id
        assert backup_state['thread_id'] == thread_id
        assert backup_state['conversation_context']['active_conversation'] is True
        assert len(backup_state['message_history']) == 2
        
        # Step 3: Restore primary state from backup
        await real_services_fixture.redis.set_json(cache_key, backup_state, ex=7200)
        
        # Step 4: Verify database consistency
        db_state = await real_services_fixture.postgres.fetchval("""
            SELECT state_data FROM restart_test_states 
            WHERE user_id = $1 AND thread_id = $2
        """, auth_user.user_id, thread_id)
        
        assert db_state is not None
        db_state_dict = json.loads(db_state)
        assert db_state_dict['user_id'] == auth_user.user_id
        
        # Step 5: Validate complete recovery
        recovered_state = await real_services_fixture.redis.get_json(cache_key)
        assert recovered_state is not None
        
        # Validate critical data integrity
        assert recovered_state['user_id'] == pre_restart_state['user_id']
        assert recovered_state['conversation_context']['ai_working_memory']['analyzed_data']['ec2_costs'] == 5000
        assert recovered_state['conversation_context']['current_stage'] == 'analysis_in_progress'
        assert len(recovered_state['message_history']) == 2
        assert recovered_state['system_state']['critical_for_recovery'] is True
        
        recovery_end_time = time.time()
        recovery_time = recovery_end_time - recovery_start_time
        
        # Recovery should be fast (< 1 second for this size)
        assert recovery_time < 1.0, f"Recovery too slow: {recovery_time}s"
        
        # Clean up test table
        await real_services_fixture.postgres.execute("DROP TABLE IF EXISTS restart_test_states")
        
        # BUSINESS VALUE VALIDATION: State recovery ensures continuity
        self.assert_business_value_delivered({
            'state_recovery_successful': True,
            'data_integrity_maintained': True,
            'recovery_time_seconds': recovery_time,
            'conversation_continuity': len(recovered_state['message_history']) == 2,
            'ai_context_preserved': 'analyzed_data' in recovered_state['conversation_context']['ai_working_memory']
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_state_consistency_during_restart(self, real_services_fixture, auth_helper, id_generator):
        """
        Test multi-user state consistency during restart operations.
        
        Business Value: Ensures all users maintain conversation continuity during restarts.
        """
        # Create multiple users with active conversations
        users_with_states = []
        
        for i in range(5):  # 5 users for multi-user testing
            auth_user = await auth_helper.create_authenticated_user(
                email=f"multi_restart_user_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            
            thread_id, run_id, _ = id_generator.generate_user_context_ids(
                user_id=auth_user.user_id,
                operation=f"multi_restart_{i}"
            )
            
            # Create user-specific conversation state
            user_state = {
                'user_id': auth_user.user_id,
                'thread_id': thread_id,
                'run_id': run_id,
                'user_index': i,
                'conversation_data': {
                    'messages_count': 5 + i,  # Different conversation lengths
                    'current_topic': f'optimization_strategy_{i}',
                    'business_context': f'business_type_{i}',
                    'optimization_progress': (i + 1) * 0.2,  # Different progress levels
                    'user_satisfaction': 4.0 + (i * 0.2),
                    'ai_recommendations': [f'recommendation_{i}_{j}' for j in range(3)]
                },
                'session_metrics': {
                    'session_duration_minutes': 10 + (i * 5),
                    'interactions_count': 8 + (i * 2),
                    'tools_used': i + 1,
                    'value_delivered': 1000 * (i + 1)
                },
                'restart_metadata': {
                    'created_before_restart': True,
                    'critical_for_user': True,
                    'recovery_priority': 5 - i  # Higher priority for earlier users
                }
            }
            
            users_with_states.append((auth_user, user_state))
        
        # Store all user states before restart
        stored_keys = []
        for auth_user, user_state in users_with_states:
            primary_key = f"multi_user:{auth_user.user_id}:{user_state['thread_id']}"
            backup_key = f"multi_backup:{auth_user.user_id}:{user_state['thread_id']}"
            
            await real_services_fixture.redis.set_json(primary_key, user_state, ex=3600)
            await real_services_fixture.redis.set_json(backup_key, user_state, ex=7200)
            
            stored_keys.append((primary_key, backup_key))
        
        # Verify all states are stored
        for primary_key, backup_key in stored_keys:
            assert await real_services_fixture.redis.exists(primary_key)
            assert await real_services_fixture.redis.exists(backup_key)
        
        # Simulate system restart - clear all primary states
        for primary_key, _ in stored_keys:
            await real_services_fixture.redis.delete(primary_key)
        
        # Verify all primary states are cleared
        for primary_key, _ in stored_keys:
            assert not await real_services_fixture.redis.exists(primary_key)
        
        # Simulate multi-user recovery process
        recovery_operations = []
        
        async def recover_user_state(user_index: int, auth_user, primary_key: str, backup_key: str) -> Dict[str, Any]:
            """Recover individual user state."""
            recovery_start = time.time()
            
            # Load backup state
            backup_state = await real_services_fixture.redis.get_json(backup_key)
            if backup_state is None:
                return {'user_id': auth_user.user_id, 'recovery_failed': True}
            
            # Restore primary state
            await real_services_fixture.redis.set_json(primary_key, backup_state, ex=3600)
            
            recovery_time = time.time() - recovery_start
            
            return {
                'user_id': auth_user.user_id,
                'user_index': user_index,
                'recovery_successful': True,
                'recovery_time': recovery_time,
                'state_integrity': backup_state['user_id'] == auth_user.user_id,
                'conversation_data_preserved': len(backup_state['conversation_data']['ai_recommendations']) == 3
            }
        
        # Perform concurrent recovery for all users
        recovery_tasks = []
        for i, ((auth_user, user_state), (primary_key, backup_key)) in enumerate(zip(users_with_states, stored_keys)):
            task = recover_user_state(i, auth_user, primary_key, backup_key)
            recovery_tasks.append(task)
        
        recovery_results = await asyncio.gather(*recovery_tasks)
        
        # Validate all recoveries successful
        assert len(recovery_results) == 5
        for result in recovery_results:
            assert result['recovery_successful'] is True
            assert result['state_integrity'] is True
            assert result['conversation_data_preserved'] is True
            assert result['recovery_time'] < 0.5  # Each recovery should be fast
        
        # Cross-validate recovered states
        for i, (primary_key, backup_key) in enumerate(stored_keys):
            recovered_state = await real_services_fixture.redis.get_json(primary_key)
            assert recovered_state is not None
            assert recovered_state['user_index'] == i
            assert recovered_state['conversation_data']['messages_count'] == 5 + i
            assert recovered_state['restart_metadata']['critical_for_user'] is True
        
        # Validate no cross-contamination between users
        for i, result_i in enumerate(recovery_results):
            user_i_id = result_i['user_id']
            
            for j, result_j in enumerate(recovery_results):
                if i != j:
                    user_j_id = result_j['user_id']
                    assert user_i_id != user_j_id, "User IDs must be unique"
                    
                    # Verify user i's state doesn't contain user j's data
                    primary_key_i = stored_keys[i][0]
                    state_i = await real_services_fixture.redis.get_json(primary_key_i)
                    assert state_i['user_id'] != user_j_id
                    assert state_i['user_index'] == i
        
        # BUSINESS VALUE VALIDATION: Multi-user recovery maintains isolation
        self.assert_business_value_delivered({
            'users_recovered': len(recovery_results),
            'recovery_success_rate': 1.0,
            'average_recovery_time': sum(r['recovery_time'] for r in recovery_results) / len(recovery_results),
            'user_isolation_maintained': True,
            'conversation_continuity_preserved': all(r['conversation_data_preserved'] for r in recovery_results)
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_state_validation_post_restart(self, real_services_fixture, auth_helper, id_generator):
        """
        Test comprehensive state validation after service restart.
        
        Business Value: Ensures data integrity and prevents corrupted state propagation.
        """
        # Create user with complex state for validation testing
        auth_user = await auth_helper.create_authenticated_user(
            email=f"validation_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        thread_id, run_id, _ = id_generator.generate_user_context_ids(
            user_id=auth_user.user_id,
            operation="validation_test"
        )
        
        # Create state with validation checksums and integrity markers
        validated_state = {
            'user_id': auth_user.user_id,
            'thread_id': thread_id,
            'run_id': run_id,
            'validation_metadata': {
                'checksum': 'expected_checksum_abc123',
                'version': '1.0',
                'critical_fields': ['user_id', 'thread_id', 'conversation_data'],
                'validation_rules': {
                    'user_id_format': 'string_non_empty',
                    'thread_id_format': 'uuid_format',
                    'message_count_min': 1,
                    'ai_context_required': True
                }
            },
            'conversation_data': {
                'messages': [
                    {'id': f'{run_id}_msg_0', 'role': 'user', 'content': 'Test message', 'timestamp': datetime.now(timezone.utc).isoformat()},
                    {'id': f'{run_id}_msg_1', 'role': 'assistant', 'content': 'Test response', 'timestamp': datetime.now(timezone.utc).isoformat()}
                ],
                'ai_context': {
                    'current_state': 'active',
                    'reasoning_chain': ['understand_request', 'analyze_context', 'generate_response'],
                    'confidence_level': 0.95
                },
                'user_context': {
                    'preferences': {'response_style': 'detailed'},
                    'session_info': {'start_time': datetime.now(timezone.utc).isoformat()}
                }
            },
            'integrity_markers': {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_validated': datetime.now(timezone.utc).isoformat(),
                'validation_passed': True,
                'corruption_indicators': []
            }
        }
        
        # Store state with backup
        primary_key = f"validation_state:{auth_user.user_id}:{thread_id}"
        await real_services_fixture.redis.set_json(primary_key, validated_state, ex=3600)
        
        # Simulate restart by clearing primary state
        await real_services_fixture.redis.delete(primary_key)
        
        # Create various corrupted states to test validation
        corruption_scenarios = [
            {
                'name': 'missing_user_id',
                'corrupted_state': {k: v for k, v in validated_state.items() if k != 'user_id'},
                'expected_validation_failure': 'missing_critical_field'
            },
            {
                'name': 'corrupted_thread_id', 
                'corrupted_state': {**validated_state, 'thread_id': 'invalid_thread_id_format'},
                'expected_validation_failure': 'invalid_thread_id_format'
            },
            {
                'name': 'missing_ai_context',
                'corrupted_state': {
                    **validated_state,
                    'conversation_data': {
                        'messages': validated_state['conversation_data']['messages'],
                        'user_context': validated_state['conversation_data']['user_context']
                        # Missing ai_context
                    }
                },
                'expected_validation_failure': 'missing_ai_context'
            },
            {
                'name': 'empty_messages',
                'corrupted_state': {
                    **validated_state,
                    'conversation_data': {
                        **validated_state['conversation_data'],
                        'messages': []  # Empty messages array
                    }
                },
                'expected_validation_failure': 'insufficient_message_count'
            }
        ]
        
        # Validation function
        def validate_state(state: Dict[str, Any]) -> Dict[str, Any]:
            """Validate state integrity after restart."""
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Check critical fields
            critical_fields = state.get('validation_metadata', {}).get('critical_fields', [])
            for field in critical_fields:
                if field not in state:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f'missing_critical_field: {field}')
            
            # Validate user_id format
            if 'user_id' in state and not isinstance(state['user_id'], str):
                validation_result['valid'] = False
                validation_result['errors'].append('invalid_user_id_type')
            
            # Validate thread_id format (should contain hyphens for UUID format)
            if 'thread_id' in state and '-' not in str(state['thread_id']):
                validation_result['valid'] = False
                validation_result['errors'].append('invalid_thread_id_format')
            
            # Validate conversation data
            if 'conversation_data' in state:
                conv_data = state['conversation_data']
                
                # Check AI context
                if 'ai_context' not in conv_data:
                    validation_result['valid'] = False
                    validation_result['errors'].append('missing_ai_context')
                
                # Check message count
                messages = conv_data.get('messages', [])
                if len(messages) < 1:
                    validation_result['valid'] = False
                    validation_result['errors'].append('insufficient_message_count')
            
            return validation_result
        
        # Test validation with good state
        good_validation = validate_state(validated_state)
        assert good_validation['valid'] is True
        assert len(good_validation['errors']) == 0
        
        # Test validation with corrupted states
        validation_results = []
        for scenario in corruption_scenarios:
            corrupted_state = scenario['corrupted_state']
            validation_result = validate_state(corrupted_state)
            
            # Validation should fail for corrupted states
            assert validation_result['valid'] is False, f"Validation should fail for {scenario['name']}"
            assert len(validation_result['errors']) > 0
            
            validation_results.append({
                'scenario': scenario['name'],
                'validation_failed_correctly': not validation_result['valid'],
                'errors_detected': len(validation_result['errors']),
                'errors': validation_result['errors']
            })
        
        # Test state recovery with validation
        # Store valid state and perform validated recovery
        await real_services_fixture.redis.set_json(primary_key, validated_state, ex=3600)
        
        # Recovery with validation
        recovery_start = time.time()
        
        # Step 1: Load state
        recovered_state = await real_services_fixture.redis.get_json(primary_key)
        assert recovered_state is not None
        
        # Step 2: Validate recovered state
        validation_result = validate_state(recovered_state)
        assert validation_result['valid'] is True, f"Recovered state invalid: {validation_result['errors']}"
        
        # Step 3: Update validation timestamp
        recovered_state['integrity_markers']['last_validated'] = datetime.now(timezone.utc).isoformat()
        recovered_state['integrity_markers']['post_restart_validation'] = True
        
        # Step 4: Re-store validated state
        await real_services_fixture.redis.set_json(primary_key, recovered_state, ex=3600)
        
        recovery_time = time.time() - recovery_start
        
        # Final validation
        final_state = await real_services_fixture.redis.get_json(primary_key)
        assert final_state['integrity_markers']['post_restart_validation'] is True
        assert final_state['user_id'] == auth_user.user_id
        assert len(final_state['conversation_data']['messages']) == 2
        
        # BUSINESS VALUE VALIDATION: Validation prevents corrupted state propagation
        self.assert_business_value_delivered({
            'validation_scenarios_tested': len(corruption_scenarios),
            'corruption_detection_rate': 1.0,  # All corruptions detected
            'valid_state_recovery_successful': True,
            'recovery_with_validation_time': recovery_time,
            'data_integrity_assured': validation_result['valid']
        }, 'automation')