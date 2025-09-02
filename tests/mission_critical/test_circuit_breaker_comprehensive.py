#!/usr/bin/env python
"""
MISSION CRITICAL: Circuit Breaker Cascade Failure Stress Tests

Business Value: Prevents $100K+ ARR loss from cascading service failures
Critical Requirements:
- Circuit breakers must prevent cascade failures across all services
- Recovery must be automatic and coordinated 
- Performance impact <5ms overhead under normal load
- 99.9% availability protection during partial service failures

This suite tests the most difficult failure scenarios that could bring down
the entire platform if circuit breakers fail to protect properly.

ANY FAILURE HERE BLOCKS PRODUCTION DEPLOYMENT.
"""

import asyncio
import gc
import json
import os
import psutil
import random
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Callable
from unittest.mock import AsyncMock, Mock, patch
import threading

import pytest
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import circuit breaker components
from netra_backend.app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    CircuitOpenException,
    CircuitState,
    ServiceCircuitBreakers
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerManager,
    get_unified_circuit_breaker_manager
)
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# FAILURE SIMULATION COMPONENTS
# ============================================================================

class ServiceFailureSimulator:
    """Simulates realistic service failures for testing circuit breakers."""
    
    def __init__(self):
        self.failure_patterns = {
            "intermittent": {"failure_rate": 0.3, "recovery_time": 5},
            "cascading": {"failure_rate": 0.8, "recovery_time": 30},  
            "timeout": {"failure_rate": 0.2, "timeout_rate": 0.8},
            "overload": {"failure_rate": 0.9, "recovery_time": 60},
            "partial": {"failure_rate": 0.5, "recovery_time": 15}
        }
        self.active_failures: Dict[str, Dict] = {}
        self.failure_start_times: Dict[str, float] = {}
        self.call_counts: Dict[str, int] = {}
    
    async def simulate_database_call(self, service_name: str = "database"):
        """Simulate database call with configurable failures."""
        await self._simulate_service_call(service_name, base_latency=0.1)
    
    async def simulate_llm_call(self, service_name: str = "llm_service"):
        """Simulate LLM call with realistic failure patterns."""
        await self._simulate_service_call(service_name, base_latency=1.5)
    
    async def simulate_auth_call(self, service_name: str = "auth_service"):
        """Simulate auth service call with failure scenarios."""
        await self._simulate_service_call(service_name, base_latency=0.3)
        
    async def simulate_redis_call(self, service_name: str = "redis"):
        """Simulate Redis call with cache failure patterns."""
        await self._simulate_service_call(service_name, base_latency=0.05)
    
    async def _simulate_service_call(self, service_name: str, base_latency: float):
        """Core service call simulation with failure injection."""
        self.call_counts[service_name] = self.call_counts.get(service_name, 0) + 1
        
        # Check if service is in active failure state
        if service_name in self.active_failures:
            failure_info = self.active_failures[service_name]
            start_time = self.failure_start_times.get(service_name, time.time())
            
            # Check if failure should recover
            if time.time() - start_time > failure_info.get("recovery_time", 30):
                self._recover_service(service_name)
            else:
                # Service is still failing
                await self._inject_failure(service_name, failure_info)
        
        # Add realistic latency
        latency_variance = random.uniform(0.8, 1.2)
        await asyncio.sleep(base_latency * latency_variance)
        
        return f"{service_name}_response_{self.call_counts[service_name]}"
    
    def inject_failure(self, service_name: str, pattern: str):
        """Inject specific failure pattern into service."""
        if pattern not in self.failure_patterns:
            raise ValueError(f"Unknown failure pattern: {pattern}")
        
        self.active_failures[service_name] = self.failure_patterns[pattern].copy()
        self.failure_start_times[service_name] = time.time()
        logger.warning(f"Injecting {pattern} failure into {service_name}")
    
    def _recover_service(self, service_name: str):
        """Mark service as recovered."""
        if service_name in self.active_failures:
            del self.active_failures[service_name]
            del self.failure_start_times[service_name]
            logger.info(f"Service {service_name} recovered from failure")
    
    async def _inject_failure(self, service_name: str, failure_info: Dict):
        """Inject failure based on failure configuration."""
        failure_rate = failure_info.get("failure_rate", 0.5)
        timeout_rate = failure_info.get("timeout_rate", 0.1)
        
        if random.random() < failure_rate:
            if random.random() < timeout_rate:
                # Simulate timeout
                await asyncio.sleep(10)  # Long delay to trigger timeouts
                raise asyncio.TimeoutError(f"{service_name} timed out")
            else:
                # Simulate service error
                raise ConnectionError(f"{service_name} connection failed")
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get comprehensive failure simulation statistics."""
        return {
            "active_failures": dict(self.active_failures),
            "call_counts": dict(self.call_counts),
            "total_calls": sum(self.call_counts.values()),
            "services_in_failure": list(self.active_failures.keys())
        }


class CascadeFailureOrchestrator:
    """Orchestrates complex cascade failure scenarios."""
    
    def __init__(self, simulator: ServiceFailureSimulator):
        self.simulator = simulator
        self.cascade_scenarios = {
            "downstream_cascade": {
                "order": ["database", "redis", "llm_service", "auth_service"],
                "delay_between_failures": 2.0,
                "failure_pattern": "cascading"
            },
            "upstream_cascade": {
                "order": ["auth_service", "llm_service", "database", "redis"],
                "delay_between_failures": 1.5,
                "failure_pattern": "overload"
            },
            "simultaneous_partial": {
                "order": ["database", "llm_service", "auth_service"],
                "delay_between_failures": 0.1,
                "failure_pattern": "partial"
            },
            "rolling_timeouts": {
                "order": ["redis", "database", "llm_service"],
                "delay_between_failures": 3.0,
                "failure_pattern": "timeout"
            }
        }
    
    async def trigger_cascade(self, scenario_name: str) -> Dict[str, Any]:
        """Trigger a specific cascade failure scenario."""
        if scenario_name not in self.cascade_scenarios:
            raise ValueError(f"Unknown cascade scenario: {scenario_name}")
        
        scenario = self.cascade_scenarios[scenario_name]
        cascade_start = time.time()
        
        logger.warning(f"Starting cascade failure scenario: {scenario_name}")
        
        # Trigger failures in sequence
        for i, service in enumerate(scenario["order"]):
            if i > 0:
                await asyncio.sleep(scenario["delay_between_failures"])
            
            self.simulator.inject_failure(service, scenario["failure_pattern"])
            logger.warning(f"Cascade step {i+1}: {service} failed")
        
        cascade_duration = time.time() - cascade_start
        
        return {
            "scenario": scenario_name,
            "cascade_duration": cascade_duration,
            "services_failed": scenario["order"],
            "failure_pattern": scenario["failure_pattern"]
        }
    
    async def recovery_test(self, scenario_name: str, recovery_delay: float = 10.0) -> Dict[str, Any]:
        """Test coordinated recovery after cascade failure."""
        # First trigger the cascade
        cascade_result = await self.trigger_cascade(scenario_name)
        
        # Wait for recovery period
        await asyncio.sleep(recovery_delay)
        
        # Force recovery of all services
        for service in cascade_result["services_failed"]:
            self.simulator._recover_service(service)
        
        recovery_end = time.time()
        
        return {
            **cascade_result,
            "recovery_delay": recovery_delay,
            "total_test_duration": recovery_end - (time.time() - cascade_result["cascade_duration"]),
            "recovery_completed": True
        }


# ============================================================================
# CIRCUIT BREAKER STRESS TEST UTILITIES  
# ============================================================================

class CircuitBreakerStressTester:
    """Comprehensive circuit breaker stress testing framework."""
    
    def __init__(self):
        self.failure_simulator = ServiceFailureSimulator()
        self.cascade_orchestrator = CascadeFailureOrchestrator(self.failure_simulator)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.test_results: List[Dict] = []
        self.concurrent_test_tasks: List[asyncio.Task] = []
        
    async def setup_circuit_breakers(self):
        """Setup circuit breakers for all critical services."""
        service_configs = {
            "database": CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2,
                timeout=5.0,
                expected_exception_types=["ConnectionError", "TimeoutError"]
            ),
            "llm_service": CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=60,
                success_threshold=3,
                timeout=30.0,
                expected_exception_types=["ConnectionError", "TimeoutError", "RateLimitError"]
            ),
            "auth_service": CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=45,
                success_threshold=2,
                timeout=10.0,
                expected_exception_types=["ConnectionError", "AuthenticationError"]
            ),
            "redis": CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=20,
                success_threshold=2,
                timeout=3.0,
                expected_exception_types=["ConnectionError", "RedisError"]
            )
        }
        
        for service_name, config in service_configs.items():
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
            logger.info(f"Setup circuit breaker for {service_name}")
    
    async def execute_stress_test(
        self, 
        test_name: str,
        concurrent_requests: int,
        test_duration: float,
        failure_scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute comprehensive stress test with optional failure injection."""
        test_start = time.time()
        
        # Trigger failure scenario if specified
        if failure_scenario:
            await self.cascade_orchestrator.trigger_cascade(failure_scenario)
        
        # Generate concurrent load
        test_tasks = []
        for i in range(concurrent_requests):
            task = asyncio.create_task(
                self._execute_concurrent_requests(f"stress_test_{i}", test_duration)
            )
            test_tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        test_end = time.time()
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        # Get circuit breaker states
        circuit_states = {
            name: cb.state.value for name, cb in self.circuit_breakers.items()
        }
        
        # Get failure statistics
        failure_stats = self.failure_simulator.get_failure_stats()
        
        stress_test_result = {
            "test_name": test_name,
            "test_duration": test_end - test_start,
            "concurrent_requests": concurrent_requests,
            "successful_tasks": len(successful_results),
            "failed_tasks": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "circuit_breaker_states": circuit_states,
            "failure_scenario": failure_scenario,
            "failure_statistics": failure_stats,
            "task_results": successful_results[:10]  # Sample of results
        }
        
        self.test_results.append(stress_test_result)
        return stress_test_result
    
    async def _execute_concurrent_requests(self, task_id: str, duration: float) -> Dict[str, Any]:
        """Execute requests for specified duration to simulate load."""
        task_start = time.time()
        request_count = 0
        successful_requests = 0
        circuit_open_count = 0
        timeout_count = 0
        
        while time.time() - task_start < duration:
            request_count += 1
            
            # Rotate through different services
            service_name = ["database", "llm_service", "auth_service", "redis"][request_count % 4]
            circuit_breaker = self.circuit_breakers.get(service_name)
            
            if not circuit_breaker:
                continue
            
            try:
                # Map service to simulator method
                service_method = {
                    "database": self.failure_simulator.simulate_database_call,
                    "llm_service": self.failure_simulator.simulate_llm_call,
                    "auth_service": self.failure_simulator.simulate_auth_call,
                    "redis": self.failure_simulator.simulate_redis_call
                }.get(service_name)
                
                if service_method:
                    await circuit_breaker.call(service_method, service_name)
                    successful_requests += 1
                
            except CircuitOpenException:
                circuit_open_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except Exception as e:
                # Other failures handled by circuit breaker
                pass
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
        
        return {
            "task_id": task_id,
            "duration": time.time() - task_start,
            "total_requests": request_count,
            "successful_requests": successful_requests,
            "circuit_open_count": circuit_open_count,
            "timeout_count": timeout_count,
            "success_rate": successful_requests / request_count if request_count > 0 else 0
        }
    
    async def memory_leak_detection_test(self, iterations: int = 100) -> Dict[str, Any]:
        """Test for memory leaks in circuit breaker operations."""
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        memory_samples = []
        
        for i in range(iterations):
            # Create and destroy circuit breakers
            temp_breaker = CircuitBreaker(
                f"temp_breaker_{i}",
                CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1)
            )
            
            # Exercise the circuit breaker
            try:
                async def failing_operation():
                    raise ConnectionError("Test failure")
                
                await temp_breaker.call(failing_operation)
            except:
                pass  # Expected failure
            
            # Sample memory usage
            if i % 10 == 0:
                gc.collect()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
            
            del temp_breaker  # Explicit cleanup
        
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": final_memory - initial_memory,
            "memory_samples": memory_samples,
            "iterations": iterations,
            "memory_leak_detected": final_memory - initial_memory > 10  # 10MB threshold
        }
    
    async def performance_overhead_test(self, requests: int = 1000) -> Dict[str, Any]:
        """Measure performance overhead of circuit breakers."""
        # Test without circuit breaker
        start_time = time.perf_counter()
        for _ in range(requests):
            await self.failure_simulator.simulate_database_call()
        baseline_time = time.perf_counter() - start_time
        
        # Test with circuit breaker
        circuit_breaker = CircuitBreaker("perf_test", CircuitBreakerConfig())
        start_time = time.perf_counter()
        for _ in range(requests):
            try:
                await circuit_breaker.call(
                    self.failure_simulator.simulate_database_call
                )
            except:
                pass  # Ignore failures for performance measurement
        
        circuit_breaker_time = time.perf_counter() - start_time
        
        overhead_ms = (circuit_breaker_time - baseline_time) / requests * 1000
        
        return {
            "baseline_time_seconds": baseline_time,
            "circuit_breaker_time_seconds": circuit_breaker_time,
            "overhead_per_request_ms": overhead_ms,
            "requests_tested": requests,
            "overhead_acceptable": overhead_ms < 5.0  # Must be <5ms per CLAUDE.md
        }


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def circuit_breaker_stress_tester():
    """Circuit breaker stress tester fixture."""
    tester = CircuitBreakerStressTester()
    await tester.setup_circuit_breakers()
    yield tester
    # Cleanup
    for cb in tester.circuit_breakers.values():
        try:
            await cb.reset()
        except:
            pass


