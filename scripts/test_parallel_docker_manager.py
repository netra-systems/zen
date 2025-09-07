#!/usr/bin/env python3
"""
Test script to verify centralized Docker manager handles parallel test execution.
This simulates multiple test runners executing simultaneously to ensure no conflicts.
"""

import sys
import time
import subprocess
import threading
import random
from pathlib import Path
from datetime import datetime
import json
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import (
    UnifiedDockerManager, EnvironmentType, ServiceStatus, UnifiedDockerManager
)


class ParallelTestSimulator:
    """Simulates parallel test execution with Docker management."""
    
    def __init__(self, num_runners: int = 5):
        self.num_runners = num_runners
        self.results = []
        self.lock = threading.Lock()
    
    def run_test_instance(self, runner_id: int, use_shared: bool = True):
        """Simulate a single test runner instance."""
        start_time = time.time()
        result = {
            'runner_id': runner_id,
            'start_time': datetime.now().isoformat(),
            'errors': [],
            'success': False
        }
        
        try:
            # Determine environment type
            env_type = EnvironmentType.TEST if use_shared else EnvironmentType.DEDICATED
            
            print(f"[Runner {runner_id}] Starting with {env_type.value} environment")
            
            # Create Docker manager
            manager = UnifiedDockerManager(
                environment_type=env_type,
                test_id=f"runner_{runner_id}_{int(time.time())}",
                use_production_images=True
            )
            
            # Acquire environment
            print(f"[Runner {runner_id}] Acquiring Docker environment...")
            env_name, ports = manager.acquire_environment()
            result['environment'] = env_name
            result['ports'] = ports
            print(f"[Runner {runner_id}] Acquired environment: {env_name}")
            
            # Simulate test execution
            test_duration = random.uniform(5, 15)
            print(f"[Runner {runner_id}] Running tests for {test_duration:.1f} seconds...")
            time.sleep(test_duration)
            
            # Randomly simulate service issues (20% chance)
            if random.random() < 0.2:
                service = random.choice(['backend', 'auth', 'postgres'])
                print(f"[Runner {runner_id}] Simulating {service} service issue...")
                
                # Test restart with rate limiting
                success = manager.restart_service(service, force=False)
                if success:
                    print(f"[Runner {runner_id}] Successfully restarted {service}")
                else:
                    print(f"[Runner {runner_id}] Restart blocked by rate limiting for {service}")
                    result['errors'].append(f"Restart rate limited for {service}")
            
            # Check service status
            services_healthy = True
            for service in ['backend', 'auth', 'postgres', 'redis']:
                status = manager.get_service_status(service)
                if status != ServiceStatus.HEALTHY and status != ServiceStatus.UNKNOWN:
                    services_healthy = False
                    result['errors'].append(f"{service} not healthy: {status.value}")
            
            # Get statistics
            stats = manager.get_statistics()
            result['stats'] = stats
            
            # Release environment
            print(f"[Runner {runner_id}] Releasing environment...")
            manager.release_environment(env_name)
            
            result['success'] = services_healthy and len(result['errors']) == 0
            result['duration'] = time.time() - start_time
            
            print(f"[Runner {runner_id}] Completed {'successfully' if result['success'] else 'with errors'}")
            
        except Exception as e:
            result['errors'].append(str(e))
            result['duration'] = time.time() - start_time
            print(f"[Runner {runner_id}] Failed with error: {e}")
        
        # Store result
        with self.lock:
            self.results.append(result)
    
    def run_parallel_test(self):
        """Run multiple test instances in parallel."""
        print(f"\n{'='*60}")
        print(f"Starting parallel Docker manager test with {self.num_runners} runners")
        print(f"{'='*60}\n")
        
        threads = []
        
        # Mix of shared and dedicated environments
        for i in range(self.num_runners):
            # 70% use shared, 30% use dedicated
            use_shared = random.random() > 0.3
            
            thread = threading.Thread(
                target=self.run_test_instance,
                args=(i, use_shared)
            )
            threads.append(thread)
            
            # Start with slight delay to simulate realistic test startup
            thread.start()
            time.sleep(random.uniform(0.5, 2))
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze and report test results."""
        print(f"\n{'='*60}")
        print("PARALLEL TEST RESULTS")
        print(f"{'='*60}\n")
        
        successful = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - successful
        
        print(f"Total runners: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {successful/len(self.results)*100:.1f}%\n")
        
        # Show environment usage
        environments = {}
        for result in self.results:
            if 'environment' in result:
                env = result['environment']
                environments[env] = environments.get(env, 0) + 1
        
        print("Environment usage:")
        for env, count in environments.items():
            print(f"  {env}: {count} runners")
        
        # Show errors if any
        if failed > 0:
            print("\nErrors encountered:")
            for result in self.results:
                if not result['success']:
                    print(f"  Runner {result['runner_id']}: {', '.join(result['errors'])}")
        
        # Show restart statistics
        total_restarts = 0
        for result in self.results:
            if 'stats' in result and 'restart_counts' in result['stats']:
                for service, count in result['stats']['restart_counts'].items():
                    total_restarts += count
        
        print(f"\nTotal service restarts: {total_restarts}")
        
        # Show timing
        durations = [r['duration'] for r in self.results]
        print(f"\nExecution times:")
        print(f"  Min: {min(durations):.1f}s")
        print(f"  Max: {max(durations):.1f}s")
        print(f"  Avg: {sum(durations)/len(durations):.1f}s")
        
        # Final verdict
        print(f"\n{'='*60}")
        if successful == len(self.results):
            print("✅ ALL TESTS PASSED - No conflicts detected!")
        elif successful > len(self.results) * 0.8:
            print("⚠️ MOSTLY PASSED - Minor issues detected")
        else:
            print("❌ FAILURES DETECTED - Review error logs")
        print(f"{'='*60}\n")


def test_unified_runner_integration():
    """Test integration with unified test runner."""
    print("\n" + "="*60)
    print("TESTING UNIFIED TEST RUNNER INTEGRATION")
    print("="*60 + "\n")
    
    # Run a simple test with the new Docker manager flags
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "unified_test_runner.py"),
        "--category", "smoke",
        "--docker-production",  # Use production images
        "--docker-stats",  # Show statistics
        "--fast-fail"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Unified test runner integration successful")
    else:
        print("❌ Unified test runner integration failed")
        print(f"Error: {result.stderr}")
    
    return result.returncode == 0


def main():
    """Main test entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test centralized Docker manager with parallel execution"
    )
    parser.add_argument(
        "--runners",
        type=int,
        default=5,
        help="Number of parallel test runners (default: 5)"
    )
    parser.add_argument(
        "--test-unified",
        action="store_true",
        help="Also test unified test runner integration"
    )
    
    args = parser.parse_args()
    
    # Run parallel test
    simulator = ParallelTestSimulator(num_runners=args.runners)
    simulator.run_parallel_test()
    
    # Optionally test unified runner integration
    if args.test_unified:
        success = test_unified_runner_integration()
        if not success:
            sys.exit(1)
    
    # Check if all tests passed
    all_passed = all(r['success'] for r in simulator.results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()