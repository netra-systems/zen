"""
GCP Load Balancer Header Forwarding Test - Infrastructure Validation

CRITICAL INFRASTRUCTURE VALIDATION: This test validates that WebSocket connections
through GCP Load Balancer properly forward authentication headers to backend services.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Infrastructure Integrity & Production Readiness
- Business Goal: Ensure auth headers reach backend through GCP staging load balancer
- Value Impact: Validates WebSocket authentication works in production environment
- Strategic Impact: Prevents header stripping issues that break authentication in staging/production

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY real GCP load balancer testing (NO mocks)
2. MANDATORY authentication header validation through infrastructure
3. MANDATORY WebSocket connection through staging GCP environment
4. MANDATORY hard failure when headers are stripped by load balancer
5. MANDATORY clear error messages explaining infrastructure issues
6. Must reproduce header forwarding failures found in staging environment

INFRASTRUCTURE TEST FLOW:
```
GCP Staging Connection  ->  Load Balancer Request  ->  Header Forwarding Check  -> 
Backend Header Validation  ->  WebSocket Authentication  ->  Success/Failure Analysis
```

This reproduces the issue where GCP Load Balancer strips authentication headers,
causing WebSocket connections to fail with authentication errors.
"""

import asyncio
import json
import pytest
import time
import websockets
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - INFRASTRUCTURE FOCUSED
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env