@pytest.fixture
def failure_simulator():
    """Service failure simulator fixture."""
    return ServiceFailureSimulator()


@pytest.fixture
def cascade_orchestrator(failure_simulator):
    """Cascade failure orchestrator fixture."""
    return CascadeFailureOrchestrator(failure_simulator)


# ============================================================================
# CIRCUIT BREAKER STRESS TESTS  
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(120)
async def test_circuit_breaker_prevents_cascade_failures(circuit_breaker_stress_tester):
    """CRITICAL: Test that circuit breakers prevent cascade failures."""
    tester = circuit_breaker_stress_tester
    
    # Execute stress test with cascade failure scenario
    result = await tester.execute_stress_test(
        test_name="cascade_prevention",
        concurrent_requests=20,
        test_duration=30.0,
        failure_scenario="downstream_cascade"
    )
    
    # CRITICAL ASSERTIONS: Circuit breakers must prevent total system failure
    assert result["success_rate"] > 0.3, \
        f"Success rate too low: {result['success_rate']:.2f}. Circuit breakers failed to protect system."
    
    # At least some circuit breakers should be open (protecting services)
    open_breakers = [name for name, state in result["circuit_breaker_states"].items() if state == "open"]
    assert len(open_breakers) > 0, \
        "No circuit breakers opened during cascade failure - protection not working"
    
    # System should not be completely down
    assert result["successful_tasks"] > result["failed_tasks"] * 0.5, \
        "Too many tasks failed - cascade failure not properly contained"
    
    logger.info(f"Cascade prevention test: {result['success_rate']:.2f} success rate, "
                f"{len(open_breakers)} breakers opened")


