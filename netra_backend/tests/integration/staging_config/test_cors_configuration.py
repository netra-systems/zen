"""
Test CORS Configuration

Validates Cross-Origin Resource Sharing configuration
with staging URLs.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest
# Test framework import - using pytest fixtures instead

import asyncio
from typing import Dict, List

import httpx

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

class TestCORSConfiguration(StagingConfigTestBase):
    """Test CORS configuration in staging."""

    @pytest.mark.asyncio
    async def test_cors_preflight(self):
        """Test CORS preflight requests."""
        self.skip_if_not_staging()

        origins = [
        'https://staging.netrasystems.ai',
        'https://app-staging.netrasystems.ai',
        'http://localhost:3000'
        ]

        async with httpx.AsyncClient() as client:
            for origin in origins:
                with self.subTest(origin=origin):
                    # Send OPTIONS request
                    response = await client.options(
                    f"{self.staging_url}/api/threads",
                    headers={
                    'Origin': origin,
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type, Authorization'
                    }
                    )

                    # Check CORS headers
                    self.assertIn('Access-Control-Allow-Origin', response.headers)
                    self.assertIn('Access-Control-Allow-Methods', response.headers)
                    self.assertIn('Access-Control-Allow-Headers', response.headers)

                    # Verify origin is allowed
                    allowed_origin = response.headers.get('Access-Control-Allow-Origin')
                    self.assertIn(allowed_origin, [origin, '*'],
                    f"Origin {origin} not allowed")

                    @pytest.mark.asyncio
                    async def test_cors_actual_request(self):
                        """Test CORS headers on actual requests."""
                        self.skip_if_not_staging()

                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                            f"{self.staging_url}/health",
                            headers={
                            'Origin': 'https://staging.netrasystems.ai'
                            }
                            )

            # Check CORS headers in response
                            self.assertIn('Access-Control-Allow-Origin', response.headers)

            # Verify credentials support
                            if 'Access-Control-Allow-Credentials' in response.headers:
                                self.assertEqual(response.headers['Access-Control-Allow-Credentials'], 'true')

                                @pytest.mark.asyncio
                                async def test_cors_blocked_origin(self):
                                    """Test CORS blocks unauthorized origins."""
                                    self.skip_if_not_staging()

        # Test with unauthorized origin
                                    async with httpx.AsyncClient() as client:
                                        response = await client.options(
                                        f"{self.staging_url}/api/threads",
                                        headers={
                                        'Origin': 'https://malicious-site.com',
                                        'Access-Control-Request-Method': 'POST'
                                        }
                                        )

            # Should either not include CORS headers or explicitly deny
                                        if 'Access-Control-Allow-Origin' in response.headers:
                                            allowed = response.headers['Access-Control-Allow-Origin']
                                            self.assertNotEqual(allowed, 'https://malicious-site.com',
                                            "Malicious origin should not be allowed")

                                            @pytest.mark.asyncio
                                            async def test_cors_methods(self):
                                                """Test allowed CORS methods."""
                                                self.skip_if_not_staging()

                                                async with httpx.AsyncClient() as client:
                                                    response = await client.options(
                                                    f"{self.staging_url}/api/threads",
                                                    headers={
                                                    'Origin': 'https://staging.netrasystems.ai',
                                                    'Access-Control-Request-Method': 'DELETE'
                                                    }
                                                    )

                                                    if 'Access-Control-Allow-Methods' in response.headers:
                                                        allowed_methods = response.headers['Access-Control-Allow-Methods']

                # Check standard methods are allowed
                                                        for method in ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']:
                                                            self.assertIn(method, allowed_methods,
                                                            f"Method {method} not in allowed methods")

                                                            @pytest.mark.asyncio
                                                            async def test_cors_headers(self):
                                                                """Test allowed CORS headers."""
                                                                self.skip_if_not_staging()

                                                                custom_headers = [
                                                                'Authorization',
                                                                'Content-Type',
                                                                'X-Requested-With',
                                                                'X-CSRF-Token'
                                                                ]

                                                                async with httpx.AsyncClient() as client:
                                                                    response = await client.options(
                                                                    f"{self.staging_url}/api/threads",
                                                                    headers={
                                                                    'Origin': 'https://staging.netrasystems.ai',
                                                                    'Access-Control-Request-Headers': ', '.join(custom_headers)
                                                                    }
                                                                    )

                                                                    if 'Access-Control-Allow-Headers' in response.headers:
                                                                        allowed_headers = response.headers['Access-Control-Allow-Headers'].lower()

                                                                        for header in custom_headers:
                                                                            self.assertIn(header.lower(), allowed_headers,
                                                                            f"Header {header} not allowed")

                                                                            @pytest.mark.asyncio
                                                                            async def test_cors_max_age(self):
                                                                                """Test CORS preflight cache duration."""
                                                                                self.skip_if_not_staging()

                                                                                async with httpx.AsyncClient() as client:
                                                                                    response = await client.options(
                                                                                    f"{self.staging_url}/api/threads",
                                                                                    headers={
                                                                                    'Origin': 'https://staging.netrasystems.ai',
                                                                                    'Access-Control-Request-Method': 'POST'
                                                                                    }
                                                                                    )

                                                                                    if 'Access-Control-Max-Age' in response.headers:
                                                                                        max_age = int(response.headers['Access-Control-Max-Age'])

                # Should be reasonable (1 hour to 1 day)
                                                                                        self.assertGreaterEqual(max_age, 3600,
                                                                                        "CORS max age too short")
                                                                                        self.assertLessEqual(max_age, 86400,
                                                                                        "CORS max age too long")

                                                                                        @pytest.mark.asyncio
                                                                                        async def test_cors_websocket(self):
                                                                                            """Test CORS for WebSocket endpoints."""
                                                                                            self.skip_if_not_staging()

                                                                                            async with httpx.AsyncClient() as client:
                                                                                                response = await client.options(
                                                                                                f"{self.staging_url}/ws",
                                                                                                headers={
                                                                                                'Origin': 'https://staging.netrasystems.ai',
                                                                                                'Access-Control-Request-Method': 'GET',
                                                                                                'Access-Control-Request-Headers': 'Upgrade, Connection'
                                                                                                }
                                                                                                )

            # WebSocket endpoints might handle CORS differently
                                                                                                if response.status_code == 200:
                                                                                                    self.assertIn('Access-Control-Allow-Origin', response.headers)