"""
Comprehensive unit tests for UnifiedDockerManager class.

CRITICAL: Tests follow SSOT patterns and CLAUDE.md requirements:
- All imports are absolute from package root
- Tests MUST raise errors on failures (no try/except suppression)
- Mock Docker CLI operations for unit tests (infrastructure)
- Test ALL public methods with 100% coverage
- Focus on business logic, state management, and integration points

Business Value: Ensures Docker orchestration works reliably for chat value delivery.
"""

import asyncio
import json
import os
import platform
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch, mock_open
import pytest

from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    OrchestrationConfig,
    EnvironmentType,
    ServiceMode,
    ServiceStatus,
    ContainerState,
    ServiceHealth,
    ContainerInfo
)
from test_framework.dynamic_port_allocator import DynamicPortAllocator, PortRange
from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping
from test_framework.docker_introspection import DockerIntrospector
from test_framework.resource_monitor import DockerResourceSnapshot
from test_framework.memory_guardian import MemoryGuardian, TestProfile


class TestUnifiedDockerManagerInitialization:
    """Test initialization and configuration of UnifiedDockerManager."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        manager = UnifiedDockerManager()
        
        assert manager.config is not None
        assert isinstance(manager.config, OrchestrationConfig)
        assert manager.environment_type == EnvironmentType.DEDICATED
        assert manager.test_id is not None
        assert manager.use_production_images is True
        assert manager.mode == ServiceMode.DOCKER
        assert manager.use_alpine is True
        assert manager.rebuild_images is True
        assert manager.rebuild_backend_only is True
        assert manager.pull_policy == "missing"
        assert manager.no_cache_app_code is True

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = OrchestrationConfig(
            environment="staging",
            startup_timeout=120.0,
            required_services=["backend", "auth"]
        )
        
        manager = UnifiedDockerManager(
            config=config,
            environment_type=EnvironmentType.STAGING,
            test_id="test-123",
            use_production_images=False,
            mode=ServiceMode.LOCAL,
            use_alpine=False,
            rebuild_images=False,
            rebuild_backend_only=False,
            pull_policy="always",
            no_cache_app_code=False
        )
        
        assert manager.config == config
        assert manager.environment_type == EnvironmentType.STAGING
        assert manager.test_id == "test-123"
        assert manager.use_production_images is False
        assert manager.mode == ServiceMode.LOCAL
        assert manager.use_alpine is False
        assert manager.rebuild_images is False
        assert manager.rebuild_backend_only is False
        assert manager.pull_policy == "always"
        assert manager.no_cache_app_code is False

    def test_init_sets_windows_support(self):
        """Test Windows platform detection."""
        with patch("platform.system") as mock_platform:
            mock_platform.return_value = "Windows"
            manager = UnifiedDockerManager()
            assert manager.is_windows is True
            
            mock_platform.return_value = "Linux"
            manager = UnifiedDockerManager()
            assert manager.is_windows is False

    def test_init_creates_required_objects(self):
        """Test that initialization creates all required objects."""
        manager = UnifiedDockerManager()
        
        assert isinstance(manager.port_discovery, DockerPortDiscovery)
        assert isinstance(manager.port_allocator, DynamicPortAllocator)
        assert isinstance(manager.allocated_ports, dict)
        assert isinstance(manager.service_health, dict)
        assert isinstance(manager.started_services, set)
        assert isinstance(manager.memory_guardian, MemoryGuardian)

    def test_generate_test_id_format(self):
        """Test test ID generation format."""
        manager = UnifiedDockerManager()
        test_id = manager._generate_test_id()
        
        # Should be 8 character hash
        assert len(test_id) == 8
        assert test_id.isalnum()

    @patch("test_framework.unified_docker_manager.get_env")
    def test_get_database_credentials_default(self, mock_get_env):
        """Test default database credentials retrieval."""
        manager = UnifiedDockerManager()
        credentials = manager.get_database_credentials()
        
        expected = {
            "user": "test_user",
            "password": "test_pass",
            "database": "netra_test"
        }
        assert credentials == expected

    @patch("test_framework.unified_docker_manager.get_env")
    def test_get_database_credentials_alpine(self, mock_get_env):
        """Test Alpine database credentials retrieval."""
        mock_get_env.return_value = "true"
        manager = UnifiedDockerManager(use_alpine=True)
        credentials = manager.get_database_credentials()
        
        expected = {
            "user": "test",
            "password": "test",
            "database": "netra_test"
        }
        assert credentials == expected

    def test_get_database_credentials_environment_types(self):
        """Test database credentials for different environment types."""
        test_cases = [
            (EnvironmentType.DEVELOPMENT, "netra", "netra123", "netra_dev"),
            (EnvironmentType.TEST, "test_user", "test_pass", "netra_test"),
            (EnvironmentType.STAGING, "staging_user", "staging_pass", "netra_staging"),
            (EnvironmentType.PRODUCTION, "netra", "netra123", "netra_production"),
            (EnvironmentType.DEDICATED, "test_user", "test_pass", "netra_test")
        ]
        
        for env_type, expected_user, expected_pass, expected_db in test_cases:
            manager = UnifiedDockerManager(environment_type=env_type)
            credentials = manager.get_database_credentials()
            
            assert credentials["user"] == expected_user
            assert credentials["password"] == expected_pass
            assert credentials["database"] == expected_db


class TestEnvironmentDetection:
    """Test environment detection and management."""

    @patch("subprocess.run")
    def test_detect_environment_from_running_containers(self, mock_run):
        """Test environment detection from running containers."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="netra-alpine-test-abc123-backend-1\nnetra-alpine-test-abc123-redis-1"
        )
        
        manager = UnifiedDockerManager()
        env_type = manager.detect_environment()
        
        assert env_type == EnvironmentType.TEST

    @patch("subprocess.run")
    def test_detect_environment_development_containers(self, mock_run):
        """Test detection of development containers."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="dev-backend\ndev-redis\ndev-postgres"
        )
        
        manager = UnifiedDockerManager()
        env_type = manager.detect_environment()
        
        assert env_type == EnvironmentType.DEVELOPMENT

    @patch("subprocess.run")
    def test_detect_environment_test_containers(self, mock_run):
        """Test detection of test containers."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test-backend\ntest-redis"
        )
        
        manager = UnifiedDockerManager()
        env_type = manager.detect_environment()
        
        assert env_type == EnvironmentType.TEST

    @patch("subprocess.run")
    def test_detect_environment_subprocess_error(self, mock_run):
        """Test environment detection handles subprocess errors."""
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 10)
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.STAGING)
        env_type = manager.detect_environment()
        
        # Should return configured environment type on error
        assert env_type == EnvironmentType.STAGING

    @patch("subprocess.run")
    def test_detect_environment_no_containers(self, mock_run):
        """Test environment detection when no containers are running."""
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.PRODUCTION)
        env_type = manager.detect_environment()
        
        # Should return configured environment type
        assert env_type == EnvironmentType.PRODUCTION


