"""
Podman Adapter for Container Operations

Provides Podman-specific implementations of container operations
with compatibility layer for Docker-like behavior.

Business Value: Enables container operations without Docker Desktop licensing.
"""

import asyncio
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
import yaml
import os

from test_framework.container_runtime import ContainerRuntime, get_runtime_command
from test_framework.docker_rate_limiter import DockerRateLimiter

logger = logging.getLogger(__name__)


@dataclass
class PodmanComposeConfig:
    """Configuration for Podman Compose operations."""
    compose_file: str
    project_name: str
    use_pods: bool = True  # Group services in pods for better networking
    rootless: bool = True  # Use rootless containers by default
    systemd: bool = False  # Use systemd for service management (Linux only)
    

class PodmanAdapter:
    """
    Adapter for Podman container operations.
    
    Provides Docker-compatible interface while leveraging Podman-specific features:
    - Rootless containers for better security
    - Pod-based service grouping
    - Systemd integration for health monitoring
    """
    
    def __init__(self, rate_limiter: Optional[DockerRateLimiter] = None):
        """Initialize Podman adapter with optional rate limiting."""
        self.rate_limiter = rate_limiter or DockerRateLimiter()
        self._pods: Set[str] = set()
        self._containers: Dict[str, str] = {}  # service_name -> container_id
    
    async def compose_up(
        self, 
        compose_file: str,
        project_name: str,
        detached: bool = True,
        build: bool = False,
        remove_orphans: bool = True,
        timeout: int = 300
    ) -> Tuple[bool, str]:
        """
        Start services using podman-compose.
        
        Returns:
            Tuple of (success, output_message)
        """
        try:
            # Build command
            cmd = ["podman-compose"]
            cmd.extend(["-f", compose_file])
            cmd.extend(["-p", project_name])
            cmd.append("up")
            
            if detached:
                cmd.append("-d")
            if build:
                cmd.append("--build")
            if remove_orphans:
                cmd.append("--remove-orphans")
            
            # Execute with rate limiting
            result = await self._execute_command(cmd, timeout=timeout)
            
            if result.returncode == 0:
                # Track started containers
                await self._update_container_tracking(project_name)
                return True, f"Services started successfully for project {project_name}"
            else:
                return False, f"Failed to start services: {result.stderr}"
                
        except Exception as e:
            logger.error(f"Error in compose_up: {e}")
            return False, str(e)
    
    async def compose_down(
        self,
        compose_file: str,
        project_name: str,
        remove_volumes: bool = False,
        remove_orphans: bool = True,
        timeout: int = 60
    ) -> Tuple[bool, str]:
        """
        Stop and remove services using podman-compose.
        
        Returns:
            Tuple of (success, output_message)
        """
        try:
            cmd = ["podman-compose"]
            cmd.extend(["-f", compose_file])
            cmd.extend(["-p", project_name])
            cmd.append("down")
            
            if remove_volumes:
                cmd.append("-v")
            if remove_orphans:
                cmd.append("--remove-orphans")
            
            result = await self._execute_command(cmd, timeout=timeout)
            
            if result.returncode == 0:
                # Clear tracking
                self._clear_container_tracking(project_name)
                return True, f"Services stopped for project {project_name}"
            else:
                return False, f"Failed to stop services: {result.stderr}"
                
        except Exception as e:
            logger.error(f"Error in compose_down: {e}")
            return False, str(e)
    
    async def create_pod(self, pod_name: str, port_mappings: Dict[int, int]) -> bool:
        """
        Create a Podman pod for grouping containers.
        
        Pods provide shared network namespace for containers,
        similar to Docker Compose networks.
        """
        try:
            cmd = ["podman", "pod", "create", "--name", pod_name]
            
            # Add port mappings
            for container_port, host_port in port_mappings.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])
            
            result = await self._execute_command(cmd)
            
            if result.returncode == 0:
                self._pods.add(pod_name)
                logger.info(f"Created pod: {pod_name}")
                return True
            else:
                logger.error(f"Failed to create pod {pod_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating pod: {e}")
            return False
    
    async def remove_pod(self, pod_name: str, force: bool = True) -> bool:
        """Remove a Podman pod and all its containers."""
        try:
            cmd = ["podman", "pod", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(pod_name)
            
            result = await self._execute_command(cmd)
            
            if result.returncode == 0:
                self._pods.discard(pod_name)
                logger.info(f"Removed pod: {pod_name}")
                return True
            else:
                logger.error(f"Failed to remove pod {pod_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing pod: {e}")
            return False
    
    async def get_container_health(self, container_name: str) -> Optional[str]:
        """
        Get health status of a container.
        
        Returns: 'healthy', 'unhealthy', 'starting', or None
        """
        try:
            cmd = ["podman", "inspect", container_name, "--format", "{{.State.Health.Status}}"]
            result = await self._execute_command(cmd)
            
            if result.returncode == 0:
                health = result.stdout.strip()
                return health if health and health != "<no value>" else None
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting container health: {e}")
            return None
    
    async def get_container_logs(
        self, 
        container_name: str,
        lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get logs from a container."""
        try:
            cmd = ["podman", "logs"]
            if lines:
                cmd.extend(["--tail", str(lines)])
            if follow:
                cmd.append("-f")
            cmd.append(container_name)
            
            result = await self._execute_command(cmd, timeout=10)
            return result.stdout if result.returncode == 0 else ""
            
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            return ""
    
    async def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """
        List containers with their details.
        
        Returns list of container info dictionaries.
        """
        try:
            cmd = ["podman", "ps", "--format", "json"]
            if all_containers:
                cmd.append("-a")
            
            result = await self._execute_command(cmd)
            
            if result.returncode == 0:
                containers = json.loads(result.stdout)
                return containers
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            return []
    
    async def restart_container(self, container_name: str, timeout: int = 30) -> bool:
        """Restart a container."""
        try:
            cmd = ["podman", "restart", "-t", str(timeout), container_name]
            result = await self._execute_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return False
    
    async def stop_container(self, container_name: str, timeout: int = 10) -> bool:
        """Stop a container."""
        try:
            cmd = ["podman", "stop", "-t", str(timeout), container_name]
            result = await self._execute_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False
    
    async def remove_container(self, container_name: str, force: bool = True) -> bool:
        """Remove a container."""
        try:
            cmd = ["podman", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(container_name)
            
            result = await self._execute_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error removing container: {e}")
            return False
    
    async def execute_in_container(
        self,
        container_name: str,
        command: List[str],
        user: Optional[str] = None,
        workdir: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Execute a command inside a container."""
        try:
            cmd = ["podman", "exec"]
            if user:
                cmd.extend(["-u", user])
            if workdir:
                cmd.extend(["-w", workdir])
            cmd.append(container_name)
            cmd.extend(command)
            
            result = await self._execute_command(cmd)
            return result.returncode == 0, result.stdout
            
        except Exception as e:
            logger.error(f"Error executing in container: {e}")
            return False, str(e)
    
    async def wait_for_healthy(
        self,
        container_name: str,
        timeout: int = 60,
        check_interval: int = 2
    ) -> bool:
        """Wait for a container to become healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            health = await self.get_container_health(container_name)
            
            if health == "healthy":
                logger.info(f"Container {container_name} is healthy")
                return True
            elif health == "unhealthy":
                logger.warning(f"Container {container_name} is unhealthy")
                return False
            
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for {container_name} to become healthy")
        return False
    
    async def generate_systemd_units(self, pod_name: str, output_dir: Path) -> bool:
        """
        Generate systemd unit files for a pod (Linux only).
        
        This enables better service management and auto-restart.
        """
        if os.name == 'nt':
            logger.debug("Systemd not available on Windows")
            return False
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                "podman", "generate", "systemd",
                "--new",  # Create new containers on start
                "--files",  # Write to files
                "--pod-prefix", "",  # No prefix
                "--container-prefix", "",  # No prefix
                "--name",  # Use names instead of IDs
                pod_name
            ]
            
            result = await self._execute_command(cmd, cwd=str(output_dir))
            
            if result.returncode == 0:
                logger.info(f"Generated systemd units for pod {pod_name} in {output_dir}")
                return True
            else:
                logger.error(f"Failed to generate systemd units: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error generating systemd units: {e}")
            return False
    
    async def _execute_command(
        self,
        cmd: List[str],
        timeout: int = 30,
        cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Execute a command with rate limiting."""
        # For now, skip rate limiting for Podman as it doesn't have the same issues as Docker
        # TODO: Add async rate limiting if needed in the future
        
        try:
            # Run command
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=timeout
                )
                
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=result.returncode,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace')
                )
                
            except asyncio.TimeoutError:
                result.kill()
                await result.wait()
                raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        
        except Exception as e:
            logger.error(f"Error executing command {' '.join(cmd)}: {e}")
            raise
    
    async def _update_container_tracking(self, project_name: str):
        """Update internal tracking of containers."""
        containers = await self.list_containers()
        for container in containers:
            labels = container.get("Labels", {})
            if labels.get("com.docker.compose.project") == project_name:
                service = labels.get("com.docker.compose.service")
                if service:
                    self._containers[service] = container["Id"][:12]
    
    def _clear_container_tracking(self, project_name: str):
        """Clear container tracking for a project."""
        # Remove containers associated with project
        to_remove = []
        for service, container_id in self._containers.items():
            if service.startswith(project_name):
                to_remove.append(service)
        
        for service in to_remove:
            del self._containers[service]
    
    def convert_docker_compose_to_podman(self, docker_compose_path: str) -> Dict[str, Any]:
        """
        Convert Docker Compose file to Podman-compatible format.
        
        Main differences:
        - Remove unsupported options
        - Adjust network configuration
        - Add pod definitions
        """
        with open(docker_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Adjustments for Podman
        podman_config = compose_config.copy()
        
        # Remove Docker-specific options
        if 'services' in podman_config:
            for service_name, service_config in podman_config['services'].items():
                # Remove unsupported deploy options
                if 'deploy' in service_config:
                    # Podman doesn't support swarm mode deploy options
                    del service_config['deploy']
                
                # Adjust healthcheck format if needed
                if 'healthcheck' in service_config:
                    hc = service_config['healthcheck']
                    # Ensure test is in list format
                    if 'test' in hc and isinstance(hc['test'], str):
                        hc['test'] = ['CMD-SHELL', hc['test']]
        
        return podman_config