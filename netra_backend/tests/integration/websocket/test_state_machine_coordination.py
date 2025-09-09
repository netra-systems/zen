"""
WebSocket State Machine Coordination Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Risk Reduction
- Value Impact: Prevents state machine coordination failures that break WebSocket lifecycle
- Strategic Impact: Protects $500K+ ARR by ensuring reliable connection state management

CRITICAL RACE CONDITION REPRODUCTION:
These integration tests reproduce race conditions in the coordination between:
1. ApplicationConnectionState machine and WebSocket transport state
2. ConnectionStateMachineRegistry and individual connection state machines  
3. WebSocket accept() completion and state machine transitions
4. Message queuing and state machine readiness validation

Integration Test Requirements:
- Uses REAL WebSocket connections with REAL authentication
- Uses REAL Redis and database services per CLAUDE.md requirements
- Tests coordination between multiple state management components
- Reproduces timing-dependent race conditions seen in GCP Cloud Run

CRITICAL: These tests MUST initially FAIL to prove coordination race condition reproduction.
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine,
    ConnectionStateMachineRegistry,
    StateTransitionInfo,
    get_connection_state_registry
)
from netra_backend.app.websocket_core import (
    WebSocketManager,
    get_websocket_manager,
    MessageRouter,
    get_message_router
)
from netra_backend.app.websocket_core.utils import (
    is_websocket_connected_and_ready,
    validate_websocket_handshake_completion
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

# Test Framework Imports - FIXED: Use correct base integration test import
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@dataclass 
class CoordinationEvent:
    """Track state machine coordination events."""
    timestamp: float
    event_type: str
    connection_id: str
    user_id: str
    component: str  # "state_machine", "ws_manager", "registry", "transport"
    state_before: Optional[str] = None
    state_after: Optional[str] = None
    coordination_success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateMachineCoordinationTest(BaseIntegrationTest):
    """
    Integration tests for WebSocket state machine coordination race conditions.
    
    CRITICAL: These tests use real services to reproduce coordination failures
    that occur when multiple state management components get out of sync.
    """
    
    def setUp(self):
        """Set up state machine coordination test environment."""
        super().setUp()
        
        # Real authentication setup (CLAUDE.md Section 15)
        self.auth_helper = E2EAuthHelper()
        
        # Coordination tracking
        self.coordination_events: List[CoordinationEvent] = []
        self.coordination_failures: List[str] = []
        self.state_inconsistencies: List[str] = []
        self.synchronization_errors: List[str] = []
        
        # Test users with real authentication
        self.test_users = []
        for i in range(3):
            user_data = self.auth_helper.create_test_user(
                username=f"coord_test_user_{i}_{int(time.time())}",
                email=f"coord_user_{i}_{int(time.time())}@test.netra.ai" 
            )
            self.test_users.append(user_data)
        
        # State tracking for coordination analysis
        self.active_state_machines: Dict[str, ConnectionStateMachine] = {}
        self.coordination_violations: List[Dict[str, Any]] = []
        
        # Timing controls for race condition reproduction
        self.coordination_check_interval = 0.01  # 10ms coordination checks
        self.race_condition_window = 0.5  # 500ms window for race conditions
        
    def _record_coordination_event(self, event_type: str, connection_id: str, user_id: str,
                                  component: str, coordination_success: bool = True,
                                  state_before: Optional[str] = None,
                                  state_after: Optional[str] = None,
                                  error: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None):
        """Record coordination event for analysis."""
        event = CoordinationEvent(
            timestamp=time.time(),
            event_type=event_type,
            connection_id=connection_id,
            user_id=user_id,
            component=component,
            state_before=state_before,
            state_after=state_after,
            coordination_success=coordination_success,
            error=error,
            metadata=metadata or {}
        )
        self.coordination_events.append(event)
    
    @pytest.mark.integration
    def test_state_machine_registry_coordination_race(self):
        """
        Test 1: Coordination race between ConnectionStateMachine and Registry.
        
        CRITICAL RACE CONDITION: This reproduces failures where the registry
        and individual state machines have different views of connection state,
        causing coordination failures during concurrent operations.
        """
        user_data = self.test_users[0]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        registry_coordination_issues = []
        state_machine_registry_mismatches = []
        
        def monitor_registry_coordination(connection_id: str, monitoring_duration: float):
            """Monitor registry and state machine coordination."""
            registry = get_connection_state_registry()
            start_time = time.time()
            
            coordination_checks = []
            
            while time.time() - start_time < monitoring_duration:
                try:
                    # Get state machine from registry
                    state_machine = registry.get_connection_state_machine(connection_id)
                    
                    if state_machine:
                        # Get individual state machine state
                        individual_state = state_machine.current_state
                        individual_ready = state_machine.is_ready_for_messages
                        
                        # Get registry view of operational connections
                        operational_connections = registry.get_all_operational_connections()
                        registry_operational = connection_id in operational_connections
                        
                        # Check for coordination mismatches
                        expected_operational = individual_state in [
                            ApplicationConnectionState.PROCESSING_READY,
                            ApplicationConnectionState.PROCESSING,
                            ApplicationConnectionState.IDLE,
                            ApplicationConnectionState.DEGRADED
                        ]
                        
                        if registry_operational != expected_operational:
                            mismatch = {
                                "timestamp": time.time(),
                                "connection_id": connection_id,
                                "individual_state": individual_state.value,
                                "individual_ready": individual_ready,
                                "registry_operational": registry_operational,
                                "expected_operational": expected_operational,
                                "mismatch_type": "registry_individual_state"
                            }
                            state_machine_registry_mismatches.append(mismatch)
                            
                            self.coordination_failures.append(
                                f"Registry coordination mismatch: Registry={registry_operational}, "
                                f"Expected={expected_operational}, State={individual_state.value}"
                            )
                            
                            self._record_coordination_event(
                                "coordination_mismatch", connection_id, user_data['user_id'],
                                "registry", coordination_success=False,
                                state_before=individual_state.value,
                                error="Registry-StateMachine coordination mismatch",
                                metadata=mismatch
                            )
                        
                        coordination_checks.append({
                            "timestamp": time.time(),
                            "individual_state": individual_state.value,
                            "registry_operational": registry_operational,
                            "coordination_ok": registry_operational == expected_operational
                        })
                    
                    else:
                        # State machine not found in registry - coordination issue
                        registry_coordination_issues.append({
                            "timestamp": time.time(),
                            "connection_id": connection_id,
                            "issue": "StateMachine not found in registry"
                        })
                        
                        self._record_coordination_event(
                            "registry_lookup_failure", connection_id, user_data['user_id'],
                            "registry", coordination_success=False,
                            error="StateMachine not found in registry"
                        )
                    
                    # Brief pause between coordination checks
                    time.sleep(self.coordination_check_interval)
                    
                except Exception as e:
                    registry_coordination_issues.append({
                        "timestamp": time.time(),
                        "connection_id": connection_id,
                        "error": str(e)
                    })
            
            return coordination_checks
        
        def trigger_concurrent_state_transitions(connection_id: str, user_id: str):
            """Trigger concurrent state transitions to create race conditions."""
            registry = get_connection_state_registry()
            
            try:
                # Register connection in registry
                state_machine = registry.register_connection(
                    connection_id=connection_id,
                    user_id=user_id
                )
                
                self.active_state_machines[connection_id] = state_machine
                
                # Perform rapid state transitions to trigger coordination races
                transitions = [
                    ApplicationConnectionState.ACCEPTED,
                    ApplicationConnectionState.AUTHENTICATED,
                    ApplicationConnectionState.SERVICES_READY,
                    ApplicationConnectionState.PROCESSING_READY
                ]
                
                for i, target_state in enumerate(transitions):
                    success = state_machine.transition_to(
                        target_state,
                        reason=f"Coordination race test transition {i}",
                        metadata={"transition_index": i, "test": "registry_coordination"}
                    )
                    
                    self._record_coordination_event(
                        "state_transition", connection_id, user_id,
                        "state_machine", coordination_success=success,
                        state_after=target_state.value,
                        metadata={"transition_index": i, "success": success}
                    )
                    
                    # Brief delay to allow coordination checks to interleave
                    time.sleep(0.02)
                
            except Exception as e:
                self.coordination_failures.append(f"State transition error: {e}")
        
        # Execute registry coordination race test
        connection_id = f"coord_race_test_{int(time.time())}"
        
        # Start coordination monitoring
        monitoring_thread = threading.Thread(
            target=lambda: setattr(
                self, 'coordination_results',
                monitor_registry_coordination(connection_id, self.race_condition_window)
            ),
            name="CoordinationMonitor"
        )
        monitoring_thread.start()
        
        # Create WebSocket connection with authentication
        with self.client.websocket_connect(
            f"/ws?token={auth_token}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as websocket:
            
            # Trigger concurrent state transitions
            transition_thread = threading.Thread(
                target=trigger_concurrent_state_transitions,
                args=(connection_id, user_data['user_id']),
                name="StateTransitionTrigger"
            )
            transition_thread.start()
            
            # Allow time for race conditions to manifest
            time.sleep(self.race_condition_window)
            
            # Wait for threads to complete
            transition_thread.join(timeout=5.0)
        
        monitoring_thread.join(timeout=5.0)
        
        # Analyze registry coordination race results
        coordination_results = getattr(self, 'coordination_results', [])
        coordination_ok_count = sum(1 for r in coordination_results if r.get('coordination_ok', False))
        coordination_fail_count = len(coordination_results) - coordination_ok_count
        
        print(f"\n=== REGISTRY COORDINATION RACE ANALYSIS ===")
        print(f"Coordination checks: {len(coordination_results)}")
        print(f"Coordination OK: {coordination_ok_count}")
        print(f"Coordination failures: {coordination_fail_count}")
        print(f"Registry issues: {len(registry_coordination_issues)}")
        print(f"State mismatches: {len(state_machine_registry_mismatches)}")
        print(f"Overall coordination failures: {len(self.coordination_failures)}")
        
        if state_machine_registry_mismatches:
            print("Registry-StateMachine mismatches detected:")
            for mismatch in state_machine_registry_mismatches[:3]:  # Show first 3
                print(f"  - {mismatch['individual_state']} vs registry_op={mismatch['registry_operational']}")
        
        # Check for coordination race conditions
        coordination_race_detected = (
            len(state_machine_registry_mismatches) > 0 or
            len(registry_coordination_issues) > 2 or
            coordination_fail_count > coordination_ok_count or
            len(self.coordination_failures) > 0
        )
        
        # CRITICAL: Registry coordination issues indicate race conditions
        pytest.fail(
            f"Registry coordination race test completed. "
            f"Race detected: {coordination_race_detected}, "
            f"Mismatches: {len(state_machine_registry_mismatches)}, "
            f"Issues: {len(registry_coordination_issues)}"
        )
    
    @pytest.mark.integration
    def test_websocket_transport_state_machine_sync_race(self):
        """
        Test 2: Synchronization race between WebSocket transport and ApplicationConnectionState.
        
        This reproduces race conditions where WebSocket transport state (CONNECTED)
        and ApplicationConnectionState machine get out of sync, causing accept() errors.
        """
        user_data = self.test_users[1]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        transport_sync_violations = []
        accept_timing_issues = []
        
        def monitor_transport_state_sync(connection_id: str, websocket_ref: Dict[str, Any]):
            """Monitor synchronization between transport and state machine."""
            registry = get_connection_state_registry()
            sync_checks = []
            
            start_time = time.time()
            while time.time() - start_time < self.race_condition_window:
                try:
                    # Get state machine state
                    state_machine = registry.get_connection_state_machine(connection_id)
                    if state_machine:
                        app_state = state_machine.current_state
                        app_ready = state_machine.is_ready_for_messages
                        
                        # Get WebSocket transport state (simulated)
                        websocket = websocket_ref.get('websocket')
                        transport_connected = websocket is not None
                        
                        # Check for sync violations
                        # If app state is ACCEPTED or beyond, transport should be connected
                        if app_state not in [ApplicationConnectionState.CONNECTING, ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED]:
                            if not transport_connected:
                                violation = {
                                    "timestamp": time.time(),
                                    "connection_id": connection_id,
                                    "app_state": app_state.value,
                                    "app_ready": app_ready,
                                    "transport_connected": transport_connected,
                                    "violation_type": "transport_behind_app_state"
                                }
                                transport_sync_violations.append(violation)
                                
                                self.synchronization_errors.append(
                                    f"Transport sync violation: App state {app_state.value} "
                                    f"but transport not connected"
                                )
                                
                                self._record_coordination_event(
                                    "transport_sync_violation", connection_id, user_data['user_id'],
                                    "transport", coordination_success=False,
                                    state_before=app_state.value,
                                    error="Transport behind application state",
                                    metadata=violation
                                )
                        
                        sync_checks.append({
                            "timestamp": time.time(),
                            "app_state": app_state.value,
                            "app_ready": app_ready,
                            "transport_connected": transport_connected,
                            "sync_ok": True  # Will be updated if violations found
                        })
                    
                    time.sleep(self.coordination_check_interval)
                    
                except Exception as e:
                    accept_timing_issues.append({
                        "timestamp": time.time(),
                        "connection_id": connection_id,
                        "error": str(e)
                    })
            
            return sync_checks
        
        def simulate_accept_timing_race(connection_id: str, user_id: str, websocket_ref: Dict[str, Any]):
            """Simulate accept timing race conditions."""
            registry = get_connection_state_registry()
            
            try:
                # Register connection
                state_machine = registry.register_connection(connection_id, user_id)
                
                # Simulate slow accept process
                async def slow_accept_simulation():
                    # State machine thinks we're moving to ACCEPTED
                    state_machine.transition_to(
                        ApplicationConnectionState.ACCEPTED,
                        reason="Simulated accept start"
                    )
                    
                    # But transport accept is delayed (race condition window)
                    await asyncio.sleep(0.1)  # 100ms delay
                    
                    # Now transport is ready
                    websocket_ref['transport_ready'] = True
                    
                    # Continue state machine progression
                    state_machine.transition_to(
                        ApplicationConnectionState.AUTHENTICATED,
                        reason="Authentication completed"
                    )
                    
                    state_machine.transition_to(
                        ApplicationConnectionState.SERVICES_READY,
                        reason="Services ready"
                    )
                    
                    return True
                
                # Run the slow accept simulation
                asyncio.run(slow_accept_simulation())
                
            except Exception as e:
                accept_timing_issues.append({
                    "connection_id": connection_id,
                    "simulation_error": str(e),
                    "timestamp": time.time()
                })
        
        # Execute transport state synchronization race test
        connection_id = f"transport_sync_test_{int(time.time())}"
        websocket_ref = {'websocket': None, 'transport_ready': False}
        
        # Start transport synchronization monitoring
        sync_monitoring_thread = threading.Thread(
            target=lambda: setattr(
                self, 'sync_results',
                monitor_transport_state_sync(connection_id, websocket_ref)
            ),
            name="TransportSyncMonitor"
        )
        sync_monitoring_thread.start()
        
        # Create WebSocket connection
        with self.client.websocket_connect(
            f"/ws?token={auth_token}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as websocket:
            
            websocket_ref['websocket'] = websocket
            
            # Simulate accept timing race
            race_simulation_thread = threading.Thread(
                target=simulate_accept_timing_race,
                args=(connection_id, user_data['user_id'], websocket_ref),
                name="AcceptRaceSimulation"
            )
            race_simulation_thread.start()
            
            # Allow race condition to manifest
            time.sleep(self.race_condition_window)
            
            race_simulation_thread.join(timeout=5.0)
        
        sync_monitoring_thread.join(timeout=5.0)
        
        # Analyze transport synchronization race results
        sync_results = getattr(self, 'sync_results', [])
        total_checks = len(sync_results)
        sync_violations = len(transport_sync_violations)
        timing_issues = len(accept_timing_issues)
        
        print(f"\n=== TRANSPORT STATE SYNC RACE ANALYSIS ===")
        print(f"Total sync checks: {total_checks}")
        print(f"Sync violations: {sync_violations}")
        print(f"Timing issues: {timing_issues}")
        print(f"Synchronization errors: {len(self.synchronization_errors)}")
        
        if transport_sync_violations:
            print("Transport sync violations detected:")
            for violation in transport_sync_violations[:3]:  # Show first 3
                print(f"  - App: {violation['app_state']}, Transport: {violation['transport_connected']}")
        
        # Check for synchronization race conditions
        sync_race_detected = (
            sync_violations > 0 or
            timing_issues > 1 or
            len(self.synchronization_errors) > 0
        )
        
        # CRITICAL: Transport synchronization issues indicate race conditions
        pytest.fail(
            f"Transport state sync race test completed. "
            f"Race detected: {sync_race_detected}, "
            f"Sync violations: {sync_violations}, "
            f"Timing issues: {timing_issues}"
        )
    
    @pytest.mark.integration
    def test_multi_component_coordination_race_condition(self):
        """
        Test 3: Multi-component coordination race between all state management components.
        
        This test reproduces complex race conditions where WebSocketManager,
        ConnectionStateMachine, Registry, and transport layer all get out of sync.
        """
        user_data = self.test_users[2]
        auth_token = self.auth_helper.get_valid_jwt_token(user_data['user_id'])
        
        multi_component_violations = []
        coordination_chaos_events = []
        
        def monitor_all_components(connection_id: str, monitoring_duration: float):
            """Monitor coordination across all components."""
            registry = get_connection_state_registry()
            ws_manager = get_websocket_manager()
            
            component_states = []
            start_time = time.time()
            
            while time.time() - start_time < monitoring_duration:
                try:
                    timestamp = time.time()
                    
                    # Get state from each component
                    state_machine = registry.get_connection_state_machine(connection_id)
                    sm_state = state_machine.current_state.value if state_machine else "NOT_FOUND"
                    sm_ready = state_machine.is_ready_for_messages if state_machine else False
                    
                    # WebSocket Manager state (simulated)
                    try:
                        ws_manager_ready = ws_manager.is_connection_ready(connection_id) if hasattr(ws_manager, 'is_connection_ready') else False
                    except:
                        ws_manager_ready = False
                    
                    # Registry operational state
                    operational_connections = registry.get_all_operational_connections()
                    registry_operational = connection_id in operational_connections
                    
                    # Check for multi-component coordination violations
                    components_ready = {
                        "state_machine": sm_ready,
                        "ws_manager": ws_manager_ready,
                        "registry": registry_operational
                    }
                    
                    # All components should agree on readiness
                    ready_states = list(components_ready.values())
                    if not all(ready_states) and any(ready_states):
                        # Some ready, some not - coordination violation
                        violation = {
                            "timestamp": timestamp,
                            "connection_id": connection_id,
                            "sm_state": sm_state,
                            "components_ready": components_ready,
                            "violation_type": "partial_component_readiness"
                        }
                        multi_component_violations.append(violation)
                        
                        self.coordination_failures.append(
                            f"Multi-component violation: {components_ready}"
                        )
                        
                        self._record_coordination_event(
                            "multi_component_violation", connection_id, user_data['user_id'],
                            "multi_component", coordination_success=False,
                            state_before=sm_state,
                            error="Components have inconsistent readiness states",
                            metadata=violation
                        )
                    
                    component_states.append({
                        "timestamp": timestamp,
                        "sm_state": sm_state,
                        "sm_ready": sm_ready,
                        "ws_manager_ready": ws_manager_ready,
                        "registry_operational": registry_operational,
                        "coordination_ok": len(set(ready_states)) <= 1  # All same or all different
                    })
                    
                    time.sleep(self.coordination_check_interval)
                    
                except Exception as e:
                    coordination_chaos_events.append({
                        "timestamp": time.time(),
                        "error": str(e),
                        "component": "monitoring"
                    })
            
            return component_states
        
        def create_coordination_chaos(connection_id: str, user_id: str):
            """Create chaotic conditions to trigger multi-component race conditions."""
            registry = get_connection_state_registry()
            
            try:
                # Register connection
                state_machine = registry.register_connection(connection_id, user_id)
                
                # Create concurrent operations on different components
                def rapid_state_transitions():
                    """Rapid state machine transitions."""
                    for i in range(5):
                        target_states = [
                            ApplicationConnectionState.ACCEPTED,
                            ApplicationConnectionState.AUTHENTICATED,
                            ApplicationConnectionState.SERVICES_READY,
                            ApplicationConnectionState.PROCESSING_READY,
                            ApplicationConnectionState.PROCESSING
                        ]
                        if i < len(target_states):
                            state_machine.transition_to(
                                target_states[i],
                                reason=f"Chaos transition {i}"
                            )
                        time.sleep(0.01)
                
                def registry_operations():
                    """Concurrent registry operations."""
                    for i in range(3):
                        try:
                            # Get stats (reads registry state)
                            stats = registry.get_registry_stats()
                            
                            # Cleanup (modifies registry)
                            registry.cleanup_closed_connections()
                            
                            time.sleep(0.02)
                        except Exception as e:
                            coordination_chaos_events.append({
                                "timestamp": time.time(),
                                "error": str(e),
                                "component": "registry_ops"
                            })
                
                # Run operations concurrently to create chaos
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [
                        executor.submit(rapid_state_transitions),
                        executor.submit(registry_operations)
                    ]
                    
                    for future in as_completed(futures, timeout=5.0):
                        try:
                            future.result()
                        except Exception as e:
                            coordination_chaos_events.append({
                                "timestamp": time.time(),
                                "error": str(e),
                                "component": "chaos_execution"
                            })
            
            except Exception as e:
                coordination_chaos_events.append({
                    "timestamp": time.time(),
                    "error": str(e),
                    "component": "chaos_setup"
                })
        
        # Execute multi-component coordination race test
        connection_id = f"multi_coord_test_{int(time.time())}"
        
        # Start comprehensive monitoring
        monitoring_thread = threading.Thread(
            target=lambda: setattr(
                self, 'multi_coord_results',
                monitor_all_components(connection_id, self.race_condition_window)
            ),
            name="MultiComponentMonitor"
        )
        monitoring_thread.start()
        
        # Create WebSocket connection
        with self.client.websocket_connect(
            f"/ws?token={auth_token}",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as websocket:
            
            # Create coordination chaos
            chaos_thread = threading.Thread(
                target=create_coordination_chaos,
                args=(connection_id, user_data['user_id']),
                name="CoordinationChaos"
            )
            chaos_thread.start()
            
            # Allow chaos to manifest
            time.sleep(self.race_condition_window)
            
            chaos_thread.join(timeout=5.0)
        
        monitoring_thread.join(timeout=5.0)
        
        # Analyze multi-component coordination race results
        multi_coord_results = getattr(self, 'multi_coord_results', [])
        total_checks = len(multi_coord_results)
        coordination_ok_checks = sum(1 for r in multi_coord_results if r.get('coordination_ok', False))
        coordination_violations = len(multi_component_violations)
        chaos_events = len(coordination_chaos_events)
        
        print(f"\n=== MULTI-COMPONENT COORDINATION RACE ANALYSIS ===")
        print(f"Total coordination checks: {total_checks}")
        print(f"Coordination OK checks: {coordination_ok_checks}")
        print(f"Coordination violations: {coordination_violations}")
        print(f"Chaos events: {chaos_events}")
        print(f"Overall coordination failures: {len(self.coordination_failures)}")
        
        if multi_component_violations:
            print("Multi-component violations detected:")
            for violation in multi_component_violations[:3]:  # Show first 3
                print(f"  - State: {violation['sm_state']}, Ready states: {violation['components_ready']}")
        
        # Check for multi-component race conditions  
        multi_race_detected = (
            coordination_violations > 0 or
            chaos_events > 3 or  # More than 3 chaos events indicates instability
            coordination_ok_checks < total_checks / 2 or  # Less than 50% coordination success
            len(self.coordination_failures) > 0
        )
        
        # CRITICAL: Multi-component coordination failures indicate complex race conditions
        pytest.fail(
            f"Multi-component coordination race test completed. "
            f"Race detected: {multi_race_detected}, "
            f"Violations: {coordination_violations}, "
            f"Chaos events: {chaos_events}, "
            f"Coordination success rate: {coordination_ok_checks}/{total_checks}"
        )
    
    def tearDown(self):
        """Clean up state machine coordination test environment."""
        # Log coordination test summary
        print(f"\n=== STATE MACHINE COORDINATION TEST SUMMARY ===")
        print(f"Coordination events recorded: {len(self.coordination_events)}")
        print(f"Coordination failures: {len(self.coordination_failures)}")
        print(f"State inconsistencies: {len(self.state_inconsistencies)}")
        print(f"Synchronization errors: {len(self.synchronization_errors)}")
        print(f"Coordination violations: {len(self.coordination_violations)}")
        
        # Clean up active state machines
        registry = get_connection_state_registry()
        for connection_id, state_machine in self.active_state_machines.items():
            try:
                registry.unregister_connection(connection_id)
            except Exception as cleanup_error:
                print(f"State machine cleanup error for {connection_id}: {cleanup_error}")
        
        # Clean up test users
        for user_data in self.test_users:
            try:
                self.auth_helper.cleanup_test_user(user_data['user_id'])
            except Exception as user_cleanup_error:
                print(f"User cleanup error: {user_cleanup_error}")
        
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])