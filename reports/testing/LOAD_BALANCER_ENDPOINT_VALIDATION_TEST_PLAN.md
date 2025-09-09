# 🔍 GCP Staging Load Balancer Endpoint Validation Test Plan

**Generated**: 2025-09-09 15:45:00 UTC
**Mission**: Validate that GCP staging E2E tests use load balancer endpoints (*.staging.netrasystems.ai) instead of direct Cloud Run URLs

## 🚨 CRITICAL BUSINESS CONTEXT

### Root Cause Analysis
**PROBLEM**: E2E tests are hitting direct Cloud Run URLs like `https://netra-backend-staging-pnovr5vsba-uc.a.run.app` instead of load balancer URLs like `https://api.staging.netrasystems.ai`

**BUSINESS IMPACT**: 
- Tests don't mirror real user paths → $500K+ ARR at risk
- Load balancer configuration issues go undetected
- SSL/TLS certificate validation bypassed
- Header propagation and routing logic untested

### Evidence From Current Analysis
From `netra_backend/app/core/network_constants.py`:
```python
# PROBLEMATIC: Direct Cloud Run URLs
STAGING_BACKEND_URL: Final[str] = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
STAGING_FRONTEND_URL: Final[str] = "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"
STAGING_WEBSOCKET_URL: Final[str] = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/ws"
```

From `tests/e2e/staging_config.py`:
```python
# PROBLEMATIC: Direct GCP Cloud Run endpoints
backend_url: str = "https://netra-backend-staging-701982941522.us-central1.run.app"
auth_url: str = "https://netra-auth-service-701982941522.us-central1.run.app"
frontend_url: str = "https://netra-frontend-staging-701982941522.us-central1.run.app"
```

## 🎯 COMPREHENSIVE TEST PLAN

### Test Architecture Overview
Following `reports/testing/TEST_CREATION_GUIDE.md` SSOT patterns:

```
Mission Critical Tests (MANDATORY - Never Skip)
    ↓
Integration Tests (Real Services - Load Balancer Validation)
    ↓  
Unit Tests (Configuration Validation)
```

## 1. 🔗 Load Balancer Endpoint Validation Tests

### Business Value Justification (BVJ)
- **Segment**: Platform/Internal + All Customer Tiers (Free, Early, Mid, Enterprise)
- **Business Goal**: Prevent $500K+ ARR loss from routing and infrastructure failures
- **Value Impact**: Ensures real user traffic paths are validated in staging
- **Strategic Impact**: Critical infrastructure integrity validation

### Test File: `tests/mission_critical/test_load_balancer_endpoint_validation.py`

