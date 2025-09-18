'''
'''
Integration Tests for Agent Death Recovery
=========================================
Tests the complete integration of execution tracking with the agent system
to ensure agent death is properly detected and recovery mechanisms work.

These tests verify:
1. Agent death during real execution scenarios
2. Recovery mechanisms and fallback behavior
3. WebSocket integration for real-time notifications
4. Health monitoring integration
5. Cross-service communication during failures
6. End-to-end agent failure handling workflows

Tests use real services where possible (no mocks for core functionality).
'''
'''

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from shared.isolated_environment import IsolatedEnvironment

    # Import execution tracking and agent components
from netra_backend.app.core.agent_execution_tracker import ( )
AgentExecutionTracker, ExecutionState as CoreExecutionState
    
from netra_backend.app.agents.execution_tracking.tracker import ( )
ExecutionTracker, AgentExecutionContext, AgentExecutionResult, ExecutionProgress
    
from netra_backend.app.agents.execution_tracking.registry import ExecutionState
from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor
from netra_backend.app.agents.execution_tracking.timeout import TimeoutManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class MockWebSocketBridge:
    """Mock WebSocket bridge that captures notifications for testing"""

    def __init__(self):
        pass
        self.notifications = []
        self.is_connected = True

        async def notify_execution_started(self, run_id: str, agent_name: str,
        execution_id: str, estimated_duration_ms: int):
        """Mock execution started notification"""
        self.notifications.append({ })
        'type': 'execution_started',
        'data': { }
        'run_id': run_id,
        'agent_name': agent_name,
        'execution_id': execution_id,
        'estimated_duration_ms': estimated_duration_ms
        },
        'timestamp': time.time()
    

        async def notify_execution_progress(self, run_id: str, agent_name: str,
        progress_data: Dict[str, Any]):
        """Mock execution progress notification"""
        self.notifications.append({ })
        'type': 'execution_progress',
        'data': { }
        'run_id': run_id,
        'agent_name': agent_name,
        'progress_data': progress_data
        },
        'timestamp': time.time()
    

        async def notify_execution_completed(self, run_id: str, agent_name: str,
        execution_result: Dict[str, Any]):
        """Mock execution completed notification"""
        self.notifications.append({ })
        'type': 'execution_completed',
        'data': { }
        'run_id': run_id,
        'agent_name': agent_name,
        'execution_result': execution_result
        },
        'timestamp': time.time()
    

        async def notify_execution_failed(self, run_id: str, agent_name: str,
        error_details: Dict[str, Any]):
        """Mock execution failed notification"""
        self.notifications.append({ })
        'type': 'execution_failed',
        'data': { }
        'run_id': run_id,
        'agent_name': agent_name,
        'error_details': error_details
        },
        'timestamp': time.time()
    

        async def notify_agent_death(self, run_id: str, agent_name: str,
        death_type: str, details: Dict[str, Any]):
        """Mock agent death notification"""
        self.notifications.append({ })
        'type': 'agent_death',
        'data': { }
        'run_id': run_id,
        'agent_name': agent_name,
        'death_type': death_type,
        'details': details
        },
        'timestamp': time.time()
    

    def get_notifications_by_type(self, notification_type: str) -> List[Dict[str, Any]]:
        """Get all notifications of a specific type"""
        await asyncio.sleep(0)
        return [item for item in []] == notification_type]

    def clear_notifications(self):
        """Clear all recorded notifications"""
        self.notifications.clear()


