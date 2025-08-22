"""Circuit Breaker Cascade Prevention L4 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (system resilience foundation)
- Business Goal: Prevent cascading failures that could take down entire platform
- Value Impact: Protects $25K MRR through system-wide availability and resilience
- Strategic Impact: Critical for maintaining SLA commitments and preventing revenue loss during partial service degradation

Critical Path: 
Service health monitoring -> Failure threshold detection -> Circuit breaker activation -> Graceful degradation -> Recovery monitoring

Coverage: Real service failures, circuit breaker state transitions, cascade prevention, staging environment validation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from unittest.mock import AsyncMock

import httpx
import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector

from netra_backend.app.services.circuit_breaker.circuit_breaker_manager import (
    CircuitBreakerManager,
)
from netra_backend.app.services.circuit_breaker.failure_detector import FailureDetector
from netra_backend.app.services.circuit_breaker.service_health_monitor import (
    ServiceHealthMonitor,
)

# Mock staging components for now since staging environment may not be available
class MockStagingTestSuite:
    def __init__(self):
        self.env_config = type('EnvConfig', (), {})()
        self.env_config.services = type('Services', (), {})()
        self.env_config.services.backend = "http://localhost:8000"
        self.env_config.services.auth = "http://localhost:8001"
        self.env_config.services.frontend = "http://localhost:3000"
        self.env_config.services.websocket = "ws://localhost:8000/ws"
    
    async def setup(self):
        pass
    
    async def teardown(self):
        pass

async def get_staging_suite():
    return MockStagingTestSuite()

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"

@dataclass
class ServiceHealthMetrics:
    """Service health metrics container."""
    service_name: str
    success_rate: float
    error_rate: float
    response_time_p95: float
    request_count: int
    circuit_breaker_state: CircuitBreakerState
    failure_count: int
    recovery_time: Optional[float] = None

class CircuitBreakerL4TestSuite:
    """L4 test suite for circuit breaker cascade prevention in staging environment."""
    
    def __init__(self):
        self.staging_suite: Optional[MockStagingTestSuite] = None
        self.circuit_breaker_manager: Optional[CircuitBreakerManager] = None
        self.health_monitor: Optional[ServiceHealthMonitor] = None
        self.failure_detector: Optional[FailureDetector] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.service_endpoints: Dict[str, str] = {}
        self.test_metrics = {
            "circuit_breaker_activations": 0,
            "cascade_failures_prevented": 0,
            "service_recoveries": 0,
            "total_requests_tested": 0,
            "graceful_degradations": 0
        }
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for circuit breaker testing."""
        self.staging_suite = await get_staging_suite()
        await self.staging_suite.setup()
        
        # Get staging service endpoints
        self.service_endpoints = {
            "backend": self.staging_suite.env_config.services.backend,
            "auth": self.staging_suite.env_config.services.auth,
            "frontend": self.staging_suite.env_config.services.frontend,
            "websocket": self.staging_suite.env_config.services.websocket.replace("wss://", "https://").replace("/ws", "")
        }
        
        # Initialize circuit breaker components
        self.circuit_breaker_manager = CircuitBreakerManager()
        await self.circuit_breaker_manager.start()
        
        # Create instances without calling initialize since these don't have that method
        try:
            self.health_monitor = ServiceHealthMonitor()
        except Exception:
            self.health_monitor = None
            
        try:
            self.failure_detector = FailureDetector()
        except Exception:
            self.failure_detector = None
            
        try:
            self.metrics_collector = MetricsCollector()
        except Exception:
            self.metrics_collector = None
        
        # Configure circuit breakers for each service
        await self._configure_service_circuit_breakers()
    
    async def _configure_service_circuit_breakers(self) -> None:
        """Configure circuit breakers for all staging services."""
        from netra_backend.app.services.circuit_breaker.circuit_breaker_manager import ServiceConfig, CircuitBreakerConfig
        
        # Register services with circuit breaker manager
        for service_name, endpoint in self.service_endpoints.items():
            config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=30,
                half_open_max_calls=3,
                timeout_seconds=30.0
            )
            service_config = ServiceConfig(
                name=service_name,
                endpoint=endpoint,
                health_check_url=f"{endpoint}/health",
                circuit_breaker_config=config
            )
            await self.circuit_breaker_manager.register_service(service_config)
    
    async def monitor_service_health(self, service_name: str, 
                                   duration_seconds: int = 60) -> ServiceHealthMetrics:
        """Monitor service health over specified duration."""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        success_count = 0
        error_count = 0
        response_times = []
        failure_count = 0
        
        while time.time() < end_time:
            try:
                # Make health check request
                endpoint = self.service_endpoints[service_name]
                health_url = f"{endpoint}/health/"
                
                request_start = time.time()
                response = await self._make_service_request(health_url)
                request_time = (time.time() - request_start) * 1000  # Convert to ms
                
                response_times.append(request_time)
                self.test_metrics["total_requests_tested"] += 1
                
                if response["success"] and response["status_code"] == 200:
                    success_count += 1
                else:
                    error_count += 1
                    failure_count += 1
                
                # Check circuit breaker state
                cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(
                    service_name
                )
                
                if cb_state == CircuitBreakerState.OPEN:
                    self.test_metrics["circuit_breaker_activations"] += 1
                
                # Brief pause between requests
                await asyncio.sleep(1.0)
                
            except Exception as e:
                error_count += 1
                failure_count += 1
                response_times.append(30000)  # 30s timeout equivalent
        
        total_requests = success_count + error_count
        success_rate = success_count / total_requests if total_requests > 0 else 0
        error_rate = error_count / total_requests if total_requests > 0 else 0
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        
        final_cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
        
        return ServiceHealthMetrics(
            service_name=service_name,
            success_rate=success_rate,
            error_rate=error_rate,
            response_time_p95=p95_response_time,
            request_count=total_requests,
            circuit_breaker_state=final_cb_state,
            failure_count=failure_count
        )
    
    async def _make_service_request(self, url: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Make request to service endpoint with timeout."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "content": response.text[:200]  # First 200 chars
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": str(e),
                "response_time": timeout * 1000
            }
    
    async def simulate_service_failure(self, service_name: str, 
                                     failure_type: str = "high_latency") -> Dict[str, Any]:
        """Simulate service failure to trigger circuit breaker."""
        failure_start_time = time.time()
        
        try:
            if failure_type == "high_latency":
                return await self._simulate_high_latency_failure(service_name)
            elif failure_type == "error_responses":
                return await self._simulate_error_response_failure(service_name)
            elif failure_type == "connection_timeout":
                return await self._simulate_connection_timeout_failure(service_name)
            elif failure_type == "service_unavailable":
                return await self._simulate_service_unavailable_failure(service_name)
            else:
                return {"success": False, "error": f"Unknown failure type: {failure_type}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "failure_duration": time.time() - failure_start_time
            }
    
    async def _simulate_high_latency_failure(self, service_name: str) -> Dict[str, Any]:
        """Simulate high latency failure scenario."""
        endpoint = self.service_endpoints[service_name]
        failure_requests = 0
        successful_triggers = 0
        
        # Send requests with very short timeout to trigger latency failures
        for i in range(10):
            try:
                # Use very short timeout to simulate latency issues
                result = await self._make_service_request(f"{endpoint}/health/", timeout=0.1)
                failure_requests += 1
                
                if not result["success"]:
                    successful_triggers += 1
                
                # Report failure to circuit breaker
                await self.circuit_breaker_manager.record_failure(
                    service_name, "high_latency", result.get("response_time", 100)
                )
                
                await asyncio.sleep(0.5)
                
            except Exception:
                failure_requests += 1
                successful_triggers += 1
        
        # Check if circuit breaker was triggered
        cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
        
        return {
            "success": True,
            "failure_type": "high_latency",
            "failure_requests": failure_requests,
            "successful_triggers": successful_triggers,
            "circuit_breaker_state": cb_state,
            "circuit_breaker_triggered": cb_state == CircuitBreakerState.OPEN
        }
    
    async def _simulate_error_response_failure(self, service_name: str) -> Dict[str, Any]:
        """Simulate error response failure scenario."""
        endpoint = self.service_endpoints[service_name]
        error_requests = 0
        
        # Try to trigger errors by hitting non-existent endpoints
        error_endpoints = [
            f"{endpoint}/nonexistent/endpoint",
            f"{endpoint}/invalid/path/123",
            f"{endpoint}/error/trigger/test"
        ]
        
        for error_endpoint in error_endpoints:
            for attempt in range(3):
                try:
                    result = await self._make_service_request(error_endpoint, timeout=5.0)
                    error_requests += 1
                    
                    # Record failure if status code indicates error
                    if result.get("status_code", 0) >= 400:
                        await self.circuit_breaker_manager.record_failure(
                            service_name, "error_response", result["status_code"]
                        )
                    
                    await asyncio.sleep(0.3)
                    
                except Exception:
                    error_requests += 1
        
        cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
        
        return {
            "success": True,
            "failure_type": "error_responses",
            "error_requests": error_requests,
            "circuit_breaker_state": cb_state,
            "circuit_breaker_triggered": cb_state == CircuitBreakerState.OPEN
        }
    
    async def _simulate_connection_timeout_failure(self, service_name: str) -> Dict[str, Any]:
        """Simulate connection timeout failure scenario."""
        timeout_requests = 0
        
        # Use extremely short timeout to force connection timeouts
        for i in range(8):
            try:
                endpoint = self.service_endpoints[service_name]
                result = await self._make_service_request(f"{endpoint}/health/", timeout=0.01)
                timeout_requests += 1
                
                # This should almost always timeout with 0.01s timeout
                await self.circuit_breaker_manager.record_failure(
                    service_name, "connection_timeout", "timeout"
                )
                
                await asyncio.sleep(0.2)
                
            except Exception:
                timeout_requests += 1
        
        cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
        
        return {
            "success": True,
            "failure_type": "connection_timeout",
            "timeout_requests": timeout_requests,
            "circuit_breaker_state": cb_state,
            "circuit_breaker_triggered": cb_state == CircuitBreakerState.OPEN
        }
    
    async def _simulate_service_unavailable_failure(self, service_name: str) -> Dict[str, Any]:
        """Simulate service unavailable failure scenario."""
        # Try to connect to invalid ports/URLs to simulate service unavailability
        invalid_endpoint = self.service_endpoints[service_name].replace(":443", ":9999")
        unavailable_requests = 0
        
        for i in range(6):
            try:
                result = await self._make_service_request(f"{invalid_endpoint}/health/", timeout=2.0)
                unavailable_requests += 1
                
                await self.circuit_breaker_manager.record_failure(
                    service_name, "service_unavailable", "connection_refused"
                )
                
                await asyncio.sleep(0.5)
                
            except Exception:
                unavailable_requests += 1
        
        cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
        
        return {
            "success": True,
            "failure_type": "service_unavailable",
            "unavailable_requests": unavailable_requests,
            "circuit_breaker_state": cb_state,
            "circuit_breaker_triggered": cb_state == CircuitBreakerState.OPEN
        }
    
    async def test_circuit_breaker_state_transitions(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker state transitions through complete lifecycle."""
        state_transitions = []
        
        try:
            # Start with CLOSED state
            initial_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
            state_transitions.append(("initial", initial_state, time.time()))
            
            # Trigger failures to move to OPEN state
            failure_result = await self.simulate_service_failure(service_name, "high_latency")
            
            # Check if moved to OPEN
            after_failure_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
            state_transitions.append(("after_failure", after_failure_state, time.time()))
            
            if after_failure_state == CircuitBreakerState.OPEN:
                # Wait for recovery timeout to move to HALF_OPEN
                await asyncio.sleep(10)  # Shorter wait for testing
                
                # Force transition to HALF_OPEN
                await self.circuit_breaker_manager.transition_to_half_open(service_name)
                half_open_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
                state_transitions.append(("half_open", half_open_state, time.time()))
                
                # Test successful requests to move back to CLOSED
                if half_open_state == CircuitBreakerState.HALF_OPEN:
                    success_count = 0
                    for i in range(3):
                        try:
                            endpoint = self.service_endpoints[service_name]
                            result = await self._make_service_request(f"{endpoint}/health/", timeout=10.0)
                            
                            if result["success"] and result["status_code"] == 200:
                                await self.circuit_breaker_manager.record_success(service_name)
                                success_count += 1
                            
                            await asyncio.sleep(1.0)
                            
                        except Exception:
                            pass
                    
                    # Check final state
                    final_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
                    state_transitions.append(("final", final_state, time.time()))
                    
                    if final_state == CircuitBreakerState.CLOSED:
                        self.test_metrics["service_recoveries"] += 1
            
            return {
                "success": True,
                "service_name": service_name,
                "state_transitions": state_transitions,
                "completed_full_cycle": len(state_transitions) >= 3,
                "failure_result": failure_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "service_name": service_name,
                "error": str(e),
                "state_transitions": state_transitions
            }
    
    async def test_cascade_failure_prevention(self, failure_scenario: str) -> Dict[str, Any]:
        """Test prevention of cascading failures across services."""
        cascade_start_time = time.time()
        
        try:
            if failure_scenario == "auth_service_failure":
                return await self._test_auth_service_failure_cascade()
            elif failure_scenario == "backend_service_failure":
                return await self._test_backend_service_failure_cascade()
            elif failure_scenario == "websocket_service_failure":
                return await self._test_websocket_service_failure_cascade()
            elif failure_scenario == "multiple_service_failure":
                return await self._test_multiple_service_failure_cascade()
            else:
                return {"success": False, "error": f"Unknown failure scenario: {failure_scenario}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cascade_duration": time.time() - cascade_start_time
            }
    
    async def _test_auth_service_failure_cascade(self) -> Dict[str, Any]:
        """Test cascade prevention when auth service fails."""
        # Simulate auth service failure
        auth_failure = await self.simulate_service_failure("auth", "error_responses")
        
        # Monitor if other services remain healthy
        backend_health = await self.monitor_service_health("backend", duration_seconds=20)
        frontend_health = await self.monitor_service_health("frontend", duration_seconds=20)
        
        # Check for graceful degradation
        degradation_detected = await self._check_graceful_degradation("auth")
        
        cascade_prevented = (
            backend_health.success_rate >= 0.8 and
            frontend_health.success_rate >= 0.7 and
            degradation_detected
        )
        
        if cascade_prevented:
            self.test_metrics["cascade_failures_prevented"] += 1
            self.test_metrics["graceful_degradations"] += 1
        
        return {
            "success": True,
            "failure_scenario": "auth_service_failure",
            "auth_failure_result": auth_failure,
            "backend_health": backend_health,
            "frontend_health": frontend_health,
            "cascade_prevented": cascade_prevented,
            "graceful_degradation": degradation_detected
        }
    
    async def _test_backend_service_failure_cascade(self) -> Dict[str, Any]:
        """Test cascade prevention when backend service fails."""
        # Simulate backend service failure
        backend_failure = await self.simulate_service_failure("backend", "connection_timeout")
        
        # Monitor other services
        auth_health = await self.monitor_service_health("auth", duration_seconds=20)
        websocket_health = await self.monitor_service_health("websocket", duration_seconds=20)
        
        # Check for graceful degradation
        degradation_detected = await self._check_graceful_degradation("backend")
        
        cascade_prevented = (
            auth_health.success_rate >= 0.9 and
            websocket_health.success_rate >= 0.8 and
            degradation_detected
        )
        
        if cascade_prevented:
            self.test_metrics["cascade_failures_prevented"] += 1
            self.test_metrics["graceful_degradations"] += 1
        
        return {
            "success": True,
            "failure_scenario": "backend_service_failure",
            "backend_failure_result": backend_failure,
            "auth_health": auth_health,
            "websocket_health": websocket_health,
            "cascade_prevented": cascade_prevented,
            "graceful_degradation": degradation_detected
        }
    
    async def _test_websocket_service_failure_cascade(self) -> Dict[str, Any]:
        """Test cascade prevention when WebSocket service fails."""
        # Simulate WebSocket service failure
        ws_failure = await self.simulate_service_failure("websocket", "service_unavailable")
        
        # Monitor other services
        backend_health = await self.monitor_service_health("backend", duration_seconds=20)
        auth_health = await self.monitor_service_health("auth", duration_seconds=20)
        
        # Check for graceful degradation
        degradation_detected = await self._check_graceful_degradation("websocket")
        
        cascade_prevented = (
            backend_health.success_rate >= 0.9 and
            auth_health.success_rate >= 0.9 and
            degradation_detected
        )
        
        if cascade_prevented:
            self.test_metrics["cascade_failures_prevented"] += 1
            self.test_metrics["graceful_degradations"] += 1
        
        return {
            "success": True,
            "failure_scenario": "websocket_service_failure",
            "websocket_failure_result": ws_failure,
            "backend_health": backend_health,
            "auth_health": auth_health,
            "cascade_prevented": cascade_prevented,
            "graceful_degradation": degradation_detected
        }
    
    async def _test_multiple_service_failure_cascade(self) -> Dict[str, Any]:
        """Test cascade prevention when multiple services fail simultaneously."""
        # Simulate multiple service failures
        auth_failure = await self.simulate_service_failure("auth", "high_latency")
        websocket_failure = await self.simulate_service_failure("websocket", "error_responses")
        
        # Monitor remaining service
        backend_health = await self.monitor_service_health("backend", duration_seconds=25)
        
        # Check for system-wide graceful degradation
        system_degradation = await self._check_system_wide_degradation()
        
        cascade_prevented = (
            backend_health.success_rate >= 0.7 and  # Lower threshold due to multiple failures
            system_degradation["graceful_degradation_active"]
        )
        
        if cascade_prevented:
            self.test_metrics["cascade_failures_prevented"] += 1
            self.test_metrics["graceful_degradations"] += 1
        
        return {
            "success": True,
            "failure_scenario": "multiple_service_failure",
            "auth_failure_result": auth_failure,
            "websocket_failure_result": websocket_failure,
            "backend_health": backend_health,
            "cascade_prevented": cascade_prevented,
            "system_degradation": system_degradation
        }
    
    async def _check_graceful_degradation(self, failed_service: str) -> bool:
        """Check if graceful degradation is active for failed service."""
        try:
            # Check if circuit breaker is open for failed service
            cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(failed_service)
            
            # Check if fallback mechanisms are active
            fallback_active = await self.circuit_breaker_manager.is_fallback_active(failed_service)
            
            # Check if dependent services are handling the failure gracefully
            dependent_services = await self.circuit_breaker_manager.get_dependent_services(failed_service)
            graceful_handling = True
            
            for service in dependent_services:
                service_cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service)
                if service_cb_state == CircuitBreakerState.OPEN:
                    graceful_handling = False
                    break
            
            return (
                cb_state == CircuitBreakerState.OPEN and
                fallback_active and
                graceful_handling
            )
            
        except Exception:
            return False
    
    async def _check_system_wide_degradation(self) -> Dict[str, Any]:
        """Check system-wide graceful degradation status."""
        try:
            # Get overall system health
            system_health = await self.health_monitor.get_system_health_status()
            
            # Check if emergency protocols are active
            emergency_protocols = await self.circuit_breaker_manager.are_emergency_protocols_active()
            
            # Check load balancing adjustments
            load_balancing_adjusted = await self.circuit_breaker_manager.is_load_balancing_adjusted()
            
            return {
                "graceful_degradation_active": (
                    system_health.get("degraded_mode", False) and
                    emergency_protocols and
                    load_balancing_adjusted
                ),
                "system_health_score": system_health.get("health_score", 0),
                "emergency_protocols_active": emergency_protocols,
                "load_balancing_adjusted": load_balancing_adjusted
            }
            
        except Exception as e:
            return {
                "graceful_degradation_active": False,
                "error": str(e)
            }
    
    async def test_recovery_monitoring(self, service_name: str) -> Dict[str, Any]:
        """Test recovery monitoring and automatic recovery process."""
        recovery_start_time = time.time()
        
        try:
            # First, trigger circuit breaker
            failure_result = await self.simulate_service_failure(service_name, "high_latency")
            
            # Verify circuit breaker is open
            cb_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
            
            if cb_state != CircuitBreakerState.OPEN:
                return {
                    "success": False,
                    "error": "Circuit breaker not triggered",
                    "circuit_breaker_state": cb_state
                }
            
            # Wait for recovery timeout and monitor recovery process
            recovery_timeout = 30  # seconds
            recovery_start = time.time()
            
            while time.time() - recovery_start < recovery_timeout:
                current_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
                
                if current_state == CircuitBreakerState.HALF_OPEN:
                    # Test recovery with successful requests
                    recovery_success = await self._test_service_recovery(service_name)
                    
                    if recovery_success:
                        final_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
                        
                        if final_state == CircuitBreakerState.CLOSED:
                            recovery_time = time.time() - recovery_start
                            self.test_metrics["service_recoveries"] += 1
                            
                            return {
                                "success": True,
                                "service_name": service_name,
                                "recovery_time": recovery_time,
                                "recovery_successful": True,
                                "final_state": final_state
                            }
                    
                    break
                
                await asyncio.sleep(2.0)
            
            # If we get here, recovery didn't complete within timeout
            final_state = await self.circuit_breaker_manager.get_circuit_breaker_state(service_name)
            
            return {
                "success": False,
                "service_name": service_name,
                "recovery_time": time.time() - recovery_start,
                "recovery_successful": False,
                "final_state": final_state,
                "error": "Recovery timeout"
            }
            
        except Exception as e:
            return {
                "success": False,
                "service_name": service_name,
                "error": str(e),
                "recovery_time": time.time() - recovery_start_time
            }
    
    async def _test_service_recovery(self, service_name: str) -> bool:
        """Test service recovery with successful requests."""
        try:
            endpoint = self.service_endpoints[service_name]
            success_count = 0
            required_successes = 2  # Based on circuit breaker config
            
            for i in range(required_successes + 1):
                result = await self._make_service_request(f"{endpoint}/health/", timeout=10.0)
                
                if result["success"] and result["status_code"] == 200:
                    await self.circuit_breaker_manager.record_success(service_name)
                    success_count += 1
                else:
                    await self.circuit_breaker_manager.record_failure(
                        service_name, "recovery_test", result.get("status_code", 0)
                    )
                
                await asyncio.sleep(1.0)
            
            return success_count >= required_successes
            
        except Exception:
            return False
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources."""
        try:
            # Reset all circuit breakers to closed state
            for service_name in self.service_endpoints.keys():
                await self.circuit_breaker_manager.reset_circuit_breaker(service_name)
            
            # Shutdown components
            if self.circuit_breaker_manager:
                await self.circuit_breaker_manager.shutdown()
            if self.health_monitor:
                await self.health_monitor.shutdown()
            if self.failure_detector:
                await self.failure_detector.shutdown()
            if self.metrics_collector:
                await self.metrics_collector.shutdown()
                
        except Exception as e:
            print(f"Cleanup warning: {e}")

@pytest.fixture
async def circuit_breaker_l4_suite():
    """Create L4 circuit breaker test suite."""
    suite = CircuitBreakerL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.staging
async def test_circuit_breaker_activation_on_service_failure_l4(circuit_breaker_l4_suite):
    """Test circuit breaker activation when service fails in staging."""
    # Test circuit breaker state transitions for backend service
    transition_result = await circuit_breaker_l4_suite.test_circuit_breaker_state_transitions("backend")
    
    # Validate state transitions
    assert transition_result["success"] is True, f"State transition test failed: {transition_result.get('error')}"
    
    # Validate failure triggered circuit breaker
    failure_result = transition_result["failure_result"]
    assert failure_result["circuit_breaker_triggered"] is True, "Circuit breaker was not triggered by failures"
    
    # Validate state transition sequence
    state_transitions = transition_result["state_transitions"]
    assert len(state_transitions) >= 2, "Insufficient state transitions recorded"
    
    # Check if circuit breaker went through expected states
    states_seen = [transition[1] for transition in state_transitions]
    assert CircuitBreakerState.OPEN in states_seen, "Circuit breaker never opened"

@pytest.mark.asyncio
@pytest.mark.staging
async def test_cascade_failure_prevention_auth_service_l4(circuit_breaker_l4_suite):
    """Test cascade failure prevention when auth service fails in staging."""
    # Test auth service failure cascade prevention
    cascade_result = await circuit_breaker_l4_suite.test_cascade_failure_prevention(
        "auth_service_failure"
    )
    
    # Validate cascade prevention
    assert cascade_result["success"] is True
    assert cascade_result["cascade_prevented"] is True, "Cascade failure was not prevented"
    assert cascade_result["graceful_degradation"] is True, "Graceful degradation not activated"
    
    # Validate other services remained healthy
    backend_health = cascade_result["backend_health"]
    frontend_health = cascade_result["frontend_health"]
    
    assert backend_health.success_rate >= 0.8, f"Backend service too unhealthy: {backend_health.success_rate}"
    assert frontend_health.success_rate >= 0.7, f"Frontend service too unhealthy: {frontend_health.success_rate}"
    
    # Validate auth service circuit breaker was triggered
    auth_failure = cascade_result["auth_failure_result"]
    assert auth_failure["circuit_breaker_triggered"] is True

@pytest.mark.asyncio
@pytest.mark.staging
async def test_cascade_failure_prevention_backend_service_l4(circuit_breaker_l4_suite):
    """Test cascade failure prevention when backend service fails in staging."""
    # Test backend service failure cascade prevention
    cascade_result = await circuit_breaker_l4_suite.test_cascade_failure_prevention(
        "backend_service_failure"
    )
    
    # Validate cascade prevention
    assert cascade_result["success"] is True
    assert cascade_result["cascade_prevented"] is True, "Cascade failure was not prevented"
    
    # Validate other services remained healthy
    auth_health = cascade_result["auth_health"]
    websocket_health = cascade_result["websocket_health"]
    
    assert auth_health.success_rate >= 0.9, f"Auth service affected by backend failure: {auth_health.success_rate}"
    assert websocket_health.success_rate >= 0.8, f"WebSocket service affected by backend failure: {websocket_health.success_rate}"

@pytest.mark.asyncio
@pytest.mark.staging  
async def test_multiple_service_failure_cascade_prevention_l4(circuit_breaker_l4_suite):
    """Test cascade prevention when multiple services fail simultaneously in staging."""
    # Test multiple service failure scenario
    cascade_result = await circuit_breaker_l4_suite.test_cascade_failure_prevention(
        "multiple_service_failure"
    )
    
    # Validate cascade prevention under stress
    assert cascade_result["success"] is True
    assert cascade_result["cascade_prevented"] is True, "Multiple service failure cascade not prevented"
    
    # Validate remaining service health
    backend_health = cascade_result["backend_health"]
    assert backend_health.success_rate >= 0.7, f"Backend service failed under multiple service failure load: {backend_health.success_rate}"
    
    # Validate system-wide graceful degradation
    system_degradation = cascade_result["system_degradation"]
    assert system_degradation["graceful_degradation_active"] is True, "System-wide graceful degradation not active"
    
    # Validate emergency protocols
    assert system_degradation["emergency_protocols_active"] is True, "Emergency protocols not activated"

@pytest.mark.asyncio
@pytest.mark.staging
async def test_circuit_breaker_recovery_monitoring_l4(circuit_breaker_l4_suite):
    """Test circuit breaker recovery monitoring and automatic recovery in staging."""
    # Test recovery for WebSocket service
    recovery_result = await circuit_breaker_l4_suite.test_recovery_monitoring("websocket")
    
    # Validate recovery process
    assert recovery_result["success"] is True, f"Recovery test failed: {recovery_result.get('error')}"
    assert recovery_result["recovery_successful"] is True, "Service recovery was not successful"
    assert recovery_result["final_state"] == CircuitBreakerState.CLOSED, "Circuit breaker did not return to CLOSED state"
    
    # Validate recovery time
    assert recovery_result["recovery_time"] < 60.0, f"Recovery took too long: {recovery_result['recovery_time']}s"
    
    # Validate metrics
    assert circuit_breaker_l4_suite.test_metrics["service_recoveries"] >= 1

@pytest.mark.asyncio
@pytest.mark.staging
async def test_circuit_breaker_half_open_state_behavior_l4(circuit_breaker_l4_suite):
    """Test circuit breaker half-open state behavior in staging."""
    service_name = "frontend"
    
    # Trigger circuit breaker to open state
    failure_result = await circuit_breaker_l4_suite.simulate_service_failure(
        service_name, "connection_timeout"
    )
    
    assert failure_result["circuit_breaker_triggered"] is True, "Circuit breaker not triggered"
    
    # Force transition to half-open
    await circuit_breaker_l4_suite.circuit_breaker_manager.transition_to_half_open(service_name)
    
    # Verify half-open state
    half_open_state = await circuit_breaker_l4_suite.circuit_breaker_manager.get_circuit_breaker_state(service_name)
    assert half_open_state == CircuitBreakerState.HALF_OPEN, "Circuit breaker not in half-open state"
    
    # Test limited request processing in half-open state
    endpoint = circuit_breaker_l4_suite.service_endpoints[service_name]
    successful_requests = 0
    
    for i in range(5):  # Try more requests than half-open allows
        try:
            result = await circuit_breaker_l4_suite._make_service_request(f"{endpoint}/health/", timeout=10.0)
            
            if result["success"] and result["status_code"] == 200:
                await circuit_breaker_l4_suite.circuit_breaker_manager.record_success(service_name)
                successful_requests += 1
            
            await asyncio.sleep(0.5)
            
        except Exception:
            pass
    
    # Check final state after half-open testing
    final_state = await circuit_breaker_l4_suite.circuit_breaker_manager.get_circuit_breaker_state(service_name)
    
    # Should either return to CLOSED (if enough successes) or stay HALF_OPEN/go to OPEN
    assert final_state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN]
    
    # Validate limited request processing worked
    assert successful_requests >= 2, f"Too few successful requests in half-open: {successful_requests}"

