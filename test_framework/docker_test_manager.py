"""
Docker-based Test Service Manager - DEPRECATED

This module is deprecated and redirects to the SSOT DockerTestUtility.
All Docker testing should use test_framework.ssot.docker.DockerTestUtility.

CRITICAL: This class is only kept for backward compatibility.
New code must use DockerTestUtility directly.
"""

import asyncio
import logging
import warnings
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# SSOT imports - all Docker operations go through DockerTestUtility
from test_framework.ssot.docker import (
    DockerTestUtility,
    DockerTestEnvironmentType,
    create_docker_test_utility
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Compatibility enum mapping
class ServiceMode(Enum):
    """Service execution mode - DEPRECATED. Use DockerTestEnvironmentType."""
    DOCKER = "docker"  # Use Docker Compose (default)
    LOCAL = "local"    # Use dev_launcher (legacy)
    MOCK = "mock"      # Use mocks only
    
    def to_environment_type(self) -> DockerTestEnvironmentType:
        """Convert to SSOT DockerTestEnvironmentType."""
        if self == ServiceMode.DOCKER:
            return DockerTestEnvironmentType.SHARED
        elif self == ServiceMode.LOCAL:
            return DockerTestEnvironmentType.ISOLATED
        else:  # MOCK
            return DockerTestEnvironmentType.ISOLATED


class DockerTestManager:
    """
    DEPRECATED: Manages Docker Compose services for testing.
    
    This class now redirects to the SSOT DockerTestUtility.
    Use test_framework.ssot.docker.DockerTestUtility directly for new code.
    
    This implementation provides backward compatibility by delegating all
    operations to the SSOT DockerTestUtility.
    """
    
    def __init__(self, mode: ServiceMode = ServiceMode.DOCKER):
        """
        Initialize the DEPRECATED test service manager.
        
        Args:
            mode: Service execution mode (docker, local, or mock)
        """
        # Issue deprecation warning
        warnings.warn(
            "DockerTestManager is deprecated. Use test_framework.ssot.docker.DockerTestUtility directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.mode = mode
        self.env = get_env()
        self.project_root = Path.cwd()
        self.compose_file = self.project_root / "docker-compose.test.yml"
        self.project_name = "netra-test"
        self._running_services = set()
        self._docker_available = None
        
        # Create SSOT DockerTestUtility instance
        environment_type = mode.to_environment_type()
        self._docker_utility = create_docker_test_utility(environment_type)
        
        logger.warning(
            f"DockerTestManager is deprecated. Redirecting to DockerTestUtility with {environment_type.value} environment."
        )
        
    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system - DEPRECATED."""
        if self._docker_available is None:
            # Use SSOT UnifiedDockerManager for Docker availability check
            try:
                from test_framework.unified_docker_manager import UnifiedDockerManager
                manager = UnifiedDockerManager()
                
                # This would typically be async, but maintaining sync interface for compatibility
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self._docker_available = loop.run_until_complete(manager.is_docker_available())
            except Exception as e:
                logger.error(f"Error checking Docker availability: {e}")
                self._docker_available = False
                
        return self._docker_available
    
    def get_effective_mode(self) -> ServiceMode:
        """
        Get the effective service mode based on environment and availability - DEPRECATED.
        
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
                logger.warning("Docker requested but not available, falling back to mock mode")
                return ServiceMode.MOCK
            return ServiceMode.DOCKER
            
        # Use configured mode with fallback
        if self.mode == ServiceMode.DOCKER and not self.is_docker_available():
            logger.warning("Docker mode configured but Docker not available, falling back to mock mode")
            return ServiceMode.MOCK
            
        return self.mode
    
    def get_service_url(self, service: str) -> str:
        """Get service URL - DEPRECATED."""
        # Default service URLs for compatibility
        service_ports = {
            "postgres": 5432,
            "postgres-test": 5433,
            "redis": 6379,
            "redis-test": 6380,
            "backend": 8000,
            "backend-test": 8001,
            "auth": 8001,
            "auth-test": 8002,
            "clickhouse": 8123
        }
        
        port = service_ports.get(service, 8000)
        return f"http://localhost:{port}"
    
    def configure_mock_environment(self):
        """Configure mock environment for testing - DEPRECATED."""
        logger.info("Configuring mock environment (deprecated method)")
        # Set environment variables for mock mode
        self.env.set("TEST_SERVICE_MODE", "mock")
        
    def configure_test_environment(self):
        """Configure test environment - DEPRECATED."""
        logger.info("Configuring test environment (deprecated method)")
        # Set basic test environment variables
        self.env.set("TEST_SERVICE_MODE", self.mode.value)
        
    async def start_services(self, 
                           services: Optional[List[str]] = None,
                           profiles: Optional[List[str]] = None,
                           wait_healthy: bool = True,
                           timeout: int = 120) -> bool:
        """Start services using SSOT DockerTestUtility - DEPRECATED."""
        logger.warning("Using deprecated DockerTestManager.start_services - redirecting to DockerTestUtility")
        
        try:
            async with self._docker_utility as docker:
                # Default services if none specified
                if services is None:
                    services = ["postgres", "redis"]
                
                # Start services
                result = await docker.start_services(
                    services=services,
                    wait_for_health=wait_healthy,
                    timeout=float(timeout)
                )
                
                # Track running services for compatibility
                if result["success"]:
                    self._running_services.update(services)
                
                return result["success"]
                
        except Exception as e:
            logger.error(f"Error starting services via DockerTestUtility: {e}")
            return False
    
    async def stop_services(self, 
                          services: Optional[List[str]] = None,
                          cleanup_volumes: bool = False) -> bool:
        """Stop services using SSOT DockerTestUtility - DEPRECATED."""
        logger.warning("Using deprecated DockerTestManager.stop_services - redirecting to DockerTestUtility")
        
        try:
            async with self._docker_utility as docker:
                # Stop services
                result = await docker.stop_services(services)
                
                # Update running services tracking
                if result["success"]:
                    if services:
                        for service in services:
                            self._running_services.discard(service)
                    else:
                        self._running_services.clear()
                
                return result["success"]
                
        except Exception as e:
            logger.error(f"Error stopping services via DockerTestUtility: {e}")
            return False
    
    def get_running_services(self) -> List[str]:
        """Get list of running services - DEPRECATED."""
        return list(self._running_services)


# Export compatibility
__all__ = ["DockerTestManager", "ServiceMode"]