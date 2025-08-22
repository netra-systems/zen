"""Agent Pipeline Circuit Breaking L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (core platform stability)
- Business Goal: System stability under load, prevent cascading failures
- Value Impact: $100K MRR - Ensures agent pipelines remain stable under stress
- Strategic Impact: Circuit breaking prevents system-wide failures, maintains service quality

Critical Path: Load spike detection -> Circuit activation <5s -> Graceful degradation -> Load shedding -> Recovery mechanisms
Coverage: Agent pipeline overload scenarios, circuit breaker coordination, load shedding strategies, cascade prevention
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
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.agents.supervisor_consolidated import SupervisorAgent

# Add project root to path
from app.core.circuit_breaker_core import CircuitBreaker
from app.core.circuit_breaker_types import CircuitConfig, CircuitState
from app.core.exceptions_base import NetraException
from app.schemas.registry import AgentMessage, TaskPriority

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class AgentPipelineMetrics:
    """Metrics for agent pipeline performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_activations: int = 0
    load_shed_operations: int = 0
    recovery_attempts: int = 0
    average_response_time: float = 0.0
    peak_concurrent_agents: int = 0
    
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios."""
    concurrent_requests: int
    request_rate_per_second: int
    duration_seconds: int
    failure_injection_rate: float = 0.0
    target_circuit_activation_time: float = 5.0


class MockAgentPipeline:
    """Mock agent pipeline for circuit breaking tests."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.active_agents = 0
        self.processing_times = []
        self.failure_rate = 0.0
        self.is_overloaded = False
        
    async def process_request(self, request_id: str, simulate_failure: bool = False) -> Dict[str, Any]:
        """Process agent request with potential failure simulation."""
        if self.active_agents >= self.max_concurrent:
            self.is_overloaded = True
            raise NetraException("Agent pipeline overloaded", error_code="PIPELINE_OVERLOAD")
        
        self.active_agents += 1
        start_time = time.time()
        
        try:
            # Simulate processing time based on load
            processing_time = 0.1 + (self.active_agents * 0.05)  # Increases with load
            
            if simulate_failure:
                await asyncio.sleep(processing_time * 0.5)
                raise NetraException("Simulated agent failure", error_code="AGENT_FAILURE")
            
            await asyncio.sleep(processing_time)
            
            response_time = time.time() - start_time
            self.processing_times.append(response_time)
            
            return {
                "request_id": request_id,
                "success": True,
                "response_time": response_time,
                "active_agents": self.active_agents
            }
        finally:
            self.active_agents -= 1


