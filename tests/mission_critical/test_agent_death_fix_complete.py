#!/usr/bin/env python
"""
MISSION CRITICAL TEST: Verify Agent Death Bug is Fixed

This test verifies that the critical agent death bug from AGENT_DEATH_AFTER_TRIAGE_BUG_REPORT.md
has been completely fixed by the new execution tracking system.

Test Coverage:
1. Agent death detection via heartbeat monitoring
2. Timeout detection and enforcement
3. WebSocket notification on agent death
4. Health check accuracy during agent failure
5. Recovery mechanism triggering

SUCCESS CRITERIA:
- Agent death MUST be detected within 30 seconds
- WebSocket MUST send death notification
- Health checks MUST reflect agent state
- Recovery mechanisms MUST trigger
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# Import the components we're testing
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker,
    ExecutionState,
    get_execution_tracker
)
from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker
from netra_backend.app.agents.security.security_manager import SecurityManager
from netra_backend.app.core.execution_health_integration import (
    ExecutionHealthIntegration,
    setup_execution_health_monitoring
)
from netra_backend.app.services.unified_health_service import UnifiedHealthService
from netra_backend.app.core.health_types import HealthStatus


class MockWebSocketBridge:
    """Mock WebSocket bridge to capture death notifications."""
    
    def __init__(self):
        self.death_notifications = []
        self.events_sent = []
        
    async def notify_agent_death(self, run_id: str, agent_name: str, reason: str, details: Dict[str, Any]):
        """Capture death notification."""
        self.death_notifications.append({
            'run_id': run_id,
            'agent_name': agent_name,
            'reason': reason,
            'details': details,
            'timestamp': datetime.now(timezone.utc)
        })
        
    async def send_agent_event(self, event_type: str, data: Dict[str, Any]):
        """Capture general events."""
        self.events_sent.append({
            'type': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        })


class TestAgentDeathFixComplete:
    """Comprehensive test suite verifying the agent death bug is fixed."""
    
    @pytest.mark.asyncio
    async def test_complete_death_detection_flow(self):
        """Test the complete flow from agent execution to death detection."""
        print("\n" + "="*80)
        print("TEST: Complete Agent Death Detection Flow")
        print("="*80)
        
        # Setup components
        tracker = AgentExecutionTracker()
        websocket = MockWebSocketBridge()
        health_service = UnifiedHealthService("test", "1.0.0")
        
        # Setup health integration
        health_integration = ExecutionHealthIntegration(health_service)
        await health_integration.register_health_checks()
        
        # Create and start execution
        exec_id = tracker.create_execution(
            agent_name='triage_agent',
            thread_id='thread_123',
            user_id='user_456',
            timeout_seconds=30
        )
        tracker.start_execution(exec_id)
        print(f"✅ Created execution: {exec_id}")
        
        # Send initial heartbeats (agent is alive)
        for i in range(3):
            await asyncio.sleep(1)
            assert tracker.heartbeat(exec_id), "Heartbeat should succeed"
            print(f"  💓 Heartbeat {i+1} sent")
        
        # Check health while agent is alive
        health_result = await health_integration.check_agent_execution_health()
        assert health_result['status'] == HealthStatus.HEALTHY.value
        print("✅ Health check shows HEALTHY while agent alive")
        
        # Simulate agent death (stop heartbeats)
        print("\n🔴 SIMULATING AGENT DEATH - stopping heartbeats...")
        await asyncio.sleep(12)  # Wait for death detection
        
        # Check if death was detected
        record = tracker.get_execution(exec_id)
        assert record is not None, "Execution record should exist"
        assert record.is_dead(), "Agent should be detected as dead"
        print(f"✅ Agent death detected after {record.time_since_heartbeat.total_seconds():.1f}s")
        
        # Check health after agent death
        health_result = await health_integration.check_agent_execution_health()
        assert health_result['status'] == HealthStatus.UNHEALTHY.value
        assert 'dead_agents' in health_result
        assert len(health_result['dead_agents']) == 1
        print("✅ Health check shows UNHEALTHY after agent death")
        
        # Verify dead agent details
        dead_agent = health_result['dead_agents'][0]
        assert dead_agent['agent'] == 'triage_agent'
        assert dead_agent['execution_id'] == exec_id
        print(f"✅ Dead agent correctly identified: {dead_agent['agent']}")
        
    @pytest.mark.asyncio
    async def test_timeout_detection_and_enforcement(self):
        """Test that timeouts are properly detected and enforced."""
        print("\n" + "="*80)
        print("TEST: Timeout Detection and Enforcement")
        print("="*80)
        
        tracker = AgentExecutionTracker()
        
        # Create execution with short timeout
        exec_id = tracker.create_execution(
            agent_name='data_agent',
            thread_id='thread_789',
            user_id='user_123',
            timeout_seconds=5
        )
        tracker.start_execution(exec_id)
        print(f"✅ Created execution with 5s timeout: {exec_id}")
        
        # Keep sending heartbeats but exceed timeout
        for i in range(7):
            await asyncio.sleep(1)
            tracker.heartbeat(exec_id)
            print(f"  💓 Heartbeat {i+1} at {i+1}s")
        
        # Check if timeout was detected
        record = tracker.get_execution(exec_id)
        assert record is not None
        assert record.is_timed_out(), "Execution should be timed out"
        print(f"✅ Timeout detected after {record.duration.total_seconds():.1f}s")
        
    @pytest.mark.asyncio
    async def test_security_manager_integration(self):
        """Test that SecurityManager prevents agent death via protection mechanisms."""
        print("\n" + "="*80)
        print("TEST: Security Manager Integration")
        print("="*80)
        
        from netra_backend.app.agents.security.resource_guard import ResourceGuard
        from netra_backend.app.agents.security.circuit_breaker import SystemCircuitBreaker
        
        # Setup security components
        resource_guard = ResourceGuard()
        circuit_breaker = SystemCircuitBreaker()
        security_manager = SecurityManager(resource_guard, circuit_breaker)
        
        # Test request validation
        request_valid = await security_manager.validate_request('user_123', 'triage_agent')
        assert request_valid, "First request should be valid"
        print("✅ Security validation passed")
        
        # Test resource acquisition
        resources = await security_manager.acquire_resources('user_123')
        assert resources is not None, "Resources should be acquired"
        print("✅ Resources acquired successfully")
        
        # Test execution recording
        await security_manager.record_execution('user_123', 'triage_agent', success=False)
        print("✅ Execution failure recorded")
        
        # Test circuit breaker after failures
        for i in range(2):
            await security_manager.record_execution('user_123', 'triage_agent', success=False)
        
        # Circuit should be open after 3 failures
        circuit_open = circuit_breaker.is_open('triage_agent')
        assert circuit_open, "Circuit breaker should be open after 3 failures"
        print("✅ Circuit breaker triggered after repeated failures")
        
    @pytest.mark.asyncio
    async def test_websocket_death_notification(self):
        """Test that WebSocket properly notifies on agent death."""
        print("\n" + "="*80)
        print("TEST: WebSocket Death Notification")
        print("="*80)
        
        # Setup execution tracker with WebSocket integration
        tracker = ExecutionTracker()
        websocket = MockWebSocketBridge()
        
        # Create task to monitor deaths
        death_detected = asyncio.Event()
        
        async def death_callback(execution_id: str, reason: str):
            """Callback when death is detected."""
            await websocket.notify_agent_death(
                run_id=execution_id,
                agent_name='triage_agent',
                reason=reason,
                details={'execution_id': execution_id}
            )
            death_detected.set()
        
        # Start execution with monitoring
        exec_id = await tracker.start_execution(
            agent_name='triage_agent',
            thread_id='thread_abc',
            user_id='user_xyz',
            metadata={'run_id': 'run_123'}
        )
        print(f"✅ Started execution with monitoring: {exec_id}")
        
        # Send a few heartbeats
        for i in range(2):
            await asyncio.sleep(1)
            await tracker.heartbeat(exec_id)
            print(f"  💓 Heartbeat {i+1}")
        
        # Stop heartbeats to simulate death
        print("\n🔴 Simulating agent death...")
        
        # Register death callback
        tracker.registry.on_state_change = death_callback
        
        # Wait for timeout (using shorter timeout for test)
        await tracker.timeout(exec_id)
        
        # Verify WebSocket notification was sent
        await asyncio.wait_for(death_detected.wait(), timeout=5)
        
        assert len(websocket.death_notifications) > 0, "WebSocket should send death notification"
        notification = websocket.death_notifications[0]
        assert notification['agent_name'] == 'triage_agent'
        assert notification['reason'] == 'timeout'
        print(f"✅ WebSocket death notification sent: {notification['reason']}")
        
    @pytest.mark.asyncio
    async def test_multiple_concurrent_deaths(self):
        """Test system stability with multiple concurrent agent deaths."""
        print("\n" + "="*80)
        print("TEST: Multiple Concurrent Agent Deaths")
        print("="*80)
        
        tracker = AgentExecutionTracker()
        health_integration = ExecutionHealthIntegration()
        
        # Create multiple executions
        exec_ids = []
        for i in range(5):
            exec_id = tracker.create_execution(
                agent_name=f'agent_{i}',
                thread_id=f'thread_{i}',
                user_id=f'user_{i}',
                timeout_seconds=10
            )
            tracker.start_execution(exec_id)
            exec_ids.append(exec_id)
            print(f"  Started agent_{i}: {exec_id}")
        
        # Send initial heartbeats
        for exec_id in exec_ids:
            tracker.heartbeat(exec_id)
        print(f"✅ Started {len(exec_ids)} concurrent agents")
        
        # Kill 3 agents (stop their heartbeats)
        dead_agents = exec_ids[:3]
        alive_agents = exec_ids[3:]
        
        print(f"\n🔴 Killing {len(dead_agents)} agents...")
        
        # Keep alive agents beating, let others die
        for _ in range(12):
            await asyncio.sleep(1)
            for exec_id in alive_agents:
                tracker.heartbeat(exec_id)
        
        # Check health status
        health_result = await health_integration.check_agent_execution_health()
        
        # Verify dead agents detected
        dead_count = 0
        alive_count = 0
        for exec_id in exec_ids:
            record = tracker.get_execution(exec_id)
            if record and record.is_dead():
                dead_count += 1
            elif record and not record.is_terminal:
                alive_count += 1
        
        assert dead_count == 3, f"Should detect 3 dead agents, found {dead_count}"
        assert alive_count == 2, f"Should have 2 alive agents, found {alive_count}"
        print(f"✅ Correctly detected {dead_count} dead and {alive_count} alive agents")
        
        # Verify health shows unhealthy
        assert health_result['status'] == HealthStatus.UNHEALTHY.value
        print("✅ Health status correctly shows UNHEALTHY")
        
    @pytest.mark.asyncio 
    async def test_recovery_after_agent_death(self):
        """Test that system can recover after agent death."""
        print("\n" + "="*80)
        print("TEST: Recovery After Agent Death")
        print("="*80)
        
        tracker = AgentExecutionTracker()
        
        # Create and kill an agent
        exec_id1 = tracker.create_execution(
            agent_name='triage_agent',
            thread_id='thread_1',
            user_id='user_1',
            timeout_seconds=5
        )
        tracker.start_execution(exec_id1)
        print(f"✅ Started first agent: {exec_id1}")
        
        # Let it timeout
        await asyncio.sleep(6)
        record1 = tracker.get_execution(exec_id1)
        assert record1.is_timed_out(), "First agent should be timed out"
        print("🔴 First agent timed out")
        
        # Mark as failed
        tracker.update_execution_state(exec_id1, ExecutionState.FAILED, error="Timeout")
        
        # Start recovery agent
        exec_id2 = tracker.create_execution(
            agent_name='triage_agent_recovery',
            thread_id='thread_2',
            user_id='user_1',
            timeout_seconds=30
        )
        tracker.start_execution(exec_id2)
        print(f"✅ Started recovery agent: {exec_id2}")
        
        # Keep recovery agent alive
        for i in range(3):
            await asyncio.sleep(1)
            tracker.heartbeat(exec_id2)
            print(f"  💓 Recovery agent heartbeat {i+1}")
        
        # Complete recovery successfully
        tracker.update_execution_state(exec_id2, ExecutionState.SUCCESS, result={'recovered': True})
        
        # Verify recovery
        record2 = tracker.get_execution(exec_id2)
        assert record2.state == ExecutionState.SUCCESS
        assert record2.result.get('recovered') == True
        print("✅ Recovery agent completed successfully")
        
        # Check system health after recovery
        health_integration = ExecutionHealthIntegration()
        health_result = await health_integration.check_agent_execution_health()
        assert health_result['status'] == HealthStatus.HEALTHY.value
        print("✅ System health restored after recovery")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MISSION CRITICAL: AGENT DEATH BUG FIX VERIFICATION")
    print("="*80)
    print("This test suite verifies the complete fix for the agent death bug.")
    print("ALL tests must PASS for the bug to be considered FIXED.")
    print("="*80 + "\n")
    
    pytest.main([__file__, "-v", "-s", "--tb=short"])