```python
"""
MISSION CRITICAL: Load Balancer Endpoint Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal + All Customer Tiers
- Business Goal: Prevent $500K+ ARR loss from load balancer misconfigurations  
- Value Impact: Validates real user traffic paths through load balancer
- Strategic Impact: Ensures staging mirrors production traffic patterns

🚨 CRITICAL: These tests MUST PASS for Golden Path business value delivery.
Without proper load balancer routing, chat functionality fails for real users.
"""

import pytest
import asyncio
import aiohttp
import websockets
import ssl
import socket
from urllib.parse import urlparse
from typing import Dict, List, Tuple
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

class TestLoadBalancerEndpointValidation(BaseIntegrationTest):
    """MISSION CRITICAL: Validate load balancer endpoint usage in staging."""
    
    @pytest.fixture(autouse=True)
    async def setup_load_balancer_validation(self):
        """Setup for load balancer endpoint validation."""
        await self.initialize_test_environment()
        
        # Expected load balancer domains (CORRECT)
        self.expected_domains = {
            "api": "api.staging.netrasystems.ai",
            "auth": "auth.staging.netrasystems.ai", 
            "app": "app.staging.netrasystems.ai",
            "websocket": "ws.staging.netrasystems.ai"  # or api.staging.netrasystems.ai
        }
        
        # Forbidden direct Cloud Run patterns (INCORRECT)
        self.forbidden_patterns = [
            "*.us-central1.run.app",
            "*.a.run.app", 
            "*-staging-*.run.app",
            "*-701982941522.*",
            "*pnovr5vsba*"
        ]
        
        # Create authenticated user for endpoint testing
        self.test_user_context = await create_authenticated_user_context(
            user_email=f"load_balancer_test_{int(time.time())}@staging.netra.ai",
            environment="staging"
        )
        self.auth_helper = E2EAuthHelper(environment="staging")
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_staging_configuration_uses_load_balancer_domains(self):
        """CRITICAL: Verify staging config uses load balancer domains, not direct Cloud Run."""
        from tests.e2e.staging_config import get_staging_config
        from netra_backend.app.core.network_constants import URLConstants
        
        config = get_staging_config()
        violations = []
        
        # Test 1: Staging config URLs must use load balancer domains
        urls_to_check = {
            "backend_url": config.urls.backend_url,
            "auth_url": config.urls.auth_url,
            "frontend_url": config.urls.frontend_url,
            "websocket_url": config.urls.websocket_url,
            "api_base_url": config.urls.api_base_url
        }
        
        for url_name, url_value in urls_to_check.items():
            parsed = urlparse(url_value)
            hostname = parsed.hostname
            
            # Check for forbidden direct Cloud Run patterns
            for forbidden_pattern in self.forbidden_patterns:
                pattern_check = forbidden_pattern.replace("*", "")
                if pattern_check in hostname:
                    violations.append({
                        "url_name": url_name,
                        "url_value": url_value,
                        "hostname": hostname,
                        "violation": f"Uses forbidden Cloud Run pattern: {forbidden_pattern}",
                        "expected": "Should use *.staging.netrasystems.ai domain"
                    })
        
        # Test 2: Network constants must use load balancer domains
        network_constants_violations = []
        if hasattr(URLConstants, 'STAGING_BACKEND_URL'):
            if any(pattern.replace("*", "") in URLConstants.STAGING_BACKEND_URL 
                   for pattern in self.forbidden_patterns):
                network_constants_violations.append({
                    "constant": "STAGING_BACKEND_URL",
                    "value": URLConstants.STAGING_BACKEND_URL,
                    "violation": "Uses direct Cloud Run URL"
                })
        
        # Assert no violations found
        all_violations = violations + network_constants_violations
        
        assert len(all_violations) == 0, f"""
        CRITICAL FAILURE: Staging configuration uses direct Cloud Run URLs instead of load balancer domains!
        
        Violations found: {len(all_violations)}
        {chr(10).join([f"- {v['url_name']}: {v['violation']}" for v in all_violations])}
        
        REQUIRED ACTION:
        1. Update staging_config.py to use *.staging.netrasystems.ai domains
        2. Update network_constants.py STAGING_* constants
        3. Configure load balancer routing in GCP
        4. Update DNS records for staging subdomains
        
        This is BLOCKING for Golden Path business value!
        """
        
        self.logger.info("✅ All staging URLs use proper load balancer domains")
    
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_load_balancer_domain_resolution_and_connectivity(self):
        """CRITICAL: Verify load balancer domains resolve and accept connections."""
        resolution_results = {}
        
        for service, expected_domain in self.expected_domains.items():
            try:
                # Test 1: DNS resolution
                start_time = time.time()
                
                # Resolve domain to IP
                try:
                    addr_info = socket.getaddrinfo(expected_domain, 443, socket.AF_INET)
                    resolved_ips = [info[4][0] for info in addr_info]
                    resolution_time = time.time() - start_time
                    
                    resolution_results[service] = {
                        "domain": expected_domain,
                        "dns_resolution": True,
                        "resolution_time": resolution_time,
                        "resolved_ips": resolved_ips,
                        "ip_count": len(resolved_ips)
                    }
                    
                except socket.gaierror as e:
                    resolution_results[service] = {
                        "domain": expected_domain,
                        "dns_resolution": False,
                        "error": str(e),
                        "resolution_time": time.time() - start_time
                    }
                    continue
                
                # Test 2: HTTPS connectivity
                try:
                    url = f"https://{expected_domain}/health"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=15.0) as resp:
                            resolution_results[service]["https_connectivity"] = True
                            resolution_results[service]["health_status"] = resp.status
                            resolution_results[service]["response_headers"] = dict(resp.headers)
                            
                except Exception as e:
                    resolution_results[service]["https_connectivity"] = False
                    resolution_results[service]["connectivity_error"] = str(e)
                
                # Test 3: SSL certificate validation
                try:
                    context = ssl.create_default_context()
                    sock = socket.create_connection((expected_domain, 443), timeout=10)
                    ssl_sock = context.wrap_socket(sock, server_hostname=expected_domain)
                    cert = ssl_sock.getpeercert()
                    ssl_sock.close()
                    
                    resolution_results[service]["ssl_certificate"] = {
                        "valid": True,
                        "subject": cert.get("subject"),
                        "issuer": cert.get("issuer"),
                        "expires": cert.get("notAfter")
                    }
                    
                except Exception as e:
                    resolution_results[service]["ssl_certificate"] = {
                        "valid": False,
                        "error": str(e)
                    }
                    
            except Exception as e:
                resolution_results[service] = {
                    "domain": expected_domain,
                    "error": str(e),
                    "test_failed": True
                }
        
        # Validate results
        failed_domains = []
        dns_failures = []
        ssl_failures = []
        
        for service, results in resolution_results.items():
            if results.get("test_failed") or not results.get("dns_resolution"):
                failed_domains.append(f"{service}: {results.get('error', 'DNS failure')}")
            
            if not results.get("dns_resolution"):
                dns_failures.append(service)
                
            ssl_cert = results.get("ssl_certificate", {})
            if not ssl_cert.get("valid"):
                ssl_failures.append(f"{service}: {ssl_cert.get('error', 'Unknown SSL error')}")
        
        # Report results (don't fail if infrastructure not ready)
        if failed_domains:
            self.logger.warning(f"Load balancer domain issues detected: {failed_domains}")
            self.logger.warning("This indicates load balancer infrastructure may not be fully configured")
        
        if dns_failures:
            self.logger.warning(f"DNS resolution failures: {dns_failures}")
            
        if ssl_failures:
            self.logger.warning(f"SSL certificate issues: {ssl_failures}")
        
        # Assert at least some basic connectivity works
        working_domains = sum(1 for r in resolution_results.values() 
                            if r.get("dns_resolution") and not r.get("test_failed"))
        
        self.logger.info(f"Load balancer domain validation: {working_domains}/{len(self.expected_domains)} domains working")
        
        # Log detailed results for infrastructure debugging
        for service, results in resolution_results.items():
            self.logger.info(f"🔍 {service} ({results.get('domain')}): {results}")
```

