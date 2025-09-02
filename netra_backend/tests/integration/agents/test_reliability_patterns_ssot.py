"""
Reliability Patterns SSOT Integration Test Suite

This test suite focuses on reliability pattern SSOT compliance at the integration level.
These tests verify that reliability management patterns work consistently across different
components and that there is truly unified reliability infrastructure being used.

CRITICAL: These tests are designed to FAIL in the current state where multiple reliability
implementations exist. They will PASS once proper SSOT consolidation is achieved.

Integration Test Focus:
1. Reliability manager consistency across agents
2. Error handling pattern uniformity
3. Health tracking integration and consistency
4. Retry logic coordination across components
5. Failure recovery behavior consistency
6. Monitoring and metrics collection uniformity
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.reliability import get_reliability_wrapper


class TestReliabilityManagerConsistency:
    """Test reliability manager consistency across different agent types."""
    
    @pytest.mark.asyncio
    async def test_reliability_manager_integration_consistency(self):
        """
        CRITICAL: Verify reliability manager integration is consistent across agents.
        
        Current State: SHOULD FAIL - Different reliability integration patterns
        Expected: All agents integrate with reliability manager identically
        """
        # Create agents with different names and configurations
        agents = [
            BaseAgent(name="DataAgent", enable_reliability=True),
            BaseAgent(name="TriageAgent", enable_reliability=True),
            BaseAgent(name="OptimizationAgent", enable_reliability=True)
        ]
        
        # Verify reliability manager integration consistency
        reliability_managers = []
        legacy_reliabilities = []
        
        for agent in agents:
            reliability_managers.append((agent.name, agent.reliability_manager))
            legacy_reliabilities.append((agent.name, agent.legacy_reliability))
        
        # ASSERTION: All agents should have reliability managers
        missing_reliability = [name for name, rm in reliability_managers if rm is None]
        assert len(missing_reliability) == 0, (
            f"SSOT VIOLATION: Agents missing reliability manager: {missing_reliability}. "
            f"All agents must have consistent reliability manager integration."
        )
        
        # ASSERTION: All agents should have legacy reliability for backward compatibility
        missing_legacy = [name for name, lr in legacy_reliabilities if lr is None]
        assert len(missing_legacy) == 0, (
            f"SSOT VIOLATION: Agents missing legacy reliability: {missing_legacy}. "
            f"Backward compatibility layer required for SSOT transition."
        )
        
        # Verify reliability manager types are consistent
        rm_types = [type(rm).__name__ for name, rm in reliability_managers if rm is not None]
        unique_rm_types = set(rm_types)
        
        assert len(unique_rm_types) == 1, (
            f"SSOT VIOLATION: Inconsistent reliability manager types across agents. "
            f"Found types: {unique_rm_types}. "
            f"All agents must use the same reliability manager implementation."
        )
    
    @pytest.mark.asyncio
    async def test_reliability_operation_execution_consistency(self):
        """
        CRITICAL: Verify reliability operation execution is consistent.
        
        Current State: SHOULD FAIL - Different execution patterns across agents
        Expected: All agents execute operations through reliability infrastructure identically
        """
        # Create multiple agents
        agents = [
            BaseAgent(name=f"TestAgent_{i}", enable_reliability=True)
            for i in range(3)
        ]
        
        # Create test operations with tracking
        execution_results = []
        
        async def tracked_operation(agent_name: str):
            execution_results.append(f"{agent_name}_executed")
            return f"success_from_{agent_name}"
        
        # Execute operations through each agent's reliability infrastructure
        operation_outcomes = []
        for agent in agents:
            try:
                result = await agent.execute_with_reliability(
                    lambda: tracked_operation(agent.name),
                    f"test_operation_{agent.name}",
                    timeout=2.0
                )
                operation_outcomes.append((agent.name, "success", result))
            except Exception as e:
                operation_outcomes.append((agent.name, "failure", str(e)))
        
        # ASSERTION: All operations should execute successfully through reliability layer
        failures = [outcome for outcome in operation_outcomes if outcome[1] == "failure"]
        assert len(failures) == 0, (
            f"SSOT VIOLATION: Reliability operation execution inconsistency. "
            f"Failed executions: {failures}. "
            f"All agents must execute operations through reliability infrastructure consistently."
        )
        
        # ASSERTION: All operations should have been tracked (executed exactly once each)
        expected_executions = {f"TestAgent_{i}_executed" for i in range(3)}
        actual_executions = set(execution_results)
        
        assert actual_executions == expected_executions, (
            f"SSOT VIOLATION: Operation execution tracking inconsistency. "
            f"Expected: {expected_executions}. "
            f"Actual: {actual_executions}. "
            f"Reliability infrastructure must track operations consistently."
        )
    
    @pytest.mark.asyncio
    async def test_reliability_error_handling_consistency(self):
        """
        CRITICAL: Verify error handling through reliability layer is consistent.
        
        Current State: SHOULD FAIL - Inconsistent error handling patterns
        Expected: All agents handle errors through reliability infrastructure identically
        """
        # Create agents for error handling test
        agents = [
            BaseAgent(name="ErrorTestAgent1", enable_reliability=True),
            BaseAgent(name="ErrorTestAgent2", enable_reliability=True)
        ]
        
        # Create operation that always fails
        failure_count = {'count': 0}
        
        async def failing_operation():
            failure_count['count'] += 1
            raise ConnectionError(f"Simulated connection error {failure_count['count']}")
        
        # Execute failing operations through reliability layer
        error_handling_results = []
        for agent in agents:
            try:
                result = await agent.execute_with_reliability(
                    failing_operation,
                    f"failing_operation_{agent.name}",
                    timeout=1.0
                )
                error_handling_results.append((agent.name, "unexpected_success", result))
            except Exception as e:
                error_type = type(e).__name__
                error_handling_results.append((agent.name, error_type, str(e)))
        
        # ASSERTION: Error handling should be consistent across agents
        error_types = [result[1] for result in error_handling_results]
        unique_error_types = set(error_types)
        
        assert len(unique_error_types) == 1, (
            f"SSOT VIOLATION: Inconsistent error handling across agents. "
            f"Error handling results: {error_handling_results}. "
            f"All agents must handle errors through reliability layer consistently."
        )
        
        # ASSERTION: Should not have unexpected successes
        unexpected_successes = [result for result in error_handling_results if result[1] == "unexpected_success"]
        assert len(unexpected_successes) == 0, (
            f"SSOT VIOLATION: Unexpected successful operations. "
            f"Reliability layer should handle failures consistently: {unexpected_successes}."
        )


class TestHealthTrackingIntegration:
    """Test health tracking integration consistency across reliability infrastructure."""
    
    @pytest.mark.asyncio
    async def test_health_status_consistency_across_agents(self):
        """
        CRITICAL: Verify health status reporting is consistent across agents.
        
        Current State: SHOULD FAIL - Different health status structures
        Expected: All agents report health status with consistent structure and content
        """
        # Create agents with different configurations
        agents = [
            BaseAgent(name="HealthAgent1", enable_reliability=True, enable_execution_engine=True),
            BaseAgent(name="HealthAgent2", enable_reliability=True, enable_execution_engine=False),
            BaseAgent(name="HealthAgent3", enable_reliability=False, enable_execution_engine=True)
        ]
        
        # Collect health status from all agents
        health_statuses = []
        for agent in agents:
            health_status = agent.get_health_status()
            health_statuses.append((agent.name, health_status))
        
        # ASSERTION: All health statuses should have consistent base structure
        required_base_fields = ['agent_name', 'state', 'overall_status']
        
        for agent_name, health_status in health_statuses:
            missing_fields = []
            for field in required_base_fields:
                if field not in health_status:
                    missing_fields.append(field)
            
            assert len(missing_fields) == 0, (
                f"SSOT VIOLATION: Agent {agent_name} missing required health fields: {missing_fields}. "
                f"Health status: {health_status}. "
                f"All agents must report consistent health status structure."
            )
        
        # Check for conditional fields based on configuration
        reliability_enabled_agents = [
            (name, status) for name, status in health_statuses 
            if name in ["HealthAgent1", "HealthAgent2"]  # These have reliability enabled
        ]
        
        for agent_name, health_status in reliability_enabled_agents:
            assert 'legacy_reliability' in health_status or 'reliability_status' in health_status, (
                f"SSOT VIOLATION: Agent {agent_name} with reliability enabled missing reliability health data. "
                f"Health status keys: {list(health_status.keys())}. "
                f"Reliability health tracking not properly integrated."
            )
    
    @pytest.mark.asyncio
    async def test_health_status_reliability_integration(self):
        """
        CRITICAL: Verify reliability components are properly integrated into health status.
        
        Current State: SHOULD FAIL - Reliability health not properly integrated
        Expected: Reliability manager health reflects in overall agent health
        """
        # Create agent with full reliability infrastructure
        agent = BaseAgent(
            name="ReliabilityHealthAgent", 
            enable_reliability=True, 
            enable_execution_engine=True
        )
        
        # Execute some operations to generate health data
        success_operation = AsyncMock(return_value="success")
        failure_operation = AsyncMock(side_effect=RuntimeError("test error"))
        
        # Mix of operations to create varied health state
        operations = [
            (success_operation, "success_test"),
            (failure_operation, "failure_test"),
            (success_operation, "success_test_2")
        ]
        
        for operation, op_name in operations:
            try:
                await agent.execute_with_reliability(operation, op_name, timeout=1.0)
            except Exception:
                pass  # Expected for failure operations
        
        # Get comprehensive health status
        health_status = agent.get_health_status()
        
        # ASSERTION: Reliability health should be reflected in overall status
        overall_status = health_status.get('overall_status')
        assert overall_status in ['healthy', 'degraded', 'unhealthy'], (
            f"SSOT VIOLATION: Invalid overall health status: {overall_status}. "
            f"Reliability integration must produce valid health assessment."
        )
        
        # ASSERTION: Should have reliability-specific health indicators
        reliability_indicators = ['legacy_reliability', 'modern_execution', 'monitoring']
        found_indicators = [
            indicator for indicator in reliability_indicators 
            if indicator in health_status
        ]
        
        assert len(found_indicators) > 0, (
            f"SSOT VIOLATION: No reliability health indicators found in health status. "
            f"Available keys: {list(health_status.keys())}. "
            f"Expected indicators: {reliability_indicators}. "
            f"Reliability components must contribute to health status."
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_health_integration(self):
        """
        CRITICAL: Verify circuit breaker health is integrated into reliability health.
        
        Current State: SHOULD FAIL - Circuit breaker health not properly integrated
        Expected: Circuit breaker status affects overall reliability health assessment
        """
        # Create agent with reliability infrastructure
        agent = BaseAgent(name="CBHealthAgent", enable_reliability=True)
        
        # Get initial health status
        initial_health = agent.get_health_status()
        initial_overall_status = initial_health.get('overall_status', 'unknown')
        
        # Get circuit breaker status separately
        cb_status = agent.get_circuit_breaker_status()
        
        # ASSERTION: Circuit breaker status should be accessible
        assert cb_status.get('status') != 'not_available', (
            f"SSOT VIOLATION: Circuit breaker status not accessible. "
            f"Circuit breaker status: {cb_status}. "
            f"Circuit breaker must be integrated with health monitoring."
        )
        
        # Force circuit breaker into unhealthy state by causing failures
        failure_operation = AsyncMock(side_effect=ConnectionError("Force circuit open"))
        
        # Execute enough failures to potentially affect circuit breaker state
        for _ in range(6):  # Exceed typical failure threshold
            try:
                await agent.execute_with_reliability(
                    failure_operation,
                    "force_failure_test",
                    timeout=0.5
                )
            except Exception:
                pass
        
        # Get health status after failures
        post_failure_health = agent.get_health_status()
        post_failure_overall_status = post_failure_health.get('overall_status', 'unknown')
        
        # Get circuit breaker status after failures
        post_failure_cb_status = agent.get_circuit_breaker_status()
        
        # ASSERTION: Circuit breaker state change should potentially affect overall health
        cb_state = post_failure_cb_status.get('state', 'unknown')
        
        if cb_state == 'OPEN':
            # If circuit breaker is open, health should reflect this
            assert post_failure_overall_status in ['degraded', 'unhealthy'], (
                f"SSOT VIOLATION: Circuit breaker OPEN but overall health unchanged. "
                f"Initial: {initial_overall_status}, Post-failure: {post_failure_overall_status}. "
                f"Circuit breaker state must influence overall health assessment."
            )
        
        # At minimum, reliability health data should be present and consistent
        reliability_health_keys = [
            key for key in post_failure_health.keys() 
            if 'reliability' in key.lower() or 'circuit' in key.lower()
        ]
        
        assert len(reliability_health_keys) > 0, (
            f"SSOT VIOLATION: No reliability health data in health status after operations. "
            f"Health keys: {list(post_failure_health.keys())}. "
            f"Reliability infrastructure must provide health data."
        )


class TestRetryLogicIntegration:
    """Test retry logic integration consistency across reliability components."""
    
    @pytest.mark.asyncio
    async def test_retry_behavior_consistency_across_agents(self):
        """
        CRITICAL: Verify retry behavior is consistent across different agents.
        
        Current State: SHOULD FAIL - Different retry behaviors across agents
        Expected: All agents retry operations using consistent patterns and configurations
        """
        # Create agents for retry testing
        agents = [
            BaseAgent(name=f"RetryAgent_{i}", enable_reliability=True)
            for i in range(3)
        ]
        
        # Create operation that fails predictably then succeeds
        attempt_counts = {}
        
        async def retry_test_operation(agent_name: str):
            if agent_name not in attempt_counts:
                attempt_counts[agent_name] = 0
            attempt_counts[agent_name] += 1
            
            # Fail first 2 attempts, succeed on 3rd
            if attempt_counts[agent_name] <= 2:
                raise TimeoutError(f"Attempt {attempt_counts[agent_name]} failed for {agent_name}")
            return f"success_on_attempt_{attempt_counts[agent_name]}_for_{agent_name}"
        
        # Execute retry operations through each agent
        retry_results = []
        for agent in agents:
            try:
                result = await agent.execute_with_reliability(
                    lambda: retry_test_operation(agent.name),
                    f"retry_test_{agent.name}",
                    timeout=5.0  # Allow time for retries
                )
                retry_results.append((agent.name, "success", result, attempt_counts[agent.name]))
            except Exception as e:
                retry_results.append((agent.name, "failure", str(e), attempt_counts.get(agent.name, 0)))
        
        # ASSERTION: All agents should have consistent retry behavior
        successful_retries = [result for result in retry_results if result[1] == "success"]
        
        assert len(successful_retries) == len(agents), (
            f"SSOT VIOLATION: Inconsistent retry behavior across agents. "
            f"Retry results: {retry_results}. "
            f"All agents should successfully retry operations with consistent pattern."
        )
        
        # ASSERTION: All agents should have made the same number of attempts
        attempt_counts_list = [result[3] for result in successful_retries]
        unique_attempt_counts = set(attempt_counts_list)
        
        assert len(unique_attempt_counts) == 1, (
            f"SSOT VIOLATION: Inconsistent retry attempt counts across agents. "
            f"Attempt counts: {attempt_counts_list}. "
            f"All agents must use consistent retry configuration and behavior."
        )
    
    @pytest.mark.asyncio
    async def test_retry_configuration_consistency(self):
        """
        CRITICAL: Verify retry configurations are consistent across reliability components.
        
        Current State: SHOULD FAIL - Different retry configurations
        Expected: All reliability components use same retry configuration
        """
        # Create different reliability components
        agent1 = BaseAgent(name="RetryConfigAgent1", enable_reliability=True)
        agent2 = BaseAgent(name="RetryConfigAgent2", enable_reliability=True)
        
        # Extract retry configurations from reliability managers
        rm1 = agent1.reliability_manager
        rm2 = agent2.reliability_manager
        
        # Check retry configurations
        retry_config_1 = None
        retry_config_2 = None
        
        if rm1 and hasattr(rm1, '_retry_config'):
            retry_config_1 = rm1._retry_config
        if rm2 and hasattr(rm2, '_retry_config'):
            retry_config_2 = rm2._retry_config
        
        # ASSERTION: Both agents should have retry configurations
        assert retry_config_1 is not None, (
            f"SSOT VIOLATION: Agent1 reliability manager missing retry configuration. "
            f"All reliability managers must have consistent retry configuration."
        )
        
        assert retry_config_2 is not None, (
            f"SSOT VIOLATION: Agent2 reliability manager missing retry configuration. "
            f"All reliability managers must have consistent retry configuration."
        )
        
        # Compare retry configuration parameters
        config_1_params = self._extract_retry_config_params(retry_config_1)
        config_2_params = self._extract_retry_config_params(retry_config_2)
        
        # ASSERTION: Retry configurations should be identical
        mismatched_params = []
        for param, value1 in config_1_params.items():
            value2 = config_2_params.get(param)
            if value1 != value2:
                mismatched_params.append((param, value1, value2))
        
        assert len(mismatched_params) == 0, (
            f"SSOT VIOLATION: Inconsistent retry configuration parameters. "
            f"Mismatched parameters: {mismatched_params}. "
            f"All retry configurations must be identical across components."
        )
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_consistency(self):
        """
        CRITICAL: Verify exponential backoff behavior is consistent.
        
        Current State: SHOULD FAIL - Different backoff implementations
        Expected: All retry operations use consistent exponential backoff algorithm
        """
        # Create agent for backoff testing
        agent = BaseAgent(name="BackoffAgent", enable_reliability=True)
        
        # Track timing of retry attempts
        attempt_times = []
        
        async def timed_failure_operation():
            attempt_times.append(time.time())
            if len(attempt_times) < 4:  # Fail first 3 attempts
                raise ConnectionError(f"Timed failure attempt {len(attempt_times)}")
            return "success_after_backoff"
        
        # Execute operation that will trigger retries with backoff
        start_time = time.time()
        try:
            result = await agent.execute_with_reliability(
                timed_failure_operation,
                "backoff_test_operation",
                timeout=30.0  # Allow time for backoff delays
            )
            end_time = time.time()
            
            # ASSERTION: Should have succeeded after retries
            assert result == "success_after_backoff", (
                f"SSOT VIOLATION: Retry with backoff did not succeed as expected. "
                f"Result: {result}. Backoff retry mechanism not working correctly."
            )
            
        except Exception as e:
            pytest.fail(
                f"SSOT VIOLATION: Retry operation failed unexpectedly: {e}. "
                f"Exponential backoff retry should have succeeded."
            )
        
        # ASSERTION: Should have made expected number of attempts
        expected_attempts = 4  # 3 failures + 1 success
        assert len(attempt_times) == expected_attempts, (
            f"SSOT VIOLATION: Unexpected number of retry attempts. "
            f"Expected: {expected_attempts}, Actual: {len(attempt_times)}. "
            f"Retry logic not behaving consistently."
        )
        
        # Check backoff timing (delays should increase exponentially)
        if len(attempt_times) >= 3:
            delay_1 = attempt_times[1] - attempt_times[0]
            delay_2 = attempt_times[2] - attempt_times[1]
            
            # Allow some tolerance for timing variations
            backoff_ratio = delay_2 / delay_1 if delay_1 > 0 else 0
            
            # Exponential backoff should roughly double the delay
            assert 1.5 <= backoff_ratio <= 3.0, (
                f"SSOT VIOLATION: Exponential backoff timing inconsistent. "
                f"First delay: {delay_1:.2f}s, Second delay: {delay_2:.2f}s, "
                f"Ratio: {backoff_ratio:.2f} (expected ~2.0). "
                f"Backoff algorithm not implementing exponential pattern correctly."
            )
    
    def _extract_retry_config_params(self, retry_config) -> Dict[str, Any]:
        """Extract retry configuration parameters for comparison."""
        params = {}
        
        if retry_config:
            # Extract common retry configuration parameters
            param_names = ['max_retries', 'base_delay', 'max_delay', 'backoff_factor']
            
            for param_name in param_names:
                if hasattr(retry_config, param_name):
                    params[param_name] = getattr(retry_config, param_name)
        
        return params


class TestReliabilityMonitoringConsistency:
    """Test reliability monitoring and metrics consistency."""
    
    @pytest.mark.asyncio
    async def test_reliability_metrics_collection_consistency(self):
        """
        CRITICAL: Verify reliability metrics collection is consistent across components.
        
        Current State: SHOULD FAIL - Inconsistent metrics collection
        Expected: All reliability components collect metrics using consistent patterns
        """
        # Create agents for metrics testing
        agents = [
            BaseAgent(name=f"MetricsAgent_{i}", enable_reliability=True)
            for i in range(2)
        ]
        
        # Execute operations to generate metrics
        operations = [
            (lambda: asyncio.sleep(0.1), "fast_operation"),  # Success
            (lambda: (_ for _ in ()).throw(RuntimeError("test error")), "error_operation"),  # Failure
            (lambda: "success", "simple_operation")  # Success
        ]
        
        # Execute operations through each agent
        for agent in agents:
            for operation, op_name in operations:
                try:
                    await agent.execute_with_reliability(
                        operation, f"{op_name}_{agent.name}", timeout=2.0
                    )
                except Exception:
                    pass  # Expected for error operations
        
        # Collect reliability health/metrics from each agent
        agent_metrics = []
        for agent in agents:
            health_status = agent.get_health_status()
            metrics = self._extract_reliability_metrics(health_status)
            agent_metrics.append((agent.name, metrics))
        
        # ASSERTION: All agents should have metrics with consistent structure
        metric_structures = []
        for agent_name, metrics in agent_metrics:
            if metrics:
                metric_keys = set(metrics.keys())
                metric_structures.append((agent_name, metric_keys))
        
        if len(metric_structures) > 1:
            # Check consistency of metrics structure across agents
            reference_structure = metric_structures[0][1]
            inconsistent_agents = []
            
            for agent_name, structure in metric_structures[1:]:
                if structure != reference_structure:
                    inconsistent_agents.append((agent_name, structure))
            
            assert len(inconsistent_agents) == 0, (
                f"SSOT VIOLATION: Inconsistent reliability metrics structure across agents. "
                f"Reference structure: {reference_structure}. "
                f"Inconsistent agents: {inconsistent_agents}. "
                f"All reliability components must collect metrics consistently."
            )
    
    @pytest.mark.asyncio
    async def test_reliability_monitoring_integration(self):
        """
        CRITICAL: Verify reliability monitoring is properly integrated across infrastructure.
        
        Current State: SHOULD FAIL - Monitoring not properly integrated
        Expected: Reliability monitoring provides consistent visibility across all components
        """
        # Create agent with full monitoring infrastructure
        agent = BaseAgent(
            name="MonitoringAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Execute operations to populate monitoring data
        success_count = 0
        failure_count = 0
        
        operations = [
            (lambda: "success_1", True),
            (lambda: "success_2", True),
            (lambda: (_ for _ in ()).throw(ValueError("monitored error")), False),
            (lambda: "success_3", True)
        ]
        
        for operation, should_succeed in operations:
            try:
                await agent.execute_with_reliability(operation, "monitoring_test", timeout=1.0)
                if should_succeed:
                    success_count += 1
            except Exception:
                if not should_succeed:
                    failure_count += 1
        
        # Get comprehensive monitoring data
        health_status = agent.get_health_status()
        
        # ASSERTION: Monitoring data should be integrated into health status
        monitoring_indicators = [
            'monitoring', 'modern_execution', 'legacy_reliability'
        ]
        
        found_monitoring = []
        for indicator in monitoring_indicators:
            if indicator in health_status:
                found_monitoring.append(indicator)
        
        assert len(found_monitoring) > 0, (
            f"SSOT VIOLATION: No monitoring data found in health status. "
            f"Available keys: {list(health_status.keys())}. "
            f"Expected monitoring indicators: {monitoring_indicators}. "
            f"Reliability monitoring must be integrated into health reporting."
        )
        
        # Verify monitoring reflects actual operations
        if 'modern_execution' in health_status:
            modern_data = health_status['modern_execution']
            if isinstance(modern_data, dict) and 'monitor' in modern_data:
                monitor_data = modern_data['monitor']
                
                # Should have some indication of operations executed
                operation_indicators = ['status', 'health', 'executions', 'operations']
                monitor_has_operations = any(
                    indicator in str(monitor_data).lower() 
                    for indicator in operation_indicators
                )
                
                assert monitor_has_operations, (
                    f"SSOT VIOLATION: Monitoring data does not reflect executed operations. "
                    f"Monitor data: {monitor_data}. "
                    f"Monitoring must track operational activity."
                )
    
    def _extract_reliability_metrics(self, health_status: Dict[str, Any]) -> Dict[str, Any]:
        """Extract reliability metrics from health status."""
        metrics = {}
        
        # Look for metrics in various health status locations
        if 'legacy_reliability' in health_status:
            legacy_data = health_status['legacy_reliability']
            if isinstance(legacy_data, dict):
                # Extract metrics from legacy reliability data
                metric_keys = ['success_count', 'failure_count', 'total_operations', 'health']
                for key in metric_keys:
                    if key in legacy_data:
                        metrics[f"legacy_{key}"] = legacy_data[key]
        
        if 'modern_execution' in health_status:
            modern_data = health_status['modern_execution']
            if isinstance(modern_data, dict):
                # Extract metrics from modern execution data
                for key, value in modern_data.items():
                    metrics[f"modern_{key}"] = value
        
        if 'monitoring' in health_status:
            monitoring_data = health_status['monitoring']
            if isinstance(monitoring_data, dict):
                for key, value in monitoring_data.items():
                    metrics[f"monitoring_{key}"] = value
        
        return metrics


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])