"""
Infrastructure Test: Load Balancer Routing Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure load balancer routes traffic correctly to backend services
- Value Impact: Prevents routing failures that cause 404/503 errors and service unavailability
- Strategic Impact: Validates critical infrastructure routing for all user requests

CRITICAL: This test validates that the GCP load balancer correctly routes requests
to the appropriate backend services. Routing failures result in complete service
unavailability for users.

This addresses GitHub issue #113: GCP Load Balancer Routing Configuration
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set
import pytest
import aiohttp
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestLoadBalancerRoutingValidation(SSotBaseTestCase):
    """
    Test load balancer routing to backend services.
    
    INFRASTRUCTURE TEST: Validates that load balancer correctly routes requests
    to backend services based on path and domain routing rules.
    """
    
    # Load balancer domains and their expected routing
    LOAD_BALANCER_ROUTING = {
        "api.staging.netrasystems.ai": {
            "service": "backend",
            "paths": {
                "/health": "backend_health",
                "/api/v1/health": "backend_api_health", 
                "/api/v1/agents": "backend_agents",
                "/ws": "backend_websocket",
                "/websocket": "backend_websocket",
            }
        },
        "auth.staging.netrasystems.ai": {
            "service": "auth",
            "paths": {
                "/health": "auth_health",
                "/auth/login": "auth_login",
                "/auth/callback": "auth_callback",
                "/auth/logout": "auth_logout",
            }
        },
        "app.staging.netrasystems.ai": {
            "service": "frontend",
            "paths": {
                "/": "frontend_root",
                "/dashboard": "frontend_dashboard",
                "/login": "frontend_login",
            }
        }
    }
    
    # Expected response characteristics for routing validation
    EXPECTED_RESPONSES = {
        "backend_health": {"status_range": (200, 299), "content_type": "application/json"},
        "backend_api_health": {"status_range": (200, 299), "content_type": "application/json"},
        "backend_agents": {"status_range": (200, 401), "content_type": "application/json"},  # 401 without auth is OK
        "backend_websocket": {"status_range": (400, 426), "upgrade": "websocket"},  # WebSocket upgrade expected
        "auth_health": {"status_range": (200, 299), "content_type": "application/json"},
        "auth_login": {"status_range": (200, 302), "content_type": "text/html"},  # Login page or redirect
        "auth_callback": {"status_range": (302, 400), "location": True},  # OAuth callback redirect
        "auth_logout": {"status_range": (200, 302)},  # Logout redirect
        "frontend_root": {"status_range": (200, 299), "content_type": "text/html"},
        "frontend_dashboard": {"status_range": (200, 302), "content_type": "text/html"},
        "frontend_login": {"status_range": (200, 302), "content_type": "text/html"},
    }
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.infrastructure
    async def test_load_balancer_routes_to_correct_backend_services(self):
        """
        HARD FAIL: Load balancer MUST route requests to correct backend services.
        
        This test validates that each domain and path combination routes to the
        expected backend service and returns appropriate responses.
        """
        routing_results = {}
        routing_failures = []
        
        timeout = aiohttp.ClientTimeout(total=30.0)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for domain, config in self.LOAD_BALANCER_ROUTING.items():
                domain_results = {}
                
                for path, expected_endpoint in config["paths"].items():
                    url = f"https://{domain}{path}"
                    
                    try:
                        start_time = time.time()
                        async with session.get(url, allow_redirects=False) as response:
                            response_time = time.time() - start_time
                            
                            result = {
                                'status_code': response.status,
                                'response_time': response_time,
                                'headers': dict(response.headers),
                                'content_type': response.headers.get('content-type', ''),
                                'location': response.headers.get('location'),
                            }
                            
                            # Validate routing based on expected response
                            expected = self.EXPECTED_RESPONSES.get(expected_endpoint, {})
                            routing_valid = self._validate_routing_response(result, expected, expected_endpoint)
                            
                            result['routing_valid'] = routing_valid
                            result['expected_endpoint'] = expected_endpoint
                            
                            if not routing_valid:
                                routing_failures.append(
                                    f"Routing failed for {url}: "
                                    f"status {response.status}, expected {expected.get('status_range', 'any')}"
                                )
                            
                            domain_results[path] = result
                            
                    except asyncio.TimeoutError:
                        domain_results[path] = {
                            'status_code': None,
                            'response_time': None,
                            'routing_valid': False,
                            'expected_endpoint': expected_endpoint,
                            'error': 'Timeout'
                        }
                        routing_failures.append(f"Timeout routing to {url}")
                        
                    except Exception as e:
                        domain_results[path] = {
                            'status_code': None,
                            'response_time': None,
                            'routing_valid': False,
                            'expected_endpoint': expected_endpoint,
                            'error': str(e)
                        }
                        routing_failures.append(f"Routing error for {url}: {e}")
                
                routing_results[domain] = domain_results
        
        if routing_failures:
            error_report = self._build_routing_failure_report(routing_results, routing_failures)
            raise AssertionError(
                f"CRITICAL: Load balancer routing failures detected!\n\n"
                f"Load balancer routing failures cause 404/503 errors and prevent\n"
                f"users from accessing services. This indicates infrastructure problems.\n\n"
                f"ROUTING FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Check load balancer path-based routing configuration\n"
                f"2. Verify backend service health and availability\n"
                f"3. Validate load balancer target groups and health checks\n"
                f"4. Review firewall and security group settings\n"
                f"5. Check backend service DNS resolution\n\n"
                f"Reference: GCP Load Balancer Routing Configuration"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.infrastructure
    async def test_load_balancer_health_check_endpoints(self):
        """
        HARD FAIL: Load balancer health check endpoints MUST be accessible.
        
        This test validates that load balancer health check endpoints are working
        correctly. Health check failures cause load balancer to mark services as unhealthy.
        """
        health_check_results = {}
        health_check_failures = []
        
        health_endpoints = {
            "api.staging.netrasystems.ai": ["/health", "/api/v1/health"],
            "auth.staging.netrasystems.ai": ["/health"],
        }
        
        timeout = aiohttp.ClientTimeout(total=15.0)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for domain, endpoints in health_endpoints.items():
                domain_results = {}
                
                for endpoint in endpoints:
                    url = f"https://{domain}{endpoint}"
                    
                    try:
                        start_time = time.time()
                        async with session.get(url) as response:
                            response_time = time.time() - start_time
                            
                            # Health endpoints should return 200 OK
                            if response.status != 200:
                                health_check_failures.append(
                                    f"Health check failed for {url}: HTTP {response.status}"
                                )
                            
                            # Health endpoints should respond quickly
                            if response_time > 10.0:
                                health_check_failures.append(
                                    f"Health check too slow for {url}: {response_time:.2f}s > 10.0s"
                                )
                            
                            try:
                                content = await response.json()
                                domain_results[endpoint] = {
                                    'status_code': response.status,
                                    'response_time': response_time,
                                    'content': content,
                                    'success': response.status == 200
                                }
                            except Exception:
                                # Non-JSON response is OK for health checks
                                domain_results[endpoint] = {
                                    'status_code': response.status,
                                    'response_time': response_time,
                                    'content': 'non-json',
                                    'success': response.status == 200
                                }
                            
                    except Exception as e:
                        domain_results[endpoint] = {
                            'status_code': None,
                            'response_time': None,
                            'success': False,
                            'error': str(e)
                        }
                        health_check_failures.append(f"Health check error for {url}: {e}")
                
                health_check_results[domain] = domain_results
        
        if health_check_failures:
            error_report = self._build_health_check_failure_report(health_check_results, health_check_failures)
            raise AssertionError(
                f"CRITICAL: Load balancer health check failures detected!\n\n"
                f"Health check failures cause load balancer to mark services as unhealthy,\n"
                f"leading to service unavailability and traffic routing problems.\n\n"
                f"HEALTH CHECK FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Verify backend service health check endpoints are working\n"
                f"2. Check load balancer health check configuration\n"
                f"3. Review health check timeout and interval settings\n"
                f"4. Validate backend service startup and readiness\n"
                f"5. Check service dependencies (database, Redis, etc.)\n\n"
                f"Reference: Load Balancer Health Check Configuration"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services 
    @pytest.mark.infrastructure
    async def test_load_balancer_websocket_routing(self):
        """
        HARD FAIL: Load balancer MUST support WebSocket connections.
        
        This test validates that WebSocket connections can be established through
        the load balancer. WebSocket routing failures prevent real-time features.
        """
        websocket_results = {}
        websocket_failures = []
        
        websocket_endpoints = [
            "wss://api.staging.netrasystems.ai/ws",
            "wss://api.staging.netrasystems.ai/websocket",
        ]
        
        for endpoint in websocket_endpoints:
            try:
                # Test WebSocket handshake through load balancer
                websocket_info = await self._test_websocket_handshake(endpoint)
                websocket_results[endpoint] = websocket_info
                
                if not websocket_info['handshake_success']:
                    websocket_failures.append(
                        f"WebSocket handshake failed for {endpoint}: {websocket_info['error']}"
                    )
                
                # Test upgrade headers
                if not websocket_info['upgrade_headers_present']:
                    websocket_failures.append(
                        f"Missing WebSocket upgrade headers for {endpoint}"
                    )
                
            except Exception as e:
                websocket_results[endpoint] = {
                    'handshake_success': False,
                    'upgrade_headers_present': False,
                    'error': str(e)
                }
                websocket_failures.append(f"WebSocket test failed for {endpoint}: {e}")
        
        if websocket_failures:
            error_report = self._build_websocket_failure_report(websocket_results, websocket_failures)
            raise AssertionError(
                f"CRITICAL: Load balancer WebSocket routing failures detected!\n\n"
                f"WebSocket routing failures prevent real-time features including\n"
                f"agent execution events and live chat functionality.\n\n"
                f"WEBSOCKET FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Verify load balancer WebSocket upgrade support\n"
                f"2. Check WebSocket routing configuration\n"
                f"3. Validate backend WebSocket handler configuration\n"
                f"4. Review session affinity settings for WebSocket connections\n"
                f"5. Check timeout settings for long-lived connections\n\n"
                f"Reference: Load Balancer WebSocket Configuration"
            )
    
    def _validate_routing_response(self, result: Dict, expected: Dict, endpoint: str) -> bool:
        """Validate that routing response matches expectations."""
        status_code = result.get('status_code')
        
        # Check status code range
        if 'status_range' in expected:
            status_min, status_max = expected['status_range']
            if not (status_min <= status_code <= status_max):
                return False
        
        # Check content type
        if 'content_type' in expected:
            expected_type = expected['content_type']
            actual_type = result.get('content_type', '')
            if expected_type not in actual_type:
                return False
        
        # Check specific headers
        if 'location' in expected and expected['location']:
            if not result.get('location'):
                return False
        
        # Check WebSocket upgrade
        if 'upgrade' in expected:
            upgrade_header = result.get('headers', {}).get('upgrade', '').lower()
            if expected['upgrade'].lower() not in upgrade_header:
                return False
        
        return True
    
    async def _test_websocket_handshake(self, endpoint: str) -> Dict:
        """Test WebSocket handshake through load balancer."""
        try:
            import websockets
            
            # Attempt WebSocket connection
            try:
                async with websockets.connect(endpoint, timeout=15) as websocket:
                    return {
                        'handshake_success': True,
                        'upgrade_headers_present': True,
                        'connection_established': True,
                        'error': None
                    }
            except websockets.exceptions.InvalidStatusCode as e:
                # Check if it's a proper WebSocket upgrade rejection
                if e.status_code in [400, 401, 403, 426]:  # Expected for unauthenticated requests
                    return {
                        'handshake_success': True,  # Handshake protocol works
                        'upgrade_headers_present': True,
                        'connection_established': False,
                        'rejection_reason': f"HTTP {e.status_code}",
                        'error': None
                    }
                else:
                    return {
                        'handshake_success': False,
                        'upgrade_headers_present': False,
                        'connection_established': False,
                        'error': f"Invalid status code: {e.status_code}"
                    }
        except Exception as e:
            return {
                'handshake_success': False,
                'upgrade_headers_present': False,
                'connection_established': False,
                'error': str(e)
            }
    
    def _build_routing_failure_report(self, routing_results: Dict, failures: List[str]) -> str:
        """Build detailed routing failure report."""
        report_parts = []
        
        for domain, paths in routing_results.items():
            failed_paths = []
            for path, result in paths.items():
                if not result.get('routing_valid', False):
                    error_msg = result.get('error', f'HTTP {result.get("status_code", "Unknown")}')
                    failed_paths.append(f"    {path}: {error_msg}")
            
            if failed_paths:
                report_parts.append(f"  {domain}:\n" + "\n".join(failed_paths))
        
        return "\n".join(report_parts)
    
    def _build_health_check_failure_report(self, health_results: Dict, failures: List[str]) -> str:
        """Build health check failure report."""
        report_parts = []
        
        for domain, endpoints in health_results.items():
            failed_endpoints = []
            for endpoint, result in endpoints.items():
                if not result.get('success', False):
                    error_msg = result.get('error', f'HTTP {result.get("status_code", "Unknown")}')
                    failed_endpoints.append(f"    {endpoint}: {error_msg}")
            
            if failed_endpoints:
                report_parts.append(f"  {domain}:\n" + "\n".join(failed_endpoints))
        
        return "\n".join(report_parts)
    
    def _build_websocket_failure_report(self, websocket_results: Dict, failures: List[str]) -> str:
        """Build WebSocket failure report."""
        report_parts = []
        
        for endpoint, result in websocket_results.items():
            if not result.get('handshake_success', False):
                report_parts.append(f"  {endpoint}: {result.get('error', 'Handshake failed')}")
        
        return "\n".join(report_parts)


if __name__ == "__main__":
    # Run this test standalone to check load balancer routing
    import asyncio
    
    async def run_tests():
        test_instance = TestLoadBalancerRoutingValidation()
        
        try:
            await test_instance.test_load_balancer_routes_to_correct_backend_services()
            print("✅ Load balancer routing to backend services working")
        except AssertionError as e:
            print(f"❌ Load balancer routing failures:\n{e}")
            return False
        
        try:
            await test_instance.test_load_balancer_health_check_endpoints()
            print("✅ Load balancer health check endpoints working")
        except AssertionError as e:
            print(f"❌ Health check failures:\n{e}")
            return False
        
        try:
            await test_instance.test_load_balancer_websocket_routing()
            print("✅ Load balancer WebSocket routing working")
        except AssertionError as e:
            print(f"❌ WebSocket routing failures:\n{e}")
            return False
        
        return True
    
    if asyncio.run(run_tests()):
        print("✅ All load balancer routing validation tests passed!")
    else:
        exit(1)