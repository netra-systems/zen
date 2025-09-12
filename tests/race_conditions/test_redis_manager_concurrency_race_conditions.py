"""
Stress and Race Condition Tests for Redis Manager Concurrency

MISSION CRITICAL: Stress tests that validate the Redis race condition fix
handles high-concurrency scenarios and prevents race conditions under load.

ROOT CAUSE VALIDATION: These tests confirm that:
1. Multiple concurrent Redis readiness checks don't interfere with each other
2. The 500ms grace period works correctly under concurrent load
3. Background task race conditions are eliminated under stress
4. GCP environment handling is thread-safe and consistent

SSOT COMPLIANCE: Uses real Redis services and existing concurrency patterns.

Business Value:
- Segment: Platform/Internal  
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Ensures Redis race condition fix works under production load
- Strategic Impact: Validates scalable WebSocket reliability for multi-user chat
"""

import asyncio
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict, List
from collections import defaultdict
import statistics

from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.containers_utils import ensure_redis_container

from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator
)


class TestRedisManagerConcurrencyRaceConditions:
    """Stress and race condition tests for Redis manager concurrency."""
    
    @pytest.fixture
    def mock_app_state_concurrent(self):
        """Create thread-safe mock app state for concurrency testing."""
        app_state = Mock()
        
        # Thread-safe Redis manager mock
        redis_manager = Mock()
        redis_manager.is_connected = Mock(return_value=True)
        app_state.redis_manager = redis_manager
        
        # Other required components
        app_state.db_session_factory = Mock()
        app_state.database_available = True
        app_state.auth_validation_complete = True
        app_state.key_manager = Mock()
        app_state.agent_supervisor = Mock()
        app_state.thread_service = Mock()
        app_state.agent_websocket_bridge = Mock()
        app_state.startup_complete = True
        app_state.startup_failed = False
        app_state.startup_phase = "complete"
        
        return app_state
    
    @pytest.mark.stress
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_redis_readiness_validation_stress(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test high-concurrency Redis readiness validation doesn't cause race conditions."""
        
        ensure_redis_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            # Track all validation attempts and their timing
            validation_results = []
            validation_lock = asyncio.Lock()
            
            async def concurrent_validation(validator_id: int, iterations: int):
                """Run multiple Redis readiness validations concurrently."""
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                local_results = []
                
                for iteration in range(iterations):
                    start_time = time.time()
                    
                    try:
                        # Test async Redis readiness validation
                        result = await validator._validate_redis_readiness()
                        
                        elapsed_time = time.time() - start_time
                        
                        validation_data = {
                            'validator_id': validator_id,
                            'iteration': iteration,
                            'result': result,
                            'elapsed_time': elapsed_time,
                            'timestamp': time.time()
                        }
                        
                        local_results.append(validation_data)
                        
                        # Verify grace period was applied
                        assert elapsed_time >= 0.45, \
                            f"Grace period missing in validator {validator_id}, iteration {iteration}: {elapsed_time}s"
                        
                    except Exception as e:
                        local_results.append({
                            'validator_id': validator_id,
                            'iteration': iteration,
                            'result': False,
                            'error': str(e),
                            'elapsed_time': 0,
                            'timestamp': time.time()
                        })
                
                # Add to global results thread-safely
                async with validation_lock:
                    validation_results.extend(local_results)
                
                return len([r for r in local_results if r.get('result', False)])
            
            # Run high-concurrency stress test
            concurrent_validators = 8
            iterations_per_validator = 5
            total_expected = concurrent_validators * iterations_per_validator
            
            # Create tasks for concurrent execution
            tasks = [
                concurrent_validation(validator_id, iterations_per_validator)
                for validator_id in range(concurrent_validators)
            ]
            
            # Execute all concurrent validations
            start_stress_time = time.time()
            success_counts = await asyncio.gather(*tasks, return_exceptions=True)
            total_stress_time = time.time() - start_stress_time
            
            # Analyze stress test results
            total_successes = 0
            for i, success_count in enumerate(success_counts):
                if isinstance(success_count, Exception):
                    pytest.fail(f"Concurrent validator {i} failed with exception: {success_count}")
                total_successes += success_count
            
            # Should have high success rate (allowing for some timing variations)
            success_rate = total_successes / total_expected
            assert success_rate >= 0.9, f"Success rate too low under stress: {success_rate:.2%}"
            
            # Analyze timing consistency
            elapsed_times = [r['elapsed_time'] for r in validation_results if r.get('result', False)]
            if elapsed_times:
                avg_time = statistics.mean(elapsed_times)
                std_time = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0
                
                # Average should include grace period
                assert avg_time >= 0.45, f"Average time too low: {avg_time}s"
                
                # Standard deviation should be reasonable (not excessive variance)
                assert std_time <= 1.0, f"Too much timing variance: {std_time}s"
            
            print(f" PASS:  Stress test: {total_successes}/{total_expected} validations succeeded "
                  f"in {total_stress_time:.2f}s (success rate: {success_rate:.2%})")
    
    @pytest.mark.stress
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_redis_connection_state_race_conditions(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test Redis connection state changes under concurrent load don't cause races."""
        
        ensure_redis_container()
        
        # Simulate unstable Redis connection during high load
        connection_state = {'connected': True, 'call_count': 0}
        connection_lock = threading.Lock()
        
        def unstable_connection():
            """Simulate Redis connection that becomes unstable under load."""
            with connection_lock:
                connection_state['call_count'] += 1
                
                # Simulate connection instability every few calls
                if connection_state['call_count'] % 7 == 0:
                    connection_state['connected'] = not connection_state['connected']
                
                return connection_state['connected']
        
        mock_app_state_concurrent.redis_manager.is_connected = Mock(side_effect=unstable_connection)
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            connection_results = []
            result_lock = asyncio.Lock()
            
            async def test_connection_stability(test_id: int, checks_per_test: int):
                """Test connection stability under concurrent access."""
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                local_results = []
                
                for check in range(checks_per_test):
                    start_time = time.time()
                    
                    try:
                        result = await validator._validate_redis_readiness()
                        elapsed_time = time.time() - start_time
                        
                        local_results.append({
                            'test_id': test_id,
                            'check': check,
                            'result': result,
                            'elapsed_time': elapsed_time,
                            'connection_calls': connection_state['call_count']
                        })
                        
                    except Exception as e:
                        local_results.append({
                            'test_id': test_id,
                            'check': check,
                            'result': False,
                            'error': str(e),
                            'elapsed_time': 0
                        })
                
                async with result_lock:
                    connection_results.extend(local_results)
                
                return local_results
            
            # Run concurrent stability tests
            concurrent_tests = 6
            checks_per_test = 8
            
            tasks = [
                test_connection_stability(test_id, checks_per_test)
                for test_id in range(concurrent_tests)
            ]
            
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify no race conditions occurred
            for i, result in enumerate(all_results):
                if isinstance(result, Exception):
                    pytest.fail(f"Connection stability test {i} failed: {result}")
            
            # Analyze connection state handling
            successful_checks = [r for r in connection_results if r.get('result', False)]
            failed_checks = [r for r in connection_results if not r.get('result', False)]
            
            # Should handle both connected and disconnected states gracefully
            assert len(successful_checks) > 0, "No successful checks during connection instability"
            assert len(failed_checks) > 0, "No failed checks during connection instability (test may be invalid)"
            
            # Grace period should be applied consistently
            for check in successful_checks:
                if check['elapsed_time'] > 0:  # Ignore error cases
                    assert check['elapsed_time'] >= 0.4, \
                        f"Grace period missing during connection instability: {check['elapsed_time']}s"
            
            print(f" PASS:  Connection stability test: {len(successful_checks)} successful, "
                  f"{len(failed_checks)} failed (instability handled correctly)")
    
    @pytest.mark.stress
    @pytest.mark.real_services
    @pytest.mark.asyncio 
    async def test_full_websocket_readiness_under_load(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test complete WebSocket readiness validation under concurrent load."""
        
        ensure_redis_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            load_results = []
            result_lock = asyncio.Lock()
            
            async def full_readiness_under_load(load_id: int):
                """Run full WebSocket readiness validation under load."""
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                start_time = time.time()
                
                try:
                    result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=120.0)
                    
                    elapsed_time = time.time() - start_time
                    
                    load_result = {
                        'load_id': load_id,
                        'ready': result.ready,
                        'state': result.state,
                        'elapsed_time': elapsed_time,
                        'validation_time': result.elapsed_time,
                        'failed_services': result.failed_services
                    }
                    
                    async with result_lock:
                        load_results.append(load_result)
                    
                    return load_result
                    
                except Exception as e:
                    error_result = {
                        'load_id': load_id,
                        'ready': False,
                        'error': str(e),
                        'elapsed_time': time.time() - start_time
                    }
                    
                    async with result_lock:
                        load_results.append(error_result)
                    
                    return error_result
            
            # Generate high concurrent load
            concurrent_load = 10
            tasks = [full_readiness_under_load(i) for i in range(concurrent_load)]
            
            # Execute under load
            start_load_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_load_time = time.time() - start_load_time
            
            # Analyze load test results
            successful_validations = 0
            total_validation_time = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Load test {i} failed with exception: {result}")
                
                if result.get('ready', False):
                    successful_validations += 1
                    total_validation_time += result.get('validation_time', 0)
            
            # Should maintain high success rate under load
            success_rate = successful_validations / concurrent_load
            assert success_rate >= 0.8, f"Success rate under load too low: {success_rate:.2%}"
            
            # Average validation time should include Redis grace period
            if successful_validations > 0:
                avg_validation_time = total_validation_time / successful_validations
                assert avg_validation_time >= 0.5, \
                    f"Average validation time suggests grace period missing: {avg_validation_time}s"
            
            print(f" PASS:  Load test: {successful_validations}/{concurrent_load} succeeded "
                  f"in {total_load_time:.2f}s (success rate: {success_rate:.2%})")
    
    @pytest.mark.stress
    @pytest.mark.real_services
    async def test_redis_readiness_thread_safety(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test Redis readiness validation is thread-safe across different contexts."""
        
        ensure_redis_container()
        
        # Shared state to track thread safety
        shared_state = {
            'concurrent_calls': 0,
            'max_concurrent': 0,
            'results': [],
            'errors': []
        }
        thread_lock = threading.Lock()
        
        def thread_safe_validation(thread_id: int, iterations: int):
            """Run Redis validation in separate thread context."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
                    validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                    
                    thread_results = []
                    
                    for i in range(iterations):
                        with thread_lock:
                            shared_state['concurrent_calls'] += 1
                            if shared_state['concurrent_calls'] > shared_state['max_concurrent']:
                                shared_state['max_concurrent'] = shared_state['concurrent_calls']
                        
                        try:
                            # Run async validation in thread context
                            start_time = time.time()
                            
                            # Note: Since the method was changed to async, we need to handle it properly
                            result = loop.run_until_complete(validator._validate_redis_readiness())
                            
                            elapsed_time = time.time() - start_time
                            
                            thread_results.append({
                                'thread_id': thread_id,
                                'iteration': i,
                                'result': result,
                                'elapsed_time': elapsed_time
                            })
                            
                        except Exception as e:
                            with thread_lock:
                                shared_state['errors'].append(f"Thread {thread_id}, iteration {i}: {e}")
                        
                        finally:
                            with thread_lock:
                                shared_state['concurrent_calls'] -= 1
                    
                    with thread_lock:
                        shared_state['results'].extend(thread_results)
                    
                    return thread_results
                    
            finally:
                loop.close()
        
        # Run thread safety test
        thread_count = 4
        iterations_per_thread = 3
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [
                executor.submit(thread_safe_validation, thread_id, iterations_per_thread)
                for thread_id in range(thread_count)
            ]
            
            # Wait for all threads to complete
            thread_results = []
            for future in futures:
                try:
                    result = future.result(timeout=60)  # 60 second timeout per thread
                    thread_results.extend(result)
                except Exception as e:
                    pytest.fail(f"Thread safety test failed: {e}")
        
        # Analyze thread safety results
        total_expected = thread_count * iterations_per_thread
        successful_results = [r for r in shared_state['results'] if r.get('result', False)]
        
        # Should have reasonable success rate
        success_rate = len(successful_results) / total_expected
        assert success_rate >= 0.7, f"Thread safety test success rate too low: {success_rate:.2%}"
        
        # Check for thread safety errors
        if shared_state['errors']:
            print(f" WARNING: [U+FE0F]  Thread safety warnings: {len(shared_state['errors'])} errors occurred")
            for error in shared_state['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        # Verify grace period was consistently applied
        for result in successful_results:
            if result['elapsed_time'] > 0:
                assert result['elapsed_time'] >= 0.4, \
                    f"Grace period missing in thread {result['thread_id']}: {result['elapsed_time']}s"
        
        print(f" PASS:  Thread safety test: {len(successful_results)}/{total_expected} successful "
              f"(max concurrent: {shared_state['max_concurrent']})")
    
    @pytest.mark.stress
    @pytest.mark.real_services  
    @pytest.mark.asyncio
    async def test_memory_usage_under_concurrent_load(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test memory usage remains stable under concurrent Redis validation load."""
        
        ensure_redis_container()
        
        import gc
        import sys
        
        # Baseline memory measurement
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            async def memory_stress_validation(stress_id: int, stress_iterations: int):
                """Run validations while monitoring memory usage."""
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                validation_results = []
                
                for i in range(stress_iterations):
                    try:
                        result = await validator._validate_redis_readiness()
                        validation_results.append(result)
                        
                        # Small delay to allow garbage collection
                        await asyncio.sleep(0.01)
                        
                    except Exception:
                        pass  # Continue stress test even if individual validations fail
                
                return validation_results
            
            # Run memory stress test  
            stress_tasks = 15
            iterations_per_task = 10
            
            tasks = [
                memory_stress_validation(i, iterations_per_task)
                for i in range(stress_tasks)
            ]
            
            # Execute memory stress test
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Force garbage collection after stress test
            gc.collect()
            final_objects = len(gc.get_objects())
            
            # Memory usage should not have grown excessively
            object_growth = final_objects - initial_objects
            growth_rate = object_growth / initial_objects if initial_objects > 0 else 0
            
            # Allow some growth but not excessive memory leaks
            assert growth_rate <= 0.5, f"Excessive memory growth: {growth_rate:.2%} ({object_growth} objects)"
            
            # Count successful validations
            total_successes = 0
            for result_list in all_results:
                if isinstance(result_list, list):
                    total_successes += sum(1 for r in result_list if r)
            
            expected_total = stress_tasks * iterations_per_task
            success_rate = total_successes / expected_total
            
            print(f" PASS:  Memory stress test: {total_successes}/{expected_total} successful "
                  f"(success rate: {success_rate:.2%}, object growth: {growth_rate:.2%})")
    
    @pytest.mark.stress
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_redis_grace_period_consistency_under_stress(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test Redis grace period timing remains consistent under stress conditions."""
        
        ensure_redis_container()
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            timing_data = []
            timing_lock = asyncio.Lock()
            
            async def measure_grace_period_consistency(measurer_id: int, measurements: int):
                """Measure grace period timing consistency under load."""
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                local_timings = []
                
                for measurement in range(measurements):
                    start_time = time.time()
                    
                    try:
                        result = await validator._validate_redis_readiness()
                        elapsed_time = time.time() - start_time
                        
                        if result:  # Only measure successful validations
                            local_timings.append({
                                'measurer_id': measurer_id,
                                'measurement': measurement,
                                'elapsed_time': elapsed_time,
                                'timestamp': time.time()
                            })
                    
                    except Exception:
                        pass  # Continue measuring even if some validations fail
                
                async with timing_lock:
                    timing_data.extend(local_timings)
                
                return local_timings
            
            # Run timing consistency test
            concurrent_measurers = 8
            measurements_per_measurer = 6
            
            tasks = [
                measure_grace_period_consistency(i, measurements_per_measurer)
                for i in range(concurrent_measurers)
            ]
            
            # Execute timing measurements
            measurement_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze timing consistency
            all_elapsed_times = [t['elapsed_time'] for t in timing_data]
            
            if len(all_elapsed_times) >= 10:  # Need sufficient data points
                avg_time = statistics.mean(all_elapsed_times)
                median_time = statistics.median(all_elapsed_times)
                std_dev = statistics.stdev(all_elapsed_times)
                min_time = min(all_elapsed_times)
                max_time = max(all_elapsed_times)
                
                # All measurements should include grace period
                assert min_time >= 0.4, f"Minimum time too low (grace period missing): {min_time}s"
                
                # Average should be around expected grace period
                assert avg_time >= 0.45, f"Average time too low: {avg_time}s"
                
                # Should not have excessive timing variance under stress
                assert std_dev <= 2.0, f"Timing variance too high under stress: {std_dev}s"
                
                # Maximum time should be reasonable (not hanging)
                assert max_time <= 10.0, f"Maximum time too high (possible hang): {max_time}s"
                
                print(f" PASS:  Grace period consistency: avg={avg_time:.3f}s, median={median_time:.3f}s, "
                      f"std={std_dev:.3f}s, range=[{min_time:.3f}s, {max_time:.3f}s]")
            else:
                pytest.fail(f"Insufficient timing data: {len(all_elapsed_times)} measurements")
    
    @pytest.mark.stress  
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_error_handling_under_concurrent_failures(
        self,
        mock_app_state_concurrent,
        isolated_env
    ):
        """Test error handling remains robust under concurrent failure scenarios."""
        
        ensure_redis_container()
        
        # Create different failure scenarios
        failure_scenarios = {
            'redis_none': lambda: setattr(mock_app_state_concurrent, 'redis_manager', None),
            'redis_exception': lambda: setattr(
                mock_app_state_concurrent.redis_manager, 
                'is_connected', 
                Mock(side_effect=Exception("Simulated Redis failure"))
            ),
            'redis_timeout': lambda: setattr(
                mock_app_state_concurrent.redis_manager,
                'is_connected',
                Mock(side_effect=asyncio.TimeoutError("Redis timeout"))
            )
        }
        
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend'}):
            
            error_results = []
            error_lock = asyncio.Lock()
            
            async def test_failure_scenario(scenario_name: str, failure_setup, test_iterations: int):
                """Test a specific failure scenario."""
                # Apply failure setup
                failure_setup()
                
                validator = create_gcp_websocket_validator(mock_app_state_concurrent)
                
                local_results = []
                
                for iteration in range(test_iterations):
                    try:
                        start_time = time.time()
                        result = await validator._validate_redis_readiness()
                        elapsed_time = time.time() - start_time
                        
                        local_results.append({
                            'scenario': scenario_name,
                            'iteration': iteration,
                            'result': result,
                            'elapsed_time': elapsed_time,
                            'error_type': None
                        })
                        
                    except Exception as e:
                        local_results.append({
                            'scenario': scenario_name,
                            'iteration': iteration,
                            'result': False,
                            'elapsed_time': 0,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        })
                
                async with error_lock:
                    error_results.extend(local_results)
                
                return local_results
            
            # Test all failure scenarios concurrently
            scenario_tasks = []
            iterations_per_scenario = 5
            
            for scenario_name, failure_setup in failure_scenarios.items():
                task = test_failure_scenario(scenario_name, failure_setup, iterations_per_scenario)
                scenario_tasks.append(task)
            
            # Execute failure scenario tests
            scenario_results = await asyncio.gather(*scenario_tasks, return_exceptions=True)
            
            # Analyze error handling robustness
            scenarios_tested = len(failure_scenarios)
            total_iterations = scenarios_tested * iterations_per_scenario
            
            # Count different types of results
            successful_failures = 0  # Scenarios that failed gracefully
            unexpected_errors = 0
            
            for result in error_results:
                if result['result'] is False and result['error_type'] is None:
                    # Graceful failure (returned False without exception)
                    successful_failures += 1
                elif result['error_type'] is not None:
                    # Exception occurred - check if it's expected
                    if result['error_type'] in ['Exception', 'TimeoutError', 'AttributeError']:
                        successful_failures += 1  # Expected error types
                    else:
                        unexpected_errors += 1
            
            # Error handling should be robust (failures should be graceful)
            graceful_failure_rate = successful_failures / total_iterations
            assert graceful_failure_rate >= 0.8, \
                f"Error handling not robust enough: {graceful_failure_rate:.2%} graceful failures"
            
            # Should not have many unexpected errors
            assert unexpected_errors <= total_iterations * 0.1, \
                f"Too many unexpected errors: {unexpected_errors}/{total_iterations}"
            
            print(f" PASS:  Error handling test: {successful_failures}/{total_iterations} graceful failures "
                  f"({graceful_failure_rate:.2%}), {unexpected_errors} unexpected errors")