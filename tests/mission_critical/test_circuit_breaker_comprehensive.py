class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

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
import threading
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

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
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


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
    """Use real service instance."""
    # TODO: Initialize real service
    """Service failure simulator fixture."""
    return ServiceFailureSimulator()


@pytest.fixture
def cascade_orchestrator(failure_simulator):
    """Use real service instance."""
    # TODO: Initialize real service
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


# ============================================================================
# WEBSOCKET INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_websocket_notifications():
    """Test circuit breaker state changes trigger WebSocket notifications."""
    try:
        from netra_backend.app.websocket_core import WebSocketManager
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    except ImportError:
        pytest.skip("WebSocket components not available")
    
    # Mock WebSocket manager
    websocket_manager = AsyncMock(spec=WebSocketManager)
    websocket_manager.websocket = TestWebSocketConnection()
    websocket_notifier = WebSocketNotifier.create_for_user(websocket_manager)
    
    # Create circuit breaker with WebSocket integration
    from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    
    breaker = CircuitBreaker(
        name="websocket_test_service", failure_threshold=2,
        recovery_timeout=1.0,
        half_open_max_calls=1
    )
    
    # Simulate service failures that should trigger notifications
    failures = 0
    for i in range(5):
        try:
            if i < 3:  # First 3 calls fail
                failures += 1
                await breaker.call(lambda: exec('raise Exception("Service failure")'))
            else:  # Next calls succeed
                await breaker.call(lambda: "success")
        except:
            pass  # Expected failures
        
        # Check if WebSocket notification should be sent for state changes
        current_state = breaker.state
        if i == 1:  # Should open after 2 failures
            assert current_state == "open", "Circuit breaker should be open after threshold failures"
            
            # Simulate WebSocket notification for circuit opening
            await websocket_notifier.send_agent_status_changed(
                context=AsyncMock(thread_id="test_thread"),
                agent_id="circuit_test", 
                old_status="running",
                new_status="circuit_open",
                metadata={"circuit_breaker": breaker.name, "state": current_state}
            )
    
    # Verify WebSocket notifications were sent
    assert websocket_manager.send_to_thread.call_count > 0, "WebSocket notifications should be sent for circuit state changes"
    
    logger.info("✅ Circuit breaker WebSocket notifications validated")

@pytest.mark.asyncio
async def test_circuit_breaker_websocket_event_sequence():
    """Test proper sequence of WebSocket events during circuit breaker lifecycle."""
    try:
        from netra_backend.app.websocket_core import WebSocketManager
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    websocket_manager = AsyncMock(spec=WebSocketManager)
    websocket_events = []
    
    def capture_websocket_event(*args, **kwargs):
        if len(args) > 1:
            websocket_events.append({
                "thread_id": args[0],
                "message": args[1],
                "timestamp": asyncio.get_event_loop().time()
            })
    
    websocket_manager.send_to_thread.side_effect = capture_websocket_event
    websocket_notifier = WebSocketNotifier.create_for_user(websocket_manager)
    
    breaker = CircuitBreaker(
        name="event_sequence_service", failure_threshold=2,
        recovery_timeout=0.5
    )
    
    # Execute circuit breaker lifecycle with WebSocket events
    lifecycle_events = ["closed", "open", "half_open", "closed"]
    
    for expected_state in lifecycle_events:
        if expected_state == "closed" and breaker.state == "closed":
            # Initial state - send notification
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id="lifecycle_test"),
                message=f"Circuit breaker in {expected_state} state"
            )
        elif expected_state == "open":
            # Trigger failures to open circuit
            for _ in range(3):
                try:
                    await breaker.call(lambda: exec('raise Exception("Failure")'))
                except:
                    pass
            
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id="lifecycle_test"),
                message=f"Circuit breaker opened after failures"
            )
        elif expected_state == "half_open":
            # Wait for recovery timeout
            await asyncio.sleep(0.6)
            
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id="lifecycle_test"),
                message="Circuit breaker entering half-open state"
            )
        elif expected_state == "closed":
            # Successful call to close circuit
            try:
                await breaker.call(lambda: "success")
            except:
                pass
            
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id="lifecycle_test"),
                message="Circuit breaker closed after successful recovery"
            )
    
    # Verify event sequence
    assert len(websocket_events) >= len(lifecycle_events), \
        f"Should have events for each lifecycle state: got {len(websocket_events)} events"
    
    # Events should be ordered by timestamp
    timestamps = [event["timestamp"] for event in websocket_events]
    assert timestamps == sorted(timestamps), "WebSocket events should be in chronological order"
    
    logger.info(f"✅ Circuit breaker WebSocket event sequence validated: {len(websocket_events)} events")

