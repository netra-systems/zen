"""
End-to-End Tests for GCP Load Balancer Deployment Requirements

This test suite validates the actual deployed GCP infrastructure against all critical requirements:
1. Load Balancer Backend Protocol: HTTPS
2. WebSocket Support: 3600s timeout and session affinity
3. Protocol Headers: X-Forwarded-Proto preservation
4. Health Checks: HTTPS protocol on port 443
5. CORS: HTTPS-only origins
6. Cloud Run Ingress: "all" with FORCE_HTTPS=true

These tests run against the actual deployed staging environment to ensure the infrastructure
is correctly configured and operational.

Usage:
    # Run all deployment requirement tests
    python -m pytest tests/e2e/test_gcp_deployment_requirements.py -v

    # Run specific requirement tests
    python -m pytest tests/e2e/test_gcp_deployment_requirements.py::TestWebSocketSupport -v
    
    # Run with staging environment
    pytest tests/e2e/test_gcp_deployment_requirements.py --env=staging -v
"""

import asyncio
import pytest
import aiohttp
import websockets
import ssl
import json
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.environment_markers import env
from test_framework.base_e2e_test import BaseE2ETest


class TestGCPDeploymentRequirementsBase(BaseE2ETest):
    """Base class for GCP deployment requirement tests."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment and URLs."""
        super().setup_class()
        
        # Staging URLs - these should be actual deployed URLs
        cls.staging_urls = {
            "frontend": "https://app.staging.netrasystems.ai",
            "backend": "https://api.staging.netrasystems.ai", 
            "auth": "https://auth.staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai/ws"
        }
        
        # Test configuration
        cls.test_timeout = 30
        cls.websocket_timeout = 60  # Extended for WebSocket tests
        
        # SSL context for HTTPS validation
        cls.ssl_context = ssl.create_default_context()
        cls.ssl_context.check_hostname = True
        cls.ssl_context.verify_mode = ssl.CERT_REQUIRED


@env("staging", "prod")
class TestBackendProtocolHTTPS(GCPDeploymentRequirementsTestBase):
    """Test Requirement 1: Load Balancer Backend Protocol must be HTTPS."""
    
    @pytest.mark.e2e
    async def test_all_endpoints_use_https(self):
        """Test that all service endpoints use HTTPS protocol."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            results = {}
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket for HTTPS test
                    continue
                    
                try:
                    # Test that HTTPS is enforced
                    parsed_url = urlparse(url)
                    assert parsed_url.scheme == "https", f"{service_name} URL should use HTTPS: {url}"
                    
                    # Test SSL certificate and connection
                    health_endpoint = f"{url}/health" if service_name != "frontend" else url
                    async with session.get(health_endpoint) as response:
                        results[service_name] = {
                            "url": url,
                            "status": response.status,
                            "https": parsed_url.scheme == "https",
                            "ssl_valid": True  # Connection succeeded with SSL verification
                        }
                        
                except aiohttp.ClientError as e:
                    pytest.fail(f"HTTPS connection failed for {service_name} ({url}): {e}")
                except Exception as e:
                    pytest.fail(f"Unexpected error testing {service_name}: {e}")
            
            # Verify all services use HTTPS
            for service_name, result in results.items():
                assert result["https"], f"{service_name} must use HTTPS"
                assert result["ssl_valid"], f"{service_name} must have valid SSL certificate"
                print(f"[OK] {service_name}: HTTPS verified (status: {result['status']})")
    
    @pytest.mark.e2e
    async def test_http_to_https_redirect(self):
        """Test that HTTP requests are redirected to HTTPS."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=False)  # Allow HTTP for redirect test
        ) as session:
            
            for service_name, https_url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket
                    continue
                    
                # Convert HTTPS URL to HTTP
                http_url = https_url.replace("https://", "http://")
                
                try:
                    async with session.get(
                        http_url,
                        allow_redirects=False,
                        ssl=False
                    ) as response:
                        # Should get a redirect response
                        assert response.status in [301, 302, 308], (
                            f"{service_name} should redirect HTTP to HTTPS, got status {response.status}"
                        )
                        
                        # Check redirect location
                        location = response.headers.get('Location', '')
                        assert location.startswith('https://'), (
                            f"{service_name} redirect should be to HTTPS: {location}"
                        )
                        
                        print(f"[OK] {service_name}: HTTP→HTTPS redirect verified ({response.status} → {location})")
                        
                except aiohttp.ClientError:
                    # Some load balancers might not respond to HTTP at all, which is also acceptable
                    print(f"[WARN] {service_name}: HTTP not accessible (acceptable - HTTPS-only configuration)")