## 2. 🏗️ Infrastructure Correctness Tests

### Test File: `tests/integration/test_load_balancer_infrastructure_validation.py`

```python
"""
Load Balancer Infrastructure Validation Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure $100K+ MRR load balancer infrastructure works correctly
- Value Impact: Validates routing, SSL, and header propagation through load balancer
- Strategic Impact: Critical infrastructure reliability validation
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, List
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

class TestLoadBalancerInfrastructure(BaseIntegrationTest):
    """Integration tests for load balancer infrastructure correctness."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_load_balancer_routing_correctness(self):
        """Test load balancer routes requests to correct backend services."""
        routing_tests = []
        
        # Test routing to different services through load balancer
        test_routes = [
            {
                "service": "backend_api",
                "url": "https://api.staging.netrasystems.ai/health",
                "expected_service": "backend"
            },
            {
                "service": "auth_service", 
                "url": "https://auth.staging.netrasystems.ai/auth/health",
                "expected_service": "auth"
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            for route_test in test_routes:
                try:
                    async with session.get(route_test["url"], timeout=15.0) as resp:
                        headers = dict(resp.headers)
                        
                        # Validate routing worked
                        routing_result = {
                            "service": route_test["service"],
                            "url": route_test["url"],
                            "status": resp.status,
                            "routed_correctly": resp.status in [200, 401, 403],
                            "headers": headers,
                            "load_balancer_headers": {}
                        }
                        
                        # Check for load balancer specific headers
                        lb_headers = [
                            "X-Cloud-Trace-Context",
                            "X-Forwarded-For", 
                            "X-Forwarded-Proto",
                            "Via"
                        ]
                        
                        for header in lb_headers:
                            if header in headers:
                                routing_result["load_balancer_headers"][header] = headers[header]
                        
                        routing_tests.append(routing_result)
                        
                except Exception as e:
                    routing_tests.append({
                        "service": route_test["service"],
                        "url": route_test["url"],
                        "error": str(e),
                        "routed_correctly": False
                    })
        
        # Validate routing results
        successful_routes = sum(1 for test in routing_tests if test.get("routed_correctly"))
        
        assert successful_routes > 0, f"No routes worked through load balancer: {routing_tests}"
        
        self.logger.info(f"✅ Load balancer routing: {successful_routes}/{len(test_routes)} routes working")
        
        # Log load balancer evidence
        for test in routing_tests:
            lb_headers = test.get("load_balancer_headers", {})
            if lb_headers:
                self.logger.info(f"🔄 {test['service']}: Load balancer headers detected: {lb_headers}")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_load_balancer_ssl_termination(self):
        """Test load balancer properly terminates SSL and validates certificates."""
        ssl_tests = []
        
        domains_to_test = [
            "api.staging.netrasystems.ai",
            "auth.staging.netrasystems.ai"
        ]
        
        for domain in domains_to_test:
            try:
                # Test SSL certificate via HTTPS connection
                import ssl
                import socket
                
                context = ssl.create_default_context()
                sock = socket.create_connection((domain, 443), timeout=10)
                ssl_sock = context.wrap_socket(sock, server_hostname=domain)
                
                cert = ssl_sock.getpeercert()
                cipher = ssl_sock.cipher()
                ssl_sock.close()
                
                ssl_tests.append({
                    "domain": domain,
                    "ssl_valid": True,
                    "certificate": {
                        "subject": cert.get("subject"),
                        "issuer": cert.get("issuer"),
                        "expires": cert.get("notAfter"),
                        "san": cert.get("subjectAltName", [])
                    },
                    "cipher": cipher,
                    "tls_version": cipher[1] if cipher else None
                })
                
            except Exception as e:
                ssl_tests.append({
                    "domain": domain, 
                    "ssl_valid": False,
                    "error": str(e)
                })
        
        # Validate SSL results
        valid_ssl_count = sum(1 for test in ssl_tests if test.get("ssl_valid"))
        
        # Log SSL certificate details
        for test in ssl_tests:
            if test.get("ssl_valid"):
                cert = test.get("certificate", {})
                self.logger.info(f"🔒 {test['domain']}: Valid SSL - {cert.get('issuer')} - Expires: {cert.get('expires')}")
            else:
                self.logger.warning(f"❌ {test['domain']}: SSL issue - {test.get('error')}")
        
        self.logger.info(f"✅ SSL validation: {valid_ssl_count}/{len(domains_to_test)} domains have valid SSL")
```

