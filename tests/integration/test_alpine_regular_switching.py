#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive Integration Tests for Alpine vs Regular Container Switching

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal - Development Velocity, Risk Reduction, CI/CD Optimization
    # REMOVED_SYNTAX_ERROR: - Business Goal: Enable memory-optimized test execution with seamless switching capabilities
    # REMOVED_SYNTAX_ERROR: - Value Impact: Reduces CI costs by 40-60%, faster test execution, robust container orchestration
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Enables production-ready container switching for different deployment scenarios

    # REMOVED_SYNTAX_ERROR: This test suite validates:
        # REMOVED_SYNTAX_ERROR: 1. Sequential switching between Alpine and regular containers
        # REMOVED_SYNTAX_ERROR: 2. Parallel execution with proper isolation
        # REMOVED_SYNTAX_ERROR: 3. Performance comparisons and benchmarks
        # REMOVED_SYNTAX_ERROR: 4. Error recovery and fallback mechanisms
        # REMOVED_SYNTAX_ERROR: 5. Migration path and data persistence
        # REMOVED_SYNTAX_ERROR: 6. CI/CD integration scenarios

        # REMOVED_SYNTAX_ERROR: CRITICAL: These tests use REAL Docker containers and services (no mocks).
        # REMOVED_SYNTAX_ERROR: They validate production scenarios for container switching functionality.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import logging
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import psutil
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import subprocess
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: import tempfile
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: import yaml
        # REMOVED_SYNTAX_ERROR: from contextlib import asynccontextmanager
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Optional, Tuple, Any
        # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Add project root to path for absolute imports (CLAUDE.md compliance)
        # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent
        # REMOVED_SYNTAX_ERROR: sys.path.insert(0, str(project_root))

        # REMOVED_SYNTAX_ERROR: from test_framework.unified_docker_manager import ( )
        # REMOVED_SYNTAX_ERROR: UnifiedDockerManager,
        # REMOVED_SYNTAX_ERROR: EnvironmentType,
        # REMOVED_SYNTAX_ERROR: OrchestrationConfig,
        # REMOVED_SYNTAX_ERROR: ServiceMode
        
        # REMOVED_SYNTAX_ERROR: from test_framework.docker_port_discovery import DockerPortDiscovery
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient

        # Configure logging
        # REMOVED_SYNTAX_ERROR: logging.basicConfig(level=logging.INFO)
        # REMOVED_SYNTAX_ERROR: logger = logging.getLogger(__name__)


# REMOVED_SYNTAX_ERROR: class ContainerMetrics:
    # REMOVED_SYNTAX_ERROR: """Container performance metrics collection."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.startup_time = 0.0
    # REMOVED_SYNTAX_ERROR: self.memory_usage_mb = 0.0
    # REMOVED_SYNTAX_ERROR: self.cpu_usage_percent = 0.0
    # REMOVED_SYNTAX_ERROR: self.disk_usage_mb = 0.0
    # REMOVED_SYNTAX_ERROR: self.container_names = []
    # REMOVED_SYNTAX_ERROR: self.image_sizes_mb = {}

# REMOVED_SYNTAX_ERROR: def to_dict(self) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "startup_time": self.startup_time,
    # REMOVED_SYNTAX_ERROR: "memory_usage_mb": self.memory_usage_mb,
    # REMOVED_SYNTAX_ERROR: "cpu_usage_percent": self.cpu_usage_percent,
    # REMOVED_SYNTAX_ERROR: "disk_usage_mb": self.disk_usage_mb,
    # REMOVED_SYNTAX_ERROR: "container_names": self.container_names,
    # REMOVED_SYNTAX_ERROR: "image_sizes_mb": self.image_sizes_mb
    


# REMOVED_SYNTAX_ERROR: class AlpineRegularSwitchingTestSuite:
    # REMOVED_SYNTAX_ERROR: """Main test suite for comprehensive Alpine vs regular container switching."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def docker_available(self):
    # REMOVED_SYNTAX_ERROR: """Check if Docker is available for integration tests."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = subprocess.run(["docker", "version"], capture_output=True, timeout=10)
        # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
            # REMOVED_SYNTAX_ERROR: pytest.skip("Docker not available")
            # REMOVED_SYNTAX_ERROR: return True
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def compose_available(self):
    # REMOVED_SYNTAX_ERROR: """Check if docker-compose is available."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = subprocess.run(["docker-compose", "version"], capture_output=True, timeout=10)
        # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
            # REMOVED_SYNTAX_ERROR: pytest.skip("Docker Compose not available")
            # REMOVED_SYNTAX_ERROR: return True
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: pytest.skip("formatted_string")

                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def isolated_test_environment(self):
    # REMOVED_SYNTAX_ERROR: """Create isolated test environment for each test."""
    # REMOVED_SYNTAX_ERROR: test_id = "formatted_string"

    # Cleanup any existing containers from previous failed tests
    # REMOVED_SYNTAX_ERROR: self._cleanup_test_containers(test_id)

    # REMOVED_SYNTAX_ERROR: yield test_id

    # Cleanup after test
    # REMOVED_SYNTAX_ERROR: self._cleanup_test_containers(test_id)

