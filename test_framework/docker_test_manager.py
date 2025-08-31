"""
Docker-based Test Service Manager

This module provides a unified interface for managing Docker Compose services
during testing. It replaces direct dev_launcher usage with Docker Compose 
for improved isolation and consistency.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Use centralized environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return os.getenv(key, default)
        def set(self, key, value, source="test_framework"):
            os.environ[key] = value
    
    def get_env():
        return FallbackEnv()


class ServiceMode(Enum):
    """Service execution mode."""
    DOCKER = "docker"  # Use Docker Compose (default)
    LOCAL = "local"    # Use dev_launcher (legacy)
    MOCK = "mock"      # Use mocks only


class DockerTestManager:
    """
    Manages Docker Compose services for testing.
    
    This is the primary interface for test infrastructure setup,
    replacing direct dev_launcher usage with containerized services.
    """
    
    def __init__(self, mode: ServiceMode = ServiceMode.DOCKER):
        """
        Initialize the test service manager.
        
        Args:
            mode: Service execution mode (docker, local, or mock)
        """
        self.mode = mode
        self.env = get_env()
        self.project_root = Path.cwd()
        self.compose_file = self.project_root / "docker-compose.test.yml"
        self.project_name = "netra-test"
        self._running_services = set()
        self._docker_available = None
        
    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        if self._docker_available is not None:
            return self._docker_available
            
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._docker_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._docker_available = False
            
        return self._docker_available
    
    def get_effective_mode(self) -> ServiceMode:
        """
        Get the effective service mode based on environment and availability.
        
        Returns:
            ServiceMode: The mode that will actually be used
        """
        # Check environment override
        env_mode = self.env.get("TEST_SERVICE_MODE", "").lower()
        if env_mode == "mock":
            return ServiceMode.MOCK
        elif env_mode == "local":
            return ServiceMode.LOCAL
        elif env_mode == "docker":
            if not self.is_docker_available():
                print("[WARNING] Docker requested but not available, falling back to mock mode")
                return ServiceMode.MOCK
            return ServiceMode.DOCKER
            
        # Use configured mode with fallback
        if self.mode == ServiceMode.DOCKER and not self.is_docker_available():
            print("[WARNING] Docker not available, falling back to mock mode")
            return ServiceMode.MOCK
            
        return self.mode
    
    async def start_services(
        self,
        services: Optional[List[str]] = None,
        profiles: Optional[List[str]] = None,
        wait_healthy: bool = True,
        timeout: int = 60
    ) -> bool:
        """
        Start test services based on the configured mode.
        
        Args:
            services: Specific services to start (None = core services only)
            profiles: Docker Compose profiles to activate (e.g., ["e2e", "clickhouse"])
            wait_healthy: Whether to wait for services to be healthy
            timeout: Maximum time to wait for services (seconds)
            
        Returns:
            bool: True if services started successfully
        """
        effective_mode = self.get_effective_mode()
        
        if effective_mode == ServiceMode.MOCK:
            # Mock mode - no real services needed
            print("[TEST] Running in mock mode - no real services started")
            return True
            
        elif effective_mode == ServiceMode.LOCAL:
            # Legacy mode - use dev_launcher
            return await self._start_local_services(services)
            
        else:  # ServiceMode.DOCKER
            # Default mode - use Docker Compose
            return await self._start_docker_services(services, profiles, wait_healthy, timeout)
    
    async def _start_docker_services(
        self,
        services: Optional[List[str]],
        profiles: Optional[List[str]],
        wait_healthy: bool,
        timeout: int
    ) -> bool:
        """Start services using Docker Compose."""
        try:
            # Build command
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file),
                "-p", self.project_name
            ]
            
            # Add profiles if specified
            if profiles:
                for profile in profiles:
                    cmd.extend(["--profile", profile])
            
            # Check if services are already running before starting
            existing_check = subprocess.run(
                ["docker", "compose", "-f", str(self.compose_file), "-p", self.project_name, "ps", "--services", "--filter", "status=running"],
                capture_output=True,
                text=True
            )
            
            running_services = set(existing_check.stdout.strip().split('\n')) if existing_check.stdout.strip() else set()
            requested_services = set(services if services else ["postgres-test", "redis-test"])
            
            # Only start services that aren't already running
            services_to_start = requested_services - running_services
            
            if not services_to_start:
                print(f"[TEST] All requested services already running: {', '.join(requested_services)}")
                self._running_services.update(requested_services)
                return True
            
            cmd.extend(["up", "-d"])
            # Note: Removed --remove-orphans flag to prevent killing unrelated containers
            
            # Add specific services to start
            cmd.extend(list(services_to_start))
            
            print(f"[TEST] Starting Docker services: {' '.join(cmd)}")
            
            # Start services
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[ERROR] Failed to start Docker services: {result.stderr}")
                return False
            
            # Track running services
            self._running_services.update(services or ["postgres-test", "redis-test"])
            
            # Wait for services to be healthy
            if wait_healthy:
                return await self._wait_for_healthy(timeout)
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to start Docker services: {e}")
            return False
    
    async def _start_local_services(self, services: Optional[List[str]]) -> bool:
        """Start services using dev_launcher (legacy mode)."""
        try:
            from dev_launcher.service_startup import ServiceStartup
            
            print("[TEST] Starting local services via dev_launcher")
            
            # Configure services to start
            service_config = {
                "postgres": services is None or "postgres" in services,
                "redis": services is None or "redis" in services,
                "clickhouse": services and "clickhouse" in services,
                "backend": services and "backend" in services,
                "auth": services and "auth" in services,
                "frontend": False  # Never start frontend for tests
            }
            
            # Start services
            startup = ServiceStartup()
            success = await startup.start_services(service_config)
            
            if success:
                self._running_services.update(
                    [s for s, enabled in service_config.items() if enabled]
                )
                
            return success
            
        except ImportError:
            print("[ERROR] dev_launcher not available for local mode")
            return False
    
    async def _wait_for_healthy(self, timeout: int) -> bool:
        """Wait for Docker services to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check health status of all running services
            all_healthy = True
            
            for service in self._running_services:
                cmd = [
                    "docker", "inspect",
                    f"{self.project_name}-{service}",
                    "--format", "{{.State.Health.Status}}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                health_status = result.stdout.strip()
                
                if health_status not in ["healthy", ""]:  # Empty means no health check
                    if health_status == "unhealthy":
                        print(f"[ERROR] Service {service} is unhealthy")
                        return False
                    all_healthy = False
            
            if all_healthy:
                print("[TEST] All services are healthy")
                return True
            
            await asyncio.sleep(2)
        
        print(f"[ERROR] Services did not become healthy within {timeout} seconds")
        return False
    
    async def stop_services(self, cleanup_volumes: bool = False) -> bool:
        """
        Stop test services.
        
        Args:
            cleanup_volumes: Whether to remove volumes (data cleanup)
            
        Returns:
            bool: True if services stopped successfully
        """
        effective_mode = self.get_effective_mode()
        
        if effective_mode == ServiceMode.MOCK:
            return True
            
        elif effective_mode == ServiceMode.LOCAL:
            return await self._stop_local_services()
            
        else:  # ServiceMode.DOCKER
            return await self._stop_docker_services(cleanup_volumes)
    
    async def _stop_docker_services(self, cleanup_volumes: bool) -> bool:
        """Stop Docker Compose services."""
        try:
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file),
                "-p", self.project_name,
                "down"
            ]
            
            if cleanup_volumes:
                cmd.extend(["-v", "--remove-orphans"])
            
            print(f"[TEST] Stopping Docker services: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self._running_services.clear()
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"[ERROR] Failed to stop Docker services: {e}")
            return False
    
    async def _stop_local_services(self) -> bool:
        """Stop local services via dev_launcher."""
        try:
            from dev_launcher.service_startup import ServiceStartup
            
            print("[TEST] Stopping local services")
            
            startup = ServiceStartup()
            success = await startup.stop_services()
            
            if success:
                self._running_services.clear()
                
            return success
            
        except ImportError:
            print("[ERROR] dev_launcher not available")
            return False
    
    def get_service_url(self, service: str) -> str:
        """
        Get the URL for a test service.
        
        Args:
            service: Service name (postgres, redis, backend, auth, etc.)
            
        Returns:
            str: Service URL based on the current mode
        """
        effective_mode = self.get_effective_mode()
        
        # Define port mappings
        docker_ports = {
            "postgres": 5433,
            "redis": 6380,
            "clickhouse": 8124,
            "backend": 8001,
            "auth": 8082,
            "frontend": 3001
        }
        
        local_ports = {
            "postgres": 5432,
            "redis": 6379,
            "clickhouse": 8123,
            "backend": 8000,
            "auth": 8081,
            "frontend": 3000
        }
        
        if effective_mode == ServiceMode.DOCKER:
            port = docker_ports.get(service)
        else:
            port = local_ports.get(service)
        
        if not port:
            raise ValueError(f"Unknown service: {service}")
        
        # Special handling for database URLs
        if service == "postgres":
            if effective_mode == ServiceMode.DOCKER:
                return f"postgresql://test:test@localhost:{port}/netra_test"
            else:
                return f"postgresql://netra:netra123@localhost:{port}/netra_dev"
        elif service == "redis":
            return f"redis://localhost:{port}/0"
        else:
            return f"http://localhost:{port}"
    
    def configure_mock_environment(self):
        """Configure environment variables for mock/test services."""
        effective_mode = self.get_effective_mode()
        
        # Set test mode indicator
        self.env.set("TEST_SERVICE_MODE", effective_mode.value, "docker_test_manager")
        
        # Configure database URLs based on mode
        if effective_mode == ServiceMode.DOCKER:
            self.env.set("DATABASE_URL", self.get_service_url("postgres"), "docker_test_manager")
            self.env.set("REDIS_URL", self.get_service_url("redis"), "docker_test_manager")
            self.env.set("AUTH_SERVICE_URL", self.get_service_url("auth"), "docker_test_manager")
        elif effective_mode == ServiceMode.MOCK:
            # Use in-memory/mock configurations
            self.env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "docker_test_manager")
            self.env.set("TEST_DISABLE_REDIS", "true", "docker_test_manager")
            self.env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "docker_test_manager")
        
        # Common test environment settings
        self.env.set("TESTING", "1", "docker_test_manager")
        self.env.set("ENVIRONMENT", "testing", "docker_test_manager")
        self.env.set("LOG_LEVEL", "ERROR", "docker_test_manager")
    
    def configure_test_environment(self):
        """DEPRECATED: Use configure_mock_environment() instead.
        
        This method is maintained for backward compatibility only.
        """
        import warnings
        warnings.warn(
            "configure_test_environment() is deprecated. Use configure_mock_environment() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.configure_mock_environment()
    
    async def cleanup(self):
        """Clean up all test resources."""
        await self.stop_services(cleanup_volumes=True)


# Global instance for easy access
_test_manager: Optional[DockerTestManager] = None


def get_test_manager(mode: Optional[ServiceMode] = None) -> DockerTestManager:
    """
    Get or create the global test service manager.
    
    Args:
        mode: Service mode to use (uses environment default if not specified)
        
    Returns:
        DockerTestManager: The test service manager instance
    """
    global _test_manager
    
    if _test_manager is None or (mode and _test_manager.mode != mode):
        _test_manager = DockerTestManager(mode or ServiceMode.DOCKER)
        
    return _test_manager


async def setup_test_services(
    services: Optional[List[str]] = None,
    profiles: Optional[List[str]] = None,
    mode: Optional[ServiceMode] = None
) -> DockerTestManager:
    """
    Convenience function to set up test services.
    
    Args:
        services: Specific services to start
        profiles: Docker Compose profiles to activate
        mode: Service mode to use
        
    Returns:
        DockerTestManager: Configured and started test manager
    """
    manager = get_test_manager(mode)
    manager.configure_mock_environment()
    
    success = await manager.start_services(services, profiles)
    if not success:
        raise RuntimeError("Failed to start test services")
    
    return manager