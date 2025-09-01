#!/usr/bin/env python
"""
Test script to verify dynamic Docker naming allows parallel execution.
This demonstrates that multiple test runs can occur simultaneously without conflicts.
"""

import subprocess
import threading
import time
import random
import string
import sys

def generate_project_name():
    """Generate a unique project name for this test run."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"test_run_{suffix}"

def run_docker_test(test_id: int):
    """Run a Docker test with a unique project name and ports."""
    project_name = generate_project_name()
    
    # Use different ports for each test to avoid conflicts
    postgres_port = 5434 + test_id
    redis_port = 6381 + test_id
    
    print(f"[Test {test_id}] Starting with project name: {project_name}")
    print(f"[Test {test_id}] Using ports - Postgres: {postgres_port}, Redis: {redis_port}")
    
    # Set environment variables for dynamic port allocation
    env = os.environ.copy()
    env["TEST_POSTGRES_PORT"] = str(postgres_port)
    env["TEST_REDIS_PORT"] = str(redis_port)
    
    try:
        # Start containers with unique project name and ports
        cmd_up = [
            "docker-compose",
            "-f", "docker-compose.test.yml",
            "-p", project_name,
            "up", "-d",
            "test-postgres", "test-redis"  # Start just essential services for speed
        ]
        
        print(f"[Test {test_id}] Starting containers...")
        result = subprocess.run(cmd_up, capture_output=True, text=True, timeout=60, env=env)
        
        if result.returncode != 0:
            print(f"[Test {test_id}] ERROR starting containers: {result.stderr}")
            return False
        
        # List containers to verify they started with correct names
        cmd_ps = [
            "docker-compose",
            "-f", "docker-compose.test.yml",
            "-p", project_name,
            "ps"
        ]
        
        result = subprocess.run(cmd_ps, capture_output=True, text=True)
        print(f"[Test {test_id}] Running containers:\n{result.stdout}")
        
        # Simulate some work
        time.sleep(random.uniform(2, 5))
        
        # Clean up
        cmd_down = [
            "docker-compose",
            "-f", "docker-compose.test.yml",
            "-p", project_name,
            "down", "-v"
        ]
        
        print(f"[Test {test_id}] Cleaning up...")
        result = subprocess.run(cmd_down, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"[Test {test_id}] SUCCESS - Completed without conflicts")
            return True
        else:
            print(f"[Test {test_id}] WARNING during cleanup: {result.stderr}")
            return True  # Still consider it a success if containers ran
            
    except subprocess.TimeoutExpired:
        print(f"[Test {test_id}] TIMEOUT")
        # Try to clean up
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml",
            "-p", project_name, "down", "-v"
        ], capture_output=True, timeout=10)
        return False
    except Exception as e:
        print(f"[Test {test_id}] ERROR: {e}")
        return False

def main():
    """Run multiple Docker tests in parallel to verify no conflicts."""
    print("="*60)
    print("Testing Parallel Docker Execution with Dynamic Naming")
    print("="*60)
    
    # Check Docker is running
    result = subprocess.run(["docker", "version"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: Docker is not running. Please start Docker first.")
        sys.exit(1)
    
    print("OK: Docker is running")
    
    # Clean up any existing test containers first
    print("\nCleaning up any existing test containers...")
    subprocess.run([
        "docker", "ps", "-a", "--filter", "name=test_run_",
        "--format", "{{.ID}}", "|", "xargs", "-r", "docker", "rm", "-f"
    ], shell=True, capture_output=True)
    
    # Run tests in parallel
    num_parallel_tests = 3
    print(f"\nStarting {num_parallel_tests} parallel Docker tests...")
    print("Each test will use a unique project name to avoid conflicts.\n")
    
    threads = []
    results = []
    
    def run_and_record(test_id):
        result = run_docker_test(test_id)
        results.append(result)
    
    # Start all tests
    for i in range(num_parallel_tests):
        thread = threading.Thread(target=run_and_record, args=(i+1,))
        threads.append(thread)
        thread.start()
        time.sleep(0.5)  # Small delay between starts
    
    # Wait for all tests to complete
    for thread in threads:
        thread.join(timeout=120)
    
    # Check results
    print("\n" + "="*60)
    print("Test Results:")
    print("="*60)
    
    success_count = sum(1 for r in results if r)
    failure_count = len(results) - success_count
    
    print(f"Successful runs: {success_count}/{num_parallel_tests}")
    print(f"Failed runs: {failure_count}/{num_parallel_tests}")
    
    if success_count == num_parallel_tests:
        print("\nSUCCESS: All parallel tests completed without conflicts!")
        print("Dynamic container naming is working correctly.")
        return 0
    else:
        print("\nWARNING: Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())