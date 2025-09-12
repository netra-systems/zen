"""WebSocket Service Discovery Tests.

Tests service discovery requirements per SPEC/websockets.xml:
- Backend provides WebSocket config discovery to frontend
- Frontend discovers WebSocket config at earliest application state
- Service discovery integration with existing config system

Business Value: Ensures seamless WebSocket connectivity across environments
without hardcoded URLs, enabling smooth deployments and scalability.

BVJ: Enterprise/Platform - Configuration Management - Service discovery
prevents connection failures during deployment changes and multi-environment support.
"""

import asyncio
import json
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.config import UnifiedTestConfig


@pytest.mark.e2e
class TestWebSocketServiceDiscovery:
    """Test suite for WebSocket service discovery mechanisms."""
    
    @pytest.fixture
    async def backend_client(self):
        """Get authenticated backend client."""
        client = BackendTestClient()
        await client.authenticate()
        try:
            yield client
        finally:
            await client.close()
    
    @pytest.fixture
    async def websocket_client(self, backend_client):
        """Get authenticated WebSocket client."""
        token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        await ws_client.connect(token)
        try:
            yield ws_client
        finally:
            await ws_client.disconnect()
    
    @pytest.mark.e2e
    async def test_websocket_config_endpoint_exists(self, backend_client):
        """Test backend provides WebSocket configuration endpoint."""
        # Test service discovery endpoint for WebSocket config
        response = await backend_client.get("/api/config/websocket")
        
        assert response.status_code == 200, (
            f"WebSocket config endpoint failed: {response.status_code}. "
            f"Service discovery requires /api/config/websocket endpoint."
        )
        
        config_data = response.json()
        assert isinstance(config_data, dict), "WebSocket config must be JSON object"
        
        # Required configuration fields per SPEC/websockets.xml
        required_fields = ["websocket_url", "connection_timeout", "heartbeat_interval"]
        for field in required_fields:
            assert field in config_data, f"WebSocket config missing required field: {field}"
        
        # Validate WebSocket URL format
        websocket_url = config_data["websocket_url"]
        assert isinstance(websocket_url, str), "websocket_url must be string"
        assert websocket_url.startswith(("ws://", "wss://")), "websocket_url must use ws:// or wss:// protocol"
        assert "/ws" in websocket_url, "websocket_url must include /ws path"
        
        # Validate numeric configuration values
        assert isinstance(config_data["connection_timeout"], (int, float)), "connection_timeout must be number"
        assert config_data["connection_timeout"] > 0, "connection_timeout must be positive"
        
        assert isinstance(config_data["heartbeat_interval"], (int, float)), "heartbeat_interval must be number"
        assert config_data["heartbeat_interval"] > 0, "heartbeat_interval must be positive"
    
    @pytest.mark.e2e
    async def test_websocket_config_environment_specific(self, backend_client):
        """Test WebSocket config is environment-specific."""
        response = await backend_client.get("/api/config/websocket")
        config_data = response.json()
        
        websocket_url = config_data["websocket_url"]
        
        # Check environment-appropriate configuration
        config = UnifiedTestConfig()
        base_url = config.backend_base_url
        
        if "localhost" in base_url or "127.0.0.1" in base_url:
            # Local development environment
            assert "localhost" in websocket_url or "127.0.0.1" in websocket_url, (
                "Local environment should use localhost WebSocket URL"
            )
        elif "staging" in base_url:
            # Staging environment
            assert "staging" in websocket_url, (
                "Staging environment should use staging WebSocket URL"
            )
        elif any(prod_indicator in base_url for prod_indicator in ["production", "api", ".com"]):
            # Production environment
            assert websocket_url.startswith("wss://"), (
                "Production environment must use secure WebSocket (wss://)"
            )
    
    @pytest.mark.e2e
    async def test_websocket_config_authentication_integration(self, backend_client):
        """Test WebSocket config includes authentication parameters."""
        response = await backend_client.get("/api/config/websocket")
        config_data = response.json()
        
        # Should include authentication method information
        auth_fields = ["auth_method", "token_param", "auth_header"]
        auth_field_count = sum(1 for field in auth_fields if field in config_data)
        
        assert auth_field_count >= 1, (
            f"WebSocket config should include authentication information. "
            f"Expected at least one of: {auth_fields}"
        )
        
        # If auth_method is specified, validate it
        if "auth_method" in config_data:
            auth_method = config_data["auth_method"]
            assert auth_method in ["jwt", "bearer", "query"], (
                f"Unknown auth_method: {auth_method}. Expected: jwt, bearer, or query"
            )
        
        # If token_param is specified for query auth
        if "token_param" in config_data:
            assert isinstance(config_data["token_param"], str), "token_param must be string"
            assert config_data["token_param"], "token_param cannot be empty"
        
        # If auth_header is specified for header auth
        if "auth_header" in config_data:
            assert isinstance(config_data["auth_header"], str), "auth_header must be string"
            assert config_data["auth_header"], "auth_header cannot be empty"
    
    @pytest.mark.e2e
    async def test_websocket_config_connection_parameters(self, backend_client):
        """Test WebSocket config includes connection optimization parameters."""
        response = await backend_client.get("/api/config/websocket")
        config_data = response.json()
        
        # Connection optimization parameters
        optimization_params = {
            "max_reconnect_attempts": (int, lambda x: x >= 0),
            "reconnect_delay_ms": (int, lambda x: x > 0),
            "ping_interval": (int, lambda x: x > 0),
            "pong_timeout": (int, lambda x: x > 0),
            "close_timeout": (int, lambda x: x > 0)
        }
        
        for param, (expected_type, validator) in optimization_params.items():
            if param in config_data:
                value = config_data[param]
                assert isinstance(value, expected_type), f"{param} must be {expected_type.__name__}"
                assert validator(value), f"{param} validation failed: {value}"
    
    @pytest.mark.e2e
    async def test_websocket_discovery_at_application_startup(self, backend_client):
        """Test WebSocket config is discoverable during application initialization."""
        # Simulate application startup config discovery
        startup_config_response = await backend_client.get("/api/config/startup")
        
        if startup_config_response.status_code == 200:
            startup_config = startup_config_response.json()
            
            # Startup config should reference WebSocket config availability
            assert any(
                "websocket" in str(value).lower() 
                for value in startup_config.values() 
                if isinstance(value, (str, dict))
            ), "Startup config should reference WebSocket configuration availability"
        
        # Verify WebSocket config is accessible without authentication for discovery
        unauth_client = BackendTestClient()
        try:
            # Some configs might be available without auth for service discovery
            unauth_response = await unauth_client.get("/api/config/websocket/public")
            
            if unauth_response.status_code == 200:
                public_config = unauth_response.json()
                assert "websocket_url" in public_config, (
                    "Public WebSocket config should include websocket_url for discovery"
                )
        finally:
            await unauth_client.close()
    
    @pytest.mark.e2e
    async def test_websocket_config_caching_headers(self, backend_client):
        """Test WebSocket config includes appropriate caching headers."""
        response = await backend_client.get("/api/config/websocket")
        
        # Check caching headers for config optimization
        headers = dict(response.headers)
        
        # Should have cache control for config stability
        cache_headers = ["cache-control", "etag", "last-modified"]
        has_cache_header = any(header.lower() in [h.lower() for h in headers.keys()] for header in cache_headers)
        
        if has_cache_header:
            # If caching is used, validate it's appropriate for config
            if "cache-control" in [h.lower() for h in headers.keys()]:
                cache_control = next(v for k, v in headers.items() if k.lower() == "cache-control")
                
                # Config should be cacheable but not for too long
                assert "no-cache" not in cache_control.lower() or "max-age" in cache_control.lower(), (
                    "WebSocket config caching should allow reasonable cache duration"
                )
    
    @pytest.mark.e2e
    async def test_websocket_config_version_compatibility(self, backend_client):
        """Test WebSocket config includes version compatibility information."""
        response = await backend_client.get("/api/config/websocket")
        config_data = response.json()
        
        # Version information for compatibility checking
        version_fields = ["protocol_version", "api_version", "min_client_version"]
        version_info_count = sum(1 for field in version_fields if field in config_data)
        
        if version_info_count > 0:
            # Validate version format if present
            if "protocol_version" in config_data:
                protocol_version = config_data["protocol_version"]
                assert isinstance(protocol_version, str), "protocol_version must be string"
                # Should follow semantic versioning or simple version format
                assert any(char.isdigit() for char in protocol_version), "protocol_version should contain version numbers"
            
            if "api_version" in config_data:
                api_version = config_data["api_version"]
                assert isinstance(api_version, str), "api_version must be string"
                assert any(char.isdigit() for char in api_version), "api_version should contain version numbers"
    
    @pytest.mark.e2e
    async def test_websocket_config_load_balancing_support(self, backend_client):
        """Test WebSocket config supports load balancing scenarios."""
        response = await backend_client.get("/api/config/websocket")
        config_data = response.json()
        
        # Load balancing considerations
        websocket_url = config_data["websocket_url"]
        
        # Should not hardcode specific server instances
        problematic_patterns = ["server1", "instance-", "pod-", ":8080", ":3000"]
        for pattern in problematic_patterns:
            if pattern in websocket_url.lower():
                # This might indicate hardcoded instance-specific URLs
                assert False, (
                    f"WebSocket URL may contain instance-specific pattern '{pattern}': {websocket_url}. "
                    f"This could prevent proper load balancing."
                )
        
        # Should use service names or load balancer endpoints
        if not any(local in websocket_url for local in ["localhost", "127.0.0.1"]):
            # In non-local environments, should use proper service names
            url_parts = websocket_url.split("://")[1].split("/")[0]
            assert not url_parts.endswith(":8080") and not url_parts.endswith(":3000"), (
                f"Non-local WebSocket URL should not use development ports: {websocket_url}"
            )
    
    @pytest.mark.e2e
    async def test_websocket_config_security_headers(self, backend_client):
        """Test WebSocket config endpoint returns appropriate security headers."""
        response = await backend_client.get("/api/config/websocket")
        headers = dict(response.headers)
        
        # Security headers for config endpoint
        security_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": ["DENY", "SAMEORIGIN"],
            "content-type": "application/json"
        }
        
        for header, expected_values in security_headers.items():
            header_key = next((k for k in headers.keys() if k.lower() == header.lower()), None)
            if header_key:
                header_value = headers[header_key]
                
                if isinstance(expected_values, list):
                    assert any(expected in header_value.upper() for expected in expected_values), (
                        f"Security header {header} has unexpected value: {header_value}"
                    )
                else:
                    assert expected_values in header_value.lower(), (
                        f"Security header {header} missing expected value: {expected_values}"
                    )
    
    @pytest.mark.e2e
    async def test_websocket_config_error_handling(self, backend_client):
        """Test WebSocket config endpoint handles errors gracefully."""
        # Test malformed requests
        try:
            response = await backend_client.get("/api/config/websocket?invalid=param")
            # Should either succeed or return proper error
            assert response.status_code in [200, 400], (
                f"Unexpected status code for malformed request: {response.status_code}"
            )
            
            if response.status_code == 400:
                error_data = response.json()
                assert "error" in error_data or "message" in error_data, (
                    "Error response should include error message"
                )
        except Exception as e:
            # Should not crash on malformed requests
            pytest.fail(f"WebSocket config endpoint crashed on malformed request: {e}")
    
    # Helper methods (each  <= 8 lines)
    def _validate_url_format(self, url: str) -> bool:
        """Validate WebSocket URL format."""
        if not isinstance(url, str):
            return False
        return url.startswith(("ws://", "wss://")) and len(url) > 10
    
    def _extract_domain_from_websocket_url(self, websocket_url: str) -> str:
        """Extract domain from WebSocket URL."""
        return websocket_url.split("://")[1].split("/")[0].split(":")[0]