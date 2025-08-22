"""Error Circuit Breakers Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Prevent cascading failures and maintain system stability
- Value Impact: Protects against service outages, maintains user experience during failures
- Strategic Impact: $35K-55K MRR protection through fault-tolerant architecture

Critical Path: Error detection -> Circuit state management -> Fallback activation -> Recovery monitoring -> Service restoration
Coverage: Circuit breaker patterns, failure isolation, graceful degradation, automatic recovery
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.services.circuit_breaker.circuit_breaker_service import (
    CircuitBreakerService,
)
from netra_backend.app.services.circuit_breaker.circuit_state import (
    CircuitBreaker,
    CircuitState,
)
from netra_backend.app.services.fallback_service import FallbackService
from netra_backend.app.services.health_check_service import HealthCheckService

logger = logging.getLogger(__name__)

class CircuitBreakerManager:
    """Manages circuit breaker testing with real failure simulation."""
    
    def __init__(self):
        self.circuit_service = None
        self.health_service = None
        self.fallback_service = None
        self.circuit_breakers = {}
        self.failure_history = []
        self.recovery_events = []
        self.metrics = {
            "total_requests": 0,
            "failed_requests": 0,
            "circuit_trips": 0,
            "successful_recoveries": 0,
            "fallback_activations": 0
        }
        
    async def initialize_services(self):
        """Initialize circuit breaker services."""
        try:
            self.circuit_service = CircuitBreakerService()
            await self.circuit_service.initialize()
            
            self.health_service = HealthCheckService()
            await self.health_service.start()
            
            self.fallback_service = FallbackService()
            await self.fallback_service.initialize()
            
            logger.info("Circuit breaker services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize circuit breaker services: {e}")
            raise
    
    async def create_circuit_breaker(self, service_name: str, config: Dict[str, Any] = None) -> str:
        """Create a circuit breaker for a service."""
        breaker_id = f"cb_{service_name}_{uuid.uuid4().hex[:8]}"
        
        default_config = {
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "success_threshold": 3,
            "timeout": 10
        }
        
        if config:
            default_config.update(config)
        
        try:
            circuit_breaker = CircuitBreaker(
                name=service_name,
                failure_threshold=default_config["failure_threshold"],
                recovery_timeout=default_config["recovery_timeout"],
                success_threshold=default_config["success_threshold"],
                timeout=default_config["timeout"]
            )
            
            self.circuit_breakers[breaker_id] = {
                "circuit": circuit_breaker,
                "service_name": service_name,
                "config": default_config,
                "created_at": time.time(),
                "request_count": 0,
                "failure_count": 0
            }
            
            return breaker_id
            
        except Exception as e:
            logger.error(f"Failed to create circuit breaker for {service_name}: {e}")
            raise
    
    async def simulate_service_request(self, breaker_id: str, should_fail: bool = False, 
                                     response_time: float = 0.1) -> Dict[str, Any]:
        """Simulate a service request through circuit breaker."""
        if breaker_id not in self.circuit_breakers:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        breaker_info = self.circuit_breakers[breaker_id]
        circuit = breaker_info["circuit"]
        request_start = time.time()
        
        try:
            self.metrics["total_requests"] += 1
            breaker_info["request_count"] += 1
            
            # Check circuit state before request
            if circuit.state == CircuitState.OPEN:
                # Circuit is open, request should be rejected
                self.metrics["fallback_activations"] += 1
                fallback_response = await self.execute_fallback(breaker_info["service_name"])
                
                return {
                    "success": False,
                    "circuit_open": True,
                    "fallback_executed": True,
                    "fallback_response": fallback_response,
                    "response_time": time.time() - request_start
                }
            
            # Execute request (simulate)
            await asyncio.sleep(response_time)
            
            if should_fail:
                # Simulate service failure
                circuit.record_failure()
                self.metrics["failed_requests"] += 1
                breaker_info["failure_count"] += 1
                
                # Record failure event
                failure_event = {
                    "breaker_id": breaker_id,
                    "service_name": breaker_info["service_name"],
                    "timestamp": time.time(),
                    "failure_type": "simulated_failure",
                    "circuit_state_after": circuit.state.value
                }
                
                self.failure_history.append(failure_event)
                
                # Check if circuit tripped
                if circuit.state == CircuitState.OPEN:
                    self.metrics["circuit_trips"] += 1
                
                raise Exception("Simulated service failure")
            
            else:
                # Simulate successful request
                circuit.record_success()
                
                # Check for circuit recovery
                if circuit.state == CircuitState.CLOSED and breaker_info["failure_count"] > 0:
                    recovery_event = {
                        "breaker_id": breaker_id,
                        "service_name": breaker_info["service_name"],
                        "timestamp": time.time(),
                        "previous_failures": breaker_info["failure_count"],
                        "recovery_method": "success_threshold_met"
                    }
                    
                    self.recovery_events.append(recovery_event)
                    self.metrics["successful_recoveries"] += 1
                    breaker_info["failure_count"] = 0
                
                return {
                    "success": True,
                    "circuit_open": False,
                    "response_time": time.time() - request_start,
                    "circuit_state": circuit.state.value
                }
            
        except Exception as e:
            return {
                "success": False,
                "circuit_open": circuit.state == CircuitState.OPEN,
                "error": str(e),
                "response_time": time.time() - request_start,
                "circuit_state": circuit.state.value
            }
    
    async def execute_fallback(self, service_name: str) -> Dict[str, Any]:
        """Execute fallback logic when circuit is open."""
        try:
            if service_name == "llm_service":
                return {
                    "response": "I'm experiencing high load. Please try again shortly.",
                    "fallback_type": "cached_response",
                    "degraded": True
                }
            elif service_name == "database_service":
                return {
                    "data": "cached_data",
                    "fallback_type": "cache_lookup",
                    "degraded": True
                }
            elif service_name == "external_api":
                return {
                    "result": "default_result",
                    "fallback_type": "default_response",
                    "degraded": True
                }
            else:
                return {
                    "message": "Service temporarily unavailable",
                    "fallback_type": "generic_fallback",
                    "degraded": True
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "fallback_type": "error_fallback",
                "degraded": True
            }
    
    async def trigger_circuit_recovery_test(self, breaker_id: str) -> Dict[str, Any]:
        """Test circuit breaker recovery mechanism."""
        if breaker_id not in self.circuit_breakers:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        breaker_info = self.circuit_breakers[breaker_id]
        circuit = breaker_info["circuit"]
        
        try:
            # Force circuit to open state by simulating failures
            initial_state = circuit.state
            
            # Trigger enough failures to open circuit
            failure_threshold = breaker_info["config"]["failure_threshold"]
            for i in range(failure_threshold + 1):
                await self.simulate_service_request(breaker_id, should_fail=True)
            
            assert circuit.state == CircuitState.OPEN
            
            # Wait for recovery timeout (simulate)
            recovery_timeout = breaker_info["config"]["recovery_timeout"]
            circuit.last_failure_time = time.time() - recovery_timeout - 1
            
            # Circuit should transition to HALF_OPEN
            circuit.check_recovery()
            assert circuit.state == CircuitState.HALF_OPEN
            
            # Test successful recovery
            success_threshold = breaker_info["config"]["success_threshold"]
            for i in range(success_threshold):
                result = await self.simulate_service_request(breaker_id, should_fail=False)
                assert result["success"] is True
            
            # Circuit should be closed now
            assert circuit.state == CircuitState.CLOSED
            
            return {
                "recovery_successful": True,
                "initial_state": initial_state.value,
                "final_state": circuit.state.value,
                "failures_triggered": failure_threshold + 1,
                "successes_for_recovery": success_threshold
            }
            
        except Exception as e:
            return {
                "recovery_successful": False,
                "error": str(e),
                "circuit_state": circuit.state.value
            }
    
    async def test_cascading_failure_prevention(self, service_names: List[str]) -> Dict[str, Any]:
        """Test that circuit breakers prevent cascading failures."""
        try:
            # Create circuit breakers for multiple services
            breaker_ids = []
            for service_name in service_names:
                breaker_id = await self.create_circuit_breaker(service_name)
                breaker_ids.append(breaker_id)
            
            # Simulate failure in first service
            primary_breaker = breaker_ids[0]
            
            # Trigger circuit trip in primary service
            failure_threshold = self.circuit_breakers[primary_breaker]["config"]["failure_threshold"]
            for i in range(failure_threshold + 1):
                await self.simulate_service_request(primary_breaker, should_fail=True)
            
            primary_circuit = self.circuit_breakers[primary_breaker]["circuit"]
            assert primary_circuit.state == CircuitState.OPEN
            
            # Test that other services remain functional
            isolation_results = []
            for breaker_id in breaker_ids[1:]:
                result = await self.simulate_service_request(breaker_id, should_fail=False)
                isolation_results.append({
                    "breaker_id": breaker_id,
                    "service_functional": result["success"],
                    "circuit_state": result["circuit_state"]
                })
            
            # Verify isolation
            functional_services = [r for r in isolation_results if r["service_functional"]]
            
            return {
                "cascading_prevented": len(functional_services) == len(breaker_ids) - 1,
                "failed_service_isolated": primary_circuit.state == CircuitState.OPEN,
                "functional_services": len(functional_services),
                "total_services": len(breaker_ids),
                "isolation_details": isolation_results
            }
            
        except Exception as e:
            return {
                "cascading_prevented": False,
                "error": str(e)
            }
    
    async def test_load_based_circuit_behavior(self, breaker_id: str, request_count: int) -> Dict[str, Any]:
        """Test circuit breaker behavior under load."""
        if breaker_id not in self.circuit_breakers:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        load_test_start = time.time()
        concurrent_requests = []
        
        try:
            # Generate mix of successful and failing requests
            tasks = []
            for i in range(request_count):
                # 30% failure rate
                should_fail = i % 10 < 3
                task = self.simulate_service_request(breaker_id, should_fail=should_fail)
                tasks.append(task)
            
            # Execute requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            load_test_time = time.time() - load_test_start
            
            # Analyze results
            successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success")]
            fallback_requests = [r for r in results if isinstance(r, dict) and r.get("fallback_executed")]
            
            circuit_state = self.circuit_breakers[breaker_id]["circuit"].state
            
            return {
                "total_requests": len(results),
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "fallback_requests": len(fallback_requests),
                "final_circuit_state": circuit_state.value,
                "load_test_time": load_test_time,
                "requests_per_second": request_count / load_test_time if load_test_time > 0 else 0
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "load_test_time": time.time() - load_test_start
            }
    
    async def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker metrics."""
        active_circuits = len(self.circuit_breakers)
        open_circuits = len([
            cb for cb in self.circuit_breakers.values() 
            if cb["circuit"].state == CircuitState.OPEN
        ])
        half_open_circuits = len([
            cb for cb in self.circuit_breakers.values() 
            if cb["circuit"].state == CircuitState.HALF_OPEN
        ])
        
        # Calculate failure rate
        failure_rate = 0
        if self.metrics["total_requests"] > 0:
            failure_rate = (self.metrics["failed_requests"] / self.metrics["total_requests"]) * 100
        
        # Calculate average response times
        response_times = []
        for event in self.failure_history:
            if "response_time" in event:
                response_times.append(event["response_time"])
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "active_circuit_breakers": active_circuits,
            "open_circuits": open_circuits,
            "half_open_circuits": half_open_circuits,
            "closed_circuits": active_circuits - open_circuits - half_open_circuits,
            "total_requests": self.metrics["total_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "failure_rate": failure_rate,
            "circuit_trips": self.metrics["circuit_trips"],
            "successful_recoveries": self.metrics["successful_recoveries"],
            "fallback_activations": self.metrics["fallback_activations"],
            "average_response_time": avg_response_time,
            "total_failure_events": len(self.failure_history),
            "total_recovery_events": len(self.recovery_events)
        }
    
    async def cleanup(self):
        """Clean up circuit breaker resources."""
        try:
            if self.circuit_service:
                await self.circuit_service.shutdown()
            if self.health_service:
                await self.health_service.stop()
            if self.fallback_service:
                await self.fallback_service.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def circuit_manager():
    """Create circuit breaker manager for testing."""
    manager = CircuitBreakerManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
