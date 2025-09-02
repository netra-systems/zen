#!/usr/bin/env python3
"""
Mission Critical Test Suite - SSOT Orchestration Edge Cases
===========================================================

This test suite focuses on EXTREMELY DIFFICULT edge cases and scenarios that
could break the SSOT orchestration system. These are the tests that catch
the subtle bugs that only appear in production under stress.

Critical Edge Case Areas:
1. Concurrent access patterns and race conditions
2. Import failures and recovery scenarios
3. Environment variable tampering and manipulation
4. Invalid configuration states and corruption
5. Memory leaks and resource exhaustion
6. Performance degradation under high load
7. Thread safety violations and deadlocks
8. Error propagation and exception handling

Business Value: Ensures the SSOT orchestration system is production-ready
and can handle real-world stress, failures, and edge conditions.

WARNING: These tests are designed to be BRUTAL. They test failure modes,
race conditions, memory leaks, and all the nasty edge cases.
"""

import gc
import os
import psutil
import pytest
import sys
import threading
import time
import tracemalloc
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT orchestration modules
try:
    from test_framework.ssot.orchestration import (
        OrchestrationConfig,
        get_orchestration_config,
        refresh_global_orchestration_config,
        _global_orchestration_config,
        _global_config_lock
    )
    from test_framework.ssot.orchestration_enums import (
        BackgroundTaskStatus,
        E2ETestCategory,
        ExecutionStrategy
    )
    SSOT_ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    SSOT_ORCHESTRATION_AVAILABLE = False
    pytest.skip(f"SSOT orchestration modules not available: {e}", allow_module_level=True)


