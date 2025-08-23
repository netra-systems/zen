"""
Docker Compose management for local testing.

Manages Docker containers for testing Cloud Run services locally.
"""

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import test_framework.aiofiles_mock as aiofiles
import yaml

from ..unified.base_interfaces import (
    BaseTestComponent,
    IContainerManager,
    ServiceConfig,
    ServiceStatus,
    TestEnvironment,
)


@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    container_id: str
    name: str
    image: str
    status: ServiceStatus
    ports: Dict[str, int]
    created_at: datetime
    health_status: Optional[str] = None
    exit_code: Optional[int] = None
    
    @classmethod
    def from_docker_inspect(cls, inspect_data: Dict[str, Any]) -> 'ContainerInfo':
        """Create ContainerInfo from docker inspect output."""
        state = inspect_data.get('State', {})
        config = inspect_data.get('Config', {})
        network = inspect_data.get('NetworkSettings', {})
        
        # Parse status
        if state.get('Running'):
            if state.get('Health', {}).get('Status') == 'healthy':
                status = ServiceStatus.HEALTHY
            elif state.get('Health', {}).get('Status') == 'unhealthy':
                status = ServiceStatus.UNHEALTHY
            elif state.get('Health', {}).get('Status') == 'starting':
                status = ServiceStatus.STARTING
            else:
                status = ServiceStatus.DEGRADED
        else:
            status = ServiceStatus.STOPPED
        
        # Parse ports
        ports = {}
        for container_port, bindings in network.get('Ports', {}).items():
            if bindings:
                port_num = container_port.split('/')[0]
                host_port = bindings[0].get('HostPort')
                if host_port:
                    ports[port_num] = int(host_port)
        
        return cls(
            container_id=inspect_data.get('Id', '')[:12],
            name=inspect_data.get('Name', '').lstrip('/'),
            image=config.get('Image', ''),
            status=status,
            ports=ports,
            created_at=datetime.fromisoformat(
                inspect_data.get('Created', '').replace('Z', '+00:00')
            ),
            health_status=state.get('Health', {}).get('Status'),
            exit_code=state.get('ExitCode')
        )


