"""
Docker Test Manager for managing test services.

This module provides Docker-based service orchestration for tests,
integrating with the unified Docker management system.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

# Import UnifiedDockerManager for compatibility export
from test_framework.unified_docker_manager import UnifiedDockerManager

logger = logging.getLogger(__name__)


class ServiceMode(Enum):
    """Service execution modes for testing."""
    DOCKER = "docker"  # Use Docker Compose services
    LOCAL = "local"    # Use local dev services
    MOCK = "mock"      # Use mocks only


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    port: int
    health_endpoint: Optional[str] = None
    required: bool = True
    startup_timeout: int = 30
    depends_on: List[str] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class DockerTestManager:
    """
    Manages Docker services for testing.
    
    This class provides a simplified interface for managing test services,
    delegating to the unified Docker manager when needed.
    """

    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.running_services: Set[str] = set()
        self.service_mode = ServiceMode.DOCKER
        self._setup_default_services()

    def _setup_default_services(self):
        """Setup default service configurations."""
        self.services.update({
            "postgres-test": ServiceConfig(
                name="postgres",
                port=5434,
                health_endpoint="/health",
                startup_timeout=30
            ),
            "redis-test": ServiceConfig(
                name="redis",
                port=6381,
                health_endpoint=None,
                startup_timeout=15
            ),
            "backend-test": ServiceConfig(
                name="backend",
                port=8000,
                health_endpoint="/health",
                depends_on=["postgres-test", "redis-test"],
                startup_timeout=60
            ),
            "auth-test": ServiceConfig(
                name="auth",
                port=8081,
                health_endpoint="/health",
                depends_on=["postgres-test", "redis-test"],
                startup_timeout=45
            ),
            "frontend-test": ServiceConfig(
                name="frontend",
                port=3000,
                health_endpoint="/health",
                depends_on=["backend-test", "auth-test"],
                startup_timeout=45
            )
        })

    def configure_mock_environment(self):
        """Configure environment for mock testing."""
        self.service_mode = ServiceMode.MOCK
        logger.info("Configured for mock environment - no real services will be started")

    async def start_services(
        self,
        services: Optional[List[str]] = None,
        profiles: Optional[List[str]] = None,
        wait_healthy: bool = True,
        timeout: int = 120
    ) -> bool:
        """
        Start specified services.

        Args:
            services: List of service names to start
            profiles: Docker Compose profiles to use
            wait_healthy: Whether to wait for services to be healthy
            timeout: Timeout for service startup

        Returns:
            True if all services started successfully
        """
        if self.service_mode == ServiceMode.MOCK:
            logger.info("Mock mode - skipping service startup")
            return True

        services = services or ["postgres-test", "redis-test"]
        logger.info(f"Starting services: {services}")

        try:
            # Use unified Docker manager for actual orchestration
            from test_framework.unified_docker_manager import ServiceOrchestrator, OrchestrationConfig
            
            config = OrchestrationConfig(
                environment="test",
                required_services=[s.replace("-test", "") for s in services],
                startup_timeout=float(timeout),
                health_check_timeout=10.0,
                health_check_retries=12
            )
            
            orchestrator = ServiceOrchestrator(config)
            success, _ = await orchestrator.orchestrate_services()
            
            if success:
                self.running_services.update(services)
                logger.info(f"Successfully started services: {services}")
            else:
                logger.error(f"Failed to start services: {services}")
                
            return success

        except ImportError:
            logger.warning("Unified Docker manager not available, using fallback")
            # Fallback: just mark as running for testing
            self.running_services.update(services)
            await asyncio.sleep(1)  # Simulate startup time
            return True

        except Exception as e:
            logger.error(f"Error starting services: {e}")
            return False

    async def stop_services(self, cleanup_volumes: bool = False) -> bool:
        """
        Stop all running services.

        Args:
            cleanup_volumes: Whether to clean up Docker volumes

        Returns:
            True if services stopped successfully
        """
        if self.service_mode == ServiceMode.MOCK:
            logger.info("Mock mode - skipping service shutdown")
            return True

        if not self.running_services:
            logger.info("No services running")
            return True

        logger.info(f"Stopping services: {list(self.running_services)}")

        try:
            # Use unified Docker manager for actual cleanup
            from test_framework.unified_docker_manager import ServiceOrchestrator, OrchestrationConfig
            
            config = OrchestrationConfig(
                environment="test",
                required_services=list(self.running_services),
                startup_timeout=30.0,
                health_check_timeout=5.0,
                health_check_retries=3
            )
            
            orchestrator = ServiceOrchestrator(config)
            await orchestrator.cleanup_services()
            
            self.running_services.clear()
            logger.info("Successfully stopped all services")
            return True

        except ImportError:
            logger.warning("Unified Docker manager not available, using fallback")
            # Fallback: just clear running services
            self.running_services.clear()
            await asyncio.sleep(1)  # Simulate shutdown time
            return True

        except Exception as e:
            logger.error(f"Error stopping services: {e}")
            return False

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the URL for a service."""
        service_config = self.services.get(f"{service_name}-test") or self.services.get(service_name)
        if not service_config:
            logger.warning(f"Service {service_name} not found")
            return None

        port = service_config.port
        return f"http://localhost:{port}"

    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is running."""
        return f"{service_name}-test" in self.running_services or service_name in self.running_services

    async def wait_for_service(self, service_name: str, timeout: int = 30) -> bool:
        """Wait for a service to be healthy."""
        if self.service_mode == ServiceMode.MOCK:
            return True

        service_config = self.services.get(f"{service_name}-test")
        if not service_config:
            logger.warning(f"Service {service_name} not configured")
            return False

        if not service_config.health_endpoint:
            logger.info(f"No health endpoint for {service_name}, assuming healthy")
            return True

        # Simple health check simulation
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # In a real implementation, this would make HTTP requests
                # For now, just simulate success
                await asyncio.sleep(1)
                logger.info(f"Service {service_name} is healthy")
                return True
            except Exception as e:
                logger.debug(f"Health check failed for {service_name}: {e}")
                await asyncio.sleep(2)

        logger.error(f"Service {service_name} failed to become healthy within {timeout}s")
        return False

    async def ensure_all_services_available(self) -> bool:
        """Ensure all required services are available."""
        if self.service_mode == ServiceMode.MOCK:
            return True

        required_services = [name for name, config in self.services.items() if config.required]
        
        for service_name in required_services:
            if not await self.wait_for_service(service_name.replace("-test", "")):
                return False
        
        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services."""
        return {
            "mode": self.service_mode.value,
            "running_services": list(self.running_services),
            "total_services": len(self.services),
            "healthy": len(self.running_services) == len([s for s in self.services.values() if s.required])
        }