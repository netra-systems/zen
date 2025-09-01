"""
Unified Docker Management System - SSOT for Docker Operations

Combines the best features of ServiceOrchestrator and CentralizedDockerManager:
- Async/await architecture for better concurrency
- Cross-platform locking to prevent restart storms
- Environment type management (shared/dedicated/production) 
- Comprehensive health monitoring and reporting
- Memory optimization to prevent Docker crashes
- Rate limiting to prevent service restart storms

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Enable reliable parallel test execution, prevent environment crashes
3. Value Impact: Prevents 4-8 hours/week of developer downtime, enables CI/CD reliability
4. Revenue Impact: Protects $2M+ ARR by ensuring test infrastructure stability
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import threading
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
import socket
import yaml
import warnings

if os.name != 'nt':
    import fcntl
else:
    fcntl = None
    
if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
from shared.isolated_environment import get_env
from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping
from test_framework.docker_introspection import DockerIntrospector, IntrospectionReport

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Service health status."""
    service_name: str
    is_healthy: bool
    port: int
    response_time_ms: float
    error_message: Optional[str] = None
    last_check: Optional[float] = None


@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    name: str
    service: str
    container_id: str
    image: str
    state: "ContainerState"  # Forward reference to avoid circular dependency
    health: Optional[str] = None
    uptime: Optional[str] = None
    ports: Optional[Dict[str, int]] = None
    exit_code: Optional[int] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_docker_inspect(cls, inspect_data: Dict[str, Any]) -> 'ContainerInfo':
        """Create ContainerInfo from docker inspect output."""
        state = inspect_data.get('State', {})
        config = inspect_data.get('Config', {})
        network = inspect_data.get('NetworkSettings', {})
        
        # Parse status
        if state.get('Running'):
            if state.get('Health', {}).get('Status') == 'healthy':
                container_state = ContainerState.HEALTHY
            elif state.get('Health', {}).get('Status') == 'unhealthy':
                container_state = ContainerState.UNHEALTHY
            elif state.get('Health', {}).get('Status') == 'starting':
                container_state = ContainerState.STARTING
            else:
                container_state = ContainerState.RUNNING
        else:
            container_state = ContainerState.STOPPED
        
        # Parse ports
        ports = {}
        for container_port, bindings in network.get('Ports', {}).items():
            if bindings:
                port_num = container_port.split('/')[0]
                host_port = bindings[0].get('HostPort')
                if host_port:
                    ports[port_num] = int(host_port)
        
        # Extract service name from container name
        name = inspect_data.get('Name', '').lstrip('/')
        service = name.split('_')[1] if '_' in name else name.split('-')[-1]
        
        return cls(
            name=name,
            service=service,
            container_id=inspect_data.get('Id', '')[:12],
            image=config.get('Image', ''),
            state=container_state,
            health=state.get('Health', {}).get('Status'),
            ports=ports,
            exit_code=state.get('ExitCode'),
            created_at=datetime.fromisoformat(
                inspect_data.get('Created', '').replace('Z', '+00:00')
            ) if inspect_data.get('Created') else None
        )


@dataclass
class OrchestrationConfig:
    """Service orchestration configuration."""
    environment: str = "test"
    startup_timeout: float = 60.0
    health_check_timeout: float = 5.0
    health_check_retries: int = 12
    health_check_interval: float = 2.0
    required_services: List[str] = None
    
    def __post_init__(self):
        if self.required_services is None:
            self.required_services = ["postgres", "redis", "backend", "auth"]


class EnvironmentType(Enum):
    """Test environment types"""
    SHARED = "shared"  # Shared test environment (default)
    DEDICATED = "dedicated"  # Dedicated per test run
    PRODUCTION = "production"  # Production-like images
    DEVELOPMENT = "development"  # Development images


class ServiceMode(Enum):
    """Service execution mode for testing."""
    DOCKER = "docker"  # Use Docker Compose (default)
    LOCAL = "local"    # Use dev_launcher (legacy)
    MOCK = "mock"      # Use mocks only


class ContainerState(Enum):
    """Docker container states."""
    RUNNING = "running"
    STOPPED = "stopped" 
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"


class ServiceStatus(Enum):
    """Docker service status"""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RESTARTING = "restarting"


