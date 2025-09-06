"""
Unit tests for CORS Configuration Builder.
Tests the new class-based CORS configuration system.
"""

import pytest
from shared.cors_config_builder import (
    CORSConfigurationBuilder,
    CORSEnvironment,
    CORSSecurityEvent
)
from shared.isolated_environment import IsolatedEnvironment


class TestCORSConfigurationBuilder:
    """Test the main CORS Configuration Builder class."""

    def test_initialization_default(self):
        """Test initialization with default environment."""
        cors = CORSConfigurationBuilder()
        assert cors.environment == "development"
        assert cors.origins is not None
        assert cors.headers is not None
        assert cors.security is not None

    def test_initialization_with_env_vars(self):
        """Test initialization with custom environment variables."""
        env_vars = {"ENVIRONMENT": "production"}
        cors = CORSConfigurationBuilder(env_vars)
        assert cors.environment == "production"

    def test_environment_detection(self):
        """Test environment detection from various env vars."""
        # List of all environment variable names that could interfere with detection
        env_var_names = [
            "ENVIRONMENT", "ENV", "NETRA_ENVIRONMENT", "NETRA_ENV",
            "NODE_ENV", "AUTH_ENV", "K_SERVICE", "GCP_PROJECT_ID"
        ]

        test_cases = [
            ({"ENVIRONMENT": "production"}, "production"),
            ({"ENV": "staging"}, "staging"),
            ({"NODE_ENV": "development"}, "development"),
            ({"NETRA_ENV": "prod"}, "production"),
            ({"AUTH_ENV": "stg"}, "staging"),
            ({}, "development")  # Default
        ]

        for env_vars, expected in test_cases:
            # Create isolated environment by clearing all environment detection variables
            # then setting only the specific one we want to test
            isolated_env_vars = {var_name: None for var_name in env_var_names}
            isolated_env_vars.update(env_vars)

            cors = CORSConfigurationBuilder(isolated_env_vars)
            assert cors.environment == expected, f"Expected {expected}, got {cors.environment} for {env_vars}"

    def test_sub_builders_exist(self):
        """Test that all sub-builders are initialized."""
        cors = CORSConfigurationBuilder()
        assert hasattr(cors, 'origins')
        assert hasattr(cors, 'headers')
        assert hasattr(cors, 'security')
        assert hasattr(cors, 'service_detector')
        assert hasattr(cors, 'fastapi')
        assert hasattr(cors, 'health')
        assert hasattr(cors, 'websocket')
        assert hasattr(cors, 'static')


