"""
SSOT Mock Service Endpoints for Offline Testing

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure  
- Business Goal: Enable development and testing in offline environments
- Value Impact: Developers can test without running full Docker stack
- Strategic Impact: Faster development cycles and offline capability

This module provides lightweight mock services that mimic the basic behavior
of backend, auth, and WebSocket services for offline testing scenarios.

CRITICAL: These are MOCKS for offline testing only. Real services are preferred.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from threading import Thread
import socket

try:
    from aiohttp import web, WebSocketResponse
    from aiohttp.web_ws import WSMsgType
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    # Create dummy classes to avoid attribute errors
    class DummyWeb:
        class Application: pass
        class WebSocketResponse: pass
        @staticmethod
        def json_response(*args, **kwargs): pass
        @staticmethod
        def HTTPUnauthorized(*args, **kwargs): pass
        class TCPSite: 
            def __init__(self, *args, **kwargs): pass
            async def start(self): pass
            async def stop(self): pass
        class AppRunner:
            def __init__(self, *args, **kwargs): pass
            async def setup(self): pass
            async def cleanup(self): pass
    
    class DummyWSMsgType:
        TEXT = "text"
        ERROR = "error"
    
    web = DummyWeb()
    WebSocketResponse = DummyWeb.WebSocketResponse
    WSMsgType = DummyWSMsgType()

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class MockServiceConfig:
    """Configuration for mock services."""
    backend_port: int = 18000  # Different from real service ports
    auth_port: int = 18001
    enable_websocket: bool = True
    enable_cors: bool = True
    delay_ms: int = 50  # Simulate network latency


class MockBackendService:
    """Lightweight mock backend service for offline testing."""
    
    def __init__(self, config: MockServiceConfig):
        self.config = config
        self.app = None
        self.runner = None
        self.site = None
        self._websocket_connections: List[WebSocketResponse] = []
        
    async def create_app(self) -> web.Application:
        """Create aiohttp application with mock endpoints."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for mock services")
            
        app = web.Application()
        
        # Add CORS middleware if enabled
        if self.config.enable_cors:
            # Simple CORS handling for testing
            async def cors_middleware(request, handler):
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                return response
            
            app.middlewares.append(cors_middleware)
        
        # Health endpoint
        app.router.add_get('/health', self.health_endpoint)
        
        # Chat endpoints
        app.router.add_get('/api/chat/history', self.get_chat_history)
        app.router.add_post('/api/chat/send', self.send_chat_message)
        
        # Thread endpoints
        app.router.add_post('/api/threads/create', self.create_thread)
        app.router.add_get('/api/threads', self.get_threads)
        
        # Agent endpoints
        app.router.add_get('/api/agents/status', self.get_agent_status)
        app.router.add_post('/api/agents/execute/{task_type}', self.execute_agent_task)
        
        # WebSocket endpoint
        if self.config.enable_websocket:
            app.router.add_get('/ws', self.websocket_handler)
        
        # User endpoints
        app.router.add_get('/api/user/profile', self.get_user_profile)
        app.router.add_get('/api/user/settings', self.get_user_settings)
        
        # Metrics endpoint
        app.router.add_get('/api/metrics', self.get_metrics)
        
        return app
    
    async def _simulate_delay(self):
        """Simulate network latency."""
        if self.config.delay_ms > 0:
            await asyncio.sleep(self.config.delay_ms / 1000.0)
    
    async def health_endpoint(self, request):
        """Mock health endpoint."""
        await self._simulate_delay()
        return web.json_response({
            "status": "healthy",
            "service": "netra-backend-mock",
            "timestamp": time.time(),
            "version": "mock-1.0.0"
        })
    
    async def get_chat_history(self, request):
        """Mock chat history endpoint."""
        await self._simulate_delay()
        thread_id = request.query.get('thread_id', 'mock-thread-1')
        
        return web.json_response([
            {
                "id": "mock-msg-1",
                "thread_id": thread_id,
                "role": "user",
                "content": "Hello, this is a mock message",
                "timestamp": time.time() - 3600
            },
            {
                "id": "mock-msg-2",
                "thread_id": thread_id,
                "role": "assistant", 
                "content": "This is a mock response from the backend service",
                "timestamp": time.time() - 3500
            }
        ])
    
    async def send_chat_message(self, request):
        """Mock send chat message endpoint."""
        await self._simulate_delay()
        data = await request.json()
        
        # Broadcast to WebSocket connections if any
        ws_message = {
            "type": "chat_response",
            "data": {
                "message": f"Mock response to: {data.get('message', 'unknown')}",
                "thread_id": data.get('thread_id', 'mock-thread-1'),
                "timestamp": time.time()
            }
        }
        
        await self._broadcast_to_websockets(ws_message)
        
        return web.json_response({
            "success": True,
            "message_id": f"mock-msg-{int(time.time())}",
            "response": "Message received by mock backend"
        })
    
    async def create_thread(self, request):
        """Mock create thread endpoint."""
        await self._simulate_delay()
        data = await request.json()
        
        return web.json_response({
            "thread_id": f"mock-thread-{int(time.time())}",
            "name": data.get('name', 'Mock Thread'),
            "created_at": time.time()
        })
    
    async def get_threads(self, request):
        """Mock get threads endpoint."""
        await self._simulate_delay()
        
        return web.json_response([
            {
                "thread_id": "mock-thread-1",
                "name": "Mock Thread 1",
                "created_at": time.time() - 86400,
                "message_count": 5
            },
            {
                "thread_id": "mock-thread-2", 
                "name": "Mock Thread 2",
                "created_at": time.time() - 3600,
                "message_count": 2
            }
        ])
    
    async def get_agent_status(self, request):
        """Mock agent status endpoint."""
        await self._simulate_delay()
        
        return web.json_response({
            "agents_active": 2,
            "agents_idle": 3,
            "total_agents": 5,
            "system_status": "operational",
            "mock": True
        })
    
    async def execute_agent_task(self, request):
        """Mock agent task execution endpoint."""
        await self._simulate_delay()
        task_type = request.match_info['task_type']
        data = await request.json()
        
        # Simulate agent execution with WebSocket events
        ws_events = [
            {"type": "agent_started", "task_type": task_type, "timestamp": time.time()},
            {"type": "agent_thinking", "status": "processing", "timestamp": time.time() + 1},
            {"type": "agent_completed", "result": "Mock task completed", "timestamp": time.time() + 2}
        ]
        
        for event in ws_events:
            await self._broadcast_to_websockets(event)
            await asyncio.sleep(0.1)  # Small delay between events
        
        return web.json_response({
            "task_id": f"mock-task-{int(time.time())}",
            "status": "completed",
            "result": f"Mock execution of {task_type} task",
            "mock": True
        })
    
    async def get_user_profile(self, request):
        """Mock user profile endpoint."""
        await self._simulate_delay()
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise web.HTTPUnauthorized(text="Mock auth required")
        
        return web.json_response({
            "user_id": "mock-user-123",
            "email": "mock@example.com",
            "name": "Mock User",
            "mock": True
        })
    
    async def get_user_settings(self, request):
        """Mock user settings endpoint."""
        await self._simulate_delay()
        
        return web.json_response({
            "theme": "light",
            "notifications": True,
            "language": "en",
            "mock": True
        })
    
    async def get_metrics(self, request):
        """Mock metrics endpoint."""
        await self._simulate_delay()
        
        return web.json_response({
            "requests_total": 1234,
            "response_time_avg": 0.15,
            "active_connections": len(self._websocket_connections),
            "uptime_seconds": 3600,
            "mock": True
        })
    
    async def websocket_handler(self, request):
        """Mock WebSocket endpoint."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._websocket_connections.append(ws)
        logger.info(f"Mock WebSocket connection established (total: {len(self._websocket_connections)})")
        
        try:
            # Send welcome message
            await ws.send_str(json.dumps({
                "type": "connection_established",
                "message": "Connected to mock backend WebSocket",
                "timestamp": time.time(),
                "mock": True
            }))
            
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        
                        # Handle different message types
                        if data.get('type') == 'ping':
                            response = {
                                "type": "pong",
                                "timestamp": time.time(),
                                "original": data,
                                "mock": True
                            }
                            await ws.send_str(json.dumps(response))
                            
                        elif data.get('type') == 'chat':
                            # Mock chat processing
                            await asyncio.sleep(0.5)  # Simulate thinking time
                            
                            response = {
                                "type": "chat_response",
                                "message": f"Mock response to: {data.get('message', 'unknown')}",
                                "thread_id": data.get('thread_id', 'mock-thread-1'),
                                "timestamp": time.time(),
                                "mock": True
                            }
                            await ws.send_str(json.dumps(response))
                            
                        else:
                            # Echo unknown messages
                            response = {
                                "type": "echo",
                                "original": data,
                                "timestamp": time.time(),
                                "mock": True
                            }
                            await ws.send_str(json.dumps(response))
                            
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON received",
                            "mock": True
                        }))
                        
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'Mock WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"Mock WebSocket error: {e}")
        finally:
            # Cleanup
            if ws in self._websocket_connections:
                self._websocket_connections.remove(ws)
            logger.info(f"Mock WebSocket connection closed (remaining: {len(self._websocket_connections)})")
        
        return ws
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSockets."""
        if not self._websocket_connections:
            return
        
        # Remove closed connections
        active_connections = []
        for ws in self._websocket_connections:
            if not ws.closed:
                active_connections.append(ws)
                try:
                    await ws.send_str(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {e}")
        
        self._websocket_connections = active_connections
    
    async def start(self):
        """Start the mock backend service."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available - cannot start mock backend service")
        
        self.app = await self.create_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', self.config.backend_port)
        await self.site.start()
        
        logger.info(f"Mock backend service started on http://localhost:{self.config.backend_port}")
    
    async def stop(self):
        """Stop the mock backend service."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Mock backend service stopped")


