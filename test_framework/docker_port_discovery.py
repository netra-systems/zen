"""
Docker port discovery for dynamic service configuration.

Discovers actual ports used by Docker containers, supporting both
docker-compose and standalone container deployments.
"""

import json
import logging
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServicePortMapping:
    """Port mapping information for a service."""
    service_name: str
    container_name: str
    internal_port: int
    external_port: int
    protocol: str = "tcp"
    host: str = "localhost"
    is_available: bool = True


class DockerPortDiscovery:
    """
    Discovers actual ports used by Docker services.
    
    Handles dynamic port mapping discovery for both docker-compose
    and standalone Docker containers, providing real port information
    for test configuration.
    """
    
    # Service to port mappings (internal container ports)
    SERVICE_PORTS = {
        "backend": 8000,
        "auth": 8081,
        "frontend": 3000,
        "postgres": 5432,
        "redis": 6379,
        "clickhouse": 8123,
    }
    
    # Alternative container name patterns
    CONTAINER_PATTERNS = {
        "backend": ["netra-backend", "netra_backend", "backend"],
        "auth": ["netra-auth", "auth-service", "auth"],
        "frontend": ["netra-frontend", "frontend"],
        "postgres": ["netra-postgres", "netra-dev-postgres", "postgres"],
        "redis": ["netra-redis", "netra-dev-redis", "redis"],
        "clickhouse": ["netra-clickhouse", "netra-dev-clickhouse", "clickhouse"],
    }
    
    def __init__(self):
        """Initialize Docker port discovery."""
        self.docker_available = self._check_docker_available()
        self.compose_project = self._detect_compose_project()
        
    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    def _detect_compose_project(self) -> Optional[str]:
        """Detect docker-compose project name if running."""
        try:
            # Try to detect from docker-compose ps
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse JSON output to get project name
                containers = json.loads(result.stdout)
                if containers and isinstance(containers, list):
                    # Extract project from container labels
                    for container in containers:
                        if "Project" in container:
                            return container["Project"]
                            
        except Exception as e:
            logger.debug(f"Could not detect compose project: {e}")
            
        return None
        
    def discover_all_ports(self) -> Dict[str, ServicePortMapping]:
        """
        Discover all service ports from running Docker containers.
        
        Returns:
            Dictionary mapping service names to port mappings
        """
        if not self.docker_available:
            logger.warning("Docker not available, using default ports")
            return self._get_default_mappings()
            
        port_mappings = {}
        
        # Try docker-compose first if project detected
        if self.compose_project:
            compose_ports = self._discover_compose_ports()
            port_mappings.update(compose_ports)
            
        # Then check standalone containers
        standalone_ports = self._discover_standalone_ports()
        
        # Merge, preferring compose ports
        for service, mapping in standalone_ports.items():
            if service not in port_mappings:
                port_mappings[service] = mapping
                
        # Fill in defaults for missing services
        default_mappings = self._get_default_mappings()
        for service, mapping in default_mappings.items():
            if service not in port_mappings:
                port_mappings[service] = mapping
                
        return port_mappings
        
    def _discover_compose_ports(self) -> Dict[str, ServicePortMapping]:
        """Discover ports from docker-compose services."""
        port_mappings = {}
        
        try:
            # Get docker-compose port mappings
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return port_mappings
                
            containers = json.loads(result.stdout)
            
            for container in containers:
                service_name = container.get("Service", "")
                
                # Match service name to our known services
                for known_service, internal_port in self.SERVICE_PORTS.items():
                    if known_service in service_name.lower():
                        # Parse ports from Publishers field
                        publishers = container.get("Publishers", [])
                        for pub in publishers:
                            if pub.get("TargetPort") == internal_port:
                                external_port = pub.get("PublishedPort")
                                if external_port:
                                    port_mappings[known_service] = ServicePortMapping(
                                        service_name=known_service,
                                        container_name=container.get("Name", ""),
                                        internal_port=internal_port,
                                        external_port=external_port,
                                        is_available=container.get("State") == "running"
                                    )
                                    break
                        break
                        
        except Exception as e:
            logger.error(f"Error discovering compose ports: {e}")
            
        return port_mappings
        
    def _discover_standalone_ports(self) -> Dict[str, ServicePortMapping]:
        """Discover ports from standalone Docker containers."""
        port_mappings = {}
        
        try:
            # Get all running containers with port mappings
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return port_mappings
                
            # Parse JSON output line by line (docker ps outputs newline-delimited JSON)
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    container = json.loads(line)
                    container_name = container.get("Names", "")
                    
                    # Match container name to our known services
                    for service, patterns in self.CONTAINER_PATTERNS.items():
                        if any(pattern in container_name.lower() for pattern in patterns):
                            # Parse port mappings
                            ports_str = container.get("Ports", "")
                            if ports_str:
                                port_mapping = self._parse_port_string(ports_str, self.SERVICE_PORTS[service])
                                if port_mapping:
                                    port_mappings[service] = ServicePortMapping(
                                        service_name=service,
                                        container_name=container_name,
                                        internal_port=self.SERVICE_PORTS[service],
                                        external_port=port_mapping,
                                        is_available=True
                                    )
                            break
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error discovering standalone ports: {e}")
            
        return port_mappings
        
    def _parse_port_string(self, ports_str: str, target_port: int) -> Optional[int]:
        """
        Parse Docker port string to find external port.
        
        Args:
            ports_str: Port string from docker ps (e.g., "0.0.0.0:6379->6379/tcp")
            target_port: Internal port we're looking for
            
        Returns:
            External port number if found
        """
        try:
            # Parse multiple port mappings
            for mapping in ports_str.split(", "):
                if f"->{target_port}" in mapping:
                    # Extract external port
                    if ":" in mapping:
                        # Format: 0.0.0.0:6379->6379/tcp
                        external = mapping.split(":")[1].split("->")[0]
                        return int(external)
                    else:
                        # Format: 6379->6379/tcp
                        external = mapping.split("->")[0]
                        return int(external)
        except (ValueError, IndexError):
            pass
            
        return None
        
    def _get_default_mappings(self) -> Dict[str, ServicePortMapping]:
        """Get default port mappings when Docker discovery fails."""
        return {
            service: ServicePortMapping(
                service_name=service,
                container_name=f"local-{service}",
                internal_port=port,
                external_port=port,
                is_available=False
            )
            for service, port in self.SERVICE_PORTS.items()
        }
        
    def get_service_url(self, service: str) -> Optional[str]:
        """
        Get the URL for a specific service.
        
        Args:
            service: Service name
            
        Returns:
            Service URL if available
        """
        port_mappings = self.discover_all_ports()
        
        if service not in port_mappings:
            return None
            
        mapping = port_mappings[service]
        
        if not mapping.is_available:
            return None
            
        # Build appropriate URL based on service type
        if service in ["backend", "auth", "frontend", "clickhouse"]:
            return f"http://{mapping.host}:{mapping.external_port}"
        elif service == "postgres":
            return f"postgresql://postgres@{mapping.host}:{mapping.external_port}/netra_dev"
        elif service == "redis":
            return f"redis://{mapping.host}:{mapping.external_port}"
            
        return None
        
    def ensure_services_available(self, required_services: List[str]) -> Tuple[bool, Dict[str, str]]:
        """
        Check if required services are available.
        
        Args:
            required_services: List of required service names
            
        Returns:
            Tuple of (all_available, missing_services)
        """
        port_mappings = self.discover_all_ports()
        missing_services = {}
        
        for service in required_services:
            if service not in port_mappings:
                missing_services[service] = "Service not found"
            elif not port_mappings[service].is_available:
                missing_services[service] = "Service not running"
                
        return len(missing_services) == 0, missing_services
        
    def get_cypress_config(self) -> Dict[str, any]:
        """
        Get Cypress configuration with discovered ports.
        
        Returns:
            Configuration dictionary for Cypress
        """
        port_mappings = self.discover_all_ports()
        
        # Build Cypress environment configuration
        config = {
            "baseUrl": f"http://localhost:{port_mappings['frontend'].external_port}",
            "env": {
                "BACKEND_URL": f"http://localhost:{port_mappings['backend'].external_port}",
                "AUTH_URL": f"http://localhost:{port_mappings['auth'].external_port}",
                "FRONTEND_URL": f"http://localhost:{port_mappings['frontend'].external_port}",
                "POSTGRES_PORT": port_mappings['postgres'].external_port,
                "REDIS_PORT": port_mappings['redis'].external_port,
            }
        }
        
        # Add service availability flags
        for service, mapping in port_mappings.items():
            config["env"][f"{service.upper()}_AVAILABLE"] = mapping.is_available
            
        return config
        
    def start_missing_services(self, required_services: List[str]) -> Tuple[bool, List[str]]:
        """
        Attempt to start missing Docker services.
        
        Args:
            required_services: List of required service names
            
        Returns:
            Tuple of (success, started_services)
        """
        if not self.docker_available:
            return False, []
            
        started_services = []
        
        # Check which services are missing
        _, missing = self.ensure_services_available(required_services)
        
        if not missing:
            return True, []
            
        # Try docker-compose up for missing services
        if self.compose_project or self._has_compose_file():
            try:
                services_to_start = list(missing.keys())
                result = subprocess.run(
                    ["docker", "compose", "up", "-d"] + services_to_start,
                    capture_output=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    started_services.extend(services_to_start)
                    logger.info(f"Started services via docker-compose: {services_to_start}")
                    return True, started_services
                    
            except Exception as e:
                logger.error(f"Failed to start services via docker-compose: {e}")
                
        return False, started_services
        
    def _has_compose_file(self) -> bool:
        """Check if docker-compose file exists."""
        from pathlib import Path
        compose_files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "docker-compose.dev.yml",
            "docker-compose.dev.yaml"
        ]
        
        for file in compose_files:
            if Path(file).exists():
                return True
        return False