async def test_circuit_breaker_basic_functionality(circuit_manager):
    """Test basic circuit breaker open/close functionality."""
    # Create circuit breaker
    breaker_id = await circuit_manager.create_circuit_breaker("test_service")
    
    # Test normal operation (circuit closed)
    for i in range(3):
        result = await circuit_manager.simulate_service_request(breaker_id, should_fail=False)
        assert result["success"] is True
        assert result["circuit_open"] is False
    
    # Trigger circuit opening with failures
    failure_threshold = 5
    for i in range(failure_threshold + 1):
        result = await circuit_manager.simulate_service_request(breaker_id, should_fail=True)
        if i >= failure_threshold:
            assert result["circuit_open"] is True
            assert result["fallback_executed"] is True
    
    # Verify circuit is open and fallback is executed
    result = await circuit_manager.simulate_service_request(breaker_id, should_fail=False)
    assert result["circuit_open"] is True
    assert result["fallback_executed"] is True

@pytest.mark.asyncio
async def test_circuit_recovery_mechanism(circuit_manager):
    """Test circuit breaker recovery from open to closed state."""
    breaker_id = await circuit_manager.create_circuit_breaker("recovery_service")
    
    # Test recovery mechanism
    recovery_result = await circuit_manager.trigger_circuit_recovery_test(breaker_id)
    
    assert recovery_result["recovery_successful"] is True
    assert recovery_result["final_state"] == "CLOSED"
    assert recovery_result["failures_triggered"] >= 5
    assert recovery_result["successes_for_recovery"] >= 3