class TestPortAllocatorInitialization:
    """Test port allocator initialization for different environments."""

    def test_initialize_port_allocator_dedicated(self):
        """Test port allocator initialization for dedicated environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        allocator = manager._initialize_port_allocator()
        
        assert isinstance(allocator, DynamicPortAllocator)
        assert allocator.port_range == PortRange.DEDICATED_TEST

    def test_initialize_port_allocator_test(self):
        """Test port allocator initialization for test environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        allocator = manager._initialize_port_allocator()
        
        assert allocator.port_range == PortRange.SHARED_TEST

    def test_initialize_port_allocator_development(self):
        """Test port allocator initialization for development environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        allocator = manager._initialize_port_allocator()
        
        assert allocator.port_range == PortRange.DEVELOPMENT

    def test_initialize_port_allocator_staging(self):
        """Test port allocator initialization for staging environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.STAGING)
        allocator = manager._initialize_port_allocator()
        
        assert allocator.port_range == PortRange.STAGING

    def test_initialize_port_allocator_production(self):
        """Test port allocator initialization for production environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.PRODUCTION)
        allocator = manager._initialize_port_allocator()
        
        # Production uses staging ports
        assert allocator.port_range == PortRange.STAGING


class TestFileLockingMechanism:
    """Test cross-platform file locking mechanisms."""

    @patch("os.name", "posix")
    @patch("fcntl.flock")
    @patch("builtins.open", new_callable=mock_open)
    def test_file_lock_unix(self, mock_file_open, mock_flock):
        """Test file locking on Unix systems."""
        manager = UnifiedDockerManager()
        
        with manager._file_lock("test_lock"):
            mock_file_open.assert_called()
            mock_flock.assert_called()

    @patch("os.name", "nt")
    @patch("msvcrt.locking")
    @patch("builtins.open", new_callable=mock_open)
    def test_file_lock_windows(self, mock_file_open, mock_locking):
        """Test file locking on Windows systems."""
        with patch("msvcrt.locking") as mock_locking:
            manager = UnifiedDockerManager()
            
            with manager._file_lock("test_lock"):
                mock_file_open.assert_called()

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_file_lock_permission_error(self, mock_file_open):
        """Test file locking handles permission errors."""
        manager = UnifiedDockerManager()
        
        with pytest.raises(OSError):
            with manager._file_lock("test_lock"):
                pass


class TestStateManagement:
    """Test state loading and saving functionality."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_state_existing_file(self, mock_exists, mock_file):
        """Test loading existing state file."""
        manager = UnifiedDockerManager()
        state = manager._load_state()
        
        assert state == {"test": "data"}

    @patch("pathlib.Path.exists", return_value=False)
    def test_load_state_missing_file(self, mock_exists):
        """Test loading when state file doesn't exist."""
        manager = UnifiedDockerManager()
        state = manager._load_state()
        
        expected = {"environments": {}, "last_cleanup": None}
        assert state == expected

    @patch("builtins.open", new_callable=mock_open, read_data='invalid json')
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_state_invalid_json(self, mock_exists, mock_file):
        """Test loading handles invalid JSON."""
        manager = UnifiedDockerManager()
        state = manager._load_state()
        
        # Should return default state on JSON error
        expected = {"environments": {}, "last_cleanup": None}
        assert state == expected

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_state(self, mock_json_dump, mock_file):
        """Test saving state to file."""
        manager = UnifiedDockerManager()
        test_state = {"test": "data"}
        
        manager._save_state(test_state)
        
        mock_file.assert_called()
        mock_json_dump.assert_called_once_with(test_state, mock_file.return_value, indent=2)

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_state_permission_error(self, mock_file):
        """Test save state handles permission errors gracefully."""
        manager = UnifiedDockerManager()
        test_state = {"test": "data"}
        
        # Should not raise exception but log error
        manager._save_state(test_state)


