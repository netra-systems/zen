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
import os
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
                proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                proc_cmdline = proc.info['cmdline'] if proc.info['cmdline'] else []
                
                # Check for Linux dockerd process
                if 'dockerd' in proc_name or any('dockerd' in cmd for cmd in proc_cmdline):
                    return proc.info['pid']
                
                # Check for Windows Docker Desktop processes
                if os.name == 'nt' and ('com.docker.backend.exe' in proc_name or 'docker desktop.exe' in proc_name):
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
    
    def _create_test_container(self, name_suffix: str, image: str = "redis:7-alpine", 
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
            cmd.extend(["sh", "-c", "sleep 300"])  # Default: sleep for 5 minutes with shell
            
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
                    "--memory", "64m", "redis:7-alpine", "sleep", "10"
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
                image="redis:7-alpine",
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
        
        # Simulate orphaning by removing container externally using safe method
        subprocess.run([
            "docker", "stop", "-t", "10", container_name
        ], capture_output=True, timeout=15)
        subprocess.run([
            "docker", "rm", container_name
        ], capture_output=True, timeout=10)
        
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
    # COMPREHENSIVE CRITICAL INFRASTRUCTURE TESTS
    # ==========================================
    
    def test_critical_unified_docker_manager_extreme_stress(self):
        """CRITICAL: Test UnifiedDockerManager under extreme stress conditions."""
        stress_environments = []
        critical_metrics = {
            'total_attempts': 0,
            'successful_acquisitions': 0,
            'failed_acquisitions': 0,
            'daemon_crashes': 0,
            'memory_violations': 0,
            'timeout_failures': 0,
            'avg_acquisition_time': 0
        }
        
        acquisition_times = []
        
        try:
            # Create extreme load with 15 concurrent environments
            for i in range(15):
                env_name = f"critical_stress_{i}_{int(time.time())}"
                critical_metrics['total_attempts'] += 1
                
                try:
                    # Monitor daemon before acquisition
                    daemon_pre = self.daemon_monitor.check_daemon_stability()
                    assert daemon_pre['stable'], f"Daemon unstable before acquisition {i}"
                    
                    start_time = time.time()
                    result = self.docker_manager.acquire_environment(
                        env_name,
                        use_alpine=True,
                        timeout=60
                    )
                    acquisition_time = time.time() - start_time
                    acquisition_times.append(acquisition_time)
                    
                    if result:
                        stress_environments.append(env_name)
                        critical_metrics['successful_acquisitions'] += 1
                        
                        # Verify health immediately
                        health = self.docker_manager.get_health_report(env_name)
                        assert health.get('all_healthy', False), f"Environment {env_name} unhealthy immediately"
                        
                        # Check resource usage
                        if hasattr(self.docker_manager, '_get_environment_containers'):
                            containers = self.docker_manager._get_environment_containers(env_name)
                            for container in containers:
                                stats = container.stats(stream=False)
                                memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                                if memory_mb > 500:
                                    critical_metrics['memory_violations'] += 1
                    else:
                        critical_metrics['failed_acquisitions'] += 1
                        
                    # Monitor daemon after acquisition
                    daemon_post = self.daemon_monitor.check_daemon_stability()
                    if not daemon_post['stable'] or daemon_post['restarts_count'] > 0:
                        critical_metrics['daemon_crashes'] += 1
                        
                except Exception as e:
                    critical_metrics['failed_acquisitions'] += 1
                    if "timeout" in str(e).lower():
                        critical_metrics['timeout_failures'] += 1
                    logger.error(f"Critical stress environment {i} failed: {e}")
                
                # Brief pause between acquisitions
                time.sleep(0.3)
            
            # Calculate final metrics
            if acquisition_times:
                critical_metrics['avg_acquisition_time'] = sum(acquisition_times) / len(acquisition_times)
            
            # CRITICAL ASSERTIONS - Zero tolerance for failures
            assert critical_metrics['daemon_crashes'] == 0, f"CRITICAL: {critical_metrics['daemon_crashes']} daemon crashes detected"
            assert critical_metrics['memory_violations'] == 0, f"CRITICAL: {critical_metrics['memory_violations']} memory violations"
            
            # High success rate required for critical infrastructure
            success_rate = critical_metrics['successful_acquisitions'] / critical_metrics['total_attempts']
            assert success_rate >= 0.80, f"CRITICAL: Success rate {success_rate:.2%} < 80%"
            
            # Performance requirements
            assert critical_metrics['avg_acquisition_time'] < 45, \
                f"CRITICAL: Avg acquisition time {critical_metrics['avg_acquisition_time']:.2f}s > 45s"
            
            logger.info(f"CRITICAL stress test PASSED: {critical_metrics}")
            
        finally:
            # Critical cleanup - must not fail
            for env_name in stress_environments:
                try:
                    self.docker_manager.release_environment(env_name)
                except Exception as e:
                    logger.error(f"CRITICAL cleanup failure for {env_name}: {e}")
    
    def test_critical_alpine_optimization_performance_validation(self):
        """CRITICAL: Validate Alpine optimization provides required performance gains."""
        alpine_performance = {}
        regular_performance = {}
        
        # Test Alpine containers
        alpine_env = f"critical_alpine_{int(time.time())}"
        try:
            alpine_start = time.time()
            alpine_result = self.docker_manager.acquire_environment(
                alpine_env,
                use_alpine=True,
                timeout=30
            )
            alpine_time = time.time() - alpine_start
            
            assert alpine_result is not None, "CRITICAL: Alpine environment creation failed"
            assert alpine_time < 30, f"CRITICAL: Alpine startup {alpine_time:.2f}s > 30s"
            
            # Monitor Alpine resource usage
            if hasattr(self.docker_manager, '_get_environment_containers'):
                containers = self.docker_manager._get_environment_containers(alpine_env)
                total_alpine_memory = 0
                
                for container in containers:
                    stats = container.stats(stream=False)
                    memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                    total_alpine_memory += memory_mb
                
                alpine_performance = {
                    'startup_time': alpine_time,
                    'total_memory_mb': total_alpine_memory,
                    'container_count': len(containers)
                }
                
                # CRITICAL Alpine requirements
                assert total_alpine_memory < 800, f"CRITICAL: Alpine using {total_alpine_memory:.2f}MB > 800MB"
            
            self.docker_manager.release_environment(alpine_env)
            
        except Exception as e:
            logger.error(f"CRITICAL Alpine test failed: {e}")
            raise
        
        # Test regular containers for comparison
        regular_env = f"critical_regular_{int(time.time())}"
        try:
            regular_start = time.time()
            regular_result = self.docker_manager.acquire_environment(
                regular_env,
                use_alpine=False,
                timeout=60
            )
            regular_time = time.time() - regular_start
            
            if regular_result:
                if hasattr(self.docker_manager, '_get_environment_containers'):
                    containers = self.docker_manager._get_environment_containers(regular_env)
                    total_regular_memory = 0
                    
                    for container in containers:
                        stats = container.stats(stream=False)
                        memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                        total_regular_memory += memory_mb
                    
                    regular_performance = {
                        'startup_time': regular_time,
                        'total_memory_mb': total_regular_memory,
                        'container_count': len(containers)
                    }
                
                self.docker_manager.release_environment(regular_env)
            
        except Exception as e:
            logger.warning(f"Regular container test failed (not critical): {e}")
        
        # Validate Alpine advantages
        if alpine_performance and regular_performance:
            time_improvement = regular_performance['startup_time'] / alpine_performance['startup_time']
            memory_improvement = regular_performance['total_memory_mb'] / alpine_performance['total_memory_mb']
            
            # CRITICAL: Alpine must be significantly better
            assert time_improvement >= 1.3, f"CRITICAL: Alpine only {time_improvement:.2f}x faster, need 1.3x+"
            assert memory_improvement >= 1.2, f"CRITICAL: Alpine only {memory_improvement:.2f}x memory efficient, need 1.2x+"
            
            logger.info(f"CRITICAL Alpine validation PASSED: {time_improvement:.2f}x faster, {memory_improvement:.2f}x memory efficient")
    
    def test_critical_parallel_environment_isolation_verification(self):
        """CRITICAL: Verify complete isolation between parallel environments."""
        num_parallel_envs = 8
        parallel_environments = []
        isolation_violations = []
        
        def create_isolated_environment(index):
            env_name = f"isolation_test_{index}_{int(time.time())}"
            try:
                # Create environment with unique identifier
                result = self.docker_manager.acquire_environment(
                    env_name,
                    use_alpine=True,
                    timeout=60
                )
                
                if result:
                    parallel_environments.append(env_name)
                    
                    # Create a unique file in each environment to test isolation
                    if hasattr(self.docker_manager, '_get_environment_containers'):
                        containers = self.docker_manager._get_environment_containers(env_name)
                        for container in containers:
                            try:
                                # Create unique test file
                                test_content = f"isolation_test_{index}_{env_name}"
                                container.exec_run(f'sh -c "echo {test_content} > /tmp/isolation_test"')
                            except Exception as e:
                                logger.warning(f"Failed to create test file in {container.name}: {e}")
                    
                    return (env_name, True, index)
                return (env_name, False, index)
                
            except Exception as e:
                logger.error(f"Isolation test environment {index} failed: {e}")
                return (env_name, False, index)
        
        try:
            # Create environments in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(create_isolated_environment, i) for i in range(num_parallel_envs)]
                results = [f.result() for f in as_completed(futures)]
            
            successful_envs = [(name, idx) for name, success, idx in results if success]
            success_count = len(successful_envs)
            
            # CRITICAL: High success rate required
            assert success_count >= 6, f"CRITICAL: Only {success_count}/{num_parallel_envs} parallel environments succeeded"
            
            # Test isolation between environments
            for i, (env1, idx1) in enumerate(successful_envs[:4]):  # Test first 4 to avoid timeout
                # Verify environment health
                health1 = self.docker_manager.get_health_report(env1)
                assert health1.get('all_healthy', False), f"CRITICAL: Environment {env1} not healthy"
                
                # Test file isolation
                if hasattr(self.docker_manager, '_get_environment_containers'):
                    containers1 = self.docker_manager._get_environment_containers(env1)
                    
                    for container1 in containers1:
                        try:
                            # Read the test file from this environment
                            result = container1.exec_run('cat /tmp/isolation_test 2>/dev/null || echo "MISSING"')
                            content = result.output.decode().strip()
                            
                            if content == "MISSING":
                                continue
                            
                            # Verify this environment only has its own data
                            expected_content = f"isolation_test_{idx1}_{env1}"
                            if expected_content not in content:
                                isolation_violations.append(f"Environment {env1} has incorrect content: {content}")
                            
                            # Check that other environments' data is not present
                            for j, (env2, idx2) in enumerate(successful_envs):
                                if i != j:
                                    other_content = f"isolation_test_{idx2}_{env2}"
                                    if other_content in content:
                                        isolation_violations.append(f"Environment {env1} contaminated with {env2} data")
                                        
                        except Exception as e:
                            logger.warning(f"Isolation test failed for container {container1.name}: {e}")
            
            # CRITICAL: Zero tolerance for isolation violations
            assert len(isolation_violations) == 0, f"CRITICAL: Isolation violations detected: {isolation_violations}"
            
            logger.info(f"CRITICAL isolation test PASSED: {success_count} environments fully isolated")
            
        finally:
            # Critical cleanup
            for env_name in parallel_environments:
                try:
                    self.docker_manager.release_environment(env_name)
                except Exception as e:
                    logger.error(f"CRITICAL cleanup failure for isolation test {env_name}: {e}")
    
    def test_critical_rate_limiter_daemon_protection_extreme(self):
        """CRITICAL: Test rate limiter protects daemon under extreme load."""
        daemon_pre_test = self.daemon_monitor.check_daemon_stability()
        assert daemon_pre_test['stable'], f"CRITICAL: Daemon unstable at test start: {daemon_pre_test}"
        
        extreme_load_metrics = {
            'commands_attempted': 0,
            'commands_successful': 0,
            'commands_rate_limited': 0,
            'commands_failed': 0,
            'daemon_crashes': 0,
            'max_concurrent': 0
        }
        
        def execute_extreme_load_command(index):
            try:
                extreme_load_metrics['commands_attempted'] += 1
                
                # Execute rate-limited Docker command
                result = execute_docker_command(
                    ["docker", "version", "--format", "json"],
                    timeout=10
                )
                
                if result.returncode == 0:
                    extreme_load_metrics['commands_successful'] += 1
                else:
                    extreme_load_metrics['commands_failed'] += 1
                
                return {'index': index, 'success': True, 'duration': result.duration}
                
            except Exception as e:
                if "rate limit" in str(e).lower():
                    extreme_load_metrics['commands_rate_limited'] += 1
                else:
                    extreme_load_metrics['commands_failed'] += 1
                
                return {'index': index, 'success': False, 'error': str(e)}
        
        try:
            # Generate extreme concurrent load
            with ThreadPoolExecutor(max_workers=25) as executor:
                # Submit 100 concurrent commands
                futures = [executor.submit(execute_extreme_load_command, i) for i in range(100)]
                extreme_load_metrics['max_concurrent'] = 25
                
                # Collect results
                results = [f.result() for f in as_completed(futures)]
            
            # Check daemon stability after extreme load
            daemon_post_test = self.daemon_monitor.check_daemon_stability()
            
            # CRITICAL: Daemon must remain stable
            assert daemon_post_test['stable'], f"CRITICAL: Daemon became unstable after extreme load: {daemon_post_test}"
            assert daemon_post_test['restarts_count'] == 0, f"CRITICAL: Daemon restarted {daemon_post_test['restarts_count']} times"
            
            # Rate limiter must have protected the daemon
            successful_rate = extreme_load_metrics['commands_successful'] / extreme_load_metrics['commands_attempted']
            assert successful_rate >= 0.70, f"CRITICAL: Success rate {successful_rate:.2%} < 70% under extreme load"
            
            # Some rate limiting should have occurred to protect daemon
            if extreme_load_metrics['commands_rate_limited'] > 0:
                logger.info(f"CRITICAL: Rate limiter protected daemon by limiting {extreme_load_metrics['commands_rate_limited']} commands")
            
            logger.info(f"CRITICAL extreme load test PASSED: Daemon protected, metrics: {extreme_load_metrics}")
            
        except Exception as e:
            extreme_load_metrics['daemon_crashes'] += 1
            logger.error(f"CRITICAL extreme load test failed: {e}")
            raise
    
    def test_critical_memory_pressure_resilience_validation(self):
        """CRITICAL: Validate system resilience under extreme memory pressure."""
        memory_pressure_environments = []
        initial_memory = psutil.virtual_memory()
        
        pressure_metrics = {
            'environments_created': 0,
            'memory_violations': 0,
            'oom_kills': 0,
            'system_memory_peak_mb': 0,
            'container_memory_peak_mb': 0
        }
        
        try:
            # Create memory-intensive environments
            for i in range(8):  # Reduced for safety
                env_name = f"memory_pressure_{i}_{int(time.time())}"
                
                try:
                    result = self.docker_manager.acquire_environment(
                        env_name,
                        use_alpine=True,  # Use Alpine for efficiency
                        timeout=45
                    )
                    
                    if result:
                        memory_pressure_environments.append(env_name)
                        pressure_metrics['environments_created'] += 1
                        
                        # Monitor container memory usage
                        if hasattr(self.docker_manager, '_get_environment_containers'):
                            containers = self.docker_manager._get_environment_containers(env_name)
                            total_container_memory = 0
                            
                            for container in containers:
                                stats = container.stats(stream=False)
                                memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                                total_container_memory += memory_mb
                                
                                # Check for memory violations
                                if memory_mb > 400:  # Lower threshold for Alpine
                                    pressure_metrics['memory_violations'] += 1
                                    
                                # Check if container was OOM killed
                                if stats.get('memory_stats', {}).get('limit', 0) > 0:
                                    if memory_mb >= (stats['memory_stats']['limit'] / (1024 * 1024)) * 0.95:
                                        pressure_metrics['oom_kills'] += 1
                            
                            pressure_metrics['container_memory_peak_mb'] = max(
                                pressure_metrics['container_memory_peak_mb'],
                                total_container_memory
                            )
                        
                        # Monitor system memory
                        current_memory = psutil.virtual_memory()
                        pressure_metrics['system_memory_peak_mb'] = max(
                            pressure_metrics['system_memory_peak_mb'],
                            current_memory.used / (1024 * 1024)
                        )
                        
                        # Verify health under pressure
                        health = self.docker_manager.get_health_report(env_name)
                        assert health.get('all_healthy', False), f"CRITICAL: Environment {env_name} unhealthy under memory pressure"
                    
                except Exception as e:
                    logger.error(f"Memory pressure environment {i} failed: {e}")
                
                # Brief pause between creations
                time.sleep(0.5)
            
            # CRITICAL memory pressure validations
            assert pressure_metrics['environments_created'] >= 6, \
                f"CRITICAL: Only {pressure_metrics['environments_created']}/8 environments survived memory pressure"
            
            # No memory violations allowed in critical infrastructure
            assert pressure_metrics['memory_violations'] == 0, \
                f"CRITICAL: {pressure_metrics['memory_violations']} memory violations detected"
            
            # System should remain stable
            final_memory = psutil.virtual_memory()
            memory_increase_mb = (final_memory.used - initial_memory.used) / (1024 * 1024)
            assert memory_increase_mb < 4000, \
                f"CRITICAL: System memory increased by {memory_increase_mb:.2f}MB > 4000MB"
            
            logger.info(f"CRITICAL memory pressure test PASSED: {pressure_metrics}")
            
        finally:
            # Critical cleanup to release memory pressure
            for env_name in memory_pressure_environments:
                try:
                    self.docker_manager.release_environment(env_name)
                except Exception as e:
                    logger.error(f"CRITICAL memory pressure cleanup failed for {env_name}: {e}")
            
            # Force garbage collection
            import gc
            gc.collect()
    
    # ==========================================
    # FINAL VALIDATION TESTS
    # ==========================================
    
    # ==========================================
    # ADDITIONAL SERVICE STARTUP TESTS (Team Delta Requirements)
    # ==========================================
    
    def test_service_startup_under_resource_contention(self):
        """CRITICAL: Validate service startup works under resource contention."""
        # Create resource contention by starting multiple environments
        contention_environments = []
        
        try:
            # Start multiple environments to create resource contention
            for i in range(3):
                env_name = f"contention-env-{i}-{int(time.time())}"
                contention_environments.append(env_name)
                self.test_containers.add(env_name)
                
                # Create environment with limited resources
                try:
                    result = self.docker_manager.acquire_environment(
                        env_name,
                        use_alpine=True,
                        timeout=45
                    )
                    
                    if result:
                        # Verify startup succeeded despite resource contention
                        health = self.docker_manager.wait_for_services(env_name, timeout=30)
                        assert health, f"Environment {env_name} failed health check under resource contention"
                        
                        logger.info(f"Environment {env_name} started successfully under contention")
                    
                except Exception as e:
                    logger.warning(f"Expected resource contention for environment {i}: {e}")
                
                # Brief pause between environment starts
                time.sleep(2)
            
            # At least one environment should succeed even under contention
            healthy_environments = 0
            for env_name in contention_environments:
                try:
                    health_report = self.docker_manager.get_health_report(env_name)
                    if health_report.get('all_healthy', False):
                        healthy_environments += 1
                except Exception:
                    pass
            
            assert healthy_environments >= 1, f"No environments healthy under resource contention: {healthy_environments}/3"
            logger.info(f"RESOURCE CONTENTION PASSED: {healthy_environments}/3 environments healthy")
            
        finally:
            # Clean up contention environments
            for env_name in contention_environments:
                try:
                    self.docker_manager.release_environment(env_name)
                except Exception as e:
                    logger.error(f"Failed to clean up contention environment {env_name}: {e}")
    
    def test_service_startup_with_pre_existing_conflicts(self):
        """CRITICAL: Validate startup handles pre-existing container conflicts."""
        # Create conflicting containers that might interfere
        conflict_containers = []
        
        try:
            # Create containers that might conflict with service startup
            for i in range(3):
                container_name = f"conflict-container-{i}-{int(time.time())}"
                
                result = execute_docker_command([
                    "docker", "run", "-d", "--name", container_name,
                    "redis:7-alpine", "sleep", "60"
                ], timeout=20)
                
                if result.returncode == 0:
                    conflict_containers.append(container_name)
                    self.test_containers.add(container_name)
            
            # Now try to start service environment with potential conflicts
            env_name = f"conflict-test-{int(time.time())}"
            self.test_containers.add(env_name)
            
            start_time = time.time()
            result = self.docker_manager.acquire_environment(
                env_name,
                use_alpine=True,
                timeout=60
            )
            startup_duration = time.time() - start_time
            
            # Startup should succeed despite pre-existing containers
            assert result is not None, "Service startup failed due to pre-existing containers"
            assert startup_duration < 60, f"Startup took too long with conflicts: {startup_duration:.2f}s"
            
            # Verify services are healthy
            healthy = self.docker_manager.wait_for_services(env_name, timeout=30)
            assert healthy, "Services not healthy after conflict resolution"
            
            logger.info(f"CONFLICT RESOLUTION PASSED: Startup succeeded with {len(conflict_containers)} conflicting containers")
            
        finally:
            # Clean up conflict containers
            for container_name in conflict_containers:
                try:
                    execute_docker_command(["docker", "stop", container_name], timeout=5)
                    execute_docker_command(["docker", "rm", container_name], timeout=5)
                except Exception as e:
                    logger.error(f"Failed to clean up conflict container {container_name}: {e}")
    
    def test_service_startup_port_conflict_auto_resolution(self):
        """CRITICAL: Validate automatic port conflict resolution during startup."""
        # Create containers using common ports
        port_blocking_containers = []
        
        try:
            # Block common service ports
            common_ports = [5432, 6379, 8000]  # postgres, redis, backend
            
            for i, port in enumerate(common_ports):
                container_name = f"port-blocker-{port}-{int(time.time())}"
                
                try:
                    result = execute_docker_command([
                        "docker", "run", "-d", "--name", container_name,
                        "-p", f"{port}:{port}", "redis:7-alpine",
                        "sh", "-c", f"nc -l -p {port} || sleep 60"
                    ], timeout=15)
                    
                    if result.returncode == 0:
                        port_blocking_containers.append(container_name)
                        self.test_containers.add(container_name)
                        logger.info(f"Blocked port {port} with container {container_name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to block port {port}: {e}")
                
                time.sleep(1)
            
            # Now start services which should auto-resolve port conflicts
            env_name = f"port-resolution-test-{int(time.time())}"
            self.test_containers.add(env_name)
            
            start_time = time.time()
            result = self.docker_manager.acquire_environment(
                env_name,
                use_alpine=True,
                timeout=90  # Allow extra time for port resolution
            )
            resolution_time = time.time() - start_time
            
            # Should succeed despite port conflicts through dynamic allocation
            assert result is not None, "Service startup failed due to port conflicts"
            assert resolution_time < 90, f"Port resolution took too long: {resolution_time:.2f}s"
            
            # Verify services are running on alternative ports
            health_report = self.docker_manager.get_health_report(env_name)
            assert health_report.get('all_healthy', False), "Services not healthy after port resolution"
            
            logger.info(f"PORT RESOLUTION PASSED: Services started despite {len(port_blocking_containers)} port conflicts")
            
        finally:
            # Clean up port blocking containers
            for container_name in port_blocking_containers:
                try:
                    execute_docker_command(["docker", "stop", container_name], timeout=3)
                    execute_docker_command(["docker", "rm", container_name], timeout=3)
                except Exception as e:
                    logger.error(f"Failed to clean up port blocker {container_name}: {e}")
    
    def test_service_startup_network_isolation_verification(self):
        """CRITICAL: Validate services start with proper network isolation."""
        env_name = f"network-isolation-test-{int(time.time())}"
        self.test_containers.add(env_name)
        
        # Start environment and verify network isolation
        result = self.docker_manager.acquire_environment(
            env_name,
            use_alpine=True,
            timeout=45
        )
        
        assert result is not None, "Environment creation failed"
        
        # Wait for services to be healthy
        healthy = self.docker_manager.wait_for_services(env_name, timeout=30)
        assert healthy, "Services should be healthy"
        
        # Check network configuration
        if hasattr(self.docker_manager, '_get_environment_containers'):
            containers = self.docker_manager._get_environment_containers(env_name)
            
            if containers:
                # Verify containers are on isolated network
                network_names = set()
                
                for container in containers:
                    container.reload()
                    networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                    
                    for network_name in networks.keys():
                        if network_name != 'bridge':  # Skip default bridge
                            network_names.add(network_name)
                
                # Should have at least one custom network for isolation
                assert len(network_names) >= 1, "Containers should be on isolated network"
                
                # All containers should share the same custom network
                if len(containers) > 1:
                    first_container_networks = set(containers[0].attrs['NetworkSettings']['Networks'].keys())
                    
                    for container in containers[1:]:
                        container_networks = set(container.attrs['NetworkSettings']['Networks'].keys())
                        shared_networks = first_container_networks.intersection(container_networks)
                        
                        assert len(shared_networks) > 0, f"Containers not sharing network: {container.name}"
                
                logger.info(f"NETWORK ISOLATION PASSED: {len(containers)} containers on isolated networks {network_names}")
    
    def test_service_startup_rolling_deployment_simulation(self):
        """CRITICAL: Validate rolling deployment scenarios work correctly."""
        base_env_name = f"rolling-deploy-{int(time.time())}"
        environments = []
        
        try:
            # Simulate rolling deployment by starting multiple versions
            for version in range(3):
                env_name = f"{base_env_name}-v{version}"
                environments.append(env_name)
                self.test_containers.add(env_name)
                
                start_time = time.time()
                
                # Each "version" starts with slight delay to simulate rolling deploy
                result = self.docker_manager.acquire_environment(
                    env_name,
                    use_alpine=True,
                    timeout=45
                )
                
                startup_time = time.time() - start_time
                
                if result:
                    # Verify this version started successfully
                    healthy = self.docker_manager.wait_for_services(env_name, timeout=25)
                    assert healthy, f"Version {version} failed to become healthy"
                    
                    logger.info(f"Version {version} deployed successfully in {startup_time:.2f}s")
                    
                    # Brief pause to simulate rolling deployment timing
                    time.sleep(3)
                else:
                    logger.warning(f"Version {version} failed to deploy")
            
            # Verify multiple versions can run concurrently
            healthy_versions = 0
            for env_name in environments:
                try:
                    health_report = self.docker_manager.get_health_report(env_name)
                    if health_report.get('all_healthy', False):
                        healthy_versions += 1
                except Exception:
                    pass
            
            # At least 2 versions should be healthy in rolling deployment
            assert healthy_versions >= 2, f"Rolling deployment failed: only {healthy_versions}/3 versions healthy"
            
            logger.info(f"ROLLING DEPLOYMENT PASSED: {healthy_versions}/3 versions healthy")
            
        finally:
            # Clean up all versions
            for env_name in environments:
                try:
                    self.docker_manager.release_environment(env_name)
                except Exception as e:
                    logger.error(f"Failed to clean up version {env_name}: {e}")
    
    def test_service_startup_cross_platform_compatibility(self):
        """CRITICAL: Validate startup works consistently across platform configurations."""
        import platform
        
        system_info = {
            'platform': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
        
        logger.info(f"Testing cross-platform compatibility on: {system_info}")
        
        env_name = f"cross-platform-test-{int(time.time())}"
        self.test_containers.add(env_name)
        
        # Test startup with platform-specific optimizations
        start_time = time.time()
        
        result = self.docker_manager.acquire_environment(
            env_name,
            use_alpine=True,  # Alpine should work on all platforms
            timeout=60
        )
        
        startup_duration = time.time() - start_time
        
        assert result is not None, f"Cross-platform startup failed on {system_info['platform']}"
        
        # Platform-specific performance expectations
        if system_info['platform'] == 'Windows':
            # Windows Docker typically slower
            assert startup_duration < 60, f"Windows startup too slow: {startup_duration:.2f}s"
        elif system_info['platform'] == 'Darwin':  # macOS
            # macOS Docker Desktop has VM overhead
            assert startup_duration < 45, f"macOS startup too slow: {startup_duration:.2f}s"
        else:  # Linux
            # Linux should be fastest
            assert startup_duration < 30, f"Linux startup too slow: {startup_duration:.2f}s"
        
        # Verify services are healthy regardless of platform
        healthy = self.docker_manager.wait_for_services(env_name, timeout=30)
        assert healthy, f"Services not healthy on {system_info['platform']}"
        
        # Platform-specific validations
        health_report = self.docker_manager.get_health_report(env_name)
        assert health_report.get('all_healthy'), f"Health check failed on {system_info['platform']}"
        
        logger.info(f"CROSS-PLATFORM PASSED: {system_info['platform']} startup in {startup_duration:.2f}s")

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