@pytest.mark.asyncio
@pytest.mark.staging
async def test_service_health_monitoring_accuracy_l4(circuit_breaker_l4_suite):
    """Test accuracy of service health monitoring in staging."""
    # Monitor all services for a period
    monitoring_duration = 30  # seconds
    
    service_health_results = {}
    
    for service_name in circuit_breaker_l4_suite.service_endpoints.keys():
        health_metrics = await circuit_breaker_l4_suite.monitor_service_health(
            service_name, monitoring_duration
        )
        service_health_results[service_name] = health_metrics
    
    # Validate health monitoring accuracy
    for service_name, health_metrics in service_health_results.items():
        # Validate reasonable request count
        assert health_metrics.request_count >= 20, f"Too few requests monitored for {service_name}: {health_metrics.request_count}"
        
        # Validate response time monitoring
        assert health_metrics.response_time_p95 > 0, f"Invalid response time for {service_name}"
        assert health_metrics.response_time_p95 < 30000, f"Response time too high for {service_name}: {health_metrics.response_time_p95}ms"
        
        # Validate success rate is reasonable for healthy services
        if health_metrics.circuit_breaker_state == CircuitBreakerState.CLOSED:
            assert health_metrics.success_rate >= 0.8, f"Success rate too low for healthy {service_name}: {health_metrics.success_rate}"
        
        # Validate error rate calculation
        assert 0 <= health_metrics.error_rate <= 1, f"Invalid error rate for {service_name}: {health_metrics.error_rate}"
        assert abs(health_metrics.success_rate + health_metrics.error_rate - 1.0) < 0.01, f"Success and error rates don't sum to 1 for {service_name}"
    
    # Validate overall system health
    total_requests = sum(metrics.request_count for metrics in service_health_results.values())
    assert total_requests >= 80, f"Insufficient total monitoring requests: {total_requests}"