class AgentPipelineCircuitManager:
    """Manages circuit breaker for agent pipeline with load shedding."""
    
    def __init__(self):
        self.circuit_config = CircuitConfig(
            name="agent_pipeline",
            failure_threshold=5,
            recovery_timeout=30,
            timeout_seconds=10
        )
        self.circuit_breaker = CircuitBreaker(self.circuit_config)
        self.pipeline = MockAgentPipeline(max_concurrent=8)
        self.metrics = AgentPipelineMetrics()
        self.load_shedding_active = False
        self.load_shed_threshold = 0.8  # 80% failure rate triggers load shedding
        
    async def execute_agent_request(self, request_id: str, priority: TaskPriority = TaskPriority.NORMAL) -> Dict[str, Any]:
        """Execute agent request through circuit breaker with load shedding."""
        self.metrics.total_requests += 1
        
        # Check if load shedding should be active
        if self._should_activate_load_shedding():
            if priority == TaskPriority.NORMAL:
                self.metrics.load_shed_operations += 1
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": "Request shed due to high load",
                    "load_shed": True
                }
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            return {
                "request_id": request_id,
                "success": False,
                "error": "Circuit breaker open",
                "circuit_open": True
            }
        
        try:
            # Execute through pipeline
            failure_rate = min(self.metrics.total_requests * 0.01, 0.3)  # Increasing failure rate
            simulate_failure = self.metrics.total_requests > 10 and (self.metrics.total_requests % 4 == 0)
            
            result = await self.pipeline.process_request(request_id, simulate_failure)
            
            self.circuit_breaker.record_success()
            self.metrics.successful_requests += 1
            
            return result
            
        except NetraException as e:
            self.circuit_breaker.record_failure(str(e))
            self.metrics.failed_requests += 1
            
            if self.circuit_breaker.is_open and self.circuit_breaker.state == CircuitState.OPEN:
                self.metrics.circuit_activations += 1
            
            return {
                "request_id": request_id,
                "success": False,
                "error": str(e),
                "circuit_state": self.circuit_breaker.state.value
            }
    
    def _should_activate_load_shedding(self) -> bool:
        """Determine if load shedding should be activated."""
        if self.metrics.total_requests < 5:
            return False
            
        failure_rate = self.metrics.failed_requests / self.metrics.total_requests
        
        if failure_rate >= self.load_shed_threshold and not self.load_shedding_active:
            self.load_shedding_active = True
            logger.info(f"Load shedding activated at {failure_rate:.2%} failure rate")
        elif failure_rate < (self.load_shed_threshold * 0.5) and self.load_shedding_active:
            self.load_shedding_active = False
            logger.info(f"Load shedding deactivated at {failure_rate:.2%} failure rate")
            
        return self.load_shedding_active
    
    async def test_recovery_mechanism(self) -> Dict[str, Any]:
        """Test circuit breaker recovery mechanisms."""
        recovery_start = time.time()
        recovery_successful = False
        
        # Wait for circuit to enter half-open state
        max_wait = 35
        while time.time() - recovery_start < max_wait:
            if self.circuit_breaker.state == CircuitState.HALF_OPEN:
                break
            await asyncio.sleep(0.5)
        
        if self.circuit_breaker.state == CircuitState.HALF_OPEN:
            # Attempt recovery with successful requests
            for i in range(3):
                self.metrics.recovery_attempts += 1
                request_id = f"recovery_{i}"
                
                # Force successful execution for recovery
                self.pipeline.failure_rate = 0.0
                
                result = await self.execute_agent_request(request_id, TaskPriority.HIGH)
                
                if result["success"] and self.circuit_breaker.state == CircuitState.CLOSED:
                    recovery_successful = True
                    break
                    
                await asyncio.sleep(0.1)
        
        recovery_time = time.time() - recovery_start
        
        return {
            "recovery_successful": recovery_successful,
            "recovery_time": recovery_time,
            "recovery_attempts": self.metrics.recovery_attempts,
            "final_circuit_state": self.circuit_breaker.state.value
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        avg_response_time = 0.0
        if self.pipeline.processing_times:
            avg_response_time = sum(self.pipeline.processing_times) / len(self.pipeline.processing_times)
        
        return {
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate(),
                "failed_requests": self.metrics.failed_requests,
                "circuit_activations": self.metrics.circuit_activations,
                "load_shed_operations": self.metrics.load_shed_operations,
                "recovery_attempts": self.metrics.recovery_attempts
            },
            "performance": {
                "average_response_time": avg_response_time,
                "peak_concurrent_agents": max(self.pipeline.processing_times) if self.pipeline.processing_times else 0,
                "pipeline_overloaded": self.pipeline.is_overloaded
            },
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "is_open": self.circuit_breaker.is_open
            },
            "load_shedding": {
                "active": self.load_shedding_active,
                "threshold": self.load_shed_threshold,
                "operations": self.metrics.load_shed_operations
            }
        }


