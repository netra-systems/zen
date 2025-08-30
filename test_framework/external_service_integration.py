"""External Service Integration for IsolatedEnvironment Test Infrastructure.

This module provides integration patterns for external services including:
- WebSocket connections and testing
- HTTP clients with real endpoint testing
- LLM service integration with rate limiting and cost controls
- Auth service staging endpoint configuration
- File system isolation for tests that write files

Business Value: Platform/Internal - External Integration Excellence  
Enables comprehensive testing of external integrations without mocks.

Key Features:
- Real WebSocket server infrastructure for testing
- HTTP client with staging endpoint integration
- LLM service integration with cost controls
- File system isolation and cleanup
- Rate limiting and circuit breakers
- Health monitoring for external dependencies
"""

import asyncio
import contextlib
import json
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Set, Union, AsyncIterator,
    Callable, Tuple, NamedTuple
)
from urllib.parse import urljoin
import threading
import weakref

# Core environment management
from netra_backend.app.core.isolated_environment import get_env
from test_framework.isolated_environment_manager import TestResource, ResourceType

# External service dependencies with graceful fallback
try:
    import websockets
    from websockets import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    
try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExternalServiceConfig:
    """Configuration for external service integrations."""
    
    # WebSocket configuration
    websocket_host: str = "localhost"
    websocket_port: int = 8765
    websocket_timeout: float = 30.0
    enable_websocket_logging: bool = True
    
    # HTTP client configuration
    http_timeout: float = 30.0
    http_max_connections: int = 10
    http_max_keepalive: int = 5
    enable_http_retry: bool = True
    http_retry_count: int = 3
    http_retry_delay: float = 1.0
    
    # Auth service configuration
    auth_service_url: str = "http://localhost:8082"
    auth_service_timeout: float = 30.0
    auth_test_user_email: str = "test@example.com"
    auth_test_user_password: str = "test_password_123"
    
    # LLM service configuration
    enable_real_llm: bool = False
    llm_rate_limit_rpm: int = 60
    llm_cost_limit_usd: float = 1.0
    llm_timeout: float = 60.0
    llm_retry_count: int = 2
    
    # File system isolation
    temp_dir_prefix: str = "netra_test_fs_"
    auto_cleanup_files: bool = True
    file_isolation_enabled: bool = True
    max_file_size_mb: int = 100
    
    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    circuit_breaker_retry_timeout: float = 30.0