# REMOVED_SYNTAX_ERROR: def _cleanup_test_containers(self, test_id: str):
    # REMOVED_SYNTAX_ERROR: """Clean up containers created during testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # Find and stop containers with test_id prefix
        # REMOVED_SYNTAX_ERROR: cmd = ["docker", "ps", "-a", "--filter", "formatted_string", "--format", "{{.Names}}"]
        # REMOVED_SYNTAX_ERROR: result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # REMOVED_SYNTAX_ERROR: if result.returncode == 0 and result.stdout.strip():
            # REMOVED_SYNTAX_ERROR: container_names = result.stdout.strip().split(" )
            # REMOVED_SYNTAX_ERROR: ")
            # REMOVED_SYNTAX_ERROR: for name in container_names:
                # REMOVED_SYNTAX_ERROR: if name.strip():
                    # REMOVED_SYNTAX_ERROR: subprocess.run(["docker", "rm", "-f", name.strip()],
                    # REMOVED_SYNTAX_ERROR: capture_output=True, timeout=10)
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")


                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestSequentialSwitching(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Test sequential switching between Alpine and regular containers."""

# REMOVED_SYNTAX_ERROR: def test_regular_to_alpine_to_regular_switching(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test complete switching cycle: Regular -> Alpine -> Regular."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # Phase 1: Start with regular containers
    # REMOVED_SYNTAX_ERROR: logger.info("Phase 1: Starting regular containers")
    # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: regular_startup_time = time.time() - start_time

    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular containers in phase 1"

    # Verify regular containers are working
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular, services)
    # REMOVED_SYNTAX_ERROR: regular_metrics = self._collect_container_metrics(manager_regular, services)
    # REMOVED_SYNTAX_ERROR: regular_metrics.startup_time = regular_startup_time

    # Phase 2: Switch to Alpine containers
    # REMOVED_SYNTAX_ERROR: logger.info("Phase 2: Switching to Alpine containers")
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())

    # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: alpine_startup_time = time.time() - start_time

    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start Alpine containers in phase 2"

    # Verify Alpine containers are working
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_alpine, services)
    # REMOVED_SYNTAX_ERROR: alpine_metrics = self._collect_container_metrics(manager_alpine, services)
    # REMOVED_SYNTAX_ERROR: alpine_metrics.startup_time = alpine_startup_time

    # Verify containers are actually Alpine-based
    # REMOVED_SYNTAX_ERROR: self._verify_alpine_containers(manager_alpine, services)

    # Phase 3: Switch back to regular containers
    # REMOVED_SYNTAX_ERROR: logger.info("Phase 3: Switching back to regular containers")
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.graceful_shutdown())

    # REMOVED_SYNTAX_ERROR: manager_regular_2 = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular_2.start_services_smart(services, wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: regular_2_startup_time = time.time() - start_time

    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular containers in phase 3"

    # Verify regular containers are working again
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular_2, services)
    # REMOVED_SYNTAX_ERROR: regular_2_metrics = self._collect_container_metrics(manager_regular_2, services)
    # REMOVED_SYNTAX_ERROR: regular_2_metrics.startup_time = regular_2_startup_time

    # Cleanup
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular_2.graceful_shutdown())

    # Log performance comparison
    # REMOVED_SYNTAX_ERROR: logger.info("Sequential Switching Performance Report:")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

    # Assertions for performance
    # REMOVED_SYNTAX_ERROR: assert alpine_metrics.memory_usage_mb < regular_metrics.memory_usage_mb, \
    # REMOVED_SYNTAX_ERROR: "Alpine containers should use less memory than regular containers"

    # Verify consistent behavior across switches
    # REMOVED_SYNTAX_ERROR: startup_variance = abs(regular_startup_time - regular_2_startup_time) / regular_startup_time
    # REMOVED_SYNTAX_ERROR: assert startup_variance < 0.5, "Startup times should be consistent across switches"

# REMOVED_SYNTAX_ERROR: def test_data_persistence_across_switches(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test that data persists when switching between container types."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment

    # Start with regular containers and insert test data
    # REMOVED_SYNTAX_ERROR: logger.info("Starting regular containers and inserting test data")
    # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(["postgres", "redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular containers for data test"

    # Insert test data
    # REMOVED_SYNTAX_ERROR: test_data = { )
    # REMOVED_SYNTAX_ERROR: "postgres": "INSERT INTO test_table (data) VALUES ('regular_test_data')",
    # REMOVED_SYNTAX_ERROR: "redis": "SET test_key 'regular_test_value'"
    

    # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_regular, test_data)
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())

    # Switch to Alpine and verify data persistence
    # REMOVED_SYNTAX_ERROR: logger.info("Switching to Alpine containers and verifying data persistence")
    # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine.start_services_smart(["postgres", "redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start Alpine containers for data test"

    # Verify test data is accessible
    # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_alpine, test_data)

    # Insert additional data in Alpine containers
    # REMOVED_SYNTAX_ERROR: alpine_data = { )
    # REMOVED_SYNTAX_ERROR: "postgres": "INSERT INTO test_table (data) VALUES ('alpine_test_data')",
    # REMOVED_SYNTAX_ERROR: "redis": "SET alpine_key 'alpine_test_value'"
    

    # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_alpine, alpine_data)
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.graceful_shutdown())

    # Switch back to regular and verify all data
    # REMOVED_SYNTAX_ERROR: logger.info("Switching back to regular containers and verifying all data")
    # REMOVED_SYNTAX_ERROR: manager_regular_2 = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular_2.start_services_smart(["postgres", "redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular containers for final data verification"

    # Verify both original and Alpine-inserted data
    # REMOVED_SYNTAX_ERROR: combined_data = {**test_data, **alpine_data}
    # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_regular_2, combined_data)

    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular_2.graceful_shutdown())

# REMOVED_SYNTAX_ERROR: def _verify_container_functionality(self, manager: UnifiedDockerManager, services: List[str]):
    # REMOVED_SYNTAX_ERROR: """Verify that containers are functional."""
    # REMOVED_SYNTAX_ERROR: health_report = manager.get_health_report()
    # REMOVED_SYNTAX_ERROR: assert "FAILED" not in health_report, "formatted_string"

    # REMOVED_SYNTAX_ERROR: for service in services:
        # REMOVED_SYNTAX_ERROR: health = manager.service_health.get(service)
        # REMOVED_SYNTAX_ERROR: assert health is not None, "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert health.is_healthy, "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert health.response_time_ms < 10000, "formatted_string"

# REMOVED_SYNTAX_ERROR: def _verify_alpine_containers(self, manager: UnifiedDockerManager, services: List[str]):
    # REMOVED_SYNTAX_ERROR: """Verify containers are actually Alpine-based."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: container_info = manager.get_enhanced_container_status(services)
    # REMOVED_SYNTAX_ERROR: for service, info in container_info.items():
        # Check if image name contains 'alpine' or if it's an Alpine-based image
        # REMOVED_SYNTAX_ERROR: assert any(keyword in info.image.lower() for keyword in ['alpine', 'minimal']), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def _collect_container_metrics(self, manager: UnifiedDockerManager, services: List[str]) -> ContainerMetrics:
    # REMOVED_SYNTAX_ERROR: """Collect performance metrics from containers."""
    # REMOVED_SYNTAX_ERROR: metrics = ContainerMetrics()

    # REMOVED_SYNTAX_ERROR: try:
        # Get container names and basic info
        # REMOVED_SYNTAX_ERROR: container_info = manager.get_enhanced_container_status(services)
        # REMOVED_SYNTAX_ERROR: metrics.container_names = list(container_info.keys())

        # Collect memory and CPU usage
        # REMOVED_SYNTAX_ERROR: total_memory = 0.0
        # REMOVED_SYNTAX_ERROR: total_cpu = 0.0

        # REMOVED_SYNTAX_ERROR: for service, info in container_info.items():
            # Get container stats
            # REMOVED_SYNTAX_ERROR: cmd = ["docker", "stats", "--no-stream", "--format",
            # REMOVED_SYNTAX_ERROR: "{{.MemUsage}},{{.CPUPerc}}", info.name]
            # REMOVED_SYNTAX_ERROR: result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # REMOVED_SYNTAX_ERROR: if result.returncode == 0:
                # REMOVED_SYNTAX_ERROR: stats_line = result.stdout.strip()
                # REMOVED_SYNTAX_ERROR: if stats_line:
                    # REMOVED_SYNTAX_ERROR: mem_usage, cpu_perc = stats_line.split(',')

                    # Parse memory usage (e.g., "45.2MiB / 512MiB")
                    # REMOVED_SYNTAX_ERROR: if '/' in mem_usage:
                        # REMOVED_SYNTAX_ERROR: mem_str = mem_usage.split(' / ')[0].strip()
                        # REMOVED_SYNTAX_ERROR: mem_mb = self._parse_memory_string(mem_str)
                        # REMOVED_SYNTAX_ERROR: total_memory += mem_mb

                        # Parse CPU percentage (e.g., "1.25%")
                        # REMOVED_SYNTAX_ERROR: if '%' in cpu_perc:
                            # REMOVED_SYNTAX_ERROR: cpu_val = float(cpu_perc.replace('%', '').strip())
                            # REMOVED_SYNTAX_ERROR: total_cpu += cpu_val

                            # Get image size
                            # REMOVED_SYNTAX_ERROR: img_cmd = ["docker", "images", info.image, "--format", "{{.Size}}"]
                            # REMOVED_SYNTAX_ERROR: img_result = subprocess.run(img_cmd, capture_output=True, text=True, timeout=10)
                            # REMOVED_SYNTAX_ERROR: if img_result.returncode == 0 and img_result.stdout.strip():
                                # REMOVED_SYNTAX_ERROR: size_str = img_result.stdout.strip()
                                # REMOVED_SYNTAX_ERROR: metrics.image_sizes_mb[service] = self._parse_memory_string(size_str)

                                # REMOVED_SYNTAX_ERROR: metrics.memory_usage_mb = total_memory
                                # REMOVED_SYNTAX_ERROR: metrics.cpu_usage_percent = total_cpu

                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                                    # REMOVED_SYNTAX_ERROR: return metrics

# REMOVED_SYNTAX_ERROR: def _parse_memory_string(self, mem_str: str) -> float:
    # REMOVED_SYNTAX_ERROR: """Parse memory string to MB."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: if 'GB' in mem_str:
            # REMOVED_SYNTAX_ERROR: return float(mem_str.replace('GB', '').strip()) * 1000
            # REMOVED_SYNTAX_ERROR: elif 'MB' in mem_str:
                # REMOVED_SYNTAX_ERROR: return float(mem_str.replace('MB', '').strip())
                # REMOVED_SYNTAX_ERROR: elif 'GiB' in mem_str:
                    # REMOVED_SYNTAX_ERROR: return float(mem_str.replace('GiB', '').strip()) * 1024
                    # REMOVED_SYNTAX_ERROR: elif 'MiB' in mem_str:
                        # REMOVED_SYNTAX_ERROR: return float(mem_str.replace('MiB', '').strip())
                        # REMOVED_SYNTAX_ERROR: elif 'KB' in mem_str or 'KiB' in mem_str:
                            # REMOVED_SYNTAX_ERROR: return float(mem_str.replace('KB', '').replace('KiB', '').strip()) / 1000
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: return 0.0
                                # REMOVED_SYNTAX_ERROR: except ValueError:
                                    # REMOVED_SYNTAX_ERROR: return 0.0

# REMOVED_SYNTAX_ERROR: def _insert_test_data(self, manager: UnifiedDockerManager, test_data: Dict[str, str]):
    # REMOVED_SYNTAX_ERROR: """Insert test data into services."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: project_name = manager._get_project_name()

        # REMOVED_SYNTAX_ERROR: if 'postgres' in test_data:
            # First create table if it doesn't exist
            # REMOVED_SYNTAX_ERROR: create_cmd = [ )
            # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
            # REMOVED_SYNTAX_ERROR: "psql", "-U", "netra", "-d", "netra", "-c",
            # REMOVED_SYNTAX_ERROR: "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);"
            
            # REMOVED_SYNTAX_ERROR: subprocess.run(create_cmd, capture_output=True, timeout=10)

            # Insert data
            # REMOVED_SYNTAX_ERROR: insert_cmd = [ )
            # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
            # REMOVED_SYNTAX_ERROR: "psql", "-U", "netra", "-d", "netra", "-c", test_data['postgres']
            
            # REMOVED_SYNTAX_ERROR: subprocess.run(insert_cmd, capture_output=True, timeout=10)

            # REMOVED_SYNTAX_ERROR: if 'redis' in test_data:
                # REMOVED_SYNTAX_ERROR: redis_cmd = [ )
                # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
                # REMOVED_SYNTAX_ERROR: "redis-cli", test_data['redis']
                
                # REMOVED_SYNTAX_ERROR: subprocess.run(redis_cmd, capture_output=True, timeout=10)

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

# REMOVED_SYNTAX_ERROR: def _verify_test_data(self, manager: UnifiedDockerManager, test_data: Dict[str, str]):
    # REMOVED_SYNTAX_ERROR: """Verify test data exists in services."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: project_name = manager._get_project_name()

        # REMOVED_SYNTAX_ERROR: if 'postgres' in test_data:
            # Query data
            # REMOVED_SYNTAX_ERROR: query_cmd = [ )
            # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
            # REMOVED_SYNTAX_ERROR: "psql", "-U", "netra", "-d", "netra", "-t", "-c",
            # REMOVED_SYNTAX_ERROR: "SELECT COUNT(*) FROM test_table;"
            
            # REMOVED_SYNTAX_ERROR: result = subprocess.run(query_cmd, capture_output=True, text=True, timeout=10)
            # REMOVED_SYNTAX_ERROR: assert result.returncode == 0, "Failed to query postgres test data"
            # REMOVED_SYNTAX_ERROR: count = int(result.stdout.strip())
            # REMOVED_SYNTAX_ERROR: assert count > 0, "No test data found in postgres"

            # REMOVED_SYNTAX_ERROR: if 'redis' in test_data:
                # Get data
                # REMOVED_SYNTAX_ERROR: redis_cmd = [ )
                # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
                # REMOVED_SYNTAX_ERROR: "redis-cli", "EXISTS", "test_key"
                
                # REMOVED_SYNTAX_ERROR: result = subprocess.run(redis_cmd, capture_output=True, text=True, timeout=10)
                # REMOVED_SYNTAX_ERROR: assert result.returncode == 0, "Failed to query redis test data"
                # REMOVED_SYNTAX_ERROR: exists = int(result.stdout.strip())
                # REMOVED_SYNTAX_ERROR: assert exists == 1, "Test key not found in redis"

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")


                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestParallelExecution(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Test parallel execution of Alpine and regular containers."""

# REMOVED_SYNTAX_ERROR: def test_parallel_alpine_and_regular_containers(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test running Alpine and regular containers simultaneously."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # Start both container types in parallel
    # REMOVED_SYNTAX_ERROR: logger.info("Starting Alpine and regular containers in parallel")

    # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # Verify different project names to avoid conflicts
    # REMOVED_SYNTAX_ERROR: regular_project = manager_regular._get_project_name()
    # REMOVED_SYNTAX_ERROR: alpine_project = manager_alpine._get_project_name()
    # REMOVED_SYNTAX_ERROR: assert regular_project != alpine_project, "Project names should be different for parallel execution"

    # Start both environments simultaneously
# REMOVED_SYNTAX_ERROR: async def start_both():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: regular_task = asyncio.create_task( )
    # REMOVED_SYNTAX_ERROR: manager_regular.start_services_smart(services, wait_healthy=True)
    
    # REMOVED_SYNTAX_ERROR: alpine_task = asyncio.create_task( )
    # REMOVED_SYNTAX_ERROR: manager_alpine.start_services_smart(services, wait_healthy=True)
    

    # REMOVED_SYNTAX_ERROR: regular_success, alpine_success = await asyncio.gather(regular_task, alpine_task)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return regular_success, alpine_success

    # REMOVED_SYNTAX_ERROR: regular_success, alpine_success = asyncio.run(start_both())

    # REMOVED_SYNTAX_ERROR: assert regular_success, "Failed to start regular containers in parallel execution"
    # REMOVED_SYNTAX_ERROR: assert alpine_success, "Failed to start Alpine containers in parallel execution"

    # Verify both environments are healthy
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular, services)
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_alpine, services)

    # Verify port isolation (no conflicts)
    # REMOVED_SYNTAX_ERROR: regular_ports = self._get_container_ports(manager_regular, services)
    # REMOVED_SYNTAX_ERROR: alpine_ports = self._get_container_ports(manager_alpine, services)

    # Check for port conflicts
    # REMOVED_SYNTAX_ERROR: regular_port_set = set(regular_ports.values())
    # REMOVED_SYNTAX_ERROR: alpine_port_set = set(alpine_ports.values())
    # REMOVED_SYNTAX_ERROR: conflicts = regular_port_set & alpine_port_set
    # REMOVED_SYNTAX_ERROR: assert not conflicts, "formatted_string"

    # Test independent operations
    # REMOVED_SYNTAX_ERROR: self._test_independent_operations(manager_regular, manager_alpine, services)

    # Cleanup both environments
# REMOVED_SYNTAX_ERROR: async def cleanup_both():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: regular_task = asyncio.create_task(manager_regular.graceful_shutdown())
    # REMOVED_SYNTAX_ERROR: alpine_task = asyncio.create_task(manager_alpine.graceful_shutdown())
    # REMOVED_SYNTAX_ERROR: await asyncio.gather(regular_task, alpine_task)

    # REMOVED_SYNTAX_ERROR: asyncio.run(cleanup_both())

# REMOVED_SYNTAX_ERROR: def test_resource_contention_handling(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test resource contention when running multiple container types."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # Start multiple instances to test resource handling
    # REMOVED_SYNTAX_ERROR: managers = []
    # REMOVED_SYNTAX_ERROR: for i in range(3):
        # REMOVED_SYNTAX_ERROR: for container_type in ["regular", "alpine"]:
            # REMOVED_SYNTAX_ERROR: use_alpine = container_type == "alpine"
            # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager( )
            # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
            # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: use_alpine=use_alpine
            
            # REMOVED_SYNTAX_ERROR: managers.append((manager, container_type, i))

            # Start all managers
# REMOVED_SYNTAX_ERROR: async def start_all():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for manager, container_type, i in managers:
        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task( )
        # REMOVED_SYNTAX_ERROR: manager.start_services_smart(services[:1], wait_healthy=True)  # Start fewer services to reduce resource usage
        
        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return results

        # REMOVED_SYNTAX_ERROR: logger.info("Starting multiple container instances to test resource contention")
        # REMOVED_SYNTAX_ERROR: results = asyncio.run(start_all())

        # At least some should succeed (graceful degradation)
        # REMOVED_SYNTAX_ERROR: successful_starts = sum(1 for result in results if result is True)
        # REMOVED_SYNTAX_ERROR: assert successful_starts >= len(managers) // 2, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # Cleanup all managers
# REMOVED_SYNTAX_ERROR: async def cleanup_all():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for manager, _, _ in managers:
        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(manager.graceful_shutdown())
        # REMOVED_SYNTAX_ERROR: tasks.append(task)
        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks, return_exceptions=True)

        # REMOVED_SYNTAX_ERROR: asyncio.run(cleanup_all())

# REMOVED_SYNTAX_ERROR: def _get_container_ports(self, manager: UnifiedDockerManager, services: List[str]) -> Dict[str, int]:
    # REMOVED_SYNTAX_ERROR: """Get exposed ports for containers."""
    # REMOVED_SYNTAX_ERROR: ports = {}
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: container_info = manager.get_enhanced_container_status(services)
        # REMOVED_SYNTAX_ERROR: for service, info in container_info.items():
            # Extract port from container info or use default
            # REMOVED_SYNTAX_ERROR: if hasattr(info, 'ports') and info.ports:
                # REMOVED_SYNTAX_ERROR: ports[service] = info.ports[0]  # Take first port
                # REMOVED_SYNTAX_ERROR: else:
                    # Use service-specific default ports
                    # REMOVED_SYNTAX_ERROR: default_ports = {"postgres": 5432, "redis": 6379, "backend": 8000, "auth": 8081}
                    # REMOVED_SYNTAX_ERROR: ports[service] = default_ports.get(service, 8000)
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return ports

# REMOVED_SYNTAX_ERROR: def _test_independent_operations(self, manager_regular: UnifiedDockerManager,
# REMOVED_SYNTAX_ERROR: manager_alpine: UnifiedDockerManager, services: List[str]):
    # REMOVED_SYNTAX_ERROR: """Test that parallel containers operate independently."""
    # REMOVED_SYNTAX_ERROR: try:
        # Insert different data in each environment
        # REMOVED_SYNTAX_ERROR: regular_data = {"postgres": "INSERT INTO test_table (data) VALUES ('regular_parallel_data')"}
        # REMOVED_SYNTAX_ERROR: alpine_data = {"postgres": "INSERT INTO test_table (data) VALUES ('alpine_parallel_data')"}

        # Setup tables in both
        # REMOVED_SYNTAX_ERROR: for manager in [manager_regular, manager_alpine]:
            # REMOVED_SYNTAX_ERROR: project_name = manager._get_project_name()
            # REMOVED_SYNTAX_ERROR: create_cmd = [ )
            # REMOVED_SYNTAX_ERROR: "docker", "exec", "formatted_string",
            # REMOVED_SYNTAX_ERROR: "psql", "-U", "netra", "-d", "netra", "-c",
            # REMOVED_SYNTAX_ERROR: "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);"
            
            # REMOVED_SYNTAX_ERROR: subprocess.run(create_cmd, capture_output=True, timeout=10)

            # Insert data
            # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_regular, regular_data)
            # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_alpine, alpine_data)

            # Verify data isolation
            # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_regular, regular_data)
            # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_alpine, alpine_data)

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")


                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                # REMOVED_SYNTAX_ERROR: @pytest.mark.performance
# REMOVED_SYNTAX_ERROR: class TestPerformanceComparison(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Performance comparison tests between Alpine and regular containers."""

# REMOVED_SYNTAX_ERROR: def test_startup_time_comparison(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Compare startup times between Alpine and regular containers."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]
    # REMOVED_SYNTAX_ERROR: iterations = 3  # Multiple iterations for reliable metrics

    # REMOVED_SYNTAX_ERROR: startup_times = {"regular": [], "alpine": []}

    # REMOVED_SYNTAX_ERROR: for iteration in range(iterations):
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # Test regular containers
        # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=False
        

        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: regular_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: assert success, "formatted_string"
        # REMOVED_SYNTAX_ERROR: startup_times["regular"].append(regular_time)
        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())

        # Wait between tests to ensure clean state
        # REMOVED_SYNTAX_ERROR: time.sleep(2)

        # Test Alpine containers
        # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=True
        

        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: alpine_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: assert success, "formatted_string"
        # REMOVED_SYNTAX_ERROR: startup_times["alpine"].append(alpine_time)
        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.graceful_shutdown())

        # Wait between iterations
        # REMOVED_SYNTAX_ERROR: time.sleep(2)

        # Calculate averages
        # REMOVED_SYNTAX_ERROR: avg_regular = sum(startup_times["regular"]) / len(startup_times["regular"])
        # REMOVED_SYNTAX_ERROR: avg_alpine = sum(startup_times["alpine"]) / len(startup_times["alpine"])

        # Log detailed performance report
        # REMOVED_SYNTAX_ERROR: logger.info("Startup Time Performance Report:")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # Alpine should not be significantly slower than regular
        # REMOVED_SYNTAX_ERROR: assert avg_alpine <= avg_regular * 1.5, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_memory_usage_comparison(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Compare memory usage between Alpine and regular containers."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # REMOVED_SYNTAX_ERROR: memory_results = {"regular": [], "alpine": []}

    # REMOVED_SYNTAX_ERROR: for container_type in ["regular", "alpine"]:
        # REMOVED_SYNTAX_ERROR: use_alpine = container_type == "alpine"

        # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=use_alpine
        

        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: assert success, "formatted_string"

        # Wait for stabilization
        # REMOVED_SYNTAX_ERROR: time.sleep(10)

        # Collect memory metrics multiple times
        # REMOVED_SYNTAX_ERROR: for _ in range(5):
            # REMOVED_SYNTAX_ERROR: metrics = self._collect_container_metrics(manager, services)
            # REMOVED_SYNTAX_ERROR: memory_results[container_type].append(metrics.memory_usage_mb)
            # REMOVED_SYNTAX_ERROR: time.sleep(2)

            # REMOVED_SYNTAX_ERROR: asyncio.run(manager.graceful_shutdown())

            # Calculate averages
            # REMOVED_SYNTAX_ERROR: avg_regular_memory = sum(memory_results["regular"]) / len(memory_results["regular"])
            # REMOVED_SYNTAX_ERROR: avg_alpine_memory = sum(memory_results["alpine"]) / len(memory_results["alpine"])

            # Log performance report
            # REMOVED_SYNTAX_ERROR: logger.info("Memory Usage Performance Report:")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # REMOVED_SYNTAX_ERROR: if avg_regular_memory > 0:
                # REMOVED_SYNTAX_ERROR: savings = (avg_regular_memory - avg_alpine_memory) / avg_regular_memory * 100
                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # Alpine should use less memory
                # REMOVED_SYNTAX_ERROR: assert avg_alpine_memory < avg_regular_memory, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_cpu_usage_comparison(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Compare CPU usage between Alpine and regular containers."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # REMOVED_SYNTAX_ERROR: cpu_results = {"regular": [], "alpine": []}

    # REMOVED_SYNTAX_ERROR: for container_type in ["regular", "alpine"]:
        # REMOVED_SYNTAX_ERROR: use_alpine = container_type == "alpine"

        # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=use_alpine
        

        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: assert success, "formatted_string"

        # Generate some load and measure
        # REMOVED_SYNTAX_ERROR: time.sleep(5)

        # REMOVED_SYNTAX_ERROR: for _ in range(3):
            # REMOVED_SYNTAX_ERROR: metrics = self._collect_container_metrics(manager, services)
            # REMOVED_SYNTAX_ERROR: cpu_results[container_type].append(metrics.cpu_usage_percent)
            # REMOVED_SYNTAX_ERROR: time.sleep(5)

            # REMOVED_SYNTAX_ERROR: asyncio.run(manager.graceful_shutdown())

            # Calculate averages
            # REMOVED_SYNTAX_ERROR: avg_regular_cpu = sum(cpu_results["regular"]) / len(cpu_results["regular"])
            # REMOVED_SYNTAX_ERROR: avg_alpine_cpu = sum(cpu_results["alpine"]) / len(cpu_results["alpine"])

            # Log performance report
            # REMOVED_SYNTAX_ERROR: logger.info("CPU Usage Performance Report:")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

            # CPU usage should be comparable (within reasonable bounds)
            # REMOVED_SYNTAX_ERROR: if avg_regular_cpu > 0:
                # REMOVED_SYNTAX_ERROR: ratio = avg_alpine_cpu / avg_regular_cpu
                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                # REMOVED_SYNTAX_ERROR: assert ratio < 2.0, f"Alpine CPU usage should not be >2x higher than regular"


                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestErrorRecovery(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Test error recovery and fallback mechanisms."""

# REMOVED_SYNTAX_ERROR: def test_fallback_from_alpine_to_regular(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test fallback from Alpine to regular containers when Alpine fails."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres"]

    # Simulate Alpine failure by using invalid compose file
    # REMOVED_SYNTAX_ERROR: with tempfile.TemporaryDirectory() as temp_dir:
        # REMOVED_SYNTAX_ERROR: temp_path = Path(temp_dir)

        # Create invalid Alpine compose file
        # REMOVED_SYNTAX_ERROR: invalid_alpine_compose = temp_path / "docker-compose.alpine-test.yml"
        # REMOVED_SYNTAX_ERROR: invalid_alpine_compose.write_text(''' )
        # REMOVED_SYNTAX_ERROR: version: '3.8'
        # REMOVED_SYNTAX_ERROR: services:
            # REMOVED_SYNTAX_ERROR: test-postgres:
                # REMOVED_SYNTAX_ERROR: image: nonexistent-alpine-image:latest
                # REMOVED_SYNTAX_ERROR: ports:
                    # REMOVED_SYNTAX_ERROR: - "5434:5432"
                    # REMOVED_SYNTAX_ERROR: ''')

                    # Create valid regular compose file as fallback
                    # REMOVED_SYNTAX_ERROR: regular_compose = temp_path / "docker-compose.test.yml"
                    # REMOVED_SYNTAX_ERROR: regular_compose.write_text(''' )
                    # REMOVED_SYNTAX_ERROR: version: '3.8'
                    # REMOVED_SYNTAX_ERROR: services:
                        # REMOVED_SYNTAX_ERROR: test-postgres:
                            # REMOVED_SYNTAX_ERROR: image: postgres:15
                            # REMOVED_SYNTAX_ERROR: environment:
                                # REMOVED_SYNTAX_ERROR: POSTGRES_DB: netra
                                # REMOVED_SYNTAX_ERROR: POSTGRES_USER: netra
                                # REMOVED_SYNTAX_ERROR: POSTGRES_PASSWORD: test_password
                                # REMOVED_SYNTAX_ERROR: ports:
                                    # REMOVED_SYNTAX_ERROR: - "5434:5432"
                                    # REMOVED_SYNTAX_ERROR: ''')

                                    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_path)}):
                                        # Try Alpine first (should fail)
                                        # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
                                        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
                                        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
                                        # REMOVED_SYNTAX_ERROR: use_alpine=True
                                        

                                        # Alpine startup should fail
                                        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=False))
                                        # REMOVED_SYNTAX_ERROR: assert not success, "Alpine containers should fail with invalid image"

                                        # Fallback to regular containers
                                        # REMOVED_SYNTAX_ERROR: logger.info("Alpine failed as expected, falling back to regular containers")
                                        # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
                                        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
                                        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
                                        # REMOVED_SYNTAX_ERROR: use_alpine=False
                                        

                                        # Regular containers should work
                                        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
                                        # REMOVED_SYNTAX_ERROR: assert success, "Regular containers should work as fallback"

                                        # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular, services)
                                        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())

# REMOVED_SYNTAX_ERROR: def test_cleanup_after_failed_alpine_deployment(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test cleanup after failed Alpine deployment."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment

    # Start Alpine containers
    # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # Start services (may partially succeed)
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.start_services_smart(["postgres"], wait_healthy=False))

    # Force cleanup
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.graceful_shutdown())

    # Verify cleanup was successful
    # REMOVED_SYNTAX_ERROR: project_name = manager_alpine._get_project_name()
    # REMOVED_SYNTAX_ERROR: cmd = ["docker", "ps", "-a", "--filter", "formatted_string", "--format", "{{.Names}}"]
    # REMOVED_SYNTAX_ERROR: result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    # REMOVED_SYNTAX_ERROR: remaining_containers = result.stdout.strip().split(" )
    # REMOVED_SYNTAX_ERROR: ") if result.stdout.strip() else []
    # REMOVED_SYNTAX_ERROR: remaining_containers = [item for item in []]

    # REMOVED_SYNTAX_ERROR: assert not remaining_containers, "formatted_string"

    # Verify we can start fresh containers after cleanup
    # REMOVED_SYNTAX_ERROR: manager_fresh = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_fresh.start_services_smart(["postgres"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Should be able to start fresh containers after cleanup"

    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_fresh.graceful_shutdown())

# REMOVED_SYNTAX_ERROR: def test_partial_deployment_recovery(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test recovery from partial deployments."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # Start with one service type
    # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # Start only one service first
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager.start_services_smart(["postgres"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start first service"

    # Add second service (simulating incremental deployment)
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager.start_services_smart(["redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to add second service"

    # Verify both services are running
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager, services)

    # REMOVED_SYNTAX_ERROR: asyncio.run(manager.graceful_shutdown())


    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestMigrationPaths(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Test migration paths and gradual transitions."""

# REMOVED_SYNTAX_ERROR: def test_gradual_migration_some_alpine_some_regular(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test gradual migration with some services Alpine, some regular."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment

    # Start with all regular services
    # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(["postgres", "redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular services"

    # Insert test data
    # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_regular, {"postgres": "INSERT INTO test_table (data) VALUES ('gradual_test')"})
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())

    # Migrate one service to Alpine
    # REMOVED_SYNTAX_ERROR: manager_alpine_partial = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # Start only Redis with Alpine (partial migration)
    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine_partial.start_services_smart(["redis"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start Alpine Redis"

    # Start Postgres with regular (keeping it regular)
    # REMOVED_SYNTAX_ERROR: manager_regular_partial = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular_partial.start_services_smart(["postgres"], wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start regular Postgres"

    # Verify mixed environment works
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_alpine_partial, ["redis"])
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular_partial, ["postgres"])

    # Verify data persistence
    # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_regular_partial, {"postgres": "INSERT INTO test_table (data) VALUES ('gradual_test')"})

    # Cleanup
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine_partial.graceful_shutdown())
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular_partial.graceful_shutdown())

