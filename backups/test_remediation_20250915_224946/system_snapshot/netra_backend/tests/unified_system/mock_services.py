"""
Mock Service Infrastructure for Unified System Testing.

Business Value: Enables controlled testing of external dependencies.
Supports mocking OAuth providers, LLM services, and other external APIs.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import websockets
from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

logger = logging.getLogger(__name__)

@dataclass
class MockResponse:
    """Standard mock response structure."""
    status_code: int
    data: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None

@dataclass
class MockServiceConfig:
    """Configuration for mock service."""
    name: str
    host: str = "localhost"
    port: int = 8888

class MockOAuthProvider:
    """Mock OAuth provider for testing authentication flows."""
    
    def __init__(self, provider_name: str = "google"):
        self.provider_name = provider_name
        self._auth_codes: Dict[str, Dict[str, Any]] = {}
        self._access_tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_auth_code(self, user_id: str, email: str) -> str:
        """Generate mock authorization code."""
        code = f"mock_auth_code_{user_id}_{hash(email) % 10000}"
        self._store_auth_code(code, user_id, email)
        return code
    
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange auth code for access token."""
        if code not in self._auth_codes:
            return None
        return self._create_token_response(code)
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from access token."""
        if access_token not in self._access_tokens:
            return None
        return self._access_tokens[access_token]
    
    def _store_auth_code(self, code: str, user_id: str, email: str) -> None:
        """Store authorization code with user data."""
        self._auth_codes[code] = {
            "user_id": user_id,
            "email": email,
            "expires_at": self._get_expiry_time()
        }
    
    def _create_token_response(self, code: str) -> Dict[str, Any]:
        """Create access token response."""
        user_data = self._auth_codes[code]
        token = f"mock_access_token_{code}"
        self._access_tokens[token] = user_data
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600
        }
    
    def _get_expiry_time(self) -> float:
        """Get token expiry timestamp."""
        import time
        return time.time() + 3600

class MockLLMService:
    """Mock LLM service for testing AI interactions."""
    
    def __init__(self, model_name: str = "mock-gpt-4"):
        self.model_name = model_name
        self._responses: List[str] = []
        self._response_index = 0
    
    def set_responses(self, responses: List[str]) -> None:
        """Set predetermined responses for testing."""
        self._responses = responses
        self._response_index = 0
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate mock completion response."""
        response_text = self._get_next_response()
        return self._create_completion_response(response_text, prompt)
    
    async def generate_streaming_completion(self, prompt: str, **kwargs):
        """Generate mock streaming completion."""
        response_text = self._get_next_response()
        for chunk in self._chunk_response(response_text):
            yield chunk
    
    def _get_next_response(self) -> str:
        """Get next predetermined response."""
        if not self._responses:
            return "Mock AI response for testing purposes."
        
        response = self._responses[self._response_index]
        self._response_index = (self._response_index + 1) % len(self._responses)
        return response
    
    def _create_completion_response(self, text: str, prompt: str) -> Dict[str, Any]:
        """Create structured completion response."""
        return {
            "id": f"mock-completion-{hash(prompt) % 10000}",
            "model": self.model_name,
            "choices": [{
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 25}
        }
    
    def _chunk_response(self, text: str) -> List[Dict[str, Any]]:
        """Split response into streaming chunks."""
        words = text.split()
        chunks = []
        for i, word in enumerate(words):
            chunks.append({
                "id": f"chunk-{i}",
                "choices": [{"delta": {"content": word + " "}}]
            })
        return chunks

class MockWebSocketServer:
    """Mock WebSocket server for testing real-time communication."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self._server = None
        self._connections: set = set()
        self._message_handlers: Dict[str, callable] = {}
    
    async def start(self) -> None:
        """Start the mock WebSocket server."""
        self._server = await websockets.serve(
            self._handle_connection, self.host, self.port
        )
        logger.info(f"Mock WebSocket server started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the mock WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("Mock WebSocket server stopped")
    
    def register_handler(self, message_type: str, handler: callable) -> None:
        """Register message handler for specific type."""
        self._message_handlers[message_type] = handler
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        if not self._connections:
            return
        
        message_json = json.dumps(message)
        await self._send_to_all_connections(message_json)
    
    async def _handle_connection(self, websocket, path: str) -> None:
        """Handle new WebSocket connection."""
        self._connections.add(websocket)
        try:
            await self._process_messages(websocket)
        finally:
            self._connections.remove(websocket)
    
    async def _process_messages(self, websocket) -> None:
        """Process incoming messages from connection."""
        async for message_raw in websocket:
            await self._handle_message(websocket, message_raw)
    
    async def _handle_message(self, websocket, message_raw: str) -> None:
        """Handle individual message from connection."""
        try:
            message = json.loads(message_raw)
            response = await self._process_message(message)
            if response:
                await websocket.send(json.dumps(response))
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"error": "Invalid JSON"}))
    
    async def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process message and generate response."""
        message_type = message.get("type", "unknown")
        handler = self._message_handlers.get(message_type)
        
        if handler:
            return await handler(message)
        return {"type": "echo", "data": message}
    
    async def _send_to_all_connections(self, message: str) -> None:
        """Send message to all active connections."""
        if not self._connections:
            return
        
        disconnected = set()
        for connection in self._connections:
            try:
                await connection.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(connection)
        
        # Remove disconnected connections
        self._connections -= disconnected

class MockHTTPService:
    """Mock HTTP service with health endpoints."""
    
    def __init__(self, service_name: str, port: int, host: str = "localhost"):
        self.service_name = service_name
        self.host = host
        self.port = port
        self.app = None
        self.server = None
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup mock HTTP routes."""
        self.app = web.Application()
        self.app.router.add_get('/health', self._health_handler)
        self.app.router.add_get('/status', self._status_handler)
        
        # Service-specific routes
        if self.service_name == "auth-service":
            self.app.router.add_post('/auth/login', self._auth_login_handler)
            self.app.router.add_post('/auth/logout', self._auth_logout_handler)
            self.app.router.add_get('/auth/verify', self._auth_verify_handler)
        elif self.service_name == "backend-service":
            self.app.router.add_get('/api/users', self._api_users_handler)
            self.app.router.add_get('/api/systems', self._api_systems_handler)
        elif self.service_name == "frontend-service":
            self.app.router.add_get('/', self._frontend_handler)
    
    async def _health_handler(self, request) -> web.Response:
        """Mock health check endpoint."""
        health_data = {
            "status": "healthy",
            "service": self.service_name,
            "timestamp": time.time(),
            "version": "1.0.0-mock",
            "checks": {
                "database": "healthy",
                "memory": "healthy",
                "disk": "healthy"
            },
            "metrics": {
                "uptime_seconds": 3600,
                "memory_usage_mb": 128,
                "cpu_usage_percent": 15
            }
        }
        return web.json_response(health_data)
    
    async def _status_handler(self, request) -> web.Response:
        """Mock status endpoint."""
        status_data = {
            "service": self.service_name,
            "status": "running",
            "environment": "test"
        }
        return web.json_response(status_data)
    
    async def _auth_login_handler(self, request) -> web.Response:
        """Mock auth login endpoint."""
        return web.json_response({
            "access_token": "mock_token_123",
            "token_type": "Bearer",
            "expires_in": 3600
        })
    
    async def _auth_logout_handler(self, request) -> web.Response:
        """Mock auth logout endpoint."""
        return web.json_response({"message": "Logged out successfully"})
    
    async def _auth_verify_handler(self, request) -> web.Response:
        """Mock auth verification endpoint."""
        return web.json_response({
            "valid": True,
            "user_id": "test_user_123"
        })
    
    async def _api_users_handler(self, request) -> web.Response:
        """Mock API users endpoint."""
        return web.json_response({
            "users": [{
                "id": 1,
                "username": "test_user",
                "email": "test@example.com"
            }]
        })
    
    async def _api_systems_handler(self, request) -> web.Response:
        """Mock API systems endpoint."""
        return web.json_response({
            "systems": [{
                "id": 1,
                "name": "test_system",
                "status": "active"
            }]
        })
    
    async def _frontend_handler(self, request) -> web.Response:
        """Mock frontend handler."""
        return web.Response(text="Mock Frontend Service", content_type="text/html")
    
    async def start(self) -> None:
        """Start the mock HTTP service."""
        from aiohttp import ClientSession
        
        # Use aiohttp test server which handles ports automatically
        self.server = TestServer(self.app, host=self.host)
        await self.server.start_server()
        
        # Update the port to the actual assigned port
        self.port = self.server.port
        logger.info(f"Mock HTTP service '{self.service_name}' started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the mock HTTP service."""
        if self.server:
            await self.server.close()
        logger.info(f"Mock HTTP service '{self.service_name}' stopped")
    
    @property
    def url(self) -> str:
        """Get the service URL."""
        if self.server and hasattr(self.server, 'port'):
            return f"http://{self.host}:{self.server.port}"
        return f"http://{self.host}:{self.port}"

class MockWebSocketService:
    """Enhanced mock WebSocket service."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.app = None
        self.server = None
        self._connections: set = set()
        self._message_handlers: Dict[str, callable] = {}
        self._setup_websocket_app()
    
    def _setup_websocket_app(self) -> None:
        """Setup WebSocket application."""
        self.app = web.Application()
        self.app.router.add_get('/ws', self._websocket_handler)
        self.app.router.add_get('/health', self._ws_health_handler)
    
    async def _websocket_handler(self, request) -> web.WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._connections.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        response = await self._process_message(data)
                        if response:
                            await ws.send_str(json.dumps(response))
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({"error": "Invalid JSON"}))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self._connections.discard(ws)
        
        return ws
    
    async def _ws_health_handler(self, request) -> web.Response:
        """WebSocket health endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "websocket-service",
            "active_connections": len(self._connections)
        })
    
    async def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process WebSocket message."""
        message_type = message.get("type", "unknown")
        handler = self._message_handlers.get(message_type)
        
        if handler:
            return await handler(message)
        
        # Default echo response
        return {
            "type": "echo",
            "data": message,
            "timestamp": time.time()
        }
    
    def register_handler(self, message_type: str, handler: callable) -> None:
        """Register message handler."""
        self._message_handlers[message_type] = handler
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        if not self._connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for ws in self._connections:
            try:
                await ws.send_str(message_str)
            except Exception:
                disconnected.add(ws)
        
        self._connections -= disconnected
    
    async def start(self) -> None:
        """Start WebSocket service."""
        self.server = TestServer(self.app, host=self.host)
        await self.server.start_server()
        
        # Update port to actual assigned port
        self.port = self.server.port
        logger.info(f"Mock WebSocket service started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop WebSocket service."""
        if self.server:
            await self.server.close()
        logger.info("Mock WebSocket service stopped")
    
    @property
    def url(self) -> str:
        """Get the WebSocket service URL."""
        if self.server and hasattr(self.server, 'port'):
            return f"http://{self.host}:{self.server.port}"
        return f"http://{self.host}:{self.port}"

