#!/usr/bin/env python3
"""
CORS Dynamic Ports Test Suite
Tests that expose CORS failures when services run on non-standard ports.

These tests are designed to FAIL with the current implementation and demonstrate
the critical issue where CORS configuration doesn't properly handle dynamic ports
in development environments.

EXPECTED FAILURES:
    1. Frontend on port 3002+ fails CORS validation
2. Backend on port 8002+ fails CORS validation
3. Auth service on port 8082+ fails CORS validation
"""

import os
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import httpx
import pytest

@dataclass
class DynamicServiceConfig:
    # """Dynamic service configuration for testing."""

    # frontend_port: int
    # backend_port: int
    # auth_port: int

    # @property
    def frontend_url(self) -> str:
        return f"http://localhost:{self.frontend_port}"

    @property
    def backend_url(self) -> str:
        return f"http://localhost:{self.backend_port}"

    @property
    def auth_url(self) -> str:
        return f"http://localhost:{self.auth_port}"

class TestSyntaxFix:
    """Generated test class"""

    @staticmethod
    def find_free_port(start_port: int = 8000) -> int:
        """Find a free port starting from the given port."""
        port = start_port
        while port < start_port + 100:  # Try 100 ports
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    return port
                except OSError:
                    port += 1
        raise RuntimeError(f"No free port found starting from {start_port}")

    @staticmethod
    def mock_service_discovery(config):
        """Mock service discovery with dynamic port configuration."""
        mock_discovery = MagicMock()
        mock_discovery.read_backend_info.return_value = {
            "port": config.backend_port,
            "api_url": config.backend_url,
            "ws_url": f"ws://localhost:{config.backend_port}/ws",
        }
        mock_discovery.read_frontend_info.return_value = {
            "port": config.frontend_port,
            "url": config.frontend_url,
        }
        mock_discovery.read_auth_info.return_value = {
            "port": config.auth_port,
            "url": config.auth_url,
            "api_url": config.auth_url,
        }

    with patch(
        "app.core.middleware_setup.ServiceDiscovery", return_value=mock_discovery
    ):
        with patch.dict(
            os.environ, {"ENVIRONMENT": "development", "CORS_ORIGINS": "*"}
        ):
            yield mock_discovery