class TestGCPLoadBalancerHeaders(BaseE2ETest):
    """Test GCP Load Balancer header forwarding for WebSocket authentication."""
    
    @pytest.fixture(autouse=True)
    async def setup_infrastructure_test(self):
        """Setup infrastructure test environment."""
        await self.initialize_test_environment()
        
        # Get staging environment configuration
        self.env = get_env()
        self.staging_backend_url = self.env.get("GCP_STAGING_BACKEND_URL", "")
        self.staging_websocket_url = self.env.get("GCP_STAGING_WEBSOCKET_URL", "")
        
        # Hard failure if staging URLs not configured - this is infrastructure validation
        if not self.staging_backend_url or not self.staging_websocket_url:
            pytest.fail(
                "INFRASTRUCTURE CONFIGURATION FAILURE: Staging GCP URLs not configured. "
                "Required environment variables: GCP_STAGING_BACKEND_URL, GCP_STAGING_WEBSOCKET_URL. "
                "This infrastructure test validates production-like load balancer behavior. "
                "Fix required: Configure staging GCP environment URLs for infrastructure testing."
            )
    
    @pytest.mark.infrastructure
    @pytest.mark.real_services  
    @pytest.mark.timeout(60)
    async def test_gcp_load_balancer_forwards_auth_headers(self):
        """
        CRITICAL: Test that GCP Load Balancer forwards authentication headers to backend.
        
        This test validates that WebSocket authentication works through GCP infrastructure
        by verifying that auth headers make it through the load balancer to the backend service.
        """
        self.logger.info("Testing GCP Load Balancer header forwarding for WebSocket auth")
        
        # Step 1: Test direct backend connectivity (bypass load balancer)
        await self._test_backend_health_check()
        
        # Step 2: Test load balancer HTTP header forwarding with detailed validation
        auth_token = await self._get_test_auth_token()
        header_test_results = await self._test_http_header_forwarding_detailed(auth_token)
        
        if not header_test_results["headers_forwarded"]:
            failure_details = header_test_results.get("failure_reason", "Unknown failure")
            response_status = header_test_results.get("response_status", "No response")
            response_headers = header_test_results.get("response_headers", {})
            
            pytest.fail(
                f"CRITICAL INFRASTRUCTURE FAILURE: GCP Load Balancer header forwarding failed. "
                f"Failure details: {failure_details}. "
                f"Response status: {response_status}. "
                f"Response headers: {response_headers}. "
                f"This breaks WebSocket authentication in staging/production environments. "
                f"Fix required: Configure load balancer to preserve Authorization headers."
            )
        
        # Step 3: Test WebSocket connection through load balancer with detailed analysis
        websocket_test_results = await self._test_websocket_through_load_balancer_detailed(auth_token)
        
        if not websocket_test_results["connection_successful"]:
            failure_reason = websocket_test_results.get("failure_reason", "Unknown failure")
            error_code = websocket_test_results.get("error_code", "No error code")
            connection_time = websocket_test_results.get("connection_time", "Unknown")
            
            pytest.fail(
                f"CRITICAL INFRASTRUCTURE FAILURE: WebSocket authentication fails through GCP Load Balancer. "
                f"Failure reason: {failure_reason}. "
                f"Error code: {error_code}. "
                f"Connection attempt duration: {connection_time}s. "
                f"Headers may be forwarded for HTTP but not WebSocket connections. "
                f"Fix required: Configure load balancer WebSocket header preservation."
            )
        
        self.logger.info("SUCCESS: GCP Load Balancer properly forwards auth headers for WebSocket connections")
    
    async def _test_backend_health_check(self):
        """Test direct backend connectivity."""
        self.logger.info("Testing direct backend connectivity...")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self.staging_backend_url}/health") as response:
                    if response.status != 200:
                        pytest.fail(f"Backend health check failed: {response.status}")
                    
                    health_data = await response.json()
                    assert health_data.get("status") == "healthy", f"Backend unhealthy: {health_data}"
                    
        except Exception as e:
            pytest.fail(f"Cannot reach backend directly: {e}")
    
    async def _get_test_auth_token(self) -> str:
        """Get authentication token for testing."""
        self.logger.info("Getting test authentication token...")
        
        # For infrastructure testing, we need a real auth token
        # This could come from environment variables or a test user creation process
        test_token = self.env.get("INFRASTRUCTURE_TEST_AUTH_TOKEN", "")
        
        if not test_token:
            pytest.fail(
                "INFRASTRUCTURE AUTH FAILURE: Infrastructure test auth token not configured. "
                "Required environment variable: INFRASTRUCTURE_TEST_AUTH_TOKEN. "
                "This test validates auth header forwarding through GCP load balancer. "
                "Fix required: Configure valid auth token for infrastructure testing or implement test user creation."
            )
        
        return test_token
    
    async def _test_http_header_forwarding(self, auth_token: str) -> bool:
        """Test that HTTP requests forward auth headers through load balancer."""
        self.logger.info("Testing HTTP header forwarding through load balancer...")
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-Test-Header": "infrastructure-test",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Make authenticated request through load balancer
                async with session.get(
                    f"{self.staging_backend_url}/api/auth/verify",
                    headers=headers
                ) as response:
                    
                    if response.status == 401:
                        self.logger.error("Authentication failed - headers likely stripped by load balancer")
                        return False
                    
                    if response.status == 200:
                        self.logger.info("HTTP headers successfully forwarded through load balancer")
                        return True
                    
                    self.logger.warning(f"Unexpected response status: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"HTTP header forwarding test failed: {e}")
            return False
    
    async def _test_websocket_through_load_balancer(self, auth_token: str) -> bool:
        """Test WebSocket connection through load balancer with auth headers."""
        self.logger.info("Testing WebSocket connection through load balancer...")
        
        # Construct WebSocket URL with auth headers
        websocket_url = self.staging_websocket_url.replace("http", "ws")
        if not websocket_url.endswith("/ws"):
            websocket_url = f"{websocket_url}/ws"
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-Test-Header": "websocket-infrastructure-test"
        }
        
        try:
            # Attempt WebSocket connection through load balancer
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=15
            ) as websocket:
                
                # Send test message to verify connection works
                test_message = {
                    "type": "infrastructure_test",
                    "message": "Testing load balancer WebSocket forwarding",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    self.logger.info(f"WebSocket response received: {response_data}")
                    return True
                    
                except asyncio.TimeoutError:
                    self.logger.error("WebSocket response timeout - connection may be established but not functional")
                    return False
                    
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 1011:
                self.logger.error("WebSocket 1011 error - likely authentication failure due to header stripping")
                return False
            raise
            
        except Exception as e:
            self.logger.error(f"WebSocket connection through load balancer failed: {e}")
            return False
    
    @pytest.mark.infrastructure
    @pytest.mark.real_services
    @pytest.mark.timeout(30)
    async def test_load_balancer_websocket_upgrade_headers(self):
        """
        Test that load balancer properly handles WebSocket upgrade headers.
        
        This test validates WebSocket upgrade negotiation through GCP infrastructure.
        """
        self.logger.info("Testing WebSocket upgrade header handling through load balancer")
        
        websocket_url = self.staging_websocket_url.replace("http", "ws")
        if not websocket_url.endswith("/ws"):
            websocket_url = f"{websocket_url}/ws"
        
        # Test WebSocket upgrade headers
        try:
            async with websockets.connect(
                websocket_url,
                timeout=15,
                # Force specific upgrade headers to test load balancer handling
                extra_headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Version": "13",
                    "X-Infrastructure-Test": "websocket-upgrade"
                }
            ) as websocket:
                
                # Connection successful
                self.logger.info("WebSocket upgrade successful through load balancer")
                
                # Send ping to verify bidirectional communication
                await websocket.ping()
                
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 404:
                pytest.fail("WebSocket endpoint not found - load balancer routing issue")
            elif e.status_code == 502:
                pytest.fail("Bad Gateway - load balancer cannot reach backend WebSocket service")
            elif e.status_code == 503:
                pytest.fail("Service Unavailable - backend WebSocket service down or overloaded")
            else:
                pytest.fail(f"WebSocket upgrade failed with status {e.status_code} - infrastructure issue")
                
        except Exception as e:
            pytest.fail(f"WebSocket upgrade through load balancer failed: {e}")
    
    async def _test_http_header_forwarding_detailed(self, auth_token: str) -> Dict[str, Any]:
        """Test HTTP header forwarding with detailed result analysis."""
        self.logger.info("Testing HTTP header forwarding through load balancer with detailed analysis...")
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-Test-Header": "infrastructure-test",
            "X-Request-ID": f"test-{int(time.time())}",
            "Content-Type": "application/json"
        }
        
        result = {
            "headers_forwarded": False,
            "response_status": None,
            "response_headers": {},
            "failure_reason": None,
            "request_time": None
        }
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                # Make authenticated request through load balancer
                async with session.get(
                    f"{self.staging_backend_url}/api/auth/verify",
                    headers=headers
                ) as response:
                    
                    result["request_time"] = time.time() - start_time
                    result["response_status"] = response.status
                    result["response_headers"] = dict(response.headers)
                    
                    if response.status == 401:
                        result["failure_reason"] = "Authentication failed - headers likely stripped by load balancer"
                        return result
                    
                    if response.status == 200:
                        # Verify response contains auth verification data
                        try:
                            response_data = await response.json()
                            if response_data.get("authenticated") or response_data.get("user"):
                                result["headers_forwarded"] = True
                                result["failure_reason"] = None
                            else:
                                result["failure_reason"] = "Auth verification endpoint returned 200 but no auth data"
                        except Exception as json_error:
                            result["failure_reason"] = f"Could not parse auth verification response: {json_error}"
                        return result
                    
                    if response.status == 404:
                        result["failure_reason"] = "Auth verification endpoint not found - routing issue"
                        return result
                    
                    if response.status >= 500:
                        result["failure_reason"] = f"Backend server error: {response.status}"
                        return result
                    
                    result["failure_reason"] = f"Unexpected response status: {response.status}"
                    return result
                    
        except asyncio.TimeoutError:
            result["failure_reason"] = "Request timeout - load balancer or backend not responding"
        except Exception as e:
            result["failure_reason"] = f"HTTP header forwarding test failed: {e}"
            
        return result
    
    async def _test_websocket_through_load_balancer_detailed(self, auth_token: str) -> Dict[str, Any]:
        """Test WebSocket connection through load balancer with detailed analysis."""
        self.logger.info("Testing WebSocket connection through load balancer with detailed analysis...")
        
        # Construct WebSocket URL with auth headers
        websocket_url = self.staging_websocket_url.replace("http", "ws")
        if not websocket_url.endswith("/ws"):
            websocket_url = f"{websocket_url}/ws"
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-Test-Header": "websocket-infrastructure-test",
            "X-Request-ID": f"ws-test-{int(time.time())}"
        }
        
        result = {
            "connection_successful": False,
            "failure_reason": None,
            "error_code": None,
            "connection_time": None,
            "response_received": False,
            "response_data": None
        }
        
        try:
            start_time = time.time()
            
            # Attempt WebSocket connection through load balancer
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=15
            ) as websocket:
                
                result["connection_time"] = time.time() - start_time
                
                # Send test message to verify connection works
                test_message = {
                    "type": "infrastructure_test",
                    "message": "Testing load balancer WebSocket forwarding",
                    "request_id": headers["X-Request-ID"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    result["response_received"] = True
                    result["response_data"] = json.loads(response)
                    result["connection_successful"] = True
                    
                    self.logger.info(f"WebSocket response received: {result['response_data']}")
                    
                except asyncio.TimeoutError:
                    result["failure_reason"] = "WebSocket response timeout - connection established but not functional"
                    result["connection_time"] = time.time() - start_time
                except json.JSONDecodeError as json_error:
                    result["failure_reason"] = f"Invalid JSON response: {json_error}"
                    result["response_data"] = response
                    
        except websockets.exceptions.ConnectionClosedError as e:
            result["connection_time"] = time.time() - start_time
            result["error_code"] = e.code
            
            if e.code == 1011:
                result["failure_reason"] = "WebSocket 1011 error - likely authentication failure due to header stripping"
            elif e.code == 1008:
                result["failure_reason"] = "WebSocket 1008 error - policy violation, possibly auth-related"
            elif e.code == 1006:
                result["failure_reason"] = "WebSocket 1006 error - abnormal closure, possibly infrastructure issue"
            else:
                result["failure_reason"] = f"WebSocket connection closed with code {e.code}"
                
        except websockets.exceptions.InvalidStatusCode as e:
            result["connection_time"] = time.time() - start_time
            result["error_code"] = e.status_code
            
            if e.status_code == 404:
                result["failure_reason"] = "WebSocket endpoint not found - load balancer routing issue"
            elif e.status_code == 502:
                result["failure_reason"] = "Bad Gateway - load balancer cannot reach backend WebSocket service"
            elif e.status_code == 503:
                result["failure_reason"] = "Service Unavailable - backend WebSocket service down or overloaded"
            else:
                result["failure_reason"] = f"WebSocket upgrade failed with HTTP {e.status_code}"
                
        except asyncio.TimeoutError:
            result["connection_time"] = time.time() - start_time
            result["failure_reason"] = "WebSocket connection timeout - load balancer or backend not responding"
            
        except Exception as e:
            result["connection_time"] = time.time() - start_time
            result["failure_reason"] = f"WebSocket connection through load balancer failed: {e}"
            
        return result
    
    @pytest.mark.infrastructure
    @pytest.mark.real_services
    @pytest.mark.timeout(45)
    async def test_load_balancer_connection_timeout_handling(self):
        """
        Test load balancer timeout handling for WebSocket connections.
        
        Validates that load balancer doesn't prematurely terminate WebSocket connections.
        """
        self.logger.info("Testing load balancer WebSocket connection timeout handling")
        
        auth_token = await self._get_test_auth_token()
        websocket_url = self.staging_websocket_url.replace("http", "ws")
        if not websocket_url.endswith("/ws"):
            websocket_url = f"{websocket_url}/ws"
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=20
            ) as websocket:
                
                self.logger.info("WebSocket connected - testing timeout handling")
                
                # Keep connection alive for 30 seconds to test load balancer timeout
                start_time = time.time()
                duration = 30  # seconds
                
                while time.time() - start_time < duration:
                    # Send periodic pings to keep connection alive
                    await websocket.ping()
                    await asyncio.sleep(5)
                
                self.logger.info("WebSocket connection maintained through load balancer timeout period")
                
        except websockets.exceptions.ConnectionClosed as e:
            if time.time() - start_time < duration * 0.8:  # Failed before 80% of expected duration
                pytest.fail(
                    f"Load balancer prematurely closed WebSocket connection after {time.time() - start_time:.1f}s. "
                    "Expected to maintain connection for longer period. Check load balancer timeout settings."
                )
        except Exception as e:
            pytest.fail(f"Load balancer timeout test failed: {e}")