class CircuitBreakerState:
    """Circuit breaker state for external service resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
        
    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit breaker state."""
        with self._lock:
            if self.state == "CLOSED":
                return True
            elif self.state == "OPEN":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            else:  # HALF_OPEN
                return True
                
    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            
    def record_failure(self) -> None:
        """Record failed execution."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"


class WebSocketTestResource(TestResource):
    """WebSocket test resource for real WebSocket testing."""
    
    def __init__(self, resource_id: str, config: ExternalServiceConfig):
        super().__init__(resource_id, ResourceType.WEBSOCKET_CONNECTION)
        self.config = config
        self.server = None
        self.server_task = None
        self.client = None
        self.server_port = config.websocket_port
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.message_handlers: Dict[str, Callable] = {}
        self.received_messages: List[Dict] = []
        
    async def initialize(self) -> None:
        """Initialize WebSocket test server and client."""
        await super().initialize()
        
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets not available for WebSocket testing")
            
        # Start test WebSocket server
        await self._start_test_server()
        
        # Create test client
        await self._create_test_client()
        
        self.add_cleanup_callback(self._cleanup_websocket)
        
        logger.debug(f"WebSocket test resource {self.resource_id} initialized on port {self.server_port}")
        
    async def _start_test_server(self) -> None:
        """Start WebSocket test server."""
        async def server_handler(websocket, path):
            """Handle WebSocket connections."""
            self.connected_clients.add(websocket)
            try:
                async for message in websocket:
                    await self._handle_server_message(websocket, message)
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.connected_clients.discard(websocket)
                
        # Find available port
        for port in range(self.config.websocket_port, self.config.websocket_port + 100):
            try:
                self.server = await websockets.serve(
                    server_handler,
                    self.config.websocket_host,
                    port,
                    timeout=self.config.websocket_timeout
                )
                self.server_port = port
                break
            except OSError:
                continue
        else:
            raise RuntimeError("No available WebSocket port found")
            
    async def _create_test_client(self) -> None:
        """Create WebSocket test client."""
        server_url = f"ws://{self.config.websocket_host}:{self.server_port}"
        
        try:
            self.client = await websockets.connect(
                server_url,
                timeout=self.config.websocket_timeout
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect WebSocket client: {e}")
            
    async def _handle_server_message(self, websocket, message):
        """Handle incoming WebSocket message on server."""
        try:
            data = json.loads(message)
            self.received_messages.append({
                'timestamp': time.time(),
                'websocket': websocket,
                'data': data
            })
            
            # Execute registered handlers
            message_type = data.get('type', 'unknown')
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](data)
                if response:
                    await websocket.send(json.dumps(response))
                    
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            
    async def _cleanup_websocket(self) -> None:
        """Clean up WebSocket server and client."""
        try:
            # Close client
            if self.client:
                await self.client.close()
                self.client = None
                
            # Close server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.server = None
                
        except Exception as e:
            logger.warning(f"Error cleaning up WebSocket for {self.resource_id}: {e}")
            
    async def send_message(self, message: Union[str, Dict]) -> None:
        """Send message from client to server."""
        if not self.client:
            raise RuntimeError("WebSocket client not connected")
            
        if isinstance(message, dict):
            message = json.dumps(message)
            
        await self.client.send(message)
        self.touch()
        
    async def receive_message(self, timeout: Optional[float] = None) -> Dict:
        """Receive message from server to client."""
        if not self.client:
            raise RuntimeError("WebSocket client not connected")
            
        timeout = timeout or self.config.websocket_timeout
        
        try:
            message = await asyncio.wait_for(self.client.recv(), timeout=timeout)
            self.touch()
            return json.loads(message)
        except asyncio.TimeoutError:
            raise TimeoutError(f"WebSocket receive timeout after {timeout}s")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON received: {e}")
            
    async def broadcast_to_clients(self, message: Union[str, Dict]) -> None:
        """Broadcast message from server to all connected clients."""
        if isinstance(message, dict):
            message = json.dumps(message)
            
        # Send to all connected clients
        if self.connected_clients:
            await asyncio.gather(
                *[client.send(message) for client in self.connected_clients],
                return_exceptions=True
            )
            
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """Register handler for specific message type."""
        self.message_handlers[message_type] = handler
        
    def get_received_messages(self, message_type: Optional[str] = None) -> List[Dict]:
        """Get received messages, optionally filtered by type."""
        if message_type is None:
            return [msg['data'] for msg in self.received_messages]
        else:
            return [msg['data'] for msg in self.received_messages if msg['data'].get('type') == message_type]
            
    def clear_received_messages(self) -> None:
        """Clear received messages buffer."""
        self.received_messages.clear()


class HTTPTestResource(TestResource):
    """HTTP client test resource for real API testing."""
    
    def __init__(self, resource_id: str, config: ExternalServiceConfig):
        super().__init__(resource_id, ResourceType.HTTP_CLIENT)
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.circuit_breaker = CircuitBreakerState(
            failure_threshold=config.circuit_breaker_failure_threshold,
            timeout=config.circuit_breaker_timeout
        )
        
    async def initialize(self) -> None:
        """Initialize HTTP client."""
        await super().initialize()
        
        if not HTTP_AVAILABLE:
            raise RuntimeError("httpx not available for HTTP testing")
            
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.http_timeout),
            limits=httpx.Limits(
                max_connections=self.config.http_max_connections,
                max_keepalive_connections=self.config.http_max_keepalive
            ),
            follow_redirects=True
        )
        
        self.add_cleanup_callback(self._cleanup_http_client)
        
        logger.debug(f"HTTP test resource {self.resource_id} initialized")
        
    async def _cleanup_http_client(self) -> None:
        """Clean up HTTP client."""
        try:
            if self.client:
                await self.client.aclose()
                self.client = None
        except Exception as e:
            logger.warning(f"Error cleaning up HTTP client for {self.resource_id}: {e}")
            
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with circuit breaker protection."""
        if not self.client:
            raise RuntimeError("HTTP client not initialized")
            
        if not self.circuit_breaker.can_execute():
            raise RuntimeError("HTTP client circuit breaker is OPEN")
            
        self.touch()
        
        try:
            response = await self._make_request_with_retry(method, url, **kwargs)
            self.circuit_breaker.record_success()
            return response
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e
            
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(1 if not self.config.enable_http_retry else self.config.http_retry_count + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                return response
                
            except Exception as e:
                last_exception = e
                
                if attempt < (1 if not self.config.enable_http_retry else self.config.http_retry_count):
                    await asyncio.sleep(self.config.http_retry_delay * (2 ** attempt))
                    logger.debug(f"HTTP request retry {attempt + 1} for {method} {url}")
                else:
                    break
                    
        raise last_exception
        
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)
        
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)
        
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)
        
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)
        
    # Convenience methods for auth service testing
    async def auth_signup(self, email: str, password: str) -> Dict:
        """Sign up new user with auth service."""
        signup_url = urljoin(self.config.auth_service_url, "/auth/signup")
        
        response = await self.post(signup_url, json={
            "email": email,
            "password": password
        })
        
        response.raise_for_status()
        return response.json()
        
    async def auth_login(self, email: str, password: str) -> Dict:
        """Login user with auth service."""
        login_url = urljoin(self.config.auth_service_url, "/auth/login")
        
        response = await self.post(login_url, json={
            "email": email,
            "password": password
        })
        
        response.raise_for_status()
        return response.json()
        
    async def auth_refresh_token(self, refresh_token: str) -> Dict:
        """Refresh access token with auth service."""
        refresh_url = urljoin(self.config.auth_service_url, "/auth/refresh")
        
        response = await self.post(refresh_url, json={
            "refresh_token": refresh_token
        })
        
        response.raise_for_status()
        return response.json()
        
    async def health_check(self) -> bool:
        """Check health of configured services."""
        try:
            health_url = urljoin(self.config.auth_service_url, "/health")
            response = await self.get(health_url)
            return response.status_code == 200
        except Exception:
            return False