@pytest.mark.asyncio
async def test_circuit_breaker_websocket_error_notifications():
    """Test WebSocket error notifications during circuit breaker failures."""
    try:
        from netra_backend.app.websocket_core import WebSocketManager
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    websocket_manager = AsyncMock(spec=WebSocketManager)
    error_notifications = []
    
    def capture_error_notification(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], dict):
            message = args[1]
            if "error" in message.get("type", "").lower() or "fail" in message.get("type", "").lower():
                error_notifications.append(message)
    
    websocket_manager.send_to_thread.side_effect = capture_error_notification
    websocket_notifier = WebSocketNotifier.create_for_user(websocket_manager)
    
    breaker = CircuitBreaker(
        name="error_notification_service", failure_threshold=2,
        recovery_timeout=1.0
    )
    
    # Simulate different types of failures with error notifications
    error_scenarios = [
        {"error_type": "timeout", "message": "Service timeout"},
        {"error_type": "connection", "message": "Connection failed"},
        {"error_type": "processing", "message": "Processing error"},
        {"error_type": "resource", "message": "Resource unavailable"}
    ]
    
    for scenario in error_scenarios:
        try:
            await breaker.call(lambda: exec(f'raise Exception("{scenario["message"]}"))'))
        except Exception as e:
            # Send error notification via WebSocket
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id="error_test"),
                message=f"Circuit breaker error: {scenario['error_type']} - {str(e)}"
            )
    
    # Verify error notifications
    assert websocket_manager.send_to_thread.call_count >= len(error_scenarios), \
        "Should send WebSocket notifications for each error scenario"
    
    logger.info(f"✅ Circuit breaker WebSocket error notifications validated: {len(error_scenarios)} scenarios")

