"""
Mock Service Infrastructure for Unified System Testing.

Business Value: Enables controlled testing of external dependencies.
Supports mocking OAuth providers, LLM services, and other external APIs.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from unittest.mock import AsyncMock, MagicMock
import websockets
import logging
from aiohttp import web, WSMsgType
from aiohttp.test_utils import TestServer
import time

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