class FileSystemTestResource(TestResource):
    """File system test resource with isolation and cleanup."""
    
    def __init__(self, resource_id: str, config: ExternalServiceConfig):
        super().__init__(resource_id, ResourceType.FILE_SYSTEM)
        self.config = config
        self.temp_dir: Optional[Path] = None
        self.created_files: Set[Path] = set()
        self.max_file_size = config.max_file_size_mb * 1024 * 1024  # Convert to bytes
        
    async def initialize(self) -> None:
        """Initialize isolated file system."""
        await super().initialize()
        
        # Create isolated temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(
            prefix=f"{self.config.temp_dir_prefix}{self.resource_id}_"
        ))
        
        self.add_cleanup_callback(self._cleanup_files)
        
        logger.debug(f"File system resource {self.resource_id} initialized at {self.temp_dir}")
        
    async def _cleanup_files(self) -> None:
        """Clean up created files and directories."""
        if not self.config.auto_cleanup_files:
            return
            
        try:
            # Clean up individual files
            for file_path in self.created_files:
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        import shutil
                        shutil.rmtree(file_path)
                        
            # Clean up temp directory
            if self.temp_dir and self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                
            logger.debug(f"Cleaned up {len(self.created_files)} files for {self.resource_id}")
            
        except Exception as e:
            logger.warning(f"Error cleaning up files for {self.resource_id}: {e}")
            
    def get_temp_path(self, filename: str) -> Path:
        """Get path for temporary file in isolated directory."""
        if not self.temp_dir:
            raise RuntimeError("File system resource not initialized")
            
        return self.temp_dir / filename
        
    async def create_file(self, filename: str, content: Union[str, bytes]) -> Path:
        """Create file in isolated directory."""
        file_path = self.get_temp_path(filename)
        
        # Check file size
        content_size = len(content) if isinstance(content, (str, bytes)) else 0
        if content_size > self.max_file_size:
            raise ValueError(f"File size {content_size} exceeds limit {self.max_file_size}")
            
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        if AIOFILES_AVAILABLE:
            import aiofiles
            mode = 'w' if isinstance(content, str) else 'wb'
            async with aiofiles.open(file_path, mode) as f:
                await f.write(content)
        else:
            # Fallback to synchronous write
            mode = 'w' if isinstance(content, str) else 'wb'
            with open(file_path, mode) as f:
                f.write(content)
                
        self.created_files.add(file_path)
        self.touch()
        
        return file_path
        
    async def read_file(self, filename: str) -> Union[str, bytes]:
        """Read file from isolated directory."""
        file_path = self.get_temp_path(filename)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if AIOFILES_AVAILABLE:
            import aiofiles
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
        else:
            # Fallback to synchronous read
            with open(file_path, 'rb') as f:
                content = f.read()
                
        self.touch()
        
        # Try to decode as string, fall back to bytes
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content
            
    def create_directory(self, dirname: str) -> Path:
        """Create directory in isolated space."""
        dir_path = self.get_temp_path(dirname)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        self.created_files.add(dir_path)
        self.touch()
        
        return dir_path
        
    def list_files(self) -> List[Path]:
        """List all files in isolated directory."""
        if not self.temp_dir or not self.temp_dir.exists():
            return []
            
        return list(self.temp_dir.rglob("*"))
        
    def get_size_usage(self) -> Dict[str, int]:
        """Get file system usage statistics."""
        total_size = 0
        file_count = 0
        
        for file_path in self.created_files:
            if file_path.exists() and file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
                
        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'file_count': file_count,
            'max_size_mb': self.config.max_file_size_mb
        }