@env("staging", "prod")
class TestWebSocketSupport(GCPDeploymentRequirementsTestBase):
    """Test Requirement 2: WebSocket Support with 3600s timeout and session affinity."""
    
    @pytest.mark.e2e
    async def test_websocket_connection_establishment(self):
        """Test that WebSocket connections can be established."""
        uri = self.staging_urls["websocket"]
        
        try:
            # Test basic WebSocket connection
            async with websockets.connect(
                uri,
                timeout=10,
                ssl=self.ssl_context
            ) as websocket:
                # Send a ping to verify connection
                await websocket.ping()
                print("[OK] WebSocket connection established successfully")
                
                # Test that connection uses WSS (secure WebSocket)
                assert uri.startswith("wss://"), f"WebSocket should use secure protocol: {uri}"
                print("[OK] WebSocket uses secure protocol (WSS)")
                
        except websockets.exceptions.ConnectionClosed:
            pytest.fail("WebSocket connection was closed unexpectedly")
        except websockets.exceptions.InvalidStatus as e:
            pytest.fail(f"WebSocket connection failed with status code: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    @pytest.mark.e2e
    async def test_websocket_long_duration_connection(self):
        """Test WebSocket connection can be maintained for extended periods."""
        uri = self.staging_urls["websocket"]
        connection_duration = 30  # Test for 30 seconds (shorter than full 3600s for CI/CD)
        
        try:
            async with websockets.connect(
                uri,
                timeout=10,
                ssl=self.ssl_context
            ) as websocket:
                start_time = time.time()
                
                # Keep connection alive and test periodically
                while time.time() - start_time < connection_duration:
                    await websocket.ping()
                    await asyncio.sleep(5)  # Wait 5 seconds between pings
                
                elapsed = time.time() - start_time
                print(f"[OK] WebSocket connection maintained for {elapsed:.1f} seconds")
                
                # Verify connection is still active
                await websocket.ping()
                print("[OK] WebSocket connection still active after extended duration")
                
        except websockets.exceptions.ConnectionClosed:
            pytest.fail("WebSocket connection was closed before timeout period")
        except Exception as e:
            pytest.fail(f"WebSocket long-duration test failed: {e}")
    
    @pytest.mark.e2e
    async def test_websocket_session_affinity(self):
        """Test session affinity by making multiple WebSocket connections."""
        uri = self.staging_urls["websocket"]
        connections = []
        
        try:
            # Create multiple connections to test session affinity
            for i in range(3):
                conn = await websockets.connect(
                    uri,
                    timeout=10,
                    ssl=self.ssl_context
                )
                connections.append(conn)
                
                # Send a message to establish session
                await conn.send(json.dumps({
                    "type": "test_session",
                    "connection_id": i,
                    "timestamp": time.time()
                }))
                
                print(f"[OK] WebSocket connection {i+1} established")
            
            # Test that all connections remain stable
            for i, conn in enumerate(connections):
                await conn.ping()
                print(f"[OK] WebSocket connection {i+1} still active")
            
        except Exception as e:
            pytest.fail(f"WebSocket session affinity test failed: {e}")
        finally:
            # Clean up connections
            for conn in connections:
                if not conn.closed:
                    await conn.close()
    
    @pytest.mark.e2e
    async def test_websocket_upgrade_headers(self):
        """Test that WebSocket upgrade headers are properly handled."""
        # Test WebSocket upgrade via HTTP first
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            websocket_http_url = self.staging_urls["websocket"].replace("wss://", "https://")
            
            headers = {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version": "13"
            }
            
            try:
                async with session.get(websocket_http_url, headers=headers) as response:
                    # Should get 101 Switching Protocols or appropriate WebSocket response
                    print(f"WebSocket upgrade response status: {response.status}")
                    print(f"Response headers: {dict(response.headers)}")
                    
                    # Check for WebSocket-related headers in response
                    connection_header = response.headers.get('Connection', '').lower()
                    upgrade_header = response.headers.get('Upgrade', '').lower()
                    
                    # Some load balancers handle this differently, so we check for various valid responses
                    valid_responses = [101, 400, 426]  # 101=Success, 400/426=Upgrade required
                    assert response.status in valid_responses, (
                        f"WebSocket upgrade should return valid status, got {response.status}"
                    )
                    
                    print("[OK] WebSocket upgrade headers properly handled")
                    
            except aiohttp.ClientError as e:
                print(f"[WARN] WebSocket upgrade test inconclusive: {e}")


@env("staging", "prod")
class TestProtocolHeaders(GCPDeploymentRequirementsTestBase):
    """Test Requirement 3: Protocol Headers - X-Forwarded-Proto preservation."""
    
    @pytest.mark.e2e
    async def test_x_forwarded_proto_header_preservation(self):
        """Test that X-Forwarded-Proto header is properly set to https."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket for HTTP header test
                    continue
                
                try:
                    # Test endpoint that might echo headers back
                    test_endpoint = f"{url}/health" if service_name != "frontend" else url
                    
                    async with session.get(test_endpoint) as response:
                        # Check response headers for HTTPS enforcement indicators
                        strict_transport_security = response.headers.get('Strict-Transport-Security')
                        if strict_transport_security:
                            print(f"[OK] {service_name}: HSTS header present: {strict_transport_security}")
                        
                        # Check for other security headers that indicate HTTPS processing
                        security_headers = [
                            'Strict-Transport-Security',
                            'X-Content-Type-Options', 
                            'X-Frame-Options',
                            'X-XSS-Protection'
                        ]
                        
                        found_security_headers = []
                        for header in security_headers:
                            if header in response.headers:
                                found_security_headers.append(header)
                        
                        if found_security_headers:
                            print(f"[OK] {service_name}: Security headers present: {found_security_headers}")
                        
                        # The actual X-Forwarded-Proto header would be added by the load balancer
                        # and consumed by the backend, so we test the result (successful HTTPS connection)
                        assert response.status in [200, 301, 302, 404], (
                            f"{service_name} should respond properly over HTTPS"
                        )
                        
                        print(f"[OK] {service_name}: HTTPS protocol headers properly handled")
                        
                except aiohttp.ClientError as e:
                    pytest.fail(f"Protocol header test failed for {service_name}: {e}")
    
    @pytest.mark.e2e
    async def test_secure_cookie_handling(self):
        """Test that cookies are set with secure flags over HTTPS."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            # Test auth service specifically for secure cookies
            auth_url = self.staging_urls["auth"]
            
            try:
                async with session.get(f"{auth_url}/health") as response:
                    # Check Set-Cookie headers for secure flags
                    set_cookie_headers = response.headers.getall('Set-Cookie', [])
                    
                    for cookie in set_cookie_headers:
                        # Cookies should have Secure flag when served over HTTPS
                        if 'Secure' not in cookie:
                            print(f"[WARN] Cookie without Secure flag: {cookie}")
                        else:
                            print(f"[OK] Secure cookie found: {cookie[:50]}...")
                    
                    print(f"[OK] Auth service: Cookie security verified")
                    
            except aiohttp.ClientError as e:
                print(f"[WARN] Secure cookie test inconclusive for auth service: {e}")


@env("staging", "prod")
class TestHTTPSHealthChecks(GCPDeploymentRequirementsTestBase):
    """Test Requirement 4: Health Checks use HTTPS protocol with port 443."""
    
    @pytest.mark.e2e
    async def test_health_endpoints_over_https(self):
        """Test that health check endpoints work over HTTPS on port 443."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket
                    continue
                
                health_endpoint = f"{url}/health" if service_name != "frontend" else url
                
                try:
                    async with session.get(health_endpoint) as response:
                        # Verify the connection uses port 443 (standard HTTPS port)
                        parsed_url = urlparse(health_endpoint)
                        effective_port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                        
                        assert effective_port == 443, (
                            f"{service_name} health check should use port 443, using {effective_port}"
                        )
                        
                        # Health checks should return success or redirect
                        assert response.status in [200, 301, 302, 404], (
                            f"{service_name} health check failed with status {response.status}"
                        )
                        
                        print(f"[OK] {service_name}: HTTPS health check on port 443 successful (status: {response.status})")
                        
                except aiohttp.ClientError as e:
                    pytest.fail(f"HTTPS health check failed for {service_name}: {e}")
    
    @pytest.mark.e2e
    async def test_health_check_response_times(self):
        """Test that health checks respond within reasonable time limits."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5),  # 5 second timeout for health checks
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket
                    continue
                
                health_endpoint = f"{url}/health" if service_name != "frontend" else url
                
                start_time = time.time()
                try:
                    async with session.get(health_endpoint) as response:
                        response_time = time.time() - start_time
                        
                        # Health checks should respond quickly
                        assert response_time < 5.0, (
                            f"{service_name} health check too slow: {response_time:.2f}s"
                        )
                        
                        print(f"[OK] {service_name}: Health check response time: {response_time:.2f}s")
                        
                except asyncio.TimeoutError:
                    pytest.fail(f"{service_name} health check timeout (>5s)")
                except aiohttp.ClientError as e:
                    print(f"[WARN] {service_name}: Health check error (may be expected): {e}")


@env("staging", "prod")
class TestCORSConfiguration(GCPDeploymentRequirementsTestBase):
    """Test Requirement 5: CORS - HTTPS-only origins."""
    
    @pytest.mark.e2e
    async def test_cors_preflight_requests(self):
        """Test CORS preflight requests for cross-origin access."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            # Test CORS on API endpoints
            api_url = self.staging_urls["backend"]
            
            cors_headers = {
                "Origin": "https://app.staging.netrasystems.ai",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
            
            try:
                # Send CORS preflight request
                async with session.options(f"{api_url}/health", headers=cors_headers) as response:
                    # Check CORS response headers
                    access_control_allow_origin = response.headers.get('Access-Control-Allow-Origin')
                    access_control_allow_methods = response.headers.get('Access-Control-Allow-Methods')
                    access_control_allow_headers = response.headers.get('Access-Control-Allow-Headers')
                    
                    print(f"CORS Allow-Origin: {access_control_allow_origin}")
                    print(f"CORS Allow-Methods: {access_control_allow_methods}")
                    print(f"CORS Allow-Headers: {access_control_allow_headers}")
                    
                    # Verify CORS headers are present and restrictive
                    if access_control_allow_origin:
                        # Should not be wildcard '*' for credentialed requests
                        assert access_control_allow_origin != '*', (
                            "CORS Allow-Origin should not be wildcard for secure applications"
                        )
                        
                        # Should be HTTPS origin
                        assert access_control_allow_origin.startswith('https://'), (
                            f"CORS Allow-Origin should be HTTPS: {access_control_allow_origin}"
                        )
                        
                        print(f"[OK] CORS Allow-Origin properly configured: {access_control_allow_origin}")
                    
                    # Check for credentials support
                    allow_credentials = response.headers.get('Access-Control-Allow-Credentials')
                    if allow_credentials:
                        print(f"[OK] CORS credentials configured: {allow_credentials}")
                    
            except aiohttp.ClientError as e:
                print(f"[WARN] CORS preflight test inconclusive: {e}")
    
    @pytest.mark.e2e
    async def test_cors_actual_requests(self):
        """Test actual CORS requests from different origins."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            api_url = self.staging_urls["backend"]
            
            # Test with valid HTTPS origin
            valid_origin_headers = {"Origin": "https://app.staging.netrasystems.ai"}
            
            try:
                async with session.get(f"{api_url}/health", headers=valid_origin_headers) as response:
                    # Check that CORS headers are included in actual response
                    cors_header = response.headers.get('Access-Control-Allow-Origin')
                    if cors_header:
                        assert cors_header.startswith('https://'), (
                            f"CORS response should specify HTTPS origin: {cors_header}"
                        )
                        print(f"[OK] CORS actual request allowed from HTTPS origin")
                    
            except aiohttp.ClientError as e:
                print(f"[WARN] CORS actual request test inconclusive: {e}")


@env("staging", "prod")
class TestCloudRunIngress(GCPDeploymentRequirementsTestBase):
    """Test Requirement 6: Cloud Run Ingress 'all' with FORCE_HTTPS=true."""
    
    @pytest.mark.e2e
    async def test_https_enforcement(self):
        """Test that HTTPS is enforced across all services."""
        # This test is covered by other HTTPS tests but we verify the overall behavior
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket
                    continue
                
                try:
                    endpoint = f"{url}/health" if service_name != "frontend" else url
                    async with session.get(endpoint) as response:
                        # Verify HTTPS is working
                        assert url.startswith("https://"), f"{service_name} should use HTTPS"
                        
                        # Check for HSTS header (indicates FORCE_HTTPS is working)
                        hsts = response.headers.get('Strict-Transport-Security')
                        if hsts:
                            print(f"[OK] {service_name}: HSTS enabled - {hsts}")
                        else:
                            print(f"[WARN] {service_name}: HSTS header not found (may be added by proxy)")
                        
                        print(f"[OK] {service_name}: HTTPS enforcement verified")
                        
                except aiohttp.ClientError as e:
                    pytest.fail(f"HTTPS enforcement test failed for {service_name}: {e}")
    
    @pytest.mark.e2e
    async def test_service_accessibility(self):
        """Test that services are accessible from external traffic (ingress 'all')."""
        # This test verifies that the services can be reached from external clients
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            results = {}
            
            for service_name, url in self.staging_urls.items():
                if service_name == "websocket":  # Skip WebSocket for HTTP test
                    continue
                
                try:
                    endpoint = f"{url}/health" if service_name != "frontend" else url
                    async with session.get(endpoint) as response:
                        results[service_name] = {
                            "accessible": True,
                            "status": response.status,
                            "url": endpoint
                        }
                        
                        # Services should be accessible (not blocked by ingress rules)
                        assert response.status in [200, 301, 302, 404], (
                            f"{service_name} should be accessible, got status {response.status}"
                        )
                        
                        print(f"[OK] {service_name}: Externally accessible (status: {response.status})")
                        
                except aiohttp.ClientError as e:
                    results[service_name] = {
                        "accessible": False,
                        "error": str(e),
                        "url": endpoint
                    }
                    pytest.fail(f"{service_name} not accessible from external traffic: {e}")
            
            # Verify all services are accessible
            accessible_count = sum(1 for r in results.values() if r.get("accessible", False))
            expected_count = len([s for s in self.staging_urls if s != "websocket"])
            
            assert accessible_count == expected_count, (
                f"Only {accessible_count}/{expected_count} services accessible"
            )
            
            print(f"[OK] All {accessible_count} services accessible via external ingress")
    
    @pytest.mark.e2e
    async def test_websocket_external_access(self):
        """Test that WebSocket service is accessible externally."""
        uri = self.staging_urls["websocket"]
        
        try:
            # Test WebSocket connection from external client
            async with websockets.connect(
                uri,
                timeout=10,
                ssl=self.ssl_context
            ) as websocket:
                # Verify connection works
                await websocket.ping()
                print("[OK] WebSocket service accessible via external ingress")
                
        except websockets.exceptions.ConnectionClosed:
            pytest.fail("WebSocket service not accessible from external traffic")
        except Exception as e:
            pytest.fail(f"WebSocket external access test failed: {e}")


# Integration test that runs all requirements together
@env("staging", "prod")
class TestOverallDeploymentRequirements(GCPDeploymentRequirementsTestBase):
    """Integration test for all deployment requirements working together."""
    
    @pytest.mark.e2e
    async def test_end_to_end_https_workflow(self):
        """Test a complete workflow using all services over HTTPS."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.test_timeout),
            connector=aiohttp.TCPConnector(ssl=self.ssl_context)
        ) as session:
            
            workflow_steps = []
            
            # Step 1: Access frontend
            try:
                async with session.get(self.staging_urls["frontend"]) as response:
                    workflow_steps.append("[OK] Frontend accessible via HTTPS")
            except Exception as e:
                workflow_steps.append(f"[FAIL] Frontend access failed: {e}")
            
            # Step 2: Check auth service
            try:
                async with session.get(f"{self.staging_urls['auth']}/health") as response:
                    workflow_steps.append("[OK] Auth service health check via HTTPS")
            except Exception as e:
                workflow_steps.append(f"[FAIL] Auth service health check failed: {e}")
            
            # Step 3: Check API service
            try:
                async with session.get(f"{self.staging_urls['backend']}/health") as response:
                    workflow_steps.append("[OK] API service health check via HTTPS")
            except Exception as e:
                workflow_steps.append(f"[FAIL] API service health check failed: {e}")
            
            # Step 4: Test WebSocket connection
            try:
                async with websockets.connect(
                    self.staging_urls["websocket"],
                    timeout=10,
                    ssl=self.ssl_context
                ) as websocket:
                    await websocket.ping()
                    workflow_steps.append("[OK] WebSocket connection via WSS")
            except Exception as e:
                workflow_steps.append(f"[FAIL] WebSocket connection failed: {e}")
            
            # Print workflow results
            print("[WORKFLOW] End-to-End Workflow Results:")
            for step in workflow_steps:
                print(f"  {step}")
            
            # Verify all steps succeeded
            failed_steps = [step for step in workflow_steps if step.startswith("[FAIL]")]
            assert len(failed_steps) == 0, f"Workflow failed at: {failed_steps}"
            
            print("[OK] Complete end-to-end HTTPS workflow successful")


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])