@pytest.mark.mission_critical
class TestConcurrentAccessEdgeCases:
    """Test concurrent access patterns and race conditions - BRUTAL tests."""
    
    def test_concurrent_singleton_creation_race_condition(self):
        """CRITICAL: Test race condition during singleton creation."""
        # Reset singleton to test creation race
        OrchestrationConfig._instance = None
        
        instances = []
        creation_times = []
        errors = []
        
        def create_and_time():
            try:
                start = time.time()
                instance = OrchestrationConfig()
                end = time.time()
                instances.append(instance)
                creation_times.append(end - start)
            except Exception as e:
                errors.append(e)
        
        # Create massive concurrent load
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=create_and_time)
            threads.append(thread)
        
        # Start all at once to maximize race condition chance
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        end_time = time.time()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        
        # Verify ALL instances are identical
        assert len(instances) > 0
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance, "Race condition in singleton creation"
        
        # Performance check - should not take too long even under load
        total_time = end_time - start_time
        assert total_time < 2.0, f"Concurrent creation took too long: {total_time}s"
    
    def test_concurrent_availability_checking_with_import_mocking(self):
        """CRITICAL: Test concurrent availability checks with mocked failing imports."""
        config = OrchestrationConfig()
        
        # Mock imports to sometimes fail, sometimes succeed (flaky imports)
        call_count = {'count': 0}
        
        def flaky_orchestrator_check():
            call_count['count'] += 1
            if call_count['count'] % 3 == 0:  # Fail every 3rd call
                return False, "Flaky import failure"
            else:
                return True, None
        
        with patch.object(config, '_check_orchestrator_availability', side_effect=flaky_orchestrator_check):
            results = []
            errors = []
            
            def check_availability():
                try:
                    config.refresh_availability(force=True)
                    result = config.orchestrator_available
                    results.append(result)
                    return result
                except Exception as e:
                    errors.append(e)
                    return None
            
            # Concurrent access with flaky imports
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(check_availability) for _ in range(50)]
                concurrent_results = [future.result() for future in as_completed(futures)]
            
            # Should not have errors even with flaky imports
            assert len(errors) == 0, f"Errors during concurrent flaky checks: {errors}"
            
            # Results should be boolean (not None)
            assert all(isinstance(r, bool) for r in concurrent_results), "Non-boolean results from availability check"
    
    def test_concurrent_cache_invalidation_and_refresh(self):
        """CRITICAL: Test concurrent cache invalidation doesn't corrupt state."""
        config = OrchestrationConfig()
        
        # Set up initial cached state
        config._availability_cache['orchestrator'] = True
        config._availability_cache['master_orchestration'] = False
        config._import_cache['TestAgent'] = Mock()
        config._import_errors['master_orchestration'] = "Initial error"
        
        def refresh_and_check():
            try:
                config.refresh_availability(force=True)
                # Immediately check availability
                orch_avail = config.orchestrator_available
                master_avail = config.master_orchestration_available
                errors = config.get_import_errors()
                cached = config.get_cached_import('TestAgent')
                return (orch_avail, master_avail, len(errors), cached)
            except Exception as e:
                return f"ERROR: {e}"
        
        # Many threads refreshing and checking concurrently
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(refresh_and_check) for _ in range(30)]
            results = [future.result() for future in as_completed(futures)]
        
        # No results should be errors
        error_results = [r for r in results if isinstance(r, str) and r.startswith("ERROR")]
        assert len(error_results) == 0, f"Concurrent cache operations had errors: {error_results}"
        
        # All results should be tuples with expected types
        valid_results = [r for r in results if isinstance(r, tuple) and len(r) == 4]
        assert len(valid_results) == len(results), "Some results had unexpected format"
    
    def test_deadlock_prevention_in_nested_calls(self):
        """CRITICAL: Test that nested calls don't cause deadlocks."""
        config = OrchestrationConfig()
        
        # Mock method that tries to call another availability check (nested call)
        def nested_availability_check():
            # This could potentially deadlock if locks aren't reentrant
            master_avail = config.master_orchestration_available
            background_avail = config.background_e2e_available
            return True, f"Nested calls: master={master_avail}, bg={background_avail}"
        
        with patch.object(config, '_check_orchestrator_availability', side_effect=nested_availability_check):
            config._availability_cache['orchestrator'] = None
            
            # This should not deadlock
            start_time = time.time()
            result = config.orchestrator_available
            end_time = time.time()
            
            # Should complete quickly (no deadlock)
            assert end_time - start_time < 1.0, "Potential deadlock detected in nested calls"
            assert isinstance(result, bool), "Nested call returned invalid result"
    
    def test_thread_local_state_isolation(self):
        """CRITICAL: Test that threads don't interfere with each other's state."""
        config = OrchestrationConfig()
        
        thread_results = {}
        
        def thread_specific_test(thread_id):
            try:
                # Each thread sets different environment overrides
                thread_env = {f'ORCHESTRATION_ORCHESTRATOR_AVAILABLE': str(thread_id % 2 == 0).lower()}
                
                with patch.dict(os.environ, thread_env):
                    # Force refresh to pick up environment
                    config.refresh_availability(force=True)
                    
                    # Check availability
                    result = config.orchestrator_available
                    
                    # Store thread-specific result
                    thread_results[thread_id] = {
                        'availability': result,
                        'env_override': thread_id % 2 == 0,
                        'expected_match': result == (thread_id % 2 == 0)
                    }
                    
            except Exception as e:
                thread_results[thread_id] = {'error': str(e)}
        
        # Run multiple threads with different environment settings
        threads = []
        for i in range(10):
            thread = threading.Thread(target=thread_specific_test, args=(i,))
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify all threads completed successfully
        assert len(thread_results) == 10, "Not all threads completed"
        
        # Check for errors
        errors = [result.get('error') for result in thread_results.values() if 'error' in result]
        assert len(errors) == 0, f"Thread errors: {errors}"


