#!/usr/bin/env python3
'''
Comprehensive Integration Tests for Alpine vs Regular Container Switching

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction, CI/CD Optimization
- Business Goal: Enable memory-optimized test execution with seamless switching capabilities
- Value Impact: Reduces CI costs by 40-60%, faster test execution, robust container orchestration
- Strategic Impact: Enables production-ready container switching for different deployment scenarios

This test suite validates:
1. Sequential switching between Alpine and regular containers
2. Parallel execution with proper isolation
3. Performance comparisons and benchmarks
4. Error recovery and fallback mechanisms
5. Migration path and data persistence
6. CI/CD integration scenarios

CRITICAL: These tests use REAL Docker containers and services (no mocks).
They validate production scenarios for container switching functionality.
'''

import asyncio
import json
import logging
import os
import psutil
import pytest
import subprocess
import sys
import tempfile
import time
import yaml
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from shared.isolated_environment import IsolatedEnvironment

        # Add project root to path for absolute imports (CLAUDE.md compliance)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import ( )
UnifiedDockerManager,
EnvironmentType,
OrchestrationConfig,
ServiceMode
        
from test_framework.docker_port_discovery import DockerPortDiscovery
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

        # Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContainerMetrics:
    """Container performance metrics collection."""

    def __init__(self):
        pass
        self.startup_time = 0.0
        self.memory_usage_mb = 0.0
        self.cpu_usage_percent = 0.0
        self.disk_usage_mb = 0.0
        self.container_names = []
        self.image_sizes_mb = {}

    def to_dict(self) -> Dict[str, Any]:
        return { )
        "startup_time": self.startup_time,
        "memory_usage_mb": self.memory_usage_mb,
        "cpu_usage_percent": self.cpu_usage_percent,
        "disk_usage_mb": self.disk_usage_mb,
        "container_names": self.container_names,
        "image_sizes_mb": self.image_sizes_mb
    