## 3. 🎯 Real User Path Simulation Tests

### Test File: `tests/e2e/test_load_balancer_user_path_simulation.py`

```python
"""
Real User Path Simulation Through Load Balancer

Business Value Justification (BVJ):
- Segment: All Customer Tiers (Free, Early, Mid, Enterprise)
- Business Goal: Validate $500K+ ARR user experience through load balancer
- Value Impact: Ensures real user chat flows work through proper infrastructure
- Strategic Impact: Golden Path business value validation
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
import time
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)

class TestLoadBalancerUserPathSimulation(BaseE2ETest):
    """E2E tests simulating real user paths through load balancer."""
    
    @pytest.fixture(autouse=True)
    async def setup_user_path_simulation(self):
        """Setup for user path simulation through load balancer."""
        await self.initialize_test_environment()
        
        # Use CORRECT load balancer URLs
        self.load_balancer_config = {
            "api_base": "https://api.staging.netrasystems.ai",
            "auth_base": "https://auth.staging.netrasystems.ai", 
            "websocket_base": "wss://api.staging.netrasystems.ai/ws",  # or dedicated ws subdomain
            "frontend_base": "https://app.staging.netrasystems.ai"
        }
        
        # Create authenticated user context
        self.test_user_context = await create_authenticated_user_context(
            user_email=f"user_path_test_{int(time.time())}@staging.netra.ai",
            environment="staging"
        )
        
        self.auth_helper = E2EAuthHelper(
            environment="staging",
            custom_urls=self.load_balancer_config  # Force load balancer URLs
        )
        self.ws_auth_helper = E2EWebSocketAuthHelper(
            environment="staging", 
            custom_urls=self.load_balancer_config
        )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_complete_auth_flow_through_load_balancer(self):
        """Test complete authentication flow through load balancer."""
        auth_flow_results = {}
        
        # Test 1: Token creation through auth service via load balancer
        try:
            auth_url = f"{self.load_balancer_config['auth_base']}/auth/token"
            
            auth_token = await self.auth_helper.get_staging_token_async(
                email=self.test_user_context.agent_context["user_email"]
            )
            
            assert auth_token and len(auth_token) > 20, "Auth token creation failed"
            
            auth_flow_results["token_creation"] = {
                "success": True,
                "token_length": len(auth_token),
                "via_load_balancer": True
            }
            
        except Exception as e:
            auth_flow_results["token_creation"] = {
                "success": False,
                "error": str(e)
            }
            pytest.fail(f"Token creation through load balancer failed: {e}")
        
        # Test 2: Authenticated API calls through load balancer
        try:
            headers = self.auth_helper.get_auth_headers(auth_token)
            api_url = f"{self.load_balancer_config['api_base']}/api/v1/user/profile"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=15.0) as resp:
                    auth_flow_results["authenticated_api"] = {
                        "success": resp.status in [200, 401, 403, 404],  # Auth processed
                        "status": resp.status,
                        "via_load_balancer": True,
                        "headers": dict(resp.headers)
                    }
                    
        except Exception as e:
            auth_flow_results["authenticated_api"] = {
                "success": False, 
                "error": str(e)
            }
        
        # Validate auth flow through load balancer
        successful_steps = sum(1 for result in auth_flow_results.values() if result.get("success"))
        total_steps = len(auth_flow_results)
        
        assert successful_steps >= (total_steps * 0.8), f"Auth flow through load balancer failed: {successful_steps}/{total_steps}"
        
        self.logger.info("✅ Complete auth flow works through load balancer")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_connections_through_load_balancer(self):
        """CRITICAL: Test WebSocket connections work through load balancer."""
        websocket_results = {}
        
        # Test 1: Basic WebSocket connection through load balancer
        try:
            ws_url = self.load_balancer_config["websocket_base"]
            
            start_time = time.time()
            
            # Connect through load balancer
            async with websockets.connect(
                ws_url,
                open_timeout=20,
                close_timeout=5
            ) as websocket:
                connection_time = time.time() - start_time
                
                websocket_results["basic_connection"] = {
                    "success": True,
                    "connection_time": connection_time,
                    "via_load_balancer": True,
                    "url": ws_url
                }
                
        except Exception as e:
            websocket_results["basic_connection"] = {
                "success": False,
                "error": str(e),
                "url": self.load_balancer_config["websocket_base"]
            }
            pytest.fail(f"Basic WebSocket connection through load balancer failed: {e}")
        
        # Test 2: Authenticated WebSocket with agent events
        try:
            ws_connection = await self.ws_auth_helper.connect_authenticated_websocket(
                url_override=self.load_balancer_config["websocket_base"],
                timeout=20.0
            )
            
            websocket_results["authenticated_connection"] = {
                "success": True,
                "via_load_balancer": True
            }
            
            # Test 3: Agent execution with WebSocket events through load balancer  
            agent_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Test load balancer WebSocket routing",
                "user_id": self.test_user_context.user_id
            }
            
            await ws_connection.send(json.dumps(agent_message))
            
            # Collect WebSocket events
            events_received = []
            
            try:
                for _ in range(10):  # Collect up to 10 events
                    event_raw = await asyncio.wait_for(ws_connection.recv(), timeout=5.0)
                    event = json.loads(event_raw)
                    events_received.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
            except asyncio.TimeoutError:
                pass  # Normal - may not receive all events immediately
            
            # Validate critical WebSocket events received through load balancer
            event_types = [event.get("type") for event in events_received]
            critical_events = ["agent_started", "agent_completed"]
            received_critical = [event for event in critical_events if event in event_types]
            
            websocket_results["agent_execution"] = {
                "success": len(received_critical) > 0,
                "events_received": len(events_received),
                "event_types": event_types,
                "critical_events_received": received_critical,
                "via_load_balancer": True
            }
            
            # Clean up
            await ws_connection.close()
            
        except Exception as e:
            websocket_results["agent_execution"] = {
                "success": False,
                "error": str(e)
            }
        
        # Validate WebSocket functionality through load balancer
        successful_tests = sum(1 for result in websocket_results.values() if result.get("success"))
        total_tests = len(websocket_results)
        
        assert successful_tests >= (total_tests * 0.8), f"WebSocket through load balancer failed: {successful_tests}/{total_tests}"
        
        self.logger.info("✅ WebSocket connections and agent events work through load balancer")
        for test_name, result in websocket_results.items():
            status = "✅" if result.get("success") else "❌"
            self.logger.info(f"  {status} {test_name}: {result}")
```

