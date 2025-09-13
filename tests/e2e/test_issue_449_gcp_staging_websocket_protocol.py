"""
Issue #449 - WebSocket uvicorn middleware stack failures - E2E Staging Tests

PURPOSE: Test real GCP Cloud Run environment WebSocket protocol issues that occur
         when uvicorn middleware stack conflicts with Cloud Run's protocol handling.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality failing in GCP staging due to
                Cloud Run protocol mismatches with uvicorn middleware stack.

E2E SCOPE:
- Real GCP staging environment WebSocket connections
- Cloud Run protocol negotiation with uvicorn
- Load balancer WebSocket upgrade handling  
- Container-level ASGI scope processing
- Real network conditions and timeouts

TEST STRATEGY:
These tests should INITIALLY FAIL to demonstrate the real production issues.
Tests connect to actual GCP staging environment to reproduce failures.
"""

import asyncio
import json
import pytest
import websockets
import requests
import time
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch
from urllib.parse import urljoin
import ssl

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class GCPStagingWebSocketTester:
    """
    Test WebSocket connections against real GCP staging environment.
    
    CRITICAL: This tests the actual production environment where Issue #449
    manifests as uvicorn middleware stack failures in Cloud Run.
    """
    
    def __init__(self):
        env_manager = get_env()
        self.staging_base_url = env_manager.get("STAGING_BASE_URL", "https://netra-backend-staging-00498-ssn.a.run.app")
        self.staging_ws_url = self.staging_base_url.replace("https://", "wss://")
        self.timeout = 30.0  # GCP staging timeout
        self.connection_failures = []
        self.protocol_errors = []
        self.middleware_conflicts = []
    
    async def test_websocket_connection(self, path: str = "/ws") -> Dict[str, Any]:
        """
        Test WebSocket connection to GCP staging environment.
        
        This tests the actual uvicorn middleware stack in Cloud Run.
        """
        full_ws_url = f"{self.staging_ws_url}{path}"
        result = {
            "url": full_ws_url,
            "success": False,
            "error": None,
            "response_time": None,
            "connection_state": None,
            "protocol_version": None,
            "subprotocol": None
        }
        
        start_time = time.time()
        
        try:
            # Configure SSL for GCP staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Test WebSocket connection with subprotocol negotiation
            async with websockets.connect(
                full_ws_url,
                ssl=ssl_context,
                timeout=self.timeout,
                subprotocols=["chat", "graphql-ws"],
                extra_headers={
                    "User-Agent": "Issue-449-Test-Client",
                    "Origin": "https://app.netra.co"
                }
            ) as websocket:
                result["success"] = True
                result["connection_state"] = websocket.state.name
                result["protocol_version"] = websocket.version
                result["subprotocol"] = websocket.subprotocol
                
                # Test basic message exchange
                await websocket.send("test message")
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                result["response"] = response
                
        except websockets.exceptions.InvalidStatus as e:
            # This indicates protocol negotiation failure
            self.protocol_errors.append({
                "error": "Invalid WebSocket status",
                "details": str(e),
                "status_code": getattr(e, 'status_code', None)
            })
            result["error"] = f"Protocol error: {e}"
            
        except websockets.exceptions.ConnectionClosedError as e:
            # This indicates middleware conflicts causing connection drops
            self.middleware_conflicts.append({
                "error": "Connection closed unexpectedly",
                "details": str(e),
                "code": e.code,
                "reason": e.reason
            })
            result["error"] = f"Connection closed: {e.code} {e.reason}"
            
        except asyncio.TimeoutError:
            # This indicates Cloud Run timeout issues
            self.connection_failures.append({
                "error": "Connection timeout",
                "timeout": self.timeout,
                "url": full_ws_url
            })
            result["error"] = "Connection timeout"
            
        except Exception as e:
            # General connection failures
            self.connection_failures.append({
                "error": "General connection failure",
                "details": str(e),
                "url": full_ws_url
            })
            result["error"] = f"Connection failed: {e}"
        
        finally:
            result["response_time"] = time.time() - start_time
        
        return result
    
    def test_http_to_websocket_upgrade(self, path: str = "/ws") -> Dict[str, Any]:
        """
        Test HTTP to WebSocket upgrade process in GCP staging.
        
        This tests uvicorn's protocol transition handling in Cloud Run.
        """
        full_http_url = f"{self.staging_base_url}{path}"
        result = {
            "url": full_http_url,
            "upgrade_attempted": False,
            "upgrade_success": False,
            "response_headers": {},
            "status_code": None,
            "error": None
        }
        
        try:
            # Attempt WebSocket upgrade via HTTP request
            headers = {
                "Connection": "Upgrade",
                "Upgrade": "websocket",
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Protocol": "chat, superchat",
                "Origin": "https://app.netra.co",
                "User-Agent": "Issue-449-Upgrade-Test"
            }
            
            response = requests.get(
                full_http_url,
                headers=headers,
                timeout=self.timeout,
                verify=False  # For staging environment
            )
            
            result["upgrade_attempted"] = True
            result["status_code"] = response.status_code
            result["response_headers"] = dict(response.headers)
            
            # Check if upgrade was successful
            if response.status_code == 101:
                result["upgrade_success"] = True
            elif response.status_code in [426, 400]:
                # These indicate upgrade rejection
                result["error"] = f"Upgrade rejected with {response.status_code}"
            else:
                result["error"] = f"Unexpected status {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            result["error"] = f"HTTP request failed: {e}"
        
        return result
    
    def test_staging_service_availability(self) -> Dict[str, Any]:
        """
        Test staging service availability before WebSocket tests.
        
        This ensures the staging environment is operational.
        """
        health_url = f"{self.staging_base_url}/health"
        result = {
            "service_available": False,
            "health_status": None,
            "response_time": None,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            response = requests.get(
                health_url,
                timeout=self.timeout,
                verify=False
            )
            
            result["health_status"] = response.status_code
            result["service_available"] = response.status_code == 200
            
            if response.status_code == 200:
                result["health_data"] = response.json()
            
        except requests.exceptions.RequestException as e:
            result["error"] = f"Health check failed: {e}"
        
        finally:
            result["response_time"] = time.time() - start_time
        
        return result


class TestIssue449GCPStagingWebSocketProtocol(SSotBaseTestCase):
    """
    E2E tests for Issue #449 - GCP staging WebSocket protocol failures.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to demonstrate
    the real production issues in GCP staging environment.
    """
    
    def setUp(self):
        super().setUp()
        self.gcp_tester = GCPStagingWebSocketTester()
        
        # Check if staging environment is available
        self.staging_available = True
        try:
            health_result = self.gcp_tester.test_staging_service_availability()
            if not health_result["service_available"]:
                self.staging_available = False
                self.skipTest(f"GCP staging not available: {health_result['error']}")
        except Exception as e:
            self.staging_available = False
            self.skipTest(f"Cannot reach GCP staging: {e}")
    
    @pytest.mark.asyncio
    async def test_gcp_staging_websocket_connection_failure(self):
        """
        Test WebSocket connection failures in GCP staging environment.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn middleware
        stack failures in the real GCP Cloud Run environment.
        """
        # Test main WebSocket endpoint
        result = await self.gcp_tester.test_websocket_connection("/ws")
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should connect successfully
        self.assertTrue(
            result["success"],
            f"WebSocket connection should succeed in staging: {result['error']}"
        )
        
        # Additional validations that should fail
        self.assertIsNotNone(result["protocol_version"], "WebSocket protocol version should be negotiated")
        self.assertLess(result["response_time"], 10.0, "WebSocket connection should be fast")
        
        # If we get here, check for protocol issues
        if not result["success"]:
            # Verify we captured the expected failure types
            self.assertGreater(
                len(self.gcp_tester.protocol_errors) + len(self.gcp_tester.middleware_conflicts),
                0,
                "Should have captured protocol or middleware errors"
            )
    
    @pytest.mark.asyncio  
    async def test_gcp_staging_websocket_subprotocol_negotiation_failure(self):
        """
        Test WebSocket subprotocol negotiation failures in GCP staging.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn fails to
        properly negotiate WebSocket subprotocols in Cloud Run.
        """
        # Test WebSocket with subprotocol negotiation
        result = await self.gcp_tester.test_websocket_connection("/ws")
        
        # ASSERTION THAT SHOULD FAIL: subprotocol should be negotiated
        if result["success"]:
            self.assertIsNotNone(
                result["subprotocol"],
                "WebSocket subprotocol should be negotiated in staging"
            )
            self.assertIn(
                result["subprotocol"], 
                ["chat", "graphql-ws"],
                f"Negotiated subprotocol should be valid: {result['subprotocol']}"
            )
        else:
            # If connection failed, verify it's a protocol negotiation issue
            error_msg = result["error"].lower()
            self.assertTrue(
                "protocol" in error_msg or "upgrade" in error_msg,
                f"Should be protocol-related failure: {result['error']}"
            )
    
    def test_gcp_staging_http_websocket_upgrade_failure(self):
        """
        Test HTTP to WebSocket upgrade failures in GCP staging.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn's HTTP to
        WebSocket upgrade process fails in Cloud Run middleware stack.
        """
        # Test HTTP to WebSocket upgrade
        result = self.gcp_tester.test_http_to_websocket_upgrade("/ws")
        
        # ASSERTION THAT SHOULD FAIL: upgrade should be successful
        self.assertTrue(
            result["upgrade_success"],
            f"HTTP to WebSocket upgrade should succeed: {result['error']}"
        )
        
        # Additional validations that should fail
        self.assertEqual(
            result["status_code"], 101,
            f"Should get 101 Switching Protocols, got {result['status_code']}"
        )
        
        # Check for proper upgrade headers
        headers = result["response_headers"]
        self.assertIn("upgrade", [k.lower() for k in headers.keys()],
                     "Response should have Upgrade header")
        self.assertIn("connection", [k.lower() for k in headers.keys()],
                     "Response should have Connection header")
    
    @pytest.mark.asyncio
    async def test_gcp_staging_multiple_websocket_connections_failure(self):
        """
        Test multiple concurrent WebSocket connections in GCP staging.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn middleware
        stack cannot handle multiple concurrent WebSocket connections.
        """
        # Test multiple concurrent connections
        connection_tasks = [
            self.gcp_tester.test_websocket_connection(f"/ws?id={i}")
            for i in range(3)  # Test 3 concurrent connections
        ]
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # ASSERTION THAT SHOULD FAIL: all connections should succeed
        successful_connections = [r for r in results if isinstance(r, dict) and r.get("success")]
        self.assertEqual(
            len(successful_connections), 3,
            f"All 3 WebSocket connections should succeed, got {len(successful_connections)}"
        )
        
        # Check for middleware conflicts in failed connections
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get("success")]
        if failed_connections:
            # Verify failures are middleware-related
            error_messages = [r.get("error", "") for r in failed_connections]
            combined_errors = " ".join(error_messages).lower()
            self.assertTrue(
                "middleware" in combined_errors or "conflict" in combined_errors,
                f"Failures should be middleware-related: {error_messages}"
            )
    
    @pytest.mark.asyncio
    async def test_gcp_staging_websocket_with_authentication_failure(self):
        """
        Test WebSocket with authentication in GCP staging environment.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn middleware
        incorrectly handles WebSocket authentication in Cloud Run.
        """
        # Create WebSocket URL with authentication parameters
        auth_ws_url = f"{self.gcp_tester.staging_ws_url}/ws?token=test-token"
        
        result = {
            "success": False,
            "error": None,
            "auth_processed": False
        }
        
        try:
            # Test WebSocket with authentication
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(
                auth_ws_url,
                ssl=ssl_context,
                timeout=self.gcp_tester.timeout,
                extra_headers={
                    "Authorization": "Bearer test-token",
                    "Origin": "https://app.netra.co"
                }
            ) as websocket:
                result["success"] = True
                result["auth_processed"] = True
                
                # Test authenticated message exchange
                await websocket.send(json.dumps({"type": "auth_test", "token": "test-token"}))
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                result["response"] = response
                
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 1011:  # Internal server error
                result["error"] = f"WebSocket auth middleware conflict: {e.code} {e.reason}"
            else:
                result["error"] = f"Auth connection closed: {e.code} {e.reason}"
                
        except Exception as e:
            result["error"] = f"Auth WebSocket failed: {e}"
        
        # ASSERTION THAT SHOULD FAIL: authenticated WebSocket should work
        self.assertTrue(
            result["success"],
            f"WebSocket with authentication should work: {result['error']}"
        )
        
        self.assertTrue(
            result["auth_processed"],
            "WebSocket authentication should be processed correctly"
        )
    
    def test_gcp_staging_websocket_cors_middleware_conflict(self):
        """
        Test WebSocket CORS middleware conflicts in GCP staging.
        
        EXPECTED: This test should FAIL, demonstrating CORS middleware
        incorrectly processes WebSocket requests in Cloud Run.
        """
        # Test WebSocket with CORS headers
        result = self.gcp_tester.test_http_to_websocket_upgrade("/ws")
        
        if result["upgrade_attempted"]:
            headers = result["response_headers"]
            
            # ASSERTION THAT SHOULD FAIL: WebSocket shouldn't have CORS headers
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods", 
                "access-control-allow-headers"
            ]
            
            found_cors_headers = [
                header for header in cors_headers 
                if any(h.lower() == header for h in headers.keys())
            ]
            
            self.assertEqual(
                len(found_cors_headers), 0,
                f"WebSocket upgrade should not have CORS headers: {found_cors_headers}"
            )
        else:
            # If upgrade failed, it might be due to CORS middleware conflict
            if result["status_code"] in [400, 403]:
                self.fail(f"WebSocket upgrade rejected, possibly due to CORS middleware: {result['error']}")
    
    @pytest.mark.asyncio
    async def test_gcp_staging_websocket_timeout_under_load(self):
        """
        Test WebSocket timeout behavior under load in GCP staging.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn middleware
        stack causes timeout issues under load in Cloud Run.
        """
        # Test WebSocket connection with simulated load
        timeout_results = []
        
        for i in range(5):  # Test 5 connections with different timings
            start_time = time.time()
            
            result = await self.gcp_tester.test_websocket_connection(f"/ws?load_test={i}")
            
            timeout_result = {
                "connection_id": i,
                "success": result["success"],
                "response_time": result["response_time"],
                "error": result["error"],
                "exceeded_timeout": result["response_time"] > 15.0  # 15s threshold
            }
            timeout_results.append(timeout_result)
            
            # Add delay between connections to simulate load
            await asyncio.sleep(1.0)
        
        # ASSERTION THAT SHOULD FAIL: all connections should complete within timeout
        failed_connections = [r for r in timeout_results if not r["success"] or r["exceeded_timeout"]]
        self.assertEqual(
            len(failed_connections), 0,
            f"All WebSocket connections should complete within timeout, failed: {len(failed_connections)}"
        )
        
        # Check average response time
        successful_times = [r["response_time"] for r in timeout_results if r["success"]]
        if successful_times:
            avg_response_time = sum(successful_times) / len(successful_times)
            self.assertLess(
                avg_response_time, 5.0,
                f"Average WebSocket response time should be < 5s, got {avg_response_time:.2f}s"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])