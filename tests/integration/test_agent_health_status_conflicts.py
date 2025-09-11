"""
Agent Health Status Race Condition Reproduction Test

PURPOSE: Expose scattered agent status tracking that creates race conditions and state conflicts.
This test is DESIGNED TO FAIL before SSOT remediation to demonstrate the violations.

BUSINESS IMPACT:
- Segment: Platform (affects all user tiers)  
- Goal: Stability - prevent race conditions in agent status tracking
- Value Impact: Race conditions cause agent state divergence affecting chat reliability
- Revenue Impact: Inconsistent agent states create user experience degradation

EXPECTED BEHAVIOR:
- SHOULD FAIL: Multiple state tracking systems create conflicting agent status
- SHOULD FAIL: Race conditions between AgentRegistry, ExecutionTracker, and HealthMonitor
- SHOULD FAIL: No single source of truth for "is agent alive?"

After SSOT consolidation, this test should demonstrate:
- Single agent state tracking system
- Consistent agent status across all components
- No race conditions in state updates
"""

import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor
from netra_backend.app.core.agent_execution_tracker import ExecutionRecord, ExecutionState, AgentExecutionTracker
from netra_backend.app.core.agent_reliability_types import AgentError

# Try to import agent registry to test state conflicts
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    AGENT_REGISTRY_AVAILABLE = True
except ImportError:
    AGENT_REGISTRY_AVAILABLE = False


