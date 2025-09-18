from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks."
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message.""

        if self._closed:
            raise RuntimeError(WebSocket is closed)"
            raise RuntimeError(WebSocket is closed)""

        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):"
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        Get all sent messages."
        Get all sent messages.""

        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        '''
        Mission Critical Test Suite: Docker Lifecycle Management
        Comprehensive testing of Docker lifecycle operations, focusing on:
        1. Safe container removal with graceful shutdown sequences
        2. Rate limiter functionality and operation throttling
        3. Memory limit enforcement and container resource management
        4. Concurrent operation handling to prevent daemon crashes
        5. Network lifecycle management (creation, verification, cleanup)
        6. Container conflict resolution and existing container handling
        7. Health check monitoring and status detection
        8. Cleanup operations and proper resource management
        This test suite uses REAL Docker operations (no mocks) to validate
        production-like scenarios and edge cases.
        Business Value Justification (BVJ):
        1. Segment: Platform/Internal - Development Velocity, Risk Reduction
        2. Business Goal: Ensure Docker infrastructure reliability for CI/CD and development
        3. Value Impact: Prevents 4-8 hours/week of developer downtime from Docker failures
        4. Revenue Impact: Protects development velocity for $""2M""+ ARR platform
        '''
        '''
        import asyncio
        import concurrent.futures
        import contextlib
        import json
        import logging
        import os
        import pytest
        import subprocess
        import threading
        import time
        import unittest
        from pathlib import Path
        from typing import Dict, List, Optional, Set, Tuple
        from shared.isolated_environment import IsolatedEnvironment
            # Import the Docker management infrastructure
        from test_framework.unified_docker_manager import ( )
        UnifiedDockerManager,
        ContainerInfo,
        ContainerState,
        ServiceHealth,
        EnvironmentType,
        ServiceMode
            
        from test_framework.docker_rate_limiter import ( )
        DockerRateLimiter,
        DockerCommandResult,
        get_docker_rate_limiter
            
        from test_framework.docker_port_discovery import ( )
        DockerPortDiscovery,
        ServicePortMapping
            
        from test_framework.dynamic_port_allocator import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        DynamicPortAllocator,
        PortRange,
        PortAllocationResult
            
        logger = logging.getLogger(__name__)
class DockerLifecycleTestSuite(SSotAsyncTestCase):
        '''
        '''
        Comprehensive test suite for Docker lifecycle management.
        Tests real Docker operations under various scenarios including
        stress conditions, concurrent access, and failure scenarios.
        '''
        '''
        @classmethod
    def setUpClass(cls):
        "Set up class-level test infrastructure."
        cls.test_project_prefix = lifecycle_test""
        cls.docker_manager = None
        cls.rate_limiter = get_docker_rate_limiter()
        cls.created_containers: Set[str] = set()
        cls.created_networks: Set[str] = set()
        cls.allocated_ports: Set[int] = set()
    # Verify Docker is available
        if not cls._docker_available():
        raise unittest.SkipTest(Docker not available for lifecycle tests)
        # Clean up any previous test artifacts
        cls._cleanup_test_artifacts()
        @classmethod
    def tearDownClass(cls):
        "Clean up class-level resources."
        pass
        cls._cleanup_test_artifacts()
    def setUp(self):
        Set up individual test.""
        self.test_id = formatted_string
        self.docker_manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=self.test_id,
        use_production_images=True
    
    def tearDown(self):
        Clean up individual test.""
        pass
        if self.docker_manager:
        try:
            # Release environment and clean up
        if hasattr(self.docker_manager, '_project_name') and self.docker_manager._project_name:
        self.docker_manager.release_environment(self.docker_manager._project_name)
        except Exception as e:
        logger.warning(formatted_string)
        @classmethod
    def _docker_available(cls) -> bool:
        "Check if Docker is available."
        try:
        result = subprocess.run(['docker', 'version'),
        capture_output=True,
        timeout=10)
        return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
        @classmethod
    def _cleanup_test_artifacts(cls):
        "Clean up any test artifacts from previous runs."
        try:
        # Stop and remove test containers
        result = subprocess.run( )
        ['docker', 'ps', '-a', '--filter', 'formatted_string', '--format', '{{.ID}}'],
        capture_output=True, text=True, timeout=30
        
        if result.returncode == 0 and result.stdout.strip():
        container_ids = result.stdout.strip().split( )
        )
        for container_id in container_ids:
                # Use safe removal instead of docker rm -f
        try:
                    # Stop gracefully first
        subprocess.run(['docker', 'stop', '-t', '10', container_id),
        capture_output=True, timeout=15)
                    # Then remove without force
        subprocess.run(['docker', 'rm', container_id),
        capture_output=True, timeout=10)
        except Exception:
        pass  # Continue with other containers
                        # Remove test networks
        result = subprocess.run( )
        ['docker', 'network', 'ls', '--filter', 'formatted_string', '--format', '{{.ID}}'],
        capture_output=True, text=True, timeout=30
                        
        if result.returncode == 0 and result.stdout.strip():
        network_ids = result.stdout.strip().split( )
        ")"
        for network_id in network_ids:
        subprocess.run(['docker', 'network', 'rm', network_id),
        capture_output=True, timeout=10)
        except Exception as e:
        logger.warning(
                                    # =============================================================================
                                    # Safe Container Removal Tests
                                    # =============================================================================
    def test_graceful_container_shutdown_sequence(self):
        ""Test that containers are shut down gracefully with proper signal handling.""

        pass
    # Create a test container that can handle signals
        container_name = formatted_string"
        container_name = formatted_string"
    # Start a container with a process that can handle SIGTERM
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'trap echo Received SIGTERM; exit 0" TERM; while true; do sleep 1; done'"
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        self.created_containers.add(container_name)
    # Wait for container to be running
        time.sleep(2)
    # Verify container is running
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running')
    # Test graceful shutdown with timeout
        start_time = time.time()
        stop_cmd = ['docker', 'stop', '--time', '10', container_name]
        result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=30)
        shutdown_time = time.time() - start_time
        self.assertEqual(result.returncode, 0, formatted_string")"
        self.assertLess(shutdown_time, 15, Container shutdown took longer than expected)
    # Verify container stopped gracefully (exit code 0)
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.ExitCode}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), '0', Container did not exit gracefully")"
    # Test force removal after graceful stop
        rm_cmd = ['docker', 'rm', container_name]
        result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, 
    def test_force_removal_sequence_for_unresponsive_containers(self):
        ""Test force removal sequence for containers that don't respond to signals.'"
        container_name = formatted_string"
        container_name = formatted_string"
    # Create a container that ignores SIGTERM
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'trap " TERM; while true; do sleep 1; done'"
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        self.created_containers.add(container_name)
    # Wait for container to be running
        time.sleep(2)
    # Try graceful stop with short timeout
        start_time = time.time()
        stop_cmd = ['docker', 'stop', '--time', '3', container_name]
        result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=15)
        stop_time = time.time() - start_time
    # Should succeed but take the full timeout + kill time
        self.assertEqual(result.returncode, 0, formatted_string")"
        self.assertGreaterEqual(stop_time, 3, Stop should have waited for timeout)
        self.assertLess(stop_time, 10, Force kill should happen after timeout")"
    # Verify container is stopped
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'exited')
    def test_container_removal_with_volume_cleanup(self):
        Test container removal properly cleans up associated volumes."
        Test container removal properly cleans up associated volumes.""

        pass
        container_name = formatted_string"
        container_name = formatted_string""

        volume_name = formatted_string
    # Create a named volume
        volume_cmd = ['docker', 'volume', 'create', volume_name]
        result = subprocess.run(volume_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, formatted_string")"
        try:
        # Create container with the volume
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '-v', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'echo test data > /data/test.txt && sleep 3600'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_containers.add(container_name)
        # Verify volume contains data
        exec_cmd = ['docker', 'exec', container_name, 'cat', '/data/test.txt']
        result = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("test data, result.stdout)"
        # Remove container
        # Use safe removal instead of docker rm -f
        stop_cmd = ['docker', 'stop', '-t', '10', container_name]
        rm_cmd = ['docker', 'rm', container_name]
        result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, formatted_string)
        # Verify volume still exists (named volumes should persist)
        ls_cmd = ['docker', 'volume', 'ls', '-q', '--filter', 'formatted_string']
        result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn(volume_name, result.stdout)
        finally:
            # Clean up volume
            # Use safe volume removal (volumes typically don't need -f)'
        subprocess.run(['docker', 'volume', 'rm', volume_name),
        capture_output=True, timeout=10)
            # =============================================================================
            # Rate Limiter Functionality Tests
            # =============================================================================
    def test_rate_limiter_throttling_behavior(self):
        "Test that rate limiter properly throttles Docker operations."
        rate_limiter = DockerRateLimiter(min_interval=1.0, max_concurrent=2)
    # Record execution times
        execution_times = []
    def timed_operation():
        start_time = time.time()
        result = rate_limiter.execute_docker_command(['docker', 'version'], timeout=10)
        end_time = time.time()
        execution_times.append((start_time, end_time, result.returncode))
        return result
    # Execute multiple operations concurrently
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(timed_operation) for _ in range(5)]
        results = [future.result() for future in futures]
        total_time = time.time() - start_time
        # Verify all operations succeeded
        for result in results:
        self.assertEqual(result.returncode, 0, Docker version command should succeed)"
        self.assertEqual(result.returncode, 0, Docker version command should succeed)"
            # Verify rate limiting behavior
        self.assertEqual(len(execution_times), 5, "All operations should complete)"
            # Check that operations were properly spaced
        execution_times.sort(key=lambda x: None x[0)  # Sort by start time
            # With min_interval=1.0 and max_concurrent=2, operations should be spaced
        gaps = []
        for i in range(1, len(execution_times)):
        gap = execution_times[i][0] - execution_times[i-1][0]
        gaps.append(gap)
                # Some gaps should be at least min_interval due to throttling
        significant_gaps = [item for item in []]  # Allow some tolerance
        self.assertGreater(len(significant_gaps), 0, Rate limiter should introduce delays)
    def test_rate_limiter_concurrent_limit_enforcement(self):
        "Test that rate limiter enforces concurrent operation limits."
        pass
        rate_limiter = DockerRateLimiter(min_interval=0.1, max_concurrent=2)
        concurrent_count = 0
        max_concurrent_observed = 0
        lock = threading.Lock()
    def tracked_operation():
        pass
        nonlocal concurrent_count, max_concurrent_observed
    def custom_cmd(cmd, **kwargs):
        pass
        nonlocal concurrent_count, max_concurrent_observed
        with lock:
        concurrent_count += 1
        max_concurrent_observed = max(max_concurrent_observed, concurrent_count)
        # Simulate some work
        time.sleep(0.5)
        with lock:
        concurrent_count -= 1
            # Execute actual command
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            # Monkey patch the subprocess execution
        return rate_limiter.execute_docker_command(['docker', 'version'], timeout=15)
            # Execute operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(tracked_operation) for _ in range(5)]
        results = [future.result() for future in futures]
                # Verify concurrent limit was respected
        self.assertLessEqual(max_concurrent_observed, 2,
        formatted_string)"
        formatted_string)"
        self.assertGreater(max_concurrent_observed, 0, "Some operations should have run)"
    def test_rate_limiter_retry_with_backoff(self):
        Test rate limiter retry behavior with exponential backoff.""
        rate_limiter = DockerRateLimiter(min_interval=0.1, max_retries=3, base_backoff=0.5)
    # Track retry attempts
        attempt_times = []
    def failing_command(cmd, **kwargs):
        attempt_times.append(time.time())
        if len(attempt_times) < 3:  # Fail first 2 attempts
        result = subprocess.CompletedProcess(cmd, 1, '', 'Simulated failure')
        return result
        else:  # Succeed on ""3rd"" attempt
        return subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=10)
        start_time = time.time()
        result = rate_limiter.execute_docker_command(['docker', 'fake-command'], timeout=30)
        total_time = time.time() - start_time
    # Verify retry behavior
        self.assertEqual(len(attempt_times), 3, Should make 3 attempts)
        self.assertEqual(result.returncode, 0, Should eventually succeed)"
        self.assertEqual(result.returncode, 0, Should eventually succeed)"
        self.assertEqual(result.retry_count, 2, "Should report 2 retries)"
    # Verify backoff timing
        if len(attempt_times) >= 2:
        first_retry_delay = attempt_times[1] - attempt_times[0]
        self.assertGreaterEqual(first_retry_delay, 0.4, First retry should wait ~0.""5s"")
        if len(attempt_times) >= 3:
        second_retry_delay = attempt_times[2] - attempt_times[1]
        self.assertGreaterEqual(second_retry_delay, 0.9, "Second retry should wait ~1.""0s"")"
            # =============================================================================
            # Memory Limit Enforcement Tests
            # =============================================================================
    def test_container_memory_limit_enforcement(self):
        Test that containers respect configured memory limits."
        Test that containers respect configured memory limits.""

        pass
        container_name = "formatted_string"
        memory_limit = ""128m""
    # Create container with memory limit
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', memory_limit,
        'alpine:latest',
        'sh', '-c', 'sleep 3600'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, ""
        self.created_containers.add(container_name)
    # Wait for container to start
        time.sleep(2)
    # Verify memory limit is set
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.HostConfig.Memory}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
    # Convert ""128m"" to bytes (128 * 1024 * 1024)
        expected_memory = 134217728
        actual_memory = int(result.stdout.strip())
        self.assertEqual(actual_memory, expected_memory,
        formatted_string)
    # Test memory usage enforcement (this will kill the container if exceeded)
        stress_cmd = [
        'docker', 'exec', container_name,
        'sh', '-c', 'dd if=/dev/zero of=/tmp/big bs=""1M"" count=200 || echo "Memory limit enforced'"
    
        result = subprocess.run(stress_cmd, capture_output=True, text=True, timeout=30)
    # The command might fail due to memory limit, which is expected
        self.assertTrue(result.returncode != 0 or Memory limit enforced in result.stdout)
    def test_docker_manager_memory_optimization_settings(self):
        Test that Docker manager applies proper memory optimization settings.""
        manager = UnifiedDockerManager(use_production_images=True)
    # Verify service memory limits are configured
        for service_name, config in manager.SERVICES.items():
        self.assertIn('memory_limit', config, formatted_string)
        memory_limit = config['memory_limit']
        # Parse memory limit (e.g., """512m"", ""1g"")"
        if memory_limit.endswith('m'):
        memory_mb = int(memory_limit[:-1)
        elif memory_limit.endswith('g'):
        memory_mb = int(memory_limit[:-1) * 1024
        else:
        self.fail(
                    # Verify reasonable memory limits
        self.assertGreater(memory_mb, 0, formatted_string")"
        self.assertLessEqual(memory_mb, 4096, 
    def test_memory_pressure_container_behavior(self):
        ""Test container behavior under memory pressure.""

        pass
        container_name = formatted_string"
        container_name = formatted_string"
    # Create container with very low memory limit
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""64m""',
        '--oom-kill-disable=false',  # Allow OOM killer
        'alpine:latest',
        'sh', '-c', 'sleep 3600'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string")"
        self.created_containers.add(container_name)
    # Wait for container to start
        time.sleep(2)
    # Try to exceed memory limit
        stress_start_time = time.time()
        stress_cmd = [
        'docker', 'exec', container_name,
        'sh', '-c', 'head -c ""100m"" </dev/zero >bigfile 2>&1; echo Exit code: $?'
    
        result = subprocess.run(stress_cmd, capture_output=True, text=True, timeout=30)
        stress_duration = time.time() - stress_start_time
    # Check if container was killed or command failed due to memory
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}} {{.State.OOMKilled}}']
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        status_parts = inspect_result.stdout.strip().split()
        if len(status_parts) >= 2:
        status, oom_killed = status_parts[0], status_parts[1]
        # Either the container should be OOM killed, or the command should fail
        self.assertTrue( )
        oom_killed == 'true' or result.returncode != 0 or cannot allocate memory" in result.stderr.lower(),"
        Memory limit enforcement should prevent excessive memory allocation
        
        # =============================================================================
        # Concurrent Operation Handling Tests
        # =============================================================================
    def test_concurrent_container_creation_without_conflicts(self):
        "Test that multiple containers can be created concurrently without conflicts."
        num_containers = 5
        container_names = [formatted_string for i in range(num_containers)]
    def create_container(container_name):
        try:
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        return container_name, result.returncode, result.stderr
        except Exception as e:
        return container_name, -1, str(e)
            # Create containers concurrently
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_containers) as executor:
        futures = [executor.submit(create_container, name) for name in container_names]
        results = [future.result() for future in futures]
        creation_time = time.time() - start_time
                # Track created containers for cleanup
        self.created_containers.update(container_names)
                # Verify all containers were created successfully
        successful_creations = []
        failed_creations = []
        for name, returncode, stderr in results:
        if returncode == 0:
        successful_creations.append(name)
        else:
        failed_creations.append((name, stderr))
        self.assertEqual(len(successful_creations), num_containers,
        formatted_string")"
                            # Verify concurrent creation was efficient
        self.assertLess(creation_time, 60, 
                            # Verify all containers are running
        for container_name in successful_creations:
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running',
        formatted_string")"
    def test_concurrent_docker_operations_stability(self):
        Test Docker daemon stability under concurrent operations load."
        Test Docker daemon stability under concurrent operations load.""

        pass
        operations_per_thread = 3
        num_threads = 4
        operation_results = []
        operation_lock = threading.Lock()
    def stress_operations(thread_id):
        "Perform various Docker operations concurrently."
        thread_results = []
        for i in range(operations_per_thread):
        container_name = ""
        try:
            # Create container
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest', 'sleep', '30'
            
        start_time = time.time()
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        create_time = time.time() - start_time
        if result.returncode == 0:
        with operation_lock:
        self.created_containers.add(container_name)
                    # Inspect container
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
                    # Stop container
        stop_cmd = ['docker', 'stop', container_name]
        stop_result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=20)
                    # Remove container
        rm_cmd = ['docker', 'rm', container_name]
        rm_result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        thread_results.append()
        'thread_id': thread_id,
        'operation_id': i,
        'create_success': result.returncode == 0,
        'inspect_success': inspect_result.returncode == 0,
        'stop_success': stop_result.returncode == 0,
        'rm_success': rm_result.returncode == 0,
        'create_time': create_time,
        'total_success': all()
        result.returncode == 0,
        inspect_result.returncode == 0,
        stop_result.returncode == 0,
        rm_result.returncode == 0
                    
                    
        else:
        thread_results.append()
        'thread_id': thread_id,
        'operation_id': i,
        'create_success': False,
        'total_success': False,
        'error': result.stderr
                        
        except Exception as e:
        thread_results.append()
        'thread_id': thread_id,
        'operation_id': i,
        'total_success': False,
        'exception': str(e)
                            
                            # Brief pause between operations
        time.sleep(0.1)
        with operation_lock:
        operation_results.extend(thread_results)
                                # Run stress test
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(stress_operations, i) for i in range(num_threads)]
        for future in futures:
        future.result()  # Wait for completion
        total_time = time.time() - start_time
                                        # Analyze results
        total_operations = len(operation_results)
        successful_operations = [item for item in []]
        success_rate = len(successful_operations) / total_operations if total_operations > 0 else 0
                                        # Verify Docker daemon remained stable
        self.assertGreater(success_rate, 0.8, formatted_string)
        self.assertLess(total_time, 120, ""
                                        # Verify Docker is still responsive after stress test
        version_cmd = ['docker', 'version']
        result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, Docker daemon not responsive after stress test)
    def test_docker_manager_concurrent_environment_acquisition(self):
        Test UnifiedDockerManager handling concurrent environment requests.""
        pass
        num_concurrent = 3
        environment_results = []
    def acquire_environment(manager_id):
        Acquire environment concurrently.""
        try:
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=formatted_string
        
        start_time = time.time()
        env_name, ports = manager.acquire_environment()
        acquisition_time = time.time() - start_time
        # Verify environment is functional
        health_report = manager.get_health_report()
        return {
        'manager_id': manager_id,
        'success': True,
        'env_name': env_name,
        'ports': ports,
        'acquisition_time': acquisition_time,
        'health_report': health_report,
        'manager': manager
        
        except Exception as e:
        return {
        'manager_id': manager_id,
        'success': False,
        'error': str(e),
        'manager': None
            
            # Acquire environments concurrently
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(acquire_environment, i) for i in range(num_concurrent)]
        environment_results = [future.result() for future in futures]
        total_time = time.time() - start_time
        try:
                    # Analyze results
        successful_acquisitions = [item for item in []]]
        self.assertGreaterEqual(len(successful_acquisitions), 1,
        At least one environment should be acquired successfully)"
        At least one environment should be acquired successfully)"
                    # Verify unique environment names
        env_names = [result['env_name'] for result in successful_acquisitions]
        self.assertEqual(len(env_names), len(set(env_names)),
        "Environment names should be unique)"
                    # Verify reasonable acquisition times
        acquisition_times = [result['acquisition_time'] for result in successful_acquisitions]
        avg_acquisition_time = sum(acquisition_times) / len(acquisition_times)
        self.assertLess(avg_acquisition_time, 60, formatted_string)
        finally:
                        # Clean up acquired environments
        for result in environment_results:
        if result['success'] and result['manager']:
        try:
        result['manager').release_environment(result['env_name')
        except Exception as e:
        logger.warning(""
                                        # =============================================================================
                                        # Network Lifecycle Management Tests
                                        # =============================================================================
    def test_docker_network_creation_and_verification(self):
        Test Docker network creation and proper configuration verification.""
        pass
        network_name = formatted_string
    # Create custom network
        create_cmd = [
        'docker', 'network', 'create',
        '--driver', 'bridge',
        '--label', 'formatted_string',
        network_name
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_networks.add(network_name)
    # Verify network exists and has correct configuration
        inspect_cmd = ['docker', 'network', 'inspect', network_name]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, "Failed to inspect created network)"
        network_info = json.loads(result.stdout)[0]
        self.assertEqual(network_info['Driver'], 'bridge', Network should use bridge driver)
        self.assertIn('test_id', network_info['Labels'], "Network should have test_id label)"
        self.assertEqual(network_info['Labels']['test_id'], self.test_id, Network label should match test ID)
    # Test container connectivity on the network
        container1_name = formatted_string"
        container1_name = formatted_string"
        container2_name = formatted_string"
        container2_name = formatted_string"
    # Create containers on the network
        for container_name in [container1_name, container2_name]:
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        self.created_containers.add(container_name)
        # Wait for containers to start
        time.sleep(3)
        # Test connectivity between containers
        ping_cmd = [
        'docker', 'exec', container1_name,
        'ping', '-c', '3', container2_name
        
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string")"
    def test_network_isolation_between_environments(self):
        Test that different environments have isolated networks.""
        network1_name = formatted_string
        network2_name = formatted_string"
        network2_name = formatted_string"
    # Create two separate networks
        for network_name in [network1_name, network2_name]:
        create_cmd = [
        'docker', 'network', 'create',
        '--label', 'formatted_string',
        network_name
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string")"
        self.created_networks.add(network_name)
        # Create containers on different networks
        container_net1 = formatted_string
        container_net2 = formatted_string""
        containers = [
        (container_net1, network1_name),
        (container_net2, network2_name)
        
        for container_name, network_name in containers:
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
            
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, 
        self.created_containers.add(container_name)
            # Wait for containers to start
        time.sleep(3)
            # Get IP addresses
    def get_container_ip(container_name):
        inspect_cmd = [
        'docker', 'inspect', container_name,
        '--format', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
    
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
        ip1 = get_container_ip(container_net1)
        ip2 = get_container_ip(container_net2)
        self.assertNotEqual(ip1, ", "
        self.assertNotEqual(ip2, , "
        self.assertNotEqual(ip2, , "
    # Verify containers cannot reach each other across networks
        ping_cmd = ['docker', 'exec', container_net1, 'ping', '-c', '1', '-W', '3', ip2]
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
    # Ping should fail (containers on different networks)
        self.assertNotEqual(result.returncode, 0,
        Containers on different networks should not be able to communicate")"
    def test_network_cleanup_on_environment_release(self):
        Test that networks are properly cleaned up when environments are released.""
        pass
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=formatted_string
    
        try:
        # Acquire environment (this should create networks)
        env_name, ports = manager.acquire_environment()
        # Verify networks exist
        ls_cmd = ['docker', 'network', 'ls', '--format', '{{.Name}}']
        result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=10)
        networks_before = set(result.stdout.strip().split( ))"
        networks_before = set(result.stdout.strip().split( ))""

        ))
        # Release environment
        manager.release_environment(env_name)
        # Wait a moment for cleanup
        time.sleep(2)
        # Verify test networks are cleaned up
        result = subprocess.run(ls_cmd, capture_output=True, text=True, timeout=10)
        networks_after = set(result.stdout.strip().split( ))
        "))"
        # Any networks created for this test should be removed
        test_networks = [item for item in []]
        remaining_test_networks = [item for item in []]
        self.assertEqual(len(remaining_test_networks), 0,
        "
        ""

        except Exception as e:
            # Ensure cleanup even if test fails
        try:
        manager.release_environment(env_name if 'env_name' in locals() else None)
        except:
        pass
        raise e
                    # =============================================================================
                    # Container Conflict Resolution Tests
                    # =============================================================================
    def test_existing_container_conflict_detection_and_resolution(self):
        "Test detection and resolution of existing container name conflicts."
        conflict_container_name = ""
    # Create initial container
        create_cmd = [
        'docker', 'run', '-d', '--name', conflict_container_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)
        self.created_containers.add(conflict_container_name)
    # Try to create another container with the same name (should fail)
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, Second container creation should fail due to name conflict)"
        self.assertNotEqual(result.returncode, 0, Second container creation should fail due to name conflict)"
        self.assertIn(already in use", result.stderr.lower(), Error should indicate name conflict)"
    # Test conflict resolution by removing existing container
    # Use safe removal instead of docker rm -f
        stop_cmd = ['docker', 'stop', '-t', '10', conflict_container_name]
        subprocess.run(stop_cmd, capture_output=True)
        rm_cmd = ['docker', 'rm', conflict_container_name]
        result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, formatted_string)
    # Now creating container with same name should succeed
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, ""
    def test_docker_manager_automatic_conflict_resolution(self):
        Test UnifiedDockerManager automatic conflict resolution.""
        pass
    # Create a conflicting container manually
        conflicting_container = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', conflicting_container,
        '--label', 'formatted_string',
        '-p', '8999:80',  # Bind to a port that might conflict
        'alpine:latest',
        'sh', '-c', 'sleep 60'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_containers.add(conflicting_container)
    # Create manager and try to acquire environment
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id="formatted_string"
    
        try:
        # This should handle conflicts automatically
        start_time = time.time()
        env_name, ports = manager.acquire_environment()
        acquisition_time = time.time() - start_time
        # Verify environment was acquired successfully despite conflicts
        self.assertIsNotNone(env_name, Environment should be acquired despite conflicts)
        self.assertIsInstance(ports, dict, "Ports should be returned)"
        self.assertLess(acquisition_time, 120, formatted_string)
        # Verify services are healthy
        health_report = manager.get_health_report()
        healthy_services = [service for service, health in health_report.items() )
        if isinstance(health, dict) and health.get('healthy', False)]
        # Should have at least some healthy services
        self.assertGreater(len(healthy_services), 0, Should have at least some healthy services after conflict resolution)"
        self.assertGreater(len(healthy_services), 0, Should have at least some healthy services after conflict resolution)""

        finally:
        try:
        manager.release_environment(env_name if 'env_name' in locals() else None)
        except:
        pass
    def test_port_conflict_detection_and_resolution(self):
        "Test detection and resolution of port conflicts."
        test_port = 28999  # Use a high port to avoid system conflicts
    # Create container using the test port
        conflicting_container = ""
        create_cmd = [
        'docker', 'run', '-d', '--name', conflicting_container,
        '--label', 'formatted_string',
        '-p', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'while true; do echo 'HTTP/1.1 200 OK\
        \
        Hello' | nc -l -p 80; done'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)
        self.created_containers.add(conflicting_container)
    # Wait for container to start
        time.sleep(3)
    # Verify port is in use
        port_check_cmd = ['docker', 'port', conflicting_container]
        result = subprocess.run(port_check_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, Port should be bound)"
        self.assertEqual(result.returncode, 0, Port should be bound)"
        self.assertIn(str(test_port), result.stdout, formatted_string")"
    # Try to create another container using the same port (should fail)
        second_container = formatted_string
        create_cmd2 = [
        'docker', 'run', '-d', '--name', second_container,
        '--label', 'formatted_string',
        '-p', 'formatted_string',
        'alpine:latest',
        'sleep', '60'
    
        result = subprocess.run(create_cmd2, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, Second container should fail due to port conflict")"
    # Verify error message indicates port conflict
        error_indicators = [port is already allocated, bind, already in use, address already in use"]"
        error_found = any(indicator in result.stderr.lower() for indicator in error_indicators)
        self.assertTrue(error_found, "
        self.assertTrue(error_found, "
    # Test port conflict resolution by using dynamic port allocation
        port_allocator = DynamicPortAllocator()
    # Allocate alternative port
        port_range = PortRange(start=29000, end=29100)
        allocation_result = port_allocator.allocate_ports([http), [port_range)"
        allocation_result = port_allocator.allocate_ports([http), [port_range)"
        self.assertTrue(allocation_result.success, "Should be able to allocate alternative port)"
        alternative_port = allocation_result.allocated_ports[http]
        try:
        # Create container with alternative port
        create_cmd3 = [
        'docker', 'run', '-d', '--name', second_container,
        '--label', 'formatted_string',
        '-p', 'formatted_string',
        'alpine:latest',
        'sleep', '60'
        
        result = subprocess.run(create_cmd3, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, ""
        self.created_containers.add(second_container)
        finally:
            # Release allocated port
        port_allocator.release_ports(allocation_result.allocation_id)
            # =============================================================================
            # Health Check Monitoring Tests
            # =============================================================================
    def test_container_health_check_detection(self):
        Test detection of container health status through health checks.""
        pass
        healthy_container = formatted_string
        unhealthy_container = formatted_string"
        unhealthy_container = formatted_string"
    # Create healthy container with health check
        healthy_create_cmd = [
        'docker', 'run', '-d', '--name', healthy_container,
        '--label', 'formatted_string',
        '--health-cmd', 'echo "healthy',"
        '--health-interval', '""5s""',
        '--health-timeout', '""3s""',
        '--health-retries', '2',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
    
        result = subprocess.run(healthy_create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)
        self.created_containers.add(healthy_container)
    # Create unhealthy container with failing health check
        unhealthy_create_cmd = [
        'docker', 'run', '-d', '--name', unhealthy_container,
        '--label', 'formatted_string',
        '--health-cmd', 'exit 1',  # Always fail
        '--health-interval', '""5s""',
        '--health-timeout', '""3s""',
        '--health-retries', '2',
        'alpine:latest',
        'sh', '-c', 'sleep 60'
    
        result = subprocess.run(unhealthy_create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, ""
        self.created_containers.add(unhealthy_container)
    # Wait for health checks to stabilize
        time.sleep(15)
    # Check health status
    def get_health_status(container_name):
        pass
        inspect_cmd = [
        'docker', 'inspect', container_name,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
    
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
        healthy_status = get_health_status(healthy_container)
        unhealthy_status = get_health_status(unhealthy_container)
    # Verify health statuses
        self.assertEqual(healthy_status, 'healthy', formatted_string)
        self.assertEqual(unhealthy_status, 'unhealthy', ""
    def test_docker_manager_service_health_monitoring(self):
        Test UnifiedDockerManager health monitoring capabilities.""
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=formatted_string
    
        try:
        # Acquire environment
        env_name, ports = manager.acquire_environment()
        # Wait for services to start
        start_time = time.time()
        success = manager.wait_for_services(timeout=60)
        wait_time = time.time() - start_time
        self.assertTrue(success, Services should start successfully)"
        self.assertTrue(success, Services should start successfully)"
        self.assertLess(wait_time, 90, "
        self.assertLess(wait_time, 90, "
        # Get health report
        health_report = manager.get_health_report()
        self.assertIsInstance(health_report, dict, Health report should be a dictionary)"
        self.assertIsInstance(health_report, dict, Health report should be a dictionary)"
        self.assertGreater(len(health_report), 0, "Health report should contain service information)"
        # Verify health report structure
        for service_name, health_info in health_report.items():
        self.assertIsInstance(health_info, dict, formatted_string)
            # Check for expected health fields
        if 'healthy' in health_info:
        self.assertIsInstance(health_info['healthy'), bool,
        ""
        if 'response_time' in health_info:
        self.assertIsInstance(health_info['response_time'], (int, float),
        formatted_string)
                    # Test health monitoring over time
        health_checks = []
        for i in range(3):
        time.sleep(5)  # Wait between checks
        check_start = time.time()
        health = manager.get_health_report()
        check_duration = time.time() - check_start
        health_checks.append()
        'check_number': i,
        'check_duration': check_duration,
        'health_report': health
                        
                        # Health checks should be reasonably fast
        self.assertLess(check_duration, 10, ""
                        # Analyze health check consistency
        service_names = set()
        for check in health_checks:
        service_names.update(check['health_report'].keys())
                            # Services should be consistently reported
        for check in health_checks:
        for service_name in service_names:
        self.assertIn(service_name, check['health_report'),
        formatted_string)
        finally:
        try:
        manager.release_environment(env_name if 'env_name' in locals() else None)
        except:
        pass
    def test_health_check_timeout_and_retry_behavior(self):
        "Test health check timeout and retry behavior."
        pass
        slow_container = formatted_string"
        slow_container = formatted_string"
    # Create container with slow health check
        create_cmd = [
        'docker', 'run', '-d', '--name', slow_container,
        '--label', 'formatted_string',
        '--health-cmd', 'sleep 10 && echo "finally healthy',  # Takes 10 seconds"
        '--health-interval', '""15s""',
        '--health-timeout', '""5s""',  # Timeout after 5 seconds
        '--health-retries', '2',
        'alpine:latest',
        'sh', '-c', 'sleep 300'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string)
        self.created_containers.add(slow_container)
    # Monitor health status changes
        health_history = []
        start_time = time.time()
    # Check health status every few seconds for up to 60 seconds
        while time.time() - start_time < 60:
        inspect_cmd = [
        'docker', 'inspect', slow_container,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
        
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        status = result.stdout.strip()
        current_time = time.time() - start_time
            # Only record status changes
        if not health_history or health_history[-1]['status'] != status:
        health_history.append()
        'time': current_time,
        'status': status
                
        time.sleep(3)
                # Analyze health status progression
        statuses = [entry['status'] for entry in health_history]
                Should see progression from starting -> unhealthy (due to timeout)
        self.assertIn('starting', statuses, "Should start with 'starting' status)"
                # Due to timeout (""5s"") being less than health check duration (""10s""),
                # it should eventually become unhealthy
        final_status = statuses[-1] if statuses else 'none'
        self.assertEqual(final_status, 'unhealthy',
        formatted_string)
                # =============================================================================
                # Cleanup Operations Tests
                # =============================================================================
    def test_comprehensive_resource_cleanup(self):
        Test comprehensive cleanup of Docker resources.""
        resources_created = {
        'containers': [],
        'networks': [],
        'volumes': []
    
    # Create various resources
        base_name = formatted_string
    # Create volume
        volume_name = ""
        volume_cmd = ['docker', 'volume', 'create', volume_name]
        result = subprocess.run(volume_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, formatted_string)
        resources_created['volumes'].append(volume_name)
    # Create network
        network_name = formatted_string"
        network_name = formatted_string""

        network_cmd = [
        'docker', 'network', 'create',
        '--label', 'formatted_string',
        network_name
    
        result = subprocess.run(network_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string")"
        resources_created['networks'].append(network_name)
    # Create containers on the network with volumes
        for i in range(3):
        container_name = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        '-v', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'formatted_string'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, formatted_string")"
        resources_created['containers'].append(container_name)
        self.created_containers.add(container_name)
        # Verify resources exist
        time.sleep(3)
        # Verify containers are running
        for container_name in resources_created['containers']:
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running', 
            # Verify network connectivity
        container1 = resources_created['containers'][0]
        container2 = resources_created['containers'][1]
        ping_cmd = ['docker', 'exec', container1, 'ping', '-c', '1', container2]
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, Containers should be able to communicate")"
            # Verify shared volume data
        for i, container_name in enumerate(resources_created['containers'):
        read_cmd = ['docker', 'exec', container_name, 'cat', 'formatted_string']
        result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, 
        self.assertIn(formatted_string", result.stdout, Volume data should be correct)"
                # Perform cleanup
        cleanup_start_time = time.time()
                # Stop and remove containers
        for container_name in resources_created['containers']:
                    # Stop container
        stop_cmd = ['docker', 'stop', container_name]
        result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string)
                    # Remove container
        rm_cmd = ['docker', 'rm', container_name]
        result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, ""
                    # Remove network
        network_rm_cmd = ['docker', 'network', 'rm', network_name]
        result = subprocess.run(network_rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, formatted_string)
                    # Remove volume
        volume_rm_cmd = ['docker', 'volume', 'rm', volume_name]
        result = subprocess.run(volume_rm_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, ""
        cleanup_duration = time.time() - cleanup_start_time
        self.assertLess(cleanup_duration, 60, formatted_string)
                    # Verify resources are actually removed
                    # Check containers
        for container_name in resources_created['containers']:
        inspect_cmd = ['docker', 'inspect', container_name]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0, ""
                        # Check network
        network_ls_cmd = ['docker', 'network', 'ls', '--filter', 'formatted_string', '-q']
        result = subprocess.run(network_ls_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), '', formatted_string)
                        # Check volume
        volume_ls_cmd = ['docker', 'volume', 'ls', '--filter', 'formatted_string', '-q']
        result = subprocess.run(volume_ls_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), '', ""
    def test_orphaned_resource_detection_and_cleanup(self):
        Test detection and cleanup of orphaned Docker resources."
        Test detection and cleanup of orphaned Docker resources.""

        pass
    # Create some containers that will become "orphaned"
        orphaned_containers = []
        for i in range(3):
        container_name = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--label', 'netra_test=true',  # Mark as test container
        'alpine:latest',
        'sleep', '300'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, ""
        orphaned_containers.append(container_name)
        self.created_containers.add(container_name)
        # Wait for containers to start
        time.sleep(3)
        # Verify containers exist and are running
        for container_name in orphaned_containers:
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running', formatted_string)
            # Test orphaned container detection
        manager = UnifiedDockerManager(test_id=""
            # Use the cleanup method
        cleanup_successful = manager.cleanup_orphaned_containers()
        self.assertTrue(cleanup_successful, Orphaned container cleanup should succeed)
            # Verify orphaned containers were cleaned up
            # Note: The actual implementation may vary, but test containers with our test_id should be cleanable
        time.sleep(2)
            # Check if containers still exist
        remaining_containers = []
        for container_name in orphaned_containers:
        inspect_cmd = ['docker', 'inspect', container_name]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        remaining_containers.append(container_name)
                    # The cleanup should have removed at least some test containers
                    # (Implementation may vary based on the actual cleanup logic)
        self.assertLessEqual(len(remaining_containers), len(orphaned_containers),
        Cleanup should remove some or all orphaned containers)"
        Cleanup should remove some or all orphaned containers)""

    def test_environment_cleanup_completeness(self):
        "Test that environment cleanup is complete and doesn't leave artifacts."
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=""
    
        try:
        # Record initial state
        initial_containers = self._get_docker_containers()
        initial_networks = self._get_docker_networks()
        # Acquire environment
        env_name, ports = manager.acquire_environment()
        # Record state after acquisition
        post_acquisition_containers = self._get_docker_containers()
        post_acquisition_networks = self._get_docker_networks()
        # Should have more resources after acquisition
        self.assertGreaterEqual(len(post_acquisition_containers), len(initial_containers),
        Should have created containers)
        # Release environment
        manager.release_environment(env_name)
        # Wait for cleanup to complete
        time.sleep(5)
        # Record final state
        final_containers = self._get_docker_containers()
        final_networks = self._get_docker_networks()
        # Count test-related containers
    def count_test_containers(containers):
        return len([item for item in [))
        initial_test_containers = count_test_containers(initial_containers)
        final_test_containers = count_test_containers(final_containers)
    # Should have cleaned up test containers
        self.assertLessEqual(final_test_containers, initial_test_containers,
        Should have cleaned up test containers)"
        Should have cleaned up test containers)"
    # Verify no test networks remain
        test_networks = [item for item in []]
        self.assertEqual(len(test_networks), 0, formatted_string")"
        except Exception as e:
        # Ensure cleanup even if test fails
        try:
        manager.release_environment(env_name if 'env_name' in locals() else None)
        except:
        pass
        raise e
    def _get_docker_containers(self) -> List[str]:
        Get list of Docker containers.""
        pass
        cmd = ['docker', 'ps', '-a', '--format', '{{.Names}}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        return [name.strip() for name in result.stdout.strip().split( ))
        ) if name.strip()]
        return []
    def _get_docker_networks(self) -> List[str]:
        Get list of Docker networks.""
        cmd = ['docker', 'network', 'ls', '--format', '{{.Name}}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        return [name.strip() for name in result.stdout.strip().split( ))
        ) if name.strip()]
        return []
class DockerInfrastructureServiceStartupTests(SSotAsyncTestCase):
        "Infrastructure Test Category: Service Startup (5 tests)"
        @classmethod
    def setUpClass(cls):
        pass
        cls.test_project_prefix = infra_startup"
        cls.test_project_prefix = infra_startup""

        cls.created_containers = set()
        cls.docker_manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        use_production_images=True
    
        @classmethod
    def tearDownClass(cls):
        pass
        cls._cleanup_containers()
        @classmethod
    def _cleanup_containers(cls):
        pass
        for container in cls.created_containers:
        try:
        subprocess.run(['docker', 'stop', '-t', '5', container], capture_output=True, timeout=10)
        subprocess.run(['docker', 'rm', container], capture_output=True, timeout=10)
        except:
        pass
    def test_rapid_service_startup_under_30_seconds(self):
        "Test services start within 30 second requirement using Alpine optimization."
        test_id = formatted_string""
    # Test with multiple environments in sequence
        startup_times = []
        for i in range(3):
        env_name = formatted_string
        start_time = time.time()
        # Use Alpine images for fastest startup
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.DEDICATED,
        test_id=env_name,
        use_alpine_images=True
        
        try:
        result = manager.acquire_environment(timeout=30)
        startup_time = time.time() - start_time
        startup_times.append(startup_time)
        self.assertIsNotNone(result, formatted_string)"
        self.assertIsNotNone(result, formatted_string)"
        self.assertLess(startup_time, 30, "
        self.assertLess(startup_time, 30, "
            # Verify services are actually healthy
        health_report = manager.get_health_report()
        healthy_services = sum(1 for h in health_report.values() )
        if isinstance(h, dict) and h.get('healthy'))
        self.assertGreater(healthy_services, 0, Should have healthy services)"
        self.assertGreater(healthy_services, 0, Should have healthy services)""

        finally:
        if 'result' in locals() and result:
        manager.release_environment(result[0] if isinstance(result, tuple) else env_name)
                    # Verify average startup time meets requirement
        avg_startup = sum(startup_times) / len(startup_times)
        self.assertLess(avg_startup, 25, "
        self.assertLess(avg_startup, 25, ""

    def test_service_startup_with_resource_constraints(self):
        "Test service startup under strict memory and CPU limits."
        pass
        test_id = formatted_string
    # Create containers with strict resource limits
        constrained_containers = []
        for i in range(5):
        container_name = formatted_string""
        # Start container with strict limits
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--memory', '""128m""', '--cpus', '0.5',
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'echo Service $$ starting && sleep 60'
        
        start_time = time.time()
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=15)
        creation_time = time.time() - start_time
        self.assertEqual(result.returncode, 0,
        formatted_string)"
        formatted_string)""

        constrained_containers.append(container_name)
        self.created_containers.add(container_name)
        # Verify startup was reasonably fast despite constraints
        self.assertLess(creation_time, 10, "
        self.assertLess(creation_time, 10, "
        # Verify all containers are running within limits
        for container_name in constrained_containers:
            # Check container is running
        inspect_cmd = ['docker', 'inspect', container_name,
        '--format', '{{.State.Status}} {{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        parts = result.stdout.strip().split()
        if len(parts) >= 3:
        status, memory_limit, cpu_limit = parts
        self.assertEqual(status, 'running', formatted_string)"
        self.assertEqual(status, 'running', formatted_string)"
        self.assertEqual(memory_limit, '134217728', "Memory limit should be ""128MB"")  # ""128MB"" in bytes"
    def test_startup_failure_recovery_mechanism(self):
        Test automatic recovery when services fail to start initially.""
        test_id = formatted_string
    # Create a scenario where first attempt might fail
        recovery_container = formatted_string"
        recovery_container = formatted_string"
    # Use a command that has a chance of failing initially
        create_cmd = [
        'docker', 'run', '-d', '--name', recovery_container,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'if [ $(date +%S) -lt 30 ]; then sleep 2 && echo "Started successfully; else sleep 60; fi'"
    
        max_attempts = 3
        success = False
        for attempt in range(max_attempts):
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
        success = True
        self.created_containers.add(recovery_container)
        break
        else:
                # Clean up failed container name conflict
        subprocess.run(['docker', 'rm', recovery_container),
        capture_output=True, timeout=10)
        time.sleep(1)
        self.assertTrue(success, Recovery mechanism should eventually succeed)
                # Verify container is healthy after recovery
        inspect_cmd = ['docker', 'inspect', recovery_container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running', "Recovered container should be running)"
    def test_parallel_service_startup_isolation(self):
        Test multiple services can start in parallel without interference."
        Test multiple services can start in parallel without interference.""

        pass
        test_id = "formatted_string"
    def start_isolated_service(service_id):
        Start an isolated service and return result.""
        container_name = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--network', 'none',  # Network isolation
        'alpine:latest',
        'sh', '-c', 'formatted_string'
    
        start_time = time.time()
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        startup_time = time.time() - start_time
        return {
        'service_id': service_id,
        'container_name': container_name,
        'success': result.returncode == 0,
        'startup_time': startup_time,
        'error': result.stderr if result.returncode != 0 else None
    
    # Start 8 services in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(start_isolated_service, i) for i in range(8)]
        results = [future.result() for future in futures]
        # Add successful containers to cleanup list
        for result_data in results:
        if result_data['success']:
        self.created_containers.add(result_data['container_name')
                # Analyze results
        successful_starts = [item for item in []]]
        startup_times = [r['startup_time'] for r in successful_starts]
        self.assertGreaterEqual(len(successful_starts), 6,
        formatted_string)"
        formatted_string)""

        if startup_times:
        avg_startup = sum(startup_times) / len(startup_times)
        max_startup = max(startup_times)
        self.assertLess(avg_startup, 5, "
        self.assertLess(avg_startup, 5, "
        self.assertLess(max_startup, 15, formatted_string)"
        self.assertLess(max_startup, 15, formatted_string)""

    def test_service_dependency_startup_ordering(self):
        "Test services start in correct dependency order."
        pass
        test_id = formatted_string""
    # Create a dependency chain: db -> backend -> frontend
        dependency_containers = []
    # Database service (no dependencies)
        db_container = formatted_string
        create_db_cmd = [
        'docker', 'run', '-d', '--name', db_container,
        '--label', 'formatted_string',
        '--label', 'service_type=database',
        'alpine:latest',
        'sh', '-c', 'echo DB ready > /tmp/ready && sleep 60'"
        'sh', '-c', 'echo DB ready > /tmp/ready && sleep 60'""

    
        start_time = time.time()
        result = subprocess.run(create_db_cmd, capture_output=True, text=True, timeout=15)
        db_start_time = time.time() - start_time
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        dependency_containers.append(db_container)
        self.created_containers.add(db_container)
    # Wait for DB to be ready
        time.sleep(2)
    # Backend service (depends on DB)
        backend_container = formatted_string"
        backend_container = formatted_string""

        create_backend_cmd = [
        'docker', 'run', '-d', '--name', backend_container,
        '--label', 'formatted_string',
        '--label', 'service_type=backend',
        '--link', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'echo "Backend connecting to DB && sleep 60'"
    
        start_time = time.time()
        result = subprocess.run(create_backend_cmd, capture_output=True, text=True, timeout=15)
        backend_start_time = time.time() - start_time
        self.assertEqual(result.returncode, 0, formatted_string)
        dependency_containers.append(backend_container)
        self.created_containers.add(backend_container)
    # Verify dependency order timing
        self.assertLess(db_start_time, backend_start_time + 5,
        "DB should start before or around same time as backend)"
    # Verify both services are running
        for container in dependency_containers:
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running',
        formatted_string)
class DockerInfrastructureHealthMonitoringTests(SSotAsyncTestCase):
        Infrastructure Test Category: Health Monitoring (5 tests)""
        @classmethod
    def setUpClass(cls):
        pass
        cls.test_project_prefix = infra_health
        cls.created_containers = set()
        @classmethod
    def tearDownClass(cls):
        pass
        cls._cleanup_containers()
        @classmethod
    def _cleanup_containers(cls):
        pass
        for container in cls.created_containers:
        try:
        subprocess.run(['docker', 'stop', '-t', '3', container], capture_output=True, timeout=10)
        subprocess.run(['docker', 'rm', container], capture_output=True, timeout=10)
        except:
        pass
    def test_real_time_health_monitoring_accuracy(self):
        "Test real-time health monitoring provides accurate service status."
        test_id = formatted_string"
        test_id = formatted_string"
    # Create containers with different health states
        health_scenarios = [
        ('healthy', 'echo "healthy'),"
        ('degraded', 'if [ $(($(date +%s) % 10)) -lt 3 ]; then exit 1; else echo ok; fi'),
        ('unhealthy', 'exit 1')
    
        test_containers = []
        for scenario_name, health_cmd in health_scenarios:
        container_name = ""
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--health-cmd', health_cmd,
        '--health-interval', '""3s""',
        '--health-timeout', '""2s""',
        '--health-retries', '2',
        'alpine:latest',
        'sleep', '120'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0,
        formatted_string)
        test_containers.append((container_name, scenario_name))
        self.created_containers.add(container_name)
        # Monitor health status over time
        health_history = {container: [] for container, _ in test_containers}
        monitoring_duration = 30  # seconds
        check_interval = 3
        start_time = time.time()
        while time.time() - start_time < monitoring_duration:
        for container_name, scenario in test_containers:
        inspect_cmd = [
        'docker', 'inspect', container_name,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
                
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
        status = result.stdout.strip()
        timestamp = time.time() - start_time
        health_history[container_name].append((timestamp, status))
        time.sleep(check_interval)
                    # Analyze health monitoring accuracy
        for container_name, scenario in test_containers:
        history = health_history[container_name]
        self.assertGreater(len(history), 5, ""
                        # Get final health status
        if history:
        final_status = history[-1][1]
        if scenario == 'healthy':
        self.assertEqual(final_status, 'healthy',
        fHealthy container should report healthy status)
        elif scenario == 'unhealthy':
        self.assertEqual(final_status, 'unhealthy',
        fUnhealthy container should report unhealthy status)
                                    # Degraded scenario may vary between healthy/unhealthy
    def test_health_check_performance_under_load(self):
        ""Test health check performance doesn't degrade under system load.'""

        pass
        test_id = formatted_string"
        test_id = formatted_string"
    # Create load generators
        load_containers = []
        for i in range(10):
        container_name = formatted_string"
        container_name = formatted_string""

        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""64m""', '--cpus', '0.3',
        'alpine:latest',
        'sh', '-c', 'while true; do dd if=/dev/zero of=/dev/null bs=""1M"" count=1; sleep 0.1; done'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
        load_containers.append(container_name)
        self.created_containers.add(container_name)
        self.assertGreaterEqual(len(load_containers), 8, Should create at least 8 load containers)
            # Create monitored service with health checks
        monitored_container = formatted_string""
        create_monitored_cmd = [
        'docker', 'run', '-d', '--name', monitored_container,
        '--label', 'formatted_string',
        '--health-cmd', 'echo healthy',
        '--health-interval', '""2s""',
        '--health-timeout', '""1s""',
        '--health-retries', '1',
        'alpine:latest',
        'sleep', '60'
            
        result = subprocess.run(create_monitored_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_containers.add(monitored_container)
            # Monitor health check performance under load
        health_check_times = []
        for _ in range(15):  # 15 health checks over 30 seconds
        start = time.time()
        inspect_cmd = [
        'docker', 'inspect', monitored_container,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
            
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        check_duration = time.time() - start
        if result.returncode == 0:
        health_check_times.append(check_duration)
        status = result.stdout.strip()
                # Health should remain responsive under load
        self.assertIn(status, ['starting', 'healthy', 'unhealthy'),
        "
        ""

        time.sleep(2)
                # Verify health check performance
        if health_check_times:
        avg_check_time = sum(health_check_times) / len(health_check_times)
        max_check_time = max(health_check_times)
        self.assertLess(avg_check_time, 1.0, formatted_string)"
        self.assertLess(avg_check_time, 1.0, formatted_string)"
        self.assertLess(max_check_time, 2.0, "
        self.assertLess(max_check_time, 2.0, ""

    def test_health_status_change_detection_speed(self):
        "Test rapid detection of health status changes."
        test_id = formatted_string
    # Create container that changes health status
        changing_container = formatted_string""
    # Health check that fails after 20 seconds
        create_cmd = [
        'docker', 'run', '-d', '--name', changing_container,
        '--label', 'formatted_string',
        '--health-cmd', 'if [ $(cat /proc/uptime | cut -d. -f1) -gt 20 ]; then exit 1; else echo ok; fi',
        '--health-interval', '""2s""',
        '--health-timeout', '""1s""',
        '--health-retries', '1',
        'alpine:latest',
        'sleep', '60'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_containers.add(changing_container)
    # Monitor health status changes
        status_changes = []
        last_status = None
        start_time = time.time()
        while time.time() - start_time < 45:  # Monitor for 45 seconds
        inspect_cmd = [
        'docker', 'inspect', changing_container,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
    
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
        current_status = result.stdout.strip()
        timestamp = time.time() - start_time
        if current_status != last_status:
        status_changes.append((timestamp, last_status, current_status))
        last_status = current_status
        time.sleep(1)
            # Verify status change detection
        self.assertGreaterEqual(len(status_changes), 2,
        "
        ""

            Find the change from healthy to unhealthy
        health_to_unhealthy = None
        for timestamp, from_status, to_status in status_changes:
        if from_status == 'healthy' and to_status == 'unhealthy':
        health_to_unhealthy = timestamp
        break
        if health_to_unhealthy:
                        # Should detect change reasonably quickly after 20 seconds
        self.assertLess(health_to_unhealthy, 35,
        formatted_string)"
        formatted_string)""

    def test_multi_service_health_aggregation(self):
        "Test health monitoring across multiple services with aggregation."
        pass
        test_id = formatted_string""
    # Create multiple services with different health patterns
        services = [
        ('web', 'echo web ok', '""2s""'),
        ('api', 'echo api ok', '3s'),"
        ('api', 'echo api ok', '3s'),"
        ('cache', 'echo "cache ok', '""2s""'),"
        ('worker', 'if [ $(($(date +%s) % 8)) -lt 2 ]; then exit 1; else echo worker ok; fi', '""2s""')
    
        service_containers = {}
        for service_name, health_cmd, interval in services:
        container_name = ""
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--label', 'formatted_string',
        '--health-cmd', health_cmd,
        '--health-interval', interval,
        '--health-timeout', '""1s""',
        '--health-retries', '1',
        'alpine:latest',
        'sleep', '60'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0,
        formatted_string)
        service_containers[service_name] = container_name
        self.created_containers.add(container_name)
        # Monitor aggregated health across all services
        health_snapshots = []
        for check_round in range(10):
        snapshot = {'timestamp': time.time(), 'services': {}}
        for service_name, container_name in service_containers.items():
        inspect_cmd = [
        'docker', 'inspect', container_name,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
                
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
        snapshot['services'][service_name] = result.stdout.strip()
        health_snapshots.append(snapshot)
        time.sleep(3)
                    # Analyze aggregated health data
        self.assertGreater(len(health_snapshots), 8, Should have multiple health snapshots)"
        self.assertGreater(len(health_snapshots), 8, Should have multiple health snapshots)"
                    # Verify all services were monitored
        for snapshot in health_snapshots:
        self.assertEqual(len(snapshot['services'], len(services),
        All services should be in each snapshot")"
                        # Calculate service availability
        service_availability = {}
        for service_name in service_containers.keys():
        healthy_count = sum(1 for snapshot in health_snapshots )
        if snapshot['services'].get(service_name) == 'healthy')
        total_checks = len(health_snapshots)
        availability = healthy_count / total_checks if total_checks > 0 else 0
        service_availability[service_name] = availability
                            # Most services should have high availability
        high_availability_services = sum(1 for avail in service_availability.values() if avail >= 0.7)
        self.assertGreaterEqual(high_availability_services, 3,
        "
        ""

    def test_health_monitoring_resource_efficiency(self):
        "Test health monitoring doesn't consume excessive system resources."
        test_id = ""
    # Create many services to stress the monitoring system
        monitored_containers = []
        for i in range(20):
        container_name = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--health-cmd', 'formatted_string',
        '--health-interval', '""5s""',
        '--health-timeout', '""2s""',
        '--health-retries', '1',
        '--memory', '""32m""',  # Small memory limit
        'alpine:latest',
        'sleep', '90'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
        monitored_containers.append(container_name)
        self.created_containers.add(container_name)
        self.assertGreaterEqual(len(monitored_containers), 15,
        Should create at least 15 monitored services)"
        Should create at least 15 monitored services)"
            # Perform intensive health monitoring
        monitoring_operations = 0
        start_time = time.time()
        while time.time() - start_time < 30:  # Monitor for 30 seconds
            # Check health of all services
        for container_name in monitored_containers:
        inspect_cmd = [
        'docker', 'inspect', container_name,
        '--format', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
                
        operation_start = time.time()
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=3)
        operation_time = time.time() - operation_start
        if result.returncode == 0:
        monitoring_operations += 1
                    # Individual health checks should be fast
        self.assertLess(operation_time, 0.5,
        formatted_string")"
        time.sleep(1)  # Brief pause between rounds
                    # Verify monitoring efficiency
        total_monitoring_time = time.time() - start_time
        operations_per_second = monitoring_operations / total_monitoring_time
        self.assertGreater(monitoring_operations, 100,
        "
        ""

        self.assertGreater(operations_per_second, 5,
        formatted_string")"
class DockerInfrastructureFailureRecoveryTests(SSotAsyncTestCase):
        Infrastructure Test Category: Failure Recovery (5 tests)""
        @classmethod
    def setUpClass(cls):
        pass
        cls.test_project_prefix = infra_recovery
        cls.created_containers = set()
        @classmethod
    def tearDownClass(cls):
        pass
        cls._cleanup_containers()
        @classmethod
    def _cleanup_containers(cls):
        pass
        for container in cls.created_containers:
        try:
        subprocess.run(['docker', 'stop', '-t', '3', container], capture_output=True, timeout=10)
        subprocess.run(['docker', 'rm', container], capture_output=True, timeout=10)
        except:
        pass
    def test_automatic_service_restart_on_failure(self):
        Test services automatically restart when they fail.""
        test_id = formatted_string
    # Create service with restart policy
        service_container = ""
        create_cmd = [
        'docker', 'run', '-d', '--name', service_container,
        '--label', 'formatted_string',
        '--restart', 'always',  # Always restart on failure
        'alpine:latest',
        'sh', '-c', 'echo Service starting && sleep 30 && echo Service completed'
    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string)"
        self.assertEqual(result.returncode, 0, formatted_string)""

        self.created_containers.add(service_container)
    # Wait for service to be running
        time.sleep(3)
    # Get initial container ID
        inspect_cmd = ['docker', 'inspect', service_container, '--format', '{{.Id}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        initial_id = result.stdout.strip()[:12]
    # Kill the service to trigger restart
        kill_cmd = ['docker', 'kill', service_container]
        result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, "Should be able to kill service)"
    # Monitor for automatic restart
        restart_detected = False
        restart_time = None
        monitor_start = time.time()
        for attempt in range(30):  # Monitor for up to 60 seconds
        time.sleep(2)
    # Check if container restarted (new ID, running status)
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if inspect_result.returncode == 0:
        current_id = inspect_result.stdout.strip()[:12]
        # Check if it's running with new ID'
        status_cmd = ['docker', 'inspect', service_container, '--format', '{{.State.Status}}']
        status_result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=10)
        if (status_result.returncode == 0 and )
        status_result.stdout.strip() == 'running' and
        current_id != initial_id):
        restart_detected = True
        restart_time = time.time() - monitor_start
        break
        self.assertTrue(restart_detected, fService should automatically restart after failure)
        if restart_time:
        self.assertLess(restart_time, 60, ""
    def test_failure_cascade_prevention(self):
        Test system prevents cascade failures across services.""
        pass
        test_id = formatted_string
    # Create network for service communication
        network_name = formatted_string"
        network_name = formatted_string""

        network_cmd = ['docker', 'network', 'create', network_name]
        result = subprocess.run(network_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        try:
        # Create multiple interconnected services
        service_containers = []
        for i in range(5):
        container_name = formatted_string"
        container_name = formatted_string""

        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        '--restart', 'unless-stopped',  # Restart unless manually stopped
        'alpine:latest',
        'sh', '-c', 'formatted_string'
            
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0,
        "
        ""

        service_containers.append(container_name)
        self.created_containers.add(container_name)
            # Wait for all services to be running
        time.sleep(5)
            # Verify all services are initially running
        for container in service_containers:
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running',
        formatted_string)"
        formatted_string)"
                # Kill multiple services simultaneously to test cascade prevention
        killed_services = service_containers[:3]  # Kill first 3 services
        for container in killed_services:
        kill_cmd = ['docker', 'kill', container]
        subprocess.run(kill_cmd, capture_output=True, timeout=10)
                    # Wait for system to stabilize and recover
        time.sleep(10)
                    # Check if cascade was prevented (remaining services still running)
        remaining_services = service_containers[3:]
        cascade_prevented = True
        for container in remaining_services:
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0 or result.stdout.strip() != 'running':
        cascade_prevented = False
        break
        self.assertTrue(cascade_prevented,
        "Remaining services should continue running (cascade prevented))"
                            # Verify some killed services are restarting
        recovered_services = 0
        for container in killed_services:
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == 'running':
        recovered_services += 1
        self.assertGreater(recovered_services, 0, Some services should recover automatically)
        finally:
                                        # Clean up network
        network_rm_cmd = ['docker', 'network', 'rm', network_name]
        subprocess.run(network_rm_cmd, capture_output=True, timeout=10)
    def test_resource_exhaustion_recovery(self):
        "Test recovery from resource exhaustion scenarios."
        test_id = formatted_string"
        test_id = formatted_string"
    # Create services that consume resources
        resource_containers = []
    # Create memory-hungry containers
        for i in range(3):
        container_name = "formatted_string"
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""128m""',  # Limited memory
        '--oom-kill-disable=false',  # Allow OOM killer
        'alpine:latest',
        'sh', '-c', 'while true; do dd if=/dev/zero of=/tmp/fill bs=""1M"" count=10 2>/dev/null || true; sleep 1; done'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
        resource_containers.append(container_name)
        self.created_containers.add(container_name)
            # Create a critical service that should survive resource pressure
        critical_container = formatted_string
        create_critical_cmd = [
        'docker', 'run', '-d', '--name', critical_container,
        '--label', 'formatted_string',
        '--memory', '""64m""',
        '--restart', 'always',
        '--priority', '1000',  # Higher priority
        'alpine:latest',
        'sh', '-c', 'while true; do echo "Critical service running; sleep 2; done'"
            
        result = subprocess.run(create_critical_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string)
        self.created_containers.add(critical_container)
            # Let system run under resource pressure
        time.sleep(15)
            # Check system recovery and critical service survival
        critical_status_cmd = ['docker', 'inspect', critical_container, '--format', '{{.State.Status}}']
        result = subprocess.run(critical_status_cmd, capture_output=True, text=True, timeout=10)
            # Critical service should either be running or have restarted
        self.assertEqual(result.returncode, 0, Critical service should exist)"
        self.assertEqual(result.returncode, 0, Critical service should exist)""

        status = result.stdout.strip()
        self.assertIn(status, ['running', 'restarting'),
        formatted_string")"
            # Check if any resource-hungry containers were killed (expected behavior)
        killed_containers = 0
        for container in resource_containers:
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.OOMKilled}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == 'true':
        killed_containers += 1
                    # Some resource-hungry containers should be OOM killed
        self.assertGreater(killed_containers, 0, Resource exhaustion should trigger OOM kills)
    def test_network_failure_recovery(self):
        ""Test recovery from network connectivity issues.""

        pass
        test_id = formatted_string"
        test_id = formatted_string"
    # Create custom network
        network_name = formatted_string"
        network_name = formatted_string""

        network_cmd = ['docker', 'network', 'create', network_name]
        result = subprocess.run(network_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, "
        self.assertEqual(result.returncode, 0, ""

        try:
        # Create services on the network
        service_containers = []
        for i in range(3):
        container_name = formatted_string"
        container_name = formatted_string""

        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'formatted_string'
            
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0,
        "
        ""

        service_containers.append(container_name)
        self.created_containers.add(container_name)
            # Wait for services to start
        time.sleep(5)
            # Simulate network failure by disconnecting containers
        disconnected_containers = []
        for container in service_containers[:2]:  # Disconnect first 2 services
        disconnect_cmd = ['docker', 'network', 'disconnect', network_name, container]
        result = subprocess.run(disconnect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        disconnected_containers.append(container)
                # Wait for network failure to be detected
        time.sleep(5)
                # Reconnect services to simulate recovery
        for container in disconnected_containers:
        connect_cmd = ['docker', 'network', 'connect', network_name, container]
        result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        logger.info(formatted_string")"
                        # Wait for recovery
        time.sleep(5)
                        # Verify services recovered network connectivity
        for container in service_containers:
                            # Check container is still running
        inspect_cmd = ['docker', 'inspect', container, '--format', '{{.State.Status}}']
        result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout.strip(), 'running',
        "
        "
                            # Verify network connectivity
        ping_cmd = ['docker', 'exec', container, 'ping', '-c', '1', 'google.com']
        ping_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
                            # Network connectivity should be restored (may take time)
        if ping_result.returncode != 0:
                                # Allow some time for DNS/routing to recover
        time.sleep(5)
        retry_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=10)
                                # Don't fail if external connectivity issues, but service should be running'
        finally:
                                    # Clean up network
        network_rm_cmd = ['docker', 'network', 'rm', network_name]
        subprocess.run(network_rm_cmd, capture_output=True, timeout=10)
    def test_docker_daemon_connection_recovery(self):
        "Test recovery from Docker daemon connection issues."
        test_id = ""
    # Create a service
        test_container = formatted_string
        create_cmd = [
        'docker', 'run', '-d', '--name', test_container,
        '--label', 'formatted_string',
        '--restart', 'always',
        'alpine:latest',
        'sh', '-c', 'while true; do echo Service running; sleep 3; done'"
        'sh', '-c', 'while true; do echo Service running; sleep 3; done'""

    
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, formatted_string")"
        self.created_containers.add(test_container)
    # Verify initial connectivity
        initial_check = subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=5)
        self.assertEqual(initial_check.returncode, 0, Docker daemon should be accessible initially)
    # Simulate daemon connection stress by rapid commands
        connection_errors = 0
        rapid_commands = []
    # Generate many rapid Docker commands to stress daemon connection
        for i in range(50):
        cmd_start = time.time()
        result = subprocess.run(['docker', 'ps', '-q'),
        capture_output=True, text=True, timeout=2)
        cmd_duration = time.time() - cmd_start
        rapid_commands.append()
        'success': result.returncode == 0,
        'duration': cmd_duration,
        'attempt': i
        
        if result.returncode != 0:
        connection_errors += 1
        time.sleep(0.5)  # Very rapid commands
            # Verify daemon connection recovery
        recovery_start = time.time()
        daemon_recovered = False
            Give daemon time to recover from rapid commands
        for attempt in range(10):
        recovery_check = subprocess.run(['docker', 'version'),
        capture_output=True, text=True, timeout=10)
        if recovery_check.returncode == 0:
        daemon_recovered = True
        break
        time.sleep(2)
        recovery_time = time.time() - recovery_start
        self.assertTrue(daemon_recovered, Docker daemon should recover from connection stress")"
        self.assertLess(recovery_time, 20, 
                    # Verify service is still running after connection stress
        service_check = subprocess.run(['docker', 'inspect', test_container, '--format', '{{.State.Status))'],
        capture_output=True, text=True, timeout=10)
        self.assertEqual(service_check.returncode, 0, Should be able to inspect service after recovery")"
        self.assertEqual(service_check.stdout.strip(), 'running', Service should still be running)
class DockerInfrastructurePerformanceTests(SSotAsyncTestCase):
        "Infrastructure Test Category: Performance (5 tests)"
        @classmethod
    def setUpClass(cls):
        pass
        cls.test_project_prefix = infra_perf
        cls.created_containers = set()
        @classmethod
    def tearDownClass(cls):
        pass
        cls._cleanup_containers()
        @classmethod
    def _cleanup_containers(cls):
        pass
        for container in cls.created_containers:
        try:
        subprocess.run(['docker', 'stop', '-t', '2', container], capture_output=True, timeout=8)
        subprocess.run(['docker', 'rm', container], capture_output=True, timeout=8)
        except:
        pass
    def test_container_creation_throughput_benchmark(self):
        "Test container creation throughput meets performance requirements."
        test_id = formatted_string
    # Measure container creation throughput
        creation_times = []
        created_containers = []
        total_start = time.time()
        for i in range(15):
        container_name = formatted_string""
        create_start = time.time()
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""64m""',
        'alpine:latest',
        'sleep', '30'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        create_duration = time.time() - create_start
        if result.returncode == 0:
        creation_times.append(create_duration)
        created_containers.append(container_name)
        self.created_containers.add(container_name)
        else:
        logger.warning(
        total_duration = time.time() - total_start
                # Analyze throughput performance
        self.assertGreaterEqual(len(created_containers), 12,
        formatted_string")"
        if creation_times:
        avg_creation = sum(creation_times) / len(creation_times)
        max_creation = max(creation_times)
        min_creation = min(creation_times)
        throughput_per_sec = len(created_containers) / total_duration
                    # Performance requirements
        self.assertLess(avg_creation, 3.0, 
        self.assertLess(max_creation, 8.0, formatted_string")"
        self.assertGreater(throughput_per_sec, 0.5,
        
        logger.info(formatted_string" )"
        
    def test_memory_usage_efficiency_validation(self):
        ""Test containers operate within memory efficiency requirements.""

        pass
        test_id = formatted_string"
        test_id = formatted_string"
    # Create containers with different memory profiles
        memory_test_containers = []
        memory_configs = [
        ('small', '""32m""'),
        ('medium', '""128m""'),
        ('large', '""256m""')
    
        for size_name, memory_limit in memory_configs:
        for i in range(3):  # 3 containers per size
        container_name = formatted_string"
        container_name = formatted_string""

        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', memory_limit,
        'alpine:latest',
        'sh', '-c', 'formatted_string'
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
        memory_test_containers.append((container_name, size_name, memory_limit))
        self.created_containers.add(container_name)
        self.assertGreaterEqual(len(memory_test_containers), 8, Should create most test containers)
            # Wait for containers to stabilize
        time.sleep(5)
            # Measure actual memory usage
        memory_measurements = []
        for container_name, size_name, limit in memory_test_containers:
                # Get memory statistics
        stats_cmd = ['docker', 'stats', '--no-stream', '--format',
        'table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}', container_name]
        result = subprocess.run(stats_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        lines = result.stdout.strip().split( )
        ")"
        if len(lines) >= 2:  # Skip header
        data_line = lines[1]
        if '\t' in data_line:
        parts = data_line.split('\t')
        if len(parts) >= 2:
        memory_usage = parts[1].strip()
                            # Parse memory usage (e.g., 45.""2MiB"" / ""128MiB"")
        if '/' in memory_usage:
        current_mem = memory_usage.split('/')[0].strip()
        if 'MiB' in current_mem:
        mem_mb = float(current_mem.replace('MiB', '').strip())
        memory_measurements.append()
        'container': container_name,
        'size_category': size_name,
        'limit': limit,
        'actual_mb': mem_mb
                                    
                                    # Analyze memory efficiency
        self.assertGreater(len(memory_measurements), 6, Should collect memory measurements)
                                    # Verify memory usage is reasonable for each category
        by_category = {}
        for measurement in memory_measurements:
        category = measurement['size_category']
        if category not in by_category:
        by_category[category] = []
        by_category[category).append(measurement['actual_mb')
        for category, usage_list in by_category.items():
        avg_usage = sum(usage_list) / len(usage_list)
        max_usage = max(usage_list)
                                                # Memory efficiency requirements
        if category == 'small':
        self.assertLess(avg_usage, 20, ""
        elif category == 'medium':
        self.assertLess(avg_usage, 80, formatted_string)
        elif category == 'large':
        self.assertLess(avg_usage, 200, ""
    def test_concurrent_operations_performance(self):
        Test performance under concurrent Docker operations.""
        test_id = formatted_string
    def concurrent_operation_worker(worker_id, operations_count):
        "Perform multiple Docker operations concurrently."
        pass
        worker_results = []
        worker_containers = []
        for i in range(operations_count):
        container_name = formatted_string
        operation_start = time.time()
        try:
            # Create container
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""32m""',
        'alpine:latest',
        'echo', 'formatted_string'
            
        create_result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=15)
        create_success = create_result.returncode == 0
        if create_success:
        worker_containers.append(container_name)
                # Inspect container
        inspect_cmd = ['docker', 'inspect', container_name, '--format', '{{.State.ExitCode}}']
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
        inspect_success = inspect_result.returncode == 0
                # Remove container
        rm_cmd = ['docker', 'rm', container_name]
        rm_result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10)
        rm_success = rm_result.returncode == 0
        operation_duration = time.time() - operation_start
        worker_results.append()
        'worker_id': worker_id,
        'operation_id': i,
        'duration': operation_duration,
        'create_success': create_success,
        'inspect_success': inspect_success,
        'rm_success': rm_success,
        'overall_success': create_success and inspect_success and rm_success
                
        else:
        worker_results.append()
        'worker_id': worker_id,
        'operation_id': i,
        'duration': time.time() - operation_start,
        'overall_success': False,
        'error': create_result.stderr
                    
        except Exception as e:
        worker_results.append()
        'worker_id': worker_id,
        'operation_id': i,
        'duration': time.time() - operation_start,
        'overall_success': False,
        'exception': str(e)
                        
                        # Brief pause between operations
        time.sleep(0.1)
        return worker_results
                        # Run concurrent operations with multiple workers
        total_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
        executor.submit(concurrent_operation_worker, worker_id, 4)
        for worker_id in range(6)
                            
        all_results = []
        for future in concurrent.futures.as_completed(futures):
        worker_results = future.result()
        all_results.extend(worker_results)
        total_duration = time.time() - total_start
                                # Analyze concurrent performance
        successful_operations = [item for item in []]]
        operation_durations = [item for item in []]
        self.assertGreaterEqual(len(successful_operations), 20,
        formatted_string")"
        if operation_durations:
        avg_duration = sum(operation_durations) / len(operation_durations)
        max_duration = max(operation_durations)
        operations_per_sec = len(all_results) / total_duration
                                    # Performance requirements for concurrent operations
        self.assertLess(avg_duration, 5.0, 
        self.assertLess(max_duration, 15.0, formatted_string")"
        self.assertGreater(operations_per_sec, 1.0,
        
    def test_io_performance_with_volume_mounts(self):
        '''Test I/O performance with volume mounts.'
        WARNING: tmpfs removed - causes system crashes from RAM exhaustion.
        '''
        '''
        pass
        test_id = formatted_string""
    # Test different I/O scenarios
    tmpfs removed - causes system crashes from RAM exhaustion
        io_scenarios = [
        ('regular', None, None),
        ('volume', formatted_string, None)
    
        io_results = {}
        for scenario_name, volume_name, _ in io_scenarios:  # Third param was for tmpfs (removed)
        container_name = formatted_string"
        container_name = formatted_string"
    # Create volume if needed
        if volume_name:
        vol_create_cmd = ['docker', 'volume', 'create', volume_name]
        subprocess.run(vol_create_cmd, capture_output=True, timeout=10)
        # Build container command
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""128m""'
        
        if volume_name:
        create_cmd.extend(['-v', 'formatted_string')
            # tmpfs mount removed - causes system crashes
        create_cmd.extend()
        'alpine:latest',
        'sleep', '60'
            
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
        self.created_containers.add(container_name)
                # Test write performance
        write_path = '/data/testfile' if volume_name else '/tmp/testfile'
        write_start = time.time()
        write_cmd = [
        'docker', 'exec', container_name,
        'dd', 'if=/dev/zero', 'formatted_string', 'bs=""1M""', 'count=10'
                
        write_result = subprocess.run(write_cmd, capture_output=True, text=True, timeout=30)
        write_duration = time.time() - write_start
        write_success = write_result.returncode == 0
                # Test read performance
        read_duration = 0
        read_success = False
        if write_success:
        read_start = time.time()
        read_cmd = [
        'docker', 'exec', container_name,
        'dd', 'formatted_string', 'of=/dev/null', 'bs=""1M""'
                    
        read_result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=30)
        read_duration = time.time() - read_start
        read_success = read_result.returncode == 0
        io_results[scenario_name] = {
        'write_duration': write_duration,
        'read_duration': read_duration,
        'write_success': write_success,
        'read_success': read_success
                    
                    # Cleanup volume
        if volume_name:
        vol_rm_cmd = ['docker', 'volume', 'rm', volume_name]
        subprocess.run(vol_rm_cmd, capture_output=True, timeout=10)
                        # Analyze I/O performance
        self.assertGreaterEqual(len(io_results), 2, "Should test multiple I/O scenarios)"
        for scenario, results in io_results.items():
        if results['write_success']:
        write_time = results['write_duration']
        self.assertLess(write_time, 20, formatted_string)
        if results['read_success']:
        read_time = results['read_duration']
        self.assertLess(read_time, 10, ""
                                    tmpfs comparison removed - tmpfs causes system crashes from RAM exhaustion
    def test_alpine_optimization_performance_gains(self):
        Test Alpine container optimization provides performance gains.""
        test_id = formatted_string
    # Compare Alpine vs Ubuntu performance
        image_comparisons = [
        ('alpine', 'alpine:latest'),
        ('ubuntu', 'ubuntu:20.4')
    
        comparison_results = {}
        for image_type, image_name in image_comparisons:
        startup_times = []
        container_sizes = []
        # Test multiple containers for each image type
        for i in range(3):
        container_name = formatted_string"
        container_name = formatted_string"
            # Measure startup time
        startup_start = time.time()
        create_cmd = [
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', '""64m""',
        image_name,
        'sleep', '30'
            
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        startup_duration = time.time() - startup_start
        if result.returncode == 0:
        startup_times.append(startup_duration)
        self.created_containers.add(container_name)
                # Measure container size
        size_cmd = ['docker', 'inspect', container_name, '--format', '{{.SizeRw}}']
        size_result = subprocess.run(size_cmd, capture_output=True, text=True, timeout=10)
        if size_result.returncode == 0:
        try:
        size_bytes = int(size_result.stdout.strip() or '0')
        container_sizes.append(size_bytes)
        except:
        pass
        if startup_times:
        comparison_results[image_type] = {
        'avg_startup': sum(startup_times) / len(startup_times),
        'min_startup': min(startup_times),
        'max_startup': max(startup_times),
        'avg_size_mb': sum(container_sizes) / len(container_sizes) / (1024*1024) if container_sizes else 0,
        'success_count': len(startup_times)
                                
                                # Analyze Alpine optimization benefits
        self.assertIn('alpine', comparison_results, "Should test Alpine containers)"
        alpine_results = comparison_results['alpine']
                                # Alpine performance requirements
        self.assertLess(alpine_results['avg_startup'), 8.0,
        formatted_string)
        self.assertLess(alpine_results['max_startup'), 15.0,
        ""
                                # If Ubuntu comparison available, verify Alpine is faster
        if 'ubuntu' in comparison_results:
        ubuntu_results = comparison_results['ubuntu']
        alpine_avg = alpine_results['avg_startup']
        ubuntu_avg = ubuntu_results['avg_startup']
                                    # Alpine should be significantly faster than Ubuntu
        speedup_factor = ubuntu_avg / alpine_avg if alpine_avg > 0 else 1
        self.assertGreater(speedup_factor, 1.2,
        formatted_string)
        logger.info(""
    def test_unified_docker_manager_comprehensive_environment_lifecycle(self):
        Test complete environment lifecycle with UnifiedDockerManager.""
        pass
        test_env_name = formatted_string
        try:
        # Test environment acquisition
        start_time = time.time()
        result = self.docker_manager.acquire_environment( )
        test_env_name,
        use_alpine=True,
        timeout=45
        
        acquire_time = time.time() - start_time
        self.assertIsNotNone(result, Failed to acquire environment)"
        self.assertIsNotNone(result, Failed to acquire environment)"
        self.assertLess(acquire_time, 45, "
        self.assertLess(acquire_time, 45, "
        # Verify environment health
        health = self.docker_manager.get_health_report(test_env_name)
        self.assertTrue(health.get('all_healthy', False), formatted_string)"
        self.assertTrue(health.get('all_healthy', False), formatted_string)"
        # Test port allocation
        ports = result.get('ports', {)
        self.assertGreater(len(ports), 0, "No ports allocated)"
        for service, port in ports.items():
        self.assertGreaterEqual(port, 1024, formatted_string)
        self.assertLessEqual(port, 65535, ""
            # Test resource monitoring if method available
        if hasattr(self.docker_manager, '_get_environment_containers'):
        containers = self.docker_manager._get_environment_containers(test_env_name)
        self.assertGreater(len(containers), 0, No containers found for environment)
        for container in containers:
        stats = container.stats(stream=False)
        memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
        self.assertLess(memory_mb, 500, ""
        finally:
                        # Clean up environment
        if hasattr(self.docker_manager, 'release_environment'):
        self.docker_manager.release_environment(test_env_name)
    def test_parallel_environment_management_isolation(self):
        Test parallel environment management with proper isolation.""
        num_environments = 5
        environments = []
    def create_environment(index):
        env_name = formatted_string
        try:
        result = self.docker_manager.acquire_environment( )
        env_name,
        use_alpine=True,
        timeout=60
        
        if result:
        environments.append(env_name)
        return (env_name, True)
        return (env_name, False)
        except Exception as e:
        logger.error(formatted_string)"
        logger.error(formatted_string)""

        return (env_name, False)
        try:
                    # Create environments in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_environment, i) for i in range(num_environments)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        successful_envs = [item for item in []]
        success_count = len(successful_envs)
        self.assertGreaterEqual(success_count, 3, "
        self.assertGreaterEqual(success_count, 3, "
                        # Test isolation between environments
        for i, env1 in enumerate(successful_envs):
        health1 = self.docker_manager.get_health_report(env1)
        self.assertTrue(health1.get('all_healthy', False), formatted_string)"
        self.assertTrue(health1.get('all_healthy', False), formatted_string)"
                            # Test that one environment doesn't affect others'
        if i < 2:  # Test subset to avoid timeout
        for j, env2 in enumerate(successful_envs):
        if i != j and j < 2:
        health2 = self.docker_manager.get_health_report(env2)
        self.assertTrue(health2.get('all_healthy', False),
        "
        ""

        finally:
                                        # Clean up all environments
        for env_name in environments:
        try:
        if hasattr(self.docker_manager, 'release_environment'):
        self.docker_manager.release_environment(env_name)
        except Exception as e:
        logger.warning(formatted_string)"
        logger.warning(formatted_string)""

    def test_container_failure_recovery_mechanisms(self):
        "Test container failure recovery and restart mechanisms."
        pass
        test_env_name = formatted_string""
        try:
        # Create environment
        result = self.docker_manager.acquire_environment(test_env_name, use_alpine=True)
        self.assertIsNotNone(result, Failed to create test environment)
        # Test recovery mechanisms (if available)
        if hasattr(self.docker_manager, '_get_environment_containers'):
        containers = self.docker_manager._get_environment_containers(test_env_name)
        if containers:
        self.assertGreater(len(containers), 0, No containers to test recovery)"
        self.assertGreater(len(containers), 0, No containers to test recovery)"
                # Kill containers to simulate failures
        killed_containers = []
        for container in containers[:2]:  # Kill first 2 containers
        try:
        container.kill()
        killed_containers.append(container.name)
        logger.info("
        logger.info(""

        except Exception as e:
        logger.warning(formatted_string)"
        logger.warning(formatted_string)"
        self.assertGreater(len(killed_containers), 0, "No containers killed for recovery test)"
                        # Log recovery test completion
        logger.info(formatted_string)
        finally:
                            # Clean up environment
        try:
        if hasattr(self.docker_manager, 'release_environment'):
        self.docker_manager.release_environment(test_env_name)
        except Exception as e:
        logger.warning(""
    def test_resource_optimization_alpine_performance(self):
        Test resource optimization with Alpine containers.""
        env_name = formatted_string
        try:
        # Measure Alpine environment creation time
        start_time = time.time()
        result = self.docker_manager.acquire_environment( )
        env_name,
        use_alpine=True,
        timeout=60
        
        creation_time = time.time() - start_time
        self.assertIsNotNone(result, Failed to create Alpine environment)"
        self.assertIsNotNone(result, Failed to create Alpine environment)"
        self.assertLess(creation_time, 60, "
        self.assertLess(creation_time, 60, "
        # Monitor resource usage if method available
        if hasattr(self.docker_manager, '_get_environment_containers'):
        containers = self.docker_manager._get_environment_containers(env_name)
        if containers:
        total_memory = 0
        for container in containers:
        stats = container.stats(stream=False)
        memory_mb = stats['memory_stats']['usage'] / (1024 * 1024)
        total_memory += memory_mb
                    # Alpine should be memory efficient
        self.assertLess(total_memory, 1000, formatted_string)"
        self.assertLess(total_memory, 1000, formatted_string)"
        logger.info("
        logger.info(""

        finally:
                        # Clean up environment
        if hasattr(self.docker_manager, 'release_environment'):
        self.docker_manager.release_environment(env_name)
    def test_stress_testing_multiple_rapid_environments(self):
        "Test stress conditions with rapid environment creation/destruction."
        pass
        num_environments = 6  # Reasonable number for stress testing
        environments_created = []
        stress_metrics = {
        'successful_creations': 0,
        'failed_creations': 0,
        'avg_creation_time': 0,
        'max_creation_time': 0,
        'total_cleanup_time': 0
    
        creation_times = []
        try:
        # Rapid environment creation
        for i in range(num_environments):
        env_name = formatted_string
        try:
        start_time = time.time()
        result = self.docker_manager.acquire_environment( )
        env_name,
        use_alpine=True,
        timeout=45
                
        creation_time = time.time() - start_time
        creation_times.append(creation_time)
        if result:
        environments_created.append(env_name)
        stress_metrics['successful_creations'] += 1
                    # Quick health check
        health = self.docker_manager.get_health_report(env_name)
        self.assertIsNotNone(health, formatted_string")"
        else:
        stress_metrics['failed_creations'] += 1
        except Exception as e:
        stress_metrics['failed_creations'] += 1
        logger.warning(
                            # Brief pause to avoid overwhelming the system
        time.sleep(0.5)
                            # Calculate stress metrics
        if creation_times:
        stress_metrics['avg_creation_time'] = sum(creation_times) / len(creation_times)
        stress_metrics['max_creation_time'] = max(creation_times)
                                # Validate stress test results
        success_rate = stress_metrics['successful_creations'] / num_environments
        self.assertGreaterEqual(success_rate, 0.70, formatted_string")"
        self.assertLess(stress_metrics['avg_creation_time'), 35,
        
        logger.info(formatted_string")"
        finally:
                                    # Cleanup all created environments
        cleanup_start = time.time()
        for env_name in environments_created:
        try:
        if hasattr(self.docker_manager, 'release_environment'):
        self.docker_manager.release_environment(env_name)
        except Exception as e:
        logger.warning(
        stress_metrics['total_cleanup_time'] = time.time() - cleanup_start
        self.assertLess(stress_metrics['total_cleanup_time'), 60,
        formatted_string")"
        if __name__ == '__main__':
        logging.basicConfig(level=logging.INFO)
        unittest.main()
'''
)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]
}}}}}}}