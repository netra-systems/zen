"""
Comprehensive Docker Health Monitoring and Container Validation Tests

This module contains validation tests for Docker container health during pytest collection:
- Container health monitoring during test collection phases
- Memory usage tracking and validation
- CPU usage monitoring and limits enforcement
- Network isolation and connectivity tests
- Container restart and recovery validation
- Service dependency health checks

These tests are designed to be DIFFICULT and catch regressions by validating
that Docker containers remain healthy under pytest collection stress.
"""

import asyncio
import docker
import json
import os
import psutil
import pytest
import subprocess
import sys
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import requests
import socket
from shared.isolated_environment import IsolatedEnvironment

# Docker client and container management
from docker.errors import DockerException, ContainerError, ImageNotFound, APIError

# Test framework imports
from test_framework.docker_test_utils import (
    DockerContainerManager,
    get_container_memory_stats,
    wait_for_container_health,
    force_container_restart
)


@dataclass
class ContainerHealthMetrics:
    """Container health metrics snapshot"""
    container_name: str
    status: str
    health_status: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_bytes: int
    network_tx_bytes: int
    uptime_seconds: float
    restart_count: int
    timestamp: float
    error_message: Optional[str] = None


@dataclass
class HealthValidationResult:
    """Result of health validation test"""
    test_name: str
    success: bool
    duration_seconds: float
    containers_monitored: int
    health_violations: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class DockerHealthMonitor:
    """
    Advanced Docker container health monitoring and validation
    """
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.docker_available = True
        except DockerException:
            self.docker_available = False
            self.docker_client = None
        
        self.monitoring_active = False
        self.health_history = []
        self.alert_thresholds = {
            'memory_percent': 85.0,    # 85% memory usage
            'cpu_percent': 80.0,       # 80% CPU usage
            'restart_count': 5,        # Max 5 restarts
            'response_time': 10.0      # 10 second response time
        }
    
    def get_container_health_metrics(self, container_name: str) -> Optional[ContainerHealthMetrics]:
        """Get comprehensive health metrics for a container"""
        if not self.docker_available:
            return None
            
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Get container stats
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100.0
            else:
                cpu_percent = 0.0
            
            # Memory stats
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
            
            # Network stats
            networks = stats.get('networks', {})
            total_rx = sum(net['rx_bytes'] for net in networks.values())
            total_tx = sum(net['tx_bytes'] for net in networks.values())
            
            # Container status
            container.reload()
            status = container.status
            
            # Health status
            health_status = "unknown"
            if hasattr(container.attrs, 'State') and 'Health' in container.attrs['State']:
                health_status = container.attrs['State']['Health']['Status']
            
            # Uptime
            started_at = container.attrs['State']['StartedAt']
            if started_at:
                from datetime import datetime
                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                uptime = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
            else:
                uptime = 0
            
            # Restart count
            restart_count = container.attrs['RestartCount']
            
            return ContainerHealthMetrics(
                container_name=container_name,
                status=status,
                health_status=health_status,
                cpu_percent=min(cpu_percent, 999.0),  # Cap at reasonable value
                memory_usage_mb=memory_usage / 1024 / 1024,
                memory_limit_mb=memory_limit / 1024 / 1024,
                memory_percent=memory_percent,
                network_rx_bytes=total_rx,
                network_tx_bytes=total_tx,
                uptime_seconds=uptime,
                restart_count=restart_count,
                timestamp=time.time()
            )
            
        except Exception as e:
            return ContainerHealthMetrics(
                container_name=container_name,
                status="error",
                health_status="unhealthy",
                cpu_percent=0,
                memory_usage_mb=0,
                memory_limit_mb=0,
                memory_percent=0,
                network_rx_bytes=0,
                network_tx_bytes=0,
                uptime_seconds=0,
                restart_count=999,
                timestamp=time.time(),
                error_message=str(e)
            )
    
    def get_running_containers(self) -> List[str]:
        """Get list of running container names related to the project"""
        if not self.docker_available:
            return []
            
        try:
            containers = self.docker_client.containers.list(all=False)  # Only running containers
            
            # Filter for project-related containers
            project_containers = []
            for container in containers:
                name = container.name
                # Look for common project container patterns
                if any(keyword in name.lower() for keyword in [
                    'netra', 'dev-', 'test-', 'postgres', 'redis', 'clickhouse',
                    'backend', 'frontend', 'auth', 'analytics'
                ]):
                    project_containers.append(name)
                    
            return project_containers
            
        except Exception as e:
            print(f"Error listing containers: {e}")
            return []
    
    @contextmanager
    def continuous_monitoring(self, containers: List[str], 
                            interval: float = 2.0) -> Generator[List[ContainerHealthMetrics], None, None]:
        """Context manager for continuous container health monitoring"""
        monitoring_data = []
        self.monitoring_active = True
        
        def monitoring_worker():
            while self.monitoring_active:
                timestamp = time.time()
                current_metrics = []
                
                for container_name in containers:
                    metrics = self.get_container_health_metrics(container_name)
                    if metrics:
                        current_metrics.append(metrics)
                        
                monitoring_data.extend(current_metrics)
                
                if self.monitoring_active:  # Check again before sleep
                    time.sleep(interval)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitoring_worker, daemon=True)
        monitor_thread.start()
        
        try:
            yield monitoring_data
        finally:
            self.monitoring_active = False
            monitor_thread.join(timeout=5.0)
    
    def check_service_connectivity(self, service_configs: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """Check connectivity to services"""
        connectivity_results = {}
        
        for service_name, config in service_configs.items():
            try:
                host = config.get('host', 'localhost')
                port = config.get('port', 80)
                protocol = config.get('protocol', 'tcp')
                endpoint = config.get('endpoint', '/')
                
                if protocol == 'http' or protocol == 'https':
                    # HTTP health check
                    url = f"{protocol}://{host}:{port}{endpoint}"
                    response = requests.get(url, timeout=10)
                    connectivity_results[service_name] = response.status_code < 400
                    
                else:
                    # TCP connectivity check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    connectivity_results[service_name] = result == 0
                    sock.close()
                    
            except Exception as e:
                print(f"Connectivity check failed for {service_name}: {e}")
                connectivity_results[service_name] = False
        
        return connectivity_results
    
    def validate_health_metrics(self, metrics_history: List[ContainerHealthMetrics]) -> List[str]:
        """Validate health metrics against thresholds and return violations"""
        violations = []
        
        # Group by container
        by_container = {}
        for metric in metrics_history:
            if metric.container_name not in by_container:
                by_container[metric.container_name] = []
            by_container[metric.container_name].append(metric)
        
        for container_name, container_metrics in by_container.items():
            if not container_metrics:
                continue
                
            latest_metric = max(container_metrics, key=lambda m: m.timestamp)
            
            # Memory usage validation
            if latest_metric.memory_percent > self.alert_thresholds['memory_percent']:
                violations.append(
                    f"{container_name}: Memory usage {latest_metric.memory_percent:.1f}% "
                    f"exceeds threshold {self.alert_thresholds['memory_percent']:.1f}%"
                )
            
            # CPU usage validation  
            if latest_metric.cpu_percent > self.alert_thresholds['cpu_percent']:
                violations.append(
                    f"{container_name}: CPU usage {latest_metric.cpu_percent:.1f}% "
                    f"exceeds threshold {self.alert_thresholds['cpu_percent']:.1f}%"
                )
            
            # Restart count validation
            if latest_metric.restart_count > self.alert_thresholds['restart_count']:
                violations.append(
                    f"{container_name}: Restart count {latest_metric.restart_count} "
                    f"exceeds threshold {self.alert_thresholds['restart_count']}"
                )
            
            # Health status validation
            if latest_metric.health_status in ['unhealthy', 'starting'] and latest_metric.uptime_seconds > 60:
                violations.append(
                    f"{container_name}: Health status '{latest_metric.health_status}' "
                    f"after {latest_metric.uptime_seconds:.0f}s uptime"
                )
            
            # Container status validation
            if latest_metric.status not in ['running']:
                violations.append(
                    f"{container_name}: Container status '{latest_metric.status}' is not running"
                )
        
        return violations


class DockerHealthValidationTests:
    """
    Comprehensive Docker health validation tests
    """
    
    @pytest.fixture(scope="class")
    def health_monitor(self) -> DockerHealthMonitor:
        """Setup Docker health monitor"""
        monitor = DockerHealthMonitor()
        if not monitor.docker_available:
            pytest.skip("Docker not available for health monitoring tests")
        yield monitor
    
    @pytest.fixture(autouse=True)
    def setup_test_isolation(self):
        """Ensure each test starts with clean state"""
        yield
        # Brief pause between tests to let containers stabilize
        time.sleep(1)

    def test_container_health_during_pytest_collection(self, health_monitor: DockerHealthMonitor):
        """
        Test container health monitoring during pytest collection phase
        
        Runs pytest collection on a large test suite while monitoring
        container health to ensure containers remain stable.
        """
        
        # Get running containers
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No project containers running for health monitoring")
        
        # Create temporary test suite for collection
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create 100 test files to stress collection
            for i in range(100):
                test_file = temp_path / f"test_health_collection_{i:03d}.py"
                content = f'''"""Generated test file {i} for health monitoring during collection"""

import pytest
import time

class TestGeneratedHealthCollection{i:03d}:
    """Generated test class for health monitoring"""
    
    def test_simple_{i:03d}(self):
        """Simple test that always passes"""
        assert True
        
    @pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
    def test_parametrized_{i:03d}(self, value):
        """Parametrized test"""
        assert value > 0
        
    def test_with_fixture_{i:03d}(self, request):
        """Test using fixture"""
        assert hasattr(request, 'node')
'''
                test_file.write_text(content, encoding='utf-8')
            
            # Monitor containers during pytest collection
            with health_monitor.continuous_monitoring(containers, interval=1.0) as health_data:
                # Run pytest collection
                start_time = time.time()
                
                try:
                    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", str(temp_path)]
                    process = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120.0  # 2 minute timeout
                    )
                    
                    collection_successful = process.returncode == 0
                    collection_time = time.time() - start_time
                    
                except subprocess.TimeoutExpired:
                    collection_successful = False
                    collection_time = 120.0
                
                # Wait for final health metrics
                time.sleep(2)
        
        # Validate health during collection
        violations = health_monitor.validate_health_metrics(health_data)
        
        # Assertions
        assert collection_successful, "Pytest collection should succeed during health monitoring"
        assert collection_time < 60.0, f"Collection took {collection_time:.2f}s, should be under 60s"
        
        # Health validations
        assert len(health_data) > 0, "Should have collected health metrics during test"
        
        # Check for health violations
        critical_violations = [v for v in violations if 'unhealthy' in v or 'not running' in v]
        assert len(critical_violations) == 0, (
            f"Critical health violations during collection: {critical_violations}"
        )
        
        # Memory violations should be limited
        memory_violations = [v for v in violations if 'Memory usage' in v]
        max_memory_violations = len(containers) * 2  # Allow 2 violations per container
        assert len(memory_violations) <= max_memory_violations, (
            f"Too many memory violations: {len(memory_violations)} (max {max_memory_violations}). "
            f"Violations: {memory_violations}"
        )
        
        # Verify we have sufficient monitoring data
        metrics_per_container = len(health_data) / len(containers) if containers else 0
        min_metrics_per_container = 5  # Should have at least 5 data points per container
        assert metrics_per_container >= min_metrics_per_container, (
            f"Insufficient monitoring data: {metrics_per_container:.1f} metrics per container, "
            f"expected at least {min_metrics_per_container}"
        )

    def test_memory_usage_validation_under_load(self, health_monitor: DockerHealthMonitor):
        """
        Test memory usage validation when containers are under load
        
        Creates memory pressure while monitoring container memory usage
        to verify memory limits are enforced and containers don't crash.
        """
        
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No containers for memory validation test")
        
        def create_memory_pressure():
            """Create memory pressure in the system"""
            pressure_data = []
            try:
                # Allocate memory in chunks
                for i in range(50):  # 50 chunks of 10MB each
                    chunk = bytearray(10 * 1024 * 1024)
                    chunk[0:1024] = b'MEMORY_PRESSURE' * (1024 // 15)
                    pressure_data.append(chunk)
                    time.sleep(0.2)  # Brief pause
                    
                # Hold memory for monitoring period
                time.sleep(10)
                
            finally:
                # Clean up
                del pressure_data
                import gc
                gc.collect()
        
        # Start memory pressure in background
        from threading import Thread
        pressure_thread = Thread(target=create_memory_pressure, daemon=True)
        
        with health_monitor.continuous_monitoring(containers, interval=1.0) as health_data:
            pressure_thread.start()
            
            # Monitor for 15 seconds during memory pressure
            time.sleep(15)
            
            pressure_thread.join(timeout=5)
        
        # Analyze memory usage patterns
        by_container = {}
        for metric in health_data:
            if metric.container_name not in by_container:
                by_container[metric.container_name] = []
            by_container[metric.container_name].append(metric)
        
        for container_name, metrics in by_container.items():
            if not metrics:
                continue
                
            # Check memory usage patterns
            memory_percentages = [m.memory_percent for m in metrics if m.memory_percent > 0]
            if memory_percentages:
                max_memory = max(memory_percentages)
                avg_memory = sum(memory_percentages) / len(memory_percentages)
                
                # Memory should stay within reasonable bounds
                assert max_memory < 95.0, (
                    f"{container_name}: Peak memory usage {max_memory:.1f}% too high, "
                    f"containers should have memory limits enforced"
                )
                
                # Average memory shouldn't be excessive
                assert avg_memory < 70.0, (
                    f"{container_name}: Average memory usage {avg_memory:.1f}% too high during test"
                )
            
            # Check for container stability
            statuses = [m.status for m in metrics]
            running_count = sum(1 for s in statuses if s == 'running')
            stability_ratio = running_count / len(statuses)
            
            assert stability_ratio >= 0.8, (
                f"{container_name}: Container stability {stability_ratio:.2f} too low, "
                f"should remain running during memory pressure"
            )
        
        # Overall validation
        violations = health_monitor.validate_health_metrics(health_data)
        
        # Some memory violations are expected under pressure, but not crashes
        crash_violations = [v for v in violations if 'not running' in v or 'unhealthy' in v]
        assert len(crash_violations) == 0, (
            f"Container crashes detected during memory pressure: {crash_violations}"
        )

    def test_cpu_usage_monitoring_during_intensive_operations(self, health_monitor: DockerHealthMonitor):
        """
        Test CPU usage monitoring when containers perform intensive operations
        
        Triggers CPU-intensive operations while monitoring container
        CPU usage to verify limits and performance.
        """
        
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No containers for CPU monitoring test")
        
        def create_cpu_pressure():
            """Create CPU pressure through intensive computation"""
            import math
            start_time = time.time()
            
            # Run CPU-intensive operations for 10 seconds
            while time.time() - start_time < 10:
                # Mathematical operations to consume CPU
                for i in range(10000):
                    _ = math.sqrt(i) * math.sin(i) * math.cos(i)
                
                # Brief pause to allow monitoring
                time.sleep(0.01)
        
        # Create multiple CPU pressure threads
        from concurrent.futures import ThreadPoolExecutor
        
        with health_monitor.continuous_monitoring(containers, interval=0.5) as health_data:
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Start CPU pressure on multiple threads
                futures = []
                for _ in range(4):
                    future = executor.submit(create_cpu_pressure)
                    futures.append(future)
                
                # Wait for all pressure operations to complete
                for future in as_completed(futures, timeout=20):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"CPU pressure thread failed: {e}")
                
                # Additional monitoring after pressure
                time.sleep(3)
        
        # Analyze CPU usage patterns
        by_container = {}
        for metric in health_data:
            if metric.container_name not in by_container:
                by_container[metric.container_name] = []
            by_container[metric.container_name].append(metric)
        
        for container_name, metrics in by_container.items():
            cpu_values = [m.cpu_percent for m in metrics if m.cpu_percent >= 0]
            if not cpu_values:
                continue
                
            max_cpu = max(cpu_values)
            avg_cpu = sum(cpu_values) / len(cpu_values)
            
            # CPU usage should be monitored and bounded
            assert max_cpu < 200.0, (  # Allow some burst above 100% for multi-core
                f"{container_name}: Peak CPU usage {max_cpu:.1f}% indicates possible runaway process"
            )
            
            # Container should respond to CPU pressure
            if avg_cpu > 0:  # Only test if we got meaningful CPU readings
                assert avg_cpu < 150.0, (
                    f"{container_name}: Average CPU usage {avg_cpu:.1f}% too high, "
                    f"may indicate CPU limit issues"
                )
        
        # Validate overall health
        violations = health_monitor.validate_health_metrics(health_data)
        
        # CPU violations might occur but shouldn't cause crashes
        cpu_violations = [v for v in violations if 'CPU usage' in v]
        status_violations = [v for v in violations if 'not running' in v]
        
        assert len(status_violations) == 0, (
            f"Container status issues during CPU pressure: {status_violations}"
        )
        
        # Should have collected meaningful metrics
        assert len(health_data) >= len(containers) * 10, (
            f"Insufficient monitoring data during CPU test: {len(health_data)} metrics"
        )

    def test_network_isolation_and_connectivity_validation(self, health_monitor: DockerHealthMonitor):
        """
        Test network isolation and connectivity between containers
        
        Validates that containers can communicate with each other as expected
        while maintaining proper network isolation.
        """
        
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No containers for network validation")
        
        # Define expected service endpoints based on common configurations
        service_configs = {
            'dev-postgres': {
                'host': 'localhost',
                'port': 5433,
                'protocol': 'tcp'
            },
            'dev-redis': {
                'host': 'localhost', 
                'port': 6380,
                'protocol': 'tcp'
            },
            'dev-clickhouse': {
                'host': 'localhost',
                'port': 8124,
                'protocol': 'http',
                'endpoint': '/ping'
            },
            'dev-backend': {
                'host': 'localhost',
                'port': 8000,
                'protocol': 'http',
                'endpoint': '/health'
            },
            'dev-auth': {
                'host': 'localhost',
                'port': 8081,
                'protocol': 'http',
                'endpoint': '/health'
            },
            'dev-frontend': {
                'host': 'localhost',
                'port': 3000,
                'protocol': 'http',
                'endpoint': '/api/health'
            }
        }
        
        # Filter service configs to only test running containers
        active_services = {}
        for service_name, config in service_configs.items():
            if any(service_name in container for container in containers):
                active_services[service_name] = config
        
        if not active_services:
            pytest.skip("No recognizable services found for network testing")
        
        with health_monitor.continuous_monitoring(containers, interval=2.0) as health_data:
            # Test connectivity multiple times during monitoring
            connectivity_results = []
            
            for round_num in range(5):  # 5 connectivity test rounds
                round_results = health_monitor.check_service_connectivity(active_services)
                connectivity_results.append(round_results)
                
                # Wait between rounds
                time.sleep(2)
        
        # Analyze connectivity results
        service_availability = {}
        for service_name in active_services.keys():
            successful_checks = sum(1 for result in connectivity_results 
                                  if result.get(service_name, False))
            availability = successful_checks / len(connectivity_results)
            service_availability[service_name] = availability
        
        # Validate network connectivity
        for service_name, availability in service_availability.items():
            min_availability = 0.6  # At least 60% availability
            
            assert availability >= min_availability, (
                f"Service {service_name} availability {availability:.2f} below minimum {min_availability}. "
                f"This indicates network connectivity issues."
            )
        
        # Check that containers maintained network health during connectivity tests
        violations = health_monitor.validate_health_metrics(health_data)
        
        network_related_violations = [v for v in violations if 
                                    'not running' in v or 'unhealthy' in v or 'restart' in v]
        
        assert len(network_related_violations) == 0, (
            f"Container health issues during network testing: {network_related_violations}"
        )
        
        # Verify we tested a reasonable number of services
        assert len(service_availability) >= 1, (
            "Should have tested at least one service for network connectivity"
        )
        
        # At least one service should have good availability
        good_services = [name for name, availability in service_availability.items() 
                        if availability >= 0.8]
        
        assert len(good_services) >= 1, (
            f"At least one service should have good availability ( >= 80%). "
            f"Availabilities: {service_availability}"
        )

    def test_container_restart_and_recovery_validation(self, health_monitor: DockerHealthMonitor):
        """
        Test container restart behavior and recovery validation
        
        Deliberately restarts containers and validates they recover properly
        with maintained health and functionality.
        """
        
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No containers for restart validation")
        
        # Choose a non-critical container for restart testing (avoid databases)
        restart_candidates = [c for c in containers 
                            if not any(db in c.lower() for db in ['postgres', 'redis', 'clickhouse'])]
        
        if not restart_candidates:
            pytest.skip("No suitable containers found for restart testing")
        
        # Pick the first suitable container
        target_container = restart_candidates[0]
        
        print(f"Testing restart and recovery for container: {target_container}")
        
        # Record pre-restart health
        pre_restart_metrics = health_monitor.get_container_health_metrics(target_container)
        assert pre_restart_metrics is not None, f"Could not get metrics for {target_container}"
        assert pre_restart_metrics.status == "running", f"Container {target_container} not running initially"
        
        restart_start_time = time.time()
        
        with health_monitor.continuous_monitoring([target_container], interval=1.0) as health_data:
            try:
                # Restart the container
                container = health_monitor.docker_client.containers.get(target_container)
                container.restart(timeout=30)
                
                print(f"Restarted container {target_container}, waiting for recovery...")
                
                # Monitor recovery for up to 60 seconds
                recovery_timeout = 60
                recovery_start = time.time()
                
                while time.time() - recovery_start < recovery_timeout:
                    current_metrics = health_monitor.get_container_health_metrics(target_container)
                    
                    if (current_metrics and 
                        current_metrics.status == "running" and
                        current_metrics.uptime_seconds > 5):  # Give it a few seconds to stabilize
                        print(f"Container {target_container} recovered after {time.time() - recovery_start:.1f}s")
                        break
                        
                    time.sleep(2)
                else:
                    pytest.fail(f"Container {target_container} did not recover within {recovery_timeout}s")
                
                # Continue monitoring for stability
                time.sleep(10)
                
            except Exception as e:
                pytest.fail(f"Failed to restart container {target_container}: {e}")
        
        restart_duration = time.time() - restart_start_time
        
        # Analyze recovery metrics
        recovery_metrics = [m for m in health_data if m.timestamp > restart_start_time]
        
        if recovery_metrics:
            final_metric = max(recovery_metrics, key=lambda m: m.timestamp)
            
            # Validate recovery
            assert final_metric.status == "running", (
                f"Container {target_container} status '{final_metric.status}' after restart"
            )
            
            # Restart count should have increased
            if pre_restart_metrics.restart_count >= 0:  # Valid restart count
                assert final_metric.restart_count > pre_restart_metrics.restart_count, (
                    f"Restart count should have increased: before={pre_restart_metrics.restart_count}, "
                    f"after={final_metric.restart_count}"
                )
            
            # Memory usage should be reasonable after restart
            assert final_metric.memory_percent < 80, (
                f"Memory usage {final_metric.memory_percent:.1f}% too high after restart"
            )
        
        # Performance validation
        max_restart_time = 90  # Should restart within 90 seconds
        assert restart_duration < max_restart_time, (
            f"Container restart took {restart_duration:.1f}s, should be under {max_restart_time}s"
        )
        
        # Health validation
        violations = health_monitor.validate_health_metrics(recovery_metrics)
        
        # Filter out expected violations during restart
        persistent_violations = [v for v in violations 
                               if 'not running' not in v or 
                               health_data[-1].timestamp - restart_start_time > 30]  # Only after 30s
        
        assert len(persistent_violations) <= 2, (  # Allow minor violations during restart
            f"Too many persistent health violations after restart: {persistent_violations}"
        )

    def test_service_dependency_health_validation(self, health_monitor: DockerHealthMonitor):
        """
        Test health validation of service dependencies
        
        Validates that service dependencies (database, cache, etc.) remain
        healthy and that dependent services handle dependency issues gracefully.
        """
        
        containers = health_monitor.get_running_containers()
        if not containers:
            pytest.skip("No containers for dependency health validation")
        
        # Categorize containers by type
        databases = [c for c in containers if any(db in c.lower() for db in ['postgres', 'mysql'])]
        caches = [c for c in containers if any(cache in c.lower() for cache in ['redis', 'memcached'])]
        analytics = [c for c in containers if any(db in c.lower() for db in ['clickhouse', 'elastic'])]
        applications = [c for c in containers if any(app in c.lower() for app in ['backend', 'frontend', 'auth'])]
        
        all_services = {
            'databases': databases,
            'caches': caches, 
            'analytics': analytics,
            'applications': applications
        }
        
        # Filter to only categories with containers
        active_services = {k: v for k, v in all_services.items() if v}
        
        if not active_services:
            pytest.skip("No categorizable services found for dependency validation")
        
        with health_monitor.continuous_monitoring(containers, interval=1.5) as health_data:
            # Monitor for extended period to catch dependency issues
            monitoring_duration = 30  # 30 seconds
            start_time = time.time()
            
            while time.time() - start_time < monitoring_duration:
                # Check health of each service category
                for category, service_list in active_services.items():
                    for service in service_list:
                        metrics = health_monitor.get_container_health_metrics(service)
                        if metrics and metrics.status != "running":
                            print(f"Warning: {category} service {service} status: {metrics.status}")
                
                time.sleep(3)
        
        # Analyze dependency health patterns
        by_category = {}
        for metric in health_data:
            # Categorize each metric
            category = None
            for cat_name, service_list in active_services.items():
                if metric.container_name in service_list:
                    category = cat_name
                    break
            
            if category:
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(metric)
        
        # Validate each service category
        for category, metrics in by_category.items():
            if not metrics:
                continue
                
            # Check stability within category
            running_metrics = [m for m in metrics if m.status == "running"]
            stability_ratio = len(running_metrics) / len(metrics)
            
            min_stability = 0.85  # 85% uptime minimum
            assert stability_ratio >= min_stability, (
                f"{category} services stability {stability_ratio:.2f} below minimum {min_stability}. "
                f"Dependency services should be highly available."
            )
            
            # Check resource usage patterns for dependencies
            if category in ['databases', 'caches']:
                # Critical services should have consistent resource usage
                memory_values = [m.memory_percent for m in running_metrics if m.memory_percent > 0]
                if memory_values:
                    memory_variance = max(memory_values) - min(memory_values)
                    max_memory_variance = 30  # 30% variance allowed
                    
                    assert memory_variance <= max_memory_variance, (
                        f"{category} memory usage variance {memory_variance:.1f}% too high, "
                        f"indicates instability in critical dependencies"
                    )
        
        # Cross-category dependency analysis
        if 'applications' in by_category and 'databases' in by_category:
            # Application health should correlate with database health
            app_metrics = by_category['applications']
            db_metrics = by_category['databases']
            
            app_healthy_count = sum(1 for m in app_metrics if m.status == "running")
            db_healthy_count = sum(1 for m in db_metrics if m.status == "running")
            
            app_health_ratio = app_healthy_count / len(app_metrics) if app_metrics else 0
            db_health_ratio = db_healthy_count / len(db_metrics) if db_metrics else 0
            
            # If databases are healthy, applications should be too (with some tolerance)
            if db_health_ratio > 0.9:
                min_app_health = 0.7  # Apps should be at least 70% healthy if DBs are 90% healthy
                assert app_health_ratio >= min_app_health, (
                    f"Applications health {app_health_ratio:.2f} too low when databases health "
                    f"is {db_health_ratio:.2f}. Applications should handle database availability well."
                )
        
        # Overall validation
        violations = health_monitor.validate_health_metrics(health_data)
        
        # Critical dependency violations should be minimal
        critical_violations = [v for v in violations if 
                             any(svc in v for svc in databases + caches) and 
                             ('not running' in v or 'unhealthy' in v)]
        
        max_critical_violations = 1  # Allow at most 1 critical dependency issue
        assert len(critical_violations) <= max_critical_violations, (
            f"Too many critical dependency violations: {critical_violations}"
        )
        
        # Should have monitored multiple service categories
        assert len(by_category) >= 2, (
            f"Should monitor multiple service categories, found: {list(by_category.keys())}"
        )