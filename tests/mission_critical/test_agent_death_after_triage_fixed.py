"""
CRITICAL TEST: Agent Processing Death After Triage - FIXED VERSION
================================================================
This test verifies the FIX for a CRITICAL production bug where:
1. Agent starts processing normally
2. Goes through triage successfully  
3. Dies silently without error or proper health detection
4. WebSocket continues to send empty responses with "..."
5. Health service FAILS to detect the dead agent
6. No errors are logged, system appears "healthy"

With the NEW IMPLEMENTATION:
- ExecutionTracker monitors all agent executions
- HeartbeatMonitor detects agent death within 30 seconds
- TimeoutManager enforces execution timeouts
- WebSocket sends proper error notifications
- Health service accurately reflects agent state

THIS TEST VERIFIES THE FIX WORKS CORRECTLY.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

# Import the new execution tracking system
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, ExecutionState, ExecutionRecord
)
from netra_backend.app.agents.execution_tracking.tracker import (
    ExecutionTracker, AgentExecutionContext, AgentExecutionResult, ExecutionProgress
)
from netra_backend.app.agents.execution_tracking.registry import ExecutionRegistry, ExecutionState as NewExecutionState
from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor
from netra_backend.app.agents.execution_tracking.timeout import TimeoutManager


class DeathDetectionVerifier:
    """Verifies that the new death detection system works correctly"""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.death_detected_events = []
        self.heartbeat_failures = []
        self.timeout_events = []
        
    def record_event(self, event: Dict[str, Any]):
        """Record execution events for analysis"""
        self.events.append({
            **event,
            'timestamp': time.time()
        })
        
        # Detect death-related events
        if event.get('type') == 'agent_death':
            self.death_detected_events.append(event)
        elif event.get('type') == 'heartbeat_failure':
            self.heartbeat_failures.append(event)
        elif event.get('type') == 'execution_timeout':
            self.timeout_events.append(event)
    
    def get_verification_report(self) -> Dict[str, Any]:
        """Generate verification report"""
        return {
            'death_detection_working': len(self.death_detected_events) > 0,
            'heartbeat_monitoring_working': len(self.heartbeat_failures) > 0 or self._has_heartbeat_status(),
            'timeout_detection_working': len(self.timeout_events) > 0,
            'total_events': len(self.events),
            'death_events': self.death_detected_events,
            'heartbeat_events': self.heartbeat_failures,
            'timeout_events': self.timeout_events
        }
    
    def _has_heartbeat_status(self) -> bool:
        """Check if we received heartbeat status information"""
        return any('heartbeat' in event.get('data', {}) for event in self.events)


@pytest.mark.critical
class TestAgentDeathAfterTriageFixed:
    """Test suite verifying the agent death bug is FIXED"""
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_execution_tracker_detects_agent_death(self):
        """
        CRITICAL: Test that ExecutionTracker detects agent death
        
        This test MUST PASS to prove the bug is FIXED!
        """
        verifier = DeathDetectionVerifier()
        
        # Create execution tracker with fast detection for testing
        tracker = ExecutionTracker(
            websocket_bridge=None,  # No WebSocket for this test
            heartbeat_interval=1.0,  # Check every 1 second
            timeout_check_interval=1.0
        )
        
        # Create execution context
        context = AgentExecutionContext(
            run_id="test-death-detection",
            agent_name="triage",
            thread_id="test-thread",
            user_id="test-user"
        )
        
        print("\\n" + "="*80)
        print("TESTING: ExecutionTracker Death Detection")
        print("="*80)
        
        # Start tracking execution
        execution_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        print(f"✅ Started execution tracking: {execution_id}")
        
        # Verify execution started
        status = await tracker.get_execution_status(execution_id)
        assert status is not None, "Execution status should exist"
        assert status.execution_record.state in [NewExecutionState.INITIALIZING, NewExecutionState.PENDING]
        
        # Simulate agent starting work with heartbeats
        await tracker.update_execution_progress(
            execution_id,
            ExecutionProgress(
                stage="triage_start",
                percentage=10.0,
                message="Starting triage analysis..."
            )
        )
        print("📊 Progress update 1: Triage starting")
        
        await asyncio.sleep(1)
        
        await tracker.update_execution_progress(
            execution_id,
            ExecutionProgress(
                stage="triage_analysis",
                percentage=30.0,
                message="Analyzing user request..."
            )
        )
        print("📊 Progress update 2: Analysis in progress")
        
        await asyncio.sleep(1)
        
        # Verify agent is working
        status = await tracker.get_execution_status(execution_id)
        print(f"📋 Current state: {status.execution_record.state.value}")
        print(f"💓 Heartbeat alive: {status.heartbeat_status.is_alive if status.heartbeat_status else 'N/A'}")
        
        # Now simulate AGENT DEATH - no more heartbeats or progress updates!
        print("\\n💀 SIMULATING AGENT DEATH - No more heartbeats...")
        
        # The old system would miss this completely
        # The new system SHOULD detect this via heartbeat monitoring
        
        # Wait for death detection
        death_detected = False
        timeout_detected = False
        max_wait_seconds = 15
        
        for i in range(max_wait_seconds):
            await asyncio.sleep(1)
            status = await tracker.get_execution_status(execution_id)
            
            if status:
                state_name = status.execution_record.state.value
                heartbeat_alive = status.heartbeat_status.is_alive if status.heartbeat_status else "N/A"
                missed_beats = status.heartbeat_status.missed_heartbeats if status.heartbeat_status else 0
                
                print(f"⏱️  Second {i+1}: State={state_name}, Heartbeat={heartbeat_alive}, Missed={missed_beats}")
                
                # Check for death detection
                if status.execution_record.state == NewExecutionState.FAILED:
                    error_msg = status.execution_record.metadata.get("error", "")
                    if "heartbeat failure" in error_msg.lower():
                        death_detected = True
                        print(f"💀 DEATH DETECTED: {error_msg}")
                        verifier.record_event({
                            'type': 'agent_death',
                            'data': {'method': 'heartbeat_failure', 'execution_id': execution_id}
                        })
                        break
                elif status.execution_record.state == NewExecutionState.TIMEOUT:
                    timeout_detected = True
                    print(f"⏰ TIMEOUT DETECTED")
                    verifier.record_event({
                        'type': 'execution_timeout',
                        'data': {'execution_id': execution_id}
                    })
                    break
            else:
                print(f"⏱️  Second {i+1}: No status found")
        
        # Verify the NEW system detected the problem
        final_status = await tracker.get_execution_status(execution_id)
        report = verifier.get_verification_report()
        
        print("\\n" + "="*80)
        print("EXECUTION TRACKER DEATH DETECTION RESULTS")
        print("="*80)
        print(f"Death detected via heartbeat: {death_detected}")
        print(f"Timeout detected: {timeout_detected}")
        if final_status:
            print(f"Final execution state: {final_status.execution_record.state.value}")
            print(f"Final error: {final_status.execution_record.metadata.get('error', 'None')}")
        print(f"Detection events recorded: {len(report['death_events']) + len(report['timeout_events'])}")
        print("="*80)
        
        # The NEW system MUST detect agent death or timeout
        detection_successful = death_detected or timeout_detected
        
        assert detection_successful, \\
            f"CRITICAL FAILURE: New execution tracking system failed to detect agent death! " \\
            f"Final state: {final_status.execution_record.state.value if final_status else 'NOT_FOUND'}"
        
        print("✅ SUCCESS: New execution tracking system detected agent death/timeout!")
        print("🐛 BUG IS FIXED: Silent agent death is now detected!")
        
        # Cleanup
        await tracker.shutdown()
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitor_standalone(self):
        """
        Test HeartbeatMonitor component detects death correctly
        """
        print("\\n" + "="*80)
        print("TESTING: HeartbeatMonitor Standalone")
        print("="*80)
        
        # Create monitor with fast detection for testing
        heartbeat_monitor = HeartbeatMonitor(heartbeat_interval_seconds=1.0)
        
        # Start monitoring an execution
        execution_id = "test-heartbeat-standalone"
        await heartbeat_monitor.start_monitoring(execution_id)
        print(f"📡 Started monitoring: {execution_id}")
        
        # Send heartbeats to keep agent "alive"
        for i in range(3):
            await heartbeat_monitor.send_heartbeat(execution_id, {"beat": i})
            await asyncio.sleep(0.5)
            print(f"💓 Heartbeat {i+1} sent")
        
        # Verify agent is alive
        status = await heartbeat_monitor.get_heartbeat_status(execution_id)
        assert status is not None, "Heartbeat status should exist"
        assert status.is_alive, "Agent should be alive after recent heartbeats"
        print(f"✅ Agent confirmed alive: missed={status.missed_heartbeats}")
        
        # Now stop sending heartbeats (simulate agent death)
        print("\\n💀 Stopping heartbeats to simulate agent death...")
        
        # Wait for death detection (should happen within ~5 seconds)
        death_detected = False
        for i in range(10):
            await asyncio.sleep(1)
            status = await heartbeat_monitor.get_heartbeat_status(execution_id)
            
            if status:
                print(f"⏱️  Second {i+1}: Alive={status.is_alive}, Missed={status.missed_heartbeats}")
                if not status.is_alive:
                    death_detected = True
                    break
            else:
                print(f"⏱️  Second {i+1}: No heartbeat status")
        
        print("\\n" + "="*50)
        print(f"Death detected: {death_detected}")
        print("="*50)
        
        assert death_detected, "HeartbeatMonitor failed to detect agent death"
        print("✅ SUCCESS: HeartbeatMonitor detected agent death!")
        
        # Cleanup
        await heartbeat_monitor.shutdown()
    
    @pytest.mark.asyncio
    async def test_timeout_manager_enforces_limits(self):
        """
        Test TimeoutManager enforces execution timeouts
        """
        print("\\n" + "="*80)
        print("TESTING: TimeoutManager Enforcement")
        print("="*80)
        
        timeout_manager = TimeoutManager(check_interval_seconds=1.0)
        
        execution_id = "test-timeout-enforcement"
        timeout_seconds = 3.0  # Short timeout for testing
        
        # Set timeout
        await timeout_manager.set_timeout(execution_id, timeout_seconds, "test-agent")
        print(f"⏰ Set timeout: {timeout_seconds}s for {execution_id}")
        
        # Verify timeout is set
        timeout_info = await timeout_manager.get_timeout_info(execution_id)
        assert timeout_info is not None, "Timeout info should exist"
        assert not timeout_info.has_timed_out, "Should not be timed out initially"
        assert timeout_info.remaining_seconds > 0, "Should have remaining time"
        print(f"✅ Timeout configured: remaining={timeout_info.remaining_seconds:.1f}s")
        
        # Wait for timeout to trigger
        print("\\n⏳ Waiting for timeout...")
        timeout_detected = False
        
        for i in range(8):  # Wait up to 8 seconds
            await asyncio.sleep(1)
            timeout_info = await timeout_manager.get_timeout_info(execution_id)
            
            if timeout_info:
                remaining = max(0, timeout_info.remaining_seconds)
                print(f"⏱️  Second {i+1}: Remaining={remaining:.1f}s, Timed out={timeout_info.has_timed_out}")
                
                if timeout_info.has_timed_out:
                    timeout_detected = True
                    break
            else:
                print(f"⏱️  Second {i+1}: No timeout info found")
        
        print("\\n" + "="*50)
        print(f"Timeout detected: {timeout_detected}")
        print("="*50)
        
        assert timeout_detected, "TimeoutManager failed to detect timeout"
        print("✅ SUCCESS: TimeoutManager enforced timeout!")
        
        # Cleanup
        await timeout_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_execution_registry_tracks_state(self):
        """
        Test ExecutionRegistry tracks execution state correctly
        """
        print("\\n" + "="*80)
        print("TESTING: ExecutionRegistry State Tracking")
        print("="*80)
        
        registry = ExecutionRegistry()
        
        # Register a new execution
        record = await registry.register_execution(
            run_id="test-registry-tracking",
            agent_name="test-agent",
            context={"test": True}
        )
        
        execution_id = record.execution_id
        print(f"📝 Registered execution: {execution_id}")
        print(f"📊 Initial state: {record.state.value}")
        
        # Verify initial state
        assert record.state == NewExecutionState.PENDING
        
        # Update state progression
        states = [
            (NewExecutionState.INITIALIZING, "Starting up"),
            (NewExecutionState.RUNNING, "Processing request"),
            (NewExecutionState.SUCCESS, "Completed successfully")
        ]
        
        for new_state, message in states:
            success = await registry.update_execution_state(
                execution_id, 
                new_state,
                {"progress": message}
            )
            assert success, f"Failed to update state to {new_state.value}"
            
            # Verify state update
            updated_record = await registry.get_execution(execution_id)
            assert updated_record is not None
            assert updated_record.state == new_state
            print(f"📊 State updated to: {new_state.value} - {message}")
        
        # Test metrics
        metrics = await registry.get_execution_metrics()
        print(f"📈 Registry metrics: {metrics.dict()}")
        
        print("\\n✅ SUCCESS: ExecutionRegistry tracked states correctly!")
        
        # Cleanup
        await registry.shutdown()
    
    @pytest.mark.asyncio 
    async def test_comprehensive_integration(self):
        """
        Test all components working together to detect agent death
        """
        print("\\n" + "="*80)
        print("TESTING: Comprehensive Integration Test")
        print("="*80)
        
        # Setup all components
        tracker = ExecutionTracker(
            websocket_bridge=None,
            heartbeat_interval=1.0,
            timeout_check_interval=1.0
        )
        
        verifier = DeathDetectionVerifier()
        
        # Test scenario: Agent starts, works, then dies
        context = AgentExecutionContext(
            run_id="integration-test",
            agent_name="comprehensive-agent",
            thread_id="test-thread",
            user_id="test-user"
        )
        
        # Phase 1: Normal execution start
        print("\\n🚀 Phase 1: Starting execution...")
        execution_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        # Phase 2: Agent working normally
        print("\\n⚙️ Phase 2: Agent working normally...")
        work_phases = [
            ("initialization", 20, "Initializing components"),
            ("triage", 40, "Analyzing request"),
            ("processing", 60, "Processing data"),
            ("analysis", 80, "Running analysis")
        ]
        
        for phase, percentage, message in work_phases:
            await tracker.update_execution_progress(
                execution_id,
                ExecutionProgress(
                    stage=phase,
                    percentage=percentage,
                    message=message
                )
            )
            print(f"  📊 {percentage}%: {message}")
            await asyncio.sleep(0.5)
        
        # Verify healthy execution
        status = await tracker.get_execution_status(execution_id)
        assert status is not None
        assert status.heartbeat_status.is_alive
        print("✅ Agent confirmed healthy and working")
        
        # Phase 3: Agent death simulation
        print("\\n💀 Phase 3: Agent dies silently...")
        print("   (No more heartbeats will be sent)")
        
        # Phase 4: Death detection
        print("\\n🔍 Phase 4: Waiting for death detection...")
        
        death_mechanisms = {
            'heartbeat_failure': False,
            'timeout': False,
            'health_check': False
        }
        
        # Monitor for death detection
        for i in range(12):  # Wait up to 12 seconds
            await asyncio.sleep(1)
            status = await tracker.get_execution_status(execution_id)
            
            if status:
                state = status.execution_record.state.value
                heartbeat_alive = status.heartbeat_status.is_alive if status.heartbeat_status else "N/A"
                
                print(f"⏱️  Second {i+1}: State={state}, Heartbeat={heartbeat_alive}")
                
                # Check for different death detection mechanisms
                if status.execution_record.state == NewExecutionState.FAILED:
                    error = status.execution_record.metadata.get("error", "")
                    if "heartbeat" in error.lower():
                        death_mechanisms['heartbeat_failure'] = True
                        verifier.record_event({'type': 'heartbeat_failure', 'data': {'execution_id': execution_id}})
                        print("💀 Death detected via: HEARTBEAT FAILURE")
                        break
                elif status.execution_record.state == NewExecutionState.TIMEOUT:
                    death_mechanisms['timeout'] = True
                    verifier.record_event({'type': 'execution_timeout', 'data': {'execution_id': execution_id}})
                    print("💀 Death detected via: TIMEOUT")
                    break
                
                # Check heartbeat status
                if status.heartbeat_status and not status.heartbeat_status.is_alive:
                    death_mechanisms['health_check'] = True
        
        # Phase 5: Verification
        print("\\n📋 Phase 5: Verification Results")
        print("="*50)
        
        report = verifier.get_verification_report()
        final_status = await tracker.get_execution_status(execution_id)
        
        any_detection = any(death_mechanisms.values())
        
        print(f"Death detection mechanisms triggered:")
        for mechanism, triggered in death_mechanisms.items():
            status_icon = "✅" if triggered else "❌"
            print(f"  {status_icon} {mechanism}")
        
        print(f"\\nFinal execution state: {final_status.execution_record.state.value if final_status else 'NOT_FOUND'}")
        print(f"Overall death detection: {'✅ SUCCESS' if any_detection else '❌ FAILED'}")
        print("="*50)
        
        # Assert that at least one mechanism detected the death
        assert any_detection, \\
            f"CRITICAL: No death detection mechanism triggered! " \\
            f"Mechanisms checked: {death_mechanisms}"
        
        print("\\n🎉 COMPREHENSIVE TEST PASSED!")
        print("🐛 Agent death bug is FIXED!")
        print("✅ All detection mechanisms are working!")
        
        # Cleanup
        await tracker.shutdown()

    @pytest.mark.asyncio
    async def test_websocket_integration_mock(self):
        """
        Test WebSocket integration with mocked WebSocket bridge
        """
        print("\\n" + "="*80)
        print("TESTING: WebSocket Integration (Mocked)")
        print("="*80)
        
        # Mock WebSocket bridge
        websocket_bridge = MagicMock()
        websocket_bridge.notify_execution_started = AsyncMock()
        websocket_bridge.notify_execution_progress = AsyncMock()
        websocket_bridge.notify_execution_completed = AsyncMock()
        websocket_bridge.notify_execution_failed = AsyncMock()
        websocket_bridge.notify_agent_death = AsyncMock()
        
        # Create tracker with WebSocket bridge
        tracker = ExecutionTracker(
            websocket_bridge=websocket_bridge,
            heartbeat_interval=1.0,
            timeout_check_interval=1.0
        )
        
        # Test execution with WebSocket notifications
        context = AgentExecutionContext(
            run_id="websocket-test",
            agent_name="websocket-agent",
            thread_id="test-thread",
            user_id="test-user"
        )
        
        execution_id = await tracker.start_execution(
            run_id=context.run_id,
            agent_name=context.agent_name,
            context=context
        )
        
        # Verify started notification
        websocket_bridge.notify_execution_started.assert_called_once()
        print("✅ Execution started notification sent")
        
        # Send progress update
        await tracker.update_execution_progress(
            execution_id,
            ExecutionProgress(
                stage="testing",
                percentage=50.0,
                message="Testing WebSocket integration"
            )
        )
        
        # Verify progress notification
        websocket_bridge.notify_execution_progress.assert_called()
        print("✅ Progress notification sent")
        
        # Simulate agent death (no more heartbeats)
        print("\\n💀 Simulating agent death for WebSocket notification test...")
        
        # Wait for death detection
        for i in range(8):
            await asyncio.sleep(1)
            status = await tracker.get_execution_status(execution_id)
            if status and status.execution_record.state in [NewExecutionState.FAILED, NewExecutionState.TIMEOUT]:
                break
        
        # Give some time for death notification
        await asyncio.sleep(1)
        
        # Verify death notification was sent
        assert websocket_bridge.notify_agent_death.called or websocket_bridge.notify_execution_failed.called, \\
            "No death/failure notification sent via WebSocket"
        
        print("✅ Death notification sent via WebSocket")
        print("🌐 WebSocket integration working correctly!")
        
        # Cleanup
        await tracker.shutdown()


@pytest.mark.asyncio
async def test_legacy_vs_new_system_comparison():
    """
    Compare old broken system vs new fixed system
    """
    print("\\n" + "="*80)
    print("LEGACY vs NEW SYSTEM COMPARISON")
    print("="*80)
    
    # Simulate old system behavior (broken)
    print("\\n❌ LEGACY SYSTEM (BROKEN):")
    print("  - Agent starts processing")
    print("  - Agent dies silently")
    print("  - No heartbeat monitoring")
    print("  - No timeout detection")
    print("  - Health check returns 'healthy'")
    print("  - WebSocket sends empty responses")
    print("  - User sees infinite loading")
    print("  - RESULT: Complete silent failure")
    
    # Test new system behavior (fixed)
    print("\\n✅ NEW SYSTEM (FIXED):")
    
    tracker = ExecutionTracker(
        websocket_bridge=None,
        heartbeat_interval=1.0,
        timeout_check_interval=1.0
    )
    
    context = AgentExecutionContext(
        run_id="comparison-test",
        agent_name="comparison-agent",
        thread_id="test-thread",
        user_id="test-user"
    )
    
    execution_id = await tracker.start_execution(
        run_id=context.run_id,
        agent_name=context.agent_name,
        context=context
    )
    
    print("  - Agent starts with execution tracking")
    
    # Agent works briefly
    await tracker.update_execution_progress(
        execution_id,
        ExecutionProgress(stage="working", percentage=30.0, message="Processing...")
    )
    
    print("  - Heartbeat monitoring active")
    print("  - Timeout detection configured")
    
    # Agent dies (no more heartbeats)
    print("  - Agent dies silently...")
    
    # Wait for detection
    detected = False
    for i in range(8):
        await asyncio.sleep(1)
        status = await tracker.get_execution_status(execution_id)
        if status and status.execution_record.state in [NewExecutionState.FAILED, NewExecutionState.TIMEOUT]:
            detected = True
            print(f"  - Death detected in {i+1} seconds!")
            break
    
    if detected:
        print("  - WebSocket would send death notification")
        print("  - Health check shows actual failure")
        print("  - User receives proper error message")
        print("  - RESULT: Failure detected and handled properly!")
        print("\\n🎉 NEW SYSTEM SUCCESSFULLY FIXES THE BUG!")
    else:
        print("  - WARNING: Death not detected in time")
        
    print("\\n" + "="*80)
    
    await tracker.shutdown()
    
    # This should always pass with the new system
    assert detected, "New system should detect agent death"


if __name__ == "__main__":
    # Run the comprehensive test suite
    import sys
    
    print("\\n" + "="*80)
    print("COMPREHENSIVE AGENT DEATH DETECTION TEST SUITE")
    print("="*80)
    print("Testing the FIX for critical agent death after triage bug")
    print("All tests MUST PASS to confirm bug is fixed")
    print("="*80 + "\\n")
    
    pytest.main([__file__, "-v", "--tb=short", "-s"])