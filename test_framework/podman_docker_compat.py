"""
Podman to Docker Compatibility Wrapper

Provides a UnifiedDockerManager-compatible interface for PodmanAdapter.
This allows the test runner to work with both Docker and Podman seamlessly.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from test_framework.podman_adapter import PodmanAdapter
from test_framework.podman_dynamic_ports import PodmanDynamicPortManager
from test_framework.unified_docker_manager import (
    EnvironmentType, ServiceStatus, ContainerState
)

logger = logging.getLogger(__name__)


class PodmanDockerCompatWrapper:
    """
    Wraps PodmanAdapter to provide UnifiedDockerManager-compatible interface.
    """
    
    def __init__(
        self,
        environment_type: EnvironmentType = EnvironmentType.SHARED,
        test_id: Optional[str] = None,
        use_alpine: bool = True,
        **kwargs
    ):
        """Initialize wrapper with Docker-compatible parameters."""
        self.environment_type = environment_type
        self.test_id = test_id or f"test_{int(time.time())}"
        self.use_alpine = use_alpine
        
        # Initialize the Podman adapter and dynamic port manager
        self.adapter = PodmanAdapter()
        self.port_manager = PodmanDynamicPortManager(self.test_id)
        
        # Track state
        self._environment_acquired = False
        self._compose_file = self._get_compose_file()
        self._project_name = f"netra-test-{self.test_id}"
        
        # Ports will be allocated dynamically
        self._ports = {}
        
    def _get_compose_file(self) -> str:
        """Get appropriate compose file for Podman."""
        project_root = Path(__file__).parent.parent
        return str(project_root / "podman-compose.yml")
        
    def _get_default_ports(self) -> Dict[str, int]:
        """Get default port mappings based on environment type."""
        if self.environment_type == EnvironmentType.SHARED:
            # Test environment ports
            return {
                'backend': 8000,
                'auth': 8081,
                'postgres': 5434,
                'redis': 6381,
                'clickhouse': 8125,
                'frontend': 3000
            }
        else:
            # Development environment ports
            return {
                'backend': 8000,
                'auth': 8081,
                'postgres': 5433,
                'redis': 6380,
                'clickhouse': 8124,
                'frontend': 3000
            }
    
    def acquire_environment(self) -> Tuple[str, Dict[str, int]]:
        """
        Acquire a test environment using Podman with dynamic ports.
        
        Returns:
            Tuple of (environment_id, port_mapping)
        """
        if self._environment_acquired:
            return self.test_id, self._ports
        
        try:
            # Start services with dynamic ports
            logger.info(f"Starting Podman services with dynamic ports for environment {self.test_id}")
            
            # Start all services and get allocated ports
            self._ports = self.port_manager.start_all_services()
            
            logger.info(f"Podman services started successfully with ports: {self._ports}")
            self._environment_acquired = True
            return self.test_id, self._ports
                
        except Exception as e:
            logger.error(f"Failed to acquire Podman environment: {e}")
            # Clean up any partial starts
            self.port_manager.cleanup()
            raise
    
    def wait_for_services(
        self, 
        timeout: int = 60,
        required_services: Optional[List[str]] = None
    ) -> bool:
        """
        Wait for services to become healthy.
        
        Args:
            timeout: Maximum wait time in seconds
            required_services: List of services to check (None for all)
            
        Returns:
            True if all services are healthy
        """
        # Services are already waited for in start_all_services
        # This is just for compatibility
        if self._environment_acquired:
            logger.info("Services already started and healthy")
            return True
        
        logger.warning("Services not started yet")
        return False
    
    def _is_service_healthy(self, service_name: str) -> bool:
        """Check if a service container is healthy."""
        import subprocess
        
        # Map service names to container names
        container_map = {
            'postgres': f'test-postgres-{self.test_id}',
            'redis': f'test-redis-{self.test_id}',
            'clickhouse': f'test-clickhouse-{self.test_id}',
        }
        
        container_name = container_map.get(service_name, service_name)
        
        try:
            # Check container status
            result = subprocess.run(
                ["podman", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                status = result.stdout.strip()
                # Check if container is running and healthy
                return "Up" in status or "healthy" in status
                
        except Exception as e:
            logger.debug(f"Failed to check health for {container_name}: {e}")
        
        return False
    
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get the status of a service."""
        if self._is_service_healthy(service_name):
            return ServiceStatus.HEALTHY
        
        # Map service names to container names
        container_map = {
            'postgres': f'test-postgres-{self.test_id}',
            'redis': f'test-redis-{self.test_id}',
            'clickhouse': f'test-clickhouse-{self.test_id}',
        }
        
        container_name = container_map.get(service_name, service_name)
        
        # Check if container exists but not healthy
        import subprocess
        try:
            result = subprocess.run(
                ["podman", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and container_name in result.stdout:
                return ServiceStatus.UNHEALTHY
                
        except Exception:
            pass
        
        return ServiceStatus.NOT_FOUND
    
    def restart_service(self, service_name: str, force: bool = False) -> bool:
        """Restart a service container."""
        import subprocess
        try:
            cmd = ["podman", "restart"]
            if force:
                cmd.append("--time=0")
            cmd.append(service_name)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to restart {service_name}: {e}")
            return False
    
    def release_environment(self, environment_id: str) -> None:
        """Release the test environment."""
        if not self._environment_acquired:
            return
        
        try:
            logger.info(f"Stopping Podman services for environment {environment_id}")
            
            # Clean up all containers
            self.port_manager.cleanup()
            self._environment_acquired = False
            self._ports.clear()
            
        except Exception as e:
            logger.error(f"Failed to release environment: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get container statistics."""
        return {
            'containers_started': 1 if self._environment_acquired else 0,
            'containers_stopped': 0,
            'total_runtime': 0,
            'runtime': 'podman'
        }