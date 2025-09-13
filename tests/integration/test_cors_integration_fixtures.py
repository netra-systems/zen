from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""Fixtures Tests - Split from test_cors_integration.py"""



import os





class TestSyntaxFix:

    """Test class for orphaned methods"""



    def mock_backend_server_url(self):

        """Get backend server URL for testing."""

        return get_env().get("BACKEND_URL", "http://localhost:8000")



    def mock_auth_server_url(self):

        """Get auth server URL for testing."""

        return get_env().get("AUTH_URL", "http://localhost:8081")



    def frontend_origin(self):

        """Frontend origin that makes cross-origin requests."""

        return "http://localhost:3001"



    def websocket_url(self):

        """Get WebSocket URL for testing."""

        return get_env().get("WS_URL", "ws://localhost:8000/ws")



    def backend_url(self):

        return get_env().get("BACKEND_URL", "http://localhost:8000")



    def auth_url(self):

        return get_env().get("AUTH_URL", "http://localhost:8081")