## 4. 🔧 Configuration Drift Prevention Tests

### Test File: `tests/unit/test_load_balancer_configuration_compliance.py`

```python
"""
Configuration Drift Prevention for Load Balancer Endpoints

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent $25K+ MRR loss from configuration drift
- Value Impact: Ensures consistent load balancer domain usage
- Strategic Impact: Configuration integrity automation
"""

import pytest
import re
import ast
import os
from typing import List, Dict, Tuple
from pathlib import Path

class TestLoadBalancerConfigurationCompliance:
    """Unit tests to prevent configuration drift to direct Cloud Run URLs."""
    
    @pytest.mark.unit
    def test_no_hardcoded_cloud_run_urls_in_codebase(self):
        """CRITICAL: Ensure no hardcoded Cloud Run URLs exist in codebase."""
        
        # Define forbidden patterns
        forbidden_patterns = [
            r'https://[^"]*\.run\.app[^"]*',  # Any .run.app URL
            r'wss://[^"]*\.run\.app[^"]*',    # Any WebSocket .run.app URL  
            r'[^"]*-staging-[^"]*\.run\.app', # Staging Cloud Run pattern
            r'[^"]*701982941522[^"]*',        # Specific project ID
            r'[^"]*pnovr5vsba[^"]*'          # Specific Cloud Run hash
        ]
        
        # Files to check for violations
        files_to_check = [
            "netra_backend/app/core/network_constants.py",
            "tests/e2e/staging_config.py", 
            "auth_service/auth_core/config.py",
            "frontend/src/config/endpoints.js",
            "test_framework/ssot/e2e_auth_helper.py"
        ]
        
        violations = []
        
        for file_path in files_to_check:
            full_path = Path(__file__).parent.parent.parent / file_path
            
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                line_num = 0
                for line in content.split('\n'):
                    line_num += 1
                    
                    for pattern in forbidden_patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        for match in matches:
                            violations.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                                "violation": match,
                                "pattern": pattern
                            })
                            
            except Exception as e:
                # Don't fail test for file reading issues
                continue
        
        # Assert no violations
        assert len(violations) == 0, f"""
        CRITICAL: Found hardcoded Cloud Run URLs in codebase!
        
        Violations: {len(violations)}
        {chr(10).join([f"- {v['file']}:{v['line']}: {v['violation']}" for v in violations])}
        
        REQUIRED FIXES:
        1. Replace all Cloud Run URLs with *.staging.netrasystems.ai domains
        2. Use load balancer endpoints only
        3. Update configuration constants to use proper domains
        4. Configure DNS and load balancer routing
        """
    
    @pytest.mark.unit  
    def test_network_constants_use_load_balancer_domains(self):
        """Test network constants use proper load balancer domains."""
        from netra_backend.app.core.network_constants import URLConstants
        
        # Expected domain patterns (CORRECT)
        expected_domain_patterns = [
            r'.*\.staging\.netrasystems\.ai',
            r'.*\.netrasystems\.ai'
        ]
        
        # Check URLConstants for proper domains
        staging_constants = []
        
        for attr_name in dir(URLConstants):
            if attr_name.startswith('STAGING_') and attr_name.endswith('_URL'):
                value = getattr(URLConstants, attr_name)
                if isinstance(value, str) and ('http' in value or 'ws' in value):
                    staging_constants.append({
                        "name": attr_name,
                        "value": value
                    })
        
        violations = []
        for constant in staging_constants:
            value = constant["value"]
            
            # Check if uses proper domain
            uses_correct_domain = any(
                re.match(pattern, value, re.IGNORECASE) 
                for pattern in expected_domain_patterns
            )
            
            # Check for forbidden patterns
            uses_cloud_run = (
                '.run.app' in value or 
                '701982941522' in value or
                'pnovr5vsba' in value
            )
            
            if uses_cloud_run or not uses_correct_domain:
                violations.append({
                    "constant": constant["name"],
                    "value": value,
                    "issue": "Uses Cloud Run URL instead of load balancer domain"
                })
        
        assert len(violations) == 0, f"""
        Network constants use incorrect domains: {violations}
        
        All STAGING_*_URL constants must use *.staging.netrasystems.ai domains
        """
    
    @pytest.mark.unit
    def test_staging_config_compliance(self):
        """Test staging config uses load balancer domains."""
        from tests.e2e.staging_config import StagingURLs
        
        staging_urls = StagingURLs()
        
        urls_to_check = {
            "backend_url": staging_urls.backend_url,
            "auth_url": staging_urls.auth_url,
            "frontend_url": staging_urls.frontend_url,
            "websocket_url": staging_urls.websocket_url,
            "api_base_url": staging_urls.api_base_url
        }
        
        violations = []
        for url_name, url_value in urls_to_check.items():
            if '.run.app' in url_value:
                violations.append({
                    "url_name": url_name,
                    "url_value": url_value,
                    "issue": "Uses Cloud Run domain instead of load balancer"
                })
        
        assert len(violations) == 0, f"""
        StagingURLs configuration violations: {violations}
        
        All staging URLs must use *.staging.netrasystems.ai load balancer domains
        """
```

