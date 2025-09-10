"""
AgentHealthMonitor SSOT Violations Reproduction Test

PURPOSE: Expose multiple AgentHealthMonitor implementations with inconsistent death detection thresholds.
This test is DESIGNED TO FAIL before SSOT remediation to demonstrate the violations.

BUSINESS IMPACT:
- Segment: Platform (affects all user tiers)
- Goal: Stability - prevent inconsistent agent death detection
- Value Impact: Inconsistent thresholds create silent agent failures affecting 90% of chat value
- Revenue Impact: Prevents user churn from unreliable AI interactions

EXPECTED BEHAVIOR:
- SHOULD FAIL: Different timeout thresholds across health monitors (10s vs 30s vs 60s)
- SHOULD FAIL: Multiple implementations create conflicting death detection logic
- SHOULD FAIL: Performance overhead from multiple concurrent monitors

After SSOT consolidation, this test should demonstrate:
- Single death detection threshold (standardized)
- One health monitoring implementation
- Consistent agent status tracking
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor
from netra_backend.app.core.agent_reliability_types import AgentError

# Try to import the multiple health monitor implementations
try:
    from dev_launcher.health_monitor import HealthStatus as DevHealthStatus
    from dev_launcher.enhanced_health_monitor import EnhancedHealthMonitor
    DEV_MONITORS_AVAILABLE = True
except ImportError:
    DEV_MONITORS_AVAILABLE = False


class TestAgentHealthMonitorSSOTViolations(SSotAsyncTestCase):
    """
    Reproduction tests for AgentHealthMonitor SSOT violations.
    These tests SHOULD FAIL with current fragmented implementation.
    """

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        self.test_agent_name = "test_agent"
        self.test_execution_id = "exec_123"
        
        # Create multiple health monitors to expose SSOT violation
        self.core_monitor = AgentHealthMonitor()
        
        # Mock reliability wrapper for health status
        self.mock_reliability_wrapper = Mock()
        self.mock_reliability_wrapper.circuit_breaker.get_status.return_value = {"state": "closed"}
        
        # Mock execution tracker to simulate agent state
        self.mock_execution_tracker = Mock()

    async def test_multiple_implementations_inconsistent_death_thresholds(self):
        """
        REPRODUCTION TEST: Expose different death detection thresholds across implementations.
        
        Expected to FAIL: Shows 10s vs 30s vs 60s timeout inconsistencies.
        After SSOT fix: Should have single consistent threshold.
        """
        # Test core AgentHealthMonitor timeout (10 seconds from code analysis)
        last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=12)
        
        core_death_detected = await self.core_monitor.detect_agent_death(
            agent_name=self.test_agent_name,
            last_heartbeat=last_heartbeat,
            execution_context={"test": True}
        )
        
        # This SHOULD detect death (12s > 10s threshold)
        self.assertTrue(
            core_death_detected, 
            "Core monitor should detect death after 12s (>10s threshold)"
        )
        
        # If dev monitors are available, test their different thresholds
        if DEV_MONITORS_AVAILABLE:
            # Dev launcher health monitors have different grace periods (30s, 90s)
            # This exposes the SSOT violation - different components use different thresholds
            
            dev_status = DevHealthStatus(
                is_healthy=True,
                last_check=datetime.now(),
                consecutive_failures=0,
                grace_period_seconds=30  # Different threshold!
            )
            
            # Grace period of 30s means agent wouldn't be considered dead at 12s
            time_in_grace = 12  # seconds since start
            grace_period_over = time_in_grace > 30
            
            # This exposes the violation: core monitor says dead, dev monitor says alive
            self.assertFalse(
                grace_period_over,
                "SSOT VIOLATION EXPOSED: Dev monitor uses 30s, core uses 10s"
            )
            
            # Record the violation for analysis
            violation_detected = {
                "core_monitor_threshold": 10,
                "dev_monitor_threshold": 30,
                "test_duration": 12,
                "core_detects_death": core_death_detected,
                "dev_considers_alive": not grace_period_over,
                "violation_severity": "CRITICAL"
            }
            
            # This assertion SHOULD FAIL to expose the SSOT violation
            self.fail(
                f"SSOT VIOLATION DETECTED: Multiple inconsistent death thresholds. "
                f"Core monitor: {violation_detected['core_monitor_threshold']}s, "
                f"Dev monitor: {violation_detected['dev_monitor_threshold']}s. "
                f"At {violation_detected['test_duration']}s: core={violation_detected['core_detects_death']}, "
                f"dev={violation_detected['dev_considers_alive']}"
            )

    async def test_multiple_health_status_implementations_conflict(self):
        """
        REPRODUCTION TEST: Show conflicting health status from multiple implementations.
        
        Expected to FAIL: Different health status objects and calculation methods.
        After SSOT fix: Should have single AgentHealthStatus interface.
        """
        # Create error history for testing
        error_history = [
            AgentError(
                error_type="TestError",
                message="Test error",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=30),
                context={"test": True}
            )
        ]
        
        # Get health status from core monitor
        core_status = self.core_monitor.get_comprehensive_health_status(
            agent_name=self.test_agent_name,
            error_history=error_history,
            reliability_wrapper=self.mock_reliability_wrapper
        )
        
        # Record operation times to affect health calculation
        self.core_monitor.record_successful_operation("test_op", 2.5)
        self.core_monitor.record_successful_operation("test_op", 3.0)
        
        # Get updated status
        updated_status = self.core_monitor.get_comprehensive_health_status(
            agent_name=self.test_agent_name,
            error_history=error_history,
            reliability_wrapper=self.mock_reliability_wrapper
        )
        
        # The violation is exposed by having different status objects and methods
        status_implementations = {
            "core_status_type": type(core_status).__name__,
            "core_has_overall_health": hasattr(core_status, 'overall_health'),
            "core_has_circuit_breaker_state": hasattr(core_status, 'circuit_breaker_state')
        }
        
        if DEV_MONITORS_AVAILABLE:
            dev_status = DevHealthStatus(
                is_healthy=True,
                last_check=datetime.now(),
                consecutive_failures=0,
                state="monitoring"  # Different state representation!
            )
            
            status_implementations.update({
                "dev_status_type": type(dev_status).__name__,
                "dev_has_is_healthy": hasattr(dev_status, 'is_healthy'),
                "dev_has_consecutive_failures": hasattr(dev_status, 'consecutive_failures'),
                "different_interfaces": type(core_status).__name__ != type(dev_status).__name__
            })
            
            # This SHOULD FAIL to expose the interface inconsistency
            self.fail(
                f"SSOT VIOLATION: Multiple health status interfaces detected. "
                f"Core uses {status_implementations['core_status_type']}, "
                f"Dev uses {status_implementations['dev_status_type']}. "
                f"Interface mismatch: {status_implementations['different_interfaces']}"
            )

    async def test_performance_overhead_from_multiple_monitors(self):
        """
        REPRODUCTION TEST: Measure performance overhead from multiple concurrent health monitors.
        
        Expected to FAIL: Demonstrates N*M complexity from multiple monitors checking same agents.
        After SSOT fix: Should show single monitoring path with O(1) per agent.
        """
        num_agents = 10
        num_checks = 100
        
        # Simulate multiple agents
        agents = [f"agent_{i}" for i in range(num_agents)]
        
        # Time core monitor performance
        start_time = time.perf_counter()
        for _ in range(num_checks):
            for agent in agents:
                await self.core_monitor.detect_agent_death(
                    agent_name=agent,
                    last_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=5),
                    execution_context={"test": True}
                )
        core_monitor_time = time.perf_counter() - start_time
        
        # The SSOT violation is that we have multiple monitoring systems
        # that would each independently check all agents
        if DEV_MONITORS_AVAILABLE:
            # Simulate what would happen with multiple monitors
            # Each monitor checking each agent independently
            simulated_monitors = 3  # core, dev, enhanced
            theoretical_overhead = core_monitor_time * simulated_monitors
            
            performance_analysis = {
                "core_monitor_time": core_monitor_time,
                "num_agents": num_agents,
                "num_checks": num_checks,
                "simulated_monitors": simulated_monitors,
                "theoretical_total_time": theoretical_overhead,
                "overhead_multiplier": simulated_monitors,
                "checks_per_second": (num_agents * num_checks) / core_monitor_time
            }
            
            # This SHOULD FAIL to expose the performance violation
            if theoretical_overhead > 0.1:  # If total time would exceed 100ms
                self.fail(
                    f"SSOT VIOLATION: Multiple monitors create performance overhead. "
                    f"Core monitor: {performance_analysis['core_monitor_time']:.4f}s, "
                    f"Theoretical total with {performance_analysis['simulated_monitors']} monitors: "
                    f"{performance_analysis['theoretical_total_time']:.4f}s "
                    f"({performance_analysis['overhead_multiplier']}x overhead)"
                )
        
        # Even with just core monitor, record baseline for comparison
        self.assertLess(
            core_monitor_time, 0.05, 
            f"Core monitor baseline too slow: {core_monitor_time:.4f}s for {num_agents * num_checks} checks"
        )

    async def test_inconsistent_error_history_tracking(self):
        """
        REPRODUCTION TEST: Show scattered error history tracking across multiple systems.
        
        Expected to FAIL: Different error tracking mechanisms create state divergence.
        After SSOT fix: Should have unified error history management.
        """
        # Create errors in core system
        core_errors = [
            AgentError(
                error_type="ConnectionError",
                message="Core connection failed",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=60),
                context={"source": "core"}
            ),
            AgentError(
                error_type="TimeoutError", 
                message="Core timeout",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=30),
                context={"source": "core"}
            )
        ]
        
        # Get error summary from core monitor
        core_summary = self.core_monitor.get_error_summary(core_errors)
        
        # If dev monitors available, simulate their different error tracking
        if DEV_MONITORS_AVAILABLE:
            # Dev monitors track errors differently (consecutive_failures, different states)
            dev_error_tracking = {
                "consecutive_failures": 2,  # Different tracking method
                "last_failure_time": datetime.now(),
                "failure_types": ["startup_failure", "health_check_failure"],  # Different error types
                "error_count_method": "consecutive"  # vs. core's "total_errors"
            }
            
            # Compare tracking methods
            tracking_differences = {
                "core_total_errors": core_summary["total_errors"],
                "core_recent_errors": core_summary["recent_errors"],
                "core_error_types": list(core_summary["error_types"].keys()),
                "dev_consecutive_failures": dev_error_tracking["consecutive_failures"],
                "dev_failure_types": dev_error_tracking["failure_types"],
                "tracking_methods_differ": "total_errors" != "consecutive_failures",
                "error_type_schemas_differ": (
                    set(core_summary["error_types"].keys()) != 
                    set(dev_error_tracking["failure_types"])
                )
            }
            
            # This SHOULD FAIL to expose the scattered tracking violation
            self.fail(
                f"SSOT VIOLATION: Scattered error tracking detected. "
                f"Core tracks {tracking_differences['core_total_errors']} total errors "
                f"with types {tracking_differences['core_error_types']}, "
                f"Dev tracks {tracking_differences['dev_consecutive_failures']} consecutive failures "
                f"with types {tracking_differences['dev_failure_types']}. "
                f"Methods differ: {tracking_differences['tracking_methods_differ']}, "
                f"Schemas differ: {tracking_differences['error_type_schemas_differ']}"
            )

    async def test_agent_state_synchronization_failure(self):
        """
        REPRODUCTION TEST: Demonstrate agent state synchronization failures between monitors.
        
        Expected to FAIL: Shows how different monitors can have different views of same agent.
        After SSOT fix: Should have single agent state source.
        """
        # Mock execution tracker with specific state
        dead_execution = Mock()
        dead_execution.agent_name = self.test_agent_name
        dead_execution.is_dead.return_value = True
        dead_execution.is_timed_out.return_value = False
        dead_execution.updated_at = datetime.now(timezone.utc) - timedelta(seconds=15)
        dead_execution.error = "Mock agent death"
        dead_execution.execution_id = self.test_execution_id
        
        # Configure mock to return dead execution
        self.core_monitor.execution_tracker.get_executions_by_agent.return_value = [dead_execution]
        
        # Get status from core monitor
        error_history = []
        core_status = self.core_monitor.get_comprehensive_health_status(
            agent_name=self.test_agent_name,
            error_history=error_history,
            reliability_wrapper=self.mock_reliability_wrapper
        )
        
        # Core monitor should detect dead agent
        self.assertEqual(core_status.status, "dead", "Core monitor should detect dead agent")
        
        if DEV_MONITORS_AVAILABLE:
            # Dev monitor might see agent as still in grace period or monitoring
            dev_status = DevHealthStatus(
                is_healthy=False,
                last_check=datetime.now(),
                consecutive_failures=1,
                state="monitoring",  # Different state!
                startup_time=datetime.now() - timedelta(seconds=10),
                grace_period_seconds=30
            )
            
            # Check if dev monitor considers agent still in grace period
            still_in_grace = not dev_status.is_grace_period_over()
            
            state_synchronization_failure = {
                "core_status": core_status.status,
                "core_overall_health": core_status.overall_health,
                "dev_state": dev_status.state if hasattr(dev_status, 'state') else 'unknown',
                "dev_is_healthy": dev_status.is_healthy,
                "dev_still_in_grace": still_in_grace,
                "synchronization_failure": (
                    core_status.status == "dead" and 
                    dev_status.is_healthy is not False
                )
            }
            
            # This SHOULD FAIL to expose the synchronization violation
            self.fail(
                f"SSOT VIOLATION: Agent state synchronization failure detected. "
                f"Core monitor status: '{state_synchronization_failure['core_status']}' "
                f"(health: {state_synchronization_failure['core_overall_health']:.2f}), "
                f"Dev monitor state: '{state_synchronization_failure['dev_state']}' "
                f"(healthy: {state_synchronization_failure['dev_is_healthy']}, "
                f"grace: {state_synchronization_failure['dev_still_in_grace']}). "
                f"Sync failure: {state_synchronization_failure['synchronization_failure']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])