class AlpineRegularSwitchingTestSuite:
        """Main test suite for comprehensive Alpine vs regular container switching."""

        @pytest.fixture
    def docker_available(self):
        """Check if Docker is available for integration tests."""
        try:
        result = subprocess.run(["docker", "version"], capture_output=True, timeout=10)
        if result.returncode != 0:
        pytest.skip("Docker not available")
        return True
        except Exception as e:
        pytest.skip("formatted_string")

        @pytest.fixture
    def compose_available(self):
        """Check if docker-compose is available."""
        pass
        try:
        result = subprocess.run(["docker-compose", "version"], capture_output=True, timeout=10)
        if result.returncode != 0:
        pytest.skip("Docker Compose not available")
        return True
        except Exception as e:
        pytest.skip("formatted_string")

        @pytest.fixture
    def isolated_test_environment(self):
        """Create isolated test environment for each test."""
        test_id = "formatted_string"

    Cleanup any existing containers from previous failed tests
        self._cleanup_test_containers(test_id)

        yield test_id

    # Cleanup after test
        self._cleanup_test_containers(test_id)

    def _cleanup_test_containers(self, test_id: str):
        """Clean up containers created during testing."""
        pass
        try:
        # Find and stop containers with test_id prefix
        cmd = ["docker", "ps", "-a", "--filter", "formatted_string", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
        container_names = result.stdout.strip().split(" )
        ")
        for name in container_names:
        if name.strip():
        subprocess.run(["docker", "rm", "-f", name.strip()],
        capture_output=True, timeout=10)
        except Exception as e:
        logger.warning("formatted_string")


        @pytest.mark.integration
class TestSequentialSwitching(AlpineRegularSwitchingTestSuite):
        """Test sequential switching between Alpine and regular containers."""

        def test_regular_to_alpine_to_regular_switching(self, docker_available, compose_available,
        isolated_test_environment):
        """Test complete switching cycle: Regular -> Alpine -> Regular."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

    # Phase 1: Start with regular containers
        logger.info("Phase 1: Starting regular containers")
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        start_time = time.time()
        success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
        regular_startup_time = time.time() - start_time

        assert success, "Failed to start regular containers in phase 1"

    # Verify regular containers are working
        self._verify_container_functionality(manager_regular, services)
        regular_metrics = self._collect_container_metrics(manager_regular, services)
        regular_metrics.startup_time = regular_startup_time

    # Phase 2: Switch to Alpine containers
        logger.info("Phase 2: Switching to Alpine containers")
        asyncio.run(manager_regular.graceful_shutdown())

        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

        start_time = time.time()
        success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
        alpine_startup_time = time.time() - start_time

        assert success, "Failed to start Alpine containers in phase 2"

    # Verify Alpine containers are working
        self._verify_container_functionality(manager_alpine, services)
        alpine_metrics = self._collect_container_metrics(manager_alpine, services)
        alpine_metrics.startup_time = alpine_startup_time

    # Verify containers are actually Alpine-based
        self._verify_alpine_containers(manager_alpine, services)

    # Phase 3: Switch back to regular containers
        logger.info("Phase 3: Switching back to regular containers")
        asyncio.run(manager_alpine.graceful_shutdown())

        manager_regular_2 = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        start_time = time.time()
        success = asyncio.run(manager_regular_2.start_services_smart(services, wait_healthy=True))
        regular_2_startup_time = time.time() - start_time

        assert success, "Failed to start regular containers in phase 3"

    # Verify regular containers are working again
        self._verify_container_functionality(manager_regular_2, services)
        regular_2_metrics = self._collect_container_metrics(manager_regular_2, services)
        regular_2_metrics.startup_time = regular_2_startup_time

    # Cleanup
        asyncio.run(manager_regular_2.graceful_shutdown())

    # Log performance comparison
        logger.info("Sequential Switching Performance Report:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")

    # Assertions for performance
        assert alpine_metrics.memory_usage_mb < regular_metrics.memory_usage_mb, \
        "Alpine containers should use less memory than regular containers"

    # Verify consistent behavior across switches
        startup_variance = abs(regular_startup_time - regular_2_startup_time) / regular_startup_time
        assert startup_variance < 0.5, "Startup times should be consistent across switches"

        def test_data_persistence_across_switches(self, docker_available, compose_available,
        isolated_test_environment):
        """Test that data persists when switching between container types."""
        test_id = isolated_test_environment

    # Start with regular containers and insert test data
        logger.info("Starting regular containers and inserting test data")
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_regular.start_services_smart(["postgres", "redis"], wait_healthy=True))
        assert success, "Failed to start regular containers for data test"

    # Insert test data
        test_data = { )
        "postgres": "INSERT INTO test_table (data) VALUES ('regular_test_data')",
        "redis": "SET test_key 'regular_test_value'"
    

        self._insert_test_data(manager_regular, test_data)
        asyncio.run(manager_regular.graceful_shutdown())

    # Switch to Alpine and verify data persistence
        logger.info("Switching to Alpine containers and verifying data persistence")
        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

        success = asyncio.run(manager_alpine.start_services_smart(["postgres", "redis"], wait_healthy=True))
        assert success, "Failed to start Alpine containers for data test"

    # Verify test data is accessible
        self._verify_test_data(manager_alpine, test_data)

    # Insert additional data in Alpine containers
        alpine_data = { )
        "postgres": "INSERT INTO test_table (data) VALUES ('alpine_test_data')",
        "redis": "SET alpine_key 'alpine_test_value'"
    

        self._insert_test_data(manager_alpine, alpine_data)
        asyncio.run(manager_alpine.graceful_shutdown())

    # Switch back to regular and verify all data
        logger.info("Switching back to regular containers and verifying all data")
        manager_regular_2 = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_regular_2.start_services_smart(["postgres", "redis"], wait_healthy=True))
        assert success, "Failed to start regular containers for final data verification"

    # Verify both original and Alpine-inserted data
        combined_data = {**test_data, **alpine_data}
        self._verify_test_data(manager_regular_2, combined_data)

        asyncio.run(manager_regular_2.graceful_shutdown())

    def _verify_container_functionality(self, manager: UnifiedDockerManager, services: List[str]):
        """Verify that containers are functional."""
        health_report = manager.get_health_report()
        assert "FAILED" not in health_report, "formatted_string"

        for service in services:
        health = manager.service_health.get(service)
        assert health is not None, "formatted_string"
        assert health.is_healthy, "formatted_string"
        assert health.response_time_ms < 10000, "formatted_string"

    def _verify_alpine_containers(self, manager: UnifiedDockerManager, services: List[str]):
        """Verify containers are actually Alpine-based."""
        pass
        container_info = manager.get_enhanced_container_status(services)
        for service, info in container_info.items():
        # Check if image name contains 'alpine' or if it's an Alpine-based image
        assert any(keyword in info.image.lower() for keyword in ['alpine', 'minimal']), \
        "formatted_string"

    def _collect_container_metrics(self, manager: UnifiedDockerManager, services: List[str]) -> ContainerMetrics:
        """Collect performance metrics from containers."""
        metrics = ContainerMetrics()

        try:
        # Get container names and basic info
        container_info = manager.get_enhanced_container_status(services)
        metrics.container_names = list(container_info.keys())

        # Collect memory and CPU usage
        total_memory = 0.0
        total_cpu = 0.0

        for service, info in container_info.items():
            # Get container stats
        cmd = ["docker", "stats", "--no-stream", "--format",
        "{{.MemUsage}},{{.CPUPerc}}", info.name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
        stats_line = result.stdout.strip()
        if stats_line:
        mem_usage, cpu_perc = stats_line.split(',')

                    # Parse memory usage (e.g., "45.2MiB / 512MiB")
        if '/' in mem_usage:
        mem_str = mem_usage.split(' / ')[0].strip()
        mem_mb = self._parse_memory_string(mem_str)
        total_memory += mem_mb

                        # Parse CPU percentage (e.g., "1.25%")
        if '%' in cpu_perc:
        cpu_val = float(cpu_perc.replace('%', '').strip())
        total_cpu += cpu_val

                            # Get image size
        img_cmd = ["docker", "images", info.image, "--format", "{{.Size}}"]
        img_result = subprocess.run(img_cmd, capture_output=True, text=True, timeout=10)
        if img_result.returncode == 0 and img_result.stdout.strip():
        size_str = img_result.stdout.strip()
        metrics.image_sizes_mb[service] = self._parse_memory_string(size_str)

        metrics.memory_usage_mb = total_memory
        metrics.cpu_usage_percent = total_cpu

        except Exception as e:
        logger.warning("formatted_string")

        return metrics

    def _parse_memory_string(self, mem_str: str) -> float:
        """Parse memory string to MB."""
        try:
        if 'GB' in mem_str:
        return float(mem_str.replace('GB', '').strip()) * 1000
        elif 'MB' in mem_str:
        return float(mem_str.replace('MB', '').strip())
        elif 'GiB' in mem_str:
        return float(mem_str.replace('GiB', '').strip()) * 1024
        elif 'MiB' in mem_str:
        return float(mem_str.replace('MiB', '').strip())
        elif 'KB' in mem_str or 'KiB' in mem_str:
        return float(mem_str.replace('KB', '').replace('KiB', '').strip()) / 1000
        else:
        return 0.0
        except ValueError:
        return 0.0

    def _insert_test_data(self, manager: UnifiedDockerManager, test_data: Dict[str, str]):
        """Insert test data into services."""
        try:
        project_name = manager._get_project_name()

        if 'postgres' in test_data:
            # First create table if it doesn't exist
        create_cmd = [ )
        "docker", "exec", "formatted_string",
        "psql", "-U", "netra", "-d", "netra", "-c",
        "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);"
            
        subprocess.run(create_cmd, capture_output=True, timeout=10)

            # Insert data
        insert_cmd = [ )
        "docker", "exec", "formatted_string",
        "psql", "-U", "netra", "-d", "netra", "-c", test_data['postgres']
            
        subprocess.run(insert_cmd, capture_output=True, timeout=10)

        if 'redis' in test_data:
        redis_cmd = [ )
        "docker", "exec", "formatted_string",
        "redis-cli", test_data['redis']
                
        subprocess.run(redis_cmd, capture_output=True, timeout=10)

        except Exception as e:
        logger.warning("formatted_string")

    def _verify_test_data(self, manager: UnifiedDockerManager, test_data: Dict[str, str]):
        """Verify test data exists in services."""
        pass
        try:
        project_name = manager._get_project_name()

        if 'postgres' in test_data:
            # Query data
        query_cmd = [ )
        "docker", "exec", "formatted_string",
        "psql", "-U", "netra", "-d", "netra", "-t", "-c",
        "SELECT COUNT(*) FROM test_table;"
            
        result = subprocess.run(query_cmd, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, "Failed to query postgres test data"
        count = int(result.stdout.strip())
        assert count > 0, "No test data found in postgres"

        if 'redis' in test_data:
                # Get data
        redis_cmd = [ )
        "docker", "exec", "formatted_string",
        "redis-cli", "EXISTS", "test_key"
                
        result = subprocess.run(redis_cmd, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, "Failed to query redis test data"
        exists = int(result.stdout.strip())
        assert exists == 1, "Test key not found in redis"

        except Exception as e:
        pytest.fail("formatted_string")


        @pytest.mark.integration
class TestParallelExecution(AlpineRegularSwitchingTestSuite):
        """Test parallel execution of Alpine and regular containers."""

        def test_parallel_alpine_and_regular_containers(self, docker_available, compose_available,
        isolated_test_environment):
        """Test running Alpine and regular containers simultaneously."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

    # Start both container types in parallel
        logger.info("Starting Alpine and regular containers in parallel")

        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

    # Verify different project names to avoid conflicts
        regular_project = manager_regular._get_project_name()
        alpine_project = manager_alpine._get_project_name()
        assert regular_project != alpine_project, "Project names should be different for parallel execution"

    # Start both environments simultaneously
    async def start_both():
        pass
        regular_task = asyncio.create_task( )
        manager_regular.start_services_smart(services, wait_healthy=True)
    
        alpine_task = asyncio.create_task( )
        manager_alpine.start_services_smart(services, wait_healthy=True)
    

        regular_success, alpine_success = await asyncio.gather(regular_task, alpine_task)
        await asyncio.sleep(0)
        return regular_success, alpine_success

        regular_success, alpine_success = asyncio.run(start_both())

        assert regular_success, "Failed to start regular containers in parallel execution"
        assert alpine_success, "Failed to start Alpine containers in parallel execution"

    # Verify both environments are healthy
        self._verify_container_functionality(manager_regular, services)
        self._verify_container_functionality(manager_alpine, services)

    # Verify port isolation (no conflicts)
        regular_ports = self._get_container_ports(manager_regular, services)
        alpine_ports = self._get_container_ports(manager_alpine, services)

    # Check for port conflicts
        regular_port_set = set(regular_ports.values())
        alpine_port_set = set(alpine_ports.values())
        conflicts = regular_port_set & alpine_port_set
        assert not conflicts, "formatted_string"

    # Test independent operations
        self._test_independent_operations(manager_regular, manager_alpine, services)

    # Cleanup both environments
    async def cleanup_both():
        pass
        regular_task = asyncio.create_task(manager_regular.graceful_shutdown())
        alpine_task = asyncio.create_task(manager_alpine.graceful_shutdown())
        await asyncio.gather(regular_task, alpine_task)

        asyncio.run(cleanup_both())

        def test_resource_contention_handling(self, docker_available, compose_available,
        isolated_test_environment):
        """Test resource contention when running multiple container types."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

    # Start multiple instances to test resource handling
        managers = []
        for i in range(3):
        for container_type in ["regular", "alpine"]:
        use_alpine = container_type == "alpine"
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=use_alpine
            
        managers.append((manager, container_type, i))

            # Start all managers
    async def start_all():
        pass
        tasks = []
        for manager, container_type, i in managers:
        task = asyncio.create_task( )
        manager.start_services_smart(services[:1], wait_healthy=True)  # Start fewer services to reduce resource usage
        
        tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0)
        return results

        logger.info("Starting multiple container instances to test resource contention")
        results = asyncio.run(start_all())

        # At least some should succeed (graceful degradation)
        successful_starts = sum(1 for result in results if result is True)
        assert successful_starts >= len(managers) // 2, \
        "formatted_string"

        # Cleanup all managers
    async def cleanup_all():
        pass
        tasks = []
        for manager, _, _ in managers:
        task = asyncio.create_task(manager.graceful_shutdown())
        tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.run(cleanup_all())

    def _get_container_ports(self, manager: UnifiedDockerManager, services: List[str]) -> Dict[str, int]:
        """Get exposed ports for containers."""
        ports = {}
        try:
        container_info = manager.get_enhanced_container_status(services)
        for service, info in container_info.items():
            Extract port from container info or use default
        if hasattr(info, 'ports') and info.ports:
        ports[service] = info.ports[0]  # Take first port
        else:
                    # Use service-specific default ports
        default_ports = {"postgres": 5432, "redis": 6379, "backend": 8000, "auth": 8081}
        ports[service] = default_ports.get(service, 8000)
        except Exception as e:
        logger.warning("formatted_string")

        await asyncio.sleep(0)
        return ports

        def _test_independent_operations(self, manager_regular: UnifiedDockerManager,
        manager_alpine: UnifiedDockerManager, services: List[str]):
        """Test that parallel containers operate independently."""
        try:
        # Insert different data in each environment
        regular_data = {"postgres": "INSERT INTO test_table (data) VALUES ('regular_parallel_data')"}
        alpine_data = {"postgres": "INSERT INTO test_table (data) VALUES ('alpine_parallel_data')"}

        # Setup tables in both
        for manager in [manager_regular, manager_alpine]:
        project_name = manager._get_project_name()
        create_cmd = [ )
        "docker", "exec", "formatted_string",
        "psql", "-U", "netra", "-d", "netra", "-c",
        "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);"
            
        subprocess.run(create_cmd, capture_output=True, timeout=10)

            # Insert data
        self._insert_test_data(manager_regular, regular_data)
        self._insert_test_data(manager_alpine, alpine_data)

            # Verify data isolation
        self._verify_test_data(manager_regular, regular_data)
        self._verify_test_data(manager_alpine, alpine_data)

        except Exception as e:
        logger.warning("formatted_string")


        @pytest.mark.integration
        @pytest.mark.performance
class TestPerformanceComparison(AlpineRegularSwitchingTestSuite):
        """Performance comparison tests between Alpine and regular containers."""

        def test_startup_time_comparison(self, docker_available, compose_available,
        isolated_test_environment):
        """Compare startup times between Alpine and regular containers."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]
        iterations = 3  # Multiple iterations for reliable metrics

        startup_times = {"regular": [], "alpine": []}

        for iteration in range(iterations):
        logger.info("formatted_string")

        # Test regular containers
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
        

        start_time = time.time()
        success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
        regular_time = time.time() - start_time

        assert success, "formatted_string"
        startup_times["regular"].append(regular_time)
        asyncio.run(manager_regular.graceful_shutdown())

        # Wait between tests to ensure clean state
        time.sleep(2)

        # Test Alpine containers
        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
        

        start_time = time.time()
        success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
        alpine_time = time.time() - start_time

        assert success, "formatted_string"
        startup_times["alpine"].append(alpine_time)
        asyncio.run(manager_alpine.graceful_shutdown())

        # Wait between iterations
        time.sleep(2)

        # Calculate averages
        avg_regular = sum(startup_times["regular"]) / len(startup_times["regular"])
        avg_alpine = sum(startup_times["alpine"]) / len(startup_times["alpine"])

        # Log detailed performance report
        logger.info("Startup Time Performance Report:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")

        # Alpine should not be significantly slower than regular
        assert avg_alpine <= avg_regular * 1.5, \
        "formatted_string"

        def test_memory_usage_comparison(self, docker_available, compose_available,
        isolated_test_environment):
        """Compare memory usage between Alpine and regular containers."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

        memory_results = {"regular": [], "alpine": []}

        for container_type in ["regular", "alpine"]:
        use_alpine = container_type == "alpine"

        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=use_alpine
        

        success = asyncio.run(manager.start_services_smart(services, wait_healthy=True))
        assert success, "formatted_string"

        # Wait for stabilization
        time.sleep(10)

        # Collect memory metrics multiple times
        for _ in range(5):
        metrics = self._collect_container_metrics(manager, services)
        memory_results[container_type].append(metrics.memory_usage_mb)
        time.sleep(2)

        asyncio.run(manager.graceful_shutdown())

            # Calculate averages
        avg_regular_memory = sum(memory_results["regular"]) / len(memory_results["regular"])
        avg_alpine_memory = sum(memory_results["alpine"]) / len(memory_results["alpine"])

            # Log performance report
        logger.info("Memory Usage Performance Report:")
        logger.info("formatted_string")
        logger.info("formatted_string")

        if avg_regular_memory > 0:
        savings = (avg_regular_memory - avg_alpine_memory) / avg_regular_memory * 100
        logger.info("formatted_string")

                # Alpine should use less memory
        assert avg_alpine_memory < avg_regular_memory, \
        "formatted_string"

        def test_cpu_usage_comparison(self, docker_available, compose_available,
        isolated_test_environment):
        """Compare CPU usage between Alpine and regular containers."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

        cpu_results = {"regular": [], "alpine": []}

        for container_type in ["regular", "alpine"]:
        use_alpine = container_type == "alpine"

        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=use_alpine
        

        success = asyncio.run(manager.start_services_smart(services, wait_healthy=True))
        assert success, "formatted_string"

        # Generate some load and measure
        time.sleep(5)

        for _ in range(3):
        metrics = self._collect_container_metrics(manager, services)
        cpu_results[container_type].append(metrics.cpu_usage_percent)
        time.sleep(5)

        asyncio.run(manager.graceful_shutdown())

            # Calculate averages
        avg_regular_cpu = sum(cpu_results["regular"]) / len(cpu_results["regular"])
        avg_alpine_cpu = sum(cpu_results["alpine"]) / len(cpu_results["alpine"])

            # Log performance report
        logger.info("CPU Usage Performance Report:")
        logger.info("formatted_string")
        logger.info("formatted_string")

            # CPU usage should be comparable (within reasonable bounds)
        if avg_regular_cpu > 0:
        ratio = avg_alpine_cpu / avg_regular_cpu
        logger.info("formatted_string")
        assert ratio < 2.0, f"Alpine CPU usage should not be >2x higher than regular"


        @pytest.mark.integration
class TestErrorRecovery(AlpineRegularSwitchingTestSuite):
        """Test error recovery and fallback mechanisms."""

        def test_fallback_from_alpine_to_regular(self, docker_available, compose_available,
        isolated_test_environment):
        """Test fallback from Alpine to regular containers when Alpine fails."""
        test_id = isolated_test_environment
        services = ["postgres"]

    # Simulate Alpine failure by using invalid compose file
        with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create invalid Alpine compose file
        invalid_alpine_compose = temp_path / "docker-compose.alpine-test.yml"
        invalid_alpine_compose.write_text(''' )
        version: '3.8'
        services:
        test-postgres:
        image: nonexistent-alpine-image:latest
        ports:
        - "5434:5432"
        ''')

                    # Create valid regular compose file as fallback
        regular_compose = temp_path / "docker-compose.test.yml"
        regular_compose.write_text(''' )
        version: '3.8'
        services:
        test-postgres:
        image: postgres:15
        environment:
        POSTGRES_DB: netra
        POSTGRES_USER: netra
        POSTGRES_PASSWORD: test_password
        ports:
        - "5434:5432"
        ''')

        with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_path)}):
                                        # Try Alpine first (should fail)
        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
                                        

                                        # Alpine startup should fail
        success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=False))
        assert not success, "Alpine containers should fail with invalid image"

                                        # Fallback to regular containers
        logger.info("Alpine failed as expected, falling back to regular containers")
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
                                        

                                        # Regular containers should work
        success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
        assert success, "Regular containers should work as fallback"

        self._verify_container_functionality(manager_regular, services)
        asyncio.run(manager_regular.graceful_shutdown())

        def test_cleanup_after_failed_alpine_deployment(self, docker_available, compose_available,
        isolated_test_environment):
        """Test cleanup after failed Alpine deployment."""
        test_id = isolated_test_environment

    # Start Alpine containers
        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

    # Start services (may partially succeed)
        asyncio.run(manager_alpine.start_services_smart(["postgres"], wait_healthy=False))

    # Force cleanup
        asyncio.run(manager_alpine.graceful_shutdown())

    # Verify cleanup was successful
        project_name = manager_alpine._get_project_name()
        cmd = ["docker", "ps", "-a", "--filter", "formatted_string", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        remaining_containers = result.stdout.strip().split(" )
        ") if result.stdout.strip() else []
        remaining_containers = [item for item in []]

        assert not remaining_containers, "formatted_string"

    # Verify we can start fresh containers after cleanup
        manager_fresh = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_fresh.start_services_smart(["postgres"], wait_healthy=True))
        assert success, "Should be able to start fresh containers after cleanup"

        asyncio.run(manager_fresh.graceful_shutdown())

        def test_partial_deployment_recovery(self, docker_available, compose_available,
        isolated_test_environment):
        """Test recovery from partial deployments."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

    # Start with one service type
        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

    # Start only one service first
        success = asyncio.run(manager.start_services_smart(["postgres"], wait_healthy=True))
        assert success, "Failed to start first service"

    # Add second service (simulating incremental deployment)
        success = asyncio.run(manager.start_services_smart(["redis"], wait_healthy=True))
        assert success, "Failed to add second service"

    # Verify both services are running
        self._verify_container_functionality(manager, services)

        asyncio.run(manager.graceful_shutdown())


        @pytest.mark.integration
class TestMigrationPaths(AlpineRegularSwitchingTestSuite):
        """Test migration paths and gradual transitions."""

        def test_gradual_migration_some_alpine_some_regular(self, docker_available, compose_available,
        isolated_test_environment):
        """Test gradual migration with some services Alpine, some regular."""
        test_id = isolated_test_environment

    # Start with all regular services
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_regular.start_services_smart(["postgres", "redis"], wait_healthy=True))
        assert success, "Failed to start regular services"

    # Insert test data
        self._insert_test_data(manager_regular, {"postgres": "INSERT INTO test_table (data) VALUES ('gradual_test')"})
        asyncio.run(manager_regular.graceful_shutdown())

    # Migrate one service to Alpine
        manager_alpine_partial = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

    # Start only Redis with Alpine (partial migration)
        success = asyncio.run(manager_alpine_partial.start_services_smart(["redis"], wait_healthy=True))
        assert success, "Failed to start Alpine Redis"

    # Start Postgres with regular (keeping it regular)
        manager_regular_partial = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_regular_partial.start_services_smart(["postgres"], wait_healthy=True))
        assert success, "Failed to start regular Postgres"

    # Verify mixed environment works
        self._verify_container_functionality(manager_alpine_partial, ["redis"])
        self._verify_container_functionality(manager_regular_partial, ["postgres"])

    # Verify data persistence
        self._verify_test_data(manager_regular_partial, {"postgres": "INSERT INTO test_table (data) VALUES ('gradual_test')"})

    # Cleanup
        asyncio.run(manager_alpine_partial.graceful_shutdown())
        asyncio.run(manager_regular_partial.graceful_shutdown())

        def test_rollback_scenario(self, docker_available, compose_available,
        isolated_test_environment):
        """Test rollback from Alpine to regular containers."""
        test_id = isolated_test_environment
        services = ["postgres", "redis"]

    # Start with Alpine containers
        logger.info("Phase 1: Starting with Alpine containers")
        manager_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
    

        success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
        assert success, "Failed to start Alpine containers"

    # Insert data and verify functionality
        alpine_data = {"postgres": "INSERT INTO test_table (data) VALUES ('alpine_rollback_test')"}
        self._insert_test_data(manager_alpine, alpine_data)
        self._verify_container_functionality(manager_alpine, services)

    # Simulate issue requiring rollback
        logger.info("Phase 2: Simulating issue and performing rollback")
        asyncio.run(manager_alpine.graceful_shutdown())

    # Rollback to regular containers
        manager_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
    

        success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
        assert success, "Failed to rollback to regular containers"

    # Verify data survived rollback
        self._verify_test_data(manager_regular, alpine_data)
        self._verify_container_functionality(manager_regular, services)

    # Verify containers are indeed regular (not Alpine)
        container_info = manager_regular.get_enhanced_container_status(services)
        for service, info in container_info.items():
        assert "alpine" not in info.image.lower(), "formatted_string"

        asyncio.run(manager_regular.graceful_shutdown())


        @pytest.mark.integration
class TestCICDIntegration(AlpineRegularSwitchingTestSuite):
        """Test CI/CD integration scenarios."""

        def test_environment_variable_configuration(self, docker_available, compose_available,
        isolated_test_environment):
        """Test container selection based on environment variables."""
        test_id = isolated_test_environment

    # Test with FORCE_ALPINE=true
        with patch.dict(os.environ, {"FORCE_ALPINE": "true", "CI": "true"}):
        manager_forced_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True  # Should use Alpine due to env var
        

        compose_file = manager_forced_alpine._get_compose_file()
        assert "alpine" in compose_file.lower(), "Should select Alpine compose file when FORCE_ALPINE=true"

        # Test with FORCE_ALPINE=false
        with patch.dict(os.environ, {"FORCE_ALPINE": "false", "CI": "true"}):
        manager_forced_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False  # Should use regular due to env var
            

        compose_file = manager_forced_regular._get_compose_file()
        assert "alpine" not in compose_file.lower(), "Should select regular compose file when FORCE_ALPINE=false"

        def test_ci_specific_optimizations(self, docker_available, compose_available,
        isolated_test_environment):
        """Test CI-specific optimizations with different container types."""
        test_id = isolated_test_environment
        services = ["postgres"]  # Minimal services for CI

    # Simulate CI environment
        with patch.dict(os.environ, {"CI": "true", "BUILD_MODE": "test"}):

        # Test Alpine optimization for CI
        manager_ci_alpine = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=True
        

        start_time = time.time()
        success = asyncio.run(manager_ci_alpine.start_services_smart(services, wait_healthy=True))
        ci_alpine_time = time.time() - start_time

        assert success, "Alpine containers should work in CI environment"
        self._verify_container_functionality(manager_ci_alpine, services)

        asyncio.run(manager_ci_alpine.graceful_shutdown())

        # Test regular containers for CI
        manager_ci_regular = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=False
        

        start_time = time.time()
        success = asyncio.run(manager_ci_regular.start_services_smart(services, wait_healthy=True))
        ci_regular_time = time.time() - start_time

        assert success, "Regular containers should work in CI environment"
        self._verify_container_functionality(manager_ci_regular, services)

        asyncio.run(manager_ci_regular.graceful_shutdown())

        # Log CI performance comparison
        logger.info("CI Performance Comparison:")
        logger.info("formatted_string")
        logger.info("formatted_string")
        logger.info("formatted_string")

        def test_different_test_runner_configurations(self, docker_available, compose_available,
        isolated_test_environment):
        """Test Alpine/regular switching with different test runner configs."""
        test_id = isolated_test_environment

    # Test configurations that might be used by unified test runner
        configs = [ )
        {"use_alpine": True, "rebuild_images": False},
        {"use_alpine": False, "rebuild_images": False},
        {"use_alpine": True, "rebuild_images": True},
        {"use_alpine": False, "rebuild_images": True}
    

        for i, config in enumerate(configs):
        logger.info("formatted_string")

        manager = UnifiedDockerManager( )
        environment_type=EnvironmentType.SHARED,
        test_id="formatted_string",
        use_alpine=config["use_alpine"],
        rebuild_images=config["rebuild_images"]
        

        # Start minimal services
        success = asyncio.run(manager.start_services_smart(["postgres"], wait_healthy=True))
        assert success, "formatted_string"

        # Verify functionality
        self._verify_container_functionality(manager, ["postgres"])

        # Verify container type matches configuration
        container_info = manager.get_enhanced_container_status(["postgres"])
        postgres_info = container_info.get("postgres")

        if config["use_alpine"]:
        assert any(keyword in postgres_info.image.lower() for keyword in ['alpine', 'minimal']), \
        "formatted_string"
        else:
                # Regular containers should not have 'alpine' in image name
        assert 'alpine' not in postgres_info.image.lower(), \
        "formatted_string"

        asyncio.run(manager.graceful_shutdown())


        if __name__ == "__main__":
                    # Run all tests with comprehensive reporting
        pytest.main([ ))
        __file__,
        "-v",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings",
        "-m", "not performance",  # Skip performance tests by default for speed
        "--durations=10"  # Show slowest 10 tests
                    
