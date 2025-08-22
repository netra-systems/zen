"""Mock services for testing.

This module provides mock implementations of external services
to enable isolated testing without dependencies on real services.
"""

from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock


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
        
    def get_service(self, name: str):
        return self._services.get(name)
        
    async def start_all_services(self):
        pass
        
    async def stop_all_services(self):
        pass


__all__ = [
    "MockLLMService",
    "MockOAuthProvider", 
    "MockWebSocketServer",
    "ServiceRegistry",
]