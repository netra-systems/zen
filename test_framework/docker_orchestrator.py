"""
Centralized Docker Test Environment Orchestrator
Manages isolated test environments with fresh Alpine-based images
"""

import os
import sys
import time
import json
import subprocess
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.isolated_environment import IsolatedEnvironment
from test_framework.port_conflict_fix import DockerPortManager, PortConflictResolver

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for a single service"""
    name: str
    dockerfile: str
    build_context: str = "."
    ports: Dict[str, int] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    healthcheck: Optional[Dict[str, Any]] = None
    volumes: List[str] = field(default_factory=list)
    command: Optional[str] = None
    

@dataclass 
class TestEnvironment:
    """Represents an isolated test environment"""
    id: str
    name: str
    services: Dict[str, ServiceConfig]
    network_name: str
    created_at: datetime
    status: str = "pending"
    cleanup_on_exit: bool = True
    

class DockerOrchestrator:
    """Orchestrates Docker environments for testing with fresh builds"""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self.env = IsolatedEnvironment()
        self.environments: Dict[str, TestEnvironment] = {}
        self.docker_client = self._verify_docker()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.port_manager = DockerPortManager(environment='test')
        # Clean up stale containers on init
        PortConflictResolver.cleanup_stale_docker_containers()
        
    def _verify_docker(self) -> bool:
        """Verify Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Docker not available")
            return True
        except Exception as e:
            logger.error(f"Docker verification failed: {e}")
            raise
            
    def create_test_environment(
        self,
        name: str,
        services: List[str],
        isolation_level: str = "full",
        use_alpine: bool = True
    ) -> TestEnvironment:
        """Create a new isolated test environment"""
        
        # Generate unique environment ID
        env_id = self._generate_env_id(name)
        network_name = f"test-net-{env_id}"
        
        # Configure services based on requirements
        service_configs = self._configure_services(
            services, 
            env_id,
            use_alpine=use_alpine
        )
        
        # Create test environment
        test_env = TestEnvironment(
            id=env_id,
            name=name,
            services=service_configs,
            network_name=network_name,
            created_at=datetime.now(),
            status="creating"
        )
        
        self.environments[env_id] = test_env
        
        # Create Docker network
        self._create_network(network_name)
        
        # Build and start services
        self._build_services(test_env)
        self._start_services(test_env)
        
        test_env.status = "running"
        return test_env
        
    def _generate_env_id(self, name: str) -> str:
        """Generate unique environment ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{name}-{timestamp}".encode()
        return hashlib.md5(hash_input).hexdigest()[:8]
        
    def _configure_services(
        self, 
        services: List[str], 
        env_id: str,
        use_alpine: bool = True
    ) -> Dict[str, ServiceConfig]:
        """Configure services for the test environment"""
        
        configs = {}
        
        # Allocate all ports upfront with safe allocation
        services_to_allocate = {}
        if "postgres" in services:
            services_to_allocate["postgres"] = 5432
        if "redis" in services:
            services_to_allocate["redis"] = 6379
        if "backend" in services:
            services_to_allocate["backend"] = 8000
        if "auth" in services:
            services_to_allocate["auth"] = 8081
        if "frontend" in services:
            services_to_allocate["frontend"] = 3000
        
        # Safely allocate ports with socket holding
        allocated_ports = self.port_manager.allocate_service_ports(services_to_allocate)
        
        # Base services configuration
        if "postgres" in services:
            configs["postgres"] = ServiceConfig(
                name=f"test-postgres-{env_id}",
                dockerfile="postgres:15-alpine" if use_alpine else "postgres:15",
                ports={"5432": allocated_ports["postgres"]},
                environment={
                    "POSTGRES_USER": "test_user",
                    "POSTGRES_PASSWORD": "test_pass", 
                    "POSTGRES_DB": "test_db",
                    "POSTGRES_INITDB_ARGS": "--data-checksums"
                },
                healthcheck={
                    "test": ["CMD-SHELL", "pg_isready -U test_user"],
                    "interval": "2s",
                    "timeout": "1s",
                    "retries": 10
                }
            )
            
        if "redis" in services:
            configs["redis"] = ServiceConfig(
                name=f"test-redis-{env_id}",
                dockerfile="redis:7-alpine" if use_alpine else "redis:7",
                ports={"6379": allocated_ports["redis"]},
                command="redis-server --appendonly no --save ''",
                healthcheck={
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "2s",
                    "timeout": "1s",
                    "retries": 5
                }
            )
            
        if "backend" in services:
            dockerfile = "docker/backend.alpine.Dockerfile" if use_alpine else "docker/backend.Dockerfile"
            configs["backend"] = ServiceConfig(
                name=f"test-backend-{env_id}",
                dockerfile=dockerfile,
                build_context=str(self.base_path),
                ports={"8000": allocated_ports["backend"]},
                environment={
                    "ENVIRONMENT": "testing",
                    "LOG_LEVEL": "ERROR",
                    "POSTGRES_HOST": f"test-postgres-{env_id}",
                    "REDIS_HOST": f"test-redis-{env_id}",
                    "TEST_MODE": "true"
                },
                depends_on=["postgres", "redis"],
                healthcheck={
                    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                    "interval": "5s",
                    "timeout": "3s",
                    "retries": 10
                }
            )
            
        if "auth" in services:
            dockerfile = "docker/auth.alpine.Dockerfile" if use_alpine else "docker/auth.Dockerfile"
            configs["auth"] = ServiceConfig(
                name=f"test-auth-{env_id}",
                dockerfile=dockerfile,
                build_context=str(self.base_path),
                ports={"8081": allocated_ports["auth"]},
                environment={
                    "ENVIRONMENT": "testing",
                    "LOG_LEVEL": "ERROR",
                    "POSTGRES_HOST": f"test-postgres-{env_id}",
                    "REDIS_HOST": f"test-redis-{env_id}",
                    "TEST_MODE": "true",
                    "JWT_SECRET_KEY": "test_jwt_secret"
                },
                depends_on=["postgres", "redis"],
                healthcheck={
                    "test": ["CMD", "curl", "-f", "http://localhost:8081/health"],
                    "interval": "5s",
                    "timeout": "3s",
                    "retries": 10
                }
            )
            
        if "frontend" in services:
            dockerfile = "docker/frontend.alpine.Dockerfile" if use_alpine else "docker/frontend.Dockerfile"
            configs["frontend"] = ServiceConfig(
                name=f"test-frontend-{env_id}",
                dockerfile=dockerfile,
                build_context=str(self.base_path),
                ports={"3000": allocated_ports["frontend"]},
                environment={
                    "NODE_ENV": "test",
                    "NEXT_PUBLIC_API_URL": f"http://test-backend-{env_id}:8000",
                    "NEXT_PUBLIC_AUTH_URL": f"http://test-auth-{env_id}:8081"
                },
                depends_on=["backend", "auth"]
            )
            
        return configs
        
    def _get_free_port(self) -> int:
        """Get a free port for service binding - DEPRECATED, use port_manager instead"""
        # This method is now deprecated and should not be used directly
        # It's kept for backward compatibility but will use the safe allocator
        logger.warning("_get_free_port is deprecated, using port_manager instead")
        
        # Use the safe port allocator to prevent race conditions
        if not hasattr(self, '_temp_allocator'):
            from test_framework.port_conflict_fix import SafePortAllocator
            self._temp_allocator = SafePortAllocator(instance_id="docker-orchestrator")
        
        port, sock = self._temp_allocator.allocate_port_with_hold(
            service_name="unknown",
            environment="test"
        )
        # Store socket for later release
        if not hasattr(self, '_held_sockets'):
            self._held_sockets = {}
        self._held_sockets[port] = sock
        return port
        
    def _create_network(self, network_name: str):
        """Create Docker network for test environment"""
        try:
            subprocess.run(
                ["docker", "network", "create", network_name],
                check=True,
                capture_output=True
            )
            logger.info(f"Created network: {network_name}")
        except subprocess.CalledProcessError as e:
            if "already exists" not in e.stderr.decode():
                raise
                
    def _build_services(self, test_env: TestEnvironment):
        """Build Docker images for services with fresh code"""
        
        futures = []
        
        for service_name, config in test_env.services.items():
            if config.dockerfile.startswith("docker/"):
                # Custom Dockerfile - build fresh image
                future = self._executor.submit(
                    self._build_image,
                    config,
                    test_env.id
                )
                futures.append((service_name, future))
                
        # Wait for all builds to complete
        for service_name, future in futures:
            try:
                future.result(timeout=300)  # 5 minute timeout
                logger.info(f"Built image for {service_name}")
            except Exception as e:
                logger.error(f"Failed to build {service_name}: {e}")
                raise
                
    def _build_image(self, config: ServiceConfig, env_id: str):
        """Build a single Docker image"""
        
        image_tag = f"{config.name}:test-{env_id}"
        
        build_args = [
            "docker", "build",
            "-f", config.dockerfile,
            "-t", image_tag,
            "--build-arg", f"BUILD_ENV=test",
            "--no-cache",  # Always fresh build for tests
            config.build_context
        ]
        
        result = subprocess.run(
            build_args,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Build failed: {result.stderr}")
            
        return image_tag
        
    def _start_services(self, test_env: TestEnvironment):
        """Start services in dependency order"""
        
        started = set()
        
        def start_service(name: str, config: ServiceConfig):
            # Wait for dependencies
            for dep in config.depends_on:
                if dep not in started:
                    dep_config = test_env.services.get(dep)
                    if dep_config:
                        start_service(dep, dep_config)
                        
            # Start the service
            self._run_container(config, test_env)
            started.add(name)
            
            # Wait for health check
            if config.healthcheck:
                self._wait_for_healthy(config)
                
        for name, config in test_env.services.items():
            if name not in started:
                start_service(name, config)
        
        # Release held sockets after all services are started
        self.port_manager._release_sockets()
        
        # Release any sockets held by deprecated _get_free_port
        if hasattr(self, '_held_sockets'):
            for sock in self._held_sockets.values():
                try:
                    sock.close()
                except:
                    pass
            self._held_sockets.clear()
                
    def _run_container(self, config: ServiceConfig, test_env: TestEnvironment):
        """Run a Docker container"""
        
        run_args = [
            "docker", "run",
            "-d",
            "--name", config.name,
            "--network", test_env.network_name
        ]
        
        # Add port mappings
        for container_port, host_port in config.ports.items():
            run_args.extend(["-p", f"{host_port}:{container_port}"])
            
        # Add environment variables
        for key, value in config.environment.items():
            run_args.extend(["-e", f"{key}={value}"])
            
        # Add volumes
        for volume in config.volumes:
            run_args.extend(["-v", volume])
            
        # Add image
        if config.dockerfile.startswith("docker/"):
            image = f"{config.name}:test-{test_env.id}"
        else:
            image = config.dockerfile
            
        run_args.append(image)
        
        # Add command if specified
        if config.command:
            run_args.extend(config.command.split())
            
        result = subprocess.run(run_args, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start {config.name}: {result.stderr}")
            
    def _wait_for_healthy(self, config: ServiceConfig, timeout: int = 60):
        """Wait for container to be healthy"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["docker", "inspect", config.name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data and data[0].get("State", {}).get("Health", {}).get("Status") == "healthy":
                    return
                    
            time.sleep(1)
            
        raise TimeoutError(f"Container {config.name} not healthy after {timeout}s")
        
    def refresh_dev_services(self, services: Optional[List[str]] = None):
        """Refresh development services with latest code changes"""
        
        services = services or ["backend", "auth", "frontend"]
        
        logger.info("Refreshing development services with latest changes...")
        
        for service in services:
            self._rebuild_dev_service(service)
            
    def _rebuild_dev_service(self, service: str):
        """Rebuild and restart a development service"""
        
        container_name = f"netra-dev-{service}"
        
        # Stop existing container
        subprocess.run(
            ["docker", "stop", container_name],
            capture_output=True
        )
        
        # Remove existing container
        subprocess.run(
            ["docker", "rm", container_name],
            capture_output=True
        )
        
        # Rebuild with latest code
        build_args = [
            "docker-compose",
            "build",
            "--no-cache",
            f"dev-{service}"
        ]
        
        result = subprocess.run(build_args, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to rebuild {service}: {result.stderr}")
            return
            
        # Start the service
        subprocess.run(
            ["docker-compose", "up", "-d", f"dev-{service}"],
            capture_output=True
        )
        
        logger.info(f"Refreshed {service} with latest changes")
        
    def cleanup_environment(self, env_id: str):
        """Clean up a test environment"""
        
        test_env = self.environments.get(env_id)
        if not test_env:
            return
            
        logger.info(f"Cleaning up environment {env_id}")
        
        # Clean up port allocations
        self.port_manager.cleanup()
        
        # Stop and remove containers
        for config in test_env.services.values():
            subprocess.run(
                ["docker", "stop", config.name],
                capture_output=True
            )
            subprocess.run(
                ["docker", "rm", config.name],
                capture_output=True
            )
            
        # Remove network
        subprocess.run(
            ["docker", "network", "rm", test_env.network_name],
            capture_output=True
        )
        
        # Remove from tracking
        del self.environments[env_id]
        
    def get_service_url(self, env_id: str, service: str) -> str:
        """Get the URL for a service in an environment"""
        
        test_env = self.environments.get(env_id)
        if not test_env:
            raise ValueError(f"Environment {env_id} not found")
            
        config = test_env.services.get(service)
        if not config:
            raise ValueError(f"Service {service} not found in environment")
            
        # Get the first port mapping
        if config.ports:
            port = list(config.ports.values())[0]
            return f"http://localhost:{port}"
            
        return None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up all environments on exit"""
        for env_id in list(self.environments.keys()):
            self.cleanup_environment(env_id)
        self._executor.shutdown(wait=True)
        # Clean up port manager
        self.port_manager.cleanup()
        # Clean up temp allocator if it exists
        if hasattr(self, '_temp_allocator'):
            self._temp_allocator.cleanup_all()