class LLMTestResource(TestResource):
    """LLM test resource with rate limiting and cost controls."""
    
    def __init__(self, resource_id: str, config: ExternalServiceConfig):
        super().__init__(resource_id, ResourceType.TEMPORARY_DATA)
        self.config = config
        self.request_count = 0
        self.cost_used = 0.0
        self.last_request_time = 0.0
        self.rate_limiter_lock = threading.Lock()
        
    async def initialize(self) -> None:
        """Initialize LLM resource with rate limiting."""
        await super().initialize()
        
        if not self.config.enable_real_llm:
            logger.debug(f"LLM resource {self.resource_id} initialized in mock mode")
            return
            
        # Verify LLM API keys are available
        env = get_env()
        
        available_keys = []
        if env.get("OPENAI_API_KEY"):
            available_keys.append("OpenAI")
        if env.get("ANTHROPIC_API_KEY"):
            available_keys.append("Anthropic")
        if env.get("GEMINI_API_KEY"):
            available_keys.append("Gemini")
            
        if not available_keys:
            raise RuntimeError("No LLM API keys available for real LLM testing")
            
        logger.debug(f"LLM resource {self.resource_id} initialized with {', '.join(available_keys)}")
        
    async def check_rate_limit(self) -> bool:
        """Check if request is within rate limit."""
        with self.rate_limiter_lock:
            current_time = time.time()
            
            # Reset counter every minute
            if current_time - self.last_request_time > 60:
                self.request_count = 0
                
            # Check rate limit
            if self.request_count >= self.config.llm_rate_limit_rpm:
                return False
                
            # Check cost limit
            if self.cost_used >= self.config.llm_cost_limit_usd:
                return False
                
            return True
            
    async def record_request(self, estimated_cost: float = 0.01) -> None:
        """Record LLM request for rate limiting and cost tracking."""
        with self.rate_limiter_lock:
            self.request_count += 1
            self.cost_used += estimated_cost
            self.last_request_time = time.time()
            self.touch()
            
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics."""
        with self.rate_limiter_lock:
            return {
                'request_count': self.request_count,
                'cost_used_usd': self.cost_used,
                'rate_limit_rpm': self.config.llm_rate_limit_rpm,
                'cost_limit_usd': self.config.llm_cost_limit_usd,
                'last_request_time': self.last_request_time
            }
            
    async def simulate_llm_request(
        self,
        prompt: str,
        model: str = "test-model",
        estimated_cost: float = 0.01
    ) -> Dict:
        """Simulate LLM request with rate limiting."""
        if not await self.check_rate_limit():
            raise RuntimeError("LLM rate limit or cost limit exceeded")
            
        await self.record_request(estimated_cost)
        
        # If real LLM is disabled, return mock response
        if not self.config.enable_real_llm:
            return {
                'response': f"Mock response for: {prompt[:50]}...",
                'model': model,
                'cost': estimated_cost,
                'mock': True
            }
            
        # Here you would implement actual LLM API calls
        # For now, return a realistic mock
        await asyncio.sleep(0.5)  # Simulate network delay
        
        return {
            'response': f"Real LLM response for: {prompt[:50]}...",
            'model': model,
            'cost': estimated_cost,
            'mock': False
        }


class ExternalServiceManager:
    """Manager for external service integrations in tests.
    
    This class provides a unified interface for managing external services
    including WebSocket servers, HTTP clients, file system isolation,
    and LLM service integration.
    """
    
    def __init__(self, config: Optional[ExternalServiceConfig] = None):
        self.config = config or ExternalServiceConfig()
        self._active_resources: Dict[str, TestResource] = {}
        self._lock = threading.RLock()
        
    async def create_websocket_resource(self, resource_id: str) -> WebSocketTestResource:
        """Create WebSocket test resource."""
        resource = WebSocketTestResource(resource_id, self.config)
        await resource.initialize()
        
        with self._lock:
            self._active_resources[resource_id] = resource
            
        return resource
        
    async def create_http_resource(self, resource_id: str) -> HTTPTestResource:
        """Create HTTP test resource."""
        resource = HTTPTestResource(resource_id, self.config)
        await resource.initialize()
        
        with self._lock:
            self._active_resources[resource_id] = resource
            
        return resource
        
    async def create_filesystem_resource(self, resource_id: str) -> FileSystemTestResource:
        """Create file system test resource."""
        resource = FileSystemTestResource(resource_id, self.config)
        await resource.initialize()
        
        with self._lock:
            self._active_resources[resource_id] = resource
            
        return resource
        
    async def create_llm_resource(self, resource_id: str) -> LLMTestResource:
        """Create LLM test resource."""
        resource = LLMTestResource(resource_id, self.config)
        await resource.initialize()
        
        with self._lock:
            self._active_resources[resource_id] = resource
            
        return resource
        
    async def cleanup_resource(self, resource_id: str) -> None:
        """Clean up specific resource."""
        with self._lock:
            resource = self._active_resources.pop(resource_id, None)
            
        if resource:
            await resource.cleanup()
            
    async def cleanup_all_resources(self) -> None:
        """Clean up all resources."""
        with self._lock:
            resources_to_cleanup = list(self._active_resources.values())
            self._active_resources.clear()
            
        if resources_to_cleanup:
            cleanup_tasks = [resource.cleanup() for resource in resources_to_cleanup]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        logger.debug(f"Cleaned up {len(resources_to_cleanup)} external service resources")
        
    @contextlib.asynccontextmanager
    async def external_services_environment(
        self,
        test_id: str,
        enable_websocket: bool = True,
        enable_http: bool = True,
        enable_filesystem: bool = True,
        enable_llm: bool = False
    ) -> AsyncIterator[Dict[str, TestResource]]:
        """Create complete external services test environment."""
        resources = {}
        
        try:
            if enable_websocket and WEBSOCKETS_AVAILABLE:
                ws_resource = await self.create_websocket_resource(f"{test_id}_websocket")
                resources['websocket'] = ws_resource
                
            if enable_http and HTTP_AVAILABLE:
                http_resource = await self.create_http_resource(f"{test_id}_http")
                resources['http'] = http_resource
                
            if enable_filesystem:
                fs_resource = await self.create_filesystem_resource(f"{test_id}_filesystem")
                resources['filesystem'] = fs_resource
                
            if enable_llm:
                llm_resource = await self.create_llm_resource(f"{test_id}_llm")
                resources['llm'] = llm_resource
                
            logger.debug(f"Created external services environment {test_id} with {list(resources.keys())}")
            
            yield resources
            
        finally:
            # Clean up resources
            cleanup_tasks = [resource.cleanup() for resource in resources.values()]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Remove from active resources
            with self._lock:
                for resource in resources.values():
                    self._active_resources.pop(resource.resource_id, None)
                    
            logger.debug(f"Cleaned up external services environment {test_id}")


# Global instance for convenient access
_global_external_service_manager: Optional[ExternalServiceManager] = None
_manager_lock = threading.Lock()


def get_external_service_manager(config: Optional[ExternalServiceConfig] = None) -> ExternalServiceManager:
    """Get global external service manager instance."""
    global _global_external_service_manager
    
    if _global_external_service_manager is None:
        with _manager_lock:
            if _global_external_service_manager is None:
                _global_external_service_manager = ExternalServiceManager(config)
                
    return _global_external_service_manager


# ============================================================================
# CONVENIENCE CONTEXT MANAGERS
# ============================================================================

@contextlib.asynccontextmanager
async def isolated_websocket_testing(
    test_id: Optional[str] = None,
    config: Optional[ExternalServiceConfig] = None
) -> AsyncIterator[WebSocketTestResource]:
    """Convenient context manager for WebSocket testing."""
    if test_id is None:
        test_id = str(uuid.uuid4()).replace("-", "_")
        
    manager = ExternalServiceManager(config)
    
    try:
        websocket_resource = await manager.create_websocket_resource(f"{test_id}_websocket")
        yield websocket_resource
    finally:
        await manager.cleanup_all_resources()


@contextlib.asynccontextmanager
async def isolated_http_testing(
    test_id: Optional[str] = None,
    config: Optional[ExternalServiceConfig] = None
) -> AsyncIterator[HTTPTestResource]:
    """Convenient context manager for HTTP testing."""
    if test_id is None:
        test_id = str(uuid.uuid4()).replace("-", "_")
        
    manager = ExternalServiceManager(config)
    
    try:
        http_resource = await manager.create_http_resource(f"{test_id}_http")
        yield http_resource
    finally:
        await manager.cleanup_all_resources()


@contextlib.asynccontextmanager
async def isolated_filesystem_testing(
    test_id: Optional[str] = None,
    config: Optional[ExternalServiceConfig] = None
) -> AsyncIterator[FileSystemTestResource]:
    """Convenient context manager for file system testing."""
    if test_id is None:
        test_id = str(uuid.uuid4()).replace("-", "_")
        
    manager = ExternalServiceManager(config)
    
    try:
        fs_resource = await manager.create_filesystem_resource(f"{test_id}_filesystem")
        yield fs_resource
    finally:
        await manager.cleanup_all_resources()
