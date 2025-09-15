"""
Staging Authentication and Service Health Validation - Issue #1176
================================================================

MISSION CRITICAL: Validate all staging services are healthy and authentication
works properly as prerequisites for Golden Path functionality.

BUSINESS IMPACT: Authentication failures block all users from accessing 
$500K+ ARR chat functionality. Service health issues cause instability.

TARGET: Complete staging environment health validation
- Auth Service: https://auth.staging.netrasystems.ai
- Backend API: https://api.staging.netrasystems.ai
- WebSocket: wss://api.staging.netrasystems.ai/ws
- Database connectivity and service dependencies

PURPOSE: Ensure staging infrastructure is ready for Golden Path validation
and identify any foundational issues blocking user authentication.
"""

import asyncio
import json
import time
import pytest
import websockets
from typing import Dict, List, Any, Optional
import httpx

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestStagingAuthenticationServiceHealth(SSotAsyncTestCase):
    """
    Comprehensive staging environment health and authentication validation.
    
    These tests ensure all staging services are operational and authentication
    flows work correctly before attempting Golden Path validation.
    """

    # Staging environment endpoints
    STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"
    STAGING_API_URL = "https://api.staging.netrasystems.ai"
    STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
    
    # Health check timeouts
    HEALTH_TIMEOUT = 15.0
    AUTH_TIMEOUT = 20.0
    CONNECTION_TIMEOUT = 25.0
    
    # Service health requirements
    MIN_RESPONSE_TIME = 5.0  # Max 5 seconds for health checks
    MAX_AUTH_TIME = 10.0     # Max 10 seconds for authentication

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for health tests"""
        return UserExecutionContext.from_request(
            user_id="staging_health_test_user",
            thread_id="staging_health_test_thread",
            run_id="staging_health_test_run"
        )

    async def setUp(self):
        """Set up staging health validation tests."""
        await super().setUp()
        self.service_health_status = {}

    async def test_staging_auth_service_health_comprehensive(self):
        """
        P0 CRITICAL: Comprehensive authentication service health validation.
        
        This validates the auth service is operational and can handle
        authentication requests required for Golden Path functionality.
        """
        auth_health = {
            "service_reachable": False,
            "health_endpoint_working": False,
            "response_time": None,
            "authentication_working": False,
            "jwt_validation_working": False,
            "error_details": []
        }
        
        try:
            # Test health endpoint
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
                health_response = await client.get(f"{self.STAGING_AUTH_URL}/health")
                
                auth_health["response_time"] = time.time() - start_time
                auth_health["service_reachable"] = True
                
                if health_response.status_code == 200:
                    auth_health["health_endpoint_working"] = True
                    
                    # Parse health response
                    try:
                        health_data = health_response.json()
                        auth_health["health_data"] = health_data
                    except:
                        auth_health["health_data"] = health_response.text
                else:
                    auth_health["error_details"].append(
                        f"Health endpoint returned {health_response.status_code}: {health_response.text}"
                    )
            
            # Validate response time
            self.assertIsNotNone(
                auth_health["response_time"],
                "Auth service health check failed to complete"
            )
            
            self.assertLessEqual(
                auth_health["response_time"], self.MIN_RESPONSE_TIME,
                f"Auth service too slow: {auth_health['response_time']:.2f}s > {self.MIN_RESPONSE_TIME}s"
            )
            
            # Validate health endpoint works
            self.assertTrue(
                auth_health["health_endpoint_working"],
                f"Auth service health endpoint failed:\n{auth_health['error_details']}"
            )
            
        except Exception as e:
            auth_health["error_details"].append(f"Health check exception: {str(e)}")
            self.fail(
                f"STAGING AUTH SERVICE HEALTH CHECK FAILED:\n"
                f"Error: {str(e)}\n"
                f"Auth health status: {auth_health}\n"
                f"This blocks all Golden Path authentication."
            )
        
        # Store for other tests
        self.service_health_status["auth"] = auth_health

    async def test_staging_auth_service_e2e_authentication_flow(self):
        """
        P0 CRITICAL: End-to-end authentication flow validation.
        
        This tests the complete authentication flow that Golden Path requires,
        including JWT token generation and validation.
        """
        auth_flow_status = {
            "test_auth_endpoint_available": False,
            "authentication_successful": False,
            "jwt_token_received": False,
            "jwt_token_valid": False,
            "user_id_received": False,
            "auth_time": None,
            "token_details": {}
        }
        
        try:
            start_time = time.time()
            
            # Test E2E authentication endpoint
            async with httpx.AsyncClient(timeout=self.AUTH_TIMEOUT) as client:
                auth_payload = {
                    "simulation_key": "staging-e2e-test-bypass-key-2025",
                    "email": "health-test@staging.netrasystems.ai"
                }
                
                auth_response = await client.post(
                    f"{self.STAGING_AUTH_URL}/auth/e2e/test-auth",
                    headers={"Content-Type": "application/json"},
                    json=auth_payload
                )
                
                auth_flow_status["auth_time"] = time.time() - start_time
                auth_flow_status["test_auth_endpoint_available"] = True
                
                # Validate authentication response
                self.assertEqual(
                    auth_response.status_code, 200,
                    f"Authentication failed with status {auth_response.status_code}:\n"
                    f"Response: {auth_response.text}\n"
                    f"This completely blocks Golden Path user authentication."
                )
                
                auth_flow_status["authentication_successful"] = True
                
                # Parse authentication data
                auth_data = auth_response.json()
                
                # Validate required fields
                self.assertIn(
                    "access_token", auth_data,
                    f"No access_token in auth response: {auth_data}"
                )
                
                self.assertIn(
                    "user_id", auth_data,
                    f"No user_id in auth response: {auth_data}"
                )
                
                access_token = auth_data["access_token"]
                user_id = auth_data["user_id"]
                
                auth_flow_status["jwt_token_received"] = True
                auth_flow_status["user_id_received"] = True
                
                # Validate JWT token format
                self.assertTrue(
                    access_token.startswith("eyJ"),
                    f"Invalid JWT token format: {access_token[:30]}..."
                )
                
                auth_flow_status["jwt_token_valid"] = True
                
                # Store token details
                auth_flow_status["token_details"] = {
                    "user_id": user_id,
                    "token_length": len(access_token),
                    "token_prefix": access_token[:20] + "...",
                    "expires_in": auth_data.get("expires_in"),
                    "token_type": auth_data.get("token_type", "Bearer")
                }
                
                # Validate authentication timing
                self.assertLessEqual(
                    auth_flow_status["auth_time"], self.MAX_AUTH_TIME,
                    f"Authentication too slow: {auth_flow_status['auth_time']:.2f}s > {self.MAX_AUTH_TIME}s"
                )
                
        except Exception as e:
            self.fail(
                f"STAGING E2E AUTHENTICATION FLOW FAILED:\n"
                f"Error: {str(e)}\n"
                f"Auth flow status: {auth_flow_status}\n"
                f"This completely blocks Golden Path user access."
            )
        
        # Store for other tests
        self.service_health_status["auth_flow"] = auth_flow_status

    async def test_staging_backend_api_service_health(self):
        """
        P0 CRITICAL: Backend API service health validation.
        
        This validates the backend API service is operational and can handle
        requests required for Golden Path chat functionality.
        """
        backend_health = {
            "service_reachable": False,
            "health_endpoint_working": False,
            "response_time": None,
            "authenticated_access_working": False,
            "error_details": []
        }
        
        try:
            # Test backend health endpoint (unauthenticated)
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.HEALTH_TIMEOUT) as client:
                health_response = await client.get(f"{self.STAGING_API_URL}/health")
                
                backend_health["response_time"] = time.time() - start_time
                backend_health["service_reachable"] = True
                
                # Backend health might return 200 or might require auth
                if health_response.status_code in [200, 401, 403]:
                    backend_health["health_endpoint_working"] = True
                    
                    try:
                        health_data = health_response.json()
                        backend_health["health_data"] = health_data
                    except:
                        backend_health["health_data"] = health_response.text
                else:
                    backend_health["error_details"].append(
                        f"Backend health endpoint returned unexpected status {health_response.status_code}"
                    )
            
            # Validate service is reachable
            self.assertTrue(
                backend_health["service_reachable"],
                f"Backend API service not reachable: {backend_health['error_details']}"
            )
            
            # Validate response time
            self.assertIsNotNone(
                backend_health["response_time"],
                "Backend service health check failed to complete"
            )
            
            self.assertLessEqual(
                backend_health["response_time"], self.MIN_RESPONSE_TIME,
                f"Backend service too slow: {backend_health['response_time']:.2f}s > {self.MIN_RESPONSE_TIME}s"
            )
            
        except Exception as e:
            backend_health["error_details"].append(f"Health check exception: {str(e)}")
            self.fail(
                f"STAGING BACKEND API HEALTH CHECK FAILED:\n"
                f"Error: {str(e)}\n"
                f"Backend health status: {backend_health}\n"
                f"This blocks Golden Path chat functionality."
            )
        
        # Store for other tests
        self.service_health_status["backend"] = backend_health

    async def test_staging_websocket_service_basic_connectivity(self):
        """
        P0 CRITICAL: WebSocket service basic connectivity validation.
        
        This validates the WebSocket service accepts connections and handles
        the basic handshake required for Golden Path real-time functionality.
        """
        websocket_health = {
            "service_reachable": False,
            "connection_possible": False,
            "handshake_time": None,
            "connection_stable": False,
            "auth_header_support": False,
            "error_details": []
        }
        
        try:
            # Test basic WebSocket connectivity (no auth)
            start_time = time.time()
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                timeout=self.CONNECTION_TIMEOUT
            ) as websocket:
                
                websocket_health["handshake_time"] = time.time() - start_time
                websocket_health["service_reachable"] = True
                websocket_health["connection_possible"] = True
                
                # Test connection stability
                await asyncio.sleep(2.0)
                
                # Try to send a ping
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=5.0)
                
                websocket_health["connection_stable"] = True
            
            # Validate handshake timing
            self.assertIsNotNone(
                websocket_health["handshake_time"],
                "WebSocket handshake failed to complete"
            )
            
            self.assertLessEqual(
                websocket_health["handshake_time"], self.MIN_RESPONSE_TIME,
                f"WebSocket handshake too slow: {websocket_health['handshake_time']:.2f}s > {self.MIN_RESPONSE_TIME}s"
            )
            
            # Validate connection works
            self.assertTrue(
                websocket_health["connection_possible"],
                "WebSocket connection failed"
            )
            
            self.assertTrue(
                websocket_health["connection_stable"],
                "WebSocket connection unstable"
            )
            
        except Exception as e:
            websocket_health["error_details"].append(f"Connection exception: {str(e)}")
            self.fail(
                f"STAGING WEBSOCKET BASIC CONNECTIVITY FAILED:\n"
                f"Error: {str(e)}\n"
                f"WebSocket health status: {websocket_health}\n"
                f"This blocks Golden Path real-time functionality."
            )
        
        # Store for other tests
        self.service_health_status["websocket"] = websocket_health

    async def test_staging_websocket_authenticated_connection(self):
        """
        P0 CRITICAL: WebSocket authenticated connection validation.
        
        This tests the complete WebSocket authentication flow required
        for Golden Path chat functionality.
        """
        # Get authentication token first
        auth_token = None
        
        try:
            async with httpx.AsyncClient(timeout=self.AUTH_TIMEOUT) as client:
                auth_payload = {
                    "simulation_key": "staging-e2e-test-bypass-key-2025",
                    "email": "websocket-test@staging.netrasystems.ai"
                }
                
                auth_response = await client.post(
                    f"{self.STAGING_AUTH_URL}/auth/e2e/test-auth",
                    headers={"Content-Type": "application/json"},
                    json=auth_payload
                )
                
                self.assertEqual(auth_response.status_code, 200, "Authentication failed")
                auth_data = auth_response.json()
                auth_token = auth_data["access_token"]
        
        except Exception as e:
            self.fail(f"Failed to get auth token for WebSocket test: {str(e)}")
        
        # Test authenticated WebSocket connection
        websocket_auth = {
            "auth_connection_possible": False,
            "connection_ready_received": False,
            "user_context_created": False,
            "handshake_time": None,
            "welcome_message": None,
            "error_details": []
        }
        
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            start_time = time.time()
            
            async with websockets.connect(
                self.STAGING_WS_URL,
                extra_headers=headers,
                timeout=self.CONNECTION_TIMEOUT
            ) as websocket:
                
                websocket_auth["auth_connection_possible"] = True
                websocket_auth["handshake_time"] = time.time() - start_time
                
                # Wait for connection ready message
                try:
                    welcome_message = await asyncio.wait_for(
                        websocket.recv(), timeout=10.0
                    )
                    
                    welcome_data = json.loads(welcome_message)
                    websocket_auth["welcome_message"] = welcome_data
                    
                    # Validate connection ready message
                    self.assertEqual(
                        welcome_data.get("type"), "connection_ready",
                        f"Expected connection_ready, got: {welcome_data}"
                    )
                    
                    websocket_auth["connection_ready_received"] = True
                    
                    # Validate user context
                    if "user_id" in welcome_data:
                        websocket_auth["user_context_created"] = True
                    
                except asyncio.TimeoutError:
                    websocket_auth["error_details"].append("No welcome message received within 10 seconds")
            
            # Validate authenticated connection works
            self.assertTrue(
                websocket_auth["auth_connection_possible"],
                f"Authenticated WebSocket connection failed: {websocket_auth['error_details']}"
            )
            
            self.assertTrue(
                websocket_auth["connection_ready_received"],
                f"No connection_ready message received: {websocket_auth}"
            )
            
            self.assertTrue(
                websocket_auth["user_context_created"],
                f"User context not created properly: {websocket_auth['welcome_message']}"
            )
            
        except Exception as e:
            websocket_auth["error_details"].append(f"Authenticated connection exception: {str(e)}")
            self.fail(
                f"STAGING WEBSOCKET AUTHENTICATED CONNECTION FAILED:\n"
                f"Error: {str(e)}\n"
                f"WebSocket auth status: {websocket_auth}\n"
                f"This blocks Golden Path chat functionality."
            )
        
        # Store for other tests
        self.service_health_status["websocket_auth"] = websocket_auth

    async def test_staging_service_dependencies_integration(self):
        """
        P1 HIGH: Validate service dependencies and integration health.
        
        This tests that all staging services can work together properly
        for complete Golden Path functionality.
        """
        # Ensure all basic health tests passed
        await self.test_staging_auth_service_health_comprehensive()
        await self.test_staging_backend_api_service_health()
        await self.test_staging_websocket_service_basic_connectivity()
        
        integration_health = {
            "all_services_healthy": False,
            "auth_to_websocket_flow": False,
            "backend_to_websocket_integration": False,
            "cross_service_timing": {},
            "overall_health_score": 0
        }
        
        try:
            # Calculate overall health score
            healthy_services = 0
            total_services = 0
            
            for service_name, service_health in self.service_health_status.items():
                total_services += 1
                
                if service_name == "auth":
                    if service_health.get("health_endpoint_working"):
                        healthy_services += 1
                elif service_name == "backend":
                    if service_health.get("service_reachable"):
                        healthy_services += 1
                elif service_name == "websocket":
                    if service_health.get("connection_possible"):
                        healthy_services += 1
            
            if total_services > 0:
                integration_health["overall_health_score"] = (healthy_services / total_services) * 100
                integration_health["all_services_healthy"] = (healthy_services == total_services)
            
            # Test auth to WebSocket integration
            if (self.service_health_status.get("auth", {}).get("health_endpoint_working") and
                self.service_health_status.get("websocket", {}).get("connection_possible")):
                integration_health["auth_to_websocket_flow"] = True
            
            # Validate overall integration health
            self.assertGreaterEqual(
                integration_health["overall_health_score"], 75.0,
                f"STAGING SERVICE INTEGRATION HEALTH TOO LOW:\n"
                f"Health score: {integration_health['overall_health_score']:.1f}%\n"
                f"Service health status: {self.service_health_status}\n"
                f"Integration health: {integration_health}\n"
                f"Poor integration health blocks Golden Path functionality."
            )
            
            # Validate critical integration flows work
            self.assertTrue(
                integration_health["auth_to_websocket_flow"],
                f"Auth to WebSocket integration broken:\n"
                f"This blocks authenticated Golden Path functionality."
            )
            
        except Exception as e:
            self.fail(
                f"STAGING SERVICE DEPENDENCIES INTEGRATION FAILED:\n"
                f"Error: {str(e)}\n"
                f"Service health status: {self.service_health_status}\n"
                f"Integration health: {integration_health}\n"
                f"This blocks complete Golden Path functionality."
            )

    async def test_staging_environment_readiness_summary(self):
        """
        P1 HIGH: Generate comprehensive staging environment readiness summary.
        
        This provides a complete assessment of staging readiness for
        Golden Path validation and identifies any blocking issues.
        """
        # Run all health checks
        await self.test_staging_auth_service_health_comprehensive()
        await self.test_staging_auth_service_e2e_authentication_flow()
        await self.test_staging_backend_api_service_health()
        await self.test_staging_websocket_service_basic_connectivity()
        await self.test_staging_websocket_authenticated_connection()
        
        readiness_summary = {
            "overall_readiness": False,
            "readiness_score": 0,
            "service_status": {},
            "blocking_issues": [],
            "warnings": [],
            "golden_path_ready": False
        }
        
        try:
            # Analyze service status
            critical_services = ["auth", "auth_flow", "backend", "websocket", "websocket_auth"]
            healthy_critical_services = 0
            
            for service in critical_services:
                service_data = self.service_health_status.get(service, {})
                service_healthy = False
                
                if service == "auth":
                    service_healthy = service_data.get("health_endpoint_working", False)
                elif service == "auth_flow":
                    service_healthy = service_data.get("jwt_token_valid", False)
                elif service == "backend":
                    service_healthy = service_data.get("service_reachable", False)
                elif service == "websocket":
                    service_healthy = service_data.get("connection_stable", False)
                elif service == "websocket_auth":
                    service_healthy = service_data.get("connection_ready_received", False)
                
                readiness_summary["service_status"][service] = {
                    "healthy": service_healthy,
                    "details": service_data
                }
                
                if service_healthy:
                    healthy_critical_services += 1
                else:
                    readiness_summary["blocking_issues"].append(
                        f"Service {service} not healthy: {service_data}"
                    )
            
            # Calculate readiness score
            readiness_summary["readiness_score"] = (healthy_critical_services / len(critical_services)) * 100
            readiness_summary["overall_readiness"] = (healthy_critical_services == len(critical_services))
            
            # Determine Golden Path readiness
            readiness_summary["golden_path_ready"] = (
                readiness_summary["readiness_score"] >= 90.0 and
                len(readiness_summary["blocking_issues"]) == 0
            )
            
            # Add performance warnings
            for service, data in self.service_health_status.items():
                response_time = data.get("response_time")
                if response_time and response_time > 3.0:
                    readiness_summary["warnings"].append(
                        f"Service {service} slow response time: {response_time:.2f}s"
                    )
            
            # Validate staging is ready for Golden Path testing
            self.assertTrue(
                readiness_summary["golden_path_ready"],
                f"STAGING ENVIRONMENT NOT READY FOR GOLDEN PATH TESTING:\n"
                f"Readiness score: {readiness_summary['readiness_score']:.1f}%\n"
                f"Blocking issues: {readiness_summary['blocking_issues']}\n"
                f"Service status: {readiness_summary['service_status']}\n"
                f"Warnings: {readiness_summary['warnings']}\n"
                f"\nStaging must be fully operational for Golden Path validation."
            )
            
        except Exception as e:
            self.fail(
                f"STAGING ENVIRONMENT READINESS ASSESSMENT FAILED:\n"
                f"Error: {str(e)}\n"
                f"Readiness summary: {readiness_summary}\n"
                f"Cannot proceed with Golden Path testing."
            )
        
        # Store final readiness assessment
        self.service_health_status["readiness_summary"] = readiness_summary


if __name__ == "__main__":
    import unittest
    unittest.main()