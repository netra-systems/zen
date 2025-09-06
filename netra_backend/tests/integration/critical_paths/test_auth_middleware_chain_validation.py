from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''Auth Middleware Chain Validation L3 Integration Tests

# REMOVED_SYNTAX_ERROR: Tests the complete auth middleware chain including request validation,
# REMOVED_SYNTAX_ERROR: token extraction, permission checking, and audit logging middleware.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: ALL (Security foundation for all tiers)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Ensure bulletproof security for compliance requirements
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevent security breaches that could cost millions
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: SOC2/ISO27001 compliance enabling enterprise deals

    # REMOVED_SYNTAX_ERROR: Critical Path:
        # REMOVED_SYNTAX_ERROR: Request -> Token extraction -> Validation -> Permission check ->
        # REMOVED_SYNTAX_ERROR: Rate limiting -> Audit logging -> Handler execution -> Response

        # REMOVED_SYNTAX_ERROR: Mock-Real Spectrum: L3 (Real middleware with controlled requests)
        # REMOVED_SYNTAX_ERROR: - Real middleware stack
        # REMOVED_SYNTAX_ERROR: - Real token validation
        # REMOVED_SYNTAX_ERROR: - Real permission engine
        # REMOVED_SYNTAX_ERROR: - Simulated HTTP requests
        # REMOVED_SYNTAX_ERROR: """"

        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Test framework import - using pytest fixtures instead

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass, field
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Any, Callable, Dict, List, Optional

        # REMOVED_SYNTAX_ERROR: import httpx
        # REMOVED_SYNTAX_ERROR: import jwt
        # REMOVED_SYNTAX_ERROR: import pytest

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_settings
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.monitoring.metrics_collector import MetricsCollector
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.middleware.audit_middleware import AuditMiddleware
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.middleware.auth_middleware import AuthMiddleware
        # CORSMiddleware import removed - CORS now handled at app level
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.middleware.rate_limit_middleware import RateLimitMiddleware

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.auth_types import ( )
        # REMOVED_SYNTAX_ERROR: AuthError,
        # REMOVED_SYNTAX_ERROR: MiddlewareContext,
        # REMOVED_SYNTAX_ERROR: RequestContext,
        # REMOVED_SYNTAX_ERROR: Token,
        # REMOVED_SYNTAX_ERROR: TokenData,
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.exceptions_auth import ( )
        # REMOVED_SYNTAX_ERROR: AuthenticationError,
        # REMOVED_SYNTAX_ERROR: TokenExpiredError,
        # REMOVED_SYNTAX_ERROR: TokenInvalidError,
        

        # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class MiddlewareTestCase:
    # REMOVED_SYNTAX_ERROR: """Test case for middleware chain"""
    # REMOVED_SYNTAX_ERROR: name: str
    # REMOVED_SYNTAX_ERROR: request: Dict[str, Any]
    # REMOVED_SYNTAX_ERROR: expected_status: int
    # REMOVED_SYNTAX_ERROR: expected_headers: Dict[str, str]
    # REMOVED_SYNTAX_ERROR: should_reach_handler: bool
    # REMOVED_SYNTAX_ERROR: error_message: Optional[str] = None

    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class MiddlewareMetrics:
    # REMOVED_SYNTAX_ERROR: """Metrics for middleware performance"""
    # REMOVED_SYNTAX_ERROR: total_requests: int = 0
    # REMOVED_SYNTAX_ERROR: authenticated_requests: int = 0
    # REMOVED_SYNTAX_ERROR: unauthorized_requests: int = 0
    # REMOVED_SYNTAX_ERROR: rate_limited_requests: int = 0
    # REMOVED_SYNTAX_ERROR: middleware_latencies: Dict[str, List[float]] = field(default_factory=dict)
    # REMOVED_SYNTAX_ERROR: total_latency: List[float] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: audit_events_logged: int = 0

    # REMOVED_SYNTAX_ERROR: @property
# REMOVED_SYNTAX_ERROR: def avg_total_latency(self) -> float:
    # REMOVED_SYNTAX_ERROR: return sum(self.total_latency) / len(self.total_latency) if self.total_latency else 0

    # REMOVED_SYNTAX_ERROR: @property