@pytest.mark.asyncio
async def test_fallback_mechanism_activation(circuit_manager):
    """Test fallback mechanism when services are unavailable."""
    # Test different service types
    service_types = ["llm_service", "database_service", "external_api", "unknown_service"]
    
    for service_type in service_types:
        breaker_id = await circuit_manager.create_circuit_breaker(service_type)
        
        # Trigger circuit opening
        for i in range(6):
            await circuit_manager.simulate_service_request(breaker_id, should_fail=True)
        
        # Test fallback execution
        result = await circuit_manager.simulate_service_request(breaker_id, should_fail=False)
        
        assert result["circuit_open"] is True
        assert result["fallback_executed"] is True
        assert result["fallback_response"]["degraded"] is True
        assert "fallback_type" in result["fallback_response"]

@pytest.mark.asyncio
async def test_cascading_failure_prevention(circuit_manager):
    """Test that circuit breakers prevent cascading failures across services."""
    service_names = ["service_a", "service_b", "service_c", "service_d"]
    
    cascade_result = await circuit_manager.test_cascading_failure_prevention(service_names)
    
    assert cascade_result["cascading_prevented"] is True
    assert cascade_result["failed_service_isolated"] is True
    assert cascade_result["functional_services"] == 3  # 4 - 1 failed
    
    # Verify other services remain functional
    for detail in cascade_result["isolation_details"]:
        assert detail["service_functional"] is True
        assert detail["circuit_state"] == "CLOSED"