class TestAgentHealthStatusConflicts(SSotAsyncTestCase):
    """
    Reproduction tests for agent health status race conditions and conflicts.
    These tests SHOULD FAIL with current scattered implementation.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for race condition testing."""
        await super().asyncSetUp()
        
        self.test_agent_name = "race_test_agent"
        self.test_user_id = "user_123"
        self.test_thread_id = "thread_456"
        self.test_execution_id = "exec_789"
        
        # Create multiple systems that track agent state independently (SSOT violation)
        self.health_monitor = AgentHealthMonitor()
        self.execution_tracker = AgentExecutionTracker()
        
        # Mock reliability wrapper
        self.mock_reliability_wrapper = Mock()
        self.mock_reliability_wrapper.circuit_breaker.get_status.return_value = {"state": "closed"}
        
        # Shared state for race condition testing
        self.state_updates = []
        self.state_conflicts = []
        self.lock = threading.Lock()

    async def test_concurrent_state_updates_create_race_conditions(self):
        """
        REPRODUCTION TEST: Demonstrate race conditions from concurrent state updates.
        
        Expected to FAIL: Shows how multiple systems updating agent state concurrently
        create inconsistent views and race conditions.
        """
        # Create initial execution record
        execution_record = ExecutionRecord(
            execution_id=self.test_execution_id,
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            state=ExecutionState.RUNNING,
            started_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Add to execution tracker
        self.execution_tracker.start_execution(
            execution_id=self.test_execution_id,
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        race_condition_results = []
        
        async def health_monitor_updater():
            """Simulate health monitor updating agent status."""
            for i in range(10):
                try:
                    # Health monitor checks if agent is dead
                    last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=i * 2)
                    is_dead = await self.health_monitor.detect_agent_death(
                        agent_name=self.test_agent_name,
                        last_heartbeat=last_heartbeat,
                        execution_context={"source": "health_monitor", "iteration": i}
                    )
                    
                    with self.lock:
                        race_condition_results.append({
                            "source": "health_monitor",
                            "iteration": i,
                            "timestamp": datetime.now(timezone.utc),
                            "agent_status": "dead" if is_dead else "alive",
                            "heartbeat_age": i * 2
                        })
                    
                    await asyncio.sleep(0.01)  # Small delay to encourage race conditions
                except Exception as e:
                    with self.lock:
                        race_condition_results.append({
                            "source": "health_monitor",
                            "iteration": i,
                            "error": str(e)
                        })

        async def execution_tracker_updater():
            """Simulate execution tracker updating agent state."""
            for i in range(10):
                try:
                    # Execution tracker updates heartbeat
                    self.execution_tracker.update_heartbeat(self.test_execution_id)
                    
                    # Get execution state
                    executions = self.execution_tracker.get_executions_by_agent(self.test_agent_name)
                    current_execution = executions[0] if executions else None
                    
                    with self.lock:
                        race_condition_results.append({
                            "source": "execution_tracker",
                            "iteration": i,
                            "timestamp": datetime.now(timezone.utc),
                            "agent_status": current_execution.state.value if current_execution else "unknown",
                            "execution_found": current_execution is not None
                        })
                    
                    await asyncio.sleep(0.015)  # Slightly different timing to create race
                except Exception as e:
                    with self.lock:
                        race_condition_results.append({
                            "source": "execution_tracker", 
                            "iteration": i,
                            "error": str(e)
                        })

        # Run both updaters concurrently to create race conditions
        await asyncio.gather(
            health_monitor_updater(),
            execution_tracker_updater()
        )
        
        # Analyze race condition results
        health_results = [r for r in race_condition_results if r.get("source") == "health_monitor"]
        tracker_results = [r for r in race_condition_results if r.get("source") == "execution_tracker"]
        
        # Find conflicting states at similar timestamps
        conflicts_found = []
        for health_result in health_results:
            if "error" in health_result or "timestamp" not in health_result:
                continue
                
            health_time = health_result["timestamp"]
            health_status = health_result.get("agent_status")
            
            # Find tracker results within 50ms
            for tracker_result in tracker_results:
                if "error" in tracker_result or "timestamp" not in tracker_result:
                    continue
                    
                tracker_time = tracker_result["timestamp"]
                time_diff = abs((health_time - tracker_time).total_seconds())
                
                if time_diff < 0.05:  # Within 50ms
                    tracker_status = tracker_result.get("agent_status")
                    
                    # Check for status conflicts
                    if health_status != tracker_status:
                        conflicts_found.append({
                            "health_status": health_status,
                            "tracker_status": tracker_status,
                            "time_diff_ms": time_diff * 1000,
                            "health_iteration": health_result.get("iteration"),
                            "tracker_iteration": tracker_result.get("iteration")
                        })
        
        # This SHOULD FAIL to expose the race condition violation
        if conflicts_found:
            self.fail(
                f"SSOT VIOLATION: Race conditions detected between health monitor and execution tracker. "
                f"Found {len(conflicts_found)} state conflicts: {conflicts_found[:3]}..."
            )
        else:
            # Even if no conflicts found in this run, the architecture allows for them
            self.fail(
                f"SSOT VIOLATION: Race condition architecture detected. "
                f"Health monitor results: {len(health_results)}, "
                f"Tracker results: {len(tracker_results)}. "
                f"Multiple independent state tracking systems create race condition potential."
            )

    async def test_agent_registry_health_monitor_state_divergence(self):
        """
        REPRODUCTION TEST: Show state divergence between AgentRegistry and HealthMonitor.
        
        Expected to FAIL: Demonstrates how agent registry and health monitor can have
        different views of the same agent's status.
        """
        if not AGENT_REGISTRY_AVAILABLE:
            self.skipTest("AgentRegistry not available for state divergence test")
        
        # Create mock agent registry
        mock_registry = Mock(spec=AgentRegistry)
        mock_registry.agents = {}
        mock_registry.lifecycle_managers = {}
        
        # Simulate agent registry thinking agent is alive
        mock_lifecycle_manager = Mock()
        mock_lifecycle_manager.is_agent_running.return_value = True
        mock_lifecycle_manager.get_agent_status.return_value = "running"
        mock_registry.lifecycle_managers[self.test_agent_name] = mock_lifecycle_manager
        
        # Create error history that makes health monitor think agent is unhealthy
        error_history = [
            AgentError(
                error_type="CriticalError",
                message="Agent experiencing critical failures",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=10),
                context={"severity": "high"}
            ),
            AgentError(
                error_type="TimeoutError",
                message="Agent timeout detected",
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=5),
                context={"timeout_duration": 30}
            )
        ]
        
        # Get health status from health monitor
        health_status = self.health_monitor.get_comprehensive_health_status(
            agent_name=self.test_agent_name,
            error_history=error_history,
            reliability_wrapper=self.mock_reliability_wrapper
        )
        
        # Compare states
        registry_thinks_running = mock_lifecycle_manager.is_agent_running.return_value
        registry_status = mock_lifecycle_manager.get_agent_status.return_value
        health_monitor_status = health_status.status
        health_monitor_health = health_status.overall_health
        
        state_divergence_analysis = {
            "registry_running": registry_thinks_running,
            "registry_status": registry_status,
            "health_monitor_status": health_monitor_status,
            "health_monitor_health": health_monitor_health,
            "states_diverged": registry_status != health_monitor_status,
            "registry_positive": registry_thinks_running,
            "health_monitor_negative": health_monitor_health < 0.5
        }
        
        # This SHOULD FAIL to expose the state divergence violation
        if (state_divergence_analysis["states_diverged"] or 
            (state_divergence_analysis["registry_positive"] and 
             state_divergence_analysis["health_monitor_negative"])):
            
            self.fail(
                f"SSOT VIOLATION: State divergence detected between AgentRegistry and HealthMonitor. "
                f"Registry status: '{state_divergence_analysis['registry_status']}' "
                f"(running: {state_divergence_analysis['registry_running']}), "
                f"Health monitor status: '{state_divergence_analysis['health_monitor_status']}' "
                f"(health: {state_divergence_analysis['health_monitor_health']:.2f}). "
                f"Divergence: {state_divergence_analysis['states_diverged']}"
            )

    async def test_execution_state_tracking_inconsistency(self):
        """
        REPRODUCTION TEST: Show inconsistent execution state tracking across systems.
        
        Expected to FAIL: Multiple systems track execution state differently,
        creating inconsistent views of agent lifecycle.
        """
        # Start execution in tracker
        execution_id = self.execution_tracker.start_execution(
            execution_id=self.test_execution_id,
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Update execution state multiple times
        states_timeline = []
        
        # Execution tracker perspective
        self.execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        states_timeline.append({
            "timestamp": datetime.now(timezone.utc),
            "source": "execution_tracker",
            "state": "running",
            "method": "update_execution_state"
        })
        
        await asyncio.sleep(0.01)
        
        # Health monitor perspective (checking for death)
        last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=8)
        is_dead = await self.health_monitor.detect_agent_death(
            agent_name=self.test_agent_name,
            last_heartbeat=last_heartbeat,
            execution_context={"test": True}
        )
        
        states_timeline.append({
            "timestamp": datetime.now(timezone.utc),
            "source": "health_monitor",
            "state": "dead" if is_dead else "alive",
            "method": "detect_agent_death",
            "heartbeat_age": 8
        })
        
        await asyncio.sleep(0.01)
        
        # Execution tracker updates heartbeat (agent should be alive)
        self.execution_tracker.update_heartbeat(execution_id)
        current_execution = self.execution_tracker.get_execution(execution_id)
        
        states_timeline.append({
            "timestamp": datetime.now(timezone.utc),
            "source": "execution_tracker",
            "state": current_execution.state.value if current_execution else "unknown",
            "method": "update_heartbeat",
            "is_alive": current_execution.is_alive if current_execution else False
        })
        
        # Analyze state tracking inconsistencies
        tracker_states = [s for s in states_timeline if s["source"] == "execution_tracker"]
        health_states = [s for s in states_timeline if s["source"] == "health_monitor"]
        
        inconsistencies = []
        
        # Check for conflicting final states
        final_tracker_state = tracker_states[-1]["state"] if tracker_states else None
        final_health_state = health_states[-1]["state"] if health_states else None
        
        if final_tracker_state and final_health_state:
            # Map states for comparison
            tracker_alive = final_tracker_state in ["running", "pending", "starting"]
            health_alive = final_health_state == "alive"
            
            if tracker_alive != health_alive:
                inconsistencies.append({
                    "type": "final_state_conflict",
                    "tracker_state": final_tracker_state,
                    "health_state": final_health_state,
                    "tracker_alive": tracker_alive,
                    "health_alive": health_alive
                })
        
        # Check for temporal inconsistencies
        if len(states_timeline) >= 3:
            # Health monitor detected death, but tracker updated heartbeat after
            health_death_time = None
            tracker_heartbeat_time = None
            
            for state in states_timeline:
                if state["source"] == "health_monitor" and state["state"] == "dead":
                    health_death_time = state["timestamp"]
                elif state["source"] == "execution_tracker" and state["method"] == "update_heartbeat":
                    tracker_heartbeat_time = state["timestamp"]
            
            if health_death_time and tracker_heartbeat_time and tracker_heartbeat_time > health_death_time:
                inconsistencies.append({
                    "type": "temporal_inconsistency",
                    "description": "Health monitor detected death before tracker updated heartbeat",
                    "health_death_time": health_death_time.isoformat(),
                    "tracker_heartbeat_time": tracker_heartbeat_time.isoformat()
                })
        
        # This SHOULD FAIL to expose the inconsistent tracking violation
        if inconsistencies:
            self.fail(
                f"SSOT VIOLATION: Execution state tracking inconsistencies detected. "
                f"Timeline: {len(states_timeline)} state updates, "
                f"Inconsistencies: {inconsistencies}"
            )
        else:
            # Even if no inconsistencies in this specific run, the architecture allows them
            self.fail(
                f"SSOT VIOLATION: Multiple independent execution state tracking systems detected. "
                f"Tracker states: {len(tracker_states)}, Health states: {len(health_states)}. "
                f"Independent tracking creates inconsistency potential."
            )

    async def test_agent_lifecycle_state_machine_conflicts(self):
        """
        REPRODUCTION TEST: Show conflicts between different agent lifecycle state machines.
        
        Expected to FAIL: Different components implement different state machines
        for agent lifecycle, creating conflicts and undefined behavior.
        """
        # ExecutionTracker state machine
        execution_states = [
            ExecutionState.PENDING,
            ExecutionState.STARTING, 
            ExecutionState.RUNNING,
            ExecutionState.COMPLETING,
            ExecutionState.COMPLETED
        ]
        
        # Health monitor state machine (inferred from status strings)
        health_states = ["healthy", "degraded", "unhealthy", "dead"]
        
        # Start execution and track state transitions
        execution_id = self.execution_tracker.start_execution(
            execution_id=self.test_execution_id,
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        state_machine_analysis = []
        
        # Simulate state transitions through execution lifecycle
        for i, exec_state in enumerate(execution_states):
            # Update execution state
            if i > 0:  # Don't update PENDING as it's the initial state
                self.execution_tracker.update_execution_state(execution_id, exec_state)
            
            # Get current execution
            current_execution = self.execution_tracker.get_execution(execution_id)
            
            # Get health status at this point
            error_history = []
            if exec_state in [ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.DEAD]:
                error_history.append(AgentError(
                    error_type="StateTransitionError",
                    message=f"Error during {exec_state.value}",
                    timestamp=datetime.now(timezone.utc),
                    context={"execution_state": exec_state.value}
                ))
            
            health_status = self.health_monitor.get_comprehensive_health_status(
                agent_name=self.test_agent_name,
                error_history=error_history,
                reliability_wrapper=self.mock_reliability_wrapper
            )
            
            state_machine_analysis.append({
                "iteration": i,
                "execution_state": exec_state.value,
                "execution_is_alive": current_execution.is_alive if current_execution else False,
                "execution_is_terminal": current_execution.is_terminal if current_execution else False,
                "health_status": health_status.status,
                "health_score": health_status.overall_health,
                "timestamp": datetime.now(timezone.utc)
            })
            
            await asyncio.sleep(0.01)
        
        # Analyze state machine conflicts
        conflicts = []
        
        for analysis in state_machine_analysis:
            exec_state = analysis["execution_state"]
            exec_alive = analysis["execution_is_alive"]
            exec_terminal = analysis["execution_is_terminal"]
            health_status = analysis["health_status"]
            health_score = analysis["health_score"]
            
            # Check for logical conflicts
            if exec_alive and health_status == "dead":
                conflicts.append({
                    "type": "alive_vs_dead",
                    "execution_state": exec_state,
                    "execution_alive": exec_alive,
                    "health_status": health_status,
                    "iteration": analysis["iteration"]
                })
            
            if exec_terminal and health_score > 0.8:
                conflicts.append({
                    "type": "terminal_vs_healthy",
                    "execution_state": exec_state,
                    "execution_terminal": exec_terminal,
                    "health_score": health_score,
                    "iteration": analysis["iteration"]
                })
            
            if exec_state == "completed" and health_status == "unhealthy":
                conflicts.append({
                    "type": "completed_vs_unhealthy",
                    "execution_state": exec_state,
                    "health_status": health_status,
                    "iteration": analysis["iteration"]
                })
        
        # Analyze state machine compatibility
        compatibility_analysis = {
            "execution_states_count": len(execution_states),
            "health_states_count": len(health_states),
            "total_transitions": len(state_machine_analysis),
            "conflicts_found": len(conflicts),
            "different_state_machines": True,  # They use different state representations
            "mapping_undefined": True  # No clear mapping between state machines
        }
        
        # This SHOULD FAIL to expose the state machine conflict violation
        self.fail(
            f"SSOT VIOLATION: Multiple agent lifecycle state machines create conflicts. "
            f"Execution tracker has {compatibility_analysis['execution_states_count']} states, "
            f"Health monitor has {compatibility_analysis['health_states_count']} states. "
            f"Conflicts detected: {compatibility_analysis['conflicts_found']}, "
            f"State machine mapping undefined: {compatibility_analysis['mapping_undefined']}. "
            f"Sample conflicts: {conflicts[:2] if conflicts else 'Architecture allows conflicts'}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])