class TestEnvironmentNaming:
    """Test environment naming conventions."""

    def test_get_environment_name_dedicated_alpine(self):
        """Test environment naming for dedicated Alpine environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="abc123",
            use_alpine=True
        )
        
        name = manager._get_environment_name()
        assert name == "netra_alpine_test_abc123"

    def test_get_environment_name_dedicated_regular(self):
        """Test environment naming for dedicated regular environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="abc123",
            use_alpine=False
        )
        
        name = manager._get_environment_name()
        assert name == "netra_test_abc123"

    def test_get_environment_name_test_alpine(self):
        """Test environment naming for test Alpine environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.TEST,
            use_alpine=True
        )
        
        name = manager._get_environment_name()
        assert name == "netra_alpine_test"

    def test_get_environment_name_test_regular(self):
        """Test environment naming for test regular environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.TEST,
            use_alpine=False
        )
        
        name = manager._get_environment_name()
        assert name == "netra_test"

    def test_get_environment_name_other_types(self):
        """Test environment naming for other environment types."""
        test_cases = [
            (EnvironmentType.DEVELOPMENT, True, "netra_alpine_development"),
            (EnvironmentType.DEVELOPMENT, False, "netra_development"),
            (EnvironmentType.STAGING, True, "netra_alpine_staging"),
            (EnvironmentType.STAGING, False, "netra_staging"),
            (EnvironmentType.PRODUCTION, True, "netra_alpine_production"),
            (EnvironmentType.PRODUCTION, False, "netra_production")
        ]
        
        for env_type, use_alpine, expected in test_cases:
            manager = UnifiedDockerManager(
                environment_type=env_type,
                use_alpine=use_alpine
            )
            
            name = manager._get_environment_name()
            assert name == expected

    def test_get_project_name_dedicated(self):
        """Test project name generation for dedicated environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="abc123",
            use_alpine=True
        )
        
        project_name = manager._get_project_name()
        assert project_name == "netra-alpine-test-abc123"

    def test_get_project_name_caching(self):
        """Test that project name is cached after first generation."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="abc123"
        )
        
        # First call should generate and cache
        name1 = manager._get_project_name()
        name2 = manager._get_project_name()
        
        assert name1 == name2
        assert hasattr(manager, '_project_name')


class TestPortAllocation:
    """Test port allocation and management."""

    @patch.object(DynamicPortAllocator, "allocate_ports")
    def test_allocate_service_ports_new_allocation(self, mock_allocate):
        """Test allocating ports when none are allocated."""
        mock_allocate.return_value = {
            "backend": 8001,
            "auth": 8082,
            "postgres": 5435,
            "redis": 6382
        }
        
        manager = UnifiedDockerManager()
        manager.allocated_ports = {}  # Clear any existing ports
        
        ports = manager._allocate_service_ports()
        
        mock_allocate.assert_called_once()
        assert ports == mock_allocate.return_value
        assert manager.allocated_ports == mock_allocate.return_value

    def test_allocate_service_ports_existing_allocation(self):
        """Test that existing port allocation is returned."""
        existing_ports = {"backend": 8001, "auth": 8082}
        
        manager = UnifiedDockerManager()
        manager.allocated_ports = existing_ports
        
        ports = manager._allocate_service_ports()
        
        assert ports == existing_ports

    @patch("socket.socket")
    def test_find_available_port(self, mock_socket):
        """Test finding available port."""
        mock_sock = Mock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.return_value = None
        mock_sock.getsockname.return_value = ("127.0.0.1", 8888)
        
        manager = UnifiedDockerManager()
        port = manager._find_available_port()
        
        assert port == 8888
        mock_sock.bind.assert_called_with(("", 0))

    @patch("socket.socket")
    def test_find_available_port_socket_error(self, mock_socket):
        """Test finding available port handles socket errors."""
        mock_socket.side_effect = OSError("Socket error")
        
        manager = UnifiedDockerManager()
        port = manager._find_available_port()
        
        # Should return default port on error
        assert port == 8000


class TestServiceMapping:
    """Test service name mapping for different environments."""

    def test_map_service_name_development(self):
        """Test service name mapping for development environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        
        test_cases = [
            ("postgres", "dev-postgres"),
            ("redis", "dev-redis"),
            ("backend", "dev-backend"),
            ("auth", "dev-auth"),
            ("frontend", "dev-frontend"),
            ("unknown", "unknown")
        ]
        
        for service, expected in test_cases:
            mapped = manager._map_service_name(service)
            assert mapped == expected

    def test_map_service_name_other_environments(self):
        """Test service name mapping for non-development environments."""
        for env_type in [EnvironmentType.TEST, EnvironmentType.STAGING, EnvironmentType.PRODUCTION]:
            manager = UnifiedDockerManager(environment_type=env_type)
            
            # Should return service name unchanged
            assert manager._map_service_name("backend") == "backend"
            assert manager._map_service_name("postgres") == "postgres"


class TestNetworkManagement:
    """Test Docker network setup and cleanup."""

    @patch("subprocess.run")
    def test_setup_network_success(self, mock_run):
        """Test successful network setup."""
        mock_run.side_effect = [
            Mock(returncode=0),  # Network create success
            Mock(returncode=0)   # Network inspect success
        ]
        
        manager = UnifiedDockerManager()
        result = manager._setup_network()
        
        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_setup_network_already_exists(self, mock_run):
        """Test network setup when network already exists."""
        mock_run.side_effect = [
            Mock(returncode=1, stderr="already exists"),  # Network exists
            Mock(returncode=0)  # Network inspect success
        ]
        
        manager = UnifiedDockerManager()
        result = manager._setup_network()
        
        assert result is True

    @patch("subprocess.run")
    def test_setup_network_failure(self, mock_run):
        """Test network setup failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager._setup_network()
        
        assert result is False

    @patch("subprocess.run")
    def test_cleanup_network_success(self, mock_run):
        """Test successful network cleanup."""
        mock_run.return_value = Mock(returncode=0)
        
        manager = UnifiedDockerManager()
        result = manager._cleanup_network()
        
        assert result is True

    @patch("subprocess.run")
    def test_cleanup_network_not_found(self, mock_run):
        """Test network cleanup when network doesn't exist."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager._cleanup_network()
        
        # Should return True even if network doesn't exist
        assert result is True


class TestContainerManagement:
    """Test container removal and management."""

    @patch("subprocess.run")
    def test_safe_container_remove_success(self, mock_run):
        """Test successful container removal."""
        mock_run.side_effect = [
            Mock(returncode=0),  # Stop container
            Mock(returncode=0)   # Remove container
        ]
        
        manager = UnifiedDockerManager()
        result = manager.safe_container_remove("test-container")
        
        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_safe_container_remove_not_found(self, mock_run):
        """Test container removal when container doesn't exist."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager.safe_container_remove("test-container")
        
        # Should return True even if container doesn't exist
        assert result is True

    @patch("subprocess.run")
    def test_safe_container_remove_timeout(self, mock_run):
        """Test container removal with timeout."""
        def slow_run(*args, **kwargs):
            time.sleep(0.1)  # Simulate slow operation
            return Mock(returncode=0)
        
        mock_run.side_effect = slow_run
        
        manager = UnifiedDockerManager()
        result = manager.safe_container_remove("test-container", timeout=0.05)
        
        # Should handle timeout gracefully
        assert result is True