class TestOriginsBuilder:
    """Test the Origins sub-builder."""

    def test_development_origins(self):
        """Test development environment origins."""
        env_vars = {"ENVIRONMENT": "development"}
        cors = CORSConfigurationBuilder(env_vars)
        origins = cors.origins.allowed

        assert "http://localhost:3000" in origins
        assert "http://127.0.0.1:8000" in origins
        assert "http://[::1]:3000" in origins  # IPv6
        assert len(origins) > 20  # Should have many localhost variants

    def test_staging_origins(self):
        """Test staging environment origins."""
        env_vars = {"ENVIRONMENT": "staging"}
        cors = CORSConfigurationBuilder(env_vars)
        origins = cors.origins.allowed

        assert "https://app.staging.netrasystems.ai" in origins
        assert "https://netra-frontend-701982941522.us-central1.run.app" in origins
        assert "http://localhost:3000" in origins  # Local testing support

    def test_production_origins(self):
        """Test production environment origins."""
        env_vars = {"ENVIRONMENT": "production"}
        cors = CORSConfigurationBuilder(env_vars)
        origins = cors.origins.allowed

        assert "https://netrasystems.ai" in origins
        assert "https://app.netrasystems.ai" in origins
        assert "http://localhost:3000" not in origins  # No localhost in production

    def test_custom_cors_origins(self):
        """Test custom CORS_ORIGINS environment variable."""
        env_vars = {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://custom1.com,https://custom2.com"
        }
        cors = CORSConfigurationBuilder(env_vars)
        origins = cors.origins.allowed

        assert origins == ["https://custom1.com", "https://custom2.com"]

    def test_is_allowed_direct_match(self):
        """Test is_allowed with direct origin match."""
        env_vars = {"ENVIRONMENT": "production"}
        cors = CORSConfigurationBuilder(env_vars)

        assert cors.origins.is_allowed("https://netrasystems.ai") is True
        assert cors.origins.is_allowed("https://evil.com") is False

    def test_is_allowed_localhost_in_dev(self):
        """Test localhost is allowed in development."""
        env_vars = {"ENVIRONMENT": "development"}
        cors = CORSConfigurationBuilder(env_vars)

        assert cors.origins.is_allowed("http://localhost:9999") is True
        assert cors.origins.is_allowed("http://127.0.0.1:5555") is True
        assert cors.origins.is_allowed("http://172.17.0.1:3000") is True  # Docker

    def test_is_allowed_service_to_service(self):
        """Test service-to-service bypass."""
        cors = CORSConfigurationBuilder()

        assert cors.origins.is_allowed("https://evil.com", service_to_service=True) is True

    def test_validate_origin_format(self):
        """Test origin format validation."""
        cors = CORSConfigurationBuilder()

        # Valid origins
        valid, error = cors.origins.validate_origin_format("https://example.com")
        assert valid is True
        assert error is None

        # Invalid origins
        invalid_cases = [
            ("", "Origin cannot be empty"),
            ("example.com", "Origin must include scheme"),
            ("ftp://example.com", "Invalid scheme"),
            ("https://", "Origin must include hostname"),
            ("https://example.com/path", "Origin should not include path")
        ]

        for origin, expected_error in invalid_cases:
            valid, error = cors.origins.validate_origin_format(origin)
            assert valid is False
            assert expected_error in error


class TestHeadersBuilder:
    """Test the Headers sub-builder."""

    def test_allowed_headers(self):
        """Test allowed headers list."""
        cors = CORSConfigurationBuilder()
        headers = cors.headers.allowed_headers

        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert "X-Service-Name" in headers

    def test_exposed_headers(self):
        """Test exposed headers list."""
        cors = CORSConfigurationBuilder()
        headers = cors.headers.exposed_headers

        assert "X-Trace-ID" in headers
        assert "X-Request-ID" in headers
        assert "Vary" in headers

    def test_allowed_methods(self):
        """Test allowed methods list."""
        cors = CORSConfigurationBuilder()
        methods = cors.headers.allowed_methods

        assert "GET" in methods
        assert "POST" in methods
        assert "OPTIONS" in methods

    def test_is_header_allowed(self):
        """Test header validation."""
        cors = CORSConfigurationBuilder()

        assert cors.headers.is_header_allowed("Authorization") is True
        assert cors.headers.is_header_allowed("authorization") is True  # Case insensitive
        assert cors.headers.is_header_allowed("X-Evil-Header") is False

    def test_is_method_allowed(self):
        """Test method validation."""
        cors = CORSConfigurationBuilder()

        assert cors.headers.is_method_allowed("GET") is True
        assert cors.headers.is_method_allowed("get") is True  # Case insensitive
        assert cors.headers.is_method_allowed("TRACE") is False


