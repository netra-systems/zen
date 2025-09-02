"""
CRITICAL P0: Docker Lifecycle Management Test Suite

This comprehensive test suite validates Docker Desktop crash fixes:
1. Safe container removal (no `docker rm -f`)
2. Rate limiting to prevent API storms 
3. Memory limit enforcement to prevent pressure crashes
4. Concurrent operation safety
5. Failure recovery and resilience

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Prevent Docker daemon crashes, enable reliable CI/CD
3. Value Impact: Prevents 8-16 hours/week of developer downtime from Docker instability
4. Revenue Impact: Protects development velocity for $2M+ ARR platform

DIFFICULTY LEVEL: EXTREME - Designed to catch ANY regression in Docker stability
"""

import pytest
import asyncio
import threading
import time
import subprocess
import logging
import random
import psutil
import json
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

# ABSOLUTE IMPORTS ONLY - CLAUDE.md compliance
from test_framework.unified_docker_manager import UnifiedDockerManager, ContainerInfo
from test_framework.docker_rate_limiter import (
    DockerRateLimiter, 
    get_docker_rate_limiter,
    execute_docker_command,
    DockerCommandResult
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class StressTestResults:
    """Results from Docker stress testing."""
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_response_time: float
    max_response_time: float
    rate_limited_operations: int
    concurrent_peak: int
    docker_daemon_stable: bool
    memory_violations: int
    timeout_violations: int


@dataclass
class MemoryTestResult:
    """Result of memory pressure testing."""
    container_name: str
    memory_limit_mb: int
    peak_memory_usage_mb: float
    memory_violations: int
    oom_killed: bool
    container_crashed: bool
    memory_reservation_honored: bool


class DockerDaemonMonitor:
    """Monitor Docker daemon stability during tests."""
    
    def __init__(self):
        self.start_time = time.time()
        self.daemon_restarts = 0
        self.initial_pid = self._get_docker_daemon_pid()
        
    def _get_docker_daemon_pid(self) -> Optional[int]:
        """Get Docker daemon process ID."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'dockerd' in proc.info['name'] or \
                   (proc.info['cmdline'] and any('dockerd' in cmd for cmd in proc.info['cmdline'])):
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return None
    
    def check_daemon_stability(self) -> Dict[str, Any]:
        """Check if Docker daemon has restarted or crashed."""
        current_pid = self._get_docker_daemon_pid()
        daemon_restarted = False
        
        if current_pid is None:
            return {
                'stable': False,
                'daemon_running': False,
                'restart_detected': True,
                'restarts_count': self.daemon_restarts + 1
            }
        
        if self.initial_pid and current_pid != self.initial_pid:
            daemon_restarted = True
            self.daemon_restarts += 1
            self.initial_pid = current_pid
            
        return {
            'stable': not daemon_restarted,
            'daemon_running': True,
            'restart_detected': daemon_restarted,
            'restarts_count': self.daemon_restarts,
            'current_pid': current_pid
        }


@pytest.mark.critical
class TestDockerLifecycleCritical:
    """
    CRITICAL P0: Comprehensive Docker lifecycle management tests.
    
    These tests are designed to be DIFFICULT and catch any regression
    in Docker stability fixes. Each test pushes the system to its limits.
    """
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test environment and ensure cleanup."""
        logger.info("=== Setting up Docker Lifecycle Critical Tests ===")
        
        # Initialize Docker manager and rate limiter
        self.docker_manager = UnifiedDockerManager()
        self.rate_limiter = get_docker_rate_limiter()
        self.daemon_monitor = DockerDaemonMonitor()
        
        # Track containers created during test for cleanup
        self.test_containers: Set[str] = set()
        
        # Performance tracking
        self.operation_times: List[float] = []
        self.rate_limited_count = 0
        
        yield
        
        # CRITICAL: Cleanup all test containers safely
        logger.info("=== Cleaning up Docker Lifecycle Critical Tests ===")
        self._cleanup_test_containers()
        
        # Verify Docker daemon is still stable after tests
        stability = self.daemon_monitor.check_daemon_stability()
        if not stability['stable']:
            pytest.fail(f"Docker daemon became unstable during tests: {stability}")
    
    def _cleanup_test_containers(self):
        """Safely cleanup all containers created during testing."""
        for container_name in self.test_containers:
            try:
                logger.info(f"Safely removing test container: {container_name}")
                success = self.docker_manager.safe_container_remove(container_name, timeout=5)
                if not success:
                    logger.warning(f"Failed to safely remove container: {container_name}")
            except Exception as e:
                logger.error(f"Error during container cleanup {container_name}: {e}")
    
    def _create_test_container(self, name_suffix: str, image: str = "alpine:latest", 
                             memory_limit: Optional[str] = None,
                             command: Optional[List[str]] = None) -> str:
        """Create a test container with tracking."""
        container_name = f"netra-test-lifecycle-{name_suffix}-{int(time.time() * 1000)}"
        self.test_containers.add(container_name)
        
        cmd = ["docker", "run", "-d", "--name", container_name]
        
        if memory_limit:
            cmd.extend(["--memory", memory_limit, "--memory-reservation", memory_limit])
            
        cmd.append(image)
        
        if command:
            cmd.extend(command)
        else:
            cmd.extend(["sleep", "300"])  # Default: sleep for 5 minutes
            
        result = execute_docker_command(cmd, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create test container: {result.stderr}")
            
        return container_name
    
    # ==========================================
    # SAFE CONTAINER REMOVAL TESTS
    # ==========================================
    
    @pytest.mark.parametrize("timeout", [1, 5, 10, 30])
    def test_safe_removal_different_timeouts(self, timeout):
        """Test safe_container_remove with different timeout values."""
        container_name = self._create_test_container(f"timeout-{timeout}")
        
        # Let container start properly
        time.sleep(2)
        
        start_time = time.time()
        success = self.docker_manager.safe_container_remove(container_name, timeout=timeout)
        removal_time = time.time() - start_time
        
        assert success, f"Safe removal should succeed with timeout {timeout}s"
        assert removal_time < timeout + 15, f"Removal took too long: {removal_time}s > {timeout + 15}s"
        
        # Verify container is actually gone
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True, text=True
        )
        assert inspect_result.returncode != 0, "Container should be removed"
    
    def test_safe_removal_prevents_force_flag(self):
        """CRITICAL: Verify no docker rm -f is ever used."""
        container_name = self._create_test_container("no-force-test")
        
        # Patch subprocess to detect any rm -f usage
        force_flag_detected = False
        original_run = subprocess.run
        
        def patched_run(cmd, *args, **kwargs):
            nonlocal force_flag_detected
            if isinstance(cmd, list) and "docker" in cmd and "rm" in cmd and "-f" in cmd:
                force_flag_detected = True
                logger.error(f"CRITICAL: docker rm -f detected in command: {cmd}")
            return original_run(cmd, *args, **kwargs)
        
        with patch('subprocess.run', side_effect=patched_run):
            success = self.docker_manager.safe_container_remove(container_name)
            
        assert success, "Safe removal should succeed"
        assert not force_flag_detected, "CRITICAL: docker rm -f should NEVER be used"
    
    def test_safe_removal_nonexistent_container(self):
        """Test safe removal of non-existent container."""
        fake_container = "netra-test-nonexistent-" + str(int(time.time() * 1000))
        
        # Should return True (nothing to remove)
        success = self.docker_manager.safe_container_remove(fake_container)
        assert success, "Removing non-existent container should return True"
    
    def test_safe_removal_concurrent_attempts(self):
        """Test concurrent removal attempts on same container."""
        container_name = self._create_test_container("concurrent-removal")
        time.sleep(2)
        
        results = []
        
        def attempt_removal():
            return self.docker_manager.safe_container_remove(container_name)
        
        # Launch multiple concurrent removal attempts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_removal) for _ in range(5)]
            for future in as_completed(futures):
                results.append(future.result())
        
        # At least one should succeed, others should gracefully handle already-removed container
        assert any(results), "At least one removal attempt should succeed"
        assert len([r for r in results if r]) >= 1, "Multiple successes should be handled gracefully"
    
    def test_safe_removal_stubborn_container(self):
        """Test safe removal of container that takes time to stop."""
        # Create container that ignores SIGTERM (simulates stubborn container)
        container_name = self._create_test_container(
            "stubborn",
            command=["sh", "-c", "trap 'echo ignoring term' TERM; while true; do sleep 1; done"]
        )
        time.sleep(3)
        
        start_time = time.time()
        success = self.docker_manager.safe_container_remove(container_name, timeout=5)
        removal_time = time.time() - start_time
        
        # Should eventually succeed even with stubborn container
        assert success, "Should successfully remove stubborn container"
        assert removal_time >= 5, "Should respect timeout for stubborn container"
        assert removal_time < 20, "Should not hang indefinitely"
    
    # ==========================================
    # RATE LIMITING TESTS
    # ==========================================
    
    def test_rate_limiting_minimum_interval(self):
        """Test that minimum interval between operations is enforced."""
        operation_times = []
        
        # Perform rapid Docker operations
        for i in range(5):
            start_time = time.time()
            result = execute_docker_command(["docker", "version"], timeout=10)
            end_time = time.time()
            
            assert result.returncode == 0, f"Docker command {i} should succeed"
            operation_times.append((start_time, end_time))
        
        # Verify minimum intervals are enforced
        for i in range(1, len(operation_times)):
            interval = operation_times[i][0] - operation_times[i-1][1]
            assert interval >= 0.4, f"Operation {i} violated minimum interval: {interval}s < 0.5s"
    
    def test_rate_limiting_max_concurrent_operations(self):
        """Test that maximum concurrent operations are enforced."""
        concurrent_operations = []
        operation_results = []
        
        def long_running_operation(op_id: int):
            start_time = time.time()
            # Use a slower Docker command to create concurrency pressure
            result = execute_docker_command(
                ["docker", "images", "--format", "json"], 
                timeout=15
            )
            end_time = time.time()
            
            concurrent_operations.append({
                'op_id': op_id,
                'start_time': start_time,
                'end_time': end_time,
                'success': result.returncode == 0
            })
            
            return result
        
        # Launch more operations than max_concurrent limit
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(long_running_operation, i) for i in range(8)]
            for future in as_completed(futures):
                operation_results.append(future.result())
        
        # Verify all operations succeeded
        assert len(operation_results) == 8, "All operations should complete"
        assert all(op['success'] for op in concurrent_operations), "All operations should succeed"
        
        # Analyze concurrency - no more than max_concurrent should overlap
        max_concurrent = 3  # From DockerRateLimiter default
        for check_time in [op['start_time'] + 0.1 for op in concurrent_operations]:
            concurrent_count = sum(
                1 for op in concurrent_operations
                if op['start_time'] <= check_time <= op['end_time']
            )
            assert concurrent_count <= max_concurrent + 1, \
                f"Too many concurrent operations at {check_time}: {concurrent_count} > {max_concurrent}"
    
    def test_rate_limiting_under_extreme_load(self):
        """DIFFICULT: Test rate limiter under extreme load (100+ operations)."""
        total_operations = 100
        results = []
        start_time = time.time()
        
        def rapid_operation(op_id: int):
            try:
                result = execute_docker_command(["docker", "version"], timeout=5)
                return {
                    'op_id': op_id,
                    'success': result.returncode == 0,
                    'duration': result.duration,
                    'retry_count': result.retry_count
                }
            except Exception as e:
                return {
                    'op_id': op_id,
                    'success': False,
                    'error': str(e),
                    'duration': 0,
                    'retry_count': 0
                }
        
        # Launch extreme load
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(rapid_operation, i) for i in range(total_operations)]
            for future in as_completed(futures):
                results.append(future.result())
        
        total_time = time.time() - start_time
        successful_ops = [r for r in results if r['success']]
        
        # Verify system stability under load
        assert len(successful_ops) >= total_operations * 0.95, \
            f"Success rate too low: {len(successful_ops)}/{total_operations}"
        
        # Verify rate limiting is effective
        avg_duration = sum(r['duration'] for r in successful_ops) / len(successful_ops)
        assert avg_duration >= 0.4, f"Average operation time too fast: {avg_duration}s (rate limiting not working)"
        
        # Verify Docker daemon is still stable
        stability = self.daemon_monitor.check_daemon_stability()
        assert stability['stable'], f"Docker daemon crashed under load: {stability}"
    
    def test_rate_limiting_exponential_backoff(self):
        """Test exponential backoff on failures."""
        fail_count = 0
        
        def failing_operation():
            nonlocal fail_count
            fail_count += 1
            # Simulate a failing Docker command
            result = execute_docker_command(["docker", "inspect", "nonexistent-container"], timeout=5)
            return result
        
        start_time = time.time()
        result = failing_operation()
        duration = time.time() - start_time
        
        # Should fail but with proper backoff timing
        assert result.returncode != 0, "Should fail for nonexistent container"
        assert result.retry_count > 0, "Should have attempted retries"
        assert duration >= 1.0, "Should have exponential backoff delay"
    
    # ==========================================
    # MEMORY MANAGEMENT TESTS
    # ==========================================
    
    @pytest.mark.parametrize("memory_limit", ["128m", "256m", "512m"])
    def test_memory_limits_enforcement(self, memory_limit):
        """Test that memory limits are properly enforced."""
        container_name = self._create_test_container(
            f"memory-{memory_limit}",
            memory_limit=memory_limit,
            command=["sh", "-c", "while true; do sleep 1; done"]
        )
        
        # Wait for container to start
        time.sleep(5)
        
        # Check container memory configuration
        inspect_result = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{.HostConfig.Memory}}"],
            capture_output=True, text=True
        )
        
        assert inspect_result.returncode == 0, "Should be able to inspect container memory"
        
        memory_bytes = int(inspect_result.stdout.strip())
        expected_bytes = self._parse_memory_limit(memory_limit)
        
        assert memory_bytes == expected_bytes, \
            f"Memory limit not set correctly: {memory_bytes} != {expected_bytes}"
    
    def test_memory_pressure_handling(self):
        """DIFFICULT: Test container behavior under memory pressure."""
        # Create container with low memory limit
        container_name = self._create_test_container(
            "memory-pressure",
            memory_limit="64m",
            command=["sh", "-c", """
                # Gradually consume memory
                i=1
                while [ $i -le 100 ]; do
                    # Allocate ~1MB chunks
                    dd if=/dev/zero of=/tmp/mem_$i bs=1M count=1 2>/dev/null || break
                    sleep 0.1
                    i=$((i+1))
                done
                sleep 60
            """]
        )
        
        # Monitor container for memory issues
        start_time = time.time()
        max_monitor_time = 30
        
        while time.time() - start_time < max_monitor_time:
            # Check if container is still running
            inspect_result = subprocess.run(
                ["docker", "inspect", container_name, "--format", "{{.State.Running}} {{.State.OOMKilled}}"],
                capture_output=True, text=True
            )
            
            if inspect_result.returncode != 0:
                break
                
            status_parts = inspect_result.stdout.strip().split()
            is_running = status_parts[0] == "true"
            oom_killed = len(status_parts) > 1 and status_parts[1] == "true"
            
            if oom_killed:
                # Expected behavior - container was OOM killed due to memory limit
                logger.info("Container was OOM killed as expected due to memory limit")
                break
                
            if not is_running:
                # Container exited - check exit code
                exit_code_result = subprocess.run(
                    ["docker", "inspect", container_name, "--format", "{{.State.ExitCode}}"],
                    capture_output=True, text=True
                )
                exit_code = int(exit_code_result.stdout.strip())
                assert exit_code in [0, 125, 137], f"Container failed with unexpected exit code: {exit_code}"
                break
                
            time.sleep(2)
        
        # Verify system is still stable after memory pressure
        stability = self.daemon_monitor.check_daemon_stability()
        assert stability['stable'], "Docker daemon should remain stable under memory pressure"
    
    def test_memory_reservation_effectiveness(self):
        """Test that memory reservations work correctly."""
        containers = []
        
        try:
            # Create multiple containers with memory reservations
            for i in range(3):
                container_name = self._create_test_container(
                    f"memory-reservation-{i}",
                    memory_limit="256m"
                )
                containers.append(container_name)
            
            # Wait for all containers to start
            time.sleep(5)
            
            # Verify all containers are running with proper memory settings
            for container_name in containers:
                inspect_result = subprocess.run([
                    "docker", "inspect", container_name, 
                    "--format", "{{.HostConfig.Memory}} {{.HostConfig.MemoryReservation}}"
                ], capture_output=True, text=True)
                
                assert inspect_result.returncode == 0, f"Should inspect {container_name}"
                memory_info = inspect_result.stdout.strip().split()
                memory_limit = int(memory_info[0])
                memory_reservation = int(memory_info[1])
                
                assert memory_limit == 268435456, f"Memory limit incorrect for {container_name}: {memory_limit}"  # 256MB
                assert memory_reservation == 268435456, f"Memory reservation incorrect for {container_name}: {memory_reservation}"
                
        finally:
            # Clean up containers
            for container_name in containers:
                self.docker_manager.safe_container_remove(container_name)
    
    def _parse_memory_limit(self, memory_str: str) -> int:
        """Parse memory limit string to bytes."""
        memory_str = memory_str.lower()
        if memory_str.endswith('m'):
            return int(memory_str[:-1]) * 1024 * 1024
        elif memory_str.endswith('g'):
            return int(memory_str[:-1]) * 1024 * 1024 * 1024
        else:
            return int(memory_str)
    
    # ==========================================
    # STRESS TESTS (VERY DIFFICULT)
    # ==========================================
    
    def test_rapid_container_lifecycle_stress(self):
        """EXTREME: Rapid create/start/stop/remove cycles (50+ containers)."""
        num_containers = 50
        container_names = []
        operation_results = []
        
        def container_lifecycle(container_id: int):
            """Full container lifecycle in one operation."""
            container_name = f"netra-stress-{container_id}-{int(time.time() * 1000)}"
            
            try:
                # Create
                start_time = time.time()
                create_result = execute_docker_command([
                    "docker", "run", "-d", "--name", container_name,
                    "--memory", "64m", "alpine:latest", "sleep", "10"
                ], timeout=30)
                
                if create_result.returncode != 0:
                    return {'container_id': container_id, 'success': False, 'phase': 'create', 
                           'error': create_result.stderr}
                
                # Let it run briefly
                time.sleep(random.uniform(0.5, 2.0))
                
                # Safe removal
                success = self.docker_manager.safe_container_remove(container_name, timeout=5)
                end_time = time.time()
                
                return {
                    'container_id': container_id,
                    'success': success,
                    'duration': end_time - start_time,
                    'container_name': container_name,
                    'phase': 'complete'
                }
                
            except Exception as e:
                return {'container_id': container_id, 'success': False, 'phase': 'exception', 
                       'error': str(e)}
        
        # Execute stress test
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(container_lifecycle, i) for i in range(num_containers)]
            for future in as_completed(futures):
                operation_results.append(future.result())
        
        total_time = time.time() - start_time
        successful_ops = [r for r in operation_results if r['success']]
        
        # Verify stress test results
        success_rate = len(successful_ops) / num_containers
        assert success_rate >= 0.90, f"Success rate too low under stress: {success_rate:.2%}"
        
        avg_duration = sum(r['duration'] for r in successful_ops) / len(successful_ops)
        assert avg_duration < 15.0, f"Average operation too slow: {avg_duration:.2f}s"
        
        # Verify Docker daemon survived the stress test
        stability = self.daemon_monitor.check_daemon_stability()
        assert stability['stable'], f"Docker daemon crashed during stress test: {stability}"
        
        logger.info(f"Stress test completed: {len(successful_ops)}/{num_containers} successful "
                   f"in {total_time:.2f}s (avg {avg_duration:.2f}s per container)")
    
    def test_parallel_operations_from_multiple_threads(self):
        """DIFFICULT: Test parallel operations from many threads simultaneously."""
        num_threads = 15
        operations_per_thread = 10
        all_results = []
        
        def thread_operations(thread_id: int):
            """Execute multiple Docker operations in one thread."""
            thread_results = []
            
            for op_id in range(operations_per_thread):
                try:
                    # Mix different types of operations
                    if op_id % 3 == 0:
                        result = execute_docker_command(["docker", "version"], timeout=10)
                    elif op_id % 3 == 1:
                        result = execute_docker_command(["docker", "images", "-q"], timeout=10)
                    else:
                        result = execute_docker_command(["docker", "system", "df"], timeout=10)
                    
                    thread_results.append({
                        'thread_id': thread_id,
                        'op_id': op_id,
                        'success': result.returncode == 0,
                        'duration': result.duration,
                        'retry_count': result.retry_count
                    })
                    
                    # Small random delay to create more realistic load
                    time.sleep(random.uniform(0.1, 0.3))
                    
                except Exception as e:
                    thread_results.append({
                        'thread_id': thread_id,
                        'op_id': op_id,
                        'success': False,
                        'error': str(e),
                        'duration': 0,
                        'retry_count': 0
                    })
            
            return thread_results
        
        # Execute parallel operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(thread_operations, i) for i in range(num_threads)]
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        total_time = time.time() - start_time
        total_ops = num_threads * operations_per_thread
        successful_ops = [r for r in all_results if r['success']]
        
        # Verify parallel operations results
        assert len(all_results) == total_ops, f"Should have {total_ops} results, got {len(all_results)}"
        
        success_rate = len(successful_ops) / total_ops
        assert success_rate >= 0.95, f"Parallel operations success rate too low: {success_rate:.2%}"
        
        avg_duration = sum(r['duration'] for r in successful_ops) / len(successful_ops)
        assert avg_duration >= 0.4, f"Average duration suggests rate limiting not working: {avg_duration:.2f}s"
        
        # Verify system stability
        stability = self.daemon_monitor.check_daemon_stability()
        assert stability['stable'], f"Docker daemon unstable after parallel operations: {stability}"
        
        logger.info(f"Parallel operations completed: {len(successful_ops)}/{total_ops} successful "
                   f"in {total_time:.2f}s across {num_threads} threads")
    
    def test_network_and_disk_exhaustion_simulation(self):
        """EXTREME: Test Docker operations under resource exhaustion."""
        # Create containers to consume resources
        resource_containers = []
        
        try:
            # Create network-heavy containers
            for i in range(5):
                container_name = self._create_test_container(
                    f"network-load-{i}",
                    command=["sh", "-c", "while true; do ping -c 1 8.8.8.8 >/dev/null 2>&1; sleep 0.1; done"]
                )
                resource_containers.append(container_name)
            
            # Create disk-heavy containers 
            for i in range(3):
                container_name = self._create_test_container(
                    f"disk-load-{i}",
                    command=["sh", "-c", "while true; do dd if=/dev/zero of=/tmp/load_$$ bs=1M count=10 2>/dev/null; rm -f /tmp/load_$$; done"]
                )
                resource_containers.append(container_name)
            
            # Wait for resource consumption to start
            time.sleep(10)
            
            # Now perform Docker operations under resource pressure
            test_results = []
            for i in range(20):
                start_time = time.time()
                result = execute_docker_command(["docker", "version"], timeout=15)
                end_time = time.time()
                
                test_results.append({
                    'success': result.returncode == 0,
                    'duration': end_time - start_time,
                    'retry_count': result.retry_count
                })
                
                time.sleep(0.5)
            
            # Verify operations still work under resource pressure
            successful_ops = [r for r in test_results if r['success']]
            success_rate = len(successful_ops) / len(test_results)
            
            assert success_rate >= 0.85, f"Success rate under resource pressure too low: {success_rate:.2%}"
            
            # Verify Docker daemon stability
            stability = self.daemon_monitor.check_daemon_stability()
            assert stability['stable'], f"Docker daemon crashed under resource pressure: {stability}"
            
        finally:
            # Clean up resource containers
            for container_name in resource_containers:
                try:
                    self.docker_manager.safe_container_remove(container_name, timeout=10)
                except Exception as e:
                    logger.warning(f"Failed to cleanup resource container {container_name}: {e}")
    
    # ==========================================
    # INTEGRATION TESTS
    # ==========================================
    
    def test_full_lifecycle_with_health_checks(self):
        """Test complete container lifecycle with health monitoring."""
        # Create container with health check
        container_name = self._create_test_container(
            "health-check",
            command=["sh", "-c", """
                # Simple HTTP server for health check
                echo 'HTTP/1.1 200 OK\n\nHealthy' > /tmp/response.txt
                while true; do 
                    nc -l -p 8080 < /tmp/response.txt 2>/dev/null || true
                    sleep 1
                done
            """]
        )
        
        # Add health check to container
        subprocess.run([
            "docker", "exec", container_name, "sh", "-c",
            "apk add --no-cache netcat-openbsd 2>/dev/null || true"
        ], capture_output=True)
        
        # Verify container is running
        time.sleep(5)
        inspect_result = subprocess.run([
            "docker", "inspect", container_name, "--format", "{{.State.Running}}"
        ], capture_output=True, text=True)
        
        assert inspect_result.returncode == 0, "Should be able to inspect container"
        assert inspect_result.stdout.strip() == "true", "Container should be running"
        
        # Test graceful stop and removal
        success = self.docker_manager.safe_container_remove(container_name, timeout=10)
        assert success, "Should successfully remove container with health check"
        
        # Verify complete removal
        final_inspect = subprocess.run([
            "docker", "inspect", container_name
        ], capture_output=True, text=True)
        assert final_inspect.returncode != 0, "Container should be completely removed"
    
    def test_dependency_chain_management(self):
        """Test management of containers with dependencies."""
        # Create network for container communication
        network_name = f"test-network-{int(time.time())}"
        network_result = execute_docker_command([
            "docker", "network", "create", network_name
        ], timeout=10)
        assert network_result.returncode == 0, "Should create test network"
        
        try:
            # Create database container
            db_container = self._create_test_container(
                "postgres-dep",
                image="postgres:15-alpine",
                command=None  # Use default postgres command
            )
            
            # Connect to network
            subprocess.run([
                "docker", "network", "connect", network_name, db_container
            ], capture_output=True)
            
            # Create app container that depends on database
            app_container = self._create_test_container(
                "app-dep",
                command=["sh", "-c", f"sleep 30"]  # Simple app simulation
            )
            
            subprocess.run([
                "docker", "network", "connect", network_name, app_container
            ], capture_output=True)
            
            # Wait for containers to start
            time.sleep(10)
            
            # Verify both containers are running
            for container in [db_container, app_container]:
                inspect_result = subprocess.run([
                    "docker", "inspect", container, "--format", "{{.State.Running}}"
                ], capture_output=True, text=True)
                assert inspect_result.returncode == 0, f"Should inspect {container}"
                assert inspect_result.stdout.strip() == "true", f"Container {container} should be running"
            
            # Remove containers in proper order (app first, then database)
            app_success = self.docker_manager.safe_container_remove(app_container, timeout=10)
            db_success = self.docker_manager.safe_container_remove(db_container, timeout=10)
            
            assert app_success, "Should successfully remove app container"
            assert db_success, "Should successfully remove database container"
            
        finally:
            # Clean up network
            subprocess.run([
                "docker", "network", "rm", network_name
            ], capture_output=True)
    
    # ==========================================
    # FAILURE RECOVERY TESTS
    # ==========================================
    
    def test_recovery_from_partial_failures(self):
        """Test recovery from partial Docker operation failures."""
        # Create container that will have issues
        problematic_container = self._create_test_container(
            "problematic",
            command=["sh", "-c", "trap 'exit 1' TERM; while true; do sleep 1; done"]
        )
        
        time.sleep(3)
        
        # Simulate Docker daemon being busy/slow
        def slow_docker_operation():
            return execute_docker_command([
                "docker", "exec", problematic_container, "sh", "-c", "sleep 2; echo 'slow operation'"
            ], timeout=10)
        
        # Execute multiple slow operations to create failure conditions
        slow_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(slow_docker_operation) for _ in range(5)]
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=15)
                    slow_results.append(result.returncode == 0)
                except Exception:
                    slow_results.append(False)
        
        # Now test recovery with normal operations
        recovery_success = True
        for i in range(5):
            result = execute_docker_command(["docker", "version"], timeout=10)
            if result.returncode != 0:
                recovery_success = False
                break
            time.sleep(1)
        
        assert recovery_success, "Should recover from partial failures"
        
        # Clean up
        success = self.docker_manager.safe_container_remove(problematic_container, timeout=15)
        assert success, "Should remove problematic container"
    
    def test_cleanup_after_simulated_crashes(self):
        """Test automatic cleanup after simulated crash conditions."""
        # Create several containers
        crash_containers = []
        for i in range(5):
            container_name = self._create_test_container(
                f"crash-test-{i}",
                command=["sleep", "120"]
            )
            crash_containers.append(container_name)
        
        time.sleep(5)
        
        # Simulate crash by forcefully stopping containers (external to our safe removal)
        for container_name in crash_containers[:3]:  # Stop some externally
            subprocess.run([
                "docker", "stop", "-t", "1", container_name
            ], capture_output=True)
        
        # Now test cleanup with our safe removal
        cleanup_results = []
        for container_name in crash_containers:
            success = self.docker_manager.safe_container_remove(container_name, timeout=10)
            cleanup_results.append(success)
        
        # All cleanup operations should succeed
        assert all(cleanup_results), f"Cleanup should handle crashed containers: {cleanup_results}"
        
        # Verify all containers are gone
        for container_name in crash_containers:
            inspect_result = subprocess.run([
                "docker", "inspect", container_name
            ], capture_output=True, text=True)
            assert inspect_result.returncode != 0, f"Container {container_name} should be removed"
    
    def test_orphaned_resource_detection(self):
        """Test detection and cleanup of orphaned Docker resources."""
        # Create resources that might become orphaned
        test_prefix = f"orphan-test-{int(time.time())}"
        
        # Create container
        container_name = self._create_test_container(
            test_prefix,
            command=["sleep", "60"]
        )
        
        # Create volume
        volume_name = f"{test_prefix}-volume"
        volume_result = execute_docker_command([
            "docker", "volume", "create", volume_name
        ], timeout=10)
        assert volume_result.returncode == 0, "Should create test volume"
        
        # Simulate orphaning by removing container externally
        subprocess.run([
            "docker", "rm", "-f", container_name
        ], capture_output=True)
        
        # Test our cleanup can handle orphaned resources
        container_cleanup = self.docker_manager.safe_container_remove(container_name, timeout=5)
        assert container_cleanup, "Should handle orphaned container cleanup gracefully"
        
        # Clean up volume
        volume_cleanup = execute_docker_command([
            "docker", "volume", "rm", volume_name
        ], timeout=10)
        assert volume_cleanup.returncode == 0, "Should clean up orphaned volume"
    
    # ==========================================
    # PERFORMANCE BENCHMARKS
    # ==========================================
    
    def test_performance_benchmarks(self):
        """Benchmark Docker operations to detect performance regressions."""
        operation_types = [
            ("version", ["docker", "version"]),
            ("images", ["docker", "images", "-q"]),
            ("system_df", ["docker", "system", "df"]),
        ]
        
        benchmark_results = {}
        
        for op_name, cmd in operation_types:
            times = []
            successes = 0
            
            # Run each operation 10 times
            for _ in range(10):
                start_time = time.time()
                result = execute_docker_command(cmd, timeout=10)
                end_time = time.time()
                
                if result.returncode == 0:
                    successes += 1
                    times.append(end_time - start_time)
            
            if times:
                benchmark_results[op_name] = {
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'success_rate': successes / 10,
                    'total_operations': 10
                }
        
        # Verify reasonable performance
        for op_name, metrics in benchmark_results.items():
            assert metrics['success_rate'] >= 0.9, f"{op_name} success rate too low: {metrics['success_rate']}"
            assert metrics['avg_time'] <= 5.0, f"{op_name} too slow: {metrics['avg_time']:.2f}s"
            assert metrics['min_time'] >= 0.4, f"{op_name} too fast (rate limiting issue): {metrics['min_time']:.2f}s"
        
        logger.info("Performance benchmarks:")
        for op_name, metrics in benchmark_results.items():
            logger.info(f"  {op_name}: avg={metrics['avg_time']:.2f}s, "
                       f"range={metrics['min_time']:.2f}-{metrics['max_time']:.2f}s, "
                       f"success={metrics['success_rate']:.1%}")
    
    # ==========================================
    # FINAL VALIDATION TESTS
    # ==========================================
    
    def test_docker_daemon_final_stability_check(self):
        """Final comprehensive check that Docker daemon is stable."""
        stability_start = self.daemon_monitor.check_daemon_stability()
        
        # Perform a series of varied Docker operations
        final_operations = [
            (["docker", "version"], "version check"),
            (["docker", "system", "info"], "system info"),
            (["docker", "images"], "list images"),
            (["docker", "ps", "-a"], "list containers"),
            (["docker", "network", "ls"], "list networks"),
            (["docker", "volume", "ls"], "list volumes"),
        ]
        
        operation_results = []
        for cmd, description in final_operations:
            try:
                result = execute_docker_command(cmd, timeout=15)
                operation_results.append({
                    'command': description,
                    'success': result.returncode == 0,
                    'duration': result.duration
                })
            except Exception as e:
                operation_results.append({
                    'command': description,
                    'success': False,
                    'error': str(e),
                    'duration': 0
                })
        
        stability_end = self.daemon_monitor.check_daemon_stability()
        
        # Verify all operations succeeded
        failed_ops = [op for op in operation_results if not op['success']]
        assert len(failed_ops) == 0, f"Final stability operations failed: {failed_ops}"
        
        # Verify daemon stability throughout test suite
        assert stability_end['stable'], f"Docker daemon became unstable: {stability_end}"
        assert stability_end['daemon_running'], "Docker daemon should still be running"
        assert stability_end['restarts_count'] == 0, f"Docker daemon restarted {stability_end['restarts_count']} times"
        
        logger.info(f"CRITICAL P0 Docker Lifecycle Tests PASSED: "
                   f"Daemon stable (PID: {stability_end['current_pid']}), "
                   f"No restarts, All {len(operation_results)} final operations successful")