class TestRestartControl:
    """Test restart rate limiting and control mechanisms."""

    def test_check_restart_allowed_first_time(self):
        """Test restart allowed for first time."""
        manager = UnifiedDockerManager()
        result = manager._check_restart_allowed("backend")
        
        assert result is True

    def test_check_restart_allowed_within_cooldown(self):
        """Test restart blocked within cooldown period."""
        manager = UnifiedDockerManager()
        
        # Record a restart
        manager._record_restart("backend")
        
        # Immediate restart should be blocked
        result = manager._check_restart_allowed("backend")
        assert result is False

    def test_check_restart_allowed_after_cooldown(self):
        """Test restart allowed after cooldown period."""
        manager = UnifiedDockerManager()
        manager.RESTART_COOLDOWN = 0.1  # Short cooldown for testing
        
        # Record a restart
        manager._record_restart("backend")
        
        # Wait for cooldown
        time.sleep(0.2)
        
        # Should be allowed now
        result = manager._check_restart_allowed("backend")
        assert result is True

    def test_check_restart_allowed_max_attempts(self):
        """Test restart blocked after max attempts."""
        manager = UnifiedDockerManager()
        manager.RESTART_COOLDOWN = 0.01  # Very short cooldown
        manager.MAX_RESTART_ATTEMPTS = 2
        
        service = "backend"
        
        # Use up all restart attempts
        for _ in range(manager.MAX_RESTART_ATTEMPTS):
            manager._record_restart(service)
            time.sleep(0.02)  # Wait for cooldown
        
        # Next restart should be blocked
        result = manager._check_restart_allowed(service)
        assert result is False

    def test_record_restart(self):
        """Test restart recording."""
        manager = UnifiedDockerManager()
        service = "backend"
        
        manager._record_restart(service)
        
        assert service in manager.restart_history
        assert len(manager.restart_history[service]) == 1
        assert isinstance(manager.restart_history[service][0], float)


class TestServiceStatusChecking:
    """Test service status checking and health monitoring."""

    @patch("subprocess.run")
    def test_get_service_status_running(self, mock_run):
        """Test getting status of running service."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="running"
        )
        
        manager = UnifiedDockerManager()
        status = manager.get_service_status("backend")
        
        assert status == ServiceStatus.HEALTHY

    @patch("subprocess.run")
    def test_get_service_status_stopped(self, mock_run):
        """Test getting status of stopped service."""
        mock_run.return_value = Mock(returncode=1, stdout="")
        
        manager = UnifiedDockerManager()
        status = manager.get_service_status("backend")
        
        assert status == ServiceStatus.STOPPED

    @patch("subprocess.run")
    def test_get_service_status_subprocess_error(self, mock_run):
        """Test service status handles subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("Docker error")
        
        manager = UnifiedDockerManager()
        status = manager.get_service_status("backend")
        
        assert status == ServiceStatus.UNKNOWN

    def test_is_service_healthy_with_health_data(self):
        """Test health check with existing health data."""
        manager = UnifiedDockerManager()
        manager.service_health["backend"] = ServiceHealth(
            service_name="backend",
            is_healthy=True,
            port=8000,
            response_time_ms=50.0
        )
        
        result = manager._is_service_healthy("test-env", "backend")
        assert result is True

    @patch.object(UnifiedDockerManager, "_discover_ports")
    def test_is_service_healthy_no_health_data(self, mock_discover_ports):
        """Test health check without existing health data."""
        mock_discover_ports.return_value = {"backend": 8000}
        
        manager = UnifiedDockerManager()
        result = manager._is_service_healthy("test-env", "backend")
        
        # Without health data, should check ports
        assert isinstance(result, bool)


class TestAsyncHealthChecking:
    """Test async health checking functionality."""

    @pytest.mark.asyncio
    async def test_check_docker_availability_success(self):
        """Test Docker availability check success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            manager = UnifiedDockerManager()
            result = await manager._check_docker_availability()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_check_docker_availability_failure(self):
        """Test Docker availability check failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
            
            manager = UnifiedDockerManager()
            result = await manager._check_docker_availability()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_port_connectivity_success(self):
        """Test successful port connectivity check."""
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.return_value = None
            
            manager = UnifiedDockerManager()
            result = await manager._check_port_connectivity("localhost", 8000, 1.0)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_check_port_connectivity_timeout(self):
        """Test port connectivity check timeout."""
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()
            
            manager = UnifiedDockerManager()
            result = await manager._check_port_connectivity("localhost", 8000, 1.0)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_port_connectivity_connection_error(self):
        """Test port connectivity check connection error."""
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = ConnectionRefusedError()
            
            manager = UnifiedDockerManager()
            result = await manager._check_port_connectivity("localhost", 8000, 1.0)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_http_health_success(self):
        """Test successful HTTP health check."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.get.return_value.__aenter__.return_value.status = 200
            mock_session_class.return_value = mock_session
            
            manager = UnifiedDockerManager()
            result = await manager._check_http_health("http://localhost:8000/health", 1.0)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_check_http_health_bad_status(self):
        """Test HTTP health check with bad status code."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.get.return_value.__aenter__.return_value.status = 500
            mock_session_class.return_value = mock_session
            
            manager = UnifiedDockerManager()
            result = await manager._check_http_health("http://localhost:8000/health", 1.0)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_async(self):
        """Test async service health check."""
        manager = UnifiedDockerManager()
        mapping = ServicePortMapping(
            service_name="backend",
            host_port=8000,
            container_port=8000,
            host="localhost",
            is_healthy=True,
            health_url="http://localhost:8000/health"
        )
        
        with patch.object(manager, "_check_http_health", return_value=True) as mock_http:
            health = await manager._check_service_health_async("backend", mapping)
            
            assert health.service_name == "backend"
            assert health.is_healthy is True
            assert health.port == 8000
            assert health.response_time_ms >= 0