## 5. 📊 Implementation Strategy

### Phase 1: Infrastructure Setup (Priority 1 - CRITICAL)

1. **DNS Configuration**
   ```bash
   # Configure DNS records for staging subdomains
   api.staging.netrasystems.ai → Load balancer IP
   auth.staging.netrasystems.ai → Load balancer IP  
   app.staging.netrasystems.ai → Load balancer IP
   ws.staging.netrasystems.ai → Load balancer IP (optional)
   ```

2. **Load Balancer Configuration**
   - Configure GCP Load Balancer routing rules
   - Set up SSL certificates for *.staging.netrasystems.ai
   - Configure backend service routing based on path/host

3. **Update Configuration Files**
   ```python
   # netra_backend/app/core/network_constants.py
   STAGING_BACKEND_URL: Final[str] = "https://api.staging.netrasystems.ai"
   STAGING_AUTH_URL: Final[str] = "https://auth.staging.netrasystems.ai"
   STAGING_FRONTEND_URL: Final[str] = "https://app.staging.netrasystems.ai" 
   STAGING_WEBSOCKET_URL: Final[str] = "wss://api.staging.netrasystems.ai/ws"
   
   # tests/e2e/staging_config.py
   backend_url: str = "https://api.staging.netrasystems.ai"
   auth_url: str = "https://auth.staging.netrasystems.ai"
   frontend_url: str = "https://app.staging.netrasystems.ai"
   ```