class TestSecurityBuilder:
    """Test the Security sub-builder."""

    def test_validate_content_type_allowed(self):
        """Test content type validation for allowed types."""
        cors = CORSConfigurationBuilder()

        allowed_types = [
            "application/json",
            "application/json; charset=utf-8",
            "text/plain",
            "multipart/form-data; boundary=----WebKitFormBoundary",
            ""  # Empty is allowed
        ]

        for content_type in allowed_types:
            assert cors.security.validate_content_type(content_type) is True

    def test_validate_content_type_suspicious(self):
        """Test content type validation for suspicious types."""
        cors = CORSConfigurationBuilder()

        suspicious_types = [
            "text/x-shellscript",
            "application/x-msdownload",
            "text/vbscript",
            "application/vnd.ms-excel"
        ]

        for content_type in suspicious_types:
            assert cors.security.validate_content_type(content_type) is False

    def test_log_security_event(self):
        """Test security event logging."""
        cors = CORSConfigurationBuilder()
        cors.security.clear_security_events()

        cors.security.log_security_event(
            "test_event",
            "https://test.com",
            "/api/test",
            request_id="req-123",
            additional_info={"key": "value"}
        )

        events = cors.security.get_security_events()
        assert len(events) == 1

        event = events[0]
        assert event.event_type == "test_event"
        assert event.origin == "https://test.com"
        assert event.path == "/api/test"
        assert event.request_id == "req-123"
        assert event.details.get("key") == "value"

    def test_security_events_bounded(self):
        """Test that security events are bounded to prevent memory leaks."""
        cors = CORSConfigurationBuilder()
        cors.security.clear_security_events()

        # Add more than 1000 events
        for i in range(1100):
            cors.security.log_security_event(
                f"test_event_{i}",
                f"https://test{i}.com",
                f"/api/test{i}"
            )

        # Should be bounded after cleanup - we trim to 500 when we hit 1001
        # but then continue adding, so we'll have 599 events (500 + 99 more)
        events = cors.security.get_security_events(2000)
        assert 500 <= len(events) <= 600  # Between 500 and 600 events


class TestServiceDetector:
    """Test the Service Detector sub-builder."""

    def test_is_internal_request_by_header(self):
        """Test internal request detection by service header."""
        cors = CORSConfigurationBuilder()

        headers = {"x-service-name": "auth-service"}
        assert cors.service_detector.is_internal_request(headers) is True

        headers = {"x-service-name": "unknown-service"}
        assert cors.service_detector.is_internal_request(headers) is False

    def test_is_internal_request_by_user_agent(self):
        """Test internal request detection by user agent."""
        cors = CORSConfigurationBuilder()

        headers = {"user-agent": "httpx/0.24.0"}
        assert cors.service_detector.is_internal_request(headers) is True

        headers = {"user-agent": "Mozilla/5.0"}
        assert cors.service_detector.is_internal_request(headers) is False

    def test_should_bypass_cors(self):
        """Test CORS bypass logic."""
        # Development environment - should bypass for internal
        cors_dev = CORSConfigurationBuilder({"ENVIRONMENT": "development"})
        headers = {"x-service-name": "auth-service"}
        assert cors_dev.service_detector.should_bypass_cors(headers) is True

        # Production environment - should NOT bypass
        cors_prod = CORSConfigurationBuilder({"ENVIRONMENT": "production"})
        assert cors_prod.service_detector.should_bypass_cors(headers) is False


class TestFastAPIBuilder:
    """Test the FastAPI sub-builder."""

    def test_get_middleware_config(self):
        """Test FastAPI middleware configuration generation."""
        cors = CORSConfigurationBuilder({"ENVIRONMENT": "production"})
        config = cors.fastapi.get_middleware_config()

        assert "allow_origins" in config
        assert "allow_credentials" in config
        assert "allow_methods" in config
        assert "allow_headers" in config
        assert "expose_headers" in config
        assert "max_age" in config

        assert config["allow_credentials"] is True
        assert config["max_age"] == 3600

    def test_get_middleware_kwargs(self):
        """Test FastAPI middleware kwargs generation."""
        cors = CORSConfigurationBuilder()
        kwargs = cors.fastapi.get_middleware_kwargs()

        # Should be same as get_middleware_config for now
        assert kwargs == cors.fastapi.get_middleware_config()


class TestHealthBuilder:
    """Test the Health sub-builder."""

    def test_get_config_info(self):
        """Test configuration info generation."""
        cors = CORSConfigurationBuilder({"ENVIRONMENT": "staging"})
        info = cors.health.get_config_info()

        assert info["environment"] == "staging"
        assert info["origins_count"] > 0
        assert "origins" in info
        assert "allow_credentials" in info
        assert "config_valid" in info

    def test_validate_config(self):
        """Test configuration validation."""
        cors = CORSConfigurationBuilder()

        valid_config = {
            "allow_origins": ["https://example.com"],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"],
            "expose_headers": ["X-Request-ID"],
            "max_age": 3600
        }
        assert cors.health.validate_config(valid_config) is True

        # Missing key
        invalid_config = valid_config.copy()
        del invalid_config["allow_origins"]
        assert cors.health.validate_config(invalid_config) is False

        # Wrong type
        invalid_config = valid_config.copy()
        invalid_config["allow_credentials"] = "true"  # Should be bool
        assert cors.health.validate_config(invalid_config) is False

    def test_get_debug_info(self):
        """Test debug info generation."""
        cors = CORSConfigurationBuilder()
        debug = cors.health.get_debug_info()

        assert "environment" in debug
        assert "configuration" in debug
        assert "validation" in debug
        assert "security" in debug
        assert "sample_origins" in debug