@pytest.mark.asyncio
async def test_circuit_breaker_under_load(circuit_manager):
    """Test circuit breaker behavior under high load conditions."""
    breaker_id = await circuit_manager.create_circuit_breaker("load_service")
    
    # Test with various load levels
    load_levels = [50, 100, 200]
    
    for request_count in load_levels:
        load_result = await circuit_manager.test_load_based_circuit_behavior(breaker_id, request_count)
        
        assert load_result["total_requests"] == request_count
        assert load_result["load_test_time"] < 10.0  # Should complete within 10 seconds
        assert load_result["requests_per_second"] > 0
        
        # Verify circuit breaker functionality under load
        assert "final_circuit_state" in load_result
        
        # With 30% failure rate, circuit should eventually open
        if request_count >= 100:
            assert load_result["fallback_requests"] > 0

@pytest.mark.asyncio
async def test_circuit_breaker_configuration_variations(circuit_manager):
    """Test circuit breakers with different configuration parameters."""
    configurations = [
        {"failure_threshold": 3, "recovery_timeout": 10, "success_threshold": 2},
        {"failure_threshold": 10, "recovery_timeout": 60, "success_threshold": 5},
        {"failure_threshold": 1, "recovery_timeout": 5, "success_threshold": 1}
    ]
    
    for i, config in enumerate(configurations):
        service_name = f"config_test_service_{i}"
        breaker_id = await circuit_manager.create_circuit_breaker(service_name, config)
        
        # Test that circuit trips at configured threshold
        for failure_count in range(config["failure_threshold"] + 1):
            result = await circuit_manager.simulate_service_request(breaker_id, should_fail=True)
            
            if failure_count >= config["failure_threshold"]:
                assert result["circuit_open"] is True
            else:
                assert result["circuit_open"] is False

