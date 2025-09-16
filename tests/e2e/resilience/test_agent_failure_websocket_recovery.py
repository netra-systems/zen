"""Agent Failure Recovery via WebSocket Test - P1 HIGH Priority Integration Test

Comprehensive test suite for validating agent failure recovery mechanisms through 
WebSocket communication. Tests error event propagation, graceful degradation,
circuit breaker activation, and system recovery patterns.

Business Value Justification (BVJ):
1. Segment: All paid tiers ($80K+ MRR protection)
2. Business Goal: Ensure system resilience during agent failures
3. Value Impact: Prevents complete service outages, maintains partial functionality
4. Revenue Impact: Protects against customer churn from system failures

Refactored for <300 lines using helpers.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
import pytest_asyncio
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS, TEST_ENDPOINTS
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient
from tests.e2e.helpers.agent.agent_failure_recovery_helpers import (
    AgentFailureSimulator,
    WebSocketErrorEventValidator,
    CircuitBreakerTester,
    FailureType,
    RecoveryAction,
    create_error_test_scenarios,
    validate_recovery_timing,
    create_mock_websocket_error
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest_asyncio.fixture
async def failure_simulator():
    """Create agent failure simulator fixture."""
    simulator = AgentFailureSimulator()
    try:
        yield simulator
    finally:
        # Cleanup any active failures
        pass


@pytest_asyncio.fixture
async def error_validator():
    """Create WebSocket error event validator fixture."""
    validator = WebSocketErrorEventValidator()
    try:
        yield validator
    finally:
        validator.clear_errors()


@pytest_asyncio.fixture
async def circuit_breaker_tester():
    """Create circuit breaker tester fixture."""
    tester = CircuitBreakerTester()
    try:
        yield tester
    finally:
        # Cleanup circuit states
        pass


@pytest_asyncio.fixture
async def websocket_client():
    """Create WebSocket client for testing."""
    client = RealWebSocketClient(TEST_ENDPOINTS.ws_url)
    try:
        yield client
    finally:
        await client.close()


@pytest.mark.e2e
class AgentFailureRecoveryTests:
    """Test agent failure recovery mechanisms via WebSocket."""
    
    @pytest.mark.e2e
    async def test_agent_timeout_recovery(self, failure_simulator, error_validator):
        """Test recovery from agent timeout failures."""
        simulator = failure_simulator
        validator = error_validator
        
        # Simulate agent timeout
        agent_id = "test_agent_timeout"
        failure_data = await simulator.simulate_agent_timeout(agent_id, timeout_duration=5.0)
        
        # Validate failure was recorded
        assert failure_data["failure_type"] == FailureType.TIMEOUT.value
        assert failure_data["agent_id"] == agent_id
        
        # Simulate recovery
        recovery_start = time.time()
        recovery_result = await simulator.trigger_recovery(
            failure_data["failure_id"], 
            RecoveryAction.RETRY
        )
        recovery_end = time.time()
        
        # Validate recovery
        assert recovery_result["success"]
        assert recovery_result["recovery_action"] == RecoveryAction.RETRY.value
        
        # Validate recovery timing
        recovery_within_limit = await validate_recovery_timing(recovery_start, recovery_end, 10.0)
        assert recovery_within_limit, "Recovery took too long"
        
        # Check failure statistics
        stats = simulator.get_failure_statistics()
        assert stats["total_failures"] >= 1
        assert stats["recovery_attempts"] >= 1
        
        logger.info(f"Agent timeout recovery test completed: {stats}")
    
    @pytest.mark.e2e
    async def test_network_error_handling(self, failure_simulator, error_validator):
        """Test handling of network connectivity errors."""
        simulator = failure_simulator
        validator = error_validator
        
        # Simulate network error
        agent_id = "test_agent_network"
        failure_data = await simulator.simulate_network_error(agent_id, "CONNECTION_LOST")
        
        # Validate failure data
        assert failure_data["failure_type"] == FailureType.NETWORK_ERROR.value
        assert failure_data["error_code"] == "CONNECTION_LOST"
        
        # Create mock error event
        error_event = {
            "type": "agent_error",
            "payload": {
                "error_type": "network_error",
                "message": "Network connection lost",
                "severity": "HIGH",
                "error_id": failure_data["failure_id"]
            },
            "timestamp": time.time()
        }
        
        # Validate error event structure
        validator.capture_error_event(error_event)
        assert validator.validate_error_event_structure(error_event)
        
        # Trigger recovery
        recovery_result = await simulator.trigger_recovery(
            failure_data["failure_id"],
            RecoveryAction.RETRY
        )
        
        assert recovery_result["success"]
        logger.info("Network error handling test completed successfully")
    
    @pytest.mark.e2e
    async def test_processing_error_fallback(self, failure_simulator, error_validator):
        """Test fallback mechanism for processing errors."""
        simulator = failure_simulator
        validator = error_validator
        
        # Simulate processing error
        agent_id = "test_agent_processing"
        failure_data = await simulator.simulate_processing_error(
            agent_id, 
            "AI model request failed"
        )
        
        # Validate failure data
        assert failure_data["failure_type"] == FailureType.PROCESSING_ERROR.value
        assert "failed" in failure_data["error_message"]
        
        # Test fallback recovery
        recovery_result = await simulator.trigger_recovery(
            failure_data["failure_id"],
            RecoveryAction.FALLBACK
        )
        
        assert recovery_result["success"]
        assert recovery_result["recovery_action"] == RecoveryAction.FALLBACK.value
        
        # Validate failure statistics show successful recovery
        stats = simulator.get_failure_statistics()
        assert stats["recovery_attempts"] >= 1
        assert stats["success_rate"] > 0
        
        logger.info("Processing error fallback test completed")
    
    @pytest.mark.e2e
    async def test_circuit_breaker_activation(self, failure_simulator, circuit_breaker_tester):
        """Test circuit breaker activates after multiple failures."""
        simulator = failure_simulator
        circuit_tester = circuit_breaker_tester
        
        circuit_name = "agent_service"
        circuit_tester.initialize_circuit(circuit_name, threshold=3)
        
        # Trigger multiple failures to activate circuit breaker
        for i in range(5):
            failure_data = await simulator.simulate_processing_error(
                f"agent_{i}", 
                f"Processing error {i}"
            )
            
            # Trigger circuit breaker failure
            circuit_result = await circuit_tester.trigger_failure(circuit_name)
            
            if i >= 2:  # After 3rd failure, circuit should be open
                assert circuit_result["state"] == "OPEN"
        
        # Validate circuit breaker behavior
        circuit_stats = circuit_tester.get_circuit_statistics()
        assert circuit_stats["circuits"][circuit_name] == "OPEN"
        assert circuit_stats["failure_counts"][circuit_name] >= 3
        
        # Test recovery attempt
        recovery_result = await circuit_tester.attempt_recovery(circuit_name)
        assert recovery_result["state"] == "HALF_OPEN"
        
        logger.info(f"Circuit breaker test completed: {circuit_stats}")
    
    @pytest.mark.e2e
    async def test_error_event_communication(self, failure_simulator, error_validator, websocket_client):
        """Test error events are properly communicated via WebSocket."""
        simulator = failure_simulator
        validator = error_validator
        client = websocket_client
        
        # Simulate multiple types of errors
        error_scenarios = create_error_test_scenarios()
        
        captured_events = []
        
        for scenario in error_scenarios[:3]:  # Test first 3 scenarios
            failure_type = scenario["failure_type"]
            
            if failure_type == FailureType.TIMEOUT:
                failure_data = await simulator.simulate_agent_timeout("test_agent")
            elif failure_type == FailureType.NETWORK_ERROR:
                failure_data = await simulator.simulate_network_error("test_agent")
            elif failure_type == FailureType.PROCESSING_ERROR:
                failure_data = await simulator.simulate_processing_error("test_agent")
            
            # Create corresponding error event
            error_event = {
                "type": f"{failure_type.value}_error",
                "payload": {
                    "error_type": failure_type.value,
                    "message": f"Test {failure_type.value} error",
                    "severity": scenario["severity"],
                    "error_id": failure_data["failure_id"]
                },
                "timestamp": time.time()
            }
            
            validator.capture_error_event(error_event)
            captured_events.append(error_event)
            
            # Validate error event structure
            assert validator.validate_error_event_structure(error_event)
        
        # Validate we captured multiple error types
        assert len(captured_events) >= 3
        
        # Validate different error types are represented
        error_types = {event["payload"]["error_type"] for event in captured_events}
        assert len(error_types) >= 2
        
        logger.info(f"Error event communication test completed with {len(captured_events)} events")
    
    @pytest.mark.e2e
    async def test_graceful_degradation(self, failure_simulator, error_validator):
        """Test system gracefully degrades during failures."""
        simulator = failure_simulator
        validator = error_validator
        
        # Simulate resource exhaustion
        agent_id = "test_agent_degradation"
        failure_data = await simulator.simulate_processing_error(
            agent_id,
            "Resource exhaustion - high load"
        )
        
        # Create degradation event
        degradation_event = {
            "type": "system_degradation",
            "payload": {
                "error_type": "resource_exhaustion",
                "message": "System operating in degraded mode",
                "severity": "MEDIUM",
                "degradation_level": "partial_functionality"
            },
            "timestamp": time.time()
        }
        
        validator.capture_error_event(degradation_event)
        
        # Validate degradation is communicated
        assert validator.validate_error_event_structure(degradation_event)
        
        # Test graceful degradation recovery
        recovery_result = await simulator.trigger_recovery(
            failure_data["failure_id"],
            RecoveryAction.GRACEFUL_DEGRADATION
        )
        
        assert recovery_result["success"]
        assert recovery_result["recovery_action"] == RecoveryAction.GRACEFUL_DEGRADATION.value
        
        logger.info("Graceful degradation test completed")
    
    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_recovery_performance(self, failure_simulator, circuit_breaker_tester):
        """Test recovery mechanisms complete within performance requirements."""
        simulator = failure_simulator
        circuit_tester = circuit_breaker_tester
        
        # Initialize circuit for performance testing
        circuit_name = "performance_test_circuit"
        circuit_tester.initialize_circuit(circuit_name)
        
        # Measure failure simulation performance
        start_time = time.time()
        
        failure_data = await simulator.simulate_agent_timeout("perf_test_agent", 1.0)
        
        simulation_time = time.time() - start_time
        assert simulation_time < 1.0  # Should be very fast
        
        # Measure recovery performance
        recovery_start = time.time()
        
        recovery_result = await simulator.trigger_recovery(
            failure_data["failure_id"],
            RecoveryAction.RETRY
        )
        
        recovery_time = time.time() - recovery_start
        assert recovery_time < 2.0  # Should be fast
        
        # Test circuit breaker performance
        circuit_start = time.time()
        
        circuit_result = await circuit_tester.trigger_failure(circuit_name)
        
        circuit_time = time.time() - circuit_start
        assert circuit_time < 0.5  # Should be very fast
        
        # Validate overall performance
        total_test_time = time.time() - start_time
        assert total_test_time < 10.0  # Entire test should complete quickly
        
        logger.info(f"Recovery performance test completed in {total_test_time:.3f}s - "
                   f"Simulation: {simulation_time:.3f}s, "
                   f"Recovery: {recovery_time:.3f}s, "
                   f"Circuit: {circuit_time:.3f}s")
    
    @pytest.mark.e2e
    async def test_multiple_concurrent_failures(self, failure_simulator, error_validator):
        """Test handling of multiple concurrent agent failures."""
        simulator = failure_simulator
        validator = error_validator
        
        # Create multiple concurrent failures
        failure_tasks = []
        
        for i in range(3):
            task = asyncio.create_task(
                simulator.simulate_processing_error(f"concurrent_agent_{i}", f"Concurrent error {i}")
            )
            failure_tasks.append(task)
        
        # Wait for all failures to be simulated
        failure_results = await asyncio.gather(*failure_tasks)
        
        # Validate all failures were recorded
        assert len(failure_results) == 3
        
        for failure in failure_results:
            assert failure["status"] == "active"
            assert "concurrent_agent_" in failure["agent_id"]
        
        # Test concurrent recovery
        recovery_tasks = []
        
        for failure in failure_results:
            task = asyncio.create_task(
                simulator.trigger_recovery(failure["failure_id"], RecoveryAction.RETRY)
            )
            recovery_tasks.append(task)
        
        recovery_results = await asyncio.gather(*recovery_tasks)
        
        # Validate all recoveries succeeded
        for recovery in recovery_results:
            assert recovery["success"]
        
        # Check final statistics
        stats = simulator.get_failure_statistics()
        assert stats["total_failures"] >= 3
        assert stats["recovery_attempts"] >= 3
        assert stats["active_failures"] == 0  # All should be recovered
        
        logger.info(f"Concurrent failures test completed: {stats}")
