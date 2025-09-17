class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message.
        if self._closed:
            raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        Close WebSocket connection.""
        self._closed = True
        self.is_connected = False
    def get_messages(self) -> list:
        Get all sent messages."
        return self.messages_sent.copy()
        '''
        Docker Stability Validation Suite - Comprehensive Real-World Testing
        This validation suite runs comprehensive stress tests to verify Docker stability improvements:
        1. Concurrent container operations without Docker daemon crashes
        2. Memory limit enforcement working correctly
        3. Rate limiter preventing API storms
        4. Safe container removal working properly
        5. No resource leaks after operations
        Business Value Justification (BVJ):
        1. Segment: Platform/Internal - Development Velocity, Risk Reduction
        2. Business Goal: Validate Docker infrastructure reliability for CI/CD and development
        3. Value Impact: Prevents 4-8 hours/week of developer downtime from Docker failures
        4. Revenue Impact: Protects development velocity for $2M+ ARR platform
        '''
        import asyncio
        import concurrent.futures
        import json
        import logging
        import os
        import psutil
        import subprocess
        import threading
        import time
        import unittest
        from contextlib import contextmanager
        from dataclasses import dataclass
        from pathlib import Path
        from typing import Dict, List, Optional, Set, Tuple, Any
            # Import Docker management infrastructure
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
            
        from test_framework.docker_port_discovery import DockerPortDiscovery
        from test_framework.dynamic_port_allocator import DynamicPortAllocator
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        logger = logging.getLogger(__name__)
        @dataclass
class ValidationResult:
        "Result of a validation test.
        test_name: str
        success: bool
        duration: float
        metrics: Dict[str, Any]
        errors: List[str]
        warnings: List[str]
        @dataclass
class StressTestResult:
        ""Result of a stress test scenario.
        scenario: str
        total_operations: int
        successful_operations: int
        failed_operations: int
        success_rate: float
        avg_operation_time: float
        max_concurrent_operations: int
        resource_usage: Dict[str, float]
        errors: List[str]
