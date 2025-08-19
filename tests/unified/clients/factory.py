"""Factory for creating typed test clients with real service connections."""

import logging
from typing import Optional
from pathlib import Path

from dev_launcher.discovery import ServiceDiscovery
from .auth_client import AuthTestClient
from .backend_client import BackendTestClient
from .websocket_client import WebSocketTestClient

logger = logging.getLogger(__name__)


class TestClientFactory:
    """Factory for creating typed test clients connected to real services."""
    
    def __init__(self, discovery: Optional[ServiceDiscovery] = None):
        """Initialize the test client factory.
        
        Args:
            discovery: Service discovery instance. Creates default if not provided.
        """
        self.discovery = discovery or ServiceDiscovery()
        self._auth_client: Optional[AuthTestClient] = None
        self._backend_client: Optional[BackendTestClient] = None
        
    async def create_auth_client(self) -> AuthTestClient:
        """Create or return cached auth service test client.
        
        Returns:
            AuthTestClient connected to the real auth service
        """
        if not self._auth_client:
            info = await self.discovery.get_service_info("auth")
            self._auth_client = AuthTestClient(base_url=info.base_url)
            logger.info(f"Created auth client for {info.base_url}")
            
        return self._auth_client
        
    async def create_backend_client(self, token: Optional[str] = None) -> BackendTestClient:
        """Create backend service test client.
        
        Args:
            token: Optional JWT token for authenticated requests
            
        Returns:
            BackendTestClient connected to the real backend service
        """
        info = await self.discovery.get_service_info("backend")
        client = BackendTestClient(base_url=info.base_url, token=token)
        logger.info(f"Created backend client for {info.base_url}")
        return client
        
    async def create_websocket_client(self, token: str) -> WebSocketTestClient:
        """Create WebSocket test client.
        
        Args:
            token: JWT token for WebSocket authentication
            
        Returns:
            WebSocketTestClient configured for real WebSocket connection
        """
        ws_url = await self.discovery.get_websocket_url("backend", token=token)
        client = WebSocketTestClient(url=ws_url)
        logger.info(f"Created WebSocket client for {ws_url}")
        return client
        
    async def create_authenticated_backend_client(self, email: str = "test@example.com",
                                                 password: str = "testpass123") -> BackendTestClient:
        """Create an authenticated backend client.
        
        Args:
            email: User email for authentication
            password: User password for authentication
            
        Returns:
            BackendTestClient with valid auth token
        """
        auth_client = await self.create_auth_client()
        token = await auth_client.login(email, password)
        return await self.create_backend_client(token=token)
        
    async def create_authenticated_websocket_client(self, email: str = "test@example.com",
                                                   password: str = "testpass123") -> WebSocketTestClient:
        """Create an authenticated WebSocket client.
        
        Args:
            email: User email for authentication
            password: User password for authentication
            
        Returns:
            Connected WebSocketTestClient with valid auth
        """
        auth_client = await self.create_auth_client()
        token = await auth_client.login(email, password)
        ws_client = await self.create_websocket_client(token)
        await ws_client.connect()
        return ws_client
        
    async def cleanup(self) -> None:
        """Clean up all client connections."""
        if self._auth_client:
            await self._auth_client.close()
            self._auth_client = None
            
        if self._backend_client:
            await self._backend_client.close()
            self._backend_client = None