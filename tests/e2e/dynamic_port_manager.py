"""Dynamic Port Manager for E2E Tests
Manages port allocation dynamically for test environments, supporting both Docker
and local testing scenarios with automatic port detection.

BVJ:
- Segment: Platform/Internal
- Business Goal: Ensure reliable test execution across environments
- Value Impact: Prevents test failures due to port conflicts
- Strategic Impact: Enables parallel test execution and CI/CD reliability
"""

import os
import socket
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class TestMode(Enum):
    """Test execution modes"""
    LOCAL = "local"
    DOCKER = "docker"
    CI = "ci"


@dataclass
class ServicePorts:
    """Service port configuration"""
    backend: int
    auth: int
    frontend: int
    postgres: int
    redis: int
    clickhouse: int
    

class DynamicPortManager:
    """Manages dynamic port allocation for test services"""
    
    # Default ports for different modes
    DEFAULT_PORTS = {
        TestMode.LOCAL: ServicePorts(
            backend=8000,
            auth=8081,
            frontend=3000,
            postgres=5432,
            redis=6379,
            clickhouse=8123
        ),
        TestMode.DOCKER: ServicePorts(
            backend=8001,  # Test backend port
            auth=8082,     # Test auth port
            frontend=3001, # Test frontend port
            postgres=5433, # Test postgres port
            redis=6380,    # Test redis port
            clickhouse=8124 # Test clickhouse port
        ),
        TestMode.CI: ServicePorts(
            backend=0,  # Dynamic allocation
            auth=0,     # Dynamic allocation
            frontend=0, # Dynamic allocation
            postgres=0, # Dynamic allocation
            redis=0,    # Dynamic allocation
            clickhouse=0 # Dynamic allocation
        )
    }
    
    def __init__(self, mode: Optional[TestMode] = None):
        """Initialize port manager with detection mode"""
        self.mode = mode or self._detect_mode()
        self.allocated_ports: Dict[str, int] = {}
        self.ports = self._initialize_ports()
        
    def _detect_mode(self) -> TestMode:
        """Detect test execution mode from environment"""
        # Check if running in CI
        if os.environ.get("CI") == "true":
            return TestMode.CI
        # Check if running in Docker
        if os.environ.get("DOCKER_CONTAINER") == "true" or os.path.exists("/.dockerenv"):
            return TestMode.DOCKER
        # Default to local
        return TestMode.LOCAL
        
    def _initialize_ports(self) -> ServicePorts:
        """Initialize ports based on mode"""
        base_ports = self.DEFAULT_PORTS[self.mode]
        
        # Override with environment variables if set
        backend = int(os.environ.get("TEST_BACKEND_PORT", base_ports.backend))
        auth = int(os.environ.get("TEST_AUTH_PORT", base_ports.auth))
        frontend = int(os.environ.get("TEST_FRONTEND_PORT", base_ports.frontend))
        postgres = int(os.environ.get("TEST_POSTGRES_PORT", base_ports.postgres))
        redis = int(os.environ.get("TEST_REDIS_PORT", base_ports.redis))
        clickhouse = int(os.environ.get("TEST_CLICKHOUSE_PORT", base_ports.clickhouse))
        
        # If mode is CI or port is 0, allocate dynamically
        if self.mode == TestMode.CI:
            backend = backend or self._find_free_port()
            auth = auth or self._find_free_port()
            frontend = frontend or self._find_free_port()
            postgres = postgres or self._find_free_port()
            redis = redis or self._find_free_port()
            clickhouse = clickhouse or self._find_free_port()
            
        return ServicePorts(
            backend=backend,
            auth=auth,
            frontend=frontend,
            postgres=postgres,
            redis=redis,
            clickhouse=clickhouse
        )
        
    def _find_free_port(self) -> int:
        """Find a free port on the system"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
        
    def is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except OSError:
                return False
                
    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs with current ports"""
        host = "localhost"
        if self.mode == TestMode.DOCKER:
            # Use service names for Docker networking
            return {
                "backend": f"http://backend-test:{self.ports.backend}",
                "auth": f"http://auth-test:{self.ports.auth}",
                "frontend": f"http://frontend-test:{self.ports.frontend}",
                "websocket": f"ws://backend-test:{self.ports.backend}/ws",
                "postgres": f"postgresql://test:test@postgres-test:{self.ports.postgres}/netra_test",
                "redis": f"redis://redis-test:{self.ports.redis}/0",
                "clickhouse": f"clickhouse://clickhouse-test:{self.ports.clickhouse}/netra_test_analytics"
            }
        else:
            # Use localhost for local testing
            return {
                "backend": f"http://{host}:{self.ports.backend}",
                "auth": f"http://{host}:{self.ports.auth}",
                "frontend": f"http://{host}:{self.ports.frontend}",
                "websocket": f"ws://{host}:{self.ports.backend}/ws",
                "postgres": f"postgresql://test:test@{host}:{self.ports.postgres}/netra_test",
                "redis": f"redis://{host}:{self.ports.redis}/0",
                "clickhouse": f"clickhouse://{host}:{self.ports.clickhouse}/netra_test_analytics"
            }
            
    def export_to_env(self) -> None:
        """Export port configuration to environment variables"""
        os.environ["TEST_BACKEND_PORT"] = str(self.ports.backend)
        os.environ["TEST_AUTH_PORT"] = str(self.ports.auth)
        os.environ["TEST_FRONTEND_PORT"] = str(self.ports.frontend)
        os.environ["TEST_POSTGRES_PORT"] = str(self.ports.postgres)
        os.environ["TEST_REDIS_PORT"] = str(self.ports.redis)
        os.environ["TEST_CLICKHOUSE_PORT"] = str(self.ports.clickhouse)
        
        # Export service URLs
        urls = self.get_service_urls()
        os.environ["TEST_BACKEND_URL"] = urls["backend"]
        os.environ["TEST_AUTH_URL"] = urls["auth"]
        os.environ["TEST_FRONTEND_URL"] = urls["frontend"]
        os.environ["TEST_WEBSOCKET_URL"] = urls["websocket"]
        os.environ["DATABASE_URL"] = urls["postgres"]
        os.environ["REDIS_URL"] = urls["redis"]
        os.environ["CLICKHOUSE_URL"] = urls["clickhouse"]
        
    def wait_for_service(self, service: str, timeout: int = 30) -> bool:
        """Wait for a service to be available"""
        import time
        port = getattr(self.ports, service)
        host = "localhost"
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True
            time.sleep(0.5)
            
        return False
        
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            "mode": self.mode.value,
            "ports": {
                "backend": self.ports.backend,
                "auth": self.ports.auth,
                "frontend": self.ports.frontend,
                "postgres": self.ports.postgres,
                "redis": self.ports.redis,
                "clickhouse": self.ports.clickhouse
            },
            "urls": self.get_service_urls()
        }


# Global instance for easy access
_port_manager: Optional[DynamicPortManager] = None


def get_port_manager() -> DynamicPortManager:
    """Get or create the global port manager instance"""
    global _port_manager
    if _port_manager is None:
        _port_manager = DynamicPortManager()
        _port_manager.export_to_env()
    return _port_manager


def reset_port_manager() -> None:
    """Reset the global port manager instance"""
    global _port_manager
    _port_manager = None