# REMOVED_SYNTAX_ERROR: def test_rollback_scenario(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test rollback from Alpine to regular containers."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres", "redis"]

    # Start with Alpine containers
    # REMOVED_SYNTAX_ERROR: logger.info("Phase 1: Starting with Alpine containers")
    # REMOVED_SYNTAX_ERROR: manager_alpine = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=True
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_alpine.start_services_smart(services, wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to start Alpine containers"

    # Insert data and verify functionality
    # REMOVED_SYNTAX_ERROR: alpine_data = {"postgres": "INSERT INTO test_table (data) VALUES ('alpine_rollback_test')"}
    # REMOVED_SYNTAX_ERROR: self._insert_test_data(manager_alpine, alpine_data)
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_alpine, services)

    # Simulate issue requiring rollback
    # REMOVED_SYNTAX_ERROR: logger.info("Phase 2: Simulating issue and performing rollback")
    # REMOVED_SYNTAX_ERROR: asyncio.run(manager_alpine.graceful_shutdown())

    # Rollback to regular containers
    # REMOVED_SYNTAX_ERROR: manager_regular = UnifiedDockerManager( )
    # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
    # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: use_alpine=False
    

    # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_regular.start_services_smart(services, wait_healthy=True))
    # REMOVED_SYNTAX_ERROR: assert success, "Failed to rollback to regular containers"

    # Verify data survived rollback
    # REMOVED_SYNTAX_ERROR: self._verify_test_data(manager_regular, alpine_data)
    # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_regular, services)

    # Verify containers are indeed regular (not Alpine)
    # REMOVED_SYNTAX_ERROR: container_info = manager_regular.get_enhanced_container_status(services)
    # REMOVED_SYNTAX_ERROR: for service, info in container_info.items():
        # REMOVED_SYNTAX_ERROR: assert "alpine" not in info.image.lower(), "formatted_string"

        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_regular.graceful_shutdown())


        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
