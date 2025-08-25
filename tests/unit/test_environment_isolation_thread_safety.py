"""Test thread safety of IsolatedEnvironment under concurrent access.

This test focuses on verifying that the IsolatedEnvironment implementation
maintains thread safety and data integrity under concurrent access patterns
that occur in production multi-threaded applications.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Stability and Risk Reduction
- Value Impact: Prevents race conditions and data corruption in environment management
- Strategic Impact: Critical for multi-threaded production stability

This addresses a gap in current test coverage - concurrent access thread safety.
"""

import os
import threading
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from unittest.mock import patch

from netra_backend.app.core.isolated_environment import get_env, IsolatedEnvironment


class TestEnvironmentIsolationThreadSafety:
    """Test thread safety of IsolatedEnvironment under concurrent access."""
    
    @pytest.fixture(autouse=True)
    def setup_isolation(self):
        """Setup isolated test environment."""
        # Get fresh environment instance
        env = get_env()
        
        # Enable isolation mode for testing
        env.enable_isolation()
        
        # Clear any existing isolated variables
        env.clear()
        
        yield env
        
        # Clean up after test
        env.disable_isolation()

    def test_concurrent_get_operations_thread_safe(self, setup_isolation):
        """Test that concurrent get operations are thread-safe."""
        env = setup_isolation
        
        # Set up test data
        test_vars = {
            f'THREAD_TEST_VAR_{i}': f'value_{i}' 
            for i in range(10)
        }
        
        for key, value in test_vars.items():
            env.set(key, value, 'test_setup')
        
        results = {}
        errors = []
        
        def concurrent_get_worker(thread_id: int) -> Dict[str, Any]:
            """Worker function for concurrent get operations."""
            thread_results = {}
            try:
                # Each thread performs multiple get operations
                for i in range(5):
                    for key, expected_value in test_vars.items():
                        retrieved_value = env.get(key)
                        thread_results[f'{key}_attempt_{i}'] = {
                            'expected': expected_value,
                            'retrieved': retrieved_value,
                            'thread_id': thread_id,
                            'attempt': i
                        }
                        
                        # Small delay to increase chance of race conditions
                        time.sleep(0.001)
                        
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                
            return thread_results
        
        # Execute concurrent get operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(concurrent_get_worker, thread_id)
                for thread_id in range(10)
            ]
            
            for future in as_completed(futures):
                thread_results = future.result()
                results.update(thread_results)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all get operations returned correct values
        for result_key, result_data in results.items():
            assert result_data['retrieved'] == result_data['expected'], (
                f"Thread safety violation: {result_key} returned {result_data['retrieved']}, "
                f"expected {result_data['expected']}"
            )

    def test_concurrent_set_operations_thread_safe(self, setup_isolation):
        """Test that concurrent set operations are thread-safe."""
        env = setup_isolation
        
        set_operations = []
        errors = []
        
        def concurrent_set_worker(thread_id: int) -> List[Dict[str, Any]]:
            """Worker function for concurrent set operations."""
            thread_operations = []
            try:
                # Each thread sets multiple variables
                for i in range(5):
                    key = f'THREAD_{thread_id}_VAR_{i}'
                    value = f'thread_{thread_id}_value_{i}'
                    source = f'thread_{thread_id}'
                    
                    env.set(key, value, source)
                    thread_operations.append({
                        'key': key,
                        'value': value,
                        'source': source,
                        'thread_id': thread_id
                    })
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                    
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                
            return thread_operations
        
        # Execute concurrent set operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(concurrent_set_worker, thread_id)
                for thread_id in range(8)
            ]
            
            for future in as_completed(futures):
                thread_operations = future.result()
                set_operations.extend(thread_operations)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all set operations took effect
        for operation in set_operations:
            retrieved_value = env.get(operation['key'])
            assert retrieved_value == operation['value'], (
                f"Set operation failed for {operation['key']}: "
                f"expected {operation['value']}, got {retrieved_value}"
            )

    def test_concurrent_mixed_operations_thread_safe(self, setup_isolation):
        """Test mixed concurrent operations (get/set/exists/delete) are thread-safe."""
        env = setup_isolation
        
        # Pre-populate some test variables
        base_vars = {f'BASE_VAR_{i}': f'base_value_{i}' for i in range(5)}
        for key, value in base_vars.items():
            env.set(key, value, 'test_setup')
        
        results = []
        errors = []
        
        def mixed_operations_worker(thread_id: int) -> Dict[str, Any]:
            """Worker performing mixed operations."""
            thread_results = {
                'get_results': [],
                'set_results': [],
                'exists_results': [],
                'delete_results': []
            }
            
            try:
                for i in range(3):
                    # Get operation
                    for key in base_vars.keys():
                        value = env.get(key)
                        thread_results['get_results'].append({
                            'key': key,
                            'value': value,
                            'iteration': i
                        })
                    
                    # Set operation - create thread-specific variables
                    thread_key = f'THREAD_{thread_id}_ITER_{i}'
                    thread_value = f'value_{thread_id}_{i}'
                    env.set(thread_key, thread_value, f'thread_{thread_id}')
                    thread_results['set_results'].append({
                        'key': thread_key,
                        'value': thread_value
                    })
                    
                    # Exists operation
                    exists_key = list(base_vars.keys())[i % len(base_vars)]
                    exists_result = env.exists(exists_key)
                    thread_results['exists_results'].append({
                        'key': exists_key,
                        'exists': exists_result
                    })
                    
                    # Delete operation (only on thread-specific vars to avoid conflicts)
                    if i > 0:  # Don't delete on first iteration
                        delete_key = f'THREAD_{thread_id}_ITER_{i-1}'
                        env.delete(delete_key)
                        thread_results['delete_results'].append({
                            'key': delete_key,
                            'deleted': True
                        })
                    
                    time.sleep(0.001)  # Small delay
                    
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                
            return thread_results
        
        # Execute mixed concurrent operations
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(mixed_operations_worker, thread_id)
                for thread_id in range(6)
            ]
            
            for future in as_completed(futures):
                thread_results = future.result()
                results.append(thread_results)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors during mixed operations: {errors}"
        
        # Verify base variables still exist and have correct values
        for key, expected_value in base_vars.items():
            actual_value = env.get(key)
            assert actual_value == expected_value, (
                f"Base variable corrupted: {key} = {actual_value}, expected {expected_value}"
            )
        
        # Verify set operations took effect (check a few samples)
        for result in results[:3]:  # Check first 3 threads
            for set_result in result['set_results']:
                if env.exists(set_result['key']):  # May have been deleted by same thread
                    actual_value = env.get(set_result['key'])
                    assert actual_value == set_result['value'], (
                        f"Thread-specific set operation failed: {set_result['key']}"
                    )

    def test_isolation_mode_toggle_thread_safe(self, setup_isolation):
        """Test that toggling isolation mode is thread-safe."""
        env = setup_isolation
        
        # Start in isolation mode (from fixture)
        assert env.is_isolated()
        
        # Set some variables in isolation mode
        env.set('ISOLATION_TEST_VAR', 'isolated_value', 'test')
        
        toggle_results = []
        errors = []
        
        def isolation_toggle_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that toggles isolation mode and tests behavior."""
            thread_results = {
                'toggle_attempts': 0,
                'get_results': [],
                'isolation_states': []
            }
            
            try:
                for i in range(3):
                    # Record current isolation state
                    is_isolated = env.is_isolated()
                    thread_results['isolation_states'].append(is_isolated)
                    
                    # Get variable value
                    value = env.get('ISOLATION_TEST_VAR')
                    thread_results['get_results'].append({
                        'iteration': i,
                        'value': value,
                        'was_isolated': is_isolated
                    })
                    
                    # Only even-numbered threads try to toggle isolation
                    if thread_id % 2 == 0:
                        if is_isolated:
                            env.disable_isolation()
                        else:
                            env.enable_isolation()
                        thread_results['toggle_attempts'] += 1
                    
                    time.sleep(0.002)  # Small delay
                    
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                
            return thread_results
        
        # Execute concurrent isolation toggling
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(isolation_toggle_worker, thread_id)
                for thread_id in range(4)
            ]
            
            for future in as_completed(futures):
                thread_results = future.result()
                toggle_results.append(thread_results)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors during isolation toggle: {errors}"
        
        # Verify environment is still functional
        # The exact final state of isolation is unpredictable due to concurrent toggles,
        # but the environment should still work
        final_isolation_state = env.is_isolated()
        
        # Test that basic operations still work
        env.set('POST_TOGGLE_TEST', 'post_toggle_value', 'test')
        retrieved_value = env.get('POST_TOGGLE_TEST')
        assert retrieved_value == 'post_toggle_value', (
            f"Environment not functional after concurrent isolation toggles: "
            f"expected 'post_toggle_value', got {retrieved_value}"
        )

    def test_singleton_behavior_under_concurrent_instantiation(self):
        """Test that singleton behavior is maintained under concurrent instantiation."""
        instances = []
        errors = []
        
        def create_instance_worker(thread_id: int) -> IsolatedEnvironment:
            """Worker that creates IsolatedEnvironment instances."""
            try:
                # Multiple ways to get the instance
                instance1 = get_env()
                instance2 = IsolatedEnvironment()
                instance3 = IsolatedEnvironment.get_instance()
                
                # All should be the same object
                assert instance1 is instance2, f"Thread {thread_id}: instance1 is not instance2"
                assert instance1 is instance3, f"Thread {thread_id}: instance1 is not instance3"
                
                return instance1
                
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                return None
        
        # Create instances concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_instance_worker, thread_id)
                for thread_id in range(10)
            ]
            
            for future in as_completed(futures):
                instance = future.result()
                if instance is not None:
                    instances.append(instance)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Singleton thread safety errors: {errors}"
        
        # Verify all instances are the same object
        if instances:
            first_instance = instances[0]
            for i, instance in enumerate(instances[1:], 1):
                assert instance is first_instance, (
                    f"Singleton violation: instance {i} is not the same object as instance 0"
                )

    def test_subprocess_env_thread_safe(self, setup_isolation):
        """Test that get_subprocess_env() is thread-safe."""
        env = setup_isolation
        
        # Set up test environment variables
        test_vars = {
            f'SUBPROCESS_VAR_{i}': f'subprocess_value_{i}' 
            for i in range(5)
        }
        
        for key, value in test_vars.items():
            env.set(key, value, 'subprocess_test')
        
        subprocess_envs = []
        errors = []
        
        def get_subprocess_env_worker(thread_id: int) -> Dict[str, str]:
            """Worker that gets subprocess environment."""
            try:
                # Get subprocess environment multiple times
                env_results = []
                for i in range(3):
                    subprocess_env = env.get_subprocess_env()
                    env_results.append(subprocess_env)
                    time.sleep(0.001)
                
                return env_results
                
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")
                return []
        
        # Get subprocess environments concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(get_subprocess_env_worker, thread_id)
                for thread_id in range(5)
            ]
            
            for future in as_completed(futures):
                thread_env_results = future.result()
                subprocess_envs.extend(thread_env_results)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"get_subprocess_env thread safety errors: {errors}"
        
        # Verify all subprocess environments contain our test variables
        for subprocess_env in subprocess_envs:
            for key, expected_value in test_vars.items():
                assert key in subprocess_env, f"Missing {key} in subprocess environment"
                assert subprocess_env[key] == expected_value, (
                    f"Incorrect value for {key}: expected {expected_value}, "
                    f"got {subprocess_env[key]}"
                )
            
            # Verify critical system variables are present
            assert 'PATH' in subprocess_env, "PATH missing from subprocess environment"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])