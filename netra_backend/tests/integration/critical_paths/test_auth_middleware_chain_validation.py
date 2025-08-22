"""Auth Middleware Chain Validation L3 Integration Tests

Tests the complete auth middleware chain including request validation,
token extraction, permission checking, and audit logging middleware.

Business Value Justification (BVJ):
- Segment: ALL (Security foundation for all tiers)
- Business Goal: Ensure bulletproof security for compliance requirements
- Value Impact: Prevent security breaches that could cost millions
- Strategic Impact: SOC2/ISO27001 compliance enabling enterprise deals

Critical Path:
Request -> Token extraction -> Validation -> Permission check ->
Rate limiting -> Audit logging -> Handler execution -> Response

Mock-Real Spectrum: L3 (Real middleware with controlled requests)
- Real middleware stack
- Real token validation
- Real permission engine
- Simulated HTTP requests
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest

from netra_backend.app.core.config import get_settings
from netra_backend.app.core.monitoring import metrics_collector
from netra_backend.app.middleware.audit_middleware import AuditMiddleware
from netra_backend.app.middleware.auth_middleware import AuthMiddleware
from netra_backend.app.middleware.cors_middleware import CORSMiddleware
from netra_backend.app.middleware.rate_limit_middleware import RateLimitMiddleware

# Add project root to path
from netra_backend.app.schemas.auth_types import (
    AuthError,
    MiddlewareContext,
    RequestContext,
    # Add project root to path
    Token,
    TokenData,
)


@dataclass
class MiddlewareTestCase:
    """Test case for middleware chain"""
    name: str
    request: Dict[str, Any]
    expected_status: int
    expected_headers: Dict[str, str]
    should_reach_handler: bool
    error_message: Optional[str] = None


@dataclass
class MiddlewareMetrics:
    """Metrics for middleware performance"""
    total_requests: int = 0
    authenticated_requests: int = 0
    unauthorized_requests: int = 0
    rate_limited_requests: int = 0
    middleware_latencies: Dict[str, List[float]] = field(default_factory=dict)
    total_latency: List[float] = field(default_factory=list)
    audit_events_logged: int = 0
    
    @property
    def avg_total_latency(self) -> float:
        return sum(self.total_latency) / len(self.total_latency) if self.total_latency else 0
    
    @property
    def auth_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return (self.authenticated_requests / self.total_requests) * 100


class TestAuthMiddlewareChainValidation:
    """Test suite for auth middleware chain validation"""
    
    @pytest.fixture
    async def middleware_stack(self):
        """Create middleware stack"""
        settings = get_settings()
        
        # Initialize middlewares in order
        cors_middleware = CORSMiddleware(
            allowed_origins=["http://localhost:3000", "https://app.netra.io"],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            allowed_headers=["Authorization", "Content-Type"]
        )
        
        rate_limit_middleware = RateLimitMiddleware(
            requests_per_minute=60,
            burst_size=10
        )
        
        auth_middleware = AuthMiddleware(
            jwt_secret=settings.jwt_secret_key,
            jwt_algorithm="HS256",
            excluded_paths=["/health", "/metrics"]
        )
        
        audit_middleware = AuditMiddleware(
            log_requests=True,
            log_responses=True,
            sensitive_fields=["password", "token", "secret"]
        )
        
        # Compose middleware chain
        middleware_chain = [
            cors_middleware,
            rate_limit_middleware,
            auth_middleware,
            audit_middleware
        ]
        
        return middleware_chain
    
    @pytest.fixture
    async def token_generator(self):
        """Generate test tokens"""
        settings = get_settings()
        
        def generate_token(
            user_id: str,
            role: str = "user",
            permissions: List[str] = None,
            expired: bool = False
        ) -> str:
            payload = {
                "user_id": user_id,
                "role": role,
                "permissions": permissions or [],
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + (
                    timedelta(hours=-1) if expired else timedelta(hours=1)
                )
            }
            return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
        
        return generate_token
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_complete_middleware_chain_execution(
        self, middleware_stack, token_generator
    ):
        """Test complete middleware chain execution"""
        metrics = MiddlewareMetrics()
        
        # Create test request
        valid_token = token_generator("user123", "admin", ["read", "write"])
        
        request_context = RequestContext(
            method="POST",
            path="/api/agents/create",
            headers={
                "Authorization": f"Bearer {valid_token}",
                "Content-Type": "application/json",
                "Origin": "http://localhost:3000"
            },
            body={"name": "test_agent"},
            client_ip="127.0.0.1"
        )
        
        # Execute middleware chain
        handler_reached = False
        
        async def test_handler(ctx: RequestContext):
            nonlocal handler_reached
            handler_reached = True
            return {"status": "success", "agent_id": "123"}
        
        # Process through middleware chain
        start_time = time.time()
        current_context = request_context
        
        for middleware in middleware_stack:
            middleware_start = time.time()
            
            try:
                # Execute middleware
                result = await middleware.process(current_context, test_handler)
                
                # Track latency
                middleware_name = middleware.__class__.__name__
                if middleware_name not in metrics.middleware_latencies:
                    metrics.middleware_latencies[middleware_name] = []
                metrics.middleware_latencies[middleware_name].append(
                    time.time() - middleware_start
                )
                
                # Update context if middleware modifies it
                if hasattr(result, 'context'):
                    current_context = result.context
                    
            except Exception as e:
                metrics.unauthorized_requests += 1
                raise
        
        total_time = time.time() - start_time
        metrics.total_latency.append(total_time)
        metrics.total_requests += 1
        
        if handler_reached:
            metrics.authenticated_requests += 1
        
        # Verify handler was reached
        assert handler_reached, "Handler not reached despite valid token"
        
        # Verify performance
        assert total_time < 0.1, f"Middleware chain too slow: {total_time}s"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_auth_middleware_token_validation(
        self, middleware_stack, token_generator
    ):
        """Test various token validation scenarios"""
        auth_middleware = next(
            m for m in middleware_stack 
            if isinstance(m, AuthMiddleware)
        )
        
        test_cases = [
            MiddlewareTestCase(
                name="Valid token",
                request={
                    "headers": {
                        "Authorization": f"Bearer {token_generator('user1', 'user')}"
                    }
                },
                expected_status=200,
                expected_headers={},
                should_reach_handler=True
            ),
            MiddlewareTestCase(
                name="Expired token",
                request={
                    "headers": {
                        "Authorization": f"Bearer {token_generator('user2', 'user', expired=True)}"
                    }
                },
                expected_status=401,
                expected_headers={"WWW-Authenticate": "Bearer"},
                should_reach_handler=False,
                error_message="Token expired"
            ),
            MiddlewareTestCase(
                name="Missing token",
                request={"headers": {}},
                expected_status=401,
                expected_headers={"WWW-Authenticate": "Bearer"},
                should_reach_handler=False,
                error_message="No authorization header"
            ),
            MiddlewareTestCase(
                name="Invalid token format",
                request={
                    "headers": {"Authorization": "InvalidFormat"}
                },
                expected_status=401,
                expected_headers={"WWW-Authenticate": "Bearer"},
                should_reach_handler=False,
                error_message="Invalid authorization format"
            ),
            MiddlewareTestCase(
                name="Malformed token",
                request={
                    "headers": {"Authorization": "Bearer invalid.jwt.token"}
                },
                expected_status=401,
                expected_headers={"WWW-Authenticate": "Bearer"},
                should_reach_handler=False,
                error_message="Invalid token"
            )
        ]
        
        for test_case in test_cases:
            handler_reached = False
            
            async def handler(ctx):
                nonlocal handler_reached
                handler_reached = True
                return {"status": "success"}
            
            context = RequestContext(
                method="GET",
                path="/api/test",
                headers=test_case.request.get("headers", {}),
                body=None,
                client_ip="127.0.0.1"
            )
            
            try:
                result = await auth_middleware.process(context, handler)
                assert test_case.should_reach_handler, \
                    f"{test_case.name}: Should have been rejected"
            except AuthError as e:
                assert not test_case.should_reach_handler, \
                    f"{test_case.name}: Should have been allowed"
                if test_case.error_message:
                    assert test_case.error_message.lower() in str(e).lower()
            
            assert handler_reached == test_case.should_reach_handler, \
                f"{test_case.name}: Handler reached={handler_reached}, expected={test_case.should_reach_handler}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_rate_limit_middleware_enforcement(
        self, middleware_stack
    ):
        """Test rate limiting middleware"""
        rate_limit_middleware = next(
            m for m in middleware_stack 
            if isinstance(m, RateLimitMiddleware)
        )
        
        metrics = MiddlewareMetrics()
        client_ip = "192.168.1.1"
        
        # Send requests up to and beyond limit
        async def make_request():
            context = RequestContext(
                method="GET",
                path="/api/test",
                headers={},
                body=None,
                client_ip=client_ip
            )
            
            try:
                await rate_limit_middleware.process(
                    context,
                    lambda ctx: {"status": "success"}
                )
                return True
            except Exception as e:
                if "rate limit" in str(e).lower():
                    metrics.rate_limited_requests += 1
                return False
        
        # Send burst of requests
        results = []
        for i in range(15):  # Exceed burst size of 10
            result = await make_request()
            results.append(result)
            metrics.total_requests += 1
            
            if not result:
                break
        
        # Should have some rate limited requests
        assert metrics.rate_limited_requests > 0, \
            "Rate limiting not triggered"
        
        # First 10 should succeed (burst size)
        assert sum(results[:10]) >= 9, \
            "Initial burst should mostly succeed"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_cors_middleware_headers(
        self, middleware_stack
    ):
        """Test CORS middleware header handling"""
        cors_middleware = next(
            m for m in middleware_stack 
            if isinstance(m, CORSMiddleware)
        )
        
        test_origins = [
            ("http://localhost:3000", True),  # Allowed
            ("https://app.netra.io", True),   # Allowed
            ("http://evil.com", False),       # Not allowed
            (None, False)                      # No origin
        ]
        
        for origin, should_allow in test_origins:
            context = RequestContext(
                method="OPTIONS",  # Preflight request
                path="/api/test",
                headers={"Origin": origin} if origin else {},
                body=None,
                client_ip="127.0.0.1"
            )
            
            response_headers = {}
            
            async def handler(ctx):
                return {"status": "success"}
            
            try:
                result = await cors_middleware.process(context, handler)
                
                # Check for CORS headers
                if should_allow:
                    assert cors_middleware.is_allowed_origin(origin), \
                        f"Origin {origin} should be allowed"
                else:
                    assert not cors_middleware.is_allowed_origin(origin), \
                        f"Origin {origin} should not be allowed"
                        
            except Exception as e:
                if not should_allow:
                    assert "cors" in str(e).lower() or "origin" in str(e).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_audit_middleware_logging(
        self, middleware_stack, token_generator
    ):
        """Test audit middleware logging"""
        audit_middleware = next(
            m for m in middleware_stack 
            if isinstance(m, AuditMiddleware)
        )
        
        metrics = MiddlewareMetrics()
        audit_logs = []
        
        # Mock audit logger
        async def mock_log_event(event):
            audit_logs.append(event)
            metrics.audit_events_logged += 1
        
        audit_middleware.log_event = mock_log_event
        
        # Test various operations
        operations = [
            ("GET", "/api/users", None, 200),
            ("POST", "/api/agents", {"name": "test"}, 201),
            ("DELETE", "/api/agents/123", None, 204),
            ("PUT", "/api/users/456", {"role": "admin"}, 200),
            ("GET", "/api/secure", None, 401)  # Unauthorized
        ]
        
        for method, path, body, expected_status in operations:
            context = RequestContext(
                method=method,
                path=path,
                headers={
                    "Authorization": f"Bearer {token_generator('user1', 'admin')}"
                    if expected_status != 401 else {}
                },
                body=body,
                client_ip="127.0.0.1"
            )
            
            async def handler(ctx):
                if expected_status == 401:
                    raise AuthError("Unauthorized")
                return {"status": "success"}
            
            try:
                await audit_middleware.process(context, handler)
            except AuthError:
                pass  # Expected for 401 case
        
        # Verify audit logs created
        assert metrics.audit_events_logged == len(operations), \
            f"Expected {len(operations)} audit events, got {metrics.audit_events_logged}"
        
        # Verify audit log content
        for log in audit_logs:
            assert "method" in log
            assert "path" in log
            assert "client_ip" in log
            assert "timestamp" in log
            
            # Verify sensitive data is masked
            if log.get("body") and "password" in str(log["body"]):
                assert "***" in str(log["body"]) or "[REDACTED]" in str(log["body"])
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_middleware_chain_error_handling(
        self, middleware_stack
    ):
        """Test error handling through middleware chain"""
        # Test different error scenarios
        error_scenarios = [
            (AuthError("Invalid token"), 401, "Invalid token"),
            (ValueError("Bad request"), 400, "Bad request"),
            (PermissionError("Forbidden"), 403, "Forbidden"),
            (Exception("Internal error"), 500, "Internal server error")
        ]
        
        for error, expected_status, expected_message in error_scenarios:
            context = RequestContext(
                method="GET",
                path="/api/test",
                headers={},
                body=None,
                client_ip="127.0.0.1"
            )
            
            async def failing_handler(ctx):
                raise error
            
            # Process through chain
            caught_error = None
            for middleware in middleware_stack:
                try:
                    await middleware.process(context, failing_handler)
                except Exception as e:
                    caught_error = e
                    break
            
            assert caught_error is not None, \
                f"Error {error} should have been caught"
            
            # Verify error type preserved
            if isinstance(error, AuthError):
                assert isinstance(caught_error, AuthError)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_middleware_performance_under_load(
        self, middleware_stack, token_generator
    ):
        """Test middleware performance under load"""
        metrics = MiddlewareMetrics()
        concurrent_requests = 100
        
        async def process_request(request_id: int):
            token = token_generator(f"user{request_id}", "user")
            context = RequestContext(
                method="GET",
                path=f"/api/data/{request_id}",
                headers={"Authorization": f"Bearer {token}"},
                body=None,
                client_ip=f"192.168.1.{request_id % 255}"
            )
            
            start_time = time.time()
            handler_reached = False
            
            async def handler(ctx):
                nonlocal handler_reached
                handler_reached = True
                return {"id": request_id}
            
            # Process through chain
            for middleware in middleware_stack:
                try:
                    await middleware.process(context, handler)
                except Exception:
                    break
            
            elapsed = time.time() - start_time
            return elapsed, handler_reached
        
        # Execute concurrent requests
        tasks = [process_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        latencies = [r[0] for r in results if isinstance(r, tuple)]
        successful = sum(1 for r in results if isinstance(r, tuple) and r[1])
        
        metrics.total_requests = concurrent_requests
        metrics.authenticated_requests = successful
        metrics.total_latency = latencies
        
        # Performance assertions
        assert metrics.avg_total_latency < 0.05, \
            f"Average latency {metrics.avg_total_latency}s too high"
        
        assert metrics.auth_success_rate >= 95, \
            f"Auth success rate {metrics.auth_success_rate}% too low"
        
        # Check for memory leaks (simplified check)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 500, f"Memory usage {memory_mb}MB indicates potential leak"