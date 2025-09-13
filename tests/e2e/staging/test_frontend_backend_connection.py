"""Test frontend-backend connection issues found in staging.

These tests reproduce the ECONNREFUSED 127.0.0.1:8000 errors that occur when
the frontend Next.js proxy cannot connect to the backend service.

Based on Docker audit findings:
- Error: connect ECONNREFUSED 172.18.0.6:8000 (Docker)  
- Error: connect ECONNREFUSED 127.0.0.1:8000 (Local/Staging)
- Failed to proxy http://backend:8000/api/mcp/servers
- Failed to proxy http://backend:8000/api/mcp/tools
"""

import pytest
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional
from test_framework.environment_markers import staging_only, env_requires
from shared.isolated_environment import IsolatedEnvironment


class TestFrontendBackendConnection:
    """Test frontend-backend connectivity issues in staging."""

    @staging_only
    @env_requires(
        services=["backend_service", "frontend"],
        features=["api_proxy_configured"]
    )
    @pytest.mark.e2e
    async def test_frontend_cannot_connect_to_backend_api_proxy_failure(self):
        """Test that reproduces the ECONNREFUSED error from frontend API proxy.
        
        This test SHOULD FAIL initially, demonstrating the exact issue where
        Next.js frontend proxy attempts to connect to backend:8000 but gets
        connection refused errors.
        
        Expected failure: Connection refused to localhost:8000 or 127.0.0.1:8000
        """
        # Simulate the exact frontend API proxy behavior
        backend_url = "http://127.0.0.1:8000"  # The problematic URL from audit
        api_endpoints = [
            "/api/mcp/servers",
            "/api/mcp/tools", 
            "/api/health",
            "/api/threads"
        ]
        
        connection_failures = []
        
        # Test each endpoint that was failing in the audit
        for endpoint in api_endpoints:
            full_url = f"{backend_url}{endpoint}"
            
            try:
                # Simulate the Next.js proxy connection attempt
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=2.0, connect=1.0)
                ) as session:
                    async with session.get(full_url) as response:
                        # If we get here, connection succeeded (unexpected in failing case)
                        assert response.status < 500, (
                            f"Backend connected but returned server error {response.status} "
                            f"for {endpoint}. Expected: Connection refused error."
                        )
                        
            except aiohttp.ClientConnectorError as e:
                # This is the EXPECTED failure - connection refused
                connection_failures.append({
                    "endpoint": endpoint,
                    "url": full_url,
                    "error": str(e),
                    "error_type": "ECONNREFUSED"
                })
            except asyncio.TimeoutError:
                connection_failures.append({
                    "endpoint": endpoint, 
                    "url": full_url,
                    "error": "Connection timeout",
                    "error_type": "TIMEOUT"
                })
        
        # This test SHOULD FAIL - we expect connection failures in broken staging
        assert len(connection_failures) > 0, (
            f"Expected connection failures to backend at {backend_url}, "
            f"but all {len(api_endpoints)} endpoints connected successfully. "
            f"Either backend is running when it shouldn't be, or the proxy "
            f"configuration has been fixed."
        )
        
        # Verify we got the specific ECONNREFUSED errors from audit
        econnrefused_errors = [
            f for f in connection_failures 
            if "Connection refused" in f["error"] or f["error_type"] == "ECONNREFUSED"
        ]
        
        assert len(econnrefused_errors) >= 2, (
            f"Expected at least 2 ECONNREFUSED errors (like in audit), "
            f"but got {len(econnrefused_errors)}. "
            f"Connection failures: {connection_failures}"
        )

    @staging_only  
    @env_requires(services=["frontend"])
    @pytest.mark.e2e
    def test_frontend_proxy_configuration_mismatch(self):
        """Test frontend proxy configuration pointing to wrong backend URL.
        
        This test should FAIL, showing that the frontend is configured to 
        connect to localhost:8000 but backend is running elsewhere.
        """
        expected_backend_host = "127.0.0.1"  # From audit logs
        expected_backend_port = 8000
        
        # Test the exact connection the frontend proxy would make
        test_url = f"http://{expected_backend_host}:{expected_backend_port}/health"
        
        try:
            # Short timeout to quickly identify connection issues
            response = requests.get(test_url, timeout=2.0)
            
            # If we get here, either backend is running on expected URL (good)
            # or there's a different issue
            assert response.status_code == 200, (
                f"Backend responded with {response.status_code} at {test_url}. "
                f"Expected: 200 OK if backend is properly configured, "
                f"or connection error if misconfigured."
            )
            
        except requests.exceptions.ConnectionError as e:
            # This is the EXPECTED failure in broken staging
            assert "Connection refused" in str(e) or "ECONNREFUSED" in str(e), (
                f"Expected ECONNREFUSED error for {test_url}, "
                f"but got different connection error: {e}"
            )
            
            # FAIL the test to highlight the configuration issue
            pytest.fail(
                f"Frontend proxy cannot connect to backend at {test_url}. "
                f"Connection refused error: {e}. "
                f"Root cause: Backend service not running on expected host:port "
                f"or proxy configuration pointing to wrong backend URL."
            )
            
        except requests.exceptions.Timeout:
            pytest.fail(
                f"Frontend proxy timeout connecting to backend at {test_url}. "
                f"Backend may be running but not responding to health checks."
            )

    @staging_only
    @pytest.mark.e2e
    async def test_backend_service_not_listening_on_expected_ports(self):
        """Test that backend service is not listening on the expected ports.
        
        This test should FAIL, demonstrating that no service is listening 
        on the ports the frontend expects to connect to.
        """
        import socket
        
        expected_ports = [8000, 8080]  # Common backend ports from configuration
        listening_services = {}
        port_scan_failures = []
        
        for port in expected_ports:
            try:
                # Test if anything is listening on the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                
                if result == 0:
                    listening_services[port] = "Service listening"
                else:
                    port_scan_failures.append({
                        "port": port,
                        "error": f"No service listening on port {port}",
                        "result_code": result
                    })
                    
            except Exception as e:
                port_scan_failures.append({
                    "port": port, 
                    "error": f"Port scan failed: {e}"
                })
        
        # This test SHOULD FAIL - we expect no services listening
        assert len(port_scan_failures) > 0, (
            f"Expected backend service to be NOT listening on expected ports, "
            f"but found services on ports: {list(listening_services.keys())}. "
            f"If backend is running correctly, this indicates the connection "
            f"issue is in proxy configuration, not service availability."
        )
        
        # Verify all expected ports are unavailable (reproducing the ECONNREFUSED)
        assert len(port_scan_failures) == len(expected_ports), (
            f"Expected ALL backend ports to be unavailable (explaining ECONNREFUSED), "
            f"but {len(listening_services)} out of {len(expected_ports)} ports "
            f"have listening services: {listening_services}. "
            f"Port failures: {port_scan_failures}"
        )

    @staging_only
    @env_requires(services=["frontend"])
    @pytest.mark.e2e
    def test_docker_container_network_isolation_issue(self):
        """Test Docker container network isolation causing connection failures.
        
        This reproduces the specific Docker network issue where frontend
        container cannot reach backend container at 172.18.0.6:8000.
        
        This test should FAIL, showing network configuration problems.
        """
        # These are the actual IPs and errors from the Docker audit report
        docker_backend_ip = "172.18.0.6"  # From audit: "172.18.0.6:8000"
        docker_network_port = 8000
        
        # Simulate the frontend container trying to reach backend container
        container_backend_url = f"http://{docker_backend_ip}:{docker_network_port}"
        
        network_test_urls = [
            f"{container_backend_url}/health",
            f"{container_backend_url}/api/mcp/servers",  # Exact failing endpoint
            f"{container_backend_url}/api/mcp/tools",    # Exact failing endpoint
        ]
        
        network_failures = []
        
        for test_url in network_test_urls:
            try:
                # This will fail in broken Docker network setup
                response = requests.get(test_url, timeout=3.0)
                
                # If we get here, network is working (unexpected)
                assert response.status_code < 500, (
                    f"Docker network connected to {test_url} but got server error "
                    f"{response.status_code}. Expected: Network connection failure."
                )
                
            except requests.exceptions.ConnectionError as e:
                # This is the EXPECTED failure - Docker network isolation
                network_failures.append({
                    "url": test_url,
                    "error": str(e),
                    "expected": "Docker container network isolation"
                })
                
            except requests.exceptions.Timeout:
                network_failures.append({
                    "url": test_url,
                    "error": "Network timeout", 
                    "expected": "Docker network routing issue"
                })
        
        # This test SHOULD FAIL - demonstrating the Docker network issue
        assert len(network_failures) == len(network_test_urls), (
            f"Expected ALL Docker network connections to fail (like in audit), "
            f"but {len(network_test_urls) - len(network_failures)} succeeded. "
            f"Network failures: {network_failures}. "
            f"If some connections work, the Docker network configuration "
            f"may be partially fixed but still inconsistent."
        )
        
        # Verify we get connection refused errors specifically
        connection_refused_count = sum(
            1 for f in network_failures 
            if "refused" in f["error"].lower() or "econnrefused" in f["error"].lower()
        )
        
        assert connection_refused_count >= 1, (
            f"Expected at least 1 'connection refused' error from Docker network, "
            f"but got {connection_refused_count}. This indicates a different "
            f"type of network failure than seen in the audit logs."
        )

    @staging_only
    @pytest.mark.e2e
    def test_next_js_api_rewrites_configuration_broken(self):
        """Test Next.js API rewrites configuration causing proxy failures.
        
        This test should FAIL, showing that Next.js API rewrites are 
        misconfigured and cannot reach the backend service.
        """
        # Test the Next.js API rewrites that are failing
        frontend_proxy_urls = [
            "http://localhost:3000/api/mcp/servers",   # Proxy endpoint
            "http://localhost:3000/api/mcp/tools",     # Proxy endpoint  
            "http://localhost:3000/api/health",        # Proxy endpoint
        ]
        
        proxy_failures = []
        
        for proxy_url in frontend_proxy_urls:
            try:
                # Test the frontend proxy endpoints
                response = requests.get(proxy_url, timeout=5.0)
                
                # Check for proxy-specific error responses
                if response.status_code >= 500:
                    proxy_failures.append({
                        "url": proxy_url,
                        "status_code": response.status_code,
                        "error": f"Proxy server error: {response.status_code}",
                        "response_text": response.text[:200]  # First 200 chars
                    })
                elif response.status_code == 404:
                    proxy_failures.append({
                        "url": proxy_url,
                        "status_code": 404,
                        "error": "Proxy route not found - API rewrite misconfigured"
                    })
                    
            except requests.exceptions.ConnectionError as e:
                proxy_failures.append({
                    "url": proxy_url,
                    "error": f"Frontend proxy connection failed: {e}",
                    "type": "CONNECTION_ERROR"
                })
                
            except requests.exceptions.Timeout:
                proxy_failures.append({
                    "url": proxy_url,
                    "error": "Frontend proxy timeout - backend unreachable", 
                    "type": "TIMEOUT"
                })
        
        # This test SHOULD FAIL - showing Next.js proxy issues
        assert len(proxy_failures) > 0, (
            f"Expected Next.js API proxy failures (like in audit), "
            f"but all {len(frontend_proxy_urls)} proxy endpoints worked. "
            f"Either the proxy configuration has been fixed, or frontend "
            f"is not running in the expected configuration."
        )
        
        # Check for specific proxy error patterns from the audit
        backend_connection_errors = [
            f for f in proxy_failures
            if "connection" in f["error"].lower() or f.get("type") == "CONNECTION_ERROR"
        ]
        
        assert len(backend_connection_errors) >= 1, (
            f"Expected at least 1 backend connection error from Next.js proxy, "
            f"but got {len(backend_connection_errors)}. "
            f"All proxy failures: {proxy_failures}. "
            f"This suggests a different type of proxy issue than found in audit."
        )

    @staging_only
    @pytest.mark.e2e
    async def test_multiple_backend_connection_attempts_all_fail(self):
        """Test that multiple rapid backend connections all fail with ECONNREFUSED.
        
        This reproduces the pattern from the audit where multiple consecutive
        connection attempts all failed within seconds of each other.
        
        This test should FAIL with a pattern of connection failures.
        """
        backend_base_url = "http://127.0.0.1:8000"
        test_endpoints = [
            "/api/mcp/servers",
            "/api/mcp/tools", 
            "/api/health",
            "/api/threads",
            "/api/status"
        ]
        
        # Rapid-fire connection attempts (like in audit logs)
        connection_attempts = []
        
        for i in range(3):  # Multiple attempts like in audit
            attempt_failures = []
            
            for endpoint in test_endpoints:
                full_url = f"{backend_base_url}{endpoint}"
                
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=1.5)
                    ) as session:
                        async with session.get(full_url) as response:
                            # Successful connection (unexpected in broken state)
                            pass
                            
                except aiohttp.ClientConnectorError as e:
                    attempt_failures.append({
                        "attempt": i + 1,
                        "endpoint": endpoint,
                        "url": full_url, 
                        "error": str(e),
                        "expected": "ECONNREFUSED like audit logs"
                    })
                except Exception as e:
                    attempt_failures.append({
                        "attempt": i + 1,
                        "endpoint": endpoint,
                        "url": full_url,
                        "error": f"Unexpected error: {e}"
                    })
            
            connection_attempts.append(attempt_failures)
            
            # Small delay between attempts (matching audit timing)
            await asyncio.sleep(0.5)
        
        # This test SHOULD FAIL - expecting consistent connection failures
        total_failures = sum(len(attempt) for attempt in connection_attempts)
        expected_failures = len(test_endpoints) * 3  # 3 attempts * 5 endpoints
        
        assert total_failures >= expected_failures * 0.8, (
            f"Expected consistent connection failures across attempts "
            f"(like in audit), but only {total_failures} out of "
            f"{expected_failures} connection attempts failed. "
            f"Connection attempts: {connection_attempts}. "
            f"This suggests backend availability is inconsistent."
        )
        
        # Verify ECONNREFUSED error pattern consistency
        econnrefused_count = 0
        for attempt in connection_attempts:
            for failure in attempt:
                if "refused" in failure["error"].lower():
                    econnrefused_count += 1
        
        assert econnrefused_count >= total_failures * 0.5, (
            f"Expected at least 50% of failures to be ECONNREFUSED errors "
            f"(matching audit pattern), but only {econnrefused_count} out of "
            f"{total_failures} were connection refused errors. "
            f"This indicates a different failure mode than in the audit."
        )