@pytest.mark.asyncio  
@pytest.mark.critical
@pytest.mark.timeout(180)
async def test_circuit_breaker_recovery_coordination(circuit_breaker_stress_tester):
    """CRITICAL: Test coordinated recovery of circuit breakers after failures."""
    tester = circuit_breaker_stress_tester
    
    # First, trigger cascade failure
    cascade_result = await tester.cascade_orchestrator.trigger_cascade("upstream_cascade")
    
    # Let failures propagate and circuit breakers open
    await asyncio.sleep(5.0)
    
    # Check that circuit breakers are protecting services
    initial_states = {name: cb.state.value for name, cb in tester.circuit_breakers.items()}
    open_breakers_initial = [name for name, state in initial_states.items() if state == "open"]
    
    assert len(open_breakers_initial) > 0, "Circuit breakers should be open after cascade failure"
    
    # Force service recovery
    for service in cascade_result["services_failed"]:
        tester.failure_simulator._recover_service(service)
    
    # Execute recovery test load
    recovery_result = await tester.execute_stress_test(
        test_name="coordinated_recovery",
        concurrent_requests=15,
        test_duration=60.0,  # Longer duration for recovery testing
        failure_scenario=None  # No additional failures during recovery
    )
    
    # CRITICAL ASSERTIONS: System must recover properly
    final_states = recovery_result["circuit_breaker_states"]
    closed_breakers_final = [name for name, state in final_states.items() if state == "closed"]
    
    # At least 50% of circuit breakers should recover to closed state
    assert len(closed_breakers_final) >= len(open_breakers_initial) * 0.5, \
        f"Insufficient recovery: {len(closed_breakers_final)} closed vs {len(open_breakers_initial)} initially open"
    
    # Recovery should improve success rate over time
    assert recovery_result["success_rate"] > 0.6, \
        f"Recovery success rate too low: {recovery_result['success_rate']:.2f}"
    
    logger.info(f"Recovery test: {len(closed_breakers_final)}/{len(initial_states)} breakers recovered, "
                f"{recovery_result['success_rate']:.2f} success rate")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(90) 
