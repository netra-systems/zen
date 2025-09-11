"""
Integration Tests: Circuit Breaker Failure Recovery

Business Value Justification (BVJ):
- Segment: Enterprise (high-availability requirements)
- Business Goal: System Resilience + Uptime Maximization + Service Continuity
- Value Impact: Prevents cascade failures from bringing down entire system,
  ensures graceful degradation during service outages, maintains partial
  functionality when dependencies fail, enables rapid recovery when services
  return to health
- Revenue Impact: Protects $500K+ ARR from system-wide outages, reduces
  downtime costs ($10K+ per hour), enables Enterprise SLA commitments
  (99.9% uptime), prevents customer churn from service interruptions

Test Focus: Circuit breaker pattern implementation, failure detection,
automatic recovery, graceful degradation, and service health monitoring.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, patch
import random
from enum import Enum
from dataclasses import dataclass, field
import statistics

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.supervisor.execution_engine import UserExecutionContext
from netra_backend.app.core.config import get_config


class CircuitBreakerState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failures detected, circuit open
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 30.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 5.0               # Operation timeout


@dataclass
class CircuitBreakerMetrics:
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    operation_history: List[Dict[str, Any]] = field(default_factory=list)


class SimulatedCircuitBreaker:
    """Simulated circuit breaker for testing failure recovery patterns."""
    
    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
    
    async def call(self, operation: Callable, *args, **kwargs):
        """Execute operation through circuit breaker."""
        async with self._lock:
            current_time = time.time()
            
            # Check if we should transition from OPEN to HALF_OPEN
            if (self.metrics.state == CircuitBreakerState.OPEN and
                self.metrics.last_failure_time and
                current_time - self.metrics.last_failure_time >= self.config.recovery_timeout):
                
                await self._transition_to_half_open()
            
            # Handle different circuit states
            if self.metrics.state == CircuitBreakerState.OPEN:
                raise Exception(f"Circuit breaker OPEN for {self.service_name}")
            
            elif self.metrics.state == CircuitBreakerState.HALF_OPEN:
                # Allow limited operations to test recovery
                return await self._execute_with_half_open_logic(operation, *args, **kwargs)
            
            else:  # CLOSED state
                return await self._execute_with_closed_logic(operation, *args, **kwargs)
    
    async def _execute_with_closed_logic(self, operation: Callable, *args, **kwargs):
        """Execute operation in CLOSED state."""
        try:
            start_time = time.time()
            result = await asyncio.wait_for(operation(*args, **kwargs), timeout=self.config.timeout)
            execution_time = time.time() - start_time
            
            # Record successful operation
            self.metrics.operation_history.append({
                "timestamp": start_time,
                "success": True,
                "execution_time": execution_time,
                "state": self.metrics.state.value
            })
            
            # Reset failure count on success
            self.metrics.failure_count = 0
            return result
            
        except Exception as e:
            # Record failure
            failure_time = time.time()
            self.metrics.failure_count += 1
            self.metrics.last_failure_time = failure_time
            
            self.metrics.operation_history.append({
                "timestamp": failure_time,
                "success": False,
                "error": str(e),
                "state": self.metrics.state.value
            })
            
            # Check if we should open the circuit
            if self.metrics.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()
            
            raise e
    
    async def _execute_with_half_open_logic(self, operation: Callable, *args, **kwargs):
        """Execute operation in HALF_OPEN state."""
        try:
            start_time = time.time()
            result = await asyncio.wait_for(operation(*args, **kwargs), timeout=self.config.timeout)
            execution_time = time.time() - start_time
            
            self.metrics.success_count += 1
            self.metrics.operation_history.append({
                "timestamp": start_time,
                "success": True,
                "execution_time": execution_time,
                "state": self.metrics.state.value
            })
            
            # Check if we should close the circuit
            if self.metrics.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
            
            return result
            
        except Exception as e:
            # Failure in half-open immediately goes back to open
            failure_time = time.time()
            self.metrics.last_failure_time = failure_time
            
            self.metrics.operation_history.append({
                "timestamp": failure_time,
                "success": False,
                "error": str(e),
                "state": self.metrics.state.value
            })
            
            await self._transition_to_open()
            raise e
    
    async def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        old_state = self.metrics.state
        self.metrics.state = CircuitBreakerState.OPEN
        self._record_state_transition(old_state, CircuitBreakerState.OPEN)
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.metrics.state
        self.metrics.state = CircuitBreakerState.HALF_OPEN
        self.metrics.success_count = 0  # Reset success counter
        self._record_state_transition(old_state, CircuitBreakerState.HALF_OPEN)
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        old_state = self.metrics.state
        self.metrics.state = CircuitBreakerState.CLOSED
        self.metrics.failure_count = 0
        self.metrics.success_count = 0
        self._record_state_transition(old_state, CircuitBreakerState.CLOSED)
    
    def _record_state_transition(self, from_state: CircuitBreakerState, to_state: CircuitBreakerState):
        """Record circuit breaker state transition."""
        self.metrics.state_transitions.append({
            "from_state": from_state.value,
            "to_state": to_state.value,
            "timestamp": time.time(),
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count
        })


class TestCircuitBreakerFailureRecovery(BaseIntegrationTest):
    """
    Test circuit breaker pattern for failure detection and automatic recovery.
    
    Business Value: Prevents cascade failures and ensures system resilience
    under service degradation, critical for Enterprise availability requirements.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_circuit_breaker_test(self, real_services_fixture):
        """Setup circuit breaker failure recovery test environment."""
        self.config = get_config()
        
        # Circuit breaker test state
        self.circuit_breakers: Dict[str, SimulatedCircuitBreaker] = {}
        self.service_health_states: Dict[str, bool] = {}
        self.recovery_scenarios: List[Dict[str, Any]] = []
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Initialize test services with circuit breakers
        services = ["database_service", "llm_service", "cache_service", "auth_service"]
        for service in services:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10.0,
                success_threshold=2,
                timeout=2.0
            )
            self.circuit_breakers[service] = SimulatedCircuitBreaker(service, config)
            self.service_health_states[service] = True  # Start healthy
        
        yield
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    async def _simulate_service_call(self, service_name: str, operation_id: str) -> Dict[str, Any]:
        """Simulate a service call with configurable success/failure."""
        # Check if service is healthy
        is_healthy = self.service_health_states.get(service_name, True)
        
        # Add some randomness even to healthy services
        if is_healthy:
            success_rate = 0.9  # 90% success rate for healthy services
        else:
            success_rate = 0.1  # 10% success rate for unhealthy services
        
        # Simulate processing time
        await asyncio.sleep(random.uniform(0.05, 0.2))
        
        if random.random() < success_rate:
            return {
                "service": service_name,
                "operation_id": operation_id,
                "result": f"Success from {service_name}",
                "timestamp": time.time()
            }
        else:
            raise Exception(f"Service {service_name} operation {operation_id} failed")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_detection_and_opening(self):
        """
        Test circuit breaker detects failures and opens circuit appropriately.
        
        BVJ: Ensures rapid failure detection prevents system resource waste
        on failing services, protecting overall system performance.
        """
        service_name = "database_service"
        num_operations = 20
        
        # Make service unhealthy to trigger failures
        self.service_health_states[service_name] = False
        circuit_breaker = self.circuit_breakers[service_name]
        
        operation_results = []
        circuit_open_detected = False
        
        for op_num in range(num_operations):
            try:
                result = await circuit_breaker.call(
                    self._simulate_service_call, 
                    service_name, 
                    f"test_op_{op_num}"
                )
                operation_results.append({
                    "operation_num": op_num,
                    "success": True,
                    "result": result,
                    "circuit_state": circuit_breaker.metrics.state.value
                })
                
            except Exception as e:
                operation_results.append({
                    "operation_num": op_num,
                    "success": False,
                    "error": str(e),
                    "circuit_state": circuit_breaker.metrics.state.value
                })
                
                # Check if circuit opened
                if "Circuit breaker OPEN" in str(e):
                    circuit_open_detected = True
                    break
            
            # Small delay between operations
            await asyncio.sleep(0.1)
        
        # Verify circuit breaker opened due to failures
        assert circuit_open_detected, "Circuit breaker should have opened due to failures"
        assert circuit_breaker.metrics.state == CircuitBreakerState.OPEN, \
            f"Circuit should be OPEN, but is {circuit_breaker.metrics.state}"
        
        # Verify failure threshold was reached
        assert circuit_breaker.metrics.failure_count >= circuit_breaker.config.failure_threshold, \
            f"Failure count should be >= {circuit_breaker.config.failure_threshold}, but is {circuit_breaker.metrics.failure_count}"
        
        # Verify state transitions occurred
        transitions = circuit_breaker.metrics.state_transitions
        assert len(transitions) > 0, "No state transitions recorded"
        
        # Should have transition from CLOSED to OPEN
        open_transition = next((t for t in transitions if t["to_state"] == "open"), None)
        assert open_transition is not None, "No transition to OPEN state found"
        assert open_transition["from_state"] == "closed", \
            f"Transition to OPEN should be from CLOSED, but was from {open_transition['from_state']}"
        
        # Verify operations stopped failing fast after circuit opened
        circuit_open_operations = [r for r in operation_results if "Circuit breaker OPEN" in r.get("error", "")]
        assert len(circuit_open_operations) > 0, "No fast-failing operations detected after circuit opened"
        
        self.logger.info(f"Circuit breaker failure detection test completed: "
                        f"{len(operation_results)} operations, circuit opened after "
                        f"{circuit_breaker.metrics.failure_count} failures")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_automatic_recovery_cycle(self):
        """
        Test complete circuit breaker recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
        
        BVJ: Validates automatic recovery enables service restoration without
        manual intervention, crucial for self-healing system architecture.
        """
        service_name = "llm_service"
        circuit_breaker = self.circuit_breakers[service_name]
        
        # Reduce recovery timeout for faster testing
        circuit_breaker.config.recovery_timeout = 2.0
        
        recovery_cycle_results = {
            "phases": [],
            "state_transitions": [],
            "operation_counts": {}
        }
        
        # Phase 1: Force circuit to open
        self.service_health_states[service_name] = False
        
        phase1_operations = 0
        while circuit_breaker.metrics.state != CircuitBreakerState.OPEN:
            try:
                await circuit_breaker.call(self._simulate_service_call, service_name, f"phase1_op_{phase1_operations}")
            except Exception:
                pass
            phase1_operations += 1
            
            if phase1_operations > 10:  # Prevent infinite loop
                break
        
        recovery_cycle_results["phases"].append({
            "phase": "force_open",
            "operations": phase1_operations,
            "final_state": circuit_breaker.metrics.state.value,
            "timestamp": time.time()
        })
        
        # Phase 2: Wait for automatic transition to HALF_OPEN
        assert circuit_breaker.metrics.state == CircuitBreakerState.OPEN, "Circuit should be OPEN"
        
        # Restore service health for recovery
        self.service_health_states[service_name] = True
        
        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.config.recovery_timeout + 0.5)
        
        # Attempt operation to trigger HALF_OPEN transition
        half_open_triggered = False
        try:
            await circuit_breaker.call(self._simulate_service_call, service_name, "recovery_test")
            half_open_triggered = True
        except Exception as e:
            if circuit_breaker.metrics.state == CircuitBreakerState.HALF_OPEN:
                half_open_triggered = True
        
        recovery_cycle_results["phases"].append({
            "phase": "transition_to_half_open",
            "half_open_triggered": half_open_triggered,
            "state": circuit_breaker.metrics.state.value,
            "timestamp": time.time()
        })
        
        # Phase 3: Test HALF_OPEN operations for recovery
        half_open_operations = 0
        half_open_successes = 0
        
        while (circuit_breaker.metrics.state == CircuitBreakerState.HALF_OPEN and 
               half_open_operations < 10):  # Prevent infinite loop
            
            try:
                await circuit_breaker.call(self._simulate_service_call, service_name, f"half_open_op_{half_open_operations}")
                half_open_successes += 1
            except Exception:
                pass
            
            half_open_operations += 1
            await asyncio.sleep(0.1)
        
        recovery_cycle_results["phases"].append({
            "phase": "half_open_testing",
            "operations": half_open_operations,
            "successes": half_open_successes,
            "final_state": circuit_breaker.metrics.state.value,
            "timestamp": time.time()
        })
        
        # Phase 4: Verify circuit closed after successful operations
        final_state = circuit_breaker.metrics.state
        recovery_cycle_results["phases"].append({
            "phase": "recovery_completion",
            "final_state": final_state.value,
            "total_transitions": len(circuit_breaker.metrics.state_transitions),
            "timestamp": time.time()
        })
        
        # Verify complete recovery cycle
        transitions = circuit_breaker.metrics.state_transitions
        recovery_cycle_results["state_transitions"] = [
            {"from": t["from_state"], "to": t["to_state"], "timestamp": t["timestamp"]}
            for t in transitions
        ]
        
        # Should have transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        transition_sequence = [t["to"] for t in recovery_cycle_results["state_transitions"]]
        
        assert "open" in transition_sequence, "Circuit should have transitioned to OPEN"
        assert "half_open" in transition_sequence, "Circuit should have transitioned to HALF_OPEN"
        
        # Final state should be CLOSED if recovery was successful
        if half_open_successes >= circuit_breaker.config.success_threshold:
            assert final_state == CircuitBreakerState.CLOSED, \
                f"Circuit should have recovered to CLOSED, but is {final_state}"
        
        # Verify metrics consistency
        assert len(transitions) >= 2, f"Should have at least 2 transitions, but have {len(transitions)}"
        
        self.logger.info(f"Circuit breaker recovery cycle test completed: "
                        f"{len(transitions)} state transitions, final state: {final_state.value}")
    
    @pytest.mark.asyncio
    async def test_multiple_circuit_breaker_coordination(self):
        """
        Test coordination between multiple circuit breakers for different services.
        
        BVJ: Ensures individual service failures don't cascade to healthy services,
        maintaining partial functionality during outages.
        """
        num_operations_per_service = 15
        service_coordination_results = {}
        
        # Set different health states for services
        service_health_config = {
            "database_service": False,  # Unhealthy - should open circuit
            "llm_service": True,        # Healthy - should stay closed
            "cache_service": False,     # Unhealthy - should open circuit  
            "auth_service": True        # Healthy - should stay closed
        }
        
        for service, is_healthy in service_health_config.items():
            self.service_health_states[service] = is_healthy
        
        # Execute operations across all services concurrently
        async def test_service_operations(service_name: str, operation_count: int):
            """Test operations on a specific service."""
            circuit_breaker = self.circuit_breakers[service_name]
            service_results = {
                "service_name": service_name,
                "operations": [],
                "circuit_states": [],
                "final_state": None
            }
            
            for op_num in range(operation_count):
                try:
                    result = await circuit_breaker.call(
                        self._simulate_service_call,
                        service_name,
                        f"coord_op_{op_num}"
                    )
                    
                    service_results["operations"].append({
                        "operation_num": op_num,
                        "success": True,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    service_results["operations"].append({
                        "operation_num": op_num,
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                
                # Record circuit state
                service_results["circuit_states"].append({
                    "operation_num": op_num,
                    "state": circuit_breaker.metrics.state.value,
                    "failure_count": circuit_breaker.metrics.failure_count
                })
                
                await asyncio.sleep(0.05)  # Small delay between operations
            
            service_results["final_state"] = circuit_breaker.metrics.state.value
            return service_results
        
        # Run all service tests concurrently
        service_tasks = []
        for service_name in service_health_config.keys():
            task = asyncio.create_task(test_service_operations(service_name, num_operations_per_service))
            service_tasks.append(task)
        
        # Wait for all service tests to complete
        results = await asyncio.gather(*service_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, dict):
                service_name = result["service_name"]
                service_coordination_results[service_name] = result
        
        # Verify service coordination results
        assert len(service_coordination_results) == len(service_health_config), \
            f"Not all services completed testing: {len(service_coordination_results)}/{len(service_health_config)}"
        
        # Verify healthy services remained functional
        healthy_services = [name for name, healthy in service_health_config.items() if healthy]
        unhealthy_services = [name for name, healthy in service_health_config.items() if not healthy]
        
        for service_name in healthy_services:
            result = service_coordination_results[service_name]
            
            # Healthy services should have more successful operations
            successful_ops = [op for op in result["operations"] if op["success"]]
            success_rate = len(successful_ops) / len(result["operations"])
            
            assert success_rate >= 0.7, \
                f"Healthy service {service_name} success rate too low: {success_rate:.2%}"
            
            # Circuit should remain mostly CLOSED for healthy services
            closed_states = [state for state in result["circuit_states"] if state["state"] == "closed"]
            assert len(closed_states) >= len(result["circuit_states"]) * 0.5, \
                f"Healthy service {service_name} circuit not staying closed enough"
        
        # Verify unhealthy services opened circuits
        for service_name in unhealthy_services:
            result = service_coordination_results[service_name]
            
            # Circuit should eventually open for unhealthy services
            final_state = result["final_state"]
            open_states = [state for state in result["circuit_states"] if state["state"] == "open"]
            
            assert final_state == "open" or len(open_states) > 0, \
                f"Unhealthy service {service_name} circuit should have opened"
        
        # Verify independence - healthy services not affected by unhealthy ones
        for healthy_service in healthy_services:
            healthy_result = service_coordination_results[healthy_service]
            
            # Check that this service's operations continued even while others failed
            healthy_operations = healthy_result["operations"]
            continuous_failures = 0
            max_continuous_failures = 0
            
            for op in healthy_operations:
                if not op["success"]:
                    continuous_failures += 1
                    max_continuous_failures = max(max_continuous_failures, continuous_failures)
                else:
                    continuous_failures = 0
            
            # Healthy service should not have long sequences of failures
            assert max_continuous_failures < 5, \
                f"Healthy service {healthy_service} had too many continuous failures: {max_continuous_failures}"
        
        # Verify circuit breaker metrics
        total_state_transitions = sum(
            len(self.circuit_breakers[service].metrics.state_transitions)
            for service in service_health_config.keys()
        )
        
        assert total_state_transitions > 0, "No circuit breaker state transitions detected"
        
        self.logger.info(f"Multiple circuit breaker coordination test completed: "
                        f"{len(healthy_services)} healthy services, {len(unhealthy_services)} unhealthy services, "
                        f"{total_state_transitions} total state transitions")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance_under_load(self):
        """
        Test circuit breaker performance and overhead under high load.
        
        BVJ: Ensures circuit breaker pattern doesn't introduce significant
        performance overhead during normal operations, maintaining system throughput.
        """
        service_name = "cache_service"
        num_concurrent_operations = 100
        operations_per_worker = 20
        
        # Keep service healthy for performance testing
        self.service_health_states[service_name] = True
        circuit_breaker = self.circuit_breakers[service_name]
        
        performance_metrics = {
            "operation_times": [],
            "circuit_overhead_times": [],
            "throughput_results": [],
            "resource_usage": []
        }
        
        async def high_load_worker(worker_id: int, operation_count: int):
            """Worker that performs high-load operations through circuit breaker."""
            worker_results = {
                "worker_id": worker_id,
                "operations_completed": 0,
                "total_execution_time": 0,
                "average_operation_time": 0,
                "circuit_breaker_overhead": 0
            }
            
            start_time = time.time()
            
            for op_num in range(operation_count):
                operation_start = time.time()
                
                try:
                    # Measure circuit breaker overhead
                    circuit_start = time.time()
                    
                    result = await circuit_breaker.call(
                        self._simulate_service_call,
                        service_name,
                        f"load_worker_{worker_id}_op_{op_num}"
                    )
                    
                    circuit_end = time.time()
                    operation_end = time.time()
                    
                    # Calculate timing metrics
                    total_operation_time = operation_end - operation_start
                    circuit_overhead = circuit_end - circuit_start
                    
                    performance_metrics["operation_times"].append(total_operation_time)
                    performance_metrics["circuit_overhead_times"].append(circuit_overhead)
                    
                    worker_results["operations_completed"] += 1
                    worker_results["total_execution_time"] += total_operation_time
                    
                except Exception as e:
                    # Even failures should be fast
                    operation_end = time.time()
                    total_operation_time = operation_end - operation_start
                    performance_metrics["operation_times"].append(total_operation_time)
            
            total_worker_time = time.time() - start_time
            
            if worker_results["operations_completed"] > 0:
                worker_results["average_operation_time"] = (
                    worker_results["total_execution_time"] / worker_results["operations_completed"]
                )
            
            return worker_results
        
        # Execute high load test
        worker_tasks = []
        for worker_id in range(num_concurrent_operations):
            task = asyncio.create_task(high_load_worker(worker_id, operations_per_worker))
            worker_tasks.append(task)
        
        # Measure total test execution time
        load_test_start = time.time()
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
        load_test_end = time.time()
        
        total_test_time = load_test_end - load_test_start
        
        # Process performance results
        successful_workers = [r for r in worker_results if isinstance(r, dict)]
        assert len(successful_workers) == num_concurrent_operations, \
            f"Not all workers completed: {len(successful_workers)}/{num_concurrent_operations}"
        
        # Calculate performance metrics
        total_operations = sum(w["operations_completed"] for w in successful_workers)
        expected_total_operations = num_concurrent_operations * operations_per_worker
        
        completion_rate = total_operations / expected_total_operations
        assert completion_rate >= 0.9, \
            f"Operation completion rate too low under load: {completion_rate:.2%}"
        
        # Verify operation timing performance
        if performance_metrics["operation_times"]:
            avg_operation_time = statistics.mean(performance_metrics["operation_times"])
            p95_operation_time = sorted(performance_metrics["operation_times"])[int(0.95 * len(performance_metrics["operation_times"]))]
            
            # Operations should be reasonably fast even with circuit breaker
            assert avg_operation_time < 1.0, \
                f"Average operation time too high: {avg_operation_time:.3f}s"
            assert p95_operation_time < 2.0, \
                f"95th percentile operation time too high: {p95_operation_time:.3f}s"
        
        # Verify circuit breaker overhead is minimal
        if performance_metrics["circuit_overhead_times"]:
            avg_circuit_overhead = statistics.mean(performance_metrics["circuit_overhead_times"])
            max_circuit_overhead = max(performance_metrics["circuit_overhead_times"])
            
            # Circuit breaker overhead should be minimal
            assert avg_circuit_overhead < 0.1, \
                f"Circuit breaker overhead too high: {avg_circuit_overhead:.3f}s"
            assert max_circuit_overhead < 0.5, \
                f"Maximum circuit breaker overhead too high: {max_circuit_overhead:.3f}s"
        
        # Calculate throughput
        throughput = total_operations / total_test_time
        
        # Should achieve reasonable throughput with circuit breaker
        expected_min_throughput = 10  # operations per second
        assert throughput >= expected_min_throughput, \
            f"Throughput too low: {throughput:.1f} ops/sec (expected >= {expected_min_throughput})"
        
        # Verify circuit remained healthy under load
        assert circuit_breaker.metrics.state == CircuitBreakerState.CLOSED, \
            f"Circuit should remain CLOSED under normal load, but is {circuit_breaker.metrics.state}"
        
        self.logger.info(f"Circuit breaker performance test completed: "
                        f"{total_operations} operations, {throughput:.1f} ops/sec, "
                        f"{avg_operation_time:.3f}s avg operation time")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_graceful_degradation_patterns(self):
        """
        Test graceful degradation patterns when circuit breakers are open.
        
        BVJ: Ensures system provides fallback functionality when services fail,
        maintaining user experience and business continuity during outages.
        """
        degradation_scenarios = [
            {
                "name": "database_fallback_to_cache",
                "primary_service": "database_service",
                "fallback_service": "cache_service",
                "operations": 10
            },
            {
                "name": "llm_fallback_to_simple_response",
                "primary_service": "llm_service", 
                "fallback_service": None,  # Simple fallback
                "operations": 8
            }
        ]
        
        degradation_results = {}
        
        for scenario in degradation_scenarios:
            scenario_name = scenario["name"]
            primary_service = scenario["primary_service"]
            fallback_service = scenario["fallback_service"]
            num_operations = scenario["operations"]
            
            # Make primary service unhealthy
            self.service_health_states[primary_service] = False
            
            # Keep fallback service healthy if it exists
            if fallback_service:
                self.service_health_states[fallback_service] = True
            
            primary_circuit = self.circuit_breakers[primary_service]
            fallback_circuit = self.circuit_breakers[fallback_service] if fallback_service else None
            
            scenario_results = {
                "scenario_name": scenario_name,
                "operations": [],
                "fallback_usage": 0,
                "degradation_quality": 0
            }
            
            for op_num in range(num_operations):
                operation_result = {
                    "operation_num": op_num,
                    "primary_attempted": False,
                    "primary_success": False,
                    "fallback_attempted": False,
                    "fallback_success": False,
                    "final_result": None,
                    "degraded": False
                }
                
                # Try primary service first
                try:
                    primary_result = await primary_circuit.call(
                        self._simulate_service_call,
                        primary_service,
                        f"degradation_{scenario_name}_{op_num}"
                    )
                    
                    operation_result["primary_attempted"] = True
                    operation_result["primary_success"] = True
                    operation_result["final_result"] = primary_result
                    
                except Exception as primary_error:
                    operation_result["primary_attempted"] = True
                    operation_result["primary_success"] = False
                    
                    # Attempt graceful degradation
                    if "Circuit breaker OPEN" in str(primary_error):
                        # Circuit is open, use fallback immediately
                        fallback_result = await self._attempt_graceful_fallback(
                            scenario_name, fallback_service, fallback_circuit, op_num
                        )
                        
                        operation_result.update(fallback_result)
                        
                        if fallback_result["fallback_success"]:
                            scenario_results["fallback_usage"] += 1
                            operation_result["degraded"] = True
                            scenario_results["degradation_quality"] += 1
                
                scenario_results["operations"].append(operation_result)
                await asyncio.sleep(0.1)
            
            degradation_results[scenario_name] = scenario_results
        
        # Verify graceful degradation results
        for scenario_name, results in degradation_results.items():
            operations = results["operations"]
            
            # At least some operations should have attempted primary service
            primary_attempts = [op for op in operations if op["primary_attempted"]]
            assert len(primary_attempts) > 0, \
                f"No primary service attempts in scenario {scenario_name}"
            
            # Circuit should eventually open, triggering fallbacks
            circuit_open_operations = [op for op in operations 
                                     if op["primary_attempted"] and not op["primary_success"]]
            
            if len(circuit_open_operations) > 0:
                # Should have some fallback usage when primary fails
                fallback_operations = [op for op in operations if op["fallback_attempted"]]
                
                scenario = next(s for s in degradation_scenarios if s["name"] == scenario_name)
                if scenario["fallback_service"]:  # Only check if fallback service exists
                    assert len(fallback_operations) > 0, \
                        f"No fallback attempts when primary failed in scenario {scenario_name}"
                    
                    # Fallback success rate should be reasonable
                    successful_fallbacks = [op for op in fallback_operations if op["fallback_success"]]
                    if len(fallback_operations) > 0:
                        fallback_success_rate = len(successful_fallbacks) / len(fallback_operations)
                        assert fallback_success_rate >= 0.7, \
                            f"Fallback success rate too low in {scenario_name}: {fallback_success_rate:.2%}"
            
            # Overall operation success rate should be better with fallbacks than without
            successful_operations = [op for op in operations 
                                   if op["primary_success"] or op["fallback_success"]]
            overall_success_rate = len(successful_operations) / len(operations)
            
            # With graceful degradation, should achieve reasonable success rate
            assert overall_success_rate >= 0.5, \
                f"Overall success rate too low with degradation in {scenario_name}: {overall_success_rate:.2%}"
        
        self.logger.info(f"Graceful degradation test completed: {len(degradation_scenarios)} scenarios, "
                        f"fallback usage: {sum(r['fallback_usage'] for r in degradation_results.values())}")
    
    async def _attempt_graceful_fallback(self, scenario_name: str, fallback_service: Optional[str], 
                                       fallback_circuit: Optional[SimulatedCircuitBreaker], 
                                       op_num: int) -> Dict[str, Any]:
        """Attempt graceful fallback when primary service fails."""
        fallback_result = {
            "fallback_attempted": False,
            "fallback_success": False,
            "final_result": None
        }
        
        if fallback_service and fallback_circuit:
            # Use fallback service
            try:
                fallback_result["fallback_attempted"] = True
                
                result = await fallback_circuit.call(
                    self._simulate_service_call,
                    fallback_service,
                    f"fallback_{scenario_name}_{op_num}"
                )
                
                fallback_result["fallback_success"] = True
                fallback_result["final_result"] = {
                    "fallback_service": fallback_service,
                    "result": result,
                    "degraded": True
                }
                
            except Exception:
                fallback_result["fallback_success"] = False
                fallback_result["final_result"] = {
                    "error": "Fallback also failed",
                    "degraded": True
                }
        else:
            # Simple fallback (no service call)
            fallback_result["fallback_attempted"] = True
            fallback_result["fallback_success"] = True
            fallback_result["final_result"] = {
                "simple_fallback": True,
                "message": f"Degraded response for {scenario_name}",
                "degraded": True
            }
        
        return fallback_result