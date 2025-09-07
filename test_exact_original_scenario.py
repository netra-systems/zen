#!/usr/bin/env python3
"""
Test that reproduces the exact scenario from the original failing test.
This mirrors the exact code from test_singleton_behavior_under_concurrent_instantiation.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from shared.isolated_environment import get_env, IsolatedEnvironment

def test_exact_original_scenario():
    """Reproduce the exact original test scenario."""
    print("Reproducing exact original test scenario...")
    
    instances = []
    errors = []
    
    def create_instance_worker(thread_id: int) -> IsolatedEnvironment:
        """Worker that creates IsolatedEnvironment instances - EXACT COPY from original test."""
        try:
            # Multiple ways to get the instance - EXACT COPY
            instance1 = get_env()
            instance2 = IsolatedEnvironment()
            instance3 = IsolatedEnvironment.get_instance()
            
            # All should be the same object - EXACT COPY
            assert instance1 is instance2, f"Thread {thread_id}: instance1 is not instance2"
            assert instance1 is instance3, f"Thread {thread_id}: instance1 is not instance3"
            
            return instance1
            
        except Exception as e:
            errors.append(f"Thread {thread_id} error: {str(e)}")
            return None
    
    # Create instances concurrently - EXACT COPY
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(create_instance_worker, thread_id)
            for thread_id in range(10)
        ]
        
        for future in as_completed(futures):
            instance = future.result()
            if instance is not None:
                instances.append(instance)
    
    # Verify no errors occurred - EXACT COPY
    if len(errors) > 0:
        print(f"Singleton thread safety errors: {errors}")
        return False
    
    # Verify all instances are the same object - EXACT COPY
    if instances:
        first_instance = instances[0]
        for i, instance in enumerate(instances[1:], 1):
            if not (instance is first_instance):
                print(f"Singleton violation: instance {i} is not the same object as instance 0")
                print(f"  Instance 0 ID: {id(first_instance)}")
                print(f"  Instance {i} ID: {id(instance)}")
                return False
        
        print(f"SUCCESS: All {len(instances)} instances are identical (ID: {id(first_instance)})")
        return True
    else:
        print("ERROR: No instances created")
        return False

def analyze_singleton_state():
    """Analyze the current singleton state in detail."""
    print("\nDetailed singleton state analysis...")
    
    from shared.isolated_environment import _env_instance
    
    # Get instances through different methods
    instance_get_env = get_env()
    instance_direct = IsolatedEnvironment()
    instance_class_method = IsolatedEnvironment.get_instance()
    
    print(f"get_env() returns: ID {id(instance_get_env)}")
    print(f"IsolatedEnvironment() returns: ID {id(instance_direct)}")
    print(f"IsolatedEnvironment.get_instance() returns: ID {id(instance_class_method)}")
    print(f"Module _env_instance: ID {id(_env_instance)}")
    print(f"Class _instance: ID {id(IsolatedEnvironment._instance)}")
    
    # Verify all are the same
    all_same = (
        instance_get_env is instance_direct is instance_class_method is 
        _env_instance is IsolatedEnvironment._instance
    )
    
    print(f"All instances identical: {all_same}")
    
    if not all_same:
        print("DETAILED COMPARISON:")
        print(f"  get_env is direct: {instance_get_env is instance_direct}")
        print(f"  get_env is class_method: {instance_get_env is instance_class_method}")
        print(f"  get_env is _env_instance: {instance_get_env is _env_instance}")
        print(f"  get_env is class._instance: {instance_get_env is IsolatedEnvironment._instance}")
        print(f"  direct is class_method: {instance_direct is instance_class_method}")
        print(f"  direct is _env_instance: {instance_direct is _env_instance}")
        print(f"  direct is class._instance: {instance_direct is IsolatedEnvironment._instance}")
        print(f"  class_method is _env_instance: {instance_class_method is _env_instance}")
        print(f"  class_method is class._instance: {instance_class_method is IsolatedEnvironment._instance}")
        print(f"  _env_instance is class._instance: {_env_instance is IsolatedEnvironment._instance}")
    
    return all_same

if __name__ == "__main__":
    print("=== Exact Original Scenario Test ===")
    
    # Analyze singleton state first
    state_ok = analyze_singleton_state()
    
    # Run the exact test scenario
    test_passed = test_exact_original_scenario()
    
    overall_success = state_ok and test_passed
    
    print(f"\n=== RESULT: {'PASSED' if overall_success else 'FAILED'} ===")
    
    if not overall_success:
        print("Original test scenario would fail - singleton issue confirmed")
    else:
        print("Original test scenario passes - singleton working correctly")
    
    exit(0 if overall_success else 1)