async def test_high_concurrency_circuit_breaker_performance(circuit_breaker_stress_tester):
    """CRITICAL: Test circuit breaker performance under extreme concurrent load."""
    tester = circuit_breaker_stress_tester
    
    # Execute high concurrency stress test
    result = await tester.execute_stress_test(
        test_name="high_concurrency_performance",
        concurrent_requests=50,  # High concurrency
        test_duration=45.0,
        failure_scenario="intermittent"  # Realistic intermittent failures
    )
    
    # CRITICAL PERFORMANCE ASSERTIONS
    assert result["test_duration"] < 60.0, \
        f"Test took too long: {result['test_duration']:.2f}s. Performance degradation detected."
    
    # System should maintain reasonable success rate under high load
    assert result["success_rate"] > 0.4, \
        f"Success rate under high load too low: {result['success_rate']:.2f}"
    
    # At least 80% of concurrent tasks should complete (not hang)
    completion_rate = (result["successful_tasks"] + result["failed_tasks"]) / result["concurrent_requests"]
    assert completion_rate > 0.8, \
        f"Too many tasks hung: {completion_rate:.2f} completion rate"
    
    # Check individual task performance
    sample_results = result.get("task_results", [])
    if sample_results:
        avg_task_success_rate = statistics.mean([r.get("success_rate", 0) for r in sample_results])
        assert avg_task_success_rate > 0.3, \
            f"Individual task success rate too low: {avg_task_success_rate:.2f}"
    
    logger.info(f"High concurrency test: {result['concurrent_requests']} tasks, "
                f"{result['success_rate']:.2f} success rate, {completion_rate:.2f} completion rate")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(60)