class TestWebSocketBuilder:
    """Test the WebSocket sub-builder."""

    def test_allowed_origins(self):
        """Test WebSocket allowed origins."""
        cors = CORSConfigurationBuilder()
        ws_origins = cors.websocket.allowed_origins

        # Should be same as regular origins for now
        assert ws_origins == cors.origins.allowed

    def test_is_origin_allowed(self):
        """Test WebSocket origin validation."""
        cors = CORSConfigurationBuilder({"ENVIRONMENT": "production"})

        assert cors.websocket.is_origin_allowed("https://netrasystems.ai") is True
        assert cors.websocket.is_origin_allowed("https://evil.com") is False


class TestStaticAssetsBuilder:
    """Test the Static Assets sub-builder."""

    def test_get_static_headers(self):
        """Test static file CORS headers."""
        cors = CORSConfigurationBuilder()
        headers = cors.static.get_static_headers()

        assert headers["Access-Control-Allow-Origin"] == "*"
        assert headers["Access-Control-Allow-Methods"] == "GET, HEAD, OPTIONS"
        assert headers["Access-Control-Max-Age"] == "86400"

    def test_get_cdn_config(self):
        """Test CDN CORS configuration."""
        cors = CORSConfigurationBuilder()
        config = cors.static.get_cdn_config()

        assert config["allow_origins"] == ["*"]
        assert config["allow_credentials"] is False
        assert config["allow_methods"] == ["GET", "HEAD", "OPTIONS"]
        assert config["max_age"] == 86400


class TestValidation:
    """Test overall validation methods."""

    def test_validate_development(self):
        """Test validation in development environment."""
        cors = CORSConfigurationBuilder({"ENVIRONMENT": "development"})
        valid, error = cors.validate()

        assert valid is True
        assert error == ""

    def test_validate_production_with_wildcard(self):
        """Test validation fails in production with wildcard."""
        env_vars = {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "*"
        }
        cors = CORSConfigurationBuilder(env_vars)
        valid, error = cors.validate()

        assert valid is False
        assert "should not allow all origins" in error

    def test_get_safe_log_message(self):
        """Test safe log message generation."""
        cors = CORSConfigurationBuilder()
        message = cors.get_safe_log_message()

        assert "CORS Configuration" in message
        assert "development" in message
        assert "origins allowed" in message


class TestBackwardCompatibility:
    """Test backward compatibility functions."""

    def test_get_cors_origins(self):
        """Test backward compatibility for get_cors_origins."""
        from shared.cors_config_builder import get_cors_origins

        origins = get_cors_origins("production")
        assert "https://netrasystems.ai" in origins

    def test_get_cors_config(self):
        """Test backward compatibility for get_cors_config."""
        from shared.cors_config_builder import get_cors_config

        config = get_cors_config("staging")
        assert "allow_origins" in config
        assert "allow_credentials" in config

    def test_is_origin_allowed(self):
        """Test backward compatibility for is_origin_allowed."""
        from shared.cors_config_builder import is_origin_allowed

        allowed = is_origin_allowed(
            "https://netrasystems.ai",
            [],  # This param is ignored in new implementation
            environment="production"
        )
        assert allowed is True

    def test_validate_content_type(self):
        """Test backward compatibility for validate_content_type."""
        from shared.cors_config_builder import validate_content_type

        assert validate_content_type("application/json") is True
        assert validate_content_type("text/vbscript") is False

    def test_is_service_to_service_request(self):
        """Test backward compatibility for is_service_to_service_request."""
        from shared.cors_config_builder import is_service_to_service_request

        headers = {"x-service-name": "auth-service"}
        assert is_service_to_service_request(headers) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])