"""
Docker container discovery for dev launcher.

Discovers and manages existing Docker containers before launching services.
"""

import logging
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    name: str
    status: str
    ports: List[str]
    image: str
    container_id: str
    is_healthy: bool


class ContainerDiscovery:
    """
    Discovers existing Docker containers and determines reuse strategy.
    
    Prevents duplicate container launches by checking what's already running
    and determining if existing containers can be reused.
    """
    
    def __init__(self):
        """Initialize container discovery."""
        self.netra_containers = [
            "netra-dev-redis",
            "netra-dev-clickhouse", 
            "netra-dev-postgres",
            "netra-redis-dev",
            "netra-clickhouse-dev",
            "netra-postgres-dev"
        ]
    
    def discover_all_containers(self) -> Dict[str, ContainerInfo]:
        """
        Discover all Docker containers on the system.
        
        Returns:
            Dictionary mapping container names to ContainerInfo objects
        """
        containers = {}
        
        try:
            # Get all containers (running and stopped)
            result = subprocess.run([
                'docker', 'ps', '-a', 
                '--format', '{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}\t{{.ID}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning("Failed to list Docker containers")
                return containers
            
            lines = result.stdout.strip().split('\n')
            # No header line when using --format without 'table'
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 5:
                    name = parts[0].strip()
                    status = parts[1].strip()
                    ports = parts[2].strip().split(', ') if parts[2].strip() else []
                    image = parts[3].strip()
                    container_id = parts[4].strip()
                    
                    # Determine if container is healthy
                    is_healthy = self._check_container_health(name, status)
                    
                    containers[name] = ContainerInfo(
                        name=name,
                        status=status,
                        ports=ports,
                        image=image,
                        container_id=container_id,
                        is_healthy=is_healthy
                    )
                    
        except Exception as e:
            logger.error(f"Error discovering containers: {e}")
            
        return containers
    
    def discover_netra_containers(self) -> Dict[str, ContainerInfo]:
        """
        Discover only Netra development containers.
        
        Returns:
            Dictionary of Netra container names to ContainerInfo objects
        """
        all_containers = self.discover_all_containers()
        return {
            name: info for name, info in all_containers.items()
            if name in self.netra_containers
        }
    
    def get_running_service_containers(self) -> Dict[str, ContainerInfo]:
        """
        Get running Netra service containers that can be reused.
        
        Returns:
            Dictionary of service names to running container info
        """
        netra_containers = self.discover_netra_containers()
        running_services = {}
        
        for name, info in netra_containers.items():
            if self._is_running_status(info.status) and info.is_healthy:
                service_name = self._extract_service_name(name)
                if service_name:
                    running_services[service_name] = info
                    
        return running_services
    
    def can_reuse_container(self, container_name: str) -> bool:
        """
        Check if a specific container can be reused.
        
        Args:
            container_name: Name of the container to check
            
        Returns:
            True if container can be reused, False otherwise
        """
        containers = self.discover_all_containers()
        
        if container_name not in containers:
            return False
            
        container = containers[container_name]
        return (self._is_running_status(container.status) and 
                container.is_healthy)
    
    def get_service_discovery_report(self) -> Dict[str, any]:
        """
        Generate a comprehensive service discovery report.
        
        Returns:
            Dictionary with discovery results and recommendations
        """
        all_containers = self.discover_all_containers()
        netra_containers = self.discover_netra_containers()
        running_services = self.get_running_service_containers()
        
        return {
            'total_containers': len(all_containers),
            'netra_containers': len(netra_containers),
            'running_services': running_services,
            'reusable_services': list(running_services.keys()),
            'containers_needing_restart': [
                name for name, info in netra_containers.items()
                if not self._is_running_status(info.status)
            ],
            'unhealthy_containers': [
                name for name, info in netra_containers.items()
                if not info.is_healthy and self._is_running_status(info.status)
            ]
        }
    
    def _check_container_health(self, container_name: str, status: str) -> bool:
        """
        Check if a container is healthy.
        
        Args:
            container_name: Name of the container
            status: Container status string
            
        Returns:
            True if container is healthy, False otherwise
        """
        if not self._is_running_status(status):
            return False
            
        # For Netra containers, try a basic connectivity check
        if container_name in self.netra_containers:
            return self._check_netra_container_connectivity(container_name)
            
        return "healthy" in status.lower() or "up" in status.lower()
    
    def _check_netra_container_connectivity(self, container_name: str) -> bool:
        """
        Check connectivity for Netra service containers.
        
        Args:
            container_name: Name of the Netra container
            
        Returns:
            True if container is responsive, False otherwise
        """
        try:
            if "redis" in container_name.lower():
                result = subprocess.run([
                    'docker', 'exec', container_name, 
                    'redis-cli', 'ping'
                ], capture_output=True, text=True, timeout=5)
                return result.returncode == 0 and "PONG" in result.stdout
                
            elif "clickhouse" in container_name.lower():
                result = subprocess.run([
                    'docker', 'exec', container_name,
                    'clickhouse-client', '--query', 'SELECT 1'
                ], capture_output=True, text=True, timeout=5)
                return result.returncode == 0 and "1" in result.stdout.strip()
                
            elif "postgres" in container_name.lower():
                result = subprocess.run([
                    'docker', 'exec', container_name,
                    'pg_isready', '-U', 'postgres'
                ], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
                
        except Exception as e:
            logger.debug(f"Health check failed for {container_name}: {e}")
            
        return True  # Default to healthy if we can't check
    
    def _is_running_status(self, status: str) -> bool:
        """Check if container status indicates it's running."""
        status_lower = status.lower()
        return ("up" in status_lower and 
                "exited" not in status_lower and 
                "dead" not in status_lower)
    
    def _extract_service_name(self, container_name: str) -> Optional[str]:
        """
        Extract service name from container name.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Service name if recognized, None otherwise
        """
        name_lower = container_name.lower()
        
        if "redis" in name_lower:
            return "redis"
        elif "clickhouse" in name_lower:
            return "clickhouse"
        elif "postgres" in name_lower:
            return "postgres"
            
        return None