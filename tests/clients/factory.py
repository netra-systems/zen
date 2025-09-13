"""Factory for creating typed test clients with real service connections."""



import logging

from pathlib import Path

from typing import Optional



try:

    from dev_launcher.discovery import ServiceDiscovery

    HAS_DEV_LAUNCHER = True

except ImportError:

    # Fallback for environments without dev_launcher

    ServiceDiscovery = None

    HAS_DEV_LAUNCHER = False



from tests.clients.auth_client import AuthTestClient

from tests.clients.backend_client import BackendTestClient

from tests.clients.websocket_client import WebSocketTestClient



logger = logging.getLogger(__name__)





class TestClientFactory:

    """Factory for creating typed test clients connected to real services."""

    

    def __init__(self, discovery: Optional[ServiceDiscovery] = None):

        """Initialize the test client factory.

        

        Args:

            discovery: Service discovery instance. Creates default if not provided.

        """

        if discovery is not None:

            self.discovery = discovery

        elif HAS_DEV_LAUNCHER and ServiceDiscovery is not None:

            self.discovery = ServiceDiscovery()

        else:

            # Fallback for environments without dev_launcher

            self.discovery = None

            

        self._auth_client: Optional[AuthTestClient] = None

        self._backend_client: Optional[BackendTestClient] = None

        

    async def create_auth_client(self) -> AuthTestClient:

        """Create or return cached auth service test client.

        

        Returns:

            AuthTestClient connected to the real auth service

        """

        if not self._auth_client:

            if self.discovery is not None:

                info = await self.discovery.get_service_info("auth")

                base_url = info.base_url

            else:

                # Fallback URL when discovery is unavailable

                base_url = "http://localhost:8081"

                logger.warning("Using fallback auth URL - dev_launcher discovery unavailable")

                

            self._auth_client = AuthTestClient(base_url=base_url)

            logger.info(f"Created auth client for {base_url}")

            

        return self._auth_client

        

    async def create_backend_client(self, token: Optional[str] = None) -> BackendTestClient:

        """Create backend service test client.

        

        Args:

            token: Optional JWT token for authenticated requests

            

        Returns:

            BackendTestClient connected to the real backend service

        """

        if self.discovery is not None:

            info = await self.discovery.get_service_info("backend")

            base_url = info.base_url

        else:

            # Fallback URL when discovery is unavailable

            base_url = "http://localhost:8000"

            logger.warning("Using fallback backend URL - dev_launcher discovery unavailable")

            

        client = BackendTestClient(base_url=base_url, token=token)

        logger.info(f"Created backend client for {base_url}")

        return client

        

    async def create_websocket_client(self, token: str) -> WebSocketTestClient:

        """Create WebSocket test client.

        

        Args:

            token: JWT token for WebSocket authentication

            

        Returns:

            WebSocketTestClient configured for real WebSocket connection

        """

        if self.discovery is not None:

            # Use discovery to get WebSocket URL without token parameter

            info = await self.discovery.get_service_info("backend")

            ws_url = info.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/websocket"

        else:

            # Fallback URL when discovery is unavailable - no token in URL

            ws_url = "ws://localhost:8000/websocket"

            logger.warning("Using fallback WebSocket URL - dev_launcher discovery unavailable")

            

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

        await ws_client.connect(token=token)  # Pass token to connect method

        return ws_client

        

    async def cleanup(self) -> None:

        """Clean up all client connections."""

        if self._auth_client:

            await self._auth_client.close()

            self._auth_client = None

            

        if self._backend_client:

            await self._backend_client.close()

            self._backend_client = None

