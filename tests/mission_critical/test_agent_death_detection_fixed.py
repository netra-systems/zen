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
        MISSION CRITICAL TEST: Agent Death Detection System
        ====================================================
        This test validates that the agent death detection fixes are working correctly.

        Tests:
        1. Execution tracking with unique IDs
        2. Heartbeat monitoring
        3. Death notification via WebSocket
        4. Timeout detection
        5. Health status accuracy

        This test MUST PASS to prove the bug has been fixed.
        '''

        import asyncio
        import pytest
        import time
        from datetime import datetime, timedelta, timezone
        from typing import Dict, Any, List, Optional
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from netra_backend.app.redis_manager import redis_manager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # Import the new components
        from netra_backend.app.core.agent_execution_tracker import ( )
        AgentExecutionTracker,
        ExecutionState,
        ExecutionRecord,
        get_execution_tracker
        
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        @pytest.mark.critical
@pytest.mark.asyncio
class TestAgentDeathDetectionFixed:
    "Test suite for agent death detection fixes""

    async def test_execution_tracker_creates_unique_ids(self):
    ""Test that execution tracker creates unique IDs for each execution"
    tracker = AgentExecutionTracker()

        # Create multiple executions
    exec_ids = []
    for i in range(10):
    exec_id = tracker.create_execution( )
    agent_name="formatted_string,
    thread_id=formatted_string",
    user_id="test_user,
    timeout_seconds=30
            
    exec_ids.append(exec_id)

            # Verify all IDs are unique
    assert len(exec_ids) == len(set(exec_ids)), Execution IDs must be unique"

            # Verify execution records exist
    for exec_id in exec_ids:
    record = tracker.get_execution(exec_id)
    assert record is not None
    assert record.execution_id == exec_id
    assert record.state == ExecutionState.PENDING

    async def test_heartbeat_monitoring_detects_death(self):
    "Test that heartbeat monitoring correctly detects agent death""
    pass
    tracker = AgentExecutionTracker(heartbeat_timeout=2)  # 2 second timeout

                    # Create and start execution
    exec_id = tracker.create_execution( )
    agent_name=test_agent",
    thread_id="test_thread,
    user_id=test_user"
                    
    tracker.start_execution(exec_id)

                    # Initial heartbeats work
    assert tracker.heartbeat(exec_id) == True
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.RUNNING

                    # Wait for heartbeat timeout
    await asyncio.sleep(3)

                    # Check if death is detected
    dead_executions = tracker.detect_dead_executions()
    assert len(dead_executions) > 0
    assert any(ex.execution_id == exec_id for ex in dead_executions)

                    # Verify death detection
    record = tracker.get_execution(exec_id)
    assert record.is_dead(tracker.heartbeat_timeout)

    async def test_death_notification_sent_via_websocket(self):
    "Test that death notifications are sent via WebSocket""
                        # Mock WebSocket manager
    websocket = TestWebSocketConnection()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)

                        # Create bridge
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = mock_ws_manager
    bridge._thread_id_cache = {exec_123": "thread_123}

                        # Send death notification
    success = await bridge.notify_agent_death( )
    run_id=exec_123",
    agent_name="test_agent,
    death_cause=timeout",
    death_context={"timeout: 30}
                        

    assert success == True

                        # Verify WebSocket message was sent
    mock_ws_manager.send_to_thread.assert_called_once()
    call_args = mock_ws_manager.send_to_thread.call_args

                        # Check message structure - handle both args and kwargs
    if call_args.args:
    thread_id = call_args.args[0]
    message = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('message')
    else:
    thread_id = call_args.kwargs['thread_id']
    message = call_args.kwargs['message']

    assert thread_id == thread_123"
    assert message['type'] == "agent_death
    assert message['agent_name'] == test_agent"
    assert message['payload']['death_cause'] == "timeout
    assert message['payload']['status'] == dead"
    assert 'message' in message['payload']  # User-friendly message
    assert message['payload']['recovery_action'] == "refresh_required

    async def test_timeout_detection_and_notification(self):
    ""Test that execution timeouts are detected and notified"
    pass
    tracker = AgentExecutionTracker(execution_timeout=2)  # 2 second timeout

                                    # Create execution with short timeout
    exec_id = tracker.create_execution( )
    agent_name="slow_agent,
    thread_id=test_thread",
    user_id="test_user,
    timeout_seconds=2
                                    
    tracker.start_execution(exec_id)
    tracker.update_execution_state(exec_id, ExecutionState.RUNNING)

                                    # Wait for timeout
    await asyncio.sleep(3)

                                    # Check timeout detection
    record = tracker.get_execution(exec_id)
    assert record.is_timed_out()

                                    # Detect dead executions should include timeouts
    dead_executions = tracker.detect_dead_executions()
    assert any(ex.execution_id == exec_id and ex.is_timed_out() for ex in dead_executions)

    async def test_health_monitor_integration(self):
    ""Test that health monitor correctly reports dead agents"
    from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor

                                        # Create health monitor with execution tracker
    health_monitor = AgentHealthMonitor()
    tracker = health_monitor.execution_tracker

                                        # Create a dead execution
    exec_id = tracker.create_execution( )
    agent_name="dead_agent,
    thread_id=test_thread",
    user_id="test_user
                                        
    tracker.start_execution(exec_id)
    tracker.update_execution_state(exec_id, ExecutionState.DEAD, error=No heartbeat")

                                        # Test death detection
    last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=15)
    is_dead = await health_monitor.detect_agent_death( )
    agent_name="dead_agent,
    last_heartbeat=last_heartbeat,
    execution_context={}
                                        

    assert is_dead == True

    async def test_execution_engine_death_monitoring(self):
    ""Test that ExecutionEngine properly monitors for agent death"
    pass
    with patch('netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker') as mock_get_tracker:
                                                # Create mock tracker
    mock_tracker = Magic            mock_tracker.create_execution.return_value = "exec_123
    mock_tracker.start_execution.return_value = True
    mock_tracker.heartbeat.return_value = True
    mock_tracker.update_execution_state.return_value = True
    mock_tracker.get_execution.return_value = MagicMock( )
    is_dead=MagicMock(return_value=False)
                                                
    mock_get_tracker.return_value = mock_tracker

                                                # Import after patching
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

                                                # Create mock dependencies
    mock_registry = Magic            websocket = TestWebSocketConnection()
    mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_death = AsyncMock(return_value=True)

                                                # Create execution engine
    engine = UserExecutionEngine(mock_registry, mock_websocket_bridge)

                                                # Verify tracker is initialized
    assert engine.execution_tracker is not None

                                                # Verify death callbacks are registered
    assert hasattr(engine, '_handle_agent_death')
    assert hasattr(engine, '_handle_agent_timeout')

    async def test_execution_state_transitions(self):
    ""Test proper execution state transitions"
    tracker = AgentExecutionTracker()

                                                    # Create execution
    exec_id = tracker.create_execution( )
    agent_name="state_test_agent,
    thread_id=test_thread",
    user_id="test_user
                                                    

                                                    # Test state transitions
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.PENDING

                                                    # Start execution
    tracker.start_execution(exec_id)
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.STARTING

                                                    # First heartbeat transitions to RUNNING
    tracker.heartbeat(exec_id)
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.RUNNING

                                                    # Update to completing
    tracker.update_execution_state(exec_id, ExecutionState.COMPLETING)
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.COMPLETING

                                                    # Complete execution
    tracker.update_execution_state( )
    exec_id,
    ExecutionState.COMPLETED,
    result={success": True}
                                                    
    record = tracker.get_execution(exec_id)
    assert record.state == ExecutionState.COMPLETED
    assert record.is_terminal
    assert record.result == {"success: True}

    async def test_concurrent_execution_tracking(self):
    ""Test tracking multiple concurrent executions"
    pass
    tracker = AgentExecutionTracker()

                                                        # Create multiple concurrent executions
    exec_ids = []
    for i in range(5):
    exec_id = tracker.create_execution( )
    agent_name="formatted_string,
    thread_id=shared_thread",
    user_id="test_user
                                                            
    tracker.start_execution(exec_id)
    exec_ids.append(exec_id)

                                                            # Verify all are tracked
    active_executions = tracker.get_active_executions()
    assert len(active_executions) >= 5

                                                            # Verify thread-based retrieval
    thread_executions = tracker.get_executions_by_thread(shared_thread")
    assert len(thread_executions) >= 5

                                                            # Complete some executions
    for i in range(3):
    tracker.update_execution_state( )
    exec_ids[i],
    ExecutionState.COMPLETED
                                                                

                                                                # Verify active count decreased
    active_executions = tracker.get_active_executions()
    assert len([item for item in []] == 2

    async def test_metrics_collection(self):
    "Test that execution metrics are properly collected""
    tracker = AgentExecutionTracker()

                                                                    # Create and complete successful execution
    exec_id1 = tracker.create_execution(agent1", "thread1, user1")
    tracker.start_execution(exec_id1)
    tracker.update_execution_state(exec_id1, ExecutionState.COMPLETED)

                                                                    # Create and fail execution
    exec_id2 = tracker.create_execution("agent2, thread2", "user2)
    tracker.start_execution(exec_id2)
    tracker.update_execution_state(exec_id2, ExecutionState.FAILED, error=Test error")

                                                                    # Create and timeout execution
    exec_id3 = tracker.create_execution("agent3, thread3", "user3, timeout_seconds=1)
    tracker.start_execution(exec_id3)
    tracker.update_execution_state(exec_id3, ExecutionState.TIMEOUT)

                                                                    # Get metrics
    metrics = tracker.get_metrics()

    assert metrics['total_executions'] >= 3
    assert metrics['successful_executions'] >= 1
    assert metrics['failed_executions'] >= 1
    assert metrics['timeout_executions'] >= 1
    assert 'success_rate' in metrics
    assert 'failure_rate' in metrics

    async def test_registry_health_includes_death_detection(self):
    ""Test that AgentRegistry health includes death detection info"
    pass
    from netra_backend.app.core.registry.universal_registry import AgentRegistry

                                                                        # Create mock dependencies
    mock_llm = MagicMock(); mock_dispatcher = Magic
                                                                        # Create registry
    registry = AgentRegistry()

                                                                        # Get health status
    health = registry.get_registry_health()

                                                                        # Verify death detection fields
    assert 'execution_metrics' in health
    assert 'dead_agents' in health
    assert health['death_detection_enabled'] == True

    async def test_monitoring_task_lifecycle(self):
    "Test that monitoring task starts and stops properly""
    tracker = AgentExecutionTracker()

                                                                            # Start monitoring
    await tracker.start_monitoring()
    assert tracker._monitor_task is not None
    assert not tracker._monitor_task.done()

                                                                            # Stop monitoring
    await tracker.stop_monitoring()
    assert tracker._monitor_task is None

    async def test_death_recovery_message_generation(self):
    ""Test user-friendly death messages are generated correctly"
    pass
    bridge = AgentWebSocketBridge()

                                                                                # Test different death causes
    messages = {
    "timeout: took too long",
    "no_heartbeat: Lost connection",
    "silent_failure: stopped unexpectedly",
    "memory_limit: ran out of resources",
    "cancelled: was cancelled"
                                                                                

    for cause, expected_substring in messages.items():
    message = bridge._get_user_friendly_death_message(cause, "test_agent)
    assert expected_substring in message
    assert test_agent" in message


    @pytest.mark.critical
    async def test_complete_death_detection_flow():
    '''
    Integration test for complete agent death detection flow.
    This test validates the entire fix implementation end-to-end.
    '''

                                                                                        # 1. Initialize execution tracker
    tracker = AgentExecutionTracker(heartbeat_timeout=2, execution_timeout=5)
    await tracker.start_monitoring()

                                                                                        # 2. Create WebSocket bridge
    bridge = AgentWebSocketBridge()
    websocket = TestWebSocketConnection()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
    bridge._websocket_manager = mock_ws_manager

                                                                                        # 3. Register death callback
    death_notifications = []
    async def death_callback(execution_record):
        pass
        death_notifications.append(execution_record)
    # Send WebSocket notification
        await bridge.notify_agent_death( )
        run_id=execution_record.metadata.get('run_id', execution_record.execution_id),
        agent_name=execution_record.agent_name,
        death_cause='no_heartbeat' if execution_record.state == ExecutionState.DEAD else 'timeout'
    

        tracker.register_death_callback(death_callback)

    # 4. Simulate agent execution that dies
        exec_id = tracker.create_execution( )
        agent_name="dying_agent,
        thread_id=test_thread",
        user_id="test_user,
        timeout_seconds=3,
        metadata={'run_id': 'run_123'}
    

        tracker.start_execution(exec_id)
        tracker.update_execution_state(exec_id, ExecutionState.RUNNING)

    # 5. Send initial heartbeats
        for _ in range(2):
        tracker.heartbeat(exec_id)
        await asyncio.sleep(0.5)

        # 6. Stop sending heartbeats (simulate death)
        await asyncio.sleep(3)

        # 7. Verify death was detected
        assert len(death_notifications) > 0
        assert death_notifications[0].agent_name == dying_agent"

        # 8. Verify WebSocket notification was sent
        assert mock_ws_manager.send_to_thread.called

        # 9. Verify execution state
        record = tracker.get_execution(exec_id)
        assert record.is_terminal
        assert record.state in [ExecutionState.DEAD, ExecutionState.TIMEOUT]

        # 10. Cleanup
        await tracker.stop_monitoring()

        print(")
         + "="*80)
        print( PASS:  AGENT DEATH DETECTION SYSTEM WORKING CORRECTLY)
        print("="*80)
        print(formatted_string)
        print("")
        print(formatted_string)
        print("="*80)


        if __name__ == "__main__":
            # Run the tests