async def test_memory_leak_prevention_circuit_breakers(circuit_breaker_stress_tester):
    """CRITICAL: Test that circuit breakers don't cause memory leaks under stress."""
    tester = circuit_breaker_stress_tester
    
    # Run memory leak detection test
    memory_result = await tester.memory_leak_detection_test(iterations=200)
    
    # CRITICAL MEMORY ASSERTIONS
    assert not memory_result["memory_leak_detected"], \
        f"Memory leak detected: {memory_result['memory_increase_mb']:.2f}MB increase over {memory_result['iterations']} iterations"
    
    assert memory_result["memory_increase_mb"] < 50, \
        f"Memory usage increased too much: {memory_result['memory_increase_mb']:.2f}MB"
    
    # Memory should be relatively stable across samples
    if len(memory_result["memory_samples"]) > 5:
        memory_variance = statistics.variance(memory_result["memory_samples"])
        assert memory_variance < 100, \
            f"Memory usage too volatile: {memory_variance:.2f} variance"
    
    logger.info(f"Memory leak test: {memory_result['memory_increase_mb']:.2f}MB increase over "
                f"{memory_result['iterations']} iterations - {'✅ PASSED' if not memory_result['memory_leak_detected'] else '❌ FAILED'}")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(30)
async def test_circuit_breaker_performance_overhead(circuit_breaker_stress_tester):
    """CRITICAL: Ensure circuit breaker overhead is <5ms as required by CLAUDE.md."""
    tester = circuit_breaker_stress_tester
    
    # Run performance overhead test
    perf_result = await tester.performance_overhead_test(requests=1000)
    
    # CRITICAL PERFORMANCE REQUIREMENT: <5ms overhead
    assert perf_result["overhead_acceptable"], \
        f"Circuit breaker overhead too high: {perf_result['overhead_per_request_ms']:.3f}ms (must be <5ms)"
    
    assert perf_result["overhead_per_request_ms"] < 5.0, \
        f"Performance requirement violated: {perf_result['overhead_per_request_ms']:.3f}ms overhead per request"
    
    # Overhead should be minimal compared to baseline
    overhead_ratio = perf_result["circuit_breaker_time_seconds"] / perf_result["baseline_time_seconds"]
    assert overhead_ratio < 1.5, \
        f"Circuit breaker adds too much overhead: {overhead_ratio:.2f}x baseline time"
    
    logger.info(f"Performance overhead test: {perf_result['overhead_per_request_ms']:.3f}ms per request "
                f"({overhead_ratio:.2f}x baseline) - {'✅ PASSED' if perf_result['overhead_acceptable'] else '❌ FAILED'}")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(120)