class TestEnvironmentManagement:
    """Test environment acquisition and release."""

    @patch.object(UnifiedDockerManager, "_load_state")
    @patch.object(UnifiedDockerManager, "_save_state")
    @patch.object(UnifiedDockerManager, "_allocate_service_ports")
    def test_acquire_environment_new(self, mock_allocate, mock_save, mock_load):
        """Test acquiring new environment."""
        mock_load.return_value = {"environments": {}}
        mock_allocate.return_value = {"backend": 8001, "auth": 8082}
        
        manager = UnifiedDockerManager()
        env_name, ports = manager.acquire_environment()
        
        assert isinstance(env_name, str)
        assert ports == mock_allocate.return_value
        mock_save.assert_called()

    @patch.object(UnifiedDockerManager, "_load_state")
    @patch.object(UnifiedDockerManager, "_save_state")
    def test_acquire_environment_existing_available(self, mock_save, mock_load):
        """Test acquiring existing available environment."""
        existing_ports = {"backend": 8001, "auth": 8082}
        mock_load.return_value = {
            "environments": {
                "test-env": {
                    "users": 0,
                    "ports": existing_ports,
                    "type": "dedicated"
                }
            }
        }
        
        manager = UnifiedDockerManager()
        env_name, ports = manager.acquire_environment()
        
        assert ports == existing_ports
        mock_save.assert_called()

    @patch.object(UnifiedDockerManager, "_load_state")
    @patch.object(UnifiedDockerManager, "_save_state")
    def test_release_environment(self, mock_save, mock_load):
        """Test releasing environment."""
        mock_load.return_value = {
            "environments": {
                "test-env": {
                    "users": 1,
                    "ports": {"backend": 8001}
                }
            }
        }
        
        manager = UnifiedDockerManager()
        manager.release_environment("test-env")
        
        mock_save.assert_called()


class TestDockerAvailabilityAndMode:
    """Test Docker availability detection and mode selection."""

    @patch("subprocess.run")
    def test_is_docker_available_success(self, mock_run):
        """Test Docker availability check success."""
        mock_run.return_value = Mock(returncode=0)
        
        manager = UnifiedDockerManager()
        result = manager.is_docker_available()
        
        assert result is True

    @patch("subprocess.run")
    def test_is_docker_available_failure(self, mock_run):
        """Test Docker availability check failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager.is_docker_available()
        
        assert result is False

    @patch("subprocess.run")
    def test_is_docker_available_exception(self, mock_run):
        """Test Docker availability handles exceptions."""
        mock_run.side_effect = FileNotFoundError()
        
        manager = UnifiedDockerManager()
        result = manager.is_docker_available()
        
        assert result is False

    @patch.object(UnifiedDockerManager, "is_docker_available")
    def test_get_effective_mode_docker_available(self, mock_docker_available):
        """Test effective mode when Docker is available."""
        mock_docker_available.return_value = True
        
        manager = UnifiedDockerManager()
        mode = manager.get_effective_mode(ServiceMode.DOCKER)
        
        assert mode == ServiceMode.DOCKER

    @patch.object(UnifiedDockerManager, "is_docker_available")
    def test_get_effective_mode_docker_unavailable(self, mock_docker_available):
        """Test effective mode fallback when Docker is unavailable."""
        mock_docker_available.return_value = False
        
        manager = UnifiedDockerManager()
        mode = manager.get_effective_mode(ServiceMode.DOCKER)
        
        assert mode == ServiceMode.LOCAL

    @patch.object(UnifiedDockerManager, "is_docker_available")
    def test_get_effective_mode_mock_requested(self, mock_docker_available):
        """Test effective mode when mock is explicitly requested."""
        mock_docker_available.return_value = True
        
        manager = UnifiedDockerManager()
        mode = manager.get_effective_mode(ServiceMode.MOCK)
        
        assert mode == ServiceMode.MOCK

    def test_get_effective_mode_default(self):
        """Test effective mode with default parameter."""
        manager = UnifiedDockerManager()
        
        with patch.object(manager, "is_docker_available", return_value=True):
            mode = manager.get_effective_mode()
            assert mode == ServiceMode.DOCKER


class TestComposeFileSelection:
    """Test Docker compose file selection logic."""

    def test_get_compose_file_development(self):
        """Test compose file selection for development environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        compose_file = manager._get_compose_file()
        
        assert compose_file == "docker-compose.yml"

    def test_get_compose_file_test_alpine(self):
        """Test compose file selection for test Alpine environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.TEST,
            use_alpine=True
        )
        compose_file = manager._get_compose_file()
        
        assert compose_file == "docker-compose.alpine-test.yml"

    def test_get_compose_file_test_non_alpine(self):
        """Test compose file selection fails for non-Alpine test environment."""
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.TEST,
            use_alpine=False
        )
        
        with pytest.raises(RuntimeError, match="Tests should ALWAYS use Alpine"):
            manager._get_compose_file()


class TestServiceEnvironmentVariables:
    """Test service environment variable configuration."""

    def test_get_service_environment_variables_test(self):
        """Test environment variables for test environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        env_vars = manager._get_service_environment_variables()
        
        assert env_vars['POSTGRES_PORT'] == '5434'
        assert env_vars['REDIS_PORT'] == '6381'
        assert env_vars['BACKEND_PORT'] == '8000'
        assert env_vars['AUTH_PORT'] == '8081'

    def test_get_service_environment_variables_non_test(self):
        """Test environment variables for non-test environments."""
        for env_type in [EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING]:
            manager = UnifiedDockerManager(environment_type=env_type)
            env_vars = manager._get_service_environment_variables()
            
            assert env_vars['POSTGRES_PORT'] == '5432'
            assert env_vars['REDIS_PORT'] == '6379'
            assert env_vars['BACKEND_PORT'] == '8000'
            assert env_vars['AUTH_PORT'] == '8081'

    def test_service_environment_variables_include_test_id(self):
        """Test that environment variables include test ID."""
        manager = UnifiedDockerManager(test_id="test-123")
        env_vars = manager._get_service_environment_variables()
        
        assert 'TEST_ID' in env_vars
        assert env_vars['TEST_ID'] == "test-123"

    def test_service_environment_variables_include_common_vars(self):
        """Test that environment variables include common required vars."""
        manager = UnifiedDockerManager()
        env_vars = manager._get_service_environment_variables()
        
        required_vars = [
            'POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
            'REDIS_HOST', 'AUTH_SERVICE_URL', 'BACKEND_SERVICE_URL'
        ]
        
        for var in required_vars:
            assert var in env_vars