class UnifiedDockerManager:
    """
    Unified Docker management with async orchestration and centralized coordination.
    
    Single Source of Truth (SSOT) for all Docker operations in the test framework.
    Combines orchestration capabilities with rate limiting and environment management.
    """
    
    # Class-level configuration
    LOCK_DIR = Path("/tmp/netra_docker_locks") if os.name != 'nt' else Path(os.environ.get('TEMP', '.')) / "netra_docker_locks"
    STATE_FILE = LOCK_DIR / "docker_state.json"
    RESTART_COOLDOWN = 30  # seconds between restart attempts
    MAX_RESTART_ATTEMPTS = 3
    HEALTH_CHECK_TIMEOUT = 60  # seconds
    
    # Service configuration
    SERVICES = {
        "backend": {
            "container": "netra-backend",
            "port": 8000,
            "health_endpoint": "/health",
            "memory_limit": "1024m"  # Reduced for stability
        },
        "frontend": {
            "container": "netra-frontend", 
            "port": 3000,
            "health_endpoint": "/",
            "memory_limit": "256m"  # Reduced for stability
        },
        "auth": {
            "container": "netra-auth",
            "port": 8001,
            "health_endpoint": "/health",
            "memory_limit": "512m"
        },
        "postgres": {
            "container": "netra-postgres",
            "port": 5432,
            "health_cmd": "pg_isready",
            "memory_limit": "512m"
        },
        "redis": {
            "container": "netra-redis",
            "port": 6379,
            "health_cmd": "redis-cli ping",
            "memory_limit": "256m"
        }
    }
    
    def __init__(self, 
                 config: Optional[OrchestrationConfig] = None,
                 environment_type: EnvironmentType = EnvironmentType.SHARED,
                 test_id: Optional[str] = None,
                 use_production_images: bool = True,  # Default to memory-optimized production images
                 mode: ServiceMode = ServiceMode.DOCKER):
        """
        Initialize unified Docker manager with orchestration capabilities.
        
        Args:
            config: Orchestration configuration
            environment_type: Type of test environment
            test_id: Unique test identifier for dedicated environments
            use_production_images: Use production Docker images for memory efficiency
            mode: Service execution mode (docker, local, mock)
        """
        self.config = config or OrchestrationConfig()
        self.environment_type = environment_type
        self.test_id = test_id or self._generate_test_id()
        self.use_production_images = use_production_images
        self.mode = mode
        
        # Port discovery integration
        self.port_discovery = DockerPortDiscovery(use_test_services=True)
        self.service_health: Dict[str, ServiceHealth] = {}
        self.started_services: Set[str] = set()
        
        # Container management
        self._containers: Dict[str, ContainerInfo] = {}
        self._compose_config: Optional[Dict] = None
        self._docker_available = None
        self._running_services = set()
        
        # Initialize lock directory
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for locks
        self._local = threading.local()
        
        # Restart tracking
        self._restart_history: Dict[str, List[float]] = {}
        
        # Track environment setup
        env = get_env()
        self.environment = env.get("TEST_ENV", "test")
        
        # Additional port mappings for different modes
        self._docker_ports = {
            "postgres": 5433,
            "redis": 6380,
            "clickhouse": 8124,
            "backend": 8001,
            "auth": 8082,
            "frontend": 3001
        }
        
        self._local_ports = {
            "postgres": 5432,
            "redis": 6379,
            "clickhouse": 8123,
            "backend": 8000,
            "auth": 8081,
            "frontend": 3000
        }
        
        # Initialize state
        self._load_state()
    
    def _generate_test_id(self) -> str:
        """Generate unique test ID"""
        timestamp = datetime.now().isoformat()
        pid = os.getpid()
        return hashlib.md5(f"{timestamp}_{pid}".encode()).hexdigest()[:8]
    
    @contextmanager
    def _file_lock(self, lock_name: str, timeout: int = 30):
        """
        Cross-platform file locking mechanism.
        
        Args:
            lock_name: Name of the lock file
            timeout: Maximum time to wait for lock
        """
        lock_file = self.LOCK_DIR / f"{lock_name}.lock"
        lock_file.touch(exist_ok=True)
        
        start_time = time.time()
        locked = False
        
        with open(lock_file, 'r+') as f:
            while time.time() - start_time < timeout:
                try:
                    if os.name == 'nt':
                        # Windows locking
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        # Unix locking
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (IOError, OSError):
                    time.sleep(0.1)
            
            if not locked:
                raise TimeoutError(f"Could not acquire lock {lock_name} within {timeout} seconds")
            
            try:
                yield
            finally:
                if os.name == 'nt':
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f, fcntl.LOCK_UN)
    
    def _load_state(self) -> Dict[str, Any]:
        """Load shared Docker state"""
        try:
            if self.STATE_FILE.exists():
                with self._file_lock("state"):
                    with open(self.STATE_FILE, 'r') as f:
                        return json.load(f)
        except Exception:
            pass
        return {
            "services": {},
            "environments": {},
            "restart_history": {}
        }
    
    def _save_state(self, state: Dict[str, Any]):
        """Save shared Docker state"""
        with self._file_lock("state"):
            with open(self.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2, default=str)
    
    def _get_environment_name(self) -> str:
        """Get environment name based on type"""
        if self.environment_type == EnvironmentType.SHARED:
            return "netra_test_shared"
        elif self.environment_type == EnvironmentType.DEDICATED:
            return f"netra_test_{self.test_id}"
        else:
            return f"netra_{self.environment_type.value}"
    
    def _check_restart_allowed(self, service_name: str) -> bool:
        """
        Check if restart is allowed based on cooldown and limits.
        Prevents restart storms.
        """
        now = time.time()
        
        # Get restart history
        if service_name not in self._restart_history:
            self._restart_history[service_name] = []
        
        history = self._restart_history[service_name]
        
        # Remove old entries
        history = [t for t in history if now - t < 3600]  # Keep last hour
        
        # Check cooldown
        if history and now - history[-1] < self.RESTART_COOLDOWN:
            remaining = self.RESTART_COOLDOWN - (now - history[-1])
            logger.warning(f"⏳ Restart cooldown active for {service_name}. Wait {remaining:.1f}s")
            return False
        
        # Check rate limit
        recent_restarts = len([t for t in history if now - t < 300])  # Last 5 minutes
        if recent_restarts >= self.MAX_RESTART_ATTEMPTS:
            logger.warning(f"⚠️ Too many restarts for {service_name} ({recent_restarts} in last 5 min)")
            return False
        
        return True
    
    def _record_restart(self, service_name: str):
        """Record restart attempt"""
        if service_name not in self._restart_history:
            self._restart_history[service_name] = []
        self._restart_history[service_name].append(time.time())
        
        # Update shared state
        state = self._load_state()
        state["restart_history"][service_name] = self._restart_history[service_name]
        self._save_state(state)
    
    def acquire_environment(self) -> Tuple[str, Dict[str, int]]:
        """
        Acquire test environment with proper locking.
        Returns environment name and port mappings.
        """
        env_name = self._get_environment_name()
        
        with self._file_lock(f"env_{env_name}"):
            state = self._load_state()
            
            # Check if environment exists
            if env_name not in state["environments"]:
                logger.info(f"🔧 Creating new test environment: {env_name}")
                self._create_environment(env_name)
                state["environments"][env_name] = {
                    "created": datetime.now().isoformat(),
                    "test_id": self.test_id,
                    "type": self.environment_type.value,
                    "users": 1
                }
            else:
                state["environments"][env_name]["users"] = \
                    state["environments"][env_name].get("users", 0) + 1
                logger.info(f"♻️ Reusing existing environment: {env_name} (users: {state['environments'][env_name]['users']})")
            
            self._save_state(state)
            
            # Get port mappings
            ports = self._discover_ports(env_name)
            
            return env_name, ports
    
    def release_environment(self, env_name: str):
        """Release test environment"""
        with self._file_lock(f"env_{env_name}"):
            state = self._load_state()
            
            if env_name in state["environments"]:
                state["environments"][env_name]["users"] = \
                    max(0, state["environments"][env_name].get("users", 1) - 1)
                
                # Clean up if no users and dedicated environment
                if (state["environments"][env_name]["users"] == 0 and 
                    state["environments"][env_name]["type"] == EnvironmentType.DEDICATED.value):
                    logger.info(f"🧹 Cleaning up dedicated environment: {env_name}")
                    self._cleanup_environment(env_name)
                    del state["environments"][env_name]
                
                self._save_state(state)
    
    def _create_environment(self, env_name: str):
        """Create new Docker environment"""
        compose_file = self._get_compose_file()
        
        # Prepare environment variables
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = env_name
        env["DOCKER_ENV"] = "test"
        
        if self.use_production_images:
            env["DOCKER_TAG"] = "production"
            env["BUILD_TARGET"] = "production"
        
        # Set memory limits
        for service, config in self.SERVICES.items():
            env_key = f"{service.upper()}_MEMORY_LIMIT"
            env[env_key] = config.get("memory_limit", "512m")
        
        # Start services
        cmd = [
            "docker-compose",
            "-f", compose_file,
            "-p", env_name,
            "up", "-d"
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create environment: {result.stderr}")
        
        # Wait for services to be healthy
        self._wait_for_healthy(env_name)
    
    def _cleanup_environment(self, env_name: str):
        """Clean up Docker environment"""
        compose_file = self._get_compose_file()
        
        cmd = [
            "docker-compose",
            "-f", compose_file,
            "-p", env_name,
            "down", "--remove-orphans", "-v"
        ]
        
        subprocess.run(cmd, capture_output=True)
    
    def _get_compose_file(self) -> str:
        """Get appropriate docker-compose file"""
        compose_files = [
            "docker-compose.test.yml",
            "docker-compose.yml"
        ]
        
        for file_path in compose_files:
            if Path(file_path).exists():
                return file_path
        
        raise RuntimeError("No docker-compose files found")
    
    def _discover_ports(self, env_name: str) -> Dict[str, int]:
        """Discover port mappings for environment"""
        ports = {}
        
        for service, config in self.SERVICES.items():
            container_name = f"{env_name}_{service}_1"
            
            # Get port mapping
            cmd = [
                "docker", "port",
                container_name,
                str(config["port"])
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                # Parse output like "0.0.0.0:32768"
                host_port = result.stdout.strip().split(":")[-1]
                ports[service] = int(host_port)
            else:
                # Use default port
                ports[service] = config["port"]
        
        return ports
    
    def restart_service(self, service_name: str, force: bool = False) -> bool:
        """
        Restart a service with proper coordination and rate limiting.
        
        Args:
            service_name: Name of service to restart
            force: Force restart even if cooldown active
        
        Returns:
            True if restart successful
        """
        env_name = self._get_environment_name()
        
        # Check if restart allowed
        if not force and not self._check_restart_allowed(service_name):
            return False
        
        with self._file_lock(f"service_{service_name}"):
            # Update service status
            state = self._load_state()
            state["services"][service_name] = {
                "status": ServiceStatus.RESTARTING.value,
                "timestamp": datetime.now().isoformat()
            }
            self._save_state(state)
            
            # Record restart attempt
            self._record_restart(service_name)
            
            # Perform restart
            container_name = f"{env_name}_{service_name}_1"
            cmd = ["docker", "restart", container_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            success = result.returncode == 0
            
            # Update status
            state = self._load_state()
            state["services"][service_name] = {
                "status": ServiceStatus.HEALTHY.value if success else ServiceStatus.UNHEALTHY.value,
                "timestamp": datetime.now().isoformat()
            }
            self._save_state(state)
            
            if success:
                logger.info(f"✅ Successfully restarted {service_name}")
            else:
                logger.error(f"❌ Failed to restart {service_name}: {result.stderr}")
            
            return success
    
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get current service status"""
        state = self._load_state()
        
        if service_name in state["services"]:
            status_str = state["services"][service_name].get("status", "unknown")
            return ServiceStatus(status_str)
        
        return ServiceStatus.UNKNOWN
    
    def wait_for_services(self, services: Optional[List[str]] = None, timeout: int = 60) -> bool:
        """
        Wait for services to be healthy.
        
        Args:
            services: List of services to wait for (None = all)
            timeout: Maximum time to wait
        
        Returns:
            True if all services healthy
        """
        if services is None:
            services = list(self.SERVICES.keys())
        
        env_name = self._get_environment_name()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_healthy = True
            
            for service in services:
                if not self._is_service_healthy(env_name, service):
                    all_healthy = False
                    break
            
            if all_healthy:
                return True
            
            time.sleep(2)
        
        return False
    
    def _is_service_healthy(self, env_name: str, service_name: str) -> bool:
        """Check if service is healthy"""
        container_name = f"{env_name}_{service_name}_1"
        
        # Check container status
        cmd = ["docker", "inspect", "--format='{{.State.Health.Status}}'", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            status = result.stdout.strip().strip("'")
            return status == "healthy" or status == "none"  # Some containers don't have health checks
        
        return False
    
    def _wait_for_healthy(self, env_name: str, timeout: int = 60):
        """Wait for all services in environment to be healthy"""
        logger.info(f"⏳ Waiting for services to be healthy in {env_name}...")
        
        if self.wait_for_services(timeout=timeout):
            logger.info(f"✅ All services healthy in {env_name}")
        else:
            logger.warning(f"⚠️ Some services failed to become healthy in {env_name}")
    
    # ASYNC ORCHESTRATION METHODS
    
    async def orchestrate_services(self) -> Tuple[bool, Dict[str, ServiceHealth]]:
        """
        Orchestrate all required services for E2E testing.
        Combines async orchestration with centralized Docker management.
        
        Returns:
            Tuple of (success, service_health_report)
        """
        logger.info("🚀 Starting E2E Service Orchestration with Unified Management")
        logger.info(f"Environment: {self.environment} ({self.environment_type.value})")
        logger.info(f"Required services: {self.config.required_services}")
        
        start_time = time.time()
        
        try:
            # Phase 1: Check Docker availability
            if not await self._check_docker_availability():
                return False, self._create_failure_report("Docker not available")
            
            # Phase 2: Acquire environment with centralized coordination
            env_name, ports = self.acquire_environment()
            logger.info(f"✅ Acquired environment: {env_name}")
            
            # Phase 3: Start missing services with rate limiting
            startup_success = await self._start_missing_services_coordinated()
            if not startup_success:
                return False, self._create_failure_report("Service startup failed")
            
            # Phase 4: Wait for services to be healthy
            health_success = await self._wait_for_services_healthy()
            if not health_success:
                return False, self._create_failure_report("Service health checks failed")
            
            # Phase 5: Configure environment variables
            self._configure_service_environment()
            
            elapsed = time.time() - start_time
            logger.info(f"✅ E2E Service Orchestration completed successfully in {elapsed:.1f}s")
            
            return True, self.service_health
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ E2E Service Orchestration failed after {elapsed:.1f}s: {e}")
            return False, self._create_failure_report(f"Orchestration exception: {e}")

    async def _check_docker_availability(self) -> bool:
        """Check if Docker is available and docker-compose files exist."""
        # Check Docker daemon
        if not self.port_discovery.docker_available:
            logger.error("❌ Docker daemon not available - E2E tests require Docker")
            logger.error("💡 Fix: Start Docker Desktop or install Docker")
            return False
        
        # Check for docker-compose files
        try:
            compose_file = self._get_compose_file()
            logger.info(f"✅ Docker available, using compose file: {compose_file}")
            return True
        except RuntimeError:
            logger.error("❌ No docker-compose files found")
            logger.error("💡 Expected: docker-compose.test.yml or docker-compose.yml")
            return False

    async def _start_missing_services_coordinated(self) -> bool:
        """Start missing Docker services with centralized coordination."""
        logger.info("🔄 Checking and starting required services with rate limiting...")
        
        # Check current service status
        port_mappings = self.port_discovery.discover_all_ports()
        missing_services = []
        
        for service in self.config.required_services:
            if service not in port_mappings or not port_mappings[service].is_available:
                # Check rate limiting before restart
                if self._check_restart_allowed(service):
                    missing_services.append(service)
                else:
                    logger.warning(f"⚠️ Service {service} restart blocked by rate limiting")
        
        if not missing_services:
            logger.info("✅ All required services are already running")
            return True
        
        logger.info(f"⚡ Starting missing services: {missing_services}")
        
        # Record restart attempts
        for service in missing_services:
            self._record_restart(service)
        
        # Start services using existing environment acquisition
        env_name = self._get_environment_name()
        
        # Use compose to start services
        compose_file = self._get_compose_file()
        service_names = self._map_to_compose_services(missing_services)
        
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = env_name
        env["DOCKER_ENV"] = "test"
        
        if self.use_production_images:
            env["DOCKER_TAG"] = "production"
            env["BUILD_TARGET"] = "production"
        
        # Set memory limits
        for service, config in self.SERVICES.items():
            env_key = f"{service.upper()}_MEMORY_LIMIT"
            env[env_key] = config.get("memory_limit", "512m")
        
        cmd = ["docker", "compose", "-f", compose_file, "-p", env_name, "up", "-d"] + service_names
        logger.info(f"🚀 Executing: {' '.join(cmd)}")
        
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), 
                timeout=self.config.startup_timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Services started successfully")
                self.started_services.update(missing_services)
                
                # Wait a moment for services to initialize
                await asyncio.sleep(3)
                return True
            else:
                logger.error(f"❌ Service startup failed with return code {result.returncode}")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Service startup timed out after {self.config.startup_timeout}s")
            return False
        except Exception as e:
            logger.error(f"❌ Service startup failed: {e}")
            return False

    async def _wait_for_services_healthy(self) -> bool:
        """Wait for all required services to be healthy using async health checks."""
        logger.info("🏥 Waiting for services to be healthy...")
        
        # Get current port mappings
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Create health check tasks
        health_tasks = []
        for service in self.config.required_services:
            if service in port_mappings:
                task = self._check_service_health_async(service, port_mappings[service])
                health_tasks.append(task)
        
        if not health_tasks:
            logger.error("❌ No services to check - this shouldn't happen")
            return False
        
        # Wait for all health checks to complete
        try:
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            # Process results
            all_healthy = True
            for i, result in enumerate(health_results):
                service = self.config.required_services[i]
                
                if isinstance(result, Exception):
                    logger.error(f"❌ Health check failed for {service}: {result}")
                    all_healthy = False
                    self.service_health[service] = ServiceHealth(
                        service_name=service,
                        is_healthy=False,
                        port=0,
                        response_time_ms=0,
                        error_message=str(result)
                    )
                else:
                    self.service_health[service] = result
                    if result.is_healthy:
                        logger.info(f"✅ {service} healthy on port {result.port} ({result.response_time_ms:.1f}ms)")
                    else:
                        logger.error(f"❌ {service} unhealthy: {result.error_message}")
                        all_healthy = False
            
            return all_healthy
            
        except Exception as e:
            logger.error(f"❌ Health check coordination failed: {e}")
            return False

    async def _check_service_health_async(self, service: str, mapping: ServicePortMapping) -> ServiceHealth:
        """Check health of a specific service with async implementation."""
        start_time = time.time()
        
        for attempt in range(self.config.health_check_retries):
            try:
                if service in ["postgres", "redis", "clickhouse"]:
                    # Database services - check port connectivity
                    is_healthy = await self._check_port_connectivity(
                        mapping.host, mapping.external_port, self.config.health_check_timeout
                    )
                    if is_healthy:
                        response_time = (time.time() - start_time) * 1000
                        return ServiceHealth(
                            service_name=service,
                            is_healthy=True,
                            port=mapping.external_port,
                            response_time_ms=response_time,
                            last_check=time.time()
                        )
                
                elif service in ["backend", "auth", "frontend"]:
                    # HTTP services - check health endpoint
                    health_url = f"http://{mapping.host}:{mapping.external_port}/health"
                    is_healthy = await self._check_http_health(health_url, self.config.health_check_timeout)
                    if is_healthy:
                        response_time = (time.time() - start_time) * 1000
                        return ServiceHealth(
                            service_name=service,
                            is_healthy=True,
                            port=mapping.external_port,
                            response_time_ms=response_time,
                            last_check=time.time()
                        )
                
                # Wait before retry
                if attempt < self.config.health_check_retries - 1:
                    await asyncio.sleep(self.config.health_check_interval)
                    
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed for {service}: {e}")
        
        # All attempts failed
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            service_name=service,
            is_healthy=False,
            port=mapping.external_port,
            response_time_ms=response_time,
            error_message=f"Failed after {self.config.health_check_retries} attempts",
            last_check=time.time()
        )

    async def _check_port_connectivity(self, host: str, port: int, timeout: float) -> bool:
        """Check if a port is connectable."""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _check_http_health(self, url: str, timeout: float) -> bool:
        """Check HTTP health endpoint."""
        try:
            # Use aiohttp if available, otherwise try basic connectivity
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        return response.status == 200
            except ImportError:
                # Fallback to port connectivity check
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return await self._check_port_connectivity(parsed.hostname, parsed.port, timeout)
        except Exception:
            return False

    def _configure_service_environment(self) -> None:
        """Configure environment variables with discovered service ports."""
        env = get_env()
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Set service URLs for E2E tests
        for service, mapping in port_mappings.items():
            if mapping.is_available:
                service_url = self._build_service_url(service, mapping)
                if service_url:
                    env_var = f"{service.upper()}_SERVICE_URL"
                    env.set(env_var, service_url, source="unified_docker_manager")
                    logger.info(f"🔧 {env_var}={service_url}")
        
        # Set specific URLs needed by E2E tests
        if "backend" in port_mappings and port_mappings["backend"].is_available:
            backend_port = port_mappings["backend"].external_port
            env.set("BACKEND_URL", f"http://localhost:{backend_port}", source="unified_docker_manager")
            env.set("WEBSOCKET_URL", f"ws://localhost:{backend_port}/ws", source="unified_docker_manager")
        
        if "auth" in port_mappings and port_mappings["auth"].is_available:
            auth_port = port_mappings["auth"].external_port
            env.set("AUTH_SERVICE_URL", f"http://localhost:{auth_port}", source="unified_docker_manager")
        
        # Set database URLs
        if "postgres" in port_mappings and port_mappings["postgres"].is_available:
            postgres_port = port_mappings["postgres"].external_port
            db_url = f"postgresql://test:test@localhost:{postgres_port}/netra_test"
            env.set("DATABASE_URL", db_url, source="unified_docker_manager")
        
        if "redis" in port_mappings and port_mappings["redis"].is_available:
            redis_port = port_mappings["redis"].external_port
            redis_url = f"redis://localhost:{redis_port}/1"
            env.set("REDIS_URL", redis_url, source="unified_docker_manager")

    def _build_service_url(self, service: str, mapping: ServicePortMapping) -> Optional[str]:
        """Build service URL from port mapping."""
        if service in ["backend", "auth", "frontend"]:
            return f"http://{mapping.host}:{mapping.external_port}"
        elif service == "postgres":
            return f"postgresql://test:test@{mapping.host}:{mapping.external_port}/netra_test"
        elif service == "redis":
            return f"redis://{mapping.host}:{mapping.external_port}/1"
        elif service == "clickhouse":
            return f"http://{mapping.host}:{mapping.external_port}"
        return None

    def _map_to_compose_services(self, services: List[str]) -> List[str]:
        """Map service names to docker-compose service names."""
        # Map generic service names to compose service names
        service_mapping = {
            "postgres": "test-postgres",
            "redis": "test-redis", 
            "clickhouse": "test-clickhouse",
            "backend": "backend",  # These might be built on-demand
            "auth": "auth",
            "frontend": "frontend"
        }
        
        return [service_mapping.get(service, service) for service in services]

    def _create_failure_report(self, reason: str) -> Dict[str, ServiceHealth]:
        """Create failure report for orchestration."""
        failure_health = {}
        for service in self.config.required_services:
            failure_health[service] = ServiceHealth(
                service_name=service,
                is_healthy=False,
                port=0,
                response_time_ms=0,
                error_message=reason,
                last_check=time.time()
            )
        return failure_health

    async def cleanup_services(self) -> None:
        """Cleanup services that were started by orchestrator."""
        if not self.started_services:
            return
        
        logger.info(f"🧹 Cleaning up started services: {list(self.started_services)}")
        
        # Release environment through centralized management
        env_name = self._get_environment_name()
        self.release_environment(env_name)
        
        # Additional cleanup if needed
        compose_file = self._get_compose_file()
        if compose_file:
            try:
                service_names = self._map_to_compose_services(list(self.started_services))
                cmd = ["docker", "compose", "-f", compose_file, "-p", env_name, "stop"] + service_names
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await asyncio.wait_for(result.communicate(), timeout=30)
                
                if result.returncode == 0:
                    logger.info("✅ Services stopped successfully")
                else:
                    logger.warning("⚠️ Some services may not have stopped cleanly")
                    
            except Exception as e:
                logger.warning(f"⚠️ Service cleanup failed: {e}")

    def get_health_report(self) -> str:
        """Generate comprehensive health report."""
        if not self.service_health:
            return "No service health data available"
        
        report_lines = [
            "\n" + "=" * 60,
            "UNIFIED DOCKER MANAGER HEALTH REPORT", 
            "=" * 60,
            f"Environment: {self.environment} ({self.environment_type.value})",
            f"Services checked: {len(self.service_health)}",
        ]
        
        healthy_count = sum(1 for health in self.service_health.values() if health.is_healthy)
        report_lines.append(f"Healthy services: {healthy_count}/{len(self.service_health)}")
        report_lines.append("")
        
        for service, health in self.service_health.items():
            status = "✅ HEALTHY" if health.is_healthy else "❌ UNHEALTHY"
            report_lines.append(f"{service:12} | {status:12} | Port: {health.port:5} | {health.response_time_ms:6.1f}ms")
            if health.error_message:
                report_lines.append(f"             | Error: {health.error_message}")
        
        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def cleanup_old_environments(self, max_age_hours: int = 24):
        """Clean up old test environments"""
        with self._file_lock("cleanup"):
            state = self._load_state()
            now = datetime.now()
            
            environments_to_remove = []
            
            for env_name, env_data in state["environments"].items():
                # Skip shared environment
                if env_data["type"] == EnvironmentType.SHARED.value:
                    continue
                
                # Check age
                created = datetime.fromisoformat(env_data["created"])
                age_hours = (now - created).total_seconds() / 3600
                
                if age_hours > max_age_hours and env_data.get("users", 0) == 0:
                    environments_to_remove.append(env_name)
            
            # Clean up old environments
            for env_name in environments_to_remove:
                logger.info(f"🧹 Cleaning up old environment: {env_name}")
                self._cleanup_environment(env_name)
                del state["environments"][env_name]
            
            self._save_state(state)

    def get_statistics(self) -> Dict[str, Any]:
        """Get Docker management statistics with orchestration data."""
        state = self._load_state()
        
        stats = {
            "environments": len(state["environments"]),
            "active_environments": sum(1 for e in state["environments"].values() if e.get("users", 0) > 0),
            "services": {},
            "restart_counts": {},
            "health_summary": {
                "total_services": len(self.service_health),
                "healthy_services": sum(1 for h in self.service_health.values() if h.is_healthy),
                "average_response_time": sum(h.response_time_ms for h in self.service_health.values()) / len(self.service_health) if self.service_health else 0
            }
        }
        
        # Service statistics
        for service, data in state["services"].items():
            stats["services"][service] = data.get("status", "unknown")
        
        # Restart statistics
        for service, history in self._restart_history.items():
            stats["restart_counts"][service] = len(history)
        
        return stats

    # =====================================
    # CONSOLIDATED FEATURES FROM OTHER DOCKER MANAGERS
    # =====================================
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        if hasattr(self, '_docker_available') and self._docker_available is not None:
            return self._docker_available
            
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._docker_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._docker_available = False
            
        return self._docker_available
    
    def get_effective_mode(self, requested_mode: Optional[ServiceMode] = None) -> ServiceMode:
        """
        Get the effective service mode based on Docker availability and configuration.
        
        Args:
            requested_mode: Requested service mode, defaults to DOCKER
            
        Returns:
            Effective service mode to use
        """
        if requested_mode is None:
            requested_mode = ServiceMode.DOCKER
            
        # Force mock mode in test environments if explicitly requested
        if requested_mode == ServiceMode.MOCK:
            return ServiceMode.MOCK
            
        # Fall back to local if Docker not available
        if requested_mode == ServiceMode.DOCKER and not self.is_docker_available():
            logger.warning("Docker not available, falling back to local mode")
            return ServiceMode.LOCAL
            
        return requested_mode
    
    async def check_container_reusable(self, service: str) -> bool:
        """
        Check if existing container can be reused (smart container reuse).
        
        Args:
            service: Service name to check
            
        Returns:
            True if container exists and is healthy/reusable
        """
        try:
            # Get container status using docker-compose ps
            cmd = ["docker-compose", "-f", self._get_compose_file(), 
                   "-p", f"netra-{self.environment}", "ps", "--format", "json", service]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0 or not result.stdout.strip():
                return False  # No container exists
                
            container_data = json.loads(result.stdout.strip())
            state = container_data.get("State", "").lower()
            health = container_data.get("Health", "")
            
            # Container is reusable if running and healthy (or no health check)
            if state == "running":
                return health in ["", "healthy"] or health.startswith("healthy")
                
            return False
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error checking container reusability for {service}: {e}")
            return False
    
    async def start_services_smart(self, services: List[str], wait_healthy: bool = True) -> bool:
        """
        Start services only if they're not already healthy (smart container reuse).
        
        Args:
            services: List of service names to start
            wait_healthy: Wait for services to become healthy
            
        Returns:
            True if all services started successfully
        """
        logger.info(f"Smart starting services: {', '.join(services)}")
        
        services_to_start = []
        reused_services = []
        
        # Check which services can be reused
        for service in services:
            if await self.check_container_reusable(service):
                reused_services.append(service)
                logger.info(f"Reusing healthy container for {service}")
            else:
                services_to_start.append(service)
        
        if reused_services:
            logger.info(f"Reused {len(reused_services)} healthy containers: {', '.join(reused_services)}")
        
        # Start only services that need starting
        if services_to_start:
            logger.info(f"Starting {len(services_to_start)} services: {', '.join(services_to_start)}")
            
            cmd = ["docker-compose", "-f", self._get_compose_file(),
                   "-p", f"netra-{self.environment}", "up", "-d"] + services_to_start
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    logger.error(f"Failed to start services: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout starting services: {', '.join(services_to_start)}")
                return False
        
        # Wait for health if requested
        if wait_healthy:
            return self.wait_for_services(services, timeout=self.HEALTH_CHECK_TIMEOUT)
            
        return True
    
    async def graceful_shutdown(self, services: Optional[List[str]] = None, timeout: int = 30) -> bool:
        """
        Perform graceful shutdown of services with proper cleanup.
        
        Args:
            services: Services to shutdown, None for all
            timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            True if shutdown completed successfully
        """
        logger.info(f"Gracefully shutting down services: {services or 'all'}")
        
        try:
            # Build the shutdown command
            cmd = ["docker-compose", "-f", self._get_compose_file(),
                   "-p", f"netra-{self.environment}", "down"]
            
            if services:
                # For specific services, use stop instead of down
                cmd = ["docker-compose", "-f", self._get_compose_file(),
                       "-p", f"netra-{self.environment}", "stop", "-t", str(timeout)] + services
            else:
                cmd.extend(["-t", str(timeout)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            
            if result.returncode != 0:
                logger.warning(f"Graceful shutdown had issues: {result.stderr}")
                # Try force shutdown if graceful failed
                return await self.force_shutdown(services)
            
            logger.info("Graceful shutdown completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Graceful shutdown timed out after {timeout}s, attempting force shutdown")
            return await self.force_shutdown(services)
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            return False
    
    async def force_shutdown(self, services: Optional[List[str]] = None) -> bool:
        """
        Force shutdown services (kill containers).
        
        Args:
            services: Services to force shutdown, None for all
            
        Returns:
            True if force shutdown completed
        """
        logger.warning(f"Force shutting down services: {services or 'all'}")
        
        try:
            cmd = ["docker-compose", "-f", self._get_compose_file(),
                   "-p", f"netra-{self.environment}", "kill"]
            
            if services:
                cmd.extend(services)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Also remove containers
            cmd_rm = ["docker-compose", "-f", self._get_compose_file(),
                      "-p", f"netra-{self.environment}", "rm", "-f"]
            if services:
                cmd_rm.extend(services)
            
            subprocess.run(cmd_rm, capture_output=True, text=True, timeout=30)
            
            logger.info("Force shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during force shutdown: {e}")
            return False
    
    async def reset_test_data(self, services: Optional[List[str]] = None) -> bool:
        """
        Reset test data without restarting containers.
        
        Args:
            services: Services to reset data for, None for all applicable
            
        Returns:
            True if data reset completed successfully
        """
        if services is None:
            services = ["postgres", "redis"]
            
        logger.info(f"Resetting test data for services: {', '.join(services)}")
        success = True
        
        for service in services:
            if service == "postgres":
                success &= await self._reset_postgres_data()
            elif service == "redis":
                success &= await self._reset_redis_data()
            else:
                logger.warning(f"Test data reset not implemented for service: {service}")
                
        return success
    
    async def _reset_postgres_data(self) -> bool:
        """Reset PostgreSQL test data."""
        try:
            # Execute SQL commands to clear test data
            sql_commands = [
                "TRUNCATE TABLE users CASCADE;",
                "TRUNCATE TABLE sessions CASCADE;", 
                "TRUNCATE TABLE threads CASCADE;",
                "TRUNCATE TABLE messages CASCADE;"
            ]
            
            for sql in sql_commands:
                cmd = ["docker-compose", "-f", self._get_compose_file(),
                       "-p", f"netra-{self.environment}", "exec", "-T", "postgres",
                       "psql", "-U", "netra", "-d", "netra", "-c", sql]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    logger.warning(f"Failed to execute SQL: {sql} - {result.stderr}")
                    
            logger.info("PostgreSQL test data reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting PostgreSQL data: {e}")
            return False
    
    async def _reset_redis_data(self) -> bool:
        """Reset Redis test data."""
        try:
            cmd = ["docker-compose", "-f", self._get_compose_file(),
                   "-p", f"netra-{self.environment}", "exec", "-T", "redis",
                   "redis-cli", "FLUSHALL"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Failed to flush Redis: {result.stderr}")
                return False
                
            logger.info("Redis test data reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting Redis data: {e}")
            return False
    
    def get_enhanced_container_status(self, services: Optional[List[str]] = None) -> Dict[str, ContainerInfo]:
        """
        Get detailed container status information (enhanced from DockerHealthManager).
        
        Args:
            services: Services to get status for, None for all
            
        Returns:
            Dictionary mapping service name to ContainerInfo
        """
        cmd = ["docker-compose", "-f", self._get_compose_file(),
               "-p", f"netra-{self.environment}", "ps", "--format", "json"]
        
        if services:
            cmd.extend(services)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                if services:
                    # Return stopped status for requested services
                    return {
                        service: ContainerInfo(
                            name=f"netra-{self.environment}-{service}",
                            service=service,
                            container_id="",
                            image="",
                            state=ContainerState.STOPPED
                        ) for service in services
                    }
                return {}
            
            containers = {}
            
            if not result.stdout.strip():
                if services:
                    return {
                        service: ContainerInfo(
                            name=f"netra-{self.environment}-{service}",
                            service=service,
                            container_id="",
                            image="",
                            state=ContainerState.STOPPED
                        ) for service in services
                    }
                return {}
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    container_data = json.loads(line)
                    name = container_data.get("Name", "")
                    service = container_data.get("Service", "")
                    state_str = container_data.get("State", "").lower()
                    health = container_data.get("Health", "")
                    
                    # Determine container state
                    if state_str == "running":
                        if health == "healthy":
                            state = ContainerState.HEALTHY
                        elif health == "unhealthy":
                            state = ContainerState.UNHEALTHY
                        elif health == "starting":
                            state = ContainerState.STARTING
                        else:
                            state = ContainerState.RUNNING
                    else:
                        state = ContainerState.STOPPED
                    
                    containers[service] = ContainerInfo(
                        name=name,
                        service=service,
                        container_id=container_data.get("ID", ""),
                        image=container_data.get("Image", ""),
                        state=state,
                        health=health,
                        uptime=container_data.get("RunningFor", "")
                    )
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
                
            return containers
            
        except Exception as e:
            logger.error(f"Error getting enhanced container status: {e}")
            return {}
    
    def cleanup_orphaned_containers(self) -> bool:
        """
        Clean up orphaned containers and networks.
        
        Returns:
            True if cleanup completed successfully
        """
        logger.info("Cleaning up orphaned containers and networks")
        
        try:
            # Remove orphaned containers
            cmd = ["docker-compose", "-f", self._get_compose_file(),
                   "-p", f"netra-{self.environment}", "down", "--remove-orphans"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.warning(f"Orphan cleanup had issues: {result.stderr}")
                return False
            
            # Prune unused networks
            subprocess.run(["docker", "network", "prune", "-f"], 
                         capture_output=True, text=True, timeout=30)
            
            logger.info("Orphan cleanup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during orphan cleanup: {e}")
            return False
    
    # =====================================
    # DOCKER INTROSPECTION AND MONITORING
    # =====================================
    
    def create_introspector(self) -> DockerIntrospector:
        """
        Create a Docker introspector for log analysis and issue detection.
        
        Returns:
            Configured DockerIntrospector instance
        """
        compose_file = self._get_compose_file()
        project_name = f"netra-{self.environment}"
        
        return DockerIntrospector(compose_file, project_name)
    
    async def analyze_service_health(self, 
                                   services: Optional[List[str]] = None,
                                   since: str = "1h",
                                   max_lines: int = 500) -> IntrospectionReport:
        """
        Perform comprehensive health analysis of services.
        
        Args:
            services: Services to analyze, None for all
            since: Time window for analysis (e.g., '1h', '30m')
            max_lines: Maximum log lines to analyze
            
        Returns:
            Detailed introspection report
        """
        logger.info(f"Analyzing service health for: {services or 'all services'}")
        
        introspector = self.create_introspector()
        report = introspector.analyze_services(
            services=services,
            since=since,
            max_lines=max_lines
        )
        
        # Log critical issues
        if report.has_critical_issues:
            logger.error(f"Found {len(report.critical_issues)} critical issues!")
            for issue in report.critical_issues:
                logger.error(f"  - {issue.title}")
        
        return report


# Convenience functions for backward compatibility and async orchestration
_default_manager = None


def get_default_manager() -> UnifiedDockerManager:
    """Get or create default Docker manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = UnifiedDockerManager()
    return _default_manager


def restart_service(service_name: str, force: bool = False) -> bool:
    """Restart service using default manager"""
    return get_default_manager().restart_service(service_name, force)


def wait_for_services(services: Optional[List[str]] = None, timeout: int = 60) -> bool:
    """Wait for services using default manager"""
    return get_default_manager().wait_for_services(services, timeout)


async def orchestrate_e2e_services(
    required_services: Optional[List[str]] = None,
    timeout: float = 60.0,
    environment_type: EnvironmentType = EnvironmentType.SHARED,
    use_production_images: bool = True
) -> Tuple[bool, UnifiedDockerManager]:
    """
    Convenient async function to orchestrate E2E services with unified management.
    
    Args:
        required_services: List of required services (default: postgres, redis, backend, auth)
        timeout: Startup timeout in seconds
        environment_type: Type of environment (shared/dedicated/production)
        use_production_images: Use production Docker images for memory efficiency
        
    Returns:
        Tuple of (success, manager)
    """
    if required_services is None:
        required_services = ["postgres", "redis", "backend", "auth"]
    
    config = OrchestrationConfig(
        required_services=required_services,
        startup_timeout=timeout
    )
    
    manager = UnifiedDockerManager(
        config=config,
        environment_type=environment_type,
        use_production_images=use_production_images
    )
    
    success, _ = await manager.orchestrate_services()
    
    return success, manager


# Pytest integration
async def pytest_orchestrate_services():
    """Pytest integration for service orchestration."""
    success, manager = await orchestrate_e2e_services()
    
    if not success:
        logger.error(manager.get_health_report())
        raise RuntimeError("E2E Service orchestration failed - cannot run tests")
    
    logger.info(manager.get_health_report())
    return manager


# Legacy compatibility classes
class ServiceOrchestrator(UnifiedDockerManager):
    """Legacy compatibility class - redirects to UnifiedDockerManager"""
    
    def __init__(self, config: Optional[OrchestrationConfig] = None):
        """Initialize with legacy ServiceOrchestrator interface"""
        super().__init__(config=config, environment_type=EnvironmentType.SHARED, use_production_images=True)
        logger.info("ServiceOrchestrator is deprecated - using UnifiedDockerManager")


class CentralizedDockerManager(UnifiedDockerManager):
    """Legacy compatibility class - redirects to UnifiedDockerManager"""
    
    def __init__(self, 
                 environment_type: EnvironmentType = EnvironmentType.SHARED,
                 test_id: Optional[str] = None,
                 use_production_images: bool = True):
        """Initialize with legacy CentralizedDockerManager interface"""
        super().__init__(
            config=OrchestrationConfig(),
            environment_type=environment_type, 
            test_id=test_id,
            use_production_images=use_production_images
        )
        logger.info("CentralizedDockerManager is deprecated - using UnifiedDockerManager")