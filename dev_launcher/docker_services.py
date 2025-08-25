"""
Docker-based service management for dev launcher.

Provides Docker container support for Redis, ClickHouse, and PostgreSQL
when local installations are not available but Docker is installed.
"""

import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from dev_launcher.container_discovery import ContainerDiscovery
from dev_launcher.isolated_environment import get_env

logger = logging.getLogger(__name__)


class DockerServiceManager:
    """
    Manages Docker-based service containers for development environment.
    
    Provides fallback containers for services when local installations
    are not available but Docker is present.
    """
    
    def __init__(self):
        self.container_configs = self._get_container_configs()
        self.running_containers: List[str] = []
        self.container_discovery = ContainerDiscovery()
        self.env = get_env()
    
    def start_redis_container(self) -> Tuple[bool, str]:
        """
        Start Redis container for local development.
        
        Returns:
            Tuple of (success, message)
        """
        container_name = "netra-dev-redis"
        
        # First check if we can reuse existing container
        if self.container_discovery.can_reuse_container(container_name):
            return True, f"Redis container '{container_name}' already running and healthy"
        
        # Also check alternative container names
        alt_container_name = "netra-redis-dev"
        if self.container_discovery.can_reuse_container(alt_container_name):
            return True, f"Redis container '{alt_container_name}' already running and healthy"
        
        try:
            # Remove existing container if exists
            self._remove_container_if_exists(container_name)
            
            # Start Redis container
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "6379:6379",
                "--restart", "unless-stopped",
                "redis:latest",
                "redis-server", "--appendonly", "yes"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.running_containers.append(container_name)
                # Wait for Redis to be ready
                if self._wait_for_redis_ready():
                    return True, f"Redis container '{container_name}' started successfully on port 6379"
                else:
                    return False, "Redis container started but failed readiness check"
            else:
                return False, f"Failed to start Redis container: {result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout starting Redis container"
        except Exception as e:
            return False, f"Error starting Redis container: {str(e)}"
    
    def start_clickhouse_container(self) -> Tuple[bool, str]:
        """
        Start ClickHouse container for local development.
        
        Returns:
            Tuple of (success, message)
        """
        container_name = "netra-dev-clickhouse"
        
        # First check if we can reuse existing container
        if self.container_discovery.can_reuse_container(container_name):
            return True, f"ClickHouse container '{container_name}' already running and healthy"
        
        # Also check alternative container names
        alt_container_name = "netra-clickhouse-dev"
        if self.container_discovery.can_reuse_container(alt_container_name):
            return True, f"ClickHouse container '{alt_container_name}' already running and healthy"
        
        try:
            # Remove existing container if exists
            self._remove_container_if_exists(container_name)
            
            # Start ClickHouse container
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "9000:9000",  # Native protocol
                "-p", "8123:8123",  # HTTP interface
                "--restart", "unless-stopped",
                "-e", "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1",
                "-e", "CLICKHOUSE_PASSWORD=netra_dev_password",
                "--ulimit", "nofile=262144:262144",
                "clickhouse/clickhouse-server:latest"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.running_containers.append(container_name)
                # Wait for ClickHouse to be ready
                if self._wait_for_clickhouse_ready():
                    return True, f"ClickHouse container '{container_name}' started successfully on ports 8123/9000"
                else:
                    return False, "ClickHouse container started but failed readiness check"
            else:
                return False, f"Failed to start ClickHouse container: {result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout starting ClickHouse container"
        except Exception as e:
            return False, f"Error starting ClickHouse container: {str(e)}"
    
    def start_postgres_container(self) -> Tuple[bool, str]:
        """
        Start PostgreSQL container for local development.
        
        Returns:
            Tuple of (success, message)
        """
        container_name = "netra-dev-postgres"
        
        # First check if we can reuse existing container
        if self.container_discovery.can_reuse_container(container_name):
            return True, f"PostgreSQL container '{container_name}' already running and healthy"
        
        # Also check alternative container names
        alt_container_name = "netra-postgres-dev"
        if self.container_discovery.can_reuse_container(alt_container_name):
            return True, f"PostgreSQL container '{alt_container_name}' already running and healthy"
        
        try:
            # Remove existing container if exists
            self._remove_container_if_exists(container_name)
            
            # Get PostgreSQL password from environment
            postgres_password = self.env.get("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")
            postgres_db = self.env.get("POSTGRES_DB", "netra_dev")
            postgres_user = self.env.get("POSTGRES_USER", "postgres")
            
            # Start PostgreSQL container
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", "5433:5432",  # Use 5433 to match config
                "--restart", "unless-stopped",
                "-e", f"POSTGRES_DB={postgres_db}",
                "-e", f"POSTGRES_USER={postgres_user}",
                "-e", f"POSTGRES_PASSWORD={postgres_password}",
                "-v", "netra_dev_postgres_data:/var/lib/postgresql/data",
                "postgres:15-alpine"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.running_containers.append(container_name)
                # Wait for PostgreSQL to be ready
                if self._wait_for_postgres_ready():
                    return True, f"PostgreSQL container '{container_name}' started successfully on port 5433"
                else:
                    return False, "PostgreSQL container started but failed readiness check"
            else:
                return False, f"Failed to start PostgreSQL container: {result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout starting PostgreSQL container"
        except Exception as e:
            return False, f"Error starting PostgreSQL container: {str(e)}"
    
    def stop_all_containers(self) -> List[str]:
        """
        Stop all Netra development containers.
        
        Returns:
            List of messages about stopped containers
        """
        messages = []
        container_names = ["netra-dev-redis", "netra-dev-clickhouse", "netra-dev-postgres"]
        
        for container_name in container_names:
            try:
                result = subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    messages.append(f"Stopped container '{container_name}'")
                    if container_name in self.running_containers:
                        self.running_containers.remove(container_name)
                else:
                    if "No such container" not in result.stderr:
                        messages.append(f"Failed to stop '{container_name}': {result.stderr.strip()}")
            except Exception as e:
                messages.append(f"Error stopping '{container_name}': {str(e)}")
        
        return messages
    
    def cleanup_containers(self) -> List[str]:
        """
        Remove all Netra development containers.
        
        Returns:
            List of messages about removed containers
        """
        messages = []
        container_names = ["netra-dev-redis", "netra-dev-clickhouse", "netra-dev-postgres"]
        
        # First stop all containers
        stop_messages = self.stop_all_containers()
        messages.extend(stop_messages)
        
        # Then remove them
        for container_name in container_names:
            try:
                result = subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    messages.append(f"Removed container '{container_name}'")
                else:
                    if "No such container" not in result.stderr:
                        messages.append(f"Failed to remove '{container_name}': {result.stderr.strip()}")
            except Exception as e:
                messages.append(f"Error removing '{container_name}': {str(e)}")
        
        return messages
    
    def get_container_status(self) -> Dict[str, str]:
        """
        Get status of all Netra development containers.
        
        Returns:
            Dictionary mapping container names to their status
        """
        status = {}
        container_names = ["netra-dev-redis", "netra-dev-clickhouse", "netra-dev-postgres"]
        
        for container_name in container_names:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    status[container_name] = result.stdout.strip()
                else:
                    status[container_name] = "not found"
            except Exception:
                status[container_name] = "unknown"
        
        return status
    
    def get_service_discovery_report(self) -> Dict[str, any]:
        """Get comprehensive service discovery report."""
        return self.container_discovery.get_service_discovery_report()
    
    def discover_running_services(self) -> Dict[str, str]:
        """
        Discover running Netra services and return their status.
        
        Returns:
            Dictionary mapping service names to container info
        """
        running_services = self.container_discovery.get_running_service_containers()
        return {
            service: f"{info.name} ({info.status})"
            for service, info in running_services.items()
        }
    
    def _is_container_running(self, container_name: str) -> bool:
        """Check if a container is currently running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False
    
    def _remove_container_if_exists(self, container_name: str):
        """Remove a container if it exists (ignores errors)."""
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True, timeout=30
            )
        except Exception:
            pass  # Ignore errors - container might not exist
    
    def _wait_for_redis_ready(self, timeout: int = 30) -> bool:
        """Wait for Redis container to be ready to accept connections."""
        for _ in range(timeout):
            try:
                result = subprocess.run(
                    ["docker", "exec", "netra-dev-redis", "redis-cli", "ping"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "PONG" in result.stdout:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False
    
    def _wait_for_clickhouse_ready(self, timeout: int = 60) -> bool:
        """Wait for ClickHouse container to be ready to accept connections."""
        for _ in range(timeout):
            try:
                result = subprocess.run(
                    ["docker", "exec", "netra-dev-clickhouse", "clickhouse-client", "--query", "SELECT 1"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "1" in result.stdout.strip():
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False
    
    def _wait_for_postgres_ready(self, timeout: int = 60) -> bool:
        """Wait for PostgreSQL container to be ready to accept connections."""
        for _ in range(timeout):
            try:
                result = subprocess.run(
                    ["docker", "exec", "netra-dev-postgres", "pg_isready", "-U", "postgres"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False
    
    def _get_container_configs(self) -> Dict[str, Dict]:
        """Get container configuration for each service."""
        return {
            "redis": {
                "image": "redis:latest",
                "name": "netra-dev-redis",
                "ports": {"6379": "6379"},
                "command": ["redis-server", "--appendonly", "yes"]
            },
            "clickhouse": {
                "image": "clickhouse/clickhouse-server:latest",
                "name": "netra-dev-clickhouse",
                "ports": {"9000": "9000", "8123": "8123"},
                "env": {
                    "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT": "1",
                    "CLICKHOUSE_PASSWORD": "netra_dev_password"
                }
            },
            "postgres": {
                "image": "postgres:15-alpine",
                "name": "netra-dev-postgres",
                "ports": {"5433": "5432"},
                "env": {
                    "POSTGRES_DB": "netra_dev",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "",
                    "POSTGRES_HOST_AUTH_METHOD": "trust"
                }
            }
        }


def start_required_services(service_config, results) -> List[str]:
    """
    Start required Docker services based on availability results.
    
    Args:
        service_config: ServicesConfiguration object
        results: Dictionary of ServiceAvailabilityResult objects
    
    Returns:
        List of status messages
    """
    messages = []
    docker_manager = DockerServiceManager()
    
    for service_name, result in results.items():
        if result.docker_available and not result.available:
            if service_name == 'redis':
                success, message = docker_manager.start_redis_container()
                messages.append(f"Redis Docker: {message}")
            elif service_name == 'clickhouse':
                success, message = docker_manager.start_clickhouse_container()
                messages.append(f"ClickHouse Docker: {message}")
            elif service_name == 'postgres':
                success, message = docker_manager.start_postgres_container()
                messages.append(f"PostgreSQL Docker: {message}")
    
    return messages


def check_docker_availability() -> bool:
    """Quick check if Docker is available and running."""
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def get_docker_service_urls() -> Dict[str, str]:
    """Get connection URLs for Docker-based services."""
    return {
        'redis': 'redis://localhost:6379/0',
        'clickhouse_native': 'clickhouse://default:netra_dev_password@localhost:9000/netra_dev',
        'clickhouse_http': 'http://default:netra_dev_password@localhost:8123',
        'postgres': 'postgresql://postgres:@localhost:5433/netra_dev'
    }