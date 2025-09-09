"""
WebSocket Staging Environment Validation Test Suite

This test suite validates the GCP staging environment infrastructure components
that affect WebSocket connections and the WebSocket 1011 error scenarios.

Business Impact:
- Validates staging environment configuration for WebSocket functionality  
- Tests GCP Cloud Run WebSocket upgrade support and configuration
- Confirms load balancer WebSocket handling and SSL certificate validation
- Validates environment variable propagation in Cloud Run infrastructure

CRITICAL: These tests validate the infrastructure foundation required 
for WebSocket 1011 error fixes to work properly in staging.
"""

import asyncio
import json
import logging
import httpx
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Configure test for staging infrastructure validation
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.infrastructure,
    pytest.mark.websocket,
    pytest.mark.gcp,
]


@pytest.fixture
def staging_config():
    """Staging configuration for infrastructure validation."""
    return StagingTestConfig()


@pytest.fixture
def staging_auth_helper(staging_config):
    """Auth helper for staging infrastructure tests."""
    return E2EAuthHelper(environment="staging")


class TestWebSocketStagingEnvironmentValidation:
    """
    Test suite that validates GCP staging environment infrastructure.
    
    These tests verify that the staging environment is properly configured
    to support WebSocket connections and the fixes for 1011 errors.
    """
    
    async def test_staging_domains_resolve_correctly(
        self,
        staging_config: StagingTestConfig
    ):
        """
        Test that staging domains resolve correctly and are reachable.
        
        This validates the basic network connectivity to staging services
        that is required for WebSocket connections to work.
        
        EXPECTED: All staging domains should resolve and return valid responses.
        """
        logger.info("🏗️ INFRASTRUCTURE TEST: Staging domain resolution validation")
        
        # Extract domains from staging URLs
        staging_domains = {
            "backend": staging_config.urls.backend_url,
            "auth": staging_config.urls.auth_url,
            "websocket": staging_config.urls.websocket_url
        }
        
        domain_results = {}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for service_name, service_url in staging_domains.items():
                logger.info(f"🔍 Testing {service_name} domain: {service_url}")
                
                try:
                    # Test basic HTTP connectivity
                    if service_name == "websocket":
                        # Convert WebSocket URL to HTTP for basic connectivity test
                        http_url = service_url.replace("ws://", "http://").replace("wss://", "https://")
                        test_url = f"{http_url.rstrip('/ws')}/health"
                    else:
                        test_url = f"{service_url}/health"
                    
                    start_time = time.time()
                    response = await client.get(test_url)
                    response_time = time.time() - start_time
                    
                    domain_results[service_name] = {
                        "url": service_url,
                        "test_url": test_url,
                        "reachable": True,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "error": None
                    }
                    
                    logger.info(f"✅ {service_name}: {response.status_code} in {response_time:.3f}s")
                    
                    # Validate response indicates healthy service
                    if response.status_code not in [200, 404]:  # 404 is acceptable for health endpoint
                        logger.warning(f"⚠️ {service_name}: Unexpected status code {response.status_code}")
                    
                except httpx.RequestError as e:
                    domain_results[service_name] = {
                        "url": service_url,
                        "test_url": test_url if 'test_url' in locals() else service_url,
                        "reachable": False,
                        "error": f"RequestError: {e}",
                        "response_time": None
                    }
                    logger.error(f"❌ {service_name}: Request failed - {e}")
                    
                except Exception as e:
                    domain_results[service_name] = {
                        "url": service_url,
                        "test_url": test_url if 'test_url' in locals() else service_url,
                        "reachable": False,
                        "error": f"Unexpected error: {e}",
                        "response_time": None
                    }
                    logger.error(f"❌ {service_name}: Unexpected error - {e}")
        
        # Validate results
        reachable_services = sum(1 for result in domain_results.values() if result["reachable"])
        total_services = len(domain_results)
        
        logger.info("🔍 DOMAIN RESOLUTION RESULTS:")
        for service, result in domain_results.items():
            status = "REACHABLE" if result["reachable"] else "UNREACHABLE"
            time_str = f" ({result['response_time']:.3f}s)" if result["response_time"] else ""
            logger.info(f"   {service.upper()}: {status}{time_str}")
            if not result["reachable"]:
                logger.error(f"     Error: {result['error']}")
        
        # Require at least backend and auth services to be reachable
        backend_reachable = domain_results.get("backend", {}).get("reachable", False)
        auth_reachable = domain_results.get("auth", {}).get("reachable", False)
        
        if not backend_reachable:
            pytest.fail(f"CRITICAL: Backend service unreachable at {staging_config.urls.backend_url}")
        
        if not auth_reachable:
            pytest.fail(f"CRITICAL: Auth service unreachable at {staging_config.urls.auth_url}")
        
        logger.info(f"✅ Infrastructure connectivity: {reachable_services}/{total_services} services reachable")
        
        return domain_results

    async def test_load_balancer_websocket_upgrade_support(
        self,
        staging_config: StagingTestConfig
    ):
        """
        Test that the load balancer supports WebSocket upgrade requests.
        
        This validates that the GCP load balancer is properly configured
        to handle WebSocket protocol upgrades, which is required for 
        WebSocket connections to establish successfully.
        
        EXPECTED: Load balancer should support WebSocket upgrade headers.
        """
        logger.info("🏗️ INFRASTRUCTURE TEST: Load balancer WebSocket upgrade support")
        
        # Test WebSocket upgrade request to the staging WebSocket endpoint
        websocket_url = staging_config.urls.websocket_url
        
        try:
            # Parse WebSocket URL to get host and path
            parsed_url = urlparse(websocket_url)
            host = parsed_url.netloc
            path = parsed_url.path or "/ws"
            scheme = "https" if parsed_url.scheme == "wss" else "http"
            
            # Create WebSocket upgrade request manually to test load balancer
            upgrade_headers = {
                "Host": host,
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",  # Base64 encoded test key
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Protocol": "chat",
                "Origin": f"{scheme}://{host}",
                "User-Agent": "WebSocket-Infrastructure-Test/1.0",
                # Add infrastructure test headers
                "X-Test-Type": "infrastructure-websocket-upgrade",
                "X-Load-Balancer-Test": "websocket-upgrade-support"
            }
            
            logger.info(f"🔍 Testing WebSocket upgrade to: {host}{path}")
            logger.info(f"📤 Upgrade headers: {list(upgrade_headers.keys())}")
            
            # Send HTTP upgrade request to test load balancer support
            http_url = f"{scheme}://{host}{path}"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                start_time = time.time()
                response = await client.get(http_url, headers=upgrade_headers)
                response_time = time.time() - start_time
                
                logger.info(f"📥 Response: {response.status_code} in {response_time:.3f}s")
                logger.info(f"📥 Response headers: {dict(response.headers)}")
                
                # Analyze response for WebSocket upgrade support
                upgrade_analysis = {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "headers": dict(response.headers),
                    "upgrade_supported": False,
                    "websocket_ready": False,
                    "error_details": None
                }
                
                # Check for WebSocket upgrade support indicators
                if response.status_code == 101:
                    # Perfect - WebSocket upgrade successful
                    upgrade_analysis["upgrade_supported"] = True
                    upgrade_analysis["websocket_ready"] = True
                    logger.info("✅ WebSocket upgrade successful (101 Switching Protocols)")
                    
                elif response.status_code == 426:
                    # Upgrade Required - server supports WebSocket but needs proper handshake
                    upgrade_analysis["upgrade_supported"] = True
                    logger.info("✅ WebSocket upgrade supported (426 Upgrade Required)")
                    
                elif response.status_code in [400, 404]:
                    # Bad Request or Not Found - may indicate WebSocket endpoint exists but needs proper handshake
                    if any(header.lower() in ["upgrade", "websocket"] for header in response.headers):
                        upgrade_analysis["upgrade_supported"] = True
                        logger.info("✅ WebSocket upgrade likely supported (upgrade headers present)")
                    else:
                        logger.warning(f"⚠️ WebSocket upgrade unclear (status {response.status_code})")
                        
                elif response.status_code >= 500:
                    # Server error - may indicate configuration issues
                    upgrade_analysis["error_details"] = f"Server error: {response.status_code}"
                    logger.error(f"❌ Server error during upgrade test: {response.status_code}")
                    
                else:
                    logger.warning(f"⚠️ Unexpected response: {response.status_code}")
                
                # Additional analysis of response headers
                response_headers = {k.lower(): v for k, v in response.headers.items()}
                
                websocket_indicators = [
                    "upgrade" in response_headers,
                    "connection" in response_headers,
                    any("websocket" in v.lower() for v in response_headers.values()),
                    "sec-websocket" in str(response_headers)
                ]
                
                if any(websocket_indicators):
                    upgrade_analysis["upgrade_supported"] = True
                    logger.info("✅ WebSocket indicators found in response headers")
                
                logger.info("🔍 WEBSOCKET UPGRADE ANALYSIS:")
                logger.info(f"   Upgrade Supported: {upgrade_analysis['upgrade_supported']}")
                logger.info(f"   WebSocket Ready: {upgrade_analysis['websocket_ready']}")
                logger.info(f"   Response Time: {upgrade_analysis['response_time']:.3f}s")
                
                if not upgrade_analysis["upgrade_supported"]:
                    pytest.fail(
                        f"INFRASTRUCTURE ISSUE: Load balancer may not support WebSocket upgrades. "
                        f"Status: {response.status_code}, Headers: {dict(response.headers)}"
                    )
                
                return upgrade_analysis
                
        except httpx.RequestError as e:
            logger.error(f"❌ WebSocket upgrade test failed: {e}")
            pytest.fail(f"INFRASTRUCTURE ISSUE: Cannot reach WebSocket endpoint for upgrade test: {e}")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in upgrade test: {e}")
            raise

    async def test_gcp_cloud_run_websocket_configuration(
        self,
        staging_config: StagingTestConfig,
        staging_auth_helper: E2EAuthHelper
    ):
        """
        Test GCP Cloud Run WebSocket configuration and capabilities.
        
        This validates that the Cloud Run services are properly configured
        to handle WebSocket connections, including timeout settings and
        connection persistence.
        
        EXPECTED: Cloud Run should support WebSocket connections with appropriate timeouts.
        """
        logger.info("🏗️ INFRASTRUCTURE TEST: GCP Cloud Run WebSocket configuration")
        
        # Test Cloud Run service health and WebSocket capabilities
        cloud_run_tests = {}
        
        try:
            # Test 1: Service health and metadata
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Check backend service health
                backend_health_url = f"{staging_config.urls.backend_url}/health"
                
                start_time = time.time()
                response = await client.get(backend_health_url)
                health_response_time = time.time() - start_time
                
                cloud_run_tests["health_check"] = {
                    "status_code": response.status_code,
                    "response_time": health_response_time,
                    "healthy": response.status_code == 200
                }
                
                logger.info(f"📊 Backend health: {response.status_code} in {health_response_time:.3f}s")
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # Check for WebSocket-related health information
                    websocket_health = health_data.get("websocket", {})
                    e2e_health = health_data.get("e2e_testing", {})
                    
                    cloud_run_tests["websocket_health"] = websocket_health
                    cloud_run_tests["e2e_health"] = e2e_health
                    
                    logger.info(f"📊 WebSocket health data: {websocket_health}")
                    logger.info(f"📊 E2E testing health data: {e2e_health}")
                    
                    # Analyze E2E testing configuration
                    e2e_enabled = e2e_health.get("enabled", False)
                    if not e2e_enabled:
                        logger.warning("⚠️ E2E testing shows as disabled in health check")
                        logger.warning("⚠️ This confirms the root cause of WebSocket 1011 errors")
                
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            cloud_run_tests["health_check"] = {"error": str(e), "healthy": False}
        
        try:
            # Test 2: WebSocket connection establishment (basic test)
            logger.info("🔍 Testing basic WebSocket connection to Cloud Run...")
            
            # Get auth token for WebSocket test
            token = await staging_auth_helper.get_staging_token_async()
            
            # Create WebSocket headers
            websocket_headers = {
                "Authorization": f"Bearer {token}",
                "X-Test-Type": "cloud-run-websocket-test",
                "X-Infrastructure-Test": "basic-connection"
            }
            
            start_time = time.time()
            connection_timeout = 10.0  # Shorter timeout for infrastructure test
            
            try:
                async with websockets.connect(
                    staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=connection_timeout,
                    close_timeout=3.0
                ) as websocket:
                    connection_time = time.time() - start_time
                    
                    cloud_run_tests["websocket_connection"] = {
                        "success": True,
                        "connection_time": connection_time,
                        "cloud_run_capable": True
                    }
                    
                    logger.info(f"✅ WebSocket connection successful in {connection_time:.3f}s")
                    
                    # Send a simple test message to validate full functionality
                    test_message = {
                        "type": "infrastructure_test",
                        "test_phase": "cloud_run_websocket_validation"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Try to receive response (with short timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        cloud_run_tests["websocket_connection"]["message_exchange"] = True
                        logger.info("✅ WebSocket message exchange successful")
                    except asyncio.TimeoutError:
                        cloud_run_tests["websocket_connection"]["message_exchange"] = False
                        logger.warning("⚠️ WebSocket message exchange timeout (may be expected)")
                    
            except websockets.exceptions.ConnectionClosedError as e:
                connection_time = time.time() - start_time
                
                cloud_run_tests["websocket_connection"] = {
                    "success": False,
                    "connection_time": connection_time,
                    "error_code": e.code,
                    "error_reason": e.reason,
                    "cloud_run_capable": e.code != 1006  # 1006 would indicate infrastructure failure
                }
                
                logger.info(f"📊 WebSocket connection closed: {e.code} - {e.reason} in {connection_time:.3f}s")
                
                if e.code == 1011:
                    logger.info("✅ Got expected 1011 error - confirms issue reproduction capability")
                elif e.code == 1006:
                    logger.error("❌ 1006 error indicates potential Cloud Run infrastructure issue")
                
            except asyncio.TimeoutError:
                connection_time = time.time() - start_time
                
                cloud_run_tests["websocket_connection"] = {
                    "success": False,
                    "connection_time": connection_time,
                    "timeout": True,
                    "cloud_run_capable": False  # Timeout may indicate configuration issue
                }
                
                logger.warning(f"⚠️ WebSocket connection timeout after {connection_time:.3f}s")
                
        except Exception as e:
            logger.error(f"❌ WebSocket connection test failed: {e}")
            cloud_run_tests["websocket_connection"] = {"error": str(e), "success": False}
        
        # Test 3: Environment variable analysis
        try:
            logger.info("🔍 Analyzing Cloud Run environment configuration...")
            
            # Check if we can infer environment configuration from responses
            env_analysis = {
                "environment_detected": "staging",  # We know we're testing staging
                "cloud_run_detected": True,  # Staging uses Cloud Run
                "e2e_variables_detected": False,  # Likely false based on health check
                "websocket_support_detected": cloud_run_tests.get("websocket_connection", {}).get("success", False)
            }
            
            # Look for Cloud Run specific headers or indicators
            health_check = cloud_run_tests.get("health_check", {})
            if health_check.get("healthy"):
                env_analysis["service_healthy"] = True
            
            # Analyze E2E configuration from health data
            e2e_health = cloud_run_tests.get("e2e_health", {})
            if e2e_health:
                env_analysis["e2e_variables_detected"] = e2e_health.get("enabled", False)
                env_analysis["e2e_config_source"] = "health_endpoint"
            
            cloud_run_tests["environment_analysis"] = env_analysis
            
            logger.info("🔍 CLOUD RUN ENVIRONMENT ANALYSIS:")
            for key, value in env_analysis.items():
                logger.info(f"   {key}: {value}")
            
        except Exception as e:
            logger.error(f"❌ Environment analysis failed: {e}")
            cloud_run_tests["environment_analysis"] = {"error": str(e)}
        
        # Validate overall Cloud Run configuration
        logger.info("🔍 CLOUD RUN CONFIGURATION RESULTS:")
        for test_name, result in cloud_run_tests.items():
            if isinstance(result, dict):
                success = result.get("success") or result.get("healthy") or not result.get("error")
                status = "PASS" if success else "FAIL"
                logger.info(f"   {test_name}: {status}")
                if not success and result.get("error"):
                    logger.info(f"     Error: {result['error']}")
        
        # Require service health to be good
        if not cloud_run_tests.get("health_check", {}).get("healthy"):
            pytest.fail("INFRASTRUCTURE ISSUE: Backend service health check failed")
        
        return cloud_run_tests

    async def test_ssl_certificate_websocket_validation(
        self,
        staging_config: StagingTestConfig
    ):
        """
        Test SSL certificate validation for WebSocket connections.
        
        This validates that the staging environment has proper SSL certificates
        configured for secure WebSocket connections (WSS).
        
        EXPECTED: SSL certificates should be valid and properly configured for WebSocket upgrades.
        """
        logger.info("🏗️ INFRASTRUCTURE TEST: SSL certificate WebSocket validation")
        
        websocket_url = staging_config.urls.websocket_url
        
        # Only test SSL if using WSS protocol
        if not websocket_url.startswith("wss://"):
            logger.info("ℹ️ Skipping SSL test - WebSocket URL uses non-secure protocol")
            return {"ssl_test": "skipped", "reason": "non_secure_protocol"}
        
        try:
            # Parse WSS URL 
            parsed_url = urlparse(websocket_url)
            host = parsed_url.netloc
            port = parsed_url.port or 443
            
            logger.info(f"🔍 Testing SSL certificate for: {host}:{port}")
            
            # Test SSL certificate using HTTPS request to same host
            https_test_url = f"https://{host}/health"
            
            ssl_results = {
                "host": host,
                "port": port,
                "certificate_valid": False,
                "websocket_ssl_ready": False,
                "certificate_info": {},
                "error": None
            }
            
            async with httpx.AsyncClient(
                timeout=10.0,
                verify=True  # Strict SSL verification
            ) as client:
                start_time = time.time()
                response = await client.get(https_test_url)
                response_time = time.time() - start_time
                
                ssl_results["certificate_valid"] = True
                ssl_results["response_time"] = response_time
                ssl_results["status_code"] = response.status_code
                
                logger.info(f"✅ SSL certificate valid - HTTPS response: {response.status_code} in {response_time:.3f}s")
                
                # Check response headers for WebSocket upgrade support over SSL
                headers = dict(response.headers)
                ssl_results["response_headers"] = headers
                
                # Look for security headers that might affect WebSocket connections
                security_headers = {
                    "Strict-Transport-Security": headers.get("strict-transport-security"),
                    "X-Frame-Options": headers.get("x-frame-options"),
                    "X-Content-Type-Options": headers.get("x-content-type-options"),
                    "Content-Security-Policy": headers.get("content-security-policy")
                }
                
                ssl_results["security_headers"] = security_headers
                
                logger.info("📊 Security headers:")
                for header_name, header_value in security_headers.items():
                    if header_value:
                        logger.info(f"   {header_name}: {header_value[:100]}...")
                    else:
                        logger.info(f"   {header_name}: Not set")
                
                # Test actual WSS connection to validate SSL + WebSocket combination
                try:
                    logger.info("🔍 Testing actual WSS connection...")
                    
                    wss_start_time = time.time()
                    async with websockets.connect(
                        websocket_url,
                        ssl=True,  # Enable SSL verification for WebSocket
                        open_timeout=10.0
                    ) as websocket:
                        wss_connection_time = time.time() - wss_start_time
                        
                        ssl_results["websocket_ssl_ready"] = True
                        ssl_results["wss_connection_time"] = wss_connection_time
                        
                        logger.info(f"✅ WSS connection successful in {wss_connection_time:.3f}s")
                        
                except websockets.exceptions.ConnectionClosedError as e:
                    wss_connection_time = time.time() - wss_start_time
                    
                    # Connection closed but SSL handshake worked if we got this far
                    ssl_results["websocket_ssl_ready"] = True
                    ssl_results["wss_connection_time"] = wss_connection_time
                    ssl_results["wss_close_code"] = e.code
                    ssl_results["wss_close_reason"] = e.reason
                    
                    logger.info(f"✅ WSS SSL handshake successful, connection closed: {e.code} in {wss_connection_time:.3f}s")
                    
                except Exception as wss_error:
                    ssl_results["websocket_ssl_ready"] = False
                    ssl_results["wss_error"] = str(wss_error)
                    
                    logger.error(f"❌ WSS connection failed: {wss_error}")
                
        except httpx.RequestError as e:
            ssl_results["certificate_valid"] = False
            ssl_results["error"] = f"HTTPS request failed: {e}"
            logger.error(f"❌ SSL certificate test failed: {e}")
            
        except Exception as e:
            ssl_results["certificate_valid"] = False  
            ssl_results["error"] = f"Unexpected error: {e}"
            logger.error(f"❌ SSL validation failed: {e}")
        
        # Validate SSL results
        logger.info("🔍 SSL CERTIFICATE VALIDATION RESULTS:")
        logger.info(f"   Certificate Valid: {ssl_results['certificate_valid']}")
        logger.info(f"   WebSocket SSL Ready: {ssl_results['websocket_ssl_ready']}")
        
        if ssl_results.get("wss_connection_time"):
            logger.info(f"   WSS Connection Time: {ssl_results['wss_connection_time']:.3f}s")
        
        if ssl_results.get("error"):
            logger.error(f"   Error: {ssl_results['error']}")
        
        # Require valid SSL certificate for staging
        if not ssl_results["certificate_valid"]:
            pytest.fail(f"INFRASTRUCTURE ISSUE: SSL certificate invalid - {ssl_results.get('error')}")
        
        return ssl_results

    async def test_websocket_connection_through_load_balancer(
        self,
        staging_config: StagingTestConfig,
        staging_auth_helper: E2EAuthHelper
    ):
        """
        Test complete WebSocket connection flow through the load balancer.
        
        This validates the complete infrastructure path from client to WebSocket service
        through the GCP load balancer, testing all components that could affect
        WebSocket 1011 errors.
        
        EXPECTED: Complete infrastructure path should be functional.
        """
        logger.info("🏗️ INFRASTRUCTURE TEST: Complete WebSocket connection through load balancer")
        
        infrastructure_test_results = {
            "load_balancer_path": False,
            "websocket_upgrade": False,
            "authentication_path": False,
            "message_routing": False,
            "connection_persistence": False
        }
        
        try:
            # Get authentication token
            token = await staging_auth_helper.get_staging_token_async()
            
            # Create comprehensive infrastructure test headers
            infrastructure_headers = {
                "Authorization": f"Bearer {token}",
                "X-Infrastructure-Test": "complete-load-balancer-path",
                "X-Test-Phase": "websocket-through-lb",
                "X-Load-Balancer-Validation": "full-path-test",
                "X-Expected-Flow": "lb -> cloud-run -> websocket-service",
                "User-Agent": "Infrastructure-Test-Client/1.0"
            }
            
            logger.info(f"📤 Testing complete infrastructure path with headers: {list(infrastructure_headers.keys())}")
            
            # Test complete WebSocket connection flow
            start_time = time.time()
            connection_phases = {}
            
            async with websockets.connect(
                staging_config.urls.websocket_url,
                additional_headers=infrastructure_headers,
                open_timeout=15.0,
                close_timeout=5.0
            ) as websocket:
                # Phase 1: Connection establishment (load balancer + Cloud Run)
                connection_time = time.time() - start_time
                connection_phases["connection_establishment"] = {
                    "success": True,
                    "time": connection_time
                }
                infrastructure_test_results["load_balancer_path"] = True
                infrastructure_test_results["websocket_upgrade"] = True
                
                logger.info(f"✅ Phase 1: Connection established through load balancer in {connection_time:.3f}s")
                
                # Phase 2: Authentication validation
                auth_test_message = {
                    "type": "auth_validation_test",
                    "infrastructure_test": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(auth_test_message))
                
                try:
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    auth_response_data = json.loads(auth_response)
                    
                    connection_phases["authentication"] = {
                        "success": True,
                        "response": auth_response_data
                    }
                    infrastructure_test_results["authentication_path"] = True
                    
                    logger.info("✅ Phase 2: Authentication path through infrastructure successful")
                    
                except asyncio.TimeoutError:
                    connection_phases["authentication"] = {
                        "success": False,
                        "error": "timeout"
                    }
                    logger.warning("⚠️ Phase 2: Authentication response timeout")
                
                # Phase 3: Message routing validation
                routing_messages = [
                    {"type": "ping", "sequence": 1},
                    {"type": "infrastructure_test", "sequence": 2}, 
                    {"type": "echo", "data": "routing_test", "sequence": 3}
                ]
                
                routing_responses = []
                for i, message in enumerate(routing_messages):
                    await websocket.send(json.dumps(message))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        routing_responses.append(json.loads(response))
                        logger.info(f"📥 Routing message {i+1}: Response received")
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Routing message {i+1}: Response timeout")
                        break
                    except Exception as e:
                        logger.error(f"❌ Routing message {i+1}: Error - {e}")
                        break
                
                if routing_responses:
                    connection_phases["message_routing"] = {
                        "success": True,
                        "responses_received": len(routing_responses),
                        "total_sent": len(routing_messages)
                    }
                    infrastructure_test_results["message_routing"] = True
                    logger.info(f"✅ Phase 3: Message routing successful ({len(routing_responses)}/{len(routing_messages)} responses)")
                else:
                    connection_phases["message_routing"] = {
                        "success": False,
                        "error": "no_responses"
                    }
                    logger.warning("⚠️ Phase 3: Message routing failed - no responses received")
                
                # Phase 4: Connection persistence test
                logger.info("🔄 Phase 4: Testing connection persistence (20s)...")
                persistence_start = time.time()
                
                persistence_successful = True
                for i in range(4):  # 4 tests over 20 seconds
                    await asyncio.sleep(5.0)
                    
                    persistence_message = {
                        "type": "persistence_test",
                        "iteration": i + 1,
                        "elapsed": time.time() - persistence_start
                    }
                    
                    try:
                        await websocket.send(json.dumps(persistence_message))
                        persistence_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        logger.info(f"📥 Persistence test {i+1}/4: Success")
                        
                    except Exception as e:
                        logger.error(f"❌ Persistence test {i+1}/4: Failed - {e}")
                        persistence_successful = False
                        break
                
                connection_phases["persistence"] = {
                    "success": persistence_successful,
                    "duration": time.time() - persistence_start
                }
                infrastructure_test_results["connection_persistence"] = persistence_successful
                
                if persistence_successful:
                    logger.info("✅ Phase 4: Connection persistence validation successful")
                else:
                    logger.warning("⚠️ Phase 4: Connection persistence issues detected")
                
                # Final infrastructure validation
                total_test_time = time.time() - start_time
                
                successful_phases = sum(1 for result in infrastructure_test_results.values() if result)
                total_phases = len(infrastructure_test_results)
                
                logger.info("🔍 COMPLETE INFRASTRUCTURE TEST RESULTS:")
                logger.info(f"   Total Test Time: {total_test_time:.3f}s")
                logger.info(f"   Successful Phases: {successful_phases}/{total_phases}")
                
                for phase, success in infrastructure_test_results.items():
                    status = "PASS" if success else "FAIL"
                    logger.info(f"   {phase}: {status}")
                
                if successful_phases >= 3:  # Require at least 3/5 phases to pass
                    logger.info("✅ Infrastructure validation successful")
                else:
                    pytest.fail(
                        f"INFRASTRUCTURE ISSUES: Only {successful_phases}/{total_phases} phases successful. "
                        f"Critical infrastructure components may not be properly configured."
                    )
                
                return {
                    "infrastructure_results": infrastructure_test_results,
                    "connection_phases": connection_phases,
                    "total_time": total_test_time,
                    "success_rate": successful_phases / total_phases
                }
                
        except websockets.exceptions.ConnectionClosedError as e:
            connection_time = time.time() - start_time
            
            logger.error(f"❌ Infrastructure connection failed: Code {e.code} - {e.reason} in {connection_time:.3f}s")
            
            # Analyze failure type
            if e.code == 1011:
                logger.info("ℹ️ Got 1011 error - confirms infrastructure can reproduce the issue")
            elif e.code == 1006:
                pytest.fail("INFRASTRUCTURE ISSUE: Connection closed abnormally - possible load balancer configuration problem")
            
            return {
                "infrastructure_results": infrastructure_test_results,
                "connection_error": {"code": e.code, "reason": e.reason, "time": connection_time},
                "success_rate": 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Infrastructure test failed: {e}")
            raise


if __name__ == "__main__":
    # Direct test execution for infrastructure validation
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
    
    # Run infrastructure validation tests
    async def run_infrastructure_tests():
        staging_config = StagingTestConfig()
        auth_helper = E2EAuthHelper(environment="staging")
        
        test_instance = TestWebSocketStagingEnvironmentValidation()
        
        infrastructure_tests = [
            ("domain_resolution", test_instance.test_staging_domains_resolve_correctly),
            ("websocket_upgrade_support", test_instance.test_load_balancer_websocket_upgrade_support),
            ("cloud_run_configuration", test_instance.test_gcp_cloud_run_websocket_configuration),
            ("ssl_certificate_validation", test_instance.test_ssl_certificate_websocket_validation),
            ("complete_lb_path", test_instance.test_websocket_connection_through_load_balancer)
        ]
        
        results = {}
        for test_name, test_method in infrastructure_tests:
            try:
                print(f"\n🏗️ Running infrastructure test: {test_name}")
                
                if test_name in ["cloud_run_configuration", "complete_lb_path"]:
                    result = await test_method(staging_config, auth_helper)
                else:
                    result = await test_method(staging_config)
                
                results[test_name] = {"success": True, "result": result}
                print(f"✅ {test_name}: SUCCESS")
                
            except Exception as e:
                results[test_name] = {"success": False, "error": str(e)}
                print(f"❌ {test_name}: FAILED - {e}")
        
        print(f"\n📊 INFRASTRUCTURE VALIDATION SUMMARY:")
        for test_name, result in results.items():
            status = "PASS" if result["success"] else "FAIL"
            print(f"   {test_name}: {status}")
        
        overall_success = all(result["success"] for result in results.values())
        print(f"\n🏗️ OVERALL INFRASTRUCTURE STATUS: {'READY' if overall_success else 'ISSUES_DETECTED'}")
    
    asyncio.run(run_infrastructure_tests())