class ServiceRegistry:
    """Registry for managing mock services."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._running_services: Dict[str, Any] = {}
    
    def register_oauth_provider(self, name: str, provider: MockOAuthProvider) -> None:
        """Register OAuth provider mock."""
        self._services[f"oauth_{name}"] = provider
    
    def register_llm_service(self, name: str, service: MockLLMService) -> None:
        """Register LLM service mock."""
        self._services[f"llm_{name}"] = service
    
    def register_websocket_server(self, name: str, server: MockWebSocketServer) -> None:
        """Register WebSocket server mock."""
        self._services[f"websocket_{name}"] = server
    
    def register_http_service(self, name: str, service: MockHTTPService) -> None:
        """Register HTTP service mock."""
        self._services[f"http_{name}"] = service
    
    def register_websocket_service(self, name: str, service: MockWebSocketService) -> None:
        """Register WebSocket service mock."""
        self._services[f"ws_{name}"] = service
    
    async def start_all_services(self) -> None:
        """Start all registered services that have start methods."""
        for name, service in self._services.items():
            if hasattr(service, 'start'):
                await service.start()
                self._running_services[name] = service
    
    async def stop_all_services(self) -> None:
        """Stop all running services."""
        for name, service in self._running_services.items():
            if hasattr(service, 'stop'):
                await service.stop()
        self._running_services.clear()
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get registered service by name."""
        return self._services.get(name)
    
    def get_http_service_url(self, service_name: str) -> Optional[str]:
        """Get HTTP service URL by name."""
        service = self._services.get(f"http_{service_name}")
        if service and hasattr(service, 'url'):
            return service.url
        return None

