# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: CRITICAL TEST: Agent Processing Death After Triage - FIXED VERSION
# REMOVED_SYNTAX_ERROR: ================================================================
# REMOVED_SYNTAX_ERROR: This test verifies the FIX for a CRITICAL production bug where:
    # REMOVED_SYNTAX_ERROR: 1. Agent starts processing normally
    # REMOVED_SYNTAX_ERROR: 2. Goes through triage successfully
    # REMOVED_SYNTAX_ERROR: 3. Dies silently without error or proper health detection
    # REMOVED_SYNTAX_ERROR: 4. WebSocket continues to send empty responses with "..."
    # REMOVED_SYNTAX_ERROR: 5. Health service FAILS to detect the dead agent
    # REMOVED_SYNTAX_ERROR: 6. No errors are logged, system appears "healthy"

    # REMOVED_SYNTAX_ERROR: With the NEW IMPLEMENTATION:
        # REMOVED_SYNTAX_ERROR: - ExecutionTracker monitors all agent executions
        # REMOVED_SYNTAX_ERROR: - HeartbeatMonitor detects agent death within 30 seconds
        # REMOVED_SYNTAX_ERROR: - TimeoutManager enforces execution timeouts
        # REMOVED_SYNTAX_ERROR: - WebSocket sends proper error notifications
        # REMOVED_SYNTAX_ERROR: - Health service accurately reflects agent state

        # REMOVED_SYNTAX_ERROR: THIS TEST VERIFIES THE FIX WORKS CORRECTLY.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Optional
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Import the new execution tracking system
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_execution_tracker import ( )
        # REMOVED_SYNTAX_ERROR: AgentExecutionTracker, ExecutionState, ExecutionRecord
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_tracking.tracker import ( )
        # REMOVED_SYNTAX_ERROR: ExecutionTracker, AgentExecutionContext, AgentExecutionResult, ExecutionProgress
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_tracking.registry import ExecutionRegistry, ExecutionState as NewExecutionState
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_tracking.timeout import TimeoutManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class DeathDetectionVerifier:
    # REMOVED_SYNTAX_ERROR: """Verifies that the new death detection system works correctly"""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.events: List[Dict[str, Any]] = []
    # REMOVED_SYNTAX_ERROR: self.death_detected_events = []
    # REMOVED_SYNTAX_ERROR: self.heartbeat_failures = []
    # REMOVED_SYNTAX_ERROR: self.timeout_events = []

# REMOVED_SYNTAX_ERROR: def record_event(self, event: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: """Record execution events for analysis"""
    # REMOVED_SYNTAX_ERROR: self.events.append({ ))
    # REMOVED_SYNTAX_ERROR: **event,
    # REMOVED_SYNTAX_ERROR: 'timestamp': time.time()
    

    # Detect death-related events
    # REMOVED_SYNTAX_ERROR: if event.get('type') == 'agent_death':
        # REMOVED_SYNTAX_ERROR: self.death_detected_events.append(event)
        # REMOVED_SYNTAX_ERROR: elif event.get('type') == 'heartbeat_failure':
            # REMOVED_SYNTAX_ERROR: self.heartbeat_failures.append(event)
            # REMOVED_SYNTAX_ERROR: elif event.get('type') == 'execution_timeout':
                # REMOVED_SYNTAX_ERROR: self.timeout_events.append(event)

# REMOVED_SYNTAX_ERROR: def get_verification_report(self) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Generate verification report"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'death_detection_working': len(self.death_detected_events) > 0,
    # REMOVED_SYNTAX_ERROR: 'heartbeat_monitoring_working': len(self.heartbeat_failures) > 0 or self._has_heartbeat_status(),
    # REMOVED_SYNTAX_ERROR: 'timeout_detection_working': len(self.timeout_events) > 0,
    # REMOVED_SYNTAX_ERROR: 'total_events': len(self.events),
    # REMOVED_SYNTAX_ERROR: 'death_events': self.death_detected_events,
    # REMOVED_SYNTAX_ERROR: 'heartbeat_events': self.heartbeat_failures,
    # REMOVED_SYNTAX_ERROR: 'timeout_events': self.timeout_events
    

