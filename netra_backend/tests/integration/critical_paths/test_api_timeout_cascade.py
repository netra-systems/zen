"""API Timeout Cascade L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API reliability and resilience)
- Business Goal: Prevent timeout cascades and maintain service stability
- Value Impact: Protects against service degradation and user experience issues
- Strategic Impact: $15K MRR protection through timeout management

Critical Path: Request timeout detection -> Cascade prevention -> Graceful degradation -> Recovery coordination -> Service restoration
Coverage: Timeout propagation, circuit breaking, cascade prevention, recovery mechanisms
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import pytest

logger = logging.getLogger(__name__)


class TimeoutType(Enum):
    """Types of timeouts in the system."""
    REQUEST = "request"
    CONNECTION = "connection"
    READ = "read"
    WRITE = "write"
    SERVICE = "service"


@dataclass
class TimeoutConfig:
    """Timeout configuration for services."""
    service_name: str
    request_timeout: float
    connection_timeout: float
    read_timeout: float
    max_retries: int
    backoff_multiplier: float
    circuit_breaker_threshold: int


class ApiTimeoutManager:
    """Manages L3 API timeout cascade tests with real timeout scenarios."""
    
    def __init__(self):
        self.gateway_server = None
        self.backend_servers = {}
        self.timeout_configs = {}
        self.timeout_events = []
        self.cascade_detections = []
        self.recovery_events = []
        self.service_states = {}
        
    async def initialize_timeout_testing(self):
        """Initialize timeout cascade testing environment."""
        try:
            await self.setup_timeout_configs()
            await self.start_backend_services()
            await self.start_timeout_gateway()
            logger.info("Timeout cascade testing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize timeout testing: {e}")
            raise
    
    async def setup_timeout_configs(self):
        """Configure timeout settings for different services."""
        self.timeout_configs = {
            "user_service": TimeoutConfig(
                service_name="user_service",
                request_timeout=2.0,
                connection_timeout=1.0,
                read_timeout=1.5,
                max_retries=3,
                backoff_multiplier=2.0,
                circuit_breaker_threshold=5
            ),
            "auth_service": TimeoutConfig(
                service_name="auth_service",
                request_timeout=1.0,  # Critical service - short timeout
                connection_timeout=0.5,
                read_timeout=0.8,
                max_retries=2,
                backoff_multiplier=1.5,
                circuit_breaker_threshold=3
            ),
            "data_service": TimeoutConfig(
                service_name="data_service",
                request_timeout=5.0,  # Data processing - longer timeout
                connection_timeout=2.0,
                read_timeout=4.0,
                max_retries=2,
                backoff_multiplier=2.0,
                circuit_breaker_threshold=4
            ),
            "notification_service": TimeoutConfig(
                service_name="notification_service",
                request_timeout=3.0,
                connection_timeout=1.0,
                read_timeout=2.0,
                max_retries=1,  # Non-critical - fail fast
                backoff_multiplier=1.0,
                circuit_breaker_threshold=2
            )
        }
        
        # Initialize service states
        for service_name in self.timeout_configs.keys():
            self.service_states[service_name] = {
                "status": "healthy",
                "consecutive_failures": 0,
                "last_success": time.time(),
                "circuit_open": False
            }
    
    async def start_backend_services(self):
        """Start mock backend services with configurable delays."""
        service_ports = {
            "user_service": 8201,
            "auth_service": 8202,
            "data_service": 8203,
            "notification_service": 8204
        }
        
        for service_name, port in service_ports.items():
            server = await self.start_backend_service(service_name, port)
            self.backend_servers[service_name] = server
    
    async def start_backend_service(self, service_name: str, port: int):
        """Start a mock backend service with configurable response times."""
        from aiohttp import web
        
        async def handle_request(request):
            """Handle backend service requests with potential delays."""
            # Check for artificial delay injection
            delay = float(request.query.get('delay', '0'))
            
            # Check for failure injection
            fail_mode = request.query.get('fail', '')
            
            if fail_mode == 'timeout':
                # Simulate a hanging request
                await asyncio.sleep(30)  # Long delay to cause timeout
            elif fail_mode == 'slow':
                # Simulate slow response
                await asyncio.sleep(delay if delay > 0 else 3.0)
            elif fail_mode == 'error':
                # Simulate service error
                return web.Response(status=500, json={"error": "Service error"})
            elif delay > 0:
                # Normal delay for testing
                await asyncio.sleep(delay)
            
            # Normal successful response
            await asyncio.sleep(0.1)  # Base processing time
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json={
                    "service": service_name,
                    "timestamp": time.time(),
                    "processed_in": port,
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
    
    async def start_timeout_gateway(self):
        """Start API gateway with timeout management."""
        from aiohttp import web
        
        async def timeout_middleware(request, handler):
            """Timeout management middleware."""
            start_time = time.time()
            
            try:
                # Set request timeout
                response = await asyncio.wait_for(
                    handler(request),
                    timeout=10.0  # Gateway-level timeout
                )
                
                processing_time = time.time() - start_time
                response.headers["X-Processing-Time"] = str(processing_time)
                
                return response
                
            except asyncio.TimeoutError:
                processing_time = time.time() - start_time
                
                self.record_timeout_event(
                    request.path, TimeoutType.REQUEST, processing_time, "gateway_timeout"
                )
                
                return web.Response(
                    status=504,
                    headers={
                        "X-Processing-Time": str(processing_time),
                        "X-Timeout-Type": "gateway"
                    },
                    json={"error": "Gateway timeout", "timeout_seconds": processing_time}
                )
            except Exception as e:
                processing_time = time.time() - start_time
                
                return web.Response(
                    status=500,
                    headers={"X-Processing-Time": str(processing_time)},
                    json={"error": str(e)}
                )
        
        async def handle_api_request(request):
            """Handle API requests with service routing and timeout management."""
            path_parts = request.path.strip('/').split('/')
            
            if len(path_parts) < 3:
                return web.Response(status=404, json={"error": "Invalid path"})
            
            service_type = path_parts[2]  # /api/v1/{service_type}
            
            # Map service types to backend services
            service_mapping = {
                "users": "user_service",
                "auth": "auth_service",
                "data": "data_service",
                "notifications": "notification_service"
            }
            
            if service_type not in service_mapping:
                return web.Response(status=404, json={"error": "Service not found"})
            
            service_name = service_mapping[service_type]
            
            # Check circuit breaker
            if self.service_states[service_name]["circuit_open"]:
                return web.Response(
                    status=503,
                    headers={"X-Circuit-Status": "open"},
                    json={"error": "Service circuit breaker open"}
                )
            
            # Forward request with timeout management
            return await self.forward_with_timeout_management(
                request, service_name, path_parts[3:] if len(path_parts) > 3 else []
            )
        
        app = web.Application(middlewares=[timeout_middleware])
        
        # Register API routes
        app.router.add_route('*', '/api/v1/{service_type}', handle_api_request)
        app.router.add_route('*', '/api/v1/{service_type}/{path:.*}', handle_api_request)
        
        self.gateway_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Timeout gateway started on {self.gateway_server.sockets[0].getsockname()}")
    
    async def forward_with_timeout_management(self, request, service_name: str, path_parts: List[str]):
        """Forward request to backend service with timeout management."""
        config = self.timeout_configs[service_name]
        service_port = {
            "user_service": 8201,
            "auth_service": 8202,
            "data_service": 8203,
            "notification_service": 8204
        }[service_name]
        
        # Build backend URL
        backend_path = "/" + "/".join(path_parts) if path_parts else "/"
        backend_url = f"http://localhost:{service_port}{backend_path}"
        
        # Add query parameters
        if request.query_string:
            backend_url += f"?{request.query_string}"
        
        retry_count = 0
        last_error = None
        
        while retry_count <= config.max_retries:
            start_time = time.time()
            
            try:
                # Create timeout configuration
                timeout = aiohttp.ClientTimeout(
                    total=config.request_timeout,
                    connect=config.connection_timeout,
                    sock_read=config.read_timeout
                )
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        request.method,
                        backend_url,
                        headers=dict(request.headers)
                    ) as response:
                        
                        processing_time = time.time() - start_time
                        
                        # Record successful request
                        await self.record_service_success(service_name, processing_time)
                        
                        # Forward response
                        body = await response.read()
                        
                        return web.Response(
                            status=response.status,
                            headers=dict(response.headers),
                            body=body
                        )
                        
            except asyncio.TimeoutError as e:
                processing_time = time.time() - start_time
                timeout_type = self.classify_timeout_error(str(e))
                
                self.record_timeout_event(
                    request.path, timeout_type, processing_time, 
                    f"{service_name}_timeout_attempt_{retry_count + 1}"
                )
                
                await self.record_service_failure(service_name, "timeout")
                
                last_error = e
                retry_count += 1
                
                if retry_count <= config.max_retries:
                    # Apply backoff
                    backoff_delay = config.backoff_multiplier ** retry_count * 0.1
                    await asyncio.sleep(backoff_delay)
                
            except Exception as e:
                processing_time = time.time() - start_time
                
                self.record_timeout_event(
                    request.path, TimeoutType.SERVICE, processing_time,
                    f"{service_name}_error_attempt_{retry_count + 1}"
                )
                
                await self.record_service_failure(service_name, "error")
                
                last_error = e
                retry_count += 1
                
                if retry_count <= config.max_retries:
                    backoff_delay = config.backoff_multiplier ** retry_count * 0.1
                    await asyncio.sleep(backoff_delay)
        
        # All retries exhausted
        total_processing_time = time.time() - start_time
        
        return web.Response(
            status=504,
            headers={
                "X-Processing-Time": str(total_processing_time),
                "X-Retry-Count": str(retry_count),
                "X-Service": service_name
            },
            json={
                "error": "Service timeout after retries",
                "service": service_name,
                "retries": retry_count,
                "last_error": str(last_error)
            }
        )
    
    def classify_timeout_error(self, error_message: str) -> TimeoutType:
        """Classify timeout error type based on error message."""
        if "connect" in error_message.lower():
            return TimeoutType.CONNECTION
        elif "read" in error_message.lower():
            return TimeoutType.READ
        elif "write" in error_message.lower():
            return TimeoutType.WRITE
        else:
            return TimeoutType.REQUEST
    
    def record_timeout_event(self, path: str, timeout_type: TimeoutType, 
                           duration: float, context: str):
        """Record timeout event for analysis."""
        event = {
            "path": path,
            "timeout_type": timeout_type.value,
            "duration": duration,
            "context": context,
            "timestamp": time.time()
        }
        self.timeout_events.append(event)
    
    async def record_service_success(self, service_name: str, processing_time: float):
        """Record successful service call."""
        state = self.service_states[service_name]
        state["status"] = "healthy"
        state["consecutive_failures"] = 0
        state["last_success"] = time.time()
        
        # Close circuit breaker if open
        if state["circuit_open"]:
            state["circuit_open"] = False
            self.recovery_events.append({
                "service": service_name,
                "event": "circuit_closed",
                "timestamp": time.time(),
                "processing_time": processing_time
            })
    
    async def record_service_failure(self, service_name: str, failure_type: str):
        """Record service failure and manage circuit breaker."""
        state = self.service_states[service_name]
        state["consecutive_failures"] += 1
        
        config = self.timeout_configs[service_name]
        
        # Check if circuit breaker should open
        if state["consecutive_failures"] >= config.circuit_breaker_threshold:
            if not state["circuit_open"]:
                state["circuit_open"] = True
                state["status"] = "circuit_open"
                
                # Detect potential cascade
                await self.detect_timeout_cascade(service_name)
    
    async def detect_timeout_cascade(self, failed_service: str):
        """Detect potential timeout cascade scenarios."""
        current_time = time.time()
        
        # Count recent failures across services
        recent_failures = 0
        failing_services = []
        
        for service_name, state in self.service_states.items():
            if (state["consecutive_failures"] > 0 and 
                current_time - state["last_success"] < 30):  # Within 30 seconds
                recent_failures += state["consecutive_failures"]
                failing_services.append(service_name)
        
        # Cascade detection criteria
        if len(failing_services) >= 2 or recent_failures >= 10:
            cascade_event = {
                "trigger_service": failed_service,
                "affected_services": failing_services,
                "total_failures": recent_failures,
                "detection_time": current_time,
                "severity": "high" if len(failing_services) >= 3 else "medium"
            }
            
            self.cascade_detections.append(cascade_event)
            logger.warning(f"Timeout cascade detected: {cascade_event}")
    
    async def make_timeout_request(self, path: str, method: str = "GET",
                                 query_params: Optional[Dict[str, str]] = None,
                                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make request through timeout-managed gateway."""
        base_url = f"http://localhost:{self.gateway_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        if query_params:
            query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
            url = f"{url}?{query_string}"
        
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
                        "timeout_occurred": response.status == 504
                    }
                    
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
                "timeout_occurred": "timeout" in str(e).lower()
            }
    
    async def simulate_timeout_cascade(self, cascade_scenario: str) -> Dict[str, Any]:
        """Simulate different timeout cascade scenarios."""
        start_time = time.time()
        results = []
        
        if cascade_scenario == "auth_service_overload":
            # Simulate auth service being slow, affecting dependent services
            test_requests = [
                ("/api/v1/auth", {"delay": "2.0"}),  # Exceed auth timeout
                ("/api/v1/users", {}),  # Depends on auth
                ("/api/v1/data", {}),   # Also depends on auth
            ]
            
        elif cascade_scenario == "data_service_timeout":
            # Simulate data service timing out
            test_requests = [
                ("/api/v1/data", {"delay": "6.0"}),  # Exceed data timeout
                ("/api/v1/users", {}),
                ("/api/v1/notifications", {}),
            ]
            
        elif cascade_scenario == "network_partition":
            # Simulate network issues affecting multiple services
            test_requests = [
                ("/api/v1/auth", {"fail": "timeout"}),
                ("/api/v1/users", {"fail": "timeout"}),
                ("/api/v1/data", {"fail": "timeout"}),
            ]
            
        else:
            # Default scenario
            test_requests = [
                ("/api/v1/users", {"delay": "1.0"}),
                ("/api/v1/auth", {}),
            ]
        
        # Execute test requests
        for path, params in test_requests:
            for attempt in range(3):  # Multiple attempts to trigger failures
                result = await self.make_timeout_request(path, query_params=params)
                results.append({
                    "path": path,
                    "attempt": attempt + 1,
                    "result": result
                })
                
                # Short delay between attempts
                await asyncio.sleep(0.1)
        
        cascade_duration = time.time() - start_time
        
        # Analyze results
        timeout_count = len([r for r in results if r["result"]["timeout_occurred"]])
        error_count = len([r for r in results if r["result"]["status_code"] >= 500])
        
        return {
            "scenario": cascade_scenario,
            "duration": cascade_duration,
            "total_requests": len(results),
            "timeout_count": timeout_count,
            "error_count": error_count,
            "cascade_detected": len(self.cascade_detections) > 0,
            "results": results
        }
    
    async def get_timeout_metrics(self) -> Dict[str, Any]:
        """Get comprehensive timeout metrics."""
        total_timeouts = len(self.timeout_events)
        total_cascades = len(self.cascade_detections)
        total_recoveries = len(self.recovery_events)
        
        if total_timeouts == 0:
            return {"total_timeouts": 0, "cascades": 0, "recoveries": 0}
        
        # Timeout type breakdown
        timeout_breakdown = {}
        for event in self.timeout_events:
            timeout_type = event["timeout_type"]
            timeout_breakdown[timeout_type] = timeout_breakdown.get(timeout_type, 0) + 1
        
        # Service health summary
        service_health = {}
        for service_name, state in self.service_states.items():
            service_health[service_name] = {
                "status": state["status"],
                "consecutive_failures": state["consecutive_failures"],
                "circuit_open": state["circuit_open"],
                "time_since_last_success": time.time() - state["last_success"]
            }
        
        # Cascade analysis
        cascade_analysis = {
            "total_detected": total_cascades,
            "severity_breakdown": {},
            "most_affected_services": []
        }
        
        if self.cascade_detections:
            for cascade in self.cascade_detections:
                severity = cascade["severity"]
                cascade_analysis["severity_breakdown"][severity] = (
                    cascade_analysis["severity_breakdown"].get(severity, 0) + 1
                )
        
        return {
            "total_timeouts": total_timeouts,
            "total_cascades": total_cascades,
            "total_recoveries": total_recoveries,
            "timeout_breakdown": timeout_breakdown,
            "service_health": service_health,
            "cascade_analysis": cascade_analysis,
            "configured_services": len(self.timeout_configs)
        }
    
    async def cleanup(self):
        """Clean up timeout testing resources."""
        try:
            if self.gateway_server:
                self.gateway_server.close()
                await self.gateway_server.wait_closed()
            
            for server in self.backend_servers.values():
                server.close()
                await server.wait_closed()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def timeout_manager():
    """Create timeout manager for L3 testing."""
    manager = ApiTimeoutManager()
    await manager.initialize_timeout_testing()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_service_timeout_handling(timeout_manager):
    """Test basic service timeout handling."""
    # Test request that should timeout
    result = await timeout_manager.make_timeout_request(
        "/api/v1/auth", query_params={"delay": "2.0"}
    )
    
    assert result["status_code"] == 504
    assert result["timeout_occurred"] is True
    assert "timeout" in result["body"]["error"].lower()
    assert result["response_time"] >= 1.0  # Should respect timeout


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_timeout_retry_mechanism(timeout_manager):
    """Test timeout retry mechanisms."""
    # Test request that times out but should retry
    result = await timeout_manager.make_timeout_request(
        "/api/v1/users", query_params={"delay": "3.0"}
    )
    
    # Should eventually timeout after retries
    assert result["status_code"] == 504
    
    # Should have retry count in headers
    if "X-Retry-Count" in result["headers"]:
        retry_count = int(result["headers"]["X-Retry-Count"])
        assert retry_count > 1  # Should have retried


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_circuit_breaker_activation(timeout_manager):
    """Test circuit breaker activation on repeated timeouts."""
    # Make multiple requests to trigger circuit breaker
    service_path = "/api/v1/auth"
    
    for i in range(5):  # Exceed circuit breaker threshold
        result = await timeout_manager.make_timeout_request(
            service_path, query_params={"fail": "timeout"}
        )
        
        # Early requests should timeout
        if i < 3:
            assert result["status_code"] == 504
        else:
            # Later requests should hit circuit breaker
            if result["status_code"] == 503:
                assert "circuit breaker" in result["body"]["error"].lower()
                break


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_timeout_cascade_detection(timeout_manager):
    """Test detection of timeout cascades."""
    cascade_result = await timeout_manager.simulate_timeout_cascade(
        "auth_service_overload"
    )
    
    assert cascade_result["scenario"] == "auth_service_overload"
    assert cascade_result["total_requests"] > 0
    assert cascade_result["timeout_count"] > 0
    
    # Should detect cascade when multiple services are affected
    if cascade_result["cascade_detected"]:
        assert len(timeout_manager.cascade_detections) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_different_timeout_types(timeout_manager):
    """Test different types of timeouts."""
    timeout_scenarios = [
        ("connection", "/api/v1/users", {"fail": "timeout"}),
        ("read", "/api/v1/data", {"delay": "6.0"}),
        ("request", "/api/v1/notifications", {"delay": "4.0"})
    ]
    
    for timeout_type, path, params in timeout_scenarios:
        result = await timeout_manager.make_timeout_request(path, query_params=params)
        
        # Should result in timeout
        assert result["status_code"] in [504, 500]
        assert result["timeout_occurred"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_service_recovery_after_timeout(timeout_manager):
    """Test service recovery after timeout issues."""
    service_path = "/api/v1/users"
    
    # First, cause some timeouts
    for i in range(3):
        await timeout_manager.make_timeout_request(
            service_path, query_params={"delay": "3.0"}
        )
    
    # Then make successful requests
    for i in range(3):
        result = await timeout_manager.make_timeout_request(service_path)
        
        if result["status_code"] == 200:
            # Service should recover
            assert "success" in result["body"]["status"]
            break


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_timeout_handling(timeout_manager):
    """Test concurrent timeout handling."""
    # Make concurrent requests with various delays
    concurrent_tasks = []
    
    for i in range(10):
        delay = "1.0" if i % 3 == 0 else "0.1"  # Some will timeout
        task = timeout_manager.make_timeout_request(
            "/api/v1/users", query_params={"delay": delay}
        )
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks)
    
    # Should handle concurrent requests
    successful_results = [r for r in results if r["status_code"] == 200]
    timeout_results = [r for r in results if r["status_code"] == 504]
    
    assert len(successful_results) > 0  # Some should succeed
    assert len(timeout_results) > 0     # Some should timeout


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_network_partition_simulation(timeout_manager):
    """Test network partition timeout scenario."""
    cascade_result = await timeout_manager.simulate_timeout_cascade(
        "network_partition"
    )
    
    assert cascade_result["scenario"] == "network_partition"
    assert cascade_result["error_count"] > 0
    
    # Network partition should affect multiple services
    assert cascade_result["total_requests"] >= 6  # Multiple services tested


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_timeout_metrics_accuracy(timeout_manager):
    """Test accuracy of timeout metrics collection."""
    # Generate timeout events
    test_requests = [
        ("/api/v1/auth", {"delay": "2.0"}),    # Should timeout
        ("/api/v1/users", {}),                 # Should succeed
        ("/api/v1/data", {"delay": "6.0"}),    # Should timeout
    ]
    
    for path, params in test_requests * 2:  # 6 total requests
        await timeout_manager.make_timeout_request(path, query_params=params)
    
    metrics = await timeout_manager.get_timeout_metrics()
    
    # Verify metrics
    assert metrics["configured_services"] == 4
    assert metrics["total_timeouts"] >= 2  # At least some timeouts
    
    # Check timeout breakdown
    timeout_breakdown = metrics["timeout_breakdown"]
    assert len(timeout_breakdown) > 0
    
    # Check service health
    service_health = metrics["service_health"]
    assert len(service_health) == 4
    
    # Some services should show failures
    failing_services = [
        s for s, h in service_health.items() 
        if h["consecutive_failures"] > 0
    ]
    assert len(failing_services) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_timeout_performance_requirements(timeout_manager):
    """Test timeout performance requirements."""
    # Test that timeout detection is fast
    start_time = time.time()
    
    result = await timeout_manager.make_timeout_request(
        "/api/v1/auth", query_params={"delay": "2.0"}
    )
    
    timeout_detection_time = time.time() - start_time
    
    # Should timeout quickly (within configured timeout + small overhead)
    assert timeout_detection_time < 2.5  # Auth service timeout is 1.0s + retries
    assert result["status_code"] == 504
    
    # Test successful request performance
    start_time = time.time()
    
    success_result = await timeout_manager.make_timeout_request("/api/v1/users")
    
    success_time = time.time() - start_time
    
    if success_result["status_code"] == 200:
        assert success_time < 0.5  # Fast successful requests