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
        self.redis_client = MockRedisClient()  # Uses the comprehensive canonical MockRedisClient
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
    """
    Comprehensive Mock Redis client that consolidates all MockRedisClient implementations.
    
    This is the canonical MockRedisClient for all test infrastructure.
    Provides all Redis operations needed across the codebase with:
    - Complete Redis API compatibility (get, set, delete, incr, etc.)
    - TTL/expiration support with automatic cleanup
    - Failure simulation for error testing
    - Operation tracking for verification
    - Pattern matching for keys() method
    - Counter support for rate limiting tests
    """
    
    def __init__(self):
        """Initialize comprehensive mock redis client."""
        # Core storage
        self.data = {}  # Main key-value store
        self.ttls = {}  # TTL tracking (uses datetime objects)
        self.expires = {}  # Alternative expiration tracking for compatibility
        self.counters = {}  # Counter tracking for rate limiting
        
        # Connection state
        self.closed = False
        self.connection_count = 0
        
        # Operation tracking
        self.operation_count = 0
        self.command_history = []  # List of tuples: (command, *args)
        
        # Failure simulation
        self.should_fail = False
        self.failure_type = "connection"  # "connection" or "operation"
    
    async def ping(self):
        """Mock ping operation."""
        if self.should_fail and self.failure_type == "connection":
            import redis.asyncio as redis
            raise redis.ConnectionError("Mock connection failed")
        return True
    
    async def get(self, key: str):
        """Mock get operation with TTL support."""
        self.command_history.append(('get', key))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock get operation failed")
        
        # Check TTL expiration (supports both datetime and timestamp formats)
        if key in self.ttls:
            from datetime import datetime, UTC
            import time
            
            ttl_value = self.ttls[key]
            is_expired = False
            
            if isinstance(ttl_value, datetime):
                is_expired = datetime.now(UTC) > ttl_value
            else:
                # Assume timestamp
                is_expired = time.time() > ttl_value
            
            if is_expired:
                # Key has expired, remove it
                if key in self.data:
                    del self.data[key]
                del self.ttls[key]
                if key in self.counters:
                    del self.counters[key]
                return None
        
        # Check alternative expires format
        if key in self.expires:
            from datetime import datetime, UTC
            if datetime.now(UTC) > self.expires[key]:
                if key in self.data:
                    del self.data[key]
                del self.expires[key]
                if key in self.counters:
                    del self.counters[key]
                return None
        
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        """Mock set operation with optional TTL."""
        self.command_history.append(('set', key, value, ex))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock set operation failed")
        
        self.data[key] = str(value)
        
        # Set TTL if provided
        if ex:
            from datetime import datetime, UTC, timedelta
            import time
            
            # Support both datetime and timestamp formats
            self.ttls[key] = datetime.now(UTC) + timedelta(seconds=ex)
            self.expires[key] = datetime.now(UTC) + timedelta(seconds=ex)
        
        return True
    
    async def setex(self, key: str, time: int, value: str):
        """Mock setex operation - set key with expiration time."""
        self.command_history.append(('setex', key, time, value))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock setex operation failed")
        
        self.data[key] = str(value)
        
        # Set TTL
        from datetime import datetime, UTC, timedelta
        self.ttls[key] = datetime.now(UTC) + timedelta(seconds=time)
        self.expires[key] = datetime.now(UTC) + timedelta(seconds=time)
        
        return True
    
    async def delete(self, *keys):
        """Mock delete operation supporting multiple keys."""
        self.command_history.append(('delete', *keys))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock delete operation failed")
        
        deleted_count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted_count += 1
            if key in self.ttls:
                del self.ttls[key]
            if key in self.expires:
                del self.expires[key]
            if key in self.counters:
                del self.counters[key]
        
        # For single key deletion, return count; for multiple keys, return total count
        return deleted_count
    
    async def incr(self, key: str):
        """Mock increment operation."""
        self.command_history.append(('incr', key))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock incr operation failed")
        
        current = int(self.data.get(key, "0"))
        new_value = current + 1
        self.data[key] = str(new_value)
        
        # Track in counters for rate limiting
        self.counters[key] = new_value
        
        return new_value
    
    async def expire(self, key: str, seconds: int):
        """Mock expire operation to set TTL on existing key."""
        self.command_history.append(('expire', key, seconds))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock expire operation failed")
        
        if key in self.data:
            from datetime import datetime, UTC, timedelta
            import time
            
            self.ttls[key] = datetime.now(UTC) + timedelta(seconds=seconds)
            self.expires[key] = datetime.now(UTC) + timedelta(seconds=seconds)
            return True
        
        return False
    
    async def ttl(self, key: str):
        """Mock TTL operation to get remaining time to live."""
        self.command_history.append(('ttl', key))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock ttl operation failed")
        
        if key not in self.data:
            return -2  # Key doesn't exist
        
        if key not in self.ttls:
            return -1  # Key exists but no TTL set
        
        from datetime import datetime, UTC
        import time
        
        ttl_value = self.ttls[key]
        
        if isinstance(ttl_value, datetime):
            remaining = (ttl_value - datetime.now(UTC)).total_seconds()
        else:
            # Assume timestamp
            remaining = ttl_value - time.time()
        
        return max(int(remaining), -2) if remaining > 0 else -2
    
    async def keys(self, pattern: str):
        """Mock keys operation with pattern matching."""
        self.command_history.append(('keys', pattern))
        self.operation_count += 1
        
        if self.should_fail and self.failure_type == "operation":
            import redis.asyncio as redis
            raise redis.RedisError("Mock keys operation failed")
        
        # Simple pattern matching
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.data.keys() if k.startswith(prefix)]
        elif pattern.startswith("*"):
            suffix = pattern[1:]
            return [k for k in self.data.keys() if k.endswith(suffix)]
        else:
            # Exact match
            return [pattern] if pattern in self.data else []
    
    async def close(self):
        """Mock closing redis client."""
        self.closed = True
        self.connection_count = 0
    
    async def aclose(self):
        """Mock async closing redis client (alternative method name)."""
        await self.close()
    
    def clear_data(self):
        """Clear all mock data (useful for test cleanup)."""
        self.data.clear()
        self.ttls.clear()
        self.expires.clear()
        self.counters.clear()
        self.command_history.clear()
        self.operation_count = 0
    
    def set_failure_mode(self, should_fail: bool, failure_type: str = "connection"):
        """
        Set failure mode for testing error conditions.
        
        Args:
            should_fail: Whether operations should fail
            failure_type: Type of failure - "connection" or "operation"
        """
        self.should_fail = should_fail
        self.failure_type = failure_type
    
    def get_operation_history(self):
        """Get history of all operations performed."""
        return self.command_history.copy()
    
    def reset_operation_tracking(self):
        """Reset operation tracking counters and history."""
        self.operation_count = 0
        self.command_history.clear()


class MockClickHouseClient:
    """Mock ClickHouse client."""
    
    def __init__(self):
        """Initialize mock clickhouse client."""
        self.closed = False
    
    def close(self):
        """Mock closing clickhouse client."""
        self.closed = True
