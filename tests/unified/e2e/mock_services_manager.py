"""
Mock Services Manager for Startup Sequence Tests
Business Value: Fast test execution without real service startup overhead
Modular design: <300 lines, 8-line functions max
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class MockTimeoutException(Exception):
    """Mock timeout exception for HTTP requests."""
    pass


@dataclass
class MockServiceProcess:
    """Mock representation of a running service process."""
    name: str
    port: int
    health_url: str = ""
    startup_timeout: int = 30
    ready: bool = False
    startup_time: float = 0.0


class MockServicesManager:
    """Mock services manager that simulates service startup without real processes."""
    
    def __init__(self, project_root: Optional[Any] = None):
        """Initialize mock services manager."""
        self.project_root = project_root
        self.services: Dict[str, MockServiceProcess] = {}
        self.startup_delay = 0.1  # Simulate quick startup
        self.all_ready = False
        self._setup_mock_services()
    
    def _setup_mock_services(self) -> None:
        """Setup mock service configurations."""
        self.services = {
            "auth": MockServiceProcess("auth", 8081, "/health"),
            "backend": MockServiceProcess("backend", 8000, "/health"),  
            "frontend": MockServiceProcess("frontend", 3000, "/")
        }
    
    async def start_all_services(self) -> None:
        """Mock starting all services with simulated delays."""
        await self._start_auth_service()
        await self._start_backend_service()
        await self._start_frontend_service()
        self.all_ready = True
    
    async def _start_auth_service(self) -> None:
        """Mock start auth service."""
        service = self.services["auth"]
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def _start_backend_service(self) -> None:
        """Mock start backend service."""
        service = self.services["backend"] 
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def _start_frontend_service(self) -> None:
        """Mock start frontend service."""
        service = self.services["frontend"]
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def stop_all_services(self) -> None:
        """Mock stopping all services."""
        for service in self.services.values():
            service.ready = False
        self.all_ready = False
        await asyncio.sleep(0.01)  # Minimal cleanup delay
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get mock URLs for all services."""
        return {
            name: f"http://localhost:{svc.port}"
            for name, svc in self.services.items()
            if svc.ready
        }
    
    def is_all_ready(self) -> bool:
        """Check if all mock services are ready."""
        return self.all_ready and all(svc.ready for svc in self.services.values())
    
    async def health_status(self) -> Dict[str, Any]:
        """Get mock health status of all services."""
        return {
            name: {
                "ready": service.ready,
                "port": service.port,
                "process_alive": service.ready,
                "startup_time": service.startup_time
            }
            for name, service in self.services.items()
        }


class MockDatabaseConnections:
    """Mock database connections for testing."""
    
    def __init__(self):
        """Initialize mock database connections."""
        self.postgres_pool = MockPostgresPool()
        self.redis_client = MockRedisClient()
        self.clickhouse_client = MockClickHouseClient()
        self.connection_status = {}
    
    async def connect_all(self) -> None:
        """Mock connecting to all databases."""
        await asyncio.sleep(0.01)  # Minimal connection delay
        self.connection_status = {
            "postgresql": True,
            "clickhouse": True,
            "redis": True
        }
    
    async def disconnect_all(self) -> None:
        """Mock disconnecting from all databases."""
        await asyncio.sleep(0.01)  # Minimal disconnection delay
        self.connection_status = {}


class MockPostgresPool:
    """Mock PostgreSQL connection pool."""
    
    def __init__(self):
        """Initialize mock postgres pool."""
        self.closed = False
    
    async def close(self) -> None:
        """Mock closing pool."""
        self.closed = True


class MockRedisClient:
    """Mock Redis client."""
    
    def __init__(self):
        """Initialize mock redis client."""
        self.closed = False
    
    async def close(self) -> None:
        """Mock closing redis client."""
        self.closed = True


class MockClickHouseClient:
    """Mock ClickHouse client."""
    
    def __init__(self):
        """Initialize mock clickhouse client."""
        self.closed = False
    
    def close(self) -> None:
        """Mock closing clickhouse client."""
        self.closed = True


class MockE2EServiceOrchestrator:
    """Mock service orchestrator for testing."""
    
    def __init__(self):
        """Initialize mock orchestrator."""
        self.services_manager = MockServicesManager()
        self.ready = False
    
    async def start_test_environment(self, db_name: str) -> None:
        """Mock starting test environment."""
        await self.services_manager.start_all_services()
        await asyncio.sleep(0.01)  # Minimal setup delay
        self.ready = True
    
    async def stop_test_environment(self, db_name: str) -> None:
        """Mock stopping test environment."""
        await self.services_manager.stop_all_services()
        self.ready = False


class MockHttpClient:
    """Mock HTTP client for service health checks."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize mock HTTP client."""
        self.timeout = timeout
        self.closed = False
        self.service_responses = {
            "http://localhost:8081/health": 200,
            "http://localhost:8000/health": 200,
            "http://localhost:3000/": 200
        }
        self.failure_mode = False
    
    def set_failure_mode(self, enabled: bool, failed_services: List[str] = None) -> None:
        """Set failure mode for specific services."""
        self.failure_mode = enabled
        if not enabled:
            # Reset all to healthy
            self.service_responses = {
                "http://localhost:8081/health": 200,
                "http://localhost:8000/health": 200,
                "http://localhost:3000/": 200
            }
        elif enabled and failed_services:
            for service in failed_services:
                if service == "auth":
                    self.service_responses["http://localhost:8081/health"] = 503
                    # When auth fails, backend should also fail due to dependency
                    self.service_responses["http://localhost:8000/health"] = 503
                elif service == "backend":
                    self.service_responses["http://localhost:8000/health"] = 503
                elif service == "frontend":
                    self.service_responses["http://localhost:3000/"] = 503
    
    async def get(self, url: str, headers: Optional[Dict] = None) -> 'MockResponse':
        """Mock HTTP GET request."""
        # Simulate timeout for very short timeout values
        if self.timeout < 0.2:
            raise MockTimeoutException("Request timed out")
        
        await asyncio.sleep(0.01)  # Minimal request delay
        status_code = self.service_responses.get(url, 200)
        return MockResponse(status_code)
    
    async def aclose(self) -> None:
        """Mock closing HTTP client."""
        self.closed = True


class MockResponse:
    """Mock HTTP response."""
    
    def __init__(self, status_code: int):
        """Initialize mock response."""
        self.status_code = status_code