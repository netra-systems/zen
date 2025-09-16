"""Test client factory and base classes for real service testing."""

from tests.clients.auth_client import AuthTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.factory import ClientFactory
from tests.clients.websocket_client import WebSocketTestClient

# Backward compatibility alias
TestClientFactory = ClientFactory

__all__ = [
    "ClientFactory",
    "TestClientFactory",  # Backward compatibility
    "AuthTestClient", 
    "BackendTestClient",
    "WebSocketTestClient"
]
