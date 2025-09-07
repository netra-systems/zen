#!/usr/bin/env python3
"""
Aggressive singleton thread safety test to reproduce potential race conditions.
This script attempts to stress-test the singleton pattern under high concurrency.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from shared.isolated_environment import IsolatedEnvironment, get_env

def stress_test_singleton_creation():
    """Stress test singleton creation under high concurrency."""
    print("Starting aggressive singleton thread safety test...")
    
    instances = []
    errors = []
    creation_times = []
    
    def create_instance_worker(thread_id: int) -> tuple:
        """Worker that creates instances and measures timing."""
        start_time = time.time()
        try:
            # Try multiple ways to get the instance in rapid succession
            for _ in range(10):
                instance1 = get_env()
                instance2 = IsolatedEnvironment()
                instance3 = IsolatedEnvironment.get_instance()
                
                # Check they're all the same
                if not (instance1 is instance2 is instance3):
                    errors.append(f"Thread {thread_id}: Instances not identical: "
                                f"get_env()={id(instance1)}, IsolatedEnvironment()={id(instance2)}, "
                                f"get_instance()={id(instance3)}")
                    return None, time.time() - start_time
                
                # Very short sleep to increase race condition chances
                time.sleep(0.0001)
            
            return instance1, time.time() - start_time
            
        except Exception as e:
            errors.append(f"Thread {thread_id} error: {str(e)}")
            return None, time.time() - start_time
    
    # High concurrency test
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(create_instance_worker, thread_id)
            for thread_id in range(100)  # 100 concurrent threads
        ]
        
        for future in as_completed(futures):
            instance, duration = future.result()
            if instance is not None:
                instances.append(instance)
                creation_times.append(duration)
    
    print(f"Completed stress test:")
    print(f"- Created {len(instances)} valid instances")
    print(f"- Found {len(errors)} errors")
    print(f"- Average creation time: {sum(creation_times) / len(creation_times):.4f}s" if creation_times else "N/A")
    print(f"- Max creation time: {max(creation_times):.4f}s" if creation_times else "N/A")
    
    if errors:
        print("\nERRORS FOUND:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Verify all instances are the same object
    if instances:
        first_instance = instances[0]
        unique_instances = set(id(inst) for inst in instances)
        
        print(f"\nSingleton verification:")
        print(f"- Total instances returned: {len(instances)}")
        print(f"- Unique instance IDs: {len(unique_instances)}")
        print(f"- First instance ID: {id(first_instance)}")
        
        if len(unique_instances) == 1:
            print("SINGLETON PATTERN WORKING CORRECTLY")
            return True
        else:
            print("SINGLETON PATTERN VIOLATION DETECTED!")
            print(f"  Found {len(unique_instances)} different instances:")
            for instance_id in unique_instances:
                count = sum(1 for inst in instances if id(inst) == instance_id)
                print(f"    Instance {instance_id}: {count} occurrences")
            return False
    else:
        print("No valid instances created!")
        return False

if __name__ == "__main__":
    success = stress_test_singleton_creation()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)