@pytest.mark.asyncio
async def test_circuit_breaker_performance_metrics(circuit_manager):
    """Test circuit breaker performance metrics collection."""
    # Create multiple circuit breakers and generate activity
    breaker_ids = []
    for i in range(3):
        breaker_id = await circuit_manager.create_circuit_breaker(f"metrics_service_{i}")
        breaker_ids.append(breaker_id)
    
    # Generate mixed workload
    for breaker_id in breaker_ids:
        # Mix of successful and failing requests
        for i in range(20):
            should_fail = i % 5 == 0  # 20% failure rate
            await circuit_manager.simulate_service_request(breaker_id, should_fail=should_fail)
    
    # Get metrics
    metrics = await circuit_manager.get_circuit_breaker_metrics()
    
    # Verify metrics structure and values
    assert metrics["active_circuit_breakers"] == 3
    assert metrics["total_requests"] >= 60
    assert metrics["failed_requests"] > 0
    assert 0 <= metrics["failure_rate"] <= 100
    assert metrics["circuit_trips"] >= 0
    assert metrics["fallback_activations"] >= 0
    
    # Verify performance requirements
    assert metrics["average_response_time"] < 1.0  # Should be fast

@pytest.mark.asyncio
async def test_concurrent_circuit_breaker_operations(circuit_manager):
    """Test concurrent operations across multiple circuit breakers."""
    # Create multiple circuit breakers
    num_breakers = 5
    breaker_tasks = []
    
    for i in range(num_breakers):
        service_name = f"concurrent_service_{i}"
        task = circuit_manager.create_circuit_breaker(service_name)
        breaker_tasks.append(task)
    
    breaker_ids = await asyncio.gather(*breaker_tasks)
    
    # Execute concurrent requests across all breakers
    request_tasks = []
    for i in range(50):  # 50 total requests
        breaker_id = breaker_ids[i % num_breakers]
        should_fail = i % 7 == 0  # ~14% failure rate
        task = circuit_manager.simulate_service_request(breaker_id, should_fail=should_fail)
        request_tasks.append(task)
    
    results = await asyncio.gather(*request_tasks, return_exceptions=True)
    
    # Verify concurrent execution worked
    successful_results = [r for r in results if isinstance(r, dict) and not isinstance(r, Exception)]
    assert len(successful_results) == 50
    
    # Verify circuit breakers operated independently
    final_metrics = await circuit_manager.get_circuit_breaker_metrics()
    assert final_metrics["active_circuit_breakers"] == num_breakers
    assert final_metrics["total_requests"] >= 50