class AgentSimulator:
        """Simulates agent behavior for testing death scenarios"""

    def __init__(self, execution_tracker: ExecutionTracker):
        pass
        self.tracker = execution_tracker
        self.is_alive = True
        self.execution_id = None

    async def start_execution(self, run_id: str, agent_name: str, context: AgentExecutionContext):
        """Start a simulated agent execution"""
        self.execution_id = await self.tracker.start_execution(run_id, agent_name, context)
        await asyncio.sleep(0)
        return self.execution_id

    async def do_work_phases(self, phases: List[Dict[str, Any]]):
        """Simulate agent doing work in phases"""
        pass
        for phase in phases:
        if not self.is_alive:
        break

        progress = ExecutionProgress( )
        stage=phase['stage'],
        percentage=phase['percentage'],
        message=phase['message']
            

        await self.tracker.update_execution_progress(self.execution_id, progress)
        await asyncio.sleep(phase.get('duration', 0.5))

    async def die_silently(self):
        """Simulate agent dying silently (no more heartbeats)"""
        self.is_alive = False
    # Agent stops sending heartbeats - this should trigger death detection

    async def complete_successfully(self, result_data: Any = None):
        """Simulate agent completing successfully"""
        pass
        if self.execution_id and self.is_alive:
        result = AgentExecutionResult( )
        success=True,
        execution_id=self.execution_id,
        duration_seconds=time.time() - time.time(),  # Approximate
        data=result_data
        
        await self.tracker.complete_execution(self.execution_id, result)

    async def fail_with_error(self, error_message: str):
        """Simulate agent failing with an error"""
        if self.execution_id:
        error = Exception(error_message)
        await self.tracker.handle_execution_failure(self.execution_id, error)


class TestAgentDeathRecoveryIntegration:
        """Integration tests for agent death recovery"""

        @pytest.fixture
    async def websocket_bridge(self):
        """Create mock WebSocket bridge for testing"""
        await asyncio.sleep(0)
        return MockWebSocketBridge()

        @pytest.fixture
    async def execution_tracker(self, websocket_bridge):
        """Create ExecutionTracker with WebSocket integration"""
        pass
        tracker = ExecutionTracker( )
        websocket_bridge=websocket_bridge,
        heartbeat_interval=1.0,  # Fast for testing
        timeout_check_interval=1.0
    
        yield tracker
        await tracker.shutdown()

@pytest.mark.asyncio
    # Removed problematic line: async def test_agent_death_detected_with_websocket_notification( )
self, execution_tracker, websocket_bridge
):
"""Test that agent death is detected and WebSocket notifications are sent"""
print("")
 + ="*80)"
