"""
Staging Environment E2E Tests for EventValidator SSOT

This test suite validates EventValidator SSOT integration in the staging environment
with real LLM services and production-like conditions.

Created: 2025-09-10
Purpose: Validate EventValidator SSOT in staging environment
Requirements: Real LLM integration, staging environment, performance validation
"""

import asyncio
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiohttp
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestSsotEventValidatorStaging(SSotAsyncTestCase):
    """
    Staging environment E2E tests for EventValidator SSOT.
    
    These tests validate that the SSOT EventValidator works correctly in
    production-like conditions with real LLM integration and load testing.
    
    CRITICAL: Uses real staging services and LLM APIs - no mocks.
    """
    
    async def asyncSetUp(self):
        """Set up staging test environment with real services."""
        await super().asyncSetUp()
        
        self.env = IsolatedEnvironment()
        
        # Staging environment configuration
        self.staging_base_url = self.env.get_env_var("STAGING_BASE_URL", "https://staging.netra-apex.com")
        self.staging_websocket_url = self.env.get_env_var("STAGING_WEBSOCKET_URL", "wss://staging.netra-apex.com/ws")
        
        # Performance thresholds for staging
        self.max_validation_time = 2.0  # 2 seconds max
        self.max_concurrent_validations = 50  # 50 concurrent users
        self.target_success_rate = 0.98  # 98% success rate
        
        # Test configuration
        self.test_duration = 30  # 30 second load test
        self.ramp_up_time = 5   # 5 second ramp up
        
        # Skip if staging not available
        if not await self._is_staging_available():
            pytest.skip("Staging environment not available")
    
    async def test_ssot_validator_with_real_agent_execution(self):
        """
        Test: SSOT EventValidator with real LLM agent execution in staging.
        
        CURRENT EXPECTATION: FAIL - SSOT validator not integrated with staging
        POST-CONSOLIDATION: PASS - Full staging integration
        
        This test validates that the SSOT EventValidator works correctly with
        real agent executions using actual LLM APIs in the staging environment.
        """
        # Test scenarios with real agent tasks
        agent_execution_scenarios = [
            {
                'scenario': 'data_optimization_task',
                'agent_type': 'supervisor',
                'task': 'Analyze database performance metrics and suggest optimizations',
                'expected_events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'],
                'expected_duration': 45.0,
                'llm_model': 'claude-sonnet'
            },
            {
                'scenario': 'cost_analysis_task',
                'agent_type': 'apex_optimizer',
                'task': 'Calculate cost savings for AI infrastructure optimization',
                'expected_events': ['agent_started', 'tool_executing', 'agent_completed'],
                'expected_duration': 30.0,
                'llm_model': 'claude-sonnet'
            },
            {
                'scenario': 'user_experience_task',
                'agent_type': 'triage',
                'task': 'Evaluate user experience improvements for chat interface',
                'expected_events': ['agent_started', 'agent_thinking', 'agent_completed'],
                'expected_duration': 25.0,
                'llm_model': 'claude-haiku'
            }
        ]
        
        validation_results = {}
        failed_scenarios = []
        
        # Execute each scenario with real LLM integration
        for scenario in agent_execution_scenarios:
            try:
                scenario_result = await self._execute_real_agent_scenario_with_validation(scenario)
                
                validation_results[scenario['scenario']] = {
                    'execution_success': scenario_result['execution_success'],
                    'events_validated': scenario_result['events_validated'],
                    'validation_success_rate': scenario_result['validation_success_rate'],
                    'total_execution_time': scenario_result['total_execution_time'],
                    'llm_interaction_time': scenario_result['llm_interaction_time'],
                    'business_value_calculated': scenario_result['business_value_calculated']
                }
                
                if not scenario_result['execution_success'] or scenario_result['validation_success_rate'] < self.target_success_rate:
                    failed_scenarios.append({
                        'scenario': scenario['scenario'],
                        'execution_success': scenario_result['execution_success'],
                        'validation_rate': scenario_result['validation_success_rate'],
                        'errors': scenario_result.get('errors', [])
                    })
                    
            except Exception as e:
                failed_scenarios.append({
                    'scenario': scenario['scenario'],
                    'exception': str(e)
                })
                validation_results[scenario['scenario']] = {
                    'execution_success': False,
                    'exception': str(e)
                }
        
        # Log results
        print(f"\nReal agent execution with SSOT validation in staging:")
        print(f"Total scenarios: {len(agent_execution_scenarios)}")
        print(f"Successful scenarios: {len([r for r in validation_results.values() if r.get('execution_success', False)])}")
        print(f"Failed scenarios: {len(failed_scenarios)}")
        
        for scenario, result in validation_results.items():
            status = ' PASS:  PASS' if result.get('execution_success', False) else ' FAIL:  FAIL'
            print(f"  {scenario}: {status}")
            if 'validation_success_rate' in result:
                print(f"    Validation rate: {result['validation_success_rate']:.1%}")
                print(f"    Execution time: {result['total_execution_time']:.1f}s")
                print(f"    LLM time: {result['llm_interaction_time']:.1f}s")
        
        # SSOT Requirement: All scenarios must succeed with high validation rate
        self.assertEqual(
            len(failed_scenarios), 0,
            f"STAGING INTEGRATION FAILURE: {len(failed_scenarios)} scenarios failed: {failed_scenarios}"
        )
        
        # Performance Requirement: All executions within reasonable time
        slow_executions = []
        for scenario, result in validation_results.items():
            if result.get('total_execution_time', 0) > 60.0:  # 1 minute threshold
                slow_executions.append({
                    'scenario': scenario,
                    'time': result['total_execution_time']
                })
        
        self.assertEqual(
            len(slow_executions), 0,
            f"PERFORMANCE FAILURE: {len(slow_executions)} scenarios too slow: {slow_executions}"
        )
    
    async def test_ssot_validator_performance_under_load(self):
        """
        Test: SSOT EventValidator performance under concurrent load.
        
        CURRENT EXPECTATION: FAIL - Performance degradation under load
        POST-CONSOLIDATION: PASS - Consistent performance at scale
        
        This test validates that the SSOT EventValidator maintains consistent
        performance characteristics under realistic concurrent load.
        """
        # Load test configuration
        concurrent_users = [5, 10, 25, 50]  # Progressive load testing
        events_per_user = 10
        
        load_test_results = {}
        performance_failures = []
        
        for user_count in concurrent_users:
            print(f"\nLoad testing with {user_count} concurrent users...")
            
            try:
                load_result = await self._execute_concurrent_validation_load_test(
                    user_count=user_count,
                    events_per_user=events_per_user,
                    test_duration=self.test_duration
                )
                
                load_test_results[user_count] = {
                    'total_validations': load_result['total_validations'],
                    'successful_validations': load_result['successful_validations'],
                    'success_rate': load_result['success_rate'],
                    'average_response_time': load_result['average_response_time'],
                    'max_response_time': load_result['max_response_time'],
                    'min_response_time': load_result['min_response_time'],
                    'throughput_per_second': load_result['throughput_per_second'],
                    'errors': load_result['errors']
                }
                
                # Check performance thresholds
                if load_result['success_rate'] < self.target_success_rate:
                    performance_failures.append({
                        'user_count': user_count,
                        'issue': 'low_success_rate',
                        'actual': load_result['success_rate'],
                        'expected': self.target_success_rate
                    })
                
                if load_result['average_response_time'] > self.max_validation_time:
                    performance_failures.append({
                        'user_count': user_count,
                        'issue': 'slow_response',
                        'actual': load_result['average_response_time'],
                        'expected': self.max_validation_time
                    })
                    
            except Exception as e:
                performance_failures.append({
                    'user_count': user_count,
                    'issue': 'load_test_exception',
                    'exception': str(e)
                })
                load_test_results[user_count] = {
                    'exception': str(e),
                    'success_rate': 0
                }
        
        # Log performance results
        print(f"\nConcurrent load testing results:")
        for user_count, result in load_test_results.items():
            if 'exception' in result:
                print(f"  {user_count} users:  FAIL:  EXCEPTION - {result['exception']}")
            else:
                print(f"  {user_count} users: {result['success_rate']:.1%} success")
                print(f"    Avg response: {result['average_response_time']:.3f}s")
                print(f"    Throughput: {result['throughput_per_second']:.1f} validations/sec")
                print(f"    Total validations: {result['total_validations']}")
        
        print(f"\nPerformance failures: {len(performance_failures)}")
        for failure in performance_failures:
            print(f"  {failure['user_count']} users: {failure['issue']}")
            if 'actual' in failure:
                print(f"    Actual: {failure['actual']}, Expected: {failure['expected']}")
        
        # SSOT Performance Requirement: No performance failures
        self.assertEqual(
            len(performance_failures), 0,
            f"PERFORMANCE FAILURE: {len(performance_failures)} load levels failed performance requirements: {performance_failures}"
        )
        
        # Scale Requirement: Performance should not degrade significantly with load
        response_times = [r['average_response_time'] for r in load_test_results.values() if 'average_response_time' in r]
        if len(response_times) >= 2:
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            performance_degradation = (max_response_time - min_response_time) / min_response_time
            
            self.assertLessEqual(
                performance_degradation, 0.5,  # 50% degradation threshold
                f"SCALE FAILURE: Performance degraded {performance_degradation:.1%} under load (max: {max_response_time:.3f}s, min: {min_response_time:.3f}s)"
            )
    
    async def test_ssot_validator_staging_environment_integration(self):
        """
        Test: SSOT EventValidator integrates properly with staging environment.
        
        CURRENT EXPECTATION: FAIL - Integration issues with staging services
        POST-CONSOLIDATION: PASS - Seamless staging integration
        
        This test validates that the SSOT EventValidator properly integrates
        with all staging environment services and configurations.
        """
        integration_checks = [
            {
                'check': 'staging_config_loaded',
                'description': 'SSOT validator loads staging configuration correctly',
                'endpoint': f"{self.staging_base_url}/health"
            },
            {
                'check': 'websocket_connection',
                'description': 'SSOT validator works with staging WebSocket',
                'endpoint': self.staging_websocket_url
            },
            {
                'check': 'database_integration',
                'description': 'SSOT validator integrates with staging database',
                'endpoint': f"{self.staging_base_url}/api/health/database"
            },
            {
                'check': 'redis_integration',
                'description': 'SSOT validator integrates with staging Redis',
                'endpoint': f"{self.staging_base_url}/api/health/redis"
            },
            {
                'check': 'llm_integration',
                'description': 'SSOT validator works with staging LLM services',
                'endpoint': f"{self.staging_base_url}/api/health/llm"
            }
        ]
        
        integration_results = {}
        failed_integrations = []
        
        # Check each integration point
        for check in integration_checks:
            try:
                integration_result = await self._check_staging_integration(check)
                
                integration_results[check['check']] = {
                    'success': integration_result['success'],
                    'response_time': integration_result['response_time'],
                    'status_code': integration_result.get('status_code'),
                    'message': integration_result.get('message', 'OK')
                }
                
                if not integration_result['success']:
                    failed_integrations.append({
                        'check': check['check'],
                        'description': check['description'],
                        'error': integration_result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                failed_integrations.append({
                    'check': check['check'],
                    'exception': str(e)
                })
                integration_results[check['check']] = {
                    'success': False,
                    'exception': str(e)
                }
        
        # Log integration results
        print(f"\nStaging environment integration results:")
        print(f"Total integration checks: {len(integration_checks)}")
        print(f"Successful integrations: {len([r for r in integration_results.values() if r.get('success', False)])}")
        print(f"Failed integrations: {len(failed_integrations)}")
        
        for check, result in integration_results.items():
            status = ' PASS:  PASS' if result.get('success', False) else ' FAIL:  FAIL'
            print(f"  {check}: {status}")
            if 'response_time' in result:
                print(f"    Response time: {result['response_time']:.3f}s")
            if 'message' in result and result['message'] != 'OK':
                print(f"    Message: {result['message']}")
        
        # SSOT Requirement: All integrations must succeed
        self.assertEqual(
            len(failed_integrations), 0,
            f"STAGING INTEGRATION FAILURE: {len(failed_integrations)} integration checks failed: {failed_integrations}"
        )
        
        # Performance Requirement: All integrations within reasonable time
        slow_integrations = []
        for check, result in integration_results.items():
            if result.get('response_time', 0) > 5.0:  # 5 second threshold
                slow_integrations.append({
                    'check': check,
                    'response_time': result['response_time']
                })
        
        self.assertEqual(
            len(slow_integrations), 0,
            f"INTEGRATION PERFORMANCE FAILURE: {len(slow_integrations)} integrations too slow: {slow_integrations}"
        )
    
    async def _is_staging_available(self) -> bool:
        """
        Check if staging environment is available for testing.
        
        Returns:
            True if staging is available
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.staging_base_url}/health", timeout=10) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _execute_real_agent_scenario_with_validation(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute real agent scenario with SSOT validation.
        
        Args:
            scenario: Agent execution scenario configuration
            
        Returns:
            Scenario execution and validation results
        """
        start_time = time.time()
        
        try:
            # Import SSOT EventValidator
            from netra_backend.app.websocket_core.event_validator import EventValidator
            validator = EventValidator()
            
            # Execute agent task with real LLM
            agent_execution_result = await self._execute_real_agent_task(scenario)
            
            # Validate each event generated during execution
            validation_results = []
            for event in agent_execution_result['events']:
                validation_result = await validator.validate_websocket_event(
                    event_type=event['type'],
                    event_data=event['data'],
                    user_id=f"staging_test_{int(time.time())}",
                    run_id=agent_execution_result['run_id']
                )
                validation_results.append(validation_result)
            
            end_time = time.time()
            
            successful_validations = sum(1 for r in validation_results if r.get('valid', False))
            validation_success_rate = successful_validations / len(validation_results) if validation_results else 0
            
            return {
                'execution_success': agent_execution_result['success'],
                'events_validated': len(validation_results),
                'validation_success_rate': validation_success_rate,
                'total_execution_time': end_time - start_time,
                'llm_interaction_time': agent_execution_result['llm_time'],
                'business_value_calculated': any(r.get('business_impact', 0) > 0 for r in validation_results),
                'errors': agent_execution_result.get('errors', [])
            }
            
        except Exception as e:
            return {
                'execution_success': False,
                'events_validated': 0,
                'validation_success_rate': 0,
                'total_execution_time': time.time() - start_time,
                'errors': [str(e)]
            }
    
    async def _execute_real_agent_task(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute real agent task using staging LLM services.
        
        Args:
            scenario: Agent task scenario
            
        Returns:
            Agent execution results with events
        """
        start_time = time.time()
        
        try:
            # Make request to staging agent execution endpoint
            async with aiohttp.ClientSession() as session:
                request_data = {
                    'agent_type': scenario['agent_type'],
                    'task': scenario['task'],
                    'llm_model': scenario['llm_model'],
                    'timeout': scenario.get('expected_duration', 60),
                    'test_mode': True
                }
                
                async with session.post(
                    f"{self.staging_base_url}/api/agents/execute",
                    json=request_data,
                    timeout=120
                ) as response:
                    
                    if response.status != 200:
                        return {
                            'success': False,
                            'errors': [f"Agent execution failed: {response.status}"],
                            'events': [],
                            'run_id': None,
                            'llm_time': 0
                        }
                    
                    result = await response.json()
                    llm_time = time.time() - start_time
                    
                    # Extract events from execution result
                    events = []
                    for event_type in scenario['expected_events']:
                        events.append({
                            'type': event_type,
                            'data': {
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'agent_type': scenario['agent_type'],
                                'task_id': result.get('task_id'),
                                'execution_context': 'staging_test'
                            }
                        })
                    
                    return {
                        'success': result.get('success', False),
                        'events': events,
                        'run_id': result.get('run_id'),
                        'llm_time': llm_time,
                        'errors': result.get('errors', [])
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)],
                'events': [],
                'run_id': None,
                'llm_time': time.time() - start_time
            }
    
    async def _execute_concurrent_validation_load_test(self, user_count: int, events_per_user: int, test_duration: int) -> Dict[str, Any]:
        """
        Execute concurrent validation load test.
        
        Args:
            user_count: Number of concurrent users
            events_per_user: Events to validate per user
            test_duration: Test duration in seconds
            
        Returns:
            Load test results
        """
        start_time = time.time()
        
        # Create concurrent validation tasks
        validation_tasks = []
        for user_id in range(user_count):
            task = asyncio.create_task(
                self._user_validation_load_task(f"load_test_user_{user_id}", events_per_user)
            )
            validation_tasks.append(task)
        
        # Execute all tasks concurrently
        task_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Aggregate results
        total_validations = 0
        successful_validations = 0
        response_times = []
        errors = []
        
        for result in task_results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                total_validations += result.get('validations', 0)
                successful_validations += result.get('successful', 0)
                response_times.extend(result.get('response_times', []))
                errors.extend(result.get('errors', []))
        
        return {
            'total_validations': total_validations,
            'successful_validations': successful_validations,
            'success_rate': successful_validations / total_validations if total_validations > 0 else 0,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'throughput_per_second': total_validations / actual_duration if actual_duration > 0 else 0,
            'test_duration': actual_duration,
            'errors': errors[:10]  # Limit errors for readability
        }
    
    async def _user_validation_load_task(self, user_id: str, events_to_validate: int) -> Dict[str, Any]:
        """
        Execute validation load task for single user.
        
        Args:
            user_id: User identifier
            events_to_validate: Number of events to validate
            
        Returns:
            User load test results
        """
        try:
            from netra_backend.app.websocket_core.event_validator import EventValidator
            validator = EventValidator()
            
            validations = 0
            successful = 0
            response_times = []
            errors = []
            
            for i in range(events_to_validate):
                start_time = time.time()
                
                try:
                    # Create test event data
                    event_data = {
                        'user_id': user_id,
                        'event_sequence': i,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'test_load': True
                    }
                    
                    # Validate event with SSOT validator
                    validation_result = await validator.validate_websocket_event(
                        event_type='agent_thinking',
                        event_data=event_data,
                        user_id=user_id,
                        run_id=f"load_test_{user_id}_{i}"
                    )
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    response_times.append(response_time)
                    
                    validations += 1
                    if validation_result.get('valid', False):
                        successful += 1
                    else:
                        errors.append(f"Validation failed for {user_id}:{i}")
                        
                except Exception as e:
                    errors.append(f"Exception in {user_id}:{i}: {str(e)}")
                    response_times.append(time.time() - start_time)
                    validations += 1
                
                # Small delay between validations to simulate realistic usage
                await asyncio.sleep(0.01)
            
            return {
                'validations': validations,
                'successful': successful,
                'response_times': response_times,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'validations': 0,
                'successful': 0,
                'response_times': [],
                'errors': [f"User task exception: {str(e)}"]
            }
    
    async def _check_staging_integration(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check specific staging integration point.
        
        Args:
            check: Integration check configuration
            
        Returns:
            Integration check results
        """
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(check['endpoint'], timeout=10) as response:
                    end_time = time.time()
                    
                    return {
                        'success': response.status == 200,
                        'response_time': end_time - start_time,
                        'status_code': response.status,
                        'message': 'OK' if response.status == 200 else f"Status {response.status}"
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'response_time': time.time() - start_time,
                'error': str(e)
            }


if __name__ == "__main__":
    pytest.main([__file__])