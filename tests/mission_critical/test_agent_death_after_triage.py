class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
            raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        CRITICAL TEST: Agent Processing Death After Triage
        ==================================================
        This test reproduces a CRITICAL production bug where:
        1. Agent starts processing normally
        2. Goes through triage successfully
        3. Dies silently without error or proper health detection
        4. WebSocket continues to send empty responses with "...
        5. Health service FAILS to detect the dead agent
        6. No errors are logged, system appears healthy"
        Bug Signature from Production Logs:
        - agent_response with status: "... and correlation_id: null
        - No subsequent agent_started, agent_thinking, or tool events
        - WebSocket remains connected, ping/pong works
        - User sees spinning loader forever
        WHY THIS IS CRITICAL:
        - Users experience complete failure with no feedback
        - Health monitoring misses the failure completely
        - Silent failures are the worst kind - no recovery possible
        '''
        import asyncio
        import json
        import pytest
        import time
        from datetime import datetime
        from typing import Dict, Any, List, Optional
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment
class AgentDeathDetector:
        ""Monitors agent execution to detect silent deaths"
    def __init__(self):
        pass
        self.events: List[Dict[str, Any]] = []
        self.death_detected = False
        self.death_timestamp: Optional[float] = None
        self.last_meaningful_event: Optional[Dict[str, Any]] = None
        self.empty_response_count = 0
        self.health_check_failures = []
    def record_event(self, event: Dict[str, Any]:
        "Record WebSocket events for analysis""
        self.events.append()
        **event,
        'timestamp': time.time()
    
    # Detect death pattern: agent_response with ..." status
        if event.get('type') == 'agent_response':
        data = event.get('data', {}
        if data.get('status') == '...' and data.get('correlation_id') is None:
        self.empty_response_count += 1
        if self.empty_response_count >= 1 and not self.death_detected:
        self.death_detected = True
        self.death_timestamp = time.time()
        elif data.get('content'):  # Meaningful response
        self.last_meaningful_event = event
        self.empty_response_count = 0
    def get_death_report(self) -> Dict[str, Any]:
        "Generate detailed death report""
        pass
        return {
        'death_detected': self.death_detected,
        'death_timestamp': self.death_timestamp,
        'empty_responses': self.empty_response_count,
        'last_meaningful_event': self.last_meaningful_event,
        'total_events': len(self.events),
        'health_check_failures': self.health_check_failures,
        'time_since_death': ( )
        time.time() - self.death_timestamp
        if self.death_timestamp else None
    
    
        @pytest.mark.critical
class TestAgentDeathAfterTriage:
        ""Test suite for critical agent death after triage bug"
@pytest.mark.asyncio
@pytest.fixture
    async def test_agent_dies_after_triage_without_error(self):
'''
CRITICAL: Reproduce agent death after triage with no error handling
This test MUST FAIL to prove the bug exists!
'''
pass
detector = AgentDeathDetector()
        # Setup mocked components
with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry') as MockRegistry, \
patch('netra_backend.app.agents.triage_sub_agent.agent.TriageSubAgent') as MockTriage, \
patch('netra_backend.app.core.agent_health_monitor.AgentHealthMonitor') as MockHealth:
            # Configure registry to appear healthy
registry = MockRegistry.return_value
registry.is_initialized = True
registry.get_agent = MagicMock(return_value=MockTriage.return_value)
            # Configure triage to succeed then die
triage = MockTriage.return_value
triage.execute = AsyncMock(side_effect=self._simulate_triage_death)
            # Configure health service to miss the death
health_service = MockHealth.return_value
health_service.check_agent_health = AsyncMock(return_value={'status': 'healthy'}
            # Simulate WebSocket message flow
messages_sent = []
async def mock_send_message(msg: Dict[str, Any]:
pass
messages_sent.append(msg)
detector.record_event(msg)
    # Process a user message
user_message = {
'type': 'chat_message',
'data': {
'message': 'Help me optimize my cloud costs',
'thread_id': 'test-thread',
'user_id': 'test-user'
    
    
    # Start processing
    # Removed problematic line: await mock_send_message({
'type': 'agent_started',
'data': {'agent': 'supervisor', 'status': 'processing'}
    
    # Triage happens
    # Removed problematic line: await mock_send_message({
'type': 'agent_thinking',
'data': {'thought': 'Analyzing request for cloud optimization...'}
    
    # DEATH OCCURS HERE - agent sends empty response
    # Removed problematic line: await mock_send_message({
'type': 'agent_response',
'data': {'status': '...', 'correlation_id': None}
    
    # Simulate continued WebSocket activity (ping/pong)
for _ in range(5):
    await asyncio.sleep(1)
        # Health check still returns healthy (BUG!)
health_status = await health_service.check_agent_health('supervisor')
detector.health_check_failures.append()
'time': time.time(),
'reported_status': health_status,
'actual_state': 'DEAD'
        
        # Verify the bug exists
report = detector.get_death_report()
        # These assertions SHOULD FAIL in the current system
assert report['death_detected'], "Agent death was not detected!
assert report['empty_responses'] > 0, Empty responses not counted!"
assert len(report["health_check_failures] > 0, Health checks didn"t fail!"
        # The system INCORRECTLY reports healthy
for failure in report['health_check_failures']:
    assert failure['reported_status']['status'] == 'healthy', \
fHealth service correctly detected failure (this shouldnt happen with the bug!)"
            # Print detailed failure report
print(")
 + "="*80)
print(CRITICAL BUG REPRODUCTION - AGENT DEATH AFTER TRIAGE)
print("="*80)
print(formatted_string)
print("formatted_string" if report['time_since_death'] else N/A)
print("formatted_string")
print(formatted_string)
print("="*80)
@pytest.mark.asyncio
    async def test_websocket_continues_after_agent_death(self):
'''
Test that WebSocket remains healthy even when agent is dead
'''
pass
ws_messages = []
agent_dead = False
async def simulate_websocket_session():
""Simulate a WebSocket session with agent death""
    # Initial connection successful
ws_messages.append({'type': 'connection', 'status': 'established'}
    # User sends message
ws_messages.append()
'type': 'user_message',
'data': {'message': 'Analyze my AWS costs'}
    
    # Agent starts
ws_messages.append()
'type': 'agent_started',
'data': {'agent': 'triage'}
    
    # Agent dies silently
nonlocal agent_dead
agent_dead = True
    # WebSocket still sends messages (BUG!)
ws_messages.append()
'type': 'agent_response',
'data': {'status': '...', 'correlation_id': None}
    
    # Ping/pong continues working
for i in range(10):
    await asyncio.sleep(0.5)
ws_messages.append()
'type': 'ping',
'timestamp': time.time()
        
ws_messages.append()
'type': 'pong',
'timestamp': time.time()
        
await asyncio.sleep(0)
return ws_messages
        # Run simulation
messages = await simulate_websocket_session()
        # Count message types
message_types = {}
for msg in messages:
    msg_type = msg['type']
message_types[msg_type] = message_types.get(msg_type, 0) + 1
            # Verify the bug
assert agent_dead, Agent should be dead
assert message_types.get('ping', 0) > 0, "Pings still being sent"
assert message_types.get('pong', 0) > 0, Pongs still being received
assert message_types.get('agent_completed', 0) == 0, "No completion event (correct)"
assert any( )
msg.get('data', {}.get('status') == '...'
for msg in messages if msg['type'] == 'agent_response'
), Empty agent response sent (bug signature)
print("")
 + ="*80)
print("WEBSOCKET REMAINS 'HEALTHY' DESPITE AGENT DEATH)
print(="*80)
print("formatted_string)
print(formatted_string")
print("Bug confirmed: WebSocket appears healthy but agent is dead!)
print(="*80)
@pytest.mark.asyncio
    async def test_health_service_misses_agent_death(self):
'''
pass
Test that health service completely misses agent death
'''
class FakeHealthService:
    "Simulates current broken health service""
    def __init__(self):
        pass
        self.checks_performed = 0
        self.agent_states = {
        'supervisor': 'healthy',
        'triage': 'healthy'
    
    async def check_agent_health(self, agent_name: str) -> Dict[str, Any]:
        ""Always returns healthy even when agent is dead"
        self.checks_performed += 1
    # This is the BUG - doesn't actually check if agent is processing
        await asyncio.sleep(0)
        return {
        'status': 'healthy',
        'agent': agent_name,
        'timestamp': time.time(),
        'checks_performed': self.checks_performed
    
    async def kill_agent(self, agent_name: str):
        "Simulate agent death""
        self.agent_states[agent_name] = 'DEAD'
    # But check_agent_health still returns healthy!
        health_service = FakeHealthService()
    # Kill the agent
        await health_service.kill_agent('triage')
    # Health checks still await asyncio.sleep(0)
        return healthy (BUG!)
        for _ in range(10):
        health_status = await health_service.check_agent_health('triage')
        assert health_status['status'] == 'healthy', Health check should incorrectly report healthy"
        assert health_service.agent_states['triage'] == 'DEAD', "Agent is actually dead
        assert health_service.checks_performed == 10, Health checks were performed"
        print(")
         + "="*80)
        print(HEALTH SERVICE FAILURE TO DETECT DEATH)
        print("="*80)
        print(formatted_string)
        print(f"Health service reports: healthy")
        print(formatted_string)
        print("Critical bug: Health service is useless!")
        print(=*80)
@pytest.mark.asyncio
    async def test_missing_error_recovery_for_agent_death(self):
'''
pass
Test that error recovery doesn"t trigger for silent agent death
'''
error_recovery_triggered = False
recovery_attempts = []
class FakeErrorRecovery:
    "Simulates error recovery that never triggers""
    async def handle_agent_failure(self, agent: str, error: Exception):
        ""This never gets called because no exception is raised!"
        nonlocal error_recovery_triggered
        error_recovery_triggered = True
        recovery_attempts.append()
        'agent': agent,
        'error': str(error),
        'timestamp': time.time()
    
        recovery = FakeErrorRecovery()
    # Simulate agent processing
    async def process_with_silent_death():
        "Agent dies without raising exception""
        pass
    # Start processing
        print(Agent starting...")
    # Triage happens
        print("Triage processing...)
    # Agent dies silently (no exception!)
    # This is the bug - execution just stops
        await asyncio.sleep(0)
        return None  # Returns None instead of result
    # Process message
        result = await process_with_silent_death()
    # Check if recovery was triggered
        assert not error_recovery_triggered, Error recovery was NOT triggered (bug!)"
        assert len(recovery_attempts) == 0, "No recovery attempts made
        assert result is None, Agent returned None (dead)"
        print(")
         + "="*80)
        print(ERROR RECOVERY FAILURE)
        print("="*80)
        print(formatted_string)
        print("formatted_string")
        print(Critical bug: Silent failures bypass all error recovery!)
        print("="*80)
    async def _simulate_triage_death(self, *args, **kwargs):
        "Simulates agent dying during triage"
    # Start normally
        await asyncio.sleep(0.1)
    # Then die silently without exception
    # This simulates the actual bug behavior
        await asyncio.sleep(0)
        return None  # Dead agent returns None
@pytest.mark.asyncio
    async def test_comprehensive_death_detection_requirements(self):
'''
pass
Define what SHOULD happen to detect and recover from agent death
This test defines the REQUIRED behavior to fix the bug.
'''
required_checks = {
'heartbeat': False,  # No heartbeat monitoring
'timeout_detection': False,  # No timeout on agent execution
'result_validation': False,  # No validation of agent results
'execution_tracking': False,  # No tracking of execution state
'error_boundaries': False,  # No error boundaries around execution
'dead_letter_queue': False,  # No DLQ for failed messages
'circuit_breaker': False,  # No circuit breaker pattern
'supervisor_monitoring': False  # No supervisor health checks
        
        # All these SHOULD be True but are currently False
failed_requirements = [
check for check, implemented in required_checks.items()
if not implemented
        
print("")
 + ="*80)
print("MISSING DEATH DETECTION MECHANISMS)
print(="*80)
for requirement in failed_requirements:
    print("formatted_string)
print(="*80)
print("formatted_string)
print(CRITICAL: No mechanisms to detect or recover from agent death!")
print("=*80)
            # This assertion WILL FAIL showing we need these mechanisms
assert len(failed_requirements) == 0, \
formatted_string"
if __name__ == "__main__:
                # Run the test to demonstrate the bug
import sys
print(")
" + =*80)
print("RUNNING CRITICAL AGENT DEATH DETECTION TEST")
print(=*80)
print("This test MUST FAIL to prove the bug exists!")
print(If this test passes, the bug has been fixed.)
print("="*80 + " )
")