@pytest.mark.mission_critical  
class TestMemoryLeaksAndResourceManagement:
    """Test memory leaks and resource management - INTENSIVE tests."""
    
    def test_singleton_memory_leak_under_load(self):
        """CRITICAL: Test singleton doesn't leak memory under heavy load."""
        # Enable memory tracing
        tracemalloc.start()
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create and destroy many references
        for i in range(1000):
            config = OrchestrationConfig()
            
            # Access various properties to exercise code paths
            _ = config.orchestrator_available
            _ = config.master_orchestration_available
            _ = config.get_availability_status()
            _ = config.get_available_features()
            
            # Force garbage collection periodically
            if i % 100 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        
        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 10MB)
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 10, f"Memory leak detected: {memory_increase_mb:.2f}MB increase"
        
        # Stop tracing
        tracemalloc.stop()
    
    def test_cache_memory_cleanup_on_refresh(self):
        """CRITICAL: Test cache memory is properly cleaned up on refresh."""
        config = OrchestrationConfig()
        
        # Fill caches with large mock objects
        large_mock = Mock()
        large_mock.large_data = 'x' * 1000000  # 1MB of data
        
        config._import_cache['LargeObject1'] = large_mock
        config._import_cache['LargeObject2'] = Mock()
        config._import_cache['LargeObject3'] = Mock()
        
        # Create weak references to track cleanup
        weak_refs = [weakref.ref(obj) for obj in config._import_cache.values()]
        
        # Refresh should clear cache
        config.refresh_availability(force=True)
        
        # Verify cache is empty
        assert len(config._import_cache) == 0, "Cache not properly cleared"
        
        # Force garbage collection
        del large_mock
        gc.collect()
        
        # Weak references should be dead (objects cleaned up)
        dead_refs = [ref() is None for ref in weak_refs]
        assert any(dead_refs), "Cached objects not properly garbage collected"
    
    def test_error_accumulation_memory_leak(self):
        """CRITICAL: Test error messages don't accumulate and cause memory leak."""
        config = OrchestrationConfig()
        
        # Generate many different error messages
        for i in range(1000):
            error_msg = f"Mock error {i}: " + "x" * 1000  # Large error messages
            config._import_errors[f'feature_{i}'] = error_msg
        
        # Initial error count
        initial_error_count = len(config._import_errors)
        assert initial_error_count == 1000
        
        # Refresh should clear errors
        config.refresh_availability(force=True)
        
        # Verify errors are cleared
        assert len(config._import_errors) == 0, "Error messages not properly cleared"
    
    def test_thread_safety_memory_corruption(self):
        """CRITICAL: Test thread safety doesn't cause memory corruption."""
        config = OrchestrationConfig()
        
        corruption_detected = {'value': False}
        
        def stress_test_memory():
            try:
                for _ in range(100):
                    # Rapid cache manipulation
                    config._availability_cache['test'] = True
                    config._import_cache['test'] = Mock()
                    config._import_errors['test'] = "test error"
                    
                    # Refresh periodically
                    if _ % 10 == 0:
                        config.refresh_availability(force=True)
                    
                    # Verify cache integrity
                    if not isinstance(config._availability_cache, dict):
                        corruption_detected['value'] = True
                        return
                    
                    if not isinstance(config._import_cache, dict):
                        corruption_detected['value'] = True
                        return
                        
            except Exception as e:
                corruption_detected['value'] = True
        
        # Run multiple threads stressing memory
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=stress_test_memory)
            threads.append(thread)
        
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no memory corruption detected
        assert not corruption_detected['value'], "Memory corruption detected during concurrent access"