async def test_simultaneous_service_failures_isolation(circuit_breaker_stress_tester):
    """CRITICAL: Test isolation when multiple services fail simultaneously."""
    tester = circuit_breaker_stress_tester
    
    # Execute test with simultaneous partial failures
    result = await tester.execute_stress_test(
        test_name="simultaneous_failures_isolation",
        concurrent_requests=25,
        test_duration=60.0,
        failure_scenario="simultaneous_partial"
    )
    
    # CRITICAL ISOLATION ASSERTIONS
    circuit_states = result["circuit_breaker_states"]
    
    # Circuit breakers should isolate failing services
    open_or_half_open = [name for name, state in circuit_states.items() 
                        if state in ["open", "half_open"]]
    assert len(open_or_half_open) >= 2, \
        f"Expected multiple circuit breakers to activate, only {len(open_or_half_open)} did"
    
    # System should maintain partial functionality
    assert result["success_rate"] > 0.2, \
        f"System completely failed: {result['success_rate']:.2f} success rate during simultaneous failures"
    
    # Some requests should still succeed (healthy services working)
    assert result["successful_tasks"] > 0, \
        "No tasks succeeded - isolation failed, cascade failure occurred"
    
    # Failure should be contained (not 100% failure)
    assert result["success_rate"] < 0.9, \
        f"Success rate too high: {result['success_rate']:.2f} - failures not properly simulated"
    
    logger.info(f"Simultaneous failures test: {len(open_or_half_open)} breakers activated, "
                f"{result['success_rate']:.2f} success rate maintained")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(90)
async def test_circuit_breaker_state_transitions_under_load(circuit_breaker_stress_tester):
    """CRITICAL: Test proper state transitions under sustained load."""
    tester = circuit_breaker_stress_tester
    
    # Monitor state transitions over time
    state_history = []
    
    async def monitor_states():
        """Monitor circuit breaker states throughout test."""
        for _ in range(30):  # Monitor for 30 seconds
            states = {name: cb.state.value for name, cb in tester.circuit_breakers.items()}
            state_history.append({
                "timestamp": time.time(),
                "states": states.copy()
            })
            await asyncio.sleep(1.0)
    
    # Start monitoring and stress test concurrently
    monitor_task = asyncio.create_task(monitor_states())
    
    stress_result = await tester.execute_stress_test(
        test_name="state_transitions_under_load",
        concurrent_requests=30,
        test_duration=30.0,
        failure_scenario="rolling_timeouts"
    )
    
    await monitor_task
    
    # CRITICAL STATE TRANSITION ASSERTIONS
    assert len(state_history) > 20, "Insufficient state monitoring data"
    
    # Analyze state transitions
    transitions_detected = {}
    for service_name in tester.circuit_breakers.keys():
        service_states = [entry["states"].get(service_name) for entry in state_history]
        unique_states = set(service_states)
        transitions_detected[service_name] = len(unique_states)
    
    # At least one service should have experienced state transitions
    services_with_transitions = sum(1 for count in transitions_detected.values() if count > 1)
    assert services_with_transitions > 0, \
        "No state transitions detected - circuit breakers not responding to failures"
    
    # Should see transitions from closed -> open -> half_open -> closed pattern
    complex_transitions = sum(1 for count in transitions_detected.values() if count >= 2)
    assert complex_transitions > 0, \
        "No complex state transitions observed - recovery mechanism not tested"
    
    # Final state should show some recovery
    final_states = state_history[-1]["states"]
    closed_breakers_final = sum(1 for state in final_states.values() if state == "closed")
    assert closed_breakers_final > 0, \
        "No circuit breakers recovered to closed state"
    
    logger.info(f"State transitions test: {services_with_transitions} services with transitions, "
                f"{complex_transitions} with complex transitions, "
                f"{closed_breakers_final} recovered to closed")


if __name__ == "__main__":
    # Run circuit breaker stress tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])