"""
Centralized Docker Management System for Unified Test Runner
Prevents restart storms and manages parallel test execution with proper coordination.
"""

import os
import json
import time
import threading
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from enum import Enum
from datetime import datetime, timedelta
if os.name != 'nt':
    import fcntl
else:
    fcntl = None
    
if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None
from contextlib import contextmanager


class EnvironmentType(Enum):
    """Test environment types"""
    SHARED = "shared"  # Shared test environment (default)
    DEDICATED = "dedicated"  # Dedicated per test run
    PRODUCTION = "production"  # Production-like images
    DEVELOPMENT = "development"  # Development images


class ServiceStatus(Enum):
    """Docker service status"""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RESTARTING = "restarting"


class CentralizedDockerManager:
    """
    Centralized Docker management with proper coordination and locking.
    Prevents restart storms and manages parallel test execution.
    """
    
    # Class-level configuration
    LOCK_DIR = Path("/tmp/netra_docker_locks") if os.name != 'nt' else Path(os.environ.get('TEMP', '.')) / "netra_docker_locks"
    STATE_FILE = LOCK_DIR / "docker_state.json"
    RESTART_COOLDOWN = 30  # seconds between restart attempts
    MAX_RESTART_ATTEMPTS = 3
    HEALTH_CHECK_TIMEOUT = 60  # seconds
    
    # Service configuration - aligned with docker-compose.alpine.yml
    SERVICES = {
        "backend": {
            "container": "netra-backend",
            "port": 8000,
            "health_endpoint": "/health",
            "memory_limit": "1024m",  # Reduced for stability
            "compose_file": "docker-compose.alpine.yml"
        },
        "frontend": {
            "container": "netra-frontend", 
            "port": 3000,
            "health_endpoint": "/",
            "memory_limit": "256m",  # Reduced for stability
            "compose_file": "docker-compose.alpine.yml"
        },
        "auth": {
            "container": "netra-auth",
            "port": 8001,
            "health_endpoint": "/health",
            "memory_limit": "512m",
            "compose_file": "docker-compose.alpine.yml"
        },
        "postgres": {
            "container": "netra-postgres",
            "port": 5432,
            "health_cmd": "pg_isready",
            "memory_limit": "512m",
            "compose_file": "docker-compose.alpine.yml"
        },
        "redis": {
            "container": "netra-redis",
            "port": 6379,
            "health_cmd": "redis-cli ping",
            "memory_limit": "256m",
            "compose_file": "docker-compose.alpine.yml"
        },
        "clickhouse": {
            "container": "netra-clickhouse",
            "port": 8123,
            "health_endpoint": "/ping",
            "memory_limit": "512m",
            "compose_file": "docker-compose.alpine.yml"
        }
    }
    
    def __init__(self, 
                 environment_type: EnvironmentType = EnvironmentType.SHARED,
                 test_id: Optional[str] = None,
                 use_production_images: bool = True):  # Default to memory-optimized production images
        """
        Initialize centralized Docker manager.
        
        Args:
            environment_type: Type of test environment
            test_id: Unique test identifier for dedicated environments
            use_production_images: Use production Docker images for memory efficiency
        """
        self.environment_type = environment_type
        self.test_id = test_id or self._generate_test_id()
        self.use_production_images = use_production_images
        
        # Initialize lock directory
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for locks
        self._local = threading.local()
        
        # Restart tracking
        self._restart_history: Dict[str, List[float]] = {}
        
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
            print(f"⏳ Restart cooldown active for {service_name}. Wait {remaining:.1f}s")
            return False
        
        # Check rate limit
        recent_restarts = len([t for t in history if now - t < 300])  # Last 5 minutes
        if recent_restarts >= self.MAX_RESTART_ATTEMPTS:
            print(f"[WARNING] Too many restarts for {service_name} ({recent_restarts} in last 5 min)")
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
                print(f"[INFO] Creating new test environment: {env_name}")
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
                print(f"[INFO] Reusing existing environment: {env_name} (users: {state['environments'][env_name]['users']})")
            
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
                    print(f"🧹 Cleaning up dedicated environment: {env_name}")
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
        
        # Start services with proper compose command
        # Try docker compose (v2) first, fall back to docker-compose (v1)
        cmd_v2 = [
            "docker", "compose",
            "-f", compose_file,
            "-p", env_name,
            "up", "-d", "--remove-orphans"
        ]
        
        cmd_v1 = [
            "docker-compose",
            "-f", compose_file,
            "-p", env_name,
            "up", "-d", "--remove-orphans"
        ]
        
        # Try v2 first
        result = subprocess.run(cmd_v2, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            # Fall back to v1
            result = subprocess.run(cmd_v1, env=env, capture_output=True, text=True)
        
        cmd = cmd_v2  # For error reporting
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create environment: {result.stderr}")
        
        # Wait for services to be healthy
        self._wait_for_healthy(env_name)
    
    def _cleanup_environment(self, env_name: str):
        """Clean up Docker environment"""
        compose_file = self._get_compose_file()
        
        # Try docker compose (v2) first, fall back to docker-compose (v1)
        cmd_v2 = [
            "docker", "compose",
            "-f", compose_file,
            "-p", env_name,
            "down", "--remove-orphans", "-v"
        ]
        
        cmd_v1 = [
            "docker-compose",
            "-f", compose_file,
            "-p", env_name,
            "down", "--remove-orphans", "-v"
        ]
        
        # Try v2 first
        result = subprocess.run(cmd_v2, capture_output=True)
        if result.returncode != 0:
            # Fall back to v1
            subprocess.run(cmd_v1, capture_output=True)
    
    def _get_compose_file(self) -> str:
        """Get appropriate docker-compose file based on configuration."""
        # Check for compose file preference in services config
        compose_files_needed = set()
        for service, config in self.SERVICES.items():
            if 'compose_file' in config:
                compose_files_needed.add(config['compose_file'])
        
        # Default to Alpine for production images (memory optimization)
        if self.use_production_images or 'docker-compose.alpine.yml' in compose_files_needed:
            # Use alpine compose configuration for memory optimization
            compose_file = "docker-compose.alpine.yml"
            
            # If alpine file doesn't exist, use regular with memory limits
            if not Path(compose_file).exists():
                compose_file = "docker-compose.yml"
                print("[INFO] Alpine compose file not found, using standard with memory limits")
        else:
            compose_file = "docker-compose.yml"
        
        return compose_file
    
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
                print(f"[OK] Successfully restarted {service_name}")
            else:
                print(f"❌ Failed to restart {service_name}: {result.stderr}")
            
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
        print(f"⏳ Waiting for services to be healthy in {env_name}...")
        
        if self.wait_for_services(timeout=timeout):
            print(f"[OK] All services healthy in {env_name}")
        else:
            print(f"[WARNING] Some services failed to become healthy in {env_name}")
    
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
                print(f"🧹 Cleaning up old environment: {env_name}")
                self._cleanup_environment(env_name)
                del state["environments"][env_name]
            
            self._save_state(state)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Docker management statistics"""
        state = self._load_state()
        
        stats = {
            "environments": len(state["environments"]),
            "active_environments": sum(1 for e in state["environments"].values() if e.get("users", 0) > 0),
            "services": {},
            "restart_counts": {}
        }
        
        # Service statistics
        for service, data in state["services"].items():
            stats["services"][service] = data.get("status", "unknown")
        
        # Restart statistics
        for service, history in self._restart_history.items():
            stats["restart_counts"][service] = len(history)
        
        return stats


# Convenience functions for backward compatibility
_default_manager = None


def get_default_manager() -> CentralizedDockerManager:
    """Get or create default Docker manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = CentralizedDockerManager()
    return _default_manager


def restart_service(service_name: str, force: bool = False) -> bool:
    """Restart service using default manager"""
    return get_default_manager().restart_service(service_name, force)


def wait_for_services(services: Optional[List[str]] = None, timeout: int = 60) -> bool:
    """Wait for services using default manager"""
    return get_default_manager().wait_for_services(services, timeout)