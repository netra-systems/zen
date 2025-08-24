"""
HTTP and API mock implementations.
Consolidates all HTTP client mocks, service endpoint mocks, and API response mocks.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class MockTimeoutException(Exception):
    """Mock timeout exception for HTTP requests."""
    pass


class MockResponse:
    """Mock HTTP response with configurable status and content."""
    
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] = None, text: str = ""):
        """Initialize mock response."""
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    async def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        return self._json_data
        
    async def text(self) -> str:
        """Return text content."""
        return self.text
        
    def raise_for_status(self):
        """Raise exception for 4xx/5xx status codes."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} error")


class MockHttpClient:
    """Mock HTTP client for service health checks and API calls."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize mock HTTP client."""
        self.timeout = timeout
        self.closed = False
        self.service_responses = {
            "http://localhost:8081/health": MockResponse(200, {"status": "healthy"}),
            "http://localhost:8000/health": MockResponse(200, {"status": "healthy"}),
            "http://localhost:3000/": MockResponse(200, {"status": "ready"})
        }
        self.failure_mode = False
        self.request_history = []
        
    def set_failure_mode(self, enabled: bool, failed_services: List[str] = None):
        """Set failure mode for specific services."""
        self.failure_mode = enabled
        if not enabled:
            # Reset all to healthy
            self.service_responses = {
                "http://localhost:8081/health": MockResponse(200, {"status": "healthy"}),
                "http://localhost:8000/health": MockResponse(200, {"status": "healthy"}),
                "http://localhost:3000/": MockResponse(200, {"status": "ready"})
            }
        elif enabled and failed_services:
            for service in failed_services:
                if service == "auth":
                    self.service_responses["http://localhost:8081/health"] = MockResponse(
                        503, {"status": "unhealthy", "error": "Auth service down"}
                    )
                    # When auth fails, backend should also fail due to dependency
                    self.service_responses["http://localhost:8000/health"] = MockResponse(
                        503, {"status": "unhealthy", "error": "Auth dependency failed"}
                    )
                elif service == "backend":
                    self.service_responses["http://localhost:8000/health"] = MockResponse(
                        503, {"status": "unhealthy", "error": "Backend service down"}
                    )
                elif service == "frontend":
                    self.service_responses["http://localhost:3000/"] = MockResponse(
                        503, {"status": "unhealthy", "error": "Frontend service down"}
                    )
    
    def set_response(self, url: str, response: MockResponse):
        """Set custom response for a specific URL."""
        self.service_responses[url] = response
        
    async def get(self, url: str, headers: Optional[Dict] = None, **kwargs) -> MockResponse:
        """Mock HTTP GET request."""
        return await self._make_request("GET", url, headers=headers, **kwargs)
        
    async def post(self, url: str, json: Dict = None, data: Any = None, headers: Optional[Dict] = None, **kwargs) -> MockResponse:
        """Mock HTTP POST request."""
        return await self._make_request("POST", url, json=json, data=data, headers=headers, **kwargs)
        
    async def put(self, url: str, json: Dict = None, data: Any = None, headers: Optional[Dict] = None, **kwargs) -> MockResponse:
        """Mock HTTP PUT request."""
        return await self._make_request("PUT", url, json=json, data=data, headers=headers, **kwargs)
        
    async def delete(self, url: str, headers: Optional[Dict] = None, **kwargs) -> MockResponse:
        """Mock HTTP DELETE request."""
        return await self._make_request("DELETE", url, headers=headers, **kwargs)
        
    async def _make_request(self, method: str, url: str, **kwargs) -> MockResponse:
        """Internal method to make mock HTTP request."""
        # Record request in history
        self.request_history.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Simulate timeout for very short timeout values
        if self.timeout < 0.2:
            raise MockTimeoutException("Request timed out")
        
        # Simulate network delay
        await asyncio.sleep(0.01)
        
        # Return configured response or default
        response = self.service_responses.get(url, MockResponse(404, {"error": "Not found"}))
        return response
    
    async def aclose(self):
        """Mock closing HTTP client."""
        self.closed = True
        
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all requests made."""
        return self.request_history.copy()
        
    def clear_request_history(self):
        """Clear request history."""
        self.request_history.clear()


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
        
    def _setup_mock_services(self):
        """Setup mock service configurations."""
        self.services = {
            "auth": MockServiceProcess("auth", 8081, "/health"),
            "backend": MockServiceProcess("backend", 8000, "/health"),  
            "frontend": MockServiceProcess("frontend", 3000, "/")
        }
    
    async def start_all_services(self):
        """Mock starting all services with simulated delays."""
        await self._start_auth_service()
        await self._start_backend_service()
        await self._start_frontend_service()
        self.all_ready = True
    
    async def _start_auth_service(self):
        """Mock start auth service."""
        service = self.services["auth"]
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def _start_backend_service(self):
        """Mock start backend service."""
        service = self.services["backend"] 
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def _start_frontend_service(self):
        """Mock start frontend service."""
        service = self.services["frontend"]
        start_time = time.time()
        await asyncio.sleep(self.startup_delay)
        
        service.ready = True
        service.startup_time = time.time() - start_time
    
    async def stop_all_services(self):
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


class MockE2EServiceOrchestrator:
    """Mock service orchestrator for testing."""
    
    def __init__(self):
        """Initialize mock orchestrator."""
        self.services_manager = MockServicesManager()
        self.ready = False
    
    async def test_start_test_environment(self, db_name: str):
        """Mock starting test environment."""
        await self.services_manager.start_all_services()
        await asyncio.sleep(0.01)  # Minimal setup delay
        self.ready = True
    
    async def test_stop_test_environment(self, db_name: str):
        """Mock stopping test environment."""
        await self.services_manager.stop_all_services()
        self.ready = False


class MockQualityGateService:
    """Mock quality gate service for testing."""
    
    def __init__(self):
        """Initialize mock quality gate service."""
        self.validation_requests = []
        self.should_fail = False
        
    def set_failure_mode(self, enabled: bool):
        """Enable/disable failure simulation."""
        self.should_fail = enabled
        
    async def validate_content(self, content: str, content_type: str = None, context: Dict = None) -> Dict[str, Any]:
        """Mock content validation."""
        self.validation_requests.append({
            "content": content,
            "content_type": content_type,
            "context": context
        })
        
        if self.should_fail:
            return {
                "passed": False,
                "score": 0.3,
                "errors": ["Mock validation failure"],
                "metrics": {"quality_score": 0.3}
            }
        
        return {
            "passed": True,
            "score": 0.95,
            "errors": [],
            "metrics": {"quality_score": 0.95}
        }
        
    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get history of validation requests."""
        return self.validation_requests.copy()
        
    def clear_validation_history(self):
        """Clear validation request history."""
        self.validation_requests.clear()


