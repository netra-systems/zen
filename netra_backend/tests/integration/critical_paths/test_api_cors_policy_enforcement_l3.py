"""API CORS Policy Enforcement L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (browser-based client support)
- Business Goal: Enable secure cross-origin requests for web applications
- Value Impact: Supports modern web architecture and security compliance
- Strategic Impact: $15K MRR protection through proper CORS handling

Critical Path: Preflight request -> CORS validation -> Policy enforcement -> Header injection -> Response delivery
Coverage: CORS policies, preflight handling, origin validation, header management, security compliance
"""

import pytest
import asyncio
import time
import uuid
import logging
import aiohttp
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CorsPolicy:
    """CORS policy configuration."""
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    exposed_headers: List[str]
    allow_credentials: bool
    max_age: int  # Preflight cache duration in seconds


class ApiCorsManager:
    """Manages L3 API CORS policy tests with real HTTP CORS validation."""
    
    def __init__(self):
        self.test_server = None
        self.cors_policies = {}
        self.cors_requests = []
        self.policy_violations = []
        self.preflight_cache = {}
        
    async def initialize_cors_testing(self):
        """Initialize CORS testing environment."""
        try:
            # Configure CORS policies for different endpoints
            await self.setup_cors_policies()
            
            # Start test server with CORS middleware
            await self.start_cors_enabled_server()
            
            logger.info("CORS testing environment initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize CORS testing: {e}")
            raise
    
    async def setup_cors_policies(self):
        """Configure CORS policies for different API endpoints."""
        self.cors_policies = {
            "/api/v1/public": CorsPolicy(
                allowed_origins=["*"],
                allowed_methods=["GET", "POST", "OPTIONS"],
                allowed_headers=["Content-Type", "Authorization", "X-Requested-With"],
                exposed_headers=["X-Total-Count", "X-Rate-Limit"],
                allow_credentials=False,
                max_age=3600
            ),
            "/api/v1/auth": CorsPolicy(
                allowed_origins=["https://app.netrasystems.ai", "https://staging.netrasystems.ai"],
                allowed_methods=["GET", "POST", "OPTIONS"],
                allowed_headers=["Content-Type", "Authorization"],
                exposed_headers=["X-Auth-Token"],
                allow_credentials=True,
                max_age=1800
            ),
            "/api/v1/admin": CorsPolicy(
                allowed_origins=["https://admin.netrasystems.ai"],
                allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allowed_headers=["Content-Type", "Authorization", "X-Admin-Key"],
                exposed_headers=["X-Operation-Status"],
                allow_credentials=True,
                max_age=600
            ),
            "/api/v1/webhooks": CorsPolicy(
                allowed_origins=[],  # No CORS for webhooks
                allowed_methods=["POST"],
                allowed_headers=["Content-Type"],
                exposed_headers=[],
                allow_credentials=False,
                max_age=0
            ),
            "/api/v1/embed": CorsPolicy(
                allowed_origins=["*"],
                allowed_methods=["GET", "POST", "OPTIONS"],
                allowed_headers=["Content-Type", "X-API-Key"],
                exposed_headers=["X-Embed-Version"],
                allow_credentials=False,
                max_age=86400  # 24 hours
            )
        }
    
    async def start_cors_enabled_server(self):
        """Start test server with CORS middleware."""
        from aiohttp import web
        from aiohttp_cors import setup as cors_setup, ResourceOptions
        
        async def cors_middleware(request, handler):
            """Custom CORS middleware for testing."""
            start_time = time.time()
            
            # Find matching CORS policy
            cors_policy = await self.find_cors_policy(request.path)
            
            if not cors_policy:
                # No CORS policy - proceed normally
                return await handler(request)
            
            origin = request.headers.get("Origin", "")
            method = request.method
            
            # Handle preflight requests
            if method == "OPTIONS":
                return await self.handle_preflight_request(request, cors_policy, origin)
            
            # Handle actual request with CORS
            response = await handler(request)
            
            # Apply CORS headers to response
            await self.apply_cors_headers(response, cors_policy, origin, request)
            
            # Record CORS request
            self.record_cors_request(request, cors_policy, origin, time.time() - start_time)
            
            return response
        
        async def handle_public_api(request):
            """Handle public API requests."""
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "endpoint": "public",
                    "method": request.method,
                    "timestamp": time.time(),
                    "data": "Public API response"
                }
            )
        
        async def handle_auth_api(request):
            """Handle auth API requests."""
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "endpoint": "auth",
                    "method": request.method,
                    "timestamp": time.time(),
                    "token": "mock_auth_token_12345"
                }
            )
        
        async def handle_admin_api(request):
            """Handle admin API requests."""
            return web.Response(
                status=200,
                headers={
                    "Content-Type": "application/json",
                    "X-Operation-Status": "success"
                },
                json={
                    "endpoint": "admin",
                    "method": request.method,
                    "timestamp": time.time(),
                    "admin_data": "Sensitive admin information"
                }
            )
        
        async def handle_webhooks(request):
            """Handle webhook requests."""
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "webhook_received": True,
                    "timestamp": time.time()
                }
            )
        
        async def handle_embed_api(request):
            """Handle embed API requests."""
            return web.Response(
                status=200,
                headers={
                    "Content-Type": "application/json",
                    "X-Embed-Version": "1.0"
                },
                json={
                    "endpoint": "embed",
                    "embeddable": True,
                    "content": "Embeddable widget content"
                }
            )
        
        app = web.Application(middlewares=[cors_middleware])
        
        # Register routes
        app.router.add_route('*', '/api/v1/public', handle_public_api)
        app.router.add_route('*', '/api/v1/public/{path:.*}', handle_public_api)
        app.router.add_route('*', '/api/v1/auth', handle_auth_api)
        app.router.add_route('*', '/auth/{path:.*}', handle_auth_api)
        app.router.add_route('*', '/api/v1/admin', handle_admin_api)
        app.router.add_route('*', '/api/v1/admin/{path:.*}', handle_admin_api)
        app.router.add_post('/api/v1/webhooks', handle_webhooks)
        app.router.add_route('*', '/api/v1/embed', handle_embed_api)
        app.router.add_route('*', '/api/v1/embed/{path:.*}', handle_embed_api)
        
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"CORS-enabled server started on {self.test_server.sockets[0].getsockname()}")
    
    async def find_cors_policy(self, path: str) -> Optional[CorsPolicy]:
        """Find CORS policy for given path."""
        for pattern, policy in self.cors_policies.items():
            if path.startswith(pattern):
                return policy
        return None
    
    async def handle_preflight_request(self, request, cors_policy: CorsPolicy, origin: str):
        """Handle CORS preflight OPTIONS request."""
        from aiohttp import web
        
        # Validate origin
        if not self.is_origin_allowed(origin, cors_policy.allowed_origins):
            self.record_policy_violation(
                request.path, origin, "origin_not_allowed", "Preflight request from disallowed origin"
            )
            return web.Response(status=403, text="Origin not allowed")
        
        # Get requested method and headers
        requested_method = request.headers.get("Access-Control-Request-Method", "")
        requested_headers = request.headers.get("Access-Control-Request-Headers", "").split(",")
        requested_headers = [h.strip() for h in requested_headers if h.strip()]
        
        # Validate requested method
        if requested_method and requested_method not in cors_policy.allowed_methods:
            self.record_policy_violation(
                request.path, origin, "method_not_allowed", f"Method {requested_method} not allowed"
            )
            return web.Response(status=405, text="Method not allowed")
        
        # Validate requested headers
        for header in requested_headers:
            if header and not self.is_header_allowed(header, cors_policy.allowed_headers):
                self.record_policy_violation(
                    request.path, origin, "header_not_allowed", f"Header {header} not allowed"
                )
                return web.Response(status=400, text="Header not allowed")
        
        # Build preflight response headers
        response_headers = {
            "Access-Control-Allow-Origin": origin if origin != "*" else "*",
            "Access-Control-Allow-Methods": ",".join(cors_policy.allowed_methods),
            "Access-Control-Allow-Headers": ",".join(cors_policy.allowed_headers),
            "Access-Control-Max-Age": str(cors_policy.max_age)
        }
        
        if cors_policy.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"
        
        # Cache preflight response
        cache_key = f"{origin}:{requested_method}:{':'.join(requested_headers)}"
        self.preflight_cache[cache_key] = {
            "expires_at": time.time() + cors_policy.max_age,
            "policy": cors_policy,
            "origin": origin
        }
        
        return web.Response(status=200, headers=response_headers)
    
    async def apply_cors_headers(self, response, cors_policy: CorsPolicy, origin: str, request):
        """Apply CORS headers to actual response."""
        # Validate origin for actual request
        if not self.is_origin_allowed(origin, cors_policy.allowed_origins):
            self.record_policy_violation(
                request.path, origin, "origin_not_allowed", "Actual request from disallowed origin"
            )
            return
        
        # Set CORS headers
        if origin and origin != "*":
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in cors_policy.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        if cors_policy.exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = ",".join(cors_policy.exposed_headers)
        
        if cors_policy.allow_credentials and origin != "*":
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add Vary header for origin-specific responses
        if "*" not in cors_policy.allowed_origins:
            response.headers["Vary"] = "Origin"
    
    def is_origin_allowed(self, origin: str, allowed_origins: List[str]) -> bool:
        """Check if origin is allowed by policy."""
        if not origin:
            return True  # Same-origin requests don't need CORS
        
        if "*" in allowed_origins:
            return True
        
        if origin in allowed_origins:
            return True
        
        # Check for wildcard subdomain matching
        for allowed in allowed_origins:
            if allowed.startswith("*."):
                domain = allowed[2:]
                if origin.endswith(f".{domain}") or origin == f"https://{domain}":
                    return True
        
        return False
    
    def is_header_allowed(self, header: str, allowed_headers: List[str]) -> bool:
        """Check if header is allowed by policy."""
        header_lower = header.lower()
        
        # Simple headers are always allowed
        simple_headers = ["accept", "accept-language", "content-language", "content-type"]
        if header_lower in simple_headers:
            return True
        
        # Check against allowed headers
        for allowed in allowed_headers:
            if header_lower == allowed.lower():
                return True
        
        return False
    
    def record_cors_request(self, request, cors_policy: CorsPolicy, origin: str, processing_time: float):
        """Record CORS request for metrics."""
        cors_request = {
            "path": request.path,
            "method": request.method,
            "origin": origin,
            "policy_pattern": self.find_policy_pattern(request.path),
            "processing_time": processing_time,
            "timestamp": time.time(),
            "headers": dict(request.headers)
        }
        self.cors_requests.append(cors_request)
    
    def record_policy_violation(self, path: str, origin: str, violation_type: str, message: str):
        """Record CORS policy violation."""
        violation = {
            "path": path,
            "origin": origin,
            "violation_type": violation_type,
            "message": message,
            "timestamp": time.time()
        }
        self.policy_violations.append(violation)
    
    def find_policy_pattern(self, path: str) -> str:
        """Find policy pattern that matches path."""
        for pattern in self.cors_policies.keys():
            if path.startswith(pattern):
                return pattern
        return "unknown"
    
    async def make_cors_request(self, path: str, method: str = "GET", origin: str = "",
                              headers: Optional[Dict[str, str]] = None,
                              preflight: bool = False) -> Dict[str, Any]:
        """Make CORS request to test server."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        request_headers = headers or {}
        if origin:
            request_headers["Origin"] = origin
        
        if preflight:
            request_headers["Access-Control-Request-Method"] = method
            if "Access-Control-Request-Headers" not in request_headers:
                request_headers["Access-Control-Request-Headers"] = "Content-Type"
            method = "OPTIONS"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                request_method = getattr(session, method.lower())
                
                async with request_method(url, headers=request_headers) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "cors_headers": self.extract_cors_headers(response.headers),
                        "origin": origin,
                        "method": method
                    }
                    
                    if response.status == 200:
                        try:
                            result["body"] = await response.json()
                        except:
                            result["body"] = await response.text()
                    else:
                        result["body"] = await response.text()
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e),
                "origin": origin,
                "method": method
            }
    
    def extract_cors_headers(self, response_headers: Dict[str, str]) -> Dict[str, str]:
        """Extract CORS-related headers from response."""
        cors_headers = {}
        
        cors_header_names = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers",
            "Access-Control-Expose-Headers",
            "Access-Control-Allow-Credentials",
            "Access-Control-Max-Age",
            "Vary"
        ]
        
        for header_name in cors_header_names:
            if header_name in response_headers:
                cors_headers[header_name] = response_headers[header_name]
        
        return cors_headers
    
    async def test_cors_policy_compliance(self, endpoint: str, 
                                        test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test CORS policy compliance with multiple scenarios."""
        results = []
        
        for scenario in test_scenarios:
            origin = scenario.get("origin", "")
            method = scenario.get("method", "GET")
            expected_allowed = scenario.get("expected_allowed", True)
            headers = scenario.get("headers", {})
            
            # Test preflight if needed
            if method not in ["GET", "HEAD", "POST"] or headers:
                preflight_result = await self.make_cors_request(
                    endpoint, method, origin, headers, preflight=True
                )
                scenario_result = {
                    "scenario": scenario,
                    "preflight_result": preflight_result,
                    "preflight_allowed": preflight_result["status_code"] == 200
                }
                
                # If preflight fails, don't make actual request
                if preflight_result["status_code"] != 200:
                    scenario_result["actual_result"] = None
                    scenario_result["actual_allowed"] = False
                else:
                    # Make actual request
                    actual_result = await self.make_cors_request(endpoint, method, origin, headers)
                    scenario_result["actual_result"] = actual_result
                    scenario_result["actual_allowed"] = actual_result["status_code"] == 200
            else:
                # Simple request - no preflight needed
                actual_result = await self.make_cors_request(endpoint, method, origin, headers)
                scenario_result = {
                    "scenario": scenario,
                    "preflight_result": None,
                    "preflight_allowed": True,
                    "actual_result": actual_result,
                    "actual_allowed": actual_result["status_code"] == 200
                }
            
            # Check if result matches expectation
            scenario_result["expectation_met"] = (
                scenario_result["actual_allowed"] == expected_allowed
            )
            
            results.append(scenario_result)
        
        # Calculate compliance score
        compliant_results = [r for r in results if r["expectation_met"]]
        compliance_score = len(compliant_results) / len(results) * 100 if results else 0
        
        return {
            "endpoint": endpoint,
            "total_scenarios": len(results),
            "compliant_scenarios": len(compliant_results),
            "compliance_score": compliance_score,
            "results": results
        }
    
    async def get_cors_metrics(self) -> Dict[str, Any]:
        """Get comprehensive CORS metrics."""
        total_requests = len(self.cors_requests)
        total_violations = len(self.policy_violations)
        
        if total_requests == 0:
            return {"total_requests": 0, "violations": 0}
        
        # Origin breakdown
        origin_breakdown = {}
        for request in self.cors_requests:
            origin = request["origin"] or "same-origin"
            origin_breakdown[origin] = origin_breakdown.get(origin, 0) + 1
        
        # Policy pattern breakdown
        pattern_breakdown = {}
        for request in self.cors_requests:
            pattern = request["policy_pattern"]
            pattern_breakdown[pattern] = pattern_breakdown.get(pattern, 0) + 1
        
        # Violation type breakdown
        violation_breakdown = {}
        for violation in self.policy_violations:
            vtype = violation["violation_type"]
            violation_breakdown[vtype] = violation_breakdown.get(vtype, 0) + 1
        
        # Response time statistics
        response_times = [r["processing_time"] for r in self.cors_requests]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_requests": total_requests,
            "total_violations": total_violations,
            "violation_rate": total_violations / total_requests * 100 if total_requests > 0 else 0,
            "average_response_time": avg_response_time,
            "configured_policies": len(self.cors_policies),
            "preflight_cache_size": len(self.preflight_cache),
            "origin_breakdown": origin_breakdown,
            "pattern_breakdown": pattern_breakdown,
            "violation_breakdown": violation_breakdown
        }
    
    async def cleanup(self):
        """Clean up CORS testing resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def cors_manager():
    """Create CORS manager for L3 testing."""
    manager = ApiCorsManager()
    await manager.initialize_cors_testing()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_public_api_wildcard_cors(cors_manager):
    """Test public API with wildcard CORS policy."""
    test_scenarios = [
        {
            "origin": "https://example.com",
            "method": "GET",
            "expected_allowed": True
        },
        {
            "origin": "https://any-domain.com",
            "method": "POST",
            "expected_allowed": True
        },
        {
            "origin": "http://localhost:3000",
            "method": "GET",
            "expected_allowed": True
        }
    ]
    
    compliance_result = await cors_manager.test_cors_policy_compliance(
        "/api/v1/public", test_scenarios
    )
    
    assert compliance_result["compliance_score"] == 100
    assert compliance_result["compliant_scenarios"] == 3
    
    # Check CORS headers in responses
    for result in compliance_result["results"]:
        actual_result = result["actual_result"]
        cors_headers = actual_result["cors_headers"]
        
        assert "Access-Control-Allow-Origin" in cors_headers
        assert cors_headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_auth_api_restricted_origins(cors_manager):
    """Test auth API with restricted origin policy."""
    test_scenarios = [
        {
            "origin": "https://app.netrasystems.ai",
            "method": "POST",
            "expected_allowed": True
        },
        {
            "origin": "https://staging.netrasystems.ai",
            "method": "GET",
            "expected_allowed": True
        },
        {
            "origin": "https://malicious.com",
            "method": "POST",
            "expected_allowed": False
        },
        {
            "origin": "http://app.netrasystems.ai",  # Wrong protocol
            "method": "GET",
            "expected_allowed": False
        }
    ]
    
    compliance_result = await cors_manager.test_cors_policy_compliance(
        "/api/v1/auth", test_scenarios
    )
    
    assert compliance_result["compliance_score"] == 100
    
    # Check that allowed origins work
    allowed_results = [r for r in compliance_result["results"] 
                      if r["scenario"]["expected_allowed"]]
    for result in allowed_results:
        actual_result = result["actual_result"]
        assert actual_result["status_code"] == 200
        
        cors_headers = actual_result["cors_headers"]
        assert "Access-Control-Allow-Credentials" in cors_headers
        assert cors_headers["Access-Control-Allow-Credentials"] == "true"
    
    # Check that disallowed origins are blocked
    blocked_results = [r for r in compliance_result["results"] 
                      if not r["scenario"]["expected_allowed"]]
    for result in blocked_results:
        # Should be blocked at preflight or actual request
        if result["preflight_result"]:
            assert result["preflight_result"]["status_code"] in [403, 405]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_preflight_request_handling(cors_manager):
    """Test CORS preflight request handling."""
    # Test valid preflight
    preflight_result = await cors_manager.make_cors_request(
        "/api/v1/public",
        method="POST",
        origin="https://example.com",
        headers={"Access-Control-Request-Headers": "Content-Type,Authorization"},
        preflight=True
    )
    
    assert preflight_result["status_code"] == 200
    
    cors_headers = preflight_result["cors_headers"]
    assert "Access-Control-Allow-Origin" in cors_headers
    assert "Access-Control-Allow-Methods" in cors_headers
    assert "Access-Control-Allow-Headers" in cors_headers
    assert "Access-Control-Max-Age" in cors_headers
    
    # Check that allowed methods include POST
    allowed_methods = cors_headers["Access-Control-Allow-Methods"]
    assert "POST" in allowed_methods
    
    # Check max age
    max_age = int(cors_headers["Access-Control-Max-Age"])
    assert max_age > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_admin_api_strict_policy(cors_manager):
    """Test admin API with strict CORS policy."""
    test_scenarios = [
        {
            "origin": "https://admin.netrasystems.ai",
            "method": "DELETE",
            "expected_allowed": True
        },
        {
            "origin": "https://app.netrasystems.ai",  # Wrong origin for admin
            "method": "GET",
            "expected_allowed": False
        },
        {
            "origin": "https://admin.netrasystems.ai",
            "method": "PATCH",  # Method not in allowed list
            "expected_allowed": False
        }
    ]
    
    compliance_result = await cors_manager.test_cors_policy_compliance(
        "/api/v1/admin", test_scenarios
    )
    
    assert compliance_result["compliance_score"] == 100
    
    # Check successful admin request
    admin_results = [r for r in compliance_result["results"] 
                    if r["scenario"]["origin"] == "https://admin.netrasystems.ai" 
                    and r["scenario"]["method"] == "DELETE"]
    
    if admin_results:
        result = admin_results[0]
        actual_result = result["actual_result"]
        assert actual_result["status_code"] == 200
        
        # Check exposed headers
        cors_headers = actual_result["cors_headers"]
        if "Access-Control-Expose-Headers" in cors_headers:
            exposed_headers = cors_headers["Access-Control-Expose-Headers"]
            assert "X-Operation-Status" in exposed_headers


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_webhook_no_cors_policy(cors_manager):
    """Test webhook endpoint with no CORS policy."""
    # Webhooks should not have CORS headers
    result = await cors_manager.make_cors_request(
        "/api/v1/webhooks",
        method="POST",
        origin="https://external-service.com"
    )
    
    assert result["status_code"] == 200
    
    cors_headers = result["cors_headers"]
    # Should not have CORS headers
    assert "Access-Control-Allow-Origin" not in cors_headers


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_embed_api_permissive_policy(cors_manager):
    """Test embed API with permissive CORS policy for embeddable content."""
    test_scenarios = [
        {
            "origin": "https://customer-site.com",
            "method": "GET",
            "expected_allowed": True
        },
        {
            "origin": "https://another-site.org",
            "method": "POST",
            "expected_allowed": True
        }
    ]
    
    compliance_result = await cors_manager.test_cors_policy_compliance(
        "/api/v1/embed", test_scenarios
    )
    
    assert compliance_result["compliance_score"] == 100
    
    # Check that all requests succeed and have proper CORS headers
    for result in compliance_result["results"]:
        actual_result = result["actual_result"]
        assert actual_result["status_code"] == 200
        
        cors_headers = actual_result["cors_headers"]
        assert cors_headers["Access-Control-Allow-Origin"] == "*"
        
        # Check for exposed headers
        if "Access-Control-Expose-Headers" in cors_headers:
            assert "X-Embed-Version" in cors_headers["Access-Control-Expose-Headers"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_complex_preflight_scenarios(cors_manager):
    """Test complex preflight scenarios with custom headers."""
    # Test preflight with custom headers
    complex_preflight = await cors_manager.make_cors_request(
        "/api/v1/auth",
        method="POST",
        origin="https://app.netrasystems.ai",
        headers={
            "Access-Control-Request-Headers": "Content-Type,Authorization,X-Custom-Header"
        },
        preflight=True
    )
    
    # Should succeed for allowed origin but may restrict custom header
    assert complex_preflight["status_code"] in [200, 400]
    
    if complex_preflight["status_code"] == 200:
        cors_headers = complex_preflight["cors_headers"]
        allowed_headers = cors_headers.get("Access-Control-Allow-Headers", "")
        
        # Should include standard headers
        assert "Content-Type" in allowed_headers
        assert "Authorization" in allowed_headers


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cors_policy_violation_tracking(cors_manager):
    """Test tracking of CORS policy violations."""
    # Make requests that should violate policies
    violation_scenarios = [
        ("/api/v1/auth", "https://malicious.com", "GET"),
        ("/api/v1/admin", "https://wrong-admin.com", "POST"),
        ("/api/v1/auth", "https://app.netrasystems.ai", "PATCH")  # Wrong method
    ]
    
    for endpoint, origin, method in violation_scenarios:
        await cors_manager.make_cors_request(endpoint, method, origin, preflight=True)
        await cors_manager.make_cors_request(endpoint, method, origin)
    
    # Check violations were recorded
    metrics = await cors_manager.get_cors_metrics()
    
    assert metrics["total_violations"] > 0
    assert "violation_breakdown" in metrics
    
    # Should have different types of violations
    violation_types = list(metrics["violation_breakdown"].keys())
    assert len(violation_types) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cors_performance_requirements(cors_manager):
    """Test CORS middleware performance."""
    # Test response times with CORS
    response_times = []
    
    for i in range(20):
        result = await cors_manager.make_cors_request(
            "/api/v1/public",
            "GET",
            "https://example.com"
        )
        if result["status_code"] == 200:
            response_times.append(result["response_time"])
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # CORS should add minimal overhead
    assert avg_response_time < 0.2  # Less than 200ms average
    
    # Test concurrent CORS requests
    concurrent_tasks = []
    for i in range(15):
        task = cors_manager.make_cors_request(
            "/api/v1/public",
            "GET", 
            f"https://example{i}.com"
        )
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    assert concurrent_duration < 2.0  # 15 requests in < 2 seconds
    
    successful_results = [r for r in concurrent_results if r["status_code"] == 200]
    assert len(successful_results) >= 12  # Most should succeed


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_cors_metrics_accuracy(cors_manager):
    """Test accuracy of CORS metrics collection."""
    # Generate test traffic
    test_requests = [
        ("/api/v1/public", "https://example.com", "GET"),
        ("/api/v1/auth", "https://app.netrasystems.ai", "POST"),
        ("/api/v1/admin", "https://admin.netrasystems.ai", "DELETE"),
        ("/api/v1/embed", "https://customer.com", "GET"),
    ]
    
    for endpoint, origin, method in test_requests * 2:  # 8 total requests
        await cors_manager.make_cors_request(endpoint, method, origin)
    
    metrics = await cors_manager.get_cors_metrics()
    
    # Verify metrics
    assert metrics["total_requests"] == 8
    assert metrics["configured_policies"] == 5
    assert "origin_breakdown" in metrics
    assert "pattern_breakdown" in metrics
    
    # Check origin breakdown
    origin_breakdown = metrics["origin_breakdown"]
    assert "https://example.com" in origin_breakdown
    assert "https://app.netrasystems.ai" in origin_breakdown
    
    # Check pattern breakdown
    pattern_breakdown = metrics["pattern_breakdown"]
    assert "/api/v1/public" in pattern_breakdown
    assert "/api/v1/auth" in pattern_breakdown