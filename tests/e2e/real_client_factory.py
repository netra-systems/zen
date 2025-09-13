"""Real HTTP and WebSocket Client Factory for E2E Testing

Professional real network clients for comprehensive E2E testing.
NO MOCKING - actual network calls for true integration validation.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise 
- Business Goal: Ensure production-like reliability testing
- Value Impact: Prevents production bugs through real network testing
- Revenue Impact: Protects customer experience and conversion rates

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)  
- Real HTTP/WebSocket connections only
- Connection pooling for performance
- Comprehensive error handling and retry logic
"""

from typing import Any, Dict, Optional

from test_framework.http_client import (
    ClientConfig,
    create_auth_config,
    create_backend_config,
    create_test_config,
)
from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


class RealClientFactory:
    """Factory for creating real HTTP and WebSocket clients"""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        """Initialize factory with configuration"""
        self.config = config or ClientConfig()
        self._http_clients: Dict[str, RealHTTPClient] = {}
        self._ws_clients: Dict[str, RealWebSocketClient] = {}
    
    def create_http_client(self, base_url: str) -> RealHTTPClient:
        """Create or reuse HTTP client"""
        if base_url not in self._http_clients:
            self._http_clients[base_url] = RealHTTPClient(base_url, self.config)
        return self._http_clients[base_url]
    
    def create_websocket_client(self, ws_url: str) -> RealWebSocketClient:
        """Create or reuse WebSocket client"""
        if ws_url not in self._ws_clients:
            self._ws_clients[ws_url] = RealWebSocketClient(ws_url, self.config)
        return self._ws_clients[ws_url]
    
    def create_auth_http_client(self, base_url: str) -> RealHTTPClient:
        """Create HTTP client with auth-specific configuration"""
        auth_config = create_auth_config()
        return RealHTTPClient(base_url, auth_config)
    
    def create_backend_http_client(self, base_url: str) -> RealHTTPClient:
        """Create HTTP client with backend-specific configuration"""
        backend_config = create_backend_config()
        return RealHTTPClient(base_url, backend_config)
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get aggregated connection metrics"""
        http_metrics = self._get_http_metrics()
        ws_metrics = self._get_ws_metrics()
        return {"http": http_metrics, "websocket": ws_metrics}
    
    def _get_http_metrics(self) -> Dict[str, Any]:
        """Get HTTP client metrics"""
        total_requests = sum(c.metrics.requests_sent for c in self._http_clients.values())
        total_responses = sum(c.metrics.responses_received for c in self._http_clients.values())
        return {"requests": total_requests, "responses": total_responses}
    
    def _get_ws_metrics(self) -> Dict[str, Any]:
        """Get WebSocket client metrics"""
        total_sent = sum(c.metrics.requests_sent for c in self._ws_clients.values())
        total_received = sum(c.metrics.responses_received for c in self._ws_clients.values())
        return {"messages_sent": total_sent, "messages_received": total_received}
    
    async def cleanup(self) -> None:
        """Clean up all client connections"""
        await self._cleanup_http_clients()
        await self._cleanup_ws_clients()
    
    async def _cleanup_http_clients(self) -> None:
        """Close all HTTP clients"""
        for client in self._http_clients.values():
            await client.close()
        self._http_clients.clear()
    
    async def _cleanup_ws_clients(self) -> None:
        """Close all WebSocket clients"""
        for client in self._ws_clients.values():
            await client.close()
        self._ws_clients.clear()


def create_real_client_factory(config: Optional[ClientConfig] = None) -> RealClientFactory:
    """Create real client factory with optional configuration"""
    return RealClientFactory(config)


# Re-export commonly used functions
__all__ = [
    'RealClientFactory',
    'create_real_client_factory', 
    'create_test_config',
    'ClientConfig',
    'RealHTTPClient',
    'RealWebSocketClient'
]
