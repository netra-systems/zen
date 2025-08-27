"""Mock services for testing.

This module provides mock implementations of external services
to enable isolated testing without dependencies on real services.
"""

from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


class MockLLMService:
    """Mock LLM service for testing."""
    def __init__(self, model_name: str):
        self.model_name = model_name
        
    async def start(self):
        pass
        
    async def stop(self):
        pass
        
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Mock chat completion."""
        return {
            "id": "mock_completion_123",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"Mock response from {self.model_name}"
                }
            }],
            "usage": {"total_tokens": 100}
        }

class MockOAuthProvider:
    """Mock OAuth provider for testing."""
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        
    def generate_auth_code(self, user_id: str, email: str) -> str:
        return f"auth_code_{user_id}"
        
    def exchange_code_for_token(self, auth_code: str) -> Dict[str, str]:
        return {"access_token": f"token_{auth_code}", "refresh_token": f"refresh_{auth_code}"}
        
    async def start(self):
        pass
        
    async def stop(self):
        pass

class MockWebSocketServer:
    """Mock WebSocket server for testing."""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        
    async def start(self):
        pass
        
    async def stop(self):
        pass

class MockHTTPService:
    """Mock HTTP service for testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.is_running = False
        self.request_history: List[Dict[str, Any]] = []
        self.response_map: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Start the mock HTTP service."""
        self.is_running = True
        
    async def stop(self):
        """Stop the mock HTTP service."""
        self.is_running = False
        
    def set_response(self, path: str, method: str = "GET", 
                    status_code: int = 200, response_data: Dict[str, Any] = None):
        """Set a mock response for a specific endpoint."""
        key = f"{method.upper()}:{path}"
        self.response_map[key] = {
            "status_code": status_code,
            "data": response_data or {"status": "success"}
        }
    
    async def request(self, method: str, path: str, 
                     headers: Dict[str, str] = None, 
                     json_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock HTTP request."""
        if not self.is_running:
            raise ConnectionError("Service is not running")
        
        # Record request
        self.request_history.append({
            "method": method.upper(),
            "path": path,
            "headers": headers or {},
            "json_data": json_data,
            "timestamp": time.time() if 'time' in globals() else 0
        })
        
        # Check for predefined response
        key = f"{method.upper()}:{path}"
        if key in self.response_map:
            response = self.response_map[key]
            if response["status_code"] >= 400:
                raise Exception(f"HTTP {response['status_code']}: {response.get('data', {})}")
            return response["data"]
        
        # Default successful response
        return {
            "status": "success",
            "method": method,
            "path": path,
            "mock": True
        }
    
    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Mock GET request."""
        return await self.request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """Mock POST request."""
        return await self.request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """Mock PUT request."""
        return await self.request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Mock DELETE request."""
        return await self.request("DELETE", path, **kwargs)
    
    def get_request_count(self) -> int:
        """Get total number of requests made."""
        return len(self.request_history)
    
    def get_requests_for_path(self, path: str) -> List[Dict[str, Any]]:
        """Get all requests for a specific path."""
        return [req for req in self.request_history if req["path"] == path]


class ServiceRegistry:
    """Mock service registry for testing."""
    def __init__(self):
        self._services = {}
        
    def register_oauth_provider(self, name: str, provider):
        self._services[f"oauth_{name}"] = provider
        
    def register_llm_service(self, name: str, service):
        self._services[f"llm_{name}"] = service
        
    def register_websocket_server(self, name: str, server):
        self._services[f"ws_{name}"] = server
        
    def register_http_service(self, name: str, service):
        self._services[f"http_{name}"] = service
        
    def get_service(self, name: str):
        return self._services.get(name)
        
    async def start_all_services(self):
        for service in self._services.values():
            if hasattr(service, 'start'):
                await service.start()
        
    async def stop_all_services(self):
        for service in self._services.values():
            if hasattr(service, 'stop'):
                await service.stop()

def setup_unified_mock_services() -> ServiceRegistry:
    """Set up a complete mock service registry for testing."""
    registry = ServiceRegistry()
    
    # Register mock LLM services
    registry.register_llm_service(LLMModel.GEMINI_2_5_FLASH.value, MockLLMService(LLMModel.GEMINI_2_5_FLASH.value))
    registry.register_llm_service("claude-3", MockLLMService("claude-3"))
    
    # Register mock OAuth providers
    registry.register_oauth_provider("google", MockOAuthProvider("google"))
    registry.register_oauth_provider("github", MockOAuthProvider("github"))
    
    # Register mock WebSocket server
    registry.register_websocket_server("main", MockWebSocketServer("localhost", 8080))
    
    # Register mock HTTP services
    registry.register_http_service("auth", MockHTTPService("http://localhost:3001"))
    registry.register_http_service("backend", MockHTTPService("http://localhost:8000"))
    registry.register_http_service("frontend", MockHTTPService("http://localhost:3000"))
    
    return registry

__all__ = [
    "MockLLMService",
    "MockOAuthProvider", 
    "MockWebSocketServer",
    "MockHTTPService",
    "ServiceRegistry",
    "setup_unified_mock_services",
]