@pytest.mark.mission_critical
class TestEnvironmentTamperingEdgeCases:
    """Test environment variable tampering and manipulation - DEVIOUS tests."""
    
    def test_environment_variable_injection_attack(self):
        """CRITICAL: Test protection against environment variable injection."""
        config = OrchestrationConfig()
        
        # Test various injection attempts
        malicious_values = [
            'true; rm -rf /',  # Command injection attempt
            'true\n\nexport MALICIOUS=1',  # Newline injection
            'true$(malicious_command)',  # Command substitution
            'true`malicious_command`',  # Backtick command substitution
            'true && malicious_command',  # Command chaining
            '"; malicious_command; echo "true',  # Quote breaking
        ]
        
        for malicious_value in malicious_values:
            with patch.dict(os.environ, {'ORCHESTRATION_ORCHESTRATOR_AVAILABLE': malicious_value}):
                # Should safely parse as False (invalid boolean)
                result = config._get_env_override('orchestrator')
                assert result is None or result is False, f"Malicious value '{malicious_value}' was not safely handled"
    
    def test_environment_variable_race_condition(self):
        """CRITICAL: Test race conditions with changing environment variables."""
        config = OrchestrationConfig()
        
        def change_env_repeatedly():
            for i in range(50):
                # Rapidly change environment variable
                os.environ['ORCHESTRATION_ORCHESTRATOR_AVAILABLE'] = str(i % 2 == 0).lower()
                time.sleep(0.001)  # Small delay to create race condition
        
        def check_availability_repeatedly():
            results = []
            for _ in range(50):
                config.refresh_availability(force=True)
                result = config.orchestrator_available
                results.append(result)
                time.sleep(0.001)
            return results
        
        # Start environment changer
        env_thread = threading.Thread(target=change_env_repeatedly)
        env_thread.start()
        
        # Check availability while environment is changing
        results = check_availability_repeatedly()
        
        # Wait for environment thread
        env_thread.join(timeout=5)
        
        # Results should all be boolean (no corruption from race condition)
        assert all(isinstance(r, bool) for r in results), "Race condition caused invalid results"
        
        # Clean up
        os.environ.pop('ORCHESTRATION_ORCHESTRATOR_AVAILABLE', None)
    
    def test_environment_variable_persistence_across_refresh(self):
        """CRITICAL: Test environment overrides persist correctly across refresh."""
        config = OrchestrationConfig()
        
        # Set environment override
        with patch.dict(os.environ, {'ORCHESTRATION_ORCHESTRATOR_AVAILABLE': 'false'}):
            # First check
            config.refresh_availability(force=True)
            result1 = config.orchestrator_available
            
            # Multiple refreshes
            for _ in range(10):
                config.refresh_availability(force=True)
            
            # Should still respect environment override
            result2 = config.orchestrator_available
            
            assert result1 == result2 == False, "Environment override not persistent across refreshes"
    
    def test_environment_override_precedence_with_flaky_imports(self):
        """CRITICAL: Test environment override precedence with unreliable imports."""
        config = OrchestrationConfig()
        
        # Mock flaky imports
        def flaky_import():
            import random
            if random.random() < 0.5:
                return True, None
            else:
                return False, "Random import failure"
        
        with patch.object(config, '_check_orchestrator_availability', side_effect=flaky_import):
            # Environment override should always win
            with patch.dict(os.environ, {'ORCHESTRATION_ORCHESTRATOR_AVAILABLE': 'true'}):
                # Multiple checks with flaky imports
                results = []
                for _ in range(20):
                    config.refresh_availability(force=True)
                    result = config.orchestrator_available
                    results.append(result)
                
                # Environment override should always be respected
                assert all(r == True for r in results), "Environment override not respected with flaky imports"