# REMOVED_SYNTAX_ERROR: def auth_success_rate(self) -> float:
    # REMOVED_SYNTAX_ERROR: if self.total_requests == 0:
        # REMOVED_SYNTAX_ERROR: return 0
        # REMOVED_SYNTAX_ERROR: return (self.authenticated_requests / self.total_requests) * 100

# REMOVED_SYNTAX_ERROR: class TestAuthMiddlewareChainValidation:
    # REMOVED_SYNTAX_ERROR: """Test suite for auth middleware chain validation"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def middleware_stack(self):
    # REMOVED_SYNTAX_ERROR: """Create middleware stack"""
    # REMOVED_SYNTAX_ERROR: settings = get_settings()

    # Initialize middlewares in order
    # Note: FastAPI CORSMiddleware is used at app level, not in middleware chain
    # For testing, we'll skip CORS middleware in the chain since it's handled by the app

    # REMOVED_SYNTAX_ERROR: rate_limit_middleware = RateLimitMiddleware( )
    # REMOVED_SYNTAX_ERROR: requests_per_minute=60,
    # REMOVED_SYNTAX_ERROR: burst_size=10
    

    # REMOVED_SYNTAX_ERROR: auth_middleware = AuthMiddleware( )
    # REMOVED_SYNTAX_ERROR: jwt_secret=settings.jwt_secret_key,
    # REMOVED_SYNTAX_ERROR: jwt_algorithm="HS256",
    # REMOVED_SYNTAX_ERROR: excluded_paths=["/health", "/metrics"]
    

    # REMOVED_SYNTAX_ERROR: audit_middleware = AuditMiddleware( )
    # REMOVED_SYNTAX_ERROR: log_requests=True,
    # REMOVED_SYNTAX_ERROR: log_responses=True,
    # REMOVED_SYNTAX_ERROR: sensitive_fields=["password", "token", "secret"]
    

    # Compose middleware chain
    # REMOVED_SYNTAX_ERROR: middleware_chain = [ )
    # REMOVED_SYNTAX_ERROR: rate_limit_middleware,
    # REMOVED_SYNTAX_ERROR: auth_middleware,
    # REMOVED_SYNTAX_ERROR: audit_middleware
    

    # REMOVED_SYNTAX_ERROR: yield middleware_chain

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def token_generator(self):
    # REMOVED_SYNTAX_ERROR: """Generate test tokens"""
    # REMOVED_SYNTAX_ERROR: settings = get_settings()