class MockAuthService:
    """Lightweight mock auth service for offline testing."""
    
    def __init__(self, config: MockServiceConfig):
        self.config = config
        self.app = None
        self.runner = None
        self.site = None
        
    async def create_app(self) -> web.Application:
        """Create aiohttp application with mock auth endpoints."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for mock services")
            
        app = web.Application()
        
        # Add CORS middleware if enabled
        if self.config.enable_cors:
            async def cors_middleware(request, handler):
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                return response
            
            app.middlewares.append(cors_middleware)
        
        # Auth endpoints
        app.router.add_get('/health', self.health_endpoint)
        app.router.add_post('/auth/register', self.register)
        app.router.add_post('/auth/login', self.login)
        app.router.add_get('/auth/verify', self.verify_token)
        app.router.add_post('/auth/refresh', self.refresh_token)
        app.router.add_post('/auth/logout', self.logout)
        app.router.add_get('/auth/profile', self.get_profile)
        
        return app
    
    async def _simulate_delay(self):
        """Simulate network latency."""
        if self.config.delay_ms > 0:
            await asyncio.sleep(self.config.delay_ms / 1000.0)
    
    async def health_endpoint(self, request):
        """Mock auth health endpoint."""
        await self._simulate_delay()
        return web.json_response({
            "status": "healthy",
            "service": "netra-auth-mock",
            "timestamp": time.time(),
            "version": "mock-1.0.0"
        })
    
    async def register(self, request):
        """Mock user registration."""
        await self._simulate_delay()
        data = await request.json()
        
        return web.json_response({
            "user": {
                "id": f"mock-user-{int(time.time())}",
                "email": data.get('email', 'mock@example.com'),
                "name": f"{data.get('first_name', 'Mock')} {data.get('last_name', 'User')}"
            },
            "access_token": "mock-jwt-token-123",
            "refresh_token": "mock-refresh-token-456",
            "mock": True
        })
    
    async def login(self, request):
        """Mock user login."""
        await self._simulate_delay()
        data = await request.json()
        
        # Accept any email/password for mock
        return web.json_response({
            "access_token": "mock-jwt-token-123",
            "refresh_token": "mock-refresh-token-456", 
            "expires_in": 3600,
            "user": {
                "id": "mock-user-123",
                "email": data.get('email', 'mock@example.com'),
                "name": "Mock User"
            },
            "mock": True
        })
    
    async def verify_token(self, request):
        """Mock token verification."""
        await self._simulate_delay()
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise web.HTTPUnauthorized(text="Mock token required")
        
        return web.json_response({
            "valid": True,
            "user": {
                "id": "mock-user-123",
                "email": "mock@example.com",
                "name": "Mock User",
                "permissions": ["read", "write"]
            },
            "expires_in": 3600,
            "mock": True
        })
    
    async def refresh_token(self, request):
        """Mock token refresh."""
        await self._simulate_delay()
        
        return web.json_response({
            "access_token": "mock-jwt-token-refreshed-789",
            "expires_in": 3600,
            "mock": True
        })
    
    async def logout(self, request):
        """Mock user logout."""
        await self._simulate_delay()
        return web.json_response({
            "success": True,
            "message": "Mock logout successful",
            "mock": True
        })
    
    async def get_profile(self, request):
        """Mock get user profile."""
        await self._simulate_delay()
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise web.HTTPUnauthorized(text="Mock auth required")
        
        return web.json_response({
            "id": "mock-user-123",
            "email": "mock@example.com", 
            "name": "Mock User",
            "created_at": time.time() - 86400,
            "mock": True
        })
    
    async def start(self):
        """Start the mock auth service."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available - cannot start mock auth service")
        
        self.app = await self.create_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', self.config.auth_port)
        await self.site.start()
        
        logger.info(f"Mock auth service started on http://localhost:{self.config.auth_port}")
    
    async def stop(self):
        """Stop the mock auth service."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Mock auth service stopped")


class MockServiceManager:
    """Manager for all mock services."""
    
    def __init__(self, config: Optional[MockServiceConfig] = None):
        self.config = config or MockServiceConfig()
        self.backend_service = MockBackendService(self.config)
        self.auth_service = MockAuthService(self.config)
        self._running = False
    
    def check_ports_available(self) -> bool:
        """Check if mock service ports are available."""
        for port in [self.config.backend_port, self.config.auth_port]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', port))
                if result == 0:  # Port is in use
                    logger.warning(f"Mock service port {port} already in use")
                    return False
            finally:
                sock.close()
        return True
    
    async def start_all(self):
        """Start all mock services."""
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available - cannot start mock services")
            return False
        
        if not self.check_ports_available():
            logger.warning("Mock service ports not available")
            return False
        
        try:
            await self.backend_service.start()
            await self.auth_service.start()
            self._running = True
            
            logger.info(f"Mock services started:")
            logger.info(f"  Backend: http://localhost:{self.config.backend_port}")
            logger.info(f"  Auth:    http://localhost:{self.config.auth_port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start mock services: {e}")
            await self.stop_all()
            return False
    
    async def stop_all(self):
        """Stop all mock services."""
        try:
            await self.backend_service.stop()
            await self.auth_service.stop()
            self._running = False
            logger.info("All mock services stopped")
        except Exception as e:
            logger.error(f"Error stopping mock services: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if mock services are running."""
        return self._running
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for mock services."""
        return {
            "backend_url": f"http://localhost:{self.config.backend_port}",
            "auth_url": f"http://localhost:{self.config.auth_port}",
            "websocket_url": f"ws://localhost:{self.config.backend_port}/ws"
        }


# Global mock service manager
_mock_manager: Optional[MockServiceManager] = None


def get_mock_service_manager() -> MockServiceManager:
    """Get global mock service manager instance."""
    global _mock_manager
    
    if _mock_manager is None:
        _mock_manager = MockServiceManager()
    
    return _mock_manager


async def start_mock_services_if_needed() -> bool:
    """Start mock services if real services are not available.
    
    Returns:
        True if mock services started successfully, False otherwise
    """
    if not AIOHTTP_AVAILABLE:
        logger.info("aiohttp not available - mock services cannot be started")
        return False
    
    manager = get_mock_service_manager()
    
    if manager.is_running:
        logger.debug("Mock services already running")
        return True
    
    return await manager.start_all()


async def stop_mock_services():
    """Stop mock services if running."""
    manager = get_mock_service_manager()
    if manager.is_running:
        await manager.stop_all()