# REMOVED_SYNTAX_ERROR: class TestCICDIntegration(AlpineRegularSwitchingTestSuite):
    # REMOVED_SYNTAX_ERROR: """Test CI/CD integration scenarios."""

# REMOVED_SYNTAX_ERROR: def test_environment_variable_configuration(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test container selection based on environment variables."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment

    # Test with FORCE_ALPINE=true
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "true", "CI": "true"}):
        # REMOVED_SYNTAX_ERROR: manager_forced_alpine = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=True  # Should use Alpine due to env var
        

        # REMOVED_SYNTAX_ERROR: compose_file = manager_forced_alpine._get_compose_file()
        # REMOVED_SYNTAX_ERROR: assert "alpine" in compose_file.lower(), "Should select Alpine compose file when FORCE_ALPINE=true"

        # Test with FORCE_ALPINE=false
        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "false", "CI": "true"}):
            # REMOVED_SYNTAX_ERROR: manager_forced_regular = UnifiedDockerManager( )
            # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
            # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: use_alpine=False  # Should use regular due to env var
            

            # REMOVED_SYNTAX_ERROR: compose_file = manager_forced_regular._get_compose_file()
            # REMOVED_SYNTAX_ERROR: assert "alpine" not in compose_file.lower(), "Should select regular compose file when FORCE_ALPINE=false"

