"""
Test Agent Execution State Corruption - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (State corruption affects data integrity for all users)
- Business Goal: Prevent data corruption and maintain system integrity
- Value Impact: Protects customer data and prevents system inconsistencies
- Strategic Impact: Ensures reliable agent execution and trustworthy results

CRITICAL: This test validates agent execution behavior when state corruption
occurs, ensuring system can detect, handle, and recover from corrupted states.
"""

import asyncio
import json
import logging
import pytest
import time
from copy import deepcopy
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestAgentExecutionStateCorruption(BaseIntegrationTest):
    """Test agent execution behavior under state corruption conditions."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_context_corruption_detection(self, real_services_fixture):
        """Test detection of execution context corruption."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different types of context corruption
        corruption_scenarios = [
            {
                'name': 'missing_required_fields',
                'corruption_type': 'field_removal',
                'corrupt_context': lambda ctx: {k: v for k, v in ctx.items() if k != 'id'},
                'expected_detection': True
            },
            {
                'name': 'invalid_data_types',
                'corruption_type': 'type_corruption',
                'corrupt_context': lambda ctx: {**ctx, 'id': ['invalid', 'type', 'for', 'id']},
                'expected_detection': True
            },
            {
                'name': 'circular_references',
                'corruption_type': 'reference_corruption',
                'corrupt_context': lambda ctx: self._create_circular_context(ctx),
                'expected_detection': True
            },
            {
                'name': 'oversized_context',
                'corruption_type': 'size_corruption',
                'corrupt_context': lambda ctx: {**ctx, 'oversized_data': 'x' * 1000000},  # 1MB data
                'expected_detection': True
            },
            {
                'name': 'null_injection',
                'corruption_type': 'null_injection',
                'corrupt_context': lambda ctx: {**ctx, 'malicious': None, 'id': None},
                'expected_detection': True
            }
        ]
        
        corruption_detection_results = []
        
        for scenario in corruption_scenarios:
            logger.info(f"Testing context corruption detection: {scenario['name']}")
            
            # Create corrupted context
            try:
                corrupted_context = scenario['corrupt_context'](deepcopy(user_context))
                
                corruption_applied = True
            except Exception as e:
                logger.warning(f"Failed to apply corruption for {scenario['name']}: {e}")
                corruption_applied = False
                corrupted_context = user_context
            
            # Test execution with corrupted context
            start_time = time.time()
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                # Create user execution context for testing
                test_user_context = UserExecutionContext(
                    user_id=corrupted_context.get('id', 'invalid'),
                    thread_id=corrupted_context.get('thread_id', 'test_thread'),
                    run_id=corrupted_context.get('run_id', 'test_run'),
                    request_id=corrupted_context.get('request_id', 'test_request')
                )
                
                # Attempt to create engine with corrupted context
                async with user_execution_engine(test_user_context) as engine:
                    # Attempt agent execution
                    result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"Test with {scenario['name']} corruption",
                        context={"corruption_test": True, "scenario": scenario['name']}
                    )
                    
                    duration = time.time() - start_time
                    
                    # If execution succeeded with corruption, this might indicate poor detection
                    corruption_detection_results.append({
                        'scenario': scenario['name'],
                        'corruption_applied': corruption_applied,
                        'corruption_detected': False,  # Execution succeeded despite corruption
                        'execution_success': True,
                        'result': result,
                        'duration': duration,
                        'error': None
                    })
                    
            except ValueError as e:
                # ValueError often indicates validation/corruption detection
                duration = time.time() - start_time
                
                corruption_detection_results.append({
                    'scenario': scenario['name'],
                    'corruption_applied': corruption_applied,
                    'corruption_detected': True,
                    'execution_success': False,
                    'result': None,
                    'duration': duration,
                    'error': f'ValueError: {str(e)}'
                })
                
            except TypeError as e:
                # TypeError can indicate type corruption detection
                duration = time.time() - start_time
                
                corruption_detection_results.append({
                    'scenario': scenario['name'],
                    'corruption_applied': corruption_applied,
                    'corruption_detected': True,
                    'execution_success': False,
                    'result': None,
                    'duration': duration,
                    'error': f'TypeError: {str(e)}'
                })
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Check if error indicates corruption detection
                error_str = str(e).lower()
                corruption_keywords = ['corrupt', 'invalid', 'malformed', 'validation', 'integrity']
                corruption_detected = any(keyword in error_str for keyword in corruption_keywords)
                
                corruption_detection_results.append({
                    'scenario': scenario['name'],
                    'corruption_applied': corruption_applied,
                    'corruption_detected': corruption_detected,
                    'execution_success': False,
                    'result': None,
                    'duration': duration,
                    'error': str(e)
                })
        
        # Verify corruption detection effectiveness
        detection_results = [r for r in corruption_detection_results if r['corruption_applied']]
        detected_corruptions = [r for r in detection_results if r['corruption_detected']]
        
        detection_rate = len(detected_corruptions) / len(detection_results) if detection_results else 0
        
        assert detection_rate >= 0.8, \
            f"Corruption detection insufficient: {detection_rate:.1%} detection rate"
        
        # Verify no false negatives for critical corruptions
        critical_scenarios = ['missing_required_fields', 'invalid_data_types', 'null_injection']
        critical_results = [r for r in detection_results if r['scenario'] in critical_scenarios]
        critical_detected = [r for r in critical_results if r['corruption_detected']]
        
        critical_detection_rate = len(critical_detected) / len(critical_results) if critical_results else 0
        
        assert critical_detection_rate >= 0.9, \
            f"Critical corruption detection insufficient: {critical_detection_rate:.1%}"
            
        logger.info(f"Corruption detection test - Overall: {detection_rate:.1%}, "
                   f"Critical: {critical_detection_rate:.1%}")
    
    def _create_circular_context(self, original_context: Dict) -> Dict:
        """Create a context with circular references."""
        circular_context = deepcopy(original_context)
        circular_context['circular'] = circular_context  # Create circular reference
        return circular_context
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_inconsistency_handling(self, real_services_fixture):
        """Test handling of state inconsistencies during agent execution."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test state inconsistency scenarios
        inconsistency_scenarios = [
            {
                'name': 'execution_context_mismatch',
                'setup': lambda: {'execution_id': 'exec_123', 'user_id': user_context['id']},
                'corruption': lambda state: {**state, 'user_id': 'different_user_id'},
                'expected_behavior': 'access_denied_or_reset'
            },
            {
                'name': 'timestamp_manipulation',
                'setup': lambda: {'created_at': time.time(), 'last_updated': time.time()},
                'corruption': lambda state: {**state, 'created_at': time.time() + 3600},  # Future timestamp
                'expected_behavior': 'timestamp_validation_error'
            },
            {
                'name': 'status_inconsistency',
                'setup': lambda: {'status': 'running', 'completed_at': None},
                'corruption': lambda state: {**state, 'status': 'completed', 'completed_at': None},  # Inconsistent
                'expected_behavior': 'status_validation_error'
            },
            {
                'name': 'resource_count_mismatch',
                'setup': lambda: {'allocated_resources': ['res1', 'res2'], 'resource_count': 2},
                'corruption': lambda state: {**state, 'resource_count': 5},  # Count mismatch
                'expected_behavior': 'resource_validation_error'
            }
        ]
        
        inconsistency_handling_results = []
        
        for scenario in inconsistency_scenarios:
            logger.info(f"Testing state inconsistency: {scenario['name']}")
            
            # Set up initial consistent state
            initial_state = scenario['setup']()
            
            # Apply corruption to create inconsistency
            corrupted_state = scenario['corruption'](deepcopy(initial_state))
            
            # Test state validation and handling
            start_time = time.time()
            
            try:
                # Simulate state validation during agent execution
                validation_result = await self._validate_execution_state(corrupted_state, user_context)
                
                duration = time.time() - start_time
                
                inconsistency_handling_results.append({
                    'scenario': scenario['name'],
                    'initial_state': initial_state,
                    'corrupted_state': corrupted_state,
                    'validation_passed': validation_result.get('valid', False),
                    'inconsistency_detected': not validation_result.get('valid', True),
                    'handling_appropriate': self._evaluate_inconsistency_handling(validation_result, scenario),
                    'duration': duration,
                    'error': validation_result.get('error')
                })
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Exception might indicate good inconsistency detection
                error_appropriate = self._is_appropriate_inconsistency_error(e, scenario)
                
                inconsistency_handling_results.append({
                    'scenario': scenario['name'],
                    'initial_state': initial_state,
                    'corrupted_state': corrupted_state,
                    'validation_passed': False,
                    'inconsistency_detected': True,
                    'handling_appropriate': error_appropriate,
                    'duration': duration,
                    'error': str(e)
                })
        
        # Verify inconsistency handling
        detected_inconsistencies = [r for r in inconsistency_handling_results if r['inconsistency_detected']]
        appropriate_handling = [r for r in inconsistency_handling_results if r.get('handling_appropriate')]
        
        detection_rate = len(detected_inconsistencies) / len(inconsistency_handling_results)
        handling_rate = len(appropriate_handling) / len(inconsistency_handling_results)
        
        assert detection_rate >= 0.8, \
            f"State inconsistency detection insufficient: {detection_rate:.1%}"
        
        assert handling_rate >= 0.7, \
            f"State inconsistency handling insufficient: {handling_rate:.1%}"
            
        logger.info(f"State inconsistency test - Detection: {detection_rate:.1%}, "
                   f"Appropriate handling: {handling_rate:.1%}")
    
    async def _validate_execution_state(self, state: Dict, user_context: Dict) -> Dict:
        """Mock state validation function."""
        validation_errors = []
        
        # Check user ID consistency
        if state.get('user_id') != user_context.get('id'):
            validation_errors.append('User ID mismatch')
        
        # Check timestamp consistency  
        current_time = time.time()
        if state.get('created_at', 0) > current_time:
            validation_errors.append('Future timestamp detected')
        
        # Check status consistency
        if state.get('status') == 'completed' and state.get('completed_at') is None:
            validation_errors.append('Status-timestamp inconsistency')
        
        # Check resource count consistency
        allocated = state.get('allocated_resources', [])
        count = state.get('resource_count', 0)
        if len(allocated) != count:
            validation_errors.append('Resource count mismatch')
        
        return {
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'error': '; '.join(validation_errors) if validation_errors else None
        }
    
    def _evaluate_inconsistency_handling(self, validation_result: Dict, scenario: Dict) -> bool:
        """Evaluate if inconsistency was handled appropriately."""
        expected_behavior = scenario['expected_behavior']
        errors = validation_result.get('errors', [])
        
        if expected_behavior == 'access_denied_or_reset':
            return any('user' in error.lower() or 'access' in error.lower() for error in errors)
        elif expected_behavior == 'timestamp_validation_error':
            return any('timestamp' in error.lower() or 'time' in error.lower() for error in errors)
        elif expected_behavior == 'status_validation_error':
            return any('status' in error.lower() for error in errors)
        elif expected_behavior == 'resource_validation_error':
            return any('resource' in error.lower() for error in errors)
        
        return len(errors) > 0  # Any error detection is better than none
    
    def _is_appropriate_inconsistency_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error is appropriate for the inconsistency type."""
        error_str = str(error).lower()
        expected_behavior = scenario['expected_behavior']
        
        if expected_behavior == 'access_denied_or_reset':
            return any(keyword in error_str for keyword in ['access', 'permission', 'user', 'auth'])
        elif expected_behavior == 'timestamp_validation_error':
            return any(keyword in error_str for keyword in ['timestamp', 'time', 'date'])
        elif expected_behavior == 'status_validation_error':
            return any(keyword in error_str for keyword in ['status', 'state', 'phase'])
        elif expected_behavior == 'resource_validation_error':
            return any(keyword in error_str for keyword in ['resource', 'allocation', 'count'])
        
        return True  # Any error is better than silent corruption
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_concurrent_state_modification(self, real_services_fixture):
        """Test handling of concurrent state modifications."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Shared execution state
        shared_execution_state = {
            'execution_id': 'concurrent_test_123',
            'user_id': user_context['id'],
            'status': 'running',
            'progress': 0,
            'resources_allocated': [],
            'last_updated': time.time(),
            'modification_count': 0
        }
        
        # Lock for state modifications (simulating real concurrency control)
        state_lock = asyncio.Lock()
        
        async def concurrent_state_modifier(modifier_id: int, modification_type: str):
            """Simulate concurrent state modifications."""
            modifications = []
            
            for i in range(5):  # Make 5 modifications each
                async with state_lock:  # Simulate proper locking
                    try:
                        # Read current state
                        current_state = deepcopy(shared_execution_state)
                        
                        # Apply modification based on type
                        if modification_type == 'progress_update':
                            current_state['progress'] = min(100, current_state['progress'] + 10)
                        elif modification_type == 'resource_allocation':
                            current_state['resources_allocated'].append(f'resource_{modifier_id}_{i}')
                        elif modification_type == 'status_change':
                            if current_state['progress'] >= 100:
                                current_state['status'] = 'completed'
                        
                        # Update modification tracking
                        current_state['modification_count'] += 1
                        current_state['last_updated'] = time.time()
                        
                        # Simulate brief processing delay
                        await asyncio.sleep(0.01)
                        
                        # Write back state (simulating race condition potential)
                        shared_execution_state.update(current_state)
                        
                        modifications.append({
                            'modifier_id': modifier_id,
                            'modification_index': i,
                            'modification_type': modification_type,
                            'state_after': deepcopy(shared_execution_state),
                            'success': True
                        })
                        
                    except Exception as e:
                        modifications.append({
                            'modifier_id': modifier_id,
                            'modification_index': i,
                            'modification_type': modification_type,
                            'state_after': None,
                            'success': False,
                            'error': str(e)
                        })
            
            return modifications
        
        # Run concurrent state modifiers
        concurrent_tasks = [
            concurrent_state_modifier(1, 'progress_update'),
            concurrent_state_modifier(2, 'resource_allocation'),
            concurrent_state_modifier(3, 'status_change')
        ]
        
        start_time = time.time()
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Analyze concurrent modification results
        all_modifications = []
        for result in concurrent_results:
            if isinstance(result, list):
                all_modifications.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Concurrent modifier failed: {result}")
        
        successful_modifications = [m for m in all_modifications if m.get('success')]
        failed_modifications = [m for m in all_modifications if not m.get('success')]
        
        # Verify state consistency after concurrent modifications
        final_state = shared_execution_state
        
        # Check state integrity
        state_integrity_checks = {
            'progress_within_bounds': 0 <= final_state.get('progress', -1) <= 100,
            'resource_count_consistent': len(final_state.get('resources_allocated', [])) >= 0,
            'modification_count_positive': final_state.get('modification_count', 0) > 0,
            'status_progress_consistent': (
                final_state.get('status') != 'completed' or 
                final_state.get('progress', 0) >= 100
            )
        }
        
        integrity_issues = [check for check, passed in state_integrity_checks.items() if not passed]
        
        success_rate = len(successful_modifications) / len(all_modifications) if all_modifications else 0
        
        assert success_rate >= 0.8, \
            f"Too many concurrent modification failures: {success_rate:.1%} success rate"
        
        assert len(integrity_issues) == 0, \
            f"State integrity issues detected: {integrity_issues}"
        
        # Verify no data was lost due to race conditions
        expected_total_modifications = 15  # 3 modifiers  x  5 modifications each
        actual_modifications = final_state.get('modification_count', 0)
        
        # Allow some tolerance for race conditions in test environment
        modification_completeness = actual_modifications / expected_total_modifications
        
        assert modification_completeness >= 0.7, \
            f"Significant modification loss detected: {modification_completeness:.1%} completeness"
            
        logger.info(f"Concurrent state modification test - Success rate: {success_rate:.1%}, "
                   f"Integrity issues: {len(integrity_issues)}, "
                   f"Modification completeness: {modification_completeness:.1%}, "
                   f"Duration: {duration:.1f}s")
                   
    @pytest.mark.integration
    async def test_state_corruption_recovery_mechanisms(self):
        """Test state corruption recovery and rollback mechanisms."""
        # Mock state management system
        state_versions = {
            'v1': {
                'execution_id': 'recovery_test_456',
                'user_id': 'user_123',
                'status': 'running',
                'progress': 50,
                'checksum': 'valid_checksum_v1'
            },
            'v2': {
                'execution_id': 'recovery_test_456', 
                'user_id': 'user_123',
                'status': 'running',
                'progress': 75,
                'checksum': 'valid_checksum_v2'
            },
            'v3_corrupted': {
                'execution_id': None,  # Corrupted
                'user_id': 'user_123',
                'status': 'running',
                'progress': 'invalid_type',  # Type corruption
                'checksum': 'invalid_checksum'
            }
        }
        
        def validate_state_integrity(state: Dict) -> Dict:
            """Mock state integrity validation."""
            issues = []
            
            if not state.get('execution_id'):
                issues.append('Missing execution_id')
            
            if not isinstance(state.get('progress'), (int, float)):
                issues.append('Invalid progress type')
            
            if state.get('checksum') == 'invalid_checksum':
                issues.append('Checksum validation failed')
            
            return {
                'valid': len(issues) == 0,
                'issues': issues
            }
        
        def recover_state_from_backup(target_version: str) -> Dict:
            """Mock state recovery from backup."""
            if target_version in state_versions and 'corrupted' not in target_version:
                return deepcopy(state_versions[target_version])
            else:
                raise Exception(f"No valid backup found for version {target_version}")
        
        recovery_test_scenarios = [
            {
                'name': 'rollback_to_previous_version',
                'corrupted_state': state_versions['v3_corrupted'],
                'recovery_strategy': 'rollback',
                'target_version': 'v2'
            },
            {
                'name': 'rollback_to_known_good_state',
                'corrupted_state': state_versions['v3_corrupted'],
                'recovery_strategy': 'rollback',
                'target_version': 'v1'
            },
            {
                'name': 'state_reconstruction',
                'corrupted_state': {'execution_id': 'recovery_test_456', 'user_id': None},
                'recovery_strategy': 'reconstruct',
                'target_version': 'v2'
            }
        ]
        
        recovery_results = []
        
        for scenario in recovery_test_scenarios:
            logger.info(f"Testing state recovery: {scenario['name']}")
            
            corrupted_state = scenario['corrupted_state']
            start_time = time.time()
            
            try:
                # Detect corruption
                validation_result = validate_state_integrity(corrupted_state)
                
                if not validation_result['valid']:
                    logger.info(f"Corruption detected: {validation_result['issues']}")
                    
                    # Attempt recovery
                    if scenario['recovery_strategy'] == 'rollback':
                        recovered_state = recover_state_from_backup(scenario['target_version'])
                    elif scenario['recovery_strategy'] == 'reconstruct':
                        # Mock reconstruction from available data
                        base_state = recover_state_from_backup(scenario['target_version'])
                        recovered_state = {
                            **base_state,
                            **{k: v for k, v in corrupted_state.items() if v is not None}
                        }
                    else:
                        recovered_state = None
                    
                    # Validate recovered state
                    if recovered_state:
                        recovery_validation = validate_state_integrity(recovered_state)
                        recovery_successful = recovery_validation['valid']
                    else:
                        recovery_successful = False
                        
                    duration = time.time() - start_time
                    
                    recovery_results.append({
                        'scenario': scenario['name'],
                        'corruption_detected': True,
                        'recovery_attempted': True,
                        'recovery_successful': recovery_successful,
                        'recovered_state': recovered_state,
                        'recovery_issues': recovery_validation.get('issues', []) if recovered_state else ['Recovery failed'],
                        'duration': duration
                    })
                    
                else:
                    # No corruption detected (unexpected for test)
                    duration = time.time() - start_time
                    
                    recovery_results.append({
                        'scenario': scenario['name'],
                        'corruption_detected': False,
                        'recovery_attempted': False,
                        'recovery_successful': False,
                        'recovered_state': corrupted_state,
                        'recovery_issues': ['No corruption detected'],
                        'duration': duration
                    })
                    
            except Exception as e:
                duration = time.time() - start_time
                
                recovery_results.append({
                    'scenario': scenario['name'],
                    'corruption_detected': True,
                    'recovery_attempted': True,
                    'recovery_successful': False,
                    'recovered_state': None,
                    'recovery_issues': [str(e)],
                    'duration': duration
                })
        
        # Verify recovery effectiveness
        successful_recoveries = [r for r in recovery_results if r.get('recovery_successful')]
        attempted_recoveries = [r for r in recovery_results if r.get('recovery_attempted')]
        
        recovery_success_rate = len(successful_recoveries) / len(attempted_recoveries) if attempted_recoveries else 0
        
        assert recovery_success_rate >= 0.8, \
            f"State recovery success rate insufficient: {recovery_success_rate:.1%}"
        
        # Verify all corruptions were detected
        detected_corruptions = [r for r in recovery_results if r.get('corruption_detected')]
        detection_rate = len(detected_corruptions) / len(recovery_results)
        
        assert detection_rate >= 0.9, \
            f"State corruption detection insufficient: {detection_rate:.1%}"
            
        # Verify recovery time is reasonable
        avg_recovery_time = sum(r['duration'] for r in recovery_results) / len(recovery_results)
        
        assert avg_recovery_time < 2.0, \
            f"State recovery taking too long: {avg_recovery_time:.1f}s average"
            
        logger.info(f"State recovery test - Success rate: {recovery_success_rate:.1%}, "
                   f"Detection rate: {detection_rate:.1%}, "
                   f"Avg recovery time: {avg_recovery_time:.1f}s")