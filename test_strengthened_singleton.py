#!/usr/bin/env python3
"""
Test the strengthened singleton implementation.
Verifies enhanced thread safety and consistency monitoring.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from shared.isolated_environment import get_env, IsolatedEnvironment

def test_strengthened_singleton():
    """Test the strengthened singleton implementation under extreme concurrency."""
    print("Testing strengthened singleton implementation...")
    
    instances_collected = []
    errors = []
    consistency_checks = []
    
    def extreme_concurrency_worker(thread_id: int):
        """Worker that aggressively tests singleton under high concurrency."""
        try:
            thread_results = []
            
            # Rapid-fire instance creation (stress test the locking)
            for i in range(20):
                # Mix different access patterns rapidly
                if i % 4 == 0:
                    inst = get_env()
                    method = "get_env"
                elif i % 4 == 1:
                    inst = IsolatedEnvironment()
                    method = "IsolatedEnvironment"
                elif i % 4 == 2:
                    inst = IsolatedEnvironment.get_instance()
                    method = "get_instance"
                else:
                    # Test rapid successive calls
                    inst1 = get_env()
                    inst2 = IsolatedEnvironment()
                    inst3 = IsolatedEnvironment.get_instance()
                    
                    if not (inst1 is inst2 is inst3):
                        errors.append(f"Thread {thread_id}, iteration {i}: Rapid successive calls returned different instances")
                    
                    inst = inst1
                    method = "rapid_triple"
                
                thread_results.append((method, id(inst), thread_id, i))
                
                # Add some operations to increase contention
                inst.set(f"STRESS_TEST_{thread_id}_{i}", f"value_{thread_id}_{i}", f"thread_{thread_id}")
                
                # Very short sleep to increase race condition potential
                time.sleep(0.00001)  # 10 microseconds
            
            # Verify consistency at thread level
            unique_ids = set(result[1] for result in thread_results)
            if len(unique_ids) > 1:
                errors.append(f"Thread {thread_id}: Multiple instance IDs detected: {unique_ids}")
            
            consistency_checks.append((thread_id, len(unique_ids) == 1))
            
            return thread_results
            
        except Exception as e:
            errors.append(f"Thread {thread_id}: Exception - {str(e)}")
            return []
    
    # Extreme concurrency test - many threads, rapid execution
    print("Running extreme concurrency test...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(extreme_concurrency_worker, thread_id)
            for thread_id in range(100)  # 100 threads
        ]
        
        for future in as_completed(futures):
            thread_results = future.result()
            instances_collected.extend(thread_results)
    
    end_time = time.time()
    
    # Analyze results
    print(f"Completed extreme concurrency test in {end_time - start_time:.3f} seconds")
    print(f"Total instance accesses: {len(instances_collected)}")
    print(f"Total errors: {len(errors)}")
    
    if errors:
        print("ERRORS FOUND:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Analyze singleton consistency
    all_instance_ids = set(result[1] for result in instances_collected)
    print(f"Unique instance IDs found: {len(all_instance_ids)}")
    
    if len(all_instance_ids) == 1:
        instance_id = list(all_instance_ids)[0]
        print(f"SINGLETON CONSISTENCY VERIFIED: All accesses returned ID {instance_id}")
        
        # Verify thread-level consistency
        consistent_threads = sum(1 for _, consistent in consistency_checks if consistent)
        total_threads = len(consistency_checks)
        print(f"THREAD-LEVEL CONSISTENCY: {consistent_threads}/{total_threads} threads consistent")
        
        if consistent_threads == total_threads:
            print("PERFECT THREAD SAFETY: All threads saw consistent singleton")
            return True
        else:
            print("THREAD INCONSISTENCY: Some threads saw multiple IDs")
            return False
    else:
        print("SINGLETON VIOLATION: Multiple instance IDs detected")
        for instance_id in all_instance_ids:
            count = sum(1 for result in instances_collected if result[1] == instance_id)
            print(f"  ID {instance_id}: {count} occurrences")
        return False

def test_singleton_monitoring():
    """Test the singleton consistency monitoring features."""
    print("\nTesting singleton consistency monitoring...")
    
    from shared.isolated_environment import _env_instance
    
    # Verify current state
    get_env_instance = get_env()
    direct_instance = IsolatedEnvironment()
    class_method_instance = IsolatedEnvironment.get_instance()
    
    print(f"get_env() ID: {id(get_env_instance)}")
    print(f"IsolatedEnvironment() ID: {id(direct_instance)}")
    print(f"get_instance() ID: {id(class_method_instance)}")
    print(f"_env_instance ID: {id(_env_instance)}")
    print(f"cls._instance ID: {id(IsolatedEnvironment._instance)}")
    
    # Check all are identical
    all_identical = (
        get_env_instance is direct_instance is class_method_instance is
        _env_instance is IsolatedEnvironment._instance
    )
    
    print(f"All instances identical: {all_identical}")
    
    if all_identical:
        print("SINGLETON MONITORING: All access methods return same instance")
        return True
    else:
        print("SINGLETON MONITORING FAILED: Instances are not identical")
        return False

if __name__ == "__main__":
    print("=== Strengthened Singleton Testing ===")
    
    # Test 1: Extreme concurrency
    concurrency_passed = test_strengthened_singleton()
    
    # Test 2: Consistency monitoring
    monitoring_passed = test_singleton_monitoring()
    
    overall_success = concurrency_passed and monitoring_passed
    
    print(f"\n=== FINAL RESULT: {'PASSED' if overall_success else 'FAILED'} ===")
    
    if overall_success:
        print("Strengthened singleton implementation working perfectly!")
    else:
        print("Issues detected in strengthened singleton implementation")
    
    exit(0 if overall_success else 1)