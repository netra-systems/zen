"""
Route Test Fixtures

Provides fixtures for testing API routes and endpoints.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, AsyncMock
import json
import uuid
from datetime import datetime, timezone, UTC


class MockRequest:
    """Mock HTTP request for testing."""
    
    def __init__(self, method: str = "GET", path: str = "/", 
                 headers: Dict[str, str] = None, body: Any = None,
                 query_params: Dict[str, str] = None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.body = body
        self.query_params = query_params or {}
        self.state = Mock()
        self.path_params = {}
        
    def json(self):
        """Get JSON body."""
        if isinstance(self.body, dict):
            return self.body
        elif isinstance(self.body, str):
            return json.loads(self.body)
        return {}
    
    def query_param(self, key: str, default: Any = None) -> Any:
        """Get query parameter."""
        return self.query_params.get(key, default)


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status_code: int = 200, content: Any = None,
                 headers: Dict[str, str] = None):
        self.status_code = status_code
        self.content = content or {}
        self.headers = headers or {}
        
    def json(self):
        """Get JSON content."""
        return self.content if isinstance(self.content, dict) else {}


class MockRouteHandler:
    """Mock route handler for testing."""
    
    def __init__(self):
        self.routes: Dict[str, Dict[str, Callable]] = {}
        self.middleware: List[Callable] = []
        self.request_history: List[Dict[str, Any]] = []
        
    def add_route(self, method: str, path: str, handler: Callable):
        """Add a route handler."""
        if path not in self.routes:
            self.routes[path] = {}
        self.routes[path][method.upper()] = handler
    
    def get(self, path: str):
        """Decorator for GET routes."""
        def decorator(handler):
            self.add_route("GET", path, handler)
            return handler
        return decorator
    
    def post(self, path: str):
        """Decorator for POST routes."""
        def decorator(handler):
            self.add_route("POST", path, handler)
            return handler
        return decorator
    
    def put(self, path: str):
        """Decorator for PUT routes."""
        def decorator(handler):
            self.add_route("PUT", path, handler)
            return handler
        return decorator
    
    def delete(self, path: str):
        """Decorator for DELETE routes."""
        def decorator(handler):
            self.add_route("DELETE", path, handler)
            return handler
        return decorator
    
    async def handle_request(self, request: MockRequest) -> MockResponse:
        """Handle a mock request."""
        self.request_history.append({
            "method": request.method,
            "path": request.path,
            "headers": request.headers,
            "query_params": request.query_params,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Apply middleware
        for middleware in self.middleware:
            try:
                await middleware(request)
            except Exception as e:
                return MockResponse(500, {"error": f"Middleware error: {str(e)}"})
        
        # Find handler
        handler = None
        if request.path in self.routes:
            handler = self.routes[request.path].get(request.method.upper())
        
        if not handler:
            return MockResponse(404, {"error": "Not found"})
        
        try:
            result = await handler(request)
            if isinstance(result, MockResponse):
                return result
            elif isinstance(result, dict):
                return MockResponse(200, result)
            else:
                return MockResponse(200, {"result": result})
        except Exception as e:
            return MockResponse(500, {"error": str(e)})


class MockAPIClient:
    """Mock API client for testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.default_headers = {"Content-Type": "application/json"}
        self.request_history: List[Dict[str, Any]] = []
        self.mock_responses: Dict[str, MockResponse] = {}
        
    def set_mock_response(self, method: str, path: str, response: MockResponse):
        """Set a mock response for a specific endpoint."""
        key = f"{method.upper()}:{path}"
        self.mock_responses[key] = response
    
    async def async_request(self, method: str, path: str, 
                           headers: Dict[str, str] = None,
                           json_data: Dict[str, Any] = None,
                           query_params: Dict[str, str] = None) -> MockResponse:
        """Make a mock HTTP request asynchronously."""
        full_headers = {**self.default_headers}
        if headers:
            full_headers.update(headers)
        
        self.request_history.append({
            "method": method.upper(),
            "path": path,
            "headers": full_headers,
            "json_data": json_data,
            "query_params": query_params,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Check for mock response
        key = f"{method.upper()}:{path}"
        if key in self.mock_responses:
            return self.mock_responses[key]
        
        # Default successful response
        return MockResponse(200, {"status": "success", "method": method, "path": path})
    
    def request(self, method: str, path: str, 
                headers: Dict[str, str] = None,
                json_data: Dict[str, Any] = None,
                json: Dict[str, Any] = None,  # Support both json_data and json parameter names
                query_params: Dict[str, str] = None) -> MockResponse:
        """Make a mock HTTP request synchronously."""
        # Handle both json_data and json parameter names
        if json is not None:
            json_data = json
        
        # Run the async method in the current event loop or create one if none exists
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to run in a new thread
                import threading
                import concurrent.futures
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    try:
                        return new_loop.run_until_complete(
                            self.async_request(method, path, headers, json_data, query_params)
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.async_request(method, path, headers, json_data, query_params)
                )
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.async_request(method, path, headers, json_data, query_params)
                )
            finally:
                loop.close()
    
    # Synchronous HTTP methods
    def get(self, path: str, **kwargs) -> MockResponse:
        """Make a GET request."""
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> MockResponse:
        """Make a POST request."""
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> MockResponse:
        """Make a PUT request."""
        return self.request("PUT", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> MockResponse:
        """Make a DELETE request."""
        return self.request("DELETE", path, **kwargs)
    
    def patch(self, path: str, **kwargs) -> MockResponse:
        """Make a PATCH request."""
        return self.request("PATCH", path, **kwargs)
    
    # Keep async methods for backward compatibility
    async def async_get(self, path: str, **kwargs) -> MockResponse:
        """Make a GET request asynchronously."""
        return await self.async_request("GET", path, **kwargs)
    
    async def async_post(self, path: str, **kwargs) -> MockResponse:
        """Make a POST request asynchronously."""
        return await self.async_request("POST", path, **kwargs)
    
    async def async_put(self, path: str, **kwargs) -> MockResponse:
        """Make a PUT request asynchronously."""
        return await self.async_request("PUT", path, **kwargs)
    
    async def async_delete(self, path: str, **kwargs) -> MockResponse:
        """Make a DELETE request asynchronously."""
        return await self.async_request("DELETE", path, **kwargs)
    
    def websocket_connect(self, path: str) -> 'MockWebSocketContext':
        """Context manager for WebSocket connections."""
        class MockWebSocketContext:
            def __init__(self, client):
                self.client = client
                self.websocket = None
            
            def __enter__(self):
                self.websocket = MockWebSocketConnection()
                return self.websocket
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.websocket:
                    try:
                        # Try to run in existing event loop
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Can't use run_until_complete in running loop, just mark as disconnected
                            self.websocket.is_connected = False
                        else:
                            loop.run_until_complete(self.websocket.close())
                    except RuntimeError:
                        # No event loop, just mark as disconnected
                        self.websocket.is_connected = False
        
        return MockWebSocketContext(self)


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str = None):
        self.connection_id = connection_id or str(uuid.uuid4())
        self.is_connected = True
        self.messages_sent: List[Dict[str, Any]] = []
        self.messages_received: List[Dict[str, Any]] = []
        self.close_code: Optional[int] = None
        
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON message."""
        if not self.is_connected:
            raise RuntimeError("WebSocket is not connected")
        
        self.messages_sent.append({
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON message."""
        if not self.is_connected:
            raise RuntimeError("WebSocket is not connected")
        
        if self.messages_received:
            message = self.messages_received.pop(0)
            return message["data"]
        
        # Default heartbeat message
        return {"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()}
    
    async def close(self, code: int = 1000):
        """Close WebSocket connection."""
        self.is_connected = False
        self.close_code = code
    
    def add_received_message(self, data: Dict[str, Any]):
        """Add a message to the received queue."""
        self.messages_received.append({
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


class MockRouteRegistry:
    """Registry for mock routes."""
    
    def __init__(self):
        self.routes: Dict[str, MockRouteHandler] = {}
        self.global_middleware: List[Callable] = []
    
    def create_router(self, prefix: str = "") -> MockRouteHandler:
        """Create a new route handler."""
        handler = MockRouteHandler()
        self.routes[prefix] = handler
        return handler
    
    def add_middleware(self, middleware: Callable):
        """Add global middleware."""
        self.global_middleware.append(middleware)
    
    async def handle_request(self, request: MockRequest) -> MockResponse:
        """Route request to appropriate handler."""
        # Apply global middleware
        for middleware in self.global_middleware:
            try:
                await middleware(request)
            except Exception as e:
                return MockResponse(500, {"error": f"Global middleware error: {str(e)}"})
        
        # Find matching router
        for prefix, handler in self.routes.items():
            if request.path.startswith(prefix):
                return await handler.handle_request(request)
        
        return MockResponse(404, {"error": "No router found"})


# Route fixture functions

def create_mock_request(method: str = "GET", path: str = "/", 
                       **kwargs) -> MockRequest:
    """Create a mock HTTP request."""
    return MockRequest(method, path, **kwargs)

def create_mock_response(status_code: int = 200, 
                        content: Any = None) -> MockResponse:
    """Create a mock HTTP response."""
    return MockResponse(status_code, content)

def create_mock_api_client(base_url: str = "http://localhost:8000") -> MockAPIClient:
    """Create a mock API client."""
    return MockAPIClient(base_url)

def create_mock_websocket() -> MockWebSocketConnection:
    """Create a mock WebSocket connection."""
    return MockWebSocketConnection()

def create_route_handler() -> MockRouteHandler:
    """Create a mock route handler."""
    return MockRouteHandler()

def create_route_registry() -> MockRouteRegistry:
    """Create a mock route registry."""
    return MockRouteRegistry()

# Predefined route fixtures

def setup_health_routes(handler: MockRouteHandler):
    """Set up health check routes."""
    
    @handler.get("/health")
    async def health_check(request: MockRequest):
        return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}
    
    @handler.get("/health/ready")
    async def readiness_check(request: MockRequest):
        return {"ready": True, "services": ["database", "cache", "queue"]}
    
    @handler.get("/health/live")
    async def liveness_check(request: MockRequest):
        return {"alive": True, "uptime": 12345}

def setup_auth_routes(handler: MockRouteHandler):
    """Set up authentication routes."""
    
    @handler.post("/auth/login")
    async def login(request: MockRequest):
        data = request.json()
        return {
            "token": f"mock_token_{uuid.uuid4().hex[:16]}",
            "user_id": data.get("username", "test_user"),
            "expires_in": 3600
        }
    
    @handler.post("/auth/logout")
    async def logout(request: MockRequest):
        return {"message": "Logged out successfully"}
    
    @handler.get("/auth/me")
    async def get_current_user(request: MockRequest):
        return {
            "user_id": "test_user",
            "email": "test@example.com",
            "permissions": ["user"]
        }

def setup_api_routes(handler: MockRouteHandler):
    """Set up basic API routes."""
    
    @handler.get("/api/status")
    async def api_status(request: MockRequest):
        return {"api": "active", "version": "1.0.0"}
    
    @handler.get("/api/info")
    async def api_info(request: MockRequest):
        return {
            "name": "Mock API",
            "version": "1.0.0",
            "endpoints": ["/health", "/auth", "/api"]
        }

def create_full_mock_app() -> MockRouteRegistry:
    """Create a fully configured mock application."""
    registry = create_route_registry()
    
    # Create routers for different prefixes
    main_router = registry.create_router("")
    api_router = registry.create_router("/api")
    auth_router = registry.create_router("/auth")
    
    # Set up routes
    setup_health_routes(main_router)
    setup_auth_routes(auth_router)
    setup_api_routes(api_router)
    
    return registry

# Test data and validators

TEST_USER_DATA = {
    "user_id": "test_user_123",
    "email": "test@example.com",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "role": "user",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
    "permissions": ["user:read", "user:update"]
}

TEST_DOCUMENT_DATA = {
    "document_id": "test_doc_123",
    "title": "Test Document",
    "content": "This is test document content for corpus testing.",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "author": "test_user_123",
    "tags": ["test", "document", "corpus"],
    "status": "published",
    "word_count": 10,
    "version": 1,
    "metadata": {
        "source": "test_suite",
        "category": "test_data",
        "language": "en"
    }
}


class MockServiceFactory:
    """Factory for creating mock services for testing."""
    
    def __init__(self):
        self.services = {}
        self.mocks = {}
    
    def create_mock_service(self, service_name: str, methods: List[str] = None):
        """Create a mock service with specified methods."""
        mock_service = Mock()
        
        # Add common async methods if not specified
        if methods is None:
            methods = ['initialize', 'cleanup', 'get_status', 'health_check']
        
        for method_name in methods:
            # Create async mock methods
            async_mock = AsyncMock()
            setattr(mock_service, method_name, async_mock)
        
        self.services[service_name] = mock_service
        return mock_service
    
    def get_service(self, service_name: str):
        """Get a mock service by name."""
        if service_name not in self.services:
            return self.create_mock_service(service_name)
        return self.services[service_name]
    
    def create_agent_service(self):
        """Create a mock agent service."""
        return self.create_mock_service('agent', [
            'create_agent', 'delete_agent', 'get_agent', 'list_agents',
            'update_agent', 'start_agent', 'stop_agent', 'get_agent_status'
        ])
    
    def create_websocket_service(self):
        """Create a mock websocket service."""
        return self.create_mock_service('websocket', [
            'connect', 'disconnect', 'send_message', 'broadcast',
            'get_connections', 'handle_message'
        ])
    
    def create_database_service(self):
        """Create a mock database service."""
        return self.create_mock_service('database', [
            'connect', 'disconnect', 'execute_query', 'fetch_one',
            'fetch_all', 'execute_transaction'
        ])


class CommonResponseValidators:
    """Common response validation utilities."""
    
    @staticmethod
    def validate_success_response(response: MockResponse, expected_keys: List[str] = None):
        """Validate a successful response."""
        assert response.status_code == 200
        content = response.json()
        
        if expected_keys:
            for key in expected_keys:
                assert key in content, f"Expected key '{key}' not found in response"
    
    @staticmethod
    def validate_error_response(response: MockResponse, expected_status = None):
        """Validate an error response."""
        if expected_status is None:
            expected_status = 400
        elif isinstance(expected_status, list):
            # Support list of acceptable status codes
            assert response.status_code in expected_status, f"Expected status in {expected_status}, got {response.status_code}"
            return
        
        assert response.status_code == expected_status
        content = response.json()
        assert "error" in content or "message" in content
    
    @staticmethod
    def validate_auth_response(response: MockResponse):
        """Validate an authentication response."""
        assert response.status_code == 200
        content = response.json()
        assert "token" in content
        assert "user_id" in content
    
    @staticmethod
    def validate_user_data(data: Dict[str, Any]):
        """Validate user data structure."""
        required_fields = ["user_id", "email", "username"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from user data"


def basic_test_client():
    """Create a basic test client for route testing."""
    return create_mock_api_client("http://localhost:8000")


def agent_test_client():
    """Create an agent-specific test client for route testing."""
    client = create_mock_api_client("http://localhost:8000")
    
    # Set up common agent responses
    client.set_mock_response("GET", "/agents", MockResponse(200, {
        "agents": [],
        "total": 0,
        "page": 1,
        "page_size": 10
    }))
    
    client.set_mock_response("POST", "/agents", MockResponse(201, {
        "agent_id": "test_agent_123",
        "name": "Test Agent",
        "status": "created",
        "created_at": datetime.now(UTC).isoformat()
    }))
    
    client.set_mock_response("GET", "/agents/test_agent_123", MockResponse(200, {
        "agent_id": "test_agent_123",
        "name": "Test Agent",
        "status": "running",
        "created_at": datetime.now(UTC).isoformat(),
        "last_activity": datetime.now(UTC).isoformat()
    }))
    
    return client


# Test data generators

def generate_test_requests(count: int = 10) -> List[MockRequest]:
    """Generate test requests."""
    methods = ["GET", "POST", "PUT", "DELETE"]
    paths = ["/api/users", "/api/posts", "/api/comments", "/health"]
    
    requests = []
    for i in range(count):
        method = methods[i % len(methods)]
        path = paths[i % len(paths)]
        
        request = MockRequest(
            method=method,
            path=f"{path}/{i}" if method != "POST" else path,
            headers={"User-Agent": f"TestClient/{i}"},
            query_params={"page": str(i), "limit": "10"}
        )
        requests.append(request)
    
    return requests

def create_route_test_data() -> Dict[str, Any]:
    """Create comprehensive route test data."""
    return {
        "endpoints": [
            {"method": "GET", "path": "/health", "expected_status": 200},
            {"method": "POST", "path": "/auth/login", "expected_status": 200},
            {"method": "GET", "path": "/api/status", "expected_status": 200},
            {"method": "GET", "path": "/nonexistent", "expected_status": 404}
        ],
        "test_payloads": [
            {"username": "test_user", "password": "test_password"},
            {"email": "test@example.com", "name": "Test User"},
            {"query": "test search", "filters": {"active": True}}
        ],
        "headers": [
            {"Authorization": "Bearer mock_token_123"},
            {"Content-Type": "application/json"},
            {"User-Agent": "TestClient/1.0"}
        ]
    }