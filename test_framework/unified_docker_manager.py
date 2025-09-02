"""
Unified Docker Management System - SSOT for Docker Operations

Combines the best features of ServiceOrchestrator and UnifiedDockerManager:
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
# CRITICAL: Import Docker rate limiter to prevent daemon crashes
from test_framework.docker_rate_limiter import execute_docker_command
from test_framework.dynamic_port_allocator import (
    DynamicPortAllocator, 
    PortRange, 
    PortAllocationResult,
    allocate_test_ports,
    release_test_ports
)
from test_framework.docker_rate_limiter import (
    DockerRateLimiter,
    execute_docker_command,
    get_docker_rate_limiter
)

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
    
    # Service configuration - ports will be dynamically allocated
    SERVICES = {
        "backend": {
            "container": "netra-backend",
            "default_port": 8000,  # Internal container port
            "health_endpoint": "/health",
            "memory_limit": "2048m"
        },
        "frontend": {
            "container": "netra-frontend", 
            "default_port": 3000,  # Internal container port
            "health_endpoint": "/",
            "memory_limit": "1024m"  # Increased for better stability
        },
        "auth": {
            "container": "netra-auth",
            "default_port": 8081,  # Internal container port (corrected from 8001)
            "health_endpoint": "/health",
            "memory_limit": "1024m"  # Increased from 512m to prevent memory pressure (73% usage)
        },
        "postgres": {
            "container": "netra-postgres",
            "default_port": 5432,  # Internal container port
            "health_cmd": "pg_isready",
            "memory_limit": "1024m"  # Increased for better performance
        },
        "redis": {
            "container": "netra-redis",
            "default_port": 6379,  # Internal container port
            "health_cmd": "redis-cli ping",
            "memory_limit": "512m"  # Increased from 256m for better performance
        },
        "clickhouse": {
            "container": "netra-clickhouse",
            "default_port": 8123,  # Internal container port
            "health_endpoint": "/ping",
            "memory_limit": "1024m"  # Increased for better analytics performance
        }
    }
    
    def __init__(self, 
                 config: Optional[OrchestrationConfig] = None,
                 environment_type: EnvironmentType = EnvironmentType.SHARED,
                 test_id: Optional[str] = None,
                 use_production_images: bool = True,  # Default to memory-optimized production images
                 mode: ServiceMode = ServiceMode.DOCKER,
                 use_alpine: bool = False):  # Add Alpine container support
        """
        Initialize unified Docker manager with orchestration capabilities.
        
        Args:
            config: Orchestration configuration
            environment_type: Type of test environment
            test_id: Unique test identifier for dedicated environments
            use_production_images: Use production Docker images for memory efficiency
            mode: Service execution mode (docker, local, mock)
            use_alpine: Use Alpine-based Docker compose files for minimal container size
        """
        self.config = config or OrchestrationConfig()
        self.environment_type = environment_type
        self.test_id = test_id or self._generate_test_id()
        self.use_production_images = use_production_images
        self.mode = mode
        self.use_alpine = use_alpine
        
        # Port discovery and allocation
        self.port_discovery = DockerPortDiscovery(use_test_services=True)
        self.port_allocator = self._initialize_port_allocator()
        self.allocated_ports: Dict[str, int] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        self.started_services: Set[str] = set()
        
        # Container management
        self._containers: Dict[str, ContainerInfo] = {}
        self._compose_config: Optional[Dict] = None
        self._docker_available = None
        self._running_services = set()
        
        # Network management
        self._network_name: Optional[str] = None
        self._project_name: Optional[str] = None
        
        # Initialize lock directory
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for locks
        self._local = threading.local()
        
        # Restart tracking
        self._restart_history: Dict[str, List[float]] = {}
        
        # Track environment setup
        env = get_env()
        self.environment = env.get("TEST_ENV", "test")
        
        # Cleanup scheduler integration (optional)
        self._cleanup_scheduler = None
        self._enable_cleanup_scheduler = env.get("ENABLE_DOCKER_CLEANUP_SCHEDULER", "false").lower() == "true"
        
        # Ensure PROJECT_ROOT is set for docker-compose file detection
        if not env.get("PROJECT_ROOT"):
            # Calculate project root from this file's location
            current_file = Path(__file__)
            project_root = current_file.parent.parent  # Go up from test_framework to project root
            env.set("PROJECT_ROOT", str(project_root), source="unified_docker_manager")
        
        # Dynamic port allocation will replace hardcoded ports
        self._docker_ports = {}  # Will be populated dynamically
        self._local_ports = {}   # Will be populated dynamically
        
        # Initialize Docker rate limiter
        self.docker_rate_limiter = get_docker_rate_limiter()
        
        # Initialize state
        self._load_state()
    
    def _generate_test_id(self) -> str:
        """Generate unique test ID"""
        timestamp = datetime.now().isoformat()
        pid = os.getpid()
        return hashlib.md5(f"{timestamp}_{pid}".encode()).hexdigest()[:8]
    
    def _initialize_port_allocator(self) -> DynamicPortAllocator:
        """Initialize the dynamic port allocator based on environment type."""
        # Map environment types to port ranges
        port_range_map = {
            EnvironmentType.SHARED: PortRange.SHARED_TEST,
            EnvironmentType.DEDICATED: PortRange.DEDICATED_TEST,
            EnvironmentType.PRODUCTION: PortRange.STAGING,
            EnvironmentType.DEVELOPMENT: PortRange.DEVELOPMENT
        }
        
        port_range = port_range_map.get(self.environment_type, PortRange.SHARED_TEST)
        
        return DynamicPortAllocator(
            port_range=port_range,
            environment_id=self._get_environment_name(),
            test_id=self.test_id
        )
    
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
    
    def _get_project_name(self) -> str:
        """Get unique project name for Docker Compose isolation."""
        if not self._project_name:
            # Generate unique project name for parallel test isolation
            if self.environment_type == EnvironmentType.DEDICATED:
                self._project_name = f"netra-test-{self.test_id}"
            else:
                # For shared environments, add a timestamp to ensure uniqueness
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                self._project_name = f"netra-{self.environment}-{timestamp}-{self.test_id[:8]}"
        return self._project_name
    
    def _allocate_service_ports(self) -> Dict[str, int]:
        """Allocate dynamic ports for all services."""
        if self.allocated_ports:
            return self.allocated_ports
            
        logger.info(f"Allocating dynamic ports for environment {self._get_project_name()}")
        
        # Allocate ports for each service
        service_ports = {}
        for service_name, service_config in self.SERVICES.items():
            try:
                # Allocate a port for this service
                result = self.port_allocator.allocate_port(
                    service_name=service_name,
                    preferred_port=service_config['default_port']
                )
                
                if result.success:
                    service_ports[service_name] = result.port
                    logger.debug(f"Allocated port {result.port} for {service_name}")
                else:
                    # Fall back to finding a random available port
                    fallback_port = self._find_available_port()
                    service_ports[service_name] = fallback_port
                    logger.warning(f"Using fallback port {fallback_port} for {service_name}")
                    
            except Exception as e:
                logger.error(f"Failed to allocate port for {service_name}: {e}")
                # Use a fallback port
                fallback_port = self._find_available_port()
                service_ports[service_name] = fallback_port
        
        self.allocated_ports = service_ports
        return service_ports
    
    def _find_available_port(self) -> int:
        """Find an available port using socket binding."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _setup_network(self) -> bool:
        """Setup Docker network for this test run."""
        if self._network_name:
            return True
            
        project_name = self._get_project_name()
        network_name = f"{project_name}_default"
        
        try:
            # Check if network already exists
            check_cmd = ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"]
            result = self.docker_rate_limiter.execute_docker_command(check_cmd, timeout=10)
            
            if network_name not in result.stdout:
                # Create the network
                create_cmd = ["docker", "network", "create", network_name]
                result = self.docker_rate_limiter.execute_docker_command(create_cmd, timeout=30)
                
                if result.returncode != 0:
                    logger.error(f"Failed to create network {network_name}: {result.stderr}")
                    return False
                    
                logger.info(f"Created Docker network: {network_name}")
            else:
                logger.info(f"Using existing Docker network: {network_name}")
            
            self._network_name = network_name
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup network: {e}")
            return False
    
    def _cleanup_network(self) -> bool:
        """Clean up Docker network for this test run."""
        if not self._network_name:
            return True
            
        try:
            # Remove the network
            cmd = ["docker", "network", "rm", self._network_name]
            result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=30)
            
            if result.returncode != 0:
                if "not found" not in result.stderr.lower():
                    logger.warning(f"Failed to remove network {self._network_name}: {result.stderr}")
                    return False
            
            logger.info(f"Removed Docker network: {self._network_name}")
            self._network_name = None
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup network: {e}")
            return False
    
    def safe_container_remove(self, container_name: str, timeout: int = 10) -> bool:
        """
        Safely remove container with graceful shutdown.
        
        This replaces dangerous 'docker rm -f' patterns that can crash Docker daemon.
        
        Args:
            container_name: Name or ID of container to remove
            timeout: Seconds to wait for graceful stop
            
        Returns:
            True if container was safely removed or didn't exist
        """
        try:
            # First check if container exists
            inspect_cmd = ["docker", "inspect", container_name]
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)
            
            if inspect_result.returncode != 0:
                # Container doesn't exist, nothing to remove
                logger.debug(f"Container {container_name} doesn't exist, nothing to remove")
                return True
            
            # Step 1: Stop gracefully with timeout
            logger.info(f"Gracefully stopping container: {container_name}")
            stop_result = execute_docker_command(
                ["docker", "stop", "-t", str(timeout), container_name],
                timeout=timeout + 5
            )
            
            if stop_result.returncode != 0:
                logger.warning(f"Graceful stop failed for {container_name}: {stop_result.stderr}")
                # Don't proceed to rm if stop failed - container may still be running
                return False
            
            # Step 2: Wait for container to fully stop
            time.sleep(2)
            
            # Step 3: Verify container is stopped
            verify_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=5)
            
            if verify_result.returncode == 0:
                is_running = verify_result.stdout.strip() == "true"
                if is_running:
                    logger.warning(f"Container {container_name} is still running after stop command")
                    return False
            
            # Step 4: Safe removal (WITHOUT -f flag)
            logger.info(f"Safely removing stopped container: {container_name}")
            rm_result = execute_docker_command(
                ["docker", "rm", container_name],
                timeout=10
            )
            
            if rm_result.returncode == 0:
                logger.debug(f"Successfully removed container: {container_name}")
                return True
            else:
                logger.error(f"Failed to remove container {container_name}: {rm_result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout during safe removal of container {container_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to safely remove container {container_name}: {e}")
            return False
    
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
        # Ensure Docker stability before proceeding
        try:
            from test_framework.docker_stability_manager import DockerStabilityManager
            stability_manager = DockerStabilityManager()
            docker_stable, message = stability_manager.ensure_docker_stability()
            if not docker_stable:
                logger.warning(f"Docker stability issues: {message}")
        except ImportError:
            logger.debug("DockerStabilityManager not available, proceeding without stability check")
        
        # First try to detect and use existing netra-dev containers
        existing_containers = self._detect_existing_dev_containers()
        if existing_containers:
            logger.info(f"🔄 Found existing netra-dev containers: {', '.join(existing_containers.keys())}")
            ports = self._discover_ports_from_existing_containers(existing_containers)
            self.allocated_ports = ports
            
            # Use a special environment name to indicate we're using existing containers
            env_name = "netra-dev-existing"
            
            # Update state to track usage
            state = self._load_state()
            state["environments"][env_name] = {
                "created": datetime.now().isoformat(),
                "test_id": self.test_id,
                "type": "existing_dev",
                "users": state["environments"].get(env_name, {}).get("users", 0) + 1,
                "existing_containers": existing_containers
            }
            self._save_state(state)
            
            logger.info(f"✅ Using existing development containers with {len(ports)} services")
            return env_name, ports
        
        # Fall back to creating new environment if no existing containers
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
            
            # Allocate ports dynamically for new or existing environment
            services_to_allocate = list(self.SERVICES.keys())
            allocation_result = self.port_allocator.allocate_ports(services_to_allocate)
            
            if not allocation_result.success:
                # Fall back to discovery if allocation fails
                logger.warning(f"Dynamic allocation failed: {allocation_result.error_message}")
                ports = self._discover_ports(env_name)
            else:
                ports = allocation_result.ports
                self.allocated_ports = ports
            
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
        
        # Release allocated ports
        if self.allocated_ports:
            self.port_allocator.release_ports(list(self.allocated_ports.keys()))
            logger.info(f"Released {len(self.allocated_ports)} allocated ports")
            self.allocated_ports = {}
    
    def _create_environment(self, env_name: str):
        """Create new Docker environment with automatic conflict resolution"""
        compose_file = self._get_compose_file()
        
        # Build images first if requested
        if self.rebuild_images:
            project_name = self._get_project_name()
            
            if self.rebuild_backend_only:
                # Determine backend service names based on compose file
                if "alpine" in compose_file:
                    services_to_build = ["alpine-test-backend", "alpine-test-auth"]
                else:
                    services_to_build = ["test-backend", "test-auth"]
                
                logger.info(f"🔨 Building backend services: {services_to_build}")
                build_cmd = [
                    "docker-compose", "-f", compose_file,
                    "-p", project_name, "build"
                ] + services_to_build
            else:
                logger.info("🔨 Building all Docker images...")
                build_cmd = [
                    "docker-compose", "-f", compose_file,
                    "-p", project_name, "build"
                ]
            
            try:
                result = self.docker_rate_limiter.execute_docker_command(
                    build_cmd, timeout=300
                )
                if result.returncode == 0:
                    logger.info("✅ Successfully built Docker images")
                else:
                    logger.warning(f"⚠️ Failed to build images: {result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ Error building images: {e}")
        
        # SSOT: Clean up any conflicting containers first
        logger.info(f"🧹 Checking for conflicting containers before creating {env_name}")
        self._cleanup_conflicting_containers(env_name)
        
        # Prepare environment variables
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = self._get_project_name()
        env["DOCKER_ENV"] = "test"
        
        if self.use_production_images:
            env["DOCKER_TAG"] = "production"
            env["BUILD_TARGET"] = "production"
        
        # Allocate and set dynamic ports
        ports = self._allocate_service_ports()
        env["DEV_POSTGRES_PORT"] = str(ports.get("postgres", 5433))
        env["DEV_REDIS_PORT"] = str(ports.get("redis", 6380))
        env["DEV_CLICKHOUSE_HTTP_PORT"] = str(ports.get("clickhouse", 8124))
        env["DEV_CLICKHOUSE_TCP_PORT"] = str(ports.get("clickhouse", 8124) + 1000)  # TCP port offset
        env["DEV_AUTH_PORT"] = str(ports.get("auth", 8081))
        env["DEV_BACKEND_PORT"] = str(ports.get("backend", 8000))
        env["DEV_FRONTEND_PORT"] = str(ports.get("frontend", 3000))
        
        # Set memory limits
        for service, config in self.SERVICES.items():
            env_key = f"{service.upper()}_MEMORY_LIMIT"
            env[env_key] = config.get("memory_limit", "512m")
        
        # Start services with automatic retry on conflict
        max_retries = 3
        for attempt in range(max_retries):
            cmd = [
                "docker-compose",
                "-f", compose_file,
                "-p", self._get_project_name(),
                "up", "-d"
            ]
            
            docker_result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=120, env=env)
            result = subprocess.CompletedProcess(cmd, docker_result.returncode, docker_result.stdout, docker_result.stderr)
            if result.returncode == 0:
                break
            
            # Check if it's a container name conflict
            if "already in use" in result.stderr.lower():
                logger.warning(f"Container conflict detected on attempt {attempt + 1}, cleaning up...")
                self._force_cleanup_containers(result.stderr)
                time.sleep(2)  # Give Docker time to clean up
            else:
                # Not a conflict error, fail immediately
                raise RuntimeError(f"Failed to create environment: {result.stderr}")
        else:
            # All retries failed
            raise RuntimeError(f"Failed to create environment after {max_retries} attempts: {result.stderr}")
        
        # Wait for containers to be created and healthy
        logger.info(f"⏳ Waiting for containers to be created...")
        max_wait = 30  # seconds
        start_time = time.time()
        containers_found = False
        
        while time.time() - start_time < max_wait:
            # Check if containers exist
            existing_containers = self._detect_existing_containers_by_project(self._get_project_name())
            if existing_containers:
                logger.info(f"✅ Found {len(existing_containers)} containers")
                containers_found = True
                break
            
            logger.debug(f"Waiting for containers... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(2)
        
        if not containers_found:
            # Try to create them again
            logger.warning("⚠️ Containers not found after waiting, attempting to create again...")
            cmd = [
                "docker-compose",
                "-f", compose_file,
                "-p", self._get_project_name(),
                "up", "-d", "--force-recreate"
            ]
            
            docker_result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=120, env=env)
            
            # Wait again for containers
            start_time = time.time()
            while time.time() - start_time < max_wait:
                existing_containers = self._detect_existing_containers_by_project(self._get_project_name())
                if existing_containers:
                    logger.info(f"✅ Found {len(existing_containers)} containers after recreation")
                    containers_found = True
                    break
                time.sleep(2)
            
            if not containers_found:
                raise RuntimeError(f"Failed to create containers for project {self._get_project_name()}")
        
        # Wait for services to be healthy
        self._wait_for_healthy(env_name)
    
    def _cleanup_conflicting_containers(self, env_name: str):
        """Clean up any containers that might conflict with the new environment"""
        # Get list of expected container names from docker-compose
        compose_file = self._get_compose_file()
        
        try:
            # Parse compose file to get service names
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            
            # Check for conflicting containers
            for service_name in services.keys():
                # Common container name patterns
                container_patterns = [
                    f"netra-test-{service_name}",
                    f"{env_name}-{service_name}",
                    f"{env_name}_{service_name}_1"
                ]
                
                for pattern in container_patterns:
                    cmd = ["docker", "ps", "-a", "--filter", f"name={pattern}", "--format", "{{.Names}}"]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        container_names = result.stdout.strip().split('\n')
                        for container in container_names:
                            logger.info(f"Safely removing conflicting container: {container}")
                            if not self.safe_container_remove(container):
                                logger.warning(f"Failed to safely remove container {container}")
                            else:
                                logger.info(f"Successfully removed container {container}")
        
        except Exception as e:
            logger.warning(f"Could not parse compose file for cleanup: {e}")
            # Fallback: Clean up common test containers
            self._cleanup_test_containers()
    
    def _force_cleanup_containers(self, error_message: str):
        """Force cleanup containers mentioned in error message"""
        import re
        
        # Extract container name from error message
        name_pattern = r'container name "([^"]+)" is already in use'
        name_matches = re.findall(name_pattern, error_message)
        
        # Extract container ID from error message
        id_pattern = r'is already in use by container "([a-f0-9]+)"'
        id_matches = re.findall(id_pattern, error_message)
        
        # Remove by name
        for container_name in name_matches:
            logger.info(f"Safely removing conflicting container by name: {container_name}")
            if not self.safe_container_remove(container_name):
                logger.warning(f"Failed to safely remove container {container_name}")
        
        # Remove by ID as fallback
        for container_id in id_matches:
            logger.info(f"Safely removing conflicting container by ID: {container_id}")
            if not self.safe_container_remove(container_id):
                logger.warning(f"Failed to safely remove container {container_id}")
    
    def _cleanup_test_containers(self):
        """Clean up all netra-test containers"""
        cmd = ["docker", "ps", "-a", "--filter", "name=netra-test", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            container_names = result.stdout.strip().split('\n')
            for container in container_names:
                logger.debug(f"Safely removing test container: {container}")
                if not self.safe_container_remove(container):
                    logger.warning(f"Failed to safely remove test container {container}")
                else:
                    logger.debug(f"Successfully removed test container {container}")
    
    def _cleanup_environment(self, env_name: str):
        """Clean up Docker environment"""
        compose_file = self._get_compose_file()
        
        cmd = [
            "docker-compose",
            "-f", compose_file,
            "-p", env_name,
            "down", "--remove-orphans", "-v"
        ]
        
        self.docker_rate_limiter.execute_docker_command(cmd, timeout=60)
    
    def _get_compose_file(self) -> str:
        """Get appropriate docker-compose file based on Alpine setting and environment type"""
        if self.use_alpine:
            # Use Alpine compose files when Alpine support is enabled
            # Prioritize alpine-test.yml for test environments, alpine.yml for others
            compose_files = [
                "docker-compose.alpine-test.yml",
                "docker-compose.alpine.yml",
                "docker-compose.test.yml",  # Fallback to regular test compose
                "docker-compose.yml"  # Final fallback
            ]
        else:
            # Use regular compose files
            compose_files = [
                "docker-compose.test.yml",
                "docker-compose.yml"
            ]
        
        # First check in current directory
        for file_path in compose_files:
            if Path(file_path).exists():
                logger.info(f"Selected Docker compose file: {file_path} (Alpine: {self.use_alpine}, Environment: {self.environment_type.value})")
                return file_path
        
        # Then check in project root (absolute path from env)
        env = get_env()
        project_root = env.get("PROJECT_ROOT")
        if project_root:
            project_path = Path(project_root)
            for file_name in compose_files:
                full_path = project_path / file_name
                if full_path.exists():
                    logger.info(f"Selected Docker compose file: {full_path} (Alpine: {self.use_alpine}, Environment: {self.environment_type.value})")
                    return str(full_path)
        
        # Finally check common parent directories
        current_path = Path.cwd()
        for parent in [current_path, current_path.parent, current_path.parent.parent]:
            for file_name in compose_files:
                full_path = parent / file_name
                if full_path.exists():
                    logger.info(f"Selected Docker compose file: {full_path} (Alpine: {self.use_alpine}, Environment: {self.environment_type.value})")
                    return str(full_path)
        
        raise RuntimeError(f"No docker-compose files found. Expected: {', '.join(compose_files)}")
    
    def _detect_existing_containers_by_project(self, project_name: str) -> Dict[str, str]:
        """
        Detect existing containers for a specific Docker Compose project.
        
        Args:
            project_name: The Docker Compose project name
            
        Returns:
            Dictionary mapping service name to container name
        """
        containers = {}
        
        try:
            # List containers for this specific project
            cmd = ["docker", "ps", "--format", "{{.Names}}", "--filter", f"label=com.docker.compose.project={project_name}"]
            result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                container_names = result.stdout.strip().split('\n')
                for name in container_names:
                    if name:
                        # Extract service name from container name
                        # Format is usually: projectname_servicename_1
                        parts = name.split('_')
                        if len(parts) >= 2:
                            service = parts[1]
                            containers[service] = name
                        elif '-' in name:
                            # Alternative format: projectname-servicename-1
                            parts = name.split('-')
                            if len(parts) >= 2:
                                service = parts[-2] if parts[-1].isdigit() else parts[-1]
                                containers[service] = name
            
            return containers
            
        except Exception as e:
            logger.warning(f"Error detecting containers for project {project_name}: {e}")
            return {}
    
    def _detect_existing_dev_containers(self) -> Dict[str, str]:
        """
        Detect existing netra-dev-* containers that are currently running.
        Enhanced with retry logic for better reliability during test execution.
        
        Returns:
            Dictionary mapping service name to container name
        """
        containers = {}
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"🔍 Container detection attempt {attempt + 1}/{max_retries}")
                # List all running netra containers - support multiple naming patterns
                patterns = ["netra-dev-", "netra-apex-test-", "netra-test-", "netra_test_shared_"]
                
                for pattern in patterns:
                    cmd = ["docker", "ps", "--format", "{{.Names}}", "--filter", f"name={pattern}"]
                    # Use docker_rate_limiter for rate limiting
                    docker_result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=10)
                    result = subprocess.CompletedProcess(cmd, docker_result.returncode, docker_result.stdout, docker_result.stderr)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        container_names = result.stdout.strip().split('\n')
                        
                        # Map container names to service names
                        for container_name in container_names:
                            # Extract service name from different patterns
                            if container_name.startswith('netra-dev-'):
                                service = container_name.replace('netra-dev-', '')
                                containers[service] = container_name
                            elif container_name.startswith('netra-apex-test-'):
                                # Handle netra-apex-test-backend-1 -> backend
                                service = container_name.replace('netra-apex-test-', '')
                                if service.endswith('-1'):
                                    service = service[:-2]  # Remove '-1' suffix properly
                                containers[service] = container_name
                            elif container_name.startswith('netra-test-'):
                                service = container_name.replace('netra-test-', '')
                                if service.endswith('-1'):
                                    service = service[:-2]  # Remove '-1' suffix properly
                                containers[service] = container_name
                            elif container_name.startswith('netra_test_shared_'):
                                service = container_name.replace('netra_test_shared_', '')
                                if service.endswith('_1'):
                                    service = service[:-2]  # Remove '_1' suffix properly
                                containers[service] = container_name
                            else:
                                continue
                            logger.debug(f"🔍 Detected existing container: {service} -> {container_name}")
            
                # If we found containers, return immediately
                if containers:
                    logger.info(f"🔄 Found {len(containers)} existing containers on attempt {attempt + 1}")
                    for service, container_name in containers.items():
                        logger.debug(f"  - {service}: {container_name}")
                    return containers
                
                # If no containers found and not last attempt, wait and retry
                if attempt < max_retries - 1:
                    logger.debug(f"No containers found on attempt {attempt + 1}, retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.debug("No existing netra containers found after all attempts")
                    # Don't assume development containers exist - let orchestration handle it
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Docker command timed out on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    logger.debug(f"Retrying in {retry_delay}s due to timeout...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt - try alternative approach
                    logger.warning("Using alternative docker detection method")
                    try:
                        patterns = ["netra-dev-", "netra-apex-test-", "netra-test-", "netra_test_shared_"]
                        for pattern in patterns:
                            cmd = ["docker", "container", "ls", "--format", "{{.Names}}", "--filter", f"name={pattern}"]
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                            if result.returncode == 0 and result.stdout.strip():
                                container_names = result.stdout.strip().split('\n')
                                for container_name in container_names:
                                    # Extract service name based on pattern
                                    if 'netra-apex-test-' in container_name:
                                        service = container_name.replace('netra-apex-test-', '')
                                        if service.endswith('-1'):
                                            service = service[:-2]  # Remove '-1' suffix properly
                                    elif 'netra-dev-' in container_name:
                                        service = container_name.replace('netra-dev-', '')
                                    elif 'netra_test_shared_' in container_name:
                                        service = container_name.replace('netra_test_shared_', '')
                                        if service.endswith('_1'):
                                            service = service[:-2]  # Remove '_1' suffix properly
                                    else:
                                        service = container_name.replace('netra-test-', '')
                                        if service.endswith('-1'):
                                            service = service[:-2]  # Remove '-1' suffix properly
                                    containers[service] = container_name
                        if containers:
                            logger.info(f"🔄 Found {len(containers)} containers via alternative method")
                            return containers
                    except Exception as alt_e:
                        logger.warning(f"Alternative docker detection also failed: {alt_e}")
                        
            except Exception as e:
                logger.warning(f"Error detecting existing containers on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.debug(f"Retrying in {retry_delay}s due to error...")
                    import time
                    time.sleep(retry_delay)
                    continue
                # Don't assume any containers exist - let orchestration handle missing containers
            
        return containers
    
    def _discover_ports_from_existing_containers(self, containers: Dict[str, str]) -> Dict[str, int]:
        """
        Discover port mappings from existing containers.
        
        Args:
            containers: Dictionary mapping service name to container name
            
        Returns:
            Dictionary mapping service name to external port
        """
        ports = {}
        
        for service, container_name in containers.items():
            try:
                # Get port mapping for this container
                if service in self.SERVICES:
                    internal_port = self.SERVICES[service].get("default_port", 8000)
                    
                    cmd = ["docker", "port", container_name, str(internal_port)]
                    docker_result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=5)
                    result = subprocess.CompletedProcess(cmd, docker_result.returncode, docker_result.stdout, docker_result.stderr)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Parse output like "0.0.0.0:8000" or "127.0.0.1:8000"
                        port_mapping = result.stdout.strip()
                        if ':' in port_mapping:
                            external_port = int(port_mapping.split(':')[-1])
                            ports[service] = external_port
                            logger.debug(f"🔌 {service}: {internal_port} -> {external_port}")
                        else:
                            # Use internal port as fallback
                            ports[service] = internal_port
                            logger.debug(f"🔌 {service}: using internal port {internal_port}")
                    else:
                        # No port mapping found, use internal port
                        ports[service] = internal_port
                        logger.debug(f"🔌 {service}: no mapping found, using internal port {internal_port}")
                else:
                    logger.warning(f"⚠️ Unknown service: {service}")
                    
            except Exception as e:
                # Handle Docker connectivity issues gracefully
                if "pipe" in str(e).lower() or "connect" in str(e).lower():
                    logger.warning(f"Docker connectivity issue for {service}, using default port")
                    if service in self.SERVICES:
                        if service in self.allocated_ports:
                            ports[service] = self.allocated_ports[service]
                        else:
                            ports[service] = self.SERVICES[service].get("default_port", 8000)
                else:
                    logger.warning(f"Error discovering port for {service}: {e}")
                    # Use default port as fallback
                    if service in self.SERVICES:
                        if service in self.allocated_ports:
                            ports[service] = self.allocated_ports[service]
                        else:
                            ports[service] = self.SERVICES[service].get("default_port", 8000)
        
        # If we have no ports discovered due to Docker issues, use default dev ports
        if not ports and containers:
            logger.warning("🔄 Using default development ports due to Docker connectivity issues")
            dev_ports = {
                "backend": 8000,
                "auth": 8001, 
                "frontend": 3000,
                "postgres": 5432,
                "redis": 6379,
                "clickhouse": 8123
            }
            
            for service in containers.keys():
                if service in dev_ports:
                    ports[service] = dev_ports[service]
                    logger.info(f"🔌 {service}: using default dev port {dev_ports[service]}")
        
        logger.info(f"📍 Discovered ports: {ports}")
        return ports
    
    def _get_actual_container_name(self, env_name: str, service_name: str) -> Optional[str]:
        """
        Get the actual container name for a service, handling different naming patterns.
        
        Args:
            env_name: Environment name
            service_name: Service name
            
        Returns:
            Actual container name or None if not found
        """
        # Try different naming patterns
        possible_names = [
            f"{env_name}_{service_name}_1",  # Standard compose format
            f"{env_name}-{service_name}-1",   # Alternative compose format
            f"netra-apex-test-{service_name}-1",  # Our test containers
            f"netra-dev-{service_name}",     # Dev containers
            f"netra-test-{service_name}-1",  # Test containers
            f"netra_test_shared_{service_name}_1"  # Shared test containers
        ]
        
        for name in possible_names:
            # Check if container exists
            cmd = ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                actual_name = result.stdout.strip().split('\n')[0]  # Get first match
                if actual_name:
                    logger.debug(f"Found container {actual_name} for service {service_name}")
                    return actual_name
        
        # If not found by exact match, try to find by service name pattern
        cmd = ["docker", "ps", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            container_names = result.stdout.strip().split('\n')
            for container_name in container_names:
                # Check if service name is in container name
                if service_name in container_name and 'netra' in container_name:
                    logger.debug(f"Found container {container_name} by pattern match for service {service_name}")
                    return container_name
        
        return None
    
    def _is_existing_container_healthy(self, container_name: str) -> bool:
        """Check if an existing container is healthy and running."""
        try:
            # Check container status
            cmd = ["docker", "inspect", "--format='{{.State.Status}} {{.State.Health.Status}}'", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                status_output = result.stdout.strip().strip("'")
                parts = status_output.split()
                
                state_status = parts[0] if parts else ""
                health_status = parts[1] if len(parts) > 1 else "none"
                
                # Container is healthy if it's running and either healthy or has no health check
                is_running = state_status == "running"
                is_healthy = health_status in ["healthy", "none", "<no"]  # <no value> means no health check
                
                logger.debug(f"🩺 Container {container_name}: state={state_status}, health={health_status}")
                return is_running and is_healthy
            else:
                logger.debug(f"🩺 Container {container_name} not found or not accessible")
                return False
                
        except Exception as e:
            # Handle Docker connectivity issues gracefully
            if "pipe" in str(e).lower() or "connect" in str(e).lower():
                logger.warning(f"Docker connectivity issue checking {container_name}, assuming healthy")
                # If we can't check health due to Docker connectivity issues, assume healthy
                # since the containers were detected as existing
                return True
            else:
                logger.warning(f"Error checking container health for {container_name}: {e}")
                return False
    
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
            
            # Perform restart - try to find actual container name
            container_name = self._get_actual_container_name(env_name, service_name)
            if not container_name:
                logger.error(f"❌ Could not find container for service {service_name}")
                return False
            
            cmd = ["docker", "restart", container_name]
            
            docker_result = self.docker_rate_limiter.execute_docker_command(cmd, timeout=60)
            result = subprocess.CompletedProcess(cmd, docker_result.returncode, docker_result.stdout, docker_result.stderr)
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
        # Get the actual container name
        container_name = self._get_actual_container_name(env_name, service_name)
        if not container_name:
            logger.warning(f"Container for service {service_name} not found")
            return False
        
        # Check container status
        cmd = ["docker", "inspect", "--format='{{.State.Health.Status}}'", container_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            status = result.stdout.strip().strip("'")
            # Accept healthy, starting (during startup), or none (no health checks)
            is_healthy = status in ["healthy", "starting", "none"]
            logger.debug(f"Service {service_name} ({container_name}) health: {status} -> {is_healthy}")
            return is_healthy
        
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
            self._configure_service_environment(discovered_ports=ports)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ E2E Service Orchestration completed successfully in {elapsed:.1f}s")
            
            return True, self.service_health
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ E2E Service Orchestration failed after {elapsed:.1f}s: {e}")
            return False, self._create_failure_report(f"Orchestration exception: {e}")

    async def _check_docker_availability(self) -> bool:
        """Check if Docker is available and docker-compose files exist."""
        # First check if we can use existing dev containers
        existing_containers = self._detect_existing_dev_containers()
        if existing_containers:
            logger.info(f"✅ Found existing development containers, bypassing Docker daemon check")
            try:
                compose_file = self._get_compose_file()
                logger.info(f"✅ Using compose file: {compose_file}")
                return True
            except RuntimeError as e:
                logger.warning(f"⚠️ Docker compose file issue, but existing containers available: {e}")
                return True  # Allow using existing containers even if compose files have issues
        
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
        
        # If we're using existing dev containers, verify they're running and healthy
        existing_containers = self._detect_existing_dev_containers()
        if existing_containers:
            logger.info("🔄 Using existing development containers, checking health...")
            
            # Check which required services are available in existing containers
            available_services = []
            missing_services = []
            
            for service in self.config.required_services:
                if service in existing_containers:
                    # Check if the container is actually healthy
                    container_name = existing_containers[service]
                    if self._is_existing_container_healthy(container_name):
                        available_services.append(service)
                    else:
                        logger.warning(f"⚠️ Existing container {container_name} is not healthy")
                        missing_services.append(service)
                else:
                    missing_services.append(service)
            
            if available_services:
                logger.info(f"✅ Using healthy existing containers: {', '.join(available_services)}")
            
            if not missing_services:
                logger.info("✅ All required services are available in existing containers")
                return True
            else:
                logger.warning(f"⚠️ Some services not available in existing containers: {missing_services}")
                # For now, we'll consider this successful if we have the core services
                core_services = ["backend", "auth", "postgres", "redis"]
                available_core = [s for s in available_services if s in core_services]
                if len(available_core) >= 3:  # Need at least 3 core services
                    logger.info(f"✅ Sufficient core services available: {available_core}")
                    return True
        
        # Check current service status using port discovery
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
        
        # Setup network before starting services
        if not self._setup_network():
            logger.error("Failed to setup Docker network")
            return False
        
        # Start services using existing environment acquisition
        env_name = self._get_environment_name()
        
        # Use compose to start services
        compose_file = self._get_compose_file()
        service_names = self._map_to_compose_services(missing_services)
        
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = self._get_project_name()
        env["DOCKER_ENV"] = "test"
        
        if self.use_production_images:
            env["DOCKER_TAG"] = "production"
            env["BUILD_TARGET"] = "production"
        
        # Allocate and set dynamic ports
        ports = self._allocate_service_ports()
        env["DEV_POSTGRES_PORT"] = str(ports.get("postgres", 5433))
        env["DEV_REDIS_PORT"] = str(ports.get("redis", 6380))
        env["DEV_CLICKHOUSE_HTTP_PORT"] = str(ports.get("clickhouse", 8124))
        env["DEV_CLICKHOUSE_TCP_PORT"] = str(ports.get("clickhouse", 8124) + 1000)  # TCP port offset
        env["DEV_AUTH_PORT"] = str(ports.get("auth", 8081))
        env["DEV_BACKEND_PORT"] = str(ports.get("backend", 8000))
        env["DEV_FRONTEND_PORT"] = str(ports.get("frontend", 3000))
        
        # Set memory limits
        for service, config in self.SERVICES.items():
            env_key = f"{service.upper()}_MEMORY_LIMIT"
            env[env_key] = config.get("memory_limit", "512m")
        
        # Build services if needed
        if self.rebuild_images:
            backend_services = ['backend', 'auth', 'alpine-test-backend', 'alpine-test-auth', 'test-backend', 'test-auth']
            
            if self.rebuild_backend_only and any(s in backend_services for s in service_names):
                # Build backend services
                services_to_build = [s for s in service_names if s in backend_services]
                if services_to_build:
                    build_cmd = ["docker", "compose", "-f", compose_file, "-p", self._get_project_name(), "build"] + services_to_build
                    logger.info(f"🔨 Building backend services: {services_to_build}")
                    
                    result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=300, env=env)
                    if result.returncode != 0:
                        logger.warning(f"⚠️ Failed to build services: {result.stderr}")
            elif not self.rebuild_backend_only:
                # Build all requested services
                build_cmd = ["docker", "compose", "-f", compose_file, "-p", self._get_project_name(), "build"] + service_names
                logger.info(f"🔨 Building all requested services: {service_names}")
                
                result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=300, env=env)
                if result.returncode != 0:
                    logger.warning(f"⚠️ Failed to build services: {result.stderr}")
        
        cmd = ["docker", "compose", "-f", compose_file, "-p", self._get_project_name(), "up", "-d"] + service_names
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

    def _configure_service_environment(self, discovered_ports: Optional[Dict[str, int]] = None) -> None:
        """Configure environment variables with discovered service ports."""
        env = get_env()
        
        # Use provided ports or discover them
        if discovered_ports:
            ports = discovered_ports
        else:
            port_mappings = self.port_discovery.discover_all_ports()
            ports = {service: mapping.external_port for service, mapping in port_mappings.items() if mapping.is_available}
        
        # Set service URLs for E2E tests
        for service, port in ports.items():
            service_url = self._build_service_url_from_port(service, port)
            if service_url:
                env_var = f"{service.upper()}_SERVICE_URL"
                env.set(env_var, service_url, source="unified_docker_manager")
                logger.info(f"🔧 {env_var}={service_url}")
        
        # Set specific URLs needed by E2E tests
        if "backend" in ports:
            backend_port = ports["backend"]
            env.set("BACKEND_URL", f"http://localhost:{backend_port}", source="unified_docker_manager")
            env.set("WEBSOCKET_URL", f"ws://localhost:{backend_port}/ws", source="unified_docker_manager")
        
        if "auth" in ports:
            auth_port = ports["auth"]
            env.set("AUTH_SERVICE_URL", f"http://localhost:{auth_port}", source="unified_docker_manager")
        
        # Set database URLs (using correct credentials from docker-compose.test.yml)
        if "postgres" in ports:
            postgres_port = ports["postgres"]
            db_url = f"postgresql://test_user:test_pass@localhost:{postgres_port}/netra_test"
            env.set("DATABASE_URL", db_url, source="unified_docker_manager")
        
        if "redis" in ports:
            redis_port = ports["redis"]
            redis_url = f"redis://localhost:{redis_port}/1"
            env.set("REDIS_URL", redis_url, source="unified_docker_manager")

    def _build_service_url_from_port(self, service: str, port: int) -> Optional[str]:
        """Build service URL from service name and port."""
        if service in ["backend", "auth", "frontend"]:
            return f"http://localhost:{port}"
        elif service == "postgres":
            return f"postgresql://test:test@localhost:{port}/netra_test"
        elif service == "redis":
            return f"redis://localhost:{port}/1"
        elif service == "clickhouse":
            return f"http://localhost:{port}"
        return None

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
        # Determine the prefix based on the compose file being used
        compose_file = self._get_compose_file()
        
        # If using test compose file, use test- prefix for ALL services
        if "test" in compose_file:
            service_mapping = {
                "postgres": "test-postgres",
                "redis": "test-redis", 
                "clickhouse": "test-clickhouse",
                "backend": "test-backend",
                "auth": "test-auth",
                "frontend": "test-frontend"
            }
        else:
            # For dev/main compose, use dev- prefix
            service_mapping = {
                "postgres": "dev-postgres",
                "redis": "dev-redis",
                "clickhouse": "dev-clickhouse", 
                "backend": "dev-backend",
                "auth": "dev-auth",
                "frontend": "dev-frontend"
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
        
        # Release allocated ports first
        if self.allocated_ports:
            self.port_allocator.release_ports(list(self.allocated_ports.keys()))
            logger.info(f"Released {len(self.allocated_ports)} allocated ports")
            self.allocated_ports = {}
        
        # Release environment through centralized management
        env_name = self._get_environment_name()
        self.release_environment(env_name)
        
        # Clean up network
        self._cleanup_network()
        
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
            docker_result = self.docker_rate_limiter.execute_docker_command(
                ["docker", "--version"],
                timeout=5
            )
            self._docker_available = docker_result.returncode == 0
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
                   "-p", self._get_project_name(), "ps", "--format", "json", service]
            
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
            
            # Setup network before starting services
            if not self._setup_network():
                logger.error("Failed to setup Docker network")
                return False
            
            # Setup environment with dynamic ports
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self._get_project_name()
            
            # Allocate and set dynamic ports
            ports = self._allocate_service_ports()
            env["DEV_POSTGRES_PORT"] = str(ports.get("postgres", 5433))
            env["DEV_REDIS_PORT"] = str(ports.get("redis", 6380))
            env["DEV_CLICKHOUSE_HTTP_PORT"] = str(ports.get("clickhouse", 8124))
            env["DEV_CLICKHOUSE_TCP_PORT"] = str(ports.get("clickhouse", 8124) + 1000)  # TCP port offset
            env["DEV_AUTH_PORT"] = str(ports.get("auth", 8081))
            env["DEV_BACKEND_PORT"] = str(ports.get("backend", 8000))
            env["DEV_FRONTEND_PORT"] = str(ports.get("frontend", 3000))
            
            # Build images if requested
            compose_file = self._get_compose_file()
            
            if self.rebuild_images:
                backend_services = ['backend', 'auth', 'alpine-test-backend', 'alpine-test-auth', 'test-backend', 'test-auth']
                
                if self.rebuild_backend_only:
                    services_to_build = [s for s in services_to_start if s in backend_services]
                    if services_to_build:
                        build_cmd = ["docker-compose", "-f", compose_file, "-p", self._get_project_name(), "build"] + services_to_build
                        logger.info(f"🔨 Building backend services: {services_to_build}")
                        subprocess.run(build_cmd, capture_output=True, text=True, timeout=300, env=env)
                else:
                    build_cmd = ["docker-compose", "-f", compose_file, "-p", self._get_project_name(), "build"] + services_to_start
                    logger.info(f"🔨 Building all services: {services_to_start}")
                    subprocess.run(build_cmd, capture_output=True, text=True, timeout=300, env=env)
            
            cmd = ["docker-compose", "-f", compose_file,
                   "-p", self._get_project_name(), "up", "-d"] + services_to_start
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
                
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
                   "-p", self._get_project_name(), "down"]
            
            if services:
                # For specific services, use stop instead of down
                cmd = ["docker-compose", "-f", self._get_compose_file(),
                       "-p", self._get_project_name(), "stop", "-t", str(timeout)] + services
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
                   "-p", self._get_project_name(), "kill"]
            
            if services:
                cmd.extend(services)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Wait for containers to be fully killed
            await asyncio.sleep(3)
            
            # Remove containers safely (CRITICAL: NO force flag to prevent daemon crashes)
            # First ensure containers are fully stopped
            cmd_stop = ["docker-compose", "-f", self._get_compose_file(),
                       "-p", self._get_project_name(), "stop", "--timeout", "5"]
            if services:
                cmd_stop.extend(services)
            
            subprocess.run(cmd_stop, capture_output=True, text=True, timeout=30)
            
            # Wait additional time for cleanup
            await asyncio.sleep(2)
            
            # Then remove safely without force flag
            cmd_rm = ["docker-compose", "-f", self._get_compose_file(),
                      "-p", self._get_project_name(), "rm", "--timeout", "10"]
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
                       "-p", self._get_project_name(), "exec", "-T", "postgres",
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
                   "-p", self._get_project_name(), "exec", "-T", "redis",
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
               "-p", self._get_project_name(), "ps", "--format", "json"]
        
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
                   "-p", self._get_project_name(), "down", "--remove-orphans"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.warning(f"Orphan cleanup had issues: {result.stderr}")
                return False
            
            # Clean up project-specific network if exists
            self._cleanup_network()
            
            # Prune unused networks using rate-limited execution
            execute_docker_command(["docker", "network", "prune", "-f"], timeout=30)
            
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
        project_name = self._get_project_name()
        
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
    
    # =====================================
    # CLEANUP SCHEDULER INTEGRATION
    # =====================================
    
    def enable_cleanup_scheduler(self, 
                                schedule_config: Optional[object] = None,
                                resource_thresholds: Optional[object] = None) -> bool:
        """
        Enable the Docker cleanup scheduler for this manager.
        
        Args:
            schedule_config: Optional ScheduleConfig instance
            resource_thresholds: Optional ResourceThresholds instance
            
        Returns:
            True if scheduler was enabled successfully
        """
        if not self._enable_cleanup_scheduler:
            logger.debug("Cleanup scheduler is disabled via environment variable")
            return False
        
        try:
            # Import here to avoid circular imports
            from test_framework.docker_cleanup_scheduler import (
                DockerCleanupScheduler, ScheduleConfig, ResourceThresholds
            )
            
            if self._cleanup_scheduler is None:
                self._cleanup_scheduler = DockerCleanupScheduler(
                    docker_manager=self,
                    rate_limiter=self.config.rate_limiter if hasattr(self.config, 'rate_limiter') else None,
                    schedule_config=schedule_config,
                    resource_thresholds=resource_thresholds
                )
                
                # Add callbacks for test session tracking
                self._cleanup_scheduler.add_pre_cleanup_callback(self._pre_cleanup_check)
                self._cleanup_scheduler.add_post_cleanup_callback(self._post_cleanup_handler)
                
                result = self._cleanup_scheduler.start()
                if result:
                    logger.info("Docker cleanup scheduler enabled and started")
                else:
                    logger.error("Failed to start cleanup scheduler")
                return result
            else:
                logger.debug("Cleanup scheduler already enabled")
                return True
                
        except Exception as e:
            logger.error(f"Failed to enable cleanup scheduler: {e}")
            return False
    
    def disable_cleanup_scheduler(self) -> bool:
        """
        Disable the Docker cleanup scheduler.
        
        Returns:
            True if scheduler was disabled successfully
        """
        if self._cleanup_scheduler is not None:
            try:
                result = self._cleanup_scheduler.stop()
                self._cleanup_scheduler = None
                logger.info("Docker cleanup scheduler disabled")
                return result
            except Exception as e:
                logger.error(f"Failed to disable cleanup scheduler: {e}")
                return False
        return True
    
    def get_cleanup_scheduler_status(self) -> Optional[Dict[str, Any]]:
        """
        Get status of the cleanup scheduler.
        
        Returns:
            Scheduler statistics dictionary or None if scheduler not enabled
        """
        if self._cleanup_scheduler is not None:
            return self._cleanup_scheduler.get_statistics()
        return None
    
    def register_with_cleanup_scheduler(self, test_id: Optional[str] = None) -> str:
        """
        Register the current test session with the cleanup scheduler.
        
        Args:
            test_id: Optional test identifier (uses self.test_id if None)
            
        Returns:
            The registered test ID
        """
        session_id = test_id or self.test_id
        if self._cleanup_scheduler is not None:
            self._cleanup_scheduler.register_test_session(session_id)
            logger.debug(f"Registered test session {session_id} with cleanup scheduler")
        return session_id
    
    def unregister_from_cleanup_scheduler(self, test_id: Optional[str] = None, 
                                        trigger_cleanup: bool = True) -> None:
        """
        Unregister test session from cleanup scheduler.
        
        Args:
            test_id: Optional test identifier (uses self.test_id if None)
            trigger_cleanup: Whether to trigger post-test cleanup
        """
        session_id = test_id or self.test_id
        if self._cleanup_scheduler is not None:
            self._cleanup_scheduler.unregister_test_session(session_id, trigger_cleanup)
            logger.debug(f"Unregistered test session {session_id} from cleanup scheduler")
    
    def trigger_manual_cleanup(self, cleanup_types: Optional[List] = None) -> List:
        """
        Trigger manual cleanup through the scheduler if available.
        
        Args:
            cleanup_types: Optional list of CleanupType enums
            
        Returns:
            List of CleanupResult objects
        """
        if self._cleanup_scheduler is not None:
            return self._cleanup_scheduler.trigger_manual_cleanup(cleanup_types, force=True)
        else:
            logger.warning("Cleanup scheduler not available for manual cleanup")
            # Fallback to existing cleanup method
            try:
                self.cleanup_orphaned_containers()
                return []
            except Exception as e:
                logger.error(f"Fallback cleanup failed: {e}")
                return []
    
    def _pre_cleanup_check(self) -> bool:
        """
        Pre-cleanup callback to check if cleanup should proceed.
        
        Returns:
            True if cleanup should proceed
        """
        # Check if any critical services are starting up
        try:
            if hasattr(self, '_starting_services') and self._starting_services:
                logger.info("Skipping cleanup - services are starting")
                return False
            
            # Check if we're in the middle of a restart operation
            now = time.time()
            for service, restart_times in self._restart_history.items():
                if restart_times and (now - restart_times[-1]) < 60:  # Within last minute
                    logger.info(f"Skipping cleanup - {service} recently restarted")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error in pre-cleanup check: {e}")
            return True  # Proceed with cleanup on error
    
    def _post_cleanup_handler(self, results: List) -> None:
        """
        Post-cleanup callback to handle cleanup results.
        
        Args:
            results: List of CleanupResult objects
        """
        try:
            total_space_freed = sum(r.space_freed_mb for r in results if r.success)
            total_items_removed = sum(r.items_removed for r in results if r.success)
            failed_operations = [r for r in results if not r.success]
            
            if total_space_freed > 0 or total_items_removed > 0:
                logger.info(f"Cleanup completed: {total_items_removed} items removed, "
                           f"{total_space_freed:.1f} MB freed")
            
            if failed_operations:
                logger.warning(f"Some cleanup operations failed: {len(failed_operations)}")
                for result in failed_operations:
                    logger.debug(f"  {result.cleanup_type.value}: {result.error_message}")
                    
        except Exception as e:
            logger.warning(f"Error in post-cleanup handler: {e}")


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
    
    def __init__(self, config: Optional[OrchestrationConfig] = None, use_alpine: bool = False):
        """Initialize with legacy ServiceOrchestrator interface"""
        super().__init__(config=config, environment_type=EnvironmentType.SHARED, use_production_images=True, use_alpine=use_alpine)
        logger.info("ServiceOrchestrator is deprecated - using UnifiedDockerManager")


# Removed duplicate UnifiedDockerManager class that was causing circular inheritance
# The main UnifiedDockerManager class (starting at line 192) is the correct implementation