@pytest.mark.asyncio
@pytest.mark.staging
async def test_circuit_breaker_performance_under_load_l4(circuit_breaker_l4_suite):
    """Test circuit breaker performance under high load in staging."""
    # Monitor system performance during concurrent service monitoring
    concurrent_monitoring_tasks = []
    
    for service_name in circuit_breaker_l4_suite.service_endpoints.keys():
        task = circuit_breaker_l4_suite.monitor_service_health(service_name, duration_seconds=20)
        concurrent_monitoring_tasks.append(task)
    
    # Execute concurrent monitoring
    start_time = time.time()
    health_results = await asyncio.gather(*concurrent_monitoring_tasks, return_exceptions=True)
    total_duration = time.time() - start_time
    
    # Validate performance under load
    successful_monitoring = [r for r in health_results if not isinstance(r, Exception)]
    assert len(successful_monitoring) >= 3, f"Only {len(successful_monitoring)}/4 services monitored successfully under load"
    
    # Validate monitoring performance
    assert total_duration < 30.0, f"Concurrent monitoring took too long: {total_duration}s"
    
    # Validate circuit breaker responsiveness
    total_circuit_breaker_activations = circuit_breaker_l4_suite.test_metrics["circuit_breaker_activations"]
    total_cascade_preventions = circuit_breaker_l4_suite.test_metrics["cascade_failures_prevented"]
    
    # Validate metrics collection
    assert circuit_breaker_l4_suite.test_metrics["total_requests_tested"] >= 200, "Insufficient requests tested under load"
    
    # Performance should not degrade circuit breaker functionality
    for health_result in successful_monitoring:
        if isinstance(health_result, ServiceHealthMetrics):
            assert health_result.request_count >= 15, f"Service monitoring degraded under load"