class TestCORSDynamicFrontendPorts:
    # """Test 1: Dynamic Frontend Port Test - Expose hardcoded frontend port issues."""

    # @pytest.fixture
    def dynamic_frontend_configs(self):
        """Generate frontend configurations with non-standard ports."""
        return [
            DynamicServiceConfig(frontend_port=3002, backend_port=8000, auth_port=8081),
            DynamicServiceConfig(frontend_port=3003, backend_port=8000, auth_port=8081),
            DynamicServiceConfig(frontend_port=4000, backend_port=8000, auth_port=8081),
            DynamicServiceConfig(frontend_port=5173, backend_port=8000, auth_port=8081),
            # Vite dev server
            DynamicServiceConfig(frontend_port=3333, backend_port=8000, auth_port=8081),
            # Next.js alternative
        ]

    @pytest.mark.asyncio
    async def test_cors_hardcoded_localhost_origins_limitation(self, dynamic_frontend_configs
    ):
        """
        Test that demonstrates the hardcoded localhost origins limitation.

        THIS TEST WILL FAIL when CORS_ORIGINS is not set to wildcard and we have
        a restrictive environment that doesn't allow pattern matching to override
        the static origin list.
        """
        # Force a scenario where only hardcoded origins are used (no wildcard,
        # no patterns)
        with patch.dict(os.environ, {"ENVIRONMENT": "testing", "CORS_ORIGINS": ""}):
            # Mock the pattern matching to return False to simulate restrictive
            # env
            with patch(
                "app.core.middleware_setup._check_pattern_matches", return_value=False
            ):
                with patch(
                    "app.core.middleware_setup._check_wildcard_match",
                    return_value=False,
                ):
    from netra_backend.app.core.middleware_setup import (
                        _get_localhost_origins,

                    localhost_origins = _get_localhost_origins()

                    # Test dynamic frontend ports against hardcoded list only
#                     for config in dynamic_frontend_configs: # Possibly broken comprehension
                        origin = config.frontend_url

                        # Direct check against hardcoded localhost origins
                        is_in_hardcoded_list = origin in localhost_origins

                        # This will demonstrate the limitation
                        if not is_in_hardcoded_list:
                            # This assertion WILL FAIL for non-standard ports
                            assert False, (
                                f"Dynamic frontend port {
                                    config.frontend_port} NOT in hardcoded list. "
                                f"Origin: {origin}, Hardcoded localhost origins: {localhost_origins}. "
                                f"This shows the fundamental limitation: hardcoded ports 3000/3001 only."

    @pytest.mark.asyncio
    async def test_service_discovery_integration_gap(self, dynamic_frontend_configs):
        """
        Test that demonstrates the gap between service discovery and CORS configuration.

        THIS TEST WILL FAIL because service discovery knows about dynamic ports
#         but CORS configuration doesn't automatically use that information. # Possibly broken comprehension
        """
#         for config in dynamic_frontend_configs: # Possibly broken comprehension
            with mock_service_discovery(config):
    from dev_launcher.service_discovery import ServiceDiscovery
                from netra_backend.app.core.middleware_setup import get_cors_origins

                # Service discovery knows about the dynamic port
                discovery = ServiceDiscovery()
                frontend_info = discovery.read_frontend_info()

                assert (
                    frontend_info is not None
                ), "Service discovery should have frontend info"
                assert (
                    frontend_info["port"] == config.frontend_port
                ), "Service discovery should track dynamic port"

                # But CORS origins are still hardcoded
                cors_origins = get_cors_origins()

                # Check if the dynamic URL from service discovery is in CORS
                # origins
                frontend_url_from_discovery = frontend_info["url"]

                # This will fail unless wildcards are used
                if "*" not in cors_origins:
                    is_dynamic_url_allowed = frontend_url_from_discovery in cors_origins

                    if not is_dynamic_url_allowed:
                        # This assertion WILL FAIL showing the integration gap
                        assert False, (
                            f"Service discovery tracks dynamic frontend port {
                                config.frontend_port} "
                            f"at URL {frontend_url_from_discovery}, but this URL is NOT in CORS origins: {cors_origins}. "
                            f"This demonstrates the gap between service discovery and CORS configuration."

    @pytest.mark.asyncio
    async def test_dynamic_frontend_cors_headers_unit_test(, self, dynamic_frontend_configs
    ):
        """
        Unit test: Verify CORS middleware directly allows dynamic frontend ports.

        THIS TEST WILL FAIL because the CustomCORSMiddleware relies on get_cors_origins()
        which returns hardcoded localhost ports, not dynamic ones.
        """
#         for config in dynamic_frontend_configs: # Possibly broken comprehension
            with mock_service_discovery(config):
    from fastapi import Request

from netra_backend.app.core.middleware_setup import CustomCORSMiddleware

                # Mock FastAPI app and service discovery
                mock_app = MagicMock()
                mock_service_discovery_instance = MagicMock()
                mock_service_discovery_instance.read_frontend_info.return_value = {
                    "port": config.frontend_port,
                    "url": config.frontend_url,

                middleware = CustomCORSMiddleware(
                    app=mock_app, service_discovery=mock_service_discovery_instance

                # Create mock request with dynamic frontend origin
                mock_request = MagicMock(spec=Request)
                mock_request.headers = {"origin": config.frontend_url}
                mock_request.method = "GET"

                # Test if origin is allowed
                is_allowed = middleware._is_origin_allowed_with_discovery(
                    config.frontend_url

                # This assertion WILL FAIL for non-standard ports
                assert is_allowed, (
                    f"Middleware should allow dynamic frontend port {
                        config.frontend_port} "
                    f"but rejected origin {config.frontend_url}. "
                    f"The service discovery integration exists but doesn't override the "
                    f"hardcoded localhost origins in get_cors_origins()."

    @pytest.mark.asyncio
    async def test_dynamic_frontend_http_integration(self):
        """
        Integration test: Simulate actual HTTP requests from dynamic frontend ports.

        THIS TEST WILL FAIL when making actual requests because the backend
        CORS middleware will reject origins from non-standard frontend ports.
        """
        # Use a definitely non-standard port
        dynamic_port = find_free_port(4500)
        dynamic_origin = f"http://localhost:{dynamic_port}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"Origin": dynamic_origin, "Content-Type": "application/json"}

            try:
                # Test preflight request
                preflight_response = await client.options(
                    "http://localhost:8000/health", headers=headers, timeout=5.0

                # This assertion WILL FAIL - preflight will be rejected
                assert preflight_response.status_code == 200, (
                    f"Preflight OPTIONS request failed for dynamic frontend port {dynamic_port}. "
                    f"Status: {preflight_response.status_code}"

                cors_origin = preflight_response.headers.get(
                    "Access-Control-Allow-Origin"
                assert cors_origin in [dynamic_origin, "*"], (
#                     f"CORS headers missing or incorrect for dynamic frontend port {dynamic_port}. " # Possibly broken comprehension
                    f"Expected: {dynamic_origin} or *, Got: {cors_origin}"

                # Test actual request
                actual_response = await client.get(
                    "http://localhost:8000/health", headers=headers, timeout=5.0

                cors_origin = actual_response.headers.get("Access-Control-Allow-Origin")
                assert cors_origin in [dynamic_origin, "*"], (
#                     f"Actual request CORS headers missing for dynamic frontend port {dynamic_port}. " # Possibly broken comprehension
                    f"Expected: {dynamic_origin} or *, Got: {cors_origin}"

            except httpx.ConnectError:
                pytest.skip("Backend service not running for integration test")
            except httpx.TimeoutException:
                pytest.skip("Backend service timeout during integration test")

class TestCORSDynamicBackendPorts:
    # """Test 2: Dynamic Backend Port Test - Expose backend port configuration issues."""

    # @pytest.fixture
    def dynamic_backend_configs(self):
        """Generate backend configurations with non-standard ports."""
        return [
            DynamicServiceConfig(frontend_port=3001, backend_port=8002, auth_port=8081),
            DynamicServiceConfig(frontend_port=3001, backend_port=8080, auth_port=8081),
            DynamicServiceConfig(frontend_port=3001, backend_port=9000, auth_port=8081),
            DynamicServiceConfig(frontend_port=3001, backend_port=5000, auth_port=8081),
            # Flask default
        ]

    @pytest.mark.asyncio
    async def test_dynamic_backend_port_service_discovery(, self, dynamic_backend_configs
    ):
        """
        Test that service discovery properly registers dynamic backend ports.

        THIS TEST WILL FAIL because even though service discovery tracks the ports,
#         the CORS middleware doesn't properly integrate with this information. # Possibly broken comprehension
        """
#         for config in dynamic_backend_configs: # Possibly broken comprehension
            with mock_service_discovery(config):

                discovery = ServiceDiscovery()
                backend_info = discovery.read_backend_info()

                # Service discovery should work
                assert (
                    backend_info is not None
                ), "Service discovery should return backend info"
                assert (
                    backend_info["port"] == config.backend_port
                ), f"Service discovery should track dynamic backend port {
                        config.backend_port}"

                # But CORS integration will fail
                mock_app = MagicMock()
                middleware = CustomCORSMiddleware(
                    app=mock_app, service_discovery=discovery

                # Test if backend can accept requests from standard frontend
                frontend_origin = "http://localhost:3001"
                is_allowed = middleware._is_origin_allowed_with_discovery(
                    frontend_origin

                # This might pass for standard frontend port, but the real issue is that
                # the backend running on dynamic port won't be properly
                # configured for CORS
                assert (
                    is_allowed
                ), f"Standard frontend should be allowed with dynamic backend port {
                    config.backend_port}"

    @pytest.mark.asyncio
    async def test_dynamic_backend_cors_configuration_unit(, self, dynamic_backend_configs
    ):
        """
        Unit test: Verify backend CORS configuration works with dynamic ports.

        THIS TEST WILL FAIL because the CORS origins are determined at startup
        and don't account for the backend's own dynamic port allocation.
        """
#         for config in dynamic_backend_configs: # Possibly broken comprehension
            # Mock environment to simulate backend running on dynamic port
            with patch.dict(
                os.environ,
                {
                    "BACKEND_PORT": str(config.backend_port),
                    "ENVIRONMENT": "development",
                },
            ):
                with mock_service_discovery(config):
    from netra_backend.app.core.middleware_setup import (
                        get_cors_origins,

                    origins = get_cors_origins()

                    # The default origins should include the dynamic backend
                    # port for self-requests
                    backend_self_origin = f"http://localhost:{
                        config.backend_port}"

                    # This assertion WILL FAIL because _get_default_dev_origins()
                    # only includes hardcoded port 8000, not dynamic ports
                    assert backend_self_origin in origins or "*" in origins, (
                        f"Backend running on dynamic port {
                            config.backend_port} should include "
                        f"its own origin {backend_self_origin} in CORS origins. "
                        f"Current origins: {origins}. This fails because the CORS configuration "
                        f"is static and doesn't adapt to the backend's actual port."

    @pytest.mark.asyncio
    async def test_cross_service_requests_dynamic_backend(self):
        """
        Integration test: Test cross-service requests when backend runs on dynamic port.

        THIS TEST WILL FAIL because services trying to communicate with a backend
        on a dynamic port will encounter CORS rejections.
        """
        dynamic_backend_port = find_free_port(8500)
        config = DynamicServiceConfig(
            frontend_port=3001, backend_port=dynamic_backend_port, auth_port=8081

        with mock_service_discovery(config):
            # Simulate a request from auth service to dynamic backend
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {
                    "Origin": "http://localhost:8081",  # Auth service origin
                    "X-Service-ID": "netra-auth",
                    "Content-Type": "application/json",

                try:
                    # This request would go to the dynamically allocated
                    # backend port
                    response = await client.get(
                        f"http://localhost:{dynamic_backend_port}/health",
                        headers=headers,
                        timeout=5.0,

                    # This assertion WILL FAIL because the backend on dynamic port
                    # doesn't know about the auth service's static port
                    cors_origin = response.headers.get("Access-Control-Allow-Origin")
                    assert cors_origin is not None, (
                        f"Cross-service request from auth to dynamic backend port {dynamic_backend_port} "
                        f"should include CORS headers but was rejected."

                except httpx.ConnectError:
                    pytest.skip("Dynamic backend not running for cross-service test")

class TestCORSDynamicAuthServicePorts:
    # """Test 3: Dynamic Auth Service Port Test - Expose auth service port issues."""

    # @pytest.fixture
    def dynamic_auth_configs(self):
        """Generate auth service configurations with non-standard ports."""
        return [
            DynamicServiceConfig(frontend_port=3001, backend_port=8000, auth_port=8082),
            DynamicServiceConfig(frontend_port=3001, backend_port=8000, auth_port=8090),
            DynamicServiceConfig(frontend_port=3001, backend_port=8000, auth_port=9001),
            DynamicServiceConfig(frontend_port=3001, backend_port=8000, auth_port=7000),
        ]

    @pytest.mark.asyncio
    async def test_dynamic_auth_port_cors_validation(self, dynamic_auth_configs):
        """
        Test that auth service on dynamic ports properly handles CORS.

        THIS TEST WILL FAIL because the auth service CORS configuration
        doesn't dynamically adapt to non-standard ports.
        """
#         for config in dynamic_auth_configs: # Possibly broken comprehension
            with mock_service_discovery(config):
                # Test if frontend can make requests to auth service on dynamic
                # port
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    headers = {
                        "Origin": config.frontend_url,
                        "Content-Type": "application/json",

                    try:
                        # Test auth config endpoint on dynamic port
                        response = await client.get(
                            f"{config.auth_url}/auth/config",
                            headers=headers,
                            timeout=5.0,

                        # This assertion WILL FAIL for dynamic auth ports
                        cors_origin = response.headers.get(
                            "Access-Control-Allow-Origin"
                        assert cors_origin in [config.frontend_url, "*"], (
                            f"Auth service on dynamic port {
                                config.auth_port} should accept "
                            f"CORS requests from frontend but rejected origin {
                                config.frontend_url}. "
                            f"Got CORS origin: {cors_origin}"

                    except httpx.ConnectError:
                        pytest.skip(
                            f"Auth service not running on dynamic port {
                                config.auth_port}"
                    except httpx.TimeoutException:
                        pytest.skip(
                            f"Auth service timeout on dynamic port {
                                config.auth_port}"

    @pytest.mark.asyncio
    async def test_auth_service_discovery_integration(self, dynamic_auth_configs):
        """
        Unit test: Verify auth service discovery properly integrates with CORS.

        THIS TEST WILL FAIL because the auth service configuration doesn't
        properly read from service discovery for CORS setup.
        """
#         for config in dynamic_auth_configs: # Possibly broken comprehension
            with mock_service_discovery(config):

                discovery = ServiceDiscovery()
                auth_info = discovery.read_auth_info()

                assert (
                    auth_info is not None
                ), "Auth service discovery should return info"
                assert (
                    auth_info["port"] == config.auth_port
                ), f"Service discovery should track auth port {
                        config.auth_port}"

                # Test CORS integration
                mock_app = MagicMock()
                middleware = CustomCORSMiddleware(
                    app=mock_app, service_discovery=discovery

                # Test if auth service URL is in allowed origins
                auth_origin = config.auth_url
                is_allowed = middleware._check_service_discovery_origins(auth_origin)

                # This assertion WILL FAIL because _check_service_discovery_origins
                # doesn't properly handle auth service's own origin
                assert is_allowed, (
                    f"Auth service on dynamic port {
                        config.auth_port} should allow "
                    f"its own origin {auth_origin} but was rejected by service discovery integration."

    @pytest.mark.asyncio
    async def test_oauth_callback_dynamic_auth_port(self):
        """
        Integration test: Test OAuth callback handling with dynamic auth port.

        THIS TEST WILL FAIL because OAuth callbacks depend on consistent
        auth service URLs that don't account for dynamic port allocation.
        """
        dynamic_auth_port = find_free_port(8500)
        config = DynamicServiceConfig(
            frontend_port=3001, backend_port=8000, auth_port=dynamic_auth_port

        with mock_service_discovery(config):
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {
                    "Origin": config.frontend_url,
                    "Content-Type": "application/json",

                try:
                    # Test OAuth callback endpoint on dynamic port
                    callback_response = await client.options(
                        f"{config.auth_url}/auth/callback", headers=headers, timeout=5.0

                    # This assertion WILL FAIL because OAuth configuration
                    # doesn't dynamically update for port changes
                    assert callback_response.status_code == 200, (
                        f"OAuth callback on dynamic auth port {dynamic_auth_port} "
                        f"should handle CORS preflight but failed with status "
                        f"{callback_response.status_code}"

                    cors_origin = callback_response.headers.get(
                        "Access-Control-Allow-Origin"
                    assert cors_origin in [config.frontend_url, "*"], (
                        f"OAuth callback should allow frontend origin {
                            config.frontend_url} "
                        f"but got CORS origin: {cors_origin}"

                except httpx.ConnectError:
                    pytest.skip(
#                         "Auth service not running on dynamic port for OAuth test" # Possibly broken comprehension

class TestCORSComprehensiveDynamicPortFailures:
    # """Comprehensive test showing the complete scope of dynamic port failures."""

    # @pytest.mark.asyncio
    # async def test_complete_dynamic_environment_failure(self):
    # """
    # Comprehensive test: Complete failure when all services use dynamic ports.

    # THIS TEST WILL FAIL SPECTACULARLY because none of the services
    # can communicate when they all use dynamic ports in a restrictive CORS environment.
    # """
    # # Generate completely dynamic port configuration
    # config = DynamicServiceConfig(
    # frontend_port=find_free_port(3500),
    # backend_port=find_free_port(8500),
    # auth_port=find_free_port(9500),

    # # Force restrictive CORS environment (no wildcards, no pattern
    # # matching)
    # with patch.dict(
    # os.environ,
    # {
    # "ENVIRONMENT": "testing",
    # "CORS_ORIGINS": "http://localhost:3000,http://localhost:8000",
    # },
    # ):
    # with patch(
    # "app.core.middleware_setup._check_pattern_matches", return_value=False
    # ):
    # with patch(
    # "app.core.middleware_setup._check_wildcard_match",
    # return_value=False,
    # ):
    # with mock_service_discovery(config):
    from netra_backend.app.core.middleware_setup import (
                            get_cors_origins,
                            is_origin_allowed,

                        failures = []
                        cors_origins = get_cors_origins()

#                         # Test CORS validation for each dynamic origin # Possibly broken comprehension
                        dynamic_origins = [
                            config.frontend_url,
                            config.backend_url,
                            config.auth_url,
                        ]

#                         for origin in dynamic_origins: # Possibly broken comprehension
                            is_allowed = is_origin_allowed(origin, cors_origins)
                            if not is_allowed:
                                failures.append(
                                    f"Dynamic origin {origin} rejected by CORS"

                        # This assertion WILL FAIL because of multiple CORS
                        # failures
                        assert len(failures) == 0, (
                            "Multiple CORS failures in restrictive dynamic port environment:\n"
                            + "\n".join(f"- {failure}" for failure in failures)
                            + f"\n\nConfiguration: Frontend:{
                                config.frontend_port}, "
                            f"Backend:{
                                config.backend_port}, Auth:{
                                config.auth_port}\n"
                            f"CORS Origins: {cors_origins}\n"
                            f"The current CORS implementation cannot handle environments where "
                            f"all services use dynamic ports in restrictive configurations because "
                            f"it relies on hardcoded port assumptions and doesn't integrate with service discovery."

    @pytest.mark.asyncio
    async def test_credentials_with_dynamic_origins_failure(self):
        """
        Test that demonstrates CORS failure with credentials and dynamic origins.

        THIS TEST WILL FAIL because credentialed requests cannot use wildcard origins,
        so dynamic ports must be explicitly allowed, but they're not in the hardcoded list.
        """
        config = DynamicServiceConfig(
            frontend_port=find_free_port(4000), backend_port=8000, auth_port=8081

        # Simulate production-like environment where wildcards are not allowed
        # with credentials
        with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CORS_ORIGINS": ""}):
            with patch(
                "app.core.middleware_setup._check_wildcard_match", return_value=False
            ):
    from netra_backend.app.core.middleware_setup import (
                    get_cors_origins,

                cors_origins = get_cors_origins()
                origin = config.frontend_url

                # For credentialed requests, we cannot use wildcard "*"
                # So the dynamic origin must be explicitly listed
                is_origin_explicitly_allowed = origin in cors_origins

                # This assertion WILL FAIL for dynamic ports
                assert is_origin_explicitly_allowed, (
                    f"Dynamic frontend port {
                        config.frontend_port} at {origin} "
                    f"is not explicitly listed in CORS origins: {cors_origins}. "
                    f"This breaks credentialed requests because RFC 6454 prohibits wildcard "
                    f"origins with credentials. Dynamic ports must be explicitly allowed, "
                    f"but the current implementation only hardcodes ports 3000/3001."

    @pytest.mark.asyncio
    async def test_cors_origin_enumeration_vs_dynamic_reality(self):
        """
        Test that demonstrates the gap between hardcoded CORS origins and dynamic reality.

        THIS TEST WILL FAIL because it shows the mismatch between what the system
        thinks are valid origins and what ports are actually in use.
        """
        # Get what the system thinks are valid CORS origins
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
    from netra_backend.app.core.middleware_setup import (
                _get_localhost_origins,
                get_cors_origins,

            static_origins = get_cors_origins()
            localhost_origins = _get_localhost_origins()

            # Generate actual dynamic configuration
            actual_config = DynamicServiceConfig(
                frontend_port=find_free_port(4000),
                backend_port=find_free_port(8200),
                auth_port=find_free_port(9200),

            actual_origins = [
                actual_config.frontend_url,
                actual_config.backend_url,
                actual_config.auth_url,
            ]

            # Check if actual origins are covered by static configuration
            uncovered_origins = []
#             for origin in actual_origins: # Possibly broken comprehension
    from netra_backend.app.core.middleware_setup import is_origin_allowed

                if not is_origin_allowed(origin, static_origins):
                    uncovered_origins.append(origin)

            # This assertion WILL FAIL showing the coverage gap
            assert len(uncovered_origins) == 0, (
                f"Static CORS configuration doesn't cover actual dynamic origins:\n"
                f"Static origins: {static_origins}\n"
                f"Localhost origins: {localhost_origins}\n"
                f"Actual dynamic origins: {actual_origins}\n"
                f"Uncovered origins: {uncovered_origins}\n\n"
                f"This demonstrates that the hardcoded approach fails when services "
                f"use dynamic port allocation, which is common in development environments "
                f"with docker-compose, multiple developers, or CI/CD pipelines."

class TestCORSRegexPatternLimitations:
    # """Test the limitations of current regex pattern matching for dynamic ports."""

    # @pytest.mark.asyncio
    # async def test_localhost_pattern_edge_cases(self):
    # """
    # Test edge cases in localhost pattern matching.

    # Some of these tests will PASS (showing the pattern works) but others will
    # FAIL because they expose limitations in how patterns are applied.
    # """
    # with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
    from netra_backend.app.core.middleware_setup import _check_localhost_pattern

            # These should work (and test that pattern is correct)
            valid_cases = [
                "http://localhost:3000",
                "https://localhost:8080",
                "http://127.0.0.1:5000",
                "https://127.0.0.1:9999",
            ]

#             for origin in valid_cases: # Possibly broken comprehension
                assert _check_localhost_pattern(
                    origin
                ), f"Valid localhost pattern should match: {origin}"

            # Edge cases that expose limitations
            edge_cases = [
                ("http://localhost:65535", True, "Max port should be allowed"),
                ("http://localhost:99999", False, "Invalid port should be rejected"),
                ("http://localhost", True, "Localhost without port should work"),
                ("https://localhost", True, "HTTPS localhost without port should work"),
            ]

#             for origin, expected, description in edge_cases: # Possibly broken comprehension
                result = _check_localhost_pattern(origin)
                # Some of these assertions may FAIL due to regex limitations
                assert (
                    result == expected
                ), f"{description}: {origin} -> expected {expected}, got {result}"

    @pytest.mark.asyncio
    async def test_pattern_vs_static_list_inconsistency(self):
        """
        Test that shows inconsistency between pattern matching and static origin lists.

        THIS TEST WILL FAIL because it demonstrates that the pattern matching
        logic allows more origins than the static origin list includes.
        """
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
    from netra_backend.app.core.middleware_setup import (
                _check_localhost_pattern,
                _get_localhost_origins,
                get_cors_origins,
                is_origin_allowed,

            # Origins that pass pattern matching
            pattern_allowed = []
            test_origins = [
                "http://localhost:3002",
                "http://localhost:4000",
                "http://localhost:8080",
                "https://localhost:3000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
            ]

#             for origin in test_origins: # Possibly broken comprehension
                if _check_localhost_pattern(origin):
                    pattern_allowed.append(origin)

            # Origins in static list
            static_origins = _get_localhost_origins()
            cors_origins = get_cors_origins()

            # Check which pattern-allowed origins are actually allowed by full
            # CORS logic
            actually_allowed = []
            pattern_rejected = []

#             for origin in pattern_allowed: # Possibly broken comprehension
                if is_origin_allowed(origin, cors_origins):
                    actually_allowed.append(origin)
                else:
                    pattern_rejected.append(origin)

            # This assertion WILL FAIL, showing the inconsistency
            assert len(pattern_rejected) == 0, (
                f"Inconsistency between pattern matching and CORS validation:\n"
                f"Pattern allows: {pattern_allowed}\n"
                f"Static localhost origins: {static_origins}\n"
                f"Full CORS origins: {cors_origins}\n"
                f"Actually allowed: {actually_allowed}\n"
                f"Pattern-allowed but CORS-rejected: {pattern_rejected}\n\n"
                f"This shows that _check_localhost_pattern() correctly identifies valid "
                f"localhost origins, but they get rejected by the hardcoded static origin list. "
                f"The pattern matching logic is more flexible than the implementation uses."

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
