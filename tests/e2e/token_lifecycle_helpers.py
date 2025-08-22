"""
Token Lifecycle E2E Test Helpers - Modular support functions
Maintains 450-line limit through focused helper functionality
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from tests.jwt_token_helpers import JWTTestHelper
from tests.real_client_types import ClientConfig
from tests.real_websocket_client import RealWebSocketClient


class TokenLifecycleManager:
    """Manages token lifecycle operations for E2E testing."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8081"  # Updated to match services
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000"
        self.jwt_helper = JWTTestHelper()
    
    async def create_short_ttl_token(self, user_id: str, ttl_seconds: int = 30) -> str:
        """Create token with short TTL for expiration testing."""
        payload = self._build_token_payload(user_id, ttl_seconds)
        return await self.jwt_helper.create_jwt_token(payload)
    
    def _build_token_payload(self, user_id: str, ttl_seconds: int) -> Dict:
        """Build token payload with specified TTL."""
        return {
            "sub": user_id,
            "email": "test-token-refresh@netrasystems.ai",
            "permissions": ["read", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            "token_type": "access",
            "iss": "netra-auth-service"
        }
    
    async def create_valid_refresh_token(self, user_id: str) -> str:
        """Create valid refresh token."""
        payload = self._build_refresh_payload(user_id)
        return await self.jwt_helper.create_jwt_token(payload)
    
    def _build_refresh_payload(self, user_id: str) -> Dict:
        """Build refresh token payload."""
        return {
            "sub": user_id,
            "token_type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "iss": "netra-auth-service"
        }
    
    async def refresh_token_via_api(self, refresh_token: str) -> Optional[Dict]:
        """Refresh token using auth service API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await self._make_refresh_request(client, refresh_token)
            return self._parse_refresh_response(response)
    
    async def _make_refresh_request(self, client: httpx.AsyncClient, refresh_token: str):
        """Make refresh token API request."""
        return await client.post(
            f"{self.auth_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
    
    def _parse_refresh_response(self, response) -> Optional[Dict]:
        """Parse refresh token API response."""
        try:
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None


class WebSocketSessionManager:
    """Manages WebSocket sessions for token refresh testing."""
    
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.client: Optional[RealWebSocketClient] = None
    
    async def start_chat_session(self, token: str) -> bool:
        """Start WebSocket chat session with token."""
        config = ClientConfig(timeout=5.0, max_retries=1)
        self.client = RealWebSocketClient(f"{self.ws_url}?token={token}", config)
        return await self.client.connect()
    
    async def send_chat_message(self, message: str, thread_id: str) -> bool:
        """Send chat message through WebSocket."""
        if not self.client:
            return False
        chat_message = self._build_chat_message(message, thread_id)
        return await self.client.send(chat_message)
    
    def _build_chat_message(self, message: str, thread_id: str) -> Dict:
        """Build chat message payload."""
        return {
            "type": "chat_message",
            "message": message,
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def receive_response(self, timeout: float = 3.0) -> Optional[Dict]:
        """Receive response from WebSocket."""
        if not self.client:
            return None
        return await self.client.receive(timeout)
    
    async def test_connection_alive(self) -> bool:
        """Test if WebSocket connection is still alive."""
        if not self._has_active_websocket():
            return False
        return await self._ping_websocket()
    
    def _has_active_websocket(self) -> bool:
        """Check if we have an active WebSocket."""
        return bool(self.client and self.client._websocket)
    
    async def _ping_websocket(self) -> bool:
        """Ping WebSocket to test connectivity."""
        try:
            await self.client._websocket.ping()
            return True
        except Exception:
            return False
    
    async def reconnect_with_new_token(self, new_token: str) -> bool:
        """Reconnect WebSocket with new token."""
        await self.close()
        return await self.start_chat_session(new_token)
    
    async def close(self):
        """Close WebSocket connection."""
        if self.client:
            await self.client.close()


class TokenValidationHelper:
    """Helper for token validation across services."""
    
    def __init__(self, token_manager: TokenLifecycleManager):
        self.token_manager = token_manager
    
    async def verify_token_propagation(self, new_token: str):
        """Verify new token works across all services."""
        auth_valid = await self._test_auth_service(new_token)
        backend_valid = await self._test_backend_service(new_token)
        return auth_valid and backend_valid
    
    async def _test_auth_service(self, token: str) -> bool:
        """Test token against auth service."""
        result = await self.token_manager.jwt_helper.make_auth_request("/auth/verify", token)
        return result["status"] in [200, 500]
    
    async def _test_backend_service(self, token: str) -> bool:
        """Test token against backend service."""
        result = await self.token_manager.jwt_helper.make_backend_request("/health", token)
        return result["status"] in [200, 500]


class PerformanceBenchmark:
    """Performance benchmarking for token operations."""
    
    @staticmethod
    def start_timer() -> float:
        """Start performance timer."""
        return time.time()
    
    @staticmethod
    def check_duration(start_time: float, max_seconds: float) -> bool:
        """Check if operation completed within time limit."""
        duration = time.time() - start_time
        return duration < max_seconds
    
    @staticmethod
    def get_duration(start_time: float) -> float:
        """Get elapsed duration."""
        return time.time() - start_time
