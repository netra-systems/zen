"""
Circuit Breaker SSOT Integration Test Suite

This test suite focuses specifically on circuit breaker SSOT compliance at the integration level.
These tests verify that circuit breaker functionality works consistently across different components
and that there is truly only ONE circuit breaker implementation being used system-wide.

CRITICAL: These tests are designed to FAIL in the current state where multiple circuit breaker
implementations exist. They will PASS once proper SSOT consolidation is achieved.

Integration Test Focus:
1. Cross-component circuit breaker behavior consistency
2. Configuration propagation and consistency
3. State synchronization across circuit breaker instances
4. Failure threshold and recovery behavior uniformity
5. Metrics and monitoring consistency
6. Real failure scenario handling
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.reliability import get_reliability_wrapper


class TestCircuitBreakerStateConsistency:
    """Test circuit breaker state consistency across different components."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_state_synchronization_across_agents(self):
        """
        CRITICAL: Verify circuit breaker states are consistent across agents.
        
        Current State: SHOULD FAIL - Different circuit breaker instances have independent states
        Expected: All agents using same service should share circuit breaker state
        """
        # Create multiple agents that should share circuit breaker state
        agent1 = BaseSubAgent(name="Agent1", enable_reliability=True)
        agent2 = BaseSubAgent(name="Agent2", enable_reliability=True) 
        agent3 = BaseSubAgent(name="Agent3", enable_reliability=True)
        
        agents = [agent1, agent2, agent3]
        
        # Simulate failure condition that should trip circuit breaker
        failure_operation = AsyncMock(side_effect=Exception("Simulated failure"))
        
        # Execute failing operation multiple times through different agents
        # This should eventually trip the circuit breaker
        failure_count = 0
        max_failures = 6  # Should exceed typical circuit breaker threshold
        
        for i in range(max_failures):
            agent = agents[i % len(agents)]
            try:
                await agent.execute_with_reliability(
                    failure_operation, 
                    "test_operation",
                    timeout=1.0
                )
            except Exception:
                failure_count += 1
        
        # ASSERTION: All agents should now have circuit breaker in OPEN state
        circuit_states = []
        for i, agent in enumerate(agents):
            status = agent.get_circuit_breaker_status()
            circuit_states.append((f"Agent{i+1}", status.get('state', 'unknown')))
        
        # Check if all circuit breakers are in same state (should be OPEN)
        states = [state for _, state in circuit_states]
        unique_states = set(states)
        
        assert len(unique_states) == 1, (
            f"SSOT VIOLATION: Circuit breaker states not synchronized across agents. "
            f"Found states: {circuit_states}. "
            f"All agents accessing the same service should share circuit breaker state. "
            f"This indicates multiple independent circuit breaker instances exist."
        )
        
        # Verify the shared state is OPEN (circuit tripped)
        expected_state = "OPEN"
        actual_state = states[0] if states else "unknown"
        assert actual_state == expected_state, (
            f"SSOT VIOLATION: Circuit breaker did not trip as expected. "
            f"Expected state: {expected_state}, Actual state: {actual_state}. "
            f"Circuit breaker sharing mechanism not working correctly."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_configuration_consistency(self):
        """
        CRITICAL: Verify circuit breaker configurations are consistent across all instances.
        
        Current State: SHOULD FAIL - Different configurations found across components
        Expected: All circuit breakers should have identical configuration
        """
        # Create agents with reliability enabled
        agent1 = BaseSubAgent(name="TestAgent1", enable_reliability=True)
        agent2 = BaseSubAgent(name="TestAgent2", enable_reliability=True)
        
        # Get circuit breaker configurations
        config1 = agent1.get_circuit_breaker_status()
        config2 = agent2.get_circuit_breaker_status()
        
        # Extract configuration parameters for comparison
        config1_params = self._extract_circuit_breaker_config_params(config1)
        config2_params = self._extract_circuit_breaker_config_params(config2)
        
        # ASSERTION: Configuration parameters should be identical
        mismatched_params = []
        for param, value1 in config1_params.items():
            value2 = config2_params.get(param, "MISSING")
            if value1 != value2:
                mismatched_params.append((param, value1, value2))
        
        assert len(mismatched_params) == 0, (
            f"SSOT VIOLATION: Circuit breaker configuration inconsistency detected. "
            f"Mismatched parameters: {mismatched_params}. "
            f"All circuit breaker instances must have identical configuration. "
            f"This indicates multiple configuration sources or classes exist."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold_consistency(self):
        """
        CRITICAL: Verify failure thresholds are consistent across all implementations.
        
        Current State: SHOULD FAIL - Different failure thresholds across components
        Expected: Single failure threshold configuration system-wide
        """
        # Create multiple reliability wrappers (simulating different components)
        reliability1 = get_reliability_wrapper("component1", None, None)
        reliability2 = get_reliability_wrapper("component2", None, None)
        reliability3 = get_reliability_wrapper("component3", None, None)
        
        reliability_wrappers = [reliability1, reliability2, reliability3]
        
        # Extract failure thresholds from each wrapper
        failure_thresholds = []
        recovery_timeouts = []
        
        for i, wrapper in enumerate(reliability_wrappers):
            if hasattr(wrapper, 'circuit_breaker'):
                cb = wrapper.circuit_breaker
                if hasattr(cb, 'failure_threshold'):
                    failure_thresholds.append((f"component{i+1}", cb.failure_threshold))
                if hasattr(cb, 'recovery_timeout'):
                    recovery_timeouts.append((f"component{i+1}", cb.recovery_timeout))
        
        # ASSERTION: All failure thresholds should be identical
        threshold_values = [threshold for _, threshold in failure_thresholds]
        unique_thresholds = set(threshold_values)
        
        assert len(unique_thresholds) <= 1, (
            f"SSOT VIOLATION: Inconsistent failure thresholds across components. "
            f"Found thresholds: {failure_thresholds}. "
            f"All circuit breakers must use the same failure threshold configuration."
        )
        
        # ASSERTION: All recovery timeouts should be identical
        timeout_values = [timeout for _, timeout in recovery_timeouts]
        unique_timeouts = set(timeout_values)
        
        assert len(unique_timeouts) <= 1, (
            f"SSOT VIOLATION: Inconsistent recovery timeouts across components. "
            f"Found timeouts: {recovery_timeouts}. "
            f"All circuit breakers must use the same recovery timeout configuration."
        )
    
    def _extract_circuit_breaker_config_params(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration parameters from circuit breaker status."""
        config_params = {}
        
        # Extract common configuration parameters
        param_keys = [
            'failure_threshold', 'recovery_timeout', 'timeout_seconds',
            'max_failures', 'recovery_time', 'circuit_timeout'
        ]
        
        for key in param_keys:
            if key in status:
                config_params[key] = status[key]
            elif 'config' in status and isinstance(status['config'], dict):
                if key in status['config']:
                    config_params[key] = status['config'][key]
        
        return config_params


class TestCircuitBreakerFailureRecoveryConsistency:
    """Test circuit breaker failure and recovery behavior consistency."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_detection_consistency(self):
        """
        CRITICAL: Verify failure detection is consistent across all circuit breaker instances.
        
        Current State: SHOULD FAIL - Different failure detection behaviors
        Expected: Uniform failure detection and counting across all instances
        """
        # Create agents with different names but same underlying service
        agents = [
            BaseSubAgent(name=f"Agent_{i}", enable_reliability=True) 
            for i in range(3)
        ]
        
        # Create a failure operation that should be detected consistently
        failure_count = {'count': 0}
        
        async def tracked_failure_operation():
            failure_count['count'] += 1
            raise ConnectionError(f"Connection failed (attempt {failure_count['count']})")
        
        # Execute failing operations through different agents
        failure_results = []
        for i, agent in enumerate(agents):
            try:
                result = await agent.execute_with_reliability(
                    tracked_failure_operation,
                    f"test_operation_{i}",
                    timeout=1.0
                )
                failure_results.append((i, "success", result))
            except Exception as e:
                failure_results.append((i, "failure", str(e)))
        
        # Get failure counts from each agent's circuit breaker
        failure_counts = []
        for i, agent in enumerate(agents):
            status = agent.get_circuit_breaker_status()
            failure_count_value = self._extract_failure_count(status)
            failure_counts.append((i, failure_count_value))
        
        # ASSERTION: Failure counting should be consistent
        # (Either all agents share failure count, or each has same detection behavior)
        count_values = [count for _, count in failure_counts if count is not None]
        
        if len(count_values) > 1:
            # If multiple counts exist, they should either be identical (shared state)
            # or follow a predictable pattern (independent but consistent behavior)
            unique_counts = set(count_values)
            
            # Allow for slight variations due to timing, but not major differences
            max_count = max(count_values) if count_values else 0
            min_count = min(count_values) if count_values else 0
            count_variance = max_count - min_count
            
            assert count_variance <= 1, (
                f"SSOT VIOLATION: Inconsistent failure counting across agents. "
                f"Failure counts: {failure_counts}. "
                f"Variance: {count_variance} (max allowed: 1). "
                f"Circuit breaker failure detection must be consistent."
            )
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker_recovery_behavior_consistency(self):
        """
        CRITICAL: Verify circuit breaker recovery behavior is consistent.
        
        Current State: SHOULD FAIL - Different recovery behaviors
        Expected: Uniform recovery timing and behavior across all instances
        """
        # Create agent with reliability
        agent = BaseSubAgent(name="RecoveryTestAgent", enable_reliability=True)
        
        # Force circuit breaker to OPEN state by causing failures
        failure_operation = AsyncMock(side_effect=ConnectionError("Forced failure"))
        
        # Trigger enough failures to open circuit
        for _ in range(6):  # Exceed typical failure threshold
            try:
                await agent.execute_with_reliability(
                    failure_operation,
                    "force_failure_operation",
                    timeout=0.5
                )
            except Exception:
                pass
        
        # Verify circuit is OPEN
        initial_status = agent.get_circuit_breaker_status()
        initial_state = initial_status.get('state', 'unknown')
        
        assert initial_state == "OPEN", (
            f"Setup failed: Circuit breaker should be OPEN, got {initial_state}. "
            f"Cannot test recovery behavior without properly opened circuit."
        )
        
        # Record recovery timeout from configuration
        recovery_timeout = self._extract_recovery_timeout(initial_status)
        
        # Wait for recovery period (should transition to HALF_OPEN)
        if recovery_timeout:
            await asyncio.sleep(recovery_timeout + 0.5)  # Add buffer
        else:
            await asyncio.sleep(2.0)  # Default wait if timeout not found
        
        # Check if circuit moved to HALF_OPEN state
        post_wait_status = agent.get_circuit_breaker_status()
        post_wait_state = post_wait_status.get('state', 'unknown')
        
        # ASSERTION: Circuit should be in recovery state (HALF_OPEN)
        expected_recovery_state = "HALF_OPEN"
        assert post_wait_state == expected_recovery_state, (
            f"SSOT VIOLATION: Circuit breaker recovery behavior inconsistent. "
            f"Expected state after recovery timeout: {expected_recovery_state}, "
            f"Actual state: {post_wait_state}. "
            f"Recovery timeout: {recovery_timeout}s. "
            f"Circuit breaker recovery must follow consistent state transitions."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_consistency(self):
        """
        CRITICAL: Verify circuit breaker metrics are consistent across instances.
        
        Current State: SHOULD FAIL - Different metrics collection approaches
        Expected: Uniform metrics collection and reporting
        """
        # Create multiple agents to test metrics consistency
        agents = [
            BaseSubAgent(name=f"MetricsAgent_{i}", enable_reliability=True)
            for i in range(2)
        ]
        
        # Execute some operations to generate metrics
        success_operation = AsyncMock(return_value="success")
        failure_operation = AsyncMock(side_effect=RuntimeError("test error"))
        
        # Mix of successful and failed operations
        operations = [
            (success_operation, "success_op"),
            (success_operation, "success_op"),
            (failure_operation, "failure_op"),
            (success_operation, "success_op"),
            (failure_operation, "failure_op")
        ]
        
        # Execute operations through different agents
        for i, (operation, op_name) in enumerate(operations):
            agent = agents[i % len(agents)]
            try:
                await agent.execute_with_reliability(operation, op_name, timeout=1.0)
            except Exception:
                pass  # Expected for failure operations
        
        # Collect metrics from all agents
        agent_metrics = []
        for i, agent in enumerate(agents):
            status = agent.get_circuit_breaker_status()
            metrics = self._extract_circuit_breaker_metrics(status)
            agent_metrics.append((i, metrics))
        
        # ASSERTION: Metrics structure should be consistent across agents
        metric_structures = []
        for agent_id, metrics in agent_metrics:
            structure = set(metrics.keys()) if metrics else set()
            metric_structures.append((agent_id, structure))
        
        if len(metric_structures) > 1:
            # Check if all agents have same metrics structure
            first_structure = metric_structures[0][1]
            inconsistent_structures = []
            
            for agent_id, structure in metric_structures[1:]:
                if structure != first_structure:
                    inconsistent_structures.append((agent_id, structure))
            
            assert len(inconsistent_structures) == 0, (
                f"SSOT VIOLATION: Inconsistent metrics structure across agents. "
                f"Expected structure: {first_structure}. "
                f"Inconsistent agents: {inconsistent_structures}. "
                f"All circuit breakers must report identical metrics structure."
            )
    
    def _extract_failure_count(self, status: Dict[str, Any]) -> Optional[int]:
        """Extract failure count from circuit breaker status."""
        # Try different possible keys for failure count
        failure_keys = ['failure_count', 'failures', 'consecutive_failures', 'fail_count']
        
        for key in failure_keys:
            if key in status:
                return status[key]
            elif 'metrics' in status and key in status['metrics']:
                return status['metrics'][key]
            elif 'stats' in status and key in status['stats']:
                return status['stats'][key]
        
        return None
    
    def _extract_recovery_timeout(self, status: Dict[str, Any]) -> Optional[float]:
        """Extract recovery timeout from circuit breaker status."""
        timeout_keys = ['recovery_timeout', 'recovery_time', 'timeout']
        
        for key in timeout_keys:
            if key in status:
                return float(status[key])
            elif 'config' in status and key in status['config']:
                return float(status['config'][key])
        
        return None
    
    def _extract_circuit_breaker_metrics(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from circuit breaker status."""
        metrics = {}
        
        # Standard metric keys
        metric_keys = [
            'success_count', 'failure_count', 'total_requests',
            'success_rate', 'failure_rate', 'avg_response_time'
        ]
        
        for key in metric_keys:
            if key in status:
                metrics[key] = status[key]
            elif 'metrics' in status and isinstance(status['metrics'], dict):
                if key in status['metrics']:
                    metrics[key] = status['metrics'][key]
        
        return metrics


class TestCircuitBreakerIntegrationWithReliabilityManager:
    """Test circuit breaker integration with reliability management."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reliability_manager_integration(self):
        """
        CRITICAL: Verify circuit breaker integrates properly with reliability manager.
        
        Current State: SHOULD FAIL - Inconsistent integration patterns
        Expected: Seamless integration between circuit breaker and reliability manager
        """
        # Create agent with both reliability manager and circuit breaker
        agent = BaseSubAgent(name="IntegrationTestAgent", enable_reliability=True)
        
        # Get both reliability manager and circuit breaker status
        reliability_manager = agent.reliability_manager
        circuit_breaker_status = agent.get_circuit_breaker_status()
        
        # ASSERTION: Reliability manager should exist and be integrated
        assert reliability_manager is not None, (
            "SSOT VIOLATION: Reliability manager not available. "
            "Circuit breaker must be integrated with reliability manager."
        )
        
        # ASSERTION: Circuit breaker should be accessible through reliability system
        assert circuit_breaker_status.get('status') != 'not_available', (
            f"SSOT VIOLATION: Circuit breaker not accessible through reliability system. "
            f"Status: {circuit_breaker_status}. "
            f"Circuit breaker must be properly integrated with reliability infrastructure."
        )
        
        # Test that operations through reliability manager use circuit breaker
        operation_count = {'count': 0}
        
        async def tracked_operation():
            operation_count['count'] += 1
            return f"success_{operation_count['count']}"
        
        # Execute operation through reliability manager
        if hasattr(reliability_manager, 'execute_with_reliability'):
            result = await reliability_manager.execute_with_reliability(
                None,  # context placeholder
                tracked_operation
            )
        else:
            # Fallback to legacy reliability
            result = await agent.execute_with_reliability(
                tracked_operation,
                "integration_test_operation"
            )
        
        # ASSERTION: Operation should have executed successfully through integrated system
        assert operation_count['count'] == 1, (
            f"SSOT VIOLATION: Operation did not execute through reliability system. "
            f"Expected 1 execution, got {operation_count['count']}. "
            f"Circuit breaker and reliability manager integration broken."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_health_status_integration(self):
        """
        CRITICAL: Verify circuit breaker health status is properly integrated.
        
        Current State: SHOULD FAIL - Inconsistent health status reporting
        Expected: Circuit breaker health reflected in overall agent health
        """
        # Create agent with reliability infrastructure
        agent = BaseSubAgent(name="HealthTestAgent", enable_reliability=True)
        
        # Get comprehensive health status
        health_status = agent.get_health_status()
        
        # ASSERTION: Health status should include circuit breaker information
        required_health_components = [
            'agent_name', 'state', 'overall_status'
        ]
        
        missing_components = []
        for component in required_health_components:
            if component not in health_status:
                missing_components.append(component)
        
        assert len(missing_components) == 0, (
            f"SSOT VIOLATION: Missing health status components: {missing_components}. "
            f"Circuit breaker health must be integrated into overall health status."
        )
        
        # Check that circuit breaker affects overall health determination
        overall_status = health_status.get('overall_status', 'unknown')
        assert overall_status in ['healthy', 'degraded', 'unhealthy'], (
            f"SSOT VIOLATION: Invalid overall health status: {overall_status}. "
            f"Circuit breaker health must contribute to valid overall status."
        )
        
        # Verify circuit breaker specific health data is included
        cb_health_indicators = [
            'legacy_reliability', 'modern_execution', 'monitoring'
        ]
        
        cb_health_found = any(
            indicator in health_status for indicator in cb_health_indicators
        )
        
        assert cb_health_found, (
            f"SSOT VIOLATION: Circuit breaker health indicators not found in status. "
            f"Available keys: {list(health_status.keys())}. "
            f"Circuit breaker health must be visible in integrated health status."
        )


class TestCircuitBreakerCrossComponentConsistency:
    """Test circuit breaker behavior consistency across different system components."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_consistency_across_service_components(self):
        """
        CRITICAL: Verify circuit breakers behave consistently across service components.
        
        Current State: SHOULD FAIL - Different circuit breaker behaviors in different services
        Expected: Consistent circuit breaker behavior regardless of component type
        """
        # Create different types of components that use circuit breakers
        components = {
            'agent': BaseSubAgent(name="AgentComponent", enable_reliability=True),
            'reliability_wrapper1': get_reliability_wrapper("service1", None, None),
            'reliability_wrapper2': get_reliability_wrapper("service2", None, None)
        }
        
        # Test failure scenarios across all components
        failure_results = {}
        
        async def test_failure():
            raise TimeoutError("Simulated timeout")
        
        # Execute failure operations through each component type
        for component_name, component in components.items():
            failure_count = 0
            
            if component_name == 'agent':
                # Agent uses execute_with_reliability
                for _ in range(3):
                    try:
                        await component.execute_with_reliability(
                            test_failure, f"test_op_{component_name}"
                        )
                    except Exception:
                        failure_count += 1
            else:
                # Reliability wrappers use execute_safely
                for _ in range(3):
                    try:
                        await component.execute_safely(
                            test_failure, f"test_op_{component_name}"
                        )
                    except Exception:
                        failure_count += 1
            
            failure_results[component_name] = failure_count
        
        # ASSERTION: All components should have consistent failure handling
        failure_counts = list(failure_results.values())
        unique_failure_counts = set(failure_counts)
        
        assert len(unique_failure_counts) == 1, (
            f"SSOT VIOLATION: Inconsistent failure handling across components. "
            f"Failure results: {failure_results}. "
            f"All components must handle failures consistently through unified circuit breaker."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_configuration_propagation(self):
        """
        CRITICAL: Verify circuit breaker configuration propagates consistently.
        
        Current State: SHOULD FAIL - Configuration not properly shared
        Expected: Single configuration source affects all circuit breaker instances
        """
        # Test configuration consistency across multiple instantiations
        agents = []
        configs = []
        
        # Create multiple agents and collect their circuit breaker configurations
        for i in range(3):
            agent = BaseSubAgent(name=f"ConfigTestAgent_{i}", enable_reliability=True)
            agents.append(agent)
            
            cb_status = agent.get_circuit_breaker_status()
            config = self._normalize_circuit_breaker_config(cb_status)
            configs.append((f"agent_{i}", config))
        
        # ASSERTION: All configurations should be identical
        if len(configs) > 1:
            reference_config = configs[0][1]
            mismatched_configs = []
            
            for agent_name, config in configs[1:]:
                if config != reference_config:
                    mismatched_configs.append((agent_name, config))
            
            assert len(mismatched_configs) == 0, (
                f"SSOT VIOLATION: Circuit breaker configuration not consistent across agents. "
                f"Reference config: {reference_config}. "
                f"Mismatched configs: {mismatched_configs}. "
                f"All circuit breakers must use identical configuration from single source."
            )
    
    def _normalize_circuit_breaker_config(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize circuit breaker configuration for comparison."""
        normalized = {}
        
        # Extract and normalize key configuration parameters
        config_keys = [
            'failure_threshold', 'recovery_timeout', 'timeout_seconds'
        ]
        
        for key in config_keys:
            value = None
            
            # Try different locations where config might be stored
            if key in status:
                value = status[key]
            elif 'config' in status and isinstance(status['config'], dict):
                value = status['config'].get(key)
            elif hasattr(status, key):
                value = getattr(status, key)
            
            if value is not None:
                # Normalize numeric values
                if isinstance(value, (int, float)):
                    normalized[key] = float(value)
                else:
                    normalized[key] = value
        
        return normalized


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])