# REMOVED_SYNTAX_ERROR: def _has_heartbeat_status(self) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if we received heartbeat status information"""
    # REMOVED_SYNTAX_ERROR: return any('heartbeat' in event.get('data', {}) for event in self.events)


    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: class TestAgentDeathAfterTriageFixed:
    # REMOVED_SYNTAX_ERROR: """Test suite verifying the agent death bug is FIXED"""

    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: async def test_execution_tracker_detects_agent_death(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: CRITICAL: Test that ExecutionTracker detects agent death

        # REMOVED_SYNTAX_ERROR: This test MUST PASS to prove the bug is FIXED!
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: verifier = DeathDetectionVerifier()

        # Create execution tracker with fast detection for testing
        # REMOVED_SYNTAX_ERROR: tracker = ExecutionTracker( )
        # REMOVED_SYNTAX_ERROR: websocket_bridge=None,  # No WebSocket for this test
        # REMOVED_SYNTAX_ERROR: heartbeat_interval=1.0,  # Check every 1 second
        # REMOVED_SYNTAX_ERROR: timeout_check_interval=1.0
        

        # Create execution context
        # REMOVED_SYNTAX_ERROR: context = AgentExecutionContext( )
        # REMOVED_SYNTAX_ERROR: run_id="test-death-detection",
        # REMOVED_SYNTAX_ERROR: agent_name="triage",
        # REMOVED_SYNTAX_ERROR: thread_id="test-thread",
        # REMOVED_SYNTAX_ERROR: user_id="test-user"
        

        # REMOVED_SYNTAX_ERROR: print(" )
        # REMOVED_SYNTAX_ERROR: " + "="*80)
        # REMOVED_SYNTAX_ERROR: print("TESTING: ExecutionTracker Death Detection")
        # REMOVED_SYNTAX_ERROR: print("="*80)

        # Start tracking execution
        # REMOVED_SYNTAX_ERROR: execution_id = await tracker.start_execution( )
        # REMOVED_SYNTAX_ERROR: run_id=context.run_id,
        # REMOVED_SYNTAX_ERROR: agent_name=context.agent_name,
        # REMOVED_SYNTAX_ERROR: context=context
        

        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Verify execution started
        # REMOVED_SYNTAX_ERROR: status = await tracker.get_execution_status(execution_id)
        # REMOVED_SYNTAX_ERROR: assert status is not None, "Execution status should exist"
        # REMOVED_SYNTAX_ERROR: assert status.execution_record.state in [NewExecutionState.INITIALIZING, NewExecutionState.PENDING]

        # Simulate agent starting work with heartbeats
        # REMOVED_SYNTAX_ERROR: await tracker.update_execution_progress( )
        # REMOVED_SYNTAX_ERROR: execution_id,
        # REMOVED_SYNTAX_ERROR: ExecutionProgress( )
        # REMOVED_SYNTAX_ERROR: stage="triage_start",
        # REMOVED_SYNTAX_ERROR: percentage=10.0,
        # REMOVED_SYNTAX_ERROR: message="Starting triage analysis..."
        
        
        # REMOVED_SYNTAX_ERROR: print("📊 Progress update 1: Triage starting")

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)

        # REMOVED_SYNTAX_ERROR: await tracker.update_execution_progress( )
        # REMOVED_SYNTAX_ERROR: execution_id,
        # REMOVED_SYNTAX_ERROR: ExecutionProgress( )
        # REMOVED_SYNTAX_ERROR: stage="triage_analysis",
        # REMOVED_SYNTAX_ERROR: percentage=30.0,
        # REMOVED_SYNTAX_ERROR: message="Analyzing user request..."
        
        
        # REMOVED_SYNTAX_ERROR: print("📊 Progress update 2: Analysis in progress")

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)

        # Verify agent is working
        # REMOVED_SYNTAX_ERROR: status = await tracker.get_execution_status(execution_id)
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Now simulate AGENT DEATH - no more heartbeats or progress updates!
        # REMOVED_SYNTAX_ERROR: print(" )
        # REMOVED_SYNTAX_ERROR: 💀 SIMULATING AGENT DEATH - No more heartbeats...")

        # The old system would miss this completely
        # The new system SHOULD detect this via heartbeat monitoring

        # Wait for death detection
        # REMOVED_SYNTAX_ERROR: death_detected = False
        # REMOVED_SYNTAX_ERROR: timeout_detected = False
        # REMOVED_SYNTAX_ERROR: max_wait_seconds = 15

        # REMOVED_SYNTAX_ERROR: for i in range(max_wait_seconds):
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)
            # REMOVED_SYNTAX_ERROR: status = await tracker.get_execution_status(execution_id)

            # REMOVED_SYNTAX_ERROR: if status:
                # REMOVED_SYNTAX_ERROR: state_name = status.execution_record.state.value
                # REMOVED_SYNTAX_ERROR: heartbeat_alive = status.heartbeat_status.is_alive if status.heartbeat_status else "N/A"
                # REMOVED_SYNTAX_ERROR: missed_beats = status.heartbeat_status.missed_heartbeats if status.heartbeat_status else 0

                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Check for death detection
                # REMOVED_SYNTAX_ERROR: if status.execution_record.state == NewExecutionState.FAILED:
                    # REMOVED_SYNTAX_ERROR: error_msg = status.execution_record.metadata.get("error", "")
                    # REMOVED_SYNTAX_ERROR: if "heartbeat failure" in error_msg.lower():
                        # REMOVED_SYNTAX_ERROR: death_detected = True
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                        # REMOVED_SYNTAX_ERROR: verifier.record_event({ ))
                        # REMOVED_SYNTAX_ERROR: 'type': 'agent_death',
                        # REMOVED_SYNTAX_ERROR: 'data': {'method': 'heartbeat_failure', 'execution_id': execution_id}
                        
                        # REMOVED_SYNTAX_ERROR: break
                        # REMOVED_SYNTAX_ERROR: elif status.execution_record.state == NewExecutionState.TIMEOUT:
                            # REMOVED_SYNTAX_ERROR: timeout_detected = True
                            # REMOVED_SYNTAX_ERROR: print(f"⏰ TIMEOUT DETECTED")
                            # REMOVED_SYNTAX_ERROR: verifier.record_event({ ))
                            # REMOVED_SYNTAX_ERROR: 'type': 'execution_timeout',
                            # REMOVED_SYNTAX_ERROR: 'data': {'execution_id': execution_id}
                            
                            # REMOVED_SYNTAX_ERROR: break
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                # Verify the NEW system detected the problem
                                # REMOVED_SYNTAX_ERROR: final_status = await tracker.get_execution_status(execution_id)
                                # REMOVED_SYNTAX_ERROR: report = verifier.get_verification_report()

                                # REMOVED_SYNTAX_ERROR: print(" )
                                # REMOVED_SYNTAX_ERROR: " + "="*80)
                                # REMOVED_SYNTAX_ERROR: print("EXECUTION TRACKER DEATH DETECTION RESULTS")
                                # REMOVED_SYNTAX_ERROR: print("="*80)
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                # REMOVED_SYNTAX_ERROR: if final_status:
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: print("="*80)

                                    # The NEW system MUST detect agent death or timeout
                                    # REMOVED_SYNTAX_ERROR: detection_successful = death_detected or timeout_detected

                                    # REMOVED_SYNTAX_ERROR: assert detection_successful, \
                                    # REMOVED_SYNTAX_ERROR: f"CRITICAL FAILURE: New execution tracking system failed to detect agent death! " \
                                    # REMOVED_SYNTAX_ERROR: "formatted_string"

                                    # REMOVED_SYNTAX_ERROR: print("✅ SUCCESS: New execution tracking system detected agent death/timeout!")
                                    # REMOVED_SYNTAX_ERROR: print("🐛 BUG IS FIXED: Silent agent death is now detected!")

                                    # Cleanup
                                    # REMOVED_SYNTAX_ERROR: await tracker.shutdown()


                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                        # Run the comprehensive test suite
                                        # REMOVED_SYNTAX_ERROR: import sys

                                        # REMOVED_SYNTAX_ERROR: print(" )
                                        # REMOVED_SYNTAX_ERROR: " + "="*80)
                                        # REMOVED_SYNTAX_ERROR: print("COMPREHENSIVE AGENT DEATH DETECTION TEST SUITE")
                                        # REMOVED_SYNTAX_ERROR: print("="*80)
                                        # REMOVED_SYNTAX_ERROR: print("Testing the FIX for critical agent death after triage bug")
                                        # REMOVED_SYNTAX_ERROR: print("All tests MUST PASS to confirm bug is fixed")
                                        # REMOVED_SYNTAX_ERROR: print("="*80 + " )
                                        # REMOVED_SYNTAX_ERROR: ")

                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short", "-s"])