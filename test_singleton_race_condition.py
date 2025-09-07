#!/usr/bin/env python3
"""
Test to reproduce potential race condition between dual singleton patterns.
This test specifically targets the race between module-level and class-level singletons.
"""

import threading
import time
import sys
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_dual_singleton_race_condition():
    """Test for race conditions between module-level and class-level singletons."""
    print("Testing dual singleton race condition...")
    
    # First, let's verify the current state
    from shared.isolated_environment import IsolatedEnvironment, get_env, _env_instance
    
    print(f"Module-level instance ID: {id(_env_instance)}")
    print(f"Class-level instance ID: {id(IsolatedEnvironment._instance)}")
    print(f"get_env() returns ID: {id(get_env())}")
    
    # Check if they're the same
    module_instance = _env_instance
    class_instance = IsolatedEnvironment._instance
    get_env_instance = get_env()
    
    print(f"module_instance is class_instance: {module_instance is class_instance}")
    print(f"module_instance is get_env_instance: {module_instance is get_env_instance}")
    print(f"class_instance is get_env_instance: {class_instance is get_env_instance}")
    
    # Now test concurrent access to different entry points
    instances_collected = []
    errors = []
    
    def mixed_access_worker(thread_id: int):
        """Worker that uses different access methods."""
        try:
            results = []
            
            # Mix different access patterns
            if thread_id % 3 == 0:
                # Access via get_env()
                inst = get_env()
                results.append(("get_env", id(inst)))
            elif thread_id % 3 == 1:
                # Access via direct class instantiation
                inst = IsolatedEnvironment()
                results.append(("IsolatedEnvironment", id(inst)))
            else:
                # Access via class method
                inst = IsolatedEnvironment.get_instance()
                results.append(("get_instance", id(inst)))
            
            # Add some operations to increase race potential
            inst.set(f"TEST_VAR_{thread_id}", f"value_{thread_id}", f"thread_{thread_id}")
            retrieved = inst.get(f"TEST_VAR_{thread_id}")
            
            if retrieved != f"value_{thread_id}":
                errors.append(f"Thread {thread_id}: Data corruption detected")
            
            return results
            
        except Exception as e:
            errors.append(f"Thread {thread_id}: {str(e)}")
            return []
    
    # Run concurrent mixed access
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [
            executor.submit(mixed_access_worker, thread_id)
            for thread_id in range(60)
        ]
        
        for future in as_completed(futures):
            results = future.result()
            instances_collected.extend(results)
    
    # Analyze results
    print(f"\nCollected {len(instances_collected)} instance access results")
    print(f"Found {len(errors)} errors")
    
    if errors:
        print("ERRORS:")
        for error in errors[:5]:
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    # Group by access method
    by_method = {}
    for method, instance_id in instances_collected:
        if method not in by_method:
            by_method[method] = []
        by_method[method].append(instance_id)
    
    print(f"\nResults by access method:")
    unique_instance_ids = set()
    for method, instance_ids in by_method.items():
        unique_ids = set(instance_ids)
        unique_instance_ids.update(unique_ids)
        print(f"  {method}: {len(instance_ids)} calls, {len(unique_ids)} unique IDs")
        for uid in unique_ids:
            count = instance_ids.count(uid)
            print(f"    ID {uid}: {count} occurrences")
    
    print(f"\nOverall singleton analysis:")
    print(f"  Total unique instance IDs: {len(unique_instance_ids)}")
    
    if len(unique_instance_ids) == 1:
        print("  SINGLETON PATTERN WORKING: All access methods return same instance")
        return True
    else:
        print("  SINGLETON VIOLATION: Multiple instances detected!")
        print(f"  Instance IDs found: {unique_instance_ids}")
        return False

def test_import_race_condition():
    """Test race conditions during module reimport."""
    print("\nTesting import race condition...")
    
    # This test tries to catch race conditions during module loading
    def reimport_worker(thread_id: int):
        """Worker that reimports and accesses the module."""
        try:
            # Force reimport (this is aggressive testing)
            if 'shared.isolated_environment' in sys.modules:
                # Get reference before reimport
                old_module = sys.modules['shared.isolated_environment']
                old_instance_id = id(old_module._env_instance)
                
                # Reimport
                importlib.reload(old_module)
                
                # Get new reference
                new_instance_id = id(old_module._env_instance)
                
                return (thread_id, old_instance_id, new_instance_id, old_instance_id == new_instance_id)
            else:
                return (thread_id, None, None, False)
                
        except Exception as e:
            return (thread_id, "error", str(e), False)
    
    # Note: This test is very aggressive and may cause issues
    # In normal operation, modules shouldn't be reimported concurrently
    print("Skipping import race condition test (too aggressive for production code)")
    return True

if __name__ == "__main__":
    print("=== Singleton Race Condition Testing ===")
    
    # Test 1: Mixed access patterns
    success1 = test_dual_singleton_race_condition()
    
    # Test 2: Import race (skipped for safety)
    success2 = test_import_race_condition()
    
    overall_success = success1 and success2
    print(f"\n=== FINAL RESULT: {'PASSED' if overall_success else 'FAILED'} ===")
    
    if not overall_success:
        print("RACE CONDITION DETECTED - Singleton pattern needs fixing")
    else:
        print("No race conditions detected in current implementation")
    
    exit(0 if overall_success else 1)