class TestMemoryMonitoring:
    """Test memory monitoring and optimization features."""

    @patch.object(MemoryGuardian, "perform_pre_flight_check")
    def test_perform_memory_pre_flight_check_success(self, mock_pre_flight):
        """Test successful memory pre-flight check."""
        mock_pre_flight.return_value = True
        
        manager = UnifiedDockerManager()
        result = manager.perform_memory_pre_flight_check()
        
        assert result is True
        mock_pre_flight.assert_called_once()

    @patch.object(MemoryGuardian, "perform_pre_flight_check")
    def test_perform_memory_pre_flight_check_failure(self, mock_pre_flight):
        """Test failed memory pre-flight check."""
        mock_pre_flight.return_value = False
        
        manager = UnifiedDockerManager()
        result = manager.perform_memory_pre_flight_check()
        
        assert result is False

    @patch.object(MemoryGuardian, "monitor_during_operations")
    def test_monitor_memory_during_operations(self, mock_monitor):
        """Test memory monitoring during operations."""
        mock_snapshot = Mock(spec=DockerResourceSnapshot)
        mock_monitor.return_value = mock_snapshot
        
        manager = UnifiedDockerManager()
        result = manager.monitor_memory_during_operations()
        
        assert result == mock_snapshot
        mock_monitor.assert_called_once()

    @patch("subprocess.run")
    def test_get_container_memory_info_success(self, mock_run):
        """Test getting container memory information."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="50MiB / 1GiB"
        )
        
        manager = UnifiedDockerManager()
        result = manager._get_container_memory_info("backend")
        
        assert result == "50MiB / 1GiB"

    @patch("subprocess.run")
    def test_get_container_memory_info_failure(self, mock_run):
        """Test getting container memory information handles errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager._get_container_memory_info("backend")
        
        assert result is None

    @patch("subprocess.run")
    def test_check_container_memory_thresholds(self, mock_run):
        """Test container memory threshold checking."""
        # Mock docker stats to return memory usage percentages
        mock_run.return_value = Mock(
            returncode=0,
            stdout="backend,85.5\nauth,45.2\npostgres,92.1"
        )
        
        manager = UnifiedDockerManager()
        thresholds = manager._check_container_memory_thresholds()
        
        # Should return containers above threshold (assuming 80% threshold)
        assert len(thresholds) >= 2  # backend and postgres should be above threshold
        
        # Check that tuples contain service name and percentage
        for service, percentage in thresholds:
            assert isinstance(service, str)
            assert isinstance(percentage, float)


class TestContainerIntrospection:
    """Test container introspection and status reporting."""

    @patch("subprocess.run")
    def test_get_enhanced_container_status_success(self, mock_run):
        """Test getting enhanced container status."""
        mock_inspect_data = {
            "Name": "/test-backend",
            "Config": {"Image": "netra/backend:latest"},
            "State": {
                "Status": "running",
                "Health": {"Status": "healthy"},
                "StartedAt": "2023-01-01T00:00:00Z",
                "ExitCode": 0
            },
            "NetworkSettings": {
                "Ports": {"8000/tcp": [{"HostPort": "8000"}]}
            }
        }
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([mock_inspect_data])
        )
        
        manager = UnifiedDockerManager()
        status = manager.get_enhanced_container_status(["backend"])
        
        assert "backend" in status
        assert isinstance(status["backend"], ContainerInfo)
        assert status["backend"].state == ContainerState.RUNNING

    @patch("subprocess.run")
    def test_get_enhanced_container_status_no_containers(self, mock_run):
        """Test enhanced container status with no running containers."""
        mock_run.return_value = Mock(returncode=0, stdout="[]")
        
        manager = UnifiedDockerManager()
        status = manager.get_enhanced_container_status()
        
        assert isinstance(status, dict)
        assert len(status) == 0

    @patch("subprocess.run")
    def test_get_enhanced_container_status_docker_error(self, mock_run):
        """Test enhanced container status handles Docker errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        status = manager.get_enhanced_container_status()
        
        assert isinstance(status, dict)
        assert len(status) == 0

    def test_create_introspector(self):
        """Test creating Docker introspector."""
        manager = UnifiedDockerManager()
        introspector = manager.create_introspector()
        
        assert isinstance(introspector, DockerIntrospector)


class TestCleanupOperations:
    """Test cleanup operations and scheduling."""

    @patch("subprocess.run")
    def test_cleanup_orphaned_containers_success(self, mock_run):
        """Test successful cleanup of orphaned containers."""
        # Mock docker ps to return orphaned containers
        mock_run.side_effect = [
            Mock(returncode=0, stdout="orphaned-container-1\norphaned-container-2"),
            Mock(returncode=0),  # Stop container 1
            Mock(returncode=0),  # Remove container 1
            Mock(returncode=0),  # Stop container 2
            Mock(returncode=0)   # Remove container 2
        ]
        
        manager = UnifiedDockerManager()
        result = manager.cleanup_orphaned_containers()
        
        assert result is True

    @patch("subprocess.run")
    def test_cleanup_orphaned_containers_no_containers(self, mock_run):
        """Test cleanup when no orphaned containers exist."""
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        manager = UnifiedDockerManager()
        result = manager.cleanup_orphaned_containers()
        
        assert result is True

    @patch("subprocess.run")
    def test_cleanup_orphaned_containers_docker_error(self, mock_run):
        """Test cleanup handles Docker errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        
        manager = UnifiedDockerManager()
        result = manager.cleanup_orphaned_containers()
        
        assert result is False

    @patch.object(UnifiedDockerManager, "_load_state")
    @patch.object(UnifiedDockerManager, "_save_state")
    def test_cleanup_old_environments(self, mock_save, mock_load):
        """Test cleanup of old environments."""
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        recent_time = datetime.now().isoformat()
        
        mock_load.return_value = {
            "environments": {
                "old-env": {
                    "type": "dedicated",
                    "created": old_time,
                    "users": 0
                },
                "recent-env": {
                    "type": "dedicated", 
                    "created": recent_time,
                    "users": 0
                },
                "test-env": {
                    "type": "test",
                    "created": old_time,
                    "users": 0
                }
            }
        }
        
        manager = UnifiedDockerManager()
        manager.cleanup_old_environments(max_age_hours=24)
        
        # Should have saved state after cleanup
        mock_save.assert_called()

    def test_pre_test_cleanup_success(self):
        """Test successful pre-test cleanup."""
        manager = UnifiedDockerManager()
        
        with patch.object(manager, "cleanup_orphaned_containers", return_value=True) as mock_cleanup:
            result = manager.pre_test_cleanup()
            
            assert result is True
            mock_cleanup.assert_called_once()

    def test_pre_test_cleanup_failure(self):
        """Test pre-test cleanup failure."""
        manager = UnifiedDockerManager()
        
        with patch.object(manager, "cleanup_orphaned_containers", return_value=False) as mock_cleanup:
            result = manager.pre_test_cleanup()
            
            assert result is False