@pytest.mark.mission_critical
class TestInvalidConfigurationStates:
    """Test invalid configuration states and corruption - NASTY tests."""
    
    def test_corrupted_cache_state_recovery(self):
        """CRITICAL: Test recovery from corrupted cache state."""
        config = OrchestrationConfig()
        
        # Corrupt cache with invalid values
        config._availability_cache['orchestrator'] = "invalid_string"
        config._availability_cache['master_orchestration'] = 42
        config._availability_cache['background_e2e'] = []
        
        # Should recover gracefully
        try:
            result = config.orchestrator_available
            assert isinstance(result, bool), "Failed to recover from corrupted cache"
        except Exception as e:
            pytest.fail(f"Failed to recover from corrupted cache: {e}")
    
    def test_missing_cache_keys_recovery(self):
        """CRITICAL: Test recovery when cache keys are missing."""
        config = OrchestrationConfig()
        
        # Delete cache keys
        del config._availability_cache['orchestrator']
        config._availability_cache.pop('master_orchestration', None)
        
        # Should handle missing keys gracefully
        try:
            result = config.orchestrator_available
            assert isinstance(result, bool), "Failed to handle missing cache keys"
        except KeyError as e:
            pytest.fail(f"KeyError on missing cache keys: {e}")
    
    def test_corrupted_import_cache_recovery(self):
        """CRITICAL: Test recovery from corrupted import cache."""
        config = OrchestrationConfig()
        
        # Corrupt import cache
        config._import_cache['TestAgent'] = "not_a_class"
        config._import_cache['BadKey'] = None
        config._import_cache[42] = Mock()  # Invalid key type
        
        # Should handle corruption gracefully
        cached_import = config.get_cached_import('TestAgent')
        assert cached_import == "not_a_class", "Import cache handling changed unexpectedly"
        
        # Refresh should clear corruption
        config.refresh_availability(force=True)
        assert len(config._import_cache) == 0, "Corrupted cache not cleared"
    
    def test_invalid_error_state_handling(self):
        """CRITICAL: Test handling of invalid error states."""
        config = OrchestrationConfig()
        
        # Set invalid error states
        config._import_errors['orchestrator'] = None
        config._import_errors['master_orchestration'] = 42
        config._import_errors['background_e2e'] = ['list', 'of', 'errors']
        
        # Should handle gracefully
        errors = config.get_import_errors()
        assert isinstance(errors, dict), "Error handling failed"
        
        # Invalid error values should be handled
        for error_value in errors.values():
            # Should be string or at least convertible to string
            assert error_value is not None, "Null error values not handled"
    
    def test_concurrent_corruption_and_recovery(self):
        """CRITICAL: Test corruption and recovery under concurrent access."""
        config = OrchestrationConfig()
        
        corruption_errors = []
        
        def corrupt_state():
            try:
                # Randomly corrupt different parts of state
                import random
                
                for _ in range(50):
                    corruption_type = random.choice(['cache', 'imports', 'errors'])
                    
                    if corruption_type == 'cache':
                        config._availability_cache['orchestrator'] = random.choice([None, "invalid", 42, []])
                    elif corruption_type == 'imports':
                        config._import_cache['BadImport'] = random.choice([None, "string", 42])
                    elif corruption_type == 'errors':
                        config._import_errors['feature'] = random.choice([None, 42, []])
                    
                    time.sleep(0.001)
                    
            except Exception as e:
                corruption_errors.append(e)
        
        def access_state():
            try:
                for _ in range(50):
                    _ = config.orchestrator_available
                    _ = config.get_import_errors()
                    _ = config.get_cached_import('test')
                    config.refresh_availability(force=True)
                    time.sleep(0.001)
            except Exception as e:
                corruption_errors.append(e)
        
        # Run corruption and access concurrently
        corruption_thread = threading.Thread(target=corrupt_state)
        access_thread = threading.Thread(target=access_state)
        
        corruption_thread.start()
        access_thread.start()
        
        corruption_thread.join(timeout=5)
        access_thread.join(timeout=5)
        
        # Should handle corruption gracefully without errors
        assert len(corruption_errors) == 0, f"Concurrent corruption caused errors: {corruption_errors}"