class DockerStabilityValidator:
        Comprehensive Docker stability validation system.""
    def __init__(self):
        self.test_id = formatted_string
        self.created_containers: Set[str] = set()
        self.created_networks: Set[str] = set()
        self.created_volumes: Set[str] = set()
        self.allocated_ports: Set[int] = set()
        self.validation_results: List[ValidationResult] = []
        self.rate_limiter = get_docker_rate_limiter()
    # Performance tracking
        self.start_time = time.time()
        self.docker_operations_count = 0
        self.peak_memory_usage = 0
        self.peak_cpu_usage = 0
    # Resource tracking
        self.initial_containers = set()
        self.initial_networks = set()
        self.initial_volumes = set()
    def setup_validation(self) -> bool:
        "Set up validation environment and verify Docker availability."
        try:
        # Check Docker availability
        if not self._check_docker_availability():
        logger.error(Docker not available for validation)"
        return False
            # Record initial resource state
        self.initial_containers = self._get_docker_containers()
        self.initial_networks = self._get_docker_networks()
        self.initial_volumes = self._get_docker_volumes()
            # Clean up any previous test artifacts
        self._cleanup_test_artifacts()
        logger.info("
        return True
        except Exception as e:
        logger.error(formatted_string)"
        return False
    def cleanup_validation(self) -> bool:
        "Clean up validation environment and resources.
        try:
        # Clean up created resources
        self._cleanup_test_artifacts()
        # Verify no resource leaks
        final_containers = self._get_docker_containers()
        final_networks = self._get_docker_networks()
        final_volumes = self._get_docker_volumes()
        # Check for leaks
        leaked_containers = final_containers - self.initial_containers
        leaked_networks = final_networks - self.initial_networks
        leaked_volumes = final_volumes - self.initial_volumes
        # Filter out system/non-test resources
        test_leaked_containers = [item for item in []]
        test_leaked_networks = [item for item in []]
        test_leaked_volumes = [item for item in []]
        if test_leaked_containers or test_leaked_networks or test_leaked_volumes:
        logger.warning(formatted_string" )"
        
        return False
        logger.info(Validation cleanup complete - no resource leaks detected")"
        return True
        except Exception as e:
        logger.error(
        return False
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        ""Run all validation scenarios and return comprehensive report.
        if not self.setup_validation():
        return {success: False, error": "Failed to setup validation environment}
        try:
            # Run all validation scenarios
        scenarios = [
        (Docker Lifecycle Management, self._validate_docker_lifecycle_management),
        ("Concurrent Operations Stability, self._validate_concurrent_operations_stability),"
        (Memory Limits Enforcement, self._validate_memory_limits_enforcement),
        (Rate Limiter Functionality, self._validate_rate_limiter_functionality),"
        (Safe Container Removal", self._validate_safe_container_removal),
        (Resource Leak Prevention, self._validate_resource_leak_prevention),
        (Docker Daemon Resilience", self._validate_docker_daemon_resilience),"
        (Stress Test Suite, self._run_stress_test_suite)
            
        overall_success = True
        for scenario_name, scenario_func in scenarios:
        logger.info(formatted_string)"
        try:
        result = scenario_func()
        self.validation_results.append(result)
        if not result.success:
        overall_success = False
        logger.error("
        else:
        logger.info(formatted_string)"
        except Exception as e:
        logger.error("
        overall_success = False
                                # Add failed result
        self.validation_results.append(ValidationResult( ))
        test_name=scenario_name,
        success=False,
        duration=0,
        metrics={},
        errors=[str(e)],
        warnings=[]
                                
                                # Generate final report
        report = self._generate_comprehensive_report(overall_success)
                                # Cleanup
        cleanup_success = self.cleanup_validation()
        report[cleanup_success] = cleanup_success"
        return report
        except Exception as e:
        logger.error("
        self.cleanup_validation()
        return {success: False, "error: str(e)}
    def _validate_docker_lifecycle_management(self) -> ValidationResult:
        "Validate Docker lifecycle management operations.
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        # Test container lifecycle
        container_name = ""
        # Create container
        create_start = time.time()
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest', 'sleep', '60'
        
        create_time = time.time() - create_start
        if create_result.returncode != 0:
        errors.append(formatted_string)
        return ValidationResult(Docker Lifecycle Management, False,"
        time.time() - start_time, metrics, errors, warnings)
        self.created_containers.add(container_name)
        metrics['container_create_time'] = create_time
            # Inspect container
        inspect_start = time.time()
        inspect_result = self._execute_docker_command(['docker', 'inspect', container_name]
        inspect_time = time.time() - inspect_start
        if inspect_result.returncode != 0:
        errors.append(formatted_string")
        else:
        metrics['container_inspect_time'] = inspect_time
                    # Verify container is running
        container_info = json.loads(inspect_result.stdout)[0]
        if container_info['State']['Status'] != 'running':
        errors.append("
                        # Stop container gracefully
        stop_start = time.time()
        stop_result = self._execute_docker_command(['docker', 'stop', '--time', '10', container_name]
        stop_time = time.time() - stop_start
        if stop_result.returncode != 0:
        errors.append(formatted_string")
        else:
        metrics['container_stop_time'] = stop_time
        if stop_time > 15:
        warnings.append("
                                    # Remove container
        rm_start = time.time()
        rm_result = self._execute_docker_command(['docker', 'rm', container_name]
        rm_time = time.time() - rm_start
        if rm_result.returncode != 0:
        errors.append(formatted_string")
        else:
        metrics['container_remove_time'] = rm_time
        self.created_containers.discard(container_name)
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult(Docker Lifecycle Management, success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Docker Lifecycle Management", False,"
        time.time() - start_time, metrics, errors, warnings)
    def _validate_concurrent_operations_stability(self) -> ValidationResult:
        Validate stability under concurrent Docker operations."
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        num_workers = 8
        operations_per_worker = 5
        operation_results = []
        operation_lock = threading.Lock()
    def concurrent_operations(worker_id):
        "Perform Docker operations concurrently.
        worker_results = []
        for op_id in range(operations_per_worker):
        container_name = ""
        try:
            # Create container
        op_start = time.time()
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest', 'sleep', '30'
            
        if create_result.returncode == 0:
        with operation_lock:
        self.created_containers.add(container_name)
                    # Quick inspect
        inspect_result = self._execute_docker_command(['docker', 'inspect', container_name]
                    # Stop and remove
        stop_result = self._execute_docker_command(['docker', 'stop', container_name]
        rm_result = self._execute_docker_command(['docker', 'rm', container_name]
        op_time = time.time() - op_start
        success = all(]
        create_result.returncode == 0,
        inspect_result.returncode == 0,
        stop_result.returncode == 0,
        rm_result.returncode == 0
                    
        worker_results.append()
        'worker_id': worker_id,
        'op_id': op_id,
        'success': success,
        'duration': op_time,
        'container_name': container_name
                    
        if rm_result.returncode == 0:
        with operation_lock:
        self.created_containers.discard(container_name)
        else:
        worker_results.append()
        'worker_id': worker_id,
        'op_id': op_id,
        'success': False,
        'error': create_result.stderr,
        'container_name': container_name
                                
        except Exception as e:
        worker_results.append()
        'worker_id': worker_id,
        'op_id': op_id,
        'success': False,
        'error': str(e),
        'container_name': container_name
                                    
        with operation_lock:
        operation_results.extend(worker_results)
                                        # Run concurrent operations
        concurrent_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(concurrent_operations, i) for i in range(num_workers)]
        for future in futures:
        future.result()  # Wait for completion
        concurrent_duration = time.time() - concurrent_start
                                                # Analyze results
        total_ops = len(operation_results)
        successful_ops = len([item for item in []]
        success_rate = successful_ops / total_ops if total_ops > 0 else 0
                                                # Calculate metrics
        successful_durations = [op['duration'] for op in operation_results )
        if op.get('success', False) and 'duration' in op]
        metrics.update()
        'total_operations': total_ops,
        'successful_operations': successful_ops,
        'success_rate': success_rate,
        'concurrent_duration': concurrent_duration,
        'avg_operation_time': sum(successful_durations) / len(successful_durations) if successful_durations else 0,
        'max_operation_time': max(successful_durations) if successful_durations else 0,
        'min_operation_time': min(successful_durations) if successful_durations else 0
                                                
                                                # Validate results
        if success_rate < 0.85:
        errors.append(formatted_string)
        if concurrent_duration > 120:
        warnings.append(""
                                                        # Verify Docker daemon is still responsive
        version_result = self._execute_docker_command(['docker', 'version']
        if version_result.returncode != 0:
        errors.append(Docker daemon not responsive after concurrent operations)
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult(Concurrent Operations Stability, success,"
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Concurrent Operations Stability", False,
        time.time() - start_time, metrics, errors, warnings)
    def _validate_memory_limits_enforcement(self) -> ValidationResult:
        Validate memory limits are properly enforced.""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        container_name = formatted_string
        memory_limit = 128m"
        # Create container with memory limit
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        '--memory', memory_limit,
        'alpine:latest', 'sleep', '60'
        
        if create_result.returncode != 0:
        errors.append(formatted_string")
        return ValidationResult(Memory Limits Enforcement, False,
        time.time() - start_time, metrics, errors, warnings)
        self.created_containers.add(container_name)
            # Wait for container to start
        time.sleep(2)
            # Verify memory limit is set correctly
        inspect_result = self._execute_docker_command(['docker', 'inspect', container_name,
        '--format', '{{.HostConfig.Memory}}']
        if inspect_result.returncode != 0:
        errors.append(formatted_string")"
        else:
        expected_memory = 134217728  # 128MB in bytes
        actual_memory = int(inspect_result.stdout.strip())
        metrics['expected_memory_bytes'] = expected_memory
        metrics['actual_memory_bytes'] = actual_memory
        if actual_memory != expected_memory:
        errors.append(
                        # Test memory enforcement with stress command
        stress_result = self._execute_docker_command(]
        'docker', 'exec', container_name,
        'sh', '-c', 'dd if=/dev/zero of=/tmp/big bs=1M count=200 2>&1 || echo Memory limit enforced"'"
        ], timeout=30)
                        # Check if memory limit was enforced
        if stress_result.returncode == 0:
        if Memory limit enforced in stress_result.stdout:
        metrics['memory_enforcement_working'] = True
        else:
                                    # Check if container was killed due to memory
        inspect_result = self._execute_docker_command(]
        'docker', 'inspect', container_name,
        '--format', '{{.State.Status}} {{.State.OOMKilled}}'
                                    
        if inspect_result.returncode == 0:
        status_parts = inspect_result.stdout.strip().split()
        if len(status_parts) >= 2:
        status, oom_killed = status_parts[0], status_parts[1]
        metrics['container_status_after_stress'] = status
        metrics['oom_killed'] = oom_killed == 'true'
        if oom_killed != 'true' and status == 'running':
        warnings.append(Memory stress test did not trigger OOM killer as expected)"
        else:
                                                    # Command failed, which could indicate memory enforcement
        metrics['memory_enforcement_working'] = True
        metrics['stress_command_failed'] = True
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult("Memory Limits Enforcement, success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Memory Limits Enforcement, False,
        time.time() - start_time, metrics, errors, warnings)
    def _validate_rate_limiter_functionality(self) -> ValidationResult:
        "Validate rate limiter is working correctly."
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        # Test rate limiter with rapid commands
        rate_limiter = DockerRateLimiter(min_interval=1.0, max_concurrent=2)
        execution_times = []
    def timed_operation(op_id):
        op_start = time.time()
        result = rate_limiter.execute_docker_command(['docker', 'version'], timeout=10)
        op_end = time.time()
        return {
        'op_id': op_id,
        'start_time': op_start,
        'end_time': op_end,
        'duration': op_end - op_start,
        'success': result.returncode == 0
    
    # Execute operations rapidly
        rapid_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(timed_operation, i) for i in range(10)]
        results = [future.result() for future in futures]
        rapid_duration = time.time() - rapid_start
        # Analyze timing
        results.sort(key=lambda x: None x['start_time']
        # Check for rate limiting behavior
        gaps = []
        for i in range(1, len(results)):
        gap = results[i]['start_time'] - results[i-1]['start_time']
        gaps.append(gap)
            # Should see some gaps indicating rate limiting
        significant_gaps = [item for item in []]  # Allow some tolerance
        metrics.update()
        'total_operations': len(results),
        'successful_operations': len([item for item in []]],
        'rapid_execution_duration': rapid_duration,
        'avg_gap_between_operations': sum(gaps) / len(gaps) if gaps else 0,
        'significant_gaps_count': len(significant_gaps),
        'min_gap': min(gaps) if gaps else 0,
        'max_gap': max(gaps) if gaps else 0
            
            # Validate rate limiting effectiveness
        if len(significant_gaps) == 0:
        warnings.append(No significant gaps detected - rate limiter may not be active)"
        success_rate = metrics['successful_operations'] / metrics['total_operations']
        if success_rate < 0.9:
        errors.append("
                    # Test concurrent limit enforcement
        concurrent_count = 0
        max_concurrent = 0
        lock = threading.Lock()
    def concurrent_operation():
        nonlocal concurrent_count, max_concurrent
    def mock_run(cmd, **kwargs):
        nonlocal concurrent_count, max_concurrent
        with lock:
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        time.sleep(0.5)  # Simulate work
        with lock:
        concurrent_count -= 1
        return subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=10)
        return rate_limiter.execute_docker_command(['docker', 'version'], timeout=15)
            # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(concurrent_operation) for _ in range(5)]
        concurrent_results = [future.result() for future in futures]
        metrics['max_concurrent_observed'] = max_concurrent
        metrics['concurrent_limit_enforced'] = max_concurrent <= 2
        if max_concurrent > 2:
        errors.append(formatted_string)"
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult("Rate Limiter Functionality, success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Rate Limiter Functionality, False,
        time.time() - start_time, metrics, errors, warnings)
    def _validate_safe_container_removal(self) -> ValidationResult:
        "Validate safe container removal procedures."
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        # Test graceful container shutdown
        graceful_container = formatted_string"
        # Create container that handles signals
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', graceful_container,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'trap "echo Received SIGTERM; exit 0 TERM; while true; do sleep 1; done'
        
        if create_result.returncode != 0:
        errors.append(formatted_string)
        return ValidationResult("Safe Container Removal, False,"
        time.time() - start_time, metrics, errors, warnings)
        self.created_containers.add(graceful_container)
        time.sleep(2)  # Let container start
            # Test graceful stop
        graceful_start = time.time()
        stop_result = self._execute_docker_command(['docker', 'stop', '--time', '10', graceful_container]
        graceful_time = time.time() - graceful_start
        if stop_result.returncode != 0:
        errors.append(formatted_string)
        else:
        metrics['graceful_stop_time'] = graceful_time
        if graceful_time > 15:
        warnings.append(""
                        # Verify exit code
        inspect_result = self._execute_docker_command(]
        'docker', 'inspect', graceful_container, '--format', '{{.State.ExitCode}}'
                        
        if inspect_result.returncode == 0:
        exit_code = int(inspect_result.stdout.strip())
        metrics['graceful_exit_code'] = exit_code
        if exit_code != 0:
        warnings.append(formatted_string)
                                # Test unresponsive container handling
        unresponsive_container = formatted_string"
                                # Create container that ignores signals
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', unresponsive_container,
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'trap " TERM; while true; do sleep 1; done'
                                
        if create_result.returncode != 0:
        errors.append("
        else:
        self.created_containers.add(unresponsive_container)
        time.sleep(2)  # Let container start
                                        # Test force stop behavior
        force_start = time.time()
        stop_result = self._execute_docker_command(['docker', 'stop', '--time', '3', unresponsive_container]
        force_time = time.time() - force_start
        if stop_result.returncode != 0:
        errors.append(formatted_string")
        else:
        metrics['force_stop_time'] = force_time
                                                # Should take at least the timeout period plus some kill time
        if force_time < 3:
        warnings.append("
        elif force_time > 10:
        warnings.append(formatted_string")
                                                        # Test removal of stopped containers
        removal_times = []
        for container in [graceful_container, unresponsive_container]:
        if container in self.created_containers:
        rm_start = time.time()
        rm_result = self._execute_docker_command(['docker', 'rm', container]
        rm_time = time.time() - rm_start
        if rm_result.returncode == 0:
        removal_times.append(rm_time)
        self.created_containers.discard(container)
        else:
        errors.append("
        if removal_times:
        metrics['avg_removal_time'] = sum(removal_times) / len(removal_times)
        metrics['max_removal_time'] = max(removal_times)
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult(Safe Container Removal", success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Safe Container Removal, False,
        time.time() - start_time, metrics, errors, warnings)
    def _validate_resource_leak_prevention(self) -> ValidationResult:
        ""Validate that operations don't leave resource leaks.
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        # Record initial resource state
        initial_containers = self._get_docker_containers()
        initial_networks = self._get_docker_networks()
        initial_volumes = self._get_docker_volumes()
        # Create and destroy resources multiple times
        leak_test_containers = []
        leak_test_networks = []
        leak_test_volumes = []
        for i in range(5):
            # Create resources
        container_name = formatted_string"
        network_name = formatted_string"
        volume_name = formatted_string
            # Create volume
        vol_result = self._execute_docker_command(['docker', 'volume', 'create', volume_name]
        if vol_result.returncode == 0:
        leak_test_volumes.append(volume_name)
                # Create network
        net_result = self._execute_docker_command(['docker', 'network', 'create', network_name]
        if net_result.returncode == 0:
        leak_test_networks.append(network_name)
                    # Create container using network and volume
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        '-v', 'formatted_string',
        'alpine:latest', 'sleep', '10'
                    
        if create_result.returncode == 0:
        leak_test_containers.append(container_name)
                        # Brief pause
        time.sleep(1)
                        # Wait for containers to finish
        time.sleep(12)
                        # Clean up resources
        cleanup_errors = []
                        # Stop and remove containers
        for container_name in leak_test_containers:
        stop_result = self._execute_docker_command(['docker', 'stop', container_name]
        rm_result = self._execute_docker_command(['docker', 'rm', container_name]
        if rm_result.returncode != 0:
        cleanup_errors.append(formatted_string")"
                                # Remove networks
        for network_name in leak_test_networks:
        rm_result = self._execute_docker_command(['docker', 'network', 'rm', network_name]
        if rm_result.returncode != 0:
        cleanup_errors.append(
                                        # Remove volumes
        for volume_name in leak_test_volumes:
        rm_result = self._execute_docker_command(['docker', 'volume', 'rm', volume_name]
        if rm_result.returncode != 0:
        cleanup_errors.append(formatted_string")"
                                                # Wait for cleanup to complete
        time.sleep(3)
                                                # Check for leaks
        final_containers = self._get_docker_containers()
        final_networks = self._get_docker_networks()
        final_volumes = self._get_docker_volumes()
                                                # Calculate changes
        container_changes = final_containers - initial_containers
        network_changes = final_networks - initial_networks
        volume_changes = final_volumes - initial_volumes
                                                # Filter for test-related resources
        leaked_containers = [item for item in []]
        leaked_networks = [item for item in []]
        leaked_volumes = [item for item in []]
        metrics.update()
        'resources_created': len(leak_test_containers) + len(leak_test_networks) + len(leak_test_volumes),
        'cleanup_errors': len(cleanup_errors),
        'leaked_containers': len(leaked_containers),
        'leaked_networks': len(leaked_networks),
        'leaked_volumes': len(leaked_volumes),
        'total_leaks': len(leaked_containers) + len(leaked_networks) + len(leaked_volumes)
                                                
                                                # Validate no leaks
        if leaked_containers:
        errors.extend([formatted_string for c in leaked_containers]
        if leaked_networks:
        errors.extend([formatted_string for n in leaked_networks]"
        if leaked_volumes:
        errors.extend(["formatted_string for v in leaked_volumes]
        if cleanup_errors:
        warnings.extend(cleanup_errors)
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult(Resource Leak Prevention, success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult("Resource Leak Prevention, False,"
        time.time() - start_time, metrics, errors, warnings)
    def _validate_docker_daemon_resilience(self) -> ValidationResult:
        Validate Docker daemon remains stable under stress."
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        # Monitor Docker daemon responsiveness
        responsiveness_tests = []
        # Baseline responsiveness
        baseline_start = time.time()
        baseline_result = self._execute_docker_command(['docker', 'version']
        baseline_time = time.time() - baseline_start
        if baseline_result.returncode != 0:
        errors.append("Docker daemon not responsive at baseline)
        return ValidationResult(Docker Daemon Resilience, False,
        time.time() - start_time, metrics, errors, warnings)
        responsiveness_tests.append(('baseline', baseline_time))
            # Stress test with rapid operations
        stress_operations = []
        for i in range(20):
        op_start = time.time()
        result = self._execute_docker_command(['docker', 'images', '--quiet']
        op_time = time.time() - op_start
        stress_operations.append()
        'operation': i,
        'success': result.returncode == 0,
        'time': op_time
                
        if i % 5 == 4:  # Check responsiveness every 5 operations
        resp_start = time.time()
        resp_result = self._execute_docker_command(['docker', 'version']
        resp_time = time.time() - resp_start
        responsiveness_tests.append(('formatted_string', resp_time))
        if resp_result.returncode != 0:
        errors.append(""
        time.sleep(0.1)  # Brief pause
                    # Post-stress responsiveness
        post_stress_start = time.time()
        post_stress_result = self._execute_docker_command(['docker', 'version']
        post_stress_time = time.time() - post_stress_start
        if post_stress_result.returncode != 0:
        errors.append(Docker daemon not responsive after stress test)
        else:
        responsiveness_tests.append(('post_stress', post_stress_time))
                            # Analyze results
        successful_ops = len([item for item in []]]
        success_rate = successful_ops / len(stress_operations) if stress_operations else 0
        avg_op_time = sum(op[item for item in []] / successful_ops if successful_ops > 0 else 0
        response_times = [time for _, time in responsiveness_tests]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        metrics.update()
        'baseline_response_time': baseline_time,
        'post_stress_response_time': post_stress_time,
        'avg_response_time': avg_response_time,
        'max_response_time': max(response_times) if response_times else 0,
        'stress_operations_total': len(stress_operations),
        'stress_operations_successful': successful_ops,
        'stress_success_rate': success_rate,
        'avg_stress_operation_time': avg_op_time
                            
                            # Validate daemon stability
        if success_rate < 0.9:
        errors.append(""
        if post_stress_time > baseline_time * 3:
        warnings.append(formatted_string)
        if avg_response_time > 5.0:
        warnings.append(""
        success = len(errors) == 0
        duration = time.time() - start_time
        return ValidationResult(Docker Daemon Resilience, success,
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult("Docker Daemon Resilience, False,"
        time.time() - start_time, metrics, errors, warnings)
    def _run_stress_test_suite(self) -> ValidationResult:
        Run comprehensive stress test scenarios."
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        try:
        stress_scenarios = [
        ("Rapid Container Creation/Destruction, self._stress_container_lifecycle),
        (Network Operations Under Load, self._stress_network_operations),
        ("Volume Operations Under Load, self._stress_volume_operations),"
        (High Concurrency Operations, self._stress_high_concurrency)
        
        stress_results = []
        for scenario_name, scenario_func in stress_scenarios:
        logger.info(""
        try:
        scenario_start = time.time()
        result = scenario_func()
        scenario_duration = time.time() - scenario_start
        result.scenario = scenario_name
        stress_results.append(result)
        logger.info(formatted_string )
        ""
        except Exception as e:
        logger.error(formatted_string)
        errors.append(""
                    # Aggregate metrics
        if stress_results:
        total_ops = sum(r.total_operations for r in stress_results)
        successful_ops = sum(r.successful_operations for r in stress_results)
        overall_success_rate = successful_ops / total_ops if total_ops > 0 else 0
        avg_success_rate = sum(r.success_rate for r in stress_results) / len(stress_results)
        metrics.update()
        'stress_scenarios_run': len(stress_results),
        'total_stress_operations': total_ops,
        'successful_stress_operations': successful_ops,
        'overall_stress_success_rate': overall_success_rate,
        'average_scenario_success_rate': avg_success_rate,
        'scenario_results': [
        {
        'scenario': r.scenario,
        'success_rate': r.success_rate,
        'total_ops': r.total_operations,
        'avg_time': r.avg_operation_time
        } for r in stress_results
                        
                        
                        # Validate overall performance
        if overall_success_rate < 0.8:
        errors.append(formatted_string)
        if avg_success_rate < 0.85:
        warnings.append(""
        else:
        errors.append(No stress scenarios completed successfully)
        success = len(errors) == 0 and len(stress_results) > 0
        duration = time.time() - start_time
        return ValidationResult(Stress Test Suite, success,"
        duration, metrics, errors, warnings)
        except Exception as e:
        errors.append(str(e))
        return ValidationResult(Stress Test Suite", False,
        time.time() - start_time, metrics, errors, warnings)
    def _stress_container_lifecycle(self) -> StressTestResult:
        Stress test container creation and destruction.""
        total_operations = 15
        successful_operations = 0
        operation_times = []
        errors = []
        max_concurrent = 0
        concurrent_count = 0
        lock = threading.Lock()
    def lifecycle_operation(op_id):
        nonlocal successful_operations, max_concurrent, concurrent_count
        container_name = formatted_string
        try:
        with lock:
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        op_start = time.time()
            # Create
        create_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--label', 'formatted_string',
        'alpine:latest', 'sleep', '5'
            
        if create_result.returncode == 0:
        self.created_containers.add(container_name)
                # Wait briefly
        time.sleep(1)
                # Stop
        stop_result = self._execute_docker_command(['docker', 'stop', container_name]
                # Remove
        rm_result = self._execute_docker_command(['docker', 'rm', container_name]
        op_time = time.time() - op_start
        if all(r.returncode == 0 for r in [create_result, stop_result, rm_result]:
        with lock:
        successful_operations += 1
        operation_times.append(op_time)
        self.created_containers.discard(container_name)
        else:
        errors.append(""
        else:
        errors.append(formatted_string)
        except Exception as e:
        errors.append(""
        finally:
        with lock:
        concurrent_count -= 1
                                            # Run operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(lifecycle_operation, i) for i in range(total_operations)]
        for future in futures:
        future.result()
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_time = sum(operation_times) / len(operation_times) if operation_times else 0
        return StressTestResult( )
        scenario=Container Lifecycle,
        total_operations=total_operations,
        successful_operations=successful_operations,
        failed_operations=total_operations - successful_operations,
        success_rate=success_rate,
        avg_operation_time=avg_time,
        max_concurrent_operations=max_concurrent,
        resource_usage={},
        errors=errors[:10]  # Limit error list
                                                    
    def _stress_network_operations(self) -> StressTestResult:
        Stress test network operations.""
        total_operations = 10
        successful_operations = 0
        operation_times = []
        errors = []
        for i in range(total_operations):
        network_name = formatted_string
        try:
        op_start = time.time()
            # Create network
        create_result = self._execute_docker_command(]
        'docker', 'network', 'create', network_name
            
        if create_result.returncode == 0:
        self.created_networks.add(network_name)
                # Create container on network
        container_name = ""
        container_result = self._execute_docker_command(]
        'docker', 'run', '-d', '--name', container_name,
        '--network', network_name,
        '--label', 'formatted_string',
        'alpine:latest', 'sleep', '5'
                
        if container_result.returncode == 0:
        self.created_containers.add(container_name)
        time.sleep(1)
                    # Clean up
        self._execute_docker_command(['docker', 'stop', container_name]
        self._execute_docker_command(['docker', 'rm', container_name]
        self.created_containers.discard(container_name)
                    # Remove network
        rm_result = self._execute_docker_command(['docker', 'network', 'rm', network_name]
        op_time = time.time() - op_start
        if rm_result.returncode == 0:
        successful_operations += 1
        operation_times.append(op_time)
        self.created_networks.discard(network_name)
        else:
        errors.append(formatted_string)
        else:
        errors.append(""
        except Exception as e:
        errors.append(formatted_string)
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_time = sum(operation_times) / len(operation_times) if operation_times else 0
        return StressTestResult( )
        scenario=Network Operations,"
        total_operations=total_operations,
        successful_operations=successful_operations,
        failed_operations=total_operations - successful_operations,
        success_rate=success_rate,
        avg_operation_time=avg_time,
        max_concurrent_operations=1,
        resource_usage={},
        errors=errors[:5]
                                    
    def _stress_volume_operations(self) -> StressTestResult:
        "Stress test volume operations.
        total_operations = 8
        successful_operations = 0
        operation_times = []
        errors = []
        for i in range(total_operations):
        volume_name = ""
        try:
        op_start = time.time()
            # Create volume
        create_result = self._execute_docker_command(]
        'docker', 'volume', 'create', volume_name
            
        if create_result.returncode == 0:
        self.created_volumes.add(volume_name)
                # Use volume in container
        container_name = formatted_string
        container_result = self._execute_docker_command(]
        'docker', 'run', '--name', container_name,
        '-v', 'formatted_string',
        '--label', 'formatted_string',
        'alpine:latest',
        'sh', '-c', 'echo test data > /data/test.txt && cat /data/test.txt'"
                
        if container_result.returncode == 0:
        self.created_containers.add(container_name)
                    # Clean up container
        self._execute_docker_command(['docker', 'rm', container_name]
        self.created_containers.discard(container_name)
                    # Remove volume
        rm_result = self._execute_docker_command(['docker', 'volume', 'rm', volume_name]
        op_time = time.time() - op_start
        if rm_result.returncode == 0:
        successful_operations += 1
        operation_times.append(op_time)
        self.created_volumes.discard(volume_name)
        else:
        errors.append(formatted_string")
        else:
        errors.append("
        except Exception as e:
        errors.append(formatted_string")
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_time = sum(operation_times) / len(operation_times) if operation_times else 0
        return StressTestResult( )
        scenario=Volume Operations,
        total_operations=total_operations,
        successful_operations=successful_operations,
        failed_operations=total_operations - successful_operations,
        success_rate=success_rate,
        avg_operation_time=avg_time,
        max_concurrent_operations=1,
        resource_usage={},
        errors=errors[:5]
                                    
    def _stress_high_concurrency(self) -> StressTestResult:
        ""Stress test high concurrency operations.
        total_operations = 20
        successful_operations = 0
        operation_times = []
        errors = []
        max_concurrent = 0
        concurrent_count = 0
        lock = threading.Lock()
    def concurrent_operation(op_id):
        nonlocal successful_operations, max_concurrent, concurrent_count
        try:
        with lock:
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        op_start = time.time()
            # Simple but resource-intensive operation
        result = self._execute_docker_command(['docker', 'images', '--all']
        op_time = time.time() - op_start
        if result.returncode == 0:
        with lock:
        successful_operations += 1
        operation_times.append(op_time)
        else:
        errors.append(""
        except Exception as e:
        errors.append(formatted_string)
        finally:
        with lock:
        concurrent_count -= 1
                                    # Run with high concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(concurrent_operation, i) for i in range(total_operations)]
        for future in futures:
        future.result()
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_time = sum(operation_times) / len(operation_times) if operation_times else 0
        return StressTestResult( )
        scenario=High Concurrency,"
        total_operations=total_operations,
        successful_operations=successful_operations,
        failed_operations=total_operations - successful_operations,
        success_rate=success_rate,
        avg_operation_time=avg_time,
        max_concurrent_operations=max_concurrent,
        resource_usage={},
        errors=errors[:10]
                                            
    def _generate_comprehensive_report(self, overall_success: bool) -> Dict[str, Any]:
        "Generate comprehensive validation report.
        total_duration = time.time() - self.start_time
    # Aggregate metrics
        total_tests = len(self.validation_results)
        passed_tests = len([item for item in []]
        failed_tests = total_tests - passed_tests
        all_errors = []
        all_warnings = []
        for result in self.validation_results:
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        # Performance summary
        test_durations = [r.duration for r in self.validation_results]
        avg_test_duration = sum(test_durations) / len(test_durations) if test_durations else 0
        # Resource usage summary
        final_containers = self._get_docker_containers()
        final_networks = self._get_docker_networks()
        final_volumes = self._get_docker_volumes()
        report = {
        "validation_summary: {"
        overall_success: overall_success,
        total_duration_seconds: round(total_duration, 2),"
        timestamp": datetime.now().isoformat(),
        test_id: self.test_id
        },
        test_results": {"
        total_tests: total_tests,
        passed_tests: passed_tests,"
        "failed_tests: failed_tests,
        success_rate: round(passed_tests / total_tests * 100, 1) if total_tests > 0 else 0,
        "average_test_duration: round(avg_test_duration, 2)"
        },
        detailed_results: [
        {
        test_name: r.test_name,"
        success": r.success,
        duration: round(r.duration, 2),
        metrics": r.metrics,"
        error_count: len(r.errors),
        warning_count: len(r.warnings),"
        "errors: r.errors[:3],  # Limit for readability
        warnings: r.warnings[:3]
        
        for r in self.validation_results
        ],
        "performance_metrics: {"
        docker_operations_count: self.docker_operations_count,
        peak_memory_usage_mb: round(self.peak_memory_usage / (1024*1024), 1),"
        peak_cpu_usage_percent": round(self.peak_cpu_usage, 1),
        avg_test_duration: round(avg_test_duration, 2),
        max_test_duration": round(max(test_durations), 2) if test_durations else 0"
        },
        resource_status: {
        containers_at_start: len(self.initial_containers),"
        "containers_at_end: len(final_containers),
        networks_at_start: len(self.initial_networks),
        "networks_at_end: len(final_networks),"
        volumes_at_start: len(self.initial_volumes),
        volumes_at_end: len(final_volumes)"
        },
        validation_areas": {
        docker_lifecycle_management: self._get_test_status(Docker Lifecycle Management),
        "concurrent_operations_stability: self._get_test_status(Concurrent Operations Stability"),
        memory_limits_enforcement: self._get_test_status(Memory Limits Enforcement),
        rate_limiter_functionality: self._get_test_status(Rate Limiter Functionality"),
        "safe_container_removal: self._get_test_status(Safe Container Removal),
        resource_leak_prevention: self._get_test_status(Resource Leak Prevention),
        "docker_daemon_resilience: self._get_test_status(Docker Daemon Resilience"),
        stress_test_suite: self._get_test_status(Stress Test Suite)
        },
        issues_summary: {"
        total_errors": len(all_errors),
        total_warnings: len(all_warnings),
        critical_issues": [e for e in all_errors if any(keyword in e.lower() ))"
        for keyword in ['crash', 'fail', 'unresponsive', 'timeout']],
        top_errors: list(set(all_errors))[:10],
        top_warnings: list(set(all_warnings))[:10]"
        },
        "recommendations: self._generate_recommendations(overall_success, all_errors, all_warnings)
        
        return report
    def _get_test_status(self, test_name: str) -> str:
        Get status for a specific test.""
        for result in self.validation_results:
        if result.test_name == test_name:
        return PASS if result.success else FAIL
        return NOT_RUN"
    def _generate_recommendations(self, overall_success: bool, errors: List[str], warnings: List[str] -> List[str]:
        "Generate recommendations based on validation results.
        recommendations = []
        if not overall_success:
        recommendations.append("Docker stability improvements require attention before production deployment)"
        if any(memory in e.lower() for e in errors):
        recommendations.append(Review memory limit configurations and enforcement mechanisms)"
        if any(concurrent" in e.lower() for e in errors):
        recommendations.append(Investigate concurrent operation handling and rate limiting settings)
        if any(timeout" in e.lower() for e in errors + warnings):"
        recommendations.append(Consider increasing timeout values for Docker operations)
        if any(leak in e.lower() for e in errors):"
        recommendations.append("Implement additional resource cleanup monitoring)
        if any(unresponsive in e.lower() for e in errors):
        recommendations.append("Monitor Docker daemon health and consider restart mechanisms)"
        if len(warnings) > len(errors) * 2:
        recommendations.append(Address warning conditions to prevent future failures)
        if not recommendations:
        recommendations.append(Docker stability improvements are working effectively)"
        return recommendations
    def _check_docker_availability(self) -> bool:
        "Check if Docker is available and responsive.
        try:
        result = subprocess.run(['docker', 'version'],
        capture_output=True, timeout=10)
        return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    def _execute_docker_command(self, command: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        "Execute Docker command with rate limiting and monitoring."
        self.docker_operations_count += 1
    # Monitor resource usage
        try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent()
        self.peak_memory_usage = max(self.peak_memory_usage, memory_mb * 1024 * 1024)
        self.peak_cpu_usage = max(self.peak_cpu_usage, cpu_percent)
        except:
        pass  # Resource monitoring is optional
            # Use rate limiter for Docker operations
        return self.rate_limiter.execute_docker_command(command, timeout=timeout)
    def _get_docker_containers(self) -> Set[str]:
        "Get current Docker containers."
        try:
        result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}'],
        capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        return set(name.strip() for name in result.stdout.strip().split( ))
        ) if name.strip())
        except:
        pass
        return set()
    def _get_docker_networks(self) -> Set[str]:
        ""Get current Docker networks.
        try:
        result = subprocess.run(['docker', 'network', 'ls', '--format', '{{.Name}}'],
        capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        return set(name.strip() for name in result.stdout.strip().split( ))"
        ) if name.strip())
        except:
        pass
        return set()
    def _get_docker_volumes(self) -> Set[str]:
        "Get current Docker volumes.
        try:
        result = subprocess.run(['docker', 'volume', 'ls', '--format', '{{.Name}}'],
        capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
        return set(name.strip() for name in result.stdout.strip().split(" ))"
        ) if name.strip())
        except:
        pass
        return set()
    def _cleanup_test_artifacts(self):
        Clean up test artifacts and resources."
        try:
        # Remove test containers safely (no force flag)
        containers_to_remove = list(self.created_containers)
        for container_name in containers_to_remove:
            # First try to stop gracefully
        subprocess.run(['docker', 'stop', '--time', '10', container_name],
        capture_output=True, timeout=15)
            # Then remove the stopped container
        subprocess.run(['docker', 'rm', container_name],
        capture_output=True, timeout=10)
        self.created_containers.discard(container_name)
            # Remove test networks
        networks_to_remove = list(self.created_networks)
        for network_name in networks_to_remove:
        subprocess.run(['docker', 'network', 'rm', network_name],
        capture_output=True, timeout=10)
        self.created_networks.discard(network_name)
                # Remove test volumes (no force flag)
        volumes_to_remove = list(self.created_volumes)
        for volume_name in volumes_to_remove:
        subprocess.run(['docker', 'volume', 'rm', volume_name],
        capture_output=True, timeout=10)
        self.created_volumes.discard(volume_name)
        except Exception as e:
        logger.warning("
class DockerStabilityValidationTestSuite(unittest.TestCase):
        "Test suite wrapper for Docker stability validation."
    def setUp(self):
        Set up test environment.""
        logging.basicConfig(level=logging.INFO)
        self.validator = DockerStabilityValidator()
    def test_comprehensive_docker_stability_validation(self):
        Run comprehensive Docker stability validation."
        logger.info("Starting comprehensive Docker stability validation)
    # Run validation
        report = self.validator.run_comprehensive_validation()
    # Log report summary
        logger.info(=== DOCKER STABILITY VALIDATION REPORT ===)
        logger.info(""
        logger.info(formatted_string)
        logger.info(""
        logger.info(formatted_string)
    # Log validation areas
        logger.info(" )"
        === VALIDATION AREAS STATUS ===)
        for area, status in report['validation_areas'].items():
        logger.info(formatted_string)
        # Log issues
        if report['issues_summary']['total_errors'] > 0:
        logger.error(""
        for error in report['issues_summary']['top_errors']:
        logger.error(formatted_string)
        if report['issues_summary']['total_warnings'] > 0:
        logger.warning(""
        for warning in report['issues_summary']['top_warnings']:
        logger.warning(formatted_string)
                        # Log recommendations
        logger.info( )"
        === RECOMMENDATIONS ===)
        for recommendation in report['recommendations']:
        logger.info(formatted_string")
                            # Log performance metrics
        logger.info( )
        === PERFORMANCE METRICS ===)
        perf = report['performance_metrics']
        logger.info(formatted_string")"
        logger.info(
        logger.info(formatted_string")"
        logger.info(
                            # Save detailed report
        report_path = Path(__file__).parent / formatted_string""
        with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
        logger.info(
                                # Assert overall success
        self.assertTrue(report['validation_summary']['overall_success'],
        formatted_string")"
                                # Verify cleanup
        self.assertTrue(report.get('cleanup_success', False),
        Docker stability validation cleanup failed)
    def run_validation_cli():
        "Command line interface for running Docker stability validation."
        import argparse
        parser = argparse.ArgumentParser(description='Run Docker Stability Validation')
        parser.add_argument('--output-file', '-o', help='Output file for detailed report')
        parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode (less output)')
        args = parser.parse_args()
    # Configure logging
        level = logging.WARNING if args.quiet else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    # Run validation
        validator = DockerStabilityValidator()
        report = validator.run_comprehensive_validation()
    # Print summary
        print()"
         + "=*60)
        print(DOCKER STABILITY VALIDATION RESULTS)
        print(=*60)
        print(formatted_string")
        print("")
        print(formatted_string)
        print("")
    # Save report
        output_file = args.output_file or formatted_string
        with open(output_file, 'w') as f:
        json.dump(report, f, indent=2")
        print("")
        return 0 if report['validation_summary']['overall_success'] else 1
        if __name__ == '__main__':
        import sys
        if len(sys.argv) > 1:
                # CLI mode
        sys.exit(run_validation_cli())
        else:
                    # Test suite mode
        unittest.main(")