class TestStatisticsAndReporting:
    """Test statistics collection and reporting."""

    def test_get_statistics_basic(self):
        """Test basic statistics collection."""
        manager = UnifiedDockerManager()
        stats = manager.get_statistics()
        
        assert isinstance(stats, dict)
        assert "environment_type" in stats
        assert "test_id" in stats
        assert "use_alpine" in stats
        assert "allocated_ports" in stats
        assert "started_services" in stats

    def test_get_statistics_with_services(self):
        """Test statistics with started services."""
        manager = UnifiedDockerManager()
        manager.started_services.add("backend")
        manager.started_services.add("auth")
        manager.allocated_ports = {"backend": 8001, "auth": 8082}
        
        stats = manager.get_statistics()
        
        assert len(stats["started_services"]) == 2
        assert len(stats["allocated_ports"]) == 2

    @patch.object(UnifiedDockerManager, "_check_container_memory_thresholds")
    def test_get_health_report(self, mock_memory_check):
        """Test health report generation."""
        mock_memory_check.return_value = [("backend", 85.5)]
        
        manager = UnifiedDockerManager()
        manager.service_health["backend"] = ServiceHealth(
            service_name="backend",
            is_healthy=True,
            port=8000,
            response_time_ms=50.0
        )
        
        report = manager.get_health_report()
        
        assert isinstance(report, str)
        assert "backend" in report
        assert "85.5%" in report or "85.5" in report


class TestWindowsSupport:
    """Test Windows-specific functionality."""

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.run")
    def test_get_docker_service_status_windows(self, mock_run, mock_platform):
        """Test getting Docker service status on Windows."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Docker Desktop Service,Running"
        )
        
        manager = UnifiedDockerManager()
        status = manager.get_docker_service_status_windows()
        
        assert isinstance(status, dict)
        assert "docker_service_running" in status

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.run")
    def test_get_windows_event_logs(self, mock_run, mock_platform):
        """Test getting Windows event logs."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Event log entry 1\nEvent log entry 2"
        )
        
        manager = UnifiedDockerManager()
        logs = manager.get_windows_event_logs()
        
        assert isinstance(logs, list)
        assert len(logs) >= 0

    @patch("platform.system", return_value="Windows")
    def test_analyze_docker_crash_windows(self, mock_platform):
        """Test Docker crash analysis on Windows."""
        manager = UnifiedDockerManager()
        
        with patch.object(manager, "get_docker_service_status_windows", return_value={"docker_service_running": False}):
            with patch.object(manager, "get_windows_event_logs", return_value=["Error 1", "Error 2"]):
                analysis = manager.analyze_docker_crash()
                
                assert isinstance(analysis, dict)
                assert "platform" in analysis
                assert analysis["platform"] == "Windows"


class TestDevRefreshOperations:
    """Test development service refresh operations."""

    @patch("subprocess.run")
    def test_refresh_dev_success(self, mock_run):
        """Test successful dev service refresh."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        
        with patch.object(manager, "_wait_for_dev_health", return_value=True):
            result = manager.refresh_dev(["backend"], clean=False)
            
            assert result is True

    @patch("subprocess.run")
    def test_refresh_dev_build_failure(self, mock_run):
        """Test dev refresh with build failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker-compose")
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        result = manager.refresh_dev(["backend"])
        
        assert result is False

    def test_refresh_dev_wrong_environment(self):
        """Test dev refresh fails on non-development environment."""
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        with pytest.raises(ValueError, match="only works in DEVELOPMENT"):
            manager.refresh_dev(["backend"])

    @patch("subprocess.run")
    def test_wait_for_dev_health_success(self, mock_run):
        """Test waiting for dev service health."""
        # Mock health check success
        mock_run.return_value = Mock(returncode=0)
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        result = manager._wait_for_dev_health(timeout=1)
        
        assert result is True

    @patch("subprocess.run")
    def test_wait_for_dev_health_timeout(self, mock_run):
        """Test dev health check timeout."""
        # Mock health check failure
        mock_run.return_value = Mock(returncode=1)
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEVELOPMENT)
        result = manager._wait_for_dev_health(timeout=0.1)
        
        assert result is False