print("INTEGRATION TEST: Agent Death Detection with WebSocket)"
print("=*80)"

        # Create agent simulator
simulator = AgentSimulator(execution_tracker)

        # Setup execution context
context = AgentExecutionContext( )
run_id="integration-death-test,"
agent_name="integration-triage-agent,"
thread_id="integration-thread,"
user_id="integration-user"
        

        # Start execution
execution_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
        

print("")

        # Verify startup notification
startup_notifications = websocket_bridge.get_notifications_by_type('execution_started')
assert len(startup_notifications) == 1
assert startup_notifications[0]['data']['agent_name'] == context.agent_name
print(" PASS:  Execution started notification sent)"

        # Simulate agent working normally
work_phases = [ ]
{'stage': 'initialization', 'percentage': 20, 'message': 'Initializing triage...', 'duration': 0.5},
{'stage': 'analysis', 'percentage': 40, 'message': 'Analyzing user request...', 'duration': 0.5},
{'stage': 'processing', 'percentage': 60, 'message': 'Processing triage logic...', 'duration': 0.5}
        

await simulator.do_work_phases(work_phases)

        # Verify progress notifications
progress_notifications = websocket_bridge.get_notifications_by_type('execution_progress')
assert len(progress_notifications) >= 3
print("")

        # Verify execution is healthy
status = await execution_tracker.get_execution_status(execution_id)
assert status.heartbeat_status.is_alive
print(" PASS:  Agent confirmed alive and working)"

        # AGENT DEATH SIMULATION
    print("\
[U+1F480] SIMULATING AGENT DEATH...")"
await simulator.die_silently()

        # Wait for death detection
death_detected = False
max_wait_seconds = 15

for i in range(max_wait_seconds):
await asyncio.sleep(1)

            # Check for death notifications
death_notifications = websocket_bridge.get_notifications_by_type('agent_death')
failure_notifications = websocket_bridge.get_notifications_by_type('execution_failed')

if death_notifications or failure_notifications:
    pass
death_detected = True
print("")
break

                # Also check execution status
status = await execution_tracker.get_execution_status(execution_id)
if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
    pass
death_detected = True
print("")
break

                    # Verify death was detected and notifications sent
assert death_detected, "Agent death was not detected within 15 seconds"

death_notifications = websocket_bridge.get_notifications_by_type('agent_death')
failure_notifications = websocket_bridge.get_notifications_by_type('execution_failed')

total_death_notifications = len(death_notifications) + len(failure_notifications)
assert total_death_notifications > 0, "No death notifications were sent"

print("")

                    # Verify final execution state
final_status = await execution_tracker.get_execution_status(execution_id)
assert final_status.execution_record.state in [ExecutionState.FAILED, "ExecutionState.TIMEOUT]"

print(" PASS:  INTEGRATION TEST PASSED: Agent death detected with proper notifications)"
print("=*80)"

@pytest.mark.asyncio
    async def test_multiple_agent_death_scenarios(self, execution_tracker, websocket_bridge):
"""Test multiple agents dying in different ways"""
print("")
 + ="*80)"
print("INTEGRATION TEST: Multiple Agent Death Scenarios)"
print("=*80)"

                        # Create multiple agent simulators
simulators = []
execution_ids = []

scenarios = [ ]
{'name': 'heartbeat-death', 'agent': 'heartbeat-agent'},
{'name': 'timeout-death', 'agent': 'timeout-agent'},
{'name': 'error-death', 'agent': 'error-agent'}
                        

                        # Start all executions
for i, scenario in enumerate(scenarios):
simulator = AgentSimulator(execution_tracker)
simulators.append(simulator)

context = AgentExecutionContext( )
run_id="",
agent_name=scenario['agent'],
thread_id="",
user_id="multi-user"
                            

exec_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
                            
execution_ids.append(exec_id)

print("")

                            # All agents start working
work_phase = {'stage': 'working', 'percentage': 30, 'message': 'Processing...', 'duration': 1.0}

for simulator in simulators:
await simulator.do_work_phases([work_phase])

print(" PASS:  All agents started working)"

                                # Kill agents in different ways
    print("\
[U+1F480] Killing agents with different scenarios...")"

                                # Agent 0: Silent death (heartbeat failure)
await simulators[0].die_silently()
print("[U+1F480] Agent 0: Silent death (heartbeat failure))"

                                # Agent 1: Also silent death but we'll wait for timeout'
await simulators[1].die_silently()
print("[U+1F480] Agent 1: Silent death (timeout))"

                                # Agent 2: Explicit error
await simulators[2].fail_with_error("Simulated agent error)"
print("[U+1F480] Agent 2: Explicit error)"

                                # Wait for all deaths to be detected
deaths_detected = [False, False, False]
max_wait_seconds = 20

for i in range(max_wait_seconds):
await asyncio.sleep(1)

                                    # Check each execution
for j, exec_id in enumerate(execution_ids):
if not deaths_detected[j]:
    pass
status = await execution_tracker.get_execution_status(exec_id)
if status and status.execution_record.state in [ ]
ExecutionState.FAILED,
ExecutionState.TIMEOUT
]:
deaths_detected[j] = True
print("")

if all(deaths_detected):
    pass
break

                                                    # Verify all deaths were detected
for j, detected in enumerate(deaths_detected):
assert detected, ""

                                                        # Verify WebSocket notifications
death_notifications = websocket_bridge.get_notifications_by_type('agent_death')
failure_notifications = websocket_bridge.get_notifications_by_type('execution_failed')
total_notifications = len(death_notifications) + len(failure_notifications)

assert total_notifications >= 3, ""

print("")
print(" PASS:  MULTI-AGENT DEATH TEST PASSED)"
print("=*80)"

@pytest.mark.asyncio
    async def test_agent_recovery_after_death_detection(self, execution_tracker, websocket_bridge):
"""Test recovery mechanisms after agent death is detected"""
pass
print("")
 + ="*80)"
print("INTEGRATION TEST: Agent Recovery After Death Detection)"
print("=*80)"

                                                            # Track recovery attempts
recovery_events = []

                                                            # Mock recovery callback
async def mock_recovery_callback(execution_id: str, error: Exception):
pass
recovery_events.append({ })
'execution_id': execution_id,
'error': str(error),
'timestamp': time.time()
    

    # Setup initial execution
simulator = AgentSimulator(execution_tracker)

context = AgentExecutionContext( )
run_id="recovery-test,"
agent_name="recovery-agent,"
thread_id="recovery-thread,"
user_id="recovery-user"
    

execution_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
    

    # Agent works briefly
    # Removed problematic line: await simulator.do_work_phases([ ])
{'stage': 'initial', 'percentage': 25, 'message': 'Starting work...', 'duration': 0.5}
    

print("")

    # Simulate death
await simulator.die_silently()
print("[U+1F480] Agent died silently)"

    # Wait for death detection
death_detected = False
for i in range(10):
await asyncio.sleep(1)
status = await execution_tracker.get_execution_status(execution_id)

if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
    pass
death_detected = True
print("")
break

assert death_detected, "Death was not detected"

            # Simulate recovery attempt (new execution)
    print("\
CYCLE:  Attempting recovery...")"

recovery_simulator = AgentSimulator(execution_tracker)
recovery_context = AgentExecutionContext( )
run_id="recovery-attempt,"
agent_name="recovery-agent-v2,"
thread_id=context.thread_id,  # Same thread
user_id=context.user_id,
retry_count=1  # This is a retry
            

recovery_execution_id = await recovery_simulator.start_execution( )
recovery_context.run_id,
recovery_context.agent_name,
recovery_context
            

            # Recovery agent does the work
            # Removed problematic line: await recovery_simulator.do_work_phases([ ])
{'stage': 'recovery_init', 'percentage': 20, 'message': 'Recovery starting...', 'duration': 0.5},
{'stage': 'recovery_work', 'percentage': 60, 'message': 'Redoing work...', 'duration': 0.5},
{'stage': 'recovery_complete', 'percentage': 100, 'message': 'Recovery complete', 'duration': 0.5}
            

            # Complete successfully
await recovery_simulator.complete_successfully({"recovery": True, "original_failed: execution_id})"

            # Verify recovery execution succeeded
recovery_status = await execution_tracker.get_execution_status(recovery_execution_id)
assert recovery_status.execution_record.state == ExecutionState.SUCCESS

            # Check WebSocket notifications include recovery
completion_notifications = websocket_bridge.get_notifications_by_type('execution_completed')
assert len(completion_notifications) > 0

recovery_notification = completion_notifications[-1]  # Latest completion
assert recovery_notification['data']['agent_name'] == 'recovery-agent-v2'

print(" PASS:  Recovery execution completed successfully)"
print(" PASS:  RECOVERY TEST PASSED)"
print("=*80)"

@pytest.mark.asyncio
    async def test_health_monitoring_integration(self, execution_tracker, websocket_bridge):
"""Test health monitoring integration with execution tracking"""
print("")
 + ="*80)"
print("INTEGRATION TEST: Health Monitoring Integration)"
print("=*80)"

                # Get initial health status
initial_health = await execution_tracker.get_health_status()
print("")
print("")
print("")

                # Start several executions
simulators = []
execution_ids = []

for i in range(3):
simulator = AgentSimulator(execution_tracker)
simulators.append(simulator)

context = AgentExecutionContext( )
run_id="",
agent_name="",
thread_id="",
user_id="health-user"
                    

exec_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
                    
execution_ids.append(exec_id)

                    # Let agents work briefly
for simulator in simulators:
                        # Removed problematic line: await simulator.do_work_phases([ ])
{'stage': 'health_work', 'percentage': 40, 'message': 'Health testing...', 'duration': 0.5}
                        

                        # Check health with active executions
active_health = await execution_tracker.get_health_status()
print(f"\
CHART:  Health with active executions:")"
print("")
print("")
print("")

assert active_health['active_executions'] > 0
assert active_health['status'] in ['healthy', "'degraded']  # Should still be healthy"

                        # Kill some agents
await simulators[0].die_silently()
await simulators[1].die_silently()
                        # Let simulators[2] continue working

                        # Wait for deaths to be detected
await asyncio.sleep(8)  # Wait for heartbeat failures

                        # Check health after deaths
death_health = await execution_tracker.get_health_status()
print(f"\
[U+1F480] Health after agent deaths:")"
print("")
print("")
print("")
print("")

                        # Health status should reflect the problems
assert death_health['dead_agents'] > 0 or death_health['timed_out_agents'] > 0
                        # Status might be degraded or critical depending on implementation

                        # Complete the remaining agent successfully
await simulators[2].complete_successfully({"health_test": "passed})"

                        # Final health check
await asyncio.sleep(2)  # Let cleanup happen
final_health = await execution_tracker.get_health_status()
print(f"\
[U+1F3C1] Final health status:")"
print("")
print("")

print(" PASS:  HEALTH MONITORING INTEGRATION TEST PASSED)"
print("=*80)"

@pytest.mark.asyncio
    async def test_execution_metrics_during_death_scenarios(self, execution_tracker, websocket_bridge):
"""Test that execution metrics are accurate during death scenarios"""
pass
print("")
 + ="*80)"
print("INTEGRATION TEST: Execution Metrics During Death Scenarios)"
print("=*80)"

                            # Get initial metrics
initial_metrics = await execution_tracker.get_tracker_metrics()
print(f" CHART:  Initial metrics:)"
print("")
print("")
print("")

                            # Create executions with different outcomes
scenarios = [ ]
{'name': 'success', 'outcome': 'complete'},
{'name': 'heartbeat_death', 'outcome': 'die'},
{'name': 'timeout_death', 'outcome': 'die'},
{'name': 'explicit_failure', 'outcome': 'error'},
{'name': 'another_success', 'outcome': 'complete'}
                            

simulators = []
execution_ids = []

                            # Start all executions
for scenario in scenarios:
simulator = AgentSimulator(execution_tracker)
simulators.append(simulator)

context = AgentExecutionContext( )
run_id="",
agent_name="",
thread_id="",
user_id="metrics-user"
                                

exec_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
                                
execution_ids.append(exec_id)

print("")

                                # Let all agents work briefly
for simulator in simulators:
                                    # Removed problematic line: await simulator.do_work_phases([ ])
{'stage': 'metrics_work', 'percentage': 50, 'message': 'Working...', 'duration': 0.5}
                                    

                                    # Execute different outcomes
    print("\
CHART:  Executing different scenarios...")"

                                    # Success cases
await simulators[0].complete_successfully({"test": "success1})"
await simulators[4].complete_successfully({"test": "success2})"
print(" PASS:  Completed 2 successful executions)"

                                    # Death cases
await simulators[1].die_silently()  # heartbeat death
await simulators[2].die_silently()  # timeout death
print("[U+1F480] Killed 2 agents silently)"

                                    # Explicit error
await simulators[3].fail_with_error("Explicit test failure)"
print(" FAIL:  Failed 1 agent explicitly)"

                                    # Wait for deaths to be detected
await asyncio.sleep(10)

                                    # Get final metrics
final_metrics = await execution_tracker.get_tracker_metrics()
tracker_metrics = final_metrics['tracker_metrics']

print(f"\
CHART:  Final metrics:")"
print("")
print("")
print("")
print("")

                                    # Verify metrics accuracy
expected_total = initial_metrics['tracker_metrics']['total_executions_started'] + 5
expected_success = initial_metrics['tracker_metrics']['successful_executions'] + 2  # 2 completed
expected_failures = initial_metrics['tracker_metrics']['failed_executions'] + 3  # 2 died + 1 error

assert tracker_metrics['total_executions_started'] == expected_total
assert tracker_metrics['successful_executions'] == expected_success
assert tracker_metrics['failed_executions'] >= expected_failures  # >= because some might still be detecting

                                    # Success rate should be reasonable
expected_rate = expected_success / expected_total
actual_rate = tracker_metrics['success_rate']

                                    # Allow some tolerance for timing
assert abs(actual_rate - expected_rate) < 0.2, \
""

print(" PASS:  METRICS TEST PASSED - All metrics accurate during death scenarios)"
print("=*80)"

@pytest.mark.asyncio
    async def test_concurrent_agent_deaths(self, execution_tracker, websocket_bridge):
"""Test handling of multiple simultaneous agent deaths"""
print("")
 + ="*80)"
print("INTEGRATION TEST: Concurrent Agent Deaths)"
print("=*80)"

                                        # Start many agents simultaneously
num_agents = 8
simulators = []
execution_ids = []

print("")

                                        # Start all agents
for i in range(num_agents):
simulator = AgentSimulator(execution_tracker)
simulators.append(simulator)

context = AgentExecutionContext( )
run_id="",
agent_name="",
thread_id="",
user_id="concurrent-user"
                                            

exec_id = await simulator.start_execution( )
context.run_id,
context.agent_name,
context
                                            
execution_ids.append(exec_id)

print("")

                                            # Let all agents start working
for simulator in simulators:
                                                # Removed problematic line: await simulator.do_work_phases([ ])
{'stage': 'concurrent_work', 'percentage': 30, 'message': 'Working concurrently...', 'duration': 0.2}
                                                

print(" PASS:  All agents working)"

                                                # Kill most agents simultaneously
kill_count = 6  # Kill 6 out of 8
print("")

                                                # Kill agents at the same time
kill_tasks = []
for i in range(kill_count):
kill_tasks.append(simulators[i].die_silently())

                                                    # Execute all kills concurrently
await asyncio.gather(*kill_tasks)
print("")

                                                    # Let remaining agents complete
for i in range(kill_count, num_agents):
await simulators[i].complete_successfully({"concurrent_test": "})"

print("")

                                                        # Wait for all deaths to be detected
    print("\
SEARCH:  Waiting for death detection...")"
deaths_detected = 0
max_wait_seconds = 20

for wait_second in range(max_wait_seconds):
await asyncio.sleep(1)

current_deaths = 0
for i in range(kill_count):  # Only check the killed ones
status = await execution_tracker.get_execution_status(execution_ids[i])
if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
    pass
current_deaths += 1

if current_deaths > deaths_detected:
    pass
deaths_detected = current_deaths
print("")

if deaths_detected >= kill_count:
    pass
break

                                                                        # Verify all deaths were detected
final_deaths_detected = 0
for i in range(kill_count):
status = await execution_tracker.get_execution_status(execution_ids[i])
if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
    pass
final_deaths_detected += 1

print(f"\
CHART:  Final results:")"
print("")
print("")
print("")

                                                                                # We should detect most deaths (allow some tolerance for timing)
detection_rate = final_deaths_detected / kill_count
assert detection_rate >= 0.8, \
""

                                                                                # Check WebSocket notifications
death_notifications = websocket_bridge.get_notifications_by_type('agent_death')
failure_notifications = websocket_bridge.get_notifications_by_type('execution_failed')
total_death_notifications = len(death_notifications) + len(failure_notifications)

print("")

                                                                                # Should have notifications for most/all deaths
assert total_death_notifications >= final_deaths_detected, \
""

print(" PASS:  CONCURRENT DEATH TEST PASSED)"
print("=*80)"


if __name__ == "__main__:"
                                                                                    # Run integration tests
import sys

print("")
 + ="*80)"
print("AGENT DEATH RECOVERY INTEGRATION TEST SUITE)"
print("=*80)"
print("Testing integration of execution tracking with agent death recovery)"
print("These tests verify end-to-end agent failure handling)"
print("="*80 + " )"
")"

pytest.main([__file__, "-v", "--tb=short", "-s])"
pass
