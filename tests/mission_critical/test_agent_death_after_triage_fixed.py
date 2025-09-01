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
        
        print("\n" + "="*80)
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
        print("\n💀 SIMULATING AGENT DEATH - No more heartbeats...")
        
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
        
        print("\n" + "="*80)
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
        
        assert detection_successful, \
            f"CRITICAL FAILURE: New execution tracking system failed to detect agent death! " \
            f"Final state: {final_status.execution_record.state.value if final_status else 'NOT_FOUND'}"
        
        print("✅ SUCCESS: New execution tracking system detected agent death/timeout!")
        print("🐛 BUG IS FIXED: Silent agent death is now detected!")
        
        # Cleanup
        await tracker.shutdown()


if __name__ == "__main__":
    # Run the comprehensive test suite
    import sys
    
    print("\n" + "="*80)
    print("COMPREHENSIVE AGENT DEATH DETECTION TEST SUITE")
    print("="*80)
    print("Testing the FIX for critical agent death after triage bug")
    print("All tests MUST PASS to confirm bug is fixed")
    print("="*80 + "\n")
    
    pytest.main([__file__, "-v", "--tb=short", "-s"])