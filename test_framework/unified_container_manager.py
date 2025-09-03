"""
Unified Container Manager - Abstraction over Docker and Podman

This module provides a unified interface for container operations that works
with both Docker and Podman runtimes. It automatically detects the available
runtime and adapts behavior accordingly.

Business Value: Enables testing without Docker Desktop licensing while
maintaining full backward compatibility with existing Docker infrastructure.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

from test_framework.container_runtime import (
    ContainerRuntime,
    detect_container_runtime,
    get_runtime_type,
    is_podman,
    is_docker
)
from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    ContainerState,
    EnvironmentType,
    OrchestrationConfig
)
from test_framework.podman_adapter import PodmanAdapter
from test_framework.docker_rate_limiter import DockerRateLimiter

logger = logging.getLogger(__name__)


class ContainerManagerMode(Enum):
    """Container manager operation mode."""
    AUTO = "auto"  # Auto-detect runtime
    DOCKER = "docker"  # Force Docker
    PODMAN = "podman"  # Force Podman


class UnifiedContainerManager:
    """
    Unified interface for container operations supporting both Docker and Podman.
    
    This class provides:
    - Automatic runtime detection (Docker/Podman)
    - Seamless fallback between runtimes
    - Consistent API regardless of backend
    - Compatibility with existing test infrastructure
    """
    
    def __init__(
        self,
        environment: str = "test",
        test_id: Optional[str] = None,
        mode: ContainerManagerMode = ContainerManagerMode.AUTO,
        use_alpine: bool = True,
        environment_type: EnvironmentType = EnvironmentType.SHARED
    ):
        """
        Initialize the container manager.
        
        Args:
            environment: Environment name (test/development/staging)
            test_id: Unique test identifier for isolation
            mode: Container runtime mode (auto/docker/podman)
            use_alpine: Use Alpine-based images for better performance
            environment_type: Type of environment (shared/dedicated)
        """
        self.environment = environment
        self.test_id = test_id
        self.mode = mode
        self.use_alpine = use_alpine
        self.environment_type = environment_type
        
        # Detect and initialize runtime
        self._runtime = self._detect_runtime()
        self._adapter = self._initialize_adapter()
        
        # Track compose file selection
        self._compose_file: Optional[str] = None
        
        logger.info(f"Initialized UnifiedContainerManager with {self._runtime.value} runtime")
    
    def _detect_runtime(self) -> ContainerRuntime:
        """Detect which container runtime to use based on mode and availability."""
        if self.mode == ContainerManagerMode.DOCKER:
            if not is_docker():
                raise RuntimeError("Docker runtime requested but not available")
            return ContainerRuntime.DOCKER
        
        elif self.mode == ContainerManagerMode.PODMAN:
            if not is_podman():
                raise RuntimeError("Podman runtime requested but not available")
            return ContainerRuntime.PODMAN
        
        else:  # AUTO mode
            runtime_info = detect_container_runtime()
            if runtime_info.runtime == ContainerRuntime.NONE:
                raise RuntimeError("No container runtime available (Docker or Podman)")
            return runtime_info.runtime
    
    def _initialize_adapter(self):
        """Initialize the appropriate adapter based on runtime."""
        if self._runtime == ContainerRuntime.DOCKER:
            # Use existing UnifiedDockerManager for Docker
            return UnifiedDockerManager(
                environment=self.environment,
                test_id=self.test_id,
                use_alpine=self.use_alpine,
                environment_type=self.environment_type
            )
        elif self._runtime == ContainerRuntime.PODMAN:
            # Use PodmanAdapter for Podman
            rate_limiter = DockerRateLimiter()  # Works for Podman too
            return PodmanAdapter(rate_limiter=rate_limiter)
        else:
            raise RuntimeError(f"Unsupported runtime: {self._runtime}")
    
    def get_compose_file(self) -> str:
        """
        Get the appropriate compose file for the current runtime.
        
        Returns:
            Path to the compose file
        """
        if self._compose_file:
            return self._compose_file
        
        # Determine compose file based on runtime and options
        if self._runtime == ContainerRuntime.PODMAN:
            # Use Podman-specific compose file
            compose_file = "podman-compose.yml"
        else:
            # Use Docker compose files
            if self.use_alpine:
                if self.environment == "test":
                    compose_file = "docker-compose.alpine-test.yml"
                else:
                    compose_file = "docker-compose.alpine.yml"
            else:
                if self.environment == "test":
                    compose_file = "docker-compose.test.yml"
                else:
                    compose_file = "docker-compose.yml"
        
        # Get absolute path
        project_root = Path(__file__).parent.parent
        self._compose_file = str(project_root / compose_file)
        
        if not Path(self._compose_file).exists():
            logger.warning(f"Compose file not found: {self._compose_file}")
            # Fall back to default
            self._compose_file = str(project_root / "docker-compose.yml")
        
        return self._compose_file
    
    async def start_services(
        self,
        services: Optional[List[str]] = None,
        build: bool = False,
        remove_orphans: bool = True,
        timeout: int = 300
    ) -> bool:
        """
        Start container services.
        
        Args:
            services: List of service names to start (None for all)
            build: Build images before starting
            remove_orphans: Remove containers for deleted services
            timeout: Timeout in seconds
            
        Returns:
            True if services started successfully
        """
        compose_file = self.get_compose_file()
        
        if self._runtime == ContainerRuntime.DOCKER:
            # Use UnifiedDockerManager's method
            return await self._adapter.start_services_async(
                timeout=timeout,
                force_recreate=False
            )
        
        elif self._runtime == ContainerRuntime.PODMAN:
            # Use PodmanAdapter
            project_name = f"netra_{self.environment}_{self.test_id[:8]}" if self.test_id else f"netra_{self.environment}"
            
            success, message = await self._adapter.compose_up(
                compose_file=compose_file,
                project_name=project_name,
                detached=True,
                build=build,
                remove_orphans=remove_orphans,
                timeout=timeout
            )
            
            if success:
                logger.info(message)
            else:
                logger.error(message)
            
            return success
    
    async def stop_services(
        self,
        services: Optional[List[str]] = None,
        remove_volumes: bool = False,
        timeout: int = 60
    ) -> bool:
        """
        Stop container services.
        
        Args:
            services: List of service names to stop (None for all)
            remove_volumes: Remove associated volumes
            timeout: Timeout in seconds
            
        Returns:
            True if services stopped successfully
        """
        if self._runtime == ContainerRuntime.DOCKER:
            # Use UnifiedDockerManager's method
            return await self._adapter.stop_services_async(
                cleanup_volumes=remove_volumes,
                force=False,
                timeout=timeout
            )
        
        elif self._runtime == ContainerRuntime.PODMAN:
            # Use PodmanAdapter
            compose_file = self.get_compose_file()
            project_name = f"netra_{self.environment}_{self.test_id[:8]}" if self.test_id else f"netra_{self.environment}"
            
            success, message = await self._adapter.compose_down(
                compose_file=compose_file,
                project_name=project_name,
                remove_volumes=remove_volumes,
                remove_orphans=True,
                timeout=timeout
            )
            
            if success:
                logger.info(message)
            else:
                logger.error(message)
            
            return success
    
    async def wait_for_healthy(
        self,
        services: Optional[List[str]] = None,
        timeout: int = 120,
        check_interval: int = 2
    ) -> bool:
        """
        Wait for services to become healthy.
        
        Args:
            services: List of service names to check (None for all)
            timeout: Maximum time to wait in seconds
            check_interval: Time between health checks in seconds
            
        Returns:
            True if all services are healthy
        """
        if self._runtime == ContainerRuntime.DOCKER:
            # Use UnifiedDockerManager's health check
            return self._adapter.wait_for_services(
                timeout=timeout,
                required_services=services
            )
        
        elif self._runtime == ContainerRuntime.PODMAN:
            # Check health for each service
            if not services:
                # Get all running containers
                containers = await self._adapter.list_containers()
                services = [c.get("Names", [""])[0].lstrip("/") for c in containers if c.get("Names")]
            
            # Wait for each service
            tasks = []
            for service in services:
                task = self._adapter.wait_for_healthy(
                    container_name=service,
                    timeout=timeout,
                    check_interval=check_interval
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if all succeeded
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health check failed for {services[i]}: {result}")
                    return False
                elif not result:
                    logger.error(f"Service {services[i]} did not become healthy")
                    return False
            
            return True
    
    async def get_service_logs(
        self,
        service_name: str,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """
        Get logs from a service container.
        
        Args:
            service_name: Name of the service
            lines: Number of lines to retrieve
            follow: Follow log output
            
        Returns:
            Log output as string
        """
        if self._runtime == ContainerRuntime.DOCKER:
            # Use docker logs command
            import subprocess
            cmd = ["docker", "logs"]
            if lines:
                cmd.extend(["--tail", str(lines)])
            if follow:
                cmd.append("-f")
            cmd.append(service_name)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout if result.returncode == 0 else ""
        
        elif self._runtime == ContainerRuntime.PODMAN:
            return await self._adapter.get_container_logs(
                container_name=service_name,
                lines=lines,
                follow=follow
            )
    
    def get_service_url(self, service_name: str, protocol: str = "http") -> str:
        """
        Get the URL for accessing a service.
        
        Args:
            service_name: Name of the service
            protocol: Protocol to use (http/https/ws/wss)
            
        Returns:
            Service URL
        """
        if self._runtime == ContainerRuntime.DOCKER:
            # Use UnifiedDockerManager's method
            return self._adapter.get_service_url(service_name)
        
        elif self._runtime == ContainerRuntime.PODMAN:
            # Get port mapping for service
            # This is simplified - in production would query actual port mappings
            default_ports = {
                "backend": 8000,
                "auth": 8081,
                "frontend": 3000,
                "postgres": 5432,
                "redis": 6379,
                "clickhouse": 8123
            }
            
            port = default_ports.get(service_name, 8000)
            host = "localhost"
            
            if protocol in ["ws", "wss"]:
                return f"{protocol}://{host}:{port}"
            else:
                return f"{protocol}://{host}:{port}"
    
    def cleanup(self) -> bool:
        """
        Cleanup all resources.
        
        Returns:
            True if cleanup successful
        """
        if self._runtime == ContainerRuntime.DOCKER:
            return self._adapter.cleanup()
        
        elif self._runtime == ContainerRuntime.PODMAN:
            # Cleanup is handled by compose down
            return True
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """
        Get information about the current runtime.
        
        Returns:
            Dictionary with runtime information
        """
        runtime_info = detect_container_runtime()
        
        return {
            "runtime": self._runtime.value,
            "version": runtime_info.version,
            "compose_command": runtime_info.compose_command,
            "socket_path": runtime_info.socket_path,
            "is_rootless": runtime_info.is_rootless,
            "supports_compose": runtime_info.supports_compose,
            "compose_file": self.get_compose_file(),
            "environment": self.environment,
            "use_alpine": self.use_alpine
        }
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_services()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_services()
    
    def __enter__(self):
        """Sync context manager entry."""
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.start_services())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.stop_services())


# Convenience functions for backward compatibility
def create_container_manager(
    environment: str = "test",
    test_id: Optional[str] = None,
    prefer_podman: bool = False,
    use_alpine: bool = True
) -> UnifiedContainerManager:
    """
    Create a container manager instance.
    
    Args:
        environment: Environment name
        test_id: Test identifier
        prefer_podman: Prefer Podman over Docker if both available
        use_alpine: Use Alpine images
        
    Returns:
        UnifiedContainerManager instance
    """
    mode = ContainerManagerMode.AUTO
    if prefer_podman:
        # Try Podman first if preferred
        if is_podman():
            mode = ContainerManagerMode.PODMAN
    
    return UnifiedContainerManager(
        environment=environment,
        test_id=test_id,
        mode=mode,
        use_alpine=use_alpine
    )