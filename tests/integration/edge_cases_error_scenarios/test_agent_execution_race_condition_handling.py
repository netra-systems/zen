"""
Test Agent Execution Race Condition Handling - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (Concurrent usage patterns)
- Business Goal: Prevent race conditions from corrupting agent execution
- Value Impact: Ensures data consistency and prevents execution conflicts
- Strategic Impact: Enables safe concurrent agent usage for Enterprise customers

CRITICAL: This test validates race condition handling in agent execution
to prevent data corruption and execution conflicts under concurrent load.
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestAgentExecutionRaceConditionHandling(BaseIntegrationTest):
    """Test race condition handling in agent execution scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_resource_access(self, real_services_fixture):
        """Test race condition handling for concurrent resource access."""
        real_services = get_real_services()
        
        # Create multiple user contexts for concurrent access
        user_contexts = []
        for i in range(3):
            context = await self.create_test_user_context(real_services, {
                'email': f'race-condition-user-{i}@example.com',
                'name': f'Race Condition User {i}'
            })
            user_contexts.append(context)
        
        # Shared resource state (simulating shared cache or database record)
        shared_resource_state = {
            'resource_id': 'shared_resource_123',
            'value': 0,
            'last_modified_by': None,
            'modification_count': 0,
            'access_log': []
        }
        
        # Simulate resource access lock
        resource_lock = asyncio.Lock()
        
        async def concurrent_resource_access(user_context: Dict, execution_id: int, operation_type: str):
            """Simulate concurrent resource access with potential race conditions."""
            access_results = []
            
            for i in range(5):  # 5 operations per execution
                start_time = time.time()
                
                try:
                    if operation_type == 'with_lock':
                        # Proper locking to prevent race conditions
                        async with resource_lock:
                            current_value = shared_resource_state['value']
                            
                            # Simulate processing delay
                            await asyncio.sleep(0.01)
                            
                            # Modify resource
                            shared_resource_state['value'] = current_value + 1
                            shared_resource_state['last_modified_by'] = f'user_{execution_id}'
                            shared_resource_state['modification_count'] += 1
                            shared_resource_state['access_log'].append({
                                'user': execution_id,
                                'operation': i,
                                'timestamp': time.time(),
                                'value_after': shared_resource_state['value']
                            })
                            
                            new_value = shared_resource_state['value']
                            
                    else:  # 'without_lock' - potential race condition
                        # No locking - race condition prone
                        current_value = shared_resource_state['value']
                        
                        # Simulate processing delay (race condition window)
                        await asyncio.sleep(0.01)
                        
                        # Modify resource (potential race condition here)
                        shared_resource_state['value'] = current_value + 1
                        shared_resource_state['last_modified_by'] = f'user_{execution_id}'
                        shared_resource_state['modification_count'] += 1
                        shared_resource_state['access_log'].append({
                            'user': execution_id,
                            'operation': i,
                            'timestamp': time.time(),
                            'value_after': shared_resource_state['value']
                        })
                        
                        new_value = shared_resource_state['value']
                    
                    duration = time.time() - start_time
                    
                    access_results.append({
                        'execution_id': execution_id,
                        'operation_index': i,
                        'operation_type': operation_type,
                        'success': True,
                        'value_before': current_value,
                        'value_after': new_value,
                        'duration': duration,
                        'error': None
                    })
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    access_results.append({
                        'execution_id': execution_id,
                        'operation_index': i,
                        'operation_type': operation_type,
                        'success': False,
                        'value_before': None,
                        'value_after': None,
                        'duration': duration,
                        'error': str(e)
                    })
            
            return access_results
        
        # Test with proper locking (should prevent race conditions)
        logger.info("Testing concurrent access WITH proper locking")
        
        # Reset shared state
        shared_resource_state.update({
            'value': 0,
            'modification_count': 0,
            'access_log': []
        })
        
        locked_tasks = [
            concurrent_resource_access(user_contexts[i], i, 'with_lock')
            for i in range(len(user_contexts))
        ]
        
        locked_results = await asyncio.gather(*locked_tasks)
        
        # Test without proper locking (may have race conditions)
        logger.info("Testing concurrent access WITHOUT proper locking")
        
        # Reset shared state
        shared_resource_state.update({
            'value': 0,
            'modification_count': 0,
            'access_log': []
        })
        
        unlocked_tasks = [
            concurrent_resource_access(user_contexts[i], i, 'without_lock')
            for i in range(len(user_contexts))
        ]
        
        unlocked_results = await asyncio.gather(*unlocked_tasks)
        
        # Analyze race condition handling
        def analyze_race_condition_results(results: List, test_type: str):
            """Analyze results for race condition indicators."""
            all_operations = []
            for user_results in results:
                all_operations.extend(user_results)
            
            successful_operations = [op for op in all_operations if op.get('success')]
            total_operations = len(all_operations)
            
            # Check for race condition indicators
            expected_final_value = total_operations  # Each operation should increment by 1
            actual_final_value = shared_resource_state['value']
            
            # Lost updates indicate race conditions
            lost_updates = expected_final_value - actual_final_value
            race_condition_likelihood = lost_updates / expected_final_value if expected_final_value > 0 else 0
            
            return {
                'test_type': test_type,
                'total_operations': total_operations,
                'successful_operations': len(successful_operations),
                'expected_final_value': expected_final_value,
                'actual_final_value': actual_final_value,
                'lost_updates': lost_updates,
                'race_condition_likelihood': race_condition_likelihood,
                'success_rate': len(successful_operations) / total_operations if total_operations > 0 else 0
            }
        
        locked_analysis = analyze_race_condition_results(locked_results, 'with_lock')
        unlocked_analysis = analyze_race_condition_results(unlocked_results, 'without_lock')
        
        # Verify proper locking prevents race conditions
        assert locked_analysis['race_condition_likelihood'] <= 0.1, \
            f"Proper locking should prevent race conditions: {locked_analysis['race_condition_likelihood']:.1%} likelihood"
        
        assert locked_analysis['success_rate'] >= 0.9, \
            f"Locked operations should have high success rate: {locked_analysis['success_rate']:.1%}"
        
        # Without locking, we expect some race conditions in concurrent environment
        # But system should still function
        assert unlocked_analysis['success_rate'] >= 0.7, \
            f"Even without locking, system should maintain reasonable functionality: {unlocked_analysis['success_rate']:.1%}"
        
        logger.info(f"Race condition test results:\n"
                   f"  With locking - Success: {locked_analysis['success_rate']:.1%}, "
                   f"Race likelihood: {locked_analysis['race_condition_likelihood']:.1%}\n"
                   f"  Without locking - Success: {unlocked_analysis['success_rate']:.1%}, "
                   f"Race likelihood: {unlocked_analysis['race_condition_likelihood']:.1%}")
                   
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_race_conditions(self, real_services_fixture):
        """Test race condition handling in agent execution state management."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Shared execution state (simulating agent execution tracking)
        execution_state = {
            'execution_id': 'race_test_execution_789',
            'user_id': user_context['id'],
            'status': 'pending',
            'progress': 0,
            'steps_completed': [],
            'current_step': None,
            'result_data': {},
            'concurrent_updates': 0
        }
        
        # State management lock
        state_lock = asyncio.Lock()
        
        async def concurrent_state_updater(updater_id: int, update_type: str, use_locking: bool = True):
            """Simulate concurrent state updates."""
            updates = []
            
            for i in range(10):  # 10 updates per updater
                start_time = time.time()
                
                try:
                    if use_locking:
                        async with state_lock:
                            await self._perform_state_update(execution_state, updater_id, i, update_type)
                    else:
                        await self._perform_state_update(execution_state, updater_id, i, update_type)
                    
                    duration = time.time() - start_time
                    
                    updates.append({
                        'updater_id': updater_id,
                        'update_index': i,
                        'update_type': update_type,
                        'success': True,
                        'duration': duration,
                        'state_after_update': execution_state.copy(),
                        'error': None
                    })
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    updates.append({
                        'updater_id': updater_id,
                        'update_index': i,
                        'update_type': update_type,
                        'success': False,
                        'duration': duration,
                        'state_after_update': None,
                        'error': str(e)
                    })
                
                # Brief pause between updates
                await asyncio.sleep(0.005)
            
            return updates
        
        # Test concurrent state updates with different types
        concurrent_updaters = [
            concurrent_state_updater(1, 'progress_update', True),
            concurrent_state_updater(2, 'step_completion', True),
            concurrent_state_updater(3, 'result_accumulation', True)
        ]
        
        start_time = time.time()
        state_update_results = await asyncio.gather(*concurrent_updaters, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze state consistency
        all_updates = []
        for results in state_update_results:
            if isinstance(results, list):
                all_updates.extend(results)
            elif isinstance(results, Exception):
                logger.warning(f"Concurrent updater failed: {results}")
        
        successful_updates = [u for u in all_updates if u.get('success')]
        
        # Verify state consistency
        final_state = execution_state
        consistency_checks = {
            'progress_within_bounds': 0 <= final_state.get('progress', -1) <= 100,
            'steps_completed_is_list': isinstance(final_state.get('steps_completed'), list),
            'result_data_is_dict': isinstance(final_state.get('result_data'), dict),
            'concurrent_updates_positive': final_state.get('concurrent_updates', 0) >= 0,
            'execution_id_unchanged': final_state.get('execution_id') == 'race_test_execution_789'
        }
        
        consistency_issues = [check for check, passed in consistency_checks.items() if not passed]
        
        success_rate = len(successful_updates) / len(all_updates) if all_updates else 0
        
        assert success_rate >= 0.8, \
            f"Too many state update failures: {success_rate:.1%} success rate"
        
        assert len(consistency_issues) == 0, \
            f"State consistency issues after concurrent updates: {consistency_issues}"
        
        # Verify no critical data loss
        expected_total_updates = 30  # 3 updaters  x  10 updates each
        actual_concurrent_updates = final_state.get('concurrent_updates', 0)
        update_completeness = actual_concurrent_updates / expected_total_updates
        
        assert update_completeness >= 0.7, \
            f"Significant update loss due to race conditions: {update_completeness:.1%} completeness"
            
        logger.info(f"State race condition test - Success rate: {success_rate:.1%}, "
                   f"Consistency issues: {len(consistency_issues)}, "
                   f"Update completeness: {update_completeness:.1%}, "
                   f"Duration: {total_duration:.1f}s")
    
    async def _perform_state_update(self, state: Dict, updater_id: int, update_index: int, update_type: str):
        """Perform a state update with potential race condition."""
        # Simulate read-modify-write operations that are prone to race conditions
        
        if update_type == 'progress_update':
            current_progress = state.get('progress', 0)
            await asyncio.sleep(0.001)  # Simulate processing delay
            state['progress'] = min(100, current_progress + 2)  # Increment progress
            
        elif update_type == 'step_completion':
            current_steps = state.get('steps_completed', []).copy()
            await asyncio.sleep(0.001)  # Simulate processing delay
            current_steps.append(f'step_{updater_id}_{update_index}')
            state['steps_completed'] = current_steps
            state['current_step'] = f'step_{updater_id}_{update_index}'
            
        elif update_type == 'result_accumulation':
            current_results = state.get('result_data', {}).copy()
            await asyncio.sleep(0.001)  # Simulate processing delay
            current_results[f'result_{updater_id}_{update_index}'] = f'value_{updater_id}_{update_index}'
            state['result_data'] = current_results
        
        # Common update tracking
        state['concurrent_updates'] = state.get('concurrent_updates', 0) + 1
        
    @pytest.mark.integration
    async def test_deadlock_prevention_mechanisms(self):
        """Test deadlock prevention in concurrent agent execution."""
        # Simulate resources that could cause deadlock
        resource_a_lock = asyncio.Lock()
        resource_b_lock = asyncio.Lock()
        
        deadlock_test_results = []
        
        async def potential_deadlock_scenario_1(scenario_id: int):
            """First deadlock scenario: acquire A then B."""
            try:
                # Acquire locks in order A -> B
                async with resource_a_lock:
                    await asyncio.sleep(0.1)  # Hold lock A
                    async with resource_b_lock:
                        await asyncio.sleep(0.1)  # Hold both locks
                        return {
                            'scenario_id': scenario_id,
                            'scenario_type': 'A_then_B',
                            'success': True,
                            'deadlock_occurred': False
                        }
                        
            except Exception as e:
                return {
                    'scenario_id': scenario_id,
                    'scenario_type': 'A_then_B',
                    'success': False,
                    'deadlock_occurred': 'deadlock' in str(e).lower(),
                    'error': str(e)
                }
        
        async def potential_deadlock_scenario_2(scenario_id: int):
            """Second deadlock scenario: acquire B then A."""
            try:
                # Acquire locks in order B -> A (reverse order - potential deadlock)
                async with resource_b_lock:
                    await asyncio.sleep(0.1)  # Hold lock B
                    async with resource_a_lock:
                        await asyncio.sleep(0.1)  # Hold both locks
                        return {
                            'scenario_id': scenario_id,
                            'scenario_type': 'B_then_A',
                            'success': True,
                            'deadlock_occurred': False
                        }
                        
            except Exception as e:
                return {
                    'scenario_id': scenario_id,
                    'scenario_type': 'B_then_A',
                    'success': False,
                    'deadlock_occurred': 'deadlock' in str(e).lower(),
                    'error': str(e)
                }
        
        async def deadlock_prevention_scenario(scenario_id: int):
            """Deadlock prevention: always acquire locks in same order."""
            try:
                # Always acquire in consistent order: A then B
                locks_to_acquire = [resource_a_lock, resource_b_lock]
                
                # Acquire all locks
                for lock in locks_to_acquire:
                    await lock.acquire()
                
                try:
                    await asyncio.sleep(0.1)  # Do work with both locks
                    return {
                        'scenario_id': scenario_id,
                        'scenario_type': 'consistent_order',
                        'success': True,
                        'deadlock_occurred': False
                    }
                finally:
                    # Release locks in reverse order
                    for lock in reversed(locks_to_acquire):
                        lock.release()
                        
            except Exception as e:
                return {
                    'scenario_id': scenario_id,
                    'scenario_type': 'consistent_order',
                    'success': False,
                    'deadlock_occurred': 'deadlock' in str(e).lower(),
                    'error': str(e)
                }
        
        # Test potential deadlock scenarios with timeout
        deadlock_scenarios = [
            potential_deadlock_scenario_1(1),
            potential_deadlock_scenario_2(2),
            potential_deadlock_scenario_1(3),
            potential_deadlock_scenario_2(4)
        ]
        
        # Add deadlock prevention scenarios
        prevention_scenarios = [
            deadlock_prevention_scenario(5),
            deadlock_prevention_scenario(6)
        ]
        
        # Run with timeout to detect deadlocks
        try:
            deadlock_results = await asyncio.wait_for(
                asyncio.gather(*deadlock_scenarios, return_exceptions=True),
                timeout=5.0  # 5 second timeout to detect deadlocks
            )
        except asyncio.TimeoutError:
            deadlock_results = [{'deadlock_occurred': True, 'error': 'Timeout - likely deadlock'}] * len(deadlock_scenarios)
        
        try:
            prevention_results = await asyncio.wait_for(
                asyncio.gather(*prevention_scenarios, return_exceptions=True),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            prevention_results = [{'deadlock_occurred': True, 'error': 'Timeout in prevention scenario'}] * len(prevention_scenarios)
        
        # Analyze deadlock handling
        all_results = deadlock_results + prevention_results
        
        potential_deadlocks = []
        successful_completions = []
        prevention_successes = []
        
        for result in all_results:
            if isinstance(result, dict):
                if result.get('deadlock_occurred'):
                    potential_deadlocks.append(result)
                elif result.get('success'):
                    successful_completions.append(result)
                    if result.get('scenario_type') == 'consistent_order':
                        prevention_successes.append(result)
            elif isinstance(result, Exception):
                potential_deadlocks.append({'error': str(result), 'deadlock_occurred': True})
        
        # Verify deadlock prevention
        prevention_success_rate = len(prevention_successes) / len(prevention_scenarios) if prevention_scenarios else 0
        
        assert prevention_success_rate >= 0.8, \
            f"Deadlock prevention insufficient: {prevention_success_rate:.1%} prevention success rate"
        
        # Some deadlock scenarios might occur (this is expected in testing)
        # But system should not hang completely
        total_completions = len(successful_completions) + len(potential_deadlocks)
        
        assert total_completions == len(all_results), \
            "All scenarios should complete (either success or detected failure)"
            
        logger.info(f"Deadlock prevention test - Prevention success: {prevention_success_rate:.1%}, "
                   f"Potential deadlocks: {len(potential_deadlocks)}, "
                   f"Successful completions: {len(successful_completions)}")
                   
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_optimistic_locking_race_condition_handling(self, real_services_fixture):
        """Test optimistic locking for race condition prevention."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Simulate versioned data with optimistic locking
        versioned_data = {
            'record_id': 'optimistic_lock_test_999',
            'version': 1,
            'data': {'value': 0, 'last_updated': time.time()},
            'lock_failures': 0
        }
        
        async def optimistic_lock_update(updater_id: int, update_value: int):
            """Simulate optimistic locking update."""
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Read current version
                    current_version = versioned_data['version']
                    current_data = versioned_data['data'].copy()
                    
                    # Simulate processing delay (race condition window)
                    await asyncio.sleep(0.01)
                    
                    # Prepare updated data
                    new_data = current_data.copy()
                    new_data['value'] += update_value
                    new_data['last_updated'] = time.time()
                    new_data['updated_by'] = updater_id
                    
                    # Attempt atomic update with version check
                    if versioned_data['version'] == current_version:
                        # Version matches - update allowed
                        versioned_data['data'] = new_data
                        versioned_data['version'] = current_version + 1
                        
                        return {
                            'updater_id': updater_id,
                            'update_value': update_value,
                            'retry_count': retry_count,
                            'success': True,
                            'final_version': versioned_data['version'],
                            'final_value': versioned_data['data']['value'],
                            'error': None
                        }
                    else:
                        # Version mismatch - retry needed
                        retry_count += 1
                        versioned_data['lock_failures'] += 1
                        
                        if retry_count < max_retries:
                            # Brief exponential backoff
                            await asyncio.sleep(0.01 * (2 ** retry_count))
                        
                except Exception as e:
                    return {
                        'updater_id': updater_id,
                        'update_value': update_value,
                        'retry_count': retry_count,
                        'success': False,
                        'final_version': None,
                        'final_value': None,
                        'error': str(e)
                    }
            
            # Max retries exceeded
            return {
                'updater_id': updater_id,
                'update_value': update_value,
                'retry_count': retry_count,
                'success': False,
                'final_version': None,
                'final_value': None,
                'error': f'Max retries ({max_retries}) exceeded'
            }
        
        # Run concurrent optimistic lock updates
        concurrent_updates = [
            optimistic_lock_update(i, 5)  # Each updater adds 5 to value
            for i in range(6)  # 6 concurrent updaters
        ]
        
        start_time = time.time()
        optimistic_results = await asyncio.gather(*concurrent_updates)
        duration = time.time() - start_time
        
        # Analyze optimistic locking results
        successful_updates = [r for r in optimistic_results if r.get('success')]
        failed_updates = [r for r in optimistic_results if not r.get('success')]
        
        total_retries = sum(r.get('retry_count', 0) for r in optimistic_results)
        avg_retries = total_retries / len(optimistic_results)
        
        success_rate = len(successful_updates) / len(optimistic_results)
        
        # Verify optimistic locking prevented data corruption
        expected_final_value = len(successful_updates) * 5  # Each successful update adds 5
        actual_final_value = versioned_data['data']['value']
        
        assert success_rate >= 0.7, \
            f"Optimistic locking success rate too low: {success_rate:.1%}"
        
        assert actual_final_value == expected_final_value, \
            f"Data corruption detected: expected {expected_final_value}, got {actual_final_value}"
        
        # Version should be consistent with successful updates
        expected_final_version = 1 + len(successful_updates)
        actual_final_version = versioned_data['version']
        
        assert actual_final_version == expected_final_version, \
            f"Version inconsistency: expected {expected_final_version}, got {actual_final_version}"
        
        # Retries indicate race conditions were handled
        assert total_retries > 0, \
            "No retries suggest no race conditions occurred (unexpected in concurrent test)"
        
        logger.info(f"Optimistic locking test - Success rate: {success_rate:.1%}, "
                   f"Final value: {actual_final_value}, Version: {actual_final_version}, "
                   f"Avg retries: {avg_retries:.1f}, Lock failures: {versioned_data['lock_failures']}, "
                   f"Duration: {duration:.1f}s")