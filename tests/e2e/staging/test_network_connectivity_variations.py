"""Additional network connectivity test variations for staging issues.

These tests provide additional test cases and variations for the core network
connectivity issues found in staging, testing different scenarios and edge cases.
"""

import pytest
import asyncio
import socket
import time
from typing import List, Dict
from test_framework.environment_markers import staging_only, env_requires
from shared.isolated_environment import IsolatedEnvironment


class NetworkConnectivityVariationsTests:
    """Additional test variations for network connectivity issues."""

    @staging_only
    @pytest.mark.e2e
    async def test_backend_port_sequence_all_unavailable(self):
        """Test that a sequence of backend ports are all unavailable.
        
        This provides additional test coverage for port availability issues.
        This test should FAIL with connection refused errors across multiple ports.
        """
        # Test a range of ports that might be expected for backend services
        backend_ports = [8000, 8001, 8002, 8080, 8081, 3000]
        port_failures = []
        
        for port in backend_ports:
            try:
                # Quick socket connection test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                
                if result != 0:  # Connection failed
                    port_failures.append({
                        "port": port,
                        "error_code": result,
                        "status": "CONNECTION_REFUSED"
                    })
            except Exception as e:
                port_failures.append({
                    "port": port,
                    "error": str(e),
                    "status": "SOCKET_ERROR"
                })
        
        # This test should FAIL - expecting all ports unavailable
        assert len(port_failures) == len(backend_ports), (
            f"Expected all {len(backend_ports)} backend ports to be unavailable, "
            f"but {len(backend_ports) - len(port_failures)} ports are accessible. "
            f"Port failures: {port_failures}. "
            f"If some ports are available, backend may be partially running."
        )

    @staging_only  
    @pytest.mark.e2e
    async def test_intermittent_connection_failures_pattern(self):
        """Test intermittent connection failures showing unstable network.
        
        Additional test case: some connections succeed, others fail randomly.
        This test should show inconsistent network behavior.
        """
        import aiohttp
        
        test_url = "http://127.0.0.1:8000/health"
        connection_attempts = 10
        connection_results = []
        
        for i in range(connection_attempts):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as session:
                    async with session.get(test_url) as response:
                        connection_results.append({
                            "attempt": i + 1,
                            "status": "SUCCESS",
                            "status_code": response.status
                        })
            except aiohttp.ClientConnectorError:
                connection_results.append({
                    "attempt": i + 1,
                    "status": "CONNECTION_REFUSED"
                })
            except Exception as e:
                connection_results.append({
                    "attempt": i + 1,
                    "status": "OTHER_ERROR",
                    "error": str(e)
                })
            
            # Small delay between attempts
            await asyncio.sleep(0.2)
        
        # Count connection types
        successes = [r for r in connection_results if r["status"] == "SUCCESS"]
        failures = [r for r in connection_results if r["status"] != "SUCCESS"]
        
        # This test expects SOME failures (showing network instability)
        assert len(failures) >= connection_attempts * 0.3, (
            f"Expected at least 30% connection failures (network instability), "
            f"but got {len(failures)} failures out of {connection_attempts} attempts. "
            f"Success rate: {len(successes)}/{connection_attempts}. "
            f"Results: {connection_results}"
        )

    @staging_only
    @pytest.mark.e2e
    def test_proxy_configuration_multiple_backends_fail(self):
        """Test that proxy fails to connect to multiple backend variations.
        
        Additional test case: different backend URL patterns all fail.
        """
        import requests
        
        # Different backend URL patterns that might be configured
        backend_url_variations = [
            "http://127.0.0.1:8000",
            "http://localhost:8000", 
            "http://backend:8000",      # Docker service name
            "http://api:8000",          # Alternative Docker name
            "http://0.0.0.0:8000",      # Bind-all address
        ]
        
        proxy_failures = []
        
        for backend_url in backend_url_variations:
            try:
                response = requests.get(f"{backend_url}/health", timeout=2.0)
                # If we get here, connection succeeded (unexpected)
                pass
            except requests.exceptions.ConnectionError as e:
                proxy_failures.append({
                    "backend_url": backend_url,
                    "error": str(e)[:100],
                    "error_type": "CONNECTION_ERROR"
                })
            except requests.exceptions.Timeout:
                proxy_failures.append({
                    "backend_url": backend_url,
                    "error": "Request timeout",
                    "error_type": "TIMEOUT"
                })
        
        # This test should FAIL - expecting all backend variations to fail
        assert len(proxy_failures) >= len(backend_url_variations) * 0.8, (
            f"Expected most backend URL variations to fail (at least 80%), "
            f"but only {len(proxy_failures)} out of {len(backend_url_variations)} failed. "
            f"Failures: {proxy_failures}. "
            f"If many variations work, the backend may be properly configured."
        )

    @staging_only
    @pytest.mark.e2e
    async def test_websocket_connection_also_fails(self):
        """Test that WebSocket connections also fail with similar issues.
        
        Additional test case: WebSocket connections exhibit same network problems.
        """
        import aiohttp
        
        websocket_urls = [
            "ws://127.0.0.1:8000/ws",
            "ws://localhost:8000/websocket",
            "ws://127.0.0.1:8000/ws/chat"
        ]
        
        websocket_failures = []
        
        for ws_url in websocket_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        ws_url, 
                        timeout=aiohttp.ClientTimeout(total=3.0)
                    ) as ws:
                        # If we get here, WebSocket connected (unexpected)
                        await ws.close()
                        
            except aiohttp.ClientConnectorError as e:
                websocket_failures.append({
                    "ws_url": ws_url,
                    "error": str(e),
                    "error_type": "CONNECTION_REFUSED"
                })
            except Exception as e:
                websocket_failures.append({
                    "ws_url": ws_url,
                    "error": str(e)[:100],
                    "error_type": "OTHER_ERROR"
                })
        
        # This test should FAIL - expecting WebSocket connection failures too
        assert len(websocket_failures) >= len(websocket_urls) * 0.67, (
            f"Expected most WebSocket connections to fail (network issues affect all protocols), "
            f"but only {len(websocket_failures)} out of {len(websocket_urls)} failed. "
            f"Failures: {websocket_failures}. "
            f"WebSocket failures indicate broader network connectivity issues."
        )