@pytest.mark.mission_critical
class TestPerformanceDegradationEdgeCases:
    """Test performance degradation and resource exhaustion - STRESS tests."""
    
    def test_availability_check_performance_under_load(self):
        """CRITICAL: Test availability check performance doesn't degrade under load."""
        config = OrchestrationConfig()
        
        # Measure baseline performance
        start_time = time.time()
        for _ in range(100):
            _ = config.orchestrator_available
        baseline_time = time.time() - start_time
        
        # Add load and measure again
        config._import_cache.update({f'CachedItem{i}': Mock() for i in range(1000)})
        config._import_errors.update({f'Error{i}': f'Error message {i}' for i in range(100)})
        
        start_time = time.time()
        for _ in range(100):
            _ = config.orchestrator_available
        loaded_time = time.time() - start_time
        
        # Performance should not degrade significantly
        performance_ratio = loaded_time / baseline_time
        assert performance_ratio < 3.0, f"Performance degraded too much: {performance_ratio:.2f}x slower"
    
    def test_memory_usage_under_repeated_refresh(self):
        """CRITICAL: Test memory usage doesn't grow under repeated refresh."""
        config = OrchestrationConfig()
        process = psutil.Process()
        
        # Initial memory
        initial_memory = process.memory_info().rss
        
        # Repeated refresh with data accumulation
        for i in range(100):
            # Add some data
            config._import_cache[f'Item{i}'] = Mock()
            config._import_errors[f'Error{i}'] = f'Error message {i}' * 100
            
            # Refresh should clean up
            config.refresh_availability(force=True)
            
            # Periodic GC
            if i % 10 == 0:
                gc.collect()
        
        # Final memory check
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / (1024 * 1024)
        
        # Memory growth should be minimal
        assert memory_growth_mb < 5, f"Excessive memory growth: {memory_growth_mb:.2f}MB"
    
    def test_thread_contention_performance(self):
        """CRITICAL: Test performance under high thread contention."""
        config = OrchestrationConfig()
        
        results = []
        
        def timed_availability_check():
            start = time.time()
            result = config.orchestrator_available
            duration = time.time() - start
            results.append(duration)
            return result
        
        # High contention test
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(timed_availability_check) for _ in range(200)]
            for future in as_completed(futures):
                future.result()  # Ensure completion
        
        # Analyze performance results
        average_time = sum(results) / len(results)
        max_time = max(results)
        
        # Should complete quickly even under contention
        assert average_time < 0.01, f"Average check time too slow: {average_time:.4f}s"
        assert max_time < 0.1, f"Max check time too slow: {max_time:.4f}s"
    
    def test_cache_efficiency_with_large_datasets(self):
        """CRITICAL: Test cache efficiency with large datasets."""
        config = OrchestrationConfig()
        
        # Fill cache with large dataset
        large_cache = {f'Item{i}': Mock() for i in range(10000)}
        config._import_cache.update(large_cache)
        
        # Test cache lookup performance
        start_time = time.time()
        for i in range(1000):
            key = f'Item{i % 10000}'
            result = config.get_cached_import(key)
            assert result is not None, f"Cache lookup failed for {key}"
        end_time = time.time()
        
        # Cache lookups should be fast even with large cache
        total_time = end_time - start_time
        avg_lookup_time = total_time / 1000
        
        assert avg_lookup_time < 0.001, f"Cache lookup too slow: {avg_lookup_time:.6f}s per lookup"


if __name__ == "__main__":
    # Configure pytest for edge case testing
    pytest_args = [
        __file__,
        "-v",
        "-x",  # Stop on first failure
        "--tb=short",
        "-m", "mission_critical"
    ]
    
    print("Running BRUTAL SSOT Orchestration Edge Case Tests...")
    print("=" * 80)
    print("💥 EDGE CASE MODE: Testing race conditions, memory leaks, corruption")
    print("⚠️  WARNING: These tests may stress your system")
    print("=" * 80)
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 80)
        print("✅ ALL EDGE CASE TESTS PASSED")
        print("🛡️  SSOT Orchestration can handle EXTREME conditions")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ EDGE CASE TESTS FAILED")
        print("🚨 System VULNERABLE to edge conditions")
        print("=" * 80)
    
    sys.exit(result)