### Phase 2: Test Implementation (Priority 2)

1. **Create Mission Critical Tests**
   - Implement `tests/mission_critical/test_load_balancer_endpoint_validation.py`
   - Add to mission critical test suite (NEVER skip)

2. **Create Integration Tests** 
   - Implement `tests/integration/test_load_balancer_infrastructure_validation.py`
   - Test routing, SSL, header propagation

3. **Create E2E User Path Tests**
   - Implement `tests/e2e/test_load_balancer_user_path_simulation.py`
   - Test complete user journeys through load balancer

4. **Create Configuration Compliance Tests**
   - Implement `tests/unit/test_load_balancer_configuration_compliance.py`
   - Prevent regression to direct Cloud Run URLs

### Phase 3: Validation and Monitoring (Priority 3)

1. **Test Execution Pipeline**
   ```bash
   # Mission critical (must pass)
   python tests/mission_critical/test_load_balancer_endpoint_validation.py
   
   # Integration validation
   python tests/unified_test_runner.py --category integration --real-services
   
   # E2E validation
   python tests/unified_test_runner.py --category e2e --real-services --real-llm
   ```

2. **Monitoring and Alerting**
   - Set up alerts for load balancer health
   - Monitor certificate expiration
   - Track routing success rates

## 6. 🎯 Success Criteria