class MockDatabaseConnections:
    """Mock database connections for testing."""
    
    def __init__(self):
        """Initialize mock database connections."""
        self.postgres_pool = MockPostgresPool()
        self.redis_client = MockRedisClient() 
        self.clickhouse_client = MockClickHouseClient()
        self.connection_status = {}
    
    async def connect_all(self):
        """Mock connecting to all databases."""
        await asyncio.sleep(0.01)  # Minimal connection delay
        self.connection_status = {
            "postgresql": True,
            "clickhouse": True,
            "redis": True
        }
    
    async def disconnect_all(self):
        """Mock disconnecting from all databases."""
        await asyncio.sleep(0.01)  # Minimal disconnection delay
        self.connection_status = {}


class MockPostgresPool:
    """Mock PostgreSQL connection pool."""
    
    def __init__(self):
        """Initialize mock postgres pool."""
        self.closed = False
    
    async def close(self):
        """Mock closing pool."""
        self.closed = True


class MockRedisClient:
    """Mock Redis client."""
    
    def __init__(self):
        """Initialize mock redis client."""
        self.closed = False
    
    async def close(self):
        """Mock closing redis client."""
        self.closed = True


class MockClickHouseClient:
    """Mock ClickHouse client."""
    
    def __init__(self):
        """Initialize mock clickhouse client."""
        self.closed = False
    
    def close(self):
        """Mock closing clickhouse client."""
        self.closed = True