class DockerComposeManager(BaseTestComponent, IContainerManager):
    """Manages Docker Compose for local testing."""
    
    def __init__(
        self,
        compose_file: str = "docker-compose.test.yml",
        project_name: str = "netra-test"
    ):
        super().__init__({
            "compose_file": compose_file,
            "project_name": project_name
        })
        self.compose_file = Path(compose_file)
        self.project_name = project_name
        self._containers: Dict[str, ContainerInfo] = {}
        self._compose_config: Optional[Dict] = None
    
    async def initialize(self) -> None:
        """Initialize the Docker Compose manager."""
        await super().initialize()
        
        # Verify Docker is available
        if not await self._check_docker_available():
            raise RuntimeError("Docker is not available or not running")
        
        # Verify compose file exists
        if not self.compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {self.compose_file}")
        
        # Load compose configuration
        async with aiofiles.open(self.compose_file, 'r') as f:
            content = await f.read()
            self._compose_config = yaml.safe_load(content)
    
    async def start_containers(
        self,
        services: Optional[List[str]] = None
    ) -> bool:
        """Start Docker containers."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "up", "-d"
        ]
        
        if services:
            cmd.extend(services)
        
        result = await self._run_command(cmd)
        
        if result[0] == 0:
            # Update container info
            await self._update_container_info()
            return True
        
        return False
    
    async def stop_containers(
        self,
        services: Optional[List[str]] = None
    ) -> bool:
        """Stop Docker containers."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "stop"
        ]
        
        if services:
            cmd.extend(services)
        
        result = await self._run_command(cmd)
        return result[0] == 0
    
    async def wait_for_healthy(
        self,
        timeout_seconds: int = 300
    ) -> bool:
        """Wait for all containers to be healthy."""
        self.validate_initialized()
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            await self._update_container_info()
            
            all_healthy = True
            for container in self._containers.values():
                if container.status not in [ServiceStatus.HEALTHY, ServiceStatus.UNKNOWN]:
                    if container.status == ServiceStatus.STOPPED:
                        return False  # Container died
                    all_healthy = False
                    break
            
            if all_healthy and self._containers:
                return True
            
            await asyncio.sleep(2)
        
        return False
    
    async def get_container_logs(
        self,
        container_name: str,
        tail_lines: int = 100
    ) -> str:
        """Get logs from a container."""
        self.validate_initialized()
        
        cmd = [
            "docker", "logs",
            "--tail", str(tail_lines),
            f"{self.project_name}_{container_name}_1"
        ]
        
        result = await self._run_command(cmd)
        return result[1] + result[2]  # Combine stdout and stderr
    
    async def cleanup(self) -> None:
        """Clean up all containers and resources."""
        if self._initialized:
            cmd = [
                "docker-compose",
                "-f", str(self.compose_file),
                "-p", self.project_name,
                "down", "-v", "--remove-orphans"
            ]
            await self._run_command(cmd)
        
        await super().cleanup()
    
    async def exec_in_container(
        self,
        container_name: str,
        command: List[str]
    ) -> Tuple[int, str, str]:
        """Execute a command inside a container."""
        self.validate_initialized()
        
        full_container_name = f"{self.project_name}_{container_name}_1"
        cmd = ["docker", "exec", full_container_name] + command
        
        return await self._run_command(cmd)
    
    async def restart_container(self, container_name: str) -> bool:
        """Restart a specific container."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "restart", container_name
        ]
        
        result = await self._run_command(cmd)
        return result[0] == 0
    
    async def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a service to specified number of replicas."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "up", "-d",
            "--scale", f"{service_name}={replicas}"
        ]
        
        result = await self._run_command(cmd)
        return result[0] == 0
    
    async def get_container_info(self, container_name: str) -> Optional[ContainerInfo]:
        """Get information about a specific container."""
        await self._update_container_info()
        return self._containers.get(container_name)
    
    async def get_all_containers(self) -> Dict[str, ContainerInfo]:
        """Get information about all containers."""
        await self._update_container_info()
        return self._containers.copy()
    
    async def get_service_endpoint(self, service_name: str) -> Optional[str]:
        """Get the endpoint URL for a service."""
        container_info = await self.get_container_info(service_name)
        
        if not container_info or not container_info.ports:
            return None
        
        # Get the first exposed port
        port = next(iter(container_info.ports.values()))
        return f"http://localhost:{port}"
    
    async def check_network_connectivity(
        self,
        from_service: str,
        to_service: str
    ) -> bool:
        """Check if one service can connect to another."""
        self.validate_initialized()
        
        # Get target service info
        target_info = await self.get_container_info(to_service)
        if not target_info:
            return False
        
        # Try to ping from source to target
        result = await self.exec_in_container(
            from_service,
            ["ping", "-c", "1", to_service]
        )
        
        return result[0] == 0
    
    async def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = await self._run_command(["docker", "version"])
            return result[0] == 0
        except:
            return False
    
    async def _run_command(
        self,
        cmd: List[str]
    ) -> Tuple[int, str, str]:
        """Run a shell command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            process.returncode,
            stdout.decode('utf-8'),
            stderr.decode('utf-8')
        )
    
    async def _update_container_info(self) -> None:
        """Update information about all containers."""
        # Get list of containers for this project
        cmd = [
            "docker", "ps", "-a",
            "--filter", f"label=com.docker.compose.project={self.project_name}",
            "--format", "{{.Names}}"
        ]
        
        result = await self._run_command(cmd)
        if result[0] != 0:
            return
        
        container_names = result[1].strip().split('\n') if result[1].strip() else []
        
        self._containers.clear()
        for full_name in container_names:
            if not full_name:
                continue
            
            # Extract service name from container name
            # Format: projectname_servicename_1
            parts = full_name.split('_')
            if len(parts) >= 2:
                service_name = parts[1]
                
                # Get detailed container info
                inspect_cmd = ["docker", "inspect", full_name]
                inspect_result = await self._run_command(inspect_cmd)
                
                if inspect_result[0] == 0:
                    try:
                        inspect_data = json.loads(inspect_result[1])
                        if inspect_data:
                            container_info = ContainerInfo.from_docker_inspect(inspect_data[0])
                            self._containers[service_name] = container_info
                    except json.JSONDecodeError:
                        pass
    
    async def build_images(self, services: Optional[List[str]] = None) -> bool:
        """Build Docker images for services."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "build"
        ]
        
        if services:
            cmd.extend(services)
        
        result = await self._run_command(cmd)
        return result[0] == 0
    
    async def pull_images(self, services: Optional[List[str]] = None) -> bool:
        """Pull Docker images for services."""
        self.validate_initialized()
        
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            "-p", self.project_name,
            "pull"
        ]
        
        if services:
            cmd.extend(services)
        
        result = await self._run_command(cmd)
        return result[0] == 0