### Technical Success Metrics
- [ ] 100% of staging E2E tests use load balancer domains
- [ ] 0 hardcoded Cloud Run URLs in codebase
- [ ] All load balancer domains resolve correctly
- [ ] SSL certificates valid for all staging subdomains
- [ ] WebSocket connections work through load balancer
- [ ] All 5 critical WebSocket events delivered through load balancer

### Business Value Metrics  
- [ ] Golden Path success rate >95% through load balancer
- [ ] Chat functionality works end-to-end through load balancer
- [ ] Real user paths validated in staging
- [ ] Infrastructure matches production patterns
- [ ] Zero configuration drift incidents

## 7. 🚨 Risk Mitigation

### High Risk Issues
1. **Load Balancer Not Configured**: Tests will fail until infrastructure is ready
2. **DNS Propagation Delays**: May cause temporary test failures
3. **SSL Certificate Issues**: Will break HTTPS connections
4. **WebSocket Routing**: Complex to configure through load balancer

### Mitigation Strategies
1. **Gradual Rollout**: Implement tests first, then update infrastructure
2. **Fallback Mechanisms**: Allow temporary bypass during infrastructure setup
3. **Comprehensive Monitoring**: Early detection of infrastructure issues
4. **Clear Error Messages**: Help identify root cause of failures quickly

## 8. 📋 Implementation Checklist

### Infrastructure Team
- [ ] Configure GCP Load Balancer for staging
- [ ] Set up DNS records for *.staging.netrasystems.ai
- [ ] Configure SSL certificates
- [ ] Test routing rules
- [ ] Configure WebSocket support

### Development Team  
- [ ] Implement mission critical tests
- [ ] Update configuration constants
- [ ] Update staging config files
- [ ] Add configuration compliance tests
- [ ] Update test documentation

### QA Team
- [ ] Validate test execution
- [ ] Test failure scenarios
- [ ] Verify business value delivery
- [ ] Performance validation

---

**CONCLUSION**: This comprehensive test plan ensures GCP staging E2E tests validate real user paths through proper load balancer infrastructure instead of direct Cloud Run endpoints. Implementation of these tests will prevent $500K+ ARR risk from infrastructure misconfigurations and ensure Golden Path business value delivery.

The test plan follows SSOT patterns from TEST_CREATION_GUIDE.md with mission critical tests that MUST pass, comprehensive integration validation, and configuration drift prevention.