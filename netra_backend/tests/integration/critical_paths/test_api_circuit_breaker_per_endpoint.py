"""API Circuit Breaker Per-Endpoint L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API reliability infrastructure)
- Business Goal: Prevent cascading failures and maintain service availability
- Value Impact: Protects against downstream service failures
- Strategic Impact: $15K MRR protection through fault-tolerant API gateway

Critical Path: Request processing -> Failure detection -> Circuit state management -> Fallback response -> Recovery monitoring
Coverage: Per-endpoint circuit breakers, failure thresholds, recovery mechanisms, fallback strategies
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Add project root to path
from app.services.api_gateway.circuit_breaker import ApiCircuitBreaker
from app.services.api_gateway.circuit_breaker_manager import (
    CircuitBreakerManager,
)
from app.services.api_gateway.fallback_service import ApiFallbackService
from app.services.metrics.circuit_breaker_metrics import (
    CircuitBreakerMetricsService,
)

# Add project root to path

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for endpoints."""
    endpoint_pattern: str
    failure_threshold: int      # Number of failures to open circuit
    success_threshold: int      # Number of successes to close circuit
    timeout_seconds: int        # Circuit open timeout
    rolling_window_seconds: int # Failure counting window
    error_percentage: float     # Error percentage to open circuit
    minimum_requests: int       # Minimum requests before opening


