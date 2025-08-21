"""Test isolation utilities for running multiple test instances simultaneously."""

import atexit
import hashlib
import os
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class TestIsolationManager:
    """Manages isolated test environments for concurrent test execution."""
    
    _instances: Dict[str, 'TestIsolationManager'] = {}
    _lock = threading.Lock()
    
    def __init__(self, test_id: Optional[str] = None):
        """Initialize test isolation manager with unique test ID."""
        self.test_id = test_id or self._generate_test_id()
        self.ports: Dict[str, int] = {}
        self.directories: Dict[str, Path] = {}
        self.environment: Dict[str, str] = {}
        self.cleanup_registered = False
        
        # Base directories
        self.base_dir = Path(tempfile.gettempdir()) / "netra_tests" / self.test_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Track this instance
        with self._lock:
            self._instances[self.test_id] = self
    
    @staticmethod
    def _generate_test_id() -> str:
        """Generate unique test ID based on process, time, and random value."""
        unique_string = f"{os.getpid()}_{time.time()}_{os.urandom(4).hex()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    @staticmethod
    def get_free_port() -> int:
        """Get a free port by binding to port 0."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def allocate_ports(self) -> Dict[str, int]:
        """Allocate free ports for all services."""
        services = [
            'backend', 'frontend', 'postgres', 'redis', 
            'clickhouse', 'ws', 'test_server'
        ]
        
        for service in services:
            if service not in self.ports:
                self.ports[service] = self.get_free_port()
        
        return self.ports
    
    def get_redis_db_index(self) -> int:
        """Get unique Redis database index based on process ID."""
        # Redis typically supports 16 databases (0-15)
        # Use process ID to generate index, avoiding 0 (often used for production)
        base_index = (os.getpid() % 14) + 1
        
        # Add time-based offset for additional uniqueness
        time_offset = int(time.time()) % 5
        index = (base_index + time_offset) % 15
        
        return max(1, index)  # Ensure we never use database 0
    
    def setup_directories(self) -> Dict[str, Path]:
        """Create isolated directories for test outputs."""
        dirs = {
            'reports': self.base_dir / 'reports',
            'coverage': self.base_dir / 'reports' / 'coverage',
            'frontend_coverage': self.base_dir / 'reports' / 'frontend-coverage',
            'test_results': self.base_dir / 'reports' / 'tests',
            'pytest_cache': self.base_dir / '.pytest_cache',
            'jest_cache': self.base_dir / '.jest_cache',
            'next_cache': self.base_dir / '.next',
            'logs': self.base_dir / 'logs',
            'temp': self.base_dir / 'temp',
        }
        
        for name, path in dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            self.directories[name] = path
        
        return self.directories
    
    def _allocate_test_resources(self) -> Tuple[Dict[str, int], Dict[str, Path], int]:
        """Allocate ports, directories, and database indexes."""
        ports = self.allocate_ports()
        dirs = self.setup_directories()
        redis_db = self.get_redis_db_index()
        return ports, dirs, redis_db

    def _build_database_environment(self, ports: Dict, dirs: Dict, redis_db: int) -> Dict[str, str]:
        """Build database-related environment variables."""
        clickhouse_db = f"test_{self.test_id}"
        postgres_db = f"netra_test_{self.test_id}"
        
        return {
            'DATABASE_URL': f"sqlite+aiosqlite:///{dirs['temp']}/test.db",
            'POSTGRES_TEST_DB': postgres_db,
            'REDIS_URL': f"redis://localhost:6379/{redis_db}",
            'REDIS_DB_INDEX': str(redis_db),
            'CLICKHOUSE_URL': f"clickhouse://localhost:9000/{clickhouse_db}",
            'CLICKHOUSE_TEST_DB': clickhouse_db,
        }

    def _build_port_environment(self, ports: Dict[str, int]) -> Dict[str, str]:
        """Build port-related environment variables."""
        return {
            'BACKEND_PORT': str(ports.get('backend', 8000)),
            'FRONTEND_PORT': str(ports.get('frontend', 3000)),
            'WS_PORT': str(ports.get('ws', 8001)),
            'NEXT_PUBLIC_API_URL': f"http://localhost:{ports.get('backend', 8000)}",
            'PORT': str(ports.get('frontend', 3000)),
        }

    def _build_directory_environment(self, dirs: Dict[str, Path]) -> Dict[str, str]:
        """Build directory-related environment variables."""
        return {
            'REPORTS_DIR': str(dirs['reports']), 'COVERAGE_DIR': str(dirs['coverage']),
            'FRONTEND_COVERAGE_DIR': str(dirs['frontend_coverage']), 'TEST_RESULTS_DIR': str(dirs['test_results']),
            'PYTEST_CACHE_DIR': str(dirs['pytest_cache']), 'JEST_CACHE_DIR': str(dirs['jest_cache']),
            'NEXT_CACHE_DIR': str(dirs['next_cache']), 'LOG_DIR': str(dirs['logs']),
            'TEMP_DIR': str(dirs['temp']), 'LOG_FILE': str(dirs['logs'] / f"test_{self.test_id}.log"),
        }

    def _build_security_environment(self) -> Dict[str, str]:
        """Build security and API key environment variables."""
        return {
            'SECRET_KEY': f"test-secret-key-{self.test_id}",
            'JWT_SECRET': f"test-jwt-secret-{self.test_id}",
            'JWT_SECRET_KEY': f"test-jwt-secret-key-for-testing-only-must-be-32-chars-{self.test_id[:8]}",
            'FERNET_KEY': "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=",
            'ANTHROPIC_API_KEY': os.getenv("ANTHROPIC_API_KEY", "test-api-key"),
            'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY", "test-api-key"),
            'GOOGLE_CLIENT_ID': "test-google-client", 'GOOGLE_CLIENT_SECRET': "test-google-secret",
        }

    def _build_base_environment(self) -> Dict[str, str]:
        """Build base testing environment variables."""
        return {
            'TESTING': '1', 'TEST_ISOLATION': '1', 'TEST_RUN_ID': self.test_id,
            'LOG_LEVEL': 'WARNING', 'NODE_ENV': 'test', 'NEXT_TELEMETRY_DISABLED': '1',
            'DO_NOT_TRACK': '1', 'CI': 'true'
        }

    def setup_environment(self) -> Dict[str, str]:
        """Set up isolated environment variables."""
        ports, dirs, redis_db = self._allocate_test_resources()
        
        self.environment = {
            **self._build_base_environment(),
            **self._build_port_environment(ports),
            **self._build_database_environment(ports, dirs, redis_db),
            **self._build_directory_environment(dirs),
            **self._build_security_environment()
        }
        
        return self.environment
    
    def apply_environment(self) -> None:
        """Apply isolated environment variables to current process."""
        if not self.environment:
            self.setup_environment()
        
        for key, value in self.environment.items():
            os.environ[key] = value
    
    def get_pytest_args(self) -> list:
        """Get pytest arguments for isolated test execution."""
        dirs = self.directories or self.setup_directories()
        
        return [
            f"--cache-dir={dirs['pytest_cache']}",
            f"--cov-report=html:{dirs['coverage']}/html",
            f"--cov-report=json:{dirs['coverage']}/coverage.json",
            f"--html={dirs['test_results']}/report_{self.test_id}.html",
            f"--json-report-file={dirs['test_results']}/report_{self.test_id}.json",
            "--self-contained-html",
        ]
    
    def get_jest_args(self) -> list:
        """Get Jest arguments for isolated test execution."""
        dirs = self.directories or self.setup_directories()
        
        return [
            f"--cacheDirectory={dirs['jest_cache']}",
            f"--coverageDirectory={dirs['frontend_coverage']}",
            "--forceExit",
            "--detectOpenHandles",
        ]
    
    def cleanup(self, keep_reports: bool = False) -> None:
        """Clean up test isolation resources."""
        if keep_reports or os.environ.get('KEEP_TEST_REPORTS'):
            print(f"Test reports preserved at: {self.base_dir}")
            return
        
        try:
            if self.base_dir.exists():
                shutil.rmtree(self.base_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Failed to cleanup test directory: {e}")
    
    def register_cleanup(self) -> None:
        """Register cleanup to run on process exit."""
        if not self.cleanup_registered:
            atexit.register(lambda: self.cleanup())
            self.cleanup_registered = True
    
    def __enter__(self):
        """Context manager entry."""
        self.setup_environment()
        self.apply_environment()
        self.register_cleanup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Cleanup is handled by atexit
        pass
    
    @classmethod
    def get_instance(cls, test_id: Optional[str] = None) -> 'TestIsolationManager':
        """Get or create a test isolation manager instance."""
        if test_id and test_id in cls._instances:
            return cls._instances[test_id]
        return cls(test_id)
    
    def get_connection_string(self, service: str) -> str:
        """Get isolated connection string for a service."""
        ports = self.ports or self.allocate_ports()
        
        if service == 'backend':
            return f"http://localhost:{ports['backend']}"
        elif service == 'frontend':
            return f"http://localhost:{ports['frontend']}"
        elif service == 'websocket':
            return f"ws://localhost:{ports['ws']}"
        elif service == 'redis':
            redis_db = self.get_redis_db_index()
            return f"redis://localhost:6379/{redis_db}"
        elif service == 'postgres':
            return f"postgresql://test:test@localhost:{ports['postgres']}/{self.environment.get('POSTGRES_TEST_DB', 'test')}"
        elif service == 'clickhouse':
            return f"clickhouse://localhost:{ports['clickhouse']}/{self.environment.get('CLICKHOUSE_TEST_DB', 'test')}"
        else:
            raise ValueError(f"Unknown service: {service}")
    
    def print_isolation_info(self) -> None:
        """Print test isolation configuration for debugging."""
        print(f"\n{'='*60}")
        print(f"Test Isolation Configuration (ID: {self.test_id})")
        print(f"{'='*60}")
        
        if self.ports:
            print("\nAllocated Ports:")
            for service, port in sorted(self.ports.items()):
                print(f"  {service:15} : {port}")
        
        if self.directories:
            print("\nTest Directories:")
            for name, path in sorted(self.directories.items()):
                print(f"  {name:15} : {path}")
        
        print(f"\nRedis Database Index: {self.get_redis_db_index()}")
        print(f"Base Directory: {self.base_dir}")
        print(f"{'='*60}\n")


# Convenience functions
def create_isolated_test_env(test_id: Optional[str] = None) -> TestIsolationManager:
    """Create and configure an isolated test environment."""
    manager = TestIsolationManager(test_id)
    manager.setup_environment()
    manager.apply_environment()
    manager.register_cleanup()
    return manager


def get_isolated_pytest_args(manager: Optional[TestIsolationManager] = None) -> list:
    """Get pytest arguments for isolated execution."""
    if not manager:
        manager = TestIsolationManager()
    return manager.get_pytest_args()


def get_isolated_jest_args(manager: Optional[TestIsolationManager] = None) -> list:
    """Get Jest arguments for isolated execution."""
    if not manager:
        manager = TestIsolationManager()
    return manager.get_jest_args()