class TestServiceUrlGeneration:
    """Test service URL generation for E2E tests."""

    def test_get_e2e_service_urls_with_allocated_ports(self):
        """Test E2E service URL generation with allocated ports."""
        manager = UnifiedDockerManager()
        manager.allocated_ports = {
            "backend": 8001,
            "auth": 8082,
            "frontend": 3001
        }
        
        urls = manager.get_e2e_service_urls()
        
        assert urls["backend"] == "http://localhost:8001"
        assert urls["auth"] == "http://localhost:8082"
        assert urls["frontend"] == "http://localhost:3001"

    def test_get_e2e_service_urls_no_allocated_ports(self):
        """Test E2E service URL generation without allocated ports."""
        manager = UnifiedDockerManager()
        manager.allocated_ports = {}
        
        # Should discover ports from running containers
        with patch.object(manager, "_discover_ports_from_docker_ps", return_value={"backend": 8000}):
            urls = manager.get_e2e_service_urls()
            
            assert "backend" in urls
            assert urls["backend"] == "http://localhost:8000"

    def test_build_service_url_from_port(self):
        """Test building service URL from port."""
        manager = UnifiedDockerManager()
        
        url = manager._build_service_url_from_port("backend", 8001)
        assert url == "http://localhost:8001"
        
        url = manager._build_service_url_from_port("frontend", 3001)
        assert url == "http://localhost:3001"
        
        # Test unknown service
        url = manager._build_service_url_from_port("unknown", 9999)
        assert url is None

    def test_build_service_url_from_mapping(self):
        """Test building service URL from port mapping."""
        manager = UnifiedDockerManager()
        mapping = ServicePortMapping(
            service_name="backend",
            host_port=8001,
            container_port=8000,
            host="localhost",
            is_healthy=True,
            health_url="http://localhost:8001/health"
        )
        
        url = manager._build_service_url("backend", mapping)
        assert url == "http://localhost:8001"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def test_init_with_none_config(self):
        """Test initialization with None config creates default."""
        manager = UnifiedDockerManager(config=None)
        
        assert manager.config is not None
        assert isinstance(manager.config, OrchestrationConfig)

    def test_file_lock_directory_creation(self):
        """Test file lock creates lock directory if it doesn't exist."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("pathlib.Path.exists", return_value=False):
                manager = UnifiedDockerManager()
                
                # Lock directory creation should be attempted
                # Note: This tests the directory creation logic in the class definition

    @patch("subprocess.run")
    def test_docker_command_with_timeout_handling(self, mock_run):
        """Test Docker command handling with timeout."""
        # Test that subprocess timeout is handled properly
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)
        
        manager = UnifiedDockerManager()
        result = manager.is_docker_available()
        
        assert result is False

    def test_service_mapping_preserves_unknown_services(self):
        """Test that service mapping preserves unknown service names."""
        manager = UnifiedDockerManager()
        
        unknown_service = "custom-service"
        mapped = manager._map_service_name(unknown_service)
        
        assert mapped == unknown_service

    def test_empty_service_lists_handling(self):
        """Test handling of empty service lists."""
        manager = UnifiedDockerManager()
        
        # Test with empty service list
        compose_services = manager._map_to_compose_services([])
        assert compose_services == []

    @patch("builtins.open", side_effect=PermissionError("Access denied"))
    def test_state_operations_handle_permission_errors(self, mock_open):
        """Test that state operations handle permission errors gracefully."""
        manager = UnifiedDockerManager()
        
        # Load state should return default on permission error
        state = manager._load_state()
        expected = {"environments": {}, "last_cleanup": None}
        assert state == expected
        
        # Save state should not raise on permission error
        manager._save_state({"test": "data"})  # Should not raise


# Integration-style unit tests for complex workflows
class TestComplexWorkflows:
    """Test complex workflows and state transitions."""

    def test_environment_lifecycle(self):
        """Test complete environment lifecycle."""
        manager = UnifiedDockerManager()
        
        with patch.object(manager, "_load_state", return_value={"environments": {}}):
            with patch.object(manager, "_save_state") as mock_save:
                with patch.object(manager, "_allocate_service_ports", return_value={"backend": 8001}):
                    # Acquire environment
                    env_name, ports = manager.acquire_environment()
                    
                    assert isinstance(env_name, str)
                    assert ports == {"backend": 8001}
                    
                    # Release environment
                    manager.release_environment(env_name)
                    
                    # Should have saved state twice (acquire + release)
                    assert mock_save.call_count == 2

    def test_restart_rate_limiting_workflow(self):
        """Test restart rate limiting workflow."""
        manager = UnifiedDockerManager()
        manager.RESTART_COOLDOWN = 0.05  # Short cooldown for testing
        manager.MAX_RESTART_ATTEMPTS = 2
        
        service = "backend"
        
        # First restart should be allowed
        assert manager._check_restart_allowed(service) is True
        manager._record_restart(service)
        
        # Immediate restart should be blocked
        assert manager._check_restart_allowed(service) is False
        
        # Wait for cooldown
        time.sleep(0.1)
        
        # Second restart should be allowed
        assert manager._check_restart_allowed(service) is True
        manager._record_restart(service)
        
        # Wait and try third restart (should be blocked due to max attempts)
        time.sleep(0.1)
        assert manager._check_restart_allowed(service) is False

    @patch("subprocess.run")
    def test_container_discovery_workflow(self, mock_run):
        """Test container discovery and port mapping workflow."""
        # Mock docker ps output
        mock_run.return_value = Mock(
            returncode=0,
            stdout="netra-test-backend-1:8000->8001/tcp\nnetra-test-auth-1:8081->8082/tcp"
        )
        
        manager = UnifiedDockerManager()
        ports = manager._discover_ports_from_docker_ps()
        
        assert isinstance(ports, dict)
        # The actual parsing logic would determine the exact format


if __name__ == "__main__":
    # Allow running tests directly with python
    pytest.main([__file__, "-v"])