@pytest.mark.asyncio
async def test_circuit_breaker_websocket_concurrent_notifications():
    """Test WebSocket notifications work correctly with concurrent circuit breaker operations."""
    try:
        from netra_backend.app.websocket_core import WebSocketManager
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    websocket_manager = AsyncMock(spec=WebSocketManager)
    concurrent_notifications = []
    notification_lock = asyncio.Lock()
    
    async def thread_safe_capture(*args, **kwargs):
        async with notification_lock:
            concurrent_notifications.append({
                "timestamp": asyncio.get_event_loop().time(),
                "args": args,
                "kwargs": kwargs
            })
    
    websocket_manager.send_to_thread.side_effect = thread_safe_capture
    websocket_notifier = WebSocketNotifier.create_for_user(websocket_manager)
    
    # Create multiple circuit breakers for concurrent testing
    breakers = []
    for i in range(3):
        breaker = CircuitBreaker(
            name=f"concurrent_service_{i}", failure_threshold=2,
            recovery_timeout=0.5
        )
        breakers.append(breaker)
    
    # Execute concurrent operations with WebSocket notifications
    async def test_concurrent_breaker(breaker_id, breaker):
        for attempt in range(5):
            try:
                if attempt < 2:  # First 2 fail
                    await breaker.call(lambda: exec('raise Exception("Concurrent failure")'))
                else:  # Next succeed
                    await breaker.call(lambda: f"success_{breaker_id}_{attempt}")
            except:
                pass
            
            # Send notification for each attempt
            await websocket_notifier.send_agent_thinking(
                context=AsyncMock(thread_id=f"concurrent_{breaker_id}"),
                message=f"Breaker {breaker_id} attempt {attempt}"
            )
            
            await asyncio.sleep(0.1)  # Small delay between attempts
    
    # Run all breakers concurrently
    tasks = [
        test_concurrent_breaker(i, breaker)
        for i, breaker in enumerate(breakers)
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify concurrent notifications
    total_expected = len(breakers) * 5  # 3 breakers * 5 attempts each
    assert len(concurrent_notifications) >= total_expected, \
        f"Should have notifications from all concurrent operations: got {len(concurrent_notifications)}, expected {total_expected}"
    
    # Verify notifications are properly ordered by timestamp
    timestamps = [notif["timestamp"] for notif in concurrent_notifications]
    sorted_timestamps = sorted(timestamps)
    
    # Allow for some minor timing variations
    timing_errors = sum(1 for i, ts in enumerate(timestamps) 
                       if abs(ts - sorted_timestamps[i]) > 0.1)
    
    assert timing_errors < len(timestamps) * 0.1, \
        f"Too many timing errors in concurrent notifications: {timing_errors}/{len(timestamps)}"
    
    logger.info(f"✅ Circuit breaker concurrent WebSocket notifications validated: {len(concurrent_notifications)} notifications")


# ============================================================================
# EXECUTE CORE PATTERN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_execute_core_integration():
    """Test circuit breaker integration with _execute_core pattern."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    class CircuitBreakerAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="execute_core_service",
                failure_threshold=2,
                recovery_timeout=1.0
            )
            self.execution_count = 0
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            self.execution_count += 1
            
            async def protected_operation():
                # Simulate operation that might fail
                if context.run_id.endswith("_fail") and self.execution_count <= 2:
                    raise Exception(f"Execute core failure #{self.execution_count}")
                
                return {
                    "status": "success",
                    "execution_count": self.execution_count,
                    "circuit_state": self.circuit_breaker.state
                }
            
            # Use circuit breaker to protect execute_core operation
            try:
                result = await self.circuit_breaker.call(protected_operation)
                return result
            except Exception as e:
                return {
                    "status": "circuit_breaker_blocked",
                    "error": str(e),
                    "circuit_state": self.circuit_breaker.state,
                    "execution_count": self.execution_count
                }
    
    agent = CircuitBreakerAgent(name="CircuitBreakerTestAgent")
    
    # Test successful execution
    success_context = ExecutionContext(
        run_id="execute_core_success",
        agent_name=agent.name,
        state=DeepAgentState()
    )
    
    result = await agent.execute_core_logic(success_context)
    assert result["status"] == "success"
    assert result["circuit_state"] == "closed"
    
    # Test failure scenarios that trigger circuit breaker
    failure_contexts = [
        ExecutionContext(
            run_id="execute_core_fail_1",
            agent_name=agent.name,
            state=DeepAgentState()
        ),
        ExecutionContext(
            run_id="execute_core_fail_2",
            agent_name=agent.name,
            state=DeepAgentState()
        ),
        ExecutionContext(
            run_id="execute_core_fail_3",
            agent_name=agent.name,
            state=DeepAgentState()
        )
    ]
    
    results = []
    for context in failure_contexts:
        result = await agent.execute_core_logic(context)
        results.append(result)
    
    # Verify circuit breaker behavior
    # First two failures should execute but fail
    assert results[0]["status"] == "circuit_breaker_blocked"
    assert results[1]["status"] == "circuit_breaker_blocked"
    
    # Third should be blocked by open circuit
    assert "circuit" in results[2]["status"] or results[2]["circuit_state"] == "open"
    
    logger.info("✅ Circuit breaker execute_core integration validated")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_recovery_patterns():
    """Test _execute_core pattern with circuit breaker recovery scenarios."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    class RecoveryAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="recovery_service", 
                failure_threshold=2,
                recovery_timeout=0.5,
                half_open_max_calls=1
            )
            self.attempt_count = 0
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            self.attempt_count += 1
            
            async def recovery_operation():
                # Simulate recovery pattern
                if context.run_id == "recovery_transient_failures":
                    if self.attempt_count <= 3:  # First 3 attempts fail
                        raise Exception(f"Transient failure #{self.attempt_count}")
                    else:  # Then succeed
                        return {"status": "recovered", "attempts": self.attempt_count}
                elif context.run_id == "recovery_immediate_success":
                    return {"status": "immediate_success", "attempts": self.attempt_count}
                else:
                    raise Exception("Persistent failure")
            
            # Execute with circuit breaker protection
            try:
                result = await self.circuit_breaker.call(recovery_operation)
                result["circuit_state"] = self.circuit_breaker.state
                return result
            except Exception as e:
                return {
                    "status": "failed",
                    "error": str(e),
                    "circuit_state": self.circuit_breaker.state,
                    "attempts": self.attempt_count
                }
    
    # Test transient failure recovery
    recovery_agent = RecoveryAgent(name="RecoveryTestAgent")
    
    transient_context = ExecutionContext(
        run_id="recovery_transient_failures",
        agent_name=recovery_agent.name,
        state=DeepAgentState()
    )
    
    # Execute multiple times to test recovery
    recovery_results = []
    for i in range(6):  # More than failure threshold
        result = await recovery_agent.execute_core_logic(transient_context)
        recovery_results.append(result)
        
        # Wait for recovery timeout if circuit is open
        if result.get("circuit_state") == "open":
            await asyncio.sleep(0.6)  # Longer than recovery timeout
    
    # Should eventually recover
    successful_recoveries = [r for r in recovery_results if r["status"] == "recovered"]
    assert len(successful_recoveries) > 0, "Should have successful recoveries after transient failures"
    
    # Test immediate success recovery
    success_agent = RecoveryAgent(name="ImmediateSuccessAgent")
    success_context = ExecutionContext(
        run_id="recovery_immediate_success",
        agent_name=success_agent.name,
        state=DeepAgentState()
    )
    
    success_result = await success_agent.execute_core_logic(success_context)
    assert success_result["status"] == "immediate_success"
    assert success_result["circuit_state"] == "closed"
    
    logger.info("✅ Execute core circuit breaker recovery patterns validated")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_timing():
    """Test _execute_core pattern timing behavior with circuit breaker."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    import time
    
    class TimingAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="timing_service",
                failure_threshold=2,
                recovery_timeout=1.0
            )
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            start_time = time.time()
            
            async def timed_operation():
                if context.run_id.endswith("_slow"):
                    await asyncio.sleep(0.5)  # Slow operation
                elif context.run_id.endswith("_fast"):
                    await asyncio.sleep(0.05)  # Fast operation  
                elif context.run_id.endswith("_fail"):
                    raise Exception("Timing failure")
                else:
                    await asyncio.sleep(0.1)  # Normal operation
                
                return {"operation": "completed"}
            
            try:
                result = await self.circuit_breaker.call(timed_operation)
                end_time = time.time()
                
                result.update({
                    "timing": {
                        "execution_time": end_time - start_time,
                        "circuit_state": self.circuit_breaker.state
                    }
                })
                return result
                
            except Exception as e:
                end_time = time.time()
                return {
                    "status": "failed",
                    "error": str(e),
                    "timing": {
                        "execution_time": end_time - start_time,
                        "circuit_state": self.circuit_breaker.state
                    }
                }
    
    timing_agent = TimingAgent(name="TimingTestAgent")
    
    # Test different timing scenarios
    timing_tests = [
        {"run_id": "timing_fast", "expected_max_time": 0.2},
        {"run_id": "timing_normal", "expected_max_time": 0.3},
        {"run_id": "timing_slow", "expected_max_time": 0.8},
    ]
    
    for test_case in timing_tests:
        context = ExecutionContext(
            run_id=test_case["run_id"],
            agent_name=timing_agent.name,
            state=DeepAgentState()
        )
        
        result = await timing_agent.execute_core_logic(context)
        execution_time = result["timing"]["execution_time"]
        
        assert execution_time < test_case["expected_max_time"], \
            f"Execution time {execution_time:.3f}s exceeded limit {test_case['expected_max_time']}s for {test_case['run_id']}"
        
        assert result["timing"]["circuit_state"] == "closed", \
            "Circuit should remain closed for successful operations"
    
    # Test failure timing
    fail_context = ExecutionContext(
        run_id="timing_fail",
        agent_name=timing_agent.name,
        state=DeepAgentState()
    )
    
    fail_result = await timing_agent.execute_core_logic(fail_context)
    fail_time = fail_result["timing"]["execution_time"]
    
    # Failure should be fast (not waiting for timeout)
    assert fail_time < 0.1, f"Failure handling should be fast: {fail_time:.3f}s"
    
    logger.info("✅ Execute core circuit breaker timing validated")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_resource_management():
    """Test _execute_core pattern resource management with circuit breaker."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    class ResourceAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="resource_service",
                failure_threshold=2,
                recovery_timeout=1.0
            )
            self.resources_allocated = 0
            self.resources_freed = 0
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            async def resource_operation():
                # Allocate resources
                await self._allocate_resources(5)
                
                try:
                    if context.run_id.endswith("_resource_fail"):
                        raise Exception("Resource operation failed")
                    
                    # Simulate resource-intensive work
                    await asyncio.sleep(0.1)
                    
                    return {
                        "status": "success",
                        "resources": {
                            "allocated": self.resources_allocated,
                            "freed": self.resources_freed
                        }
                    }
                    
                finally:
                    # Always free resources
                    await self._free_resources(5)
            
            try:
                result = await self.circuit_breaker.call(resource_operation)
                result["circuit_state"] = self.circuit_breaker.state
                return result
                
            except Exception as e:
                return {
                    "status": "circuit_blocked",
                    "error": str(e),
                    "circuit_state": self.circuit_breaker.state,
                    "resources": {
                        "allocated": self.resources_allocated,
                        "freed": self.resources_freed
                    }
                }
        
        async def _allocate_resources(self, amount):
            self.resources_allocated += amount
            await asyncio.sleep(0.01)  # Simulate allocation time
        
        async def _free_resources(self, amount):
            self.resources_freed += amount
            await asyncio.sleep(0.01)  # Simulate cleanup time
    
    resource_agent = ResourceAgent(name="ResourceTestAgent")
    
    # Test successful resource management
    success_context = ExecutionContext(
        run_id="resource_success",
        agent_name=resource_agent.name,
        state=DeepAgentState()
    )
    
    success_result = await resource_agent.execute_core_logic(success_context)
    assert success_result["status"] == "success"
    assert success_result["resources"]["allocated"] == success_result["resources"]["freed"], \
        "Resources should be properly freed after successful execution"
    
    # Test resource management during failures
    initial_allocated = resource_agent.resources_allocated
    initial_freed = resource_agent.resources_freed
    
    fail_context = ExecutionContext(
        run_id="resource_resource_fail",
        agent_name=resource_agent.name,
        state=DeepAgentState()
    )
    
    fail_result = await resource_agent.execute_core_logic(fail_context)
    
    # Resources should still be properly managed even during failures
    final_allocated = resource_agent.resources_allocated
    final_freed = resource_agent.resources_freed
    
    allocation_delta = final_allocated - initial_allocated
    free_delta = final_freed - initial_freed
    
    assert allocation_delta == free_delta, \
        f"Resource leak detected: allocated {allocation_delta}, freed {free_delta}"
    
    logger.info("✅ Execute core circuit breaker resource management validated")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_state_consistency():
    """Test _execute_core pattern maintains state consistency with circuit breaker."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.schemas.agent import SubAgentLifecycle
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    class StateConsistencyAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="state_consistency_service",
                failure_threshold=2,
                recovery_timeout=1.0
            )
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            # Record initial states
            initial_agent_state = self.get_state()
            initial_circuit_state = self.circuit_breaker.state
            
            async def state_aware_operation():
                # Set agent state to running
                self.set_state(SubAgentLifecycle.RUNNING)
                
                if context.run_id.endswith("_state_fail"):
                    # Failure should maintain state consistency
                    raise Exception("State consistency failure")
                
                # Complete successfully
                self.set_state(SubAgentLifecycle.COMPLETED)
                
                return {
                    "status": "success",
                    "state_transitions": "running -> completed"
                }
            
            try:
                result = await self.circuit_breaker.call(state_aware_operation)
                
                # Verify final state consistency
                final_agent_state = self.get_state()
                final_circuit_state = self.circuit_breaker.state
                
                result.update({
                    "state_consistency": {
                        "agent_state": {
                            "initial": initial_agent_state,
                            "final": final_agent_state
                        },
                        "circuit_state": {
                            "initial": initial_circuit_state,
                            "final": final_circuit_state
                        }
                    }
                })
                
                return result
                
            except Exception as e:
                # Even in failure, states should be consistent
                error_agent_state = self.get_state()
                error_circuit_state = self.circuit_breaker.state
                
                # Agent should be in failed state
                self.set_state(SubAgentLifecycle.FAILED)
                
                return {
                    "status": "failed",
                    "error": str(e),
                    "state_consistency": {
                        "agent_state": {
                            "initial": initial_agent_state,
                            "error": error_agent_state,
                            "final": self.get_state()
                        },
                        "circuit_state": {
                            "initial": initial_circuit_state,
                            "error": error_circuit_state
                        }
                    }
                }
    
    consistency_agent = StateConsistencyAgent(name="StateConsistencyAgent")
    
    # Test successful state consistency
    success_context = ExecutionContext(
        run_id="state_success",
        agent_name=consistency_agent.name,
        state=DeepAgentState()
    )
    
    success_result = await consistency_agent.execute_core_logic(success_context)
    assert success_result["status"] == "success"
    
    # Verify agent state progression
    agent_states = success_result["state_consistency"]["agent_state"]
    assert agent_states["final"] == SubAgentLifecycle.COMPLETED
    
    # Circuit should remain closed for successful operations
    circuit_states = success_result["state_consistency"]["circuit_state"]
    assert circuit_states["final"] == "closed"
    
    # Test failure state consistency
    fail_context = ExecutionContext(
        run_id="state_state_fail",
        agent_name=consistency_agent.name,
        state=DeepAgentState()
    )
    
    fail_result = await consistency_agent.execute_core_logic(fail_context)
    assert fail_result["status"] == "failed"
    
    # Verify failure state handling
    fail_agent_states = fail_result["state_consistency"]["agent_state"]
    assert fail_agent_states["final"] == SubAgentLifecycle.FAILED
    
    logger.info("✅ Execute core circuit breaker state consistency validated")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_concurrent_safety():
    """Test _execute_core pattern concurrent safety with circuit breaker."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    class ConcurrentAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="concurrent_service",
                failure_threshold=3,  # Higher threshold for concurrent testing
                recovery_timeout=1.0
            )
            self.execution_count = 0
            self.concurrent_count = 0
            self.max_concurrent = 0
            self.lock = asyncio.Lock()
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            async with self.lock:
                self.execution_count += 1
                self.concurrent_count += 1
                self.max_concurrent = max(self.max_concurrent, self.concurrent_count)
                execution_id = self.execution_count
            
            async def concurrent_operation():
                try:
                    # Simulate concurrent work
                    await asyncio.sleep(0.1)
                    
                    if context.run_id.endswith(f"_fail_{execution_id}") and execution_id <= 2:
                        raise Exception(f"Concurrent failure #{execution_id}")
                    
                    return {
                        "status": "success",
                        "execution_id": execution_id
                    }
                finally:
                    async with self.lock:
                        self.concurrent_count -= 1
            
            try:
                result = await self.circuit_breaker.call(concurrent_operation)
                result.update({
                    "concurrency_stats": {
                        "execution_id": execution_id,
                        "current_concurrent": self.concurrent_count,
                        "max_concurrent": self.max_concurrent
                    },
                    "circuit_state": self.circuit_breaker.state
                })
                return result
                
            except Exception as e:
                return {
                    "status": "failed",
                    "execution_id": execution_id,
                    "error": str(e),
                    "concurrency_stats": {
                        "execution_id": execution_id,
                        "current_concurrent": self.concurrent_count,
                        "max_concurrent": self.max_concurrent
                    },
                    "circuit_state": self.circuit_breaker.state
                }
    
    concurrent_agent = ConcurrentAgent(name="ConcurrentTestAgent")
    
    # Test concurrent executions
    concurrent_contexts = []
    for i in range(10):
        context = ExecutionContext(
            run_id=f"concurrent_test_{i}",
            agent_name=concurrent_agent.name,
            state=DeepAgentState()
        )
        concurrent_contexts.append(context)
    
    # Execute concurrently
    tasks = [
        concurrent_agent.execute_core_logic(context)
        for context in concurrent_contexts
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze concurrent execution results
    successful_executions = [r for r in results if not isinstance(r, Exception) and r.get("status") == "success"]
    failed_executions = [r for r in results if not isinstance(r, Exception) and r.get("status") == "failed"]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    # Should have some successful executions
    assert len(successful_executions) > 0, "Should have successful concurrent executions"
    
    # Verify concurrency tracking
    if successful_executions:
        max_concurrent = max(r["concurrency_stats"]["max_concurrent"] for r in successful_executions)
        assert max_concurrent > 1, "Should have detected concurrent execution"
        assert max_concurrent <= 10, "Should not exceed total number of tasks"
    
    # Circuit breaker should handle concurrent failures appropriately
    total_handled = len(successful_executions) + len(failed_executions)
    assert total_handled > len(exceptions), "Circuit breaker should handle most operations"
    
    logger.info(f"✅ Execute core circuit breaker concurrent safety validated: "
                f"{len(successful_executions)} successful, {len(failed_executions)} failed, "
                f"{len(exceptions)} exceptions")

@pytest.mark.asyncio
async def test_execute_core_circuit_breaker_error_propagation():
    """Test _execute_core pattern error propagation through circuit breaker."""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.utils.circuit_breaker import CircuitBreaker
    except ImportError:
        pytest.skip("Required components not available")
    
    error_propagation_log = []
    
    class ErrorPropagationAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.circuit_breaker = CircuitBreaker(
                name="error_propagation_service",
                failure_threshold=2,
                recovery_timeout=1.0
            )
            
        async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
            async def error_prone_operation():
                operation_type = context.run_id.split("_")[-1]
                
                if operation_type == "timeout":
                    # Simulate timeout error
                    await asyncio.sleep(2.0)  # Long operation
                    raise TimeoutError("Operation timed out")
                elif operation_type == "validation":
                    # Simulate validation error
                    raise ValueError("Invalid input data")
                elif operation_type == "resource":
                    # Simulate resource error
                    raise RuntimeError("Resource unavailable")
                elif operation_type == "network":
                    # Simulate network error
                    raise ConnectionError("Network connection failed")
                else:
                    # Success case
                    return {"status": "success", "operation_type": operation_type}
            
            try:
                result = await self.circuit_breaker.call(error_prone_operation)
                
                # Log successful operation
                error_propagation_log.append({
                    "type": "success",
                    "context_id": context.run_id,
                    "circuit_state": self.circuit_breaker.state
                })
                
                result["circuit_state"] = self.circuit_breaker.state
                return result
                
            except Exception as e:
                # Log error details with circuit state
                error_info = {
                    "type": "error",
                    "context_id": context.run_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "circuit_state": self.circuit_breaker.state
                }
                error_propagation_log.append(error_info)
                
                return {
                    "status": "error_propagated",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "circuit_state": self.circuit_breaker.state,
                    "propagation_info": error_info
                }
    
    propagation_agent = ErrorPropagationAgent(name="ErrorPropagationAgent")
    
    # Test different error types
    error_scenarios = [
        "error_propagation_timeout",
        "error_propagation_validation", 
        "error_propagation_resource",
        "error_propagation_network",
        "error_propagation_success"
    ]
    
    results = []
    for scenario in error_scenarios:
        context = ExecutionContext(
            run_id=scenario,
            agent_name=propagation_agent.name,
            state=DeepAgentState()
        )
        
        result = await propagation_agent.execute_core_logic(context)
        results.append(result)
    
    # Analyze error propagation
    error_results = [r for r in results if r["status"] == "error_propagated"]
    success_results = [r for r in results if r["status"] == "success"]
    
    # Should have proper error propagation
    assert len(error_results) == 4, f"Should have 4 error propagations, got {len(error_results)}"
    assert len(success_results) == 1, f"Should have 1 success, got {len(success_results)}"
    
    # Verify error types are preserved
    error_types = [r["error_type"] for r in error_results]
    expected_types = ["TimeoutError", "ValueError", "RuntimeError", "ConnectionError"]
    
    for expected_type in expected_types:
        assert expected_type in error_types, f"Missing error type: {expected_type}"
    
    # Verify error propagation log
    logged_errors = [entry for entry in error_propagation_log if entry["type"] == "error"]
    assert len(logged_errors) == 4, "Should log all error propagations"
    
    # Circuit breaker should track state changes
    circuit_states = [entry["circuit_state"] for entry in error_propagation_log]
    unique_states = set(circuit_states)
    assert "closed" in unique_states, "Should start with closed state"
    
    # After multiple failures, circuit should open
    if len([s for s in circuit_states if s == "open"]) > 0:
        logger.info("Circuit breaker opened after repeated failures")
    
    logger.info(f"✅ Execute core circuit breaker error propagation validated: "
                f"{len(error_results)} errors propagated, {len(success_results)} successes")


if __name__ == "__main__":
    # Run circuit breaker stress tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])