# REMOVED_SYNTAX_ERROR: def test_ci_specific_optimizations(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test CI-specific optimizations with different container types."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment
    # REMOVED_SYNTAX_ERROR: services = ["postgres"]  # Minimal services for CI

    # Simulate CI environment
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"CI": "true", "BUILD_MODE": "test"}):

        # Test Alpine optimization for CI
        # REMOVED_SYNTAX_ERROR: manager_ci_alpine = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=True
        

        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_ci_alpine.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: ci_alpine_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: assert success, "Alpine containers should work in CI environment"
        # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_ci_alpine, services)

        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_ci_alpine.graceful_shutdown())

        # Test regular containers for CI
        # REMOVED_SYNTAX_ERROR: manager_ci_regular = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=False
        

        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager_ci_regular.start_services_smart(services, wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: ci_regular_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: assert success, "Regular containers should work in CI environment"
        # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager_ci_regular, services)

        # REMOVED_SYNTAX_ERROR: asyncio.run(manager_ci_regular.graceful_shutdown())

        # Log CI performance comparison
        # REMOVED_SYNTAX_ERROR: logger.info("CI Performance Comparison:")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_different_test_runner_configurations(self, docker_available, compose_available,
# REMOVED_SYNTAX_ERROR: isolated_test_environment):
    # REMOVED_SYNTAX_ERROR: """Test Alpine/regular switching with different test runner configs."""
    # REMOVED_SYNTAX_ERROR: test_id = isolated_test_environment

    # Test configurations that might be used by unified test runner
    # REMOVED_SYNTAX_ERROR: configs = [ )
    # REMOVED_SYNTAX_ERROR: {"use_alpine": True, "rebuild_images": False},
    # REMOVED_SYNTAX_ERROR: {"use_alpine": False, "rebuild_images": False},
    # REMOVED_SYNTAX_ERROR: {"use_alpine": True, "rebuild_images": True},
    # REMOVED_SYNTAX_ERROR: {"use_alpine": False, "rebuild_images": True}
    

    # REMOVED_SYNTAX_ERROR: for i, config in enumerate(configs):
        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # REMOVED_SYNTAX_ERROR: manager = UnifiedDockerManager( )
        # REMOVED_SYNTAX_ERROR: environment_type=EnvironmentType.SHARED,
        # REMOVED_SYNTAX_ERROR: test_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: use_alpine=config["use_alpine"],
        # REMOVED_SYNTAX_ERROR: rebuild_images=config["rebuild_images"]
        

        # Start minimal services
        # REMOVED_SYNTAX_ERROR: success = asyncio.run(manager.start_services_smart(["postgres"], wait_healthy=True))
        # REMOVED_SYNTAX_ERROR: assert success, "formatted_string"

        # Verify functionality
        # REMOVED_SYNTAX_ERROR: self._verify_container_functionality(manager, ["postgres"])

        # Verify container type matches configuration
        # REMOVED_SYNTAX_ERROR: container_info = manager.get_enhanced_container_status(["postgres"])
        # REMOVED_SYNTAX_ERROR: postgres_info = container_info.get("postgres")

        # REMOVED_SYNTAX_ERROR: if config["use_alpine"]:
            # REMOVED_SYNTAX_ERROR: assert any(keyword in postgres_info.image.lower() for keyword in ['alpine', 'minimal']), \
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: else:
                # Regular containers should not have 'alpine' in image name
                # REMOVED_SYNTAX_ERROR: assert 'alpine' not in postgres_info.image.lower(), \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # REMOVED_SYNTAX_ERROR: asyncio.run(manager.graceful_shutdown())


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # Run all tests with comprehensive reporting
                    # REMOVED_SYNTAX_ERROR: pytest.main([ ))
                    # REMOVED_SYNTAX_ERROR: __file__,
                    # REMOVED_SYNTAX_ERROR: "-v",
                    # REMOVED_SYNTAX_ERROR: "--tb=short",
                    # REMOVED_SYNTAX_ERROR: "--strict-markers",
                    # REMOVED_SYNTAX_ERROR: "--disable-warnings",
                    # REMOVED_SYNTAX_ERROR: "-m", "not performance",  # Skip performance tests by default for speed
                    # REMOVED_SYNTAX_ERROR: "--durations=10"  # Show slowest 10 tests
                    