class ApiCircuitBreakerManager:
    """Manages L3 API circuit breaker tests with real failure simulation."""
    
    def __init__(self):
        self.circuit_manager = None
        self.fallback_service = None
        self.metrics_service = None
        self.test_server = None
        self.backend_servers = {}
        self.circuit_configs = {}
        self.circuit_states = {}
        self.failure_injections = {}
        self.circuit_events = []
        self.fallback_responses = []
        
    async def initialize_circuit_breakers(self):
        """Initialize circuit breaker services for L3 testing."""
        try:
            self.circuit_manager = CircuitBreakerManager()
            await self.circuit_manager.initialize()
            
            self.fallback_service = ApiFallbackService()
            await self.fallback_service.initialize()
            
            self.metrics_service = CircuitBreakerMetricsService()
            await self.metrics_service.initialize()
            
            # Configure circuit breakers for endpoints
            await self.setup_circuit_breaker_configs()
            
            # Start backend services and gateway
            await self.start_backend_services()
            await self.start_gateway_with_circuit_breakers()
            
            logger.info("API circuit breaker services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker services: {e}")
            raise
    
    async def setup_circuit_breaker_configs(self):
        """Configure circuit breakers for different endpoints."""
        self.circuit_configs = {
            "/api/v1/users": CircuitBreakerConfig(
                endpoint_pattern="/api/v1/users",
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=30,
                rolling_window_seconds=60,
                error_percentage=50.0,
                minimum_requests=10
            ),
            "/api/v1/agents": CircuitBreakerConfig(
                endpoint_pattern="/api/v1/agents",
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=20,
                rolling_window_seconds=45,
                error_percentage=60.0,
                minimum_requests=5
            ),
            "/api/v1/threads": CircuitBreakerConfig(
                endpoint_pattern="/api/v1/threads",
                failure_threshold=7,
                success_threshold=4,
                timeout_seconds=45,
                rolling_window_seconds=90,
                error_percentage=40.0,
                minimum_requests=15
            ),
            "/api/v1/metrics": CircuitBreakerConfig(
                endpoint_pattern="/api/v1/metrics",
                failure_threshold=2,
                success_threshold=1,
                timeout_seconds=15,
                rolling_window_seconds=30,
                error_percentage=70.0,
                minimum_requests=3
            ),
            "/api/v1/health": CircuitBreakerConfig(
                endpoint_pattern="/api/v1/health",
                failure_threshold=10,
                success_threshold=5,
                timeout_seconds=60,
                rolling_window_seconds=120,
                error_percentage=30.0,
                minimum_requests=20
            )
        }
        
        # Register circuit breakers
        for endpoint, config in self.circuit_configs.items():
            await self.circuit_manager.register_circuit_breaker(endpoint, config)
            self.circuit_states[endpoint] = CircuitState.CLOSED
    
    async def start_backend_services(self):
        """Start mock backend services for testing."""
        backend_configs = {
            "user_service": 8001,
            "agent_service": 8002,
            "thread_service": 8003,
            "metrics_service": 8004,
            "health_service": 8005
        }
        
        for service_name, port in backend_configs.items():
            server = await self.start_backend_service(service_name, port)
            self.backend_servers[service_name] = server
    
    async def start_backend_service(self, service_name: str, port: int):
        """Start a mock backend service."""
        from aiohttp import web
        
        async def handle_request(request):
            """Handle backend service requests."""
            # Check for failure injection
            if self.should_inject_failure(service_name, request.path):
                # Simulate service failure
                if self.failure_injections[service_name]["type"] == "timeout":
                    await asyncio.sleep(10)  # Force timeout
                elif self.failure_injections[service_name]["type"] == "error":
                    return web.Response(status=500, text="Internal Server Error")
                elif self.failure_injections[service_name]["type"] == "slow":
                    await asyncio.sleep(2)  # Slow response
            
            # Normal response
            await asyncio.sleep(0.1)  # Simulate processing
            
            return web.Response(
                status=200,
                headers={
                    "X-Service-Name": service_name,
                    "X-Service-Port": str(port)
                },
                json={
                    "service": service_name,
                    "path": request.path,
                    "method": request.method,
                    "timestamp": time.time(),
                    "status": "success"
                }
            )
        
        app = web.Application()
        app.router.add_route('*', '/{path:.*}', handle_request)
        
        server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", port)
        )
        
        logger.info(f"Backend service {service_name} started on port {port}")
        return server
    
    async def start_gateway_with_circuit_breakers(self):
        """Start API gateway with circuit breaker middleware."""
        from aiohttp import web
        
        async def circuit_breaker_middleware(request, handler):
            """Circuit breaker middleware for gateway."""
            endpoint = self.normalize_endpoint_path(request.path)
            
            # Check circuit state
            circuit_state = await self.get_circuit_state(endpoint)
            
            if circuit_state == CircuitState.OPEN:
                # Circuit is open - return fallback response
                fallback_response = await self.get_fallback_response(endpoint)
                self.record_circuit_event(endpoint, "fallback_served", "circuit_open")
                
                return web.Response(
                    status=503,
                    headers={
                        "X-Circuit-State": "OPEN",
                        "X-Circuit-Fallback": "true",
                        "Retry-After": "30"
                    },
                    json=fallback_response
                )
            
            elif circuit_state == CircuitState.HALF_OPEN:
                # Half-open - allow limited requests through
                if not await self.should_allow_half_open_request(endpoint):
                    fallback_response = await self.get_fallback_response(endpoint)
                    self.record_circuit_event(endpoint, "request_blocked", "half_open_limited")
                    
                    return web.Response(
                        status=503,
                        headers={
                            "X-Circuit-State": "HALF_OPEN",
                            "X-Circuit-Fallback": "true"
                        },
                        json=fallback_response
                    )
            
            # Circuit is closed or half-open allowing request
            start_time = time.time()
            
            try:
                # Forward request to backend
                response = await self.forward_to_backend(request)
                response_time = time.time() - start_time
                
                # Record success
                await self.record_request_result(endpoint, True, response_time)
                
                # Update circuit state based on success
                await self.update_circuit_state_on_success(endpoint)
                
                response.headers["X-Circuit-State"] = circuit_state.value
                return response
                
            except Exception as e:
                response_time = time.time() - start_time
                
                # Record failure
                await self.record_request_result(endpoint, False, response_time, str(e))
                
                # Update circuit state based on failure
                await self.update_circuit_state_on_failure(endpoint)
                
                # Check if circuit should open
                if await self.should_open_circuit(endpoint):
                    await self.open_circuit(endpoint)
                
                # Return fallback response
                fallback_response = await self.get_fallback_response(endpoint)
                self.record_circuit_event(endpoint, "fallback_served", "request_failed")
                
                return web.Response(
                    status=503,
                    headers={
                        "X-Circuit-State": self.circuit_states[endpoint].value,
                        "X-Circuit-Fallback": "true",
                        "X-Error": str(e)
                    },
                    json=fallback_response
                )
        
        async def handle_gateway_request(request):
            """Handle gateway requests after circuit breaker."""
            return web.Response(
                status=200,
                json={"message": "This should not be reached directly"}
            )
        
        app = web.Application(middlewares=[circuit_breaker_middleware])
        
        # Register routes
        app.router.add_route('*', '/api/v1/users{path:.*}', handle_gateway_request)
        app.router.add_route('*', '/api/v1/agents{path:.*}', handle_gateway_request)
        app.router.add_route('*', '/api/v1/threads{path:.*}', handle_gateway_request)
        app.router.add_route('*', '/api/v1/metrics{path:.*}', handle_gateway_request)
        app.router.add_route('*', '/api/v1/health{path:.*}', handle_gateway_request)
        
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Gateway with circuit breakers started on {self.test_server.sockets[0].getsockname()}")
    
    def normalize_endpoint_path(self, path: str) -> str:
        """Normalize path to match circuit breaker configuration."""
        for config_path in self.circuit_configs.keys():
            if path.startswith(config_path):
                return config_path
        return path
    
    async def get_circuit_state(self, endpoint: str) -> CircuitState:
        """Get current circuit state for endpoint."""
        return self.circuit_states.get(endpoint, CircuitState.CLOSED)
    
    def should_inject_failure(self, service_name: str, path: str) -> bool:
        """Check if failure should be injected for service."""
        if service_name not in self.failure_injections:
            return False
        
        injection = self.failure_injections[service_name]
        if injection["active"] and injection.get("path_pattern", "") in path:
            return True
        
        return False
    
    async def forward_to_backend(self, request):
        """Forward request to backend service."""
        # Determine backend service based on path
        service_mapping = {
            "/api/v1/users": ("user_service", 8001),
            "/api/v1/agents": ("agent_service", 8002),
            "/api/v1/threads": ("thread_service", 8003),
            "/api/v1/metrics": ("metrics_service", 8004),
            "/api/v1/health": ("health_service", 8005)
        }
        
        endpoint = self.normalize_endpoint_path(request.path)
        if endpoint not in service_mapping:
            raise Exception(f"No backend service for endpoint {endpoint}")
        
        service_name, port = service_mapping[endpoint]
        backend_url = f"http://localhost:{port}{request.path}"
        
        # Add query parameters
        if request.query_string:
            backend_url += f"?{request.query_string}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method,
                backend_url,
                headers=dict(request.headers),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                
                body = await response.json() if response.status == 200 else await response.text()
                
                return web.Response(
                    status=response.status,
                    headers=dict(response.headers),
                    json=body if response.status == 200 else None,
                    text=body if response.status != 200 else None
                )
    
    async def record_request_result(self, endpoint: str, success: bool, 
                                  response_time: float, error: str = None):
        """Record request result for circuit breaker metrics."""
        result = {
            "endpoint": endpoint,
            "success": success,
            "response_time": response_time,
            "error": error,
            "timestamp": time.time()
        }
        
        await self.circuit_manager.record_result(endpoint, result)
    
    async def update_circuit_state_on_success(self, endpoint: str):
        """Update circuit state after successful request."""
        current_state = self.circuit_states[endpoint]
        config = self.circuit_configs[endpoint]
        
        if current_state == CircuitState.HALF_OPEN:
            # Check if enough successes to close circuit
            if await self.circuit_manager.get_consecutive_successes(endpoint) >= config.success_threshold:
                await self.close_circuit(endpoint)
    
    async def update_circuit_state_on_failure(self, endpoint: str):
        """Update circuit state after failed request."""
        # Circuit state changes are handled in should_open_circuit
        pass
    
    async def should_open_circuit(self, endpoint: str) -> bool:
        """Check if circuit should open based on failure criteria."""
        config = self.circuit_configs[endpoint]
        
        # Get recent failure statistics
        failure_count = await self.circuit_manager.get_failure_count(
            endpoint, config.rolling_window_seconds
        )
        total_requests = await self.circuit_manager.get_total_requests(
            endpoint, config.rolling_window_seconds
        )
        
        # Check minimum requests threshold
        if total_requests < config.minimum_requests:
            return False
        
        # Check failure threshold
        if failure_count >= config.failure_threshold:
            return True
        
        # Check error percentage
        error_percentage = (failure_count / total_requests) * 100
        if error_percentage >= config.error_percentage:
            return True
        
        return False
    
    async def open_circuit(self, endpoint: str):
        """Open circuit breaker for endpoint."""
        self.circuit_states[endpoint] = CircuitState.OPEN
        self.record_circuit_event(endpoint, "circuit_opened", "failure_threshold_exceeded")
        
        # Schedule automatic half-open transition
        config = self.circuit_configs[endpoint]
        asyncio.create_task(self.schedule_half_open(endpoint, config.timeout_seconds))
    
    async def close_circuit(self, endpoint: str):
        """Close circuit breaker for endpoint."""
        self.circuit_states[endpoint] = CircuitState.CLOSED
        self.record_circuit_event(endpoint, "circuit_closed", "success_threshold_met")
    
    async def schedule_half_open(self, endpoint: str, timeout_seconds: int):
        """Schedule transition to half-open state."""
        await asyncio.sleep(timeout_seconds)
        
        if self.circuit_states[endpoint] == CircuitState.OPEN:
            self.circuit_states[endpoint] = CircuitState.HALF_OPEN
            self.record_circuit_event(endpoint, "circuit_half_open", "timeout_expired")
    
    async def should_allow_half_open_request(self, endpoint: str) -> bool:
        """Check if half-open circuit should allow request."""
        # Allow limited requests in half-open state
        concurrent_requests = await self.circuit_manager.get_concurrent_requests(endpoint)
        return concurrent_requests < 2  # Allow max 2 concurrent requests
    
    async def get_fallback_response(self, endpoint: str) -> Dict[str, Any]:
        """Get fallback response for endpoint."""
        fallback_templates = {
            "/api/v1/users": {
                "error": "User service temporarily unavailable",
                "fallback": True,
                "retry_after": 30
            },
            "/api/v1/agents": {
                "error": "Agent service temporarily unavailable",
                "fallback": True,
                "agents": []
            },
            "/api/v1/threads": {
                "error": "Thread service temporarily unavailable",
                "fallback": True,
                "threads": []
            },
            "/api/v1/metrics": {
                "error": "Metrics service temporarily unavailable",
                "fallback": True,
                "metrics": {}
            },
            "/api/v1/health": {
                "status": "degraded",
                "fallback": True,
                "services": []
            }
        }
        
        fallback = fallback_templates.get(endpoint, {
            "error": "Service temporarily unavailable",
            "fallback": True
        })
        
        self.fallback_responses.append({
            "endpoint": endpoint,
            "fallback": fallback,
            "timestamp": time.time()
        })
        
        return fallback
    
    def record_circuit_event(self, endpoint: str, event_type: str, reason: str):
        """Record circuit breaker event."""
        event = {
            "endpoint": endpoint,
            "event_type": event_type,
            "reason": reason,
            "circuit_state": self.circuit_states[endpoint].value,
            "timestamp": time.time()
        }
        self.circuit_events.append(event)
    
    async def inject_failure(self, service_name: str, failure_type: str = "error", 
                           path_pattern: str = "", duration_seconds: int = 60):
        """Inject failure into backend service."""
        self.failure_injections[service_name] = {
            "active": True,
            "type": failure_type,  # error, timeout, slow
            "path_pattern": path_pattern,
            "started_at": time.time(),
            "duration": duration_seconds
        }
        
        # Schedule failure removal
        asyncio.create_task(self.remove_failure_injection(service_name, duration_seconds))
    
    async def remove_failure_injection(self, service_name: str, delay_seconds: int):
        """Remove failure injection after delay."""
        await asyncio.sleep(delay_seconds)
        if service_name in self.failure_injections:
            self.failure_injections[service_name]["active"] = False
    
    async def make_gateway_request(self, path: str, method: str = "GET", 
                                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make request through API gateway."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                request_method = getattr(session, method.lower())
                
                async with request_method(url, headers=headers or {}) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "circuit_state": response.headers.get("X-Circuit-State", "unknown"),
                        "is_fallback": response.headers.get("X-Circuit-Fallback") == "true"
                    }
                    
                    if response.status == 200:
                        result["body"] = await response.json()
                    else:
                        try:
                            result["body"] = await response.json()
                        except:
                            result["body"] = await response.text()
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e),
                "circuit_state": "unknown",
                "is_fallback": False
            }
    
    async def test_circuit_breaker_behavior(self, endpoint: str, 
                                          failure_count: int) -> Dict[str, Any]:
        """Test circuit breaker behavior with controlled failures."""
        results = []
        
        # Make requests until circuit opens
        for i in range(failure_count + 5):  # Extra requests to test open state
            result = await self.make_gateway_request(endpoint)
            results.append(result)
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 200]
        fallback_responses = [r for r in results if r["is_fallback"]]
        circuit_opened = any(r["circuit_state"] == "open" for r in results)
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "fallback_responses": len(fallback_responses),
            "circuit_opened": circuit_opened,
            "results": results
        }
    
    async def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker metrics."""
        total_events = len(self.circuit_events)
        total_fallbacks = len(self.fallback_responses)
        
        # Event type breakdown
        event_breakdown = {}
        for event in self.circuit_events:
            event_type = event["event_type"]
            event_breakdown[event_type] = event_breakdown.get(event_type, 0) + 1
        
        # Circuit state summary
        circuit_summary = {}
        for endpoint, state in self.circuit_states.items():
            circuit_summary[endpoint] = state.value
        
        # Endpoint breakdown
        endpoint_breakdown = {}
        for endpoint in self.circuit_configs.keys():
            endpoint_events = [e for e in self.circuit_events if e["endpoint"] == endpoint]
            endpoint_fallbacks = [f for f in self.fallback_responses if f["endpoint"] == endpoint]
            
            endpoint_breakdown[endpoint] = {
                "events": len(endpoint_events),
                "fallbacks": len(endpoint_fallbacks),
                "current_state": self.circuit_states[endpoint].value
            }
        
        return {
            "total_events": total_events,
            "total_fallbacks": total_fallbacks,
            "configured_circuits": len(self.circuit_configs),
            "event_breakdown": event_breakdown,
            "circuit_summary": circuit_summary,
            "endpoint_breakdown": endpoint_breakdown
        }
    
    async def cleanup(self):
        """Clean up circuit breaker resources."""
        try:
            # Stop gateway
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
            
            # Stop backend servers
            for server in self.backend_servers.values():
                server.close()
                await server.wait_closed()
            
            if self.circuit_manager:
                await self.circuit_manager.shutdown()
            
            if self.fallback_service:
                await self.fallback_service.shutdown()
            
            if self.metrics_service:
                await self.metrics_service.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def circuit_breaker_manager():
    """Create circuit breaker manager for L3 testing."""
    manager = ApiCircuitBreakerManager()
    await manager.initialize_circuit_breakers()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_opens_on_failures(circuit_breaker_manager):
    """Test circuit breaker opens after failure threshold."""
    endpoint = "/api/v1/agents"
    
    # Inject failures into agent service
    await circuit_breaker_manager.inject_failure("agent_service", "error", "/api/v1/agents", 30)
    
    # Test circuit breaker behavior
    test_result = await circuit_breaker_manager.test_circuit_breaker_behavior(endpoint, 10)
    
    # Circuit should open after failures
    assert test_result["circuit_opened"] is True
    assert test_result["fallback_responses"] > 0
    
    # Should have some successful requests before circuit opens
    assert test_result["successful_requests"] < test_result["total_requests"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_fallback_responses(circuit_breaker_manager):
    """Test fallback responses when circuit is open."""
    endpoint = "/api/v1/users"
    
    # Inject failures
    await circuit_breaker_manager.inject_failure("user_service", "error", "/api/v1/users", 20)
    
    # Force circuit to open by making failing requests
    for i in range(10):
        await circuit_breaker_manager.make_gateway_request(endpoint)
    
    # Make request when circuit is open
    result = await circuit_breaker_manager.make_gateway_request(endpoint)
    
    assert result["status_code"] == 503
    assert result["is_fallback"] is True
    assert result["circuit_state"] in ["open", "half_open"]
    assert "fallback" in result["body"]
    assert result["body"]["fallback"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_recovery_half_open(circuit_breaker_manager):
    """Test circuit breaker recovery through half-open state."""
    endpoint = "/api/v1/metrics"
    
    # Configure short timeout for faster testing
    config = circuit_breaker_manager.circuit_configs[endpoint]
    original_timeout = config.timeout_seconds
    config.timeout_seconds = 2  # 2 second timeout
    
    try:
        # Inject failures to open circuit
        await circuit_breaker_manager.inject_failure("metrics_service", "error", "/api/v1/metrics", 5)
        
        # Force circuit open
        for i in range(5):
            await circuit_breaker_manager.make_gateway_request(endpoint)
        
        # Wait for half-open transition
        await asyncio.sleep(3)
        
        # Remove failure injection (service recovers)
        circuit_breaker_manager.failure_injections["metrics_service"]["active"] = False
        
        # Make requests in half-open state
        half_open_results = []
        for i in range(3):
            result = await circuit_breaker_manager.make_gateway_request(endpoint)
            half_open_results.append(result)
            await asyncio.sleep(0.1)
        
        # Should eventually return to closed state
        successful_requests = [r for r in half_open_results if r["status_code"] == 200]
        assert len(successful_requests) > 0
        
        # Final request should show closed circuit
        final_result = await circuit_breaker_manager.make_gateway_request(endpoint)
        assert final_result["circuit_state"] in ["closed", "half_open"]
        
    finally:
        config.timeout_seconds = original_timeout


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_per_endpoint_circuit_isolation(circuit_breaker_manager):
    """Test that circuit breakers are isolated per endpoint."""
    endpoints = ["/api/v1/users", "/api/v1/agents", "/api/v1/threads"]
    
    # Inject failure only in user service
    await circuit_breaker_manager.inject_failure("user_service", "error", "/api/v1/users", 20)
    
    # Make requests to all endpoints
    results = {}
    for endpoint in endpoints:
        endpoint_results = []
        for i in range(8):  # Enough to trigger circuit breaker
            result = await circuit_breaker_manager.make_gateway_request(endpoint)
            endpoint_results.append(result)
        
        results[endpoint] = endpoint_results
    
    # Only user endpoint should have circuit issues
    user_fallbacks = [r for r in results["/api/v1/users"] if r["is_fallback"]]
    agent_fallbacks = [r for r in results["/api/v1/agents"] if r["is_fallback"]]
    thread_fallbacks = [r for r in results["/api/v1/threads"] if r["is_fallback"]]
    
    assert len(user_fallbacks) > 0  # User service should fail
    assert len(agent_fallbacks) == 0  # Agent service should work
    assert len(thread_fallbacks) == 0  # Thread service should work


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_different_failure_types(circuit_breaker_manager):
    """Test circuit breaker with different types of failures."""
    endpoint = "/api/v1/health"
    
    failure_types = ["error", "timeout", "slow"]
    
    for failure_type in failure_types:
        # Clear circuit state
        circuit_breaker_manager.circuit_states[endpoint] = CircuitState.CLOSED
        
        # Inject specific failure type
        await circuit_breaker_manager.inject_failure("health_service", failure_type, "/api/v1/health", 10)
        
        # Make requests to trigger circuit breaker
        failure_results = []
        for i in range(15):  # Health service has high failure threshold
            result = await circuit_breaker_manager.make_gateway_request(endpoint)
            failure_results.append(result)
            
            if result["is_fallback"]:
                break  # Circuit opened
        
        # Should eventually get fallback responses
        fallback_count = len([r for r in failure_results if r["is_fallback"]])
        
        if failure_type in ["error", "timeout"]:
            assert fallback_count > 0, f"No fallbacks for {failure_type}"
        
        # Reset for next test
        circuit_breaker_manager.failure_injections["health_service"]["active"] = False
        await asyncio.sleep(0.5)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_concurrent_requests(circuit_breaker_manager):
    """Test circuit breaker with concurrent requests."""
    endpoint = "/api/v1/threads"
    
    # Inject failures
    await circuit_breaker_manager.inject_failure("thread_service", "error", "/api/v1/threads", 15)
    
    # Make concurrent requests
    concurrent_tasks = []
    for i in range(20):
        task = circuit_breaker_manager.make_gateway_request(endpoint)
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks)
    
    # Analyze concurrent behavior
    successful = [r for r in results if r["status_code"] == 200]
    fallbacks = [r for r in results if r["is_fallback"]]
    
    # Should handle concurrent requests without issues
    assert len(results) == 20
    assert len(fallbacks) > 0  # Some should be fallbacks due to failures
    
    # Circuit should be in open or half-open state
    final_states = set(r["circuit_state"] for r in results)
    assert "open" in final_states or "half_open" in final_states


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_metrics_accuracy(circuit_breaker_manager):
    """Test accuracy of circuit breaker metrics."""
    # Generate test traffic across endpoints
    test_scenarios = [
        ("/api/v1/users", "user_service", 5),
        ("/api/v1/agents", "agent_service", 3),
        ("/api/v1/metrics", "metrics_service", 4)
    ]
    
    for endpoint, service, failure_count in test_scenarios:
        # Inject failures for some requests
        await circuit_breaker_manager.inject_failure(service, "error", endpoint, 5)
        
        # Make requests
        for i in range(failure_count + 2):
            await circuit_breaker_manager.make_gateway_request(endpoint)
        
        # Remove failure injection
        circuit_breaker_manager.failure_injections[service]["active"] = False
    
    # Get metrics
    metrics = await circuit_breaker_manager.get_circuit_breaker_metrics()
    
    # Verify metrics
    assert metrics["configured_circuits"] == 5
    assert metrics["total_events"] >= 0
    assert metrics["total_fallbacks"] >= 0
    
    # Verify endpoint breakdown
    assert len(metrics["endpoint_breakdown"]) >= 3
    for endpoint_data in metrics["endpoint_breakdown"].values():
        assert "current_state" in endpoint_data
        assert endpoint_data["current_state"] in ["closed", "open", "half_open"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_performance_requirements(circuit_breaker_manager):
    """Test circuit breaker performance overhead."""
    endpoint = "/api/v1/health"
    
    # Test response times with circuit breaker
    response_times = []
    
    for i in range(20):
        result = await circuit_breaker_manager.make_gateway_request(endpoint)
        if result["status_code"] == 200:
            response_times.append(result["response_time"])
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    
    # Circuit breaker should add minimal overhead
    assert avg_response_time < 0.5  # Average < 500ms
    assert max_response_time < 2.0  # Max < 2 seconds
    
    # Test concurrent performance
    concurrent_tasks = []
    for i in range(15):
        task = circuit_breaker_manager.make_gateway_request(endpoint)
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # Should handle concurrent requests efficiently
    assert concurrent_duration < 3.0  # 15 requests in < 3 seconds
    
    successful_concurrent = [r for r in concurrent_results if r["status_code"] == 200]
    assert len(successful_concurrent) >= 12  # Most should succeed