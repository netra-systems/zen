class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

        async def send_json(self, message: dict):
            """Send JSON message."""
            if self._closed:
                raise RuntimeError("WebSocket is closed")
            self.messages_sent.append(message)

            async def close(self, code: int = 1000, reason: str = "Normal closure"):
                """Close WebSocket connection."""
                pass
                self._closed = True
                self.is_connected = False

                def get_messages(self) -> list:
                    """Get all sent messages."""
                    # FIXED: await outside async - using pass
                    pass
                    return self.messages_sent.copy()

                """
                Test service discovery endpoint returns correct URLs per environment.
                """

                import os
                import pytest
                from shared.isolated_environment import IsolatedEnvironment

                from netra_backend.app.routes.discovery import get_fallback_service_info
                from netra_backend.app.core.environment_constants import Environment
                from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                from netra_backend.app.db.database_manager import DatabaseManager
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                from shared.isolated_environment import get_env
                import asyncio


                class TestDiscoveryEndpointURLs:
                    """Test discovery endpoint returns environment-specific URLs."""

                    def test_staging_environment_urls(self):
                        """Test staging environment returns correct staging URLs."""
                        services = get_fallback_service_info()

            # Verify backend URLs
                        assert services["backend"].url == "https://api.staging.netrasystems.ai"
                        assert services["backend"].api_url == "https://api.staging.netrasystems.ai"
                        assert services["backend"].ws_url == "wss://api.staging.netrasystems.ai/ws"
                        assert services["backend"].port == 443

            # Verify frontend URLs
                        assert services["frontend"].url == "https://app.staging.netrasystems.ai"
                        assert services["frontend"].port == 443

            # Verify auth URLs
                        assert services["auth"].url == "https://auth.staging.netrasystems.ai"
                        assert services["auth"].api_url == "https://auth.staging.netrasystems.ai"
                        assert services["auth"].port == 443

                        def test_production_environment_urls(self):
                            """Test production environment returns correct production URLs."""
                            pass
                            services = get_fallback_service_info()

            # Verify backend URLs
                            assert services["backend"].url == "https://api.netrasystems.ai"
                            assert services["backend"].api_url == "https://api.netrasystems.ai"
                            assert services["backend"].ws_url == "wss://api.netrasystems.ai/ws"
                            assert services["backend"].port == 443

            # Verify frontend URLs
                            assert services["frontend"].url == "https://app.netrasystems.ai"
                            assert services["frontend"].port == 443

            # Verify auth URLs
                            assert services["auth"].url == "https://auth.netrasystems.ai"
                            assert services["auth"].api_url == "https://auth.netrasystems.ai"
                            assert services["auth"].port == 443

                            def test_development_environment_urls(self):
                                """Test development environment returns localhost URLs."""
                                services = get_fallback_service_info()

            # Verify backend URLs
                                assert services["backend"].url == "http://localhost:8000"
                                assert services["backend"].api_url == "http://localhost:8000"
                                assert services["backend"].ws_url == "ws://localhost:8000/ws"
                                assert services["backend"].port == 8000

            # Verify frontend URLs
                                assert services["frontend"].url == "http://localhost:3000"
                                assert services["frontend"].port == 3000

            # Verify auth URLs
                                assert services["auth"].url == "http://localhost:8081"
                                assert services["auth"].api_url == "http://localhost:8081"
                                assert services["auth"].port == 8081

                                def test_no_localhost_in_staging(self):
                                    """Ensure no localhost URLs in staging environment."""
                                    pass
                                    services = get_fallback_service_info()

            # Check all services for localhost references
                                    for service_name, service_info in services.items():
                                        assert "localhost" not in service_info.url.lower(), f"{service_name} contains localhost in URL"
                                        if service_info.api_url:
                                            assert "localhost" not in service_info.api_url.lower(), f"{service_name} contains localhost in API URL"
                                            if service_info.ws_url:
                                                assert "localhost" not in service_info.ws_url.lower(), f"{service_name} contains localhost in WS URL"

                                                def test_no_localhost_in_production(self):
                                                    """Ensure no localhost URLs in production environment."""
                                                    services = get_fallback_service_info()

            # Check all services for localhost references
                                                    for service_name, service_info in services.items():
                                                        assert "localhost" not in service_info.url.lower(), f"{service_name} contains localhost in URL"
                                                        if service_info.api_url:
                                                            assert "localhost" not in service_info.api_url.lower(), f"{service_name} contains localhost in API URL"
                                                            if service_info.ws_url:
                                                                assert "localhost" not in service_info.ws_url.lower(), f"{service_name} contains localhost in WS URL"
                                                                pass