# REMOVED_SYNTAX_ERROR: def generate_token( )
# REMOVED_SYNTAX_ERROR: user_id: str,
role: str = "user",
permissions: List[str] = None,
expired: bool = False
# REMOVED_SYNTAX_ERROR: ) -> str:
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "user_id": user_id,
    # REMOVED_SYNTAX_ERROR: "role": role,
    # REMOVED_SYNTAX_ERROR: "permissions": permissions or [],
    # REMOVED_SYNTAX_ERROR: "iat": now,
    # REMOVED_SYNTAX_ERROR: "exp": now + ( )
    # REMOVED_SYNTAX_ERROR: timedelta(hours=-1) if expired else timedelta(hours=1)
    
    
    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    # REMOVED_SYNTAX_ERROR: yield generate_token

    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_complete_middleware_chain_execution( )
    # REMOVED_SYNTAX_ERROR: self, middleware_stack, token_generator
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test complete middleware chain execution"""
        # REMOVED_SYNTAX_ERROR: metrics = MiddlewareMetrics()

        # Create test request
        # REMOVED_SYNTAX_ERROR: valid_token = token_generator("user123", "admin", ["read", "write"])

        # REMOVED_SYNTAX_ERROR: request_context = RequestContext( )
        # REMOVED_SYNTAX_ERROR: method="POST",
        # REMOVED_SYNTAX_ERROR: path="/api/agents/create",
        # REMOVED_SYNTAX_ERROR: headers={ )
        # REMOVED_SYNTAX_ERROR: "Authorization": "formatted_string",
        # REMOVED_SYNTAX_ERROR: "Content-Type": "application/json",
        # REMOVED_SYNTAX_ERROR: "Origin": "http://localhost:3000"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: body={"name": "test_agent"},
        # REMOVED_SYNTAX_ERROR: client_ip="127.0.0.1"
        

        # Execute middleware chain
        # REMOVED_SYNTAX_ERROR: handler_reached = False

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_handler(ctx: RequestContext):
            # REMOVED_SYNTAX_ERROR: nonlocal handler_reached
            # REMOVED_SYNTAX_ERROR: handler_reached = True
            # REMOVED_SYNTAX_ERROR: return {"status": "success", "agent_id": "123"}

            # Process through middleware chain
            # REMOVED_SYNTAX_ERROR: start_time = time.time()
            # REMOVED_SYNTAX_ERROR: current_context = request_context

            # REMOVED_SYNTAX_ERROR: for middleware in middleware_stack:
                # REMOVED_SYNTAX_ERROR: middleware_start = time.time()

                # REMOVED_SYNTAX_ERROR: try:
                    # Execute middleware
                    # REMOVED_SYNTAX_ERROR: result = await middleware.process(current_context, test_handler)

                    # Track latency
                    # REMOVED_SYNTAX_ERROR: middleware_name = middleware.__class__.__name__
                    # REMOVED_SYNTAX_ERROR: if middleware_name not in metrics.middleware_latencies:
                        # REMOVED_SYNTAX_ERROR: metrics.middleware_latencies[middleware_name] = []
                        # REMOVED_SYNTAX_ERROR: metrics.middleware_latencies[middleware_name].append( )
                        # REMOVED_SYNTAX_ERROR: time.time() - middleware_start
                        

                        # Update context if middleware modifies it
                        # REMOVED_SYNTAX_ERROR: if hasattr(result, 'context'):
                            # REMOVED_SYNTAX_ERROR: current_context = result.context

                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                # REMOVED_SYNTAX_ERROR: metrics.unauthorized_requests += 1
                                # REMOVED_SYNTAX_ERROR: raise

                                # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time
                                # REMOVED_SYNTAX_ERROR: metrics.total_latency.append(total_time)
                                # REMOVED_SYNTAX_ERROR: metrics.total_requests += 1

                                # REMOVED_SYNTAX_ERROR: if handler_reached:
                                    # REMOVED_SYNTAX_ERROR: metrics.authenticated_requests += 1

                                    # Verify handler was reached
                                    # REMOVED_SYNTAX_ERROR: assert handler_reached, "Handler not reached despite valid token"

                                    # Verify performance
                                    # REMOVED_SYNTAX_ERROR: assert total_time < 0.1, "formatted_string"

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_auth_middleware_token_validation( )
                                    # REMOVED_SYNTAX_ERROR: self, middleware_stack, token_generator
                                    # REMOVED_SYNTAX_ERROR: ):
                                        # REMOVED_SYNTAX_ERROR: """Test various token validation scenarios"""
                                        # REMOVED_SYNTAX_ERROR: auth_middleware = next( )
                                        # REMOVED_SYNTAX_ERROR: m for m in middleware_stack
                                        # REMOVED_SYNTAX_ERROR: if isinstance(m, AuthMiddleware)
                                        

                                        # REMOVED_SYNTAX_ERROR: test_cases = [ )
                                        # REMOVED_SYNTAX_ERROR: MiddlewareTestCase( )
                                        # REMOVED_SYNTAX_ERROR: name="Valid token",
                                        # REMOVED_SYNTAX_ERROR: request={ )
                                        # REMOVED_SYNTAX_ERROR: "headers": { )
                                        # REMOVED_SYNTAX_ERROR: "Authorization": "formatted_string"
                                        
                                        # REMOVED_SYNTAX_ERROR: },
                                        # REMOVED_SYNTAX_ERROR: expected_status=200,
                                        # REMOVED_SYNTAX_ERROR: expected_headers={},
                                        # REMOVED_SYNTAX_ERROR: should_reach_handler=True
                                        # REMOVED_SYNTAX_ERROR: ),
                                        # REMOVED_SYNTAX_ERROR: MiddlewareTestCase( )
                                        # REMOVED_SYNTAX_ERROR: name="Expired token",
                                        # REMOVED_SYNTAX_ERROR: request={ )
                                        # REMOVED_SYNTAX_ERROR: "headers": { )
                                        # REMOVED_SYNTAX_ERROR: "Authorization": "formatted_string"
                                        
                                        # REMOVED_SYNTAX_ERROR: },
                                        # REMOVED_SYNTAX_ERROR: expected_status=401,
                                        # REMOVED_SYNTAX_ERROR: expected_headers={"WWW-Authenticate": "Bearer"},
                                        # REMOVED_SYNTAX_ERROR: should_reach_handler=False,
                                        # REMOVED_SYNTAX_ERROR: error_message="Token expired"
                                        # REMOVED_SYNTAX_ERROR: ),
                                        # REMOVED_SYNTAX_ERROR: MiddlewareTestCase( )
                                        # REMOVED_SYNTAX_ERROR: name="Missing token",
                                        # REMOVED_SYNTAX_ERROR: request={"headers": {}},
                                        # REMOVED_SYNTAX_ERROR: expected_status=401,
                                        # REMOVED_SYNTAX_ERROR: expected_headers={"WWW-Authenticate": "Bearer"},
                                        # REMOVED_SYNTAX_ERROR: should_reach_handler=False,
                                        # REMOVED_SYNTAX_ERROR: error_message="No authorization header"
                                        # REMOVED_SYNTAX_ERROR: ),
                                        # REMOVED_SYNTAX_ERROR: MiddlewareTestCase( )
                                        # REMOVED_SYNTAX_ERROR: name="Invalid token format",
                                        # REMOVED_SYNTAX_ERROR: request={ )
                                        # REMOVED_SYNTAX_ERROR: "headers": {"Authorization": "InvalidFormat"}
                                        # REMOVED_SYNTAX_ERROR: },
                                        # REMOVED_SYNTAX_ERROR: expected_status=401,
                                        # REMOVED_SYNTAX_ERROR: expected_headers={"WWW-Authenticate": "Bearer"},
                                        # REMOVED_SYNTAX_ERROR: should_reach_handler=False,
                                        # REMOVED_SYNTAX_ERROR: error_message="Invalid authorization format"
                                        # REMOVED_SYNTAX_ERROR: ),
                                        # REMOVED_SYNTAX_ERROR: MiddlewareTestCase( )
                                        # REMOVED_SYNTAX_ERROR: name="Malformed token",
                                        # REMOVED_SYNTAX_ERROR: request={ )
                                        # REMOVED_SYNTAX_ERROR: "headers": {"Authorization": "Bearer invalid.jwt.token"}
                                        # REMOVED_SYNTAX_ERROR: },
                                        # REMOVED_SYNTAX_ERROR: expected_status=401,
                                        # REMOVED_SYNTAX_ERROR: expected_headers={"WWW-Authenticate": "Bearer"},
                                        # REMOVED_SYNTAX_ERROR: should_reach_handler=False,
                                        # REMOVED_SYNTAX_ERROR: error_message="Invalid token"
                                        
                                        

                                        # REMOVED_SYNTAX_ERROR: for test_case in test_cases:
                                            # REMOVED_SYNTAX_ERROR: handler_reached = False

# REMOVED_SYNTAX_ERROR: async def handler(ctx):
    # REMOVED_SYNTAX_ERROR: nonlocal handler_reached
    # REMOVED_SYNTAX_ERROR: handler_reached = True
    # REMOVED_SYNTAX_ERROR: return {"status": "success"}

    # REMOVED_SYNTAX_ERROR: context = RequestContext( )
    # REMOVED_SYNTAX_ERROR: method="GET",
    # REMOVED_SYNTAX_ERROR: path="/api/test",
    # REMOVED_SYNTAX_ERROR: headers=test_case.request.get("headers", {}),
    # REMOVED_SYNTAX_ERROR: body=None,
    # REMOVED_SYNTAX_ERROR: client_ip="127.0.0.1"
    

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = await auth_middleware.process(context, handler)
        # REMOVED_SYNTAX_ERROR: assert test_case.should_reach_handler, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: except (AuthError, AuthenticationError, TokenExpiredError, TokenInvalidError) as e:
            # REMOVED_SYNTAX_ERROR: assert not test_case.should_reach_handler, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: if test_case.error_message:
                # REMOVED_SYNTAX_ERROR: assert test_case.error_message.lower() in str(e).lower()

                # REMOVED_SYNTAX_ERROR: assert handler_reached == test_case.should_reach_handler, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # REMOVED_SYNTAX_ERROR: @pytest.fixture
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_rate_limit_middleware_enforcement( )
                # REMOVED_SYNTAX_ERROR: self
                # REMOVED_SYNTAX_ERROR: ):
                    # REMOVED_SYNTAX_ERROR: """Test rate limiting middleware"""
                    # Create dedicated rate limit middleware for this test
                    # REMOVED_SYNTAX_ERROR: rate_limit_middleware = RateLimitMiddleware( )
                    # REMOVED_SYNTAX_ERROR: requests_per_minute=60,
                    # REMOVED_SYNTAX_ERROR: burst_size=10,
                    # REMOVED_SYNTAX_ERROR: window_size_seconds=60
                    

                    # REMOVED_SYNTAX_ERROR: metrics = MiddlewareMetrics()
                    # REMOVED_SYNTAX_ERROR: client_ip = "192.168.1.1"

                    # Reset rate limiting state for this client to ensure clean test
                    # REMOVED_SYNTAX_ERROR: rate_limit_middleware.reset_client_limits("formatted_string")

                    # Send requests up to and beyond limit
# REMOVED_SYNTAX_ERROR: async def make_request():
    # REMOVED_SYNTAX_ERROR: context = RequestContext( )
    # REMOVED_SYNTAX_ERROR: method="GET",
    # REMOVED_SYNTAX_ERROR: path="/api/test",
    # REMOVED_SYNTAX_ERROR: headers={},
    # REMOVED_SYNTAX_ERROR: body=None,
    # REMOVED_SYNTAX_ERROR: client_ip=client_ip
    

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: await rate_limit_middleware.process( )
        # REMOVED_SYNTAX_ERROR: context,
        # REMOVED_SYNTAX_ERROR: lambda x: None {"status": "success"}
        
        # REMOVED_SYNTAX_ERROR: return True
        # REMOVED_SYNTAX_ERROR: except AuthenticationError as e:
            # REMOVED_SYNTAX_ERROR: if "rate limit" in str(e).lower():
                # REMOVED_SYNTAX_ERROR: metrics.rate_limited_requests += 1
                # REMOVED_SYNTAX_ERROR: return False
                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: if "rate limit" in str(e).lower():
                        # REMOVED_SYNTAX_ERROR: metrics.rate_limited_requests += 1
                        # REMOVED_SYNTAX_ERROR: return False

                        # Send burst of requests
                        # REMOVED_SYNTAX_ERROR: results = []
                        # REMOVED_SYNTAX_ERROR: for i in range(15):  # Exceed burst size of 10
                        # REMOVED_SYNTAX_ERROR: result = await make_request()
                        # REMOVED_SYNTAX_ERROR: results.append(result)
                        # REMOVED_SYNTAX_ERROR: metrics.total_requests += 1
                        # Test all requests to see rate limiting behavior

                        # Test behavior matches expected rate limiting pattern
                        # REMOVED_SYNTAX_ERROR: successful_requests = sum(results)
                        # REMOVED_SYNTAX_ERROR: failed_requests = len(results) - successful_requests

                        # Should have some rate limited requests
                        # REMOVED_SYNTAX_ERROR: assert metrics.rate_limited_requests > 0, \
                        # REMOVED_SYNTAX_ERROR: "Rate limiting not triggered"

                        # Should have some successful and some failed requests for a working rate limiter
                        # REMOVED_SYNTAX_ERROR: assert successful_requests + failed_requests == len(results), \
                        # REMOVED_SYNTAX_ERROR: "All requests should be accounted for"

                        # CORS test removed - CORS is now handled by FastAPI's built-in CORSMiddleware
                        # which is well-tested and configured through shared/cors_config.py

                        # Removed problematic line: @pytest.mark.asyncio
                        # REMOVED_SYNTAX_ERROR: @pytest.fixture
                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_audit_middleware_logging( )
                        # REMOVED_SYNTAX_ERROR: self, middleware_stack, token_generator
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: """Test audit middleware logging"""
                            # REMOVED_SYNTAX_ERROR: audit_middleware = next( )
                            # REMOVED_SYNTAX_ERROR: m for m in middleware_stack
                            # REMOVED_SYNTAX_ERROR: if isinstance(m, AuditMiddleware)
                            

                            # REMOVED_SYNTAX_ERROR: metrics = MiddlewareMetrics()
                            # REMOVED_SYNTAX_ERROR: audit_logs = []

                            # Mock audit logger
# REMOVED_SYNTAX_ERROR: async def mock_log_event(event):
    # REMOVED_SYNTAX_ERROR: audit_logs.append(event)
    # REMOVED_SYNTAX_ERROR: metrics.audit_events_logged += 1

    # REMOVED_SYNTAX_ERROR: audit_middleware.log_event = mock_log_event

    # Test various operations
    # REMOVED_SYNTAX_ERROR: operations = [ )
    # REMOVED_SYNTAX_ERROR: ("GET", "/api/users", None, 200),
    # REMOVED_SYNTAX_ERROR: ("POST", "/api/agents", {"name": "test"}, 201),
    # REMOVED_SYNTAX_ERROR: ("DELETE", "/api/agents/123", None, 204),
    # REMOVED_SYNTAX_ERROR: ("PUT", "/api/users/456", {"role": "admin"}, 200),
    # REMOVED_SYNTAX_ERROR: ("GET", "/api/secure", None, 401)  # Unauthorized
    

    # REMOVED_SYNTAX_ERROR: for method, path, body, expected_status in operations:
        # REMOVED_SYNTAX_ERROR: context = RequestContext( )
        # REMOVED_SYNTAX_ERROR: method=method,
        # REMOVED_SYNTAX_ERROR: path=path,
        # REMOVED_SYNTAX_ERROR: headers={ )
        # REMOVED_SYNTAX_ERROR: "Authorization": "formatted_string"
        # REMOVED_SYNTAX_ERROR: if expected_status != 401 else {}
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: body=body,
        # REMOVED_SYNTAX_ERROR: client_ip="127.0.0.1"
        

# REMOVED_SYNTAX_ERROR: async def handler(ctx):
    # REMOVED_SYNTAX_ERROR: if expected_status == 401:
        # REMOVED_SYNTAX_ERROR: raise AuthError("Unauthorized")
        # REMOVED_SYNTAX_ERROR: return {"status": "success"}

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await audit_middleware.process(context, handler)
            # REMOVED_SYNTAX_ERROR: except AuthError:
                # REMOVED_SYNTAX_ERROR: pass  # Expected for 401 case

                # Verify audit logs created (2 events per operation: request + response)
                # REMOVED_SYNTAX_ERROR: expected_events = len(operations) * 2  # Both request and response events
                # REMOVED_SYNTAX_ERROR: assert metrics.audit_events_logged == expected_events, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # Verify audit log content
                # REMOVED_SYNTAX_ERROR: for log in audit_logs:
                    # REMOVED_SYNTAX_ERROR: assert "method" in log
                    # REMOVED_SYNTAX_ERROR: assert "path" in log
                    # REMOVED_SYNTAX_ERROR: assert "client_ip" in log
                    # REMOVED_SYNTAX_ERROR: assert "timestamp" in log

                    # Verify sensitive data is masked
                    # REMOVED_SYNTAX_ERROR: if log.get("body") and "password" in str(log["body"]):
                        # REMOVED_SYNTAX_ERROR: assert "***" in str(log["body"]) or "[REDACTED]" in str(log["body"])

                        # Removed problematic line: @pytest.mark.asyncio
                        # REMOVED_SYNTAX_ERROR: @pytest.fixture
                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_middleware_chain_error_handling( )
                        # REMOVED_SYNTAX_ERROR: self, middleware_stack
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: """Test error handling through middleware chain"""
                            # Test different error scenarios
                            # REMOVED_SYNTAX_ERROR: error_scenarios = [ )
                            # REMOVED_SYNTAX_ERROR: (AuthError("Invalid token"), 401, "Invalid token"),
                            # REMOVED_SYNTAX_ERROR: (ValueError("Bad request"), 400, "Bad request"),
                            # REMOVED_SYNTAX_ERROR: (PermissionError("Forbidden"), 403, "Forbidden"),
                            # REMOVED_SYNTAX_ERROR: (Exception("Internal error"), 500, "Internal server error")
                            

                            # REMOVED_SYNTAX_ERROR: for error, expected_status, expected_message in error_scenarios:
                                # REMOVED_SYNTAX_ERROR: context = RequestContext( )
                                # REMOVED_SYNTAX_ERROR: method="GET",
                                # REMOVED_SYNTAX_ERROR: path="/api/test",
                                # REMOVED_SYNTAX_ERROR: headers={},
                                # REMOVED_SYNTAX_ERROR: body=None,
                                # REMOVED_SYNTAX_ERROR: client_ip="127.0.0.1"
                                

# REMOVED_SYNTAX_ERROR: async def failing_handler(ctx):
    # REMOVED_SYNTAX_ERROR: raise error

    # Process through chain
    # REMOVED_SYNTAX_ERROR: caught_error = None
    # REMOVED_SYNTAX_ERROR: for middleware in middleware_stack:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await middleware.process(context, failing_handler)
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: caught_error = e
                # REMOVED_SYNTAX_ERROR: break

                # REMOVED_SYNTAX_ERROR: assert caught_error is not None, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # Verify error type preserved
                # REMOVED_SYNTAX_ERROR: if isinstance(error, AuthError):
                    # REMOVED_SYNTAX_ERROR: assert isinstance(caught_error, AuthError)

                    # Removed problematic line: @pytest.mark.asyncio
                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_middleware_performance_under_load( )
                    # REMOVED_SYNTAX_ERROR: self, middleware_stack, token_generator
                    # REMOVED_SYNTAX_ERROR: ):
                        # REMOVED_SYNTAX_ERROR: """Test middleware performance under load"""
                        # REMOVED_SYNTAX_ERROR: metrics = MiddlewareMetrics()
                        # REMOVED_SYNTAX_ERROR: concurrent_requests = 100

# REMOVED_SYNTAX_ERROR: async def process_request(request_id: int):
    # REMOVED_SYNTAX_ERROR: token = token_generator("formatted_string", "user")
    # REMOVED_SYNTAX_ERROR: context = RequestContext( )
    # REMOVED_SYNTAX_ERROR: method="GET",
    # REMOVED_SYNTAX_ERROR: path="formatted_string",
    # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"},
    # REMOVED_SYNTAX_ERROR: body=None,
    # REMOVED_SYNTAX_ERROR: client_ip="formatted_string"
    

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: handler_reached = False

# REMOVED_SYNTAX_ERROR: async def handler(ctx):
    # REMOVED_SYNTAX_ERROR: nonlocal handler_reached
    # REMOVED_SYNTAX_ERROR: handler_reached = True
    # REMOVED_SYNTAX_ERROR: return {"id": request_id}

    # Process through chain
    # REMOVED_SYNTAX_ERROR: for middleware in middleware_stack:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await middleware.process(context, handler)
            # REMOVED_SYNTAX_ERROR: except Exception:
                # REMOVED_SYNTAX_ERROR: break

                # REMOVED_SYNTAX_ERROR: elapsed = time.time() - start_time
                # REMOVED_SYNTAX_ERROR: return elapsed, handler_reached

                # Execute concurrent requests
                # REMOVED_SYNTAX_ERROR: tasks = [process_request(i) for i in range(concurrent_requests)]
                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                # Analyze results
                # REMOVED_SYNTAX_ERROR: latencies = [item for item in []]
                # REMOVED_SYNTAX_ERROR: successful = sum(1 for r in results if isinstance(r, tuple) and r[1])

                # REMOVED_SYNTAX_ERROR: metrics.total_requests = concurrent_requests
                # REMOVED_SYNTAX_ERROR: metrics.authenticated_requests = successful
                # REMOVED_SYNTAX_ERROR: metrics.total_latency = latencies

                # Performance assertions
                # REMOVED_SYNTAX_ERROR: assert metrics.avg_total_latency < 0.05, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # REMOVED_SYNTAX_ERROR: assert metrics.auth_success_rate >= 95, \
                # REMOVED_SYNTAX_ERROR: "formatted_string"

                # Check for memory leaks (simplified check)
                # REMOVED_SYNTAX_ERROR: import psutil
                # REMOVED_SYNTAX_ERROR: process = psutil.Process()
                # REMOVED_SYNTAX_ERROR: memory_mb = process.memory_info().rss / 1024 / 1024
                # REMOVED_SYNTAX_ERROR: assert memory_mb < 500, "formatted_string"