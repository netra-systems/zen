"""
Test-specific service management.

Handles starting, stopping, and monitoring services for test execution.
"""

import asyncio
import logging
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from test_launcher.config import TestConfig, ServiceConfig


logger = logging.getLogger(__name__)


class TestServiceManager:
    """Manages services for test execution."""
    
    def __init__(self, config: TestConfig):
        """Initialize service manager with test configuration."""
        self.config = config
        self.project_root = Path.cwd()
        self.running_services: Set[str] = set()
        self.service_processes: Dict[str, subprocess.Popen] = {}
        self.docker_containers: Set[str] = set()
    
    async def start_service(self, service_name: str) -> bool:
        """
        Start a specific service.
        
        Args:
            service_name: Name of the service to start
            
        Returns:
            True if service started successfully
        """
        if service_name not in self.config.services:
            logger.error(f"Service {service_name} not configured")
            return False
        
        service_config = self.config.services[service_name]
        
        if not service_config.enabled:
            logger.debug(f"Service {service_name} is disabled")
            return True
        
        logger.info(f"Starting service: {service_name}")
        
        # Check if service is already running
        if await self.is_service_running(service_name):
            logger.info(f"Service {service_name} is already running")
            self.running_services.add(service_name)
            return True
        
        # Start service based on type
        if service_name in ["postgres", "redis", "clickhouse"]:
            return await self._start_docker_service(service_name, service_config)
        elif service_name in ["backend", "auth", "frontend"]:
            return await self._start_application_service(service_name, service_config)
        else:
            logger.error(f"Unknown service type: {service_name}")
            return False
    
    async def _start_docker_service(self, service_name: str, config: ServiceConfig) -> bool:
        """Start a Docker-based service using SSOT UnifiedDockerManager."""
        try:
            logger.info(f"Starting Docker service {service_name} via UnifiedDockerManager")
            
            # Import SSOT Docker management
            from test_framework.unified_docker_manager import UnifiedDockerManager
            
            # Use UnifiedDockerManager to start service
            docker_manager = UnifiedDockerManager()
            
            # Start the service using SSOT manager
            success = await docker_manager.start_services_smart([service_name], wait_healthy=True)
            
            if success:
                logger.info(f"Successfully started {service_name} via UnifiedDockerManager")
                self.running_services.add(service_name)
                return True
            else:
                logger.error(f"Failed to start {service_name} via UnifiedDockerManager")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Docker service {service_name}: {e}")
            # Fallback to legacy Docker commands for compatibility
            return await self._start_docker_service_legacy(service_name, config)
    
    async def _start_docker_service_legacy(self, service_name: str, config: ServiceConfig) -> bool:
        """Legacy Docker service startup - fallback only."""
        try:
            # Check if Docker is available
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error("Docker is not available")
                return False
            
            # Check if container already exists
            check_cmd = ["docker", "ps", "-a", "--filter", f"name={config.container_name}", "--format", "{{.Names}}"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if config.container_name in result.stdout:
                # Container exists, start it
                logger.info(f"Starting existing container: {config.container_name}")
                start_cmd = ["docker", "start", config.container_name]
                result = subprocess.run(start_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Failed to start container: {result.stderr}")
                    return False
            else:
                # Create new container
                logger.info(f"Creating new container: {config.container_name}")
                success = await self._create_docker_container(service_name, config)
                if not success:
                    return False
            
            self.docker_containers.add(config.container_name)
            self.running_services.add(service_name)
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout starting Docker service {service_name}")
            return False
        except Exception as e:
            logger.error(f"Error starting Docker service {service_name}: {e}")
            return False
    
    async def _create_docker_container(self, service_name: str, config: ServiceConfig) -> bool:
        """Create a new Docker container for the service."""
        # Build docker run command based on service
        if service_name == "postgres":
            cmd = [
                "docker", "run", "-d",
                "--name", config.container_name,
                "-p", f"{config.port}:5432",
                "-e", f"POSTGRES_USER={config.environment.get('POSTGRES_USER', 'test')}",
                "-e", f"POSTGRES_PASSWORD={config.environment.get('POSTGRES_PASSWORD', 'test')}",
                "-e", f"POSTGRES_DB={config.environment.get('POSTGRES_DB', 'netra_test')}",
                "postgres:14-alpine"
            ]
        elif service_name == "redis":
            cmd = [
                "docker", "run", "-d",
                "--name", config.container_name,
                "-p", f"{config.port}:6379",
                "redis:7-alpine"
            ]
        elif service_name == "clickhouse":
            cmd = [
                "docker", "run", "-d",
                "--name", config.container_name,
                "-p", f"{config.port}:8123",
                "-p", f"{config.port + 1}:9000",
                "--ulimit", "nofile=262144:262144",
                "clickhouse/clickhouse-server:latest"
            ]
        else:
            logger.error(f"Unknown Docker service: {service_name}")
            return False
        
        # Add network if specified
        if self.config.docker_network:
            # Create network if it doesn't exist
            network_cmd = ["docker", "network", "create", self.config.docker_network]
            subprocess.run(network_cmd, capture_output=True)  # Ignore errors if already exists
            
            # Add network to run command
            cmd.extend(["--network", self.config.docker_network])
        
        # Run the container
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to create container: {result.stderr}")
            return False
        
        logger.info(f"Container {config.container_name} created successfully")
        return True
    
    async def _start_application_service(self, service_name: str, config: ServiceConfig) -> bool:
        """Start an application service (backend, auth, frontend)."""
        try:
            if service_name == "backend":
                cmd = [
                    "python", "-m", "uvicorn",
                    "netra_backend.app.main:app",
                    "--host", "0.0.0.0",
                    "--port", str(config.port),
                    "--no-access-log"  # Reduce noise in test output
                ]
            elif service_name == "auth":
                cmd = [
                    "python", "-m", "uvicorn",
                    "auth_service.main:app",
                    "--host", "0.0.0.0",
                    "--port", str(config.port),
                    "--no-access-log"
                ]
            elif service_name == "frontend":
                # For frontend, use test-specific build
                cmd = ["npm", "run", "test:server"]
                # Change to frontend directory
                cwd = self.project_root / "frontend"
            else:
                logger.error(f"Unknown application service: {service_name}")
                return False
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                cwd=cwd if service_name == "frontend" else self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            self.service_processes[service_name] = process
            self.running_services.add(service_name)
            
            logger.info(f"Started {service_name} service (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Error starting {service_name}: {e}")
            return False
    
    async def is_service_running(self, service_name: str) -> bool:
        """
        Check if a service is running.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service is running
        """
        if service_name not in self.config.services:
            return False
        
        config = self.config.services[service_name]
        
        # Check by port
        if config.port:
            return self._is_port_open("localhost", config.port)
        
        # Check by container name
        if config.container_name:
            cmd = ["docker", "ps", "--filter", f"name={config.container_name}", "--format", "{{.Names}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return config.container_name in result.stdout
        
        # Check by process
        if service_name in self.service_processes:
            process = self.service_processes[service_name]
            return process.poll() is None
        
        return False
    
    async def is_service_ready(self, service_name: str) -> bool:
        """
        Check if a service is ready to accept requests.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service is ready
        """
        if service_name not in self.config.services:
            return False
        
        config = self.config.services[service_name]
        
        if not config.enabled:
            return True  # Disabled services are always "ready"
        
        # Check healthcheck endpoint if available
        if config.healthcheck_endpoint:
            if config.healthcheck_endpoint.startswith("http"):
                return await self._check_http_health(config.healthcheck_endpoint)
            elif config.healthcheck_endpoint.startswith("postgresql"):
                return await self._check_postgres_health(config.healthcheck_endpoint)
            elif config.healthcheck_endpoint.startswith("redis"):
                return await self._check_redis_health(config.healthcheck_endpoint)
        
        # Fallback to port check
        if config.port:
            return self._is_port_open("localhost", config.port)
        
        return False
    
    async def _check_http_health(self, url: str) -> bool:
        """Check HTTP healthcheck endpoint."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_postgres_health(self, connection_string: str) -> bool:
        """Check PostgreSQL health."""
        try:
            import asyncpg
            conn = await asyncpg.connect(connection_string, timeout=5)
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except:
            return False
    
    async def _check_redis_health(self, redis_url: str) -> bool:
        """Check Redis health."""
        try:
            import redis.asyncio as redis
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            return True
        except:
            return False
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open."""
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.timeout, socket.error, ConnectionRefusedError):
            return False
    
    async def stop_service(self, service_name: str):
        """Stop a specific service."""
        logger.info(f"Stopping service: {service_name}")
        
        # Stop application process
        if service_name in self.service_processes:
            process = self.service_processes[service_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del self.service_processes[service_name]
        
        # Stop Docker container
        config = self.config.services.get(service_name)
        if config and config.container_name in self.docker_containers:
            cmd = ["docker", "stop", config.container_name]
            subprocess.run(cmd, capture_output=True)
            self.docker_containers.remove(config.container_name)
        
        self.running_services.discard(service_name)
    
    async def stop_all_services(self):
        """Stop all running services."""
        logger.info("Stopping all services...")
        
        # Stop application processes
        for service_name, process in list(self.service_processes.items()):
            logger.info(f"Stopping {service_name} (PID: {process.pid})")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        
        self.service_processes.clear()
        
        # Stop Docker containers (if cleanup enabled)
        if self.config.cleanup_on_exit and self.docker_containers:
            for container_name in self.docker_containers:
                logger.info(f"Stopping container: {container_name}")
                cmd = ["docker", "stop", container_name]
                subprocess.run(cmd, capture_output=True)
                
                # Optionally remove containers
                if self.config.isolation_level.value == "full":
                    cmd = ["docker", "rm", container_name]
                    subprocess.run(cmd, capture_output=True)
        
        self.docker_containers.clear()
        self.running_services.clear()
    
    def get_service_logs(self, service_name: str, lines: int = 100) -> Optional[str]:
        """Get recent logs from a service."""
        # For Docker containers
        config = self.config.services.get(service_name)
        if config and config.container_name:
            cmd = ["docker", "logs", "--tail", str(lines), config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        
        # For application processes (would need to implement log capture)
        return None