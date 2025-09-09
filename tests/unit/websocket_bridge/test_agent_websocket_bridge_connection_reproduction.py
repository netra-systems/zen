"""
Test AgentWebSocketBridge Connection Reproduction

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical)
- Business Goal: Protect $120K+ MRR from WebSocket connection failures
- Value Impact: Reproduces exact bridge connection failures causing agent event loss
- Strategic Impact: Critical for diagnosing WebSocket 1011 errors in GitHub Issue #117

This test suite reproduces the specific AgentWebSocketBridge connection issues
that cause WebSocket 1011 errors, missing agent events, and communication breakdowns.

@compliance CLAUDE.md - Real services over mocks for authentic testing
@compliance SPEC/core.xml - WebSocket bridge patterns and connection management
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase, require_docker_services

# CRITICAL: Import actual WebSocket bridge and connection components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge, 
    IntegrationState,
    IntegrationConfig, 
    HealthStatus,
    IntegrationResult,
    create_agent_websocket_bridge
)
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import get_env


class TestAgentWebSocketBridgeConnectionReproduction(BaseIntegrationTest):
    """
    Reproduce AgentWebSocketBridge connection failures that cause P1 critical issues.
    
    CRITICAL: These tests MUST fail initially to reproduce the exact connection
    and event delivery failures identified in GitHub Issue #117.
    """
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_initialization_failures(self):
        """
        REPRODUCTION TEST: AgentWebSocketBridge initialization failures.
        
        This reproduces initialization failures that cause the bridge to be
        None or improperly configured, leading to missing events.
        
        Expected to FAIL until remediation is complete.
        """
        initialization_failures = []
        
        # Test bridge creation with invalid configurations
        invalid_configs = [
            None,  # No config
            {},  # Empty config  
            {"invalid_field": "should_not_exist"},  # Invalid config fields
            IntegrationConfig(initialization_timeout_s=-1),  # Invalid timeout
            IntegrationConfig(health_check_interval_s=0),  # Invalid interval
        ]
        
        for i, config in enumerate(invalid_configs):
            try:
                # Try to create bridge with invalid config
                if config is None:
                    bridge = AgentWebSocketBridge()  # Default config
                elif isinstance(config, dict):
                    bridge = AgentWebSocketBridge(config=IntegrationConfig(**config))
                else:
                    bridge = AgentWebSocketBridge(config=config)
                
                # Check if bridge was created but is in invalid state
                if bridge.state == IntegrationState.FAILED:
                    initialization_failures.append(f"INITIALIZATION FAILURE: Config {i} created failed bridge")
                elif bridge.state == IntegrationState.UNINITIALIZED:
                    # This might be normal for some configs
                    continue
                else:
                    # Bridge created successfully with invalid config - potential issue
                    initialization_failures.append(f"POTENTIAL ISSUE: Invalid config {i} created working bridge")
                
            except (ValueError, TypeError, AttributeError) as e:
                # Expected failure for invalid configs
                continue
            except Exception as e:
                # Unexpected error during creation
                initialization_failures.append(f"UNEXPECTED INITIALIZATION ERROR: Config {i} - {e}")
        
        # Test bridge creation with valid config but missing dependencies
        try:
            # Create bridge without proper context or services
            bridge = AgentWebSocketBridge()
            
            # Try to initialize without proper dependencies
            result = await bridge.initialize()
            
            if result.success:
                initialization_failures.append("DEPENDENCY MISSING: Bridge initialized without proper dependencies")
            
        except Exception as e:
            # Expected failure - dependencies missing
            assert "dependency" in str(e).lower() or "not found" in str(e).lower() or "none" in str(e).lower()
        
        # Test create_agent_websocket_bridge factory function
        try:
            # Try to create bridge with invalid user context
            invalid_context = None
            bridge = create_agent_websocket_bridge(invalid_context)
            
            if bridge is not None:
                initialization_failures.append("FACTORY FAILURE: Bridge created with None context")
                
        except (ValueError, TypeError, AttributeError) as e:
            # Expected failure - invalid context
            pass
        except Exception as e:
            initialization_failures.append(f"FACTORY UNEXPECTED ERROR: {e}")
        
        # Report initialization failures
        if initialization_failures:
            pytest.fail(f"AgentWebSocketBridge initialization failures:\n" + "\n".join(initialization_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_connection_state_failures(self):
        """
        REPRODUCTION TEST: AgentWebSocketBridge connection state failures.
        
        This reproduces connection state issues that cause the bridge to report
        incorrect states, leading to silent failures and missing events.
        
        Expected to FAIL until remediation is complete.
        """
        connection_state_failures = []
        
        # Create user context for testing
        user_id = f"state_test_user_{uuid.uuid4().hex[:8]}"
        try:
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
        except Exception as e:
            pytest.fail(f"SETUP FAILURE: Could not create user context: {e}")
        
        # Test bridge state transitions
        try:
            bridge = create_agent_websocket_bridge(user_context)
            
            if bridge is None:
                connection_state_failures.append("BRIDGE CREATION FAILURE: Factory returned None bridge")
                return
            
            # Check initial state
            initial_state = bridge.state
            if initial_state != IntegrationState.UNINITIALIZED:
                connection_state_failures.append(f"INITIAL STATE WRONG: Expected UNINITIALIZED, got {initial_state}")
            
            # Try to initialize
            try:
                init_result = await bridge.initialize()
                
                if not init_result.success:
                    connection_state_failures.append(f"INITIALIZATION FAILED: {init_result.error}")
                
                # Check state after initialization
                post_init_state = bridge.state
                if init_result.success and post_init_state != IntegrationState.ACTIVE:
                    connection_state_failures.append(f"POST-INIT STATE WRONG: Expected ACTIVE, got {post_init_state}")
                
            except Exception as e:
                connection_state_failures.append(f"INITIALIZATION EXCEPTION: {e}")
            
            # Test health check state updates
            try:
                health_status = await bridge.check_health()
                
                if health_status.state != bridge.state:
                    connection_state_failures.append(f"HEALTH STATE MISMATCH: Bridge state {bridge.state}, health reports {health_status.state}")
                
                # Check for inconsistent health indicators
                if health_status.websocket_manager_healthy and not health_status.registry_healthy:
                    connection_state_failures.append("INCONSISTENT HEALTH: WebSocket healthy but registry unhealthy")
                elif not health_status.websocket_manager_healthy and health_status.state == IntegrationState.ACTIVE:
                    connection_state_failures.append("INCONSISTENT HEALTH: WebSocket unhealthy but state is ACTIVE")
                
            except Exception as e:
                connection_state_failures.append(f"HEALTH CHECK EXCEPTION: {e}")
            
            # Test forced state transitions
            try:
                # Try to force bridge into degraded state
                bridge.state = IntegrationState.DEGRADED
                
                # Health check should detect and potentially recover
                health_after_degraded = await bridge.check_health()
                
                if health_after_degraded.state == IntegrationState.DEGRADED and health_after_degraded.consecutive_failures == 0:
                    connection_state_failures.append("STATE INCONSISTENCY: Degraded state but no failures recorded")
                
            except Exception as e:
                connection_state_failures.append(f"STATE TRANSITION EXCEPTION: {e}")
                
        except Exception as e:
            connection_state_failures.append(f"BRIDGE SETUP EXCEPTION: {e}")
        
        # Report connection state failures
        if connection_state_failures:
            pytest.fail(f"AgentWebSocketBridge connection state failures:\n" + "\n".join(connection_state_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_event_emission_failures(self):
        """
        REPRODUCTION TEST: AgentWebSocketBridge event emission failures.
        
        This reproduces event emission failures that cause missing agent events,
        resulting in incomplete user experiences and timeout issues.
        
        Expected to FAIL until remediation is complete.
        """
        event_emission_failures = []
        
        # Create user context for event testing
        user_id = f"event_test_user_{uuid.uuid4().hex[:8]}"
        try:
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            bridge = create_agent_websocket_bridge(user_context)
            
            if bridge is None:
                pytest.fail("SETUP FAILURE: Could not create bridge for event testing")
                
        except Exception as e:
            pytest.fail(f"SETUP FAILURE: {e}")
        
        # Test all required agent event emissions
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for event_type in required_events:
            try:
                # Try to emit each event type
                emit_method_name = f"emit_{event_type}"
                
                if not hasattr(bridge, emit_method_name):
                    event_emission_failures.append(f"MISSING EVENT METHOD: Bridge missing {emit_method_name}")
                    continue
                
                emit_method = getattr(bridge, emit_method_name)
                
                if not callable(emit_method):
                    event_emission_failures.append(f"NON-CALLABLE EVENT METHOD: {emit_method_name} is not callable")
                    continue
                
                # Try to call the emit method
                test_data = {
                    "event_type": event_type,
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "test_data": f"test_{event_type}_data"
                }
                
                try:
                    # Call the emit method
                    if asyncio.iscoroutinefunction(emit_method):
                        result = await emit_method(test_data)
                    else:
                        result = emit_method(test_data)
                    
                    # Check if emission was successful
                    if result is False:
                        event_emission_failures.append(f"EVENT EMISSION FAILED: {event_type} emission returned False")
                    
                except Exception as e:
                    event_emission_failures.append(f"EVENT EMISSION EXCEPTION: {event_type} - {e}")
                
            except Exception as e:
                event_emission_failures.append(f"EVENT METHOD ACCESS EXCEPTION: {event_type} - {e}")
        
        # Test event ordering and sequencing
        try:
            # Emit events in wrong order to test validation
            wrong_order_events = [
                ("agent_completed", {"result": "premature completion"}),
                ("agent_started", {"task": "should have started first"}),
                ("tool_executing", {"tool": "out of order tool"}),
            ]
            
            sequence_errors = []
            
            for event_type, data in wrong_order_events:
                try:
                    emit_method = getattr(bridge, f"emit_{event_type}")
                    
                    if asyncio.iscoroutinefunction(emit_method):
                        await emit_method(data)
                    else:
                        emit_method(data)
                        
                except Exception as e:
                    # Expected - sequence validation should catch this
                    sequence_errors.append(f"{event_type}: {e}")
            
            # If no sequence errors occurred, we might have a validation issue
            if not sequence_errors:
                event_emission_failures.append("EVENT SEQUENCE VALIDATION MISSING: Wrong order events were accepted")
                
        except Exception as e:
            event_emission_failures.append(f"EVENT SEQUENCE TEST EXCEPTION: {e}")
        
        # Test event emission during bridge state issues
        try:
            # Force bridge into failed state
            bridge.state = IntegrationState.FAILED
            
            # Try to emit events while in failed state
            try:
                if hasattr(bridge, 'emit_agent_started'):
                    if asyncio.iscoroutinefunction(bridge.emit_agent_started):
                        await bridge.emit_agent_started({"test": "failed_state_emission"})
                    else:
                        bridge.emit_agent_started({"test": "failed_state_emission"})
                
                # If this succeeds, we have a state validation issue
                event_emission_failures.append("STATE VALIDATION MISSING: Events emitted while bridge in FAILED state")
                
            except Exception as e:
                # Expected - should not emit events while in failed state
                assert "failed" in str(e).lower() or "state" in str(e).lower()
                
        except Exception as e:
            event_emission_failures.append(f"FAILED STATE TEST EXCEPTION: {e}")
        
        # Report event emission failures
        if event_emission_failures:
            pytest.fail(f"AgentWebSocketBridge event emission failures:\n" + "\n".join(event_emission_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_recovery_failures(self):
        """
        REPRODUCTION TEST: AgentWebSocketBridge recovery failures.
        
        This reproduces recovery mechanism failures that prevent the bridge
        from recovering from errors, causing persistent connection issues.
        
        Expected to FAIL until remediation is complete.
        """
        recovery_failures = []
        
        # Create user context for recovery testing
        user_id = f"recovery_test_user_{uuid.uuid4().hex[:8]}"
        try:
            user_context = get_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            
            # Create bridge with recovery configuration
            recovery_config = IntegrationConfig(
                recovery_max_attempts=3,
                recovery_base_delay_s=0.1,  # Fast recovery for testing
                recovery_max_delay_s=1.0
            )
            
            bridge = AgentWebSocketBridge(config=recovery_config)
            
        except Exception as e:
            pytest.fail(f"RECOVERY TEST SETUP FAILURE: {e}")
        
        # Test recovery from failed initialization
        try:
            # Force initialization failure
            with patch.object(bridge, '_initialize_websocket_manager', side_effect=Exception("Simulated init failure")):
                init_result = await bridge.initialize()
                
                if init_result.success:
                    recovery_failures.append("RECOVERY ISSUE: Initialization reported success despite forced failure")
                
                # Bridge should be in failed state
                if bridge.state != IntegrationState.FAILED:
                    recovery_failures.append(f"RECOVERY STATE ISSUE: Expected FAILED state, got {bridge.state}")
                
                # Try recovery
                recovery_attempts = 0
                max_recovery_attempts = 3
                
                while recovery_attempts < max_recovery_attempts and bridge.state == IntegrationState.FAILED:
                    try:
                        # Remove the patch for recovery attempt
                        recovery_result = await bridge.recover()
                        
                        if recovery_result.success and bridge.state != IntegrationState.ACTIVE:
                            recovery_failures.append(f"RECOVERY STATE INCONSISTENCY: Recovery succeeded but state is {bridge.state}")
                        
                        recovery_attempts += 1
                        
                        if recovery_result.success:
                            break
                            
                    except Exception as e:
                        recovery_failures.append(f"RECOVERY ATTEMPT {recovery_attempts + 1} EXCEPTION: {e}")
                        recovery_attempts += 1
                
                if recovery_attempts >= max_recovery_attempts and bridge.state == IntegrationState.FAILED:
                    recovery_failures.append("RECOVERY EXHAUSTED: All recovery attempts failed")
                    
        except Exception as e:
            recovery_failures.append(f"RECOVERY TEST EXCEPTION: {e}")
        
        # Test recovery from degraded state
        try:
            # Simulate degraded state
            bridge.state = IntegrationState.DEGRADED
            
            # Record initial failure count
            initial_health = await bridge.check_health()
            initial_failures = initial_health.consecutive_failures
            
            # Trigger recovery
            recovery_result = await bridge.recover()
            
            if not recovery_result.success:
                recovery_failures.append(f"DEGRADED RECOVERY FAILED: {recovery_result.error}")
            
            # Check health after recovery
            post_recovery_health = await bridge.check_health()
            
            if post_recovery_health.consecutive_failures >= initial_failures:
                recovery_failures.append("RECOVERY FAILURE COUNT: Recovery did not reset failure count")
            
            if recovery_result.success and post_recovery_health.state != IntegrationState.ACTIVE:
                recovery_failures.append(f"RECOVERY STATE MISMATCH: Successful recovery but health shows {post_recovery_health.state}")
                
        except Exception as e:
            recovery_failures.append(f"DEGRADED RECOVERY TEST EXCEPTION: {e}")
        
        # Test recovery timeout handling
        try:
            # Set very short recovery timeout
            short_timeout_config = IntegrationConfig(
                recovery_base_delay_s=10.0,  # Long delay to trigger timeout
                recovery_max_delay_s=20.0
            )
            
            timeout_bridge = AgentWebSocketBridge(config=short_timeout_config)
            timeout_bridge.state = IntegrationState.FAILED
            
            # Try recovery with timeout
            start_time = time.time()
            
            try:
                recovery_task = asyncio.create_task(timeout_bridge.recover())
                recovery_result = await asyncio.wait_for(recovery_task, timeout=0.5)  # 500ms timeout
                
                recovery_time = time.time() - start_time
                
                if recovery_result.success and recovery_time > 0.4:
                    recovery_failures.append(f"RECOVERY TIMEOUT ISSUE: Recovery took {recovery_time:.3f}s but succeeded")
                    
            except asyncio.TimeoutError:
                recovery_time = time.time() - start_time
                recovery_failures.append(f"RECOVERY TIMEOUT: Recovery timed out after {recovery_time:.3f}s")
            
        except Exception as e:
            recovery_failures.append(f"RECOVERY TIMEOUT TEST EXCEPTION: {e}")
        
        # Report recovery failures
        if recovery_failures:
            pytest.fail(f"AgentWebSocketBridge recovery failures:\n" + "\n".join(recovery_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_multi_user_isolation_failures(self):
        """
        REPRODUCTION TEST: AgentWebSocketBridge multi-user isolation failures.
        
        This reproduces multi-user isolation failures that can cause cross-user
        event contamination and connection interference.
        
        Expected to FAIL until remediation is complete.
        """
        isolation_failures = []
        
        # Create multiple user contexts for isolation testing
        user_contexts = []
        bridges = []
        
        for i in range(3):
            user_id = f"isolation_user_{i}_{uuid.uuid4().hex[:6]}"
            try:
                context = get_user_execution_context(
                    user_id=user_id,
                    thread_id=f"thread_{i}_{uuid.uuid4().hex[:6]}",
                    run_id=f"run_{i}_{uuid.uuid4().hex[:6]}"
                )
                
                bridge = create_agent_websocket_bridge(context)
                
                if bridge is None:
                    isolation_failures.append(f"BRIDGE CREATION FAILURE: User {i} bridge is None")
                    continue
                
                user_contexts.append((user_id, context))
                bridges.append((user_id, bridge))
                
            except Exception as e:
                isolation_failures.append(f"USER {i} SETUP FAILURE: {e}")
        
        if len(bridges) < 2:
            pytest.fail("ISOLATION TEST SETUP FAILURE: Need at least 2 bridges for isolation testing")
        
        # Test concurrent bridge operations
        async def operate_bridge(user_id: str, bridge: AgentWebSocketBridge, operation_id: int):
            """Perform bridge operations for isolation testing."""
            try:
                results = {"user_id": user_id, "operation_id": operation_id, "events": []}
                
                # Initialize bridge
                init_result = await bridge.initialize()
                results["initialized"] = init_result.success
                
                if init_result.success:
                    # Emit test events
                    test_events = [
                        ("agent_started", {"task": f"isolation_test_{operation_id}"}),
                        ("agent_thinking", {"thought": f"processing_user_{operation_id}"}),
                        ("agent_completed", {"result": f"completed_for_user_{operation_id}"})
                    ]
                    
                    for event_type, data in test_events:
                        try:
                            emit_method = getattr(bridge, f"emit_{event_type}", None)
                            if emit_method and callable(emit_method):
                                if asyncio.iscoroutinefunction(emit_method):
                                    await emit_method(data)
                                else:
                                    emit_method(data)
                                results["events"].append(event_type)
                        except Exception as e:
                            results["events"].append(f"{event_type}_error: {e}")
                
                # Check health
                health = await bridge.check_health()
                results["health_state"] = health.state
                results["healthy"] = health.state == IntegrationState.ACTIVE
                
                return results
                
            except Exception as e:
                return {"user_id": user_id, "operation_id": operation_id, "error": str(e)}
        
        # Run concurrent operations
        try:
            tasks = [
                operate_bridge(user_id, bridge, i)
                for i, (user_id, bridge) in enumerate(bridges)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for isolation violations
            successful_results = [r for r in results if isinstance(r, dict) and not r.get("error")]
            
            if len(successful_results) != len(bridges):
                isolation_failures.append(f"CONCURRENT OPERATION FAILURES: Only {len(successful_results)}/{len(bridges)} operations succeeded")
            
            # Check for cross-user contamination
            user_events = {}
            for result in successful_results:
                user_id = result.get("user_id")
                events = result.get("events", [])
                user_events[user_id] = events
            
            # Verify each user only got their own events
            for user_id, events in user_events.items():
                for event in events:
                    if isinstance(event, str) and any(other_user in event for other_user in user_events.keys() if other_user != user_id):
                        isolation_failures.append(f"CROSS-USER CONTAMINATION: User {user_id} has events referencing other users")
            
            # Check health states are independent
            health_states = [r.get("health_state") for r in successful_results]
            if len(set(health_states)) == 1 and len(health_states) > 1:
                # All bridges have same health state - might indicate shared state
                isolation_failures.append(f"POTENTIAL SHARED STATE: All bridges have same health state: {health_states[0]}")
            
        except Exception as e:
            isolation_failures.append(f"CONCURRENT OPERATION EXCEPTION: {e}")
        
        # Test bridge cleanup isolation
        try:
            # Clean up one bridge and verify others are unaffected
            if len(bridges) >= 2:
                cleanup_user, cleanup_bridge = bridges[0]
                remaining_user, remaining_bridge = bridges[1]
                
                # Check remaining bridge health before cleanup
                pre_cleanup_health = await remaining_bridge.check_health()
                
                # Clean up first bridge
                try:
                    await cleanup_bridge.cleanup()
                except Exception as e:
                    isolation_failures.append(f"CLEANUP EXCEPTION: {e}")
                
                # Check remaining bridge health after cleanup
                post_cleanup_health = await remaining_bridge.check_health()
                
                if pre_cleanup_health.state != post_cleanup_health.state:
                    isolation_failures.append(f"CLEANUP ISOLATION VIOLATION: Other bridge health changed from {pre_cleanup_health.state} to {post_cleanup_health.state}")
                
        except Exception as e:
            isolation_failures.append(f"CLEANUP ISOLATION TEST EXCEPTION: {e}")
        
        # Report isolation failures
        if isolation_failures:
            pytest.fail(f"AgentWebSocketBridge multi-user isolation failures:\n" + "\n".join(isolation_failures))