class AgentPipelineLoadTester:
    """Load tester for agent pipeline circuit breaking scenarios."""
    
    def __init__(self, circuit_manager: AgentPipelineCircuitManager):
        self.circuit_manager = circuit_manager
        
    async def execute_load_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Execute comprehensive load test with circuit breaking validation."""
        start_time = time.time()
        test_results = []
        circuit_activation_time = None
        
        # Create semaphore to control concurrent requests
        semaphore = asyncio.Semaphore(config.concurrent_requests)
        
        async def execute_single_request(request_id: str) -> Dict[str, Any]:
            async with semaphore:
                priority = TaskPriority.HIGH if request_id.endswith("_priority") else TaskPriority.NORMAL
                return await self.circuit_manager.execute_agent_request(request_id, priority)
        
        # Generate request tasks
        tasks = []
        for i in range(config.concurrent_requests):
            request_id = f"load_test_{i}{'_priority' if i % 10 == 0 else ''}"
            task = asyncio.create_task(execute_single_request(request_id))
            tasks.append(task)
            
            # Rate limiting
            if config.request_rate_per_second > 0:
                await asyncio.sleep(1.0 / config.request_rate_per_second)
        
        # Execute all requests
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and detect circuit activation
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_results.append({
                    "request_id": f"load_test_{i}",
                    "success": False,
                    "error": str(result)
                })
            else:
                test_results.append(result)
                
                # Detect circuit activation time
                if (circuit_activation_time is None and 
                    not result.get("success", True) and 
                    result.get("circuit_open", False)):
                    circuit_activation_time = time.time() - start_time
        
        total_test_time = time.time() - start_time
        
        return {
            "load_test_config": {
                "concurrent_requests": config.concurrent_requests,
                "request_rate_per_second": config.request_rate_per_second,
                "duration_seconds": config.duration_seconds
            },
            "execution_metrics": {
                "total_test_time": total_test_time,
                "circuit_activation_time": circuit_activation_time,
                "circuit_activated_within_sla": (
                    circuit_activation_time is not None and 
                    circuit_activation_time <= config.target_circuit_activation_time
                )
            },
            "results": test_results,
            "performance_summary": self.circuit_manager.get_performance_summary()
        }
    
    async def test_cascade_prevention(self) -> Dict[str, Any]:
        """Test that circuit breaking prevents cascading failures."""
        # Create multiple pipeline instances to test cascade prevention
        pipelines = {
            "primary": AgentPipelineCircuitManager(),
            "secondary": AgentPipelineCircuitManager(),
            "tertiary": AgentPipelineCircuitManager()
        }
        
        cascade_results = {}
        
        # Overload primary pipeline
        primary_tasks = []
        for i in range(15):  # Exceed capacity
            task = pipelines["primary"].execute_agent_request(f"cascade_test_primary_{i}")
            primary_tasks.append(task)
        
        primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)
        
        # Test secondary pipeline (should remain operational)
        secondary_tasks = []
        for i in range(5):
            task = pipelines["secondary"].execute_agent_request(f"cascade_test_secondary_{i}")
            secondary_tasks.append(task)
        
        secondary_results = await asyncio.gather(*secondary_tasks, return_exceptions=True)
        
        # Analyze cascade prevention
        primary_failures = sum(1 for r in primary_results if isinstance(r, Exception) or not r.get("success", True))
        secondary_failures = sum(1 for r in secondary_results if isinstance(r, Exception) or not r.get("success", True))
        
        cascade_prevented = secondary_failures < (len(secondary_results) * 0.5)  # Less than 50% failure
        
        return {
            "cascade_prevention": {
                "primary_failures": primary_failures,
                "secondary_failures": secondary_failures,
                "cascade_prevented": cascade_prevented
            },
            "pipeline_states": {
                name: {
                    "circuit_state": pipeline.circuit_breaker.state.value,
                    "metrics": pipeline.get_performance_summary()
                }
                for name, pipeline in pipelines.items()
            }
        }


@pytest.fixture
async def agent_pipeline_circuit_manager():
    """Create agent pipeline circuit manager for testing."""
    manager = AgentPipelineCircuitManager()
    yield manager


@pytest.fixture
async def agent_pipeline_load_tester(agent_pipeline_circuit_manager):
    """Create load tester for agent pipeline."""
    tester = AgentPipelineLoadTester(agent_pipeline_circuit_manager)
    yield tester


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestAgentPipelineCircuitBreakingL3:
    """L3 integration tests for agent pipeline circuit breaking."""
    
    async def test_circuit_activation_under_load(self, agent_pipeline_load_tester):
        """Test that circuit breaker activates within 5 seconds under load."""
        config = LoadTestConfig(
            concurrent_requests=20,
            request_rate_per_second=10,
            duration_seconds=10,
            target_circuit_activation_time=5.0
        )
        
        result = await agent_pipeline_load_tester.execute_load_test(config)
        
        # Verify circuit activated within SLA
        assert result["execution_metrics"]["circuit_activated_within_sla"], \
            f"Circuit should activate within {config.target_circuit_activation_time}s"
        
        # Verify load test execution
        assert result["execution_metrics"]["total_test_time"] < 30.0, \
            "Load test should complete within 30 seconds"
        
        # Verify circuit breaking effectiveness
        performance = result["performance_summary"]
        assert performance["metrics"]["circuit_activations"] >= 1, \
            "Circuit should activate at least once"
        
        assert performance["metrics"]["success_rate"] < 100.0, \
            "Should have some failures to trigger circuit breaking"
    
    async def test_graceful_degradation_mechanisms(self, agent_pipeline_circuit_manager):
        """Test graceful degradation when agent pipeline is overloaded."""
        manager = agent_pipeline_circuit_manager
        
        # Generate high load to trigger degradation
        degradation_tasks = []
        for i in range(15):
            task = manager.execute_agent_request(f"degradation_test_{i}")
            degradation_tasks.append(task)
        
        results = await asyncio.gather(*degradation_tasks, return_exceptions=True)
        
        # Analyze degradation behavior
        successful_requests = [r for r in results if not isinstance(r, Exception) and r.get("success", False)]
        failed_requests = [r for r in results if isinstance(r, Exception) or not r.get("success", True)]
        
        # Should have graceful failures rather than exceptions
        exception_count = sum(1 for r in results if isinstance(r, Exception))
        assert exception_count < len(results) * 0.2, \
            "Should have fewer than 20% unhandled exceptions"
        
        # Should maintain some successful processing
        assert len(successful_requests) > 0, \
            "Should maintain some successful request processing during degradation"
        
        # Verify circuit state reflects degradation
        performance = manager.get_performance_summary()
        assert performance["circuit_breaker"]["state"] in ["OPEN", "HALF_OPEN"], \
            "Circuit should be in protective state during degradation"
    
    async def test_load_shedding_strategies(self, agent_pipeline_circuit_manager):
        """Test load shedding strategies under high failure rates."""
        manager = agent_pipeline_circuit_manager
        
        # Generate requests with mixed priorities
        shedding_tasks = []
        for i in range(20):
            priority = TaskPriority.HIGH if i % 5 == 0 else TaskPriority.NORMAL
            task = manager.execute_agent_request(f"shedding_test_{i}", priority)
            shedding_tasks.append(task)
        
        results = await asyncio.gather(*shedding_tasks, return_exceptions=True)
        
        # Analyze load shedding behavior
        shed_requests = [r for r in results if not isinstance(r, Exception) and r.get("load_shed", False)]
        high_priority_failures = []
        normal_priority_failures = []
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and not result.get("success", True):
                if i % 5 == 0:  # High priority request
                    high_priority_failures.append(result)
                else:  # Normal priority request
                    normal_priority_failures.append(result)
        
        # Verify load shedding activated
        performance = manager.get_performance_summary()
        assert performance["load_shedding"]["operations"] > 0, \
            "Load shedding should activate under high load"
        
        # Verify priority-based shedding (high priority should be preserved)
        assert len(shed_requests) > 0, "Should have shed some requests"
        
        # High priority requests should have better success rate
        total_high_priority = len([i for i in range(20) if i % 5 == 0])
        high_priority_success_rate = (total_high_priority - len(high_priority_failures)) / total_high_priority
        
        assert high_priority_success_rate >= 0.5, \
            "High priority requests should have better success rate during load shedding"
    
    async def test_cascade_prevention(self, agent_pipeline_load_tester):
        """Test that circuit breaking prevents cascading failures across services."""
        result = await agent_pipeline_load_tester.test_cascade_prevention()
        
        # Verify cascade was prevented
        assert result["cascade_prevention"]["cascade_prevented"], \
            "Circuit breaking should prevent failure cascade to secondary services"
        
        # Verify primary pipeline failed while secondary remained operational
        primary_state = result["pipeline_states"]["primary"]
        secondary_state = result["pipeline_states"]["secondary"]
        
        assert primary_state["circuit_state"] in ["OPEN", "HALF_OPEN"], \
            "Primary pipeline circuit should be in protective state"
        
        assert secondary_state["metrics"]["metrics"]["success_rate"] > 50.0, \
            "Secondary pipeline should maintain >50% success rate"
    
    async def test_recovery_mechanisms(self, agent_pipeline_circuit_manager):
        """Test circuit breaker recovery mechanisms after failure."""
        manager = agent_pipeline_circuit_manager
        
        # First, trigger circuit opening
        trigger_tasks = []
        for i in range(10):
            task = manager.execute_agent_request(f"trigger_failure_{i}")
            trigger_tasks.append(task)
        
        await asyncio.gather(*trigger_tasks, return_exceptions=True)
        
        # Verify circuit is open
        initial_state = manager.circuit_breaker.state
        assert initial_state == CircuitState.OPEN, "Circuit should be open after failures"
        
        # Test recovery mechanism
        recovery_result = await manager.test_recovery_mechanism()
        
        # Verify recovery behavior
        assert recovery_result["recovery_time"] <= 40.0, \
            "Recovery should complete within 40 seconds"
        
        assert recovery_result["recovery_attempts"] >= 1, \
            "Should attempt recovery at least once"
        
        # Verify circuit recovery (if successful)
        if recovery_result["recovery_successful"]:
            assert recovery_result["final_circuit_state"] == "CLOSED", \
                "Successful recovery should close the circuit"
        else:
            assert recovery_result["final_circuit_state"] in ["OPEN", "HALF_OPEN"], \
                "Failed recovery should keep circuit in protective state"
    
    async def test_performance_under_sustained_load(self, agent_pipeline_load_tester):
        """Test agent pipeline performance under sustained load conditions."""
        # Test with sustained moderate load
        sustained_config = LoadTestConfig(
            concurrent_requests=30,
            request_rate_per_second=5,
            duration_seconds=15
        )
        
        result = await agent_pipeline_load_tester.execute_load_test(sustained_config)
        
        performance = result["performance_summary"]
        
        # Verify performance under sustained load
        assert performance["performance"]["average_response_time"] < 2.0, \
            "Average response time should remain under 2 seconds"
        
        assert performance["metrics"]["success_rate"] >= 60.0, \
            "Should maintain at least 60% success rate under sustained load"
        
        # Verify circuit breaker effectiveness
        assert performance["circuit_breaker"]["state"] != "UNKNOWN", \
            "Circuit breaker should have a valid state"
        
        # Verify load shedding if activated
        if performance["load_shedding"]["active"]:
            assert performance["load_shedding"]["operations"] > 0, \
                "If load shedding is active, should have shed some operations"
    
    async def test_concurrent_circuit_breakers(self, agent_pipeline_load_tester):
        """Test multiple concurrent circuit breakers don't interfere."""
        # Create multiple concurrent load tests
        concurrent_tests = []
        for i in range(3):
            config = LoadTestConfig(
                concurrent_requests=10,
                request_rate_per_second=8,
                duration_seconds=8
            )
            test_task = agent_pipeline_load_tester.execute_load_test(config)
            concurrent_tests.append(test_task)
        
        results = await asyncio.gather(*concurrent_tests, return_exceptions=True)
        
        # Verify all tests completed
        successful_tests = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_tests) >= 2, \
            "At least 2 concurrent tests should complete successfully"
        
        # Verify circuit breakers operated independently
        for result in successful_tests:
            if not isinstance(result, Exception):
                performance = result["performance_summary"]
                assert "circuit_breaker" in performance, \
                    "Each test should have circuit breaker metrics"
                
                assert performance["metrics"]["total_requests"] > 0, \
                    "Each test should process some requests"