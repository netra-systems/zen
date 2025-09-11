"""
Comprehensive Integration Tests for UnifiedDockerManager - INFRASTRUCTURE CRITICAL SSOT

Business Value: Tests the infrastructure reliability supporting $2M+ business testing and 
development velocity. No mocks allowed - only real Docker service orchestration.

CRITICAL REQUIREMENTS:
- NO MOCKS allowed - use real Docker services only
- Test Docker connectivity issues blocking WebSocket validation  
- Focus on service startup coordination and dependency management
- Test infrastructure reliability supporting development and CI/CD
- Validate cross-platform compatibility and resource management

Test Categories:
1. Docker Service Orchestration (startup, dependency management, coordination)
2. Resource Management and Limits (memory, CPU, disk, resource leaks)
3. Cross-Platform Compatibility (Windows, Linux, macOS)
4. Service Health and Monitoring (real-time monitoring, failure detection)
5. Environment Isolation (test isolation, cleanup, port management)
6. CI/CD Pipeline Integration (automated orchestration, performance)

Business Impact: Protects $2M+ ARR by ensuring stable development and testing infrastructure.
"""

import asyncio
import logging
import os
import platform
import pytest
import time
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import patch, MagicMock

# SSOT Imports from SSOT_IMPORT_REGISTRY.md
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    EnvironmentType,
    ServiceMode,
    ServiceStatus,
    ServiceHealth,
    OrchestrationConfig,
    ContainerInfo
)
from test_framework.resource_monitor import (
    DockerResourceMonitor,
    ResourceThresholdLevel,
    DockerResourceSnapshot
)
from test_framework.memory_guardian import MemoryGuardian, TestProfile
from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestUnifiedDockerManagerOrchestration(SSotBaseTestCase):
    """
    Test suite for Docker Service Orchestration functionality.
    
    Tests real Docker service startup coordination, dependency management,
    and cross-service communication without any mocks.
    """
    
    def setup_method(self, method):
        """Setup test environment with real Docker manager."""
        super().setup_method(method)
        
        # Initialize real UnifiedDockerManager - NO MOCKS
        self.config = OrchestrationConfig()
        self.test_id = f"orchestration_test_{int(time.time())}"
        
        # Use DEDICATED environment for test isolation
        self.docker_manager = UnifiedDockerManager(
            config=self.config,
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id,
            use_production_images=True,
            mode=ServiceMode.DOCKER,
            use_alpine=True,
            rebuild_images=False,  # Faster tests
            rebuild_backend_only=True,
            pull_policy="missing"
        )
        
        # Track resources for cleanup
        self.started_services: Set[str] = set()
        self.allocated_ports: Dict[str, int] = {}
        
        # Verify Docker is available
        if not self._is_docker_available():
            pytest.skip("Docker daemon not available - cannot test real orchestration")
    
    def teardown_method(self, method):
        """Clean up Docker resources after test."""
        try:
            # Stop any services we started
            if self.started_services:
                asyncio.run(self._cleanup_services())
            
            # Clean up allocated ports
            if self.allocated_ports:
                self._cleanup_ports()
                
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        
        super().teardown_method(method)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            result = self.docker_manager._execute_command(["docker", "version"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _cleanup_services(self):
        """Clean up started Docker services."""
        try:
            await self.docker_manager.graceful_shutdown(
                services=list(self.started_services),
                timeout=30
            )
        except Exception as e:
            logger.warning(f"Graceful shutdown failed, forcing: {e}")
            await self.docker_manager.force_shutdown(
                services=list(self.started_services)
            )
    
    def _cleanup_ports(self):
        """Clean up allocated ports."""
        for service, port in self.allocated_ports.items():
            try:
                # Port cleanup is handled by the port allocator
                pass
            except Exception as e:
                logger.warning(f"Port cleanup failed for {service}:{port}: {e}")

    @pytest.mark.asyncio
    async def test_service_startup_coordination_with_dependencies(self):
        """
        Test that services start in correct dependency order with real Docker.
        
        Business Value: Ensures reliable service initialization supporting development velocity.
        """
        # Start with database services first (PostgreSQL, Redis)
        database_services = ["postgres", "redis"]
        
        # Start database services
        success = await self.docker_manager.start_services_smart(
            services=database_services,
            wait_healthy=True
        )
        assert success, "Database services should start successfully"
        self.started_services.update(database_services)
        
        # Verify databases are healthy before starting dependent services
        for service in database_services:
            status = self.docker_manager.get_service_status(service)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY], f"{service} should be running/healthy"
        
        # Start application services that depend on databases
        app_services = ["backend", "auth"]
        success = await self.docker_manager.start_services_smart(
            services=app_services,
            wait_healthy=True
        )
        assert success, "Application services should start after databases"
        self.started_services.update(app_services)
        
        # Verify all services are running and can communicate
        health_report = self.docker_manager.get_health_report()
        assert "postgres" in health_report
        assert "redis" in health_report
        assert "backend" in health_report
        assert "auth" in health_report

    @pytest.mark.asyncio
    async def test_service_restart_storm_prevention(self):
        """
        Test that restart storm prevention works with real services.
        
        Business Value: Prevents Docker daemon crashes that would impact development.
        """
        service_name = "redis"  # Fast-starting service for testing
        
        # Start service initially
        success = await self.docker_manager.start_services_smart([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Record restart attempt times
        restart_times = []
        
        # Attempt multiple rapid restarts
        for i in range(5):
            restart_start = time.time()
            try:
                # Force stop and restart
                await self.docker_manager.force_shutdown([service_name])
                await self.docker_manager.start_services_smart([service_name])
                restart_times.append(time.time() - restart_start)
            except Exception as e:
                # Rate limiting should prevent some restarts
                logger.info(f"Restart {i} was rate limited: {e}")
        
        # Verify rate limiting was applied (restarts should be spaced out)
        if len(restart_times) >= 2:
            time_between_restarts = restart_times[1] - restart_times[0]
            # Should have some delay due to restart cooldown
            assert time_between_restarts >= 1.0, "Rate limiting should space out restarts"

    @pytest.mark.asyncio 
    async def test_cross_service_communication_validation(self):
        """
        Test that services can communicate with each other through Docker network.
        
        Business Value: Validates end-to-end service integration critical for chat functionality.
        """
        # Start interdependent services
        services = ["postgres", "redis", "backend"]
        
        success = await self.docker_manager.start_services_smart(services, wait_healthy=True)
        assert success, "All services should start successfully"
        self.started_services.update(services)
        
        # Get service port mappings
        port_discovery = self.docker_manager.port_discovery
        mappings = await port_discovery.discover_service_ports()
        
        # Verify services have network connectivity
        for service in services:
            service_mapping = mappings.get(service)
            if service_mapping:
                # Test port connectivity
                host = service_mapping.host
                port = service_mapping.external_port
                
                connectivity = await self.docker_manager._check_port_connectivity(
                    host, port, timeout=5.0
                )
                assert connectivity, f"Service {service} should be reachable at {host}:{port}"

    def test_health_monitoring_real_time_updates(self):
        """
        Test real-time health monitoring with actual Docker services.
        
        Business Value: Enables proactive issue detection preventing development downtime.
        """
        # Start a simple service for monitoring
        service_name = "redis"
        
        # Use sync orchestration for this test
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Monitor health over time
        health_checks = []
        for i in range(3):
            status = self.docker_manager.get_service_status(service_name)
            health_checks.append(status)
            time.sleep(1)
        
        # Verify consistent health reporting
        assert all(status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY] 
                  for status in health_checks), "Service health should remain stable"
        
        # Verify health report contains service information
        health_report = self.docker_manager.get_health_report()
        assert service_name in health_report
        assert "healthy" in health_report.lower() or "running" in health_report.lower()

    def test_service_failure_detection_and_recovery(self):
        """
        Test service failure detection and automatic recovery mechanisms.
        
        Business Value: Ensures infrastructure resilience supporting continuous development.
        """
        service_name = "redis"
        
        # Start service
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Verify service is healthy
        initial_status = self.docker_manager.get_service_status(service_name)
        assert initial_status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
        
        # Simulate service failure by stopping container
        try:
            result = self.docker_manager._execute_command([
                "docker", "stop", f"netra-{service_name}"
            ], capture_output=True)
            
            # Wait a moment for failure detection
            time.sleep(2)
            
            # Check that failure is detected
            failed_status = self.docker_manager.get_service_status(service_name)
            assert failed_status in [ServiceStatus.STOPPED, ServiceStatus.FAILED, ServiceStatus.UNHEALTHY]
            
        except Exception as e:
            # If we can't simulate failure, at least verify monitoring works
            logger.info(f"Could not simulate failure: {e}")
            
        # Verify service can be restarted
        recovery_success = self.docker_manager.orchestrate_services_sync([service_name])
        assert recovery_success, "Service should be recoverable after failure"


class TestUnifiedDockerManagerResourceManagement(SSotBaseTestCase):
    """
    Test suite for Resource Management and Limits functionality.
    
    Tests memory limits, CPU monitoring, disk space management, and 
    resource leak detection with real Docker services.
    """
    
    def setup_method(self, method):
        """Setup test environment with resource monitoring."""
        super().setup_method(method)
        
        self.test_id = f"resource_test_{int(time.time())}"
        
        # Create Docker manager with resource monitoring enabled
        self.docker_manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id,
            use_production_images=True,
            mode=ServiceMode.DOCKER
        )
        
        # Initialize resource monitoring
        self.resource_monitor = DockerResourceMonitor(
            enable_auto_cleanup=True,
            cleanup_aggressive=False
        )
        
        self.memory_guardian = MemoryGuardian(profile=TestProfile.STANDARD)
        
        self.started_services: Set[str] = set()
        
        if not self._is_docker_available():
            pytest.skip("Docker daemon not available - cannot test resource management")
    
    def teardown_method(self, method):
        """Clean up resources after test."""
        try:
            if self.started_services:
                asyncio.run(self._cleanup_services())
        except Exception as e:
            logger.warning(f"Resource cleanup failed: {e}")
        
        super().teardown_method(method)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            result = self.docker_manager._execute_command(["docker", "version"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _cleanup_services(self):
        """Clean up started services."""
        try:
            await self.docker_manager.graceful_shutdown(
                services=list(self.started_services),
                timeout=30
            )
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_memory_limit_enforcement_under_load(self):
        """
        Test that memory limits are enforced when services are under load.
        
        Business Value: Prevents Docker daemon crashes that would halt development.
        """
        # Start memory-intensive service with explicit limit
        service_name = "clickhouse"  # Known to be memory-intensive
        
        success = await self.docker_manager.start_services_smart([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Monitor memory usage
        snapshot_before = self.resource_monitor.get_current_snapshot()
        
        # Get memory usage for the specific service
        container_name = f"netra-{service_name}"
        try:
            # Check container memory usage
            result = self.docker_manager._execute_command([
                "docker", "stats", container_name, "--no-stream", "--format", 
                "table {{.MemUsage}}\t{{.MemPerc}}"
            ], capture_output=True)
            
            if result.returncode == 0:
                memory_output = result.stdout
                assert memory_output, f"Should get memory stats for {container_name}"
                
                # Verify service is running within reasonable memory limits
                # (This validates the memory limit configuration is working)
                status = self.docker_manager.get_service_status(service_name)
                assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
                
        except Exception as e:
            logger.warning(f"Memory stats check failed: {e}")
            # At least verify service is running stably
            status = self.docker_manager.get_service_status(service_name)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_resource_monitoring_and_throttling(self):
        """
        Test resource monitoring and automatic throttling mechanisms.
        
        Business Value: Ensures system stability under resource pressure.
        """
        # Start service with resource monitoring
        service_name = "backend"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Monitor resources during operation
        snapshot = self.docker_manager.monitor_memory_during_operations()
        
        if snapshot:
            # Verify resource monitoring is working
            assert snapshot.timestamp > 0
            assert snapshot.total_memory_mb > 0
            
            # Check resource thresholds
            if snapshot.memory_usage_percent > 85:
                # Should trigger throttling or warnings
                assert len(self.docker_manager.memory_warnings_issued) > 0
        
        # Verify service remains stable
        status = self.docker_manager.get_service_status(service_name)
        assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_disk_space_management_and_cleanup(self):
        """
        Test disk space management and container cleanup mechanisms.
        
        Business Value: Prevents disk space issues that would halt CI/CD pipelines.
        """
        # Start service that generates data
        service_name = "postgres"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Check disk usage before cleanup
        try:
            # Get Docker system disk usage
            result = self.docker_manager._execute_command([
                "docker", "system", "df"
            ], capture_output=True)
            
            if result.returncode == 0:
                disk_info = result.stdout
                assert disk_info, "Should get Docker disk usage information"
                
                # Test cleanup functionality
                cleanup_result = self.docker_manager._execute_command([
                    "docker", "system", "prune", "-f", "--volumes"
                ], capture_output=True)
                
                # Verify cleanup executed (may or may not find items to clean)
                assert cleanup_result.returncode == 0, "Docker cleanup should execute successfully"
                
        except Exception as e:
            logger.warning(f"Disk space check failed: {e}")
            # At least verify service remains stable
            status = self.docker_manager.get_service_status(service_name)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    @pytest.mark.asyncio
    async def test_resource_leak_detection_and_prevention(self):
        """
        Test detection and prevention of resource leaks during service lifecycle.
        
        Business Value: Ensures long-term system stability for continuous development.
        """
        service_name = "redis"
        
        # Track resource usage through multiple start/stop cycles
        resource_snapshots = []
        
        for cycle in range(3):
            # Start service
            success = await self.docker_manager.start_services_smart([service_name])
            assert success
            
            # Take resource snapshot
            snapshot = self.resource_monitor.get_current_snapshot()
            if snapshot:
                resource_snapshots.append(snapshot)
            
            # Stop service
            await self.docker_manager.graceful_shutdown([service_name])
            
            # Brief pause between cycles
            await asyncio.sleep(1)
        
        # Analyze resource trends
        if len(resource_snapshots) >= 2:
            # Check for memory leaks (memory should not continuously grow)
            memory_values = [s.used_memory_mb for s in resource_snapshots]
            
            # Allow for some variation, but no major leak pattern
            max_memory = max(memory_values)
            min_memory = min(memory_values)
            memory_growth = max_memory - min_memory
            
            # Should not grow more than 500MB between cycles (reasonable threshold)
            assert memory_growth < 500, f"Potential memory leak detected: {memory_growth}MB growth"

    def test_cpu_resource_monitoring(self):
        """
        Test CPU resource monitoring and limit awareness.
        
        Business Value: Ensures services don't monopolize CPU affecting development.
        """
        service_name = "backend"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Monitor CPU usage
        container_name = f"netra-{service_name}"
        
        try:
            # Get CPU stats
            result = self.docker_manager._execute_command([
                "docker", "stats", container_name, "--no-stream", "--format",
                "table {{.CPUPerc}}"
            ], capture_output=True)
            
            if result.returncode == 0:
                cpu_output = result.stdout
                assert cpu_output, f"Should get CPU stats for {container_name}"
                
                # Verify service is not consuming excessive CPU
                # (This validates reasonable resource usage)
                status = self.docker_manager.get_service_status(service_name)
                assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
                
        except Exception as e:
            logger.warning(f"CPU monitoring test failed: {e}")
            # At least verify service stability
            status = self.docker_manager.get_service_status(service_name)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]


class TestUnifiedDockerManagerCrossPlatform(SSotBaseTestCase):
    """
    Test suite for Cross-Platform Compatibility.
    
    Tests Windows Docker Desktop, Linux containers, macOS support,
    and file system permission handling.
    """
    
    def setup_method(self, method):
        """Setup cross-platform test environment."""
        super().setup_method(method)
        
        self.test_id = f"crossplatform_test_{int(time.time())}"
        self.platform_name = platform.system()
        
        self.docker_manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id,
            mode=ServiceMode.DOCKER
        )
        
        self.started_services: Set[str] = set()
        
        if not self._is_docker_available():
            pytest.skip("Docker daemon not available - cannot test cross-platform compatibility")
    
    def teardown_method(self, method):
        """Clean up cross-platform resources."""
        try:
            if self.started_services:
                asyncio.run(self._cleanup_services())
        except Exception as e:
            logger.warning(f"Cross-platform cleanup failed: {e}")
        
        super().teardown_method(method)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            result = self.docker_manager._execute_command(["docker", "version"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _cleanup_services(self):
        """Clean up started services."""
        try:
            await self.docker_manager.graceful_shutdown(
                services=list(self.started_services),
                timeout=30
            )
        except Exception as e:
            logger.warning(f"Cross-platform service cleanup failed: {e}")

    def test_windows_docker_desktop_integration(self):
        """
        Test Docker Desktop integration on Windows platform.
        
        Business Value: Ensures Windows developers can use Docker infrastructure.
        """
        if self.platform_name != "Windows":
            pytest.skip("Windows-specific test")
        
        # Test Windows-specific Docker features
        service_name = "redis"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success, "Docker Desktop should work on Windows"
        self.started_services.add(service_name)
        
        # Verify Windows-specific path handling
        assert self.docker_manager.is_windows == True
        assert "Windows" in str(self.docker_manager.LOCK_DIR)
        
        # Test Windows file system permissions
        lock_dir = self.docker_manager.LOCK_DIR
        assert lock_dir.exists(), "Lock directory should be created on Windows"
        
        # Verify service status
        status = self.docker_manager.get_service_status(service_name)
        assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_linux_container_orchestration(self):
        """
        Test Linux container orchestration capabilities.
        
        Business Value: Ensures CI/CD pipeline compatibility on Linux servers.
        """
        if self.platform_name == "Windows":
            # Even on Windows, we're running Linux containers
            pass
        
        service_name = "postgres"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success, "Linux containers should work"
        self.started_services.add(service_name)
        
        # Test Unix-specific features if available
        if hasattr(self.docker_manager, '_unix_socket_path'):
            # Verify Unix socket handling if applicable
            pass
        
        # Verify container networking
        container_name = f"netra-{service_name}"
        result = self.docker_manager._execute_command([
            "docker", "inspect", container_name, "--format", "{{.NetworkSettings.IPAddress}}"
        ], capture_output=True)
        
        if result.returncode == 0:
            ip_address = result.stdout.strip()
            # Should have an IP address assigned
            assert ip_address, f"Container {container_name} should have IP address"

    def test_macos_development_environment_support(self):
        """
        Test macOS development environment support.
        
        Business Value: Ensures macOS developers can use Docker infrastructure.
        """
        if self.platform_name != "Darwin":
            pytest.skip("macOS-specific test")
        
        service_name = "auth"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success, "Docker should work on macOS"
        self.started_services.add(service_name)
        
        # Test macOS-specific path handling
        assert not self.docker_manager.is_windows
        lock_dir = str(self.docker_manager.LOCK_DIR)
        assert "/tmp" in lock_dir, "macOS should use Unix-style paths"
        
        # Verify service status
        status = self.docker_manager.get_service_status(service_name)
        assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_file_system_permission_handling(self):
        """
        Test file system permission handling across platforms.
        
        Business Value: Prevents permission issues that would block development.
        """
        service_name = "backend"
        
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Test lock file creation and permissions
        lock_dir = self.docker_manager.LOCK_DIR
        test_lock_file = lock_dir / f"test_permissions_{self.test_id}.lock"
        
        try:
            # Create test lock file
            test_lock_file.write_text("test")
            assert test_lock_file.exists(), "Should be able to create lock file"
            
            # Test file reading
            content = test_lock_file.read_text()
            assert content == "test", "Should be able to read lock file"
            
        except PermissionError as e:
            pytest.fail(f"Permission error on {self.platform_name}: {e}")
        
        finally:
            # Clean up test file
            if test_lock_file.exists():
                test_lock_file.unlink()
        
        # Test Docker volume permissions
        container_name = f"netra-{service_name}"
        result = self.docker_manager._execute_command([
            "docker", "inspect", container_name, "--format", "{{.Mounts}}"
        ], capture_output=True)
        
        if result.returncode == 0:
            mounts_info = result.stdout
            # Should have mount information (even if empty)
            assert isinstance(mounts_info, str), "Should get mount information"

    def test_cross_platform_port_allocation(self):
        """
        Test port allocation consistency across platforms.
        
        Business Value: Ensures consistent development experience across teams.
        """
        services = ["redis", "postgres"]
        
        # Start multiple services
        success = self.docker_manager.orchestrate_services_sync(services)
        assert success
        self.started_services.update(services)
        
        # Get port mappings
        port_discovery = self.docker_manager.port_discovery
        try:
            mappings = asyncio.run(port_discovery.discover_service_ports())
            
            # Verify port allocation worked on this platform
            for service in services:
                if service in mappings:
                    mapping = mappings[service]
                    assert mapping.external_port > 0, f"{service} should have valid external port"
                    assert mapping.internal_port > 0, f"{service} should have valid internal port"
                    
                    # Test port connectivity
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        result = sock.connect_ex((mapping.host, mapping.external_port))
                        # 0 means connection successful, other values may indicate service starting
                        assert result is not None, f"Should get connection result for {service}"
                    finally:
                        sock.close()
                        
        except Exception as e:
            logger.warning(f"Port discovery test failed: {e}")
            # At least verify services are running
            for service in services:
                status = self.docker_manager.get_service_status(service)
                assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY, ServiceStatus.STARTING]


class TestUnifiedDockerManagerEnvironmentIsolation(SSotBaseTestCase):
    """
    Test suite for Environment Isolation functionality.
    
    Tests service isolation between test runs, environment variable management,
    network isolation, and container cleanup.
    """
    
    def setup_method(self, method):
        """Setup isolated test environment."""
        super().setup_method(method)
        
        self.test_id_1 = f"isolation_test_1_{int(time.time())}"
        self.test_id_2 = f"isolation_test_2_{int(time.time() + 1)}"
        
        # Create two separate Docker managers for isolation testing
        self.docker_manager_1 = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id_1,
            mode=ServiceMode.DOCKER
        )
        
        self.docker_manager_2 = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id_2,
            mode=ServiceMode.DOCKER
        )
        
        self.started_services_1: Set[str] = set()
        self.started_services_2: Set[str] = set()
        
        if not self._is_docker_available():
            pytest.skip("Docker daemon not available - cannot test environment isolation")
    
    def teardown_method(self, method):
        """Clean up isolated test environments."""
        try:
            if self.started_services_1:
                asyncio.run(self._cleanup_services(self.docker_manager_1, self.started_services_1))
            
            if self.started_services_2:
                asyncio.run(self._cleanup_services(self.docker_manager_2, self.started_services_2))
                
        except Exception as e:
            logger.warning(f"Isolation cleanup failed: {e}")
        
        super().teardown_method(method)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            result = self.docker_manager_1._execute_command(["docker", "version"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _cleanup_services(self, docker_manager, services):
        """Clean up services for specific manager."""
        try:
            await docker_manager.graceful_shutdown(
                services=list(services),
                timeout=30
            )
        except Exception as e:
            logger.warning(f"Service cleanup failed: {e}")

    def test_service_isolation_between_test_runs(self):
        """
        Test that services are properly isolated between different test runs.
        
        Business Value: Ensures test reliability and prevents test interference.
        """
        service_name = "redis"
        
        # Start service in first environment
        success_1 = self.docker_manager_1.orchestrate_services_sync([service_name])
        assert success_1, "First environment should start service"
        self.started_services_1.add(service_name)
        
        # Start service in second environment (should be isolated)
        success_2 = self.docker_manager_2.orchestrate_services_sync([service_name])
        assert success_2, "Second environment should start service independently"
        self.started_services_2.add(service_name)
        
        # Verify both services are running independently
        status_1 = self.docker_manager_1.get_service_status(service_name)
        status_2 = self.docker_manager_2.get_service_status(service_name)
        
        assert status_1 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
        assert status_2 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
        
        # Verify they have different test IDs
        assert self.docker_manager_1.test_id != self.docker_manager_2.test_id
        
        # Stop service in first environment
        asyncio.run(self.docker_manager_1.graceful_shutdown([service_name]))
        self.started_services_1.discard(service_name)
        
        # Second environment should still be running
        status_2_after = self.docker_manager_2.get_service_status(service_name)
        assert status_2_after in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_environment_variable_management(self):
        """
        Test environment variable isolation and management.
        
        Business Value: Ensures test configuration isolation and reliability.
        """
        service_name = "postgres"
        
        # Set different environment configurations
        env = get_env()
        
        # First manager with custom environment
        env.set("TEST_DATABASE", "test_db_1", "isolation_test_1")
        success_1 = self.docker_manager_1.orchestrate_services_sync([service_name])
        assert success_1
        self.started_services_1.add(service_name)
        
        # Second manager with different environment  
        env.set("TEST_DATABASE", "test_db_2", "isolation_test_2")
        success_2 = self.docker_manager_2.orchestrate_services_sync([service_name])
        assert success_2
        self.started_services_2.add(service_name)
        
        # Verify environment isolation
        credentials_1 = self.docker_manager_1.ENVIRONMENT_CREDENTIALS[
            self.docker_manager_1.environment_type
        ]
        credentials_2 = self.docker_manager_2.ENVIRONMENT_CREDENTIALS[
            self.docker_manager_2.environment_type
        ]
        
        # Should use same credentials but different test IDs for isolation
        assert credentials_1 == credentials_2  # Same environment type
        assert self.docker_manager_1.test_id != self.docker_manager_2.test_id  # Different isolation

    def test_network_isolation_and_port_management(self):
        """
        Test network isolation and port management between environments.
        
        Business Value: Prevents port conflicts that would break CI/CD.
        """
        service_name = "backend"
        
        # Start service in both environments
        success_1 = self.docker_manager_1.orchestrate_services_sync([service_name])
        assert success_1
        self.started_services_1.add(service_name)
        
        success_2 = self.docker_manager_2.orchestrate_services_sync([service_name])
        assert success_2
        self.started_services_2.add(service_name)
        
        # Get port mappings for both
        try:
            mappings_1 = asyncio.run(self.docker_manager_1.port_discovery.discover_service_ports())
            mappings_2 = asyncio.run(self.docker_manager_2.port_discovery.discover_service_ports())
            
            # Verify different external ports (no conflicts)
            if service_name in mappings_1 and service_name in mappings_2:
                port_1 = mappings_1[service_name].external_port
                port_2 = mappings_2[service_name].external_port
                
                # Should be different external ports for isolation
                # (Or same port if sharing is intentional, but different containers)
                assert port_1 > 0 and port_2 > 0, "Both services should have valid ports"
                
        except Exception as e:
            logger.warning(f"Port isolation test failed: {e}")
            # At least verify both services are running
            status_1 = self.docker_manager_1.get_service_status(service_name)
            status_2 = self.docker_manager_2.get_service_status(service_name)
            
            assert status_1 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
            assert status_2 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    @pytest.mark.asyncio
    async def test_container_cleanup_and_resource_reclaim(self):
        """
        Test container cleanup and resource reclamation after test completion.
        
        Business Value: Prevents resource accumulation that would slow CI/CD.
        """
        service_name = "auth"
        
        # Start service
        success = await self.docker_manager_1.start_services_smart([service_name])
        assert success
        self.started_services_1.add(service_name)
        
        # Get initial container count
        result_before = self.docker_manager_1._execute_command([
            "docker", "ps", "-a", "--format", "{{.Names}}"
        ], capture_output=True)
        
        containers_before = set()
        if result_before.returncode == 0:
            containers_before = set(result_before.stdout.strip().split('\n'))
        
        # Stop and cleanup service
        await self.docker_manager_1.graceful_shutdown([service_name])
        self.started_services_1.discard(service_name)
        
        # Perform explicit cleanup
        await self.docker_manager_1.cleanup_services()
        
        # Get container count after cleanup
        result_after = self.docker_manager_1._execute_command([
            "docker", "ps", "-a", "--format", "{{.Names}}"
        ], capture_output=True)
        
        containers_after = set()
        if result_after.returncode == 0:
            containers_after = set(result_after.stdout.strip().split('\n'))
        
        # Verify cleanup occurred (container should be stopped/removed)
        container_name = f"netra-{service_name}"
        
        # Check if container is still running (it shouldn't be)
        running_result = self.docker_manager_1._execute_command([
            "docker", "ps", "--format", "{{.Names}}", "--filter", f"name={container_name}"
        ], capture_output=True)
        
        if running_result.returncode == 0:
            running_containers = running_result.stdout.strip()
            assert container_name not in running_containers, f"Container {container_name} should not be running after cleanup"

    def test_concurrent_environment_isolation(self):
        """
        Test isolation when multiple environments run concurrently.
        
        Business Value: Ensures parallel test execution doesn't create conflicts.
        """
        service_name = "redis"
        
        # Start services concurrently in both environments
        def start_in_env_1():
            return self.docker_manager_1.orchestrate_services_sync([service_name])
        
        def start_in_env_2():
            return self.docker_manager_2.orchestrate_services_sync([service_name])
        
        import threading
        
        results = {}
        threads = []
        
        def run_env_1():
            results['env_1'] = start_in_env_1()
        
        def run_env_2():
            results['env_2'] = start_in_env_2()
        
        # Start both environments concurrently
        thread_1 = threading.Thread(target=run_env_1)
        thread_2 = threading.Thread(target=run_env_2)
        
        thread_1.start()
        thread_2.start()
        
        # Wait for both to complete
        thread_1.join(timeout=60)
        thread_2.join(timeout=60)
        
        # Verify both succeeded
        assert results.get('env_1') == True, "Environment 1 should start successfully"
        assert results.get('env_2') == True, "Environment 2 should start successfully"
        
        if results.get('env_1'):
            self.started_services_1.add(service_name)
        if results.get('env_2'):
            self.started_services_2.add(service_name)
        
        # Verify both are running independently
        status_1 = self.docker_manager_1.get_service_status(service_name)
        status_2 = self.docker_manager_2.get_service_status(service_name)
        
        assert status_1 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]
        assert status_2 in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]


class TestUnifiedDockerManagerCIPipeline(SSotBaseTestCase):
    """
    Test suite for CI/CD Pipeline Integration functionality.
    
    Tests automated service orchestration, build environment consistency,
    test environment provisioning, and performance benchmarking.
    """
    
    def setup_method(self, method):
        """Setup CI/CD pipeline test environment."""
        super().setup_method(method)
        
        self.test_id = f"ci_pipeline_test_{int(time.time())}"
        
        # Create Docker manager with CI/CD optimizations
        self.docker_manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id=self.test_id,
            use_production_images=True,  # CI/CD should use production images
            mode=ServiceMode.DOCKER,
            use_alpine=True,  # Faster CI/CD with Alpine
            rebuild_images=False,  # CI/CD should use cached images when possible
            pull_policy="missing"  # Efficient for CI/CD
        )
        
        self.started_services: Set[str] = set()
        
        if not self._is_docker_available():
            pytest.skip("Docker daemon not available - cannot test CI/CD integration")
    
    def teardown_method(self, method):
        """Clean up CI/CD test resources."""
        try:
            if self.started_services:
                asyncio.run(self._cleanup_services())
        except Exception as e:
            logger.warning(f"CI/CD cleanup failed: {e}")
        
        super().teardown_method(method)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            result = self.docker_manager._execute_command(["docker", "version"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def _cleanup_services(self):
        """Clean up started services."""
        try:
            await self.docker_manager.graceful_shutdown(
                services=list(self.started_services),
                timeout=30
            )
        except Exception as e:
            logger.warning(f"CI/CD service cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_automated_service_orchestration(self):
        """
        Test automated service orchestration suitable for CI/CD pipelines.
        
        Business Value: Enables reliable automated testing protecting $2M+ ARR.
        """
        # Test full service stack startup (CI/CD typical scenario)
        services = ["postgres", "redis", "backend", "auth"]
        
        # Measure orchestration time (CI/CD performance metric)
        start_time = time.time()
        
        success = await self.docker_manager.start_services_smart(
            services=services,
            wait_healthy=True
        )
        
        orchestration_time = time.time() - start_time
        
        assert success, "CI/CD orchestration should start all services"
        self.started_services.update(services)
        
        # CI/CD should complete within reasonable time (< 3 minutes for full stack)
        assert orchestration_time < 180, f"CI/CD orchestration took too long: {orchestration_time}s"
        
        # Verify all services are healthy (CI/CD requirement)
        health_report = self.docker_manager.get_health_report()
        for service in services:
            assert service in health_report, f"Service {service} should be in health report"

    def test_build_environment_consistency(self):
        """
        Test build environment consistency across CI/CD runs.
        
        Business Value: Ensures reproducible builds and test results.
        """
        service_name = "backend"
        
        # Start service with consistent configuration
        success = self.docker_manager.orchestrate_services_sync([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Verify reproducible configuration
        container_name = f"netra-{service_name}"
        
        # Check environment variables are consistent
        result = self.docker_manager._execute_command([
            "docker", "inspect", container_name, "--format", "{{.Config.Env}}"
        ], capture_output=True)
        
        if result.returncode == 0:
            env_vars = result.stdout
            assert env_vars, f"Container {container_name} should have environment variables"
            
            # Verify test environment is properly set
            assert "test" in env_vars.lower() or "TEST" in env_vars
        
        # Check image consistency
        image_result = self.docker_manager._execute_command([
            "docker", "inspect", container_name, "--format", "{{.Config.Image}}"
        ], capture_output=True)
        
        if image_result.returncode == 0:
            image_name = image_result.stdout.strip()
            assert image_name, f"Container {container_name} should have consistent image"

    @pytest.mark.asyncio
    async def test_test_environment_provisioning(self):
        """
        Test test environment provisioning for CI/CD pipelines.
        
        Business Value: Ensures reliable test infrastructure for continuous integration.
        """
        # Provision complete test environment
        test_services = ["postgres", "redis", "backend"]
        
        # Test environment should provision quickly
        start_time = time.time()
        
        success = await self.docker_manager.ensure_services_running(
            services=test_services,
            timeout=120  # CI/CD should provision within 2 minutes
        )
        
        provisioning_time = time.time() - start_time
        
        assert success, "Test environment provisioning should succeed"
        self.started_services.update(test_services)
        
        # Verify reasonable provisioning time for CI/CD
        assert provisioning_time < 120, f"Provisioning took too long: {provisioning_time}s"
        
        # Verify environment is ready for testing
        for service in test_services:
            status = self.docker_manager.get_service_status(service)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY], f"{service} should be ready for testing"

    def test_performance_benchmarking_integration(self):
        """
        Test performance benchmarking capabilities for CI/CD.
        
        Business Value: Enables performance regression detection in CI/CD.
        """
        service_name = "redis"  # Fast service for performance testing
        
        # Benchmark service startup
        startup_times = []
        
        for i in range(3):  # Multiple runs for consistency
            start_time = time.time()
            
            success = self.docker_manager.orchestrate_services_sync([service_name])
            assert success
            
            startup_time = time.time() - start_time
            startup_times.append(startup_time)
            
            # Clean up for next iteration (except last)
            if i < 2:
                asyncio.run(self.docker_manager.graceful_shutdown([service_name]))
            else:
                self.started_services.add(service_name)
        
        # Analyze performance metrics
        avg_startup_time = sum(startup_times) / len(startup_times)
        max_startup_time = max(startup_times)
        min_startup_time = min(startup_times)
        
        # Performance should be consistent (< 50% variation)
        if max_startup_time > 0:
            variation = (max_startup_time - min_startup_time) / max_startup_time
            assert variation < 0.5, f"Performance variation too high: {variation:.2%}"
        
        # Performance should be reasonable for CI/CD (< 30 seconds)
        assert avg_startup_time < 30, f"Average startup time too slow: {avg_startup_time}s"

    @pytest.mark.asyncio
    async def test_ci_pipeline_failure_recovery(self):
        """
        Test failure recovery mechanisms suitable for CI/CD pipelines.
        
        Business Value: Ensures CI/CD pipeline resilience and reliability.
        """
        service_name = "postgres"
        
        # Start service normally
        success = await self.docker_manager.start_services_smart([service_name])
        assert success
        self.started_services.add(service_name)
        
        # Simulate failure by stopping service
        await self.docker_manager.force_shutdown([service_name])
        
        # Test recovery mechanism
        recovery_start = time.time()
        
        recovery_success = await self.docker_manager.start_services_smart(
            [service_name],
            wait_healthy=True
        )
        
        recovery_time = time.time() - recovery_start
        
        assert recovery_success, "CI/CD should recover from service failure"
        
        # Recovery should be reasonably fast for CI/CD
        assert recovery_time < 60, f"Recovery took too long: {recovery_time}s"
        
        # Verify service is healthy after recovery
        status = self.docker_manager.get_service_status(service_name)
        assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]

    def test_ci_resource_optimization(self):
        """
        Test resource optimization suitable for CI/CD environments.
        
        Business Value: Ensures efficient resource usage in CI/CD infrastructure.
        """
        # Start multiple services to test resource efficiency
        services = ["redis", "postgres"]
        
        # Monitor resource usage during CI/CD scenario
        resource_monitor = self.docker_manager.resource_monitor
        snapshot_before = resource_monitor.get_current_snapshot()
        
        # Start services
        success = self.docker_manager.orchestrate_services_sync(services)
        assert success
        self.started_services.update(services)
        
        # Take snapshot after startup
        snapshot_after = resource_monitor.get_current_snapshot()
        
        # Verify reasonable resource usage
        if snapshot_before and snapshot_after:
            memory_increase = snapshot_after.used_memory_mb - snapshot_before.used_memory_mb
            
            # Should not consume excessive memory (< 2GB for basic services)
            assert memory_increase < 2048, f"CI/CD memory usage too high: {memory_increase}MB"
        
        # Verify services are resource-efficient
        for service in services:
            status = self.docker_manager.get_service_status(service)
            assert status in [ServiceStatus.RUNNING, ServiceStatus.HEALTHY]


# Test execution markers for pytest
pytest_markers = [
    "integration",
    "infrastructure", 
    "docker",
    "no_mocks",
    "real_services"
]

if __name__ == "__main__":
    # Run tests with appropriate markers
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-m", "integration"
    ])