# Convenience functions for creating mock services
def create_mock_auth_service(port: int = 0) -> MockHTTPService:
    """Create mock auth service with dynamic port allocation."""
    return MockHTTPService("auth-service", port)

def create_mock_backend_service(port: int = 0) -> MockHTTPService:
    """Create mock backend service with dynamic port allocation."""
    return MockHTTPService("backend-service", port)

def create_mock_frontend_service(port: int = 0) -> MockHTTPService:
    """Create mock frontend service with dynamic port allocation."""
    return MockHTTPService("frontend-service", port)

def create_mock_websocket_service(port: int = 0) -> MockWebSocketService:
    """Create mock WebSocket service with dynamic port allocation."""
    return MockWebSocketService(port=port)

async def setup_unified_mock_services() -> ServiceRegistry:
    """Setup complete mock service environment for unified testing."""
    registry = ServiceRegistry()
    
    # Register HTTP services with dynamic port allocation
    auth_service = create_mock_auth_service()
    backend_service = create_mock_backend_service()
    frontend_service = create_mock_frontend_service()
    
    registry.register_http_service("auth", auth_service)
    registry.register_http_service("backend", backend_service)
    registry.register_http_service("frontend", frontend_service)
    
    # Register WebSocket service with dynamic port allocation
    ws_service = create_mock_websocket_service()
    registry.register_websocket_service("main", ws_service)
    
    # Register other mock services
    oauth_provider = MockOAuthProvider("google")
    llm_service = MockLLMService("mock-gpt-4")
    
    registry.register_oauth_provider("google", oauth_provider)
    registry.register_llm_service("openai", llm_service)
    
    return registry